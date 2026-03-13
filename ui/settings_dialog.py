"""Settings dialog — model, OCR mode, prompt management in one panel."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QApplication, QSizePolicy, QComboBox, QTabWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter

from ui.acrylic import enable_acrylic
from ui.glass_base import paint_glass
from core.prompt_manager import PromptManager

OCR_MODES = {
    "basic": "仅 OCR（快速）",
    "lines": "分行 + OCR（推荐）",
    "correct": "OCR + 云端纠错（最准）",
}


class SettingsDialog(QWidget):
    settings_changed = pyqtSignal()
    _saved_pos = None

    def __init__(self, prompt_manager: PromptManager, parent=None):
        super().__init__(parent)
        self.pm = prompt_manager
        self._drag_pos = None
        self._acrylic_applied = False
        self._models_list = []

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(520, 560)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(8)

        # title bar
        title_bar = QHBoxLayout()
        title_bar.setSpacing(6)
        title = QLabel("⚙ 设置")
        title.setObjectName("titleLabel")
        title_bar.addWidget(title)
        title_bar.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.close)
        title_bar.addWidget(close_btn)
        layout.addLayout(title_bar)

        # --- model section ---
        model_label = QLabel("分析模型")
        model_label.setObjectName("sectionLabel")
        layout.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self.model_combo)

        # --- OCR mode section ---
        ocr_label = QLabel("识别模式")
        ocr_label.setObjectName("sectionLabel")
        layout.addWidget(ocr_label)

        self.ocr_combo = QComboBox()
        for key, desc in OCR_MODES.items():
            self.ocr_combo.addItem(desc, key)
        self.ocr_combo.setCurrentIndex(1)
        layout.addWidget(self.ocr_combo)

        ocr_hint = QLabel(
            "分行+OCR：自动按行切分截图再逐行识别，长文本推荐\n"
            "OCR+云端纠错：先OCR再发截图给AI模型纠正错误"
        )
        ocr_hint.setObjectName("statusLabel")
        ocr_hint.setWordWrap(True)
        layout.addWidget(ocr_hint)

        # --- prompt section ---
        sp_label = QLabel("系统 Prompt（{text} 为待分析文本占位符）")
        sp_label.setObjectName("sectionLabel")
        layout.addWidget(sp_label)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("系统 Prompt...")
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.prompt_edit, stretch=1)

        # --- buttons ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        reset_btn = QPushButton("↺ 恢复默认 Prompt")
        reset_btn.setToolTip("重置为默认 Prompt")
        reset_btn.clicked.connect(self._on_reset)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()

        save_btn = QPushButton("✓ 保存")
        save_btn.setObjectName("captureBtn")
        save_btn.setToolTip("保存所有设置")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    # --- public API ---

    @property
    def current_model(self) -> str:
        return self.model_combo.currentText()

    @property
    def current_ocr_mode(self) -> str:
        return self.ocr_combo.currentData()

    def set_models(self, models: list, default: str):
        current = self.model_combo.currentText()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        if default not in models:
            self.model_combo.addItem(default)
        for m in models:
            self.model_combo.addItem(m)
        idx = self.model_combo.findText(current or default)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.setCurrentIndex(0)
        self.model_combo.blockSignals(False)

    def set_ocr_mode(self, mode: str):
        for i in range(self.ocr_combo.count()):
            if self.ocr_combo.itemData(i) == mode:
                self.ocr_combo.setCurrentIndex(i)
                break

    def show_dialog(self):
        self.prompt_edit.setPlainText(self.pm.system_prompt)
        if SettingsDialog._saved_pos is not None:
            self.move(SettingsDialog._saved_pos)
        else:
            screen = QApplication.primaryScreen().geometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2,
            )
        self.show()
        self.raise_()
        self.activateWindow()

    # --- internal ---

    def _on_save(self):
        self.pm.system_prompt = self.prompt_edit.toPlainText()
        self.pm.save()
        self.settings_changed.emit()
        self.close()

    def _on_reset(self):
        from core.prompt_manager import DEFAULT_PROMPT
        self.prompt_edit.setPlainText(DEFAULT_PROMPT)

    def closeEvent(self, event):
        SettingsDialog._saved_pos = self.pos()
        self._acrylic_applied = False
        super().closeEvent(event)

    # --- drag ---

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

    # --- painting ---

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
