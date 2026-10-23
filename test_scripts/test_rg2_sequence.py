"""Offline failure and sequence tests; never connect to robot hardware."""

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rg2_gripper import GripperError, RG2Gripper, _Transport
from test_scripts import test_rg2_pick_place as sequence


def state(width=100.0, grip=False, busy=False, fault=False):
    return dict(width_mm=width, grip_detected=grip, busy=busy, safety_failed=fault)


class RG2Tests(unittest.TestCase):
    def test_read_only_status_does_not_command_jaws(self):
        client = RG2Gripper('unused')
        client._rpc = Mock()
        client._rpc.rg_get_width.return_value = 101.1
        client._rpc.rg_get_busy.return_value = False
        client._rpc.rg_get_grip_detected.return_value = False
        client._rpc.rg_get_safety_failed.return_value = False
        self.assertEqual(client.status(), state(101.1))
        client._rpc.rg_grip.assert_not_called()

    def simulate(self, states, **command_options):
        client = RG2Gripper('unused', timeout=0.5)
        client._rpc = Mock()
        client._rpc.rg_grip.return_value = 0
        samples = iter(states)
        last = [states[-1]]
        def next_state():
            last[0] = next(samples, last[0])
            return last[0]
        client.status = next_state
        now = [0.0]
        def advance(seconds):
            now[0] += seconds
        with patch('rg2_gripper.time.monotonic', side_effect=lambda: now[0]), \
             patch('rg2_gripper.time.sleep', side_effect=advance):
            result = client.move(20.0, 10.0, **command_options)
        return result, client

    def test_grip_requires_detected_object(self):
        with self.assertRaisesRegex(GripperError, 'timeout'):
            self.simulate([state(), state(20)], require_grip=True)
        result, client = self.simulate([state(), state(35, grip=True)], require_grip=True)
        self.assertTrue(result['grip_detected'])
        client._rpc.rg_grip.assert_called_once_with(0, 20.0, 10.0)

    def test_release_requires_no_grip_and_target_width(self):
        with self.assertRaises(GripperError):
            self.simulate([state(35, grip=True), state(20, grip=True)], require_release=True)
        with self.assertRaises(GripperError):
            self.simulate([state(), state(40)], require_release=True)
        result, _ = self.simulate([state(), state(20)], require_release=True)
        self.assertFalse(result['grip_detected'])

    def test_fault_and_invalid_targets_send_no_command(self):
        client = RG2Gripper('unused')
        client._rpc = Mock()
        client.status = lambda: state(fault=True)
        with self.assertRaises(GripperError):
            client.move(20, 10)
        client._rpc.rg_grip.assert_not_called()
        for width, force in ((float('nan'), 10), (111, 10), (20, 41), (20, 0)):
            with self.subTest(width=width, force=force), self.assertRaises(ValueError):
                client.move(width, force)
        client._rpc.rg_grip.assert_not_called()

    def test_release_reports_latched_S2_fault_and_sends_no_jaw_command(self):
        client = RG2Gripper('unused')
        client.status = lambda: state(41.6, grip=True, fault=True)
        client._rpc = Mock()
        client._rpc.rg_get_status.return_value = 98
        client._rpc.rg_get_s1_pushed.return_value = False
        client._rpc.rg_get_s1_triggered.return_value = False
        client._rpc.rg_get_s2_pushed.return_value = False
        client._rpc.rg_get_s2_triggered.return_value = True
        with self.assertRaisesRegex(GripperError, 'S2_triggered=True'):
            client.move(100, 10, require_release=True)
        client._rpc.rg_grip.assert_not_called()
        self.assertTrue(client.status()['safety_failed'])

    def test_probe_safety_check_is_bounded_and_never_commands_or_resets(self):
        client = RG2Gripper('unused')
        client._rpc = Mock()
        original_timeout = client._transport.timeout
        def healthy(index):
            self.assertLessEqual(client._transport.timeout, .1)
            return False
        client._rpc.rg_get_safety_failed.side_effect = healthy
        client.check_safety()
        self.assertEqual(client._transport.timeout, original_timeout)
        self.assertEqual([call[0] for call in client._rpc.method_calls], ['rg_get_safety_failed'])
        client._rpc.rg_get_safety_failed.side_effect = TimeoutError('lost reply')
        with self.assertRaises(GripperError):
            client.check_safety()
        self.assertEqual(client._transport.timeout, original_timeout)
        client._rpc.rg_grip.assert_not_called()

    def test_probe_safety_fault_is_not_normal_contact(self):
        client = RG2Gripper('unused')
        client._rpc = Mock()
        client._rpc.rg_get_safety_failed.return_value = True
        with self.assertRaisesRegex(GripperError, 'contact is not accepted'):
            client.check_safety()
        client._rpc.rg_grip.assert_not_called()

    def test_command_transport_does_not_retry(self):
        transport = _Transport(1)
        transport.single_request = Mock(side_effect=ConnectionResetError)
        with patch.object(transport, 'close') as close:
            with self.assertRaises(ConnectionResetError):
                transport.request('unused', '/', b'data')
            self.assertEqual(close.call_count, 2)
        transport.single_request.assert_called_once()

    def test_status_survives_server_closing_keepalive_connections(self):
        class ClosingHandler(SimpleXMLRPCRequestHandler):
            protocol_version = 'HTTP/1.1'

            def do_POST(self):
                super().do_POST()
                # Mimic a daemon closing a cached connection unexpectedly,
                # without advertising Connection: close in its response.
                self.close_connection = True

        class CountingServer(SimpleXMLRPCServer):
            accepted_connections = 0

            def get_request(self):
                request = super().get_request()
                self.accepted_connections += 1
                return request

        server = CountingServer(('127.0.0.1', 0), requestHandler=ClosingHandler,
                                logRequests=False)
        server.register_function(lambda index: 99.6, 'rg_get_width')
        for name in ('rg_get_busy', 'rg_get_grip_detected', 'rg_get_safety_failed'):
            server.register_function(lambda index: False, name)
        jaw_command = Mock(return_value=0)
        server.register_function(jaw_command, 'rg_grip')
        thread = threading.Thread(target=server.serve_forever,
                                  kwargs={'poll_interval': 0.01}, daemon=True)
        thread.start()
        client = RG2Gripper('127.0.0.1', port=server.server_address[1])
        try:
            self.assertEqual(client.status(), state(99.6))
            self.assertEqual(client.status(), state(99.6))
            self.assertEqual(server.accepted_connections, 8)
            jaw_command.assert_not_called()
        finally:
            client.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


class FakeRobot:
    def __init__(self, events):
        self.events = events
        self.pose = [0.3, 0.0, 0.5, 0, 0, 0]
        self.presets = {
            'home_a': SimpleNamespace(joints=[0] * 6, tcp_pose=list(self.pose)),
            'positionA': SimpleNamespace(joints=[0] * 6, tcp_pose=[0.4, -0.1, 0.25, 0, 0, 0]),
            'drop': SimpleNamespace(joints=[0] * 6, tcp_pose=[0.45, -0.17, 0.27, 0, 0, 0]),
        }
        self.preset_manager = SimpleNamespace(get_preset=self.presets.get)
        self.force_controller = SimpleNamespace(is_active=False)

    def stop_force_mode(self):
        self.events.append(('force_stop',))
        self.force_controller.is_active = False
        return True

    def move_to_preset_position(self, name, **kwargs):
        self.events.append(('home', name, kwargs.get('speed')))
        self.pose = list(self.presets[name].tcp_pose)
        return True

    def move_tcp(self, *pose, **kwargs):
        if kwargs['relative']:
            self.pose[2] += kwargs.get('z', 0)
            self.events.append(('retract', kwargs.get('z')))
        else:
            self.pose = list(pose)
            self.events.append(('linear', tuple(pose[:3])))
        return True

    def get_tcp_pose(self):
        return list(self.pose)


class FakeGripper:
    def __init__(self, events, fail_grip=False, fail_release=False):
        self.events, self.held = events, False
        self.fail_grip, self.fail_release = fail_grip, fail_release

    def status(self):
        return state(35 if self.held else 80, grip=self.held)

    def check_safety(self):
        if self.status()['safety_failed']:
            raise GripperError('RG2 safety interlock activated during pick probing')

    def move(self, width, force, **kwargs):
        if kwargs.get('require_grip'):
            self.events.append(('grip', width))
            if self.fail_grip:
                raise GripperError('No object detected')
            self.held = True
        else:
            self.events.append(('release', width))
            if self.held and self.fail_release:
                raise GripperError('Release failed')
            self.held = False
        return self.status()


class SequenceTests(unittest.TestCase):
    def args(self, *extra):
        return sequence.parse_args(['--open-width-mm', '80', '--grip-width-mm', '20',
                                    '--grip-force-n', '10', '--yes', *extra])

    def run_fake(self, *, fail_grip=False, fail_release=False, dry=False, cycles=1,
                 force_start_height=None, pick_contact_z=.25):
        events = []
        robot = FakeRobot(events)
        gripper = FakeGripper(events, fail_grip, fail_release)
        def found_contact(*args, **kwargs):
            is_pick = getattr(args[2], 'contact_min_time_s', None) == 0
            if is_pick:
                self.assertEqual(kwargs['stop_at_z'], .25)
                self.assertAlmostEqual(args[2].max_descent_mm, 100)
            if force_start_height == 0 and not is_pick:
                self.assertEqual(args[2].max_descent_mm, 50)
                self.assertAlmostEqual(args[4], .27)
            pose = [.4, -.1, pick_contact_z, 0, 0, 0] if is_pick else [.45, -.17, .27, 0, 0, 0]
            robot.pose = list(pose)
            robot.stop_force_mode()
            reason = 'position' if is_pick and pick_contact_z <= .25 else 'contact'
            events.append((f'pick_{reason}', pick_contact_z) if is_pick else ('contact',))
            return dict(reason=reason, delta=0 if reason == 'position' else 10,
                        descent=args[4]-pose[2], elapsed=2, z=pose[2], pose=pose)
        def baseline(*args):
            events.append(('tare',))
            return [0] * 6
        def force_start(*args):
            is_pick = getattr(args[1], 'contact_min_time_s', None) == 0
            if force_start_height == 0 and not is_pick:
                self.assertEqual(args[1].max_descent_mm, 50)
            robot.force_controller.is_active = True
            events.append(('pick_force_start',) if is_pick else ('force_start',))
            return True
        with contextlib.redirect_stdout(io.StringIO()), \
             patch.object(sequence.drop, 'wait'), \
             patch.object(sequence.drop, 'collect_force_baseline', side_effect=baseline), \
             patch.object(sequence.drop, 'start_force_descent', side_effect=force_start), \
             patch.object(sequence.drop, 'descend_until_contact', side_effect=found_contact):
            try:
                args = self.args('--cycles', str(cycles), *(['--dry-run'] if dry else []))
                args.force_start_height_mm = force_start_height
                result = sequence.run_cycles(SimpleNamespace(processEvents=lambda: None),
                                             robot, gripper, args)
                return result, events
            except (GripperError, sequence.drop.TestAbort) as exc:
                return exc, events

    def test_full_pick_and_existing_force_drop_sequence(self):
        result, events = self.run_fake()
        self.assertEqual(result, 0)
        self.assertEqual([event[0] for event in events], [
            'home', 'release', 'linear', 'tare', 'pick_force_start', 'force_stop',
            'pick_position', 'linear', 'grip', 'linear', 'home',
            'linear', 'tare', 'force_start', 'force_stop', 'contact', 'release', 'retract',
        ])
        self.assertEqual(events[7], ('linear', (0.4, -0.1, .25)))
        self.assertEqual(events[0], ('home', 'home_a', .1))
        self.assertEqual(events[10], ('home', 'home_a', .1))

    def test_dry_run_has_no_arm_gripper_or_force_commands(self):
        result, events = self.run_fake(dry=True, cycles=0, force_start_height=0)
        self.assertEqual(result, 0)
        self.assertEqual(events, [])

    def test_fast_placement_descent_precedes_tare_and_force_mode(self):
        result, events = self.run_fake(force_start_height=0)
        self.assertEqual(result, 0)
        kinds = [event[0] for event in events]
        self.assertEqual(kinds, [
            'home', 'release', 'linear', 'tare', 'pick_force_start', 'force_stop',
            'pick_position', 'linear', 'grip', 'linear', 'home',
            'linear', 'linear', 'tare', 'force_start', 'force_stop', 'contact', 'release', 'retract',
        ])
        self.assertEqual(events[12], ('linear', (.45, -.17, .27)))

    def test_raised_pick_contact_changes_grasp_and_lift_before_closing(self):
        result, events = self.run_fake(pick_contact_z=.29)
        self.assertEqual(result, 0)
        self.assertEqual(events[5], ('force_stop',))
        self.assertAlmostEqual(events[7][1][2], .34)  # contact + 50 mm
        self.assertEqual(events[8][0], 'grip')
        self.assertAlmostEqual(events[9][1][2], .44)  # lift from new grasp, not old approach

    def test_taught_pick_position_has_no_contact_backoff(self):
        result, events = self.run_fake()
        self.assertEqual(result, 0)
        self.assertEqual(events[6], ('pick_position', .25))
        self.assertEqual(events[7], ('linear', (.4, -.1, .25)))
        self.assertEqual(events[8][0], 'grip')
        self.assertAlmostEqual(events[9][1][2], .35)  # loaded lift only

    def test_pick_search_floor_is_capped_at_taught_pose_even_with_large_budget(self):
        robot = FakeRobot([])
        for descent, expected_floor in ((150, .25), (1000, .25), (50, .30)):
            with self.subTest(descent=descent):
                args = self.args('--pick-max-descent-mm', str(descent))
                plan = sequence.plan_sequence(robot, args)
                self.assertAlmostEqual(plan['pick_search_lowest'][2], expected_floor)
                self.assertEqual(args.pick_max_descent_mm, descent)

    def test_contact_at_or_below_taught_pose_cannot_request_contact_backoff(self):
        for contact_z in (.25, .20):
            with self.subTest(contact_z=contact_z), self.assertRaises(sequence.drop.TestAbort):
                sequence.pick_contact_poses(
                    dict(reason='contact', pose=[.4, -.1, contact_z, 0, 0, 0]),
                    self.args(), [.4, -.1, .25, 0, 0, 0],
                )

    def test_real_pick_monitor_selects_taught_pose_or_higher_contact_before_grip(self):
        for higher in (False, True):
            events = []
            robot = FakeRobot(events)
            gripper = FakeGripper(events)
            pick_samples = [(10.2, .29)] if higher else [(0, .30), (0, .25)]
            samples = iter([*pick_samples, (10.2, .27)])
            tick = iter(index * .6 for index in range(20))
            def telemetry(_):
                force_n, z = next(samples)
                robot.pose = [.4, -.1, z, 0, 0, 0]
                return [0, 0, force_n, 0, 0, 0], list(robot.pose)
            def start(*args):
                robot.force_controller.is_active = True
                return True
            with self.subTest(higher=higher), \
                 patch.object(sequence.drop, 'wait'), \
                 patch.object(sequence.drop, 'collect_force_baseline', return_value=[0]*6), \
                 patch.object(sequence.drop, 'start_force_descent', side_effect=start), \
                 patch.object(sequence.drop, 'read_force_and_pose', side_effect=telemetry), \
                 patch.object(sequence.drop.time, 'monotonic', side_effect=lambda: next(tick)), \
                 patch.object(sequence.drop.time, 'sleep'), \
                 contextlib.redirect_stdout(io.StringIO()):
                result = sequence.run_sequence(
                    SimpleNamespace(processEvents=lambda: None), robot, gripper, self.args(),
                )
            self.assertEqual(result, 0)
            grip_index = next(i for i, event in enumerate(events) if event[0] == 'grip')
            self.assertEqual(events[grip_index - 2][0], 'force_stop')
            self.assertEqual(events[grip_index - 1][0], 'linear')
            self.assertAlmostEqual(events[grip_index - 1][1][2], .34 if higher else .25)
            self.assertFalse(robot.force_controller.is_active)

    def test_exhausted_pick_search_stops_force_and_never_grips_or_lifts(self):
        events = []
        robot = FakeRobot(events)
        gripper = FakeGripper(events)
        def start(*args):
            robot.force_controller.is_active = True
            return True
        with patch.object(sequence.drop, 'wait'), \
             patch.object(sequence.drop, 'collect_force_baseline', return_value=[0]*6), \
             patch.object(sequence.drop, 'start_force_descent', side_effect=start), \
             patch.object(sequence.drop, 'descend_until_contact', side_effect=sequence.drop.NoContact('No pick contact')), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(sequence.drop.NoContact):
                sequence.run_sequence(SimpleNamespace(processEvents=lambda: None), robot, gripper, self.args())
        self.assertFalse(robot.force_controller.is_active)
        self.assertNotIn('grip', [event[0] for event in events])
        self.assertEqual(events[-1][0], 'force_stop')

    def test_pick_backoff_envelope_is_checked_before_motion(self):
        events = []
        robot = FakeRobot(events)
        args = self.args('--pick-backoff-mm', '1000')
        with self.assertRaises(sequence.drop.TestAbort):
            sequence.run_sequence(None, robot, FakeGripper(events), args)
        self.assertEqual(events, [])

    def test_probe_fault_stops_force_without_rise_or_grip(self):
        for during_search in (True, False):
            events = []
            robot = FakeRobot(events)
            gripper = FakeGripper(events)
            gripper.check_safety = Mock(side_effect=[
                None, None, GripperError('RG2 safety interlock activated')
            ])
            def start(*args):
                robot.force_controller.is_active = True
                return True
            def contact(*args, **kwargs):
                if during_search:
                    args[2].contact_guard()
                robot.stop_force_mode()
                return dict(pose=[.4, -.1, .2, 0, 0, 0])
            with self.subTest(during_search=during_search), \
                 patch.object(sequence.drop, 'wait'), \
                 patch.object(sequence.drop, 'collect_force_baseline', return_value=[0]*6), \
                 patch.object(sequence.drop, 'start_force_descent', side_effect=start), \
                 patch.object(sequence.drop, 'descend_until_contact', side_effect=contact), \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(GripperError):
                    sequence.run_sequence(SimpleNamespace(processEvents=lambda: None), robot, gripper, self.args())
            self.assertFalse(robot.force_controller.is_active)
            self.assertEqual([event[0] for event in events], ['home', 'release', 'linear', 'force_stop'])

    def test_cannot_stop_pick_force_mode_prevents_rise_and_grip(self):
        events = []
        robot = FakeRobot(events)
        robot.force_controller.is_active = True
        robot.stop_force_mode = Mock(return_value=False)
        gripper = FakeGripper(events)
        contact = dict(pose=[.4, -.1, .2, 0, 0, 0])
        with patch.object(sequence.drop, 'wait'), \
             patch.object(sequence.drop, 'collect_force_baseline', return_value=[0]*6), \
             patch.object(sequence.drop, 'start_force_descent', return_value=True), \
             patch.object(sequence.drop, 'descend_until_contact', return_value=contact), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(sequence.drop.TestAbort, 'Cannot stop pick force mode'):
                sequence.run_sequence(SimpleNamespace(processEvents=lambda: None), robot, gripper, self.args())
        robot.stop_force_mode.assert_called_once()
        self.assertEqual([event[0] for event in events], ['home', 'release', 'linear'])

    def test_pick_force_parameters_are_validated(self):
        cases = (
            ['--pick-backoff-mm', '0'], ['--pick-contact-force-n', '0'],
            ['--pick-contact-force-n', '20', '--pick-command-force-n', '10'],
            ['--pick-descent-speed-mm-s', '0'], ['--pick-max-descent-mm', '-1'],
        )
        for extra in cases:
            with self.subTest(extra=extra), contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit):
                self.args(*extra)
        args = self.args('--pick-contact-force-n', '5', '--pick-backoff-mm', '60')
        self.assertEqual(args.pick_command_force_n, 6)
        self.assertEqual(args.pick_backoff_mm, 60)

    def test_two_complete_cycles_repick_and_replace_the_block(self):
        result, events = self.run_fake(cycles=2)
        self.assertEqual(result, 0)
        kinds = [event[0] for event in events]
        self.assertEqual(kinds.count('grip'), 2)
        self.assertEqual(kinds.count('contact'), 2)
        self.assertEqual(kinds.count('release'), 4)
        self.assertEqual(kinds.count('home'), 4)
        self.assertEqual(kinds[:len(kinds)//2], kinds[len(kinds)//2:])

    def test_failed_pick_does_not_lift_or_start_placement(self):
        error, events = self.run_fake(fail_grip=True)
        self.assertIsInstance(error, GripperError)
        self.assertEqual(events[-1][0], 'grip')
        self.assertNotIn(('contact',), events)

    def test_failed_release_does_not_retract(self):
        error, events = self.run_fake(fail_release=True)
        self.assertIsInstance(error, sequence.drop.TestAbort)
        self.assertEqual(events[-1][0], 'release')
        self.assertNotIn('retract', [event[0] for event in events])

    def test_higher_surface_releases_at_measured_contact_not_taught_drop(self):
        events = []
        robot = FakeRobot(events)
        robot.force_controller = SimpleNamespace(is_active=True)
        def stop_force():
            events.append(('force_stop',))
            robot.force_controller.is_active = False
            return True
        robot.stop_force_mode = stop_force
        gripper = FakeGripper(events)
        gripper.held = True
        args = self.args()
        wrapper = sequence.PlacementRobot(
            robot, gripper, args, SimpleNamespace(processEvents=lambda: None)
        )
        higher_contact = [.45, -.17, .3004, 0, 0, 0]
        def telemetry(_):
            robot.pose = list(higher_contact)
            return [0, 0, 10.2, 0, 0, 0], list(higher_contact)
        with patch.object(sequence.drop, 'wait'), \
             patch.object(sequence.drop, 'collect_force_baseline', return_value=[0]*6), \
             patch.object(sequence.drop, 'start_force_descent', return_value=True), \
             patch.object(sequence.drop, 'read_force_and_pose', side_effect=telemetry), \
             patch.object(sequence.drop.time, 'monotonic', side_effect=[0, .6]), \
             contextlib.redirect_stdout(io.StringIO()):
            result = sequence.drop.run_test(
                SimpleNamespace(processEvents=lambda: None), wrapper, args,
                move_home=False, resolved_drop_pose=robot.presets['drop'].tcp_pose,
            )
        self.assertEqual(result, 0)
        self.assertEqual([event[0] for event in events],
                         ['linear', 'force_stop', 'release', 'retract'])
        self.assertGreater(higher_contact[2], robot.presets['drop'].tcp_pose[2])
        self.assertAlmostEqual(robot.pose[2], higher_contact[2] + .1)
        self.assertFalse(gripper.held)

    def test_missing_or_outside_workspace_pick_aborts_before_actions(self):
        for missing in (True, False):
            events = []
            robot = FakeRobot(events)
            if missing:
                robot.presets.pop('positionA')
            else:
                robot.presets['positionA'].tcp_pose[0] = 1.5
            with self.subTest(missing=missing), self.assertRaises(sequence.drop.TestAbort):
                sequence.run_sequence(None, robot, FakeGripper(events), self.args())
            self.assertEqual(events, [])

    def test_recipe_overrides_and_live_required_values(self):
        with tempfile.TemporaryDirectory() as directory:
            recipe = Path(directory) / 'recipe.json'
            recipe.write_text(json.dumps(dict(open_width_mm=90, grip_width_mm=20,
                                             grip_force_n=10, pick_preset='positionA')))
            args = sequence.parse_args(['--config', str(recipe), '--open-width-mm', '80'])
            self.assertEqual(args.open_width_mm, 80)
            self.assertEqual(args.pick_preset, 'positionA')
            recipe.write_text('{"yes": true}')
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                sequence.parse_args(['--config', str(recipe)])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            sequence.parse_args([])
        args = sequence.parse_args(['--dry-run'])
        self.assertIsNone(args.grip_width_mm)


class CycleTests(unittest.TestCase):
    def args(self, *extra):
        return sequence.parse_args(['--open-width-mm', '100', '--grip-width-mm', '40',
                                    '--grip-force-n', '5', *extra])

    def test_finite_cycles_confirm_once_and_wait_between_successes(self):
        args = self.args('--cycles', '3', '--cycle-wait-s', '1.5')
        with patch.object(sequence, 'run_sequence', return_value=0) as run, \
             patch.object(sequence.drop, 'wait') as wait, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sequence.run_cycles(None, None, None, args), 0)
        self.assertEqual(run.call_count, 3)
        self.assertEqual([call.args[3].yes for call in run.call_args_list], [False, True, True])
        self.assertFalse(args.yes, 'Do not mutate the original job confirmation flag')
        self.assertEqual(wait.call_count, 2)
        wait.assert_called_with(None, 1.5)

    def test_cancelled_or_failed_cycle_never_retries(self):
        for outcomes in ([1], [0, GripperError('grip lost')]):
            with self.subTest(outcomes=outcomes), \
                 patch.object(sequence, 'run_sequence', side_effect=outcomes) as run, \
                 patch.object(sequence.drop, 'wait') as wait, \
                 contextlib.redirect_stdout(io.StringIO()):
                if len(outcomes) == 1:
                    self.assertEqual(sequence.run_cycles(None, None, None, self.args('--cycles', '10')), 1)
                else:
                    with self.assertRaises(GripperError):
                        sequence.run_cycles(None, None, None, self.args('--cycles', '10'))
                self.assertEqual(run.call_count, len(outcomes))
                self.assertEqual(wait.call_count, len(outcomes)-1)

    def test_continuous_mode_propagates_interrupt_without_another_cycle(self):
        with patch.object(sequence, 'run_sequence', side_effect=[0, 0, KeyboardInterrupt()]) as run, \
             patch.object(sequence.drop, 'wait') as wait, \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(KeyboardInterrupt):
                sequence.run_cycles(None, None, None, self.args('--cycles', '0'))
            self.assertEqual(run.call_count, 3)
            self.assertEqual(wait.call_count, 2)

    def test_repeat_settings_in_recipe_and_cli_override(self):
        with tempfile.TemporaryDirectory() as directory:
            recipe = Path(directory) / 'repeat.json'
            recipe.write_text('{"cycles": 5, "cycle_wait_s": 4}')
            args = sequence.parse_args(['--config', str(recipe), '--cycles', '2', '--dry-run'])
            self.assertEqual(args.cycles, 2)
            self.assertEqual(args.cycle_wait_s, 4)
            bad_settings = (
                {'cycles': -1}, {'cycles': True}, {'cycles': 2.5}, {'cycles': None},
                {'cycle_wait_s': -1}, {'cycle_wait_s': float('nan')},
            )
            for settings in bad_settings:
                recipe.write_text(json.dumps(settings))
                with self.subTest(settings=settings), \
                     contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    sequence.parse_args(['--config', str(recipe), '--dry-run'])


if __name__ == '__main__':
    unittest.main()
