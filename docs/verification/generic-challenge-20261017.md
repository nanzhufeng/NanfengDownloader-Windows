# 通用网页验证与blob播放器：本地增量

## 已确认事实

- 当前依赖包含curl-cffi，固定yt-dlp 2026.08.19，Windows spec已collect_all；运行时存在可用impersonate targets。缺少兼容组件不是已证实根因。
- 用户第一条作品普通请求与generic:impersonate均返回Cloudflare403。独立窗口仍停留在验证；用户明确否定该方式后已关闭本任务窗口，移除验证模块、右键入口与配套临时会话流程。不读取用户日常浏览器资料，不再弹验证窗口。
- 用户第二条作品页HTTP200，真实Chromium中可见视频currentSrc为blob，但播放器my_player明确绑定同一media元素，其config.url为HLS清单。旧代码只读取元素currentSrc，丢弃blob后误报未发现播放器。这是本次已复现根因。

## 最终修改

- 明确Cloudflare挑战只追加一次浏览器兼容请求；网页403不走媒体分片并发回退。仍失败即结束当前任务，保留原任务并明确中文原因，无人工验证循环。
- 失败恢复原标题，错误进入状态tooltip与失败详情；清空重连等进行中显示。开始时清除旧错误提示，停止时清除瞬态进度。
- blob来源只从明确拥有当前可见media元素的播放器实例配置读取；来源冲突仍拒绝，不猜测任意网络流量或广告。排除已挂载mediaKeys的元素，不绕过DRM。
- 解析浏览器后台运行，屏蔽图片、字体、媒体预加载和常见分片；播放器初始化最多12秒且可取消。浏览器finally关闭。

## 证据

- 红灯：真实Chromium本地blob夹具复现原错误；同一夹具修复后通过。无关实例和DRM元素被排除，并能取消。
- Cloudflare兼容请求最多两次、取消不追加请求；经过真实开始按钮与Qt线程验证失败保留原标题、不残留重连、不进入历史。该链路不会启动Playwright窗口。
- 用户第二条真实作品实测：2.785秒获得.m3u8，yt-dlp以download=False继续解析成功，合计3.897秒、1个可用格式，未下载完整媒体。脱敏收据.verification-downloads/blob-player-live-result.json。
- 最终完整回归结果见PROJECT_STATUS顶部；原始结果.verification-downloads/generic-final-full-tests.txt。

## 原标题传递纠正（同日后续）

- 用户截图的历史标题为32位媒体编号。已复现：动态网页解析取得原标题，文件命名已使用该标题，但随后CDN提取器的info_dict.title覆盖列表元数据，历史归档因此保存编号。
- 在单任务下载的进度入口保留原网页标题，解析成功立即传递，后续媒体进度和后处理沿用该标题；保留其他格式／时长／传输数据，不修改yt-dlp原始字典。列表、历史和输出命名来源一致。
- 真实Chromium＋本地HTTP＋yt-dlp＋FFmpeg一秒MP4复现同一编号：修复前历史标题断言红灯，修复后真实进度重放至原生Qt元数据／完成入口并归档通过。原生开始按钮／Qt线程由相邻既有回归覆盖；不把重放称完整GUI线程实测。
- 定向9项回归9.395秒通过；最终240项完整回归64.290秒通过。收据.verification-downloads/generic-title-final-red.txt、generic-title-green.txt、generic-title-full-tests.txt。
- 用户确认正常浏览器为Chrome。只读浏览器清单存在该作品页，但目标标签页读取连续超时，未取得可验证的播放器状态；未读取Cookie／主浏览器资料，未重新打开人工验证窗口。现有用户历史未扫描／改写。

## 再次实站诊断（2026-10-17，未改代码）

- 用户再次报告同一作品失败。已核实在运行进程为当前工作区start.py；Windows系统代理与Python HTTPS代理配置均指向127.0.0.1:7890。仅确认配置地址一致，不据此推断实际出口或会话一致。
- 新的Chrome兼容请求0.332秒仍返回HTTP403，cf-mitigated=challenge；未取得作品HTML，也未下载媒体。脱敏证据.verification-downloads/cloudflare-current-route.json。
- Chrome浏览器工具可发现并连接已有作品标签页，但完整页面与单个video属性读取均超时。用户确认扩展没有访问授权提示；不能把超时误判成用户未授权。
- 本轮未修改下载代码、读取浏览器Cookie／资料或重新打开人工验证窗口。下一步缺少的最小证据是现用Chrome已打开作品页保存的“网页，仅HTML”，用于确认播放器入口；收到文件前不能宣称已完成站点适配。

## 用户保存HTML分析（2026-10-17，无源码改动）

- 用户提供178652字节／3207行的正常作品HTML，未执行其中脚本。主video的src明确为同源HLS路径，资源编号与作品编号一致；页面同时有OG标题。已排除“作品页没有明确播放器来源”的假设。
- 对保存页面中实际声明的清单入口做HEAD和带正常Referer的有界GET，均403；GET明确cf-mitigated=challenge且返回HTML，而非HLS。未请求媒体分片，未下载视频。脱敏收据.verification-downloads/saved-page-source-head.json、saved-page-source-get.json。
- 页面代码另有官方签名下载入口，但调用外层显式requireLogin；未调用该入口，也不把它当匿名公共接口。
- 浏览器工具没有Cookie／会话导出能力；页面资源清单读取同样超时。未读取Chrome凭据。本轮结论：确定媒体入口不等于软件已获得访问许可，需在明确授权后另行验证本站现有浏览器会话能否安全复用；不能保证仅Cookie即可解决。

## 本站会话检查授权与文件锁（2026-10-17）

- 用户明确允许只检查／尝试复用Chrome中xmorex.com的验证Cookie，用于当前链接的解析，不下载完整视频。授权仅含本站验证会话，不扩展到其他网站、账号凭据、浏览器保护绕过或持久化保存。
- 唯一匹配的Chrome配置已定位。只读SQL限定四个本站host_key与cf_clearance／__cf_bm两个Cookie名称，数据库无法打开，未返回Cookie值。随后只打开文件而不读取内容，Windows CreateFileW明确返回32（共享冲突），证实浏览器独占锁。
- 用户表示暂时不能正常退出Chrome；保留其浏览器运行，不强制结束、不复制整份Cookie库、不绕过文件锁／浏览器加密。Cookie明文、其他站点Cookie和媒体分片读取均为0。
- 阻塞是浏览器数据库目前不可正常读取，不再是缺少授权。原授权持续有效；可正常读取时再做限定范围检查，但仍不能保证Cookie能解密或通过验证。
- 脱敏证据.verification-downloads/chrome-site-session-scope-check.json。没有新增源码修复／测试／打包，前序240测试不能称本站访问成功。

## Chrome退出后的最终检查（2026-10-17）

- 用户已正常退出Chrome并要求继续；当前未发现Chrome主进程，Cookie库可正常只读访问。
- 严格限定本站四个host_key和cf_clearance／__cf_bm两个验证Cookie名称，仅查询名称、加密前缀／长度和到期时间。结果只有1条cf_clearance，未过期，加密前缀v20；未取得／解密／导出其值，也未将Cookie发送至站点。
- Chromium官方实现将v20定义为App-Bound数据前缀，并启用路径验证保护；本机yt-dlp Windows解密器只为v10提供AES-GCM处理，其他前缀走普通DPAPI，不能据此宣称支持v20。未尝试绕过加密、修改Chrome策略或注入浏览器。
- 初次关闭后的诊断脚本曾遗漏sqlite3 URI开关而无法打开数据库；补上uri=True后正常读取限定元数据。前序Chrome运行时Win32错误32仍是独立确认的共享锁证据，不将脚本参数错误归因于浏览器。
- 普通数据库读取路线已确认不可复用该会话；继续保持Chrome关闭或重复匿名请求没有新增验证价值。后续若要接入，需浏览器内正常授权的会话接口；当前浏览器工具无此能力，不能把API名称／规划当作已实现。新增扩展安装或持久访问需另行明确确认，不沿用本次单站单次检查授权无限扩张。
- 原始HTML保持原处，未下载媒体，未改源码或发布。本次收据.verification-downloads/chrome-site-session-unlocked-check.json。当前作品下载仍未修复。
- 官方证据：https://chromium.googlesource.com/chromium/src.git/+/b8a25f9c8e9fb36450c7d4ca171fabf3d7c0b0b0/chrome/browser/os_crypt/app_bound_encryption_provider_win.cc 。

## Gaps

第一条Cloudflare作品仍未获准访问，不能称该站下载问题已解决。第二条仅确认真实作品解析成功，未下载完整视频。尚未构建／安装／发布本增量，v2026.10.17安装包不含这些修改。
