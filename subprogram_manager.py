"""
Subprogram Manager

Manages the creation, storage, and retrieval of subprograms.
Provides CRUD operations and handles JSON persistence.
"""

import json
import logging
import copy
from pathlib import Path
from typing import Dict, List, Optional, Any
from PyQt5.QtCore import QObject, pyqtSignal

from subprogram_models import SubProgram, Parameter
from sequential_controller import Action, ActionType

logger = logging.getLogger(__name__)


class SubProgramManager(QObject):
    """
    Subprogram Manager

    Manages the lifecycle of subprograms including creation, modification,
    deletion, and persistence to disk.
    """

    # Signals
    subprogram_added = pyqtSignal(SubProgram)       # Emitted when a subprogram is added
    subprogram_updated = pyqtSignal(SubProgram)     # Emitted when a subprogram is modified
    subprogram_deleted = pyqtSignal(str)            # Emitted when a subprogram is deleted (id)
    subprograms_loaded = pyqtSignal()               # Emitted when subprograms are loaded from disk

    # Singleton instance
    _instance = None

    @classmethod
    def get_instance(cls) -> 'SubProgramManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, storage_dir: str = None):
        super().__init__()
        self.subprograms: Dict[str, SubProgram] = {}  # id -> SubProgram

        # Set up storage directory
        if storage_dir is None:
            storage_dir = Path.home() / ".ur10e_control" / "subprograms"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"SubProgramManager initialized with storage: {self.storage_dir}")

        # Load existing subprograms
        self.load_all_subprograms()

    # ========================================
    # CRUD Operations
    # ========================================

    def create_subprogram(self, name: str, actions: List[Action],
                         description: str = "", icon: str = "📦",
                         category: str = "Other") -> SubProgram:
        """
        Create a new subprogram

        Args:
            name: Subprogram name
            actions: List of actions
            description: Optional description
            icon: Display icon
            category: Category for organization

        Returns:
            Created SubProgram instance
        """
        # Extract parameters from actions
        parameters = self.extract_parameters(actions)

        # Create subprogram
        subprogram = SubProgram(
            id="",  # Will be auto-generated
            name=name,
            description=description,
            icon=icon,
            category=category,
            actions=actions,
            parameters=parameters,
            usage_count=0
        )

        # Store in memory
        self.subprograms[subprogram.id] = subprogram

        # Save to disk
        self.save_subprogram(subprogram)

        # Emit signal
        self.subprogram_added.emit(subprogram)

        logger.info(f"Created subprogram: {name} (id={subprogram.id})")
        return subprogram

    def get_subprogram(self, subprogram_id: str) -> Optional[SubProgram]:
        """Get subprogram by ID"""
        return self.subprograms.get(subprogram_id)

    def get_all_subprograms(self) -> List[SubProgram]:
        """Get all subprograms"""
        return list(self.subprograms.values())

    def get_by_category(self, category: str) -> List[SubProgram]:
        """Get subprograms by category"""
        if category == "常用" or category == "Favorites":
            # Return top used subprograms
            sorted_programs = sorted(
                self.subprograms.values(),
                key=lambda sp: sp.usage_count,
                reverse=True
            )
            return sorted_programs[:10]  # Top 10 most used
        elif category == "全部" or category == "All":
            return self.get_all_subprograms()
        else:
            return [sp for sp in self.subprograms.values() if sp.category == category]

    def update_subprogram(self, subprogram_id: str, **updates) -> bool:
        """
        Update subprogram properties

        Args:
            subprogram_id: ID of subprogram to update
            **updates: Keyword arguments for properties to update

        Returns:
            True if successful, False otherwise
        """
        subprogram = self.subprograms.get(subprogram_id)
        if not subprogram:
            logger.warning(f"Subprogram not found: {subprogram_id}")
            return False

        # Update properties
        for key, value in updates.items():
            if hasattr(subprogram, key):
                setattr(subprogram, key, value)

        # Update modified date
        subprogram.update_modified_date()

        # Save to disk
        self.save_subprogram(subprogram)

        # Emit signal
        self.subprogram_updated.emit(subprogram)

        logger.info(f"Updated subprogram: {subprogram.name}")
        return True

    def delete_subprogram(self, subprogram_id: str) -> bool:
        """
        Delete a subprogram

        Args:
            subprogram_id: ID of subprogram to delete

        Returns:
            True if successful, False otherwise
        """
        subprogram = self.subprograms.get(subprogram_id)
        if not subprogram:
            logger.warning(f"Subprogram not found: {subprogram_id}")
            return False

        # Remove from memory
        del self.subprograms[subprogram_id]

        # Delete file
        filepath = self.storage_dir / f"{subprogram_id}.json"
        try:
            if filepath.exists():
                filepath.unlink()
                logger.info(f"Deleted subprogram file: {filepath}")
        except Exception as e:
            logger.error(f"Failed to delete subprogram file: {e}")
            return False

        # Emit signal
        self.subprogram_deleted.emit(subprogram_id)

        logger.info(f"Deleted subprogram: {subprogram.name}")
        return True

    # ========================================
    # Parameter Extraction
    # ========================================

    def extract_parameters(self, actions: List[Action]) -> List[Parameter]:
        """
        Extract parameterizable values from action sequence

        Analyzes the actions and identifies values that could be parameterized
        (e.g., positions, speeds, wait durations).

        Args:
            actions: List of actions to analyze

        Returns:
            List of suggested parameters
        """
        parameters = []

        for i, action in enumerate(actions):
            # Identify parameterizable values based on action type
            if action.action_type == ActionType.MOVE_TO_POSITION:
                # Position can be parameterized
                if "tcp_pose" in action.parameters:
                    param = Parameter(
                        name=f"position_{i+1}",
                        type="position",
                        default_value=action.parameters.get("tcp_pose"),
                        required=False,
                        description=f"Target position for step {i+1}",
                        action_binding={
                            "action_index": i,
                            "parameter_key": "tcp_pose"
                        }
                    )
                    parameters.append(param)

                # Speed can be parameterized
                if "speed_percent" in action.parameters:
                    param = Parameter(
                        name=f"speed_{i+1}",
                        type="number",
                        default_value=action.parameters.get("speed_percent", 50),
                        required=False,
                        description=f"Movement speed for step {i+1} (%)",
                        constraints={"min": 1, "max": 100},
                        action_binding={
                            "action_index": i,
                            "parameter_key": "speed_percent"
                        }
                    )
                    parameters.append(param)

            elif action.action_type == ActionType.WAIT:
                # Wait time can be parameterized
                param = Parameter(
                    name=f"wait_time_{i+1}",
                    type="number",
                    default_value=action.parameters.get("seconds", 1.0),
                    required=False,
                    description=f"Wait duration for step {i+1} (seconds)",
                    constraints={"min": 0.1, "max": 60.0},
                    action_binding={
                        "action_index": i,
                        "parameter_key": "seconds"
                    }
                )
                parameters.append(param)

            elif action.action_type == ActionType.REPEAT_START:
                # Repeat count can be parameterized
                param = Parameter(
                    name=f"repeat_count_{i+1}",
                    type="number",
                    default_value=action.parameters.get("repeat_count", 1),
                    required=False,
                    description=f"Number of repetitions for loop at step {i+1}",
                    constraints={"min": 1, "max": 1000},
                    action_binding={
                        "action_index": i,
                        "parameter_key": "repeat_count"
                    }
                )
                parameters.append(param)

        return parameters

    def instantiate_subprogram(self, subprogram_id: str,
                              parameter_values: Dict[str, Any] = None) -> List[Action]:
        """
        Instantiate a subprogram with parameter values

        Creates a copy of the subprogram's actions with parameters applied.

        Args:
            subprogram_id: ID of subprogram to instantiate
            parameter_values: Dictionary of parameter name -> value

        Returns:
            List of Action instances with parameters applied
        """
        subprogram = self.subprograms.get(subprogram_id)
        if not subprogram:
            logger.error(f"Subprogram not found: {subprogram_id}")
            return []

        # Deep copy actions to avoid modifying originals
        instantiated_actions = []

        for action in subprogram.actions:
            new_action = copy.deepcopy(action)
            instantiated_actions.append(new_action)

        # Apply parameter values if provided
        if parameter_values:
            for param_name, param_value in parameter_values.items():
                # Find the parameter definition
                param_def = subprogram.get_parameter_by_name(param_name)
                if not param_def or not param_def.action_binding:
                    continue

                # Apply the value to the bound action
                action_index = param_def.action_binding.get("action_index")
                parameter_key = param_def.action_binding.get("parameter_key")

                if action_index is not None and parameter_key and \
                   0 <= action_index < len(instantiated_actions):
                    instantiated_actions[action_index].parameters[parameter_key] = param_value

        # Increment usage count
        subprogram.increment_usage_count()
        self.save_subprogram(subprogram)

        logger.info(f"Instantiated subprogram: {subprogram.name} with {len(instantiated_actions)} actions")
        return instantiated_actions

    # ========================================
    # File Persistence
    # ========================================

    def save_subprogram(self, subprogram: SubProgram) -> bool:
        """
        Save subprogram to disk

        Args:
            subprogram: SubProgram instance to save

        Returns:
            True if successful, False otherwise
        """
        filepath = self.storage_dir / f"{subprogram.id}.json"

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(subprogram.to_dict(), f, indent=2, ensure_ascii=False)

            logger.info(f"Saved subprogram to: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save subprogram: {e}", exc_info=True)
            return False

    def load_subprogram(self, filepath: Path) -> Optional[SubProgram]:
        """
        Load subprogram from file

        Args:
            filepath: Path to subprogram JSON file

        Returns:
            Loaded SubProgram instance or None if failed
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            subprogram = SubProgram.from_dict(data)
            logger.info(f"Loaded subprogram: {subprogram.name} from {filepath}")
            return subprogram

        except Exception as e:
            logger.error(f"Failed to load subprogram from {filepath}: {e}", exc_info=True)
            return None

    def load_all_subprograms(self):
        """Load all subprograms from storage directory"""
        self.subprograms.clear()

        if not self.storage_dir.exists():
            logger.warning(f"Storage directory does not exist: {self.storage_dir}")
            return

        # Load all JSON files
        for filepath in self.storage_dir.glob("*.json"):
            subprogram = self.load_subprogram(filepath)
            if subprogram:
                self.subprograms[subprogram.id] = subprogram

        logger.info(f"Loaded {len(self.subprograms)} subprograms from storage")
        self.subprograms_loaded.emit()

    # ========================================
    # Search and Filter
    # ========================================

    def search_subprograms(self, query: str) -> List[SubProgram]:
        """
        Search subprograms by name, description, or tags

        Args:
            query: Search query string

        Returns:
            List of matching subprograms
        """
        query = query.lower()
        results = []

        for subprogram in self.subprograms.values():
            # Search in name, description, and tags
            if (query in subprogram.name.lower() or
                query in subprogram.description.lower() or
                any(query in tag.lower() for tag in subprogram.tags)):
                results.append(subprogram)

        return results

    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        categories = set()
        for subprogram in self.subprograms.values():
            categories.add(subprogram.category)
        return sorted(list(categories))
