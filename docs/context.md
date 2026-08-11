# 南枫下载：当前项目上下文

> 最后整理：2026-08-11
> 适用范围：`D:\CodexProjects\NanfengDownloader-Windows` 的 Windows 桌面版。
> 接手顺序：先读本文，再读 `AGENTS.md`（如存在）、`README.md`、相关代码和测试；以当前代码为准。

## 1. 产品边界

**南枫下载**是面向个人工作流的 PySide6 桌面视频下载工具，当前 Windows 开发版覆盖抖音、YouTube、哔哩哔哩、小红书和 TikTok 的单条、作者页/频道页、作品列表读取与勾选下载。

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
| 测试 | Python `unittest`，`tests/` 下 68 项回归测试 |
| 发布 | 私有 GitHub 仓库与 GitHub Release |

## 3. 目录结构与职责

```text
CleanVideoDownloader/
├─ app/
│  ├─ main.py                  # 主窗口、队列 UI、线程调度、默认路径与交互
│  ├─ windows_shell.py         # Windows 资源管理器精确选中文件
│  ├─ downloader.py            # yt-dlp 下载参数、速度/重试、进度回调、文件命名
│  ├─ catalog.py               # 单条/作者/频道/播放列表识别与作品清单读取
│  ├─ douyin.py                # 抖音短链、作品页与浏览器嗅探兜底
│  ├─ bilibili.py              # B站视频、UP 主空间、412 浏览器回退
│  ├─ xiaohongshu.py           # 小红书视频笔记、作者页与真实媒体下载
│  ├─ tiktok.py                # TikTok 单视频、作者页与严格作者归属
│  ├─ auth_profile.py           # 软件内登录资料目录、Cookie 导出与兼容迁移
│  ├─ media_validation.py       # 最终媒体文件有效性校验
│  └─ assets/                  # 图标、下拉箭头等静态资源
├─ tests/
│  ├─ test_douyin_browser_capture.py
│  ├─ test_downloader_speed.py
│  ├─ test_youtube_auth.py
│  └─ test_bilibili_xiaohongshu_support.py
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

### 哔哩哔哩与小红书规则

- 哔哩哔哩单视频、同一 BV 下的多 P 选集和可读取的合集使用 yt-dlp；多 P 会保留 `?p=N` 并展开为独立队列项，下载文件以 `P01 / P02...` 前缀防止长标题截断后重名；UP 主空间接口触发 HTTP 412 时，浏览器回退只收集当前空间中的真实 BV 视频链接。
- 小红书单视频从当前笔记页状态读取真实视频流；作者页只接收 `user_posted` 返回且具有真实 `note_id` 的视频笔记。
- 小红书图文笔记不会加入视频队列；作者页匿名状态隐藏作品 ID 时，必须提示登录，不能以推荐内容或封面凑数。
- 五个平台使用彼此独立的软件内浏览器资料目录，登录窗口均由独立进程维护。

### TikTok 与 Mac 抖音分享文本规则

- Mac/移动端抖音分享文案只要包含有效 `v.douyin.com` 短链，就应提取并解析为单个抖音作品，不要求用户手工裁剪文案。
- TikTok 单视频只返回一项；作者主页只保留该 `@handle` 的作品，不能混入推荐作者。
- TikTok 复用统一分辨率、停止、媒体校验、作者目录、命名和逐行定位合同；登录状态使用独立 `tiktok` 浏览器资料目录。

## 5. 已验证状态

以下为截至 2026-08-11 的最近验证，不应被理解为对所有平台、所有网络和所有内容的永久保证。

- **已实现且单元测试通过**：68 项 `unittest` 回归测试，覆盖五平台识别、B站作者过滤与多 P 展开、小红书视频笔记解析与断点续传、Mac 抖音分享文本、TikTok 短链/作者过滤与独立登录、5个平台侧栏与登录按钮图标、登录边界提示、抖音浏览器嗅探等待、抖音连接重试与 HTTP Range 断点续传、下载速度参数、分辨率选择、YouTube 登录/公开重试、媒体完整性、停止、执行时勾选、网络恢复、逐行精确定位输出文件、定位长文件名时窗口尺寸稳定，以及链接输入框独立清空。
- **已构建且启动验证**：Windows PyInstaller 包可启动；成品内确认存在 FFmpeg、Node.js、PO Provider 构建文件。
- **当前发布版本**：`v2026.08.10-windows`，修复逐行定位长文件名时主窗口自动横向扩张的问题。
- **当前源码未发布修复**：抖音直连下载新增最多 8 次有限重试、提前结束断点续传和 Range 忽略时安全重下；同一失败作品真实下载经历 4 次连接中断后成功，并通过全数据包扫描。详见 `docs/verification/douyin-resume-regression-20260811.md`。
- **真实服务基线已建立**：YouTube/抖音单视频实际下载和 ffprobe 验证通过，YouTube 频道与抖音作者目录语义通过；详见 `docs/verification/windows-real-regression-20260718.md`。
- **新增平台真实验证**：B站和小红书各完成一个长视频、一个短视频的实际下载，均通过 FFprobe 和 FFmpeg 全数据包扫描；B站 UP 主空间浏览器回退已读取同一主体作品。小红书作者列表仍需在软件内完成登录后做最终真实验收；详见 `docs/verification/bilibili-xiaohongshu-regression-20260726.md`。
- **TikTok 与 Mac 抖音输入验证**：TikTok 作者页严格同主体，34 秒和 63 秒长短视频均完成实际下载及媒体扫描；Mac 抖音完整分享文案成功解析为单作品。详见 `docs/verification/tiktok-mac-douyin-regression-20260801.md`。

最新 Windows 发布包：

- GitHub Release：<https://github.com/nanzhufeng/NanfengDownloader-Windows/releases/tag/v2026.08.10-windows>
- 资产：`NanfengDownloader-Windows-v2026.08.10-Setup.exe`
- SHA-256：`980CCD9A0B4CA21AB26FD7599DFB3AF49A1E36F928E1E8DB0372270B29FC04EF`

## 6. Git 与发布边界

- 当前源码根目录历史混入 Android 相关工作，且工作区长期可能处于 dirty 状态；**不要直接把该根目录推送到 Windows 发布仓库**。
- Windows 发布使用独立仓库：`D:\CodexProjects\NanfengDownloader-Windows`。
- 当前 Release 标签：`v2026.08.10-windows`。
- Windows 发布仓库：<https://github.com/nanzhufeng/NanfengDownloader-Windows>（私有）。
- 每次发布：运行测试 → PyInstaller 清洁构建 → 默认用 Inno Setup 7 x64 生成 `*-Windows-*-Setup.exe` → 静默安装、依赖、启动和卸载验证 → 计算 SHA-256 → 提交并推送 Windows 源码 → 创建 Release → 核对远端大小和摘要 → 新资产确认后再删除旧 Release。Inno Setup 6 只作为兼容回退。

## 7. 待处理与风险

1. **扩大真实下载矩阵**：五平台公开单条均已有实现，B站/小红书/TikTok 已完成长短视频矩阵；1080p、最佳画质、MP3、真实断网恢复和 GUI 大文件停止仍需按版本里程碑抽查。
2. **YouTube 风控边界**：即使附带 PO Provider，YouTube 仍可能基于网络/IP/账号行为要求登录或拦截；不能承诺任意公开视频永远免登录。
3. **Mac 版**：脚本和 spec 已随名称更新，但 `.app` 只能在 Mac 本机构建、签名和验证；Windows 不能替代该验证。
4. **Android 版**：`docs/superpowers/` 与 `android/` 是独立移动端工作流，不应混入 Windows 发行仓库；其规划或截图不代表 Windows 已实现能力。
5. **小红书作者页登录验证**：匿名页面会隐藏作者作品 ID；当前代码已提供独立登录与严格筛选，但仍需用户完成一次软件内登录后验证真实作者批量列表。

## 8. 下一位开发者的最小接手流程

```powershell
cd D:\CodexProjects\NanfengDownloader-Windows
python -m unittest discover -s tests -v
python -m compileall -q app tests
python start.py
```

开始改动前，先确认：当前需求属于 Windows 桌面版、Mac 版还是 Android 版；再只读取对应代码与文档。若涉及发布，先检查当前源码 Git 状态和 staging 仓库状态，不得清理、重置或覆盖用户已有改动。

## 9. 开发经验与复盘入口

当前项目的正式经验审计、证据矩阵、失败经验和下一轮回归门槛见 [app-development-experience-audit.md](app-development-experience-audit.md)。本文负责“当前事实”，经验审计负责“证据如何转化为项目规则与跨项目方法”，两者不重复维护同一正文。
