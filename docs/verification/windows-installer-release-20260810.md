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

- GitHub 远端资产大小与 SHA-256：待上传后核验。
- 旧 Release 与标签删除：待新资产校验完成后执行。

## 验证边界

- 本轮安装验证聚焦定位后窗口尺寸稳定，不等同于重新执行全部平台真实下载矩阵。
- 安装包未购买商业代码签名证书，Windows SmartScreen 仍可能提示未知发布者。
