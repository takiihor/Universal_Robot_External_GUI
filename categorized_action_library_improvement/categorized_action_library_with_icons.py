"""
Categorized Action Library with QIcon Support

Uses QIcon/QPixmap instead of emoji for consistent cross-platform rendering.
Combines List + Stack layout with proper icon handling.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QScrollArea, QGridLayout, QFrame, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QFont, QPixmap, QIcon

from sequential_controller import ActionType, ACTION_METADATA, ACTION_CATEGORIES
from icon_helper import IconGenerator


class ActionCardWithIcon(QFrame):
    """Action card widget using QPixmap for icons"""
    clicked = pyqtSignal(object)

    def __init__(self, action_type: ActionType, color: str, icon: QPixmap = None, parent=None):
        super().__init__(parent)
        self.action_type = action_type
        self.base_color = color
        self.icon_pixmap = icon
        self.setup_ui(color)

    def setup_ui(self, color: str):
        """Setup card UI with QPixmap icon"""
        metadata = ACTION_METADATA.get(self.action_type, {})

        # Convert solid color to RGBA with transparency
        rgba_bg = self.hex_to_rgba(color, 0.15)
        rgba_hover = self.hex_to_rgba(color, 0.25)

        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            ActionCardWithIcon {{
                background-color: {rgba_bg};
                border-radius: 8px;
                padding: 15px;
                border: 2px solid {color};
            }}
            ActionCardWithIcon:hover {{
                background-color: {rgba_hover};
                border: 2px solid {color};
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(140)
        self.setMaximumHeight(180)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Icon - QLabel with QPixmap
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(64, 64)
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        # Set pixmap (generate if not provided)
        if self.icon_pixmap:
            scaled_pixmap = self.icon_pixmap.scaled(
                56, 56,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.icon_label.setPixmap(scaled_pixmap)
        else:
            # Fallback to emoji if no pixmap provided
            emoji = metadata.get("icon", "⚙️")
            pixmap = IconGenerator.create_pixmap_from_emoji(emoji, 56, color)
            self.icon_label.setPixmap(pixmap)
        
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.icon_label, 0, Qt.AlignCenter)

        # Name
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

        # Description
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

        layout.addStretch()
        self.setToolTip(metadata.get("description", ""))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.action_type)
        super().mousePressEvent(event)

    @staticmethod
    def hex_to_rgba(hex_color: str, alpha: float) -> str:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {alpha})"


class CategoryListItemWithIcon(QWidget):
    """Category list item using QPixmap icon"""

    def __init__(self, icon_pixmap: QPixmap, name: str, color: str, parent=None):
        super().__init__(parent)
        self.setup_ui(icon_pixmap, name, color)

    def setup_ui(self, icon_pixmap: QPixmap, name: str, color: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Icon - QLabel with QPixmap
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignCenter)
        scaled_pixmap = icon_pixmap.scaled(
            28, 28,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        icon_label.setPixmap(scaled_pixmap)
        icon_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_label)

        # Name
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


class CategorizedActionLibraryWithIcons(QWidget):
    """Categorized action library using List + Stack with QIcon support"""
    action_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.action_icons = {}  # Cache for action icons
        self.category_icons = {}  # Cache for category icons
        self.setup_ui()

    def setup_ui(self):
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

        # Horizontal layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(5)

        # Category list
        self.category_list = QListWidget()
        self.category_list.setFixedWidth(180)
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

        # Stack
        self.category_stack = QStackedWidget()
        self.category_stack.setStyleSheet("""
            QStackedWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
        """)
        content_layout.addWidget(self.category_stack, 1)

        layout.addLayout(content_layout)

        # Pre-generate icons
        self.generate_icons()
        
        # Populate
        self.populate_categories()

    def generate_icons(self):
        """Pre-generate all icons"""
        # Generate category icons
        for cat_id, cat_info in ACTION_CATEGORIES.items():
            pixmap = IconGenerator.create_pixmap_from_emoji(
                cat_info["icon"],
                64,
                cat_info["color"]
            )
            self.category_icons[cat_id] = pixmap

        # Generate action icons
        for action_type, metadata in ACTION_METADATA.items():
            emoji = metadata.get("icon", "⚙️")
            
            # Find category color
            color = "#000000"
            for cat_info in ACTION_CATEGORIES.values():
                if action_type in cat_info["actions"]:
                    color = cat_info["color"]
                    break
            
            pixmap = IconGenerator.create_pixmap_from_emoji(emoji, 64, color)
            self.action_icons[action_type] = pixmap

    def populate_categories(self):
        for cat_id, cat_info in ACTION_CATEGORIES.items():
            # Create list item
            item = QListWidgetItem(self.category_list)
            item_widget = CategoryListItemWithIcon(
                self.category_icons[cat_id],
                cat_info['name'],
                cat_info['color']
            )
            item.setSizeHint(item_widget.sizeHint())
            self.category_list.addItem(item)
            self.category_list.setItemWidget(item, item_widget)

            # Create page
            page = self.create_category_page(cat_info)
            self.category_stack.addWidget(page)

        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)

    def create_category_page(self, category_info: dict) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(10, 10, 10, 10)
        page_layout.setSpacing(10)

        # Description
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

        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Cards
        card_container = QWidget()
        card_container.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout(card_container)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(5, 5, 5, 5)

        row, col = 0, 0
        max_cols = 2

        for action_type in category_info["actions"]:
            icon_pixmap = self.action_icons.get(action_type)
            card = ActionCardWithIcon(
                action_type,
                category_info["color"],
                icon_pixmap
            )
            card.clicked.connect(self.on_card_clicked)
            grid_layout.addWidget(card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        grid_layout.setRowStretch(row + 1, 1)

        scroll_area.setWidget(card_container)
        page_layout.addWidget(scroll_area)

        return page

    def on_category_changed(self, index: int):
        if index >= 0:
            self.category_stack.setCurrentIndex(index)

    def on_card_clicked(self, action_type: ActionType):
        self.action_selected.emit(action_type)
