"""Prompt management dialog - edit system prompt and set temporary instructions."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QApplication, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter

from ui.acrylic import enable_acrylic
from ui.glass_base import paint_glass
from core.prompt_manager import PromptManager


class PromptDialog(QWidget):
    saved = pyqtSignal()
    _saved_pos = None

    def __init__(self, prompt_manager: PromptManager, parent=None):
        super().__init__(parent)
        self.pm = prompt_manager
        self._drag_pos = None
        self._acrylic_applied = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(600, 560)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(8)

        title_bar = QHBoxLayout()
        title_bar.setSpacing(6)
        title = QLabel("📝 Prompt 管理")
        title.setObjectName("titleLabel")
        title_bar.addWidget(title)
        title_bar.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.close)
        title_bar.addWidget(close_btn)
        layout.addLayout(title_bar)

        sp_label = QLabel("系统 Prompt（{text} 为待分析文本占位符）")
        sp_label.setObjectName("sectionLabel")
        layout.addWidget(sp_label)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("系统 Prompt...")
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.prompt_edit, stretch=3)

        tp_label = QLabel("临时 Prompt（仅下次解析生效，用完自动清空）")
        tp_label.setObjectName("sectionLabel")
        layout.addWidget(tp_label)

        self.temp_edit = QTextEdit()
        self.temp_edit.setPlaceholderText("例如：请额外说明敬语用法...")
        self.temp_edit.setAcceptRichText(False)
        self.temp_edit.setMaximumHeight(90)
        layout.addWidget(self.temp_edit, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        reset_btn = QPushButton("↺ 恢复默认")
        reset_btn.setToolTip("重置为默认 Prompt")
        reset_btn.clicked.connect(self._on_reset)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        save_btn = QPushButton("✓ 保存")
        save_btn.setObjectName("captureBtn")
        save_btn.setToolTip("保存 Prompt 设置")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def show_dialog(self):
        self.prompt_edit.setPlainText(self.pm.system_prompt)
        self.temp_edit.setPlainText(self.pm.temp_prompt)
        if PromptDialog._saved_pos is not None:
            self.move(PromptDialog._saved_pos)
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
        PromptDialog._saved_pos = self.pos()
        self._acrylic_applied = False
        super().closeEvent(event)

    def _on_save(self):
        self.pm.system_prompt = self.prompt_edit.toPlainText()
        self.pm.temp_prompt = self.temp_edit.toPlainText()
        self.pm.save()
        self.saved.emit()
        self.close()

    def _on_reset(self):
        from core.prompt_manager import DEFAULT_PROMPT
        self.prompt_edit.setPlainText(DEFAULT_PROMPT)

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
