#!/usr/bin/env python3
"""
Automated test for Hand Guiding Tool (auto-closes)
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from ui_mainwindow import MainWindow

def test_hand_guiding_tool():
    """Test Hand Guiding Tool integration"""
    app = QApplication(sys.argv)

    print("\n" + "="*70)
    print("HAND GUIDING TOOL AUTOMATED TEST")
    print("="*70)

    # Create main window
    window = MainWindow()
    window.show()

    print("\n✓ Main window created")

    # Test results
    test_results = []

    def run_tests():
        try:
            # Test 1: Open Hand Guiding Tool
            print("\nTest 1: Opening Hand Guiding Tool...")
            window.on_hand_guiding_tool()

            if hasattr(window, 'hand_guiding_tool') and window.hand_guiding_tool:
                test_results.append(("Tool creation", True))
                print("  ✓ Tool instance created")

                # Test 2: Check if visible
                is_visible = window.hand_guiding_tool.isVisible()
                test_results.append(("Tool visibility", is_visible))
                print(f"  {'✓' if is_visible else '✗'} Tool is {'visible' if is_visible else 'not visible'}")

                # Test 3: Check UI elements
                ui_elements = [
                    'enable_freedrive_btn',
                    'disable_freedrive_btn',
                    'save_position_btn',
                    'open_gripper_btn',
                    'close_gripper_btn',
                    'position_list',
                    'status_label',
                    'position_label'
                ]

                all_present = True
                for element in ui_elements:
                    has_element = hasattr(window.hand_guiding_tool, element)
                    if not has_element:
                        all_present = False
                        print(f"  ✗ Missing: {element}")

                test_results.append(("All UI elements", all_present))
                if all_present:
                    print("  ✓ All UI elements present")

                # Test 4: Check robot controller connection
                has_robot = hasattr(window.hand_guiding_tool, 'robot') and window.hand_guiding_tool.robot is not None
                test_results.append(("Robot controller", has_robot))
                print(f"  {'✓' if has_robot else '✗'} Robot controller {'connected' if has_robot else 'not connected'}")

                # Test 5: Check position storage
                has_storage = hasattr(window.hand_guiding_tool, 'position_storage')
                test_results.append(("Position storage", has_storage))
                print(f"  {'✓' if has_storage else '✗'} Position storage {'available' if has_storage else 'not available'}")

                if has_storage:
                    pos_count = len(window.hand_guiding_tool.position_storage)
                    print(f"     Existing positions: {pos_count}")

                # Test 6: Check window title
                title = window.hand_guiding_tool.windowTitle()
                has_title = len(title) > 0
                test_results.append(("Window title", has_title))
                print(f"  {'✓' if has_title else '✗'} Window title: '{title}'")

            else:
                test_results.append(("Tool creation", False))
                print("  ✗ Tool instance NOT created")

        except Exception as e:
            test_results.append(("Exception", False))
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()

        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)

        for test_name, result in test_results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"  {status}: {test_name}")

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        else:
            print(f"\n✗✗✗ {total - passed} TEST(S) FAILED ✗✗✗")

        print("="*70 + "\n")

        # Close after 2 seconds
        QTimer.singleShot(2000, app.quit)

    # Run tests after 1 second
    QTimer.singleShot(1000, run_tests)

    sys.exit(app.exec_())

if __name__ == "__main__":
    test_hand_guiding_tool()
