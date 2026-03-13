"""Shared glass painting utilities for all frosted-glass windows.

Uses Win11 native rounded corners and DWM shadow.
paintEvent only draws the semi-transparent gradient fill, highlight and border.
"""
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QPen

RADIUS = 8.0


def paint_glass(painter: QPainter, widget_rect, acrylic_applied: bool):
    """Paint glass background fill (native corners clip the shape)."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    rect = QRectF(widget_rect).adjusted(0.5, 0.5, -0.5, -0.5)

    grad = QLinearGradient(rect.x(), rect.y(), rect.x(), rect.y() + rect.height())
    if acrylic_applied:
        grad.setColorAt(0.0, QColor(8, 8, 12, 25))
        grad.setColorAt(1.0, QColor(4, 4, 8, 40))
    else:
        grad.setColorAt(0.0, QColor(16, 16, 22, 200))
        grad.setColorAt(1.0, QColor(8, 8, 12, 220))
    painter.fillRect(rect, grad)

    # top highlight
    hl = QRectF(rect.x(), rect.y(), rect.width(), 1)
    painter.fillRect(hl, QColor(255, 255, 255, 14))

    # border
    painter.setPen(QPen(QColor(255, 255, 255, 8), 0.5))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(rect)
