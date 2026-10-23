#!/usr/bin/env python3
"""
測試 force_control 套件（不需連線機器人）

使用假的 RTDE control interface 驗證 force mode 的參數組裝、停止、
目標力重設、逾時自動釋放與感測器歸零。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from force_control import (
    ForceConfig,
    ForceController,
    build_wrench,
    clamp_target_force,
    resolve_target_force,
)
from force_control.config import build_limits

class FakeControlInterface:
    """Records the RTDE calls the controller makes."""

    def __init__(self):
        self.force_mode_calls = []
        self.stop_count = 0
        self.zero_count = 0
        self.fail_next_force_mode = False

    def forceMode(self, task_frame, selection_vector, wrench, force_type, limits):
        if self.fail_next_force_mode:
            self.fail_next_force_mode = False
            raise RuntimeError("simulated forceMode failure")
        self.force_mode_calls.append(
            {
                "task_frame": list(task_frame),
                "selection_vector": list(selection_vector),
                "wrench": list(wrench),
                "force_type": force_type,
                "limits": list(limits),
            }
        )

    def forceModeStop(self):
        self.stop_count += 1

    def zeroFtSensor(self):
        self.zero_count += 1


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def test_start_defaults():
    fake = FakeControlInterface()
    controller = ForceController(fake)

    check(controller.start(), "start() should succeed")
    check(controller.is_active, "controller should be active")
    check(len(fake.force_mode_calls) == 1, "forceMode should be called once")

    call = fake.force_mode_calls[0]
    check(call["task_frame"] == [0.0] * 6, f"default frame should be the base frame: {call}")
    check(
        call["selection_vector"] == [0, 0, 1, 0, 0, 0],
        f"default selection mismatch: {call['selection_vector']}",
    )
    check(
        call["wrench"] == [0.0, 0.0, -2.0, 0.0, 0.0, 0.0],
        f"default wrench should push down with 2 N: {call['wrench']}",
    )
    check(call["force_type"] == 2, f"default force type should be 2: {call['force_type']}")
    expected_limits = [
        ForceConfig.DEFAULT_LINEAR_DEVIATION,
        ForceConfig.DEFAULT_LINEAR_DEVIATION,
        ForceConfig.DEFAULT_LINEAR_SPEED,
        ForceConfig.DEFAULT_ANGULAR_DEVIATION,
        ForceConfig.DEFAULT_ANGULAR_DEVIATION,
        ForceConfig.DEFAULT_ANGULAR_DEVIATION,
    ]
    check(call["limits"] == expected_limits, f"default limits mismatch: {call['limits']}")
    check(controller.target_force == 2.0, "target force should be stored")
    controller.detach()


def test_set_target_force_restarts():
    fake = FakeControlInterface()
    controller = ForceController(fake)
    controller.start(timeout=0)

    check(controller.set_target_force(8.0), "set_target_force should succeed")
    check(fake.stop_count == 1, "active force mode must be stopped before restart")
    check(len(fake.force_mode_calls) == 2, "forceMode should be re-issued")
    check(
        fake.force_mode_calls[1]["wrench"] == [0.0, 0.0, -8.0, 0.0, 0.0, 0.0],
        f"restarted wrench mismatch: {fake.force_mode_calls[1]['wrench']}",
    )
    check(
        fake.force_mode_calls[1]["selection_vector"] == [0, 0, 1, 0, 0, 0],
        "restart should keep the original selection",
    )
    check(
        fake.force_mode_calls[1]["task_frame"] == [0.0] * 6,
        "restart should keep the original task frame",
    )
    controller.stop()


def test_set_target_force_while_inactive():
    fake = FakeControlInterface()
    controller = ForceController(fake)

    check(controller.set_target_force(6.0), "storing a target while inactive should succeed")
    check(controller.target_force == 6.0, "target force should be stored")
    check(not fake.force_mode_calls, "forceMode must not run while inactive")


def test_stop():
    fake = FakeControlInterface()
    controller = ForceController(fake)
    controller.start(timeout=0)

    check(controller.stop(), "stop() should succeed")
    check(not controller.is_active, "controller should be inactive after stop")
    check(fake.stop_count == 1, "forceModeStop should be called once")


def test_invalid_inputs_rejected():
    fake = FakeControlInterface()
    controller = ForceController(fake)

    check(
        not controller.start(selection_vector=[1, 0, 0, 0, 0]),
        "short selection vector must be rejected",
    )
    check(
        not controller.start(selection_vector=[0, 0, 0, 0, 0, 0]),
        "empty selection must be rejected",
    )
    check(
        not controller.start(selection_vector=[0, 0, 2, 0, 0, 0]),
        "non-binary selection must be rejected",
    )
    check(not controller.start(force_type=4), "unknown force type must be rejected")
    check(not controller.start(speed_limits=[0.1, 0.1, 0.1, 0.1, 0.1, 0.0]), "zero limit must be rejected")
    check(not controller.start(timeout=-1), "negative timeout must be rejected")
    check(not fake.force_mode_calls, "invalid requests must not reach the robot")
    check(controller.last_error, "last_error should describe the rejection")


def test_force_mode_failure_reported():
    fake = FakeControlInterface()
    errors = []
    controller = ForceController(fake, on_error=errors.append)
    fake.fail_next_force_mode = True

    check(not controller.start(), "simulated forceMode failure should fail start()")
    check(not controller.is_active, "controller must stay inactive after failure")
    check(len(errors) == 1 and "forceMode failed" in errors[0], f"error callback mismatch: {errors}")


def test_zero_sensor():
    fake = FakeControlInterface()
    controller = ForceController(fake)

    check(controller.zero_sensor(), "zero_sensor should succeed")
    check(fake.zero_count == 1, "zeroFtSensor should be called once")


def test_unavailable_controller():
    controller = ForceController()
    check(not controller.is_available, "controller without interface should be unavailable")
    check(not controller.start(), "start without interface should fail")
    check(not controller.zero_sensor(), "zero_sensor without interface should fail")
    check(not controller.stop(), "stop without interface should return False")


def test_watchdog_auto_release():
    fake = FakeControlInterface()
    timeouts = []
    states = []
    controller = ForceController(
        fake,
        on_state_changed=lambda active, target: states.append((active, target)),
        on_timeout=lambda target, timeout: timeouts.append((target, timeout)),
    )
    controller.start(target_force=3.0, timeout=0.15)

    deadline = time.monotonic() + 2.0
    while controller.is_active and time.monotonic() < deadline:
        time.sleep(0.02)

    check(not controller.is_active, "watchdog should auto-release force mode")
    check(fake.stop_count == 1, "watchdog should call forceModeStop")
    check(timeouts == [(3.0, 0.15)], f"timeout callback mismatch: {timeouts}")
    check(states[-1] == (False, 3.0), f"inactive state should be emitted: {states}")


def test_zero_timeout_disables_watchdog():
    fake = FakeControlInterface()
    controller = ForceController(fake)
    controller.start(timeout=0)

    time.sleep(0.1)
    check(controller.is_active, "timeout=0 should keep force mode active")
    check(fake.stop_count == 0, "timeout=0 should not stop force mode")
    controller.stop()


def test_attach_detach():
    fake = FakeControlInterface()
    controller = ForceController()
    controller.attach(fake)
    check(controller.is_available, "attach should make the controller available")
    check(controller.start(timeout=0), "start should work after attach")

    controller.detach()
    check(not controller.is_available, "detach should release the interface")
    check(not controller.is_active, "detach should stop force mode")
    check(fake.stop_count == 1, "detach should call forceModeStop")


def test_limit_builder():
    limits = build_limits([1, 0, 1, 0, 0, 0], 0.1, 1.0, 0.003, 0.05)
    check(
        limits == [0.1, 0.003, 0.1, 0.05, 0.05, 0.05],
        f"compliant axes need speed and non-compliant axes deviation: {limits}",
    )

    fake = FakeControlInterface()
    controller = ForceController(fake)
    check(
        controller.start(selection_vector=[1, 1, 0, 0, 0, 0], timeout=0),
        "start with a mixed selection should succeed",
    )
    call = fake.force_mode_calls[0]
    check(
        call["limits"] == [
            ForceConfig.DEFAULT_LINEAR_SPEED,
            ForceConfig.DEFAULT_LINEAR_SPEED,
            ForceConfig.DEFAULT_LINEAR_DEVIATION,
            ForceConfig.DEFAULT_ANGULAR_DEVIATION,
            ForceConfig.DEFAULT_ANGULAR_DEVIATION,
            ForceConfig.DEFAULT_ANGULAR_DEVIATION,
        ],
        f"defaults must follow the selection: {call['limits']}",
    )
    controller.stop()


def test_wrench_builder():
    check(build_wrench(5.0, [0, 0, 1, 0, 0, 0]) == [0.0, 0.0, -5.0, 0.0, 0.0, 0.0], "Fz wrench mismatch")
    check(build_wrench(5.0, [1, 1, 0, 0, 0, 0]) == [5.0, 5.0, 0.0, 0.0, 0.0, 0.0], "Fx/Fy wrench mismatch")
    check(build_wrench(5.0, [0, 0, 0, 1, 0, 0]) == [0.0, 0.0, 0.0, 1.5, 0.0, 0.0], "torque should be scaled")
    check(build_wrench(50.0, [0, 0, 0, 1, 0, 0])[3] == ForceConfig.MAX_TORQUE, "torque should be capped")


def test_resolve_target_force():
    check(resolve_target_force(None) == 10.0, "default should resolve to medium")
    check(resolve_target_force({"force_level": 5}) == 5.0, "numeric force_level should pass through")
    check(resolve_target_force({"force_level": "5.5"}) == 5.5, "numeric string should parse")
    check(resolve_target_force({"force_level": "gentle"}) == 5.0, "named level should resolve")
    check(resolve_target_force({"force_newtons": 7.5}) == 7.5, "force_newtons should win")
    check(resolve_target_force({"force_level": "strong"}, default=3.0) == 15.0, "stored value should win over default")
    check(resolve_target_force({}, default=4.0) == 4.0, "empty parameters should use the default")
    check(resolve_target_force({"force_level": "unknown"}, default=4.0) == 4.0, "unknown level should use the default")
    check(resolve_target_force({"force_newtons": 999}) == ForceConfig.MAX_TARGET_FORCE, "force should clamp to max")
    check(clamp_target_force(0) == ForceConfig.MIN_TARGET_FORCE, "force should clamp to min")


def main():
    tests = [
        ("start defaults", test_start_defaults),
        ("set_target_force restarts", test_set_target_force_restarts),
        ("set_target_force while inactive", test_set_target_force_while_inactive),
        ("stop", test_stop),
        ("invalid inputs", test_invalid_inputs_rejected),
        ("forceMode failure", test_force_mode_failure_reported),
        ("zero sensor", test_zero_sensor),
        ("unavailable controller", test_unavailable_controller),
        ("watchdog auto release", test_watchdog_auto_release),
        ("zero timeout disables watchdog", test_zero_timeout_disables_watchdog),
        ("attach/detach", test_attach_detach),
        ("limit builder", test_limit_builder),
        ("wrench builder", test_wrench_builder),
        ("resolve target force", test_resolve_target_force),
    ]

    failures = 0
    for name, test in tests:
        try:
            test()
            print(f"PASS  {name}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {name}: {exc}")
        except Exception as exc:
            failures += 1
            print(f"ERROR {name}: {type(exc).__name__}: {exc}")

    print("-" * 60)
    print(f"{len(tests) - failures}/{len(tests)} passed")
    return failures == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
