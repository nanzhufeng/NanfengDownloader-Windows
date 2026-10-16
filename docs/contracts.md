# 当前合同索引与所有权

本文维护当前源码的合同入口与职责。最新用户要求优先；源码、执行测试和实际证据用于核对实现，历史版本记录不重新定义当前行为。当前验证与发布状态只写入 [PROJECT_STATUS.md](PROJECT_STATUS.md)，交接只写入根目录 CURRENT_HANDOFF.md。

## 所有者与验收

| 概念 | 唯一所有者／当前行为 | 验收入口 |
|---|---|---|
| 输入与来源身份 | downloader.split_urls、url_safety；分享文本、多行、短链、纯作品 ID；规范化并去重，拒绝不支持的协议与凭据 URL | test_url_safety、test_torrent_input、test_youtube_auth |
| 智能读取 | catalog.discover_links 协调；平台适配器返回 CatalogItem；与媒体下载严格分开 | [公共下载合同](shared-download-contract.md)、test_catalog_request_contract、test_douyin_catalog_fast_path |
| 列表规范与选择 | catalog_rules 清理导航标题并按 URL 去重；DiscoveryWorker 与 CollectionDialog 统一选择；确认只入队 | test_catalog_rules、test_generic_collection、test_discovery_performance |
| 队列状态 | main.MainWindow；执行前重新检查勾选；每行画质；保存历史可选，关闭保留开关不删除当前列表 | test_queue_persistence、test_download_control |
| 下载历史 | history_store.HistoryStore 独立 SQLite 归档；history_page.HistoryPage 整页导航与查询管理；成功归档、收藏和删除记录不改变成品或队列 | [下载历史合同](download-history.md)、test_download_history |
| 队列呈现 | main.SingleLineItemDelegate；所有列单行显示，长文字末尾省略；原始换行仅在绘制时合并。main.MainWindow 统一处理标题、博主与链接的完整悬浮提示及单击复制 | test_queue_single_line；Qt 点击验证 |
| 队列滚动条 | main.MainWindow._apply_style 限定 DownloadQueueTable；横纵灰色圆角滑块、无端部箭头与外框，保留原生拖动、滚轮及键盘导航 | Windows 原生滚动交互及截图检查 |
| 下载与画质 | DownloadWorker → quality_fallback → 平台下载器；自动识别、1080p／720p／360p 上限、MP3；必要时明确原画质／转码／取消 | test_quality_cap、test_quality_fallback、test_quality_output_identity |
| 输出真实性与去重 | 平台下载器、media_validation；已存在输出须按目标身份与有效媒体判断；未知文件不冒称成功；仅新产物使用实际分辨率命名 | test_media_validation、test_existing_task_output、test_existing_media_deduplication |
| 恢复与停止 | DownloadWorker、downloader、平台传输实现；进度包含真实等待联网、停止、失败等状态；保留续传产物 | test_network_recovery、test_transfer_timeout、test_douyin_download_resilience |
| 登录与凭据 | auth_profile；独立浏览器资料、按平台 DPAPI Cookie 历史、目标平台临时导出与释放；未知站点匿名 | test_youtube_auth、test_audit_followups、test_generic_websites |
| 通用网站 | web_collection、generic_collection、web_media；已识别集合与单条媒体语义分开，不递归全站 | [通用网站合同](generic-download.md)、test_web_collection、test_generic_collection、test_generic_media_integration |
| 本地 BT | torrent、torrent_input；文件选择后一个任务，原路径／续传语义；磁力元数据尚未实现 | [BT 合同](torrent-download.md)、test_torrent、test_torrent_input |
| 桌面交互 | main、combo_box、combo_popup；主窗、设置与选集复用下拉；左侧平台登录，右侧链接与下载设置；下拉在选框下方稳定开关 | test_supported_platform_sidebar、test_combo_toggle |
| 关于与版本 | scripts/release_metadata 生成标签／安装包元数据；main.AboutDialog 使用软件版本、开发时间与 GitHub 信息 | test_release_metadata、test_download_summary_dialog |
| Windows 交付 | build_windows_installer.ps1、release-windows.yml；默认未签名 Setup EXE，不在输出／Release 附加 SHA-256；显式新版本，不覆盖正式历史资产 | test_release_metadata |

跨项目弹窗视觉细节路由用户级 design-apps-with-nanfengji-ui/references/popup-standard.md；本项目采用白色不透明圆角面、透明渐变软阴影、选中勾选和行内反馈，无原生黑边、硬投影和第二层焦点方框。关闭的下拉控件不得监听所有应用事件；弹层按需创建。

## 入口矩阵

- 智能读取、加载更多、分享文本：同一 catalog 协调入口；加载更多扩大列表上限，不改变作品身份。
- 拖入本地种子：torrent_input → 同一选择弹窗 → BT 队列，不进入媒体画质流程。
- 普通媒体队列与 BT 队列：由任务类型选择正确下载器；确认选择均不立即下载。
- 已完成定位、完成提示音、结果提示、自动打开目录、按作者目录：分别服从已有设置与精确任务输出。
- 重启：是否恢复队列由保留列表历史开关决定；重启不能恢复不可序列化线程句柄或假装原下载仍在运行。
- 发布：每次修改提供当前源码 BAT；打包、安装、签名、外部平台与 GitHub 发布分别验收，不把 BAT 启动视为发布完成。

## 已统一的冲突

| 原冲突 | 当前依据与统一结果 |
|---|---|
| 抖音读取先获取媒体地址，再重复下载解析 | 读取只解析作品／作者身份与列表；媒体地址与完整元数据在下载阶段获取。无元数据时明确“下载时解析” |
| 抖音作者 URL 与 HTML 拼接后 ID 含换行 | URL 与 HTML 分源解析；身份不能包含拼接分隔符 |
| 作者 API 结束后仍浏览器重读；浏览器结束包后仍空等 | 合法目标作者 has_more=0 结束采集；缺少明确结束证据才使用有界回退 |
| B站“单作品”与多 P 选集描述矛盾 | 明确 p= 或剧集只读指定项；不带 p 的多 P 页面继续提供分 P 选择 |
| 登录横排、三个主区卡片与新左侧单列冲突 | 旧布局断言已更新；左侧平台登录，主区链接与下载设置两卡 |
| 通用网站一律单条／全局最多 500 与集合实现冲突 | 单条与已识别集合分开；通常列表 500，可加载更多；樱花同作品页读取页面已列出的全部剧集 |
| 当前版本、旧目录、旧作者目录默认值混在接手文档 | context 只保存当前事实与路由；默认按平台，作者目录可选；版本／发布状态指向 PROJECT_STATUS |
| 未签名、不附哈希的用户要求与云发布注释冲突 | 本地构建输出与云 Release 正文不再附加哈希；依赖下载的内部完整性校验保留 |
| 旧 UI 测试复用日常设置 | 默认测试窗口改用 tests/ui_fixtures 的临时 INI 与输出目录；显式恢复测试仍使用自身临时配置 |
| 安装器传入版本可能与软件“关于”版本不同 | 本地与云构建通过 release_metadata --check-source 核对 APP_VERSION，错版在构建前拒绝 |

## 文档分层和维护边界

- 本文与三个专项合同是当前稳定规则；README 是用户入口，context 是开发接手导航。
- docs/releases、docs/release-*、docs/verification、app-development-experience-audit 保存注明日期的历史证据，不能据此声称当前外部平台、安装器或签名已验收。
- 适配器不能自行添加选择弹窗、排队政策或未知站点凭据。界面不能通过加载文字或占位标题判断下载成功。
- 更新规则时同时定位所有者、受影响入口与原始症状测试；先定向验收，再按交付范围扩大验证。
- 当前技术债：主窗口仍较大；平台网络预算与取消机制尚未统一。后续按独立职责增量处理，避免为了整理全面重写已验证传输链路。
