#!/usr/bin/env python3
"""
Test if window can actually maximize (functional test)
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt
from ui_mainwindow import MainWindow

def test_maximize_functionality():
    """Test if window can be maximized programmatically"""
    app = QApplication(sys.argv)

    # Create and show window
    window = MainWindow()
    window.show()

    print("\n" + "="*70)
    print("MAXIMIZE FUNCTIONALITY TEST")
    print("="*70)

    # Get initial state
    initial_size = window.size()
    print(f"\nInitial window size: {initial_size.width()} x {initial_size.height()}")
    print(f"Initial maximized state: {window.isMaximized()}")

    # Try to maximize after 1 second
    def do_maximize():
        print("\n" + "-"*70)
        print("ATTEMPTING TO MAXIMIZE WINDOW...")
        print("-"*70)
        window.showMaximized()

        # Check state after maximizing
        QTimer.singleShot(500, check_maximized)

    def check_maximized():
        maximized_size = window.size()
        print(f"\nAfter showMaximized():")
        print(f"  Window size: {maximized_size.width()} x {maximized_size.height()}")
        print(f"  Is maximized: {window.isMaximized()}")
        print(f"  Window state: {window.windowState()}")

        if window.isMaximized():
            print("\n✓✓✓ SUCCESS: Window CAN be maximized! ✓✓✓")
            print("\nThis proves the maximize button SHOULD be visible.")
            print("If you don't see it, it's a window manager display issue.")
        else:
            print("\n✗✗✗ FAILED: Window did not maximize ✗✗✗")

        # Restore normal size
        QTimer.singleShot(1500, restore_normal)

    def restore_normal():
        print("\n" + "-"*70)
        print("RESTORING TO NORMAL SIZE...")
        print("-"*70)
        window.showNormal()
        print(f"Window size: {window.size().width()} x {window.size().height()}")
        print(f"Is maximized: {window.isMaximized()}")

        print("\n" + "="*70)
        print("Test complete. Window will close in 2 seconds.")
        print("="*70)

        QTimer.singleShot(2000, app.quit)

    # Start the test sequence
    QTimer.singleShot(1000, do_maximize)

    sys.exit(app.exec_())

if __name__ == "__main__":
    test_maximize_functionality()
