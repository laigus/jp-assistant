# 项目架构

耗耗语言助手是 Windows 桌面多语言学习助手，目前支持日语和英语，主流程为：

```text
学习语言 → 屏幕框选/输入 → OCR → 文本编辑 → 翻译与语法解析 → Markdown 展示 → 朗读/生词本
```

## 模块划分

```text
jp-assistant/
├── main.py                    # 应用入口
├── app_info.py                # 应用名称、版本、Windows 标识和图标路径
├── app_paths.py               # 只读资源、安装位置和用户数据路径
├── build_windows.py           # 构建与离线自检
├── haohao.spec                # PyInstaller 目录式打包与 EXE 元数据
├── requirements-build.txt     # 构建依赖（包含运行依赖）
├── assets/
│   ├── app.png                # 完整仓鼠插画的圆角玻璃效果图，四角透明
│   ├── haohao.ico             # Windows 多尺寸图标
│   └── create_icon.py         # 从原图生成图标
├── core/
│   ├── languages.py           # 语言注册表、按语言的 OCR / 音色 / 语速配置
│   ├── ocr.py                 # meikiocr 与 Windows OCR 路由
│   ├── translator.py          # 提供商配置、模型获取、流式解析
│   ├── prompt_manager.py      # 系统 Prompt 与临时指令 Prompt 构造
│   ├── tts.py                 # edge-tts 语音合成
│   └── vocab.py               # 生词本数据
├── ui/
│   ├── main_window.py         # 主窗口与流程编排
│   ├── screenshot.py          # 全屏框选
│   ├── result_window.py       # 详情展示与缩放
│   ├── settings_dialog.py     # 左侧导航、通用设置、统一保存/取消
│   ├── language_settings_page.py # 按语言的 OCR、音色、语速、Prompt 草稿
│   ├── tts_worker.py          # 共享朗读与音色列表 Worker
│   ├── widgets.py             # 深浅主题下保持可见箭头的公共下拉框
│   ├── vocab_window.py        # 生词本界面
│   ├── ui_config.py           # 主题、透明度、窗口状态持久化
│   ├── styles.py              # QSS
│   ├── md_render.py           # Markdown HTML 与正文样式
│   ├── acrylic.py             # Windows Acrylic / DWM
│   ├── glass_base.py          # 玻璃窗口公共绘制
│   └── icons.py               # 主题自适应 SVG 图标
├── tests/                     # 聚焦回归测试
└── models_config.example.json # 模型配置示例
```

## 核心流程

应用身份集中在 `app_info.py`。主窗口、Qt 应用与 EXE 元数据共用名称，应用进程设置独立 AppUserModelID。用户创建的快捷方式直接指向带图标的 EXE，任务栏入口从当前程序创建。`assets/app.png` 保留完整仓鼠插画并加入圆角、凸起玻璃高光与柔和阴影，轮廓外透明；构建时由 `assets/create_icon.py` 校验透明通道并生成多尺寸 ICO。

## 资源与分发

- `app_paths.py` 唯一维护资源和数据位置。只读资源由模块 `__file__` 定位，源码和冻结程序均不依赖工作目录；打包版资源在 `_internal` 中，安装位置由 `sys.executable` 定位。
- 配置、生词本放在 `%LOCALAPPDATA%\HaohaoLanguageAssistant`，异常日志在其中的 `logs\crash.log`。源码与 EXE 共用用户数据；发布包不包含配置、密钥或生词本。
- 音效是内置只读资源，程序启动不向安装目录生成文件。TTS 临时音频保持现有生命周期，结束后清理。
- `haohao.spec` 收集 Qt、ONNX、OpenCV、WinRT 与 Hugging Face 动态模块，写入应用图标及产品版本；`build_windows.py` 构建后运行 `--self-check`，通过后输出完整发布目录，不修改系统快捷方式。
- 构建进程只使用 Python 与 Windows 系统目录的 PATH，避免 IDE 中其他工具的同名 ICU/DLL 混入发布包。修改打包依赖后可加 `--clean` 清理分析缓存。
- 自检模式只检查动态依赖、图标、音效和 Qt 音频初始化，不加载或写入用户数据、不调用在线服务。
- 全局热键通过 QObject 信号投递到 GUI 线程；退出事件循环时注销热键。

## 学习流程

1. 主窗口持有学习语言；`ui/screenshot.py` 获取框选区域，OCR Worker 捕获该语言配置。日语默认使用 meikiocr，并传入检测/识别阈值；英语使用 Windows OCR，要求本机安装对应语言组件。Windows 位图、DataWriter 和线程 COM apartment 在结束时释放。
2. 用户可修正 OCR 文本，再由 `PromptManager` 按学习语言组装解析 Prompt：没有临时指令时使用该语言的系统 Prompt；有临时指令时只用语言上下文、待解释文本与临时指令，不叠加系统 Prompt。
3. `GrammarAnalyzer` 按当前提供商调用 Ollama 或 OpenAI 兼容接口，并把流式增量送回界面。
4. `ui/md_render.py` 把解析结果渲染到主窗口和详情窗口；内容更新时保留详情窗口缩放比例。
5. `core/tts.py` 继续通过 Edge TTS 生成语音，Worker 捕获音色与语速。语音缓存键包含文本、语言、音色和语速，生词内容由 `core/vocab.py` 持久化。

语音合成、试听和音色列表共用 `core/tts.py` 的代理选择：通过标准库读取环境变量或 Windows 系统代理，遵守目标主机的代理绕过规则；对 WebSocket 显式传递代理，按 WSS、HTTPS、HTTP、HTTP 类型 ALL 的顺序选择。代理地址不写入项目配置，TLS 证书校验保持开启。短暂连接错误或超时等待 0.5 秒后重试一次；证书、TLS、认证或参数错误直接反馈。重试创建新的单次 `Communicate` 对象并覆盖不完整音频，最终失败时删除该音频；`ui/tts_worker.py` 将连接、超时、代理认证与 TLS 错误转换为统一中文提示。试听每次重新合成，不使用主窗口或生词本的播放缓存。

临时指令由主窗口持有。它在当前文本的重复解析中持续生效，仅在 OCR 成功识别到下一段非空文本后清空；解析、停止解析、OCR 失败和空识别结果都不会提前清空。

## 设置与语言边界

- 通用设置全局共享：API 提供商、分析模型、主题、透明度、Acrylic 和提示音。
- 主窗口以横排、互斥的语言图标按钮选择学习语言，启动时恢复已保存的选择；重复点击当前语言不重置内容。图标由 `ui/icons.py` 维护（未配置专用图标时使用地球图标），选中、悬停和焦点样式集中在 `ui/styles.py`，主题切换同步刷新。设置页的配置语言仍使用下拉框。
- 语言注册表集中维护显示名称、默认 OCR、locale、音色及输入示例；默认 Prompt 按语言维护在 `core/prompt_manager.py`。新增语言时补齐注册项和默认 Prompt，并核对其 OCR 与音色能力，不复制窗口或流程。
- 用户数据目录中的 `languages.json` 保存当前学习语言与各语言 OCR、音色、语速；`prompts.json` 保存按语言的 Prompt。界面与解释语言保持中文。
- 设置的配置语言仅决定当前编辑对象，不改变主窗口学习语言。页面切换与语言切换保留草稿，API 与语言设置的草稿不修改运行中的配置，保存前验证所有语言；保存统一生效，取消放弃未保存草稿。
- 主窗口的上下文版本标识隔离旧 OCR、解析与 TTS 回调。切换学习语言清空文本、临时指令、解析和语音缓存；保存设置使未完成回调失效但保留已显示的原文和解析。分析 Worker 使用自己的模型调用对象，后续保存设置不会修改正在运行的调用。
- 生词条目保存语言及音频使用的音色/语速，按语言和原句去重。查看历史条目时按条目语言获取当前配置；音色或语速变化后重新生成音频。原文编辑后不把另一段文本的解析一起存入生词本。

## 模型提供商

- 内置提供商为 Ollama 和 DeepSeek；设置页还可新增、删除多个 OpenAI 兼容提供商。
- API URL 可填写服务根地址、版本化根地址或完整 `chat/completions` 地址，由 `core/translator.py` 统一生成聊天与模型端点。
- Ollama 通过 `/api/tags` 获取模型；OpenAI 兼容提供商通过 `/models` 获取模型。
- 获取成功后，接口返回列表完整替换该提供商的旧列表，不混入已经失效的本地模型项；当前模型不在新列表时选择第一项。
- 模型选择框保持可编辑，自动获取后仍可手动输入模型 ID。
- 提供商、URL、密钥、模型列表和当前模型保存在用户数据目录的 `models_config.json`。

## 线程与资源约束

- OCR、LLM、TTS、试听、音色列表和模型列表请求不得阻塞 UI 线程。
- Worker 结束后由统一清理流程释放。
- 主窗口关闭时取消解析并等待后台任务的结束信号，不提前销毁运行中的 QThread 或删除仍在生成的音频；试听关闭后忽略迟到回调并清理临时音频。
- 流式 HTTP response 无论成功、取消或异常都必须关闭，避免后续请求挂起。
- 主题切换后同步刷新 QSS、图标、Markdown HTML 和 Acrylic 效果。
- 用户数据目录只存运行时内容，不存开发验证产物；`build/` 与 `dist/` 是 Git 忽略的构建输出。

## 文档边界

- 用户功能、安装与操作见 [README](../README.md)。
- 源码调试与构建见 [development](development.md)。
- 尚未完成的工作见 [roadmap](roadmap.md)。
