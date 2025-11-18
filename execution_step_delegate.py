"""
Custom item delegate used to paint execution step rows with vivid state colors.
"""

from enum import Enum
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem
from PyQt5.QtGui import QColor, QPalette, QBrush


class StepState(str, Enum):
    """Possible visual states for a sequence step."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


# Custom data role used to store the state on each QListWidgetItem
STEP_STATE_ROLE = Qt.UserRole + 100


class ExecutionStepDelegate(QStyledItemDelegate):
    """Delegate that paints QListWidget rows using StepState metadata."""

    BACKGROUND_COLORS = {
        StepState.RUNNING.value: QColor(66, 165, 245),   # Bright blue (#42A5F5)
        StepState.SUCCESS.value: QColor(102, 187, 106),  # Bright green (#66BB6A)
        StepState.FAILED.value: QColor(239, 83, 80),     # Bright red (#EF5350)
    }

    def paint(self, painter, option, index):
        # Work on a copy so we don't mutate Qt's shared option.
        opt = QStyleOptionViewItem(option)
        state = index.data(STEP_STATE_ROLE)

        if state:
            color = self.BACKGROUND_COLORS.get(state)
            if color:
                opt.backgroundBrush = QBrush(color)
                # White text for colored backgrounds to keep contrast high.
                opt.palette.setColor(QPalette.Text, QColor(255, 255, 255))
                opt.palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
            else:
                # Pending/cleared state uses default palette.
                opt.backgroundBrush = QBrush(Qt.NoBrush)
                opt.palette.setColor(QPalette.Text, option.palette.color(QPalette.Text))
                opt.palette.setColor(QPalette.HighlightedText, option.palette.color(QPalette.HighlightedText))

        super().paint(painter, opt, index)
