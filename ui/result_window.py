"""Expandable result popup - larger window for viewing analysis details."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextBrowser,
    QApplication, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter

from ui.acrylic import enable_acrylic
from ui.glass_base import paint_glass


class ResultWindow(QWidget):
    _saved_pos = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self._acrylic_applied = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(700, 640)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(8)

        title_bar = QHBoxLayout()
        title_bar.setSpacing(6)
        title = QLabel("📖 解析详情")
        title.setObjectName("titleLabel")
        title_bar.addWidget(title)
        title_bar.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.close)
        title_bar.addWidget(close_btn)
        layout.addLayout(title_bar)

        self.browser = QTextBrowser()
        self.browser.setObjectName("resultBrowser")
        self.browser.setOpenExternalLinks(True)
        self.browser.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.browser, stretch=1)

    def set_html(self, html: str):
        self.browser.setHtml(html)

    def show_at_saved_pos(self):
        if ResultWindow._saved_pos is not None:
            self.move(ResultWindow._saved_pos)
        else:
            screen = QApplication.primaryScreen().geometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2,
            )
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        ResultWindow._saved_pos = self.pos()
        self._acrylic_applied = False
        super().closeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 44:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        paint_glass(painter, self.rect(), self._acrylic_applied)
        painter.end()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._acrylic_applied:
            hwnd = int(self.winId())
            self._acrylic_applied = enable_acrylic(hwnd, tint_color=0x18080810)
            if self._acrylic_applied:
                self.update()
