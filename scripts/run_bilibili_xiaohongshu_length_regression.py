from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.catalog import discover_links
from app.downloader import DownloadOptions, download_url, find_ffmpeg_dir
from app.media_validation import validate_media_file


def _configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def _url_without_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _probe_file(path: Path, ffprobe: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,format_name:stream=index,codec_type,codec_name,width,height",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"FFprobe 失败：{completed.stderr[-500:]}")
    return json.loads(completed.stdout)


def _run_case(
    case: dict[str, Any],
    base_options: DownloadOptions,
    ffprobe: Path,
) -> dict[str, Any]:
    print(
        f"CASE_START {case['name']} {case['platform']} {case['kind']}",
        flush=True,
    )
    started = time.monotonic()
    result = {**case, "status": "FAIL"}
    try:
        catalog_started = time.monotonic()
        items = discover_links(case["source_url"], base_options, max_items=1)
        result["catalog_seconds"] = round(time.monotonic() - catalog_started, 3)
        if len(items) != 1:
            raise RuntimeError(f"智能读取应返回 1 条，实际 {len(items)} 条")
        item = items[0]
        result["catalog"] = {
            "title": item.title,
            "creator_name": item.creator_name,
            "publish_date": item.publish_date,
            "resolved_url": _url_without_query(item.url),
        }
        options = DownloadOptions(
            output_dir=base_options.output_dir,
            quality=base_options.quality,
            cookie_mode=base_options.cookie_mode,
            cookie_file=base_options.cookie_file,
            ffmpeg_dir=base_options.ffmpeg_dir,
            creator_name=item.creator_name,
        )
        progress_state = {"last_print": 0.0}

        def progress(info: dict[str, Any]) -> None:
            now = time.monotonic()
            if now - progress_state["last_print"] < 10:
                return
            progress_state["last_print"] = now
            downloaded = int(info.get("downloaded_bytes") or 0)
            total = int(info.get("total_bytes") or info.get("total_bytes_estimate") or 0)
            percent = (downloaded / total * 100) if total else 0
            print(
                f"CASE_PROGRESS {case['name']} {percent:.1f}% "
                f"{downloaded}/{total} {info.get('_speed_str') or ''} "
                f"ETA={info.get('_eta_str') or ''}",
                flush=True,
            )

        download_started = time.monotonic()
        download_result = download_url(item.url, options, progress)
        result["download_seconds"] = round(time.monotonic() - download_started, 3)
        if download_result.skipped:
            raise RuntimeError("本轮使用全新验证目录，不应跳过下载")
        if len(download_result.files) != 1:
            raise RuntimeError(f"应生成 1 个媒体文件，实际 {len(download_result.files)} 个")

        media_path = download_result.files[0]
        validated = validate_media_file(media_path, base_options.ffmpeg_dir)
        probe = _probe_file(media_path, ffprobe)
        format_info = probe.get("format") or {}
        streams = probe.get("streams") or []
        video_streams = [
            stream for stream in streams if stream.get("codec_type") == "video"
        ]
        audio_streams = [
            stream for stream in streams if stream.get("codec_type") == "audio"
        ]
        duration = float(format_info.get("duration") or 0)
        size = int(format_info.get("size") or media_path.stat().st_size)
        if duration <= 0:
            raise RuntimeError("下载文件没有有效时长")
        if not video_streams:
            raise RuntimeError("下载文件没有视频流")
        if duration < case["expected_min"]:
            raise RuntimeError(
                f"样本时长 {duration:.3f}s 低于{case['kind']}下限 "
                f"{case['expected_min']}s"
            )
        expected_max = case.get("expected_max")
        if expected_max is not None and duration > expected_max:
            raise RuntimeError(
                f"样本时长 {duration:.3f}s 超过{case['kind']}上限 "
                f"{expected_max}s"
            )

        result["media"] = {
            "path": str(media_path.resolve()),
            "duration_seconds": round(duration, 3),
            "size_bytes": size,
            "format_name": format_info.get("format_name"),
            "video_streams": video_streams,
            "audio_streams": audio_streams,
            "validated_size": validated.size,
            "average_mib_per_second": round(
                size / max(result["download_seconds"], 0.001) / (1024 * 1024),
                3,
            ),
        }
        print(
            f"CASE_PASS {case['name']} duration={duration:.3f}s size={size} "
            f"speed={result['media']['average_mib_per_second']:.3f}MiB/s "
            f"path={media_path}",
            flush=True,
        )
        result["status"] = "PASS"
    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"
        print(f"CASE_FAIL {case['name']} {result['error']}", flush=True)
    result["total_seconds"] = round(time.monotonic() - started, 3)
    return result


def main() -> int:
    _configure_console_encoding()
    parser = argparse.ArgumentParser(
        description="B站和小红书长短视频真实下载回归"
    )
    parser.add_argument("--bilibili-short", required=True)
    parser.add_argument("--bilibili-long", required=True)
    parser.add_argument("--xiaohongshu-short", required=True)
    parser.add_argument("--xiaohongshu-long", required=True)
    parser.add_argument("--quality", default="720p 及以下")
    parser.add_argument(
        "--only",
        action="append",
        choices=(
            "bilibili-short",
            "bilibili-long",
            "xiaohongshu-short",
            "xiaohongshu-long",
        ),
        help="只执行指定样本；可重复传入。默认执行全部四项。",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT
        / ".verification-downloads"
        / f"bilibili-xiaohongshu-long-short-{datetime.now():%Y%m%d-%H%M%S}",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT
        / "docs"
        / "verification"
        / "bilibili-xiaohongshu-long-short-latest.json",
    )
    args = parser.parse_args()

    ffmpeg_dir = find_ffmpeg_dir(PROJECT_ROOT)
    if not ffmpeg_dir:
        raise RuntimeError("没有找到 FFmpeg / FFprobe，不能执行真实媒体验收。")
    ffprobe = ffmpeg_dir / "ffprobe.exe"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    base_options = DownloadOptions(
        output_dir=args.output_dir,
        quality=args.quality,
        cookie_mode="不使用登录态",
        cookie_file=None,
        ffmpeg_dir=ffmpeg_dir,
    )
    cases = [
        {
            "name": "bilibili-short",
            "platform": "哔哩哔哩",
            "kind": "短视频",
            "source_url": args.bilibili_short,
            "expected_min": 10,
            "expected_max": 120,
        },
        {
            "name": "bilibili-long",
            "platform": "哔哩哔哩",
            "kind": "长视频",
            "source_url": args.bilibili_long,
            "expected_min": 1800,
            "expected_max": None,
        },
        {
            "name": "xiaohongshu-short",
            "platform": "小红书",
            "kind": "短视频",
            "source_url": args.xiaohongshu_short,
            "expected_min": 1,
            "expected_max": 30,
        },
        {
            "name": "xiaohongshu-long",
            "platform": "小红书",
            "kind": "长视频",
            "source_url": args.xiaohongshu_long,
            "expected_min": 90,
            "expected_max": None,
        },
    ]
    if args.only:
        selected = set(args.only)
        cases = [case for case in cases if case["name"] in selected]
    results = [
        _run_case(case, base_options, ffprobe)
        for case in cases
    ]
    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "quality": args.quality,
        "output_dir": str(args.output_dir.resolve()),
        "results": results,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    passed = sum(result["status"] == "PASS" for result in results)
    print(f"REPORT {args.report.resolve()}", flush=True)
    print(f"SUMMARY {passed}/{len(results)} PASS", flush=True)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
