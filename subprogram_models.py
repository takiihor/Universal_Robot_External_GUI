"""
Subprogram Data Models

Defines the data structures for subprograms and their parameters.
Subprograms are reusable action sequences that can be called from the main program.
"""

import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


@dataclass
class Parameter:
    """
    Subprogram parameter definition

    Represents a configurable parameter that can be passed to a subprogram.
    Examples: target_position, speed_percent, wait_duration, etc.
    """
    name: str                           # Parameter name (e.g., "target_position")
    type: str                           # Parameter type: "number", "string", "position", "speed", "boolean"
    default_value: Any = None          # Default value if not specified
    required: bool = False              # Whether this parameter must be provided
    description: str = ""               # Human-readable description
    constraints: Dict[str, Any] = field(default_factory=dict)  # Constraints (min, max, options, etc.)
    action_binding: Optional[Dict] = None  # Binding to specific action parameter

    def to_dict(self) -> dict:
        """Convert to dictionary format (for saving)"""
        return {
            "name": self.name,
            "type": self.type,
            "default_value": self.default_value,
            "required": self.required,
            "description": self.description,
            "constraints": self.constraints,
            "action_binding": self.action_binding
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Parameter':
        """Create instance from dictionary (for loading)"""
        return cls(
            name=data["name"],
            type=data["type"],
            default_value=data.get("default_value"),
            required=data.get("required", False),
            description=data.get("description", ""),
            constraints=data.get("constraints", {}),
            action_binding=data.get("action_binding")
        )


@dataclass
class SubProgram:
    """
    Subprogram definition

    A reusable sequence of actions that can be called from the main program.
    Think of it as a "function" or "macro" in programming.
    """
    id: str                             # Unique identifier (UUID)
    name: str                           # Display name (e.g., "Pick Part", "Lock Screw")
    description: str = ""               # Detailed description
    icon: str = "📦"                   # Display icon (emoji)
    category: str = "Other"            # Category for organization
    parameters: List[Parameter] = field(default_factory=list)  # Parameter definitions
    actions: List = field(default_factory=list)  # Action sequence (List[Action])
    version: str = "1.0"               # Version number
    created_date: str = ""             # Creation timestamp
    modified_date: str = ""            # Last modification timestamp
    usage_count: int = 0               # How many times it's been used
    tags: List[str] = field(default_factory=list)  # Search tags

    def __post_init__(self):
        """Initialize default values"""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_date:
            self.created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.modified_date:
            self.modified_date = self.created_date

    def to_dict(self) -> dict:
        """Convert to dictionary format (for saving)"""
        # Import Action here to avoid circular import
        from sequential_controller import Action

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category,
            "parameters": [p.to_dict() for p in self.parameters],
            "actions": [a.to_dict() if isinstance(a, Action) else a for a in self.actions],
            "version": self.version,
            "created_date": self.created_date,
            "modified_date": self.modified_date,
            "usage_count": self.usage_count,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SubProgram':
        """Create instance from dictionary (for loading)"""
        # Import Action here to avoid circular import
        from sequential_controller import Action

        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            icon=data.get("icon", "📦"),
            category=data.get("category", "Other"),
            parameters=[Parameter.from_dict(p) for p in data.get("parameters", [])],
            actions=[Action.from_dict(a) if isinstance(a, dict) else a
                    for a in data.get("actions", [])],
            version=data.get("version", "1.0"),
            created_date=data.get("created_date", ""),
            modified_date=data.get("modified_date", ""),
            usage_count=data.get("usage_count", 0),
            tags=data.get("tags", [])
        )

    def get_parameter_by_name(self, name: str) -> Optional[Parameter]:
        """Get parameter by name"""
        for param in self.parameters:
            if param.name == name:
                return param
        return None

    def update_modified_date(self):
        """Update the modified date to current time"""
        self.modified_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def increment_usage_count(self):
        """Increment the usage counter"""
        self.usage_count += 1

    def get_display_summary(self) -> str:
        """Get a brief summary for display"""
        action_count = len(self.actions)
        param_count = len(self.parameters)
        return f"{self.icon} {self.name} ({action_count} steps, {param_count} params)"
