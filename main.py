"""Haohao Language Assistant - Multilingual Game Learning Assistant
Floating frosted-glass panel: Screenshot → OCR → Translate + Grammar → TTS
"""
# onnxruntime must be imported before PyQt6 to avoid DLL conflicts on Windows
import onnxruntime  # noqa: F401

import sys
import os
import logging
import traceback
import keyboard
import ctypes

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon

from app_info import APP_NAME, APP_ID, ICON_PATH
from ui.main_window import MainWindow
from core.ocr import OCRService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _setup_logging():
    log_path = os.path.join(BASE_DIR, "data", "crash.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        level=logging.ERROR,
        format="%(asctime)s %(levelname)s %(message)s",
    )

def _global_exception_hook(exc_type, exc_value, exc_tb):
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.error("Unhandled exception:\n%s", msg)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def main():
    _setup_logging()
    sys.excepthook = _global_exception_hook

    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setWindowIcon(QIcon(ICON_PATH))
    app.setQuitOnLastWindowClosed(True)

    # Pre-generate sound effects if they don't exist
    sounds_dir = os.path.join(os.path.dirname(__file__), "assets", "sounds")
    if not os.path.exists(os.path.join(sounds_dir, "click.wav")):
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "assets"))
            from generate_sounds import generate_glass_click, generate_glass_chime, generate_capture_sound
            os.makedirs(sounds_dir, exist_ok=True)
            generate_glass_click(os.path.join(sounds_dir, "click.wav"))
            generate_glass_chime(os.path.join(sounds_dir, "chime.wav"))
            generate_capture_sound(os.path.join(sounds_dir, "capture.wav"))
        except Exception as e:
            print(f"Warning: Could not generate sounds: {e}")

    ocr = OCRService()
    window = MainWindow(ocr_engine=ocr)
    window.show()

    # Global hotkey: Ctrl+Alt+S to capture
    def on_hotkey():
        QTimer.singleShot(0, window._on_capture_click)

    keyboard.add_hotkey("ctrl+alt+s", on_hotkey, suppress=True)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
