# 通用网站媒体与集合合同

所有权和共用选择流程见 [当前合同索引](contracts.md) 与 [公共下载合同](shared-download-contract.md)。本页描述当前源码能力，不自行承诺已打包或所有网站实测成功。

## 单条与集合

- 普通 HTTP/HTTPS 作品页及音视频直链入队后交给 yt-dlp／web_media 解析；不递归任意网页的链接或全站。
- 已识别的播放列表、频道、系列等集合由 generic_collection 使用有界 flat/lazy 提取，通常上限 500；加载更多扩大同一来源上限。仅加入可确认独立 HTTP/HTTPS 作品，不把嵌套集合、凭据 URL、广告或推荐当作品。
- 樱花 /vod/作品ID.html 与 /vod-play/作品ID/ep集数.html 使用 web_collection 专用适配器，从同作品页面已有剧集链接排序读取；页面已列出的完整剧集不机械截断到 500，不额外递归其他剧集页面。
- 多项由共用选择弹窗搜索／勾选，确认只入队；每个被勾选队列项下载时按单条处理，不再次展开整套集合。集合错误明确失败，不悄悄按未知单视频执行。

## 凭据、传输与输出

未知网站匿名，不借用平台 Cookie；yt-dlp 负责站点与网页解析，aria2 负责已发现地址的传输。沿用按站点验证的加速参数，不对所有站点强制同一并发。不绕过登录、付费或 DRM。输出按来源域名与既有命名／有效媒体规则处理，没有准确产物必须失败。

通用媒体能力不保存任意 ZIP/PDF，也不冒充全网浏览器嗅探；本地 .torrent 为独立 BT 功能，磁力元数据尚未实现，见 [BT 合同](torrent-download.md)。

## 验证边界

当前行为回归：test_generic_websites、test_generic_collection、test_web_collection、test_generic_media_integration、test_web_media。历史 HTTP 嵌入视频、W3C 直链及站点样本只证明对应日期与输入；当前全平台公网性能须独立验证，状态见 PROJECT_STATUS。
