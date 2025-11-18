# Sequential Controller - Quick Win Improvements

## Overview

This document provides a prioritized list of **quick-win improvements** that deliver high impact with reasonable effort. These improvements can be implemented incrementally without major architectural changes.

**Total Estimated Time**: 7-10 weeks for all quick wins

**Philosophy**: Improve existing system incrementally rather than complete redesign

---

## Priority 1: Categorized Action Library (2-3 weeks)

### Why This First?
- ✅ **High impact**: Dramatically improves action discoverability
- ✅ **Low risk**: Doesn't change backend logic
- ✅ **Quick**: Can be done in 2-3 weeks
- ✅ **Foundation**: Sets up structure for new action types

### Current Problem
- All 8 actions in single flat list
- No visual organization
- Hard to find specific actions as list grows

### Proposed Solution
Replace flat QListWidget with categorized QTabWidget + card-based display

### Implementation Tasks

#### Task 1.1: Define Category Structure (2 hours)
**File**: `sequential_controller.py`

Add category metadata:
```python
# After ACTION_METADATA definition
ACTION_CATEGORIES = {
    "movement": {
        "name": "Movement",
        "icon": "🚀",
        "color": "#4CAF50",
        "description": "Robot movement actions",
        "actions": [
            ActionType.MOVE_TO_POSITION,
            ActionType.RELATIVE_MOVE,
            ActionType.RETURN_HOME,
            # ActionType.CIRCULAR_MOTION,  # If exists
        ]
    },
    "freedrive": {
        "name": "Hand Guiding",
        "icon": "🤚",
        "color": "#FF9800",
        "description": "Manual robot control",
        "actions": [
            ActionType.ENABLE_FREEDRIVE,
            ActionType.DISABLE_FREEDRIVE,
        ]
    },
    "timing": {
        "name": "Timing",
        "icon": "⏱️",
        "color": "#2196F3",
        "description": "Time-based actions",
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
    "safety": {
        "name": "Safety",
        "icon": "⚠️",
        "color": "#F44336",
        "description": "Emergency and safety actions",
        "actions": [
            ActionType.EMERGENCY_STOP,
        ]
    }
}
```

#### Task 1.2: Create CategorizedActionLibrary Widget (1-2 days)
**File**: `categorized_action_library.py` (new file)

```python
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QScrollArea,
    QGridLayout, QFrame, QLabel, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from sequential_controller import ActionType, ACTION_METADATA, ACTION_CATEGORIES


class ActionCard(QFrame):
    """Action card widget"""
    clicked = pyqtSignal(object)  # ActionType

    def __init__(self, action_type: ActionType, color: str, parent=None):
        super().__init__(parent)
        self.action_type = action_type
        self.setup_ui(color)

    def setup_ui(self, color: str):
        """Setup UI"""
        metadata = ACTION_METADATA.get(self.action_type, {})

        # Card styling
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            ActionCard {{
                background-color: {color};
                border-radius: 8px;
                padding: 15px;
            }}
            ActionCard:hover {{
                background-color: {self.darken_color(color, 10)};
                border: 2px solid white;
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(120)
        self.setMaximumHeight(150)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Icon
        icon_label = QLabel(metadata.get("icon", "⚙️"))
        icon_label.setStyleSheet("font-size: 42px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # Name
        name_label = QLabel(metadata.get("name", "Unknown"))
        name_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        # Description
        desc = metadata.get("description", "")
        if len(desc) > 40:
            desc = desc[:37] + "..."
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 10px;")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

    def mousePressEvent(self, event):
        """Mouse click event"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.action_type)

    @staticmethod
    def darken_color(hex_color: str, percent: int) -> str:
        """Darken hex color by percentage"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, r - int(r * percent / 100))
        g = max(0, g - int(g * percent / 100))
        b = max(0, b - int(b * percent / 100))
        return f"#{r:02x}{g:02x}{b:02x}"


class CategorizedActionLibrary(QWidget):
    """Categorized action library widget"""
    action_selected = pyqtSignal(object)  # ActionType

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Info label
        info_label = QLabel("Click an action card to add it to the sequence")
        info_label.setStyleSheet("color: gray; font-size: 11px; padding: 8px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Tabbed categories
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        for cat_id, cat_info in ACTION_CATEGORIES.items():
            page = self.create_category_page(cat_info)
            self.tab_widget.addTab(page, f"{cat_info['icon']} {cat_info['name']}")

        layout.addWidget(self.tab_widget)

    def create_category_page(self, category_info: dict) -> QWidget:
        """Create category page with action cards"""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(10, 10, 10, 10)

        # Category description
        desc_label = QLabel(category_info.get("description", ""))
        desc_label.setStyleSheet("color: gray; font-size: 11px; padding: 5px;")
        desc_label.setWordWrap(True)
        page_layout.addWidget(desc_label)

        # Scroll area for cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Card container
        card_container = QWidget()
        grid_layout = QGridLayout(card_container)
        grid_layout.setSpacing(10)

        # Create cards
        row, col = 0, 0
        max_cols = 2  # 2 cards per row

        for action_type in category_info["actions"]:
            card = ActionCard(action_type, category_info["color"])
            card.clicked.connect(self.on_card_clicked)
            grid_layout.addWidget(card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Add stretch to push cards to top
        grid_layout.setRowStretch(row + 1, 1)

        scroll_area.setWidget(card_container)
        page_layout.addWidget(scroll_area)

        return page

    def on_card_clicked(self, action_type: ActionType):
        """Handle card click"""
        self.action_selected.emit(action_type)
```

#### Task 1.3: Integrate into SequentialControllerPageWidget (1 day)
**File**: `sequential_controller_ui_page.py`

Replace the current `create_action_library()` method:

```python
def create_action_library(self) -> QWidget:
    """Create action library"""
    group = QGroupBox("Action Library")
    layout = QVBoxLayout()
    layout.setSpacing(5)

    # Use new categorized library
    from categorized_action_library import CategorizedActionLibrary

    self.action_library = CategorizedActionLibrary()
    self.action_library.action_selected.connect(self.on_action_type_selected)
    layout.addWidget(self.action_library)

    group.setLayout(layout)
    return group

def on_action_type_selected(self, action_type: ActionType):
    """Handle action type selection from library"""
    # Open parameter dialog
    from sequential_controller_dialog import ActionParameterDialog

    dialog = ActionParameterDialog(action_type, parent=self)
    if dialog.exec_() == QDialog.Accepted:
        parameters = dialog.get_parameters()

        # Validate required parameters
        if action_type == ActionType.SAVE_POSITION:
            if not parameters.get("position_name"):
                QMessageBox.warning(self, "Error", "Please enter a position name")
                return

        # Add to sequence
        self.seq_controller.add_action(action_type, parameters)
```

#### Task 1.4: Testing (1 day)
- Test card clicking adds actions to sequence
- Test all categories display correctly
- Test with window resize
- Verify all 8 existing actions are accessible

### Acceptance Criteria
- ✅ Action library shows 5 categories in tabs
- ✅ Each action displayed as color-coded card
- ✅ Clicking card opens parameter dialog
- ✅ All existing functionality works
- ✅ No performance issues

---

## Priority 2: Enhanced Parameter Dialogs with Presets (1-2 weeks)

### Why Second?
- ✅ **High impact**: Makes parameter entry much easier
- ✅ **Low risk**: Improves existing dialogs
- ✅ **Quick**: 1-2 weeks
- ✅ **User-friendly**: Non-technical users benefit most

### Current Problem
- Plain text labels with technical terms
- Users must know exact values (e.g., speed in m/s)
- No suggestions or presets

### Proposed Solution
Add preset buttons and friendly labels to parameter dialogs

### Implementation Tasks

#### Task 2.1: Add Preset System (1 day)
**File**: `sequential_controller_dialog.py`

Add preset definitions:
```python
# Parameter presets
PARAMETER_PRESETS = {
    "speed": {
        "label": "Movement Speed",
        "help": "How fast the robot should move",
        "presets": [
            {"label": "🐌 Slow (Safe)", "value": "slow", "description": "Safest, 50% speed"},
            {"label": "🚶 Medium", "value": "medium", "description": "Normal speed"},
            {"label": "🏃 Fast", "value": "fast", "description": "Fastest, use with caution"},
        ]
    },
    "force_level": {
        "label": "Force Level",
        "help": "How much pressure the robot should apply",
        "presets": [
            {"label": "🪶 Gentle", "value": "gentle", "description": "Very light touch"},
            {"label": "✋ Medium", "value": "medium", "description": "Moderate pressure"},
            {"label": "💪 Strong", "value": "strong", "description": "Firm pressure"},
        ]
    },
    "repeat_count": {
        "label": "Repeat Count",
        "help": "How many times to repeat the action",
        "presets": [
            {"label": "3 times", "value": 3},
            {"label": "5 times", "value": 5},
            {"label": "10 times", "value": 10},
        ]
    }
}
```

#### Task 2.2: Create Preset Button Widget (1 day)
**File**: `sequential_controller_dialog.py`

```python
class PresetButtonGroup(QWidget):
    """Preset button group widget"""
    value_selected = pyqtSignal(object)  # value

    def __init__(self, preset_config: dict, parent=None):
        super().__init__(parent)
        self.preset_config = preset_config
        self.selected_value = None
        self.setup_ui()

    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        # Help text
        if "help" in self.preset_config:
            help_label = QLabel(f"💡 {self.preset_config['help']}")
            help_label.setStyleSheet("color: gray; font-size: 11px; padding: 5px; background-color: #F0F0F0; border-radius: 3px;")
            help_label.setWordWrap(True)
            layout.addWidget(help_label)

        # Preset buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)

        self.button_group = QButtonGroup(self)

        for i, preset in enumerate(self.preset_config["presets"]):
            btn = QRadioButton(preset["label"])
            btn.setStyleSheet("""
                QRadioButton {
                    font-size: 13px;
                    padding: 8px;
                }
                QRadioButton:hover {
                    background-color: #E3F2FD;
                    border-radius: 4px;
                }
            """)

            # Description tooltip
            if "description" in preset:
                btn.setToolTip(preset["description"])

            btn.toggled.connect(lambda checked, v=preset["value"]: self.on_preset_selected(checked, v))
            self.button_group.addButton(btn, i)
            button_layout.addWidget(btn)

        layout.addLayout(button_layout)

    def on_preset_selected(self, checked: bool, value):
        """Handle preset selection"""
        if checked:
            self.selected_value = value
            self.value_selected.emit(value)

    def get_value(self):
        """Get selected value"""
        return self.selected_value

    def set_value(self, value):
        """Set value (select matching preset)"""
        for i, preset in enumerate(self.preset_config["presets"]):
            if preset["value"] == value:
                self.button_group.button(i).setChecked(True)
                return
```

#### Task 2.3: Update ActionParameterDialog (2 days)
**File**: `sequential_controller_dialog.py`

Modify `ActionParameterDialog` to use presets:

```python
class ActionParameterDialog(QDialog):
    """Enhanced action parameter dialog with presets"""

    def __init__(self, action_type: ActionType, existing_parameters: dict = None, parent=None):
        self.action_type = action_type
        self.existing_parameters = existing_parameters or {}
        self.parameter_widgets = {}

        super().__init__(parent)
        self.setWindowTitle(f"Configure: {ACTION_METADATA[action_type]['name']}")
        self.setup_ui()

    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Action info header
        header = self.create_header()
        layout.addWidget(header)

        # Parameter form
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # Add parameter inputs based on action type
        if self.action_type == ActionType.MOVE_TO_POSITION:
            self.add_position_selector(form_layout)
            self.add_speed_presets(form_layout)

        elif self.action_type == ActionType.RELATIVE_MOVE:
            self.add_direction_selector(form_layout)
            self.add_distance_input(form_layout)
            self.add_speed_presets(form_layout)

        elif self.action_type == ActionType.WAIT:
            self.add_duration_input(form_layout)

        elif self.action_type == ActionType.SAVE_POSITION:
            self.add_position_name_input(form_layout)

        # Add more parameter forms for other action types...

        layout.addLayout(form_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def create_header(self) -> QWidget:
        """Create action info header"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border-radius: 8px;
                padding: 15px;
            }
        """)

        layout = QHBoxLayout(header)

        metadata = ACTION_METADATA[self.action_type]

        # Icon
        icon_label = QLabel(metadata.get("icon", "⚙️"))
        icon_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(icon_label)

        # Name and description
        text_layout = QVBoxLayout()

        name_label = QLabel(metadata.get("name", "Unknown Action"))
        name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        text_layout.addWidget(name_label)

        desc_label = QLabel(metadata.get("description", ""))
        desc_label.setStyleSheet("color: gray; font-size: 12px;")
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)

        return header

    def add_speed_presets(self, form_layout: QFormLayout):
        """Add speed preset buttons"""
        preset_config = PARAMETER_PRESETS["speed"]

        speed_widget = PresetButtonGroup(preset_config)

        # Set existing value if available
        if "speed" in self.existing_parameters:
            speed_widget.set_value(self.existing_parameters["speed"])
        else:
            # Default to medium
            speed_widget.set_value("medium")

        self.parameter_widgets["speed"] = speed_widget
        form_layout.addRow(preset_config["label"] + ":", speed_widget)

    # Add similar methods for other preset types...
```

#### Task 2.4: Testing (1 day)
- Test preset selection for all action types
- Test dialog with existing parameters (edit mode)
- Verify tooltips display correctly
- Test with different window sizes

### Acceptance Criteria
- ✅ Parameter dialogs show friendly labels
- ✅ Preset buttons available for common parameters
- ✅ Help text explains each parameter
- ✅ Default preset selected (e.g., "medium" speed)
- ✅ Tooltips provide additional info

---

## Priority 3: Add Force Control Actions (2-3 weeks)

### Why Third?
- ✅ **High impact**: Enables massage/therapy use cases
- ✅ **High demand**: Students want force control
- ✅ **Moderate complexity**: Requires backend implementation
- ✅ **Hardware-dependent**: May need simulation mode

### Current Problem
- No way to enable/control force mode in Sequential Controller
- Users must manually switch to Force Mode page

### Proposed Solution
Add 3 new ActionType enums for force control

### Implementation Tasks

#### Task 3.1: Extend ActionType Enum (1 hour)
**File**: `sequential_controller.py`

```python
class ActionType(Enum):
    """Action type enumeration"""
    # === Existing actions ===
    MOVE_TO_POSITION = "move_to_position"
    RELATIVE_MOVE = "relative_move"
    SAVE_POSITION = "save_position"
    RETURN_HOME = "return_home"
    ENABLE_FREEDRIVE = "enable_freedrive"
    DISABLE_FREEDRIVE = "disable_freedrive"
    WAIT = "wait"
    EMERGENCY_STOP = "emergency_stop"

    # === NEW: Force Control ===
    ENABLE_FORCE = "enable_force"          # Enable force mode
    DISABLE_FORCE = "disable_force"        # Disable force mode
    SET_FORCE_LEVEL = "set_force_level"    # Set force level
```

#### Task 3.2: Add Metadata (30 minutes)
**File**: `sequential_controller.py`

```python
ACTION_METADATA = {
    # ... existing metadata ...

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
}

# Update ACTION_CATEGORIES
ACTION_CATEGORIES["interaction"] = {
    "name": "Interaction",
    "icon": "🤝",
    "color": "#FF5722",
    "description": "Force control and physical interaction",
    "actions": [
        ActionType.ENABLE_FORCE,
        ActionType.DISABLE_FORCE,
        ActionType.SET_FORCE_LEVEL,
    ]
}
```

#### Task 3.3: Implement Backend Execution (1-2 days)
**File**: `sequential_controller.py`

```python
class SequentialController(QObject):
    """Sequential Controller"""

    def _execute_action(self, action: Action) -> bool:
        """Execute single action"""
        try:
            logger.info(f"Executing action: {action.get_display_text()}")

            # ... existing action handlers ...

            # NEW: Force control handlers
            elif action.action_type == ActionType.ENABLE_FORCE:
                return self._execute_enable_force(action)

            elif action.action_type == ActionType.DISABLE_FORCE:
                return self._execute_disable_force(action)

            elif action.action_type == ActionType.SET_FORCE_LEVEL:
                return self._execute_set_force_level(action)

            # ... rest of handlers ...

    def _execute_enable_force(self, action: Action) -> bool:
        """Execute: Enable force mode"""
        force_level = action.parameters.get("force_level", "medium")

        # Check if force control is available
        if not hasattr(self.robot_controller, 'start_force_mode'):
            logger.warning("Force control not available on this robot")
            QMessageBox.warning(None, "Not Available",
                              "Force control is not available on this robot.")
            return False

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
            return True  # Not an error if not available

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
```

#### Task 3.4: Add Parameter Dialog (1 day)
**File**: `sequential_controller_dialog.py`

```python
# In ActionParameterDialog.setup_ui()

elif self.action_type == ActionType.ENABLE_FORCE:
    self.add_force_level_presets(form_layout)

elif self.action_type == ActionType.SET_FORCE_LEVEL:
    self.add_force_level_presets(form_layout)

# New method:
def add_force_level_presets(self, form_layout: QFormLayout):
    """Add force level preset buttons"""
    preset_config = PARAMETER_PRESETS["force_level"]

    force_widget = PresetButtonGroup(preset_config)

    # Set existing or default
    if "force_level" in self.existing_parameters:
        force_widget.set_value(self.existing_parameters["force_level"])
    else:
        force_widget.set_value("medium")  # Default

    self.parameter_widgets["force_level"] = force_widget
    form_layout.addRow(preset_config["label"] + ":", force_widget)
```

#### Task 3.5: Update Display Text (30 minutes)
**File**: `sequential_controller.py`

```python
class Action:
    """Action dataclass"""

    def get_display_text(self) -> str:
        """Get display text"""
        text = f"{self.get_icon()} {self.get_name()}"

        # ... existing cases ...

        # NEW: Force control display
        elif self.action_type == ActionType.ENABLE_FORCE:
            force_level = self.parameters.get("force_level", "medium")
            text += f" ({force_level})"
        elif self.action_type == ActionType.SET_FORCE_LEVEL:
            force_level = self.parameters.get("force_level", "medium")
            text += f" ({force_level})"

        return text
```

#### Task 3.6: Testing (2-3 days)
- Test with actual robot (if force sensor available)
- Test simulation mode (if hardware unavailable)
- Test force mode enable/disable sequence
- Test force level changes
- Integration testing with movement actions

### Acceptance Criteria
- ✅ 3 new force control actions available in Action Library
- ✅ Force actions appear in "Interaction" category
- ✅ Force level presets work (gentle/medium/strong)
- ✅ Backend execution works with robot
- ✅ Graceful degradation if force control unavailable
- ✅ Display text shows force level

---

## Priority 4: Execution History Panel (1 week)

### Why Fourth?
- ✅ **Medium impact**: Helps debugging and learning
- ✅ **Low risk**: Purely additive feature
- ✅ **Quick**: 1 week
- ✅ **Valuable**: Students can review what happened

### Current Problem
- No log of what was executed
- Hard to debug failed sequences
- No timestamp information

### Proposed Solution
Add execution history panel with timestamped log

### Implementation Tasks

#### Task 4.1: Create ExecutionHistoryPanel Widget (1-2 days)
**File**: `execution_history_panel.py` (new file)

```python
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from datetime import datetime
import json


class ExecutionHistoryPanel(QWidget):
    """Execution history panel widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.history_entries = []
        self.setup_ui()

    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Title
        title_label = QLabel("📜 Execution History")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # History list
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget {
                font-size: 11px;
                font-family: monospace;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        layout.addWidget(self.history_list)

        # Control buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_history)
        btn_layout.addWidget(self.clear_btn)

        self.export_btn = QPushButton("Export Log")
        self.export_btn.clicked.connect(self.export_log)
        btn_layout.addWidget(self.export_btn)

        layout.addLayout(btn_layout)

    def add_entry(self, step_index: int, action_name: str,
                  status: str, duration: float = 0.0):
        """Add history entry"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        icon = {
            "started": "▶️",
            "completed": "✅",
            "error": "❌",
            "skipped": "⏭️"
        }.get(status, "❓")

        # Format text
        if status == "started":
            text = f"{icon} [{timestamp}] Step {step_index + 1}: {action_name}"
        else:
            text = f"{icon} [{timestamp}] Step {step_index + 1}: {status.upper()} (duration: {duration:.2f}s)"

        # Create list item
        item = QListWidgetItem(text)

        # Color code by status
        if status == "error":
            item.setBackground(QColor("#FFCDD2"))
        elif status == "completed":
            item.setBackground(QColor("#C8E6C9"))
        elif status == "started":
            item.setBackground(QColor("#FFF9C4"))

        self.history_list.addItem(item)

        # Auto-scroll to bottom
        self.history_list.scrollToBottom()

        # Store entry
        self.history_entries.append({
            "timestamp": timestamp,
            "step_index": step_index,
            "action_name": action_name,
            "status": status,
            "duration": duration
        })

    def clear_history(self):
        """Clear history"""
        self.history_list.clear()
        self.history_entries.clear()

    def export_log(self):
        """Export log to file"""
        if not self.history_entries:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Execution Log",
            f"execution_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;Text Files (*.txt)"
        )

        if filename:
            if filename.endswith('.json'):
                self.export_as_json(filename)
            else:
                self.export_as_text(filename)

    def export_as_json(self, filename: str):
        """Export as JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.history_entries, f, indent=2, ensure_ascii=False)

    def export_as_text(self, filename: str):
        """Export as text"""
        with open(filename, 'w', encoding='utf-8') as f:
            for entry in self.history_entries:
                line = f"[{entry['timestamp']}] Step {entry['step_index'] + 1}: {entry['action_name']} - {entry['status']}"
                if entry['duration'] > 0:
                    line += f" ({entry['duration']:.2f}s)"
                f.write(line + "\n")
```

#### Task 4.2: Integrate into SequentialControllerPageWidget (1 day)
**File**: `sequential_controller_ui_page.py`

```python
def create_execution_control(self) -> QWidget:
    """Create execution control panel"""
    group = QGroupBox("Execution Control")
    layout = QVBoxLayout()

    # ... existing controls (task name, stats, execute button, etc.) ...

    # NEW: Execution history panel
    from execution_history_panel import ExecutionHistoryPanel

    self.history_panel = ExecutionHistoryPanel()
    layout.addWidget(self.history_panel)

    # ... rest of layout ...

    group.setLayout(layout)
    return group

def on_step_started(self, step_index, description):
    """Step started"""
    logger.info(f"Step {step_index + 1} started: {description}")

    # NEW: Add to history
    self.history_panel.add_entry(step_index, description, "started")

def on_step_completed(self, step_index, success):
    """Step completed"""
    logger.info(f"Step {step_index + 1} completed: success={success}")

    # NEW: Add to history
    status = "completed" if success else "error"
    # TODO: Track duration (requires storing start time)
    self.history_panel.add_entry(step_index, "", status, duration=0.0)
```

#### Task 4.3: Add Duration Tracking (1 day)
**File**: `sequential_controller.py`

```python
class ExecutionThread(QThread):
    """Task execution thread"""
    progress_update = pyqtSignal(int, int)  # current_step, total_steps
    step_started = pyqtSignal(int, str)     # step_index, step_description
    step_completed = pyqtSignal(int, bool, float)  # step_index, success, duration (NEW)
    execution_completed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def run(self):
        """Execute task sequence"""
        try:
            import time

            total_steps = len(self.actions)

            for i, action in enumerate(self.actions):
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

                # Emit step started
                self.step_started.emit(i, action.get_display_text())
                self.progress_update.emit(i + 1, total_steps)

                # NEW: Track duration
                start_time = time.time()

                # Execute action
                success = self.controller._execute_action(action)

                # NEW: Calculate duration
                duration = time.time() - start_time

                # Emit step completed with duration
                self.step_completed.emit(i, success, duration)

                if not success:
                    error_msg = f"Step {i+1} failed: {action.get_display_text()}"
                    logger.error(error_msg)
                    self.error_occurred.emit(error_msg)
                    self.execution_completed.emit(False)
                    return

            # All steps completed
            logger.info("All steps completed successfully")
            self.execution_completed.emit(True)

        except Exception as e:
            logger.error(f"Execution thread error: {e}", exc_info=True)
            self.error_occurred.emit(f"Execution error: {str(e)}")
            self.execution_completed.emit(False)
```

Update signal connection:
```python
# In sequential_controller_ui_page.py connect_signals()
self.seq_controller.execution_step_completed.connect(self.on_step_completed)
```

Update handler signature:
```python
def on_step_completed(self, step_index, success, duration=0.0):
    """Step completed"""
    logger.info(f"Step {step_index + 1} completed: success={success}, duration={duration:.2f}s")

    # Get action name from sequence
    actions = self.seq_controller.get_actions()
    action_name = actions[step_index].get_display_text() if step_index < len(actions) else "Unknown"

    status = "completed" if success else "error"
    self.history_panel.add_entry(step_index, action_name, status, duration)
```

#### Task 4.4: Testing (1 day)
- Test history logging during execution
- Test clear history button
- Test export to JSON and text
- Test with failed execution (verify error logging)

### Acceptance Criteria
- ✅ History panel shows timestamped execution log
- ✅ Each step shows start/complete status
- ✅ Duration displayed for each step
- ✅ Color-coded by status (green=success, red=error)
- ✅ Export log to JSON/text file
- ✅ Clear history functionality

---

## Priority 5: Add Basic Loop Support (2-3 weeks)

### Why Fifth?
- ✅ **High value**: Enables repeated actions (common use case)
- ✅ **Moderate complexity**: Requires execution logic changes
- ✅ **Educational**: Teaches programming concepts

### Current Problem
- No way to repeat actions
- Users must manually duplicate steps

### Proposed Solution
Add REPEAT_START and REPEAT_END markers with loop count

### Implementation Tasks

#### Task 5.1: Add Loop Action Types (1 hour)
**File**: `sequential_controller.py`

```python
class ActionType(Enum):
    """Action type enumeration"""
    # ... existing actions ...

    # NEW: Loop control
    REPEAT_START = "repeat_start"    # Loop start marker
    REPEAT_END = "repeat_end"        # Loop end marker
```

Add metadata:
```python
ACTION_METADATA = {
    # ... existing ...

    ActionType.REPEAT_START: {
        "icon": "🔁",
        "name": "Repeat Start",
        "description": "Begin repeating the following actions"
    },
    ActionType.REPEAT_END: {
        "icon": "🔚",
        "name": "Repeat End",
        "description": "End of repeated actions"
    },
}

# Add to control flow category
ACTION_CATEGORIES["control_flow"] = {
    "name": "Control Flow",
    "icon": "🔀",
    "color": "#9C27B0",
    "description": "Loops and conditional logic",
    "actions": [
        ActionType.WAIT,  # Move from timing
        ActionType.REPEAT_START,
        ActionType.REPEAT_END,
    ]
}
```

#### Task 5.2: Implement Loop Execution Logic (2-3 days)
**File**: `sequential_controller.py`

```python
class ExecutionThread(QThread):
    """Task execution thread with loop support"""

    def run(self):
        """Execute task sequence with loop support"""
        try:
            import time

            # Validate loops first
            if not self.validate_loops():
                self.error_occurred.emit("Invalid loop structure: mismatched REPEAT_START/END markers")
                self.execution_completed.emit(False)
                return

            # Execute with loop expansion
            expanded_actions = self.expand_loops(self.actions)
            total_steps = len(expanded_actions)

            for i, action in enumerate(expanded_actions):
                if self.should_stop:
                    self.execution_completed.emit(False)
                    return

                # Pause handling
                while self.paused and not self.should_stop:
                    time.sleep(0.1)

                if self.should_stop:
                    self.execution_completed.emit(False)
                    return

                # Skip loop markers (they were already processed)
                if action.action_type in [ActionType.REPEAT_START, ActionType.REPEAT_END]:
                    continue

                # Execute action
                self.step_started.emit(i, action.get_display_text())
                self.progress_update.emit(i + 1, total_steps)

                start_time = time.time()
                success = self.controller._execute_action(action)
                duration = time.time() - start_time

                self.step_completed.emit(i, success, duration)

                if not success:
                    error_msg = f"Step {i+1} failed: {action.get_display_text()}"
                    self.error_occurred.emit(error_msg)
                    self.execution_completed.emit(False)
                    return

            self.execution_completed.emit(True)

        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            self.error_occurred.emit(f"Execution error: {str(e)}")
            self.execution_completed.emit(False)

    def validate_loops(self) -> bool:
        """Validate loop structure (matching start/end markers)"""
        stack = []

        for i, action in enumerate(self.actions):
            if action.action_type == ActionType.REPEAT_START:
                stack.append(i)
            elif action.action_type == ActionType.REPEAT_END:
                if not stack:
                    # End without start
                    return False
                stack.pop()

        # Check all loops closed
        return len(stack) == 0

    def expand_loops(self, actions: list) -> list:
        """Expand loops into repeated action sequences"""
        expanded = []
        i = 0

        while i < len(actions):
            action = actions[i]

            if action.action_type == ActionType.REPEAT_START:
                # Find matching REPEAT_END
                loop_start = i
                loop_end = self.find_matching_end(actions, loop_start)

                if loop_end == -1:
                    # Should not happen (validated earlier)
                    raise ValueError(f"No matching REPEAT_END for REPEAT_START at index {i}")

                # Get repeat count
                repeat_count = action.parameters.get("repeat_count", 1)

                # Get actions inside loop
                loop_actions = actions[loop_start + 1:loop_end]

                # Expand loop (repeat actions N times)
                for _ in range(repeat_count):
                    expanded.extend(loop_actions)

                # Skip to after loop
                i = loop_end + 1
            else:
                # Regular action
                expanded.append(action)
                i += 1

        return expanded

    def find_matching_end(self, actions: list, start_index: int) -> int:
        """Find matching REPEAT_END for REPEAT_START at start_index"""
        depth = 1

        for i in range(start_index + 1, len(actions)):
            if actions[i].action_type == ActionType.REPEAT_START:
                depth += 1
            elif actions[i].action_type == ActionType.REPEAT_END:
                depth -= 1
                if depth == 0:
                    return i

        return -1  # Not found
```

#### Task 5.3: Add Parameter Dialog (1 day)
**File**: `sequential_controller_dialog.py`

```python
# In ActionParameterDialog.setup_ui()

elif self.action_type == ActionType.REPEAT_START:
    self.add_repeat_count_input(form_layout)

# New method:
def add_repeat_count_input(self, form_layout: QFormLayout):
    """Add repeat count input"""
    # Use preset buttons
    preset_config = PARAMETER_PRESETS.get("repeat_count", {
        "label": "Repeat Count",
        "help": "How many times to repeat the actions",
        "presets": [
            {"label": "3 times", "value": 3},
            {"label": "5 times", "value": 5},
            {"label": "10 times", "value": 10},
        ]
    })

    repeat_widget = PresetButtonGroup(preset_config)

    if "repeat_count" in self.existing_parameters:
        repeat_widget.set_value(self.existing_parameters["repeat_count"])
    else:
        repeat_widget.set_value(3)  # Default

    # Also allow custom input
    custom_layout = QHBoxLayout()
    custom_label = QLabel("Or custom:")
    custom_spinbox = QSpinBox()
    custom_spinbox.setRange(1, 100)
    custom_spinbox.setValue(repeat_widget.get_value() or 3)
    custom_spinbox.valueChanged.connect(lambda v: repeat_widget.set_value(v))
    custom_layout.addWidget(custom_label)
    custom_layout.addWidget(custom_spinbox)

    self.parameter_widgets["repeat_count"] = repeat_widget
    self.parameter_widgets["repeat_count_spinbox"] = custom_spinbox

    form_layout.addRow(preset_config["label"] + ":", repeat_widget)
    form_layout.addRow("", custom_layout)
```

#### Task 5.4: Visual Indication in Sequence List (1-2 days)
**File**: `sequential_controller_ui_page.py`

```python
def update_sequence_list(self):
    """Update sequence list display"""
    self.sequence_list.clear()

    actions = self.seq_controller.get_actions()
    loop_depth = 0

    for i, action in enumerate(actions):
        # Calculate indentation based on loop depth
        if action.action_type == ActionType.REPEAT_START:
            indent = "  " * loop_depth
            repeat_count = action.parameters.get("repeat_count", "?")
            item_text = f"{i+1}. {indent}🔁 {action.get_display_text()} ({repeat_count}x)"
            loop_depth += 1
        elif action.action_type == ActionType.REPEAT_END:
            loop_depth -= 1
            indent = "  " * loop_depth
            item_text = f"{i+1}. {indent}🔚 {action.get_display_text()}"
        else:
            indent = "  " * loop_depth
            item_text = f"{i+1}. {indent}{action.get_display_text()}"

        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, action)

        # Color code loop markers
        if action.action_type == ActionType.REPEAT_START:
            item.setBackground(QColor("#E1BEE7"))  # Purple tint
        elif action.action_type == ActionType.REPEAT_END:
            item.setBackground(QColor("#E1BEE7"))

        self.sequence_list.addItem(item)
```

#### Task 5.5: Loop Validation UI (1 day)
**File**: `sequential_controller_ui_page.py`

```python
def on_execute(self):
    """Execute task"""
    count = self.seq_controller.get_action_count()
    if count == 0:
        QMessageBox.warning(self, "Notice", "Please add action steps first")
        return

    # NEW: Validate loops before execution
    validation_errors = self.validate_sequence()
    if validation_errors:
        error_msg = "Sequence validation failed:\n\n" + "\n".join(validation_errors)
        QMessageBox.critical(self, "Validation Error", error_msg)
        return

    # Confirmation dialog
    reply = QMessageBox.question(
        self, "Confirm Execution",
        f"About to execute {count} steps.\n\nPlease confirm:\n• Work area is clear\n• No personnel near robot\n\nExecute now?",
        QMessageBox.Yes | QMessageBox.No
    )

    if reply == QMessageBox.Yes:
        self.seq_controller.execute_sequence()

def validate_sequence(self) -> list:
    """Validate sequence (check loop structure, etc.)"""
    errors = []
    actions = self.seq_controller.get_actions()

    # Check loop pairing
    stack = []
    for i, action in enumerate(actions):
        if action.action_type == ActionType.REPEAT_START:
            stack.append((i, action))
        elif action.action_type == ActionType.REPEAT_END:
            if not stack:
                errors.append(f"Step {i+1}: REPEAT_END without matching REPEAT_START")
            else:
                stack.pop()

    if stack:
        for i, action in stack:
            errors.append(f"Step {i+1}: REPEAT_START without matching REPEAT_END")

    return errors
```

#### Task 5.6: Testing (2-3 days)
- Test simple loop (repeat 3 times)
- Test nested loops (loop within loop)
- Test empty loop (start immediately followed by end)
- Test validation (mismatched markers)
- Integration testing with movement actions

### Acceptance Criteria
- ✅ REPEAT_START and REPEAT_END available in Action Library
- ✅ Repeat count configurable via dialog
- ✅ Loop actions execute correct number of times
- ✅ Nested loops supported
- ✅ Visual indentation in sequence list
- ✅ Validation prevents mismatched loops
- ✅ Execution history shows all loop iterations

---

## Summary - Quick Win Roadmap

### Timeline Overview

| Priority | Improvement | Effort | Impact | Weeks |
|----------|-------------|--------|--------|-------|
| 1 | Categorized Action Library | Medium | High | 2-3 |
| 2 | Enhanced Parameter Dialogs | Low-Medium | High | 1-2 |
| 3 | Force Control Actions | Medium | High | 2-3 |
| 4 | Execution History Panel | Low | Medium | 1 |
| 5 | Basic Loop Support | Medium-High | High | 2-3 |

**Total: 8-12 weeks**

### Benefits of Quick Win Approach

1. **Immediate Value**: Each improvement delivers standalone value
2. **Low Risk**: No major architectural changes
3. **User Feedback**: Can gather feedback after each phase
4. **Incremental**: Can stop at any point with working system
5. **Foundation**: Sets up for more advanced improvements later

### After Quick Wins - What's Next?

If quick wins are successful and user feedback is positive:

**Option A: Continue with MVP approach**
- Add gripper control actions (if hardware available)
- Add more parameter presets
- Add task templates/examples

**Option B: Move to visual block editor**
- Implement QGraphicsView block canvas
- Keep list view as fallback option
- Gather feedback on visual interface

**Option C: Focus on guided mode**
- Implement task wizard
- Create beginner-friendly tutorials
- Develop task template library

### Success Metrics

Track these metrics after each improvement:

- **Usage**: Number of students using Sequential Controller
- **Complexity**: Average number of steps per task (should increase)
- **Diversity**: Variety of action types used
- **Success Rate**: Percentage of tasks that execute successfully
- **Learning Curve**: Time for new user to create first task (should decrease)

---

## Conclusion

These 5 quick-win improvements provide **substantial value** with **manageable effort**. They improve the existing system incrementally without requiring a complete redesign.

**Recommended Next Steps**:
1. Review and approve this plan
2. Verify hardware availability (force sensor, gripper)
3. Start with Priority 1 (Categorized Action Library)
4. Gather user feedback after each improvement
5. Decide on next phase based on feedback

**Key Decision Point**: After completing quick wins (8-12 weeks), reassess whether to proceed with visual block editor (additional 4-6 weeks) or focus on other priorities (guided mode, more action types, etc.).

---

**Document Version**: 1.0
**Created**: 2025-11-10
**Status**: Ready for Implementation