"""Translation and grammar analysis via Ollama."""
import requests
import json


class GrammarAnalyzer:
    def __init__(self, model: str = "deepseek-v3.1:671b-cloud", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self._session = requests.Session()

    def analyze(self, prompt: str, callback=None):
        """Stream analysis for a pre-built prompt (from PromptManager)."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "options": {
                "num_predict": 8192,
                "temperature": 0.3,
            }
        }

        resp = None
        try:
            resp = self._session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=(10, 600),
            )
            resp.raise_for_status()

            full_content = ""
            thinking_shown = False

            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                msg = data.get("message", {})
                content = msg.get("content", "")

                if content:
                    full_content += content
                    if callback:
                        callback(full_content)
                elif not thinking_shown:
                    thinking_shown = True
                    if callback:
                        callback("⏳ 模型思考中，请等待...")

                if data.get("done", False):
                    break

            return full_content if full_content else "⚠ 模型未产出内容，请重试"

        except requests.exceptions.ConnectionError:
            return "❌ 无法连接 Ollama（请运行 ollama serve）"
        except Exception as e:
            return f"❌ {str(e)}"
        finally:
            if resp is not None:
                resp.close()

    def list_models(self) -> list[str]:
        """Fetch local model names from Ollama."""
        try:
            resp = self._session.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass
        return []

    @staticmethod
    def list_cloud_models() -> list[str]:
        """Fetch available cloud model names from Ollama registry."""
        try:
            resp = requests.get("https://ollama.com/api/tags", timeout=10)
            if resp.status_code == 200:
                names = [m["name"] for m in resp.json().get("models", [])]
                return [f"{n}-cloud" if not n.endswith("-cloud") else n for n in names]
        except Exception:
            pass
        return []

    def check_connection(self) -> bool:
        try:
            resp = self._session.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
