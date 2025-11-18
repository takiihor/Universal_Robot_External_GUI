"""
Enhanced Parameter Input Widgets

Provides reusable widgets for parameter dialogs with presets, help text, and better UX.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QButtonGroup, QFrame, QSpinBox, QDoubleSpinBox, QComboBox,
    QSlider, QRadioButton
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class PresetButtonGroup(QWidget):
    """
    Preset button group widget with multiple preset options.

    Allows quick selection of common values with visual feedback.
    """
    value_changed = pyqtSignal(object)  # Emits the selected preset value

    def __init__(self, presets: dict, default_key: str = None, parent=None):
        """
        Args:
            presets: Dictionary of {display_name: actual_value}
                    e.g., {"Slow": 20, "Medium": 50, "Fast": 80}
            default_key: Default preset key to select
        """
        super().__init__(parent)
        self.presets = presets
        self.buttons = {}
        self.current_value = None
        self.setup_ui(default_key)

    def setup_ui(self, default_key):
        """Setup UI with preset buttons"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        for i, (name, value) in enumerate(self.presets.items()):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setMinimumWidth(80)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 8px 16px;
                    border: 2px solid #ddd;
                    border-radius: 6px;
                    background-color: white;
                    font-size: 12px;
                }
                QPushButton:checked {
                    background-color: #2196F3;
                    color: white;
                    border-color: #1976D2;
                    font-weight: bold;
                }
                QPushButton:hover {
                    border-color: #2196F3;
                    background-color: #E3F2FD;
                }
                QPushButton:checked:hover {
                    background-color: #1976D2;
                }
            """)

            btn.clicked.connect(lambda checked, v=value: self.on_button_clicked(v))
            self.button_group.addButton(btn, i)
            self.buttons[name] = btn
            layout.addWidget(btn)

            # Set default
            if default_key and name == default_key:
                btn.setChecked(True)
                self.current_value = value

        layout.addStretch()

    def on_button_clicked(self, value):
        """Handle button click"""
        self.current_value = value
        self.value_changed.emit(value)

    def get_value(self):
        """Get currently selected value"""
        return self.current_value

    def set_value(self, value):
        """Set value by finding matching preset"""
        for name, preset_value in self.presets.items():
            if preset_value == value:
                self.buttons[name].setChecked(True)
                self.current_value = value
                break


class ParameterHelpText(QLabel):
    """
    Help text label with styling and icon.

    Displays helpful information about parameters.
    """

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setText(f"💡 {text}")
        self.setWordWrap(True)
        self.setStyleSheet("""
            QLabel {
                color: #555;
                font-size: 11px;
                padding: 10px;
                background-color: #F8F9FA;
                border-left: 3px solid #2196F3;
                border-radius: 4px;
            }
        """)


class SliderWithValue(QWidget):
    """
    Slider with live value display and presets.
    """
    value_changed = pyqtSignal(int)

    def __init__(self, min_val: int, max_val: int, default: int, suffix: str = "", parent=None):
        super().__init__(parent)
        self.suffix = suffix
        self.setup_ui(min_val, max_val, default)

    def setup_ui(self, min_val, max_val, default):
        """Setup UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval((max_val - min_val) // 10)
        self.slider.valueChanged.connect(self.on_value_changed)
        layout.addWidget(self.slider, 1)

        # Value label
        self.value_label = QLabel(f"{default}{self.suffix}")
        self.value_label.setMinimumWidth(60)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #2196F3;
                border: 2px solid #2196F3;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        layout.addWidget(self.value_label)

    def on_value_changed(self, value):
        """Update label and emit signal"""
        self.value_label.setText(f"{value}{self.suffix}")
        self.value_changed.emit(value)

    def get_value(self):
        """Get current value"""
        return self.slider.value()

    def set_value(self, value):
        """Set value"""
        self.slider.setValue(value)


class PinSelector(QWidget):
    """
    Pin selector for I/O operations with visual pin display.
    """
    value_changed = pyqtSignal(int)

    def __init__(self, pin_type: str = "digital", default: int = 0, parent=None):
        super().__init__(parent)
        self.pin_type = pin_type
        self.setup_ui(default)

    def setup_ui(self, default):
        """Setup UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Pin label
        pin_label = QLabel("Pin:")
        pin_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(pin_label)

        # Pin combo box
        self.pin_combo = QComboBox()
        if self.pin_type == "digital":
            # Digital pins 0-15
            self.pin_combo.addItems([f"DI/DO {i}" for i in range(16)])
        else:
            # Analog pins 0-1
            self.pin_combo.addItems([f"AO {i}" for i in range(2)])

        self.pin_combo.setCurrentIndex(default)
        self.pin_combo.currentIndexChanged.connect(self.on_pin_changed)
        self.pin_combo.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 2px solid #ddd;
                border-radius: 4px;
                font-size: 12px;
                min-width: 100px;
            }
            QComboBox:focus {
                border-color: #2196F3;
            }
        """)
        layout.addWidget(self.pin_combo)

        layout.addStretch()

    def on_pin_changed(self, index):
        """Emit signal when pin changes"""
        self.value_changed.emit(index)

    def get_value(self):
        """Get current pin number"""
        return self.pin_combo.currentIndex()

    def set_value(self, pin):
        """Set pin number"""
        self.pin_combo.setCurrentIndex(pin)


class StateSelector(QWidget):
    """
    High/Low state selector with radio buttons.
    """
    value_changed = pyqtSignal(str)

    def __init__(self, default: str = "high", parent=None):
        super().__init__(parent)
        self.setup_ui(default)

    def setup_ui(self, default):
        """Setup UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # State label
        state_label = QLabel("State:")
        state_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(state_label)

        # Radio buttons
        self.high_radio = QRadioButton("High (1)")
        self.low_radio = QRadioButton("Low (0)")

        style = """
            QRadioButton {
                font-size: 12px;
                padding: 4px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """
        self.high_radio.setStyleSheet(style)
        self.low_radio.setStyleSheet(style)

        # Set default
        if default == "high":
            self.high_radio.setChecked(True)
        else:
            self.low_radio.setChecked(True)

        # Connect signals
        self.high_radio.toggled.connect(lambda: self.on_state_changed("high"))
        self.low_radio.toggled.connect(lambda: self.on_state_changed("low"))

        layout.addWidget(self.high_radio)
        layout.addWidget(self.low_radio)
        layout.addStretch()

    def on_state_changed(self, state):
        """Emit signal when state changes"""
        if (state == "high" and self.high_radio.isChecked()) or \
           (state == "low" and self.low_radio.isChecked()):
            self.value_changed.emit(state)

    def get_value(self):
        """Get current state"""
        return "high" if self.high_radio.isChecked() else "low"

    def set_value(self, state):
        """Set state"""
        if state == "high":
            self.high_radio.setChecked(True)
        else:
            self.low_radio.setChecked(True)


class SectionHeader(QLabel):
    """
    Section header label with styling.
    """

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.setFont(font)
        self.setStyleSheet("""
            QLabel {
                color: #333;
                padding: 8px 0px 4px 0px;
                border-bottom: 2px solid #2196F3;
            }
        """)


# Example usage and testing
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget

    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("Parameter Widgets Test")
    window.setMinimumSize(600, 400)

    layout = QVBoxLayout(window)

    # Test PresetButtonGroup
    layout.addWidget(SectionHeader("Speed Presets"))
    speed_presets = PresetButtonGroup(
        {"Slow": 20, "Medium": 50, "Fast": 80},
        default_key="Medium"
    )
    speed_presets.value_changed.connect(lambda v: print(f"Speed: {v}"))
    layout.addWidget(speed_presets)

    # Test ParameterHelpText
    layout.addWidget(ParameterHelpText(
        "Speed controls how fast the robot moves. Slow is recommended for precise operations."
    ))

    # Test SliderWithValue
    layout.addWidget(SectionHeader("Force Level"))
    force_slider = SliderWithValue(0, 100, 50, "%")
    force_slider.value_changed.connect(lambda v: print(f"Force: {v}%"))
    layout.addWidget(force_slider)

    # Test PinSelector
    layout.addWidget(SectionHeader("Digital I/O"))
    pin_selector = PinSelector("digital", 0)
    pin_selector.value_changed.connect(lambda v: print(f"Pin: {v}"))
    layout.addWidget(pin_selector)

    # Test StateSelector
    state_selector = StateSelector("high")
    state_selector.value_changed.connect(lambda v: print(f"State: {v}"))
    layout.addWidget(state_selector)

    layout.addStretch()

    window.show()
    sys.exit(app.exec_())
