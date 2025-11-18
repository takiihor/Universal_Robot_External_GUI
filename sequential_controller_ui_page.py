"""
Sequential Controller Page Widget

A page widget version (not dialog) for embedding in the main window's page stack.
Contains the same functionality as SequentialControllerDialog but as a regular widget.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QGroupBox, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QDialog, QDialogButtonBox, QFormLayout, QMessageBox,
    QFileDialog, QProgressBar, QRadioButton, QButtonGroup,
    QTabWidget, QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from execution_step_delegate import ExecutionStepDelegate, STEP_STATE_ROLE, StepState

from sequential_controller import (
    SequentialController, ActionType, Action, ACTION_METADATA
)
# Use enhanced dialog with presets and better UX
from sequential_controller_dialog_enhanced import EnhancedActionParameterDialog as ActionParameterDialog
from execution_history_panel import ExecutionHistoryPanel
# New UI components
from guidance_bar import GuidanceBar
from execution_status_bar import ExecutionStatusBar
# Subprogram components
from subprogram_manager import SubProgramManager
from subprogram_library_widget import SubProgramLibrary
from subprogram_editor_widget import SubProgramEditor
from subprogram_selector_widget import SubProgramSelector

logger = logging.getLogger(__name__)


class SequentialControllerPageWidget(QWidget):
    """Sequential Controller Page Widget - Full page task sequencing interface"""

    def __init__(self, sequential_controller: SequentialController, parent=None):
        super().__init__(parent)
        self.seq_controller = sequential_controller
        self.step_states = {}
        self.subprogram_manager = SubProgramManager.get_instance()
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Initialize UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Title
        title_label = QLabel("Sequential Controller - Simple Robot Control")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # Guidance Bar - context-aware instructions
        self.guidance_bar = GuidanceBar()
        main_layout.addWidget(self.guidance_bar)

        # Main Tab Widget
        self.main_tabs = QTabWidget()
        self.main_tabs.setTabPosition(QTabWidget.North)

        # Tab 1: Main Program Editor
        self.main_program_tab = self.create_main_program_tab()
        self.main_tabs.addTab(self.main_program_tab, "📝 Main Program")

        # Tab 2: Subprogram Library
        self.subprogram_library_tab = SubProgramLibrary(self.subprogram_manager)
        self.subprogram_library_tab.subprogram_selected.connect(self.on_subprogram_library_selected)
        self.subprogram_library_tab.create_new_clicked.connect(self.on_create_new_subprogram)
        self.main_tabs.addTab(self.subprogram_library_tab, "📦 Subprogram Library")

        # Tab 3: Execution History (moved from bottom)
        self.history_panel = ExecutionHistoryPanel()
        self.main_tabs.addTab(self.history_panel, "📊 Execution History")

        main_layout.addWidget(self.main_tabs)

    def create_main_program_tab(self) -> QWidget:
        """Create main program editing tab"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Left: Action Library (with toggle for basic actions vs subprograms)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(5)

        # Toggle buttons for action type
        toggle_layout = QHBoxLayout()
        self.toggle_group = QButtonGroup(self)
        self.toggle_group.setExclusive(True)  # Make buttons mutually exclusive

        self.basic_actions_btn = QPushButton("🔧 Basic Actions")
        self.basic_actions_btn.setCheckable(True)
        self.basic_actions_btn.setChecked(True)
        self.basic_actions_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                border: 2px solid #E0E0E0;
                border-radius: 4px;
                background: white;
            }
            QPushButton:checked {
                background: #2196F3;
                color: white;
                border-color: #2196F3;
                font-weight: bold;
            }
        """)
        self.toggle_group.addButton(self.basic_actions_btn, 0)
        toggle_layout.addWidget(self.basic_actions_btn)

        self.subprograms_btn = QPushButton("📦 Subprograms")
        self.subprograms_btn.setCheckable(True)
        self.subprograms_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                border: 2px solid #E0E0E0;
                border-radius: 4px;
                background: white;
            }
            QPushButton:checked {
                background: #673AB7;
                color: white;
                border-color: #673AB7;
                font-weight: bold;
            }
        """)
        self.toggle_group.addButton(self.subprograms_btn, 1)
        toggle_layout.addWidget(self.subprograms_btn)

        left_layout.addLayout(toggle_layout)

        # Stacked widget for basic actions vs subprograms
        self.action_stack = QStackedWidget()

        # Basic action library
        self.action_library_widget = self.create_action_library()
        self.action_stack.addWidget(self.action_library_widget)

        # Subprogram selector
        self.subprogram_selector = SubProgramSelector(self.subprogram_manager)
        self.subprogram_selector.subprogram_selected.connect(self.on_subprogram_selected_for_sequence)
        self.action_stack.addWidget(self.subprogram_selector)

        left_layout.addWidget(self.action_stack)

        # Connect toggle buttons for instant switching
        self.toggle_group.buttonClicked[int].connect(self.on_action_toggle_clicked)

        layout.addWidget(left_panel, 2)

        # Center: Execution Sequence
        self.sequence_widget = self.create_sequence_editor()
        layout.addWidget(self.sequence_widget, 3)

        # Right: Execution Control
        self.control_widget = self.create_execution_control()
        layout.addWidget(self.control_widget, 1)

        return tab

    def on_action_toggle_clicked(self, index: int):
        """Handle toggle button selection"""
        if index == 0:
            self.switch_to_basic_actions()
        elif index == 1:
            self.switch_to_subprograms()

    def switch_to_basic_actions(self):
        """Show basic action library"""
        if self.action_stack.currentIndex() != 0:
            self.action_stack.setCurrentIndex(0)

    def switch_to_subprograms(self):
        """Show subprogram selector"""
        if self.action_stack.currentIndex() != 1:
            if hasattr(self.subprogram_selector, "ensure_loaded"):
                self.subprogram_selector.ensure_loaded()
            self.action_stack.setCurrentIndex(1)

    def create_action_library(self) -> QWidget:
        """Create action library"""
        group = QGroupBox("Action Library")
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Use improved categorized library (List + Stack layout, fixes vertical tab overlap)
        from categorized_action_library_improved import CategorizedActionLibrary

        self.action_library = CategorizedActionLibrary()
        self.action_library.action_selected.connect(self.on_action_card_clicked)
        layout.addWidget(self.action_library)

        group.setLayout(layout)
        return group

    def create_sequence_editor(self) -> QWidget:
        """Create execution sequence editor"""
        group = QGroupBox("Execution Sequence")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Sequence list
        self.sequence_list = QListWidget()
        self.sequence_list.setStyleSheet("""
            QListWidget {
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #FF9800;
                color: white;
            }
        """)
        self.sequence_list.setItemDelegate(ExecutionStepDelegate(self.sequence_list))
        layout.addWidget(self.sequence_list)

        # Control buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self.on_edit_action)
        btn_layout.addWidget(self.edit_btn)

        self.remove_btn = QPushButton("🗑️ Remove")
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self.on_remove_action)
        btn_layout.addWidget(self.remove_btn)

        self.up_btn = QPushButton("⬆️ Move Up")
        self.up_btn.setEnabled(False)
        self.up_btn.clicked.connect(self.on_move_up)
        btn_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton("⬇️ Move Down")
        self.down_btn.setEnabled(False)
        self.down_btn.clicked.connect(self.on_move_down)
        btn_layout.addWidget(self.down_btn)

        layout.addLayout(btn_layout)

        # Connect selection changed event
        self.sequence_list.itemSelectionChanged.connect(self.on_sequence_selection_changed)

        group.setLayout(layout)
        return group

    def create_execution_control(self) -> QWidget:
        """Create execution control panel"""
        group = QGroupBox("Execution Control")
        group.setMaximumWidth(260)  # Keep control column compact
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Task name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Task Name:"))
        self.task_name_edit = QLineEdit()
        self.task_name_edit.setPlaceholderText("e.g., pick_and_place")
        name_layout.addWidget(self.task_name_edit)
        layout.addLayout(name_layout)

        # Statistics
        self.stats_label = QLabel("Steps: 0")
        self.stats_label.setStyleSheet("QLabel { padding: 5px; background-color: #f0f0f0; border-radius: 4px; }")
        layout.addWidget(self.stats_label)

        # NEW: Execution Status Bar (replaces old buttons, progress bar, and status label)
        self.execution_status_bar = ExecutionStatusBar()
        self.execution_status_bar.execute_clicked.connect(self.on_execute)
        self.execution_status_bar.pause_clicked.connect(self.on_pause)
        self.execution_status_bar.resume_clicked.connect(self.on_resume)
        self.execution_status_bar.stop_clicked.connect(self.on_stop)
        layout.addWidget(self.execution_status_bar)

        # Hand Guiding Control Section
        hand_guiding_label = QLabel("Hand Guiding Control")
        hand_guiding_label.setStyleSheet("QLabel { font-weight: bold; margin-top: 10px; }")
        layout.addWidget(hand_guiding_label)

        self.enable_freedrive_btn = QPushButton("🤚 Enable Hand Guiding")
        self.enable_freedrive_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.enable_freedrive_btn.clicked.connect(self.on_enable_freedrive)
        layout.addWidget(self.enable_freedrive_btn)

        self.disable_freedrive_btn = QPushButton("🛑 Disable Hand Guiding")
        self.disable_freedrive_btn.setEnabled(False)
        self.disable_freedrive_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.disable_freedrive_btn.clicked.connect(self.on_disable_freedrive)
        layout.addWidget(self.disable_freedrive_btn)

        # Save/Load buttons
        file_layout = QHBoxLayout()
        file_layout.setSpacing(5)

        self.save_btn = QPushButton("💾 Save Task")
        self.save_btn.clicked.connect(self.on_save_task)
        file_layout.addWidget(self.save_btn)

        self.load_btn = QPushButton("📂 Load Task")
        self.load_btn.clicked.connect(self.on_load_task)
        file_layout.addWidget(self.load_btn)

        layout.addLayout(file_layout)

        # Clear button
        self.clear_btn = QPushButton("🗑️ Clear Sequence")
        self.clear_btn.setStyleSheet("QPushButton { color: red; }")
        self.clear_btn.clicked.connect(self.on_clear_sequence)
        layout.addWidget(self.clear_btn)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def connect_signals(self):
        """Connect signals"""
        self.seq_controller.sequence_changed.connect(self.on_sequence_changed)
        self.seq_controller.execution_started.connect(self.on_execution_started)
        self.seq_controller.execution_progress.connect(self.on_execution_progress)
        self.seq_controller.execution_step_started.connect(self.on_step_started)
        self.seq_controller.execution_step_completed.connect(self.on_step_completed)
        self.seq_controller.execution_step_completed_with_timing.connect(self.on_step_completed_with_timing)
        self.seq_controller.execution_completed.connect(self.on_execution_completed)
        self.seq_controller.execution_paused.connect(self.on_execution_paused)
        self.seq_controller.execution_resumed.connect(self.on_execution_resumed)
        self.seq_controller.error_occurred.connect(self.on_error_occurred)

    # ========================================
    # Event Handlers (same as dialog version)
    # ========================================

    def on_action_card_clicked(self, action_type: ActionType):
        """Handle action card click from categorized library"""
        # Open parameter dialog (use enhanced version)
        from sequential_controller_dialog_enhanced import EnhancedActionParameterDialog as ActionParameterDialog

        if action_type == ActionType.CALL_SUBPROGRAM:
            self.open_subprogram_call_dialog()
            return

        # Auto-generate waypoint name for MOVE_TO_POSITION (Add Waypoint)
        existing_params = {}
        if action_type == ActionType.MOVE_TO_POSITION:
            auto_name = self.generate_next_waypoint_name()
            # Capture current robot pose
            current_pose = None
            if self.seq_controller.robot_controller.rtde_receive:
                try:
                    current_pose = self.seq_controller.robot_controller.rtde_receive.getActualTCPPose()
                except Exception as e:
                    logger.warning(f"Failed to get current TCP pose: {e}")
            existing_params = {
                "position_name": auto_name,
                "speed_percent": 50,
                "move_type": "moveJ",
                "tcp_pose": current_pose  # Store the actual robot pose
            }

        dialog = ActionParameterDialog(action_type, existing_params, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            parameters = dialog.get_parameters()

            # Validate required parameters
            if action_type == ActionType.SAVE_POSITION:
                if not parameters.get("position_name"):
                    QMessageBox.warning(self, "Error", "Please enter a position name")
                    return

            # Add to sequence
            self.seq_controller.add_action(action_type, parameters)

    def open_subprogram_call_dialog(self):
        """Show inline subprogram selector dialog when clicking Call Subprogram card"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Subprogram to Call")
        dialog.setMinimumSize(520, 540)

        layout = QVBoxLayout(dialog)
        selector = SubProgramSelector(self.subprogram_manager, dialog)
        selector.ensure_loaded()

        info_label = QLabel("Choose a saved subprogram below, configure its parameters, and it will be added to the sequence.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; padding: 4px;")
        layout.addWidget(info_label)
        layout.addWidget(selector, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        def handle_selection(subprogram_id, params, loop_count):
            self.on_subprogram_selected_for_sequence(subprogram_id, params, loop_count)
            dialog.accept()

        selector.subprogram_selected.connect(handle_selection)
        dialog.exec_()

    def generate_next_waypoint_name(self) -> str:
        """Generate next waypoint name (waypoint1, waypoint2, waypoint3...)"""
        import re

        max_num = 0

        # Check existing actions in current sequence
        for action in self.seq_controller.get_actions():
            if action.action_type == ActionType.MOVE_TO_POSITION:
                waypoint_name = action.parameters.get("position_name", "")
                # Extract number from waypoint names like "waypoint1", "waypoint2"
                match = re.match(r'waypoint(\d+)', waypoint_name)
                if match:
                    num = int(match.group(1))
                    max_num = max(max_num, num)

        # Generate next waypoint name
        next_num = max_num + 1
        return f"waypoint{next_num}"

    def on_add_action(self):
        """Add action (legacy method for old list-based UI)"""
        # This method is kept for backward compatibility but not used with new categorized library
        current_item = self.action_list.currentItem() if hasattr(self, 'action_list') else None
        if not current_item:
            QMessageBox.warning(self, "Notice", "Please select an action type first")
            return

        action_type = current_item.data(Qt.UserRole)

        # Open parameter dialog
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

    def on_edit_action(self):
        """Edit action"""
        current_row = self.sequence_list.currentRow()
        if current_row < 0:
            return

        actions = self.seq_controller.get_actions()
        if current_row >= len(actions):
            return

        action = actions[current_row]

        # Open parameter dialog
        dialog = ActionParameterDialog(action.action_type, action.parameters, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_parameters = dialog.get_parameters()
            action.parameters = new_parameters

            # Update display
            self.update_sequence_list()

    def on_remove_action(self):
        """Remove action"""
        current_row = self.sequence_list.currentRow()
        if current_row < 0:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this step?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.seq_controller.remove_action_at(current_row)

    def on_move_up(self):
        """Move action up"""
        current_row = self.sequence_list.currentRow()
        if self.seq_controller.move_action_up(current_row):
            self.sequence_list.setCurrentRow(current_row - 1)

    def on_move_down(self):
        """Move action down"""
        current_row = self.sequence_list.currentRow()
        if self.seq_controller.move_action_down(current_row):
            self.sequence_list.setCurrentRow(current_row + 1)

    def on_sequence_selection_changed(self):
        """Sequence selection changed"""
        has_selection = self.sequence_list.currentRow() >= 0
        self.edit_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)

        current_row = self.sequence_list.currentRow()
        count = self.sequence_list.count()

        self.up_btn.setEnabled(current_row > 0)
        self.down_btn.setEnabled(0 <= current_row < count - 1)

    def on_sequence_changed(self):
        """Sequence content changed"""
        self.update_sequence_list()
        self.update_stats()

    def update_sequence_list(self):
        """Update sequence list display"""
        self.sequence_list.clear()

        # Reset cached states since the indices may have changed
        self.step_states = {}

        actions = self.seq_controller.get_actions()
        for i, action in enumerate(actions):
            item_text = f"{i+1}. {action.get_display_text()}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, action)
            item.setData(STEP_STATE_ROLE, StepState.PENDING.value)
            self.sequence_list.addItem(item)

    def update_stats(self):
        """Update statistics"""
        count = self.seq_controller.get_action_count()
        self.stats_label.setText(f"Steps: {count}")
        self.execution_status_bar.set_execution_enabled(count > 0)

        # Update guidance bar based on action count
        if count == 0:
            self.guidance_bar.update_context("empty_sequence")
        else:
            self.guidance_bar.update_context("has_actions", count)

    def on_execute(self):
        """Execute task"""
        count = self.seq_controller.get_action_count()
        if count == 0:
            QMessageBox.warning(self, "Notice", "Please add action steps first")
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self, "Confirm Execution",
            f"About to execute {count} steps.\n\nPlease confirm:\n• Work area is clear\n• No personnel near robot\n\nExecute now?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.seq_controller.execute_sequence()

    def on_pause(self):
        """Pause execution"""
        self.seq_controller.pause_execution()

    def on_resume(self):
        """Resume execution"""
        self.seq_controller.resume_execution()

    def on_stop(self):
        """Stop execution"""
        reply = QMessageBox.question(
            self, "Confirm Stop",
            "Are you sure you want to stop execution?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.seq_controller.stop_execution()

    def on_enable_freedrive(self):
        """Enable hand guiding (freedrive) mode"""
        try:
            # Disable execution buttons while in freedrive
            self.execution_status_bar.set_execution_enabled(False)

            # Enable freedrive mode
            success = self.seq_controller.robot_controller.enable_freedrive()

            if success:
                # Update button states
                self.enable_freedrive_btn.setEnabled(False)
                self.disable_freedrive_btn.setEnabled(True)

                QMessageBox.information(
                    self, "Hand Guiding Enabled",
                    "You can now move the robot manually by hand.\n\n"
                    "⚠️ Make sure the workspace is clear!\n\n"
                    "Click 'Disable Hand Guiding' when finished."
                )
            else:
                QMessageBox.warning(self, "Error", "Failed to enable hand guiding mode")
        except Exception as e:
            logger.error(f"Error enabling freedrive: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to enable hand guiding:\n{str(e)}")

    def on_disable_freedrive(self):
        """Disable hand guiding (freedrive) mode"""
        try:
            # Disable freedrive mode
            success = self.seq_controller.robot_controller.disable_freedrive()

            if success:
                # Update button states
                self.enable_freedrive_btn.setEnabled(True)
                self.disable_freedrive_btn.setEnabled(False)

                # Re-enable execution if there are actions
                count = self.seq_controller.get_action_count()
                self.execution_status_bar.set_execution_enabled(count > 0)

                QMessageBox.information(
                    self, "Hand Guiding Disabled",
                    "Hand guiding mode disabled.\n"
                    "Normal safety limits restored."
                )
            else:
                QMessageBox.warning(self, "Error", "Failed to disable hand guiding mode")
        except Exception as e:
            logger.error(f"Error disabling freedrive: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to disable hand guiding:\n{str(e)}")

    def on_save_task(self):
        """Save task"""
        if self.seq_controller.get_action_count() == 0:
            QMessageBox.warning(self, "Notice", "No actions to save")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Task",
            "",
            "Task Files (*.json);;All Files (*)"
        )

        if filename:
            if not filename.endswith('.json'):
                filename += '.json'

            task_name = self.task_name_edit.text().strip()
            if not task_name:
                task_name = "Untitled Task"

            success = self.seq_controller.save_to_file(filename, task_name)
            if success:
                QMessageBox.information(self, "Success", f"Task saved to:\n{filename}")

    def on_load_task(self):
        """Load task"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Task",
            "",
            "Task Files (*.json);;All Files (*)"
        )

        if filename:
            success = self.seq_controller.load_from_file(filename)
            if success:
                QMessageBox.information(self, "Success", "Task loaded successfully")

    def on_clear_sequence(self):
        """Clear sequence"""
        if self.seq_controller.get_action_count() == 0:
            return

        reply = QMessageBox.question(
            self, "Confirm Clear",
            "Are you sure you want to clear all steps?\n(This operation cannot be undone)",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.seq_controller.clear_sequence()

    # ========================================
    # Execution Status Callbacks
    # ========================================

    def on_execution_started(self, total_steps):
        """Execution started"""
        # Update execution status bar
        self.execution_status_bar.set_state("running", 0, total_steps)

        # Update guidance bar
        self.guidance_bar.update_context("executing")

        # Disable hand guiding during execution
        self.enable_freedrive_btn.setEnabled(False)
        self.disable_freedrive_btn.setEnabled(False)

        # Clear any previous execution highlights
        self.clear_execution_highlights()

    def on_execution_progress(self, current_step, total_steps):
        """Execution progress update"""
        # Update execution status bar with progress
        self.execution_status_bar.set_state("running", current_step, total_steps)

    def on_step_started(self, step_index, description):
        """Step started - highlight the current step"""
        logger.info(f"Step {step_index + 1} started: {description}")

        # Update execution status bar with current action
        total_steps = self.seq_controller.get_action_count()
        self.execution_status_bar.set_state("running", step_index + 1, total_steps, description)

        # Highlight the currently executing step
        if step_index < self.sequence_list.count():
            item = self.sequence_list.item(step_index)
            if item:
                item.setData(STEP_STATE_ROLE, StepState.RUNNING.value)
                self.step_states[step_index] = StepState.RUNNING.value
                # Scroll to the item to ensure it's visible (without selecting it)
                self.sequence_list.scrollToItem(item, QListWidget.PositionAtCenter)
                # Clear selection to prevent orange highlight from overriding our color
                self.sequence_list.clearSelection()
                self.sequence_list.viewport().update()

    def on_step_completed(self, step_index, success):
        """Step completed - update highlight based on result"""
        logger.info(f"Step {step_index + 1} completed: success={success}")

        # Update the step's appearance based on success/failure
        if step_index < self.sequence_list.count():
            item = self.sequence_list.item(step_index)
            if item:
                state = StepState.SUCCESS.value if success else StepState.FAILED.value
                item.setData(STEP_STATE_ROLE, state)
                self.step_states[step_index] = state
                # Clear selection to ensure color is visible
                self.sequence_list.clearSelection()
                self.sequence_list.viewport().update()

    def on_step_completed_with_timing(self, step_index, action_name, action_type, parameters, duration, success, error_msg):
        """Step completed with timing information - add to history"""
        self.history_panel.add_entry(
            step_index=step_index,
            action_name=action_name,
            action_type=action_type,
            parameters=parameters,
            duration=duration,
            success=success,
            error_message=error_msg
        )

    def on_execution_completed(self, success):
        """Execution completed"""
        total_steps = self.seq_controller.get_action_count()
        cancelled = getattr(self.seq_controller, "last_run_cancelled", False)

        if cancelled:
            completed_steps = sum(
                1 for state in self.step_states.values()
                if state == StepState.SUCCESS.value
            )
            self.execution_status_bar.set_state("stopped", completed_steps, total_steps)
            self.guidance_bar.update_context("stopped")
            QMessageBox.information(self, "Execution Stopped", "Task execution stopped by user.")
            self.seq_controller.last_run_cancelled = False
        else:
            # Update execution status bar
            if success:
                self.execution_status_bar.set_state("completed", total_steps, total_steps)
                self.guidance_bar.update_context("completed")
                QMessageBox.information(self, "Complete", "Task execution completed!")
            else:
                self.execution_status_bar.set_state("error", total_steps, total_steps)
                self.guidance_bar.update_context("error")

        # Re-enable hand guiding controls after execution
        self.enable_freedrive_btn.setEnabled(True)
        self.disable_freedrive_btn.setEnabled(False)

        # Clear all execution highlights after a brief delay to show final state
        # This allows user to see the success/failure colors before clearing
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, self.clear_execution_highlights)  # Clear after 2 seconds

    def on_execution_paused(self):
        """Execution paused"""
        # Update execution status bar and guidance
        self.execution_status_bar.set_state("paused")
        self.guidance_bar.update_context("paused")

    def on_execution_resumed(self):
        """Execution resumed"""
        # Update execution status bar and guidance
        total_steps = self.seq_controller.get_action_count()
        self.execution_status_bar.set_state("running", 0, total_steps)
        self.guidance_bar.update_context("executing")

    def on_error_occurred(self, error_message):
        """Error occurred"""
        logger.error(f"Sequential controller error: {error_message}")
        QMessageBox.warning(self, "Error", error_message)

    def clear_execution_highlights(self):
        """Clear all execution-related highlights from sequence list"""
        self.step_states = {}
        for i in range(self.sequence_list.count()):
            item = self.sequence_list.item(i)
            if item:
                item.setData(STEP_STATE_ROLE, StepState.PENDING.value)
        self.sequence_list.viewport().update()

    # ========================================
    # Subprogram-Related Handlers
    # ========================================

    def on_subprogram_selected_for_sequence(self, subprogram_id: str, params: dict, loop_count: int):
        """Handle subprogram selection from selector widget"""
        # Get subprogram info
        subprogram = self.subprogram_manager.get_subprogram(subprogram_id)
        if not subprogram:
            QMessageBox.warning(self, "Error", "Subprogram not found")
            return

        # Create CALL_SUBPROGRAM action
        action_params = {
            "subprogram_id": subprogram_id,
            "subprogram_name": subprogram.name,
            "parameter_values": params,
            "loop_count": loop_count
        }

        # Add to sequence
        self.seq_controller.add_action(ActionType.CALL_SUBPROGRAM, action_params)

        logger.info(f"Added subprogram call: {subprogram.name}")

    def on_subprogram_library_selected(self, subprogram):
        """Handle subprogram selection from library (for viewing/editing)"""
        # For now, just show info
        QMessageBox.information(
            self,
            f"Subprogram: {subprogram.name}",
            f"{subprogram.description}\n\n"
            f"Category: {subprogram.category}\n"
            f"Actions: {len(subprogram.actions)}\n"
            f"Parameters: {len(subprogram.parameters)}\n"
            f"Usage Count: {subprogram.usage_count}\n\n"
            "Use the edit button (✏️) on the card to modify this subprogram."
        )

    def on_create_new_subprogram(self):
        """Handle create new subprogram request"""
        # Open subprogram editor in a dialog
        editor_dialog = QDialog(self)
        editor_dialog.setWindowTitle("Create New Subprogram")
        editor_dialog.setMinimumSize(900, 600)

        layout = QVBoxLayout(editor_dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        editor = SubProgramEditor(None, editor_dialog, self.seq_controller)
        editor.saved.connect(lambda sp: self.on_subprogram_saved(sp, editor_dialog))
        editor.cancelled.connect(editor_dialog.reject)
        layout.addWidget(editor)

        editor_dialog.exec_()

    def on_subprogram_saved(self, subprogram, dialog):
        """Handle subprogram saved"""
        dialog.accept()
        QMessageBox.information(
            self,
            "Subprogram Saved",
            f"'{subprogram.name}' has been saved!\n\n"
            "You can now use it in your sequences by switching to the "
            "'Subprograms' view in the action library."
        )
        # Switch to subprogram library tab to show the new subprogram
        self.main_tabs.setCurrentIndex(1)  # Subprogram Library tab
