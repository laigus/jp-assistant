"""Translation and grammar analysis via Ollama."""
import requests
import json


GRAMMAR_PROMPT = """你是日语老师。分析以下日语文本，用中文回答。严格遵守以下规则：
- 不要写任何开场白或结尾寒暄
- 直接从"一、整体翻译"开始输出

一、整体翻译

二、单词解释
（按句分组。格式：词语（读音） — 词性，含义。读音已在括号中标注，不要额外再写"读音：xxx"。）

三、语法说明
（关键语法点，每条说明结构和含义。）

{text}"""


class GrammarAnalyzer:
    def __init__(self, model: str = "deepseek-v3.1:671b-cloud", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def analyze(self, text: str, callback=None):
        """Analyze Japanese text with streaming."""
        prompt = GRAMMAR_PROMPT.format(text=text)

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "options": {
                "num_predict": 8192,
                "temperature": 0.3,
            }
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=(10, 600)
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

    def check_connection(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
