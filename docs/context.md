# 南枫下载：当前项目上下文

> 最后整理：2026-07-18  
> 适用范围：`D:\CodexProjects\江湖工具箱\CleanVideoDownloader` 的 Windows 桌面版。  
> 接手顺序：先读本文，再读 `AGENTS.md`（如存在）、`README.md`、相关代码和测试；以当前代码为准。

## 1. 产品边界

**南枫下载**是面向个人工作流的 PySide6 桌面视频下载工具，当前 Windows 发布范围为抖音和 YouTube 的单条、作者页/频道页、作品列表读取与勾选下载。

- 支持公开内容，以及登录后当前账号本来就有权限访问的内容。
- 不支持会员、付费、DRM、私密内容或任何权限绕过。
- 账号密码不在应用内保存；软件内登录依赖独立浏览器资料目录和 Cookie。
- 当前 Windows 成品名为“南枫下载”；图标保留“南烛枫”字样，属于已确认保留的品牌标识。

## 2. 技术栈

| 层级 | 当前实现 |
|---|---|
| 桌面 UI | Python 3.13 + PySide6 |
| 下载与解析 | `yt-dlp` 2026.7.4 |
| YouTube 兼容 | `bgutil-ytdlp-pot-provider` 1.3.1、`yt-dlp-ejs` 0.8.0、随包 Node.js |
| 浏览器自动化 | Playwright |
| 视频处理 | 随包 FFmpeg |
| 打包 | PyInstaller 6.21.0 one-folder EXE；Inno Setup 7 x64 默认安装器，6 仅兼容回退 |
| 测试 | Python `unittest`，`tests/` 下 39 项回归测试 |
| 发布 | 私有 GitHub 仓库与 GitHub Release |

## 3. 目录结构与职责

```text
CleanVideoDownloader/
├─ app/
│  ├─ main.py                  # 主窗口、队列 UI、线程调度、默认路径与交互
│  ├─ downloader.py            # yt-dlp 下载参数、速度/重试、进度回调、文件命名
│  ├─ catalog.py               # 单条/作者/频道/播放列表识别与作品清单读取
│  ├─ douyin.py                # 抖音短链、作品页与浏览器嗅探兜底
│  ├─ auth_profile.py           # 软件内登录资料目录、Cookie 导出与兼容迁移
│  └─ assets/                  # 图标、下拉箭头等静态资源
├─ tests/
│  ├─ test_douyin_browser_capture.py
│  ├─ test_downloader_speed.py
│  └─ test_youtube_auth.py
├─ docs/
│  ├─ context.md               # 本文：当前接手入口
│  ├─ nanzhufeng-video-downloader-development-context-for-chatgpt.md
│  ├─ verification/            # Android 可行性验证资料，非 Windows 发布事实
│  └─ superpowers/             # Android 设计与计划资料，不能直接当作已实现
├─ start.py                    # 应用入口
├─ run.ps1                     # 开发环境启动入口
├─ 启动南枫下载.bat            # Windows 直接启动脚本
├─ 南枫下载_Windows.spec       # Windows PyInstaller 配置
├─ 安装YouTube兼容组件.bat     # 安装 yt-dlp/PO 兼容依赖的辅助脚本
├─ 启动南枫下载.command        # Mac 测试启动脚本，必须在 Mac 本机验证
├─ 南枫下载_mac.spec           # Mac PyInstaller 配置
├─ 打包Mac版.command           # Mac 打包脚本
└─ dist_new/                   # 本地发布物与独立 Windows staging 仓库，不是产品源码
```

## 4. 关键运行规则

### 名称、路径与登录状态

- 窗口标题：`南枫下载`。
- Windows 默认输出：优先 `D:\南枫下载`；无 D 盘时为 `~/Downloads/南枫下载`。
- 新软件内登录数据目录：`%LOCALAPPDATA%\NanfengDownloader`。
- 兼容旧目录：`%LOCALAPPDATA%\NanzhufengVideoDownloader`。新目录不存在而旧目录存在时，继续使用旧目录，避免用户被迫重新登录。

### 下载与识别

- 单视频链接应只加入该视频，不能自动扩展为作者/频道全部内容。
- 作者页、频道页、播放列表链接才读取作品清单；列表可分页加载、逐项勾选、修改分辨率。
- 只下载执行瞬间仍被勾选的项目；取消勾选不得继续进入下载。
- 已存在且可识别为同一输出的文件应快速跳过，不重复下载。
- 网络中断、限流等临时失败应有重试或等待网络恢复策略；登录/权限/验证码类错误不得伪装成可自动恢复错误。
- 支持按平台/博主生成目录，文件名优先使用发布时间加标题，不附加无意义平台 ID。

### YouTube 特别规则

- 目标是优先支持不登录的公开视频下载；遇到 YouTube 风控或验证码时，只能提示更换网络、稍后重试或登录，不做绕过。
- 随包 Node.js 与 PO Token Provider 用于降低公开视频受限概率；二者必须随 Windows EXE 一同验证。
- `360p`、`720p`、`1080p`、最佳画质、仅音频 MP3 的格式选择逻辑位于 `app/downloader.py`。

## 5. 已验证状态

以下为 2026-07-18 的最近验证，不应被理解为对所有平台、所有网络和所有内容的永久保证。

- **已实现且单元测试通过**：39 项 `unittest` 回归测试，覆盖抖音浏览器嗅探等待、下载速度参数、分辨率选择、YouTube 登录/公开重试、媒体有效性、停止、执行时勾选和网络恢复。
- **已构建且启动验证**：Windows PyInstaller 包可启动；成品内确认存在 FFmpeg、Node.js、PO Provider 构建文件。
- **已发布**：私有仓库 `nanzhufeng/NanfengDownloader-Windows`，发布标签 `v2026.07.19-windows`。
- **真实服务基线已建立**：YouTube/抖音单视频实际下载和 ffprobe 验证通过，YouTube 频道与抖音作者目录语义通过；详见 `docs/verification/windows-real-regression-20260718.md`。

最新 Windows 发布包：

- GitHub Release：<https://github.com/nanzhufeng/NanfengDownloader-Windows/releases/tag/v2026.07.19-windows>
- 资产：`NanfengDownloader-Windows-v2026.07.19-Setup.exe`
- SHA-256：`809272629DAE697097B41BAD1F54ED66E720E7B7CBF3BE15949DD41FEC791A55`
- SHA-256：`4E1E170B0301131412B660B7B3CB572DC77177FAC3A40C28706AD1AB4E235355`

## 6. Git 与发布边界

- 当前源码根目录历史混入 Android 相关工作，且工作区长期可能处于 dirty 状态；**不要直接把该根目录推送到 Windows 发布仓库**。
- Windows 发布使用独立仓库：`D:\CodexProjects\NanfengDownloader-Windows`。
- 当前 Release 标签：`v2026.07.19-windows`。
- Windows 发布仓库：<https://github.com/nanzhufeng/NanfengDownloader-Windows>（私有）。
- 每次发布：运行测试 → PyInstaller 清洁构建 → 默认用 Inno Setup 7 x64 生成 `*-Windows-*-Setup.exe` → 静默安装、依赖、启动和卸载验证 → 计算 SHA-256 → 提交并推送 Windows 源码 → 创建 Release → 核对远端大小和摘要 → 新资产确认后再删除旧 Release。Inno Setup 6 只作为兼容回退。

## 7. 待处理与风险

1. **扩大真实下载矩阵**：当前已验证两平台单条、作者/频道目录与 360p；1080p、最佳画质、MP3、真实断网恢复和 GUI 大文件停止仍需按版本里程碑抽查。
2. **YouTube 风控边界**：即使附带 PO Provider，YouTube 仍可能基于网络/IP/账号行为要求登录或拦截；不能承诺任意公开视频永远免登录。
3. **Mac 版**：脚本和 spec 已随名称更新，但 `.app` 只能在 Mac 本机构建、签名和验证；Windows 不能替代该验证。
4. **Android 版**：`docs/superpowers/` 与 `android/` 是独立移动端工作流，不应混入 Windows 发行仓库；其规划或截图不代表 Windows 已实现能力。
5. **Git 卫生**：Windows 独立源码由 `scripts/export_windows_source.py` 导出到 `D:\CodexProjects\NanfengDownloader-Windows`；后续 Windows 开发与发布应迁入该仓库，混合根目录仅保留历史与跨平台资料。

## 8. 下一位开发者的最小接手流程

```powershell
cd D:\CodexProjects\江湖工具箱\CleanVideoDownloader
python -m unittest discover -s tests -v
python -m compileall -q app tests
python start.py
```

开始改动前，先确认：当前需求属于 Windows 桌面版、Mac 版还是 Android 版；再只读取对应代码与文档。若涉及发布，先检查当前源码 Git 状态和 staging 仓库状态，不得清理、重置或覆盖用户已有改动。

## 9. 开发经验与复盘入口

当前项目的正式经验审计、证据矩阵、失败经验和下一轮回归门槛见 [app-development-experience-audit.md](app-development-experience-audit.md)。本文负责“当前事实”，经验审计负责“证据如何转化为项目规则与跨项目方法”，两者不重复维护同一正文。
