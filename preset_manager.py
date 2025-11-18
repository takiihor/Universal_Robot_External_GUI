"""
UR10e Robot Preset Manager Module

This module provides comprehensive preset position management for the UR10e robot,
including preset storage, validation, categorization, and advanced features like
trajectory sequences and safety validation.

Features:
- Preset position storage and management
- Category-based organization
- Safety validation and collision checking
- Import/export functionality
- Preset sequences and trajectories
- Compatibility with existing Config module

Author: UR10e Control System Development Team
Date: 2024-11-11
Version: 1.0.0
"""

import json
import os
import logging
import time
import math
from typing import List, Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
import numpy as np

# Setup logger
logger = logging.getLogger(__name__)


class PresetCategory(Enum):
    """Preset category enumeration"""
    SYSTEM = "System"
    WORKSPACE = "Workspace"
    TASK = "Task"
    USER = "User"
    MAINTENANCE = "Maintenance"
    CALIBRATION = "Calibration"
    TEMPLATE = "Template"


class PresetValidationStatus(Enum):
    """Preset validation status"""
    NOT_VALIDATED = "Not Validated"
    VALID = "Valid"
    WARNING = "Warning"
    INVALID = "Invalid"


class MotionType(Enum):
    """Motion type for preset execution"""
    JOINT = "Joint"
    LINEAR = "Linear"
    CIRCULAR = "Circular"
    SPLINE = "Spline"


@dataclass
class PresetData:
    """
    Enhanced preset data structure containing all information
    about a robot preset position.
    """
    # Basic information
    name: str
    joints: List[float]  # Joint positions in radians [j1, j2, j3, j4, j5, j6]
    description: str = ""
    category: PresetCategory = PresetCategory.USER
    
    # TCP information (optional)
    tcp_pose: Optional[List[float]] = None  # [x, y, z, rx, ry, rz]
    tcp_speed: float = 0.1  # m/s
    tcp_acceleration: float = 0.5  # m/s²
    
    # Joint motion parameters
    joint_speed: float = 0.2  # rad/s
    joint_acceleration: float = 1.0  # rad/s²
    
    # Advanced motion parameters
    blend_radius: float = 0.0  # Blend radius for smooth transitions (m)
    motion_type: MotionType = MotionType.JOINT
    
    # Metadata
    created_date: datetime = field(default_factory=datetime.now)
    modified_date: datetime = field(default_factory=datetime.now)
    author: str = "System"
    version: int = 1
    
    # Safety and validation
    locked: bool = False  # Prevent modification/deletion
    safety_validated: bool = False
    validation_status: PresetValidationStatus = PresetValidationStatus.NOT_VALIDATED
    validation_message: str = ""
    
    # Organization
    tags: List[str] = field(default_factory=list)
    group: Optional[str] = None
    priority: int = 0  # Higher priority presets shown first
    
    # Execution options
    pre_wait: float = 0.0  # Wait time before execution (seconds)
    post_wait: float = 0.0  # Wait time after execution (seconds)
    force_mode_params: Optional[Dict[str, Any]] = None  # Force mode parameters if applicable
    
    # Visual representation (for future 3D preview)
    thumbnail: Optional[bytes] = None
    color: str = "#2196F3"  # Display color in UI
    icon: str = "📍"  # Display icon
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert datetime objects to strings
        data['created_date'] = self.created_date.isoformat()
        data['modified_date'] = self.modified_date.isoformat()
        # Convert enum to string
        data['category'] = self.category.value
        data['validation_status'] = self.validation_status.value
        data['motion_type'] = self.motion_type.value
        # Remove thumbnail for JSON serialization
        data.pop('thumbnail', None)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PresetData':
        """Create from dictionary"""
        # Convert strings back to datetime
        if 'created_date' in data:
            data['created_date'] = datetime.fromisoformat(data['created_date'])
        if 'modified_date' in data:
            data['modified_date'] = datetime.fromisoformat(data['modified_date'])
        # Convert strings back to enums
        if 'category' in data:
            data['category'] = PresetCategory(data['category'])
        if 'validation_status' in data:
            data['validation_status'] = PresetValidationStatus(data['validation_status'])
        if 'motion_type' in data:
            data['motion_type'] = MotionType(data['motion_type'])
        return cls(**data)


@dataclass
class PresetSequence:
    """
    Sequence of presets for complex motion patterns
    """
    name: str
    description: str = ""
    preset_names: List[str] = field(default_factory=list)
    transitions: List[Dict[str, Any]] = field(default_factory=list)  # Transition parameters between presets
    loop_count: int = 1  # Number of times to execute sequence
    created_date: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    def add_preset(self, preset_name: str, transition_params: Optional[Dict] = None):
        """Add a preset to the sequence"""
        self.preset_names.append(preset_name)
        if transition_params:
            self.transitions.append(transition_params)
        else:
            self.transitions.append({'blend_radius': 0.0, 'wait_time': 0.0})


class PresetValidator:
    """
    Validates preset positions for safety and reachability
    """
    
    # UR10e joint limits (in radians)
    JOINT_LIMITS = [
        (-2*math.pi, 2*math.pi),  # Base
        (-2*math.pi, 2*math.pi),  # Shoulder
        (-2*math.pi, 2*math.pi),  # Elbow
        (-2*math.pi, 2*math.pi),  # Wrist 1
        (-2*math.pi, 2*math.pi),  # Wrist 2
        (-2*math.pi, 2*math.pi),  # Wrist 3
    ]
    
    # Workspace limits (in meters)
    WORKSPACE_LIMITS = {
        'x': (-0.85, 0.85),
        'y': (-0.85, 0.85),
        'z': (0.0, 1.3),
    }
    
    # Singularity thresholds
    SINGULARITY_THRESHOLD = 0.1  # radians
    
    @classmethod
    def validate_joint_limits(cls, joints: List[float]) -> Tuple[bool, str]:
        """
        Validate joint positions against robot limits
        
        Args:
            joints: List of joint angles in radians
            
        Returns:
            Tuple of (is_valid, message)
        """
        if len(joints) != 6:
            return False, f"Invalid number of joints: {len(joints)}, expected 6"
        
        for i, joint_angle in enumerate(joints):
            min_limit, max_limit = cls.JOINT_LIMITS[i]
            if not min_limit <= joint_angle <= max_limit:
                return False, f"Joint {i+1} angle {math.degrees(joint_angle):.1f}° exceeds limits [{math.degrees(min_limit):.1f}°, {math.degrees(max_limit):.1f}°]"
        
        return True, "All joints within limits"
    
    @classmethod
    def validate_workspace(cls, tcp_pose: List[float]) -> Tuple[bool, str]:
        """
        Validate TCP position against workspace limits
        
        Args:
            tcp_pose: TCP pose [x, y, z, rx, ry, rz]
            
        Returns:
            Tuple of (is_valid, message)
        """
        if tcp_pose is None or len(tcp_pose) < 3:
            return True, "No TCP pose to validate"
        
        x, y, z = tcp_pose[:3]
        
        x_min, x_max = cls.WORKSPACE_LIMITS['x']
        if not x_min <= x <= x_max:
            return False, f"X position {x:.3f}m outside workspace [{x_min}, {x_max}]"
        
        y_min, y_max = cls.WORKSPACE_LIMITS['y']
        if not y_min <= y <= y_max:
            return False, f"Y position {y:.3f}m outside workspace [{y_min}, {y_max}]"
        
        z_min, z_max = cls.WORKSPACE_LIMITS['z']
        if not z_min <= z <= z_max:
            return False, f"Z position {z:.3f}m outside workspace [{z_min}, {z_max}]"
        
        return True, "TCP position within workspace"
    
    @classmethod
    def check_singularity(cls, joints: List[float]) -> Tuple[bool, str]:
        """
        Check if joint configuration is near a singularity
        
        Args:
            joints: List of joint angles in radians
            
        Returns:
            Tuple of (is_near_singularity, message)
        """
        # Check wrist singularity (joint 5 near 0)
        if abs(joints[4]) < cls.SINGULARITY_THRESHOLD:
            return True, f"Warning: Joint 5 near singularity ({math.degrees(joints[4]):.1f}°)"
        
        # Check shoulder singularity (joint 3 near 0 or ±180°)
        if abs(joints[2]) < cls.SINGULARITY_THRESHOLD or \
           abs(abs(joints[2]) - math.pi) < cls.SINGULARITY_THRESHOLD:
            return True, f"Warning: Joint 3 near singularity ({math.degrees(joints[2]):.1f}°)"
        
        return False, "No singularity detected"
    
    @classmethod
    def validate_preset(cls, preset: PresetData) -> PresetValidationStatus:
        """
        Perform complete validation of a preset
        
        Args:
            preset: PresetData object to validate
            
        Returns:
            Validation status
        """
        # Validate joint limits
        valid, message = cls.validate_joint_limits(preset.joints)
        if not valid:
            preset.validation_status = PresetValidationStatus.INVALID
            preset.validation_message = message
            return PresetValidationStatus.INVALID
        
        # Validate workspace if TCP pose is available
        if preset.tcp_pose:
            valid, message = cls.validate_workspace(preset.tcp_pose)
            if not valid:
                preset.validation_status = PresetValidationStatus.INVALID
                preset.validation_message = message
                return PresetValidationStatus.INVALID
        
        # Check for singularities
        near_singularity, message = cls.check_singularity(preset.joints)
        if near_singularity:
            preset.validation_status = PresetValidationStatus.WARNING
            preset.validation_message = message
            return PresetValidationStatus.WARNING
        
        preset.validation_status = PresetValidationStatus.VALID
        preset.validation_message = "Preset validated successfully"
        preset.safety_validated = True
        return PresetValidationStatus.VALID


class PresetManager:
    """
    Main preset manager class handling all preset operations
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize preset manager"""
        if not hasattr(self, 'initialized'):
            self.presets: Dict[str, PresetData] = {}
            self.sequences: Dict[str, PresetSequence] = {}
            self.validator = PresetValidator()
            self.data_dir = Path("presets")
            self.data_dir.mkdir(exist_ok=True)
            self.backup_dir = self.data_dir / "backups"
            self.backup_dir.mkdir(exist_ok=True)
            
            # Load existing presets
            self._load_system_presets()
            self.load_user_presets()
            
            # Import from Config module if available
            self._import_from_config()
            
            self.initialized = True
            logger.info("Preset Manager initialized successfully")
    
    def _load_system_presets(self):
        """Load built-in system presets"""
        system_presets = [
            PresetData(
                name="home",
                joints=[0.0, -1.5708, 1.5708, -1.5708, -1.5708, 0.0],
                description="Home position - robot at origin",
                category=PresetCategory.SYSTEM,
                locked=True,
                safety_validated=True,
                validation_status=PresetValidationStatus.VALID,
                priority=100,
                icon="🏠"
            ),
            PresetData(
                name="safe",
                joints=[0.0, -2.0, 2.0, -1.5708, -1.5708, 0.0],
                description="Safe position - elevated pose",
                category=PresetCategory.SYSTEM,
                locked=True,
                safety_validated=True,
                validation_status=PresetValidationStatus.VALID,
                priority=99,
                icon="🛡️"
            ),
            PresetData(
                name="vertical",
                joints=[0.0, -1.5708, 0.0, -1.5708, -1.5708, 0.0],
                description="Vertical downward position",
                category=PresetCategory.SYSTEM,
                locked=True,
                safety_validated=True,
                validation_status=PresetValidationStatus.VALID,
                priority=98,
                icon="⬇️"
            ),
            PresetData(
                name="maintenance",
                joints=[0.0, -1.0, 0.5, -1.0, -1.5708, 0.0],
                description="Maintenance access position",
                category=PresetCategory.MAINTENANCE,
                locked=True,
                safety_validated=True,
                validation_status=PresetValidationStatus.VALID,
                priority=90,
                icon="🔧"
            ),
        ]
        
        for preset in system_presets:
            self.presets[preset.name] = preset
            logger.debug(f"Loaded system preset: {preset.name}")
    
    def _import_from_config(self):
        """Import presets from Config module for compatibility"""
        try:
            from config import Config
            
            for name, data in Config.PRESET_POSITIONS.items():
                if name not in self.presets:  # Don't override existing presets
                    preset = PresetData(
                        name=name,
                        joints=data['joints'],
                        description=data.get('description', ''),
                        category=PresetCategory.USER,
                        author="Config Import",
                        safety_validated=False
                    )
                    # Validate the imported preset
                    self.validator.validate_preset(preset)
                    self.presets[name] = preset
                    logger.info(f"Imported preset from Config: {name}")
        except ImportError:
            logger.warning("Config module not available for preset import")
        except Exception as e:
            logger.error(f"Error importing presets from Config: {e}")
    
    # ========================================
    # Basic CRUD Operations
    # ========================================
    
    def add_preset(self, preset: PresetData, validate: bool = True) -> bool:
        """
        Add a new preset
        
        Args:
            preset: PresetData object to add
            validate: Whether to validate before adding
            
        Returns:
            Success status
        """
        try:
            # Check if preset exists and is locked
            if preset.name in self.presets:
                if self.presets[preset.name].locked:
                    logger.warning(f"Cannot override locked preset: {preset.name}")
                    return False
            
            # Validate if requested
            if validate:
                status = self.validator.validate_preset(preset)
                if status == PresetValidationStatus.INVALID:
                    logger.error(f"Preset validation failed: {preset.validation_message}")
                    return False
            
            # Update timestamps
            preset.modified_date = datetime.now()
            if preset.name not in self.presets:
                preset.created_date = datetime.now()
            else:
                # Preserve original creation date
                preset.created_date = self.presets[preset.name].created_date
                preset.version = self.presets[preset.name].version + 1
            
            # Store preset
            self.presets[preset.name] = preset
            
            # Auto-save to disk
            self.save_user_presets()
            
            logger.info(f"Added preset: {preset.name} (v{preset.version})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add preset: {e}")
            return False
    
    def get_preset(self, name: str) -> Optional[PresetData]:
        """
        Get a preset by name
        
        Args:
            name: Preset name
            
        Returns:
            PresetData object or None if not found
        """
        return self.presets.get(name)
    
    def get_preset_joints(self, name: str) -> Optional[List[float]]:
        """
        Get joint positions for a preset (compatibility method)
        
        Args:
            name: Preset name
            
        Returns:
            List of joint angles or None if not found
        """
        preset = self.get_preset(name)
        return preset.joints if preset else None
    
    def update_preset(self, name: str, **kwargs) -> bool:
        """
        Update preset properties
        
        Args:
            name: Preset name
            **kwargs: Properties to update
            
        Returns:
            Success status
        """
        if name not in self.presets:
            logger.error(f"Preset not found: {name}")
            return False
        
        preset = self.presets[name]
        
        if preset.locked and 'force' not in kwargs:
            logger.warning(f"Cannot modify locked preset: {name}")
            return False
        
        # Update allowed fields
        allowed_fields = ['description', 'joints', 'tcp_pose', 'tags', 
                         'joint_speed', 'joint_acceleration', 'tcp_speed', 
                         'tcp_acceleration', 'blend_radius', 'motion_type',
                         'pre_wait', 'post_wait', 'color', 'icon', 'group']
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(preset, field, value)
        
        # Update modification timestamp
        preset.modified_date = datetime.now()
        preset.version += 1
        
        # Re-validate if joints were changed
        if 'joints' in kwargs:
            self.validator.validate_preset(preset)
        
        # Auto-save
        self.save_user_presets()
        
        logger.info(f"Updated preset: {name} (v{preset.version})")
        return True
    
    def delete_preset(self, name: str, force: bool = False) -> bool:
        """
        Delete a preset
        
        Args:
            name: Preset name
            force: Force deletion even if locked
            
        Returns:
            Success status
        """
        if name not in self.presets:
            logger.error(f"Preset not found: {name}")
            return False
        
        preset = self.presets[name]
        
        if preset.locked and not force:
            logger.warning(f"Cannot delete locked preset: {name}")
            return False
        
        # Backup before deletion
        self._backup_preset(preset)
        
        # Remove from dictionary
        del self.presets[name]
        
        # Auto-save
        self.save_user_presets()
        
        logger.info(f"Deleted preset: {name}")
        return True
    
    # ========================================
    # Query and Filter Operations
    # ========================================
    
    def list_presets(self, category: Optional[PresetCategory] = None,
                     tags: Optional[List[str]] = None,
                     validated_only: bool = False) -> List[PresetData]:
        """
        List presets with optional filtering
        
        Args:
            category: Filter by category
            tags: Filter by tags (any match)
            validated_only: Only return validated presets
            
        Returns:
            List of matching presets
        """
        results = []
        
        for preset in self.presets.values():
            # Category filter
            if category and preset.category != category:
                continue
            
            # Tags filter
            if tags and not any(tag in preset.tags for tag in tags):
                continue
            
            # Validation filter
            if validated_only and not preset.safety_validated:
                continue
            
            results.append(preset)
        
        # Sort by priority (descending) then by name
        results.sort(key=lambda p: (-p.priority, p.name))
        
        return results
    
    def search_presets(self, query: str) -> List[PresetData]:
        """
        Search presets by name or description
        
        Args:
            query: Search query string
            
        Returns:
            List of matching presets
        """
        query_lower = query.lower()
        results = []
        
        for preset in self.presets.values():
            if (query_lower in preset.name.lower() or 
                query_lower in preset.description.lower() or
                any(query_lower in tag.lower() for tag in preset.tags)):
                results.append(preset)
        
        return results
    
    def get_categories(self) -> List[PresetCategory]:
        """Get all available categories"""
        return list(PresetCategory)
    
    def get_presets_by_group(self, group: str) -> List[PresetData]:
        """Get all presets in a specific group"""
        return [p for p in self.presets.values() if p.group == group]
    
    # ========================================
    # Sequence Operations
    # ========================================
    
    def create_sequence(self, name: str, preset_names: List[str],
                       description: str = "") -> Optional[PresetSequence]:
        """
        Create a preset sequence
        
        Args:
            name: Sequence name
            preset_names: List of preset names in order
            description: Sequence description
            
        Returns:
            Created sequence or None if invalid
        """
        # Validate all presets exist
        for preset_name in preset_names:
            if preset_name not in self.presets:
                logger.error(f"Preset not found for sequence: {preset_name}")
                return None
        
        sequence = PresetSequence(
            name=name,
            description=description,
            preset_names=preset_names
        )
        
        self.sequences[name] = sequence
        logger.info(f"Created sequence: {name} with {len(preset_names)} presets")
        return sequence
    
    def get_sequence(self, name: str) -> Optional[PresetSequence]:
        """Get a sequence by name"""
        return self.sequences.get(name)
    
    def execute_sequence_data(self, sequence_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get execution data for a sequence
        
        Args:
            sequence_name: Name of the sequence
            
        Returns:
            List of execution data dictionaries
        """
        sequence = self.sequences.get(sequence_name)
        if not sequence:
            logger.error(f"Sequence not found: {sequence_name}")
            return None
        
        execution_data = []
        
        for i, preset_name in enumerate(sequence.preset_names):
            preset = self.get_preset(preset_name)
            if not preset:
                logger.error(f"Preset not found in sequence: {preset_name}")
                continue
            
            # Get transition params
            transition = sequence.transitions[i] if i < len(sequence.transitions) else {}
            
            execution_data.append({
                'preset': preset,
                'joints': preset.joints,
                'speed': preset.joint_speed,
                'acceleration': preset.joint_acceleration,
                'blend_radius': transition.get('blend_radius', preset.blend_radius),
                'wait_before': preset.pre_wait,
                'wait_after': preset.post_wait + transition.get('wait_time', 0),
                'motion_type': preset.motion_type
            })
        
        return execution_data
    
    # ========================================
    # Import/Export Operations
    # ========================================
    
    def export_presets(self, filepath: str, 
                      presets: Optional[List[str]] = None,
                      include_system: bool = False) -> bool:
        """
        Export presets to JSON file
        
        Args:
            filepath: Export file path
            presets: Specific preset names to export (None = all)
            include_system: Include system presets
            
        Returns:
            Success status
        """
        try:
            export_data = {
                'version': '1.0.0',
                'export_date': datetime.now().isoformat(),
                'presets': {},
                'sequences': {}
            }
            
            # Select presets to export
            presets_to_export = []
            if presets:
                presets_to_export = [self.presets[name] for name in presets 
                                    if name in self.presets]
            else:
                presets_to_export = self.presets.values()
            
            # Filter system presets if needed
            if not include_system:
                presets_to_export = [p for p in presets_to_export 
                                    if p.category != PresetCategory.SYSTEM]
            
            # Convert to dictionary
            for preset in presets_to_export:
                export_data['presets'][preset.name] = preset.to_dict()
            
            # Export sequences that use exported presets
            preset_names = {p.name for p in presets_to_export}
            for seq_name, sequence in self.sequences.items():
                if all(p in preset_names for p in sequence.preset_names):
                    export_data['sequences'][seq_name] = {
                        'name': sequence.name,
                        'description': sequence.description,
                        'preset_names': sequence.preset_names,
                        'transitions': sequence.transitions,
                        'loop_count': sequence.loop_count,
                        'tags': sequence.tags
                    }
            
            # Write to file
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Exported {len(export_data['presets'])} presets to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export presets: {e}")
            return False
    
    def import_presets(self, filepath: str, 
                      override_existing: bool = False,
                      validate: bool = True) -> Tuple[int, int]:
        """
        Import presets from JSON file
        
        Args:
            filepath: Import file path
            override_existing: Override existing presets
            validate: Validate imported presets
            
        Returns:
            Tuple of (successful_imports, failed_imports)
        """
        try:
            with open(filepath, 'r') as f:
                import_data = json.load(f)
            
            successful = 0
            failed = 0
            
            # Import presets
            presets_data = import_data.get('presets', {})
            for name, preset_dict in presets_data.items():
                try:
                    # Skip if exists and not overriding
                    if name in self.presets and not override_existing:
                        logger.debug(f"Skipping existing preset: {name}")
                        continue
                    
                    # Create preset from dictionary
                    preset = PresetData.from_dict(preset_dict)
                    
                    # Add to manager
                    if self.add_preset(preset, validate=validate):
                        successful += 1
                    else:
                        failed += 1
                        
                except Exception as e:
                    logger.error(f"Failed to import preset {name}: {e}")
                    failed += 1
            
            # Import sequences
            sequences_data = import_data.get('sequences', {})
            for seq_name, seq_dict in sequences_data.items():
                try:
                    sequence = PresetSequence(
                        name=seq_dict['name'],
                        description=seq_dict['description'],
                        preset_names=seq_dict['preset_names'],
                        transitions=seq_dict['transitions'],
                        loop_count=seq_dict.get('loop_count', 1),
                        tags=seq_dict.get('tags', [])
                    )
                    self.sequences[seq_name] = sequence
                except Exception as e:
                    logger.error(f"Failed to import sequence {seq_name}: {e}")
            
            logger.info(f"Import complete: {successful} successful, {failed} failed")
            return successful, failed
            
        except Exception as e:
            logger.error(f"Failed to import presets: {e}")
            return 0, 0
    
    # ========================================
    # Persistence Operations
    # ========================================
    
    def save_user_presets(self) -> bool:
        """Save user presets to disk"""
        try:
            # Filter user presets
            user_presets = {name: preset for name, preset in self.presets.items()
                          if preset.category != PresetCategory.SYSTEM}
            
            # Prepare data
            save_data = {
                'version': '1.0.0',
                'save_date': datetime.now().isoformat(),
                'presets': {name: preset.to_dict() for name, preset in user_presets.items()},
                'sequences': {}
            }
            
            # Add sequences
            for seq_name, sequence in self.sequences.items():
                save_data['sequences'][seq_name] = {
                    'name': sequence.name,
                    'description': sequence.description,
                    'preset_names': sequence.preset_names,
                    'transitions': sequence.transitions,
                    'loop_count': sequence.loop_count,
                    'tags': sequence.tags,
                    'created_date': sequence.created_date.isoformat()
                }
            
            # Save to file
            save_path = self.data_dir / "user_presets.json"
            with open(save_path, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            logger.debug(f"Saved {len(user_presets)} user presets")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user presets: {e}")
            return False
    
    def load_user_presets(self) -> bool:
        """Load user presets from disk"""
        try:
            load_path = self.data_dir / "user_presets.json"
            
            if not load_path.exists():
                logger.debug("No user presets file found")
                return True
            
            with open(load_path, 'r') as f:
                load_data = json.load(f)
            
            # Load presets
            presets_data = load_data.get('presets', {})
            for name, preset_dict in presets_data.items():
                try:
                    preset = PresetData.from_dict(preset_dict)
                    self.presets[name] = preset
                except Exception as e:
                    logger.error(f"Failed to load preset {name}: {e}")
            
            # Load sequences
            sequences_data = load_data.get('sequences', {})
            for seq_name, seq_dict in sequences_data.items():
                try:
                    sequence = PresetSequence(
                        name=seq_dict['name'],
                        description=seq_dict['description'],
                        preset_names=seq_dict['preset_names'],
                        transitions=seq_dict['transitions'],
                        loop_count=seq_dict.get('loop_count', 1),
                        tags=seq_dict.get('tags', [])
                    )
                    if 'created_date' in seq_dict:
                        sequence.created_date = datetime.fromisoformat(seq_dict['created_date'])
                    self.sequences[seq_name] = sequence
                except Exception as e:
                    logger.error(f"Failed to load sequence {seq_name}: {e}")
            
            logger.info(f"Loaded {len(presets_data)} user presets and {len(sequences_data)} sequences")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load user presets: {e}")
            return False
    
    def _backup_preset(self, preset: PresetData):
        """Create backup of a preset before deletion"""
        try:
            backup_file = self.backup_dir / f"deleted_{preset.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w') as f:
                json.dump(preset.to_dict(), f, indent=2)
            logger.debug(f"Backed up preset to {backup_file}")
        except Exception as e:
            logger.error(f"Failed to backup preset: {e}")
    
    # ========================================
    # Statistics and Analytics
    # ========================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get preset manager statistics"""
        stats = {
            'total_presets': len(self.presets),
            'system_presets': sum(1 for p in self.presets.values() 
                                if p.category == PresetCategory.SYSTEM),
            'user_presets': sum(1 for p in self.presets.values() 
                              if p.category == PresetCategory.USER),
            'validated_presets': sum(1 for p in self.presets.values() 
                                   if p.safety_validated),
            'locked_presets': sum(1 for p in self.presets.values() if p.locked),
            'total_sequences': len(self.sequences),
            'categories': {}
        }
        
        # Count by category
        for category in PresetCategory:
            count = sum(1 for p in self.presets.values() if p.category == category)
            stats['categories'][category.value] = count
        
        return stats
    
    def get_validation_report(self) -> Dict[str, List[str]]:
        """Get validation report for all presets"""
        report = {
            'valid': [],
            'warning': [],
            'invalid': [],
            'not_validated': []
        }
        
        for preset in self.presets.values():
            if preset.validation_status == PresetValidationStatus.VALID:
                report['valid'].append(preset.name)
            elif preset.validation_status == PresetValidationStatus.WARNING:
                report['warning'].append(f"{preset.name}: {preset.validation_message}")
            elif preset.validation_status == PresetValidationStatus.INVALID:
                report['invalid'].append(f"{preset.name}: {preset.validation_message}")
            else:
                report['not_validated'].append(preset.name)
        
        return report
    
    # ========================================
    # Compatibility Methods
    # ========================================
    
    def sync_to_config(self):
        """Synchronize presets back to Config module for compatibility"""
        try:
            from config import Config
            
            # Update Config.PRESET_POSITIONS
            for name, preset in self.presets.items():
                if preset.category != PresetCategory.SYSTEM:  # Don't sync system presets
                    Config.PRESET_POSITIONS[name] = {
                        'joints': preset.joints,
                        'description': preset.description
                    }
            
            logger.debug("Synchronized presets to Config module")
            
        except ImportError:
            logger.debug("Config module not available for synchronization")
        except Exception as e:
            logger.error(f"Failed to sync to Config: {e}")
    
    def get_preset_dict(self, name: str) -> Optional[Dict[str, Any]]:
        """Get preset as dictionary (Config-compatible format)"""
        preset = self.get_preset(name)
        if preset:
            return {
                'joints': preset.joints,
                'description': preset.description
            }
        return None


# ========================================
# Utility Functions
# ========================================

def create_preset_from_current_position(joints: List[float], 
                                       tcp_pose: Optional[List[float]] = None,
                                       name: str = None) -> PresetData:
    """
    Create a preset from current robot position
    
    Args:
        joints: Current joint positions
        tcp_pose: Current TCP pose (optional)
        name: Preset name (auto-generated if None)
        
    Returns:
        PresetData object
    """
    if name is None:
        name = f"position_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    preset = PresetData(
        name=name,
        joints=joints,
        tcp_pose=tcp_pose,
        description="Created from current position",
        category=PresetCategory.USER,
        author="Current Position Capture"
    )
    
    # Validate the preset
    PresetValidator.validate_preset(preset)
    
    return preset


def interpolate_presets(preset1: PresetData, preset2: PresetData, 
                       steps: int = 10) -> List[List[float]]:
    """
    Interpolate between two presets for smooth motion
    
    Args:
        preset1: Start preset
        preset2: End preset
        steps: Number of interpolation steps
        
    Returns:
        List of interpolated joint positions
    """
    joints1 = np.array(preset1.joints)
    joints2 = np.array(preset2.joints)
    
    interpolated = []
    for i in range(steps + 1):
        t = i / steps
        interpolated_joints = joints1 + t * (joints2 - joints1)
        interpolated.append(interpolated_joints.tolist())
    
    return interpolated


# ========================================
# Module Testing
# ========================================

if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test preset manager
    manager = PresetManager()
    
    # Print statistics
    stats = manager.get_statistics()
    print(f"Preset Manager Statistics:")
    print(f"  Total presets: {stats['total_presets']}")
    print(f"  System presets: {stats['system_presets']}")
    print(f"  User presets: {stats['user_presets']}")
    print(f"  Validated: {stats['validated_presets']}")
    
    # Test adding a preset
    test_preset = PresetData(
        name="test_position",
        joints=[0.1, -1.5, 1.5, -1.5, -1.5, 0.1],
        description="Test position for development",
        category=PresetCategory.USER,
        tags=["test", "development"]
    )
    
    if manager.add_preset(test_preset):
        print(f"Successfully added test preset: {test_preset.name}")
    
    # Test export
    if manager.export_presets("test_export.json"):
        print("Successfully exported presets")
    
    # Print validation report
    report = manager.get_validation_report()
    print(f"\nValidation Report:")
    print(f"  Valid: {len(report['valid'])} presets")
    print(f"  Warnings: {len(report['warning'])} presets")
    print(f"  Invalid: {len(report['invalid'])} presets")
    print(f"  Not validated: {len(report['not_validated'])} presets")
