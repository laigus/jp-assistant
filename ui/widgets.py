"""Shared controls whose affordances remain visible in translucent themes."""
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPainter, QPalette, QPolygonF
from PyQt6.QtWidgets import QComboBox


class ArrowComboBox(QComboBox):
    """Editable combo box with an always-visible dropdown arrow."""

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self.palette().color(QPalette.ColorRole.Text)
        color.setAlpha(170 if self.isEnabled() else 80)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        x = self.width() - 14
        y = self.height() / 2 + 1
        painter.drawPolygon(QPolygonF([
            QPointF(x - 4, y - 3), QPointF(x + 4, y - 3), QPointF(x, y + 2),
        ]))
