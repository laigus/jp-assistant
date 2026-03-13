"""Japanese OCR using manga-ocr, with line-split and cloud correction modes."""
import os
import threading
import base64
import io
import json

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from manga_ocr import MangaOcr
from PIL import Image
import numpy as np
import requests


OCR_MODE_BASIC = "basic"
OCR_MODE_LINES = "lines"
OCR_MODE_CORRECT = "correct"


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

    def _ensure_ready(self):
        if self._ocr is None:
            self._loaded.wait(timeout=120)
        if self._error:
            raise RuntimeError(f"OCR model load failed: {self._error}")
        if self._ocr is None:
            raise RuntimeError("OCR model not loaded (timeout)")

    def recognize(self, image: Image.Image) -> str:
        self._ensure_ready()
        with self._lock:
            return self._ocr(image)

    def recognize_lines(self, image: Image.Image) -> str:
        """Split image into text lines, OCR each separately, then join."""
        self._ensure_ready()
        lines = _split_lines(image)
        if not lines:
            with self._lock:
                return self._ocr(image)
        results = []
        with self._lock:
            for line_img in lines:
                text = self._ocr(line_img)
                if text.strip():
                    results.append(text.strip())
        return "\n".join(results)

    def recognize_with_correction(
        self, image: Image.Image,
        model: str = "deepseek-v3.1:671b-cloud",
        base_url: str = "http://localhost:11434",
    ) -> str:
        """OCR first, then send OCR text + image to LLM for correction."""
        self._ensure_ready()
        with self._lock:
            raw_text = self._ocr(image)

        corrected = _llm_correct(raw_text, image, model, base_url)
        return corrected if corrected else raw_text

    @property
    def is_ready(self) -> bool:
        return self._ocr is not None


def _split_lines(image: Image.Image, min_line_height: int = 10) -> list[Image.Image]:
    """Split an image into horizontal text lines using projection profile."""
    gray = image.convert("L")
    arr = np.array(gray)

    threshold = 200
    binary = arr < threshold
    h_proj = binary.sum(axis=1)

    is_text = h_proj > (arr.shape[1] * 0.02)

    lines = []
    in_line = False
    start = 0
    for y in range(len(is_text)):
        if is_text[y] and not in_line:
            start = y
            in_line = True
        elif not is_text[y] and in_line:
            if y - start >= min_line_height:
                pad = 4
                top = max(0, start - pad)
                bottom = min(arr.shape[0], y + pad)
                lines.append(image.crop((0, top, image.width, bottom)))
            in_line = False

    if in_line and len(is_text) - start >= min_line_height:
        pad = 4
        top = max(0, start - pad)
        lines.append(image.crop((0, top, image.width, arr.shape[0])))

    return lines if len(lines) >= 2 else []


def _llm_correct(
    ocr_text: str, image: Image.Image,
    model: str, base_url: str,
) -> str:
    """Ask LLM to correct OCR errors by comparing text with the image."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    prompt = (
        f"以下是 OCR 识别结果，可能有错误：\n{ocr_text}\n\n"
        "请对照图片中的日语文本，纠正识别错误。"
        "只输出纠正后的日语文本，不要解释。保留原文换行。"
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [img_b64],
            }
        ],
        "stream": False,
        "options": {"num_predict": 1024, "temperature": 0.1},
    }

    try:
        resp = requests.post(
            f"{base_url}/api/chat",
            json=payload,
            timeout=(10, 60),
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "").strip()
        return content if content else ""
    except Exception:
        return ""
