from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.catalog import discover_links
from app.downloader import DownloadOptions, download_url, find_ffmpeg_dir
from app.media_validation import validate_media_file


DEFAULT_YOUTUBE_SAMPLE = "https://www.youtube.com/watch?v=PONo81nwVy4"


@dataclass
class RegressionResult:
    name: str
    platform: str
    source_url: str
    expected_kind: str
    status: str = "NOT_RUN"
    catalog_count: int = 0
    catalog_seconds: float = 0.0
    download_seconds: float = 0.0
    downloaded_bytes: int = 0
    average_mib_per_second: float = 0.0
    output_files: list[str] | None = None
    note: str = ""


def _case(
    name: str,
    platform_name: str,
    url: str | None,
    expected_kind: str,
) -> tuple[str, str, str, str] | None:
    if not url:
        return None
    return name, platform_name, url, expected_kind


def _run_case(
    case: tuple[str, str, str, str],
    base_options: DownloadOptions,
    *,
    max_items: int,
    catalog_only: bool,
) -> RegressionResult:
    name, platform_name, source_url, expected_kind = case
    result = RegressionResult(
        name=name,
        platform=platform_name,
        source_url=source_url,
        expected_kind=expected_kind,
        output_files=[],
    )
    try:
        catalog_started = time.monotonic()
        items = discover_links(source_url, base_options, max_items=max_items)
        result.catalog_seconds = round(time.monotonic() - catalog_started, 3)
        result.catalog_count = len(items)
        if not items:
            raise RuntimeError("目录读取没有返回任何作品。")
        if expected_kind == "single" and len(items) != 1:
            raise RuntimeError(f"单视频链接错误地展开为 {len(items)} 条。")

        creators = {item.creator_name for item in items if item.creator_name}
        if expected_kind == "creator" and len(creators) > 1:
            raise RuntimeError(f"作者/频道列表混入多个主体：{sorted(creators)}")

        if catalog_only or expected_kind != "single":
            result.status = "PASS"
            result.note = "目录语义验证通过；集合链接默认不自动批量下载。"
            return result

        item = items[0]
        options = DownloadOptions(
            output_dir=base_options.output_dir,
            quality=base_options.quality,
            cookie_mode=base_options.cookie_mode,
            cookie_file=base_options.cookie_file,
            ffmpeg_dir=base_options.ffmpeg_dir,
            creator_name=item.creator_name,
        )
        download_started = time.monotonic()
        download_result = download_url(item.url, options, lambda info: None)
        result.download_seconds = round(time.monotonic() - download_started, 3)
        if download_result.skipped:
            result.status = "PASS"
            result.note = "样本文件已存在，下载器按合同跳过。"
            return result

        for output in download_result.files:
            probe = validate_media_file(output, options.ffmpeg_dir)
            result.downloaded_bytes += probe.size
            result.output_files.append(str(output.resolve()))
        if not result.output_files:
            raise RuntimeError("下载完成但没有可验证的媒体输出。")
        if result.download_seconds > 0:
            result.average_mib_per_second = round(
                result.downloaded_bytes / result.download_seconds / (1024 * 1024),
                3,
            )
        result.status = "PASS"
        if result.average_mib_per_second < 1:
            result.note = "媒体有效，但本次平均速度低于 1 MiB/s；需要结合线路和平台限流分析。"
        else:
            result.note = "媒体有效，已记录本次持续平均速度。"
    except Exception as exc:
        result.status = "FAIL"
        result.note = f"{type(exc).__name__}: {exc}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="南枫下载真实平台回归与持续性能基线")
    parser.add_argument("--youtube-single", default=DEFAULT_YOUTUBE_SAMPLE)
    parser.add_argument("--youtube-channel")
    parser.add_argument("--douyin-single")
    parser.add_argument("--douyin-author")
    parser.add_argument("--bilibili-single")
    parser.add_argument("--bilibili-space")
    parser.add_argument("--xiaohongshu-single")
    parser.add_argument("--xiaohongshu-author")
    parser.add_argument("--tiktok-single")
    parser.add_argument("--tiktok-author")
    parser.add_argument("--quality", default="360p 及以下")
    parser.add_argument("--max-items", type=int, default=25)
    parser.add_argument("--catalog-only", action="store_true")
    parser.add_argument("--require-douyin", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / ".verification-downloads" / datetime.now().strftime("%Y%m%d-%H%M%S"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "docs" / "verification" / "real-download-latest.json",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    options = DownloadOptions(
        output_dir=args.output_dir,
        quality=args.quality,
        cookie_mode="不使用登录态",
        cookie_file=None,
        ffmpeg_dir=find_ffmpeg_dir(PROJECT_ROOT),
    )
    cases = [
        _case("youtube-single", "YouTube", args.youtube_single, "single"),
        _case("youtube-channel", "YouTube", args.youtube_channel, "creator"),
        _case("douyin-single", "抖音", args.douyin_single, "single"),
        _case("douyin-author", "抖音", args.douyin_author, "creator"),
        _case("bilibili-single", "哔哩哔哩", args.bilibili_single, "single"),
        _case("bilibili-space", "哔哩哔哩", args.bilibili_space, "creator"),
        _case("xiaohongshu-single", "小红书", args.xiaohongshu_single, "single"),
        _case("xiaohongshu-author", "小红书", args.xiaohongshu_author, "creator"),
        _case("tiktok-single", "TikTok", args.tiktok_single, "single"),
        _case("tiktok-author", "TikTok", args.tiktok_author, "creator"),
    ]
    results = [
        _run_case(case, options, max_items=args.max_items, catalog_only=args.catalog_only)
        for case in cases
        if case is not None
    ]

    if args.require_douyin and not any(result.platform == "抖音" for result in results):
        results.append(
            RegressionResult(
                name="douyin-required",
                platform="抖音",
                source_url="",
                expected_kind="single-or-creator",
                status="FAIL",
                note="要求验证抖音，但没有提供 --douyin-single 或 --douyin-author。",
            )
        )

    report: dict[str, Any] = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "quality": args.quality,
            "ffprobe_available": bool(options.ffmpeg_dir),
            "catalog_only": args.catalog_only,
        },
        "output_dir": str(args.output_dir.resolve()),
        "results": [asdict(result) for result in results],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for result in results:
        speed = f"{result.average_mib_per_second:.3f} MiB/s" if result.downloaded_bytes else "-"
        print(f"[{result.status}] {result.name}: catalog={result.catalog_count}, speed={speed}")
        if result.note:
            print(f"  {result.note}")
    print(f"报告：{args.report.resolve()}")
    return 1 if any(result.status == "FAIL" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
