# 历史页重设计与原标题

- 源码本地未发布，未构建安装包。手机端参考nanzhufeng/NanfengDownload-Android主分支6d7245ea7b25de601730b7497a21cc516aee3029，HistoryScreen.kt、HistoryFilter.kt、InternalVideoPlayerDialog.kt。
- 最终完整unittest 225项通过，26.183秒；随后新增一项占位修复保护正常标题／其他链接／收藏状态检查，定向回归结果见项目状态。compileall与git diff --check通过。
- 原生Windows Qt Fusion隔离窗口：用户指定作品7696764946419289395重新公网解析得到完整标题和作者“闫闯说车”，通过真实进度回调写入队列／历史，并核对与源标题一致；没有使用磁盘安全文件名推测标题。
- 该作品已有QA成品由内置播放器实际解码，QVideoSink有效帧3840×2160，duration760360毫秒，errorString为空；静音验证，不把截图白色视频子面当作播放失败或播放证据。
- 真实生成10秒H264夹具验证内置播放器暂停、双击继续、进度拖动、音量、倍速、全屏Esc、关闭及重开位置记忆。菜单与筛选通过真实控件和键盘检查；外部应用边界由mock截获，不称系统播放器真实播放通过。
- 视觉核对使用自有Qt窗口grab和菜单截图联系表，没有发布用户桌面图。内部临时证据位于系统TEMP/history-redesign-native-result.json及history-redesign-final-contact.png。
- schema v1→v2旧记录／收藏保留；分享为应用内复制链接面板；报告只来自实际采样。未重验物理多DPI、全部编码器、Windows系统分享或冻结包播放器插件收集。
- 本机当前原生历史库没有截图目标URL对应记录，不能声称旧截图记录已经直接修复；同原链接的旧生成占位会在下一次获取真实下载元数据时更正，正常原标题、文件和收藏不变。
