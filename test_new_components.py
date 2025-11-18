#!/usr/bin/env python3
"""
Test script for new UI components

Tests that all new components can be imported and instantiated correctly.
"""

import sys
from PyQt5.QtWidgets import QApplication

def test_guidance_bar():
    """Test GuidanceBar component"""
    print("Testing GuidanceBar...")
    from guidance_bar import GuidanceBar

    bar = GuidanceBar()

    # Test context updates
    bar.update_context("empty_sequence")
    print("  ✓ empty_sequence context works")

    bar.update_context("has_actions", 5)
    print("  ✓ has_actions context works")

    bar.update_context("ready_to_execute")
    print("  ✓ ready_to_execute context works")

    bar.update_context("executing")
    print("  ✓ executing context works")

    bar.update_context("paused")
    print("  ✓ paused context works")

    bar.update_context("completed")
    print("  ✓ completed context works")

    bar.update_context("error")
    print("  ✓ error context works")

    print("✅ GuidanceBar tests passed!\n")
    return True

def test_execution_status_bar():
    """Test ExecutionStatusBar component"""
    print("Testing ExecutionStatusBar...")
    from execution_status_bar import ExecutionStatusBar

    bar = ExecutionStatusBar()

    # Test state updates
    bar.set_state("idle")
    print("  ✓ idle state works")

    bar.set_state("running", 1, 10, "Test Action")
    print("  ✓ running state works")

    bar.set_state("paused")
    print("  ✓ paused state works")

    bar.set_state("stopped")
    print("  ✓ stopped state works")

    bar.set_state("completed", 10, 10)
    print("  ✓ completed state works")

    bar.set_state("error")
    print("  ✓ error state works")

    # Test execution enabled/disabled
    bar.set_execution_enabled(True)
    print("  ✓ set_execution_enabled(True) works")

    bar.set_execution_enabled(False)
    print("  ✓ set_execution_enabled(False) works")

    print("✅ ExecutionStatusBar tests passed!\n")
    return True

def test_search_integration():
    """Test search functionality in CategorizedActionLibrary"""
    print("Testing CategorizedActionLibrary search...")
    from categorized_action_library_improved import CategorizedActionLibrary

    library = CategorizedActionLibrary()

    # Verify search input exists
    assert hasattr(library, 'search_input'), "search_input not found"
    print("  ✓ search_input widget exists")

    # Verify all_action_cards list exists
    assert hasattr(library, 'all_action_cards'), "all_action_cards not found"
    print("  ✓ all_action_cards list exists")

    # Verify cards were populated
    assert len(library.all_action_cards) > 0, "No action cards were created"
    print(f"  ✓ {len(library.all_action_cards)} action cards created")

    # Test search filtering (simulate typing)
    library.on_search_text_changed("move")
    print("  ✓ search filtering works for 'move'")

    library.on_search_text_changed("")
    print("  ✓ clearing search works")

    library.on_search_text_changed("gripper")
    print("  ✓ search filtering works for 'gripper'")

    print("✅ CategorizedActionLibrary search tests passed!\n")
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("UI Component Integration Tests")
    print("=" * 60 + "\n")

    # Create QApplication (required for Qt widgets)
    app = QApplication(sys.argv)

    try:
        # Run tests
        all_passed = True
        all_passed &= test_guidance_bar()
        all_passed &= test_execution_status_bar()
        all_passed &= test_search_integration()

        if all_passed:
            print("=" * 60)
            print("🎉 ALL TESTS PASSED!")
            print("=" * 60)
            return 0
        else:
            print("=" * 60)
            print("❌ SOME TESTS FAILED")
            print("=" * 60)
            return 1

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
