#!/usr/bin/env python3
"""
Test script to verify window buttons (minimize, maximize, close) are present
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt
from ui_mainwindow import MainWindow

def test_window_buttons():
    """Test window buttons presence"""
    app = QApplication(sys.argv)

    # Create main window
    window = MainWindow()
    window.show()

    # Check window flags
    flags = window.windowFlags()

    print("Window Button Check:")
    print("=" * 50)

    has_minimize = bool(flags & Qt.WindowMinimizeButtonHint)
    has_maximize = bool(flags & Qt.WindowMaximizeButtonHint)
    has_close = bool(flags & Qt.WindowCloseButtonHint)

    print(f"✓ Minimize button (_):  {'PRESENT' if has_minimize else 'MISSING'}")
    print(f"✓ Maximize button (□):  {'PRESENT' if has_maximize else 'MISSING'}")
    print(f"✓ Close button (X):     {'PRESENT' if has_close else 'MISSING'}")
    print("=" * 50)

    if has_minimize and has_maximize and has_close:
        print("\n✓✓✓ All window buttons are present! ✓✓✓")
    else:
        print("\n⚠ WARNING: Some window buttons are missing!")

    print("\nWindow will close in 2 seconds...")
    print("You should see: _ □ X buttons in the title bar")

    # Auto-close after 2 seconds
    QTimer.singleShot(2000, app.quit)

    sys.exit(app.exec_())

if __name__ == "__main__":
    test_window_buttons()
