"""Japanese OCR using meikiocr — high-speed game text recognition."""
import os
import threading
import time
import traceback

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from PIL import Image
import numpy as np

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


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
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    print(f"[OCR] Loading meikiocr engine (attempt {attempt}/{MAX_RETRIES})...")
                    from meikiocr import MeikiOCR
                    with self._lock:
                        if self._engine is None:
                            self._engine = MeikiOCR()
                    self._error = None
                    print("[OCR] Engine loaded successfully")
                    return
                except Exception as e:
                    tb = traceback.format_exc()
                    self._error = f"{e}\n{tb}"
                    print(f"[OCR] Load attempt {attempt} failed: {e}")
                    if attempt < MAX_RETRIES:
                        print(f"[OCR] Retrying in {RETRY_DELAY}s...")
                        time.sleep(RETRY_DELAY)
            print(f"[OCR] All {MAX_RETRIES} attempts failed")
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

    @property
    def error(self) -> str | None:
        return self._error
