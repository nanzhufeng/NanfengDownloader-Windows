# Windows v2026.10.16 交付验收

2026-10-16；Windows x64；安装包已冻结，后续仅更新发布资料。

- 改动：删除操作流程文字前的四个图标及占位；博主列点击复制完整名称；下载队列横纵滚动条改为无箭头、无线框的圆角灰色滑块。
- 文件：D:\ReleaseUpload\NanfengDownloader\NanfengDownloader-Windows-v2026.10.16-Setup.exe；157124878 字节；产品版本 2026.10.16，文件版本 2026.10.16.0。
- 源码：205 项完整 unittest 通过（15.185 秒）；compileall、限定 diff 检查通过。侧栏与单行列表定向回归通过；Qt 点击博主／标题／链接验证完整复制及提示，仅 mock 系统剪贴板边界。
- 滚动交互：Windows 原生验证无端部箭头、14px 控件、拖动、滚轮、Ctrl+End／Ctrl+Home 首尾行导航及横向滚动；本地实际截图检查通过。
- 构建：复用固定 build／dist；PyInstaller 与 Inno Setup 7 x64 成功，安装器压缩 109.344 秒。构建前 C 盘空余 28.10 GB，D 盘 187.19 GB。
- 冻结程序：独立临时配置和登录资料；原生窗口标题与 WM_NULL 响应通过，无外来 icuuc.dll。随包 aria2 1.37.0、FFmpeg n4.4.3-20221024、Node v24.15.0 可执行。
- README 三张预览来自当前冻结 EXE：主工作台 1820×1000、设置 760×620、下拉 444×212；14 条合成示例展示新侧栏与滚动条，未启动下载，无真实登录资料。
- 发布结构合同：14 项通过，0 项失败。
- 签名：程序与安装包均为 NotSigned，按 Windows 默认未签名规则发布。
- 安装／卸载：本版 NOT RUN。前次同类验收被自动批准审查拦截，本轮未换方式绕过；不把冻结启动或前版证据算作本版安装验收。
- 源码标签：v2026.10.16-windows，准确指向 cd35f5f6bd91938c91a886dcdf1004bb59c3c87e；后续仅发布终态记录。
- GitHub：2026-10-16 10:15:48 +08:00 正式发布，draft=false、prerelease=false，已为 latest；唯一 Setup EXE 为 uploaded，157124878 字节。10:16 从 GitHub 重新下载，与原始冻结收据及本地文件完全一致；下载文件版本 2026.10.16、NotSigned。
- 上传过程：代理通道中途 EOF，核实无残留附件后改为进程级临时清空代理的直连重传，最终成功；环境在 finally 中恢复。未重建安装包、未变更版本标签。
- 下载：[v2026.10.16-windows](https://github.com/nanzhufeng/NanfengDownloader-Windows/releases/tag/v2026.10.16-windows)；只附 Setup EXE，不附展示图或 SHA-256。

未覆盖用户现用安装目录，未清理下载或登录数据。外部平台实际下载、BT 公网、多 DPI／读屏仍待验收。旧版本冻结产物与证据不覆盖；前次中断编译残留见 windows-installer-release-20261012-1.md。
