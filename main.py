"""Haohao Language Assistant - Multilingual Game Learning Assistant
Floating frosted-glass panel: Screenshot → OCR → Translate + Grammar → TTS
"""
# onnxruntime must be imported before PyQt6 to avoid DLL conflicts on Windows
import onnxruntime  # noqa: F401

import sys
import logging
import traceback
import keyboard
import ctypes

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon

from app_info import APP_NAME, APP_ID, APP_VERSION, ICON_PATH
from app_paths import LOG_DIR, SOUNDS_DIR, ensure_data_dir
from ui.main_window import MainWindow
from core.ocr import OCRService

def _setup_logging():
    ensure_data_dir()
    logging.basicConfig(
        filename=LOG_DIR / "crash.log",
        encoding="utf-8",
        level=logging.ERROR,
        format="%(asctime)s %(levelname)s %(message)s",
    )

def _global_exception_hook(exc_type, exc_value, exc_tb):
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.error("Unhandled exception:\n%s", msg)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


class HotkeyBridge(QObject):
    """Deliver global keyboard callbacks onto the Qt GUI thread."""
    capture = pyqtSignal()


def _self_check(app):
    """Check bundled resources and dynamic backends without touching user data."""
    import meikiocr  # noqa: F401
    import edge_tts  # noqa: F401
    from winrt.windows.globalization import Language  # noqa: F401
    from winrt.windows.graphics.imaging import SoftwareBitmap  # noqa: F401
    from winrt.windows.media.ocr import OcrEngine  # noqa: F401
    from winrt.windows.storage.streams import DataWriter  # noqa: F401
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    if app.windowIcon().isNull():
        return 1
    if not all((SOUNDS_DIR / f"{name}.wav").is_file() for name in ("click", "chime", "capture")):
        return 2
    player = QMediaPlayer()
    player.setAudioOutput(QAudioOutput(player))
    return 0


def main():
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QIcon(ICON_PATH))
    app.setQuitOnLastWindowClosed(True)

    if "--self-check" in sys.argv[1:]:
        sys.exit(_self_check(app))

    _setup_logging()
    sys.excepthook = _global_exception_hook

    ocr = OCRService()
    window = MainWindow(ocr_engine=ocr)
    window.show()

    bridge = HotkeyBridge(app)
    bridge.capture.connect(window._on_capture_click)
    hotkey = keyboard.add_hotkey("ctrl+alt+s", bridge.capture.emit, suppress=True)
    try:
        sys.exit(app.exec())
    finally:
        keyboard.remove_hotkey(hotkey)


if __name__ == "__main__":
    main()
