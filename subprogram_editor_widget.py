"""
Subprogram Editor Widget

Editor for creating and modifying subprograms.
Allows users to build action sequences and configure parameters.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QDialog,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QSplitter, QToolBar, QMessageBox, QListWidget,
    QListWidgetItem, QGroupBox, QTextEdit, QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from subprogram_models import SubProgram, Parameter
from subprogram_manager import SubProgramManager
from sequential_controller import Action, ActionType, ACTION_CATEGORIES, ACTION_METADATA
from sequential_controller_dialog_enhanced import EnhancedActionParameterDialog

logger = logging.getLogger(__name__)


class SubProgramEditor(QWidget):
    """
    Subprogram Editor

    Standalone editor for creating and modifying subprograms.
    Provides action sequence editing and parameter configuration.
    """

    saved = pyqtSignal(SubProgram)
    cancelled = pyqtSignal()

    def __init__(self, subprogram: SubProgram = None, parent=None, seq_controller=None):
        super().__init__(parent)
        self.subprogram = subprogram
        self.manager = SubProgramManager.get_instance()
        self.seq_controller = seq_controller
        self.is_new = (subprogram is None)

        # Cache for action selection dialog to avoid recreation overhead
        self._action_selection_dialog = None

        # Create new subprogram if none provided
        if self.subprogram is None:
            self.subprogram = SubProgram(
                id="",
                name="New Subprogram",
                description="",
                icon="📦",
                category="Other",
                actions=[],
                parameters=[]
            )

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Toolbar
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)

        # Main content: Splitter with Actions (left) and Parameters (right)
        splitter = QSplitter(Qt.Horizontal)

        # Left: Action sequence editor
        action_panel = self.create_action_panel()
        splitter.addWidget(action_panel)

        # Right: Parameter panel
        param_panel = self.create_parameter_panel()
        splitter.addWidget(param_panel)

        splitter.setSizes([600, 300])
        layout.addWidget(splitter)

        # Bottom buttons
        button_layout = QHBoxLayout()

        # Test button
        self.test_btn = QPushButton("🧪 Test Run")
        self.test_btn.setToolTip("Test this subprogram (simulation)")
        self.test_btn.clicked.connect(self.on_test_run)
        button_layout.addWidget(self.test_btn)

        button_layout.addStretch()

        # Save button
        self.save_btn = QPushButton("💾 Save Subprogram")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        self.save_btn.clicked.connect(self.on_save)
        button_layout.addWidget(self.save_btn)

        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.on_cancel)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def create_toolbar(self) -> QWidget:
        """Create toolbar with subprogram info"""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 0, 0, 0)

        # Icon button
        self.icon_btn = QPushButton(self.subprogram.icon or "📦")
        self.icon_btn.setFixedSize(40, 40)
        self.icon_btn.setStyleSheet("font-size: 24px;")
        self.icon_btn.setToolTip("Click to change icon")
        self.icon_btn.clicked.connect(self.on_select_icon)
        layout.addWidget(self.icon_btn)

        # Name
        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit(self.subprogram.name)
        self.name_edit.setPlaceholderText("e.g., Pick Part, Lock Screw")
        layout.addWidget(self.name_edit, 2)

        # Category
        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Pick & Place",
            "Assembly",
            "Inspection",
            "Other"
        ])
        # Set current category
        index = self.category_combo.findText(self.subprogram.category)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)
        layout.addWidget(self.category_combo, 1)

        return toolbar

    def create_action_panel(self) -> QWidget:
        """Create action sequence editing panel"""
        group = QGroupBox("Action Sequence")
        layout = QVBoxLayout(group)

        # Description
        layout.addWidget(QLabel("Description:"))
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Brief description of what this subprogram does...")
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setText(self.subprogram.description)
        layout.addWidget(self.description_edit)

        # Action list
        self.action_list = QListWidget()
        self.action_list.setStyleSheet("""
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #E1BEE7;
            }
        """)
        layout.addWidget(self.action_list)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.add_action_btn = QPushButton("➕ Add Action")
        self.add_action_btn.clicked.connect(self.on_add_action)
        btn_layout.addWidget(self.add_action_btn)

        self.edit_action_btn = QPushButton("✏️ Edit")
        self.edit_action_btn.setEnabled(False)
        self.edit_action_btn.clicked.connect(self.on_edit_action)
        btn_layout.addWidget(self.edit_action_btn)

        self.remove_action_btn = QPushButton("🗑️ Remove")
        self.remove_action_btn.setEnabled(False)
        self.remove_action_btn.clicked.connect(self.on_remove_action)
        btn_layout.addWidget(self.remove_action_btn)

        self.up_btn = QPushButton("⬆️")
        self.up_btn.setEnabled(False)
        self.up_btn.clicked.connect(self.on_move_up)
        btn_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton("⬇️")
        self.down_btn.setEnabled(False)
        self.down_btn.clicked.connect(self.on_move_down)
        btn_layout.addWidget(self.down_btn)

        layout.addLayout(btn_layout)

        # Load existing actions
        self.refresh_action_list()

        # Connect selection change
        self.action_list.itemSelectionChanged.connect(self.on_action_selection_changed)

        return group

    def create_parameter_panel(self) -> QWidget:
        """Create parameter configuration panel"""
        group = QGroupBox("Parameters")
        layout = QVBoxLayout(group)

        # Info label
        info = QLabel(
            "Parameters make your subprogram flexible by allowing "
            "values to be configured when it's called."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 10px; padding: 5px;")
        layout.addWidget(info)

        # Parameter list
        self.param_list = QListWidget()
        layout.addWidget(self.param_list)

        # Auto-detect button
        self.auto_detect_btn = QPushButton("🔍 Auto-Detect Parameters")
        self.auto_detect_btn.setToolTip("Automatically find values that could be parameterized")
        self.auto_detect_btn.clicked.connect(self.on_auto_detect_parameters)
        layout.addWidget(self.auto_detect_btn)

        # Refresh parameter list
        self.refresh_parameter_list()

        return group

    def refresh_action_list(self):
        """Refresh action list display"""
        self.action_list.clear()

        for i, action in enumerate(self.subprogram.actions):
            item_text = f"{i+1}. {action.get_display_text()}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, action)
            self.action_list.addItem(item)

    def refresh_parameter_list(self):
        """Refresh parameter list display"""
        self.param_list.clear()

        for param in self.subprogram.parameters:
            item_text = f"⚙️ {param.name}: {param.type}"
            if param.default_value is not None:
                item_text += f" = {param.default_value}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, param)
            self.param_list.addItem(item)

    def on_action_selection_changed(self):
        """Handle action selection change"""
        has_selection = self.action_list.currentRow() >= 0
        self.edit_action_btn.setEnabled(has_selection)
        self.remove_action_btn.setEnabled(has_selection)

        current_row = self.action_list.currentRow()
        count = self.action_list.count()

        self.up_btn.setEnabled(current_row > 0)
        self.down_btn.setEnabled(0 <= current_row < count - 1)

    def on_add_action(self):
        """Add action to sequence"""
        # Use categorized action library dialog for a graphical picker
        if self._action_selection_dialog is None:
            self._action_selection_dialog = ActionSelectionDialog(self)
        else:
            self._action_selection_dialog.reset()

        dialog = self._action_selection_dialog
        if dialog.exec_() == QDialog.Accepted:
            action_type = dialog.get_selected_action_type()
            if action_type:
                # Open parameter dialog
                preset_params = {}
                if action_type == ActionType.MOVE_TO_POSITION:
                    preset_params = self._get_move_to_position_defaults()

                param_dialog = EnhancedActionParameterDialog(
                    action_type, preset_params, parent=self
                )
                if param_dialog.exec_() == QDialog.Accepted:
                    parameters = param_dialog.get_parameters()

                    # Create action
                    action = Action(
                        id=len(self.subprogram.actions) + 1,
                        action_type=action_type,
                        parameters=parameters
                    )

                    self.subprogram.actions.append(action)
                    self.refresh_action_list()

    def on_edit_action(self):
        """Edit selected action"""
        current_row = self.action_list.currentRow()
        if current_row < 0:
            return

        action = self.subprogram.actions[current_row]

        # Open parameter dialog
        dialog = EnhancedActionParameterDialog(action.action_type, action.parameters, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            action.parameters = dialog.get_parameters()
            self.refresh_action_list()

    def _get_move_to_position_defaults(self) -> dict:
        """Auto-generate waypoint name and capture robot pose if available"""
        auto_name = self._generate_next_waypoint_name()
        pose = None

        if self.seq_controller and getattr(self.seq_controller, "robot_controller", None):
            rtde_receive = getattr(self.seq_controller.robot_controller, "rtde_receive", None)
            if rtde_receive:
                try:
                    pose = rtde_receive.getActualTCPPose()
                except Exception as exc:
                    logger.warning("Failed to read current TCP pose for subprogram editor: %s", exc)

        return {
            "position_name": auto_name,
            "speed_percent": 50,
            "move_type": "moveJ",
            "tcp_pose": pose
        }

    def _generate_next_waypoint_name(self) -> str:
        """Generate incremental waypoint name within this subprogram"""
        import re

        max_num = 0
        for action in self.subprogram.actions:
            if action.action_type == ActionType.MOVE_TO_POSITION:
                name = action.parameters.get("position_name", "")
                match = re.match(r'waypoint(\d+)', name)
                if match:
                    max_num = max(max_num, int(match.group(1)))

        return f"waypoint{max_num + 1}"

    def on_remove_action(self):
        """Remove selected action"""
        current_row = self.action_list.currentRow()
        if current_row < 0:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Remove this action from the sequence?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            del self.subprogram.actions[current_row]
            self.refresh_action_list()

    def on_move_up(self):
        """Move action up"""
        current_row = self.action_list.currentRow()
        if current_row > 0:
            # Swap actions
            self.subprogram.actions[current_row], self.subprogram.actions[current_row - 1] = \
                self.subprogram.actions[current_row - 1], self.subprogram.actions[current_row]
            self.refresh_action_list()
            self.action_list.setCurrentRow(current_row - 1)

    def on_move_down(self):
        """Move action down"""
        current_row = self.action_list.currentRow()
        if current_row < len(self.subprogram.actions) - 1:
            # Swap actions
            self.subprogram.actions[current_row], self.subprogram.actions[current_row + 1] = \
                self.subprogram.actions[current_row + 1], self.subprogram.actions[current_row]
            self.refresh_action_list()
            self.action_list.setCurrentRow(current_row + 1)

    def on_select_icon(self):
        """Select icon for subprogram"""
        # Common icons for subprograms
        icons = ["📦", "🤏", "🔧", "🔍", "✅", "📍", "🎯", "⚡", "🔄", "💪", "🏭", "🎨"]

        from PyQt5.QtWidgets import QInputDialog
        icon, ok = QInputDialog.getItem(
            self,
            "Select Icon",
            "Choose an icon for this subprogram:",
            icons,
            0,
            False
        )

        if ok and icon:
            self.subprogram.icon = icon
            self.icon_btn.setText(icon)

    def on_auto_detect_parameters(self):
        """Auto-detect parameterizable values"""
        # Extract parameters from current actions
        parameters = self.manager.extract_parameters(self.subprogram.actions)

        if not parameters:
            QMessageBox.information(
                self,
                "No Parameters Found",
                "No parameterizable values detected in the action sequence.\n\n"
                "Parameters are automatically detected for:\n"
                "• Movement positions and speeds\n"
                "• Wait durations\n"
                "• Loop repeat counts"
            )
            return

        # Show summary and ask for confirmation
        param_summary = "\n".join([f"• {p.name}: {p.description}" for p in parameters])
        reply = QMessageBox.question(
            self,
            "Auto-Detected Parameters",
            f"Found {len(parameters)} parameterizable values:\n\n{param_summary}\n\n"
            "Add these as parameters?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.subprogram.parameters = parameters
            self.refresh_parameter_list()
            QMessageBox.information(
                self,
                "Parameters Added",
                f"Added {len(parameters)} parameters to this subprogram."
            )

    def on_test_run(self):
        """Test run the subprogram"""
        if not self.subprogram.actions:
            QMessageBox.warning(self, "No Actions", "Add actions to test the subprogram.")
            return

        QMessageBox.information(
            self,
            "Test Run",
            f"Test run simulation for: {self.name_edit.text()}\n\n"
            f"Actions: {len(self.subprogram.actions)}\n"
            f"Parameters: {len(self.subprogram.parameters)}\n\n"
            "(Full test execution will be available after integration)"
        )

    def on_save(self):
        """Save subprogram"""
        # Validate
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a name for the subprogram.")
            return

        if not self.subprogram.actions:
            QMessageBox.warning(self, "Validation Error", "Please add at least one action.")
            return

        # Update subprogram properties
        self.subprogram.name = name
        self.subprogram.description = self.description_edit.toPlainText().strip()
        self.subprogram.icon = self.icon_btn.text()
        self.subprogram.category = self.category_combo.currentText()

        # Save to manager
        if self.is_new:
            # Create new subprogram
            saved_subprogram = self.manager.create_subprogram(
                name=self.subprogram.name,
                actions=self.subprogram.actions,
                description=self.subprogram.description,
                icon=self.subprogram.icon,
                category=self.subprogram.category
            )
            saved_subprogram.parameters = self.subprogram.parameters
            self.manager.save_subprogram(saved_subprogram)
        else:
            # Update existing
            self.manager.update_subprogram(
                self.subprogram.id,
                name=self.subprogram.name,
                description=self.subprogram.description,
                icon=self.subprogram.icon,
                category=self.subprogram.category,
                actions=self.subprogram.actions,
                parameters=self.subprogram.parameters
            )

        QMessageBox.information(self, "Success", f"Saved: {self.subprogram.name}")
        self.saved.emit(self.subprogram)

    def on_cancel(self):
        """Cancel editing"""
        if self.subprogram.actions:
            reply = QMessageBox.question(
                self,
                "Confirm Cancel",
                "Discard changes?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        self.cancelled.emit()


# Simple action selection dialog for the editor
class ActionSelectionDialog(QDialog):
    """Graphical action selection dialog using categorized action library"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_action_type = None
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Select Action Type")
        self.setMinimumSize(720, 600)

        layout = QVBoxLayout(self)

        # Reuse categorized action library for graphical selection
        from categorized_action_library_improved import CategorizedActionLibrary
        self.action_library = CategorizedActionLibrary()
        self.action_library.action_selected.connect(self.on_action_selected)
        layout.addWidget(self.action_library, 1)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def on_action_selected(self, action_type: ActionType):
        """Handle action type selection"""
        self.selected_action_type = action_type
        self.accept()

    def get_selected_action_type(self) -> ActionType:
        """Get selected action type"""
        return self.selected_action_type

    def reset(self):
        """Reset selection state before reusing the dialog"""
        self.selected_action_type = None
