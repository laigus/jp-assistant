"""Workers shared by the main window, settings preview and vocabulary book."""
from PyQt6.QtCore import QThread, pyqtSignal

from core.tts import TextToSpeech, tts_error_message


class TtsWorker(QThread):
    result_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, tts: TextToSpeech, text: str, voice: str, rate: int = 0, parent=None):
        super().__init__(parent)
        self.tts = tts
        self.text = text
        self.voice = voice
        self.rate = rate

    def run(self):
        try:
            self.result_ready.emit(self.tts.speak(self.text, self.voice, self.rate))
        except Exception as exc:
            self.error.emit(tts_error_message(exc))


class VoiceListWorker(QThread):
    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.result_ready.emit(TextToSpeech.list_voices())
        except Exception as exc:
            self.error.emit(tts_error_message(exc))
