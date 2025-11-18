"""
Execution Status Bar Component

Provides unified execution control with clear visual status feedback.
Combines progress display, status information, and control buttons in one cohesive component.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from datetime import datetime


class ExecutionStatusBar(QWidget):
    """
    Unified execution status and control bar

    Signals:
        execute_clicked: User clicked execute button
        pause_clicked: User clicked pause button
        resume_clicked: User clicked resume button
        stop_clicked: User clicked stop button
    """

    execute_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_state = "idle"
        self.current_step = 0
        self.total_steps = 0
        self.current_action_name = ""
        self.setup_ui()

    def setup_ui(self):
        """Setup UI components - COMPACT VERTICAL LAYOUT"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Status display container - cleaner header style
        status_container = QWidget()
        status_container.setObjectName("statusContainer")
        status_container.setStyleSheet("""
            QWidget#statusContainer {
                background: #FFFFFF;
                border: 2px solid #E0E0E0;
                border-radius: 10px;
            }
        """)
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(14, 12, 14, 12)
        status_layout.setSpacing(8)

        # Header row with icon, text block, progress chip
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        self.status_icon = QLabel("⏸")
        self.status_icon.setFixedSize(36, 36)
        self.status_icon.setAlignment(Qt.AlignCenter)
        self.status_icon.setStyleSheet("""
            QLabel {
                font-size: 18px;
                background: #FFE0B2;
                border-radius: 10px;
            }
        """)
        header_row.addWidget(self.status_icon)

        text_block = QVBoxLayout()
        text_block.setSpacing(4)

        self.status_text = QLabel("System Ready")
        self.status_text.setStyleSheet("""
            QLabel {
                font-weight: 600;
                font-size: 14px;
                color: #212121;
            }
        """)
        text_block.addWidget(self.status_text)

        self.status_detail = QLabel("Waiting for task execution...")
        self.status_detail.setWordWrap(True)
        self.status_detail.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #757575;
            }
        """)
        text_block.addWidget(self.status_detail)

        self.progress_label = QLabel("0/0")
        self.progress_label.setStyleSheet("""
            QLabel {
                background: #E3F2FD;
                color: #1E88E5;
                padding: 4px 12px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        text_block.addWidget(self.progress_label, alignment=Qt.AlignLeft)

        self.timestamp = QLabel("")
        self.timestamp.setStyleSheet("""
            QLabel {
                color: #9E9E9E;
                font-size: 9px;
                font-family: monospace;
            }
        """)
        text_block.addWidget(self.timestamp, alignment=Qt.AlignLeft)

        header_row.addLayout(text_block, 1)
        status_layout.addLayout(header_row)

        layout.addWidget(status_container)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #E0E0E0;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                             stop:0 #4CAF50, stop:1 #66BB6A);
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # VERTICAL BUTTON LAYOUT - Each button gets full width
        # Execute button
        self.execute_btn = QPushButton("▶ Execute Task")
        self.execute_btn.setFixedHeight(38)
        self.execute_btn.setCursor(Qt.PointingHandCursor)
        self.execute_btn.setStyleSheet(self._get_button_style("#4CAF50", "#45A049"))
        self.execute_btn.clicked.connect(self.execute_clicked.emit)
        layout.addWidget(self.execute_btn)

        # Pause/Resume button
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setFixedHeight(36)
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet(self._get_button_style("#FF9800", "#FB8C00"))
        self.pause_btn.clicked.connect(self._on_pause_resume_clicked)
        layout.addWidget(self.pause_btn)

        # Stop button
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(self._get_button_style("#F44336", "#E53935"))
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.stop_btn)

    def _get_button_style(self, base_color: str, hover_color: str) -> str:
        """Generate button stylesheet"""
        return f"""
            QPushButton {{
                background: {base_color};
                color: white;
                border: none;
                border-radius: 21px;
                font-weight: bold;
                font-size: 13px;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background: {hover_color};
            }}
            QPushButton:pressed {{
                background: {base_color};
                padding-top: 2px;
            }}
            QPushButton:disabled {{
                background: #BDBDBD;
                color: #757575;
            }}
        """

    def _on_pause_resume_clicked(self):
        """Handle pause/resume button click"""
        if self.current_state == "paused":
            self.resume_clicked.emit()
        else:
            self.pause_clicked.emit()

    def update_timestamp(self):
        """Update timestamp to current time"""
        self.timestamp.setText(datetime.now().strftime("%H:%M:%S"))

    def set_state(self, state: str, current_step: int = 0, total_steps: int = 0, action_name: str = ""):
        """
        Update execution state

        Args:
            state: One of "idle", "running", "paused", "stopped", "completed", "error"
            current_step: Current step number (1-indexed)
            total_steps: Total number of steps
            action_name: Name of current action being executed
        """
        self.current_state = state
        self.current_step = current_step
        self.total_steps = total_steps
        self.current_action_name = action_name
        self.update_timestamp()

        # Update progress
        if total_steps > 0:
            progress_percent = int((current_step / total_steps) * 100)
            self.progress_bar.setValue(progress_percent)
            self.progress_label.setText(f"{current_step}/{total_steps}")
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText("0/0")

        # Update UI based on state
        if state == "idle":
            self.status_icon.setText("⏸")
            self.status_text.setText("System Ready")
            self.status_detail.setText("Waiting for task execution...")
            self.execute_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("⏸ Pause")
            self.stop_btn.setEnabled(False)
            self._update_progress_style("#90CAF9", "#0D47A1")

        elif state == "running":
            self.status_icon.setText("▶")
            self.status_text.setText("Executing Task")
            if action_name:
                self.status_detail.setText(f"Step {current_step}/{total_steps}: {action_name}")
            else:
                self.status_detail.setText(f"Processing step {current_step} of {total_steps}...")
            self.execute_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.pause_btn.setText("⏸ Pause")
            self.stop_btn.setEnabled(True)
            self._update_progress_style("#4CAF50", "#FFFFFF")

        elif state == "paused":
            self.status_icon.setText("⏸")
            self.status_text.setText("Task Paused")
            self.status_detail.setText("⚠️ Verify safety before resuming execution")
            self.status_detail.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #E65100;
                    font-weight: bold;
                }
            """)
            self.execute_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.pause_btn.setText("▶ Resume")
            self.pause_btn.setStyleSheet(self._get_button_style("#4CAF50", "#45A049"))
            self.stop_btn.setEnabled(True)
            self._update_progress_style("#FF9800", "#FFFFFF")

        elif state == "stopped":
            self.status_icon.setText("⏹")
            self.status_text.setText("Task Stopped")
            self.status_detail.setText("Execution stopped by user")
            self.status_detail.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #757575;
                }
            """)
            self.execute_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("⏸ Pause")
            self.pause_btn.setStyleSheet(self._get_button_style("#FF9800", "#FB8C00"))
            self.stop_btn.setEnabled(False)
            self._update_progress_style("#F44336", "#FFFFFF")

        elif state == "completed":
            self.status_icon.setText("✓")
            self.status_text.setText("Task Completed")
            self.status_detail.setText(f"Successfully executed {total_steps} step(s)")
            self.status_detail.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #2E7D32;
                    font-weight: bold;
                }
            """)
            self.execute_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("⏸ Pause")
            self.pause_btn.setStyleSheet(self._get_button_style("#FF9800", "#FB8C00"))
            self.stop_btn.setEnabled(False)
            self._update_progress_style("#4CAF50", "#FFFFFF")

        elif state == "error":
            self.status_icon.setText("✗")
            self.status_text.setText("Execution Failed")
            self.status_detail.setText("Check error message and fix the issue before retrying")
            self.status_detail.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #C62828;
                    font-weight: bold;
                }
            """)
            self.execute_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("⏸ Pause")
            self.pause_btn.setStyleSheet(self._get_button_style("#FF9800", "#FB8C00"))
            self.stop_btn.setEnabled(False)
            self._update_progress_style("#F44336", "#FFFFFF")

    def _update_progress_style(self, bg_color: str, text_color: str):
        """Update progress label styling"""
        self.progress_label.setStyleSheet(f"""
            QLabel {{
                background: {bg_color};
                color: {text_color};
                padding: 6px 16px;
                border-radius: 16px;
                font-weight: bold;
                font-size: 13px;
                min-width: 50px;
            }}
        """)

    def set_execution_enabled(self, enabled: bool):
        """Enable/disable execute button based on whether there are actions"""
        if self.current_state == "idle":
            self.execute_btn.setEnabled(enabled)
