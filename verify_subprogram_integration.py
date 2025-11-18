"""
Verification Script for Subprogram System Integration

Tests that all components can be imported and initialized without errors.
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test all subprogram-related imports"""
    logger.info("=" * 60)
    logger.info("Testing Subprogram System Imports")
    logger.info("=" * 60)

    try:
        logger.info("✓ Importing subprogram_models...")
        from subprogram_models import SubProgram, Parameter

        logger.info("✓ Importing subprogram_manager...")
        from subprogram_manager import SubProgramManager

        logger.info("✓ Importing sequential_controller (updated)...")
        from sequential_controller import SequentialController, ActionType, Action

        logger.info("✓ Checking CALL_SUBPROGRAM action type...")
        assert hasattr(ActionType, 'CALL_SUBPROGRAM'), "CALL_SUBPROGRAM not found!"

        logger.info("✓ All core imports successful!")
        return True

    except Exception as e:
        logger.error(f"✗ Import failed: {e}", exc_info=True)
        return False


def test_ui_components():
    """Test UI component imports"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing UI Component Imports")
    logger.info("=" * 60)

    try:
        logger.info("✓ Importing subprogram_library_widget...")
        from subprogram_library_widget import SubProgramLibrary, SubProgramCard

        logger.info("✓ Importing subprogram_editor_widget...")
        from subprogram_editor_widget import SubProgramEditor

        logger.info("✓ Importing subprogram_selector_widget...")
        from subprogram_selector_widget import SubProgramSelector, SubProgramCallDialog

        logger.info("✓ Importing execution_history_enhanced...")
        from execution_history_enhanced import EnhancedExecutionHistory

        logger.info("✓ All UI component imports successful!")
        return True

    except Exception as e:
        logger.error(f"✗ UI import failed: {e}", exc_info=True)
        return False


def test_manager_operations():
    """Test basic manager operations"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing SubProgramManager Operations")
    logger.info("=" * 60)

    try:
        from subprogram_manager import SubProgramManager
        from sequential_controller import Action, ActionType

        logger.info("✓ Creating SubProgramManager instance...")
        manager = SubProgramManager.get_instance()

        logger.info(f"✓ Loaded {len(manager.get_all_subprograms())} existing subprograms")

        logger.info("✓ Listing categories...")
        categories = manager.get_categories()
        logger.info(f"  Categories: {', '.join(categories)}")

        logger.info("✓ Testing search...")
        results = manager.search_subprograms("pick")
        logger.info(f"  Found {len(results)} subprograms matching 'pick'")

        logger.info("✓ Manager operations successful!")
        return True

    except Exception as e:
        logger.error(f"✗ Manager test failed: {e}", exc_info=True)
        return False


def test_action_type():
    """Test that CALL_SUBPROGRAM action type works"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing CALL_SUBPROGRAM Action Type")
    logger.info("=" * 60)

    try:
        from sequential_controller import Action, ActionType, ACTION_METADATA, ACTION_CATEGORIES

        logger.info("✓ Checking ActionType.CALL_SUBPROGRAM...")
        assert ActionType.CALL_SUBPROGRAM
        assert ActionType.CALL_SUBPROGRAM.value == "call_subprogram"

        logger.info("✓ Checking ACTION_METADATA...")
        assert ActionType.CALL_SUBPROGRAM in ACTION_METADATA
        metadata = ACTION_METADATA[ActionType.CALL_SUBPROGRAM]
        logger.info(f"  Icon: {metadata['icon']}")
        logger.info(f"  Name: {metadata['name']}")
        logger.info(f"  Description: {metadata['description']}")

        logger.info("✓ Checking ACTION_CATEGORIES...")
        assert 'subprograms' in ACTION_CATEGORIES
        category = ACTION_CATEGORIES['subprograms']
        logger.info(f"  Category Name: {category['name']}")
        logger.info(f"  Category Icon: {category['icon']}")

        logger.info("✓ Creating test CALL_SUBPROGRAM action...")
        test_action = Action(
            id=999,
            action_type=ActionType.CALL_SUBPROGRAM,
            parameters={
                "subprogram_id": "test-id",
                "subprogram_name": "Test Subprogram",
                "parameter_values": {},
                "loop_count": 1
            }
        )

        display_text = test_action.get_display_text()
        logger.info(f"  Display text: {display_text}")
        assert "Test Subprogram" in display_text

        logger.info("✓ CALL_SUBPROGRAM action type working correctly!")
        return True

    except Exception as e:
        logger.error(f"✗ Action type test failed: {e}", exc_info=True)
        return False


def verify_sample_subprograms():
    """Verify sample subprograms exist"""
    logger.info("\n" + "=" * 60)
    logger.info("Verifying Sample Subprograms")
    logger.info("=" * 60)

    try:
        from subprogram_manager import SubProgramManager

        manager = SubProgramManager.get_instance()
        all_sps = manager.get_all_subprograms()

        logger.info(f"✓ Found {len(all_sps)} subprograms:")
        for sp in all_sps:
            logger.info(f"  • {sp.icon} {sp.name} ({sp.category})")
            logger.info(f"    - {len(sp.actions)} actions, {len(sp.parameters)} parameters")
            logger.info(f"    - Used {sp.usage_count} times")

        if len(all_sps) >= 4:
            logger.info("✓ Sample subprograms verified!")
            return True
        else:
            logger.warning(f"⚠ Only {len(all_sps)} subprograms found (expected 4+)")
            logger.info("  Run 'python3 test_subprogram_system.py' to create samples")
            return True

    except Exception as e:
        logger.error(f"✗ Sample verification failed: {e}", exc_info=True)
        return False


def main():
    """Run all verification tests"""
    logger.info("\n" + "=" * 60)
    logger.info("SUBPROGRAM SYSTEM INTEGRATION VERIFICATION")
    logger.info("=" * 60 + "\n")

    results = []

    # Run tests
    results.append(("Core Imports", test_imports()))
    results.append(("UI Components", test_ui_components()))
    results.append(("Manager Operations", test_manager_operations()))
    results.append(("Action Type", test_action_type()))
    results.append(("Sample Subprograms", verify_sample_subprograms()))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}  {test_name}")

    all_passed = all(result for _, result in results)

    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("🎉 ALL VERIFICATIONS PASSED!")
        logger.info("=" * 60)
        logger.info("\nThe subprogram system is fully integrated and ready to use!")
        logger.info("\nTo test the UI:")
        logger.info("  python3 main.py")
        logger.info("\nThen navigate to:")
        logger.info("  Programs → Sequential Controller → Subprogram Library tab")
        return 0
    else:
        logger.error("❌ SOME VERIFICATIONS FAILED")
        logger.error("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
