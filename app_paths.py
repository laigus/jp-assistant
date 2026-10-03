"""Read-only application resources and writable per-user storage."""
import os
import sys
from pathlib import Path

RESOURCE_DIR = Path(__file__).resolve().parent
INSTALL_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else RESOURCE_DIR
DATA_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / "HaohaoLanguageAssistant"
LOG_DIR = DATA_DIR / "logs"
SOUNDS_DIR = RESOURCE_DIR / "assets" / "sounds"


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
