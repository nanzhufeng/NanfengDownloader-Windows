# 南枫下载：当前开发入口

当前稳定行为以 [合同索引](contracts.md) 及其专项合同为准；当前版本、验证与发布边界以 [PROJECT_STATUS.md](PROJECT_STATUS.md) 为准。根目录 CURRENT_HANDOFF.md 保存恢复细节。历史 Release 和验收记录只证明其注明的版本。

## 产品与授权边界

Windows 桌面批量媒体工作台，支持抖音、YouTube、哔哩哔哩、小红书、TikTok、Pornhub，以及有界通用网站媒体／集合读取和本地种子任务。公开内容及当前账号有权访问的内容可用，不绕过付费、会员、DRM、私密内容或平台访问控制；不保存账号密码。

## 实际实现所有权

- app/main.py：主窗、线程、队列、设置与关于；combo_box.py：共享下拉行为与定位；combo_popup.py：共享表面、行反馈与软阴影。
- app/catalog.py、各平台适配器、catalog_rules.py：读取来源与目录；collection_dialog.py：统一选择，确认只入队。
- app/downloader.py、douyin.py、xiaohongshu.py、web_media.py：媒体获取；quality_fallback.py：画质选择／转码；media_validation.py：有效产物。
- app/auth_profile.py：独立浏览器资料、按平台 DPAPI Cookie 快照与临时导出生命周期。
- app/torrent.py、torrent_input.py：本地种子读取、文件选择、aria2 传输与续传；不进入视频画质流程。
- scripts/release_metadata.py、build_windows_installer.ps1、packaging/windows、.github/workflows：版本、安装器与发布。

运行时精确依赖只在 requirements.txt 维护，构建依赖见 requirements-build.txt；Node、aria2 和 FFmpeg 为随包工具。不要用文档手抄的旧库版本替代锁定依赖或实际运行证据。

## 开发与本地验证

```powershell
cd D:\CodexProjects\NanfengDownloader-Windows
python -X utf8 -m unittest discover -s tests -q
python -m compileall -q app tests scripts
```

每次修改默认提供根目录“启动南枫下载.bat”，指向当前 start.py。已经运行的 Python 窗口需要正常退出后重开，才能加载修改；不能擅自结束用户下载或丢弃当前队列。

## 当前界面与状态

左侧品牌下方为单列平台登录与操作流程；主区为视频链接、下载设置两卡，路径框保留较宽空间。智能读取和清空链接在输入面右下角。设置为双列灰底卡片；保留历史、提示音、结果提示、自动打开目录及作者文件夹均服从已有设置。布局与状态验收见合同索引中的测试。

默认自动识别画质；默认按平台目录，按作者目录可选。单条与集合、读取与下载、媒体与 BT 必须分别处理。完整目录、成功媒体、当前签名和发布完成都需要各自证据，不能由列表占位标题或测试计数替代。

## Windows 交付

仅从本独立仓库构建。新版本显式使用 YYYY.MM.DD（同日修订可用 YYYY.MM.DD.N），元数据生成 Windows 标签和 Setup EXE 名称；先同步 main.APP_VERSION 与实际开发时间，本地与云构建核对关于版本与发行参数一致。已有正式标签／产物不覆盖，已有草稿按发布脚本恢复。Windows 默认未签名、不附加 SHA-256 输出或 Release 正文；依赖来源固定与内部完整性验证保留。

交付分别检查测试、冻结 EXE、安装／启动／卸载、随包工具、签名真实状态及远端资产；本地源码修改不自动等于 GitHub 版本已更新。更新不强制结束下载任务，卸载不清理下载目录或软件登录资料。安装与公网下载未验证项记录在 PROJECT_STATUS，而非写成永久事实。

历史开发审计见 [2026-07-18 审计](app-development-experience-audit.md)，历史发布与验证见 docs/releases、docs/release-*、docs/verification。
