"""Prompt management - save/load/edit system prompts with temp prompt support."""
import json
import os

DEFAULT_PROMPT = """你是日语老师。分析以下日语文本，用中文回答。严格遵守以下规则：
- 不要写任何开场白或结尾寒暄
- 使用 Markdown 格式输出
- 用 ## 标记大标题

## 一、整体翻译

## 二、单词解释
（按句分组，用 **粗体** 标记每句原文。格式：词语（读音） — 词性，含义。读音已在括号中标注，不要额外再写"读音：xxx"。）

## 三、语法说明
（关键语法点，每条说明结构和含义。）

{text}"""


class PromptManager:
    def __init__(self, data_dir: str):
        self._path = os.path.join(data_dir, "prompts.json")
        self.system_prompt = DEFAULT_PROMPT
        self.temp_prompt = ""
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.system_prompt = data.get("system_prompt", DEFAULT_PROMPT)
            except Exception:
                pass

    def save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump({"system_prompt": self.system_prompt}, f, ensure_ascii=False, indent=2)

    def build_prompt(self, text: str) -> str:
        prompt = self.system_prompt.replace("{text}", text)
        if self.temp_prompt.strip():
            prompt += f"\n\n额外要求：{self.temp_prompt}"
            self.temp_prompt = ""
        return prompt

    def reset(self):
        self.system_prompt = DEFAULT_PROMPT
        self.save()
