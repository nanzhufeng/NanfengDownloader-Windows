# Windows 安装包验证：v2026.08.11

## 构建基准

- 仓库：`NanfengDownloader-Windows`。
- 版本：`v2026.08.11-windows`。
- 安装器：`NanfengDownloader-Windows-v2026.08.11-Setup.exe`。
- 编译器：Inno Setup 7.0.2 x64。

## 本地验证

- Python `unittest`：71 项通过。
- PyInstaller：清洁构建通过。
- 发布合同：14/14 通过。
- 隔离静默安装：通过。
- 随包依赖：FFmpeg、Node.js、PO Token Provider 均存在。
- 安装后的应用：持续运行超过 8 秒。
- 隔离静默卸载：通过，测试安装目录已移除。

## 本地候选资产

- 大小：`144,098,506` 字节。
- SHA-256：`F4D06BE6835A7EA2E12F46B7DE894BD3F2FEFF078D4B01103B032A356CBD8B59`。

## GitHub 正式发布资产

- 云端构建：GitHub Actions `31515230953`，成功执行 72 项测试、PyInstaller、Inno Setup 7 x64、随包 `_internal/tools/node/node.exe` 校验，以及随包 `ffmpeg.exe -version` 实际执行校验。
- Release：`v2026.08.11-windows`。
- 大小：`178,001,895` 字节。
- SHA-256：`71D3CF09A10DAB8CA4335B7D661F3941559C936A7FB508C11E8F67C71074B05C`。
- 旧 `v2026.08.10-windows` 已在新资产远端摘要核对完成后删除。
- 本机对该 Release 的二次完整复下载仍受本机 GitHub 大文件传输 EOF 影响而中断；因此本条不将第二次本地隔离安装写为已完成，云端随包 FFmpeg 执行校验与远端 SHA-256 是当前发布验证证据。

## 发布边界

Release 保持简洁，只包含版本说明、Windows 安装包、摘要和兼容提示；界面预览仅保留在默认分支 README，不作为 Release 资产或正文图片重复上传。
