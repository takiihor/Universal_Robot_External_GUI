"""
Categorized Action Library Widget

Provides a categorized, card-based display of available actions for the Sequential Controller.
Organizes actions into tabs by category with visual cards for easy selection.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QScrollArea,
    QGridLayout, QFrame, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from sequential_controller import ActionType, ACTION_METADATA, ACTION_CATEGORIES


class ActionCard(QFrame):
    """Action card widget - clickable card displaying an action"""
    clicked = pyqtSignal(object)  # Emits ActionType when clicked

    def __init__(self, action_type: ActionType, color: str, parent=None):
        super().__init__(parent)
        self.action_type = action_type
        self.setup_ui(color)

    def setup_ui(self, color: str):
        """Setup card UI"""
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
        self.setMinimumHeight(130)
        self.setMaximumHeight(160)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Icon - LARGER and with proper container
        icon_label = QLabel(metadata.get("icon", "⚙️"))
        icon_label.setStyleSheet(f"font-size: 52px; background: transparent; border: none; color: {color};")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setMinimumHeight(60)  # Ensure full icon visibility
        layout.addWidget(icon_label)

        # Name - darker color for better readability on light background
        name_label = QLabel(metadata.get("name", "Unknown"))
        name_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px; background: transparent; border: none;")
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        # Description (truncated) - darker color
        desc = metadata.get("description", "")
        if len(desc) > 50:
            desc = desc[:47] + "..."
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("color: #666; font-size: 10px; background: transparent; border: none;")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Tooltip with full description
        self.setToolTip(metadata.get("description", ""))

    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.action_type)
        super().mousePressEvent(event)

    @staticmethod
    def hex_to_rgba(hex_color: str, alpha: float) -> str:
        """Convert hex color to RGBA with transparency"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {alpha})"

    @staticmethod
    def darken_color(hex_color: str, percent: int) -> str:
        """Darken hex color by percentage"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, r - int(r * percent / 100))
        g = max(0, g - int(g * percent / 100))
        b = max(0, b - int(b * percent / 100))
        return f"#{r:02x}{g:02x}{b:02x}"


class CategorizedActionLibrary(QWidget):
    """Categorized action library widget with tabs and cards"""
    action_selected = pyqtSignal(object)  # Emits ActionType when card clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Info label
        info_label = QLabel("💡 Click an action card to add it to the sequence")
        info_label.setStyleSheet("color: gray; font-size: 11px; padding: 8px; background-color: #F5F5F5; border-radius: 4px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Tabbed categories - HORIZONTAL on TOP
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)  # Horizontal tabs on top
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                padding: 8px 15px;
                margin-right: 2px;
                font-size: 12px;
                min-width: 100px;
                text-align: center;
            }
            QTabBar::tab:selected {
                background-color: #E3F2FD;
                font-weight: bold;
                border-top: 3px solid #2196F3;
            }
            QTabBar::tab:hover {
                background-color: #F5F5F5;
            }
        """)

        # Create a tab for each category
        for cat_id, cat_info in ACTION_CATEGORIES.items():
            page = self.create_category_page(cat_info)
            tab_label = f"{cat_info['icon']} {cat_info['name']}"
            self.tab_widget.addTab(page, tab_label)

        layout.addWidget(self.tab_widget)

    def create_category_page(self, category_info: dict) -> QWidget:
        """Create category page with action cards"""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(10, 10, 10, 10)
        page_layout.setSpacing(10)

        # Category description
        desc_label = QLabel(category_info.get("description", ""))
        desc_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px; font-style: italic;")
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

    def on_card_clicked(self, action_type: ActionType):
        """Handle card click - emit signal"""
        self.action_selected.emit(action_type)
