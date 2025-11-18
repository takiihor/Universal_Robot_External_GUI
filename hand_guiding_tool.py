#!/usr/bin/env python3
"""
Hand Guiding Tool - Position Teaching Tool

This tool is used for teaching robot positions, not part of program execution.
Users can manually move the robot and save positions, which will be saved to the position library.
"""

import logging
from typing import Dict, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QGroupBox, QLineEdit, QMessageBox, QInputDialog,
    QDialog, QDialogButtonBox, QFormLayout, QTextEdit,
    QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class HandGuidingTool(QWidget):
    """Hand Guiding Position Teaching Tool"""

    # Signals
    position_saved = pyqtSignal(str, dict)  # position name, position data

    def __init__(self, robot_controller, position_storage, parent=None):
        """
        Initialize Hand Guiding Tool

        Args:
            robot_controller: Robot controller interface (RobotController)
            position_storage: Position storage (Config.PRESET_POSITIONS)
            parent: Parent widget
        """
        super().__init__(parent)
        self.robot = robot_controller
        self.position_storage = position_storage
        self.is_freedrive_enabled = False

        # Position update timer
        self.position_update_timer = QTimer()
        self.position_update_timer.timeout.connect(self.update_position_display)

        self.setWindowTitle("Hand Guiding - Position Teaching Tool")
        self.setMinimumSize(900, 700)

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Title
        title_label = QLabel("🎓 Hand Guiding - Position Teaching Tool")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # Warning info
        info_label = QLabel(
            "⚠️ Note: This is a position teaching tool, not part of program execution.\n"
            "Use this tool to manually move the robot and save positions, "
            "then use these positions in Sequential Controller."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                background-color: #FFF3E0;
                padding: 10px;
                border-radius: 4px;
                border-left: 4px solid #FF9800;
            }
        """)
        main_layout.addWidget(info_label)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side: Control panel
        control_panel = self.create_control_panel()
        content_layout.addWidget(control_panel, 1)

        # Right side: Position list
        position_list_panel = self.create_position_list_panel()
        content_layout.addWidget(position_list_panel, 1)

        main_layout.addLayout(content_layout)

        # Operation guide
        guide_panel = self.create_guide_panel()
        main_layout.addWidget(guide_panel)

        # Bottom buttons
        button_layout = QHBoxLayout()

        export_btn = QPushButton("📤 Export Position Library")
        export_btn.clicked.connect(self.export_positions)
        button_layout.addWidget(export_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close_tool)
        button_layout.addWidget(close_btn)

        main_layout.addLayout(button_layout)

    def create_control_panel(self) -> QWidget:
        """Create control panel"""
        group = QGroupBox("Control Panel")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Freedrive control
        freedrive_layout = QVBoxLayout()

        self.enable_freedrive_btn = QPushButton("🤚 Enable Hand Guiding")
        self.enable_freedrive_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 15px;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.enable_freedrive_btn.clicked.connect(self.enable_freedrive)
        freedrive_layout.addWidget(self.enable_freedrive_btn)

        self.disable_freedrive_btn = QPushButton("🛑 Stop Hand Guiding")
        self.disable_freedrive_btn.setEnabled(False)
        self.disable_freedrive_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                font-weight: bold;
                padding: 15px;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.disable_freedrive_btn.clicked.connect(self.disable_freedrive)
        freedrive_layout.addWidget(self.disable_freedrive_btn)

        layout.addLayout(freedrive_layout)

        # Status display
        status_group = QGroupBox("Robot Status")
        status_layout = QFormLayout()

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        status_layout.addRow("Status:", self.status_label)

        self.position_label = QLabel("N/A")
        self.position_label.setStyleSheet("font-family: monospace;")
        status_layout.addRow("Current Position:", self.position_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Position control
        position_control_group = QGroupBox("Position Control")
        position_control_layout = QVBoxLayout()

        self.save_position_btn = QPushButton("💾 Save Current Position")
        self.save_position_btn.setEnabled(False)
        self.save_position_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.save_position_btn.clicked.connect(self.save_current_position)
        position_control_layout.addWidget(self.save_position_btn)

        position_control_group.setLayout(position_control_layout)
        layout.addWidget(position_control_group)

        # Gripper control
        gripper_group = QGroupBox("Gripper Test")
        gripper_layout = QHBoxLayout()

        self.open_gripper_btn = QPushButton("🤲 Open Gripper")
        self.open_gripper_btn.setEnabled(False)
        self.open_gripper_btn.clicked.connect(self.open_gripper)
        gripper_layout.addWidget(self.open_gripper_btn)

        self.close_gripper_btn = QPushButton("✊ Close Gripper")
        self.close_gripper_btn.setEnabled(False)
        self.close_gripper_btn.clicked.connect(self.close_gripper)
        gripper_layout.addWidget(self.close_gripper_btn)

        gripper_group.setLayout(gripper_layout)
        layout.addWidget(gripper_group)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_position_list_panel(self) -> QWidget:
        """Create position list panel"""
        group = QGroupBox("Saved Positions")
        layout = QVBoxLayout()

        # Position list
        self.position_list = QListWidget()
        self.position_list.setStyleSheet("""
            QListWidget {
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
        """)
        layout.addWidget(self.position_list)

        # Load existing positions
        self.refresh_position_list()

        # Operation buttons
        btn_layout = QHBoxLayout()

        load_btn = QPushButton("📥 Load")
        load_btn.setToolTip("Move robot to selected position")
        load_btn.clicked.connect(self.load_selected_position)
        btn_layout.addWidget(load_btn)

        test_btn = QPushButton("🔍 Test")
        test_btn.setToolTip("Test move to selected position (slow speed)")
        test_btn.clicked.connect(self.test_selected_position)
        btn_layout.addWidget(test_btn)

        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(self.delete_selected_position)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)

        group.setLayout(layout)
        return group

    def create_guide_panel(self) -> QWidget:
        """Create operation guide panel"""
        group = QGroupBox("📝 Operation Guide")
        layout = QVBoxLayout()

        guide_text = QTextEdit()
        guide_text.setReadOnly(True)
        guide_text.setMaximumHeight(150)
        guide_text.setHtml("""
            <ol style="line-height: 1.6;">
                <li>Click <b>"Enable Hand Guiding"</b> to enter teaching mode</li>
                <li>Gently move the robot arm by hand to target position</li>
                <li>Click <b>"Save Current Position"</b> and enter position name (e.g., position1)</li>
                <li>Repeat steps 2-3 to create all required positions</li>
                <li>Use <b>"Open/Close Gripper"</b> to test gripper actions</li>
                <li>When finished, click <b>"Stop Hand Guiding"</b></li>
                <li>Use saved position names in <b>Sequential Controller</b> to create programs</li>
            </ol>
        """)
        guide_text.setStyleSheet("background-color: #E3F2FD; border: none;")
        layout.addWidget(guide_text)

        group.setLayout(layout)
        return group

    # ========================================
    # Freedrive Control
    # ========================================

    def enable_freedrive(self):
        """Enable freedrive mode"""
        try:
            # Check if connected
            if not self.robot._connected:
                QMessageBox.warning(
                    self,
                    "Not Connected",
                    "Please connect to the robot first."
                )
                return

            # Confirmation dialog
            reply = QMessageBox.question(
                self,
                "Confirm Enable Hand Guiding",
                "About to enable hand guiding mode.\n\n"
                "Please confirm:\n"
                "• No obstacles around the robot\n"
                "• You are ready to manually move the robot\n\n"
                "Continue?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # Enable freedrive
            success = self.robot.enable_freedrive_mode()

            if success:
                self.is_freedrive_enabled = True

                # Update UI
                self.enable_freedrive_btn.setEnabled(False)
                self.disable_freedrive_btn.setEnabled(True)
                self.save_position_btn.setEnabled(True)
                self.open_gripper_btn.setEnabled(True)
                self.close_gripper_btn.setEnabled(True)

                self.status_label.setText("Hand Guiding Active")
                self.status_label.setStyleSheet("font-weight: bold; color: #FF9800;")

                # Start updating position display
                self.position_update_timer.start(100)  # Update every 100ms

                logger.info("Hand guiding enabled")

                QMessageBox.information(
                    self,
                    "Hand Guiding Enabled",
                    "You can now manually move the robot arm.\n"
                    "Move to target position, then click 'Save Current Position'."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Enable Failed",
                    "Unable to enable hand guiding mode. Please check robot connection."
                )

        except Exception as e:
            logger.error(f"Failed to enable freedrive: {e}")
            QMessageBox.critical(self, "Error", f"Failed to enable hand guiding: {str(e)}")

    def disable_freedrive(self):
        """Disable freedrive mode"""
        try:
            # Stop freedrive
            success = self.robot.disable_freedrive_mode()

            if success:
                self.is_freedrive_enabled = False

                # Update UI
                self.enable_freedrive_btn.setEnabled(True)
                self.disable_freedrive_btn.setEnabled(False)
                self.save_position_btn.setEnabled(False)
                self.open_gripper_btn.setEnabled(False)
                self.close_gripper_btn.setEnabled(False)

                self.status_label.setText("Ready")
                self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")

                # Stop updating position display
                self.position_update_timer.stop()

                logger.info("Hand guiding disabled")

                QMessageBox.information(
                    self,
                    "Hand Guiding Stopped",
                    "Hand guiding mode stopped.\n"
                    "Your saved positions can be used in Sequential Controller."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Stop Failed",
                    "Unable to stop hand guiding mode."
                )

        except Exception as e:
            logger.error(f"Failed to disable freedrive: {e}")
            QMessageBox.critical(self, "Error", f"Failed to stop hand guiding: {str(e)}")

    def update_position_display(self):
        """Update position display"""
        try:
            if self.is_freedrive_enabled:
                # Get current position
                position = self.robot.get_current_pose()

                if position:
                    # Display position (XYZ only)
                    pos_text = (
                        f"X: {position[0]:.3f} m\n"
                        f"Y: {position[1]:.3f} m\n"
                        f"Z: {position[2]:.3f} m"
                    )
                    self.position_label.setText(pos_text)

        except Exception as e:
            logger.error(f"Failed to update position: {e}")

    # ========================================
    # Position Management
    # ========================================

    def save_current_position(self):
        """Save current position"""
        try:
            # Get current position
            position = self.robot.get_current_pose()

            if not position:
                QMessageBox.warning(self, "Warning", "Unable to get current position")
                return

            # Input position name
            position_name, ok = QInputDialog.getText(
                self,
                "Save Position",
                "Please enter position name:\n(e.g., position1, pickup_point, home)",
                QLineEdit.Normal,
                ""
            )

            if not ok or not position_name.strip():
                return

            position_name = position_name.strip()

            # Check if name already exists
            if position_name in self.position_storage:
                reply = QMessageBox.question(
                    self,
                    "Position Exists",
                    f"Position '{position_name}' already exists.\nOverwrite?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply != QMessageBox.Yes:
                    return

            # Save position
            position_data = position  # Just save the pose list

            self.position_storage[position_name] = position_data

            # Emit signal
            self.position_saved.emit(position_name, position_data)

            # Refresh list
            self.refresh_position_list()

            # Save to config file
            self.save_position_storage()

            logger.info(f"Position '{position_name}' saved: {position}")

            QMessageBox.information(
                self,
                "Save Successful",
                f"Position '{position_name}' saved!\n\n"
                f"You can use this position in Sequential Controller."
            )

        except Exception as e:
            logger.error(f"Failed to save position: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save position: {str(e)}")

    def load_selected_position(self):
        """Load selected position (move robot to that position)"""
        current_item = self.position_list.currentItem()

        if not current_item:
            QMessageBox.warning(self, "Hint", "Please select a position first")
            return

        position_name = current_item.text().replace("📍 ", "")

        # Confirm
        reply = QMessageBox.question(
            self,
            "Confirm Move",
            f"Move robot to position '{position_name}'?\n\n"
            "⚠️ Please ensure no obstacles around!",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # If in freedrive mode, stop it first
            if self.is_freedrive_enabled:
                self.disable_freedrive()

            # Get position data
            position_data = self.position_storage.get(position_name)

            if not position_data:
                QMessageBox.warning(self, "Error", f"Position '{position_name}' not found")
                return

            # Move robot
            success = self.robot.move_to_pose_linear(position_data, speed=0.1, acceleration=0.1)

            if success:
                QMessageBox.information(self, "Success", f"Moved to position '{position_name}'")
            else:
                QMessageBox.warning(self, "Failed", f"Failed to move to position '{position_name}'")

        except Exception as e:
            logger.error(f"Failed to load position: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load position: {str(e)}")

    def test_selected_position(self):
        """Test selected position (move slowly)"""
        current_item = self.position_list.currentItem()

        if not current_item:
            QMessageBox.warning(self, "Hint", "Please select a position first")
            return

        position_name = current_item.text().replace("📍 ", "")

        try:
            # If in freedrive mode, stop it first
            if self.is_freedrive_enabled:
                self.disable_freedrive()

            position_data = self.position_storage.get(position_name)

            if not position_data:
                QMessageBox.warning(self, "Error", f"Position '{position_name}' not found")
                return

            # Move slowly for testing
            success = self.robot.move_to_pose_linear(
                position_data,
                speed=0.05,  # Very slow speed
                acceleration=0.05
            )

            if success:
                QMessageBox.information(self, "Test Success", f"Successfully tested position '{position_name}'")
            else:
                QMessageBox.warning(self, "Test Failed", f"Failed to test position '{position_name}'")

        except Exception as e:
            logger.error(f"Failed to test position: {e}")
            QMessageBox.critical(self, "Error", f"Failed to test position: {str(e)}")

    def delete_selected_position(self):
        """Delete selected position"""
        current_item = self.position_list.currentItem()

        if not current_item:
            QMessageBox.warning(self, "Hint", "Please select a position first")
            return

        position_name = current_item.text().replace("📍 ", "")

        # Confirm
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete position '{position_name}'?\n\n"
            "This operation cannot be undone!",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # Delete position
            if position_name in self.position_storage:
                del self.position_storage[position_name]

                # Refresh list
                self.refresh_position_list()

                # Save to config file
                self.save_position_storage()

                logger.info(f"Position '{position_name}' deleted")

                QMessageBox.information(self, "Delete Success", f"Position '{position_name}' deleted")
            else:
                QMessageBox.warning(self, "Error", f"Position '{position_name}' not found")

        except Exception as e:
            logger.error(f"Failed to delete position: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete position: {str(e)}")

    def refresh_position_list(self):
        """Refresh position list"""
        self.position_list.clear()

        for position_name in sorted(self.position_storage.keys()):
            item = QListWidgetItem(f"📍 {position_name}")
            self.position_list.addItem(item)

    # ========================================
    # Gripper Control
    # ========================================

    def open_gripper(self):
        """Open gripper"""
        try:
            # Check if gripper control exists
            if not hasattr(self.robot, 'open_gripper'):
                QMessageBox.information(
                    self,
                    "Not Available",
                    "Gripper control not available in current robot controller."
                )
                return

            success = self.robot.open_gripper()

            if success:
                logger.info("Gripper opened")
                QMessageBox.information(self, "Success", "Gripper opened")
            else:
                QMessageBox.warning(self, "Failed", "Failed to open gripper")

        except Exception as e:
            logger.error(f"Failed to open gripper: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open gripper: {str(e)}")

    def close_gripper(self):
        """Close gripper"""
        try:
            # Check if gripper control exists
            if not hasattr(self.robot, 'close_gripper'):
                QMessageBox.information(
                    self,
                    "Not Available",
                    "Gripper control not available in current robot controller."
                )
                return

            success = self.robot.close_gripper()

            if success:
                logger.info("Gripper closed")
                QMessageBox.information(self, "Success", "Gripper closed")
            else:
                QMessageBox.warning(self, "Failed", "Failed to close gripper")

        except Exception as e:
            logger.error(f"Failed to close gripper: {e}")
            QMessageBox.critical(self, "Error", f"Failed to close gripper: {str(e)}")

    # ========================================
    # File Operations
    # ========================================

    def save_position_storage(self):
        """Save position storage to file"""
        try:
            from config import Config
            Config.save_config()
            logger.info("Position storage saved")
        except Exception as e:
            logger.error(f"Failed to save position storage: {e}")

    def export_positions(self):
        """Export position library"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Position Library",
                "positions.json",
                "JSON Files (*.json);;All Files (*)"
            )

            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.position_storage, f, indent=2, ensure_ascii=False)

                QMessageBox.information(
                    self,
                    "Export Success",
                    f"Position library exported to:\n{filename}"
                )

        except Exception as e:
            logger.error(f"Failed to export positions: {e}")
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

    def close_tool(self):
        """Close tool"""
        # If still in freedrive mode, stop it first
        if self.is_freedrive_enabled:
            reply = QMessageBox.question(
                self,
                "Confirm Close",
                "Hand guiding is still active. Stop it and close?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.disable_freedrive()
                self.close()
            return

        self.close()
