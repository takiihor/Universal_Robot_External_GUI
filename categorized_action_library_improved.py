"""
Further Optimized Categorized Action Library Widget

Key improvements:
- Wider panel (420-450px) to prevent content cropping
- Smaller, more compact card design (140x65px)
- Better 2-column layout that fits perfectly
- Optimized font sizes to prevent overflow
- Improved spacing and readability
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QScrollArea, QGridLayout, QFrame, QLabel, QApplication, QToolTip, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QFont, QPalette

from sequential_controller import ActionType, ACTION_METADATA, ACTION_CATEGORIES


class ActionCard(QFrame):
    """Compact action card that prevents text cropping"""
    clicked = pyqtSignal(object)

    def __init__(self, action_type: ActionType, color: str, parent=None):
        super().__init__(parent)
        self.action_type = action_type
        self.base_color = color
        self.setup_ui(color)

    def setup_ui(self, color: str):
        """Setup card UI with compact, non-cropping design"""
        metadata = ACTION_METADATA.get(self.action_type, {})

        # Convert solid color to RGBA with transparency
        rgba_bg = self.hex_to_rgba(color, 0.10)
        rgba_hover = self.hex_to_rgba(color, 0.20)

        # Compact card styling
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            ActionCard {{
                background-color: {rgba_bg};
                border-radius: 4px;
                padding: 5px;
                border: 1px solid {color};
            }}
            ActionCard:hover {{
                background-color: {rgba_hover};
                border: 2px solid {color};
                padding: 4px;
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)
        
        # Force white background on this specific widget's tooltips
        self.setStyleSheet(self.styleSheet() + """
            ActionCard QToolTip {
                background-color: white;
                color: black;
                border: 1px solid #ccc;
            }
        """)
        
        # Compact dimensions that fit 2 columns in wider panel
        # For 550px panel: 550 - 140 (category) - 16 (margins) - 8 (spacing) = ~386px / 2 = 193px per card
        # Adjust these values if you change panel width
        self.setMinimumSize(175, 62)
        self.setMaximumSize(190, 68)

        # Tight layout
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(5, 4, 5, 4)

        # Name label - compact and bold
        # category font size
        name = metadata.get("name", "Unknown")
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-weight: bold;
                font-size: 14px;
                background: transparent;
                border: none;
            }}
        """)
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(24)
        layout.addWidget(self.name_label)

        # Description - very compact
        desc = metadata.get("description", "")
        # Shorter description for compact cards
        if len(desc) > 55:
            desc = desc[:52] + "..."

        self.desc_label = QLabel(desc)
        self.desc_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 9px;
                background: transparent;
                border: none;
                line-height: 1.15;
            }
        """)
        self.desc_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)
        layout.addStretch()

        # Enhanced tooltip with simpler HTML to avoid color conflicts
        full_description = metadata.get("description", "No description available")
        
        # Parameter hints
        param_hints = self.get_parameter_hints()
        param_text = " | ".join(param_hints) if param_hints else ""
        
        # Use plain text tooltip format which respects system colors better
        tooltip_html = f"""<b style='color: {color};'>{metadata.get("name", "Unknown")}</b><br><hr>
{full_description}
{f"<br><br><small>{param_text}</small>" if param_text else ""}
<br><br><i><small>💡 Click to add to sequence</small></i>"""
        
        self.setToolTip(tooltip_html)

    def get_parameter_hints(self):
        """Get parameter hints for the action"""
        hints_map = {
            "move_to_position": ["• Position name, Speed"],
            "relative_move": ["• Direction, Distance, Speed"],
            "wait": ["• Duration (seconds)"],
            "set_force_level": ["• Force level (0-100)"],
            "enable_force_mode": ["• Enable pressure sensing"],
            "disable_force_mode": ["• Disable pressure sensing"],
            "set_digital_output": ["• Pin number, State (high/low)"],
            "wait_for_digital_input": ["• Pin number, Expected state"],
            "read_digital_input": ["• Pin number"],
            "set_analog_output": ["• Pin number, Voltage (0-10V)"],
        }
        return hints_map.get(self.action_type.value, [])

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


class CategoryListItem(QWidget):
    """Compact category list item"""

    def __init__(self, icon: str, name: str, color: str, parent=None):
        super().__init__(parent)
        self.setup_ui(icon, name, color)

    def setup_ui(self, icon: str, name: str, color: str):
        """Setup UI with compact spacing"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(6)

        # Icon - compact
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                background: transparent;
                border: none;
            }
        """)
        icon_label.setAlignment(Qt.AlignVCenter)
        icon_label.setFixedWidth(18)
        layout.addWidget(icon_label)

        # Name - compact
        # category selector font size
        name_label = QLabel(name)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 14px; 
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
        name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        layout.addWidget(name_label, 1)


class CategorizedActionLibrary(QWidget):
    """Optimized action library with wider panel and compact cards"""
    action_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Fix tooltips FIRST before any UI setup
        self.fix_tooltip_colors()
        
        # Configurable panel width - adjust these values to change width
        # Current: 500-550px (increase/decrease as needed)
        self.setMinimumWidth(500)
        self.setMaximumWidth(550)
        self.all_action_cards = []
        self.setup_ui()
        
        # Fix tooltips again after UI setup
        self.fix_tooltip_colors()

    def setup_ui(self):
        """Setup main UI with optimized layout"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Compact header
        header = self.create_header()
        main_layout.addWidget(header)

        # Content area with categories and actions
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Category list - compact width
        self.category_list = self.create_category_list()
        content_layout.addWidget(self.category_list)

        # Action cards area
        self.category_stack = QStackedWidget()
        self.category_stack.setStyleSheet("""
            QStackedWidget {
                background: #F8F9FA;
                border-left: 1px solid #E0E0E0;
            }
        """)
        content_layout.addWidget(self.category_stack, 1)

        main_layout.addLayout(content_layout, 1)

        # Populate categories
        self.populate_categories()

    def create_header(self):
        """Create compact header section"""
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background: #FFFFFF;
                border-bottom: 2px solid #E0E0E0;
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(6)

        # Title - compact
        title = QLabel("📚 Action Library")
        title.setStyleSheet("""
            QLabel {
                color: #1976D2;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
                border: none;
            }
        """)
        header_layout.addWidget(title)

        # Search bar - compact
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search actions...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                padding: 6px 8px;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background: #FFFFFF;
                font-size: 10px;
                color: #333;
            }
            QLineEdit:focus {
                border: 2px solid #1976D2;
                padding: 5px 7px;
            }
        """)
        self.search_bar.textChanged.connect(self.on_search_text_changed)
        header_layout.addWidget(self.search_bar)

        # Instruction label - compact
        instruction = QLabel("💡 Click an action card to add it to your sequence")
        instruction.setStyleSheet("""
            QLabel {
                color: #777;
                font-size: 8px;
                font-style: italic;
                background: transparent;
                border: none;
            }
        """)
        instruction.setWordWrap(True)
        header_layout.addWidget(instruction)

        return header

    def create_category_list(self):
        """Create compact category list"""
        category_list = QListWidget()
        category_list.setFixedWidth(140)  # Slightly wider for better readability
        category_list.setStyleSheet("""
            QListWidget {
                background: #FAFAFA;
                border: none;
                outline: none;
                padding: 3px 0px;
            }
            QListWidget::item {
                border: none;
                padding: 0px;
                margin: 1px 0px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background: #E3F2FD;
                border-left: 3px solid #1976D2;
            }
            QListWidget::item:hover {
                background: #F5F5F5;
            }
        """)
        category_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        category_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        category_list.currentRowChanged.connect(self.on_category_changed)
        return category_list

    def populate_categories(self):
        """Populate categories with actions"""
        for category_key, category_info in ACTION_CATEGORIES.items():
            # Add to category list
            item = QListWidgetItem(self.category_list)
            item.setSizeHint(QSize(135, 32))  # Compact size
            
            widget = CategoryListItem(
                category_info["icon"],
                category_info["name"],
                category_info["color"]
            )
            self.category_list.setItemWidget(item, widget)

            # Create action page
            page = self.create_action_page(category_info)
            self.category_stack.addWidget(page)

        # Select first category
        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)

    def create_action_page(self, category_info):
        """Create action page with perfectly sized 2-column grid"""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: #F8F9FA;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #F0F0F0;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #BDBDBD;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9E9E9E;
            }
        """)

        # Card container with 2-column grid
        card_container = QWidget()
        card_container.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout(card_container)
        
        # Tight spacing for compact design
        grid_layout.setSpacing(5)
        grid_layout.setContentsMargins(6, 6, 6, 6)
        
        # Equal column stretch for 2 columns
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        # Create cards in 2-column layout
        row, col = 0, 0
        max_cols = 2

        for action_type in category_info["actions"]:
            card = ActionCard(action_type, category_info["color"])
            card.clicked.connect(self.on_card_clicked)
            
            # Add with alignment to prevent stretching
            grid_layout.addWidget(card, row, col, Qt.AlignTop)

            # Store card info for search
            metadata = ACTION_METADATA.get(action_type, {})
            card_info = {
                'card': card,
                'action_type': action_type,
                'name': metadata.get('name', '').lower(),
                'description': metadata.get('description', '').lower(),
                'category': category_info['name'].lower()
            }
            self.all_action_cards.append(card_info)

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
        """Handle category selection"""
        if index >= 0:
            self.category_stack.setCurrentIndex(index)

    def on_card_clicked(self, action_type: ActionType):
        """Handle card click"""
        self.action_selected.emit(action_type)

    def on_search_text_changed(self, search_text: str):
        """Filter cards based on search"""
        search_text = search_text.lower().strip()

        if not search_text:
            for card_info in self.all_action_cards:
                card_info['card'].setVisible(True)
            return

        for card_info in self.all_action_cards:
            matches = (
                search_text in card_info['name'] or
                search_text in card_info['description'] or
                search_text in card_info['category']
            )
            card_info['card'].setVisible(matches)

    def fix_tooltip_colors(self):
        """Ensure tooltips have correct colors - comprehensive fix"""
        # Method 1: Set application palette for all color groups
        app = QApplication.instance()
        if app:
            palette = app.palette()
            
            # Set for ALL color groups (Active, Inactive, Disabled)
            for color_group in [QPalette.Active, QPalette.Inactive, QPalette.Disabled]:
                palette.setColor(color_group, QPalette.ToolTipBase, QColor(255, 255, 255))
                palette.setColor(color_group, QPalette.ToolTipText, QColor(0, 0, 0))
            
            app.setPalette(palette)
            
            # Method 2: Set QToolTip palette directly
            tooltip_palette = QPalette()
            for color_group in [QPalette.Active, QPalette.Inactive, QPalette.Disabled]:
                tooltip_palette.setColor(color_group, QPalette.ToolTipBase, QColor(255, 255, 255))
                tooltip_palette.setColor(color_group, QPalette.ToolTipText, QColor(0, 0, 0))
            QToolTip.setPalette(tooltip_palette)
            
            # Method 3: Force stylesheet on application level
            current_style = app.styleSheet()
            tooltip_style = """
                QToolTip {
                    background-color: #FFFFFF !important;
                    color: #000000 !important;
                    border: 1px solid #CCCCCC;
                    padding: 8px;
                    border-radius: 4px;
                    font-size: 11px;
                }
            """
            # Append tooltip style if not already present
            if "QToolTip" not in current_style:
                app.setStyleSheet(current_style + tooltip_style)
            else:
                # Replace existing QToolTip style
                import re
                new_style = re.sub(
                    r'QToolTip\s*{[^}]*}',
                    tooltip_style.strip(),
                    current_style
                )
                app.setStyleSheet(new_style)

    def showEvent(self, event):
        """Ensure tooltips are properly styled when shown"""
        super().showEvent(event)
        self.fix_tooltip_colors()


# Standalone test
if __name__ == "__main__":
    import sys
    
    # Mock data for testing
    class MockActionType:
        def __init__(self, value):
            self.value = value
    
    ACTION_METADATA = {
        MockActionType("move_to_position"): {
            "name": "Add Waypoint",
            "description": "Add a waypoint with custom speed control"
        },
        MockActionType("relative_move"): {
            "name": "Relative Move", 
            "description": "Move a small distance from current position"
        },
        MockActionType("return_home"): {
            "name": "Return Home",
            "description": "Return to safe starting position"
        },
        MockActionType("wait"): {
            "name": "Wait",
            "description": "Pause execution for a specified duration"
        },
        MockActionType("gripper_open"): {
            "name": "Open Gripper",
            "description": "Open the gripper to release objects"
        },
        MockActionType("gripper_close"): {
            "name": "Close Gripper",
            "description": "Close the gripper to grasp objects"
        },
        MockActionType("enable_force_mode"): {
            "name": "Enable Force Mode",
            "description": "Enable pressure sensing and force control"
        },
        MockActionType("disable_force_mode"): {
            "name": "Disable Force Mode",
            "description": "Turn off force control mode"
        },
        MockActionType("set_force_level"): {
            "name": "Set Force Level",
            "description": "Adjust force/pressure level"
        },
        MockActionType("set_digital_output"): {
            "name": "Set Digital Output",
            "description": "Set digital output pin state"
        },
        MockActionType("wait_for_digital_input"): {
            "name": "Wait for Digital Input",
            "description": "Wait for digital input condition"
        },
    }
    
    ACTION_CATEGORIES = {
        "movement": {
            "name": "Movement",
            "icon": "🔄",
            "color": "#2196F3",
            "description": "Robot movement and positioning actions",
            "actions": [
                MockActionType("move_to_position"), 
                MockActionType("relative_move"),
                MockActionType("return_home")
            ]
        },
        "force": {
            "name": "Force Control",
            "icon": "💪",
            "color": "#FF5722",
            "description": "Force and pressure control",
            "actions": [
                MockActionType("enable_force_mode"), 
                MockActionType("disable_force_mode"), 
                MockActionType("set_force_level")
            ]
        },
        "gripper": {
            "name": "Gripper",
            "icon": "🤏",
            "color": "#FFC107",
            "description": "Gripper control actions",
            "actions": [
                MockActionType("gripper_open"), 
                MockActionType("gripper_close")
            ]
        },
        "io": {
            "name": "I/O Control",
            "icon": "🔌",
            "color": "#4CAF50",
            "description": "Digital input/output control",
            "actions": [
                MockActionType("set_digital_output"), 
                MockActionType("wait_for_digital_input")
            ]
        },
        "timing": {
            "name": "Timing",
            "icon": "⏱️",
            "color": "#9C27B0",
            "description": "Flow control and timing",
            "actions": [MockActionType("wait")]
        }
    }
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # CRITICAL: Set tooltip styling BEFORE creating any widgets
    # Method 1: Application-level palette
    palette = app.palette()
    for color_group in [QPalette.Active, QPalette.Inactive, QPalette.Disabled]:
        palette.setColor(color_group, QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(color_group, QPalette.ToolTipText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    # Method 2: QToolTip palette
    tooltip_palette = QPalette()
    for color_group in [QPalette.Active, QPalette.Inactive, QPalette.Disabled]:
        tooltip_palette.setColor(color_group, QPalette.ToolTipBase, QColor(255, 255, 255))
        tooltip_palette.setColor(color_group, QPalette.ToolTipText, QColor(0, 0, 0))
    QToolTip.setPalette(tooltip_palette)
    
    # Method 3: Global stylesheet with !important flags
    app.setStyleSheet("""
        QToolTip {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 1px solid #CCCCCC;
            padding: 8px;
            border-radius: 4px;
            font-size: 11px;
        }
    """)
    
    window = QWidget()
    window.setWindowTitle("Optimized Action Library - No Cropping")
    window.setGeometry(100, 100, 1000, 700)
    
    layout = QHBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    
    widget = CategorizedActionLibrary()
    widget.action_selected.connect(lambda action: print(f"Action selected: {action.value}"))
    layout.addWidget(widget)
    
    # Add a placeholder for the rest of the UI
    placeholder = QLabel("Execution Sequence Area\n(Your main workspace)")
    placeholder.setStyleSheet("""
        QLabel {
            background: #ECEFF1;
            color: #666;
            font-size: 14px;
            border: 2px dashed #999;
        }
    """)
    placeholder.setAlignment(Qt.AlignCenter)
    layout.addWidget(placeholder, 1)
    
    window.show()
    sys.exit(app.exec_())