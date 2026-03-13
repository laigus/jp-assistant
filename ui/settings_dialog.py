"""Settings dialog — model selection and prompt management."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QApplication, QSizePolicy, QComboBox, QSlider, QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter

from ui.acrylic import enable_acrylic
from ui.glass_base import paint_glass
from ui.ui_config import UIConfig, THEMES
from core.prompt_manager import PromptManager


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
        title = QLabel("⟐ 设置")
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

        # --- appearance section ---
        appear_label = QLabel("外观")
        appear_label.setObjectName("sectionLabel")
        layout.addWidget(appear_label)

        # theme color
        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)
        theme_lbl = QLabel("主题")
        theme_lbl.setFixedWidth(50)
        theme_row.addWidget(theme_lbl)
        self.theme_combo = QComboBox()
        for key, data in THEMES.items():
            self.theme_combo.addItem(data["name"], key)
        cfg = UIConfig()
        idx = list(THEMES.keys()).index(cfg.theme) if cfg.theme in THEMES else 0
        self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        theme_row.addWidget(self.theme_combo)
        layout.addLayout(theme_row)

        # opacity slider
        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(8)
        opacity_lbl = QLabel("透明度")
        opacity_lbl.setFixedWidth(50)
        opacity_row.addWidget(opacity_lbl)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(cfg.opacity)
        self.opacity_slider.setToolTip("0 = 全透明，100 = 不透明")
        opacity_row.addWidget(self.opacity_slider)
        self.opacity_value_label = QLabel(f"{cfg.opacity}%")
        self.opacity_value_label.setFixedWidth(36)
        opacity_row.addWidget(self.opacity_value_label)
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_value_label.setText(f"{v}%")
        )
        layout.addLayout(opacity_row)

        # acrylic toggle
        self.acrylic_check = QCheckBox("磨砂玻璃效果（Acrylic）")
        self.acrylic_check.setChecked(cfg.acrylic_enabled)
        self.acrylic_check.setToolTip("关闭后为纯透明，无背景模糊")
        layout.addWidget(self.acrylic_check)

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

    def set_models(self, models: list, default: str):
        saved = UIConfig().selected_model
        preferred = saved or default
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        if default not in models:
            self.model_combo.addItem(default)
        for m in models:
            self.model_combo.addItem(m)
        idx = self.model_combo.findText(preferred)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.setCurrentIndex(0)
        self.model_combo.blockSignals(False)

    def show_dialog(self):
        self.prompt_edit.setPlainText(self.pm.system_prompt)
        cfg = UIConfig()
        self.opacity_slider.setValue(cfg.opacity)
        self.opacity_value_label.setText(f"{cfg.opacity}%")
        idx = list(THEMES.keys()).index(cfg.theme) if cfg.theme in THEMES else 0
        self.theme_combo.setCurrentIndex(idx)
        self.acrylic_check.setChecked(cfg.acrylic_enabled)
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
        cfg = UIConfig()
        cfg.opacity = self.opacity_slider.value()
        cfg.theme = self.theme_combo.currentData()
        cfg.acrylic_enabled = self.acrylic_check.isChecked()
        cfg.selected_model = self.model_combo.currentText()
        cfg.save()
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
            _cfg = UIConfig()
            self._acrylic_applied = enable_acrylic(
                hwnd, tint_color=_cfg.acrylic_tint(), dark_mode=not _cfg.is_light
            )
            if self._acrylic_applied:
                self.update()
