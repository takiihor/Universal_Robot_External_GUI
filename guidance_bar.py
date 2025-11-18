"""
Guidance Bar Component

Provides context-aware guidance to help users understand the workflow.
Shows current step, helpful instructions, and safety reminders.
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class GuidanceBar(QWidget):
    """Smart guidance bar that provides context-aware instructions"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_context = "empty_sequence"
        self.setup_ui()

    def setup_ui(self):
        """Setup UI components"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(15)

        # Step indicator badge
        self.step_indicator = QLabel("Step 1/3")
        self.step_indicator.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                             stop:0 #2196F3, stop:1 #1976D2);
                color: white;
                padding: 6px 14px;
                border-radius: 14px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        self.step_indicator.setFixedHeight(28)
        layout.addWidget(self.step_indicator)

        # Guidance text
        self.guidance_text = QLabel("👉 Click an action card from the library to add it to your sequence")
        self.guidance_text.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 13px;
                padding-left: 5px;
            }
        """)
        font = QFont()
        font.setPointSize(10)
        self.guidance_text.setFont(font)
        layout.addWidget(self.guidance_text, 1)

        # Safety tip (always visible)
        self.safety_tip = QLabel("⚠️ Ensure workspace is clear before execution")
        self.safety_tip.setStyleSheet("""
            QLabel {
                color: #E65100;
                font-size: 11px;
                padding: 5px 12px;
                background: #FFF3E0;
                border-radius: 4px;
                border-left: 3px solid #FF9800;
            }
        """)
        layout.addWidget(self.safety_tip)

        # Overall container styling
        self.setStyleSheet("""
            GuidanceBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 #F8F9FA, stop:1 #E9ECEF);
                border: 1px solid #DEE2E6;
                border-radius: 6px;
            }
        """)

    def update_context(self, context: str, action_count: int = 0):
        """
        Update guidance based on current context

        Args:
            context: One of "empty_sequence", "has_actions", "ready_to_execute", "executing", "paused"
            action_count: Number of actions in sequence
        """
        self.current_context = context

        if context == "empty_sequence":
            self.step_indicator.setText("Step 1/3")
            self.guidance_text.setText("👉 Click an action card from the library to add it to your sequence")
            self.safety_tip.setVisible(True)

        elif context == "has_actions":
            self.step_indicator.setText("Step 2/3")
            self.guidance_text.setText(f"✓ {action_count} action(s) added. Review parameters and order, then click Execute")
            self.safety_tip.setVisible(True)

        elif context == "ready_to_execute":
            self.step_indicator.setText("Step 3/3")
            self.guidance_text.setText("🚀 Ready to execute! Click the Execute button to start the task")
            self.safety_tip.setVisible(True)
            self.safety_tip.setStyleSheet("""
                QLabel {
                    color: #D84315;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 5px 12px;
                    background: #FFEBEE;
                    border-radius: 4px;
                    border-left: 3px solid #F44336;
                }
            """)

        elif context == "executing":
            self.step_indicator.setText("Running")
            self.step_indicator.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                 stop:0 #FF9800, stop:1 #F57C00);
                    color: white;
                    padding: 6px 14px;
                    border-radius: 14px;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            self.guidance_text.setText("⚡ Task executing... Monitor progress in the sequence panel")
            self.safety_tip.setVisible(True)

        elif context == "paused":
            self.step_indicator.setText("Paused")
            self.step_indicator.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                 stop:0 #FFC107, stop:1 #FFA000);
                    color: white;
                    padding: 6px 14px;
                    border-radius: 14px;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            self.guidance_text.setText("⏸ Task paused. Verify safety before clicking Resume")
            self.safety_tip.setText("⚠️ Verify robot position and workspace safety")
            self.safety_tip.setVisible(True)

        elif context == "completed":
            self.step_indicator.setText("Complete")
            self.step_indicator.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                 stop:0 #4CAF50, stop:1 #388E3C);
                    color: white;
                    padding: 6px 14px;
                    border-radius: 14px;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            self.guidance_text.setText("✅ Task completed successfully! You can modify and re-execute, or create a new sequence")
            self.safety_tip.setVisible(False)

        elif context == "error":
            self.step_indicator.setText("Error")
            self.step_indicator.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                 stop:0 #F44336, stop:1 #D32F2F);
                    color: white;
                    padding: 6px 14px;
                    border-radius: 14px;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            self.guidance_text.setText("❌ Execution failed. Check the error message and fix the issue")
            self.safety_tip.setText("⚠️ Verify robot is in safe state")
            self.safety_tip.setVisible(True)
