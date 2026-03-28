"""Settings dialog — provider / model selection, API key, prompt management."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QApplication, QSizePolicy, QComboBox, QSlider, QCheckBox,
    QLineEdit, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QStandardItem, QStandardItemModel

from ui.acrylic import enable_acrylic
from ui.glass_base import paint_glass
from ui.ui_config import UIConfig, THEMES
from core.prompt_manager import PromptManager
from core.translator import ModelsConfig


class SettingsDialog(QWidget):
    settings_changed = pyqtSignal()
    _saved_pos = None

    def __init__(self, prompt_manager: PromptManager, models_cfg: ModelsConfig, parent=None):
        super().__init__(parent)
        self.pm = prompt_manager
        self.models_cfg = models_cfg
        self._drag_pos = None
        self._acrylic_applied = False
        self._ollama_local: list[str] = []
        self._ollama_cloud: list[str] = []

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(520, 640)
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

        # --- provider section ---
        prov_label = QLabel("API 提供商")
        prov_label.setObjectName("sectionLabel")
        layout.addWidget(prov_label)

        prov_row = QHBoxLayout()
        prov_row.setSpacing(6)
        self.provider_combo = QComboBox()
        self.provider_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        prov_row.addWidget(self.provider_combo)
        layout.addLayout(prov_row)

        # --- API key ---
        self.apikey_label = QLabel("API Key")
        self.apikey_label.setObjectName("sectionLabel")
        layout.addWidget(self.apikey_label)

        apikey_row = QHBoxLayout()
        apikey_row.setSpacing(6)
        self.apikey_edit = QLineEdit()
        self.apikey_edit.setPlaceholderText("输入 API Key（Ollama 无需填写）")
        self.apikey_edit.setEchoMode(QLineEdit.EchoMode.Password)
        apikey_row.addWidget(self.apikey_edit)
        self.apikey_toggle = QPushButton("👁")
        self.apikey_toggle.setFixedWidth(32)
        self.apikey_toggle.setToolTip("显示/隐藏 API Key")
        self.apikey_toggle.clicked.connect(self._toggle_apikey_visibility)
        apikey_row.addWidget(self.apikey_toggle)
        layout.addLayout(apikey_row)

        # --- model section ---
        model_label = QLabel("分析模型")
        model_label.setObjectName("sectionLabel")
        layout.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.model_combo)

        # --- appearance section ---
        appear_label = QLabel("外观")
        appear_label.setObjectName("sectionLabel")
        layout.addWidget(appear_label)

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

        self.acrylic_check = QCheckBox("磨砂玻璃效果（Acrylic）")
        self.acrylic_check.setChecked(cfg.acrylic_enabled)
        self.acrylic_check.setToolTip("关闭后为纯透明，无背景模糊")
        layout.addWidget(self.acrylic_check)

        self.chime_check = QCheckBox("完成提示音")
        self.chime_check.setChecked(cfg.chime_enabled)
        self.chime_check.setToolTip("OCR 识别和解析完成时播放提示音")
        layout.addWidget(self.chime_check)

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
    def current_provider_key(self) -> str:
        return self.provider_combo.currentData() or ""

    @property
    def current_model(self) -> str:
        return self.model_combo.currentText()

    def set_ollama_models(self, local: list[str], cloud: list[str]):
        """Cache Ollama model lists (fetched async from main_window)."""
        self._ollama_local = local
        self._ollama_cloud = cloud
        if self.current_provider_key == "ollama":
            self._populate_model_combo()

    def show_dialog(self):
        self.prompt_edit.setPlainText(self.pm.system_prompt)
        cfg = UIConfig()
        self.opacity_slider.setValue(cfg.opacity)
        self.opacity_value_label.setText(f"{cfg.opacity}%")
        idx = list(THEMES.keys()).index(cfg.theme) if cfg.theme in THEMES else 0
        self.theme_combo.setCurrentIndex(idx)
        self.acrylic_check.setChecked(cfg.acrylic_enabled)
        self.chime_check.setChecked(cfg.chime_enabled)

        self._refresh_providers()

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

    def _refresh_providers(self):
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        for key in self.models_cfg.provider_keys():
            display = self.models_cfg.provider_display_name(key)
            self.provider_combo.addItem(display, key)
        active = self.models_cfg.active_provider
        idx = self.provider_combo.findData(active)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.blockSignals(False)
        self._on_provider_changed()

    def _on_provider_changed(self):
        key = self.current_provider_key
        if not key:
            return
        prov = self.models_cfg.get_provider(key)
        ptype = prov.get("type", "ollama")

        needs_key = ptype != "ollama"
        self.apikey_label.setVisible(needs_key)
        self.apikey_edit.setVisible(needs_key)
        self.apikey_toggle.setVisible(needs_key)
        if needs_key:
            self.apikey_edit.setText(prov.get("api_key", ""))
        else:
            self.apikey_edit.clear()

        self.model_combo.setEditable(ptype != "ollama")
        self._populate_model_combo()

    def _populate_model_combo(self):
        key = self.current_provider_key
        prov = self.models_cfg.get_provider(key)
        ptype = prov.get("type", "ollama")

        self.model_combo.blockSignals(True)
        self.model_combo.clear()

        if ptype == "ollama":
            local = list(self._ollama_local)
            cloud = list(self._ollama_cloud)
            default = prov.get("default_model", "deepseek-v3.1:671b-cloud")
            if default and default not in local and default not in cloud:
                cloud.insert(0, default)

            model = self.model_combo.model()
            if not isinstance(model, QStandardItemModel):
                model = QStandardItemModel(self.model_combo)
                self.model_combo.setModel(model)

            if local:
                header = QStandardItem("── 本地模型 ──")
                header.setEnabled(False)
                header.setSelectable(False)
                model.appendRow(header)
                for m in local:
                    model.appendRow(QStandardItem(m))

            if cloud:
                header = QStandardItem("── 云端模型 ──")
                header.setEnabled(False)
                header.setSelectable(False)
                model.appendRow(header)
                for m in cloud:
                    model.appendRow(QStandardItem(m))
        else:
            for m in prov.get("models", []):
                self.model_combo.addItem(m)

        saved = UIConfig().selected_model
        if key == self.models_cfg.active_provider and saved:
            idx = self.model_combo.findText(saved)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

        self.model_combo.blockSignals(False)

    def _toggle_apikey_visibility(self):
        if self.apikey_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.apikey_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.apikey_toggle.setText("🔒")
        else:
            self.apikey_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.apikey_toggle.setText("👁")

    def _on_save(self):
        self.pm.system_prompt = self.prompt_edit.toPlainText()
        self.pm.save()

        cfg = UIConfig()
        cfg.opacity = self.opacity_slider.value()
        cfg.theme = self.theme_combo.currentData()
        cfg.acrylic_enabled = self.acrylic_check.isChecked()
        cfg.chime_enabled = self.chime_check.isChecked()
        cfg.selected_model = self.model_combo.currentText()
        cfg.save()

        prov_key = self.current_provider_key
        if prov_key:
            prov = self.models_cfg.get_provider(prov_key)
            if prov.get("type", "ollama") != "ollama":
                prov["api_key"] = self.apikey_edit.text().strip()
            self.models_cfg.active_provider = prov_key
            self.models_cfg.save()

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
