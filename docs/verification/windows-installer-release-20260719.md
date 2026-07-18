# 南枫下载 Windows 安装包验证

日期：2026-07-19

平台：Windows 10 x64

打包链路：Python 3.13.3 -> PyInstaller 6.21.0 -> Inno Setup 6.7.3

## 产物

- 文件：`NanfengDownloader-Windows-v2026.07.19-Setup.exe`
- 大小：`140286083` 字节
- SHA-256：`809272629DAE697097B41BAD1F54ED66E720E7B7CBF3BE15949DD41FEC791A55`
- 代码签名：未签名

## 分层验证

- 自动测试：39 项 `unittest` 通过。
- PyInstaller：清洁 one-folder 构建通过。
- Inno Setup：安装程序编译通过。
- 安装：静默安装到独立临时目录，退出码为 0。
- 依赖：安装后的 FFmpeg、Playwright Node 和 YouTube PO Provider 均存在。
- 启动：安装后的 `南枫下载.exe` 持续运行超过 8 秒。
- 卸载：测试安装卸载退出码为 0，临时安装目录已清理。

## 已知边界

- 安装包没有商业代码签名，Windows SmartScreen 可能显示未知发布者提示。
- 当前 Inno Setup 官方安装不包含简体中文语言文件，安装向导使用内置英文界面；应用本体仍为中文。
- 本次验证确认安装、启动和依赖完整，不等同于重新执行全部真实平台下载矩阵。
