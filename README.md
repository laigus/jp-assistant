# 日语游戏助手 (JP Assistant)

悬浮在桌面最上层的日语学习助手面板，专为在游戏中学日语设计。

截图识别日语文本 → 翻译 + 语法解析 → 语音朗读

## 功能

- **截图 OCR** — 快捷键 `Ctrl+Shift+J` 框选屏幕区域，自动识别日语文本
- **翻译 + 语法解析** — 整体翻译、逐词解释（读音/词性/含义）、语法说明
- **Markdown 渲染** — 解析结果格式化显示，清晰易读
- **语音朗读** — 高质量日语语音朗读识别到的文本
- **模型切换** — 支持 Ollama 所有模型，默认使用 deepseek-v3.1 云端模型
- **Prompt 管理** — 自定义系统 Prompt，支持临时指令
- **结果展开** — 一键弹出大窗口查看详细解析

## 环境要求

- Windows 10/11
- Python 3.10+
- [Ollama](https://ollama.com/) 已安装并运行

## 安装

```bash
cd d:\AI\jp-assistant

# 创建虚拟环境（如果还没有）
python -m venv .venv

# 安装依赖
.venv\Scripts\pip.exe install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> 首次启动会自动下载 OCR 模型（约 400MB），使用 HuggingFace 中国镜像加速。

## 启动

```bash
.venv\Scripts\python.exe main.py
```

## 使用方法

1. 启动后面板出现在屏幕右上角，可拖动
2. 按 `Ctrl+Shift+J` 或点击「截图识别」按钮框选游戏文本区域
3. 识别结果可编辑，编辑后点击「解析」重新分析
4. 点击「朗读」听日语发音
5. 点击 ⤢ 按钮展开查看详细解析
6. 点击 📝 按钮管理 Prompt（可设置临时指令）
7. 顶部下拉框可切换 Ollama 模型

## Ollama 模型

默认使用 `deepseek-v3.1:671b-cloud`（云端模型，速度快质量高）。

如需使用本地模型：

```bash
# 设置模型存储路径（可选）
$env:OLLAMA_MODELS = "D:\AI\models"

# 下载模型
ollama pull qwen3:8b
```

然后在面板顶部下拉框中切换即可。
