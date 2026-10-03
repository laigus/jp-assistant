"""Vocabulary book — save/load/delete sentence entries with analysis and TTS cache."""
import json
import os
import time
from core.languages import LANGUAGES

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_VOCAB_FILE = os.path.join(_DATA_DIR, "vocabulary.json")


class VocabEntry:
    __slots__ = ("sentence", "analysis", "tts_path", "timestamp", "language", "tts_voice", "tts_rate")

    def __init__(self, sentence: str, analysis: str, tts_path: str = "",
                 timestamp: float = 0.0, language: str = "ja", tts_voice: str = "", tts_rate: int = 0):
        self.sentence = sentence
        self.analysis = analysis
        self.tts_path = tts_path
        self.timestamp = timestamp or time.time()
        self.language = language if language in LANGUAGES else "ja"
        self.tts_voice = tts_voice or LANGUAGES[self.language].voice
        self.tts_rate = tts_rate

    def to_dict(self) -> dict:
        return {
            "sentence": self.sentence,
            "analysis": self.analysis,
            "tts_path": self.tts_path,
            "timestamp": self.timestamp,
            "language": self.language,
            "tts_voice": self.tts_voice,
            "tts_rate": self.tts_rate,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VocabEntry":
        return cls(
            sentence=d.get("sentence", ""),
            analysis=d.get("analysis", ""),
            tts_path=d.get("tts_path", ""),
            timestamp=d.get("timestamp", 0.0),
            language=d.get("language", "ja"),
            tts_voice=d.get("tts_voice", ""),
            tts_rate=d.get("tts_rate", 0),
        )


class VocabManager:
    """Vocabulary persistence; called on the UI thread."""

    def __init__(self):
        self._entries: list[VocabEntry] = []
        self._load()

    def _load(self):
        if not os.path.exists(_VOCAB_FILE):
            return
        try:
            with open(_VOCAB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._entries = [VocabEntry.from_dict(d) for d in data]
        except Exception:
            self._entries = []

    def save(self):
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_VOCAB_FILE, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._entries], f,
                      ensure_ascii=False, indent=2)

    def add(self, sentence: str, analysis: str, tts_path: str = "", *, language: str = "ja",
            tts_voice: str = "", tts_rate: int = 0) -> VocabEntry:
        for e in self._entries:
            if e.sentence == sentence and e.language == language:
                e.analysis = analysis
                voice = tts_voice or LANGUAGES[language].voice
                same_voice = (e.tts_voice, e.tts_rate) == (voice, tts_rate)
                e.tts_path = tts_path or (e.tts_path if same_voice else "")
                e.tts_voice = voice
                e.tts_rate = tts_rate
                e.timestamp = time.time()
                self.save()
                return e
        entry = VocabEntry(sentence, analysis, tts_path, language=language,
                           tts_voice=tts_voice, tts_rate=tts_rate)
        self._entries.insert(0, entry)
        self.save()
        return entry

    def remove(self, index: int):
        if 0 <= index < len(self._entries):
            self._entries.pop(index)
            self.save()

    def remove_entry(self, entry: VocabEntry):
        if entry in self._entries:
            self._entries.remove(entry)
            self.save()

    def entries(self, language: str = "") -> list[VocabEntry]:
        return [entry for entry in self._entries if not language or entry.language == language]

    def count(self) -> int:
        return len(self._entries)

    def contains(self, sentence: str, language: str = "ja") -> bool:
        return any(e.sentence == sentence and e.language == language for e in self._entries)
