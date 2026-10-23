"""
Enhanced Sequential Controller Dialog Module

Provides enhanced parameter dialogs with presets, help text, and better UX.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QDialog, QDialogButtonBox, QFrame, QScrollArea, QRadioButton
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from sequential_controller import ActionType, ACTION_METADATA
from force_control import ForceConfig, resolve_target_force
from parameter_widgets import (
    PresetButtonGroup, ParameterHelpText, SliderWithValue,
    PinSelector, StateSelector, SectionHeader
)

logger = logging.getLogger(__name__)


class EnhancedActionParameterDialog(QDialog):
    """
    Enhanced action parameter editing dialog with presets and help text.

    Supports all action types with improved UX.
    """

    def __init__(self, action_type: ActionType, parameters: dict = None, parent=None):
        super().__init__(parent)
        self.action_type = action_type
        self.parameters = parameters.copy() if parameters else {}
        self.widgets = {}  # Store widgets for later retrieval
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        metadata = ACTION_METADATA.get(self.action_type, {})
        self.setWindowTitle(f"Set Parameters - {metadata.get('name', 'Unknown Action')}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title with icon
        title_layout = QHBoxLayout()
        icon_label = QLabel(metadata.get('icon', '⚙️'))
        icon_label.setStyleSheet("font-size: 32px;")
        title_layout.addWidget(icon_label)

        title_label = QLabel(metadata.get('name', 'Unknown Action'))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Description
        desc_label = QLabel(metadata.get('description', ''))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            QLabel {
                color: #555;
                padding: 10px;
                background-color: #F8F9FA;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        layout.addWidget(desc_label)

        # Scroll area for parameters (in case of many parameters)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        self.form_layout = QVBoxLayout(content_widget)
        self.form_layout.setSpacing(15)

        # Add parameter inputs based on action type
        self._add_parameters_for_action_type()

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area, 1)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _add_parameters_for_action_type(self):
        """Add parameter inputs based on action type"""
        if self.action_type == ActionType.MOVE_TO_POSITION:
            self._add_move_to_position_params()

        elif self.action_type == ActionType.RELATIVE_MOVE:
            self._add_relative_move_params()

        elif self.action_type == ActionType.RETURN_HOME:
            self._add_return_home_params()

        elif self.action_type == ActionType.SAVE_POSITION:
            self._add_save_position_params()

        elif self.action_type == ActionType.WAIT:
            self._add_wait_params()

        elif self.action_type == ActionType.ENABLE_FREEDRIVE:
            self._add_enable_freedrive_params()

        elif self.action_type == ActionType.DISABLE_FREEDRIVE:
            self._add_disable_freedrive_params()

        elif self.action_type == ActionType.ENABLE_FORCE:
            self._add_enable_force_params()

        elif self.action_type == ActionType.DISABLE_FORCE:
            self._add_disable_force_params()

        elif self.action_type == ActionType.SET_FORCE_LEVEL:
            self._add_set_force_level_params()

        elif self.action_type == ActionType.GRIPPER_OPEN:
            self._add_gripper_open_params()

        elif self.action_type == ActionType.GRIPPER_CLOSE:
            self._add_gripper_close_params()

        elif self.action_type == ActionType.GRIPPER_MOVE:
            self._add_gripper_move_params()

        elif self.action_type == ActionType.SET_DIGITAL_OUTPUT:
            self._add_set_digital_output_params()

        elif self.action_type == ActionType.WAIT_DIGITAL_INPUT:
            self._add_wait_digital_input_params()

        elif self.action_type == ActionType.SET_ANALOG_OUTPUT:
            self._add_set_analog_output_params()

        elif self.action_type == ActionType.READ_DIGITAL_INPUT:
            self._add_read_digital_input_params()

        elif self.action_type == ActionType.EMERGENCY_STOP:
            self._add_emergency_stop_params()

        elif self.action_type == ActionType.REPEAT_START:
            self._add_repeat_start_params()

        elif self.action_type == ActionType.REPEAT_END:
            self._add_repeat_end_params()

        else:
            # Generic parameter handler
            self._add_generic_params()

    def _add_move_to_position_params(self):
        """Add parameters for Add Waypoint"""
        self.form_layout.addWidget(SectionHeader("Waypoint Name"))

        # Waypoint name input (editable text field)
        self.widgets['waypoint_name'] = QLineEdit()
        current_name = self.parameters.get("position_name", "waypoint1")
        self.widgets['waypoint_name'].setText(current_name)
        self.widgets['waypoint_name'].setPlaceholderText("e.g., waypoint1, pick_point, etc.")

        form = QFormLayout()
        form.addRow("Waypoint Name:", self.widgets['waypoint_name'])
        self.form_layout.addLayout(form)

        # Help text
        self.form_layout.addWidget(ParameterHelpText(
            "Enter a name for this waypoint. The robot will move to its current position when this waypoint is reached."
        ))

        # Speed presets
        self.form_layout.addWidget(SectionHeader("Movement Speed"))
        speed_presets = {"Slow (20%)": 20, "Medium (50%)": 50, "Fast (80%)": 80, "Full (100%)": 100}
        current_speed = self.parameters.get("speed_percent", 50)

        # Find matching preset or default to Medium
        default_key = "Medium (50%)"
        for key, val in speed_presets.items():
            if val == current_speed:
                default_key = key
                break

        self.widgets['speed_preset'] = PresetButtonGroup(speed_presets, default_key)
        self.form_layout.addWidget(self.widgets['speed_preset'])

        # Custom speed input
        self.widgets['speed_spin'] = QSpinBox()
        self.widgets['speed_spin'].setRange(1, 100)
        self.widgets['speed_spin'].setValue(current_speed)
        self.widgets['speed_spin'].setSuffix(" %")

        # Connect preset to spin box
        self.widgets['speed_preset'].value_changed.connect(
            lambda v: self.widgets['speed_spin'].setValue(v)
        )

        form2 = QFormLayout()
        form2.addRow("Custom Speed:", self.widgets['speed_spin'])
        self.form_layout.addLayout(form2)

        self.form_layout.addWidget(ParameterHelpText(
            "Speed affects how fast the robot moves. Use presets for common speeds or enter a custom value (1-100%)."
        ))

        # Movement type selector
        self.form_layout.addWidget(SectionHeader("Movement Type"))

        current_move_type = self.parameters.get("move_type", "moveJ")

        # Radio buttons for movement type
        self.widgets['moveJ_radio'] = QRadioButton("moveJ (Joint movement)")
        self.widgets['moveL_radio'] = QRadioButton("moveL (Linear movement)")

        # Set default
        if current_move_type == "moveL":
            self.widgets['moveL_radio'].setChecked(True)
        else:
            self.widgets['moveJ_radio'].setChecked(True)

        move_type_layout = QVBoxLayout()
        move_type_layout.addWidget(self.widgets['moveJ_radio'])
        move_type_layout.addWidget(self.widgets['moveL_radio'])
        self.form_layout.addLayout(move_type_layout)

        self.form_layout.addWidget(ParameterHelpText(
            "moveJ: Robot moves joints to reach position (faster, curved path). "
            "moveL: Robot moves in a straight line (slower, precise path)."
        ))

    def _add_relative_move_params(self):
        """Add parameters for Relative Move"""
        self.form_layout.addWidget(SectionHeader("Movement Direction"))

        # Direction selector
        self.widgets['direction_combo'] = QComboBox()
        directions = ["Up (+Z)", "Down (-Z)", "Left (-Y)", "Right (+Y)", "Forward (+X)", "Backward (-X)"]
        self.widgets['direction_combo'].addItems(directions)

        direction_map = {"up": 0, "down": 1, "left": 2, "right": 3, "forward": 4, "backward": 5}
        current = self.parameters.get("direction", "down")
        self.widgets['direction_combo'].setCurrentIndex(direction_map.get(current, 1))

        form = QFormLayout()
        form.addRow("Direction:", self.widgets['direction_combo'])
        self.form_layout.addLayout(form)

        # Distance with presets
        self.form_layout.addWidget(SectionHeader("Movement Distance"))

        distance_presets = {"Short (5cm)": 5, "Medium (20cm)": 20, "Long (50cm)": 50}
        current_distance = self.parameters.get("distance_cm", 20)

        default_key = "Medium (20cm)"
        for key, val in distance_presets.items():
            if val == current_distance:
                default_key = key
                break

        self.widgets['distance_preset'] = PresetButtonGroup(distance_presets, default_key)
        self.form_layout.addWidget(self.widgets['distance_preset'])

        # Custom distance input
        self.widgets['distance_spin'] = QSpinBox()
        self.widgets['distance_spin'].setRange(1, 100)
        self.widgets['distance_spin'].setValue(current_distance)
        self.widgets['distance_spin'].setSuffix(" cm")

        # Connect preset to spin box
        self.widgets['distance_preset'].value_changed.connect(
            lambda v: self.widgets['distance_spin'].setValue(v)
        )

        form2 = QFormLayout()
        form2.addRow("Custom Distance:", self.widgets['distance_spin'])
        self.form_layout.addLayout(form2)

        self.form_layout.addWidget(ParameterHelpText(
            "Relative move shifts the robot from its current position."
        ))

    def _add_return_home_params(self):
        """Add parameters for Return Home"""
        self.form_layout.addWidget(ParameterHelpText(
            "Returns the robot to its safe starting position. No additional parameters required."
        ))

    def _add_save_position_params(self):
        """Add parameters for Save Position"""
        self.form_layout.addWidget(SectionHeader("Position Information"))

        # Position name
        self.widgets['position_name'] = QLineEdit()
        self.widgets['position_name'].setText(self.parameters.get("position_name", ""))
        self.widgets['position_name'].setPlaceholderText("e.g., pick_position_1")

        # Description
        self.widgets['description'] = QLineEdit()
        self.widgets['description'].setText(self.parameters.get("description", ""))
        self.widgets['description'].setPlaceholderText("Optional: Brief description")

        form = QFormLayout()
        form.addRow("Position Name:", self.widgets['position_name'])
        form.addRow("Description:", self.widgets['description'])
        self.form_layout.addLayout(form)

        self.form_layout.addWidget(ParameterHelpText(
            "Save the current robot position with a memorable name for later use."
        ))

    def _add_wait_params(self):
        """Add parameters for Wait"""
        self.form_layout.addWidget(SectionHeader("Wait Duration"))

        # Duration presets
        duration_presets = {"Quick (1s)": 1, "Short (3s)": 3, "Medium (5s)": 5, "Long (10s)": 10}
        current_duration = self.parameters.get("seconds", 5)

        default_key = "Medium (5s)"
        for key, val in duration_presets.items():
            if val == current_duration:
                default_key = key
                break

        self.widgets['duration_preset'] = PresetButtonGroup(duration_presets, default_key)
        self.form_layout.addWidget(self.widgets['duration_preset'])

        # Custom duration
        self.widgets['duration_spin'] = QSpinBox()
        self.widgets['duration_spin'].setRange(1, 600)
        self.widgets['duration_spin'].setValue(current_duration)
        self.widgets['duration_spin'].setSuffix(" seconds")

        # Connect preset to spin box
        self.widgets['duration_preset'].value_changed.connect(
            lambda v: self.widgets['duration_spin'].setValue(v)
        )

        form = QFormLayout()
        form.addRow("Custom Duration:", self.widgets['duration_spin'])
        self.form_layout.addLayout(form)

        self.form_layout.addWidget(ParameterHelpText(
            "Pauses execution for the specified duration. Useful for waiting for external events."
        ))

    def _add_enable_freedrive_params(self):
        """Add parameters for Enable Freedrive/Hand Guiding"""
        self.form_layout.addWidget(ParameterHelpText(
            "Enables hand guiding mode. You can manually move the robot by hand. "
            "Useful for teaching positions or demonstrating movements."
        ))

    def _add_disable_freedrive_params(self):
        """Add parameters for Disable Freedrive/Hand Guiding"""
        self.form_layout.addWidget(ParameterHelpText(
            "Disables hand guiding mode. The robot returns to normal programmed control."
        ))

    def _add_enable_force_params(self):
        """Add parameters for Enable Force Mode"""
        self.form_layout.addWidget(SectionHeader("Force Mode Settings"))

        # Named force levels from ForceConfig (gentle/medium/strong)
        force_presets = {
            f"{name.capitalize()} ({newtons:.0f}N)": int(newtons)
            for name, newtons in ForceConfig.FORCE_LEVELS.items()
        }
        current_force = resolve_target_force(self.parameters)

        default_key = next(
            (key for key, val in force_presets.items() if val == current_force),
            list(force_presets)[0],
        )

        self.widgets['force_preset'] = PresetButtonGroup(force_presets, default_key)
        self.form_layout.addWidget(self.widgets['force_preset'])

        self.form_layout.addWidget(ParameterHelpText(
            "Force mode enables pressure sensing. Lower values are more sensitive. "
            "Use for safe human-robot interaction."
        ))

    def _add_disable_force_params(self):
        """Add parameters for Disable Force Mode"""
        self.form_layout.addWidget(ParameterHelpText(
            "Disables force sensing mode. The robot will operate at normal speed and force."
        ))

    def _add_set_force_level_params(self):
        """Add parameters for Set Force Level"""
        self.form_layout.addWidget(SectionHeader("Force Level"))

        # Force slider
        current_force = resolve_target_force(self.parameters)
        self.widgets['force_slider'] = SliderWithValue(
            1, int(ForceConfig.MAX_TARGET_FORCE), int(round(current_force)), "N"
        )
        self.form_layout.addWidget(self.widgets['force_slider'])

        self.form_layout.addWidget(ParameterHelpText(
            "Adjust the force threshold. Lower values make the robot more sensitive to contact."
        ))

    def _add_gripper_open_params(self):
        """Add parameters for Gripper Open"""
        self.form_layout.addWidget(ParameterHelpText(
            "Fully opens the gripper. No additional parameters required."
        ))

    def _add_gripper_close_params(self):
        """Add parameters for Gripper Close"""
        self.form_layout.addWidget(ParameterHelpText(
            "Fully closes the gripper. No additional parameters required."
        ))

    def _add_gripper_move_params(self):
        """Add parameters for Gripper Move"""
        self.form_layout.addWidget(SectionHeader("Gripper Position"))

        # Position slider
        current_pos = self.parameters.get("position_percent", 50)
        self.widgets['gripper_slider'] = SliderWithValue(0, 100, current_pos, "%")
        self.form_layout.addWidget(self.widgets['gripper_slider'])

        self.form_layout.addWidget(ParameterHelpText(
            "0% = fully open, 100% = fully closed. Adjust to control gripper opening width."
        ))

    def _add_set_digital_output_params(self):
        """Add parameters for Set Digital Output"""
        self.form_layout.addWidget(SectionHeader("Digital Output Settings"))

        # Pin selector
        current_pin = self.parameters.get("pin", 0)
        self.widgets['pin_selector'] = PinSelector("digital", current_pin)
        self.form_layout.addWidget(self.widgets['pin_selector'])

        # State selector
        current_state = self.parameters.get("state", "high")
        self.widgets['state_selector'] = StateSelector(current_state)
        self.form_layout.addWidget(self.widgets['state_selector'])

        self.form_layout.addWidget(ParameterHelpText(
            "Sets a digital output pin to HIGH (1) or LOW (0). "
            "Use to control external devices like lights, relays, or other equipment."
        ))

    def _add_wait_digital_input_params(self):
        """Add parameters for Wait for Digital Input"""
        self.form_layout.addWidget(SectionHeader("Digital Input Settings"))

        # Pin selector
        current_pin = self.parameters.get("pin", 0)
        self.widgets['pin_selector'] = PinSelector("digital", current_pin)
        self.form_layout.addWidget(self.widgets['pin_selector'])

        # State selector
        current_state = self.parameters.get("state", "high")
        self.widgets['state_selector'] = StateSelector(current_state)
        self.form_layout.addWidget(self.widgets['state_selector'])

        # Timeout
        self.form_layout.addWidget(SectionHeader("Timeout"))
        current_timeout = self.parameters.get("timeout", 30)
        self.widgets['timeout_spin'] = QSpinBox()
        self.widgets['timeout_spin'].setRange(1, 300)
        self.widgets['timeout_spin'].setValue(current_timeout)
        self.widgets['timeout_spin'].setSuffix(" seconds")

        form = QFormLayout()
        form.addRow("Timeout:", self.widgets['timeout_spin'])
        self.form_layout.addLayout(form)

        self.form_layout.addWidget(ParameterHelpText(
            "Waits until the digital input reaches the specified state. "
            "Times out if condition not met within timeout period."
        ))

    def _add_set_analog_output_params(self):
        """Add parameters for Set Analog Output"""
        self.form_layout.addWidget(SectionHeader("Analog Output Settings"))

        # Pin selector
        current_pin = self.parameters.get("pin", 0)
        self.widgets['pin_selector'] = PinSelector("analog", current_pin)
        self.form_layout.addWidget(self.widgets['pin_selector'])

        # Voltage slider
        current_voltage = self.parameters.get("voltage", 5.0)
        self.widgets['voltage_slider'] = SliderWithValue(0, 10, int(current_voltage), "V")
        self.form_layout.addWidget(self.widgets['voltage_slider'])

        self.form_layout.addWidget(ParameterHelpText(
            "Sets analog output voltage (0-10V). Use to control variable speed motors, "
            "dimmers, or other analog devices."
        ))

    def _add_read_digital_input_params(self):
        """Add parameters for Read Digital Input"""
        self.form_layout.addWidget(SectionHeader("Digital Input"))

        # Pin selector
        current_pin = self.parameters.get("pin", 0)
        self.widgets['pin_selector'] = PinSelector("digital", current_pin)
        self.form_layout.addWidget(self.widgets['pin_selector'])

        self.form_layout.addWidget(ParameterHelpText(
            "Reads the current state of a digital input pin. "
            "Useful for checking sensor states or button presses."
        ))

    def _add_emergency_stop_params(self):
        """Add parameters for Emergency Stop"""
        self.form_layout.addWidget(ParameterHelpText(
            "⚠️ IMMEDIATELY stops all robot motion. Use only in emergencies!"
        ))

    def _add_repeat_start_params(self):
        """Add parameters for Repeat Start"""
        self.form_layout.addWidget(SectionHeader("Loop Settings"))

        # Repeat count with presets
        repeat_presets = {"2 times": 2, "3 times": 3, "5 times": 5, "10 times": 10}
        current_repeat = self.parameters.get("repeat_count", 3)

        # Find matching preset or default to "3 times"
        default_key = "3 times"
        for key, val in repeat_presets.items():
            if val == current_repeat:
                default_key = key
                break

        self.widgets['repeat_preset'] = PresetButtonGroup(repeat_presets, default_key)
        self.form_layout.addWidget(self.widgets['repeat_preset'])

        # Custom repeat count
        self.widgets['repeat_spin'] = QSpinBox()
        self.widgets['repeat_spin'].setRange(1, 999)
        self.widgets['repeat_spin'].setValue(current_repeat)
        self.widgets['repeat_spin'].setSuffix(" times")

        # Connect preset to spin box
        self.widgets['repeat_preset'].value_changed.connect(
            lambda v: self.widgets['repeat_spin'].setValue(v)
        )

        form = QFormLayout()
        form.addRow("Custom Repeat:", self.widgets['repeat_spin'])
        self.form_layout.addLayout(form)

        self.form_layout.addWidget(ParameterHelpText(
            "Marks the beginning of a loop. All actions between Repeat Start and Repeat End "
            "will be executed the specified number of times. Loops can be nested."
        ))

    def _add_repeat_end_params(self):
        """Add parameters for Repeat End"""
        self.form_layout.addWidget(ParameterHelpText(
            "Marks the end of a loop. When this is reached, execution returns to the matching "
            "Repeat Start. No additional parameters required."
        ))

    def _add_generic_params(self):
        """Generic parameter handler for unknown action types"""
        self.form_layout.addWidget(ParameterHelpText(
            f"No specific parameters defined for this action type ({self.action_type.value})."
        ))

    def get_parameters(self) -> dict:
        """Get user-entered parameters"""
        params = {}

        if self.action_type == ActionType.MOVE_TO_POSITION:
            params["position_name"] = self.widgets['waypoint_name'].text().strip()
            params["speed_percent"] = self.widgets['speed_spin'].value()
            params["move_type"] = "moveL" if self.widgets['moveL_radio'].isChecked() else "moveJ"
            # Preserve the TCP pose from the original parameters
            if "tcp_pose" in self.parameters:
                params["tcp_pose"] = self.parameters["tcp_pose"]

        elif self.action_type == ActionType.RELATIVE_MOVE:
            direction_map = ["up", "down", "left", "right", "forward", "backward"]
            params["direction"] = direction_map[self.widgets['direction_combo'].currentIndex()]
            params["distance_cm"] = self.widgets['distance_spin'].value()

        elif self.action_type == ActionType.SAVE_POSITION:
            params["position_name"] = self.widgets['position_name'].text().strip()
            params["description"] = self.widgets['description'].text().strip()

        elif self.action_type == ActionType.WAIT:
            params["seconds"] = self.widgets['duration_spin'].value()

        elif self.action_type == ActionType.ENABLE_FORCE:
            params["force_level"] = self.widgets['force_preset'].get_value()

        elif self.action_type == ActionType.SET_FORCE_LEVEL:
            params["force_newtons"] = self.widgets['force_slider'].get_value()

        elif self.action_type == ActionType.GRIPPER_MOVE:
            params["position_percent"] = self.widgets['gripper_slider'].get_value()

        elif self.action_type == ActionType.SET_DIGITAL_OUTPUT:
            params["pin"] = self.widgets['pin_selector'].get_value()
            params["state"] = self.widgets['state_selector'].get_value()

        elif self.action_type == ActionType.WAIT_DIGITAL_INPUT:
            params["pin"] = self.widgets['pin_selector'].get_value()
            params["state"] = self.widgets['state_selector'].get_value()
            params["timeout"] = self.widgets['timeout_spin'].value()

        elif self.action_type == ActionType.SET_ANALOG_OUTPUT:
            params["pin"] = self.widgets['pin_selector'].get_value()
            params["voltage"] = self.widgets['voltage_slider'].get_value()

        elif self.action_type == ActionType.READ_DIGITAL_INPUT:
            params["pin"] = self.widgets['pin_selector'].get_value()

        elif self.action_type == ActionType.REPEAT_START:
            params["repeat_count"] = self.widgets['repeat_spin'].value()

        # REPEAT_END has no parameters

        return params


# Test the enhanced dialog
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Test different action types
    dialog = EnhancedActionParameterDialog(ActionType.SET_DIGITAL_OUTPUT)
    if dialog.exec_() == QDialog.Accepted:
        print("Parameters:", dialog.get_parameters())

    sys.exit()
