#!/usr/bin/env python3
"""
Test Force Mode page scroll area functionality
"""

import sys
from PyQt5.QtWidgets import QApplication, QScrollArea
from PyQt5.QtCore import QTimer
from ui_mainwindow import MainWindow

def test_force_mode_scroll():
    """Test if Force Mode page has proper scroll area"""
    app = QApplication(sys.argv)

    # Create window
    window = MainWindow()
    window.show()

    print("\n" + "="*70)
    print("FORCE MODE PAGE SCROLL AREA TEST")
    print("="*70)

    # Switch to Force Mode page (page index 3)
    window.switch_to_page(3)
    print("\n✓ Switched to Force Mode page")

    # Get the Force Mode page
    force_mode_page = window.page_stack.widget(3)
    print(f"✓ Force Mode page type: {type(force_mode_page).__name__}")

    # Check if page has scroll area
    has_scroll = False
    for child in force_mode_page.findChildren(QScrollArea):
        has_scroll = True
        print(f"✓ Found QScrollArea in Force Mode page")
        print(f"  - Widget resizable: {child.widgetResizable()}")
        print(f"  - Horizontal scrollbar policy: {child.horizontalScrollBarPolicy()}")

        # Check content widget
        content_widget = child.widget()
        if content_widget:
            print(f"  - Content widget: {type(content_widget).__name__}")
            print(f"  - Content height: {content_widget.sizeHint().height()}px")

    if has_scroll:
        print("\n✓✓✓ SUCCESS: Force Mode page has scroll area! ✓✓✓")
        print("\nAll controls should now be accessible even on smaller windows.")
    else:
        print("\n✗✗✗ FAILED: No scroll area found! ✗✗✗")

    # Visual check info
    print("\n" + "="*70)
    print("VISUAL CHECK")
    print("="*70)
    print("Please verify:")
    print("1. Force Mode page is displayed")
    print("2. Left side has Force controls, Force display, and Data Recording")
    print("3. You can scroll the left side if window is short")
    print("4. Right side shows Force chart")
    print("\nWindow will close in 5 seconds...")
    print("="*70 + "\n")

    # Auto-close after 5 seconds
    QTimer.singleShot(5000, app.quit)

    sys.exit(app.exec_())

if __name__ == "__main__":
    test_force_mode_scroll()
