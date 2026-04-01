"""Vocabulary book window — browse, play, and delete saved sentences."""
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QSizePolicy, QApplication, QTextBrowser,
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QThread
from PyQt6.QtGui import QPainter
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from ui.acrylic import enable_acrylic, disable_acrylic
from ui.glass_base import paint_glass
from ui.ui_config import UIConfig
from ui.icons import icon, icon_color_hex
from ui.md_render import md_to_html
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


class _VocabCard(QWidget):
    """Single vocabulary entry card with play / delete / expand-toggle."""
    delete_clicked = pyqtSignal(int)
    play_clicked = pyqtSignal(int)

    def __init__(self, index: int, entry: VocabEntry, is_light: bool, parent=None):
        super().__init__(parent)
        self._index = index
        self._entry = entry
        self._expanded = False
        self._build_ui(is_light)

    def _build_ui(self, is_light: bool):
        _ic = icon_color_hex(is_light)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(6)

        self._sentence_label = QLabel(self._entry.sentence)
        self._sentence_label.setWordWrap(True)
        self._sentence_label.setStyleSheet(
            "font-size: 15px; font-family: 'Yu Gothic UI', 'Meiryo', sans-serif;"
        )
        self._sentence_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        top.addWidget(self._sentence_label, stretch=1)

        self._play_btn = QPushButton()
        self._play_btn.setIcon(icon("speak", 14, _ic))
        self._play_btn.setObjectName("iconBtn")
        self._play_btn.setToolTip("朗读")
        self._play_btn.setFixedSize(30, 30)
        self._play_btn.clicked.connect(lambda: self.play_clicked.emit(self._index))
        top.addWidget(self._play_btn)

        self._del_btn = QPushButton()
        self._del_btn.setIcon(icon("delete", 14, _ic))
        self._del_btn.setObjectName("closeBtn")
        self._del_btn.setToolTip("删除")
        self._del_btn.setFixedSize(30, 30)
        self._del_btn.clicked.connect(lambda: self.delete_clicked.emit(self._index))
        top.addWidget(self._del_btn)

        layout.addLayout(top)

        self._detail_browser = QTextBrowser()
        self._detail_browser.setOpenExternalLinks(False)
        self._detail_browser.setMaximumHeight(0)
        self._detail_browser.setStyleSheet("border: none; background: transparent; padding: 0;")
        self._detail_browser.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self._detail_browser)

        self.setObjectName("vocabCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_expand()
        super().mousePressEvent(event)

    def _toggle_expand(self):
        self._expanded = not self._expanded
        if self._expanded and self._entry.analysis:
            html = md_to_html(self._entry.analysis, font_scale=0.85)
            self._detail_browser.setHtml(html)
            self._detail_browser.setMaximumHeight(16777215)
            self._detail_browser.setMinimumHeight(80)
            doc_height = self._detail_browser.document().size().toSize().height() + 16
            self._detail_browser.setMinimumHeight(min(doc_height, 400))
        else:
            self._detail_browser.setMaximumHeight(0)
            self._detail_browser.setMinimumHeight(0)


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
        self.resize(520, 600)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(8)

        _ic = icon_color_hex(UIConfig().is_light)

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

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        layout.addWidget(self._scroll, stretch=1)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()
        self._scroll.setWidget(self._list_widget)

        self._empty_label = QLabel("还没有生词，截图解析后点击 ＋ 按钮添加")
        self._empty_label.setObjectName("statusLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        layout.addWidget(self._empty_label)

    def refresh(self):
        """Rebuild the card list from VocabManager data."""
        for card in self._cards:
            self._list_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        entries = self._vocab.entries()
        is_light = UIConfig().is_light
        for i, entry in enumerate(entries):
            card = _VocabCard(i, entry, is_light)
            card.delete_clicked.connect(self._on_delete)
            card.play_clicked.connect(self._on_play)
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

    def _on_delete(self, index: int):
        self._vocab.remove(index)
        self.refresh()

    def _on_play(self, index: int):
        entries = self._vocab.entries()
        if index >= len(entries):
            return
        entry = entries[index]

        if entry.tts_path and os.path.exists(entry.tts_path):
            self._play_file(entry.tts_path)
            return

        worker = _TtsWorker(self._tts, entry.sentence)
        worker.done.connect(lambda path, idx=index: self._on_tts_done(idx, path))
        worker.error.connect(lambda _: None)
        self._workers.append(worker)
        worker.finished.connect(lambda w=worker: self._cleanup_worker(w))
        worker.start()

    def _on_tts_done(self, index: int, path: str):
        entries = self._vocab.entries()
        if index < len(entries):
            entries[index].tts_path = path
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
        cfg = UIConfig()
        if cfg.result_pos:
            self.move(cfg.result_pos[0] + 30, cfg.result_pos[1] + 30)
        else:
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
