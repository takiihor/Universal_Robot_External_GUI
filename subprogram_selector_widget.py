"""
Subprogram Selector Widget

Compact widget for selecting and adding subprograms to the main sequence.
Used in the main Sequential Controller interface.
"""

import logging
from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QDialog, QDialogButtonBox,
    QPushButton, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QFormLayout, QSpinBox, QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from subprogram_models import SubProgram
from subprogram_manager import SubProgramManager
from sequential_controller import Action, ActionType

logger = logging.getLogger(__name__)


class SubProgramCallDialog(QDialog):
    """
    Dialog for configuring subprogram call parameters

    Allows user to set parameter values and loop count when adding
    a subprogram to the main sequence.
    """

    def __init__(self, subprogram: SubProgram, parent=None):
        super().__init__(parent)
        self.subprogram = subprogram
        self.parameter_widgets = {}
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle(f"Call Subprogram: {self.subprogram.name}")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Subprogram info
        info_group = QGroupBox("Subprogram Information")
        info_layout = QVBoxLayout(info_group)

        title_label = QLabel(f"{self.subprogram.icon} {self.subprogram.name}")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        info_layout.addWidget(title_label)

        if self.subprogram.description:
            desc_label = QLabel(self.subprogram.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666;")
            info_layout.addWidget(desc_label)

        stats_label = QLabel(
            f"Actions: {len(self.subprogram.actions)} | "
            f"Parameters: {len(self.subprogram.parameters)}"
        )
        stats_label.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(stats_label)

        layout.addWidget(info_group)

        # Parameters
        if self.subprogram.parameters:
            param_group = QGroupBox("Parameters")
            param_layout = QFormLayout(param_group)

            for param in self.subprogram.parameters:
                label = QLabel(f"{param.name}:")
                if param.description:
                    label.setToolTip(param.description)

                # Create appropriate widget based on parameter type
                if param.type == "number":
                    widget = QSpinBox()
                    widget.setMinimum(param.constraints.get("min", 0))
                    widget.setMaximum(param.constraints.get("max", 100))
                    if param.default_value is not None:
                        widget.setValue(int(param.default_value))
                else:
                    widget = QLineEdit()
                    if param.default_value is not None:
                        widget.setText(str(param.default_value))

                param_layout.addRow(label, widget)
                self.parameter_widgets[param.name] = widget

            layout.addWidget(param_group)
        else:
            no_params_label = QLabel("(This subprogram has no configurable parameters)")
            no_params_label.setStyleSheet("color: #888; font-style: italic;")
            layout.addWidget(no_params_label)

        # Loop count
        loop_group = QGroupBox("Execution Options")
        loop_layout = QFormLayout(loop_group)

        self.loop_spin = QSpinBox()
        self.loop_spin.setMinimum(1)
        self.loop_spin.setMaximum(100)
        self.loop_spin.setValue(1)
        self.loop_spin.setToolTip("Number of times to execute this subprogram")
        loop_layout.addRow("Repeat Count:", self.loop_spin)

        layout.addWidget(loop_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_parameters(self) -> dict:
        """Get parameter values"""
        params = {}
        for param_name, widget in self.parameter_widgets.items():
            if isinstance(widget, QSpinBox):
                params[param_name] = widget.value()
            elif isinstance(widget, QLineEdit):
                params[param_name] = widget.text()
        return params

    def get_loop_count(self) -> int:
        """Get loop count"""
        return self.loop_spin.value()


class SubProgramSelector(QWidget):
    """
    Subprogram Selector Widget

    Compact list for selecting subprograms to add to the main sequence.
    """

    subprogram_selected = pyqtSignal(str, dict, int)  # subprogram_id, parameters, loop_count

    def __init__(self, manager: SubProgramManager = None, parent=None):
        super().__init__(parent)
        self.manager = manager or SubProgramManager.get_instance()
        self._is_loaded = False  # Track if list has been loaded
        self.init_ui()
        self.connect_signals()
        # Load immediately so list is available when user switches to this view
        self.refresh_list()

    def init_ui(self):
        """Initialize UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search...")
        self.search_input.textChanged.connect(self.refresh_list)
        main_layout.addWidget(self.search_input)

        # Split layout: list on left, preview on right
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        main_layout.addLayout(content_layout)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(6)
        content_layout.addLayout(left_panel, 1)

        # Subprogram list
        self.subprogram_list = QListWidget()
        self.subprogram_list.setStyleSheet("""
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:hover {
                background-color: #F3E5F5;
            }
            QListWidget::item:selected {
                background-color: #E1BEE7;
            }
        """)
        self.subprogram_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        left_panel.addWidget(self.subprogram_list)

        # Add button
        self.add_btn = QPushButton("➕ Add to Sequence")
        self.add_btn.setEnabled(False)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #673AB7;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover:enabled {
                background-color: #5E35B1;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.add_btn.clicked.connect(self.on_add_clicked)
        left_panel.addWidget(self.add_btn)

        # Preview panel on the right
        self.preview_group = QGroupBox("Subprogram Details")
        self.preview_group.setMinimumWidth(240)
        preview_layout = QVBoxLayout(self.preview_group)
        preview_layout.setSpacing(6)

        self.preview_title = QLabel("Select a subprogram to see details.")
        self.preview_title.setWordWrap(True)
        self.preview_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        preview_layout.addWidget(self.preview_title)

        self.preview_description = QLabel("")
        self.preview_description.setWordWrap(True)
        self.preview_description.setStyleSheet("color: #555; font-size: 11px;")
        preview_layout.addWidget(self.preview_description)

        self.preview_stats = QLabel("")
        self.preview_stats.setStyleSheet("color: #777; font-size: 10px;")
        preview_layout.addWidget(self.preview_stats)

        # Parameters list
        self.param_group = QGroupBox("Parameters")
        param_layout = QVBoxLayout(self.param_group)
        param_layout.setContentsMargins(6, 6, 6, 6)
        self.param_list = QListWidget()
        self.param_list.setStyleSheet("QListWidget::item { padding: 2px 4px; }")
        self.param_list.setFocusPolicy(Qt.NoFocus)
        param_layout.addWidget(self.param_list)
        preview_layout.addWidget(self.param_group)

        # Actions preview
        self.action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(self.action_group)
        action_layout.setContentsMargins(6, 6, 6, 6)
        self.action_list = QListWidget()
        self.action_list.setStyleSheet("QListWidget::item { padding: 2px 4px; }")
        self.action_list.setFocusPolicy(Qt.NoFocus)
        action_layout.addWidget(self.action_list)
        preview_layout.addWidget(self.action_group, 1)

        content_layout.addWidget(self.preview_group, 1)

        # Selection change
        self.subprogram_list.itemSelectionChanged.connect(self.on_selection_changed)

        # Initialize preview with placeholder
        self.update_preview(None)

    def connect_signals(self):
        """Connect manager signals"""
        self.manager.subprogram_added.connect(self.refresh_list)
        self.manager.subprogram_updated.connect(self.refresh_list)
        self.manager.subprogram_deleted.connect(self.refresh_list)

    def refresh_list(self):
        """Refresh subprogram list"""
        self._is_loaded = True  # Mark as loaded when refreshed
        self.subprogram_list.clear()
        self.update_preview(None)

        # Get all subprograms
        subprograms = self.manager.get_all_subprograms()

        # Filter by search
        search_text = self.search_input.text().strip().lower()
        if search_text:
            subprograms = [
                sp for sp in subprograms
                if search_text in sp.name.lower() or
                   search_text in sp.description.lower()
            ]

        # Sort by usage count (most used first)
        subprograms.sort(key=lambda sp: sp.usage_count, reverse=True)

        # Add to list
        for subprogram in subprograms:
            item_text = f"{subprogram.icon} {subprogram.name}"
            if subprogram.usage_count > 0:
                item_text += f" ({subprogram.usage_count}×)"

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, subprogram)
            item.setToolTip(
                f"{subprogram.description}\n\n"
                f"Category: {subprogram.category}\n"
                f"Actions: {len(subprogram.actions)}\n"
                f"Parameters: {len(subprogram.parameters)}"
            )
            self.subprogram_list.addItem(item)

        # Show message if empty
        if self.subprogram_list.count() == 0:
            item = QListWidgetItem("No subprograms available")
            item.setFlags(Qt.NoItemFlags)
            item.setForeground(Qt.gray)
            self.subprogram_list.addItem(item)

    def on_selection_changed(self):
        """Handle selection change"""
        has_selection = self.subprogram_list.currentRow() >= 0
        current_item = self.subprogram_list.currentItem()

        # Check if it's a real subprogram (not the "no subprograms" message)
        if current_item:
            subprogram = current_item.data(Qt.UserRole)
            has_selection = has_selection and (subprogram is not None)
            self.update_preview(subprogram)
        else:
            self.update_preview(None)

        self.add_btn.setEnabled(has_selection)

    def on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double click on item"""
        subprogram = item.data(Qt.UserRole)
        if subprogram:
            self.add_subprogram(subprogram)

    def on_add_clicked(self):
        """Handle add button click"""
        current_item = self.subprogram_list.currentItem()
        if not current_item:
            return

        subprogram = current_item.data(Qt.UserRole)
        if subprogram:
            self.add_subprogram(subprogram)

    def add_subprogram(self, subprogram: SubProgram):
        """Add subprogram to main sequence"""
        # Open parameter dialog
        dialog = SubProgramCallDialog(subprogram, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            params = dialog.get_parameters()
            loop_count = dialog.get_loop_count()

            # Emit signal with subprogram info
            self.subprogram_selected.emit(subprogram.id, params, loop_count)

            logger.info(f"Selected subprogram: {subprogram.name} (loop={loop_count})")

    def showEvent(self, event):
        """Override showEvent to load list on first show"""
        super().showEvent(event)
        # Only load once when first shown
        if not self._is_loaded:
            self.refresh_list()
            self._is_loaded = True

    def ensure_loaded(self):
        """Ensure the list is populated at least once"""
        if not self._is_loaded:
            self.refresh_list()

    def update_preview(self, subprogram: Optional[SubProgram]):
        """Update preview panel with subprogram details"""
        if not subprogram:
            self.preview_title.setText("Select a subprogram to see details.")
            self.preview_description.setText("")
            self.preview_stats.setText("")
            self.add_btn.setText("➕ Add to Sequence")
            self.param_list.clear()
            empty_param = QListWidgetItem("No parameters")
            empty_param.setFlags(Qt.NoItemFlags)
            self.param_list.addItem(empty_param)
            self.action_list.clear()
            empty_action = QListWidgetItem("No actions")
            empty_action.setFlags(Qt.NoItemFlags)
            self.action_list.addItem(empty_action)
            return

        self.preview_title.setText(f"{subprogram.icon} {subprogram.name}")
        self.add_btn.setText(f"➕ Add '{subprogram.name}'")
        desc = subprogram.description or "No description provided."
        self.preview_description.setText(desc)
        stats_text = (
            f"Category: {subprogram.category} | "
            f"Actions: {len(subprogram.actions)} | "
            f"Parameters: {len(subprogram.parameters)} | "
            f"Used: {subprogram.usage_count}×"
        )
        self.preview_stats.setText(stats_text)

        # Parameters
        self.param_list.clear()
        if subprogram.parameters:
            for param in subprogram.parameters:
                details = f"{param.name} ({param.type})"
                if param.required:
                    details += " • required"
                if param.default_value not in (None, ""):
                    details += f" • default: {param.default_value}"
                item = QListWidgetItem(details)
                self.param_list.addItem(item)
        else:
            item = QListWidgetItem("No parameters")
            item.setFlags(Qt.NoItemFlags)
            self.param_list.addItem(item)

        # Actions
        self.action_list.clear()
        if subprogram.actions:
            for idx, action in enumerate(subprogram.actions, 1):
                if hasattr(action, "get_display_text"):
                    text = action.get_display_text()
                elif isinstance(action, dict):
                    text = action.get("action_type", "Unknown Action")
                else:
                    text = str(action)
                item = QListWidgetItem(f"{idx}. {text}")
                self.action_list.addItem(item)
        else:
            item = QListWidgetItem("No actions defined")
            item.setFlags(Qt.NoItemFlags)
            self.action_list.addItem(item)
