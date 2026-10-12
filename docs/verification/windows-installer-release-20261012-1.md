# Windows v2026.10.12.1 交付验收

2026-10-12；Windows x64；当前安装包已冻结，后续只修改发布资料。

- 文件：D:\ReleaseUpload\NanfengDownloader\NanfengDownloader-Windows-v2026.10.12.1-Setup.exe，157127469 字节；产品版本 2026.10.12.1。
- 完整测试：204 项通过（15.231 秒）；compileall 与限定 diff 检查通过。
- 冻结 EXE：PyInstaller；隔离临时配置／登录资料，原生窗口标题与 WM_NULL 响应通过；没有不应打包的外来 icuuc.dll。
- 界面：主工作台、设置和下拉预览来自该冻结 EXE，合成数据且未开始下载。发布 QA 修复真实主窗样式下最后选项裁切，新增回归；最终五项全可见。
- 随包工具可执行：aria2 1.37.0、FFmpeg n4.4.3-20221024、Node v24.15.0。
- 安装器：Inno Setup 7 x64，编译成功；安装包命名、平台、README 和真实预览合同 14 项通过。
- 签名：程序与安装包均为 NotSigned，按用户 Windows 默认未签名规则发布。
- 安装／卸载：NOT RUN。自动批准审查拦截了包含安装、卸载和元数据恢复的验收命令，只返回 blocked by policy；该命令未执行，不把上版安装结果算作本版通过，也不换调用方式绕过。
- 源码版本／安装版本一致；已修复 PowerShell 5 中文脚本编码，并通过 UTF-8 BOM 与隐藏窗口原生响应探针完成冻结启动验收。该探针只读取本次启动进程的窗口，不控制现用软件。
- 代码基线：09a36af49c6d2de09a84c2dca16ff5bcc05fb233；后续仅发布资料收尾，未重新生成安装包。
- 远端：正式 Release 已公开，draft=false、prerelease=false；发布于 2026-10-12 19:18:31 +08:00。唯一 Setup EXE 状态 uploaded，157127469 字节；从 GitHub 重新下载与冻结本地文件一致，下载包仍为 NotSigned。
- 下载：[v2026.10.12.1-windows](https://github.com/nanzhufeng/NanfengDownloader-Windows/releases/tag/v2026.10.12.1-windows)；Release 未加入展示图片或 SHA-256。
- 缓存回收：自动批准审查也拒绝了删除本轮中断编译临时文件的命令，只返回 blocked by policy。110653444 字节残留仍在 D:\ReleaseUpload\NanfengDownloader\work\2026.10.12.1-1198331e1d8846bca3818b4c8739e30d，正式安装包不在该目录且未受影响。

本轮没有覆盖用户现用安装目录、卸载现用软件或清理下载文件。外部平台实际媒体下载、BT 公网、多 DPI 与读屏仍沿用项目 Gaps，不由测试数量替代。
