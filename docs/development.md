# 源码调试与 Windows 构建

普通用户使用发布目录中的 EXE；本页仅用于开发与发布。

## 开发环境

Windows 10/11，Python 3.10+。在项目根目录执行：

```powershell
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\python.exe main.py
```

源码调试与打包版共用 `%LOCALAPPDATA%\HaohaoLanguageAssistant`，运行前注意当前用户配置。业务模块只使用 `app_paths.py` 提供的路径，不向源码或安装目录写入用户数据。

## 构建发布目录

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-build.txt
.venv\Scripts\python.exe build_windows.py
```

输出目录为 `dist\耗耗语言助手`。必须分发整个目录，包含 EXE 和 `_internal`；不分发 `.venv`、源码、用户配置或构建缓存。

构建脚本从当前仓鼠图片生成 ICO，并写入 EXE 的名称、图标和版本。PyInstaller 目录式包包含 Python、Qt、ONNX、OpenCV 和 WinRT 运行依赖；meikiocr 模型仍使用 Hugging Face 本机缓存，Windows OCR 仍需系统语言组件。

构建进程隔离 PATH，避免 IDE 中其他工具的同名 ICU/DLL 混入发布包；依赖或打包配置变化时可加 `--clean` 清理分析缓存。

`haohao.spec` 在 PyInstaller 6 的隔离 DLL 扫描中将 ONNX Runtime 排在 WinRT 之前，保持与 `main.py` 一致的初始化顺序。此调整临时覆盖内部函数 `find_binary_dependencies`，仅用于 `Analysis`，无论成功或失败都会恢复；升级 PyInstaller 时需检查函数签名及扫描行为，并重新构建验证。

截图回归测试覆盖 100%、125%、150%、200% 缩放、带负坐标的副屏、混合缩放跨屏坐标，以及延迟截图的选区固定、取消和异常反馈。坐标测试使用模拟屏幕，真实混合 DPI 多显示器仍需实机验证。

## 自检

打包版的 `--self-check` 检查动态 OCR 模块、图标、音效和 Qt 音频初始化，退出码 0 表示通过。此模式不加载或写入用户配置，也不访问模型或语音服务；它不替代实际 OCR、模型请求或朗读验证。
