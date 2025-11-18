"""
Execution History Panel Module

Displays execution history with timestamps, duration tracking, and export functionality.
"""

import logging
import csv
import json
from datetime import datetime
from typing import List, Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QComboBox, QLineEdit, QFileDialog, QMessageBox, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont

logger = logging.getLogger(__name__)


class ExecutionHistoryEntry:
    """Data class for execution history entry"""

    def __init__(self,
                 timestamp: datetime,
                 step_index: int,
                 action_name: str,
                 action_type: str,
                 parameters: Dict[str, Any],
                 duration: float,
                 success: bool,
                 error_message: str = ""):
        self.timestamp = timestamp
        self.step_index = step_index
        self.action_name = action_name
        self.action_type = action_type
        self.parameters = parameters
        self.duration = duration
        self.success = success
        self.error_message = error_message

    def to_dict(self) -> dict:
        """Convert to dictionary for export"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "step_index": self.step_index,
            "action_name": self.action_name,
            "action_type": self.action_type,
            "parameters": self.parameters,
            "duration_seconds": round(self.duration, 3),
            "success": self.success,
            "error_message": self.error_message
        }

    def get_status_text(self) -> str:
        """Get status as text"""
        return "✓ Success" if self.success else "✗ Failed"

    def get_duration_text(self) -> str:
        """Get formatted duration text"""
        if self.duration < 1:
            return f"{self.duration*1000:.0f} ms"
        else:
            return f"{self.duration:.2f} s"


class ExecutionHistoryPanel(QWidget):
    """
    Execution history panel with logging, filtering, and export.

    Features:
    - Timestamped execution log
    - Duration tracking
    - Success/failure color coding
    - Export to CSV, TXT, JSON
    - Clear and filter options
    - Statistics display
    """

    # Signals
    history_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.history: List[ExecutionHistoryEntry] = []
        self.sequence_start_time = None
        self.sequence_end_time = None
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Header with title and controls
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Title
        title_label = QLabel("📋 Execution History")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Filter dropdown
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Success Only", "Failures Only"])
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        self.filter_combo.setMaximumWidth(150)
        header_layout.addWidget(QLabel("Filter:"))
        header_layout.addWidget(self.filter_combo)

        # Clear button
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.clicked.connect(self.clear_history)
        self.clear_btn.setMaximumWidth(120)
        header_layout.addWidget(self.clear_btn)

        # Export buttons
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.clicked.connect(lambda: self.export_history("csv"))
        self.export_csv_btn.setMaximumWidth(100)
        header_layout.addWidget(self.export_csv_btn)

        self.export_json_btn = QPushButton("Export JSON")
        self.export_json_btn.clicked.connect(lambda: self.export_history("json"))
        self.export_json_btn.setMaximumWidth(100)
        header_layout.addWidget(self.export_json_btn)

        layout.addLayout(header_layout)

        # Statistics panel
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)

        self.total_actions_label = QLabel("Total Actions: 0")
        self.success_count_label = QLabel("Success: 0")
        self.failure_count_label = QLabel("Failures: 0")
        self.total_time_label = QLabel("Total Time: 0.00 s")
        self.avg_time_label = QLabel("Avg Time: 0.00 s")

        stats_labels = [
            self.total_actions_label,
            self.success_count_label,
            self.failure_count_label,
            self.total_time_label,
            self.avg_time_label
        ]

        for label in stats_labels:
            label.setStyleSheet("""
                QLabel {
                    padding: 5px 10px;
                    background-color: #f5f5f5;
                    border-radius: 3px;
                    font-size: 11px;
                }
            """)
            stats_layout.addWidget(label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Timestamp", "Step", "Action", "Parameters", "Duration", "Status"
        ])

        # Set column widths
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Timestamp
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Step
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Action
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Parameters
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Duration
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Status

        # Table styling
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                gridline-color: #e0e0e0;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: 1px solid #ddd;
                font-weight: bold;
                font-size: 11px;
            }
        """)

        layout.addWidget(self.history_table, 1)

        logger.info("ExecutionHistoryPanel initialized")

    def add_entry(self,
                  step_index: int,
                  action_name: str,
                  action_type: str,
                  parameters: Dict[str, Any],
                  duration: float,
                  success: bool,
                  error_message: str = ""):
        """Add a new history entry"""
        entry = ExecutionHistoryEntry(
            timestamp=datetime.now(),
            step_index=step_index,
            action_name=action_name,
            action_type=action_type,
            parameters=parameters,
            duration=duration,
            success=success,
            error_message=error_message
        )

        self.history.append(entry)
        self.add_table_row(entry)
        self.update_statistics()

        # Scroll to bottom to show latest entry
        self.history_table.scrollToBottom()

        logger.debug(f"Added history entry: {action_name} ({duration:.3f}s, success={success})")

    def add_table_row(self, entry: ExecutionHistoryEntry):
        """Add entry to table"""
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)

        # Timestamp
        time_str = entry.timestamp.strftime("%H:%M:%S")
        time_item = QTableWidgetItem(time_str)
        time_item.setTextAlignment(Qt.AlignCenter)
        self.history_table.setItem(row, 0, time_item)

        # Step index
        step_item = QTableWidgetItem(str(entry.step_index + 1))
        step_item.setTextAlignment(Qt.AlignCenter)
        self.history_table.setItem(row, 1, step_item)

        # Action name
        action_item = QTableWidgetItem(entry.action_name)
        self.history_table.setItem(row, 2, action_item)

        # Parameters (compact format)
        params_str = self.format_parameters(entry.parameters)
        params_item = QTableWidgetItem(params_str)
        params_item.setToolTip(json.dumps(entry.parameters, indent=2))
        self.history_table.setItem(row, 3, params_item)

        # Duration
        duration_item = QTableWidgetItem(entry.get_duration_text())
        duration_item.setTextAlignment(Qt.AlignCenter)
        self.history_table.setItem(row, 4, duration_item)

        # Status with color coding
        status_item = QTableWidgetItem(entry.get_status_text())
        status_item.setTextAlignment(Qt.AlignCenter)

        if entry.success:
            status_item.setBackground(QColor(200, 255, 200))  # Light green
            status_item.setForeground(QColor(0, 100, 0))      # Dark green
        else:
            status_item.setBackground(QColor(255, 200, 200))  # Light red
            status_item.setForeground(QColor(150, 0, 0))      # Dark red
            if entry.error_message:
                status_item.setToolTip(f"Error: {entry.error_message}")

        self.history_table.setItem(row, 5, status_item)

    def format_parameters(self, params: Dict[str, Any]) -> str:
        """Format parameters for compact display"""
        if not params:
            return "-"

        # Show first 3 parameters in compact form
        items = []
        for key, value in list(params.items())[:3]:
            if isinstance(value, float):
                items.append(f"{key}={value:.2f}")
            else:
                items.append(f"{key}={value}")

        result = ", ".join(items)
        if len(params) > 3:
            result += f" (+{len(params)-3} more)"

        return result

    def update_statistics(self):
        """Update statistics labels"""
        total = len(self.history)
        success = sum(1 for e in self.history if e.success)
        failure = total - success

        total_time = sum(e.duration for e in self.history)
        avg_time = total_time / total if total > 0 else 0

        self.total_actions_label.setText(f"Total Actions: {total}")
        self.success_count_label.setText(f"Success: {success}")
        self.failure_count_label.setText(f"Failures: {failure}")
        self.total_time_label.setText(f"Total Time: {total_time:.2f} s")
        self.avg_time_label.setText(f"Avg Time: {avg_time:.3f} s")

        # Update success label color
        if failure == 0 and total > 0:
            self.success_count_label.setStyleSheet("""
                QLabel {
                    padding: 5px 10px;
                    background-color: #c8ffc8;
                    border-radius: 3px;
                    font-size: 11px;
                    color: #006400;
                    font-weight: bold;
                }
            """)
        else:
            self.success_count_label.setStyleSheet("""
                QLabel {
                    padding: 5px 10px;
                    background-color: #f5f5f5;
                    border-radius: 3px;
                    font-size: 11px;
                }
            """)

    def apply_filter(self):
        """Apply filter to table"""
        filter_text = self.filter_combo.currentText()

        for row in range(self.history_table.rowCount()):
            show_row = True

            if filter_text == "Success Only":
                status_item = self.history_table.item(row, 5)
                show_row = "Success" in status_item.text()
            elif filter_text == "Failures Only":
                status_item = self.history_table.item(row, 5)
                show_row = "Failed" in status_item.text()

            self.history_table.setRowHidden(row, not show_row)

    def clear_history(self):
        """Clear all history"""
        if not self.history:
            return

        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all execution history?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.history.clear()
            self.history_table.setRowCount(0)
            self.update_statistics()
            self.history_cleared.emit()
            logger.info("Execution history cleared")

    def export_history(self, format_type: str):
        """Export history to file"""
        if not self.history:
            QMessageBox.information(
                self,
                "No Data",
                "No execution history to export."
            )
            return

        # Get file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format_type == "csv":
            default_name = f"execution_history_{timestamp}.csv"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export CSV",
                default_name,
                "CSV Files (*.csv)"
            )

            if file_path:
                self.export_to_csv(file_path)

        elif format_type == "json":
            default_name = f"execution_history_{timestamp}.json"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export JSON",
                default_name,
                "JSON Files (*.json)"
            )

            if file_path:
                self.export_to_json(file_path)

    def export_to_csv(self, file_path: str):
        """Export history to CSV file"""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow([
                    "Timestamp", "Step", "Action Name", "Action Type",
                    "Parameters", "Duration (s)", "Success", "Error Message"
                ])

                # Data rows
                for entry in self.history:
                    writer.writerow([
                        entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        entry.step_index + 1,
                        entry.action_name,
                        entry.action_type,
                        json.dumps(entry.parameters),
                        round(entry.duration, 3),
                        "Yes" if entry.success else "No",
                        entry.error_message
                    ])

            QMessageBox.information(
                self,
                "Export Successful",
                f"History exported to:\n{file_path}"
            )
            logger.info(f"History exported to CSV: {file_path}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export CSV:\n{str(e)}"
            )
            logger.error(f"CSV export failed: {e}", exc_info=True)

    def export_to_json(self, file_path: str):
        """Export history to JSON file"""
        try:
            data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_actions": len(self.history),
                "success_count": sum(1 for e in self.history if e.success),
                "failure_count": sum(1 for e in self.history if not e.success),
                "total_duration_seconds": sum(e.duration for e in self.history),
                "history": [entry.to_dict() for entry in self.history]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            QMessageBox.information(
                self,
                "Export Successful",
                f"History exported to:\n{file_path}"
            )
            logger.info(f"History exported to JSON: {file_path}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export JSON:\n{str(e)}"
            )
            logger.error(f"JSON export failed: {e}", exc_info=True)

    def mark_sequence_start(self):
        """Mark the start of a sequence execution"""
        self.sequence_start_time = datetime.now()
        logger.debug("Sequence execution started")

    def mark_sequence_end(self, success: bool):
        """Mark the end of a sequence execution"""
        self.sequence_end_time = datetime.now()
        if self.sequence_start_time:
            duration = (self.sequence_end_time - self.sequence_start_time).total_seconds()
            logger.info(f"Sequence execution completed: success={success}, duration={duration:.2f}s")


# Test the history panel
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    window = ExecutionHistoryPanel()
    window.setWindowTitle("Execution History Panel Test")
    window.resize(1000, 600)

    # Add some test entries
    window.add_entry(
        step_index=0,
        action_name="Move to Position",
        action_type="move_to_position",
        parameters={"position_name": "home", "speed_percent": 50},
        duration=2.345,
        success=True
    )

    window.add_entry(
        step_index=1,
        action_name="Wait",
        action_type="wait",
        parameters={"seconds": 5},
        duration=5.001,
        success=True
    )

    window.add_entry(
        step_index=2,
        action_name="Set Digital Output",
        action_type="set_digital_output",
        parameters={"pin": 0, "state": "high"},
        duration=0.152,
        success=False,
        error_message="Pin connection error"
    )

    window.show()
    sys.exit(app.exec_())
