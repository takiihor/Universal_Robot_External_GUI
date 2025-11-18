"""
Subprogram System Test and Demo

Creates sample subprograms and demonstrates the subprogram functionality.
"""

import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from subprogram_manager import SubProgramManager
from subprogram_models import SubProgram, Parameter
from sequential_controller import Action, ActionType


def create_sample_subprograms():
    """Create sample subprograms for testing"""
    manager = SubProgramManager.get_instance()

    logger.info("Creating sample subprograms...")

    # 1. Pick Part Subprogram
    pick_actions = [
        Action(
            id=1,
            action_type=ActionType.MOVE_TO_POSITION,
            parameters={
                "position_name": "above_part",
                "tcp_pose": [0.3, 0.2, 0.3, 0, 3.14, 0],
                "speed_percent": 50,
                "move_type": "moveJ"
            }
        ),
        Action(
            id=2,
            action_type=ActionType.MOVE_TO_POSITION,
            parameters={
                "position_name": "pick_position",
                "tcp_pose": [0.3, 0.2, 0.1, 0, 3.14, 0],
                "speed_percent": 30,
                "move_type": "moveL"
            }
        ),
        Action(
            id=3,
            action_type=ActionType.GRIPPER_CLOSE,
            parameters={}
        ),
        Action(
            id=4,
            action_type=ActionType.WAIT,
            parameters={"seconds": 0.5}
        ),
        Action(
            id=5,
            action_type=ActionType.MOVE_TO_POSITION,
            parameters={
                "position_name": "above_part",
                "tcp_pose": [0.3, 0.2, 0.3, 0, 3.14, 0],
                "speed_percent": 50,
                "move_type": "moveL"
            }
        )
    ]

    pick_subprogram = manager.create_subprogram(
        name="Pick Part",
        actions=pick_actions,
        description="Pick up a part from the table using gripper",
        icon="🤏",
        category="Pick & Place"
    )
    logger.info(f"✅ Created: {pick_subprogram.name}")

    # 2. Place Part Subprogram
    place_actions = [
        Action(
            id=1,
            action_type=ActionType.MOVE_TO_POSITION,
            parameters={
                "position_name": "above_drop",
                "tcp_pose": [0.5, -0.2, 0.3, 0, 3.14, 0],
                "speed_percent": 50,
                "move_type": "moveJ"
            }
        ),
        Action(
            id=2,
            action_type=ActionType.MOVE_TO_POSITION,
            parameters={
                "position_name": "drop_position",
                "tcp_pose": [0.5, -0.2, 0.15, 0, 3.14, 0],
                "speed_percent": 30,
                "move_type": "moveL"
            }
        ),
        Action(
            id=3,
            action_type=ActionType.GRIPPER_OPEN,
            parameters={}
        ),
        Action(
            id=4,
            action_type=ActionType.WAIT,
            parameters={"seconds": 0.5}
        ),
        Action(
            id=5,
            action_type=ActionType.MOVE_TO_POSITION,
            parameters={
                "position_name": "above_drop",
                "tcp_pose": [0.5, -0.2, 0.3, 0, 3.14, 0],
                "speed_percent": 50,
                "move_type": "moveL"
            }
        )
    ]

    place_subprogram = manager.create_subprogram(
        name="Place Part",
        actions=place_actions,
        description="Place part at drop-off location and release gripper",
        icon="📍",
        category="Pick & Place"
    )
    logger.info(f"✅ Created: {place_subprogram.name}")

    # 3. Quality Inspection Subprogram
    inspect_actions = [
        Action(
            id=1,
            action_type=ActionType.MOVE_TO_POSITION,
            parameters={
                "position_name": "inspection_view",
                "tcp_pose": [0.4, 0, 0.4, 0, 3.14, 0],
                "speed_percent": 40,
                "move_type": "moveJ"
            }
        ),
        Action(
            id=2,
            action_type=ActionType.WAIT,
            parameters={"seconds": 2.0}  # Simulate camera capture
        ),
        Action(
            id=3,
            action_type=ActionType.SET_DIGITAL_OUTPUT,
            parameters={"pin": 0, "state": "high"}  # Trigger indicator
        ),
        Action(
            id=4,
            action_type=ActionType.WAIT,
            parameters={"seconds": 0.5}
        ),
        Action(
            id=5,
            action_type=ActionType.SET_DIGITAL_OUTPUT,
            parameters={"pin": 0, "state": "low"}
        )
    ]

    inspect_subprogram = manager.create_subprogram(
        name="Quality Inspection",
        actions=inspect_actions,
        description="Move to inspection position and perform visual check",
        icon="🔍",
        category="Inspection"
    )
    logger.info(f"✅ Created: {inspect_subprogram.name}")

    # 4. Lock Screw Subprogram (for assembly)
    screw_actions = [
        Action(
            id=1,
            action_type=ActionType.MOVE_TO_POSITION,
            parameters={
                "position_name": "screw_approach",
                "tcp_pose": [0.35, 0.15, 0.25, 0, 3.14, 0],
                "speed_percent": 40,
                "move_type": "moveJ"
            }
        ),
        Action(
            id=2,
            action_type=ActionType.MOVE_TO_POSITION,
            parameters={
                "position_name": "screw_contact",
                "tcp_pose": [0.35, 0.15, 0.12, 0, 3.14, 0],
                "speed_percent": 20,
                "move_type": "moveL"
            }
        ),
        Action(
            id=3,
            action_type=ActionType.ENABLE_FORCE,
            parameters={"force_level": "gentle"}
        ),
        Action(
            id=4,
            action_type=ActionType.WAIT,
            parameters={"seconds": 1.5}  # Simulate screwing
        ),
        Action(
            id=5,
            action_type=ActionType.DISABLE_FORCE,
            parameters={}
        ),
        Action(
            id=6,
            action_type=ActionType.MOVE_TO_POSITION,
            parameters={
                "position_name": "screw_retract",
                "tcp_pose": [0.35, 0.15, 0.25, 0, 3.14, 0],
                "speed_percent": 40,
                "move_type": "moveL"
            }
        )
    ]

    screw_subprogram = manager.create_subprogram(
        name="Lock Screw",
        actions=screw_actions,
        description="Approach, engage, and tighten a screw with force control",
        icon="🔧",
        category="Assembly"
    )
    logger.info(f"✅ Created: {screw_subprogram.name}")

    logger.info(f"\n📦 Total subprograms created: {len(manager.get_all_subprograms())}")

    return manager


def test_subprogram_operations():
    """Test subprogram CRUD operations"""
    logger.info("\n" + "="*60)
    logger.info("Testing Subprogram Operations")
    logger.info("="*60)

    manager = SubProgramManager.get_instance()

    # Test: List all subprograms
    logger.info("\n📚 All Subprograms:")
    for sp in manager.get_all_subprograms():
        logger.info(f"  • {sp.icon} {sp.name} - {sp.category} ({len(sp.actions)} actions)")

    # Test: Get by category
    logger.info("\n🤏 Pick & Place Subprograms:")
    pick_place = manager.get_by_category("Pick & Place")
    for sp in pick_place:
        logger.info(f"  • {sp.name}")

    # Test: Search
    logger.info("\n🔍 Search results for 'pick':")
    results = manager.search_subprograms("pick")
    for sp in results:
        logger.info(f"  • {sp.name}")

    # Test: Parameter extraction
    logger.info("\n⚙️ Testing parameter extraction:")
    test_subprogram = manager.get_all_subprograms()[0]
    params = manager.extract_parameters(test_subprogram.actions)
    logger.info(f"  Extracted {len(params)} parameters from '{test_subprogram.name}':")
    for param in params[:3]:  # Show first 3
        logger.info(f"    - {param.name} ({param.type}): {param.description}")

    # Test: Instantiation
    logger.info("\n🔨 Testing subprogram instantiation:")
    if test_subprogram:
        instantiated = manager.instantiate_subprogram(test_subprogram.id, {})
        logger.info(f"  Instantiated '{test_subprogram.name}' with {len(instantiated)} actions")

    logger.info("\n✅ All operations completed successfully!")


def demonstrate_usage():
    """Demonstrate how subprograms would be used"""
    logger.info("\n" + "="*60)
    logger.info("Demonstrating Subprogram Usage")
    logger.info("="*60)

    manager = SubProgramManager.get_instance()

    logger.info("\n💡 Example: Pick and Place Workflow")
    logger.info("-" * 40)
    logger.info("Main Program Steps:")
    logger.info("  1. Return Home")
    logger.info("  2. 📦 Call: Pick Part()")
    logger.info("  3. 📦 Call: Quality Inspection()")
    logger.info("  4. 📦 Call: Place Part()")
    logger.info("  5. Return Home")

    logger.info("\n💡 Example: Assembly Workflow with Loops")
    logger.info("-" * 40)
    logger.info("Main Program Steps:")
    logger.info("  1. Return Home")
    logger.info("  2. 📦 Call: Pick Part()")
    logger.info("  3. REPEAT 4 times:")
    logger.info("     📦 Call: Lock Screw()")
    logger.info("  4. 📦 Call: Quality Inspection()")
    logger.info("  5. 📦 Call: Place Part()")

    logger.info("\n🎯 Benefits:")
    logger.info("  ✓ Modular: Each operation is self-contained")
    logger.info("  ✓ Reusable: Same subprogram used in multiple workflows")
    logger.info("  ✓ Maintainable: Update once, applies everywhere")
    logger.info("  ✓ Scalable: Easy to build complex workflows")


def print_summary():
    """Print system summary"""
    logger.info("\n" + "="*60)
    logger.info("Subprogram System Summary")
    logger.info("="*60)

    manager = SubProgramManager.get_instance()
    all_sps = manager.get_all_subprograms()

    logger.info(f"\n📊 Statistics:")
    logger.info(f"  Total Subprograms: {len(all_sps)}")
    logger.info(f"  Categories: {len(manager.get_categories())}")

    total_actions = sum(len(sp.actions) for sp in all_sps)
    logger.info(f"  Total Actions Defined: {total_actions}")

    logger.info(f"\n📁 Storage Location:")
    logger.info(f"  {manager.storage_dir}")

    logger.info(f"\n🏷️ Categories:")
    for category in manager.get_categories():
        count = len(manager.get_by_category(category))
        logger.info(f"  • {category}: {count} subprograms")

    logger.info("\n" + "="*60)
    logger.info("✅ Subprogram System Ready!")
    logger.info("="*60)


def main():
    """Main test function"""
    logger.info("="*60)
    logger.info("SUBPROGRAM SYSTEM TEST & DEMO")
    logger.info("="*60)

    try:
        # Create sample subprograms
        manager = create_sample_subprograms()

        # Test operations
        test_subprogram_operations()

        # Demonstrate usage
        demonstrate_usage()

        # Print summary
        print_summary()

        logger.info("\n🎉 All tests completed successfully!")
        logger.info("\nYou can now:")
        logger.info("  1. Launch the main application")
        logger.info("  2. Go to 'Subprogram Library' tab")
        logger.info("  3. See the sample subprograms")
        logger.info("  4. Use them in your sequences!")

    except Exception as e:
        logger.error(f"❌ Error during testing: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
