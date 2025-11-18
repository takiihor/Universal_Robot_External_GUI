"""
Sequential Controller Module

Provides visual task sequencing for non-technical users to control the UR10e robot
through a drag-and-drop interface without coding.

Features:
- Action type definitions (movement, hand guiding, timing)
- Action sequence management (add, delete, reorder)
- Task execution control (execute, pause, resume, stop)
- Task save/load (JSON format)
"""

import json
import time
import logging
import math
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from config import Config

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Action type enumeration - Simple robot control only"""
    # Position Control
    MOVE_TO_POSITION = "move_to_position"          # Move to preset position
    RELATIVE_MOVE = "relative_move"                # Relative movement
    SAVE_POSITION = "save_position"                # Save current position
    RETURN_HOME = "return_home"                    # Return to home position

    # Hand Guiding Mode
    ENABLE_FREEDRIVE = "enable_freedrive"          # Enable hand guiding
    DISABLE_FREEDRIVE = "disable_freedrive"        # Disable hand guiding

    # Timing Control
    WAIT = "wait"                                  # Wait for time

    # Force Control
    ENABLE_FORCE = "enable_force"                  # Enable force mode
    DISABLE_FORCE = "disable_force"                # Disable force mode
    SET_FORCE_LEVEL = "set_force_level"            # Set force level

    # Gripper Control
    GRIPPER_OPEN = "gripper_open"                  # Open gripper
    GRIPPER_CLOSE = "gripper_close"                # Close gripper
    GRIPPER_MOVE = "gripper_move"                  # Move gripper to position

    # I/O Control
    SET_DIGITAL_OUTPUT = "set_digital_output"      # Set digital output
    WAIT_DIGITAL_INPUT = "wait_digital_input"      # Wait for digital input
    SET_ANALOG_OUTPUT = "set_analog_output"        # Set analog output
    READ_DIGITAL_INPUT = "read_digital_input"      # Read digital input

    # Safety Control
    EMERGENCY_STOP = "emergency_stop"              # Emergency stop

    # Loop Control
    REPEAT_START = "repeat_start"                  # Begin loop block
    REPEAT_END = "repeat_end"                      # End loop block

    # Subprogram Control
    CALL_SUBPROGRAM = "call_subprogram"            # Call a subprogram


# Action metadata: icons and friendly names
ACTION_METADATA = {
    ActionType.MOVE_TO_POSITION: {
        "icon": "📍",
        "name": "Add Waypoint",
        "description": "Add a waypoint with custom speed and movement type"
    },
    ActionType.RELATIVE_MOVE: {
        "icon": "📐",
        "name": "Relative Move",
        "description": "Move a small distance from current position"
    },
    ActionType.SAVE_POSITION: {
        "icon": "💾",
        "name": "Save Position",
        "description": "Save robot's current position"
    },
    ActionType.RETURN_HOME: {
        "icon": "🏠",
        "name": "Return Home",
        "description": "Return to safe starting position"
    },
    ActionType.ENABLE_FREEDRIVE: {
        "icon": "🤚",
        "name": "Enable Hand Guiding",
        "description": "Enable manual robot movement"
    },
    ActionType.DISABLE_FREEDRIVE: {
        "icon": "🛑",
        "name": "Disable Hand Guiding",
        "description": "End manual movement mode"
    },
    ActionType.WAIT: {
        "icon": "⏱️",
        "name": "Wait",
        "description": "Pause for specified time"
    },
    ActionType.ENABLE_FORCE: {
        "icon": "💪",
        "name": "Enable Force Mode",
        "description": "Enable force/pressure sensing and control"
    },
    ActionType.DISABLE_FORCE: {
        "icon": "🛑",
        "name": "Disable Force Mode",
        "description": "Turn off force control mode"
    },
    ActionType.SET_FORCE_LEVEL: {
        "icon": "⚖️",
        "name": "Set Force Level",
        "description": "Adjust force/pressure level"
    },
    ActionType.GRIPPER_OPEN: {
        "icon": "🤲",
        "name": "Open Gripper",
        "description": "Fully open robot gripper"
    },
    ActionType.GRIPPER_CLOSE: {
        "icon": "✊",
        "name": "Close Gripper",
        "description": "Fully close robot gripper"
    },
    ActionType.GRIPPER_MOVE: {
        "icon": "🤏",
        "name": "Move Gripper",
        "description": "Move gripper to specific position"
    },
    ActionType.SET_DIGITAL_OUTPUT: {
        "icon": "🔌",
        "name": "Set Digital Output",
        "description": "Set digital output pin (DO) high or low"
    },
    ActionType.WAIT_DIGITAL_INPUT: {
        "icon": "⏳",
        "name": "Wait for Digital Input",
        "description": "Wait until digital input pin (DI) reaches specified state"
    },
    ActionType.SET_ANALOG_OUTPUT: {
        "icon": "📊",
        "name": "Set Analog Output",
        "description": "Set analog output (AO) value"
    },
    ActionType.READ_DIGITAL_INPUT: {
        "icon": "📥",
        "name": "Read Digital Input",
        "description": "Read digital input pin (DI) state"
    },
    ActionType.EMERGENCY_STOP: {
        "icon": "🔴",
        "name": "Emergency Stop",
        "description": "Stop all motion immediately"
    },
    ActionType.REPEAT_START: {
        "icon": "🔁",
        "name": "Repeat Start",
        "description": "Begin a loop block (repeat actions)"
    },
    ActionType.REPEAT_END: {
        "icon": "🔚",
        "name": "Repeat End",
        "description": "End a loop block (return to start)"
    },
    ActionType.CALL_SUBPROGRAM: {
        "icon": "📦",
        "name": "Call Subprogram",
        "description": "Execute a saved subprogram sequence"
    }
}


# Action categories for organized display
ACTION_CATEGORIES = {
    "movement": {
        "name": "Movement",
        "icon": "🚀",
        "color": "#4CAF50",
        "description": "Robot movement and positioning actions",
        "actions": [
            ActionType.MOVE_TO_POSITION,
            ActionType.RELATIVE_MOVE,
            ActionType.RETURN_HOME,
        ]
    },
    "force": {
        "name": "Force Control",
        "icon": "💪",
        "color": "#FF5722",
        "description": "Force and pressure control actions",
        "actions": [
            ActionType.ENABLE_FORCE,
            ActionType.DISABLE_FORCE,
            ActionType.SET_FORCE_LEVEL,
        ]
    },
    "interaction": {
        "name": "Gripper",
        "icon": "🤲",
        "color": "#00BCD4",
        "description": "Gripper control actions",
        "actions": [
            ActionType.GRIPPER_OPEN,
            ActionType.GRIPPER_CLOSE,
            ActionType.GRIPPER_MOVE,
        ]
    },
    "io_control": {
        "name": "I/O Control",
        "icon": "🔌",
        "color": "#607D8B",
        "description": "Digital and analog input/output control",
        "actions": [
            ActionType.SET_DIGITAL_OUTPUT,
            ActionType.WAIT_DIGITAL_INPUT,
            ActionType.SET_ANALOG_OUTPUT,
            ActionType.READ_DIGITAL_INPUT,
        ]
    },
    "timing": {
        "name": "Timing",
        "icon": "⏱️",
        "color": "#2196F3",
        "description": "Time-based delays and pauses",
        "actions": [
            ActionType.WAIT,
        ]
    },
    "management": {
        "name": "Management",
        "icon": "🛠️",
        "color": "#9C27B0",
        "description": "Position and settings management",
        "actions": [
            ActionType.SAVE_POSITION,
        ]
    },
    "loops": {
        "name": "Loops",
        "icon": "🔁",
        "color": "#FF9800",
        "description": "Repeat action sequences",
        "actions": [
            ActionType.REPEAT_START,
            ActionType.REPEAT_END,
        ]
    },
    "subprograms": {
        "name": "Subprograms",
        "icon": "📦",
        "color": "#673AB7",
        "description": "Reusable action sequences",
        "actions": [
            ActionType.CALL_SUBPROGRAM,
        ]
    }
}


@dataclass
class Action:
    """Sequential action data class"""
    id: int
    action_type: ActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def get_icon(self) -> str:
        """Get action icon"""
        return ACTION_METADATA.get(self.action_type, {}).get("icon", "⚙️")

    def get_name(self) -> str:
        """Get action name"""
        return ACTION_METADATA.get(self.action_type, {}).get("name", "Unknown Action")

    def get_default_description(self) -> str:
        """Get default description"""
        return ACTION_METADATA.get(self.action_type, {}).get("description", "")

    def to_dict(self) -> dict:
        """Convert to dictionary format (for saving)"""
        return {
            "id": self.id,
            "type": self.action_type.value,
            "parameters": self.parameters,
            "description": self.description if self.description else self.get_default_description()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Action':
        """Create instance from dictionary (for loading)"""
        return cls(
            id=data["id"],
            action_type=ActionType(data["type"]),
            parameters=data.get("parameters", {}),
            description=data.get("description", "")
        )

    def get_display_text(self) -> str:
        """Get display text (icon + name + brief parameters)"""

        # Special format for MOVE_TO_POSITION (Add Waypoint)
        if self.action_type == ActionType.MOVE_TO_POSITION:
            waypoint_name = self.parameters.get("position_name", "?")
            # Capitalize first letter of waypoint name
            display_name = waypoint_name.capitalize()
            speed = self.parameters.get("speed_percent", 50)
            move_type = self.parameters.get("move_type", "moveJ")

            # Format the TCP pose
            tcp_pose = self.parameters.get("tcp_pose")
            if tcp_pose and isinstance(tcp_pose, list) and len(tcp_pose) == 6:
                # Format pose as [x, y, z, rx, ry, rz] with 3 decimal places
                pose_str = "[" + ", ".join([f"{p:.3f}" for p in tcp_pose]) + "]"
            else:
                pose_str = "no pose saved"

            return f"📍 {display_name}, {speed}%, {move_type}, {pose_str}"

        # Default format for other action types
        text = f"{self.get_icon()} {self.get_name()}"

        # Add parameter details based on action type
        if self.action_type == ActionType.WAIT:
            seconds = self.parameters.get("seconds", 0)
            text += f" ({seconds}s)"
        elif self.action_type == ActionType.RELATIVE_MOVE:
            direction = self.parameters.get("direction", "?")
            distance_cm = self.parameters.get("distance_cm", 0)
            text += f" ({direction}, {distance_cm}cm)"
        elif self.action_type == ActionType.SAVE_POSITION:
            pos_name = self.parameters.get("position_name", "?")
            text += f" ({pos_name})"
        elif self.action_type == ActionType.ENABLE_FORCE:
            force_level = self.parameters.get("force_level", "medium")
            text += f" ({force_level})"
        elif self.action_type == ActionType.SET_FORCE_LEVEL:
            force_level = self.parameters.get("force_level", "medium")
            text += f" ({force_level})"
        elif self.action_type == ActionType.GRIPPER_MOVE:
            position = self.parameters.get("position", 50)
            text += f" ({position}%)"
        elif self.action_type == ActionType.REPEAT_START:
            repeat_count = self.parameters.get("repeat_count", 1)
            text += f" (×{repeat_count})"
        elif self.action_type == ActionType.REPEAT_END:
            text += ""  # No additional text needed
        elif self.action_type == ActionType.CALL_SUBPROGRAM:
            # Display subprogram name and loop count if > 1
            subprogram_name = self.parameters.get("subprogram_name", "Unknown")
            loop_count = self.parameters.get("loop_count", 1)
            loop_text = f" × {loop_count}" if loop_count > 1 else ""
            text = f"📦 {subprogram_name}(){loop_text}"

        return text


class ExecutionThread(QThread):
    """Task execution thread"""
    progress_update = pyqtSignal(int, int)  # current_step, total_steps
    step_started = pyqtSignal(int, str)     # step_index, step_description
    step_completed = pyqtSignal(int, bool)  # step_index, success
    step_completed_with_timing = pyqtSignal(int, str, str, dict, float, bool, str)  # step_index, action_name, action_type, parameters, duration, success, error_msg
    execution_completed = pyqtSignal(bool)  # success
    error_occurred = pyqtSignal(str)        # error_message

    def __init__(self, controller, actions):
        super().__init__()
        self.controller = controller
        self.actions = actions
        self.should_stop = False
        self.paused = False
        self.loop_stack = []  # Stack of loop contexts: [(start_index, repeat_count, current_iteration), ...]
        self.call_stack = []  # Stack of subprogram calls: [{"name": str, "depth": int}, ...]
        self.execution_depth = 0  # Current execution depth (0 = main, 1+ = subprogram)

    def run(self):
        """Execute task sequence with loop support"""
        try:
            total_steps = len(self.actions)
            i = 0  # Current step index

            while i < len(self.actions):
                action = self.actions[i]

                # Check if should stop
                if self.should_stop:
                    logger.info("Execution stopped by user")
                    self.execution_completed.emit(False)
                    return

                # Check if paused
                while self.paused and not self.should_stop:
                    time.sleep(0.1)

                if self.should_stop:
                    self.execution_completed.emit(False)
                    return

                # Handle loop control actions
                if action.action_type == ActionType.REPEAT_START:
                    # Push loop context onto stack
                    repeat_count = action.parameters.get("repeat_count", 1)
                    self.loop_stack.append({
                        'start_index': i,
                        'repeat_count': repeat_count,
                        'current_iteration': 0
                    })
                    logger.debug(f"Loop start at index {i}, repeat {repeat_count} times")
                    i += 1
                    continue

                elif action.action_type == ActionType.REPEAT_END:
                    # Pop loop context and check if we should repeat
                    if not self.loop_stack:
                        error_msg = "REPEAT_END without matching REPEAT_START"
                        logger.error(error_msg)
                        self.error_occurred.emit(error_msg)
                        self.execution_completed.emit(False)
                        return

                    loop_context = self.loop_stack[-1]
                    loop_context['current_iteration'] += 1

                    if loop_context['current_iteration'] < loop_context['repeat_count']:
                        # Jump back to loop start
                        i = loop_context['start_index'] + 1  # Skip the REPEAT_START action
                        logger.debug(f"Loop iteration {loop_context['current_iteration']+1}/{loop_context['repeat_count']}, jumping to index {i}")
                        continue
                    else:
                        # Loop complete, pop from stack
                        self.loop_stack.pop()
                        logger.debug(f"Loop completed")
                        i += 1
                        continue

                # Emit step started signal
                self.step_started.emit(i, action.get_display_text())
                self.progress_update.emit(i + 1, total_steps)

                # Track execution time
                start_time = time.time()

                # Execute action
                success = self.controller._execute_action(action)

                # Calculate duration
                end_time = time.time()
                duration = end_time - start_time

                # Emit step completed signal (legacy, for backward compatibility)
                self.step_completed.emit(i, success)

                # Emit step completed with timing (new signal for history tracking)
                error_msg = "" if success else f"Step {i+1} failed: {action.get_display_text()}"
                self.step_completed_with_timing.emit(
                    i,
                    action.get_name(),
                    action.action_type.value,
                    action.parameters,
                    duration,
                    success,
                    error_msg
                )

                if not success:
                    logger.error(error_msg)
                    self.error_occurred.emit(error_msg)
                    self.execution_completed.emit(False)
                    return

                # Move to next action
                i += 1

            # All steps completed successfully
            logger.info("All steps completed successfully")
            self.execution_completed.emit(True)

        except Exception as e:
            logger.error(f"Execution thread error: {e}", exc_info=True)
            self.error_occurred.emit(f"Execution error: {str(e)}")
            self.execution_completed.emit(False)

    def stop(self):
        """Stop execution"""
        self.should_stop = True

    def pause(self):
        """Pause execution"""
        self.paused = True

    def resume(self):
        """Resume execution"""
        self.paused = False


class SequentialController(QObject):
    """Sequential Controller

    Manages the creation, editing, and execution of robot action sequences.
    """

    # Signal definitions
    sequence_changed = pyqtSignal()                 # Sequence content changed
    execution_started = pyqtSignal(int)             # Execution started (total steps)
    execution_progress = pyqtSignal(int, int)       # Execution progress (current, total)
    execution_step_started = pyqtSignal(int, str)   # Step started (index, description)
    execution_step_completed = pyqtSignal(int, bool)# Step completed (index, success)
    execution_step_completed_with_timing = pyqtSignal(int, str, str, dict, float, bool, str)  # Step completed with timing (step_index, action_name, action_type, parameters, duration, success, error_msg)
    execution_completed = pyqtSignal(bool)          # Execution completed (success)
    execution_paused = pyqtSignal()                 # Execution paused
    execution_resumed = pyqtSignal()                # Execution resumed
    error_occurred = pyqtSignal(str)                # Error occurred

    def __init__(self, robot_controller, parent=None):
        super().__init__(parent)
        self.robot_controller = robot_controller
        self.action_sequence: List[Action] = []
        self.next_action_id = 1
        self.is_executing = False
        self.execution_thread: Optional[ExecutionThread] = None
        self._stop_requested = False
        self.last_run_cancelled = False

        logger.info("SequentialController initialized")

    # ========================================
    # Sequence Management Methods
    # ========================================

    def add_action(self, action_type: ActionType, parameters: Dict[str, Any] = None,
                   description: str = "") -> Action:
        """Add action to end of sequence"""
        if parameters is None:
            parameters = {}

        action = Action(
            id=self.next_action_id,
            action_type=action_type,
            parameters=parameters,
            description=description
        )

        self.action_sequence.append(action)
        self.next_action_id += 1
        self.sequence_changed.emit()

        logger.info(f"Added action: {action.get_display_text()}")
        return action

    def insert_action(self, index: int, action_type: ActionType,
                     parameters: Dict[str, Any] = None, description: str = "") -> Action:
        """Insert action at specified position"""
        if parameters is None:
            parameters = {}

        action = Action(
            id=self.next_action_id,
            action_type=action_type,
            parameters=parameters,
            description=description
        )

        self.action_sequence.insert(index, action)
        self.next_action_id += 1
        self.sequence_changed.emit()

        logger.info(f"Inserted action at {index}: {action.get_display_text()}")
        return action

    def remove_action(self, action_id: int) -> bool:
        """Remove specified action"""
        for i, action in enumerate(self.action_sequence):
            if action.id == action_id:
                removed_action = self.action_sequence.pop(i)
                self.sequence_changed.emit()
                logger.info(f"Removed action: {removed_action.get_display_text()}")
                return True

        logger.warning(f"Action not found: id={action_id}")
        return False

    def remove_action_at(self, index: int) -> bool:
        """Remove action at specified index"""
        if 0 <= index < len(self.action_sequence):
            removed_action = self.action_sequence.pop(index)
            self.sequence_changed.emit()
            logger.info(f"Removed action at {index}: {removed_action.get_display_text()}")
            return True

        logger.warning(f"Invalid index: {index}")
        return False

    def move_action_up(self, index: int) -> bool:
        """Move action up one position"""
        if 0 < index < len(self.action_sequence):
            self.action_sequence[index], self.action_sequence[index-1] = \
                self.action_sequence[index-1], self.action_sequence[index]
            self.sequence_changed.emit()
            logger.info(f"Moved action up: index {index} -> {index-1}")
            return True
        return False

    def move_action_down(self, index: int) -> bool:
        """Move action down one position"""
        if 0 <= index < len(self.action_sequence) - 1:
            self.action_sequence[index], self.action_sequence[index+1] = \
                self.action_sequence[index+1], self.action_sequence[index]
            self.sequence_changed.emit()
            logger.info(f"Moved action down: index {index} -> {index+1}")
            return True
        return False

    def clear_sequence(self):
        """Clear sequence"""
        self.action_sequence.clear()
        self.sequence_changed.emit()
        logger.info("Sequence cleared")

    def get_action_count(self) -> int:
        """Get action count"""
        return len(self.action_sequence)

    def get_actions(self) -> List[Action]:
        """Get action list (copy)"""
        return self.action_sequence.copy()

    # ========================================
    # Task Execution Methods
    # ========================================

    def validate_loop_structure(self) -> Tuple[bool, str]:
        """
        Validate that all REPEAT_START have matching REPEAT_END.

        Returns:
            (valid, error_message): True if valid, False with error message if not
        """
        loop_stack = []

        for i, action in enumerate(self.action_sequence):
            if action.action_type == ActionType.REPEAT_START:
                loop_stack.append((i, action))
            elif action.action_type == ActionType.REPEAT_END:
                if not loop_stack:
                    return False, f"REPEAT_END at position {i+1} has no matching REPEAT_START"
                loop_stack.pop()

        if loop_stack:
            unmatched = [(idx+1) for idx, _ in loop_stack]
            return False, f"Unmatched REPEAT_START at position(s): {', '.join(map(str, unmatched))}"

        return True, ""

    def execute_sequence(self) -> bool:
        """Execute entire action sequence"""
        if self.is_executing:
            logger.warning("Already executing a sequence")
            return False

        if len(self.action_sequence) == 0:
            logger.warning("No actions to execute")
            self.error_occurred.emit("No actions to execute")
            return False

        # Validate loop structure
        valid, error_msg = self.validate_loop_structure()
        if not valid:
            logger.error(f"Loop validation failed: {error_msg}")
            self.error_occurred.emit(f"Loop structure error: {error_msg}")
            return False

        self._stop_requested = False
        self.last_run_cancelled = False
        self.is_executing = True
        total_steps = len(self.action_sequence)

        logger.info(f"Starting sequence execution: {total_steps} steps")
        self.execution_started.emit(total_steps)

        # Execute in new thread
        self.execution_thread = ExecutionThread(self, self.action_sequence)
        self.execution_thread.progress_update.connect(self.execution_progress.emit)
        self.execution_thread.step_started.connect(self.execution_step_started.emit)
        self.execution_thread.step_completed.connect(self.execution_step_completed.emit)
        self.execution_thread.step_completed_with_timing.connect(self.execution_step_completed_with_timing.emit)
        self.execution_thread.execution_completed.connect(self._on_execution_completed)
        self.execution_thread.error_occurred.connect(self.error_occurred.emit)
        self.execution_thread.start()

        return True

    def stop_execution(self):
        """Stop execution and halt robot immediately"""
        logger.info("Stop execution requested")
        self._stop_requested = True

        # First, stop the robot immediately
        try:
            if self.robot_controller.rtde_control:
                logger.info("Sending stop command to robot")
                self._halt_robot_motion(self.robot_controller.rtde_control)
                time.sleep(0.2)  # Brief pause to ensure stop is processed
        except Exception as e:
            logger.error(f"Failed to stop robot: {e}")

        # Then stop the execution thread
        if self.execution_thread and self.execution_thread.isRunning():
            logger.info("Stopping execution thread")
            self.execution_thread.stop()
            self.execution_thread.wait(3000)  # Wait max 3 seconds

            if self.execution_thread.isRunning():
                logger.warning("Force terminating execution thread")
                self.execution_thread.terminate()

    def pause_execution(self):
        """Pause execution"""
        if self.execution_thread and self.execution_thread.isRunning():
            logger.info("Pausing execution")
            self.execution_thread.pause()
            self.execution_paused.emit()

    def resume_execution(self):
        """Resume execution"""
        if self.execution_thread and self.execution_thread.isRunning():
            logger.info("Resuming execution")
            self.execution_thread.resume()
            self.execution_resumed.emit()

    def _on_execution_completed(self, success: bool):
        """Execution completed callback"""
        self.is_executing = False
        self.last_run_cancelled = self._stop_requested
        self._stop_requested = False
        self.execution_completed.emit(success)
        logger.info(f"Execution completed: success={success}")

    def _execute_action(self, action: Action) -> bool:
        """Execute single action (internal method, called by thread)"""
        try:
            logger.info(f"Executing action: {action.get_display_text()}")

            if action.action_type == ActionType.MOVE_TO_POSITION:
                return self._execute_move_to_position(action)

            elif action.action_type == ActionType.RELATIVE_MOVE:
                return self._execute_relative_move(action)

            elif action.action_type == ActionType.SAVE_POSITION:
                return self._execute_save_position(action)

            elif action.action_type == ActionType.RETURN_HOME:
                return self._execute_return_home(action)

            elif action.action_type == ActionType.ENABLE_FREEDRIVE:
                return self._execute_enable_freedrive(action)

            elif action.action_type == ActionType.DISABLE_FREEDRIVE:
                return self._execute_disable_freedrive(action)

            elif action.action_type == ActionType.WAIT:
                return self._execute_wait(action)

            elif action.action_type == ActionType.ENABLE_FORCE:
                return self._execute_enable_force(action)

            elif action.action_type == ActionType.DISABLE_FORCE:
                return self._execute_disable_force(action)

            elif action.action_type == ActionType.SET_FORCE_LEVEL:
                return self._execute_set_force_level(action)

            elif action.action_type == ActionType.GRIPPER_OPEN:
                return self._execute_gripper_open(action)

            elif action.action_type == ActionType.GRIPPER_CLOSE:
                return self._execute_gripper_close(action)

            elif action.action_type == ActionType.GRIPPER_MOVE:
                return self._execute_gripper_move(action)

            elif action.action_type == ActionType.SET_DIGITAL_OUTPUT:
                return self._execute_set_digital_output(action)

            elif action.action_type == ActionType.WAIT_DIGITAL_INPUT:
                return self._execute_wait_digital_input(action)

            elif action.action_type == ActionType.SET_ANALOG_OUTPUT:
                return self._execute_set_analog_output(action)

            elif action.action_type == ActionType.READ_DIGITAL_INPUT:
                return self._execute_read_digital_input(action)

            elif action.action_type == ActionType.EMERGENCY_STOP:
                return self._execute_emergency_stop(action)

            elif action.action_type == ActionType.CALL_SUBPROGRAM:
                return self._execute_call_subprogram(action)

            else:
                logger.warning(f"Action type not yet implemented: {action.action_type}")
                time.sleep(0.5)
                return True

        except Exception as e:
            logger.error(f"Error executing action: {e}", exc_info=True)
            return False

    def _execute_move_to_position(self, action: Action) -> bool:
        """Execute: Move to waypoint (using saved TCP pose)"""
        tcp_pose = action.parameters.get("tcp_pose")
        speed_percent = action.parameters.get("speed_percent", 50)
        move_type = action.parameters.get("move_type", "moveJ")

        if not tcp_pose or not isinstance(tcp_pose, list) or len(tcp_pose) != 6:
            logger.error("Missing or invalid tcp_pose parameter")
            return False

        # Convert speed_percent to actual speed
        # Define speeds for both movement types
        speed = (speed_percent / 100.0) * Config.DEFAULT_TCP_SPEED  # For moveL
        accel = Config.DEFAULT_TCP_ACCEL
        joint_speed = (speed_percent / 100.0) * Config.DEFAULT_JOINT_SPEED  # For moveJ
        joint_accel = Config.DEFAULT_JOINT_ACCEL

        # Execute movement
        try:
            if not self.robot_controller.is_connected():
                logger.error("Robot not connected")
                return False

            rtde_control = self.robot_controller.rtde_control
            if rtde_control is None:
                logger.error("RTDE control interface not available")
                return False

            logger.info(f"Moving to waypoint using {move_type}: {tcp_pose}, speed: {speed_percent}%")

            # Execute movement based on type
            if move_type == "moveL":
                # Linear movement - straight line path (cartesian space)
                result = rtde_control.moveL(tcp_pose, speed, accel, asynchronous=True)
            else:  # moveJ
                # Joint movement - curved path (joint space)
                # Use moveJ_IK which accepts TCP pose and does inverse kinematics automatically
                result = rtde_control.moveJ_IK(tcp_pose, joint_speed, joint_accel, asynchronous=True)

            if not result:
                logger.error("Failed to start waypoint movement")
                return False

            # Wait for movement to complete, checking for stop signal
            # Use getAsyncOperationProgress() to check if movement is still in progress
            rtde_receive = self.robot_controller.rtde_receive
            if rtde_receive is None:
                logger.error("RTDE receive interface not available for progress check")
                return False

            while True:
                # Check if should stop
                if self.execution_thread and self.execution_thread.should_stop:
                    logger.warning("Stop requested during movement - stopping robot")
                    self._halt_robot_motion(rtde_control, move_type)
                    time.sleep(0.2)  # Give time for robot to stop
                    return False

                # Check if paused - wait until resumed or stopped
                if self.execution_thread and self.execution_thread.paused:
                    logger.info("Pause requested during movement - pausing robot")
                    self._halt_robot_motion(rtde_control, move_type)
                    time.sleep(0.2)  # Wait for stop to complete

                    # Wait while paused
                    while self.execution_thread.paused and not self.execution_thread.should_stop:
                        time.sleep(0.1)

                    # If stopped during pause, exit
                    if self.execution_thread.should_stop:
                        logger.warning("Stop requested while paused")
                        return False

                    # If resumed, restart movement from current position to target
                    logger.info("Resuming from pause - restarting movement to target")

                    # Restart the movement command
                    if move_type == "moveL":
                        result = rtde_control.moveL(tcp_pose, speed, accel, asynchronous=True)
                    else:  # moveJ
                        result = rtde_control.moveJ_IK(tcp_pose, joint_speed, joint_accel, asynchronous=True)

                    if not result:
                        logger.error("Failed to restart movement after resume")
                        return False

                    logger.info("Movement restarted after resume")

                # Check if movement is complete using async operation progress
                # Returns value < 0 when operation is complete
                progress = rtde_control.getAsyncOperationProgress()
                if progress < 0:
                    # Movement complete
                    break

                # Also check TCP speed as backup - if near zero and progress shows done, movement finished
                tcp_speed = self._get_tcp_speed_magnitude(rtde_receive)
                if progress < 0 or (tcp_speed < 0.001 and progress >= 1.0):
                    break

                time.sleep(0.05)  # Check every 50ms

            logger.info(f"Waypoint movement completed successfully")
            return True

        except Exception as e:
            logger.error(f"Waypoint movement failed: {e}", exc_info=True)
            # Try to stop robot if error occurs
            try:
                if self.robot_controller.rtde_control:
                    self._halt_robot_motion(self.robot_controller.rtde_control, move_type)
            except:
                pass
            return False

    @staticmethod
    def _get_tcp_speed_magnitude(rtde_receive) -> float:
        """Return the scalar TCP speed based on the receive interface data."""
        if not rtde_receive:
            return 0.0

        raw_speed = rtde_receive.getActualTCPSpeed()
        if raw_speed is None:
            return 0.0

        if isinstance(raw_speed, (int, float)):
            return float(raw_speed)

        try:
            components = list(raw_speed)
        except TypeError:
            return 0.0

        if not components:
            return 0.0

        linear_components = components[:3]
        return math.sqrt(sum(val * val for val in linear_components))

    def _halt_robot_motion(self, rtde_control=None, move_type: Optional[str] = None):
        """
        Attempt a gentle robot stop. Falls back to stopScript only if soft stop fails.
        """
        if rtde_control is None:
            rtde_control = getattr(self.robot_controller, "rtde_control", None)

        if rtde_control is None:
            return

        joint_decel = max(Config.DEFAULT_JOINT_ACCEL, 0.1)
        linear_decel = max(Config.DEFAULT_TCP_ACCEL, 0.1)

        try:
            if move_type == "moveL" and hasattr(rtde_control, "stopL"):
                rtde_control.stopL(linear_decel)
                return

            if hasattr(rtde_control, "stopJ"):
                rtde_control.stopJ(joint_decel)
                return
        except Exception as e:
            logger.warning(f"Gentle stop failed ({e}), falling back to stopScript")

        try:
            rtde_control.stopScript()
        except Exception as e:
            logger.error(f"Failed to stop robot motion: {e}")

    def _execute_relative_move(self, action: Action) -> bool:
        """Execute: Relative move"""
        direction = action.parameters.get("direction", "down")
        distance_cm = action.parameters.get("distance_cm", 5)
        speed_str = action.parameters.get("speed", "medium")

        # Convert to meters
        distance = distance_cm / 100.0
        speed = self._convert_speed(speed_str)

        # Calculate relative displacement based on direction
        dx, dy, dz = 0, 0, 0
        direction_map = {
            "up": (0, 0, distance),
            "down": (0, 0, -distance),
            "left": (-distance, 0, 0),
            "right": (distance, 0, 0),
            "forward": (0, distance, 0),
            "backward": (0, -distance, 0)
        }

        dx, dy, dz = direction_map.get(direction, (0, 0, 0))

        # Execute relative movement
        return self.robot_controller.move_tcp(dx, dy, dz, 0, 0, 0,
                                              speed=speed, relative=True)

    def _execute_save_position(self, action: Action) -> bool:
        """Execute: Save position"""
        position_name = action.parameters.get("position_name")
        description = action.parameters.get("description", "")

        if not position_name:
            logger.error("Missing position_name parameter")
            return False

        # Get current joint positions
        current_joints = self.robot_controller.get_current_joint_positions()

        if not current_joints or len(current_joints) != 6:
            logger.error("Failed to get current joint positions")
            return False

        # Save position to Config
        success = Config.add_preset_position(position_name, current_joints, description)

        if success:
            logger.info(f"Position saved: {position_name}")

        return success

    def _execute_return_home(self, action: Action) -> bool:
        """Execute: Return home"""
        speed_str = action.parameters.get("speed", "medium")
        speed = self._convert_speed(speed_str)

        return self.robot_controller.move_to_preset("home", speed=speed)

    def _execute_enable_freedrive(self, action: Action) -> bool:
        """Execute: Enable hand guiding"""
        return self.robot_controller.enable_freedrive()

    def _execute_disable_freedrive(self, action: Action) -> bool:
        """Execute: Disable hand guiding"""
        return self.robot_controller.disable_freedrive()

    def _execute_wait(self, action: Action) -> bool:
        """Execute: Wait (interruptible)"""
        seconds = action.parameters.get("seconds", 1)

        # Use small sleep intervals to allow interruption
        elapsed = 0.0
        sleep_interval = 0.1  # Check every 100ms

        while elapsed < seconds:
            # Check if should stop
            if self.execution_thread and self.execution_thread.should_stop:
                logger.info("Wait interrupted by stop")
                return False

            # Check if paused
            while self.execution_thread and self.execution_thread.paused:
                if self.execution_thread.should_stop:
                    return False
                time.sleep(0.1)

            # Sleep for a short interval
            time.sleep(min(sleep_interval, seconds - elapsed))
            elapsed += sleep_interval

        return True

    def _execute_emergency_stop(self, action: Action) -> bool:
        """Execute: Emergency stop"""
        return self.robot_controller.stop_motion()

    def _execute_enable_force(self, action: Action) -> bool:
        """Execute: Enable force mode"""
        force_level = action.parameters.get("force_level", "medium")

        # Check if force control is available
        if not hasattr(self.robot_controller, 'start_force_mode'):
            logger.warning("Force control not available on this robot")
            return True  # Don't fail, just skip

        # Enable force mode
        success = self.robot_controller.start_force_mode()

        if success and force_level:
            # Set force level if specified
            self._set_force_level_internal(force_level)

        return success

    def _execute_disable_force(self, action: Action) -> bool:
        """Execute: Disable force mode"""
        if not hasattr(self.robot_controller, 'stop_force_mode'):
            logger.warning("Force control not available on this robot")
            return True  # Don't fail, just skip

        return self.robot_controller.stop_force_mode()

    def _execute_set_force_level(self, action: Action) -> bool:
        """Execute: Set force level"""
        force_level = action.parameters.get("force_level", "medium")
        return self._set_force_level_internal(force_level)

    def _set_force_level_internal(self, force_level: str) -> bool:
        """Set force level (internal helper)"""
        # Map force level to actual force value
        force_map = {
            "gentle": 5.0,    # 5N
            "medium": 10.0,   # 10N
            "strong": 15.0,   # 15N
        }

        force_value = force_map.get(force_level, 10.0)

        # Set force threshold (if robot controller supports it)
        if hasattr(self.robot_controller, 'set_force_threshold'):
            return self.robot_controller.set_force_threshold(force_value)

        # Otherwise, just log
        logger.info(f"Force level set to: {force_level} ({force_value}N)")
        return True

    def _execute_gripper_open(self, action: Action) -> bool:
        """Execute: Open gripper"""
        # Check if gripper is available
        if not hasattr(self.robot_controller, 'open_gripper'):
            logger.info("[SIMULATION] Opening gripper (hardware not available)")
            time.sleep(1.0)  # Simulate gripper action time
            return True

        return self.robot_controller.open_gripper()

    def _execute_gripper_close(self, action: Action) -> bool:
        """Execute: Close gripper"""
        # Check if gripper is available
        if not hasattr(self.robot_controller, 'close_gripper'):
            logger.info("[SIMULATION] Closing gripper (hardware not available)")
            time.sleep(1.0)  # Simulate gripper action time
            return True

        return self.robot_controller.close_gripper()

    def _execute_gripper_move(self, action: Action) -> bool:
        """Execute: Move gripper to position"""
        position = action.parameters.get("position", 50)  # 0-100%

        # Check if gripper position control is available
        if not hasattr(self.robot_controller, 'set_gripper_position'):
            logger.info(f"[SIMULATION] Moving gripper to {position}% (hardware not available)")
            time.sleep(1.0)  # Simulate gripper action time
            return True

        return self.robot_controller.set_gripper_position(position)

    def _execute_set_digital_output(self, action: Action) -> bool:
        """Execute: Set digital output"""
        pin = action.parameters.get("pin", 0)  # DO pin number
        state = action.parameters.get("state", "high")  # "high" or "low"

        # Check if digital I/O is available
        if not hasattr(self.robot_controller, 'set_digital_output'):
            logger.info(f"[SIMULATION] Setting DO{pin} to {state} (I/O not available)")
            return True

        value = 1 if state == "high" else 0
        return self.robot_controller.set_digital_output(pin, value)

    def _execute_wait_digital_input(self, action: Action) -> bool:
        """Execute: Wait for digital input (interruptible)"""
        pin = action.parameters.get("pin", 0)  # DI pin number
        state = action.parameters.get("state", "high")  # "high" or "low"
        timeout = action.parameters.get("timeout", 30)  # seconds

        # Check if digital I/O is available
        if not hasattr(self.robot_controller, 'read_digital_input'):
            logger.info(f"[SIMULATION] Waiting for DI{pin} to be {state} (I/O not available)")
            time.sleep(1.0)  # Simulate wait
            return True

        # Wait for digital input to reach specified state
        import time as time_module
        start_time = time_module.time()
        expected_value = 1 if state == "high" else 0

        while time_module.time() - start_time < timeout:
            # Check if should stop
            if self.execution_thread and self.execution_thread.should_stop:
                logger.info("Wait for digital input interrupted by stop")
                return False

            # Check if paused
            while self.execution_thread and self.execution_thread.paused:
                if self.execution_thread.should_stop:
                    return False
                time_module.sleep(0.1)

            # Check digital input
            current_value = self.robot_controller.read_digital_input(pin)
            if current_value == expected_value:
                return True

            time_module.sleep(0.1)  # Check every 100ms

        logger.warning(f"Timeout waiting for DI{pin} to be {state}")
        return False

    def _execute_set_analog_output(self, action: Action) -> bool:
        """Execute: Set analog output"""
        pin = action.parameters.get("pin", 0)  # AO pin number
        value = action.parameters.get("value", 0.0)  # Analog value (0-1 or specific range)

        # Check if analog I/O is available
        if not hasattr(self.robot_controller, 'set_analog_output'):
            logger.info(f"[SIMULATION] Setting AO{pin} to {value} (I/O not available)")
            return True

        return self.robot_controller.set_analog_output(pin, value)

    def _execute_read_digital_input(self, action: Action) -> bool:
        """Execute: Read digital input"""
        pin = action.parameters.get("pin", 0)  # DI pin number

        # Check if digital I/O is available
        if not hasattr(self.robot_controller, 'read_digital_input'):
            logger.info(f"[SIMULATION] Reading DI{pin} (I/O not available)")
            return True

        value = self.robot_controller.read_digital_input(pin)
        logger.info(f"DI{pin} = {value}")
        return True

    def _execute_call_subprogram(self, action: Action) -> bool:
        """Execute: Call subprogram with error handling strategies"""
        subprogram_id = action.parameters.get("subprogram_id")
        parameter_values = action.parameters.get("parameter_values", {})
        loop_count = action.parameters.get("loop_count", 1)
        error_handling = action.parameters.get("error_handling", "stop")  # stop, skip, retry

        if not subprogram_id:
            logger.error("Missing subprogram_id in CALL_SUBPROGRAM action")
            return False

        # Get subprogram manager
        from subprogram_manager import SubProgramManager
        manager = SubProgramManager.get_instance()

        # Get subprogram
        subprogram = manager.get_subprogram(subprogram_id)
        if not subprogram:
            logger.error(f"Subprogram not found: {subprogram_id}")
            return False

        logger.info(f"Executing subprogram: {subprogram.name} (loop_count={loop_count}, error_handling={error_handling})")

        # Push to call stack
        if self.execution_thread:
            self.execution_thread.execution_depth += 1
            self.execution_thread.call_stack.append({
                "name": subprogram.name,
                "depth": self.execution_thread.execution_depth,
                "subprogram_id": subprogram_id
            })

        try:
            # Execute the subprogram loop_count times
            for i in range(loop_count):
                if loop_count > 1:
                    logger.info(f"Subprogram iteration {i+1}/{loop_count}")

                # Instantiate subprogram with parameters
                instantiated_actions = manager.instantiate_subprogram(
                    subprogram_id, parameter_values
                )

                # Execute each action in the subprogram
                for sub_idx, sub_action in enumerate(instantiated_actions):
                    # Check if should stop
                    if self.execution_thread and self.execution_thread.should_stop:
                        logger.warning("Stop requested during subprogram execution")
                        return False

                    # Check if paused
                    while self.execution_thread and self.execution_thread.paused:
                        if self.execution_thread.should_stop:
                            return False
                        time.sleep(0.1)

                    # Execute the sub-action with error handling
                    success = False
                    retry_count = 3 if error_handling == "retry" else 1

                    for attempt in range(retry_count):
                        if attempt > 0:
                            logger.info(f"Retry attempt {attempt+1}/{retry_count} for: {sub_action.get_display_text()}")
                            time.sleep(0.5)  # Brief delay before retry

                        success = self._execute_action(sub_action)

                        if success:
                            break  # Success, no need to retry

                    # Handle failure based on error strategy
                    if not success:
                        error_msg = f"Subprogram '{subprogram.name}' action {sub_idx+1} failed: {sub_action.get_display_text()}"
                        logger.error(error_msg)

                        if error_handling == "stop":
                            # Stop execution immediately
                            return False
                        elif error_handling == "skip":
                            # Skip remaining actions in this subprogram iteration
                            logger.warning(f"Skipping remaining actions in subprogram '{subprogram.name}'")
                            break  # Break inner loop, continue with next iteration
                        elif error_handling == "retry":
                            # Already retried above, if still failed then stop
                            logger.error(f"Retry limit exceeded for subprogram '{subprogram.name}'")
                            return False

            logger.info(f"Subprogram completed: {subprogram.name}")
            return True

        finally:
            # Pop from call stack
            if self.execution_thread and self.execution_thread.call_stack:
                self.execution_thread.call_stack.pop()
                self.execution_thread.execution_depth -= 1

    # ========================================
    # Helper Conversion Methods
    # ========================================

    def _convert_speed(self, speed_str: str) -> float:
        """Convert speed string to numeric value"""
        speed_map = {
            "slow": Config.DEFAULT_TCP_SPEED * 0.5,
            "medium": Config.DEFAULT_TCP_SPEED,
            "fast": Config.DEFAULT_TCP_SPEED * 1.5
        }
        return speed_map.get(speed_str, Config.DEFAULT_TCP_SPEED)

    # ========================================
    # Task Save and Load
    # ========================================

    def save_to_file(self, filepath: str, task_name: str = "",
                     description: str = "") -> bool:
        """Save task to file"""
        try:
            task_data = {
                "task_name": task_name,
                "description": description,
                "created_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0",
                "actions": [action.to_dict() for action in self.action_sequence]
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Task saved to: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save task: {e}", exc_info=True)
            self.error_occurred.emit(f"Failed to save task: {str(e)}")
            return False

    def load_from_file(self, filepath: str) -> bool:
        """Load task from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                task_data = json.load(f)

            # Clear current sequence
            self.action_sequence.clear()

            # Load actions
            max_id = 0
            for action_dict in task_data.get("actions", []):
                action = Action.from_dict(action_dict)
                self.action_sequence.append(action)
                max_id = max(max_id, action.id)

            # Update next ID
            self.next_action_id = max_id + 1

            self.sequence_changed.emit()
            logger.info(f"Task loaded from: {filepath}, {len(self.action_sequence)} actions")
            return True

        except Exception as e:
            logger.error(f"Failed to load task: {e}", exc_info=True)
            self.error_occurred.emit(f"Failed to load task: {str(e)}")
            return False

    def get_task_info(self, filepath: str) -> Optional[Dict[str, str]]:
        """Read task file information (without loading actions)"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                task_data = json.load(f)

            return {
                "task_name": task_data.get("task_name", "Untitled Task"),
                "description": task_data.get("description", ""),
                "created_date": task_data.get("created_date", ""),
                "action_count": len(task_data.get("actions", []))
            }
        except Exception as e:
            logger.error(f"Failed to read task info: {e}")
            return None
