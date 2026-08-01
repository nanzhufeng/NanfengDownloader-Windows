# 南枫下载 Windows v2026.08.01.1 安装包验证

> 日期：2026-08-01
> 范围：Windows x64 安装包与本地安装级烟雾验证。

## 产物

- 文件：`NanfengDownloader-Windows-v2026.08.01.1-Setup.exe`
- 大小：`144085767` 字节
- SHA-256：`662BDFF26DCFD51787C3FE2B8F1E8041D34A87EF97A891D9EB3883A23AC0EF53`
- 打包链路：Python 3.13.3 → PyInstaller 6.21.0 → Inno Setup 7.0.2 x64
- 代码签名：未签名

## 验证结果

- 62 项 `unittest` 全部通过。
- Python 模块编译检查通过。
- PyInstaller 清洁 one-folder 构建通过。
- Inno Setup 7.0.2 x64 编译通过。
- 静默安装到仓库内独立测试目录成功，退出码为 0。
- 安装后的主程序持续运行 8 秒，没有提前退出。
- FFmpeg、FFprobe、Node.js 和五个平台本地 SVG 图标均存在。
- 测试安装的卸载程序退出码为 0，临时安装目录已清理。
- 新版真实界面预览已人工检查，不含账号、Cookie 或私人链接。
- GitHub Release 只上传一个 Inno Setup 安装资产，不重复上传 README 界面预览。
- GitHub 服务端记录的资产大小和 SHA-256 与本地完全一致。
- 新版发布成功后，旧 `v2026.08.01-windows` Release 与标签已删除。

## 验证边界

- 本轮安装验证不等同于重新执行全部平台真实下载矩阵；TikTok 与 Mac 抖音分享文本的真实服务证据见 `tiktok-mac-douyin-regression-20260801.md`。
- 安装包未购买商业代码签名证书，Windows SmartScreen 仍可能提示未知发布者。
- 后续发布仍必须先完成远端资产大小与 SHA-256 核验，再删除旧 Release。
