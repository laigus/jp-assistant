"""Translation and grammar analysis via multiple LLM backends."""
import json
import os
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
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
    },
}


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
                self.providers = data.get("providers", {})
                self.active_provider = data.get("active_provider", "ollama")
                return
            except Exception:
                pass
        import copy
        self.providers = copy.deepcopy(DEFAULT_PROVIDERS)
        self.active_provider = "ollama"
        self.save()

    def save(self):
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

    def add_provider(self, key: str, cfg: dict):
        self.providers[key] = cfg
        self.save()

    def remove_provider(self, key: str):
        self.providers.pop(key, None)
        if self.active_provider == key:
            self.active_provider = next(iter(self.providers), "ollama")
        self.save()


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
        prov = self._cfg.get_provider(provider_key)
        self._apply_provider(prov)
        self.model = model or prov.get("default_model", "")

    # ── analysis ──

    def analyze(self, prompt: str, callback=None, cancel_check=None):
        """Stream analysis; auto-dispatches to Ollama or OpenAI-compatible backend."""
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

        url = self._base_url.rstrip("/") + "/v1/chat/completions"
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
                delta = data.get("choices", [{}])[0].get("delta", {})
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
            url = self._base_url.rstrip("/") + "/v1/models"
            resp = self._session.get(url, headers=headers, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
