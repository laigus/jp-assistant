"""Main window - frosted glass floating panel for Japanese learning assistant."""
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLabel, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QThread, pyqtSlot, QRectF, QUrl
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QPen
from PyQt6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput

from ui.styles import MAIN_STYLE
from ui.acrylic import enable_acrylic
from ui.screenshot import ScreenshotOverlay
from core.translator import GrammarAnalyzer
from core.tts import TextToSpeech

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUNDS_DIR = os.path.join(BASE_DIR, "assets", "sounds")


class OcrWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, ocr_engine, image):
        super().__init__()
        self.ocr_engine = ocr_engine
        self.image = image

    def run(self):
        try:
            text = self.ocr_engine.recognize(self.image)
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(str(e))


class AnalyzeWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)

    def __init__(self, analyzer: GrammarAnalyzer, text: str):
        super().__init__()
        self.analyzer = analyzer
        self.text = text

    def run(self):
        result = self.analyzer.analyze(
            self.text,
            callback=lambda t: self.progress.emit(t)
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


class MainWindow(QWidget):
    """Frameless, always-on-top window with Windows Acrylic blur."""

    def __init__(self, ocr_engine=None):
        super().__init__()
        self.ocr_engine = ocr_engine
        self.analyzer = GrammarAnalyzer()
        self.tts = TextToSpeech()
        self.screenshot_overlay = ScreenshotOverlay()

        self._drag_pos = None
        self._workers = []
        self._acrylic_applied = False

        self._init_audio()
        self._init_ui()
        self._connect_signals()

    # ── Audio: all via Qt native (QSoundEffect + QMediaPlayer) ──

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
        self.setMinimumSize(400, 320)
        self.resize(440, 580)
        self.setStyleSheet(MAIN_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(10)

        # --- Title bar ---
        title_bar = QHBoxLayout()
        title_bar.setSpacing(6)

        title = QLabel("✦ 日语助手")
        title.setObjectName("titleLabel")
        title_bar.addWidget(title)
        title_bar.addStretch()

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        title_bar.addWidget(self.status_label)

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

        # --- Capture button ---
        self.capture_btn = QPushButton("📷  截图识别  (Ctrl+Shift+J)")
        self.capture_btn.setObjectName("captureBtn")
        self.capture_btn.clicked.connect(self._on_capture_click)
        layout.addWidget(self.capture_btn)

        # --- OCR result (editable) ---
        ocr_label = QLabel("识别文本（可编辑）")
        ocr_label.setObjectName("sectionLabel")
        layout.addWidget(ocr_label)

        self.ocr_text = QTextEdit()
        self.ocr_text.setPlaceholderText("截图后文本显示在这里，可手动修改...")
        self.ocr_text.setMaximumHeight(80)
        self.ocr_text.setAcceptRichText(False)
        layout.addWidget(self.ocr_text)

        # --- Action buttons ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.analyze_btn = QPushButton("🔍 解析")
        self.analyze_btn.clicked.connect(self._on_analyze_click)
        btn_row.addWidget(self.analyze_btn)

        self.speak_btn = QPushButton("🔊 朗读")
        self.speak_btn.clicked.connect(self._on_speak_click)
        btn_row.addWidget(self.speak_btn)

        layout.addLayout(btn_row)

        # --- Analysis result ---
        analysis_label = QLabel("解析结果")
        analysis_label.setObjectName("sectionLabel")
        layout.addWidget(analysis_label)

        self.analysis_area = QTextEdit()
        self.analysis_area.setObjectName("analysisArea")
        self.analysis_area.setReadOnly(True)
        self.analysis_area.setPlaceholderText("点击「解析」查看翻译和语法分析...")
        self.analysis_area.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.analysis_area, stretch=1)

        # Position: top-right of screen
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, 50)

    def _connect_signals(self):
        self.screenshot_overlay.region_captured.connect(self._on_region_captured)

    # ── Custom painting: rounded rect background ──

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)

        if not self._acrylic_applied:
            grad = QLinearGradient(0, 0, 0, rect.height())
            grad.setColorAt(0.0, QColor(25, 25, 40, 220))
            grad.setColorAt(1.0, QColor(15, 15, 28, 235))
            painter.fillPath(path, grad)

        # Top highlight (glass reflection)
        highlight_rect = QRectF(rect.x() + 1, rect.y() + 1, rect.width() - 2, 1.5)
        highlight_path = QPainterPath()
        highlight_path.addRoundedRect(highlight_rect, 16, 16)
        painter.fillPath(highlight_path, QColor(136, 204, 255, 50))

        # Subtle border
        pen = QPen(QColor(136, 204, 255, 30), 1.0)
        painter.setPen(pen)
        painter.drawPath(path)

        painter.end()

    # ── Window dragging ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ── Acrylic blur ──

    def showEvent(self, event):
        super().showEvent(event)
        if not self._acrylic_applied:
            hwnd = int(self.winId())
            self._acrylic_applied = enable_acrylic(hwnd, tint_color=0xAA201520)
            if self._acrylic_applied:
                self.update()

    # ── Actions ──

    def _on_capture_click(self):
        self._play_sound("click")
        self.status_label.setText("请框选区域...")
        self.screenshot_overlay.start_capture()

    def _on_region_captured(self, image):
        self._play_sound("capture")
        self.status_label.setText("正在识别...")

        if self.ocr_engine:
            worker = OcrWorker(self.ocr_engine, image)
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
        self.analysis_area.clear()

        worker = AnalyzeWorker(self.analyzer, text)
        worker.progress.connect(self._on_analysis_progress)
        worker.finished.connect(self._on_analysis_done)
        self._workers.append(worker)
        worker.start()

    @pyqtSlot(str)
    def _on_analysis_progress(self, text):
        self.analysis_area.setPlainText(text)
        sb = self.analysis_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    @pyqtSlot(str)
    def _on_analysis_done(self, text):
        self.analysis_area.setPlainText(text)
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

        self._media_player.playbackStateChanged.connect(_on_state_changed)

    def closeEvent(self, event):
        self.tts.cleanup()
        super().closeEvent(event)
