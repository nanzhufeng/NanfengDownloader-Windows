# 南枫下载：当前项目上下文

> 最后整理：2026-08-21
>
> 适用范围：本仓库 `D:\CodexProjects\NanfengDownloader-Windows` 的 Windows 桌面版。
> 接手顺序：先读本文、`AGENTS.md`（如存在）、`README.md`、相关代码与测试；以当前代码为准。

## 产品与边界

南枫下载是面向个人工作流的 Windows 桌面视频下载工具，支持抖音、YouTube、哔哩哔哩、小红书和 TikTok 的单视频、作者/频道/UP 主链接读取、勾选和下载。

- 支持公开内容，以及当前账号本来就有权限访问的登录后内容。
- 不支持会员、付费、DRM、私密内容或任何权限绕过。
- 不在应用内保存账号密码；软件内登录使用各平台独立的浏览器资料和 Cookie 文件。
- 产品名为“南枫下载”；图标中“南烛枫”字样是已确认保留的品牌标识。

## 技术栈

| 层级 | 当前实现 |
|---|---|
| UI | Python 3.13、PySide6 6.11.1 |
| 下载与解析 | yt-dlp 2026.7.4、Playwright 1.61.0 |
| YouTube 兼容 | bgutil-ytdlp-pot-provider 1.3.1、yt-dlp-ejs 0.8.0、随包 Node.js |
| 媒体处理 | 随包 FFmpeg / FFprobe |
| 打包 | PyInstaller 6.21.0 onedir；Inno Setup 7 x64 默认，6 仅兼容回退 |
| 测试 | Python `unittest`；依赖版本见 `requirements*.txt` |

## 目录职责

```text
NanfengDownloader-Windows/
├─ app/                         # UI、平台解析、下载、登录资料、媒体校验
├─ tests/                       # 行为与发布合同回归测试
├─ scripts/                     # 真实回归、版本元数据、构建辅助脚本
├─ packaging/windows/           # Inno Setup 安装器配置
├─ .github/workflows/           # Windows Release 工作流
├─ docs/                        # 当前上下文、验证记录、版本说明
├─ 南枫下载_Windows.spec        # PyInstaller Windows 配置
├─ requirements.txt             # 运行时精确依赖
└─ requirements-build.txt       # 打包依赖
```

## 关键运行规则

- 单视频 URL 只能下载当前视频；作者页、频道页、播放列表才读取集合。
- 每个队列项在执行前重新检查勾选状态；停止会传到 yt-dlp、抖音分块下载和 FFmpeg 子进程。
- 输出按平台/作者归档。快速跳过已有文件时，平台、作者和标题必须同时匹配，不能跨平台误跳过。
- 最终媒体必须通过 ffprobe（可用时再进行 FFmpeg 包扫描）或严格文件头校验；网页、JSON、空文件和伪 MP4 不能标记成功。
- 长视频的 FFmpeg 包扫描超时按体积上调；该规则降低慢盘或大文件的误报，不等于平台下载成功。
- 软件内登录 Cookie 按平台隔离。旧版合并 Cookie 文件仅作迁移兼容，正常下载不应使用它。
- YouTube 公共内容优先无登录；平台仍可按网络、IP 或账号行为要求验证，不能承诺永久免登录。

## 已验证基线

- 当前 Windows Release：`v2026.08.21-windows`，资产及 SHA-256 见 [README](../README.md)。
- 当前发布已验证 PyInstaller、Inno Setup 7 x64、随包 Node.js、FFmpeg、安装、启动和卸载；详见 `docs/verification/windows-installer-release-20260821.md`。
- 五平台功能的真实服务验证按各自验证文档记录；外部平台、网络、地区和账号限制必须独立报告，不能由单元测试替代。
- 当前源码的自动测试、编译检查和构建须由接手者在变更后重新执行，不能沿用旧 Release 的结果。

## 发布规则

- GitHub Windows 发布使用本独立仓库：<https://github.com/nanzhufeng/NanfengDownloader-Windows>。
- 本地构建必须通过 `scripts/build_windows_installer.ps1 -Version YYYY.MM.DD` 显式提供新版本。
- GitHub Actions 只接受新的 `vYYYY.MM.DD-windows` 标签；已存在的标签会失败，不会覆盖历史 Release 或资产。
- 默认资产是 Inno Setup 7 x64 生成的 `NanfengDownloader-Windows-vYYYY.MM.DD-Setup.exe`。
- 上传前验证：自动测试、PyInstaller、安装器、静默安装、随包运行时、启动、卸载、SHA-256；GitHub README 保留干净当前界面预览，Release 正文保持简洁且不重复上传预览图。
- 仍未购买商业代码签名证书，Windows SmartScreen 可能显示“未知发布者”。

## 当前待处理边界

1. 仍需按版本抽查真实断网恢复、GUI 超大文件停止、1080p/最佳画质/MP3 及登录后权限内容。
2. 平台真实下载结果受服务端策略影响；失败应保留平台、阶段和可执行中文提示，不能伪称本地已修复。
3. GitHub 分支保护与仓库安全告警属于远端设置，需要用户明确授权后单独配置。
4. 旧混合仓库仅作历史来源，不应再用于 Windows 打包或发布。

## 最小接手命令

```powershell
cd D:\CodexProjects\NanfengDownloader-Windows
python -m unittest discover -s tests -v
python -m compileall -q app tests scripts
python start.py
```

涉及发布时，先确认工作区状态与版本号，再执行构建；不要清理、重置或覆盖用户已有改动。
