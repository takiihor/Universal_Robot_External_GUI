#!/usr/bin/env python3
"""
Test script for enhanced parameter dialogs.

Tests all action types to ensure dialogs open correctly and parameters can be retrieved.
"""

import sys
from PyQt5.QtWidgets import QApplication
from sequential_controller import ActionType
from sequential_controller_dialog_enhanced import EnhancedActionParameterDialog


def test_dialog(action_type: ActionType, test_params: dict = None):
    """Test a single dialog type"""
    print(f"\n{'='*60}")
    print(f"Testing: {action_type.name}")
    print(f"{'='*60}")

    try:
        # Create dialog
        dialog = EnhancedActionParameterDialog(action_type, test_params)
        print(f"✓ Dialog created successfully")
        print(f"  Title: {dialog.windowTitle()}")

        # Check if parameters can be retrieved
        params = dialog.get_parameters()
        print(f"✓ Parameters retrieved: {params}")

        return True

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Test all action type dialogs"""
    app = QApplication(sys.argv)

    print("\n" + "="*60)
    print("ENHANCED PARAMETER DIALOG TESTING")
    print("="*60)

    # Test cases for each action type
    test_cases = [
        # Motion actions
        (ActionType.MOVE_TO_POSITION, {'position_name': 'home', 'speed': 50}),
        (ActionType.RELATIVE_MOVE, {'direction': 'x', 'distance': 0.1, 'speed': 50}),
        (ActionType.SAVE_POSITION, {'position_name': 'test_pos'}),
        (ActionType.RETURN_HOME, None),

        # Wait actions
        (ActionType.WAIT, {'duration': 5}),

        # Freedrive (Hand Guiding)
        (ActionType.ENABLE_FREEDRIVE, None),
        (ActionType.DISABLE_FREEDRIVE, None),

        # Force control
        (ActionType.ENABLE_FORCE, {'force_limit': 10}),
        (ActionType.DISABLE_FORCE, None),
        (ActionType.SET_FORCE_LEVEL, {'force': 15}),

        # Gripper control
        (ActionType.GRIPPER_OPEN, None),
        (ActionType.GRIPPER_CLOSE, None),
        (ActionType.GRIPPER_MOVE, {'position': 50}),

        # I/O Control
        (ActionType.SET_DIGITAL_OUTPUT, {'pin': 0, 'state': 'high'}),
        (ActionType.WAIT_DIGITAL_INPUT, {'pin': 0, 'state': 'high', 'timeout': 10}),
        (ActionType.SET_ANALOG_OUTPUT, {'pin': 0, 'voltage': 5.0}),
        (ActionType.READ_DIGITAL_INPUT, {'pin': 0}),

        # Safety
        (ActionType.EMERGENCY_STOP, None),
    ]

    results = []
    for action_type, params in test_cases:
        success = test_dialog(action_type, params)
        results.append((action_type.name, success))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} passed ({100*passed//total}%)")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
