# 南枫下载项目入口

- 接手先读 `docs/PROJECT_STATUS.md` 和 `CURRENT_HANDOFF.md`；本目录为 Windows 项目。
- 发布唯一流程见 `docs/RELEASING.md`。GitHub Windows 云构建与上传入口须先通过候选包验证；不再用 HEAD 连通性代替吞吐测试、反复中断大文件上传。
- 安装器正文在 `packaging/windows/NanfengDownloader.iss`，后台关闭边界由同目录 `close_running_app.ps1` 拥有；常规安装选项默认勾选，完整简体中文。
- 每次修改提供现有 `启动南枫下载.bat`；`发布准备.bat` 仅预览发布计划，不会直接发布。
