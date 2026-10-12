# 当前交接

2026-10-12 19:04 +08:00；D:\CodexProjects\NanfengDownloader-Windows。

用户已授权“打包上传 GitHub”。准备发布正式 Windows 修订版 v2026.10.12.1-windows，默认未签名、Release 不附 SHA-256，附件只放 Setup EXE。

## 终态本地证据

- 冻结安装包：D:\ReleaseUpload\NanfengDownloader\NanfengDownloader-Windows-v2026.10.12.1-Setup.exe；157127469 字节，NotSigned；不再重新生成该文件。
- 204 项完整测试（15.231 秒）；PyInstaller 与 Inno Setup 7 成功；隔离配置、冻结窗口响应、aria2／FFmpeg／Node 均通过。
- 当前 EXE 生成了三个脱敏真实运行页面；README 已更新。真实主窗样式下最后选项裁切在本轮发布 QA 发现并修复；新增回归后重建，最终截图五项全可见。
- scripts/verify_windows_startup.ps1 为 UTF-8 BOM，兼容 PowerShell 5；隐藏窗口用本次进程 HWND／WM_NULL 检查响应，配置与登录数据独立临时目录。
- 安装／卸载验收命令被自动批准审查拒绝，只返回 blocked by policy。未执行、不绕过；不能以旧版安装证明本版已安装。
- docs/verification/windows-installer-release-20261012-1.md 是本版证据；旧智能读取与合同审计保留原日期。

## 当前工作

尚待提交 main、创建独立标签、上传安装包、核对远端元数据并下载比对；最终更新状态资料。冻结产物不再变化，发布资料允许收尾。

原运行窗口不会热加载更新；当前源码入口为 启动南枫下载.bat。未覆盖现用安装目录，也未清理用户下载／登录数据。外部平台实际媒体下载、BT 公网、多 DPI／读屏仍未重新验收。
