"""UI configuration — transparency, theme color, persistence."""
import json
import os

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_CONFIG_FILE = os.path.join(_DATA_DIR, "ui_config.json")

THEMES = {
    "dark": {
        "name": "暗黑",
        "is_light": False,
        "base_rgb": (8, 8, 12),
        "tint_bgr": (0x08, 0x08, 0x10),
    },
    "blue_dark": {
        "name": "深蓝",
        "is_light": False,
        "base_rgb": (6, 10, 22),
        "tint_bgr": (0x16, 0x0A, 0x06),
    },
    "light": {
        "name": "纯白",
        "is_light": True,
        "base_rgb": (240, 240, 245),
        "tint_bgr": (0xF0, 0xF0, 0xF0),
    },
    "blue_light": {
        "name": "浅蓝",
        "is_light": True,
        "base_rgb": (225, 235, 250),
        "tint_bgr": (0xFA, 0xEB, 0xE1),
    },
}


class UIConfig:
    """Singleton for UI appearance settings."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._opacity = 15
            cls._instance._theme = "dark"
            cls._instance._acrylic_enabled = True
            cls._instance._window_pos = None
            cls._instance._selected_model = ""
            cls._instance._result_pos = None
            cls._instance._result_zoom = 100
            cls._instance._load()
        return cls._instance

    def _load(self):
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._opacity = max(0, min(100, data.get("opacity", 15)))
                t = data.get("theme", "dark")
                self._theme = t if t in THEMES else "dark"
                self._acrylic_enabled = data.get("acrylic", True)
                pos = data.get("window_pos")
                if pos and len(pos) == 2:
                    self._window_pos = tuple(pos)
                self._selected_model = data.get("selected_model", "")
                rp = data.get("result_pos")
                if rp and len(rp) == 2:
                    self._result_pos = tuple(rp)
                self._result_zoom = max(50, min(300, data.get("result_zoom", 100)))
        except Exception:
            pass

    def save(self):
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            data = {
                "opacity": self._opacity,
                "theme": self._theme,
                "acrylic": self._acrylic_enabled,
            }
            if self._window_pos:
                data["window_pos"] = list(self._window_pos)
            if self._selected_model:
                data["selected_model"] = self._selected_model
            if self._result_pos:
                data["result_pos"] = list(self._result_pos)
            if self._result_zoom != 100:
                data["result_zoom"] = self._result_zoom
            json.dump(data, f)

    @property
    def opacity(self) -> int:
        return self._opacity

    @opacity.setter
    def opacity(self, val: int):
        self._opacity = max(0, min(100, val))

    @property
    def theme(self) -> str:
        return self._theme

    @theme.setter
    def theme(self, val: str):
        if val in THEMES:
            self._theme = val

    @property
    def theme_data(self) -> dict:
        return THEMES[self._theme]

    @property
    def is_light(self) -> bool:
        return self.theme_data["is_light"]

    @property
    def acrylic_enabled(self) -> bool:
        return self._acrylic_enabled

    @acrylic_enabled.setter
    def acrylic_enabled(self, val: bool):
        self._acrylic_enabled = val

    def acrylic_tint(self) -> int:
        """Return tint_color in AABBGGRR format for Windows Acrylic API."""
        alpha = int(self._opacity * 0.6)
        b, g, r = self.theme_data["tint_bgr"]
        return (alpha << 24) | (b << 16) | (g << 8) | r

    def fill_alpha_top(self) -> int:
        return max(1, int(self._opacity * 0.9))

    def fill_alpha_bottom(self) -> int:
        return max(2, int(self._opacity * 1.2))

    def base_rgb(self) -> tuple:
        return self.theme_data["base_rgb"]

    @property
    def window_pos(self):
        return self._window_pos

    @window_pos.setter
    def window_pos(self, val):
        if val and len(val) == 2:
            self._window_pos = tuple(val)

    @property
    def selected_model(self) -> str:
        return self._selected_model

    @selected_model.setter
    def selected_model(self, val: str):
        self._selected_model = val or ""

    @property
    def result_pos(self):
        return self._result_pos

    @result_pos.setter
    def result_pos(self, val):
        if val and len(val) == 2:
            self._result_pos = tuple(val)

    @property
    def result_zoom(self) -> int:
        return self._result_zoom

    @result_zoom.setter
    def result_zoom(self, val: int):
        self._result_zoom = max(50, min(300, val))
