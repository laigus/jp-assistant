"""Full-screen overlay for region selection (screenshot capture)."""
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QCursor, QPen, QGuiApplication
import mss
from PIL import Image


class ScreenshotOverlay(QWidget):
    """Transparent full-screen overlay that lets user drag-select a region."""

    region_captured = pyqtSignal(object)  # emits PIL Image

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

    def start_capture(self):
        screen_geo = QGuiApplication.primaryScreen().geometry()
        # Span across all screens
        virtual_geo = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(virtual_geo)
        self._origin = QPoint()
        self._current = QPoint()
        self._selecting = False
        self.showFullScreen()
        self.activateWindow()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Semi-transparent dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self._selecting and not self._origin.isNull() and not self._current.isNull():
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
            self._selecting = False
            self.hide()
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
            self._selecting = False
            self.hide()

            rect = QRect(self._origin, self._current).normalized()
            if rect.width() > 10 and rect.height() > 10:
                self._capture_region(rect)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._selecting = False
            self.hide()

    def _capture_region(self, rect: QRect):
        global_pos = self.mapToGlobal(rect.topLeft())
        monitor = {
            "left": global_pos.x(),
            "top": global_pos.y(),
            "width": rect.width(),
            "height": rect.height(),
        }
        with mss.mss() as sct:
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            self.region_captured.emit(img)
