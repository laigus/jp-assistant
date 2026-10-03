"""Prompt management - save/load system prompts and build analysis prompts."""
import json
import os
from core.languages import LANGUAGES

DEFAULT_PROMPTS = {"ja": """你是日语老师。分析以下日语文本，用中文回答。严格遵守以下格式规则：
- 不要写任何开场白或结尾寒暄
- 使用 Markdown 格式输出

## 一、整体翻译
逐句翻译。

## 二、单词解释
按句分组。每句用 **粗体** 标记原文，然后换行列出该句的单词。
每个单词必须单独占一行，格式：
- 词语（读音，用日语假名，已经是假名的不需要再写） — 词性，含义

注意：读音已在括号中标注，不要额外再写"读音：xxx"。

## 三、语法说明
列出关键语法点，每条说明结构、含义和用法。

待分析文本：
{text}""", "en": """你是英语老师。分析以下英语文本，用中文回答。
- 不要写开场白或结尾寒暄，使用 Markdown 格式。

## 一、整体翻译
逐句翻译，保留原文语气。

## 二、单词与短语
按句分组，每句先用 **粗体** 标记原文。重点解释生词、固定搭配和短语动词。
每项单独占一行：词语或短语 — 词性、语境中的含义；重要生词可附国际音标。

## 三、语法与句子结构
说明关键时态、从句、非谓语和省略，拆解复杂句子的主干及修饰关系。

待分析文本：
{text}"""}


class PromptManager:
    def __init__(self, data_dir: str):
        self._path = os.path.join(data_dir, "prompts.json")
        self.prompts = dict(DEFAULT_PROMPTS)
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Import an existing user-written Japanese prompt into the new schema.
                saved = data.get("prompts", {})
                if "system_prompt" in data and "ja" not in saved:
                    saved["ja"] = data["system_prompt"]
                self.prompts.update({key: value for key, value in saved.items()
                                     if key in LANGUAGES and isinstance(value, str)})
            except Exception:
                pass

    def save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump({"prompts": self.prompts}, f, ensure_ascii=False, indent=2)

    def build_prompt(self, text: str, temp_instruction: str = "", language: str = "ja") -> str:
        temp_instruction = temp_instruction.strip()
        if temp_instruction:
            return (
                f"请针对以下{LANGUAGES[language].name}文本，用中文按照临时指令进行解释。\n\n"
                f"待解释文本：\n{text}\n\n"
                f"临时指令：\n{temp_instruction}"
            )
        return self.prompts[language].replace("{text}", text)
