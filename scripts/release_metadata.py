"""Windows 发布版本的唯一解析入口。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass


VERSION_PATTERN = re.compile(
    r"^(?P<year>20\d{2})\.(?P<month>0[1-9]|1[0-2])\.(?P<day>0[1-9]|[12]\d|3[01])(?:\.(?P<revision>[1-9]\d*))?$"
)
TAG_PATTERN = re.compile(r"^v(?P<version>.+)-windows$")


@dataclass(frozen=True)
class ReleaseMetadata:
    output_version: str
    app_version: str
    version_info: str
    tag: str
    installer_name: str


def release_metadata(version: str) -> ReleaseMetadata:
    match = VERSION_PATTERN.fullmatch(version.strip())
    if not match:
        raise ValueError("版本必须是 YYYY.MM.DD 或 YYYY.MM.DD.N，例如 2026.08.21。")
    parts = match.groupdict()
    try:
        dt.date(int(parts["year"]), int(parts["month"]), int(parts["day"]))
    except ValueError as exc:
        raise ValueError(f"版本日期无效：{version}") from exc
    revision = parts["revision"]
    output_version = ".".join(value for value in (parts["year"], parts["month"], parts["day"], revision) if value)
    app_version = ".".join(value for value in (parts["year"], str(int(parts["month"])), str(int(parts["day"])), revision) if value)
    version_info = app_version if revision else f"{app_version}.0"
    tag = f"v{output_version}-windows"
    return ReleaseMetadata(
        output_version,
        app_version,
        version_info,
        tag,
        f"NanfengDownloader-Windows-v{output_version}-Setup.exe",
    )


def release_metadata_from_tag(tag: str) -> ReleaseMetadata:
    match = TAG_PATTERN.fullmatch(tag.strip())
    if not match:
        raise ValueError("标签必须是 vYYYY.MM.DD-windows，例如 v2026.08.21-windows。")
    metadata = release_metadata(match.group("version"))
    if metadata.tag != tag.strip():
        raise ValueError("标签版本格式不规范，请使用补零后的 YYYY.MM.DD 日期。")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="解析南枫下载 Windows 发布版本")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--version")
    group.add_argument("--tag")
    parser.add_argument("--format", choices=("json", "shell"), default="json")
    args = parser.parse_args()
    metadata = release_metadata(args.version) if args.version else release_metadata_from_tag(args.tag)
    if args.format == "json":
        print(json.dumps(asdict(metadata), ensure_ascii=False))
    else:
        for key, value in asdict(metadata).items():
            print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
