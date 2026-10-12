# 南枫下载 Windows 项目状态

## Verified
- Last verified: 2026-10-12 13:47 +08:00
- Branch: main
- Code baseline: 1e36a7771357836f1ebfe68155804c12f79a2611 + 本轮工作区修改；提交后的最终基线以 Git 为准。
- Verified by: Codex
- Status: Blocked
- Scope: Windows v2026.10.12 源码、原生控件、冻结 EXE、Inno Setup 安装器与隔离安装验收。

## Current
- 链接快捷键粘贴替换，列表历史记录可选保存。
- 双列灰底设置卡片；共享按钮外边界反馈，没有内部第二层方框。
- 非编辑下拉控件保留文字居中、再次点击关闭；使用 Fusion 控件主题规避 Windows 编辑型弹层差异。
- 当前源码 BAT：仓库根目录 `启动南枫下载.bat`。

## In Progress
- v2026.10.12 源码同步 GitHub；安装包准备发布。

## Blocked
- 未发现正式 Windows 代码签名证书：环境变量、用户级配置入口与 Windows 证书库均未发现可用凭据；终态安装包验签为 NotSigned。
- 用户本轮 AGENTS 要求默认交付正式签名软件。只有正式凭据可用，或用户明确允许沿用历史未签名发布方式，才能完成对外安装包发布。

## Tests
| 验证层 | 结果 | 范围 / 证据 |
|---|---|---|
| Core tests | PASS | 183 项完整测试；build-release-20261012.log（本地忽略日志） |
| Windows UI | PASS | 原生 Windows 模式下拉重复开关、Esc、选择与点击回传；按钮内部无新增方框；设置开关与取消 |
| Build | PASS | PyInstaller 终态 EXE；Inno Setup 7 x64 安装包 |
| Installer | PASS | 独立目录安装、真实窗口标题及响应、aria2/FFmpeg/Node、卸载退出 0；原快捷方式保留 |
| Signature | NOT SIGNED | Get-AuthenticodeSignature；安装包 157112270 字节 |
| Remote asset | NOT RUN | 签名门禁尚未解除；未创建新 Release、标签或资产 |

## Gaps
- 本轮未重新验收外部平台真实下载；磁力链接和 BT 公网下载仍未完成真实验收。
- 当前正式签名身份缺失。

## Sync & Safety
- Observed at: 2026-10-12 13:47 +08:00
- Docs: OK（README 当前截图、版本说明、状态摘要）
- Git: DIRTY（本轮待提交修改；最终提交和推送状态见 Git）
- Remote: LOCAL ONLY（提交前观测；origin/main 为 1e36a7771357836f1ebfe68155804c12f79a2611）
- Rollback point: 1e36a7771357836f1ebfe68155804c12f79a2611（此前已发布的 v2026.09.15-windows）
- Secrets/config risk: NONE（app/scripts/packaging/docs/tests 的典型真实凭据模式未命中；预览已脱敏；设计会话目录不提交）

## Next
1. 确认正式签名可用或用户允许本版未签名发布。
2. 上传唯一 Setup EXE，下载回验，核对 main 与发布标签一致后发布。
