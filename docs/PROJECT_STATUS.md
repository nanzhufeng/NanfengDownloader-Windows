# 南枫下载 Windows 项目状态

## Verified
- Last verified: 2026-10-12 14:29 +08:00
- Branch: main
- Code baseline: c90908f680e79fb9e813025364e8ba4c113162d4（安装包代码基线）；发布资料随后收尾，最终版本基线以 v2026.10.12-windows 标签为准。
- Verified by: Codex
- Status: Active
- Scope: Windows v2026.10.12 源码、原生控件、冻结 EXE、Inno Setup 安装器与隔离安装验收。

## Current
- 链接快捷键粘贴替换，列表历史记录可选保存。
- 双列灰底设置卡片；共享按钮外边界反馈，没有内部第二层方框。
- 非编辑下拉控件保留文字居中、再次点击关闭；使用 Fusion 控件主题规避 Windows 编辑型弹层差异。
- 当前源码 BAT：仓库根目录 `启动南枫下载.bat`。

## In Progress
- 本轮代码、安装器验收和远端下载回验已完成。公开状态以 [GitHub Release](https://github.com/nanzhufeng/NanfengDownloader-Windows/releases/tag/v2026.10.12-windows) 的实时结果为准。

## Blocked
- 无。用户于 2026-10-12 将 Windows 默认发布方式改为未签名安装包；Android、macOS 规则不受此变更影响。

## Tests
| 验证层 | 结果 | 范围 / 证据 |
|---|---|---|
| Core tests | PASS | 183 项完整测试；build-release-20261012.log（本地忽略日志） |
| Windows UI | PASS | 原生 Windows 模式下拉重复开关、Esc、选择与点击回传；按钮内部无新增方框；设置开关与取消 |
| Build | PASS | PyInstaller 终态 EXE；Inno Setup 7 x64 安装包 |
| Installer | PASS | 独立目录安装、真实窗口标题及响应、aria2/FFmpeg/Node、卸载退出 0；原快捷方式保留 |
| Signature | NOT SIGNED | Get-AuthenticodeSignature；安装包 157112270 字节 |
| Remote asset | PASS | 唯一 Setup EXE；uploaded；157112270 字节；从 GitHub 下载与本地文件一致 |

## Gaps
- 本轮未重新验收外部平台真实下载；磁力链接和 BT 公网下载仍未完成真实验收。
- Windows 安装包验签为 NotSigned，按用户的新默认规则发布；不声明正式签名。

## Sync & Safety
- Observed at: 2026-10-12 14:29 +08:00
- Docs: OK（README 当前截图、版本说明、状态摘要）
- Git: DIRTY（仅本次发布资料收尾；功能代码已提交，最终同步结果以版本标签为准）
- Remote: PUSHED（代码基线 c90908f 已推送 main；本次文档收尾将随 v2026.10.12-windows 标签同步）
- Rollback point: 1e36a7771357836f1ebfe68155804c12f79a2611（此前已发布的 v2026.09.15-windows）
- Secrets/config risk: NONE（app/scripts/packaging/docs/tests 的典型真实凭据模式未命中；预览已脱敏；设计会话目录不提交）

## Next
1. 从 GitHub Release 下载本版使用；当前源码入口为根目录 BAT。
2. 后续按单独授权进行外部平台真实下载及 BT 公网验收。
