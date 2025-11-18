#!/usr/bin/env python3
"""
Quick integration test to verify UI components are properly integrated
"""

import sys
from PyQt5.QtWidgets import QApplication

def test_ui_integration():
    """Test that all UI components integrate correctly"""
    print("Testing UI integration...")

    try:
        # Test imports
        print("  ✓ Importing GuidanceBar...")
        from guidance_bar import GuidanceBar

        print("  ✓ Importing ExecutionStatusBar...")
        from execution_status_bar import ExecutionStatusBar

        print("  ✓ Importing CategorizedActionLibrary...")
        from categorized_action_library_improved import CategorizedActionLibrary

        print("  ✓ Importing SequentialControllerPageWidget...")
        from sequential_controller_ui_page import SequentialControllerPageWidget

        print("  ✓ Importing SequentialController...")
        from sequential_controller import SequentialController

        print("  ✓ Importing RobotController...")
        from robot_controller import RobotController

        # Create test instances
        print("\n  ✓ Creating RobotController...")
        robot = RobotController()

        print("  ✓ Creating SequentialController...")
        seq_controller = SequentialController(robot)

        print("  ✓ Creating SequentialControllerPageWidget...")
        page = SequentialControllerPageWidget(seq_controller)

        # Verify new components are present
        print("\n  ✓ Verifying GuidanceBar is present...")
        assert hasattr(page, 'guidance_bar'), "GuidanceBar not found in page widget"
        assert page.guidance_bar is not None, "GuidanceBar is None"

        print("  ✓ Verifying ExecutionStatusBar is present...")
        assert hasattr(page, 'execution_status_bar'), "ExecutionStatusBar not found in page widget"
        assert page.execution_status_bar is not None, "ExecutionStatusBar is None"

        print("  ✓ Verifying CategorizedActionLibrary has search...")
        assert hasattr(page.action_library, 'search_input'), "Search input not found in action library"
        assert hasattr(page.action_library, 'all_action_cards'), "all_action_cards not found"

        print("\n✅ All integration tests passed!")
        print("The UI is ready to use with the following improvements:")
        print("  • Context-aware guidance bar")
        print("  • Unified execution status bar")
        print("  • Search functionality in action library")
        return True

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    success = test_ui_integration()
    sys.exit(0 if success else 1)
