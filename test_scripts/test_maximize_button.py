#!/usr/bin/env python3
"""
Comprehensive test for maximize button presence
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt
from ui_mainwindow import MainWindow

def test_maximize_button():
    """Test maximize button and window properties"""
    app = QApplication(sys.argv)

    # Create main window
    window = MainWindow()
    window.show()

    print("\n" + "="*60)
    print("WINDOW MAXIMIZE BUTTON TEST")
    print("="*60)

    # Check window type
    print(f"\nWindow Type: {type(window).__name__}")
    print(f"Is QMainWindow: {isinstance(window, MainWindow)}")

    # Check window flags
    flags = window.windowFlags()
    print(f"\nWindow Flags: {hex(int(flags))}")

    # Check size constraints
    min_size = window.minimumSize()
    max_size = window.maximumSize()
    current_size = window.size()

    print(f"\nSize Information:")
    print(f"  Minimum Size: {min_size.width()} x {min_size.height()}")
    print(f"  Maximum Size: {max_size.width()} x {max_size.height()}")
    print(f"  Current Size: {current_size.width()} x {current_size.height()}")

    # Check if window can be maximized
    can_maximize = max_size.width() >= 16000000 and max_size.height() >= 16000000
    print(f"  Can Maximize: {can_maximize}")

    # Check size policy
    policy = window.sizePolicy()
    print(f"\nSize Policy:")
    print(f"  Horizontal: {policy.horizontalPolicy()}")
    print(f"  Vertical: {policy.verticalPolicy()}")

    # Try to check window state
    print(f"\nWindow State: {window.windowState()}")
    print(f"Is Maximized: {window.isMaximized()}")

    print("\n" + "="*60)
    print("EXPECTED: You should see _ □ X buttons in title bar")
    print("="*60)

    print("\nKeeping window open for 3 seconds...")
    print("Please visually check if maximize button (□) appears\n")

    # Auto-close after 3 seconds
    QTimer.singleShot(3000, app.quit)

    sys.exit(app.exec_())

if __name__ == "__main__":
    test_maximize_button()
