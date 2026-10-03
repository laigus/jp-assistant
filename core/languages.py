"""Language registry and per-language OCR / Edge TTS preferences."""
import copy
import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    name: str
    locale: str
    ocr_backend: str
    voice: str
    voices: tuple[str, ...]
    instruction_example: str


LANGUAGES = {
    "ja": Language("日语", "ja-JP", "meikiocr", "ja-JP-NanamiNeural",
                   ("ja-JP-NanamiNeural", "ja-JP-KeitaNeural"), "例如：只解释敬语用法..."),
    "en": Language("英语", "en-US", "windows", "en-US-JennyNeural",
                   ("en-US-JennyNeural", "en-US-AvaNeural", "en-US-AndrewNeural",
                    "en-GB-SoniaNeural", "en-GB-RyanNeural"), "例如：解释短语动词和从句结构..."),
}


def default_settings(language: str) -> dict:
    spec = LANGUAGES[language]
    return {"ocr_backend": spec.ocr_backend, "ocr_locale": spec.locale,
            "det_threshold": 0.5, "rec_threshold": 0.1,
            "voice": spec.voice, "rate": 0}


class LanguageConfig:
    def __init__(self, data_dir: str):
        self._path = os.path.join(data_dir, "languages.json")
        self.active_language = "ja"
        self.profiles = {key: default_settings(key) for key in LANGUAGES}
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            active = data.get("active_language", "ja")
            self.active_language = active if active in LANGUAGES else "ja"
            for key, profile in data.get("profiles", {}).items():
                if key in LANGUAGES and isinstance(profile, dict):
                    self.set_profile(key, profile)
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def profile(self, language: str) -> dict:
        return copy.deepcopy(self.profiles[language])

    def set_profile(self, language: str, profile: dict):
        values = default_settings(language)
        values.update({key: profile[key] for key in values if key in profile})
        backends = {"windows", "meikiocr"} if language == "ja" else {"windows"}
        if values["ocr_backend"] not in backends:
            values["ocr_backend"] = LANGUAGES[language].ocr_backend
        values["ocr_locale"] = str(values["ocr_locale"]).strip() or LANGUAGES[language].locale
        values["voice"] = str(values["voice"]).strip() or LANGUAGES[language].voice
        values["rate"] = max(-50, min(50, int(values["rate"])))
        for key in ("det_threshold", "rec_threshold"):
            values[key] = max(0.0, min(1.0, float(values[key])))
        self.profiles[language] = values

    def save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump({"active_language": self.active_language, "profiles": self.profiles},
                      f, ensure_ascii=False, indent=2)
