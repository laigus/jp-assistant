"""Translation and grammar analysis via multiple LLM backends."""
import copy
import json
import os
import re
from urllib.parse import urlsplit

import requests

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_MODELS_CONFIG = os.path.join(_DATA_DIR, "models_config.json")

DEFAULT_PROVIDERS = {
    "ollama": {
        "name": "Ollama（本地）",
        "type": "ollama",
        "base_url": "http://localhost:11434",
        "api_key": "",
        "models": ["deepseek-v3.1:671b-cloud"],
        "default_model": "deepseek-v3.1:671b-cloud",
    },
    "deepseek": {
        "name": "DeepSeek",
        "type": "openai_compatible",
        "base_url": "https://api.deepseek.com",
        "api_key": "",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
        "default_model": "deepseek-v4-flash",
    },
}

BUILTIN_PROVIDER_KEYS = frozenset(DEFAULT_PROVIDERS)


def build_openai_endpoint(base_url: str, endpoint: str) -> str:
    """Build an OpenAI-compatible endpoint from a base or full API URL."""
    base = (base_url or "").strip().rstrip("/")
    endpoint = endpoint.strip("/")
    if not base:
        return ""

    for known_endpoint in ("chat/completions", "models"):
        suffix = f"/{known_endpoint}"
        if base.endswith(suffix):
            if endpoint == known_endpoint:
                return base
            return f"{base[:-len(suffix)]}/{endpoint}"

    path_segments = [segment for segment in urlsplit(base).path.split("/") if segment]
    has_version_segment = any(
        re.fullmatch(r"v\d+(?:beta\d*)?", segment, flags=re.IGNORECASE)
        for segment in path_segments
    )
    if has_version_segment:
        return f"{base}/{endpoint}"
    return f"{base}/v1/{endpoint}"


class ModelsConfig:
    """Load / save multi-provider model configuration."""

    def __init__(self):
        self.providers: dict = {}
        self.active_provider: str = "ollama"
        self._load()

    def _load(self):
        if os.path.exists(_MODELS_CONFIG):
            try:
                with open(_MODELS_CONFIG, "r", encoding="utf-8") as f:
                    data = json.load(f)
                providers = data.get("providers", {})
                if isinstance(providers, dict) and providers:
                    self.providers = providers
                    active = data.get("active_provider", "ollama")
                    self.active_provider = (
                        active if active in providers else next(iter(providers))
                    )
                    return
            except Exception:
                pass
        self.providers = copy.deepcopy(DEFAULT_PROVIDERS)
        self.active_provider = "ollama"
        self.save()

    def save(self):
        if self.active_provider not in self.providers:
            self.active_provider = next(iter(self.providers), "ollama")
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_MODELS_CONFIG, "w", encoding="utf-8") as f:
            json.dump(
                {"providers": self.providers, "active_provider": self.active_provider},
                f, ensure_ascii=False, indent=2,
            )

    def get_provider(self, key: str | None = None) -> dict:
        key = key or self.active_provider
        return self.providers.get(key, {})

    def provider_keys(self) -> list[str]:
        return list(self.providers.keys())

    def provider_display_name(self, key: str) -> str:
        return self.providers.get(key, {}).get("name", key)

    @staticmethod
    def is_builtin_provider(key: str) -> bool:
        return key in BUILTIN_PROVIDER_KEYS

    def is_custom_provider(self, key: str) -> bool:
        return bool(key) and not self.is_builtin_provider(key)

    def next_custom_provider_key(self) -> str:
        key = "custom"
        suffix = 2
        while key in self.providers:
            key = f"custom_{suffix}"
            suffix += 1
        return key

    def create_custom_provider(self) -> str:
        key = self.next_custom_provider_key()
        custom_count = sum(
            1 for provider_key in self.providers
            if self.is_custom_provider(provider_key)
        )
        display_name = "自定义 API" if custom_count == 0 else f"自定义 API {custom_count + 1}"
        self.providers[key] = {
            "name": display_name,
            "type": "openai_compatible",
            "base_url": "",
            "api_key": "",
            "models": [],
            "default_model": "",
        }
        return key

    def add_provider(self, key: str, cfg: dict):
        self.providers[key] = cfg

    def remove_provider(self, key: str) -> bool:
        if self.is_builtin_provider(key):
            return False
        self.providers.pop(key, None)
        if self.active_provider == key:
            self.active_provider = (
                "ollama" if "ollama" in self.providers
                else next(iter(self.providers), "ollama")
            )
        return True


class GrammarAnalyzer:
    def __init__(self, provider_key: str = "", model: str = "", models_cfg: ModelsConfig | None = None):
        self._cfg = models_cfg or ModelsConfig()
        self._session = requests.Session()

        if provider_key:
            self._cfg.active_provider = provider_key
        prov = self._cfg.get_provider()
        self.provider_key = self._cfg.active_provider
        self.model = model or prov.get("default_model", "")
        self._apply_provider(prov)

    def _apply_provider(self, prov: dict):
        self._type = prov.get("type", "ollama")
        self._base_url = prov.get("base_url", "http://localhost:11434")
        self._api_key = prov.get("api_key", "")

    def switch_provider(self, provider_key: str, model: str = ""):
        self.provider_key = provider_key
        self._cfg.active_provider = provider_key
        prov = self._cfg.get_provider(provider_key)
        self._apply_provider(prov)
        self.model = model or prov.get("default_model", "")

    # ── analysis ──

    def analyze(self, prompt: str, callback=None, cancel_check=None):
        """Stream analysis; auto-dispatches to Ollama or OpenAI-compatible backend."""
        if not self.model.strip():
            return "❌ 请在设置中填写模型 ID"
        if not self._base_url.strip():
            return "❌ 请在设置中填写 API URL"
        if self._type == "ollama":
            return self._analyze_ollama(prompt, callback, cancel_check)
        return self._analyze_openai(prompt, callback, cancel_check)

    def _analyze_ollama(self, prompt: str, callback, cancel_check):
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "options": {"num_predict": 8192, "temperature": 0.3},
        }
        resp = None
        try:
            resp = self._session.post(
                f"{self._base_url}/api/chat",
                json=payload, stream=True, timeout=(10, 600),
            )
            resp.raise_for_status()
            full = ""
            thinking_shown = False
            for line in resp.iter_lines():
                if cancel_check and cancel_check():
                    return full + "\n\n⏹ 已停止"
                if not line:
                    continue
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                if content:
                    full += content
                    if callback:
                        callback(full)
                elif not thinking_shown:
                    thinking_shown = True
                    if callback:
                        callback("⏳ 模型思考中，请等待...")
                if data.get("done", False):
                    break
            return full if full else "⚠ 模型未产出内容，请重试"
        except requests.exceptions.ConnectionError:
            return "❌ 无法连接 Ollama（请运行 ollama serve）"
        except Exception as e:
            return f"❌ {e}"
        finally:
            if resp is not None:
                resp.close()

    def _analyze_openai(self, prompt: str, callback, cancel_check):
        """OpenAI-compatible streaming (works with DeepSeek, OpenAI, 通义千问, etc.)."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "temperature": 0.3,
            "max_tokens": 8192,
        }

        url = build_openai_endpoint(self._base_url, "chat/completions")
        resp = None
        try:
            resp = self._session.post(
                url, headers=headers, json=payload,
                stream=True, timeout=(10, 600),
            )
            resp.raise_for_status()
            full = ""
            thinking_shown = False
            for line in resp.iter_lines():
                if cancel_check and cancel_check():
                    return full + "\n\n⏹ 已停止"
                if not line:
                    continue
                text = line.decode("utf-8", errors="replace")
                if not text.startswith("data: "):
                    continue
                text = text[6:]
                if text.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue
                choices = data.get("choices")
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                reasoning = delta.get("reasoning_content", "")
                if content:
                    full += content
                    if callback:
                        callback(full)
                elif reasoning:
                    if not thinking_shown:
                        thinking_shown = True
                        if callback:
                            callback("⏳ 模型思考中，请等待...")
            return full if full else "⚠ 模型未产出内容，请重试"
        except requests.exceptions.ConnectionError:
            return f"❌ 无法连接 API（{self._base_url}）"
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            if status == 401:
                return "❌ API Key 无效，请在设置中检查"
            if status == 402:
                return "❌ API 余额不足，请充值"
            if status == 429:
                return "❌ 请求过于频繁，请稍后重试"
            return f"❌ HTTP {status}: {e}"
        except Exception as e:
            return f"❌ {e}"
        finally:
            if resp is not None:
                resp.close()

    # ── model listing ──

    def list_models(self) -> list[str]:
        """Return models for the current provider."""
        prov = self._cfg.get_provider(self.provider_key)
        if prov.get("type") == "ollama":
            return self._list_ollama_models()
        return prov.get("models", [])

    def _list_ollama_models(self) -> list[str]:
        ollama_prov = self._cfg.get_provider("ollama")
        url = ollama_prov.get("base_url", "http://localhost:11434") if ollama_prov else "http://localhost:11434"
        try:
            resp = self._session.get(f"{url}/api/tags", timeout=5)
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass
        return []

    @staticmethod
    def list_cloud_models() -> list[str]:
        try:
            resp = requests.get("https://ollama.com/api/tags", timeout=10)
            if resp.status_code == 200:
                names = [m["name"] for m in resp.json().get("models", [])]
                return [f"{n}-cloud" if not n.endswith("-cloud") else n for n in names]
        except Exception:
            pass
        return []

    def check_connection(self) -> bool:
        prov = self._cfg.get_provider(self.provider_key)
        if prov.get("type") == "ollama":
            try:
                resp = self._session.get(f"{self._base_url}/api/tags", timeout=5)
                return resp.status_code == 200
            except Exception:
                return False
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            url = build_openai_endpoint(self._base_url, "models")
            resp = self._session.get(url, headers=headers, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
