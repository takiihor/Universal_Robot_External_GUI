#!/usr/bin/env python3
"""
Detailed window flags test
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt
from ui_mainwindow import MainWindow

def test_window_flags_detailed():
    """Test window flags in detail"""
    app = QApplication(sys.argv)

    # Create main window
    window = MainWindow()

    print("\n" + "="*70)
    print("DETAILED WINDOW FLAGS ANALYSIS")
    print("="*70)

    flags = window.windowFlags()

    # Test individual flags
    print("\nWindow Button Flags:")
    print(f"  WindowMinimizeButtonHint: {bool(flags & Qt.WindowMinimizeButtonHint)}")
    print(f"  WindowMaximizeButtonHint: {bool(flags & Qt.WindowMaximizeButtonHint)}")
    print(f"  WindowCloseButtonHint: {bool(flags & Qt.WindowCloseButtonHint)}")

    print("\nWindow Type Flags:")
    print(f"  Window: {bool(flags & Qt.Window)}")
    print(f"  Dialog: {bool(flags & Qt.Dialog)}")
    print(f"  WindowTitleHint: {bool(flags & Qt.WindowTitleHint)}")
    print(f"  WindowSystemMenuHint: {bool(flags & Qt.WindowSystemMenuHint)}")

    print("\n" + "="*70)
    print("NOW ADDING WindowMaximizeButtonHint EXPLICITLY")
    print("="*70)

    # Try to add the maximize button hint
    window.setWindowFlags(window.windowFlags() | Qt.WindowMaximizeButtonHint)

    # Must show after setWindowFlags
    window.show()

    # Check flags again
    flags_after = window.windowFlags()
    print("\nWindow Button Flags (AFTER):")
    print(f"  WindowMinimizeButtonHint: {bool(flags_after & Qt.WindowMinimizeButtonHint)}")
    print(f"  WindowMaximizeButtonHint: {bool(flags_after & Qt.WindowMaximizeButtonHint)}")
    print(f"  WindowCloseButtonHint: {bool(flags_after & Qt.WindowCloseButtonHint)}")

    print("\n" + "="*70)
    print("Please visually check if maximize button (□) now appears")
    print("="*70)
    print("\nKeeping window open for 5 seconds...\n")

    # Auto-close after 5 seconds
    QTimer.singleShot(5000, app.quit)

    sys.exit(app.exec_())

if __name__ == "__main__":
    test_window_flags_detailed()
