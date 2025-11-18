"""
Categorized Action Library Widget - Improved Version

Uses QListWidget + QStackedWidget instead of vertical QTabWidget
to avoid text rotation issues and provide better control over layout.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QScrollArea, QGridLayout, QFrame, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QFont

from sequential_controller import ActionType, ACTION_METADATA, ACTION_CATEGORIES


class ActionCard(QFrame):
    """Action card widget - clickable card displaying an action with responsive design"""
    clicked = pyqtSignal(object)  # Emits ActionType when clicked

    def __init__(self, action_type: ActionType, color: str, parent=None):
        super().__init__(parent)
        self.action_type = action_type
        self.base_color = color
        self.setup_ui(color)

    def setup_ui(self, color: str):
        """Setup card UI with responsive design"""
        metadata = ACTION_METADATA.get(self.action_type, {})

        # Convert solid color to RGBA with transparency
        rgba_bg = self.hex_to_rgba(color, 0.15)  # 15% opacity for background
        rgba_hover = self.hex_to_rgba(color, 0.25)  # 25% opacity for hover

        # Card styling with transparency
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            ActionCard {{
                background-color: {rgba_bg};
                border-radius: 8px;
                padding: 15px;
                border: 2px solid {color};
            }}
            ActionCard:hover {{
                background-color: {rgba_hover};
                border: 2px solid {color};
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(140)
        self.setMaximumHeight(180)
        self.setMaximumWidth(220)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Icon - Fixed size container with responsive font
        self.icon_label = QLabel(metadata.get("icon", "⚙️"))
        self.icon_label.setFixedSize(64, 64)  # Fixed container size
        self.icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 48px;
                background: transparent;
                border: none;
                color: {color};
            }}
        """)
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label, 0, Qt.AlignCenter)

        # Name - with word wrap and minimum height
        self.name_label = QLabel(metadata.get("name", "Unknown"))
        self.name_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-weight: bold;
                font-size: 13px;
                background: transparent;
                border: none;
            }}
        """)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setMinimumHeight(30)
        layout.addWidget(self.name_label)

        # Description (truncated) - with word wrap
        desc = metadata.get("description", "")
        if len(desc) > 50:
            desc = desc[:47] + "..."
        self.desc_label = QLabel(desc)
        self.desc_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 10px;
                background: transparent;
                border: none;
            }
        """)
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.desc_label.setMinimumHeight(20)
        layout.addWidget(self.desc_label)

        # Add stretch to push content up
        layout.addStretch()

        # Tooltip with full description
        self.setToolTip(metadata.get("description", ""))

    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.action_type)
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        """Handle resize - adjust icon size if needed"""
        super().resizeEvent(event)
        # Could add dynamic font scaling here if needed
        # width = self.width()
        # font_size = min(48, width // 3)  # Scale icon based on width

    @staticmethod
    def hex_to_rgba(hex_color: str, alpha: float) -> str:
        """Convert hex color to RGBA with transparency"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {alpha})"


class CategoryListItem(QWidget):
    """Custom widget for category list items with icon and text side by side"""

    def __init__(self, icon: str, name: str, color: str, parent=None):
        super().__init__(parent)
        self.setup_ui(icon, name, color)

    def setup_ui(self, icon: str, name: str, color: str):
        """Setup UI with horizontal layout"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Icon label - fixed size
        icon_label = QLabel(icon)
        icon_label.setFixedSize(32, 32)
        icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                color: {color};
                background: transparent;
                border: none;
            }}
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # Name label - expandable
        name_label = QLabel(name)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)
        name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        layout.addWidget(name_label, 1)


class CategorizedActionLibrary(QWidget):
    """Categorized action library widget using List + Stack layout"""
    action_selected = pyqtSignal(object)  # Emits ActionType when card clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(450)  # keep library from stretching too wide
        self.setup_ui()

    def setup_ui(self):
        """Setup UI with List + Stack layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Info label
        info_label = QLabel("💡 Click an action card to add it to the sequence")
        info_label.setStyleSheet("""
            QLabel {
                color: gray;
                font-size: 11px;
                padding: 8px;
                background-color: #F5F5F5;
                border-radius: 4px;
            }
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Horizontal layout for list and stack
        content_layout = QHBoxLayout()
        content_layout.setSpacing(5)

        # Left: Category list
        self.category_list = QListWidget()
        self.category_list.setFixedWidth(150)
        self.category_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                outline: none;
            }
            QListWidget::item {
                border: none;
                padding: 0px;
                margin: 2px 0px;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                border-left: 3px solid #2196F3;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
            }
        """)
        self.category_list.setSpacing(2)
        self.category_list.currentRowChanged.connect(self.on_category_changed)
        content_layout.addWidget(self.category_list)

        # Right: Stacked widget for category pages
        self.category_stack = QStackedWidget()
        self.category_stack.setMaximumWidth(260)  # limit cards panel width
        self.category_stack.setStyleSheet("""
            QStackedWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
        """)
        content_layout.addWidget(self.category_stack, 1)

        layout.addLayout(content_layout)

        # Populate categories
        self.populate_categories()

    def populate_categories(self):
        """Populate category list and stack pages"""
        for cat_id, cat_info in ACTION_CATEGORIES.items():
            # Create list item with custom widget
            item = QListWidgetItem(self.category_list)
            item_widget = CategoryListItem(
                cat_info['icon'],
                cat_info['name'],
                cat_info['color']
            )
            item.setSizeHint(item_widget.sizeHint())
            self.category_list.addItem(item)
            self.category_list.setItemWidget(item, item_widget)

            # Create stack page
            page = self.create_category_page(cat_info)
            self.category_stack.addWidget(page)

        # Select first category
        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)

    def create_category_page(self, category_info: dict) -> QWidget:
        """Create category page with action cards"""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(10, 10, 10, 10)
        page_layout.setSpacing(10)

        # Category description
        desc_label = QLabel(category_info.get("description", ""))
        desc_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 11px;
                padding: 5px;
                font-style: italic;
                background: transparent;
            }
        """)
        desc_label.setWordWrap(True)
        page_layout.addWidget(desc_label)

        # Scroll area for cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Card container
        card_container = QWidget()
        card_container.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout(card_container)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(5, 5, 5, 5)

        # Create cards (2 per row)
        row, col = 0, 0
        max_cols = 2

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

    def on_category_changed(self, index: int):
        """Handle category selection change"""
        if index >= 0:
            self.category_stack.setCurrentIndex(index)

    def on_card_clicked(self, action_type: ActionType):
        """Handle card click - emit signal"""
        self.action_selected.emit(action_type)
