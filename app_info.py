"""Shared application identity for the UI, launcher and desktop shortcut."""
from pathlib import Path

APP_NAME = "耗耗语言助手"
APP_ID = "Haohao.LanguageAssistant"
BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = str(BASE_DIR / "assets" / "haohao.ico")
