# TikTok 与 Mac 抖音分享文本验证（2026-08-01）

## 范围

- Mac 端抖音完整分享文案中的 `v.douyin.com` 短链提取与单作品解析。
- TikTok 单视频、作者主页、独立登录入口、作者过滤和长短视频实际下载。
- 复用现有分辨率、停止、作者目录、命名、媒体校验和逐行定位合同。

## 自动验证

- `python -m unittest discover -s tests -v`：60 项通过。
- `python -m compileall -q app tests scripts`：通过。
- `git diff --check`：通过，仅有 Git 的 LF/CRLF 工作区提示。
- 新增合同覆盖：Mac 抖音分享文本、TikTok 平台识别、独立登录资料、作者严格过滤、第五个同宽登录按钮且不移动原输入区域。

## 真实服务验证

### Mac 抖音分享文本

- 输入短链：`https://v.douyin.com/8V9vbgG9Idk/`
- 实际解析：1 条。
- 作品 ID：`7665965733083450660`。
- 作者：`逻辑智能`。
- 发布时间：`2026-07-24`。
- 时长：2493.167 秒。
- 大小：191,065,838 字节。
- 格式：MP4。
- 结果：完整下载完成，并通过 FFprobe 与 FFmpeg 全数据包扫描。

### TikTok 作者与单条

- 作者页：`https://www.tiktok.com/@corgibobaa`
- 前 5 条全部属于 `corgibobaa`，未混入推荐作者。
- 单视频读取：1 条。
- `curl_cffi 0.15.0` 安装后，yt-dlp 不再提示缺少浏览器指纹兼容目标。

### TikTok 短视频

- 链接：`https://www.tiktok.com/@corgibobaa/video/7668895435855039757`
- 时长：34.343 秒。
- 大小：4,464,211 字节。
- 格式：MP4。
- 结果：FFprobe 与 FFmpeg 全数据包扫描通过。

### TikTok 长视频

- 链接：`https://www.tiktok.com/@corgibobaa/video/7653329176426040589`
- 时长：63.634 秒。
- 大小：7,708,335 字节。
- 格式：MP4。
- 结果：FFprobe 与 FFmpeg 全数据包扫描通过。

## 边界

- TikTok 仍可能按地区、网络出口、账号或内容状态限制访问；软件提供独立登录和可执行错误提示，但不会绕过私密、付费或地区权限。
- 公开样本会随平台删除或改变权限，后续发布前应重新选择当前可访问样本。
- 本轮只验证 BAT/源码版，不构建或发布 EXE。
