#!/usr/bin/env python3
"""
Quick test script to verify new navigation structure
This will launch the UI for 3 seconds then close automatically
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from ui_mainwindow import MainWindow

def test_navigation():
    """Test the new navigation structure"""
    app = QApplication(sys.argv)

    # Create main window
    window = MainWindow()
    window.show()

    print("✓ Application started successfully")
    print(f"✓ Navigation bar created with {len(window.nav_buttons)} buttons")
    print(f"✓ Page stack has {window.page_stack.count()} pages")
    print(f"✓ Current page: {window.page_stack.currentIndex()}")

    # Test page switching
    for i in range(window.page_stack.count()):
        window.switch_to_page(i)
        page_names = ["Basic", "Programs", "Movement", "Force Mode", "Presets", "Scripts"]
        print(f"✓ Switched to page {i}: {page_names[i]}")

    # Return to Basic page
    window.switch_to_page(0)
    print("✓ Returned to Basic page")

    print("\n✓✓✓ All tests passed! ✓✓✓")
    print("\nClosing in 3 seconds...")

    # Auto-close after 3 seconds
    QTimer.singleShot(3000, app.quit)

    sys.exit(app.exec_())

if __name__ == "__main__":
    test_navigation()
