# 南枫下载 Windows 安装包验证

> 日期：2026-07-26
>
> 安装器：Inno Setup 7.0.2 x64
>
> 产物：`NanfengDownloader-Windows-v2026.07.26-Setup.exe`

## 构建输入

- Git 仓库：`D:\CodexProjects\NanfengDownloader-Windows`
- PyInstaller 配置：`南枫下载_Windows.spec`
- Inno Setup 配置：`packaging/windows/NanfengDownloader.iss`
- 安装器版本信息：`2026.7.26`

## 自动与真实平台验证

- 49 项 `unittest` 全部通过。
- Python 编译检查与 `git diff --check` 通过。
- B站、小红书各完成一个长视频和一个短视频真实下载。
- B站多 P 地址真实读取 6 条，并实际下载第 6 P。
- 媒体结果通过 FFprobe 与 FFmpeg 全数据包扫描。

## 安装级验证

- Inno Setup 7.0.2 x64 编译成功。
- 静默安装退出码：`0`。
- 安装目录包含主程序、FFmpeg、FFprobe、Node.js 和 YouTube Provider。
- 安装后的应用保持运行并响应超过 8 秒。
- 静默卸载退出码：`0`。
- 测试安装目录剩余文件数：`0`。

## 产物

- 文件大小：`140,306,568` 字节。
- SHA-256：`C4F03C10975ABB44CA18BAF5B93767147A5310C2BC24257016BD73FEA252AA30`。

## 已知边界

- 安装包尚未使用商业代码签名，Windows SmartScreen 可能显示“未知发布者”。
- 外部平台仍可能因账号权限、地区、网络或风控策略限制特定内容。
