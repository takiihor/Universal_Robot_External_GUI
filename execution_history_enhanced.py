"""
Enhanced Execution History

Tree-based execution history showing hierarchical subprogram calls.
Displays call stack depth and nested execution context.
"""

import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QLabel, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

logger = logging.getLogger(__name__)


class EnhancedExecutionHistory(QWidget):
    """
    Enhanced Execution History with Tree View

    Shows execution history in a hierarchical tree structure,
    making it easy to see subprogram calls and nesting.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_subprogram_item = None  # Track current subprogram parent
        self.execution_start_time = None
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title and controls
        header_layout = QHBoxLayout()

        title = QLabel("📊 Execution History (Hierarchical)")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title.setFont(title_font)
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Clear button
        self.clear_btn = QPushButton("🗑️ Clear History")
        self.clear_btn.clicked.connect(self.clear_history)
        header_layout.addWidget(self.clear_btn)

        # Export button
        self.export_btn = QPushButton("💾 Export")
        self.export_btn.clicked.connect(self.export_history)
        header_layout.addWidget(self.export_btn)

        layout.addLayout(header_layout)

        # Tree widget
        self.history_tree = QTreeWidget()
        self.history_tree.setHeaderLabels([
            "Time",
            "Context",
            "Action",
            "Status",
            "Duration"
        ])

        # Set column widths
        self.history_tree.setColumnWidth(0, 80)   # Time
        self.history_tree.setColumnWidth(1, 150)  # Context
        self.history_tree.setColumnWidth(2, 300)  # Action
        self.history_tree.setColumnWidth(3, 80)   # Status
        self.history_tree.setColumnWidth(4, 80)   # Duration

        # Styling
        self.history_tree.setAlternatingRowColors(True)
        self.history_tree.setStyleSheet("""
            QTreeWidget {
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 3px;
            }
        """)

        layout.addWidget(self.history_tree)

        # Statistics
        self.stats_label = QLabel("Total: 0 actions  |  Success: 0  |  Failed: 0")
        self.stats_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.stats_label)

    def start_execution(self):
        """Mark start of execution"""
        self.execution_start_time = datetime.now()
        self.current_subprogram_item = None

    def add_main_action(self, step_index: int, action_name: str,
                       action_type: str, parameters: dict,
                       duration: float, success: bool, error_msg: str = ""):
        """
        Add a main program action to history

        Args:
            step_index: Action index in main sequence
            action_name: Action name
            action_type: Action type string
            parameters: Action parameters
            duration: Execution duration
            success: Whether action succeeded
            error_msg: Error message if failed
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Create top-level item
        item = QTreeWidgetItem(self.history_tree)
        item.setText(0, timestamp)
        item.setText(1, "Main Program")
        item.setText(2, action_name)
        item.setText(3, "✅ Success" if success else "❌ Failed")
        item.setText(4, f"{duration:.2f}s")

        # Color based on status
        if success:
            item.setBackground(3, QColor("#E8F5E9"))  # Light green
        else:
            item.setBackground(3, QColor("#FFEBEE"))  # Light red
            if error_msg:
                item.setToolTip(2, f"Error: {error_msg}")

        # If this is a subprogram call, it becomes the parent for subsequent actions
        if action_type == "call_subprogram":
            self.current_subprogram_item = item
            # Add depth indicator
            item.setText(1, "📦 Subprogram")
            item.setForeground(1, QColor("#673AB7"))
            font = item.font(1)
            font.setBold(True)
            item.setFont(1, font)

        # Expand the item if it's a subprogram
        if action_type == "call_subprogram":
            item.setExpanded(True)

        self.update_statistics()

    def add_subprogram_action(self, subprogram_name: str, action_name: str,
                             action_index: int, duration: float,
                             success: bool, error_msg: str = ""):
        """
        Add a subprogram sub-action to history

        Args:
            subprogram_name: Name of the subprogram
            action_name: Name of the action
            action_index: Index within subprogram
            duration: Execution duration
            success: Whether action succeeded
            error_msg: Error message if failed
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Determine parent item
        if self.current_subprogram_item:
            parent = self.current_subprogram_item
        else:
            # No current subprogram, add to root
            parent = None

        # Create child item
        if parent:
            item = QTreeWidgetItem(parent)
        else:
            item = QTreeWidgetItem(self.history_tree)

        item.setText(0, timestamp)
        item.setText(1, f"  └─ Step {action_index + 1}")
        item.setText(2, action_name)
        item.setText(3, "✅" if success else "❌")
        item.setText(4, f"{duration:.2f}s")

        # Color based on status
        if success:
            item.setForeground(3, QColor("#4CAF50"))
        else:
            item.setForeground(3, QColor("#F44336"))
            if error_msg:
                item.setToolTip(2, f"Error: {error_msg}")

        # Style sub-items
        item.setForeground(1, QColor("#888"))

        self.update_statistics()

    def end_subprogram(self):
        """Mark end of current subprogram"""
        self.current_subprogram_item = None

    def update_statistics(self):
        """Update statistics label"""
        total = 0
        success = 0
        failed = 0

        # Count all items (including children)
        iterator = QTreeWidgetItemIterator(self.history_tree)
        while iterator.value():
            item = iterator.value()
            total += 1

            status_text = item.text(3)
            if "Success" in status_text or "✅" in status_text:
                success += 1
            elif "Failed" in status_text or "❌" in status_text:
                failed += 1

            iterator += 1

        self.stats_label.setText(
            f"Total: {total} actions  |  "
            f"Success: {success}  |  "
            f"Failed: {failed}"
        )

    def clear_history(self):
        """Clear history"""
        self.history_tree.clear()
        self.current_subprogram_item = None
        self.update_statistics()
        logger.info("Execution history cleared")

    def export_history(self):
        """Export history to text file"""
        from PyQt5.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Execution History",
            f"execution_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("Execution History Report\n")
                    f.write("=" * 80 + "\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                    self._export_tree_item(f, self.history_tree.invisibleRootItem(), 0)

                    f.write("\n" + "=" * 80 + "\n")
                    f.write(self.stats_label.text())

                logger.info(f"Execution history exported to: {filename}")

            except Exception as e:
                logger.error(f"Failed to export history: {e}", exc_info=True)

    def _export_tree_item(self, file, item, depth):
        """Recursively export tree items"""
        for i in range(item.childCount()):
            child = item.child(i)

            # Build line with indentation
            indent = "  " * depth
            time = child.text(0)
            context = child.text(1)
            action = child.text(2)
            status = child.text(3)
            duration = child.text(4)

            line = f"{indent}[{time}] {context}: {action} - {status} ({duration})\n"
            file.write(line)

            # Recursively export children
            if child.childCount() > 0:
                self._export_tree_item(file, child, depth + 1)
