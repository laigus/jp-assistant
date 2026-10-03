"""Independent language drafts; changing the editor language never changes study language."""
import copy
import re

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDoubleSpinBox, QSpinBox, QTextEdit, QPushButton,
)

from core.languages import LANGUAGES, LanguageConfig
from core.prompt_manager import DEFAULT_PROMPTS, PromptManager
from core.tts import TextToSpeech
from ui.tts_worker import TtsWorker, VoiceListWorker
from ui.widgets import ArrowComboBox


class LanguageSettingsPage(QWidget):
    background_idle = pyqtSignal()
    def __init__(self, config: LanguageConfig, prompts: PromptManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.prompts = prompts
        self._editing_language = ""
        self._profiles = {}
        self._prompts = {}
        self._voices = []
        self._workers = []
        self._session_id = 0
        self._voice_worker = None
        self._preview_tts = None
        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._build_ui()
        self.load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        row = QHBoxLayout()
        row.addWidget(QLabel("配置语言"))
        self.language_combo = ArrowComboBox()
        for key, spec in LANGUAGES.items():
            self.language_combo.addItem(spec.name, key)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        row.addWidget(self.language_combo, 1)
        layout.addLayout(row)
        hint = QLabel("这里只编辑语言配置；学习语言在主窗口切换。")
        hint.setObjectName("statusLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._heading(layout, "截图识别 · OCR")
        self.ocr_combo = ArrowComboBox()
        self.ocr_combo.currentIndexChanged.connect(self._update_ocr_fields)
        layout.addWidget(self.ocr_combo)
        self.locale_edit = QLineEdit()
        self.locale_edit.setPlaceholderText("Windows OCR 语言，例如 en-US / en-GB")
        layout.addWidget(self.locale_edit)
        self.threshold_widget = QWidget()
        thresholds = QHBoxLayout(self.threshold_widget)
        thresholds.setContentsMargins(0, 0, 0, 0)
        thresholds.addWidget(QLabel("检测阈值"))
        self.det_spin = QDoubleSpinBox()
        self.det_spin.setRange(0, 1)
        self.det_spin.setSingleStep(0.05)
        thresholds.addWidget(self.det_spin)
        thresholds.addWidget(QLabel("识别阈值"))
        self.rec_spin = QDoubleSpinBox()
        self.rec_spin.setRange(0, 1)
        self.rec_spin.setSingleStep(0.05)
        thresholds.addWidget(self.rec_spin)
        layout.addWidget(self.threshold_widget)
        self.ocr_hint = QLabel()
        self.ocr_hint.setObjectName("statusLabel")
        self.ocr_hint.setWordWrap(True)
        layout.addWidget(self.ocr_hint)

        self._heading(layout, "朗读 · Edge TTS（保持现有引擎）")
        voice_row = QHBoxLayout()
        self.voice_combo = ArrowComboBox()
        self.voice_combo.setEditable(True)
        self.voice_combo.setToolTip("选择音色，或手动填写 Edge TTS 音色 ID")
        voice_row.addWidget(self.voice_combo, 1)
        self.fetch_voices_btn = QPushButton("获取音色")
        self.fetch_voices_btn.clicked.connect(self._fetch_voices)
        voice_row.addWidget(self.fetch_voices_btn)
        layout.addLayout(voice_row)
        rate_row = QHBoxLayout()
        rate_row.addWidget(QLabel("语速调整"))
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(-50, 50)
        self.rate_spin.setSuffix("%")
        rate_row.addWidget(self.rate_spin)
        rate_row.addStretch()
        layout.addLayout(rate_row)
        preview_row = QHBoxLayout()
        self.preview_edit = QLineEdit()
        preview_row.addWidget(self.preview_edit, 1)
        self.preview_btn = QPushButton("试听")
        self.preview_btn.clicked.connect(self._preview)
        preview_row.addWidget(self.preview_btn)
        layout.addLayout(preview_row)
        self.voice_status = QLabel()
        self.voice_status.setObjectName("statusLabel")
        self.voice_status.setWordWrap(True)
        layout.addWidget(self.voice_status)

        prompt_row = QHBoxLayout()
        label = QLabel("系统 Prompt（{text} 为待分析文本）")
        label.setObjectName("sectionLabel")
        prompt_row.addWidget(label, 1)
        self.reset_btn = QPushButton("恢复默认")
        self.reset_btn.clicked.connect(self._reset_prompt)
        prompt_row.addWidget(self.reset_btn)
        layout.addLayout(prompt_row)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.setMinimumHeight(150)
        layout.addWidget(self.prompt_edit, 1)

    @staticmethod
    def _heading(layout, text):
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        layout.addWidget(label)

    @property
    def current_language(self):
        return self.language_combo.currentData()

    def load(self):
        self._session_id += 1
        self._profiles = copy.deepcopy(self.config.profiles)
        self._prompts = dict(self.prompts.prompts)
        self._editing_language = ""
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.config.active_language))
        self.language_combo.blockSignals(False)
        self._load_language()

    def _store_current(self):
        if not self._editing_language:
            return
        profile = self._profiles[self._editing_language]
        profile.update(ocr_backend=self.ocr_combo.currentData(),
                       ocr_locale=self.locale_edit.text().strip(),
                       det_threshold=self.det_spin.value(), rec_threshold=self.rec_spin.value(),
                       voice=self.voice_combo.currentText().strip(), rate=self.rate_spin.value())
        self._prompts[self._editing_language] = self.prompt_edit.toPlainText()

    def _on_language_changed(self):
        self._store_current()
        self.end_preview()
        self._load_language()

    def _load_language(self):
        language = self.current_language
        self._editing_language = language
        profile = self._profiles[language]
        self.ocr_combo.blockSignals(True)
        self.ocr_combo.clear()
        if language == "ja":
            self.ocr_combo.addItem("meikiocr（日语游戏文字）", "meikiocr")
        self.ocr_combo.addItem("Windows OCR（本地）", "windows")
        self.ocr_combo.setCurrentIndex(self.ocr_combo.findData(profile["ocr_backend"]))
        self.ocr_combo.blockSignals(False)
        self.locale_edit.setText(profile["ocr_locale"])
        self.det_spin.setValue(profile["det_threshold"])
        self.rec_spin.setValue(profile["rec_threshold"])
        self._update_ocr_fields()
        self._populate_voices(profile["voice"])
        self.rate_spin.setValue(profile["rate"])
        self.preview_edit.setText("こんにちは。日本語を勉強しています。" if language == "ja"
                                  else "Hello! Let's practice English together.")
        self.prompt_edit.setPlainText(self._prompts[language])
        self.voice_status.clear()

    def _update_ocr_fields(self):
        is_meiki = self.ocr_combo.currentData() == "meikiocr"
        self.threshold_widget.setVisible(is_meiki)
        self.locale_edit.setVisible(not is_meiki)
        self.ocr_hint.setText("阈值越高，识别筛选越严格。" if is_meiki else
                              "需要在 Windows 语言选项中安装对应语言的 OCR 组件；本地识别无需 API。")

    def _populate_voices(self, selected):
        language = self.current_language
        names = list(LANGUAGES[language].voices)
        names.extend(v["ShortName"] for v in self._voices
                     if v.get("Locale", "").split("-")[0] == language)
        self.voice_combo.clear()
        self.voice_combo.addItems(list(dict.fromkeys(names)))
        self.voice_combo.setCurrentText(selected)

    def _fetch_voices(self):
        if self._voice_worker is not None:
            return
        self.fetch_voices_btn.setEnabled(False)
        self.voice_status.setText("正在获取 Edge TTS 音色...")
        worker = VoiceListWorker(self)
        self._voice_worker = worker
        worker.result_ready.connect(self._on_voices)
        worker.error.connect(lambda error: self.voice_status.setText(f"获取失败：{error}"))
        worker.finished.connect(lambda: self._finish_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_voices(self, voices):
        self._voices = voices
        self._populate_voices(self.voice_combo.currentText())
        self.voice_status.setText("音色列表已更新；仍可手动填写音色 ID。")

    def _preview(self):
        text = self.preview_edit.text().strip()
        voice = self.voice_combo.currentText().strip()
        if not text or not voice:
            self.voice_status.setText("请填写试听文本和音色 ID。")
            return
        if self._preview_tts is None:
            self._preview_tts = TextToSpeech()
        token = self._session_id
        self.preview_btn.setEnabled(False)
        self.voice_status.setText("正在合成试听语音...")
        worker = TtsWorker(self._preview_tts, text, voice, self.rate_spin.value(), self)
        worker.result_ready.connect(lambda path: self._on_preview_ready(token, path))
        worker.error.connect(lambda error: self._on_preview_error(token, error))
        worker.finished.connect(lambda: self._finish_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_preview_ready(self, token, path):
        if token != self._session_id:
            return
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()
        self.voice_status.setText("正在试听")

    def _on_preview_error(self, token, error):
        if token == self._session_id:
            self.voice_status.setText(f"试听失败：{error}")

    def _finish_worker(self, worker):
        self._workers.remove(worker)
        if worker is self._voice_worker:
            self._voice_worker = None
            self.fetch_voices_btn.setEnabled(True)
        else:
            self.preview_btn.setEnabled(True)
        worker.deleteLater()
        if not self._workers and self._preview_tts and not self.isVisible():
            self._player.setSource(QUrl())
            self._preview_tts.cleanup()
            self._preview_tts = None
        if not self._workers:
            self.background_idle.emit()

    def end_preview(self):
        self._session_id += 1
        self._player.stop()
        self._player.setSource(QUrl())
        if not self._workers and self._preview_tts:
            self._preview_tts.cleanup()
            self._preview_tts = None

    def _reset_prompt(self):
        self.prompt_edit.setPlainText(DEFAULT_PROMPTS[self.current_language])

    def validate(self) -> str:
        self._store_current()
        for key, profile in self._profiles.items():
            error = ""
            if not profile["voice"]:
                error = "请填写音色 ID"
            elif profile["ocr_backend"] == "windows" and not re.fullmatch(
                    r"[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})+", profile["ocr_locale"]):
                error = "请填写 OCR 语言代码，例如 en-US"
            elif "{text}" not in self._prompts[key]:
                error = "系统 Prompt 需要包含 {text} 占位符"
            if error:
                self.language_combo.setCurrentIndex(self.language_combo.findData(key))
                return f"{LANGUAGES[key].name}：{error}"
        return ""

    def apply(self):
        for key, profile in self._profiles.items():
            self.config.set_profile(key, profile)
        self.prompts.prompts = dict(self._prompts)
        self.config.save()
        self.prompts.save()
