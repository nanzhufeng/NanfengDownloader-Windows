# Windows 发布流程

## 默认入口与所有权

版本由 app/main.py 的 APP_VERSION 通过 scripts/release_metadata.py 的 AST 读取统一解析；发布入口为 scripts/publish_windows_release.ps1，构建唯一入口为 scripts/build_windows_installer.ps1；GitHub 调度在 .github/workflows/release-windows.yml。

1. 完成软件修改及版本／开发时间更新，写 docs/release-版本.md，提交并推送准确源码。
2. 运行 `发布准备.bat` 或 `powershell -File scripts/publish_windows_release.ps1 -Plan` 预览。计划只读，检查真实版本及未提交改动。
3. `powershell -File scripts/publish_windows_release.ps1` 在 GitHub Windows 上仅构建候选包，默认不发布。需要正式发布且已有用户授权时加 `-Publish`。工作流按版本串行，同一源码有活跃运行时拒绝重复调度。
4. 云端运行完整测试、同一构建脚本、冻结启动及随包工具检查；测试或上传失败必须停止，保留 draft，不得继续公开。
5. 云端只上传唯一 Setup EXE，核对名称／状态／大小后发布。候选包、阶段耗时及实际预览保存为三天 Actions artifact，不混入 Release 附件。
6. 本地从 GitHub 下载最终文件，核对版本、签名及内部冻结摘要，刷新 README 实际预览与交付证据；不把云端构建误称本机包的相同字节。

GitHub 执行端上传安装包，电脑只推送小体积源码和接收下载，不再把约 150 MB 安装包反复经过本机上行。云端首次准备依赖仍需时间；时间以实际工作流为准，不承诺固定分钟数。

## 本地构建与故障回退

`powershell -File scripts/build_windows_installer.ps1 -Version 版本` 保留本地入口。默认复用固定 build／dist；确有缓存问题才加 `-CleanRebuild`，不得复制完整构建缓存到日期目录。输出目录可由 `-ReleaseDirectory` 指定，成功生成 build-版本.json，分别记录测试、PyInstaller、启动和安装包耗时。

云端不可用时，先核对原因，再按明确记录的本地回退流程。HEAD 只能证明连通，不能据此判断实际上传速度。若一个上传进程缓慢但仍有进展，不凭短时样本强行中断；EOF 后先查 draft 与资产状态，避免重复创建 Release 或盲目覆盖。已冻结安装包不重建，正式 Release 和已发布标签不覆盖。GitHub CLI 的读取计数不是服务端接收证明，最终以 uploaded 与下载回验为准。

本地和云端工具链可能不同，始终记录实际 FFmpeg／Node 版本；云端验证通过不能替代本机安装、卸载、真实平台媒体下载。Windows 默认未签名；安装器默认完整简体中文、常规任务勾选，并仅关闭指定安装目录的自有进程。

## 2026-10-16 已确认的瓶颈

- 上版本地测试 15.185 秒，本地构建 09:33:25–09:36:30，约 185 秒，其中 Inno 压缩 109.344 秒。
- 正式发布到 10:15:48，远端回验 10:16；绝大部分时间在本机慢速上行、线路切换与 EOF 后的整包重传。
- 初次只测 HEAD 连通便选择线路，又中断了仍有进展的直连上传，增加了重复传输，这是执行流程的问题。
- 本次修订构建记录：PyInstaller 66.721 秒，冻结启动 5.784 秒，Inno 108.901 秒，共 181.669 秒。仅去掉 --clean 不会解决主要耗时；主要改进是将大文件上传移到 GitHub 执行端。

- 新云候选流程实测通过：运行 38846891113，完整测试／构建／启动／候选上传合计 6 分 20 秒（03:42:57Z–03:49:17Z）；未执行正式发布，不能把候选上传当作正式 Release 远端回验。
