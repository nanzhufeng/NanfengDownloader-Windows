# QtCore 启动修复（2026-09-10）

## 故障与证据

- 已安装的 2026.09.10 程序启动出现 `Unhandled exception in script`，与用户提供的 QtCore DLL 导入错误一致。
- 原 `Analysis-00.toc` 中，根目录 `icuuc.dll` 来自 Codex runtime 的 Poppler 目录；其他非项目 DLL 也从宿主 PATH 被发现。
- 单变量实验：移开 `ucrtbase.dll` 无效，恢复后仅移开 `icuuc.dll`，同一安装目录的 EXE 即显示“南枫下载”，窗口有响应。
- 新启动检查对旧 DLL 状态返回失败，对移开 ICU 后的同一 EXE 返回成功。

## 修复

- 本地构建脚本将 PATH 限于选定 Python、Scripts 和 Windows 系统目录，并在 finally 恢复原环境。
- 构建完成后必须通过 `scripts/verify_windows_startup.ps1` 才能生成安装包；检查准确窗口标题、响应状态和错误弹窗，结束自己启动的进程。
- Inno Setup 覆盖安装时清除旧包根目录的 `icuuc.dll` 与 `icudt78.dll`，防止旧文件残留遮蔽系统 ICU。
- 使用新版本 `2026.09.10.1`，不覆盖旧安装包。

## 已验证

- 176 项 unittest 全部通过。
- 新 PyInstaller 依赖清单中的 Codex runtime DLL 条目为 0。
- 新 dist EXE 通过真实主窗口启动检查。
- 随包 aria2 1.37.0、Node.js v24.15.0、FFmpeg n4.4.3-20221024 能执行。
- 当前安装目录备份：`D:\ReleaseUpload\NanfengDownloader\installed-backup-20260910`；原始故障 DLL 另存于 `qtcore-backup-20260910`。
- 修复安装包覆盖真实安装目录前，恢复故障 ICU；安装退出码 0，旧 ICU 已移除，安装后 EXE 通过主窗口启动检查。
- 安装包合同检查 14 项通过；文件：`D:\ReleaseUpload\NanfengDownloader\NanfengDownloader-Windows-v2026.09.10.1-Setup.exe`。
- 安装包 SHA-256：`56724967EA7014CFEAD0BDE9CC16ECF0CB9A40AA93E2F2809235CE21B0CA2132`。

本次验证针对启动故障，不代表第三方平台或公网 BT 下载已重新验收；未上传 GitHub。
