"""Main window - frosted glass floating panel for Japanese learning assistant."""
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLabel, QApplication, QSizePolicy, QTextBrowser,
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QThread, pyqtSlot, QRectF, QUrl
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QPen
from PyQt6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput

from ui.styles import MAIN_STYLE
from ui.acrylic import enable_acrylic
from ui.glass_base import paint_glass
from ui.screenshot import ScreenshotOverlay
from ui.md_render import md_to_html
from ui.result_window import ResultWindow
from ui.settings_dialog import SettingsDialog
from core.translator import GrammarAnalyzer
from core.prompt_manager import PromptManager
from core.tts import TextToSpeech
from core.ocr import OCR_MODE_BASIC, OCR_MODE_LINES, OCR_MODE_CORRECT

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUNDS_DIR = os.path.join(BASE_DIR, "assets", "sounds")
DATA_DIR = os.path.join(BASE_DIR, "data")


class OcrWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, ocr_engine, image, mode: str = OCR_MODE_BASIC,
                 model: str = "", base_url: str = ""):
        super().__init__()
        self.ocr_engine = ocr_engine
        self.image = image
        self.mode = mode
        self.model = model
        self.base_url = base_url

    def run(self):
        try:
            if self.mode == OCR_MODE_LINES:
                text = self.ocr_engine.recognize_lines(self.image)
            elif self.mode == OCR_MODE_CORRECT:
                text = self.ocr_engine.recognize_with_correction(
                    self.image, model=self.model, base_url=self.base_url
                )
            else:
                text = self.ocr_engine.recognize(self.image)
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(str(e))


class AnalyzeWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)

    def __init__(self, analyzer: GrammarAnalyzer, prompt: str):
        super().__init__()
        self.analyzer = analyzer
        self.prompt = prompt

    def run(self):
        result = self.analyzer.analyze(
            self.prompt,
            callback=lambda t: self.progress.emit(t),
        )
        self.finished.emit(result)


class TtsWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, tts: TextToSpeech, text: str):
        super().__init__()
        self.tts = tts
        self.text = text

    def run(self):
        path = self.tts.speak(self.text)
        self.finished.emit(path)


class ModelListWorker(QThread):
    finished = pyqtSignal(list)

    def __init__(self, analyzer: GrammarAnalyzer):
        super().__init__()
        self.analyzer = analyzer

    def run(self):
        models = self.analyzer.list_models()
        self.finished.emit(models)


class MainWindow(QWidget):
    """Frameless, always-on-top window with Windows Acrylic blur."""

    DEFAULT_MODEL = "deepseek-v3.1:671b-cloud"

    def __init__(self, ocr_engine=None):
        super().__init__()
        self.ocr_engine = ocr_engine
        self.analyzer = GrammarAnalyzer()
        self.tts = TextToSpeech()
        self.prompt_mgr = PromptManager(DATA_DIR)
        self.screenshot_overlay = ScreenshotOverlay()

        self._drag_pos = None
        self._workers = []
        self._acrylic_applied = False
        self._last_md = ""
        self._ocr_mode = OCR_MODE_LINES
        self._last_image = None

        self._init_audio()
        self._init_ui()
        self._connect_signals()
        self._load_models_async()

    # ── Audio ──

    def _init_audio(self):
        self._sfx = {}
        for name in ["click", "chime", "capture"]:
            path = os.path.join(SOUNDS_DIR, f"{name}.wav")
            if os.path.exists(path):
                sfx = QSoundEffect(self)
                sfx.setSource(QUrl.fromLocalFile(path))
                sfx.setVolume(0.5)
                self._sfx[name] = sfx

        self._media_player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(0.9)
        self._media_player.setAudioOutput(self._audio_output)

    def _play_sound(self, name: str):
        if name in self._sfx:
            self._sfx[name].play()

    def _play_tts_file(self, filepath: str):
        self._media_player.stop()
        self._media_player.setSource(QUrl.fromLocalFile(filepath))
        self._media_player.play()

    # ── UI ──

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(420, 380)
        self.resize(460, 660)
        self.setStyleSheet(MAIN_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(8)

        # ── title bar ──
        title_bar = QHBoxLayout()
        title_bar.setSpacing(6)

        title = QLabel("✦ 日语助手")
        title.setObjectName("titleLabel")
        title_bar.addWidget(title)
        title_bar.addStretch()

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        title_bar.addWidget(self.status_label)

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("iconBtn")
        settings_btn.setToolTip("设置（模型/识别/Prompt）")
        settings_btn.clicked.connect(self._on_settings_click)
        title_bar.addWidget(settings_btn)

        min_btn = QPushButton("─")
        min_btn.setObjectName("minBtn")
        min_btn.setToolTip("最小化")
        min_btn.clicked.connect(self.showMinimized)
        title_bar.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.close)
        title_bar.addWidget(close_btn)

        layout.addLayout(title_bar)

        # ── capture button ──
        self.capture_btn = QPushButton("📷  截图识别  (Ctrl+Alt+S)")
        self.capture_btn.setObjectName("captureBtn")
        self.capture_btn.clicked.connect(self._on_capture_click)
        layout.addWidget(self.capture_btn)

        # ── OCR result (editable) ──
        ocr_label = QLabel("识别文本（可编辑）")
        ocr_label.setObjectName("sectionLabel")
        layout.addWidget(ocr_label)

        self.ocr_text = QTextEdit()
        self.ocr_text.setPlaceholderText("截图后文本显示在这里，可手动修改...")
        self.ocr_text.setMaximumHeight(80)
        self.ocr_text.setAcceptRichText(False)
        layout.addWidget(self.ocr_text)

        # ── temp prompt ──
        tp_label = QLabel("临时指令（仅下次解析生效）")
        tp_label.setObjectName("sectionLabel")
        layout.addWidget(tp_label)

        self.temp_prompt_edit = QTextEdit()
        self.temp_prompt_edit.setPlaceholderText("例如：请额外说明敬语用法...")
        self.temp_prompt_edit.setAcceptRichText(False)
        self.temp_prompt_edit.setMaximumHeight(50)
        layout.addWidget(self.temp_prompt_edit)

        # ── action buttons ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.analyze_btn = QPushButton("🔍 解析")
        self.analyze_btn.clicked.connect(self._on_analyze_click)
        btn_row.addWidget(self.analyze_btn)

        self.speak_btn = QPushButton("🔊 朗读")
        self.speak_btn.clicked.connect(self._on_speak_click)
        btn_row.addWidget(self.speak_btn)

        self.expand_btn = QPushButton("⤢")
        self.expand_btn.setObjectName("iconBtn")
        self.expand_btn.setToolTip("展开查看详细结果")
        self.expand_btn.clicked.connect(self._on_expand_click)
        btn_row.addWidget(self.expand_btn)

        layout.addLayout(btn_row)

        # ── analysis result (markdown) ──
        analysis_label = QLabel("解析结果")
        analysis_label.setObjectName("sectionLabel")
        layout.addWidget(analysis_label)

        self.analysis_browser = QTextBrowser()
        self.analysis_browser.setOpenExternalLinks(False)
        self.analysis_browser.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.analysis_browser, stretch=1)

        # ── sub-windows (lazy-created, reused) ──
        self._result_window = None
        self._settings_dialog = None

        # ── position ──
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, 50)

    def _connect_signals(self):
        self.screenshot_overlay.region_captured.connect(self._on_region_captured)

    # ── model management ──

    def _load_models_async(self):
        worker = ModelListWorker(self.analyzer)
        worker.finished.connect(self._on_models_loaded)
        self._workers.append(worker)
        worker.start()

    @pyqtSlot(list)
    def _on_models_loaded(self, models: list):
        if self._settings_dialog:
            self._settings_dialog.set_models(models, self.DEFAULT_MODEL)
        self._models_cache = models

    def _on_settings_changed(self):
        if self._settings_dialog:
            model = self._settings_dialog.current_model
            self.analyzer.model = model
            self._ocr_mode = self._settings_dialog.current_ocr_mode
            self.status_label.setText(f"模型: {model[:25]}")

    # ── painting ──

    def paintEvent(self, event):
        painter = QPainter(self)
        paint_glass(painter, self.rect(), self._acrylic_applied)
        painter.end()

    # ── drag ──

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

    # ── acrylic ──

    def showEvent(self, event):
        super().showEvent(event)
        if not self._acrylic_applied:
            hwnd = int(self.winId())
            self._acrylic_applied = enable_acrylic(hwnd, tint_color=0x18080810)
            if self._acrylic_applied:
                self.update()

    # ── actions ──

    def _on_capture_click(self):
        self._play_sound("click")
        self.status_label.setText("请框选区域...")
        self.screenshot_overlay.start_capture()

    def _on_region_captured(self, image):
        self._play_sound("capture")
        self._last_image = image
        mode_label = {"basic": "OCR", "lines": "分行OCR", "correct": "OCR+纠错"}
        self.status_label.setText(f"正在识别（{mode_label.get(self._ocr_mode, 'OCR')}）...")
        if self.ocr_engine:
            worker = OcrWorker(
                self.ocr_engine, image,
                mode=self._ocr_mode,
                model=self.analyzer.model,
                base_url=self.analyzer.base_url,
            )
            worker.finished.connect(self._on_ocr_done)
            worker.error.connect(self._on_ocr_error)
            self._workers.append(worker)
            worker.start()
        else:
            self.status_label.setText("OCR 引擎未就绪")

    @pyqtSlot(str)
    def _on_ocr_done(self, text):
        self.ocr_text.setPlainText(text)
        self.status_label.setText("识别完成")
        self._play_sound("chime")

    @pyqtSlot(str)
    def _on_ocr_error(self, err):
        self.status_label.setText(f"识别失败: {err[:50]}")

    def _on_analyze_click(self):
        text = self.ocr_text.toPlainText().strip()
        if not text:
            self.status_label.setText("请先输入或截图获取文本")
            return

        self._play_sound("click")
        self.status_label.setText("正在解析...")
        self.analyze_btn.setEnabled(False)
        self.analysis_browser.clear()
        self._last_md = ""

        temp = self.temp_prompt_edit.toPlainText().strip()
        if temp:
            self.prompt_mgr.temp_prompt = temp
            self.temp_prompt_edit.clear()

        prompt = self.prompt_mgr.build_prompt(text)
        worker = AnalyzeWorker(self.analyzer, prompt)
        worker.progress.connect(self._on_analysis_progress)
        worker.finished.connect(self._on_analysis_done)
        self._workers.append(worker)
        worker.start()

    @pyqtSlot(str)
    def _on_analysis_progress(self, text):
        self._last_md = text
        html = md_to_html(text)
        self.analysis_browser.setHtml(html)
        sb = self.analysis_browser.verticalScrollBar()
        sb.setValue(sb.maximum())

    @pyqtSlot(str)
    def _on_analysis_done(self, text):
        self._last_md = text
        html = md_to_html(text)
        self.analysis_browser.setHtml(html)
        self.analyze_btn.setEnabled(True)
        self.status_label.setText("解析完成")
        self._play_sound("chime")

    def _on_speak_click(self):
        text = self.ocr_text.toPlainText().strip()
        if not text:
            self.status_label.setText("没有可朗读的文本")
            return

        self._play_sound("click")
        self.status_label.setText("合成语音中...")
        self.speak_btn.setEnabled(False)

        worker = TtsWorker(self.tts, text)
        worker.finished.connect(self._on_tts_done)
        self._workers.append(worker)
        worker.start()

    @pyqtSlot(str)
    def _on_tts_done(self, filepath):
        self.speak_btn.setEnabled(True)
        self.status_label.setText("朗读中...")
        self._play_tts_file(filepath)

        def _on_state_changed(state):
            if state == QMediaPlayer.PlaybackState.StoppedState:
                self.status_label.setText("就绪")

        try:
            self._media_player.playbackStateChanged.disconnect()
        except TypeError:
            pass
        self._media_player.playbackStateChanged.connect(_on_state_changed)

    def _on_settings_click(self):
        self._play_sound("click")
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self.prompt_mgr)
            self._settings_dialog.setStyleSheet(MAIN_STYLE)
            self._settings_dialog.settings_changed.connect(self._on_settings_changed)
            if hasattr(self, '_models_cache'):
                self._settings_dialog.set_models(self._models_cache, self.DEFAULT_MODEL)
            else:
                self._settings_dialog.set_models([], self.DEFAULT_MODEL)
            self._settings_dialog.set_ocr_mode(self._ocr_mode)
        self._settings_dialog.show_dialog()

    def _on_expand_click(self):
        if not self._last_md:
            self.status_label.setText("没有解析结果可展开")
            return
        self._play_sound("click")
        if self._result_window is None:
            self._result_window = ResultWindow()
            self._result_window.setStyleSheet(MAIN_STYLE)
        html = md_to_html(self._last_md, large=True)
        self._result_window.set_html(html)
        self._result_window.show_at_saved_pos()

    def closeEvent(self, event):
        self.tts.cleanup()
        if self._result_window:
            self._result_window.close()
        if self._settings_dialog:
            self._settings_dialog.close()
        super().closeEvent(event)
