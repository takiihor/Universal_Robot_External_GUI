#!/usr/bin/env python3
"""
Test Hand Guiding Tool
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from ui_mainwindow import MainWindow

def test_hand_guiding_tool():
    """Test Hand Guiding Tool integration"""
    app = QApplication(sys.argv)

    print("\n" + "="*70)
    print("HAND GUIDING TOOL TEST")
    print("="*70)

    # Create main window
    window = MainWindow()
    window.show()

    print("\n✓ Main window created and shown")

    # Test opening Hand Guiding Tool after 2 seconds
    def open_tool():
        print("\n" + "-"*70)
        print("OPENING HAND GUIDING TOOL...")
        print("-"*70)

        try:
            # Simulate menu action
            window.on_hand_guiding_tool()

            print("✓ Hand Guiding Tool opened successfully")

            # Check if tool exists
            if hasattr(window, 'hand_guiding_tool') and window.hand_guiding_tool:
                print("✓ Hand Guiding Tool instance created")
                print(f"  - Window title: {window.hand_guiding_tool.windowTitle()}")
                print(f"  - Is visible: {window.hand_guiding_tool.isVisible()}")

                # Check UI elements
                checks = [
                    ("Enable button", hasattr(window.hand_guiding_tool, 'enable_freedrive_btn')),
                    ("Disable button", hasattr(window.hand_guiding_tool, 'disable_freedrive_btn')),
                    ("Save position button", hasattr(window.hand_guiding_tool, 'save_position_btn')),
                    ("Open gripper button", hasattr(window.hand_guiding_tool, 'open_gripper_btn')),
                    ("Close gripper button", hasattr(window.hand_guiding_tool, 'close_gripper_btn')),
                    ("Position list", hasattr(window.hand_guiding_tool, 'position_list')),
                    ("Status label", hasattr(window.hand_guiding_tool, 'status_label')),
                    ("Position label", hasattr(window.hand_guiding_tool, 'position_label')),
                ]

                print("\n" + "-"*70)
                print("UI ELEMENT CHECKS:")
                print("-"*70)

                all_passed = True
                for name, result in checks:
                    status = "✓" if result else "✗"
                    print(f"  {status} {name}: {'Present' if result else 'MISSING'}")
                    if not result:
                        all_passed = False

                if all_passed:
                    print("\n✓✓✓ ALL UI ELEMENTS PRESENT ✓✓✓")
                else:
                    print("\n✗✗✗ SOME UI ELEMENTS MISSING ✗✗✗")

                # Check position storage
                print("\n" + "-"*70)
                print("POSITION STORAGE CHECK:")
                print("-"*70)

                if hasattr(window.hand_guiding_tool, 'position_storage'):
                    print(f"✓ Position storage connected")
                    print(f"  - Number of existing positions: {len(window.hand_guiding_tool.position_storage)}")

                    if len(window.hand_guiding_tool.position_storage) > 0:
                        print(f"  - Existing positions:")
                        for pos_name in list(window.hand_guiding_tool.position_storage.keys())[:5]:
                            print(f"    • {pos_name}")
                        if len(window.hand_guiding_tool.position_storage) > 5:
                            print(f"    ... and {len(window.hand_guiding_tool.position_storage) - 5} more")
                else:
                    print("✗ Position storage NOT connected")

                print("\n" + "-"*70)
                print("VISUAL CHECK:")
                print("-"*70)
                print("Please verify the Hand Guiding Tool window:")
                print("  1. Window is displayed")
                print("  2. Left panel has control buttons")
                print("  3. Right panel shows position list")
                print("  4. Bottom has operation guide")
                print("  5. Export and Close buttons at bottom")
                print("\nWindows will remain open for manual testing...")
                print("Close windows manually when done.")
                print("-"*70 + "\n")

            else:
                print("✗ Hand Guiding Tool instance NOT created")

        except Exception as e:
            print(f"\n✗✗✗ ERROR: {e}")
            import traceback
            traceback.print_exc()

    # Open tool after 2 seconds
    QTimer.singleShot(2000, open_tool)

    # Note: Not auto-closing - let user test manually
    print("\nMain window displayed. Hand Guiding Tool will open in 2 seconds...")
    print("Close windows manually when done testing.\n")

    sys.exit(app.exec_())

if __name__ == "__main__":
    test_hand_guiding_tool()
