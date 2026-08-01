# 南枫下载 Windows v2026.08.01 安装包验证

> 日期：2026-08-01
>
> 安装器：Inno Setup 7.0.2 x64
>
> 产物：`NanfengDownloader-Windows-v2026.08.01-Setup.exe`

## 构建输入

- Git 仓库：`D:\CodexProjects\NanfengDownloader-Windows`
- PyInstaller 配置：`南枫下载_Windows.spec`
- Inno Setup 配置：`packaging/windows/NanfengDownloader.iss`
- 安装器版本信息：`2026.8.1`

## 自动与真实平台验证

- 54 项 `unittest` 全部通过。
- Python 编译检查与 `git diff --check` 通过。
- 使用现有 B站视频真实调用 Windows Shell 定位接口，资源管理器显示蓝色选中框和“选中 1 个项目”。
- 安装版界面确认存在“清空链接”按钮和队列表格“定位”列。
- 新界面预览来自本次安装后的正式 EXE，未包含账号或私人链接。
- Windows 发布合同检查：`14/14` 通过。

## 安装级验证

- Inno Setup 7.0.2 x64 编译成功。
- 静默安装退出码：`0`。
- 安装目录包含主程序、FFmpeg、FFprobe、Node.js 和 YouTube Provider。
- 安装后的应用保持运行并响应超过 8 秒。
- 静默卸载退出码：`0`。
- 测试安装目录剩余文件数：`0`。

## 产物

- 文件大小：`140,317,826` 字节。
- SHA-256：`8122DA1FF708AEDA4BB3A63C5E02C7129B68CC41640DCA87F667F6267C215699`。

## 已知边界

- 安装包尚未使用商业代码签名，Windows SmartScreen 可能显示“未知发布者”。
- 外部平台仍可能因账号权限、地区、网络或风控策略限制特定内容。
