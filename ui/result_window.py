"""Expandable result popup - larger window for viewing analysis details."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextBrowser,
    QApplication, QSizePolicy,
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QPainter

from ui.acrylic import enable_acrylic
from ui.glass_base import paint_glass
from ui.ui_config import UIConfig
from ui.icons import icon, icon_color_hex
from ui.md_render import md_to_html


class ResultWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self._acrylic_applied = False
        self._zoom_pct = UIConfig().result_zoom

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

        _ic = icon_color_hex(UIConfig().is_light)

        title_bar = QHBoxLayout()
        title_bar.setSpacing(6)
        title = QLabel("解析详情")
        title.setObjectName("titleLabel")
        title_bar.addWidget(title)
        title_bar.addStretch()

        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setObjectName("iconBtn")
        zoom_out_btn.setToolTip("缩小文字")
        zoom_out_btn.clicked.connect(lambda: self._zoom(-10))
        title_bar.addWidget(zoom_out_btn)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("statusLabel")
        self.zoom_label.setToolTip("Ctrl + 鼠标滚轮缩放文字")
        title_bar.addWidget(self.zoom_label)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setObjectName("iconBtn")
        zoom_in_btn.setToolTip("放大文字")
        zoom_in_btn.clicked.connect(lambda: self._zoom(10))
        title_bar.addWidget(zoom_in_btn)

        self._close_btn = QPushButton()
        self._close_btn.setIcon(icon("close", 16, _ic))
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setToolTip("关闭")
        self._close_btn.clicked.connect(self.close)
        title_bar.addWidget(self._close_btn)
        layout.addLayout(title_bar)

        self.browser = QTextBrowser()
        self.browser.setObjectName("resultBrowser")
        self.browser.setOpenExternalLinks(True)
        self.browser.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.browser.installEventFilter(self)
        layout.addWidget(self.browser, stretch=1)

    def refresh_theme(self):
        """Re-apply acrylic effect, icon colors, and repaint for current theme."""
        cfg = UIConfig()
        _ic = icon_color_hex(cfg.is_light)
        self._close_btn.setIcon(icon("close", 16, _ic))
        if self.isVisible():
            hwnd = int(self.winId())
            from ui.acrylic import disable_acrylic
            if cfg.acrylic_enabled:
                self._acrylic_applied = enable_acrylic(
                    hwnd, tint_color=cfg.acrylic_tint(), dark_mode=not cfg.is_light
                )
            else:
                disable_acrylic(hwnd, dark_mode=not cfg.is_light)
                self._acrylic_applied = False
        self.update()

    def set_content(self, md_text: str):
        """Store raw markdown and render with remembered zoom level."""
        self._md_text = md_text
        self._zoom_pct = UIConfig().result_zoom
        self.zoom_label.setText(f"{self._zoom_pct}%")
        scale = self._zoom_pct / 100.0
        html = md_to_html(md_text, large=True, font_scale=scale)
        self.browser.setHtml(html)

    def set_html(self, html: str):
        self.browser.setHtml(html)

    def show_at_saved_pos(self):
        cfg = UIConfig()
        if cfg.result_pos:
            self.move(cfg.result_pos[0], cfg.result_pos[1])
        else:
            screen = QApplication.primaryScreen().geometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2,
            )
        self.show()
        self.raise_()
        self.activateWindow()

    def _zoom(self, delta: int):
        """Change zoom by re-rendering markdown with scaled font sizes."""
        new_pct = max(50, min(300, self._zoom_pct + delta))
        if new_pct == self._zoom_pct:
            return
        self._zoom_pct = new_pct
        self.zoom_label.setText(f"{self._zoom_pct}%")
        if hasattr(self, '_md_text') and self._md_text:
            scale = self._zoom_pct / 100.0
            html = md_to_html(self._md_text, large=True, font_scale=scale)
            scroll_pos = self.browser.verticalScrollBar().value()
            self.browser.setHtml(html)
            self.browser.verticalScrollBar().setValue(scroll_pos)

    def eventFilter(self, obj, event):
        if obj is self.browser and event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                self._zoom(10 if delta > 0 else -10)
                return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        cfg = UIConfig()
        cfg.result_pos = (self.x(), self.y())
        cfg.result_zoom = self._zoom_pct
        cfg.save()
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
            _cfg = UIConfig()
            self._acrylic_applied = enable_acrylic(
                hwnd, tint_color=_cfg.acrylic_tint(), dark_mode=not _cfg.is_light
            )
            if self._acrylic_applied:
                self.update()
