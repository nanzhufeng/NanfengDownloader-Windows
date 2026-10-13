# 当前交接

2026-10-13 22:59 +08:00；D:\CodexProjects\NanfengDownloader-Windows。

用户已授权“打包上传 GitHub”。本轮 v2026.10.13 修复列表单行显示并更新真实预览、版本及发布资料。

## 已完成

- QTableWidget 关闭自动换行，统一 SingleLineItemDelegate 末尾省略；显式换行仅在绘制时合并，原始任务数据、完整悬浮提示及历史恢复不变。
- 新增 test_queue_single_line；205 项完整测试通过（28.905 秒），compileall 与限定 diff 检查通过；Windows 原生单行绘制另验通过。
- 固定 build／dist 缓存构建成功；PyInstaller 冻结窗口、独立临时配置、原生 WM_NULL 响应及随包工具均通过。
- 安装包已冻结：D:\ReleaseUpload\NanfengDownloader\NanfengDownloader-Windows-v2026.10.13-Setup.exe，157130748 字节；程序与安装包 NotSigned。
- README 三张图来自当前冻结 EXE；脱敏合成行，长标题单行省略，没有启动下载；发布结构合同 14 项通过。
- 本版证据：docs/verification/windows-installer-release-20261013.md。旧 v2026.10.12.1 冻结文件及验收文档不覆盖。

## 发布终态

- main 与独立 v2026.10.13-windows 标签已同步；准确源码提交 edd8148321ce4b3f8e27d6143cae8bc392726909，后续仅发布终态记录。
- https://github.com/nanzhufeng/NanfengDownloader-Windows/releases/tag/v2026.10.13-windows；22:58:26 +08:00 正式发布，draft=false、prerelease=false，已为 latest。
- 唯一 Setup EXE 状态 uploaded，157130748 字节；22:59 从 GitHub 重新下载，与最初冻结收据及当前本地文件完全一致。Release 不加展示图片或 SHA-256。
- 本轮发布完成，不再运行构建／上传；后续单独反馈再启动新工作。

本版安装／卸载未重新运行：前次同类命令被自动批准审查拒绝，本轮不换调用方式绕过，也不把前版证据算作本版。外部平台实际媒体下载、BT 公网、多 DPI／读屏仍未重新验收。旧中断编译残留见前版验收记录，本轮未删除。

当前源码入口：启动南枫下载.bat。未覆盖用户现用安装目录，未清理下载／登录数据；冻结文件不再重新生成。
