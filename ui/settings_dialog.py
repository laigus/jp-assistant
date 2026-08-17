"""Settings dialog — provider / model selection, API key, prompt management."""
import copy
from urllib.parse import urlparse

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
        self._editing_provider_key = ""
        self._loading_provider = False
        self._provider_snapshot = None
        self._active_provider_snapshot = ""
        self._saved_this_session = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(540, 740)
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

        self.add_provider_btn = QPushButton("＋")
        self.add_provider_btn.setObjectName("iconBtn")
        self.add_provider_btn.setToolTip("新增自定义 API")
        self.add_provider_btn.clicked.connect(self._on_add_provider)
        prov_row.addWidget(self.add_provider_btn)

        self.remove_provider_btn = QPushButton("−")
        self.remove_provider_btn.setObjectName("iconBtn")
        self.remove_provider_btn.setToolTip("删除当前自定义 API")
        self.remove_provider_btn.clicked.connect(self._on_remove_provider)
        prov_row.addWidget(self.remove_provider_btn)
        layout.addLayout(prov_row)

        # --- custom provider name ---
        self.provider_name_label = QLabel("显示名称")
        self.provider_name_label.setObjectName("sectionLabel")
        layout.addWidget(self.provider_name_label)

        self.provider_name_edit = QLineEdit()
        self.provider_name_edit.setPlaceholderText("例如：公司网关")
        layout.addWidget(self.provider_name_edit)

        # --- custom API URL ---
        self.apiurl_label = QLabel("API URL")
        self.apiurl_label.setObjectName("sectionLabel")
        layout.addWidget(self.apiurl_label)

        self.apiurl_edit = QLineEdit()
        self.apiurl_edit.setPlaceholderText("例如：https://example.com/v1")
        self.apiurl_edit.setToolTip("支持 API 根地址、版本化地址或完整 /chat/completions 地址")
        layout.addWidget(self.apiurl_edit)

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
        self.model_label = QLabel("分析模型")
        self.model_label.setObjectName("sectionLabel")
        layout.addWidget(self.model_label)

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
        return self.model_combo.currentText().strip()

    def set_ollama_models(self, local: list[str], cloud: list[str]):
        """Cache Ollama model lists (fetched async from main_window)."""
        self._ollama_local = local
        self._ollama_cloud = cloud
        if self.current_provider_key == "ollama":
            self._populate_model_combo()

    def show_dialog(self):
        self._begin_provider_edit_session()
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

    def _begin_provider_edit_session(self):
        self._provider_snapshot = copy.deepcopy(self.models_cfg.providers)
        self._active_provider_snapshot = self.models_cfg.active_provider
        self._editing_provider_key = ""
        self._saved_this_session = False

    def _restore_provider_snapshot(self):
        if self._provider_snapshot is None:
            return
        self.models_cfg.providers = copy.deepcopy(self._provider_snapshot)
        self.models_cfg.active_provider = self._active_provider_snapshot
        self._provider_snapshot = None
        self._editing_provider_key = ""

    def _refresh_providers(self, selected_key: str = ""):
        self._loading_provider = True
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        for key in self.models_cfg.provider_keys():
            display = self.models_cfg.provider_display_name(key)
            self.provider_combo.addItem(display, key)
        target = selected_key or self.models_cfg.active_provider
        idx = self.provider_combo.findData(target)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        elif self.provider_combo.count():
            self.provider_combo.setCurrentIndex(0)
        self.provider_combo.blockSignals(False)
        self._loading_provider = False
        self._load_provider_fields(self.current_provider_key)

    def _on_provider_changed(self):
        if self._loading_provider:
            return
        key = self.current_provider_key
        if not key:
            return
        if self._editing_provider_key and self._editing_provider_key != key:
            self._store_provider_fields(self._editing_provider_key)
        self._load_provider_fields(key)

    def _load_provider_fields(self, key: str):
        if not key:
            return
        prov = self.models_cfg.get_provider(key)
        ptype = prov.get("type", "ollama")
        is_custom = self.models_cfg.is_custom_provider(key)

        self.provider_name_label.setVisible(is_custom)
        self.provider_name_edit.setVisible(is_custom)
        self.apiurl_label.setVisible(is_custom)
        self.apiurl_edit.setVisible(is_custom)
        self.remove_provider_btn.setEnabled(is_custom)
        self.remove_provider_btn.setToolTip(
            "删除当前自定义 API" if is_custom else "内置提供商保留"
        )
        if is_custom:
            self.provider_name_edit.setText(prov.get("name", key))
            self.apiurl_edit.setText(prov.get("base_url", ""))
        else:
            self.provider_name_edit.clear()
            self.apiurl_edit.clear()

        needs_key = ptype != "ollama"
        self.apikey_label.setVisible(needs_key)
        self.apikey_edit.setVisible(needs_key)
        self.apikey_toggle.setVisible(needs_key)
        if needs_key:
            self.apikey_edit.setText(prov.get("api_key", ""))
        else:
            self.apikey_edit.clear()

        self.model_combo.setEditable(ptype != "ollama")
        self.model_label.setText("模型 ID" if is_custom else "分析模型")
        self._populate_model_combo()
        if self.model_combo.isEditable() and self.model_combo.lineEdit():
            self.model_combo.lineEdit().setPlaceholderText("输入模型 ID")
        self._editing_provider_key = key

    def _store_provider_fields(self, key: str):
        if not key:
            return
        prov = self.models_cfg.get_provider(key)
        if not prov or prov.get("type", "ollama") == "ollama":
            return

        prov["api_key"] = self.apikey_edit.text().strip()
        model_id = self.current_model
        if self.models_cfg.is_custom_provider(key):
            prov["name"] = self.provider_name_edit.text().strip()
            prov["base_url"] = self.apiurl_edit.text().strip().rstrip("/")
            prov["models"] = [model_id] if model_id else []
            idx = self.provider_combo.findData(key)
            if idx >= 0:
                self.provider_combo.setItemText(idx, prov["name"] or key)
        elif model_id:
            models = list(prov.get("models", []))
            if model_id not in models:
                models.append(model_id)
            prov["models"] = models
        prov["default_model"] = model_id

    def _on_add_provider(self, _checked=False):
        self._store_provider_fields(self._editing_provider_key)
        key = self.models_cfg.create_custom_provider()
        self._refresh_providers(key)
        self.provider_name_edit.selectAll()
        self.provider_name_edit.setFocus()

    def _on_remove_provider(self, _checked=False, *, confirm: bool = True):
        key = self.current_provider_key
        if not self.models_cfg.is_custom_provider(key):
            return
        if confirm:
            answer = QMessageBox.question(
                self,
                "删除自定义 API",
                f"确定删除“{self.models_cfg.provider_display_name(key)}”吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._editing_provider_key = ""
        self.models_cfg.remove_provider(key)
        self._refresh_providers(self.models_cfg.active_provider)

    def _validate_custom_providers(self) -> bool:
        for key in self.models_cfg.provider_keys():
            if not self.models_cfg.is_custom_provider(key):
                continue
            prov = self.models_cfg.get_provider(key)
            name = prov.get("name", "").strip()
            base_url = prov.get("base_url", "").strip()
            model_id = prov.get("default_model", "").strip()
            error = ""
            if not name:
                error = "请填写显示名称"
            elif not base_url:
                error = "请填写 API URL"
            else:
                parsed = urlparse(base_url)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    error = "API URL 需以 http:// 或 https:// 开头"
            if not error and not model_id:
                error = "请填写模型 ID"
            if error:
                self._refresh_providers(key)
                QMessageBox.warning(self, "自定义 API 配置不完整", error)
                return False
        return True

    def _populate_model_combo(self):
        key = self.current_provider_key
        prov = self.models_cfg.get_provider(key)
        ptype = prov.get("type", "ollama")
        default = prov.get("default_model", "")

        self.model_combo.blockSignals(True)
        self.model_combo.clear()

        if ptype == "ollama":
            local = list(self._ollama_local)
            cloud = list(self._ollama_cloud)
            default = default or "deepseek-v3.1:671b-cloud"
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
            if default and self.model_combo.findText(default) < 0:
                self.model_combo.addItem(default)

        if default:
            idx = self.model_combo.findText(default)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            elif self.model_combo.isEditable():
                self.model_combo.setEditText(default)

        self.model_combo.blockSignals(False)

    def _toggle_apikey_visibility(self):
        if self.apikey_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.apikey_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.apikey_toggle.setText("🔒")
        else:
            self.apikey_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.apikey_toggle.setText("👁")

    def _on_save(self):
        self._store_provider_fields(self._editing_provider_key)
        if not self._validate_custom_providers():
            return

        self.pm.system_prompt = self.prompt_edit.toPlainText()
        self.pm.save()

        cfg = UIConfig()
        cfg.opacity = self.opacity_slider.value()
        cfg.theme = self.theme_combo.currentData()
        cfg.acrylic_enabled = self.acrylic_check.isChecked()
        cfg.chime_enabled = self.chime_check.isChecked()
        cfg.save()

        prov_key = self.current_provider_key
        if prov_key:
            self.models_cfg.active_provider = prov_key
            self.models_cfg.save()

        self._saved_this_session = True
        self._provider_snapshot = None
        self.settings_changed.emit()
        self.close()

    def _on_reset(self):
        from core.prompt_manager import DEFAULT_PROMPT
        self.prompt_edit.setPlainText(DEFAULT_PROMPT)

    def closeEvent(self, event):
        SettingsDialog._saved_pos = self.pos()
        if not self._saved_this_session:
            self._restore_provider_snapshot()
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
