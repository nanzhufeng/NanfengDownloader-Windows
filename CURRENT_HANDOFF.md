# 当前交接

2026-10-17 v2026.10.17.1已正式发布并回验：用户暂停Cloudflare修复，禁止继续浏览器／Cookie／实站探针。准确源码及发布标签为6f1aed637b23c0732011a8b04f6ae0394e6e72df；云运行39015112646成功，正式latest只有一个Setup附件。本地240测试46.906秒、云端240测试64.384秒、冻结启动／随包工具及14项发布结构检查通过。完整正式下载183693391字节，ProductVersion／FileVersion 2026.10.17.1，实际NotSigned；SHA-256与GitHub资产digest一致。安装包和receipt-v2026.10.17.1.json位于D:/ReleaseUpload/NanfengDownloader/，README采用本次冻结EXE预览；完整证据docs/verification/release-20261017-1.md。未在本机安装／升级／卸载精确包，未下载完整候选ZIP进行第二份EXE哈希比对。不要重建／覆盖正式版本，不把源码绿灯称为CF下载修复。

## 历史诊断与开发记录

2026-10-17 Chrome正常退出后限定检查完成：只读SQL仅本站验证Cookie元数据，1条未过期cf_clearance，前缀v20。未解密／导出值、未发送Cookie、未下载媒体。Chromium官方代码确认v20为App-Bound；当前yt-dlp Windows解密器不支持此读取路线。不得绕过Chrome加密／策略／注入，也不再让用户保持Chrome关闭或重复匿名重试；其Chrome可重新使用。该作品仍未修复。下一步若开发浏览器内授权接口，须区分源码接入与扩展安装／持久授权；后者不能直接沿用此次单站单次Cookie检查许可。首次诊断uri开关已纠正，不混淆前序真实Win32共享锁。收据chrome-site-session-unlocked-check.json，验证说明最终段；无源码、测试、打包变化。

2026-10-17 本站Chrome会话已获用户明确授权：仅xmorex.com验证Cookie、仅当前链接解析，不下载视频。只读SELECT限定本站四个域和cf_clearance／__cf_bm；Cookie数据库打不开，Win32正常只读打开检查返回32共享冲突，Cookie数据实际读取0。用户答“暂时不能退出”，必须保留Chrome运行，不再要求重复授权、不强杀、不复制整库、不绕过文件锁／Chrome加密。当前阻塞为浏览器库不可读；用户日后能正常退出并要求继续时可沿用本站／本次范围授权，再检查加密格式，仍不得承诺会话一定可复用。收据chrome-site-session-scope-check.json；无源码／测试／发布变化，原240测试不是此站绿灯。

2026-10-17 已分析用户保存HTML，无源码改动：178652字节／3207行，正常作品页，主video显式同源HLS且编号与作品一致。HEAD及带Referer有界GET清单均403，GET有cf-mitigated=challenge；媒体分片请求为0。官方download签名入口外层requireLogin，未调用。浏览器能力无Cookie接口，pageAssets.list仍超时，未读Chrome凭据。下一步必须获得用户对仅本站／本次解析复用Chrome验证Cookie的明确授权，再验证能否安全读取；不得读取其他网站、绕过Chrome加密、保存凭据或承诺Cookie一定有效。原始用户HTML留原处，不复制入项目。收据saved-page-source-head.json、saved-page-source-get.json；本次没有可交付的CF下载修复。

2026-10-17 Cloudflare再次诊断，无代码改动：当前运行确为本工作区start.py；系统／Python HTTPS代理配置同为127.0.0.1:7890，不能推断出口或会话一致。新Chrome兼容请求0.332秒仍403且cf-mitigated=challenge。Chrome标签页连接成功，DOM整体及单video属性读取均超时；用户答扩展“没有任何提示”，不得继续把问题归因于未授权。未读取Cookie／资料或开验证窗。缺少最小实站证据：用户现用Chrome保存作品页“网页，仅HTML”，供确认播放器入口；未取得前仍未解决，不改更多重试参数。证据cloudflare-current-route.json和验证说明最新段；前序240测试属于原标题等源码修复，不代表CF下载成功。

2026-10-17 最新原标题纠正：动态网页fallback虽用原网页标题命名文件，但CDN后续info_dict.title覆盖列表／历史。download_url现在在统一进度入口保留已确认source_title，媒体编号不再覆盖；真实Chromium＋本地HTTP＋yt-dlp＋FFmpeg fixture红转绿，实际进度重放Qt历史入口验证原标题，9项定向9.395秒／240项完整回归64.290秒通过。既有用户历史未改写，本次未提交／打包／发布。Cloudflare仍未解决；用户确认Chrome，浏览器清单存在该作品页但只读连接连续超时，未读取Cookie／资料或重开验证窗口。新增tests/test_generic_original_title.py；证据generic-title-final-red.txt、generic-title-green.txt、generic-title-full-tests.txt。当前源码BAT入口不变；下方为前序记录。

2026-10-17 当前本地增量（覆盖下方发布后的源码状态）：main基线a1d1a81之后未提交。用户明确否定独立Cloudflare验证窗口；已关闭本任务窗口并删除site_verification及其入口／测试，不再弹窗。保留有界generic:impersonate兼容重试及失败原标题／瞬态进度修正。第一条实站仍403；第二条作品根因为blob来源未读取绑定播放器配置，app/web_media.py已修复，真实解析3.897秒、1个HLS格式、未下载完整媒体。239项完整回归40.367秒通过；当前源码入口启动南枫下载.bat，未打包发布，不冒称既有v2026.10.17含修复。详见docs/PROJECT_STATUS.md顶部、docs/verification/generic-challenge-20261017.md；脱敏实站收据.verification-downloads/blob-player-live-result.json，测试generic-final-full-tests.txt。后续仅在用户要求时打包／上传。

2026-10-17 发布完成：v2026.10.17-windows为正式latest；源码标签f3e4fca2627d1536d7c459b5489b208f41a2a086，云运行38997384366成功。本地／云端233项测试及14项发布结构检查通过；183696841字节Setup实际NotSigned，正式下载与完整云候选EXE、GitHub摘要一致。README采用当前冻结EXE预览。文件／收据D:/ReleaseUpload/NanfengDownloader/，证据docs/verification/release-20261017.md；未实际安装／升级／卸载精确云包。源码入口启动南枫下载.bat；后续未发布措辞保留为历史记录。

2026-10-17 v2026.10.17发布准备：包含完成下载移入历史和历史操作图标／配色修正；本地233项完整回归41.505秒通过，compileall／diff检查通过。版本说明docs/release-2026.10.17.md；使用scripts/publish_windows_release.ps1 -Publish云构建正式发布，最终收据待完成。此前本地增量条目为历史记录。

2026-10-17 历史管理视觉修正：批量删除红色垃圾桶、清理失效橙色扫帚，图标和文字同色，禁用统一灰色；多分辨率原生图标、圆角反馈保留。10项历史测试及原生状态／图标栅格检查通过，详见PROJECT_STATUS顶部。本地源码尚未提交／打包／上传；之前完成项自动移入历史的改动保留，入口启动南枫下载.bat。

2026-10-17 本地增量：下载成功且历史归档成功后立即从可见／持久化队列移除，批次结束整理内部行；失败、停止、已有文件跳过和未选项保留。混合批次、定位与归档失败重启恢复已补回归。当前修改尚未提交／打包／上传，不覆盖v2026.10.16.2；入口启动南枫下载.bat。验证及边界见docs/verification/completed-queue-retirement-20261017.md与docs/PROJECT_STATUS.md顶部。

2026-10-16 发布闭环完成：v2026.10.16.2-windows为正式latest，源码标签901c2ce734ab71c31add80bd528041f83eaa2038；云端运行38892386641成功。231项完整测试、冻结启动、随包工具、14项发布结构检查通过。183695425字节Setup的正式下载／完整云候选／GitHub摘要一致，实际NotSigned；收据D:/ReleaseUpload/NanfengDownloader/receipt-v2026.10.16.2.json，说明docs/verification/release-20261016-2.md。README采用本版冻结EXE实际预览。未实际安装／卸载精确云包，其他验收边界见说明；版本包已冻结，不重建覆盖。后续记录为开发历史。

2026-10-16 UI响应优化：进度单元格复用及100ms合并总进度、未变化历史卡片复用和排版回调合并已落地；231项完整回归34.777秒通过。隔离性能与边界见docs/verification/ui-responsiveness-20261016.md。未提交／打包／发布，不覆盖既有WIP，入口启动南枫下载.bat。

## 2026-10-16 播放器最新纠正（覆盖前述弹窗形态）
MediaPlayerPage已替代独立QDialog，在HistoryPage.content_stack内打开；没有右侧文字栏，顶层窗口不增加，返回恢复原列表。手机端源码6d7245e直接核对手势与位置存储：左右双击10秒／600ms连续累加／800ms反馈／单击控制栏／2500ms隐藏／350ms缓冲提示；分段及独立书签、同窗全屏、关闭释放均已落地。主要验证见docs/verification/embedded-player-20261016.md。既有WIP未提交、不重置；当前仍未冻结或发布，入口启动南枫下载.bat。

## 2026-10-16 历史页重设计（本地未发布）
历史页灰白工具栏／时间线卡片／三个筛选／三点菜单已参考手机端重做；封面默认使用新增app/media_player.py内置播放器，app/action_popup.py统一圆角菜单。抖音解析info_dict补传完整title／uploader，队列、历史和播放器标题不再被磁盘文件名替换；同链接旧占位可随新元数据补正。schema v2追加真实传输报告，分享是应用内复制链接。详细行为见docs/download-history.md，验证与边界见docs/PROJECT_STATUS.md。全部为未提交WIP，不重置既有改动。入口仍启动南枫下载.bat。

# 当前交接

2026-10-16 抖音性能优化完成：本次下载内复用Cookie恢复结果，16MiB以上支持Range的媒体最多6连接严格分段，错误分段回退原单连接。用户同作品完整实测19.407秒→13.013／9.720秒，首批数据10.061→7.420／6.586秒；2160p和音视频流不变，第二次成品整文件SHA256匹配基线。220项完整测试及随后28项定向通过。收据 `.verification-downloads/douyin-performance/`，仅保留current成品，旧对照媒体已核验回收。其他平台未公网重验，未打包发布；仍需正常退出旧窗口后BAT重启。

2026-10-16 抖音解析后续故障已修复：软件内登录Cookie未缓存时，嗅探内部调用Cookie恢复嵌套Playwright Sync API，匿名成功但软件模式报错。Cookie读取现位于嗅探／作者读取的Sync作用域之前。218项完整测试23.498秒通过；用户作品7696764946419289395真实下载24.92秒，194853146字节、2160p、760.36秒、FFprobe通过，非跳过。仅该单作品公网绿灯，隔离下载与收据在 `.verification-downloads/douyin-parser-fix/`；未改用户现用窗口或下载目录，未打包发布，BAT重启生效。

2026-10-16 下载按钮回归已修复：`_start_downloads` 在 `items_rows` 赋值前使用它导致 UnboundLocalError，任务一直等待；标识创建／持久化已移动到实际下载行筛选之后。test_download_start 实际点击按钮并穿过Qt线程，验证切历史继续、完成归档与按钮恢复；217项完整测试通过，原生Qt链路通过。下载边界受控替代，不冒称用户抖音公网作品已下载。当前源码需正常退出旧窗口后通过BAT重开。

2026-10-16 历史功能已本地落地：设置上方“历史”切换整个右侧，独立SQLite成功归档与旧完成队列未知时间导入；搜索／筛选／视频收藏／详情／系统打开／多文件选择／定位／复制／确认删除／失效清理已接通。216项完整测试24.178秒通过，Windows原生宽窄布局与隔离真实MP4元数据／缩略图通过。细节、数据路径和未验范围见 docs/PROJECT_STATUS.md 顶部、docs/download-history.md。未提交／打包／发布，保留此前全部UI改动；设置功能审阅已删除，关于仓库文字直接链接。当前入口仍为启动南枫下载.bat。

2026-10-16 本地 UI 增量：表头与列表共用 QueueSurface 抗锯齿圆角表面，删除外圈 1px 留白；“打开保存目录”移到操作条最右侧。3 项定向测试与 Windows 原生空队列／60 行滚动队列边缘、按钮几何检查通过。未提交、未打包发布，入口仍为 `启动南枫下载.bat`；详细范围见 `docs/PROJECT_STATUS.md` 顶部。

2026-10-16；D:\CodexProjects\NanfengDownloader-Windows。

v2026.10.16.1 安装修复已本地构建并由用户实际安装：窗口可见、正常响应，桌面快捷方式存在，安装 EXE 与冻结 dist 摘要一致。安装器中文化、默认勾选常规任务、按完整安装路径关闭自有残留。启动前不再调用 Playwright 登录恢复，实际使用时保留历史登录恢复入口。

208 项完整 unittest 通过（18.931 秒）。详细证据 docs/verification/installer-repair-20261016.md。本地包 D:\ReleaseUpload\NanfengDownloader\NanfengDownloader-Windows-v2026.10.16.1-Setup.exe，157116543 字节，NotSigned，不重建覆盖。

发布耗时主要来自本机上行、线路切换和 EOF 重传；统一构建脚本记录阶段用时，默认复用固定缓存。新 GitHub 流程默认只构建候选包，云验证已通过（38846891113，源码 20f2a156cd128a65093a74cc20abf3c359430b89，208 测试 20.824 秒，整个运行 6 分 20 秒）；入口 scripts/publish_windows_release.ps1，发布准备.bat 仅输出只读计划。v2026.10.16.1 已正式发布：运行 38847856890，准确源码 24938f2d69811474148ef5348b1dfef119d704d0，唯一附件 176759836 字节，NotSigned，下载与同次云产物一致；正式包位于 D:\ReleaseUpload\NanfengDownloader\remote-v2026.10.16.1。前述本机包与云端正式包不同，不混用安装证据。既有版本不覆盖。

长期默认规则正文已更新本地产品标准 Skill，记忆说明待系统应用。当前启动入口：启动南枫下载.bat。云端正式包安装／卸载、外部平台真实下载未重验。README 三张图已更新为正式云构建的实际冻结界面。
