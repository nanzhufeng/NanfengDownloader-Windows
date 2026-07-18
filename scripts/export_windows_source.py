from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_SOURCE_ENTRIES = (
    ".gitignore",
    "README.md",
    "requirements.txt",
    "run.ps1",
    "start.py",
    "app",
    "tests",
    "scripts",
    "docs/context.md",
    "docs/app-development-experience-audit.md",
    "docs/verification/windows-real-regression-20260718.md",
    "南枫下载.spec",
    "启动南枫下载.bat",
    "安装YouTube兼容组件.bat",
)
IGNORED_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".icns"}


def _ignored(path: Path) -> bool:
    return any(part in IGNORED_NAMES for part in path.parts) or path.suffix.lower() in IGNORED_SUFFIXES


def _copy_entry(source: Path, target: Path) -> None:
    if source.is_dir():
        for child in source.rglob("*"):
            relative = child.relative_to(PROJECT_ROOT)
            if _ignored(relative) or not child.is_file():
                continue
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, destination)
        return
    destination = target / source.relative_to(PROJECT_ROOT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return completed.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="导出不含 Android/Mac 的 Windows 独立源码树")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--update", action="store_true", help="允许更新已有目标中的清单文件，不删除额外文件")
    parser.add_argument("--init-git", action="store_true")
    args = parser.parse_args()

    target = args.target.resolve()
    if target == PROJECT_ROOT or PROJECT_ROOT in target.parents:
        raise RuntimeError("Windows 独立源码目录必须位于当前混合项目目录之外。")
    if target.exists() and any(target.iterdir()) and not args.update:
        raise RuntimeError("目标目录非空；如确认只覆盖清单文件，请显式增加 --update。")
    target.mkdir(parents=True, exist_ok=True)

    missing = [entry for entry in WINDOWS_SOURCE_ENTRIES if not (PROJECT_ROOT / entry).exists()]
    if missing:
        raise RuntimeError(f"Windows 源码清单缺少文件：{', '.join(missing)}")
    for entry in WINDOWS_SOURCE_ENTRIES:
        _copy_entry(PROJECT_ROOT / entry, target)

    forbidden = [
        path.relative_to(target)
        for path in target.rglob("*")
        if path.is_file()
        and (
            "android" in {part.lower() for part in path.relative_to(target).parts}
            or path.suffix.lower() == ".command"
            or path.name.endswith("_mac.spec")
        )
    ]
    if forbidden:
        raise RuntimeError(f"Windows 导出包含禁止的平台文件：{forbidden}")

    origin = (
        "# Windows 独立源码来源\n\n"
        f"- 生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}\n"
        f"- 来源目录：`{PROJECT_ROOT}`\n"
        f"- 来源分支：`{_git_output('branch', '--show-current') or 'unknown'}`\n"
        f"- 来源提交：`{_git_output('rev-parse', 'HEAD') or 'unknown'}`\n"
        "- 来源工作区：导出时可能包含未提交的 Windows 修改，以导出目录内容为准。\n"
        "- 平台边界：该目录只包含 Windows PySide6 桌面版；Android 与 macOS 文件明确排除。\n"
    )
    (target / "WINDOWS_SOURCE_ORIGIN.md").write_text(origin, encoding="utf-8")

    if args.init_git and not (target / ".git").exists():
        subprocess.run(["git", "init", "-b", "main"], cwd=target, check=True)

    print(f"Windows 独立源码已导出：{target}")
    print(f"文件数：{sum(1 for path in target.rglob('*') if path.is_file())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
