# Windows v2026.10.12 交付验收

- 安装包：NanfengDownloader-Windows-v2026.10.12-Setup.exe，157112270 字节。
- 代码基线：c90908f680e79fb9e813025364e8ba4c113162d4；后续收尾只修改发布资料，未重新生成或修改安装包。
- 完整测试：183 项通过。
- Windows 控件：Fusion 主题下，输入区和箭头反复展开/关闭、Esc、选项选择、点击回传通过；按钮聚焦不产生内部第二层框；设置开关和取消通过。
- 构建：PyInstaller 固定缓存构建；Analysis 未发现 Codex 外来 DLL；终态 EXE 标题为“南枫下载”，窗口可响应。
- 安装器：Inno Setup 7 x64；隔离目录安装、运行和卸载退出码为 0；原有开始菜单快捷方式保留。
- 随包工具：aria2 1.37.0、FFmpeg n4.4.3、Node v24.15.0 可执行。
- 签名：程序及安装包均为 NotSigned，按用户 Windows 默认未签名发布规则交付。
- GitHub 草稿资产：仅一个正式命名的 Setup EXE，uploaded；已通过下载回验，远端文件与本地一致。
- 发布目标：[v2026.10.12-windows](https://github.com/nanzhufeng/NanfengDownloader-Windows/releases/tag/v2026.10.12-windows)；公开状态、提交与标签以实时 GitHub/Git 为准。
- 验收边界：未重新运行真实外部平台下载，磁力链接与 BT 公网下载仍未完成真实验收；没有替换用户现用安装目录或清理下载文件。
