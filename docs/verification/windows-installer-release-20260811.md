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

## 资产

- 大小：`144,086,310` 字节。
- SHA-256：`4DA39B65282BBFF3295A16FE7F50E757F4E6C9A13C824F24BD56C04968A97091`。

## 发布边界

Release 保持简洁，只包含版本说明、Windows 安装包、摘要和兼容提示；界面预览仅保留在默认分支 README，不作为 Release 资产或正文图片重复上传。
