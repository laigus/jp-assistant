# 日语游戏助手 (JP Assistant)

悬浮在桌面最上层的日语学习助手面板，专为在游戏中学日语设计。

截图识别日语文本 → 翻译 + 语法解析 → 语音朗读

## 功能

- **截图 OCR** — 快捷键 `Ctrl+Alt+S` 框选屏幕区域，自动识别日语文本（ESC / 右键取消）
- **翻译 + 语法解析** — 整体翻译、逐词解释（读音/词性/含义）、语法说明
- **Markdown 渲染** — 解析结果格式化显示，清晰易读
- **语音朗读** — 高质量日语语音朗读识别到的文本
- **多 API 后端** — 支持 Ollama、DeepSeek、OpenAI 及所有 OpenAI 兼容 API，在设置中一键切换
- **自定义 API** — 在设置中新增任意 OpenAI 兼容 URL、API Key 与模型 ID，可保存多个配置
- **Prompt 管理** — 自定义系统 Prompt，支持临时指令
- **结果展开** — 一键弹出大窗口查看详细解析，支持 Ctrl+滚轮 / 按钮缩放文字；重新解析或更新内容时保留当前缩放比例
- **多主题** — 暗黑、深蓝、纯白、浅蓝四种主题，实时切换
- **透明度可调** — 0-100% 滑块控制界面透明度
- **Acrylic 磨砂** — Windows Acrylic 磨砂效果 + Win11 原生圆角阴影，可开关
- **位置记忆** — 主窗口和弹窗位置自动保存，重启后恢复

## 技术栈

| 模块 | 方案 |
|------|------|
| UI 框架 | PyQt6（无边框、Acrylic 磨砂、置顶） |
| OCR 引擎 | **meikiocr**（ONNX，专为日语游戏文字训练，速度快精度高） |
| 翻译+语法 | 多后端 LLM API（Ollama / DeepSeek / OpenAI 兼容） |
| 语音合成 | edge-tts（微软 Edge 在线神经网络 TTS，日语女声 NanamiNeural） |
| 音效 | Mixkit 免版权 WAV 音效 + Qt QSoundEffect |
| 截图 | mss + PyQt 全屏选区覆盖层 |
| 热键 | keyboard 库（全局热键 Ctrl+Alt+S） |
| 磨砂效果 | Windows DWM API（ctypes 调用 user32/dwmapi） |

> **备选 OCR 方案**：manga-ocr（基于 PyTorch + Transformers 的漫画专用 OCR）。
> 如需切换回 manga-ocr，安装 `pip install manga-ocr` 并修改 `core/ocr.py` 即可。
> manga-ocr 依赖 PyTorch（~443MB），适合漫画短句识别，但长文本准确率较低。

## 环境要求

- Windows 10/11
- Python 3.10+
- 以下任一 LLM 后端：
  - [Ollama](https://ollama.com/) 已安装并运行（本地模型）
  - [DeepSeek API Key](https://platform.deepseek.com/)（推荐，便宜好用）
  - 任何 OpenAI 兼容 API（OpenAI、通义千问、智谱、Moonshot 等）

## 安装

```bash
cd d:\AI\jp-assistant

# 创建虚拟环境（如果还没有）
python -m venv .venv

# 安装依赖
.venv\Scripts\pip.exe install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> 首次启动会自动下载 meikiocr 模型（检测 ~14MB + 识别 ~30MB），使用 HuggingFace 下载。

## 启动

### 方式一：桌面快捷方式（推荐）

运行一次安装脚本，自动生成图标和桌面快捷方式：

```bash
.venv\Scripts\python.exe setup_shortcut.py
```

之后双击桌面上的 **"JP Assistant"** 图标即可启动，无需打开终端。

### 方式二：命令行启动

```bash
.venv\Scripts\python.exe main.py
```

## 使用方法

1. 启动后面板出现在屏幕右上角，可拖动标题栏
2. 按 `Ctrl+Alt+S` 或点击「截图识别」按钮框选游戏文本区域（右键/ESC 取消）
3. 识别结果可编辑，编辑后点击「解析」重新分析
4. 点击「朗读」听日语发音
5. 点击 ⤢ 按钮展开查看详细解析（Ctrl+滚轮缩放文字）；重新解析后窗口会继续使用当前放大比例
6. 点击 ⚙ 按钮打开设置（API、模型、Prompt、主题、透明度、Acrylic 开关）
7. 可在临时 Prompt 输入框中输入额外指令

## 模型配置

### 使用 DeepSeek API（推荐）

1. 前往 [DeepSeek 开放平台](https://platform.deepseek.com/) 注册并获取 API Key
2. 启动程序后点击 ⚙ 设置
3. 在「API 提供商」下拉框选择 **DeepSeek**
4. 填入你的 API Key
5. 选择模型（`deepseek-v4-flash` 日常够用，`deepseek-v4-pro` 更强但更慢）
6. 点击保存

### 使用 Ollama 本地模型

```bash
# 设置模型存储路径（可选）
$env:OLLAMA_MODELS = "D:\AI\models"

# 下载模型
ollama pull qwen3:8b
```

在设置中选择 **Ollama（本地）** 提供商，然后选择模型即可。

### 添加新的 API 提供商

1. 打开设置，在「API 提供商」右侧点击 **＋**。
2. 填写显示名称、API URL、API Key（服务无需密钥时可留空）和模型 ID。
3. 点击保存；新配置立即成为当前提供商，下次启动继续使用。
4. 需要移除时选中该配置并点击 **−**；Ollama 和 DeepSeek 两个内置项会保留。

API URL 支持以下三种写法，程序会自动生成正确的 OpenAI 兼容请求地址：

- API 根地址：`https://example.com`
- 版本化 API 根地址：`https://example.com/v1`、`https://example.com/api/v4`
- 完整聊天接口：`https://example.com/v1/chat/completions`

自定义提供商与各自的模型 ID 保存在 `data/models_config.json`。示例结构见
`models_config.example.json`。
