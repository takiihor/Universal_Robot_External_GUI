#!/usr/bin/env python3
"""Configurable RG2 pick at positionA, followed by the existing force drop test.

No second robot process is started: picking and placement share one RTDE
connection, and OnRobot jaw commands use its separate XML-RPC service.
"""

import argparse
import copy
import json
import logging
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config
from preset_manager import PresetManager
from rg2_gripper import GripperError, RG2Gripper
from test_scripts import test_home_to_drop_force_contact as drop
from utils import check_joint_limits

logger = logging.getLogger('rg2_pick_place')


def parse_args(argv=None):
    parser = drop.build_parser()
    parser.description = 'Force-search down to the taught pick pose, adapt to earlier contact, return home, and force-place.'
    parser.set_defaults(home_preset='home_a', approach_speed_mm_s=20.0,
                        descent_speed_mm_s=5.0)
    parser.add_argument('--config', type=Path, help='JSON recipe; CLI values override it')
    parser.add_argument('--pick-preset', default='positionA', help='Taught grasp pose and lower endpoint of the pick search')
    parser.add_argument('--pick-height-mm', type=float, default=100.0,
                        help='Vertical approach/lift above the pick pose')
    parser.add_argument('--pick-speed-mm-s', type=float, default=10.0,
                        help='Position-mode speed for final pick positioning, contact backoff, and loaded lift')
    parser.add_argument('--pick-contact-force-n', type=float, default=10.0,
                        help='Vertical force change that stops the pick search')
    parser.add_argument('--pick-command-force-n', type=float, default=None,
                        help='Pick-search commanded force; defaults to 1.2 times contact threshold')
    parser.add_argument('--pick-descent-speed-mm-s', type=float, default=5.0,
                        help='Maximum force-mode speed while searching for pick contact')
    parser.add_argument('--pick-max-descent-mm', type=float, default=150.0,
                        help='Maximum pick search travel from its approach; always capped at the taught pick Z')
    parser.add_argument('--pick-backoff-mm', type=float, default=50.0,
                        help='Rise above contact higher than the taught pick pose; no rise when picking at the taught pose')
    parser.add_argument('--joint-speed-rad-s', type=float, default=0.1,
                        help='Speed for home joint moves, including optional final return')
    parser.add_argument('--open-width-mm', type=float,
                        help='Jaw width for opening before pick and releasing on the table')
    parser.add_argument('--grip-width-mm', type=float,
                        help='Closing target narrower than the block; grip detection is required')
    parser.add_argument('--grip-force-n', type=float, help='RG2 gripping force, 3-40 N')
    parser.add_argument('--release-force-n', type=float, default=10.0,
                        help='RG2 force for opening/release commands; distinct from contact force')
    parser.add_argument('--rg2-port', type=int, default=41414)
    parser.add_argument('--rg2-tool-index', type=int, choices=(0, 1, 2), default=0)
    parser.add_argument('--rg2-timeout-s', type=float, default=8.0)
    parser.add_argument('--cycles', type=int, default=1,
                        help='Number of pick/place cycles; 0 repeats until interrupted')
    parser.add_argument('--cycle-wait-s', type=float, default=2.0,
                        help='Pause between successful cycles')

    preliminary = argparse.ArgumentParser(add_help=False)
    preliminary.add_argument('--config', type=Path)
    config_arg, _ = preliminary.parse_known_args(argv)
    if config_arg.config:
        try:
            recipe = json.loads(config_arg.config.read_text())
            allowed = {action.dest for action in parser._actions} - {
                'help', 'config', 'yes', 'dry_run', 'manual_gripper',
                'gripper_pin', 'gripper_release_level',
            }
            if not isinstance(recipe, dict) or set(recipe) - allowed:
                raise ValueError('Recipe must be an object containing supported option names')
            parser.set_defaults(**recipe)
        except (OSError, ValueError) as exc:
            parser.error(f'Cannot load recipe: {exc}')
    args = parser.parse_args(argv)
    if args.manual_gripper or args.gripper_pin is not None:
        parser.error('This sequence uses RG2 XML-RPC, not manual or digital-output release')
    # JSON defaults also need validation; argparse does not coerce numeric JSON.
    for key, value in vars(args).items():
        if key in ('home_preset', 'pick_preset', 'drop_preset', 'ip'):
            if not isinstance(value, str) or not value.strip():
                parser.error(f'{key} must be a nonempty string')
        if key == 'return_home' and type(value) is not bool:
            parser.error('return_home must be a JSON boolean')
    numeric = (
        'approach_height_mm', 'contact_force', 'command_force',
        'descent_speed_mm_s', 'max_descent_mm', 'approach_speed_mm_s',
        'lateral_tolerance_mm', 'rotation_tolerance_deg', 'settle_s',
        'release_wait_s', 'retract_mm', 'pick_height_mm', 'pick_speed_mm_s',
        'joint_speed_rad_s', 'open_width_mm', 'grip_width_mm', 'grip_force_n',
        'release_force_n', 'rg2_timeout_s', 'cycle_wait_s', 'force_start_height_mm',
        'pick_contact_force_n', 'pick_command_force_n', 'pick_descent_speed_mm_s',
        'pick_max_descent_mm', 'pick_backoff_mm',
    )
    for key in numeric:
        value = getattr(args, key)
        if value is None and key not in ('command_force', 'open_width_mm', 'grip_width_mm', 'grip_force_n', 'force_start_height_mm', 'pick_command_force_n'):
            parser.error(f'{key} cannot be null')
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
            parser.error(f'{key} must be a finite number')
    drop.validate_args(parser, args)
    if not drop.ForceConfig.MIN_TARGET_FORCE <= args.pick_contact_force_n < drop.ForceConfig.MAX_TARGET_FORCE:
        parser.error('Pick contact force is outside the supported force range')
    if args.pick_command_force_n is None:
        args.pick_command_force_n = min(args.pick_contact_force_n * 1.2,
                                       drop.ForceConfig.MAX_TARGET_FORCE)
    if not args.pick_contact_force_n <= args.pick_command_force_n <= drop.ForceConfig.MAX_TARGET_FORCE:
        parser.error('Pick command force must be at least its contact threshold and at most the force limit')
    if not 0 < args.pick_descent_speed_mm_s <= drop.ForceConfig.MAX_LINEAR_SPEED * 1000:
        parser.error('Pick force-descent speed is outside the supported range')
    if args.pick_max_descent_mm <= 0 or args.pick_backoff_mm <= 0:
        parser.error('Pick maximum descent and rise-before-grip must be positive')
    if args.pick_height_mm <= 0 or not 0 < args.pick_speed_mm_s <= 500:
        parser.error('Pick height must be positive; pick speed must be in (0, 500] mm/s')
    if not 0 < args.joint_speed_rad_s <= Config.MAX_JOINT_SPEED:
        parser.error(f'Joint speed must be in (0, {Config.MAX_JOINT_SPEED}] rad/s')
    if min(args.settle_s, args.release_wait_s) < 0 or args.rg2_timeout_s <= 0:
        parser.error('Waits must be nonnegative and RG2 timeout must be positive')
    if type(args.cycles) is not int or args.cycles < 0:
        parser.error('cycles must be a nonnegative integer (0 means continuous)')
    if args.cycle_wait_s < 0:
        parser.error('cycle_wait_s must be nonnegative')
    if type(args.rg2_port) is not int or not 1 <= args.rg2_port <= 65535:
        parser.error('RG2 port must be an integer in [1, 65535]')
    if type(args.rg2_tool_index) is not int or args.rg2_tool_index not in (0, 1, 2):
        parser.error('RG2 tool index must be 0, 1, or 2')
    required = ('open_width_mm', 'grip_width_mm', 'grip_force_n')
    if not args.dry_run and any(getattr(args, key) is None for key in required):
        parser.error('Live runs require --open-width-mm, --grip-width-mm, and --grip-force-n (or recipe values)')
    try:
        for key in ('open_width_mm', 'grip_width_mm'):
            width = getattr(args, key)
            if width is not None and not 0 <= width <= 110:
                raise ValueError(f'{key} must be in [0, 110] mm')
        for key in ('grip_force_n', 'release_force_n'):
            force = getattr(args, key)
            if force is not None and not 3 <= force <= 40:
                raise ValueError(f'{key} must be in [3, 40] N')
        if args.open_width_mm is not None:
            RG2Gripper.validate_target(args.open_width_mm, args.release_force_n)
        if args.grip_width_mm is not None and args.grip_force_n is not None:
            RG2Gripper.validate_target(args.grip_width_mm, args.grip_force_n)
        if (args.open_width_mm is not None and args.grip_width_mm is not None
                and args.open_width_mm <= args.grip_width_mm):
            raise ValueError('Opening width must be greater than closing target width')
    except ValueError as exc:
        parser.error(str(exc))
    return args


def require_presets(manager, args):
    missing = [name for name in (args.home_preset, args.pick_preset, args.drop_preset)
               if manager.get_preset(name) is None]
    if missing:
        raise drop.TestAbort('Missing saved preset(s): ' + ', '.join(dict.fromkeys(missing)))


def plan_sequence(robot, args):
    require_presets(robot.preset_manager, args)
    poses = {}
    for name in (args.home_preset, args.pick_preset, args.drop_preset):
        preset = robot.preset_manager.get_preset(name)
        joints = drop.require_six_finite(preset.joints, f'{name} joints')
        if not check_joint_limits(joints):
            raise drop.TestAbort(f'{name} joints exceed configured limits')
        poses[name] = drop.resolve_drop_pose(robot, name)
        drop.validate_plan(poses[name], poses[name])
    pick = poses[args.pick_preset]
    pick_approach = list(pick)
    pick_approach[2] += args.pick_height_mm / 1000.0
    drop.validate_plan(pick, pick_approach)
    # Bound all possible contact-dependent rise/lift heights before any motion.
    pick_lowest = list(pick_approach)
    pick_lowest[2] = max(pick[2], pick_approach[2] - args.pick_max_descent_mm / 1000.0)
    pick_highest = list(pick_approach)
    pick_highest[2] += (args.pick_backoff_mm + args.pick_height_mm) / 1000.0
    drop.validate_plan(pick_lowest, pick_highest)
    place = poses[args.drop_preset]
    descent_plan = drop.plan_descent(args, place)
    place_approach = descent_plan['approach']
    # Bound the entire fast-plus-force descent against the same absolute lower Z.
    lowest = list(place_approach)
    lowest[2] -= args.max_descent_mm / 1000.0
    highest = list(place_approach)
    highest[2] += args.retract_mm / 1000.0
    drop.validate_plan(lowest, highest)
    return dict(pick=pick, pick_approach=pick_approach, drop=place,
                drop_approach=place_approach, force_start=descent_plan['force_start'],
                pick_search_lowest=pick_lowest, pick_lift_upper_bound=pick_highest)


class PlacementRobot:
    """Inject the RG2 release callback into the existing drop test."""
    def __init__(self, robot, gripper, args, app):
        self.robot, self.gripper, self.args, self.app = robot, gripper, args, app

    def __getattr__(self, name):
        return getattr(self.robot, name)

    def move_to_preset_position(self, name):
        return self.robot.move_to_preset_position(name, speed=self.args.joint_speed_rad_s)

    def open_gripper(self):
        self.gripper.move(self.args.open_width_mm, self.args.release_force_n,
                          require_release=True, process_events=self.app.processEvents)
        return True


def require_holding(gripper):
    state = gripper.status()
    if state['busy'] or state['safety_failed'] or not state['grip_detected']:
        raise GripperError('RG2 does not confirm a held block; sequence stopped')


def force_pick_contact(app, robot, gripper, args, approach_pose, pick_pose):
    """Search with open fingers, accepting earlier contact or the taught pose."""
    search = copy.copy(args)
    search.contact_force = args.pick_contact_force_n
    search.command_force = args.pick_command_force_n
    search.descent_speed_mm_s = args.pick_descent_speed_mm_s
    search.max_descent_mm = min(args.pick_max_descent_mm,
                                (approach_pose[2] - pick_pose[2]) * 1000.0)
    # Already settled/tared: do not ignore a real contact during the first 0.5 s.
    search.contact_min_time_s = 0.0
    search.contact_guard = gripper.check_safety
    timeout = min(search.max_descent_mm / search.descent_speed_mm_s + 10.0,
                  drop.ForceConfig.MAX_TIMEOUT)
    logger.info('Pick force search: contact=%.1f N, command=%.1f N, speed limit=%.1f mm/s, max descent=%.1f mm',
                search.contact_force, search.command_force,
                search.descent_speed_mm_s, search.max_descent_mm)
    logger.info('Pick lower endpoint: taught Z=%.4f m; grip there if no earlier contact',
                pick_pose[2])
    gripper.check_safety()
    baseline = drop.collect_force_baseline(robot, app)
    gripper.check_safety()
    if not drop.start_force_descent(robot, search, timeout):
        raise drop.TestAbort('Pick force mode could not be started')
    try:
        contact = drop.descend_until_contact(robot, app, search, baseline,
                                             approach_pose[2], timeout,
                                             stop_at_z=pick_pose[2])
        # Do not turn a safety-switch collision between polls into a grasp.
        gripper.check_safety()
        return contact
    finally:
        if robot.force_controller.is_active and not robot.stop_force_mode():
            raise drop.TestAbort('Cannot stop pick force mode; grip and lift are blocked')


def pick_contact_poses(contact, args, pick_pose):
    """Grip at the taught pose, or rise from a higher measured contact."""
    pose = drop.require_six_finite(contact['pose'], 'Pick contact pose')
    if contact['reason'] == 'position' and pose[2] <= pick_pose[2]:
        grasp = list(pick_pose)
    elif contact['reason'] == 'contact' and pose[2] > pick_pose[2]:
        grasp = list(pose)
        grasp[2] += args.pick_backoff_mm / 1000.0
    else:
        raise drop.TestAbort('Pick search returned an invalid stop condition; grip blocked')
    lift = list(grasp)
    lift[2] += args.pick_height_mm / 1000.0
    drop.validate_plan(pose, grasp)
    drop.validate_plan(grasp, lift)
    return grasp, lift


def run_sequence(app, robot, gripper, args):
    plan = plan_sequence(robot, args)
    state = gripper.status()
    print('\nRG2 pick and force-place sequence', flush=True)
    print(f'  Home: {args.home_preset}; taught pick: {args.pick_preset}; drop: {args.drop_preset}')
    for key, pose in plan.items():
        print(f'  {key}: {[round(v, 4) for v in pose]}')
    print(f'  Jaw targets: open/release={args.open_width_mm} mm; grip={args.grip_width_mm} mm')
    print(f'  Jaw force: grip={args.grip_force_n} N; opening={args.release_force_n} N')
    print(f'  Speeds: home={args.joint_speed_rad_s} rad/s; transit={args.approach_speed_mm_s} mm/s; pick={args.pick_speed_mm_s} mm/s; force descent limit={args.descent_speed_mm_s} mm/s')
    print(f'  Placement: contact={args.contact_force} N; command={args.command_force} N')
    print(f'  Force pick: contact={args.pick_contact_force_n} N; command={args.pick_command_force_n} N; descent limit={args.pick_descent_speed_mm_s} mm/s; rise after earlier contact only={args.pick_backoff_mm} mm')
    print(f"  Pick lower endpoint: taught Z={plan['pick'][2]:.4f} m; grip here if no earlier contact.")
    print('  Earlier contact above that endpoint: stop, rise before grip, then lift from the new grasp height.')
    descent_plan = drop.plan_descent(args, plan['drop'])
    print(f"  Placement descent: {descent_plan['fast_mm']:.1f} mm in position mode at {args.approach_speed_mm_s:.1f} mm/s; then up to {descent_plan['force_args'].max_descent_mm:.1f} mm in force mode")
    print(f'  RG2 status: {state}', flush=True)
    if args.dry_run:
        print('DRY RUN: no jaw, arm, taring, or force-mode commands sent.', flush=True)
        return 0
    if state['busy'] or state['safety_failed'] or state['grip_detected']:
        raise GripperError('Start with the RG2 idle, fault-free, and not already holding a block')
    count = f'{args.cycles} cycle(s)' if args.cycles else 'continuous cycles until interrupted'
    if not args.yes and input(f'\nType YES to start {count}: ').strip() != 'YES':
        logger.info('Aborted by operator')
        return 1

    wrapped = PlacementRobot(robot, gripper, args, app)

    def home():
        logger.info('Moving to home preset %s', args.home_preset)
        if not wrapped.move_to_preset_position(args.home_preset):
            raise drop.TestAbort('Home move failed')
        drop.wait(app, args.settle_s)

    def linear(pose, speed, label):
        logger.info('%s', label)
        if not robot.move_tcp(*pose, speed=speed / 1000.0,
                              accel=Config.DEFAULT_TCP_ACCEL, relative=False):
            raise drop.TestAbort(f'{label} failed')
        drop.wait(app, args.settle_s)

    home()
    wrapped.open_gripper()
    linear(plan['pick_approach'], args.approach_speed_mm_s, 'Approaching above pick')
    contact = force_pick_contact(app, robot, gripper, args, plan['pick_approach'], plan['pick'])
    grasp_pose, lift_pose = pick_contact_poses(contact, args, plan['pick'])
    if contact['reason'] == 'position':
        logger.info('Picking at taught pose Z=%.4f m; no contact backoff', grasp_pose[2])
        linear(grasp_pose, args.pick_speed_mm_s, 'Positioning at taught pick pose before gripping')
    else:
        logger.info('Higher pick contact Z=%.4f m; rising %.1f mm to grasp Z=%.4f m before closing',
                    contact['pose'][2], args.pick_backoff_mm, grasp_pose[2])
        linear(grasp_pose, args.pick_speed_mm_s, 'Rising above higher pick contact before gripping')
    logger.info('Closing RG2 and requiring grip detection')
    gripper.move(args.grip_width_mm, args.grip_force_n, require_grip=True,
                 process_events=app.processEvents)
    linear(lift_pose, args.pick_speed_mm_s, 'Lifting the block from the measured grasp height')
    require_holding(gripper)
    home()
    require_holding(gripper)
    # Reuse the preflighted Cartesian pose and current connection. The preceding
    # step has already returned home, and the operator confirmed the whole run.
    placement_args = copy.copy(args)
    placement_args.yes = True
    placement_args.gripper_description = 'RG2 XML-RPC, release feedback required'
    return drop.run_test(app, wrapped, placement_args, move_home=False,
                         resolved_drop_pose=plan['drop'])


def run_cycles(app, robot, gripper, args):
    """Repeat only successful complete cycles, confirming the whole job once."""
    label = str(args.cycles) if args.cycles else 'continuous'
    print(f'Configured cycles: {label}; pause between cycles: {args.cycle_wait_s:g} s',
          flush=True)
    if args.dry_run:
        # In particular, --cycles 0 --dry-run must never enter an endless loop.
        return run_sequence(app, robot, gripper, args)

    completed = 0
    while args.cycles == 0 or completed < args.cycles:
        logger.info('Starting cycle %d / %s', completed + 1, label)
        cycle_args = copy.copy(args)
        cycle_args.yes = args.yes or completed > 0
        try:
            result = run_sequence(app, robot, gripper, cycle_args)
        except (drop.TestAbort, GripperError, KeyboardInterrupt):
            logger.warning('Stopped during cycle %d; %d complete cycle(s)',
                           completed + 1, completed)
            raise
        if result != 0:
            logger.info('Cycle sequence ended; %d complete cycle(s)', completed)
            return result
        completed += 1
        logger.info('Completed cycle %d / %s', completed, label)
        if args.cycles == 0 or completed < args.cycles:
            drop.wait(app, args.cycle_wait_s)
    return 0


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-7s %(message)s',
                        datefmt='%H:%M:%S', force=True)
    try:
        # Report missing teachings before creating any robot control connection.
        require_presets(PresetManager(), args)
    except drop.TestAbort as exc:
        logger.error('%s', exc)
        return 2
    from PyQt5.QtWidgets import QApplication
    from robot_controller import RobotController
    app = QApplication.instance() or QApplication(sys.argv[:1])
    robot = RobotController(enable_auto_reconnect=False)
    robot.error_occurred.connect(lambda message: logger.error('robot: %s', message))
    gripper = RG2Gripper(args.ip, args.rg2_port, args.rg2_tool_index, args.rg2_timeout_s)
    try:
        if not robot.connect(args.ip, Config.DEFAULT_PORT):
            return 2
        return run_cycles(app, robot, gripper, args)
    except (drop.TestAbort, GripperError) as exc:
        logger.error('%s; no automatic gripper release or recovery move will follow', exc)
        return 1
    except KeyboardInterrupt:
        logger.warning('Interrupted by operator')
        return 130
    except Exception:
        logger.exception('Pick/place failed')
        return 1
    finally:
        try:
            if robot.force_controller.is_active:
                robot.stop_force_mode()
        finally:
            gripper.close()
            if robot.is_connected():
                robot.disconnect()
            app.processEvents()


if __name__ == '__main__':
    sys.exit(main())
