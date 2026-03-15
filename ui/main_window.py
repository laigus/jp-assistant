"""Main window - frosted glass floating panel for Japanese learning assistant."""
import os
import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLabel, QApplication, QSizePolicy, QTextBrowser,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QUrl
from PyQt6.QtGui import QPainter
from PyQt6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput

from ui.styles import build_style
from ui.acrylic import enable_acrylic, disable_acrylic
from ui.glass_base import paint_glass
from ui.ui_config import UIConfig
from ui.icons import icon, icon_color_hex
from ui.screenshot import ScreenshotOverlay
from ui.md_render import md_to_html
from ui.result_window import ResultWindow
from ui.settings_dialog import SettingsDialog
from core.translator import GrammarAnalyzer
from core.prompt_manager import PromptManager
from core.tts import TextToSpeech


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUNDS_DIR = os.path.join(BASE_DIR, "assets", "sounds")
DATA_DIR = os.path.join(BASE_DIR, "data")


class OcrWorker(QThread):
    result_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, ocr_engine, image):
        super().__init__()
        self.ocr_engine = ocr_engine
        self.image = image

    def run(self):
        try:
            text = self.ocr_engine.recognize(self.image)
            self.result_ready.emit(text)
        except Exception as e:
            self.error.emit(str(e))


class AnalyzeWorker(QThread):
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(str)

    def __init__(self, analyzer: GrammarAnalyzer, prompt: str):
        super().__init__()
        self.analyzer = analyzer
        self.prompt = prompt
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
        try:
            result = self.analyzer.analyze(
                self.prompt,
                callback=lambda t: self.progress.emit(t),
                cancel_check=self._cancel.is_set,
            )
            self.result_ready.emit(result)
        except Exception as e:
            self.result_ready.emit(f"❌ 解析出错: {e}")


class TtsWorker(QThread):
    result_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, tts: TextToSpeech, text: str):
        super().__init__()
        self.tts = tts
        self.text = text

    def run(self):
        try:
            path = self.tts.speak(self.text)
            self.result_ready.emit(path)
        except Exception as e:
            self.error.emit(str(e))


class ModelListWorker(QThread):
    result_ready = pyqtSignal(list)

    def __init__(self, analyzer: GrammarAnalyzer):
        super().__init__()
        self.analyzer = analyzer

    def run(self):
        try:
            local = self.analyzer.list_models()
            cloud = GrammarAnalyzer.list_cloud_models()
            local_set = set(local)
            cloud_only = sorted(m for m in cloud if m not in local_set)
            merged = sorted(local) + cloud_only
            self.result_ready.emit(merged)
        except Exception:
            self.result_ready.emit([])


class MainWindow(QWidget):
    """Frameless, always-on-top window with Windows Acrylic blur."""

    DEFAULT_MODEL = "deepseek-v3.1:671b-cloud"

    def __init__(self, ocr_engine=None):
        super().__init__()
        self.ocr_engine = ocr_engine
        saved_model = UIConfig().selected_model
        self.analyzer = GrammarAnalyzer(model=saved_model or self.DEFAULT_MODEL)
        self.tts = TextToSpeech()
        self.prompt_mgr = PromptManager(DATA_DIR)
        self.screenshot_overlay = ScreenshotOverlay()

        self._drag_pos = None
        self._workers: list[QThread] = []
        self._acrylic_applied = False
        self._last_md = ""
        self._last_image = None
        self._analyze_worker: AnalyzeWorker | None = None
        self._tts_cache: tuple[str, str] | None = None  # (text, filepath)

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
        if name == "chime" and not UIConfig().chime_enabled:
            return
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
        _cfg = UIConfig()
        self.setStyleSheet(build_style(_cfg.opacity, _cfg.is_light))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(8)

        # ── title bar ──
        title_bar = QHBoxLayout()
        title_bar.setSpacing(6)

        _ic = icon_color_hex(UIConfig().is_light)
        title = QLabel("日语助手")
        title.setObjectName("titleLabel")
        title_bar.addWidget(title)
        title_bar.addStretch()

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        title_bar.addWidget(self.status_label)

        self._settings_btn = QPushButton()
        self._settings_btn.setIcon(icon("settings", 16, _ic))
        self._settings_btn.setObjectName("iconBtn")
        self._settings_btn.setToolTip("设置（模型/Prompt/外观）")
        self._settings_btn.clicked.connect(self._on_settings_click)
        title_bar.addWidget(self._settings_btn)

        self._min_btn = QPushButton()
        self._min_btn.setIcon(icon("minimize", 16, _ic))
        self._min_btn.setObjectName("minBtn")
        self._min_btn.setToolTip("最小化")
        self._min_btn.clicked.connect(self.showMinimized)
        title_bar.addWidget(self._min_btn)

        self._close_btn = QPushButton()
        self._close_btn.setIcon(icon("close", 16, _ic))
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setToolTip("关闭")
        self._close_btn.clicked.connect(self.close)
        title_bar.addWidget(self._close_btn)

        layout.addLayout(title_bar)

        # ── capture button ──
        self.capture_btn = QPushButton("  截图识别  Ctrl+Alt+S")
        self.capture_btn.setIcon(icon("capture", 18, _ic))
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

        self.analyze_btn = QPushButton(" 解析")
        self.analyze_btn.setIcon(icon("analyze", 16, _ic))
        self.analyze_btn.clicked.connect(self._on_analyze_click)
        btn_row.addWidget(self.analyze_btn)

        self.speak_btn = QPushButton(" 朗读")
        self.speak_btn.setIcon(icon("speak", 16, _ic))
        self.speak_btn.clicked.connect(self._on_speak_click)
        btn_row.addWidget(self.speak_btn)

        self.expand_btn = QPushButton()
        self.expand_btn.setIcon(icon("expand", 16, _ic))
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
        cfg = UIConfig()
        if cfg.window_pos:
            self.move(cfg.window_pos[0], cfg.window_pos[1])
        else:
            screen = QApplication.primaryScreen().geometry()
            self.move(screen.width() - self.width() - 20, 50)

    def _start_worker(self, worker: QThread):
        """Register a worker, start it, and schedule cleanup on finish.

        Connects to QThread.finished (the real thread-end signal, not custom
        result_ready) so deleteLater is only called after the thread stops.
        """
        self._workers.append(worker)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.start()

    def _cleanup_worker(self, worker: QThread):
        if worker in self._workers:
            self._workers.remove(worker)
        worker.deleteLater()

    def _connect_signals(self):
        self.screenshot_overlay.region_captured.connect(self._on_region_captured)

    # ── model management ──

    def _load_models_async(self):
        worker = ModelListWorker(self.analyzer)
        worker.result_ready.connect(self._on_models_loaded)
        self._start_worker(worker)

    @pyqtSlot(list)
    def _on_models_loaded(self, models: list):
        if self._settings_dialog:
            self._settings_dialog.set_models(models, self.DEFAULT_MODEL)
        self._models_cache = models

    def _on_settings_changed(self):
        if self._settings_dialog:
            model = self._settings_dialog.current_model
            self.analyzer.model = model
            self.status_label.setText(f"模型: {model[:25]}")
        self._reapply_appearance()

    def _reapply_appearance(self):
        """Re-apply acrylic tint, stylesheet, icons, and repaint."""
        cfg = UIConfig()
        style = build_style(cfg.opacity, cfg.is_light)
        self.setStyleSheet(style)
        hwnd = int(self.winId())
        dark = not cfg.is_light
        if cfg.acrylic_enabled:
            self._acrylic_applied = enable_acrylic(
                hwnd, tint_color=cfg.acrylic_tint(), dark_mode=dark
            )
        else:
            disable_acrylic(hwnd, dark_mode=dark)
            self._acrylic_applied = False
        _ic = icon_color_hex(cfg.is_light)
        self._settings_btn.setIcon(icon("settings", 16, _ic))
        self._min_btn.setIcon(icon("minimize", 16, _ic))
        self._close_btn.setIcon(icon("close", 16, _ic))
        self.capture_btn.setIcon(icon("capture", 18, _ic))
        self.analyze_btn.setIcon(icon("analyze", 16, _ic))
        self.speak_btn.setIcon(icon("speak", 16, _ic))
        self.expand_btn.setIcon(icon("expand", 16, _ic))
        if self._last_md:
            html = md_to_html(self._last_md)
            self.analysis_browser.setHtml(html)
        self.update()
        if self._settings_dialog:
            self._settings_dialog.setStyleSheet(style)
        if self._result_window:
            self._result_window.setStyleSheet(style)
            self._result_window.refresh_theme()
            if hasattr(self._result_window, '_md_text') and self._result_window._md_text:
                self._result_window.set_content(self._result_window._md_text)

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
            _cfg = UIConfig()
            if _cfg.acrylic_enabled:
                self._acrylic_applied = enable_acrylic(
                    hwnd, tint_color=_cfg.acrylic_tint(), dark_mode=not _cfg.is_light
                )
            else:
                disable_acrylic(hwnd, dark_mode=not _cfg.is_light)
                self._acrylic_applied = False
            self.update()

    # ── actions ──

    def _on_capture_click(self):
        self._play_sound("click")
        self.status_label.setText("请框选区域...")
        self.screenshot_overlay.start_capture()

    def _on_region_captured(self, image):
        self._play_sound("capture")
        self._last_image = image
        self.status_label.setText("正在识别...")
        if self.ocr_engine:
            worker = OcrWorker(self.ocr_engine, image)
            worker.result_ready.connect(self._on_ocr_done)
            worker.error.connect(self._on_ocr_error)
            self._start_worker(worker)
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
        if self._analyze_worker is not None:
            self._analyze_worker.cancel()
            self.status_label.setText("正在停止...")
            return

        text = self.ocr_text.toPlainText().strip()
        if not text:
            self.status_label.setText("请先输入或截图获取文本")
            return

        self._play_sound("click")
        self.status_label.setText("正在解析...")
        self._set_analyze_running(True)
        self.analysis_browser.clear()
        self._last_md = ""

        temp = self.temp_prompt_edit.toPlainText().strip()
        if temp:
            self.prompt_mgr.temp_prompt = temp
            self.temp_prompt_edit.clear()

        prompt = self.prompt_mgr.build_prompt(text)
        worker = AnalyzeWorker(self.analyzer, prompt)
        worker.progress.connect(self._on_analysis_progress)
        worker.result_ready.connect(self._on_analysis_done)
        self._analyze_worker = worker
        self._start_worker(worker)

    def _set_analyze_running(self, running: bool):
        _ic = icon_color_hex(UIConfig().is_light)
        if running:
            self.analyze_btn.setText(" 停止")
            self.analyze_btn.setIcon(icon("close", 16, _ic))
        else:
            self.analyze_btn.setText(" 解析")
            self.analyze_btn.setIcon(icon("analyze", 16, _ic))

    @pyqtSlot(str)
    def _on_analysis_progress(self, text):
        self._last_md = text
        html = md_to_html(text)
        self.analysis_browser.setHtml(html)
        sb = self.analysis_browser.verticalScrollBar()
        sb.setValue(sb.maximum())

    @pyqtSlot(str)
    def _on_analysis_done(self, text):
        self._analyze_worker = None
        self._last_md = text
        html = md_to_html(text)
        self.analysis_browser.setHtml(html)
        self._set_analyze_running(False)
        stopped = text.endswith("⏹ 已停止")
        self.status_label.setText("已停止" if stopped else "解析完成")
        if not stopped:
            self._play_sound("chime")
        if self._result_window and self._result_window.isVisible():
            self._result_window.set_content(text)

    def _on_speak_click(self):
        text = self.ocr_text.toPlainText().strip()
        if not text:
            self.status_label.setText("没有可朗读的文本")
            return

        self._play_sound("click")

        if self._tts_cache and self._tts_cache[0] == text and os.path.exists(self._tts_cache[1]):
            self._on_tts_done(self._tts_cache[1])
            return

        self.status_label.setText("合成语音中...")
        self.speak_btn.setEnabled(False)

        worker = TtsWorker(self.tts, text)
        worker.result_ready.connect(lambda path: self._on_tts_done(path, text))
        worker.error.connect(lambda e: self._on_tts_error(e))
        self._start_worker(worker)

    def _on_tts_error(self, err):
        self.speak_btn.setEnabled(True)
        self.status_label.setText(f"语音合成失败: {err[:40]}")

    def _on_tts_done(self, filepath, cache_text=None):
        if cache_text:
            self._tts_cache = (cache_text, filepath)
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
            _c = UIConfig()
            self._settings_dialog.setStyleSheet(build_style(_c.opacity, _c.is_light))
            self._settings_dialog.settings_changed.connect(self._on_settings_changed)
            if hasattr(self, '_models_cache'):
                self._settings_dialog.set_models(self._models_cache, self.DEFAULT_MODEL)
            else:
                self._settings_dialog.set_models([], self.DEFAULT_MODEL)
        self._settings_dialog.show_dialog()

    def _on_expand_click(self):
        if not self._last_md:
            self.status_label.setText("没有解析结果可展开")
            return
        self._play_sound("click")
        if self._result_window is None:
            self._result_window = ResultWindow()
            _c = UIConfig()
            self._result_window.setStyleSheet(build_style(_c.opacity, _c.is_light))
        self._result_window.set_content(self._last_md)
        self._result_window.show_at_saved_pos()

    def closeEvent(self, event):
        cfg = UIConfig()
        cfg.window_pos = (self.x(), self.y())
        cfg.save()
        self.tts.cleanup()
        if self._result_window:
            self._result_window.close()
        if self._settings_dialog:
            self._settings_dialog.close()
        super().closeEvent(event)
