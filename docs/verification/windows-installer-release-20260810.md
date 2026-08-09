# 南枫下载 Windows v2026.08.10 安装包验证

> 日期：2026-08-10
> 范围：Windows x64 安装包与本地安装级烟雾验证。

## 产物

- 文件：`NanfengDownloader-Windows-v2026.08.10-Setup.exe`
- 大小：`144092377` 字节
- SHA-256：`980CCD9A0B4CA21AB26FD7599DFB3AF49A1E36F928E1E8DB0372270B29FC04EF`
- 打包链路：Python 3.13 → PyInstaller → Inno Setup 7.0.2 x64
- 代码签名：未签名

## 验证结果

- 63 项 `unittest` 全部通过。
- Python 模块编译检查通过。
- “定位长文件名后主窗口尺寸不变”回归测试通过。
- PyInstaller 清洁 one-folder 构建通过。
- Inno Setup 7.0.2 x64 编译通过。
- 静默安装到仓库内隔离测试目录成功，退出码为 0。
- 安装后的主程序持续运行 8 秒，没有提前退出。
- FFmpeg、FFprobe、Node.js 和卸载程序均存在。
- 测试安装的卸载程序退出码为 0，安装内容已清理。
- GitHub Release 只上传一个 Inno Setup 安装资产，不重复上传 README 界面预览。

## 发布后核验

- GitHub Release：`v2026.08.10-windows`，状态为正式发布并设为 Latest。
- GitHub 远端只包含 `NanfengDownloader-Windows-v2026.08.10-Setup.exe` 一个资产。
- GitHub 远端资产大小为 `144092377` 字节，与本地一致。
- GitHub 服务端 SHA-256 为 `980CCD9A0B4CA21AB26FD7599DFB3AF49A1E36F928E1E8DB0372270B29FC04EF`，与本地一致。
- Release 正文未上传或嵌入界面预览；预览只保留在 README 主页面。
- 旧 `v2026.08.01.1-windows` Release 与标签已在新资产核验完成后删除。

## 验证边界

- 本轮安装验证聚焦定位后窗口尺寸稳定，不等同于重新执行全部平台真实下载矩阵。
- 安装包未购买商业代码签名证书，Windows SmartScreen 仍可能提示未知发布者。
