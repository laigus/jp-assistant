"""Shared glass painting utilities for all frosted-glass windows.

Uses Win11 native rounded corners and DWM shadow.
paintEvent only draws the semi-transparent gradient fill, highlight and border.
"""
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QLinearGradient, QPen

from ui.ui_config import UIConfig

RADIUS = 8.0


def paint_glass(painter: QPainter, widget_rect, acrylic_applied: bool):
    """Paint glass background fill (native corners clip the shape)."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    cfg = UIConfig()
    r, g, b = cfg.base_rgb()
    light = cfg.is_light

    rect = QRectF(widget_rect).adjusted(0.5, 0.5, -0.5, -0.5)

    grad = QLinearGradient(rect.x(), rect.y(), rect.x(), rect.y() + rect.height())
    if acrylic_applied:
        grad.setColorAt(0.0, QColor(r, g, b, cfg.fill_alpha_top()))
        grad.setColorAt(1.0, QColor(r, g, b, cfg.fill_alpha_bottom()))
    else:
        grad.setColorAt(0.0, QColor(r, g, b, 200))
        grad.setColorAt(1.0, QColor(r, g, b, 220))
    painter.fillRect(rect, grad)

    if light:
        hl_color = QColor(255, 255, 255, 30)
        border_color = QColor(0, 0, 0, 10)
    else:
        hl_color = QColor(255, 255, 255, 14)
        border_color = QColor(255, 255, 255, 8)

    hl = QRectF(rect.x(), rect.y(), rect.width(), 1)
    painter.fillRect(hl, hl_color)

    painter.setPen(QPen(border_color, 0.5))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(rect)
