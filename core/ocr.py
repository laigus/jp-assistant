"""Japanese OCR using manga-ocr, optimized for game text."""
import os
import threading

# Use HuggingFace mirror for China users
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from manga_ocr import MangaOcr
from PIL import Image


class JapaneseOCR:
    def __init__(self):
        self._ocr = None
        self._lock = threading.Lock()
        self._loading = False
        self._loaded = threading.Event()
        self._error = None

    def preload(self):
        if self._ocr is not None or self._loading:
            return
        self._loading = True
        thread = threading.Thread(target=self._load, daemon=True)
        thread.start()

    def _load(self):
        try:
            with self._lock:
                if self._ocr is None:
                    self._ocr = MangaOcr()
        except Exception as e:
            self._error = str(e)
        finally:
            self._loaded.set()

    def recognize(self, image: Image.Image) -> str:
        if self._ocr is None:
            self._loaded.wait(timeout=120)
        if self._error:
            raise RuntimeError(f"OCR model load failed: {self._error}")
        if self._ocr is None:
            raise RuntimeError("OCR model not loaded (timeout)")
        with self._lock:
            return self._ocr(image)

    @property
    def is_ready(self) -> bool:
        return self._ocr is not None
