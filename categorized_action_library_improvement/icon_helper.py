"""
Icon Helper Module

Provides utilities to convert emoji to QIcon/QPixmap for consistent rendering
across different platforms and Qt versions.
"""

from PyQt5.QtGui import QPixmap, QPainter, QFont, QColor, QIcon
from PyQt5.QtCore import Qt, QSize


class IconGenerator:
    """Generate QIcon from emoji or text"""

    @staticmethod
    def create_icon_from_emoji(emoji: str, size: int = 64, color: str = "#000000") -> QIcon:
        """
        Create a QIcon from emoji character
        
        Args:
            emoji: Emoji character
            size: Icon size in pixels
            color: Color for the emoji (hex format)
            
        Returns:
            QIcon object
        """
        pixmap = IconGenerator.create_pixmap_from_emoji(emoji, size, color)
        return QIcon(pixmap)

    @staticmethod
    def create_pixmap_from_emoji(emoji: str, size: int = 64, color: str = "#000000") -> QPixmap:
        """
        Create a QPixmap from emoji character
        
        Args:
            emoji: Emoji character
            size: Pixmap size in pixels
            color: Color for the emoji (hex format)
            
        Returns:
            QPixmap object
        """
        # Create transparent pixmap
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        # Setup painter
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # Setup font
        font = QFont()
        font.setPixelSize(int(size * 0.75))  # 75% of size for padding
        painter.setFont(font)

        # Set color
        painter.setPen(QColor(color))

        # Draw emoji centered
        painter.drawText(pixmap.rect(), Qt.AlignCenter, emoji)

        painter.end()

        return pixmap

    @staticmethod
    def create_colored_icon(emoji: str, base_color: str, sizes: list = None) -> QIcon:
        """
        Create a QIcon with multiple sizes for different DPI
        
        Args:
            emoji: Emoji character
            base_color: Base color for the icon
            sizes: List of sizes to generate (default: [32, 48, 64, 128])
            
        Returns:
            QIcon with multiple size variants
        """
        if sizes is None:
            sizes = [32, 48, 64, 128]

        icon = QIcon()
        for size in sizes:
            pixmap = IconGenerator.create_pixmap_from_emoji(emoji, size, base_color)
            icon.addPixmap(pixmap)

        return icon


# Pre-generate icons for all action types if needed
def generate_action_icons():
    """
    Generate QIcon objects for all action types
    This can be called once during initialization to pre-generate all icons
    """
    from sequential_controller import ACTION_METADATA, ACTION_CATEGORIES

    action_icons = {}
    
    for action_type, metadata in ACTION_METADATA.items():
        emoji = metadata.get("icon", "⚙️")
        
        # Find the category color for this action
        color = "#000000"  # default
        for cat_info in ACTION_CATEGORIES.values():
            if action_type in cat_info["actions"]:
                color = cat_info["color"]
                break
        
        # Generate icon
        icon = IconGenerator.create_colored_icon(emoji, color)
        action_icons[action_type] = icon

    return action_icons


def generate_category_icons():
    """Generate QIcon objects for all categories"""
    from sequential_controller import ACTION_CATEGORIES

    category_icons = {}
    
    for cat_id, cat_info in ACTION_CATEGORIES.items():
        icon = IconGenerator.create_colored_icon(
            cat_info["icon"],
            cat_info["color"]
        )
        category_icons[cat_id] = icon

    return category_icons
