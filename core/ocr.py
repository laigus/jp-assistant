"""OCR routing: meikiocr for Japanese games, Windows OCR for installed languages."""
import asyncio
import os
import threading
import time
import traceback

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from PIL import Image
import numpy as np

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


class MeikiOCRBackend:
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

    def recognize(self, image: Image.Image, profile: dict) -> str:
        """Recognize Japanese text from a PIL Image."""
        self._ensure_ready()
        cv_img = np.array(image.convert("RGB"))[:, :, ::-1]  # RGB → BGR
        with self._lock:
            results = self._engine.run_ocr(cv_img, det_threshold=profile["det_threshold"],
                                          rec_threshold=profile["rec_threshold"])
        lines = [r["text"] for r in results if r.get("text", "").strip()]
        return "\n".join(lines) if lines else ""

    @property
    def is_ready(self) -> bool:
        return self._engine is not None

    @property
    def error(self) -> str | None:
        return self._error


class OCRService:
    def __init__(self):
        self._meiki = MeikiOCRBackend()

    def preload(self, profile: dict):
        if profile["ocr_backend"] == "meikiocr":
            self._meiki.preload()

    def recognize(self, image: Image.Image, profile: dict) -> str:
        if profile["ocr_backend"] == "meikiocr":
            self._meiki.preload()
            return self._meiki.recognize(image, profile)
        from winrt.runtime import ApartmentType, init_apartment, uninit_apartment
        init_apartment(ApartmentType.MULTI_THREADED)
        try:
            return asyncio.run(self._recognize_windows(image, profile["ocr_locale"]))
        finally:
            uninit_apartment()

    @staticmethod
    async def _recognize_windows(image: Image.Image, locale: str) -> str:
        from winrt.windows.globalization import Language
        from winrt.windows.graphics.imaging import SoftwareBitmap, BitmapPixelFormat, BitmapAlphaMode
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.storage.streams import DataWriter

        engine = OcrEngine.try_create_from_language(Language(locale))
        if engine is None:
            raise RuntimeError(f"Windows 未安装 {locale} OCR；请在系统语言选项中安装该语言的文字识别组件。")
        rgba = image.convert("RGBA")
        limit = OcrEngine.max_image_dimension
        if max(rgba.size) > limit:
            rgba.thumbnail((limit, limit), Image.Resampling.LANCZOS)
        writer = DataWriter()
        bitmap = None
        try:
            writer.write_bytes(rgba.tobytes("raw", "BGRA"))
            bitmap = SoftwareBitmap.create_copy_with_alpha_from_buffer(
                writer.detach_buffer(), BitmapPixelFormat.BGRA8, rgba.width, rgba.height,
                BitmapAlphaMode.IGNORE,
            )
            result = await engine.recognize_async(bitmap)
            return "\n".join(line.text for line in result.lines)
        finally:
            if bitmap is not None:
                bitmap.close()
            writer.close()
