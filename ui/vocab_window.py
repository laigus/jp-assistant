"""Vocabulary book window — browse, play, and delete saved sentences."""
import os
import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QSizePolicy, QApplication, QFrame,
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QThread, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from ui.acrylic import enable_acrylic, disable_acrylic
from ui.glass_base import paint_glass
from ui.ui_config import UIConfig
from ui.icons import icon, icon_color_hex
from core.vocab import VocabManager, VocabEntry
from core.tts import TextToSpeech


class _TtsWorker(QThread):
    done = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, tts: TextToSpeech, text: str):
        super().__init__()
        self.tts = tts
        self.text = text

    def run(self):
        try:
            path = self.tts.speak(self.text)
            self.done.emit(path)
        except Exception as e:
            self.error.emit(str(e))


def _format_time(ts: float) -> str:
    t = time.localtime(ts)
    now = time.localtime()
    if t.tm_year == now.tm_year and t.tm_yday == now.tm_yday:
        return time.strftime("今天 %H:%M", t)
    if t.tm_year == now.tm_year and now.tm_yday - t.tm_yday == 1:
        return time.strftime("昨天 %H:%M", t)
    if t.tm_year == now.tm_year:
        return time.strftime("%m/%d %H:%M", t)
    return time.strftime("%Y/%m/%d", t)


class _VocabCard(QWidget):
    """Single vocabulary entry card with accent bar and hover highlight."""
    delete_clicked = pyqtSignal(object)
    play_clicked = pyqtSignal(object)
    detail_clicked = pyqtSignal(object)

    def __init__(self, entry: VocabEntry, is_light: bool, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._is_light = is_light
        self._hovered = False
        self._pressed = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMinimumHeight(56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui()

    def _build_ui(self):
        _ic = icon_color_hex(self._is_light)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._accent = QFrame()
        self._accent.setFixedWidth(3)
        accent_color = "#4a9eff" if not self._is_light else "#2979ff"
        self._accent.setStyleSheet(
            f"background: {accent_color}; border-radius: 1px; margin: 6px 0;"
        )
        root.addWidget(self._accent)

        content = QVBoxLayout()
        content.setContentsMargins(12, 8, 8, 8)
        content.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(6)

        self._sentence_label = QLabel(self._entry.sentence)
        self._sentence_label.setWordWrap(True)
        self._sentence_label.setObjectName("vocabSentence")
        self._sentence_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        top.addWidget(self._sentence_label, stretch=1)

        self._play_btn = QPushButton()
        self._play_btn.setIcon(icon("speak", 14, _ic))
        self._play_btn.setObjectName("vocabIconBtn")
        self._play_btn.setToolTip("朗读")
        self._play_btn.setFixedSize(28, 28)
        self._play_btn.clicked.connect(lambda: self.play_clicked.emit(self._entry))
        top.addWidget(self._play_btn)

        self._del_btn = QPushButton()
        self._del_btn.setIcon(icon("close", 12, _ic))
        self._del_btn.setObjectName("vocabDelBtn")
        self._del_btn.setToolTip("删除")
        self._del_btn.setFixedSize(28, 28)
        self._del_btn.clicked.connect(lambda: self.delete_clicked.emit(self._entry))
        top.addWidget(self._del_btn)

        content.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self._time_label = QLabel(_format_time(self._entry.timestamp))
        self._time_label.setObjectName("vocabMeta")
        bottom.addWidget(self._time_label)

        has_analysis = bool(self._entry.analysis and not self._entry.analysis.startswith("❌"))
        detail_hint = QLabel("点击查看解析 →" if has_analysis else "暂无解析")
        detail_hint.setObjectName("vocabMeta")
        bottom.addStretch()
        bottom.addWidget(detail_hint)

        content.addLayout(bottom)
        root.addLayout(content, stretch=1)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        if self._is_light:
            # Light theme: darken on hover/press
            if self._pressed:
                bg = QColor(0, 0, 0, 30)
                border = QColor(0, 0, 0, 40)
            elif self._hovered:
                bg = QColor(0, 0, 0, 16)
                border = QColor(0, 0, 0, 28)
            else:
                bg = QColor(0, 0, 0, 6)
                border = QColor(0, 0, 0, 10)
        else:
            # Dark theme: lighten on hover/press
            if self._pressed:
                bg = QColor(255, 255, 255, 40)
                border = QColor(255, 255, 255, 50)
            elif self._hovered:
                bg = QColor(255, 255, 255, 22)
                border = QColor(255, 255, 255, 32)
            else:
                bg = QColor(255, 255, 255, 8)
                border = QColor(255, 255, 255, 12)

        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 0.8))
        painter.drawRoundedRect(rect, 8, 8)
        painter.end()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
            child = self.childAt(event.position().toPoint())
            if child not in (self._play_btn, self._del_btn):
                self.detail_clicked.emit(self._entry)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    @property
    def entry(self) -> VocabEntry:
        return self._entry


class VocabWindow(QWidget):
    """Frosted-glass vocabulary book window."""

    def __init__(self, vocab_mgr: VocabManager, tts: TextToSpeech, parent=None):
        super().__init__(parent)
        self._vocab = vocab_mgr
        self._tts = tts
        self._drag_pos = None
        self._acrylic_applied = False
        self._workers: list[QThread] = []
        self._cards: list[_VocabCard] = []
        self._detail_window = None

        self._media_player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(0.9)
        self._media_player.setAudioOutput(self._audio_output)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(540, 620)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(8)

        _ic = icon_color_hex(UIConfig().is_light)

        # ── title bar ──
        title_bar = QHBoxLayout()
        title_bar.setSpacing(6)
        title = QLabel("生词本")
        title.setObjectName("titleLabel")
        title_bar.addWidget(title)
        title_bar.addStretch()

        self._count_label = QLabel("0 条")
        self._count_label.setObjectName("statusLabel")
        title_bar.addWidget(self._count_label)

        self._close_btn = QPushButton()
        self._close_btn.setIcon(icon("close", 16, _ic))
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setToolTip("关闭")
        self._close_btn.clicked.connect(self.close)
        title_bar.addWidget(self._close_btn)
        layout.addLayout(title_bar)

        # ── scroll area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        layout.addWidget(self._scroll, stretch=1)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()
        self._scroll.setWidget(self._list_widget)

        self._empty_label = QLabel("还没有生词，截图解析后点击 ＋ 按钮添加")
        self._empty_label.setObjectName("statusLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        layout.addWidget(self._empty_label)

    # ── card list ──

    def refresh(self):
        """Rebuild the card list from VocabManager data."""
        for card in self._cards:
            self._list_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        entries = self._vocab.entries()
        is_light = UIConfig().is_light
        for i, entry in enumerate(entries):
            card = _VocabCard(entry, is_light)
            card.delete_clicked.connect(self._on_delete)
            card.play_clicked.connect(self._on_play)
            card.detail_clicked.connect(self._on_detail)
            self._list_layout.insertWidget(i, card)
            self._cards.append(card)

        self._count_label.setText(f"{len(entries)} 条")
        self._empty_label.setVisible(len(entries) == 0)
        self._scroll.setVisible(len(entries) > 0)

    def refresh_theme(self):
        cfg = UIConfig()
        _ic = icon_color_hex(cfg.is_light)
        self._close_btn.setIcon(icon("close", 16, _ic))
        if self.isVisible():
            hwnd = int(self.winId())
            if cfg.acrylic_enabled:
                self._acrylic_applied = enable_acrylic(
                    hwnd, tint_color=cfg.acrylic_tint(), dark_mode=not cfg.is_light
                )
            else:
                disable_acrylic(hwnd, dark_mode=not cfg.is_light)
                self._acrylic_applied = False
        self.refresh()
        self.update()

    # ── actions ──

    def _on_delete(self, entry: VocabEntry):
        self._vocab.remove_entry(entry)
        self.refresh()

    def _on_play(self, entry: VocabEntry):
        if entry.tts_path and os.path.exists(entry.tts_path):
            self._play_file(entry.tts_path)
            return

        worker = _TtsWorker(self._tts, entry.sentence)
        worker.done.connect(lambda path, e=entry: self._on_tts_done(e, path))
        worker.error.connect(lambda _: None)
        self._workers.append(worker)
        worker.finished.connect(lambda w=worker: self._cleanup_worker(w))
        worker.start()

    def _on_detail(self, entry: VocabEntry):
        if not entry.analysis:
            return
        from ui.result_window import ResultWindow
        from ui.styles import build_style
        if self._detail_window is None:
            self._detail_window = ResultWindow()
        _c = UIConfig()
        self._detail_window.setStyleSheet(build_style(_c.opacity, _c.is_light))
        self._detail_window.set_content(entry.analysis)
        self._detail_window.show_at_saved_pos()

    def _on_tts_done(self, entry: VocabEntry, path: str):
        entry.tts_path = path
        self._vocab.save()
        self._play_file(path)

    def _play_file(self, filepath: str):
        self._media_player.stop()
        self._media_player.setSource(QUrl.fromLocalFile(filepath))
        self._media_player.play()

    def _cleanup_worker(self, worker: QThread):
        if worker in self._workers:
            self._workers.remove(worker)
        worker.deleteLater()

    def show_window(self):
        self.refresh()
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2,
        )
        self.show()
        self.raise_()
        self.activateWindow()

    # ── window chrome ──

    def paintEvent(self, event):
        painter = QPainter(self)
        paint_glass(painter, self.rect(), self._acrylic_applied)
        painter.end()

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

    def closeEvent(self, event):
        self._acrylic_applied = False
        if self._detail_window:
            self._detail_window.close()
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
