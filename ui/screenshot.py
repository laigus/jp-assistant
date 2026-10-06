"""Full-screen overlay for region selection (screenshot capture)."""
import logging

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QCursor, QPen, QGuiApplication
import mss
from PIL import Image


def _physical_capture_rect(global_rect: QRect) -> QRect:
    """Map Qt logical pixels to native Windows pixels, per monitor."""
    capture_rect = QRect()
    for screen in QGuiApplication.screens():
        geometry = screen.geometry()
        part = global_rect.intersected(geometry)
        if part.isEmpty():
            continue
        ratio = screen.devicePixelRatio()
        # Windows keeps native monitor origins while Qt scales their sizes.
        left = geometry.x() + round((part.x() - geometry.x()) * ratio)
        top = geometry.y() + round((part.y() - geometry.y()) * ratio)
        right = geometry.x() + round((part.x() + part.width() - geometry.x()) * ratio)
        bottom = geometry.y() + round((part.y() + part.height() - geometry.y()) * ratio)
        capture_rect = capture_rect.united(QRect(left, top, right - left, bottom - top))
    if capture_rect.isEmpty():
        raise RuntimeError("截图选区不在可用屏幕内")
    return capture_rect


class ScreenshotOverlay(QWidget):
    """Transparent full-screen overlay that lets user drag-select a region."""

    region_captured = pyqtSignal(object)  # emits PIL Image
    capture_failed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        self._origin = QPoint()
        self._current = QPoint()
        self._selecting = False
        self._pending_region: QRect | None = None
        self._capture_timer = QTimer(self)
        self._capture_timer.setSingleShot(True)
        self._capture_timer.setInterval(50)
        self._capture_timer.timeout.connect(self._capture_pending_region)

    def start_capture(self):
        self.cancel_capture()
        # Span across all screens
        virtual_geo = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(virtual_geo)
        self._origin = QPoint()
        self._current = QPoint()
        self._selecting = False
        self.show()
        self.activateWindow()

    def cancel_capture(self):
        self._capture_timer.stop()
        self._pending_region = None
        self._selecting = False
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Semi-transparent dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self._selecting:
            rect = QRect(self._origin, self._current).normalized()
            # Clear the selected region (make it transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # Draw selection border
            pen = QPen(QColor(255, 255, 255, 160), 1.5)
            painter.setPen(pen)
            painter.drawRect(rect)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.cancel_capture()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            self._current = event.pos()
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._current = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._current = event.pos()
            self._selecting = False
            rect = QRect(self._origin, self._current).normalized()
            if rect.width() > 10 and rect.height() > 10:
                # Snapshot the global selection before hiding or moving the overlay.
                self._pending_region = QRect(self.mapToGlobal(rect.topLeft()), rect.size())
            self.hide()
            if self._pending_region is not None:
                # Allow the compositor to remove the overlay before grabbing pixels.
                self._capture_timer.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_capture()

    def closeEvent(self, event):
        self.cancel_capture()
        super().closeEvent(event)

    def _capture_pending_region(self):
        self._capture_timer.stop()
        rect = self._pending_region
        self._pending_region = None
        if rect is not None:
            self._capture_region(rect)

    def _capture_region(self, global_rect: QRect):
        try:
            physical_rect = _physical_capture_rect(global_rect)
            monitor = {
                "left": physical_rect.x(),
                "top": physical_rect.y(),
                "width": physical_rect.width(),
                "height": physical_rect.height(),
            }
            with mss.mss() as sct:
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        except Exception as e:
            logging.exception("Screenshot capture failed")
            self.capture_failed.emit(str(e))
            return
        self.region_captured.emit(img)
