# 项目架构

JP Assistant 是 Windows 桌面日语学习助手，主流程为：

```text
屏幕框选 → OCR → 文本编辑 → 翻译与语法解析 → Markdown 展示 → 朗读/生词本
```

## 模块划分

```text
jp-assistant/
├── main.py                    # 应用入口
├── core/
│   ├── ocr.py                 # meikiocr 封装
│   ├── translator.py          # 提供商配置、模型获取、流式解析
│   ├── prompt_manager.py      # 系统 Prompt 与临时指令 Prompt 构造
│   ├── tts.py                 # edge-tts 语音合成
│   └── vocab.py               # 生词本数据
├── ui/
│   ├── main_window.py         # 主窗口与流程编排
│   ├── screenshot.py          # 全屏框选
│   ├── result_window.py       # 详情展示与缩放
│   ├── settings_dialog.py     # 提供商、模型、Prompt、外观设置
│   ├── vocab_window.py        # 生词本界面
│   ├── ui_config.py           # 主题、透明度、窗口状态持久化
│   ├── styles.py              # QSS
│   ├── md_render.py           # Markdown HTML 与正文样式
│   ├── acrylic.py             # Windows Acrylic / DWM
│   ├── glass_base.py          # 玻璃窗口公共绘制
│   └── icons.py               # 主题自适应 SVG 图标
├── tests/                     # 聚焦回归测试
├── data/                      # 本机运行时配置和用户数据（Git 忽略）
├── models_config.example.json # 模型配置示例
└── setup_shortcut.py          # 桌面快捷方式安装
```

## 核心流程

1. `ui/screenshot.py` 获取框选区域，`core/ocr.py` 将图像交给 meikiocr。
2. 用户可在主窗口修正 OCR 文本，再由 `PromptManager` 组装解析 Prompt：没有临时指令时使用系统 Prompt；有临时指令时仅用“待解释文本 + 临时指令”组成完整 Prompt，不叠加系统 Prompt。
3. `GrammarAnalyzer` 按当前提供商调用 Ollama 或 OpenAI 兼容接口，并把流式增量送回界面。
4. `ui/md_render.py` 把解析结果渲染到主窗口和详情窗口；内容更新时保留详情窗口缩放比例。
5. `core/tts.py` 生成语音，生词内容由 `core/vocab.py` 持久化。

临时指令由主窗口持有。它在当前文本的重复解析中持续生效，仅在 OCR 成功识别到下一段非空文本后清空；解析、停止解析、OCR 失败和空识别结果都不会提前清空。

## 模型提供商

- 内置提供商为 Ollama 和 DeepSeek；设置页还可新增、删除多个 OpenAI 兼容提供商。
- API URL 可填写服务根地址、版本化根地址或完整 `chat/completions` 地址，由 `core/translator.py` 统一生成聊天与模型端点。
- Ollama 通过 `/api/tags` 获取模型；OpenAI 兼容提供商通过 `/models` 获取模型。
- 获取成功后，接口返回列表完整替换该提供商的旧列表，不混入已经失效的本地模型项；当前模型不在新列表时选择第一项。
- 模型选择框保持可编辑，自动获取后仍可手动输入模型 ID。
- 提供商、URL、密钥、模型列表和当前模型保存在 `data/models_config.json`。

## 线程与资源约束

- OCR、LLM、TTS 和模型列表请求不得阻塞 UI 线程。
- Worker 结束后由统一清理流程释放。
- 流式 HTTP response 无论成功、取消或异常都必须关闭，避免后续请求挂起。
- 主题切换后同步刷新 QSS、图标、Markdown HTML 和 Acrylic 效果。
- `data/` 是运行时目录，不存开发验证产物。

## 文档边界

- 用户功能、安装与操作见 [README](../README.md)。
- 尚未完成的工作见 [roadmap](roadmap.md)。
