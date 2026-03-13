"""Japanese OCR using meikiocr — high-speed game text recognition."""
import os
import threading

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from PIL import Image
import numpy as np


class JapaneseOCR:
    """OCR engine using meikiocr (ONNX-based, optimized for game text)."""

    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()
        self._loaded = threading.Event()
        self._loading = False
        self._error = None

    def preload(self):
        """Start loading the OCR engine in a background thread."""
        if self._engine is not None or self._loading:
            return
        self._loading = True
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        try:
            print("[OCR] Loading meikiocr engine...")
            from meikiocr import MeikiOCR
            with self._lock:
                if self._engine is None:
                    self._engine = MeikiOCR()
            print("[OCR] Engine loaded successfully")
        except Exception as e:
            self._error = str(e)
            print(f"[OCR] Engine load failed: {e}")
        finally:
            self._loaded.set()

    def _ensure_ready(self):
        if self._engine is None:
            self._loaded.wait(timeout=180)
        if self._error:
            raise RuntimeError(f"OCR engine load failed: {self._error}")
        if self._engine is None:
            raise RuntimeError("OCR engine not loaded (timeout, model may still be downloading)")

    def recognize(self, image: Image.Image) -> str:
        """Recognize Japanese text from a PIL Image."""
        self._ensure_ready()
        cv_img = np.array(image.convert("RGB"))[:, :, ::-1]  # RGB → BGR
        with self._lock:
            results = self._engine.run_ocr(cv_img)
        lines = [r["text"] for r in results if r.get("text", "").strip()]
        return "\n".join(lines) if lines else ""

    @property
    def is_ready(self) -> bool:
        return self._engine is not None
