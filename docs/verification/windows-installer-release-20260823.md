# Windows 安装包验证：v2026.08.23

## 构建基准

- 版本：`v2026.08.23-windows`
- 资产：`NanfengDownloader-Windows-v2026.08.23-Setup.exe`
- 构建工具：PyInstaller `6.21.0`、Inno Setup `7 x64`
- 安装包大小：`144,110,432` 字节
- SHA-256：`C059CDF9B79F9A2DD3146ED587107FE0E5F27C567290E91818211D33FBA0ADDE`

## 本地验证

- `python -m unittest discover -s tests -q`：105 项通过。
- PyInstaller 清洁构建通过。
- Inno Setup 在隔离工作目录完成封装，正式目录只接收完整生成的安装包。
- 使用 `/VERYSILENT` 安装到独立临时目录；主程序、FFmpeg、FFprobe、Node.js 和 YouTube PO Provider 均存在。
- FFmpeg / FFprobe 可执行，实际版本为 `n4.4.3-20221024`；Node.js 版本为 `v24.15.0`。
- 主程序启动后持续运行超过 8 秒；随后静默卸载成功，临时安装目录已清理。

## 发布边界

- 上传前从短 ASCII 路径 `D:\ReleaseUpload\NDW-20260823-Setup.exe` 读取并校验 SHA-256。
- GitHub Release 保持简洁，不上传或嵌入界面预览；当前界面预览只保留在仓库 README。
- Windows SmartScreen 的未签名提示仍可能出现，尚未购买商业代码签名证书。
- GitHub Actions 工作流固定的 FFmpeg `9.0.1` 与本地打包运行时版本不同；当前 Release 只声明本地实际验证的 `4.4.3`，下次云端构建须先统一来源与版本再采用。
