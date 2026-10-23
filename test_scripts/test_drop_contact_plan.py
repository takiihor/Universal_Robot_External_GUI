"""Regression checks for drop planning; no robot connection or motion."""

import contextlib
import io
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_scripts import test_home_to_drop_force_contact as drop_test


class DropPlanTests(unittest.TestCase):
    def make_robot(self, tcp_pose=None, tcp_offset=None):
        preset = SimpleNamespace(joints=[0.1] * 6, tcp_pose=tcp_pose)
        control = Mock(spec=['getTCPOffset', 'getForwardKinematics'])
        control.getTCPOffset.return_value = (
            [0, 0, 0.15, 0, 0, 0] if tcp_offset is None else tcp_offset
        )
        control.getForwardKinematics.return_value = [0.4, 0.2, 0.3, 0, 0, 0]
        robot = SimpleNamespace(
            preset_manager=SimpleNamespace(get_preset=Mock(return_value=preset)),
            rtde_control=control,
            move_to_preset_position=Mock(),
            move_tcp=Mock(),
            start_force_mode=Mock(),
        )
        return robot

    def test_joint_only_preset_passes_explicit_active_tcp(self):
        robot = self.make_robot()
        result = drop_test.resolve_drop_pose(robot, 'drop')
        self.assertEqual(result, [0.4, 0.2, 0.3, 0, 0, 0])
        robot.rtde_control.getForwardKinematics.assert_called_once_with(
            [0.1] * 6, [0, 0, 0.15, 0, 0, 0]
        )

    def test_zero_tcp_removes_virtual_offset_in_rotated_frame(self):
        robot = self.make_robot(tcp_offset=[0] * 6)
        # Flange Z points along base X: the virtual 1 mm must be removed from X.
        robot.rtde_control.getForwardKinematics.return_value = [
            0.401, 0.2, 0.3, 0, math.pi / 2, 0
        ]
        result = drop_test.resolve_drop_pose(robot, 'drop')
        self.assertAlmostEqual(result[0], 0.4)
        self.assertAlmostEqual(result[1], 0.2)
        self.assertAlmostEqual(result[2], 0.3)
        self.assertEqual(result[3:], [0, math.pi / 2, 0])
        robot.rtde_control.getForwardKinematics.assert_called_once_with(
            [0.1] * 6, [0, 0, 0.001, 0, 0, 0]
        )

    def test_saved_tcp_pose_does_not_query_forward_kinematics(self):
        pose = [0.3, 0.2, 0.4, 0, 0, 0]
        robot = self.make_robot(tcp_pose=pose)
        self.assertEqual(drop_test.resolve_drop_pose(robot, 'drop'), pose)
        robot.rtde_control.getTCPOffset.assert_not_called()
        robot.rtde_control.getForwardKinematics.assert_not_called()

    def test_invalid_telemetry_is_rejected(self):
        for offset in ([0] * 5, [float('nan')] + [0] * 5):
            with self.subTest(offset=offset):
                robot = self.make_robot(tcp_offset=offset)
                with self.assertRaises(drop_test.TestAbort):
                    drop_test.resolve_drop_pose(robot, 'drop')
                robot.rtde_control.getForwardKinematics.assert_not_called()
        robot = self.make_robot()
        robot.rtde_control.getForwardKinematics.return_value = [float('inf')] * 6
        with self.assertRaises(drop_test.TestAbort):
            drop_test.resolve_drop_pose(robot, 'drop')
        robot = self.make_robot(tcp_pose=[0.2, 0.1, 0.3])
        with self.assertRaises(drop_test.TestAbort):
            drop_test.resolve_drop_pose(robot, 'drop')

    def args(self, extra=None):
        parser = drop_test.build_parser()
        args = parser.parse_args(['--home-preset', 'home_a'] + (extra or []))
        drop_test.validate_args(parser, args)
        return args

    def test_invalid_plan_aborts_before_confirmation_and_home_move(self):
        cases = (
            [1.4541, -0.0985, 0.2624, 0, 0, 0],
            [0.4, 0.2, 1.15, 0, 0, 0],  # approach exceeds Z limit
        )
        for pose in cases:
            with self.subTest(pose=pose):
                robot = self.make_robot(tcp_pose=pose)
                with patch('builtins.input') as confirmation, contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(drop_test.TestAbort, 'no motion commanded'):
                        drop_test.run_test(None, robot, self.args())
                confirmation.assert_not_called()
                robot.move_to_preset_position.assert_not_called()
                robot.move_tcp.assert_not_called()
                robot.start_force_mode.assert_not_called()

    def test_valid_dry_run_does_not_move(self):
        robot = self.make_robot(tcp_pose=[0.4, 0.2, 0.3, 0, 0, 0])
        with patch('builtins.input') as confirmation, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(drop_test.run_test(None, robot, self.args(['--dry-run'])), 0)
        confirmation.assert_not_called()
        robot.move_to_preset_position.assert_not_called()
        robot.move_tcp.assert_not_called()
        robot.start_force_mode.assert_not_called()

    def test_staged_descent_preserves_absolute_lower_z_and_original_args(self):
        args = self.args(['--force-start-height-mm', '0', '--descent-speed-mm-s', '5'])
        plan = drop_test.plan_descent(args, [.452, -.1747, .2678, 0, 0, 0])
        self.assertAlmostEqual(plan['approach'][2], .3678)
        self.assertAlmostEqual(plan['force_start'][2], .2678)
        self.assertEqual(plan['fast_mm'], 100)
        self.assertEqual(plan['force_args'].max_descent_mm, 50)
        self.assertAlmostEqual(plan['force_start'][2] - plan['force_args'].max_descent_mm/1000,
                               plan['approach'][2] - args.max_descent_mm/1000)
        self.assertEqual(args.max_descent_mm, 150)
        self.assertEqual(plan['timeout'], 20)

    def test_omitted_force_start_keeps_original_single_stage_behavior(self):
        args = self.args()
        plan = drop_test.plan_descent(args, [.4, .2, .3, 0, 0, 0])
        self.assertEqual(plan['approach'], plan['force_start'])
        self.assertEqual(plan['fast_mm'], 0)
        self.assertEqual(plan['force_args'].max_descent_mm, args.max_descent_mm)

    def test_invalid_force_start_is_rejected_before_motion(self):
        cases = (['--force-start-height-mm', '-1'],
                 ['--force-start-height-mm', '101'],
                 ['--force-start-height-mm', 'nan'],
                 ['--force-start-height-mm', '0', '--max-descent-mm', '100'])
        for extra in cases:
            with self.subTest(extra=extra), contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit):
                self.args(extra)

    def test_failed_fast_approach_does_not_tare_or_enter_force_mode(self):
        robot = self.make_robot(tcp_pose=[.4, .2, .3, 0, 0, 0])
        robot.move_tcp.side_effect = [True, False]
        args = self.args(['--yes', '--force-start-height-mm', '0'])
        with patch.object(drop_test, 'wait'), \
             patch.object(drop_test, 'collect_force_baseline') as baseline, \
             patch.object(drop_test, 'start_force_descent') as force, \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(drop_test.TestAbort, 'force-start pose failed'):
                drop_test.run_test(None, robot, args, move_home=False)
            baseline.assert_not_called()
            force.assert_not_called()

    def test_pick_contact_is_not_ignored_during_first_half_second(self):
        robot = self.make_robot()
        robot.force_controller = SimpleNamespace(is_active=True)
        robot.stop_force_mode = Mock(return_value=True)
        args = self.args()
        args.contact_min_time_s = 0.0
        pose = [.4, .2, .31, 0, 0, 0]
        with patch.object(drop_test, 'read_force_and_pose', return_value=([0, 0, 10.2, 0, 0, 0], pose)), \
             patch.object(drop_test.time, 'monotonic', side_effect=[0, .05]):
            contact = drop_test.descend_until_contact(
                robot, SimpleNamespace(processEvents=lambda: None), args, [0]*6, .35, 20
            )
        robot.stop_force_mode.assert_called_once()
        self.assertEqual(contact['pose'], pose)
        self.assertEqual(contact['elapsed'], .05)

    def test_probe_guard_runs_before_accepting_force_contact(self):
        robot = self.make_robot()
        robot.force_controller = SimpleNamespace(is_active=True)
        args = self.args()
        args.contact_min_time_s = 0
        args.contact_guard = Mock(side_effect=RuntimeError('RG2 interlock'))
        with patch.object(drop_test, 'read_force_and_pose') as telemetry, \
             patch.object(drop_test.time, 'monotonic', side_effect=[0, .05]):
            with self.assertRaisesRegex(RuntimeError, 'RG2 interlock'):
                drop_test.descend_until_contact(
                    robot, SimpleNamespace(processEvents=lambda: None), args, [0]*6, .35, 20
                )
            telemetry.assert_not_called()
        args.contact_guard.assert_called_once()

    def test_taught_pick_floor_stops_without_force_and_wins_over_same_sample_contact(self):
        for force_n in (0, 10.2):
            with self.subTest(force_n=force_n):
                robot = self.make_robot()
                robot.force_controller = SimpleNamespace(is_active=True)
                robot.stop_force_mode = Mock(return_value=True)
                args = self.args()
                args.contact_min_time_s = 0
                args.max_descent_mm = 100
                pose = [.4, .2, .25, 0, 0, 0]
                with patch.object(drop_test, 'read_force_and_pose', return_value=([0, 0, force_n, 0, 0, 0], pose)), \
                     patch.object(drop_test.time, 'monotonic', side_effect=[0, .05]):
                    result = drop_test.descend_until_contact(
                        robot, SimpleNamespace(processEvents=lambda: None), args,
                        [0]*6, .35, 20, stop_at_z=.25,
                    )
                self.assertEqual(result['reason'], 'position')
                robot.stop_force_mode.assert_called_once()

    def test_higher_pick_contact_stops_before_taught_floor(self):
        robot = self.make_robot()
        robot.force_controller = SimpleNamespace(is_active=True)
        robot.stop_force_mode = Mock(return_value=True)
        args = self.args()
        args.contact_min_time_s = 0
        pose = [.4, .2, .29, 0, 0, 0]
        with patch.object(drop_test, 'read_force_and_pose', return_value=([0, 0, 10.2, 0, 0, 0], pose)), \
             patch.object(drop_test.time, 'monotonic', side_effect=[0, .05]):
            result = drop_test.descend_until_contact(
                robot, SimpleNamespace(processEvents=lambda: None), args,
                [0]*6, .35, 20, stop_at_z=.25,
            )
        self.assertEqual(result['reason'], 'contact')
        robot.stop_force_mode.assert_called_once()

    def test_failed_force_stop_at_pick_floor_is_not_a_successful_pick(self):
        robot = self.make_robot()
        robot.force_controller = SimpleNamespace(is_active=True)
        robot.stop_force_mode = Mock(return_value=False)
        with patch.object(drop_test, 'read_force_and_pose', return_value=([0]*6, [.4, .2, .25, 0, 0, 0])), \
             patch.object(drop_test.time, 'monotonic', side_effect=[0, .05]):
            with self.assertRaisesRegex(drop_test.TestAbort, 'force mode could not be stopped'):
                drop_test.descend_until_contact(
                    robot, SimpleNamespace(processEvents=lambda: None), self.args(),
                    [0]*6, .35, 20, stop_at_z=.25,
                )

    def test_short_pick_search_budget_aborts_instead_of_gripping_above_floor(self):
        robot = self.make_robot()
        robot.force_controller = SimpleNamespace(is_active=True)
        robot.stop_force_mode = Mock(return_value=True)
        args = self.args()
        args.max_descent_mm = 50
        with patch.object(drop_test, 'read_force_and_pose', return_value=([0]*6, [.4, .2, .29, 0, 0, 0])), \
             patch.object(drop_test.time, 'monotonic', side_effect=[0, .6]):
            with self.assertRaises(drop_test.NoContact):
                drop_test.descend_until_contact(
                    robot, SimpleNamespace(processEvents=lambda: None), args,
                    [0]*6, .35, 20, stop_at_z=.25,
                )
        robot.stop_force_mode.assert_called_once()

    def test_pick_floor_with_invalid_pose_or_force_aborts(self):
        for force, pose in (([0]*6, [float('nan')]*6), (None, [.4, .2, .3, 0, 0, 0])):
            with self.subTest(force=force, pose=pose):
                robot = self.make_robot()
                robot.force_controller = SimpleNamespace(is_active=True)
                with patch.object(drop_test, 'read_force_and_pose', return_value=(force, pose)), \
                     patch.object(drop_test.time, 'monotonic', side_effect=[0, .05]):
                    with self.assertRaises(drop_test.TestAbort):
                        drop_test.descend_until_contact(
                            robot, SimpleNamespace(processEvents=lambda: None), self.args(),
                            [0]*6, .35, 20, stop_at_z=.25,
                        )


class PresetSaveTests(unittest.TestCase):
    def test_ui_saves_live_joint_and_tcp_pose_together(self):
        from ui_mainwindow import MainWindow

        receiver = Mock()
        receiver.getActualQ.return_value = [0.1] * 6
        receiver.getActualTCPPose.return_value = [0.4, 0.2, 0.3, 0, 0, 0]
        window = SimpleNamespace(
            preset_name_input=Mock(),
            robot_controller=SimpleNamespace(is_connected=lambda: True, rtde_receive=receiver),
            preset_manager=Mock(),
            show_info_message=Mock(),
            update_preset_list=Mock(),
        )
        window.preset_name_input.text.return_value = 'drop'
        MainWindow.on_save_preset_clicked(window)
        saved = window.preset_manager.add_preset.call_args.args[0]
        self.assertEqual(saved.joints, [0.1] * 6)
        self.assertEqual(saved.tcp_pose, [0.4, 0.2, 0.3, 0, 0, 0])


if __name__ == '__main__':
    unittest.main()
