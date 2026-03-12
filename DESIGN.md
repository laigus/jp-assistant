# 日语游戏助手 (JP Assistant)

## 概述
悬浮在桌面最上层的日语学习助手面板，专为游戏中学日语设计。
快捷键截图 → OCR 识别 → 翻译 + 语法解析 → 语音朗读。

## 启动方法

```bash
# 直接运行（无需手动激活虚拟环境）
d:\AI\jp-assistant\.venv\Scripts\python.exe d:\AI\jp-assistant\main.py
```

或：
```bash
cd d:\AI\jp-assistant
.venv\Scripts\activate
python main.py
```

### 全局快捷键
- **Ctrl+Shift+J** — 截图识别日语文本

### 首次启动
- OCR 模型（manga-ocr-base, ~400MB）首次启动自动从 HuggingFace 镜像下载
- 下载完成后后续启动约 5-10 秒

## 技术栈

| 模块 | 方案 |
|------|------|
| 桌面框架 | Python + PyQt6（无边框、磨砂玻璃、置顶） |
| OCR 识别 | manga-ocr（专为日语游戏/漫画训练） |
| 翻译+语法 | Ollama deepseek-v3.1:671b-cloud（默认）/ qwen3-vl:30b（本地备选） |
| 语音朗读 | edge-tts（微软免费 TTS，日语 nanami 声优） |
| 音频播放 | Qt QMediaPlayer + QSoundEffect（原生） |
| 音效 | 程序化生成的玻璃 WAV 音效 |
| 截图 | mss + PyQt 全屏选区覆盖层 |

## 已完成功能
- [x] 快捷键截图 + 区域选择
- [x] manga-ocr 日语识别（HuggingFace 中国镜像加速）
- [x] Ollama 翻译 + 语法解析（streaming 输出）
- [x] edge-tts 语音朗读（Qt QMediaPlayer 播放，不崩溃）
- [x] 玻璃音效（点击、完成、截图三种）
- [x] 无边框置顶悬浮窗
- [x] Windows Acrylic 磨砂玻璃效果
- [x] OCR 文本可编辑后重新解析
- [x] torch 优先导入避免 PyQt6 DLL 冲突

## 待优化（后续）
- [ ] 解析结果按 Markdown 格式化渲染，看起来更清晰舒服
- [ ] 可选择模型（默认云端 deepseek，可选本地模型）
- [ ] 界面美化（磨砂透明效果优化、布局调整）
- [ ] 字体优化（更好看的日语/中文字体）
- [ ] 音效优化（当前太尖锐，需要更柔和高级的玻璃音效）
- [ ] 解析结果窗口优化（按钮弹出更大的窗口显示详细结果）

## Ollama 模型

默认使用 `deepseek-v3.1:671b-cloud`（云端，速度快、质量高）。

本地备选 `qwen3-vl:30b`（已安装在 `D:\AI\models`，有 thinking 开销较慢）。

如需安装其他本地模型：
```bash
$env:OLLAMA_MODELS = "D:\AI\models"
ollama pull qwen3:8b
```

## 项目结构
```
jp-assistant/
├── main.py              # 入口（torch 优先导入避免 DLL 冲突）
├── ui/
│   ├── main_window.py   # 主窗口 + 所有 UI 逻辑
│   ├── screenshot.py    # 截图全屏选区
│   ├── acrylic.py       # Windows Acrylic 磨砂玻璃 API
│   └── styles.py        # QSS 样式表
├── core/
│   ├── ocr.py           # manga-ocr 封装（HF 镜像加速）
│   ├── translator.py    # Ollama 翻译 + 语法解析
│   └── tts.py           # edge-tts 语音合成
├── assets/
│   ├── sounds/          # 玻璃音效 WAV
│   └── generate_sounds.py
├── data/                # 数据目录
└── requirements.txt
```

## 开发记录

### 2026-03-12
- 项目创建，完成基础功能搭建
- 解决 PyTorch + PyQt6 DLL 冲突（torch 必须先于 PyQt6 导入）
- 解决 manga-ocr 模型下载（设置 HF_ENDPOINT 镜像）
- 解决 TTS 播放崩溃（从 pygame 迁移到 Qt QMediaPlayer）
- 解决 qwen3-vl:30b thinking 模式占用 token 导致输出为空的问题
- 切换默认模型为 deepseek-v3.1:671b-cloud（速度快、质量高）
- 优化 prompt：去除多余开场白/结尾、词解不重复写读音
