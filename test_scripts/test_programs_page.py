#!/usr/bin/env python3
"""
Test Programs Page to verify Sequential Controller UI is displayed
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from ui_mainwindow import MainWindow

def test_programs_page():
    """Test Programs page content"""
    app = QApplication(sys.argv)

    print("\n" + "="*70)
    print("PROGRAMS PAGE TEST")
    print("="*70)

    # Create main window
    window = MainWindow()
    window.show()

    print("\n✓ Main window created")

    def check_programs_page():
        try:
            print("\n" + "-"*70)
            print("CHECKING PROGRAMS PAGE")
            print("-"*70)

            # Switch to Programs page (index 1)
            window.switch_to_page(1)
            print("✓ Switched to Programs page (index 1)")

            # Get the Programs page widget
            programs_page = window.page_stack.widget(1)
            print(f"✓ Programs page type: {type(programs_page).__name__}")
            print(f"  - Module: {type(programs_page).__module__}")

            # Check for Sequential Controller UI elements
            print("\n" + "-"*70)
            print("CHECKING UI ELEMENTS")
            print("-"*70)

            # Common elements in Sequential Controller
            elements_to_check = [
                'action_library',
                'execution_sequence',
                'add_action_btn',
                'remove_action_btn',
                'execute_btn',
                'stop_btn',
                'save_sequence_btn',
                'load_sequence_btn'
            ]

            found_elements = []
            missing_elements = []

            for element_name in elements_to_check:
                if hasattr(programs_page, element_name):
                    found_elements.append(element_name)
                    print(f"  ✓ {element_name}: Found")
                else:
                    missing_elements.append(element_name)
                    print(f"  ✗ {element_name}: NOT FOUND")

            # Check children widgets
            print("\n" + "-"*70)
            print("PAGE CHILD WIDGETS")
            print("-"*70)

            children = programs_page.findChildren(QApplication.instance().__class__.__bases__[0])
            print(f"Total child widgets: {len(programs_page.children())}")

            # Check for specific widget types
            from PyQt5.QtWidgets import QListWidget, QPushButton, QLabel, QGroupBox

            list_widgets = programs_page.findChildren(QListWidget)
            buttons = programs_page.findChildren(QPushButton)
            labels = programs_page.findChildren(QLabel)
            group_boxes = programs_page.findChildren(QGroupBox)

            print(f"  - QListWidget count: {len(list_widgets)}")
            print(f"  - QPushButton count: {len(buttons)}")
            print(f"  - QLabel count: {len(labels)}")
            print(f"  - QGroupBox count: {len(group_boxes)}")

            if len(list_widgets) >= 2:
                print("\n  Expected Sequential Controller UI:")
                print("    ✓ Has multiple list widgets (likely Action Library + Sequence)")
            else:
                print("\n  ⚠ Warning: Expected 2+ list widgets for Sequential Controller")

            if len(buttons) >= 6:
                print("    ✓ Has multiple buttons (likely Add/Remove/Execute/etc)")
                print("\n  Sample buttons found:")
                for i, btn in enumerate(buttons[:8]):
                    print(f"      • {btn.text()}")
            else:
                print("\n  ⚠ Warning: Expected 6+ buttons for Sequential Controller")

            # Summary
            print("\n" + "="*70)
            print("SUMMARY")
            print("="*70)

            if len(found_elements) >= 4:
                print("✓ Programs page appears to have Sequential Controller UI")
            elif len(list_widgets) >= 2 and len(buttons) >= 6:
                print("✓ Programs page has Sequential Controller-like UI structure")
            else:
                print("✗ Programs page may not have Sequential Controller UI")
                print("\n  Possible issues:")
                print("    - SequentialControllerPageWidget not initialized properly")
                print("    - Import error from sequential_controller_ui_page.py")
                print("    - UI elements named differently than expected")

            print("\nKeeping window open for 5 seconds for visual inspection...")
            print("="*70 + "\n")

            # Close after 5 seconds
            QTimer.singleShot(5000, app.quit)

        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            QTimer.singleShot(2000, app.quit)

    # Check after 1 second
    QTimer.singleShot(1000, check_programs_page)

    sys.exit(app.exec_())

if __name__ == "__main__":
    test_programs_page()
