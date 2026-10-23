#!/usr/bin/env python3
"""
Drop test: home -> 100 mm above the drop preset -> compliant descent -> contact.

The robot moves to home, then linearly to the drop preset plus an approach
height. An optional position-mode descent brings it to the force-start height.
From there it descends in UR force mode with only Z compliant and stops
when the measured vertical force reaches the contact threshold. Because the drop
surface height varies, the contact point is found by force instead of a fixed
position. After contact the script releases the gripper and retracts.

No external F/T sensor is needed: force mode and the contact measurement use the
UR controller's built-in TCP force estimate (`actual_TCP_force` via RTDE).

The drop preset is a normal preset. If it has no stored TCP pose, the script
computes one from its joint values with an explicit active TCP offset in RTDE
forward kinematics. This avoids stale TCP registers in ur_rtde 1.6.5. Both the
drop and approach positions must pass workspace checks before any home move.

Force and pose are read straight from RTDE during the descent, not from the
10 Hz GUI cache, so contact is seen within a few milliseconds.

Gripper: optional. RobotController has no gripper driver, so give
`--gripper-pin` for a standard digital output or `--manual-gripper` to release
by hand. Without either, the script only finds contact and retracts.

Quick start (from the project root):
    ./start.sh drop-test --dry-run      # resolve poses, no motion
    ./start.sh drop-test                # run the test
"""

import argparse
import copy
import logging
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config
from force_control import ForceConfig
from utils import pose_to_matrix

logger = logging.getLogger("drop_contact_test")

# Force mode is commanded in the base frame: only Z is compliant, so the TCP
# descends along base -Z while X/Y and orientation are held.
COMPLIANT_AXES = [0, 0, 1, 0, 0, 0]
BASE_FRAME = [0.0] * 6


class TestAbort(Exception):
    """Abort the test with a message for the operator."""


class NoContact(TestAbort):
    """The descent finished without finding the surface."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Move to home, approach the drop preset from above, descend in UR "
            "force mode until contact, release the gripper and retract."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--ip", default=Config.DEFAULT_IP, help="Robot IP address")
    parser.add_argument("--home-preset", default="home", help="Home preset name")
    parser.add_argument("--drop-preset", default="drop", help="Drop position preset name")
    parser.add_argument(
        "--approach-height-mm", type=float, default=100.0,
        help="Height above the drop pose for the initial position-mode approach",
    )
    parser.add_argument(
        "--force-start-height-mm", type=float, default=None,
        help="Position-mode descend to this height above drop before force mode; "
             "omitting it starts force mode at the initial approach",
    )
    parser.add_argument(
        "--contact-force", type=float, default=10.0,
        help="Measured vertical force (N) that stops the descent",
    )
    parser.add_argument(
        "--command-force", type=float, default=None,
        help="Wrench commanded in force mode (N); defaults to 1.2 x contact force",
    )
    parser.add_argument(
        "--descent-speed-mm-s", type=float, default=10.0,
        help="Maximum descent speed in force mode",
    )
    parser.add_argument(
        "--max-descent-mm", type=float, default=150.0,
        help="Total downward travel budget from initial approach, including fast descent",
    )
    parser.add_argument(
        "--approach-speed-mm-s", type=float, default=50.0,
        help="Position-mode speed for the approach and retract moves",
    )
    parser.add_argument(
        "--lateral-tolerance-mm", type=float, default=5.0,
        help="Allowed X/Y deviation during force mode",
    )
    parser.add_argument(
        "--rotation-tolerance-deg", type=float, default=1.0,
        help="Allowed orientation deviation during force mode",
    )
    parser.add_argument(
        "--settle-s", type=float, default=0.5,
        help="Wait after each position move before the next step",
    )
    parser.add_argument(
        "--release-wait-s", type=float, default=1.0,
        help="Wait after releasing the gripper before retracting",
    )
    parser.add_argument(
        "--retract-mm", type=float, default=100.0,
        help="Retract distance after contact",
    )
    parser.add_argument(
        "--gripper-pin", type=int, default=None,
        help="Standard digital output that opens the gripper (0-7)",
    )
    parser.add_argument(
        "--gripper-release-level", choices=["low", "high"], default="low",
        help="Digital output level that opens the gripper",
    )
    parser.add_argument(
        "--manual-gripper", action="store_true",
        help="Pause at contact so the gripper can be released by hand",
    )
    parser.add_argument(
        "--return-home", action="store_true",
        help="Return to the home preset after retracting",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Resolve and print the poses without moving the robot",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Skip the confirmation prompt",
    )
    return parser


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.approach_height_mm <= 0:
        parser.error("--approach-height-mm must be positive")
    height = args.force_start_height_mm
    if height is not None:
        if not math.isfinite(height) or not 0 <= height <= args.approach_height_mm:
            parser.error("--force-start-height-mm must be between 0 and --approach-height-mm")
        if args.max_descent_mm <= args.approach_height_mm - height:
            parser.error("--max-descent-mm must leave travel for force mode after the fast descent")
    if not ForceConfig.MIN_TARGET_FORCE <= args.contact_force < ForceConfig.MAX_TARGET_FORCE:
        parser.error(
            f"--contact-force must be in "
            f"[{ForceConfig.MIN_TARGET_FORCE}, {ForceConfig.MAX_TARGET_FORCE})"
        )
    if args.command_force is None:
        args.command_force = min(
            args.contact_force * 1.2, ForceConfig.MAX_TARGET_FORCE
        )
    if args.command_force < args.contact_force:
        parser.error("--command-force must be at least --contact-force")
    if args.command_force > ForceConfig.MAX_TARGET_FORCE:
        parser.error(f"--command-force must not exceed {ForceConfig.MAX_TARGET_FORCE} N")

    max_descent_speed = ForceConfig.MAX_LINEAR_SPEED * 1000.0
    if not 0 < args.descent_speed_mm_s <= max_descent_speed:
        parser.error(f"--descent-speed-mm-s must be in (0, {max_descent_speed}]")
    if not 0 < args.approach_speed_mm_s <= max_descent_speed:
        parser.error(f"--approach-speed-mm-s must be in (0, {max_descent_speed}]")
    if args.max_descent_mm <= 0:
        parser.error("--max-descent-mm must be positive")
    if args.lateral_tolerance_mm < 0 or args.rotation_tolerance_deg < 0:
        parser.error("Tolerances cannot be negative")
    if args.retract_mm < 0:
        parser.error("--retract-mm cannot be negative")
    if args.gripper_pin is not None and not 0 <= args.gripper_pin <= 7:
        parser.error("--gripper-pin must be a standard digital output (0-7)")


def wait(app, seconds: float) -> None:
    """Sleep while keeping Qt queued signals (data receiver, safety) flowing."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def read_force_and_pose(robot):
    """Read TCP force and pose directly from RTDE, falling back to the cache."""
    try:
        force = list(robot.rtde_receive.getActualTCPForce())
        pose = list(robot.rtde_receive.getActualTCPPose())
        if len(force) == 6 and len(pose) == 6:
            return force, pose
    except Exception as exc:
        logger.warning("Direct RTDE read failed, using cached data: %s", exc)
    return robot.get_tcp_force(), robot.get_tcp_pose()


def require_six_finite(values, description: str):
    """Reject incomplete or non-finite robot coordinates before planning."""
    try:
        result = [float(value) for value in values]
        if len(result) == 6 and all(math.isfinite(value) for value in result):
            return result
    except (TypeError, ValueError, OverflowError):
        pass
    raise TestAbort(f"{description} must contain six finite values")


def resolve_drop_pose(robot, preset_name: str):
    """Return the TCP pose of a preset without moving to it."""
    preset = robot.preset_manager.get_preset(preset_name)
    if preset is None:
        raise TestAbort(f"Drop preset '{preset_name}' does not exist")

    if preset.tcp_pose is not None:
        logger.info("Drop pose taken from the preset TCP pose")
        return require_six_finite(preset.tcp_pose, f"Preset '{preset_name}' TCP pose")

    forward_kinematics = getattr(robot.rtde_control, "getForwardKinematics", None)
    get_tcp_offset = getattr(robot.rtde_control, "getTCPOffset", None)
    if not callable(forward_kinematics) or not callable(get_tcp_offset):
        raise TestAbort(
            f"Preset '{preset_name}' has no TCP pose; resolving it requires "
            "getForwardKinematics() and getTCPOffset(). Re-save it with a TCP pose."
        )

    try:
        joints = require_six_finite(preset.joints, f"Preset '{preset_name}' joints")
        tcp_offset = require_six_finite(get_tcp_offset(), "Active TCP offset")
        logger.info("Active TCP offset: %s", [round(v, 6) for v in tcp_offset])

        # ur_rtde 1.6.5 uses a six-register recipe when the TCP argument is
        # omitted OR all zero, leaving the script's TCP registers stale.
        # A nonzero explicit offset selects the full twelve-register recipe.
        # For a flange TCP, query a virtual point 1 mm along flange Z, then
        # remove that translation in the returned frame. No TCP setting changes.
        flange_tcp = not any(tcp_offset)
        query_offset = [0.0, 0.0, 0.001, 0.0, 0.0, 0.0] if flange_tcp else tcp_offset
        pose = require_six_finite(
            forward_kinematics(joints, query_offset), "Forward kinematics pose"
        )
        if flange_tcp:
            rotation = pose_to_matrix(pose)[:3, :3]
            for axis in range(3):
                pose[axis] -= float(rotation[axis, 2]) * 0.001
    except TestAbort:
        raise
    except Exception as exc:
        raise TestAbort(f"Forward kinematics failed for '{preset_name}': {exc}") from exc

    logger.info("Drop pose computed from preset joints with an explicit TCP offset")
    return pose


def check_home_preset(robot, preset_name: str) -> None:
    if robot.preset_manager.get_preset(preset_name) is not None:
        return
    if Config.get_preset_position(preset_name) is not None:
        return
    raise TestAbort(f"Home preset '{preset_name}' does not exist")


def validate_plan(drop_pose, approach_pose) -> None:
    """Check both Cartesian targets before confirmation or any home move."""
    for name, pose in (("Drop pose", drop_pose), ("Approach pose", approach_pose)):
        pose = require_six_finite(pose, name)
        for axis, value in zip("xyz", pose[:3]):
            low = Config.WORKSPACE_LIMITS[f"{axis}_min"]
            high = Config.WORKSPACE_LIMITS[f"{axis}_max"]
            if not low <= value <= high:
                raise TestAbort(
                    f"{name} {axis.upper()}={value:.4f} m exceeds workspace "
                    f"[{low:.4f}, {high:.4f}] m; no motion commanded. "
                    "Check the TCP configuration and drop preset."
                )


def plan_descent(args, drop_pose):
    """Split approach and force search while preserving the absolute lower Z."""
    drop_pose = require_six_finite(drop_pose, "Drop pose")
    approach = list(drop_pose)
    approach[2] += args.approach_height_mm / 1000.0
    height = args.force_start_height_mm
    if height is None:
        height = args.approach_height_mm
    if not math.isfinite(height) or not 0 <= height <= args.approach_height_mm:
        raise TestAbort("Force-start height must lie between drop and initial approach")
    force_start = list(drop_pose)
    force_start[2] += height / 1000.0
    fast_mm = args.approach_height_mm - height
    force_args = copy.copy(args)
    force_args.max_descent_mm = args.max_descent_mm - fast_mm
    if force_args.max_descent_mm <= 0:
        raise TestAbort("Fast descent uses the entire descent budget; no motion commanded")
    validate_plan(drop_pose, approach)
    validate_plan(drop_pose, force_start)
    timeout = min(force_args.max_descent_mm / args.descent_speed_mm_s + 10.0,
                  ForceConfig.MAX_TIMEOUT)
    return dict(approach=approach, force_start=force_start,
                fast_mm=fast_mm, force_args=force_args, timeout=timeout)


def print_plan(args, home_name: str, drop_pose, approach_pose, timeout: float,
               descent_plan=None) -> None:
    print()
    print("=" * 64)
    print("Drop contact test")
    print("=" * 64)
    print(f"  Home preset        : {home_name}")
    print(f"  Drop preset        : {args.drop_preset}")
    print(f"  Drop pose (base)   : {[round(v, 4) for v in drop_pose]}")
    print(f"  Approach pose      : {[round(v, 4) for v in approach_pose]}")
    print(f"  Approach height    : {args.approach_height_mm:.1f} mm")
    if descent_plan is not None:
        print(f"  Force starts at    : {[round(v, 4) for v in descent_plan['force_start']]}")
        print(f"  Fast descent       : {descent_plan['fast_mm']:.1f} mm at {args.approach_speed_mm_s:.1f} mm/s")
        print(f"  Force search limit : {descent_plan['force_args'].max_descent_mm:.1f} mm")
    print(f"  Contact threshold  : {args.contact_force:.1f} N measured")
    print(f"  Commanded force    : {args.command_force:.1f} N")
    print(f"  Descent speed      : {args.descent_speed_mm_s:.1f} mm/s")
    print(f"  Max descent        : {args.max_descent_mm:.1f} mm")
    print(f"  Force mode timeout : {timeout:.0f} s")
    if getattr(args, 'gripper_description', None):
        print(f"  Gripper            : {args.gripper_description}")
    elif args.manual_gripper:
        print("  Gripper            : manual release at contact")
    elif args.gripper_pin is not None:
        print(
            f"  Gripper            : DO{args.gripper_pin} -> "
            f"{args.gripper_release_level.upper()} releases"
        )
    else:
        print("  Gripper            : none (contact and retract only)")


def collect_force_baseline(robot, app, samples: int = 15, period: float = 0.1):
    """Zero the sensor and average the no-load force before force mode starts."""
    if not robot.zero_force_sensor():
        raise TestAbort("Could not zero the TCP force estimate")
    wait(app, 1.0)

    readings = []
    for _ in range(samples):
        force, _ = read_force_and_pose(robot)
        if force and len(force) >= 6:
            readings.append([float(v) for v in force])
        wait(app, period)

    if not readings:
        raise TestAbort("No force data received from the robot")

    baseline = [
        sum(reading[axis] for reading in readings) / len(readings)
        for axis in range(6)
    ]
    z_values = [reading[2] for reading in readings]
    spread = max(z_values) - min(z_values)
    logger.info(
        "Force baseline: Fx=%.2f Fy=%.2f Fz=%.2f N (Fz spread %.2f N over %d samples)",
        baseline[0], baseline[1], baseline[2], spread, len(readings),
    )
    return baseline


def start_force_descent(robot, args, timeout: float) -> bool:
    lateral = args.lateral_tolerance_mm / 1000.0
    rotation = math.radians(args.rotation_tolerance_deg)
    speed = args.descent_speed_mm_s / 1000.0
    limits = [lateral, lateral, speed, rotation, rotation, rotation]

    started = robot.start_force_mode(
        target_force=args.command_force,
        selection_vector=COMPLIANT_AXES,
        force_type=2,
        speed_limits=limits,
        task_frame=BASE_FRAME,
        timeout=timeout,
    )
    if started:
        logger.info(
            "Force mode started: %.1f N down, %.1f mm/s, %.1f mm X/Y deviation",
            args.command_force, args.descent_speed_mm_s, args.lateral_tolerance_mm,
        )
    return started


def descend_until_contact(robot, app, args, baseline, approach_z: float, timeout: float,
                          *, stop_at_z=None):
    """Stop on contact, or at an optional taught pick height without contact.

    The optional height is a software-monitored endpoint, not a safety-rated
    travel limit. Placement omits it and still requires measured force contact.
    """
    max_descent = args.max_descent_mm / 1000.0
    start = time.monotonic()
    last_log = start
    peak_delta = 0.0
    contact_guard = getattr(args, 'contact_guard', None)
    next_guard_check = start

    while True:
        app.processEvents()
        now = time.monotonic()
        if contact_guard is not None and now >= next_guard_check:
            contact_guard()
            next_guard_check = now + 0.1

        if now - start > 0.5 and not robot.force_controller.is_active:
            raise TestAbort("Force mode stopped unexpectedly before contact")

        force, pose = read_force_and_pose(robot)
        if stop_at_z is not None:
            # Picking cannot safely decide whether to descend or grip with
            # missing pose/force feedback.
            pose = require_six_finite(pose, "Pick search TCP pose")
            force = require_six_finite(force, "Pick search TCP force")

        delta = 0.0
        if force and len(force) >= 6:
            delta = float(force[2]) - baseline[2]
            peak_delta = max(peak_delta, abs(delta))

        # Reaching the taught pick pose is a successful position stop, even if
        # force rises in the same sample. Never add the contact backoff here.
        if stop_at_z is not None and pose[2] <= stop_at_z:
            if not robot.stop_force_mode():
                raise TestAbort("Pick position reached but force mode could not be stopped")
            logger.info("Reached taught pick Z=%.4f m without earlier accepted contact; stopping search",
                        stop_at_z)
            return {
                "reason": "position", "force": force, "delta": delta,
                "descent": approach_z - pose[2], "z": pose[2],
                "pose": pose, "elapsed": now - start,
            }

        if now - start >= getattr(args, 'contact_min_time_s', 0.5) and abs(delta) >= args.contact_force:
            if not robot.stop_force_mode():
                raise TestAbort("Contact detected but force mode could not be stopped")
            contact_pose = require_six_finite(pose, "Measured contact TCP pose")
            z = contact_pose[2]
            descent = approach_z - z
            logger.info(
                "Contact after %.1f s: Fz delta %.2f N, descended %.1f mm",
                now - start, delta, descent * 1000.0,
            )
            return {
                "reason": "contact",
                "force": force,
                "delta": delta,
                "descent": descent,
                "z": z,
                "pose": contact_pose,
                "elapsed": now - start,
            }

        if pose and approach_z - pose[2] >= max_descent:
            if not robot.stop_force_mode():
                raise TestAbort("No contact and force mode could not be stopped")
            raise NoContact(
                f"No contact after {args.max_descent_mm:.1f} mm of descent "
                f"(peak Fz delta {peak_delta:.2f} N)"
            )

        if now - start >= timeout:
            if not robot.stop_force_mode():
                raise TestAbort("No contact and force mode could not be stopped")
            raise NoContact(
                f"No contact within {timeout:.0f} s "
                f"(peak Fz delta {peak_delta:.2f} N)"
            )

        if now - last_log >= 0.5:
            z = pose[2] if pose else float("nan")
            logger.info(
                "descending: z=%.4f m, down=%.1f mm, Fz delta=%+.2f N, peak=%.2f N",
                z, (approach_z - z) * 1000.0, delta, peak_delta,
            )
            last_log = now

        time.sleep(0.004)


def release_gripper(robot, args) -> bool:
    if args.manual_gripper:
        input("Release the gripper, then press Enter to retract: ")
        logger.info("Manual gripper release acknowledged")
        return True

    open_gripper = getattr(robot, "open_gripper", None)
    if callable(open_gripper):
        try:
            released = bool(open_gripper())
        except Exception as exc:
            logger.error("open_gripper() failed: %s", exc)
            return False
        logger.info("open_gripper() returned %s", released)
        return released

    if args.gripper_pin is not None:
        level = args.gripper_release_level == "high"
        released = bool(robot.set_digital_out(args.gripper_pin, level))
        logger.info(
            "Digital output %d set %s: %s",
            args.gripper_pin, args.gripper_release_level.upper(), released,
        )
        return released

    logger.info("No gripper configured; skipping release")
    return True


def run_test(app, robot, args, *, move_home=True, resolved_drop_pose=None) -> int:
    check_home_preset(robot, args.home_preset)
    drop_pose = (resolve_drop_pose(robot, args.drop_preset)
                 if resolved_drop_pose is None else list(resolved_drop_pose))

    descent_plan = plan_descent(args, drop_pose)
    approach_pose = descent_plan['approach']
    force_start = descent_plan['force_start']
    force_args = descent_plan['force_args']
    timeout = descent_plan['timeout']
    print_plan(args, args.home_preset, drop_pose, approach_pose, timeout, descent_plan)

    if args.dry_run:
        logger.info("Dry run: poses resolved, no motion commanded")
        return 0

    if not args.yes:
        answer = input("\nType YES to move the robot: ").strip()
        if answer != "YES":
            logger.info("Aborted by operator")
            return 1

    if move_home:
        logger.info("Moving to home preset '%s'", args.home_preset)
        if not robot.move_to_preset_position(args.home_preset):
            raise TestAbort("Move to home preset failed")
        wait(app, args.settle_s)

    logger.info("Moving to approach pose (%.1f mm above drop)", args.approach_height_mm)
    moved = robot.move_tcp(
        *approach_pose,
        speed=args.approach_speed_mm_s / 1000.0,
        accel=Config.DEFAULT_TCP_ACCEL,
        relative=False,
    )
    if not moved:
        raise TestAbort("Move to approach pose failed")
    wait(app, args.settle_s)

    if descent_plan['fast_mm'] > 0:
        logger.info("Position-mode descent to force-start pose: %.1f mm at %.1f mm/s",
                    descent_plan['fast_mm'], args.approach_speed_mm_s)
        if not robot.move_tcp(*force_start, speed=args.approach_speed_mm_s / 1000.0,
                              accel=Config.DEFAULT_TCP_ACCEL, relative=False):
            raise TestAbort("Move to force-start pose failed")
        wait(app, args.settle_s)

    current = robot.get_tcp_pose()
    if current is None:
        raise TestAbort("Cannot read the TCP pose at the approach position")
    position_error = max(abs(current[i] - force_start[i]) for i in range(3))
    if position_error > 0.01:
        logger.warning(
            "TCP is %.1f mm from the force-start pose", position_error * 1000.0
        )

    baseline = collect_force_baseline(robot, app)

    if not start_force_descent(robot, force_args, timeout):
        raise TestAbort("Force mode could not be started")

    try:
        contact = descend_until_contact(
            robot, app, force_args, baseline, force_start[2], timeout
        )
    except NoContact as exc:
        current = robot.get_tcp_pose()
        lift = approach_pose[2] - current[2] if current else 0.0
        if lift > 0:
            logger.warning("%s; retracting %.1f mm to the approach pose", exc, lift * 1000.0)
            robot.move_tcp(
                z=lift,
                speed=args.approach_speed_mm_s / 1000.0,
                accel=Config.DEFAULT_TCP_ACCEL,
                relative=True,
            )
        raise

    logger.info(
        "Accepting measured placement Z=%.4f m (taught drop Z=%.4f m, difference=%+.1f mm); "
        "releasing at the current contact position",
        contact['z'], drop_pose[2], (contact['z'] - drop_pose[2]) * 1000.0,
    )
    if not release_gripper(robot, args):
        raise TestAbort(
            "Gripper release failed; robot left at the contact point"
        )
    wait(app, args.release_wait_s)

    if args.retract_mm > 0:
        logger.info("Retracting %.1f mm", args.retract_mm)
        retracted = robot.move_tcp(
            z=args.retract_mm / 1000.0,
            speed=args.approach_speed_mm_s / 1000.0,
            accel=Config.DEFAULT_TCP_ACCEL,
            relative=True,
        )
        if not retracted:
            raise TestAbort("Retract move failed")
        wait(app, args.settle_s)

    if args.return_home:
        logger.info("Returning to home preset '%s'", args.home_preset)
        if not robot.move_to_preset_position(args.home_preset):
            raise TestAbort("Return to home failed")

    print()
    print("=" * 64)
    print("RESULT: contact found and part released")
    print(f"  Contact force delta : {contact['delta']:+.2f} N")
    print(f"  Descent             : {contact['descent'] * 1000.0:.1f} mm")
    print(f"  Time to contact     : {contact['elapsed']:.1f} s")
    print(f"  Contact TCP z       : {contact['z']:.4f} m")
    print("=" * 64)
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    from PyQt5.QtWidgets import QApplication

    from robot_controller import RobotController

    app = QApplication.instance() or QApplication(sys.argv[:1])
    robot = RobotController(enable_auto_reconnect=False)
    robot.error_occurred.connect(lambda message: logger.error("robot: %s", message))

    exit_code = 1
    try:
        if not robot.connect(args.ip, Config.DEFAULT_PORT):
            logger.error("Connection to %s failed", args.ip)
            return 2

        exit_code = run_test(app, robot, args)
    except TestAbort as exc:
        logger.error("%s", exc)
    except KeyboardInterrupt:
        logger.warning("Interrupted by operator")
        exit_code = 130
    except Exception:
        logger.exception("Unexpected failure")
    finally:
        try:
            if robot.force_controller.is_active:
                logger.warning("Leaving force mode during cleanup")
                robot.stop_force_mode()
        except Exception:
            logger.exception("Failed to stop force mode during cleanup")
        if robot.is_connected:
            robot.disconnect()
        app.processEvents()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
