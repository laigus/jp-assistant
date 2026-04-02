"""Vocabulary book — save/load/delete sentence entries with analysis and TTS cache."""
import json
import os
import time

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_VOCAB_FILE = os.path.join(_DATA_DIR, "vocabulary.json")


class VocabEntry:
    __slots__ = ("sentence", "analysis", "tts_path", "timestamp")

    def __init__(self, sentence: str, analysis: str, tts_path: str = "",
                 timestamp: float = 0.0):
        self.sentence = sentence
        self.analysis = analysis
        self.tts_path = tts_path
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        return {
            "sentence": self.sentence,
            "analysis": self.analysis,
            "tts_path": self.tts_path,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VocabEntry":
        return cls(
            sentence=d.get("sentence", ""),
            analysis=d.get("analysis", ""),
            tts_path=d.get("tts_path", ""),
            timestamp=d.get("timestamp", 0.0),
        )


class VocabManager:
    """Thread-safe vocabulary persistence (JSON file)."""

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

    def add(self, sentence: str, analysis: str, tts_path: str = "") -> VocabEntry:
        for e in self._entries:
            if e.sentence == sentence:
                e.analysis = analysis
                e.tts_path = tts_path or e.tts_path
                e.timestamp = time.time()
                self.save()
                return e
        entry = VocabEntry(sentence, analysis, tts_path)
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

    def entries(self) -> list[VocabEntry]:
        return list(self._entries)

    def count(self) -> int:
        return len(self._entries)

    def contains(self, sentence: str) -> bool:
        return any(e.sentence == sentence for e in self._entries)
