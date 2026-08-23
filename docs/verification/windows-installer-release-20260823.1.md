# Windows 安装包验证：v2026.08.23.1

## 本次更新

- 设置保存后，主窗口底部保留当前状态，并以独立绿色提示块显示“设置已保存”。
- 设置弹窗移除重复的辅助说明文字。

## 构建与验证

- 资产：`NanfengDownloader-Windows-v2026.08.23.1-Setup.exe`
- 构建工具：PyInstaller `6.21.0`、Inno Setup `7 x64`
- 大小：`144,115,170` 字节
- SHA-256：`9DAC272A6E84293CDC8245AE825FA2683472857F7224AF9609EDE35C46FF04B1`
- 105 项自动测试通过，Python 编译检查通过。
- 静默安装到独立临时目录后，主程序、FFmpeg、Node.js 与 YouTube PO Provider 均存在；主程序持续运行超过 8 秒。
- 静默卸载通过，临时安装目录已移除。

## 发布边界

- 上传源为短 ASCII 路径 `D:\ReleaseUpload\NDW-202608231-Setup.exe`，上传前已完成大小与 SHA-256 校验。
- Release 保持简洁，界面预览仅保留在 README，不重复上传或嵌入 Release。
- 未购买商业代码签名证书，Windows SmartScreen 仍可能提示未知发布者。
