"""
Subprogram Library Widget

A browsable library of saved subprograms displayed as cards.
Users can search, filter by category, and select subprograms to use.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QScrollArea,
    QFrame, QTabWidget, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from subprogram_models import SubProgram
from subprogram_manager import SubProgramManager

logger = logging.getLogger(__name__)


class SubProgramCard(QFrame):
    """
    Visual card representing a subprogram

    Displays icon, name, description, usage stats, and action buttons.
    """

    clicked = pyqtSignal(SubProgram)
    edit_clicked = pyqtSignal(SubProgram)
    delete_clicked = pyqtSignal(SubProgram)

    def __init__(self, subprogram: SubProgram, parent=None):
        super().__init__(parent)
        self.subprogram = subprogram
        self.init_ui()

    def init_ui(self):
        """Initialize card UI"""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Title row: Icon + Name + Buttons
        title_layout = QHBoxLayout()
        title_layout.setSpacing(4)

        # Icon
        icon_label = QLabel(self.subprogram.icon or "📦")
        icon_label.setStyleSheet("font-size: 16px;")
        icon_label.setFixedWidth(20)
        title_layout.addWidget(icon_label)

        # Name
        name_label = QLabel(self.subprogram.name)
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(9)
        name_label.setFont(name_font)
        title_layout.addWidget(name_label, 1)

        # Edit button
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(18, 18)
        edit_btn.setToolTip("Edit subprogram")
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.subprogram))
        edit_btn.clicked.connect(lambda e: e)  # Stop propagation
        title_layout.addWidget(edit_btn)

        # Delete button
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(18, 18)
        delete_btn.setToolTip("Delete subprogram")
        delete_btn.setStyleSheet("QPushButton:hover { background-color: #ffcccc; }")
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.subprogram))
        delete_btn.clicked.connect(lambda e: e)  # Stop propagation
        title_layout.addWidget(delete_btn)

        layout.addLayout(title_layout)

        # Description (slightly larger font)
        if self.subprogram.description:
            desc_label = QLabel(self.subprogram.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666; font-size: 10px;")
            desc_label.setMaximumHeight(36)
            layout.addWidget(desc_label)

        # Compact stats row: category, steps, params, usage
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(4)

        # Category badge (inline)
        if self.subprogram.category and self.subprogram.category != "Other":
            category_label = QLabel(self.subprogram.category)
            category_label.setStyleSheet("""
                background-color: #E3F2FD;
                color: #1976D2;
                padding: 1px 4px;
                border-radius: 6px;
                font-size: 9px;
                font-weight: bold;
            """)
            stats_layout.addWidget(category_label)

        # Stats
        stats_label = QLabel(
            f"{len(self.subprogram.actions)}📊 {len(self.subprogram.parameters)}⚙️ {self.subprogram.usage_count}×"
        )
        stats_label.setStyleSheet("color: #999; font-size: 8px;")
        stats_layout.addWidget(stats_label)
        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        # Card styling - more compact
        self.setStyleSheet("""
            SubProgramCard {
                background: white;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 3px;
            }
            SubProgramCard:hover {
                border-color: #673AB7;
                background: #F3E5F5;
            }
        """)

    def mousePressEvent(self, event):
        """Handle card click"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.subprogram)
        super().mousePressEvent(event)


class SubProgramLibrary(QWidget):
    """
    Subprogram Library Panel

    Displays all available subprograms organized by category with search.
    """

    subprogram_selected = pyqtSignal(SubProgram)
    create_new_clicked = pyqtSignal()

    def __init__(self, manager: SubProgramManager = None, parent=None):
        super().__init__(parent)
        self.manager = manager or SubProgramManager.get_instance()
        self.init_ui()
        self.connect_signals()
        self.refresh_library()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title
        title = QLabel("📦 Subprogram Library")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Search bar and New button
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search subprograms...")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input, 3)

        self.new_btn = QPushButton("➕ New Subprogram")
        self.new_btn.setStyleSheet("""
            QPushButton {
                background-color: #673AB7;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5E35B1;
            }
        """)
        self.new_btn.clicked.connect(self.create_new_clicked.emit)
        search_layout.addWidget(self.new_btn, 1)

        layout.addLayout(search_layout)

        # Category tabs
        self.category_tabs = QTabWidget()
        self.category_tabs.setTabPosition(QTabWidget.North)

        # Create tabs for each category
        self.category_views = {}
        categories = [
            ("⭐ Favorites", "Favorites"),
            ("🤏 Pick & Place", "Pick & Place"),
            ("🔧 Assembly", "Assembly"),
            ("🔍 Inspection", "Inspection"),
            ("📚 All", "All")
        ]

        for tab_name, category in categories:
            scroll_area = self.create_category_view(category)
            self.category_tabs.addTab(scroll_area, tab_name)
            self.category_views[category] = scroll_area

        layout.addWidget(self.category_tabs)

        # Status label
        self.status_label = QLabel("No subprograms available")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

    def create_category_view(self, category: str) -> QScrollArea:
        """Create scrollable view for a category"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Content widget with grid layout
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(6)
        grid.setContentsMargins(3, 3, 3, 3)

        # Store reference for later updates
        content.setProperty("category", category)
        content.setProperty("grid_layout", grid)

        scroll.setWidget(content)
        return scroll

    def connect_signals(self):
        """Connect manager signals"""
        self.manager.subprogram_added.connect(self.on_subprogram_added)
        self.manager.subprogram_updated.connect(self.on_subprogram_updated)
        self.manager.subprogram_deleted.connect(self.on_subprogram_deleted)
        self.manager.subprograms_loaded.connect(self.refresh_library)

    def refresh_library(self):
        """Refresh all category views"""
        logger.info("Refreshing subprogram library")

        for category, scroll_area in self.category_views.items():
            self.refresh_category(category, scroll_area)

        # Update status
        total_count = len(self.manager.get_all_subprograms())
        if total_count > 0:
            self.status_label.setText(f"Total: {total_count} subprograms")
        else:
            self.status_label.setText("No subprograms available. Click 'New Subprogram' to create one.")

    def refresh_category(self, category: str, scroll_area: QScrollArea):
        """Refresh a specific category view"""
        content = scroll_area.widget()
        grid = content.property("grid_layout")

        # Clear existing cards
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get subprograms for this category
        subprograms = self.manager.get_by_category(category)

        # Filter by search if active
        search_text = self.search_input.text().strip().lower()
        if search_text:
            subprograms = [
                sp for sp in subprograms
                if search_text in sp.name.lower() or
                   search_text in sp.description.lower()
            ]

        # Create cards in 6-column grid for very compact display
        for i, subprogram in enumerate(subprograms):
            card = SubProgramCard(subprogram)
            card.clicked.connect(self.subprogram_selected.emit)
            card.edit_clicked.connect(self.on_edit_subprogram)
            card.delete_clicked.connect(self.on_delete_subprogram)

            row = i // 6
            col = i % 6
            grid.addWidget(card, row, col)

        # Add stretch at the end
        grid.setRowStretch(grid.rowCount(), 1)

    def on_search_changed(self):
        """Handle search text change"""
        self.refresh_library()

    def on_subprogram_added(self, subprogram: SubProgram):
        """Handle subprogram added"""
        logger.info(f"Subprogram added: {subprogram.name}")
        self.refresh_library()

    def on_subprogram_updated(self, subprogram: SubProgram):
        """Handle subprogram updated"""
        logger.info(f"Subprogram updated: {subprogram.name}")
        self.refresh_library()

    def on_subprogram_deleted(self, subprogram_id: str):
        """Handle subprogram deleted"""
        logger.info(f"Subprogram deleted: {subprogram_id}")
        self.refresh_library()

    def on_edit_subprogram(self, subprogram: SubProgram):
        """Handle edit button click"""
        logger.info(f"Edit subprogram: {subprogram.name}")
        # This will be handled by the parent widget to open the editor
        # For now, just show a message
        QMessageBox.information(
            self,
            "Edit Subprogram",
            f"Opening editor for: {subprogram.name}\n\n"
            "(Editor will be implemented in next step)"
        )

    def on_delete_subprogram(self, subprogram: SubProgram):
        """Handle delete button click"""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{subprogram.name}'?\n\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.manager.delete_subprogram(subprogram.id)
            if success:
                QMessageBox.information(self, "Success", f"Deleted: {subprogram.name}")
            else:
                QMessageBox.warning(self, "Error", f"Failed to delete: {subprogram.name}")
