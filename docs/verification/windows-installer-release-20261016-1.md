# Windows v2026.10.16.1 正式发布

- 用户授权：打包上传 GitHub。
- 源码：24938f2d69811474148ef5348b1dfef119d704d0，main；v2026.10.16.1-windows 标签指向该提交。后续提交只记录交付与 README 预览。
- 工作流：https://github.com/nanzhufeng/NanfengDownloader-Windows/actions/runs/38847856890，成功，03:54:27Z–04:01:12Z，6 分 45 秒。
- 208 项测试通过（20.744 秒）；PyInstaller、隔离冻结窗口、随包 Node／FFmpeg 和 Inno 编译通过。
- 构建阶段 247.770 秒：PyInstaller 59.049 秒，启动 12.672 秒，Inno 175.898 秒。
- 正式 Release：https://github.com/nanzhufeng/NanfengDownloader-Windows/releases/tag/v2026.10.16.1-windows；draft=false、prerelease=false，latest。
- 唯一附件 NanfengDownloader-Windows-v2026.10.16.1-Setup.exe，uploaded，176759836 字节，实际 Authenticode 为 NotSigned。
- 远端正式附件已独立下载，与同次云 artifact 的安装包字节摘要及服务端 digest 一致。内部收据：D:\ReleaseUpload\NanfengDownloader\receipt-v2026.10.16.1.json；正式文件：该目录 remote-v2026.10.16.1 子目录。
- README 三张图来自该次云构建运行的真实冻结 EXE，脱敏合成数据，未启动媒体下载；没有把预览上传为 Release 附件。
- 本机旧版残留清理及本机热修复包安装证据见 installer-repair-20261016.md；该本机包与云正式包工具链不同，不将本机安装当作云正式包安装通过。云正式包安装／卸载与真实平台下载本轮未重验。
- 前次云候选与本次正式构建应用源码相同，提交差异为交付文档；两次安装包字节并非相同，分别保留收据，不用“只是时间戳”推断可重复构建已达标。内部 PE 差异记录保留于 candidate-vs-release-pe-20261016.json；发布回验只与同一次构建比较。
