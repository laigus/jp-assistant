# 项目协作约定

## 修改原则

- 功能或设计发生变化时，同步梳理代码、README 和 `docs/`，避免实现与说明不一致。
- 以当前工作区为准，保留并继续人工修改；不要用旧版本或记忆覆盖现有内容。
- 除非任务明确要求兼容旧方案，否则删除过时代码、配置和文档，不保留并行旧流程。
- 只执行与改动直接相关的最小验证；临时日志、截图、补丁和回滚材料不要写入项目的 `data/`。

## 代码边界

- `ui/` 放界面与交互，`core/` 放 OCR、模型调用、Prompt、TTS 和生词本等业务逻辑。
- 公共 QSS/HTML 样式集中维护在 `ui/styles.py` 和 `ui/md_render.py`。
- OCR、网络请求、TTS、模型列表获取等阻塞操作使用 `QThread`，通过信号把结果送回 UI 线程。
- 流式 HTTP 响应必须在 `finally` 中关闭。
- `data/` 只存本机运行时配置与用户数据，并保持 Git 忽略。

## 本地命令

- 命令使用项目相对路径，不写死盘符。
- 启动：`.venv\Scripts\python.exe main.py`
- 安装依赖：`uv pip install --python .venv\Scripts\python.exe -r requirements.txt`
- 新增依赖时同步更新 `requirements.txt`；不要在项目规则中固定代理或镜像配置。

## 文档职责

- `README.md`：面向用户的功能、安装和使用说明。
- `docs/architecture.md`：当前模块边界、数据流和关键约束。
- `docs/roadmap.md`：只记录尚未完成且仍有效的事项。
