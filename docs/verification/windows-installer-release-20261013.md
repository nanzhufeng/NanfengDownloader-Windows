# Windows v2026.10.13 交付验收

2026-10-13；Windows x64；安装包已冻结，后续只更新发布资料。

- 改动：下载队列所有列单行显示，长内容末尾省略；标题内换行仅在绘制时合并，完整值、悬浮提示与历史恢复不变。
- 文件：D:\ReleaseUpload\NanfengDownloader\NanfengDownloader-Windows-v2026.10.13-Setup.exe；157130748 字节；产品版本 2026.10.13，文件版本 2026.10.13.0。
- 源码：205 项完整 unittest 通过（28.905 秒）；compileall、限定 diff 检查通过；新增单行列表回归已在 Windows 原生平台验证。
- 构建：复用固定 build／dist 缓存；PyInstaller 与 Inno Setup 7 x64 成功，安装器压缩 123.609 秒。C 盘启动构建前剩余 64.24 GB，D 盘 203.33 GB。
- 冻结程序：独立临时配置与登录资料；原生窗口标题、WM_NULL 响应通过；不存在外来 icuuc.dll。
- 随包工具可执行：aria2 1.37.0、FFmpeg n4.4.3-20221024、Node v24.15.0。
- 真实预览：当前冻结 EXE 主工作台 1820×1000、设置 760×620、下拉 444×212；合成数据、未启动下载。长标题及链接单行省略、五项分辨率全可见；README 已同步。
- 发布结构合同：14 项通过，0 项失败；唯一交付附件为平台命名 Setup EXE。
- 签名：程序和安装包均为 NotSigned，按 Windows 默认未签名规则发布。
- 安装／卸载：本版 NOT RUN。前次同类验收命令被自动批准审查拦截；本轮未换调用方式绕过，也不把前版或冻结启动结果算作本版安装验收。
- 源码标签：v2026.10.13-windows，准确指向 edd8148321ce4b3f8e27d6143cae8bc392726909；main 后续仅更新发布终态记录。
- GitHub：正式 Release 于 2026-10-13 22:58:26 +08:00 发布，draft=false、prerelease=false，已为 latest；唯一 Setup EXE 为 uploaded，157130748 字节。22:59 重新下载，与最初冻结收据及当前本地文件完全一致，下载文件仍为 NotSigned、版本 2026.10.13。
- 下载：[v2026.10.13-windows](https://github.com/nanzhufeng/NanfengDownloader-Windows/releases/tag/v2026.10.13-windows)；Release 只附 Setup EXE，未加入展示图或 SHA-256。

不覆盖用户现用安装目录，不清理用户下载／登录数据。实际外部平台下载、BT 公网、多 DPI 与读屏仍待验收；未重新生成旧版本冻结安装包。
