"""JP Assistant - Japanese Game Learning Assistant
Floating frosted-glass panel: Screenshot → OCR → Translate + Grammar → TTS
"""
# torch must be imported before PyQt6 to avoid DLL conflicts on Windows
import torch  # noqa: F401

import sys
import os
import keyboard

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from ui.main_window import MainWindow
from core.ocr import JapaneseOCR


def main():
    app = QApplication(sys.argv)
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

    # Start OCR model loading in background
    ocr = JapaneseOCR()
    ocr.preload()

    window = MainWindow(ocr_engine=ocr)
    window.show()

    # Global hotkey: Ctrl+Shift+J to capture
    def on_hotkey():
        QTimer.singleShot(0, window._on_capture_click)

    keyboard.add_hotkey("ctrl+shift+j", on_hotkey, suppress=True)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
