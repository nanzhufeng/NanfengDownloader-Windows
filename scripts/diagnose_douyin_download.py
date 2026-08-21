"""对单条公开抖音视频执行隔离下载诊断，不写入用户正式下载目录。"""

from __future__ import annotations

import argparse
import tempfile
import time
import traceback
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.douyin import download_douyin_url
from app.downloader import DownloadOptions, find_ffmpeg_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="诊断单条抖音下载的续传与媒体校验")
    parser.add_argument("url")
    parser.add_argument("--quality", default="720p 及以下")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir or Path(tempfile.mkdtemp(prefix="nanfeng-douyin-diagnostic-"))
    print(f"DIAGNOSTIC_DIR={output_dir}", flush=True)
    options = DownloadOptions(
        output_dir=output_dir,
        quality=args.quality,
        cookie_mode="软件内登录",
        cookie_file=None,
        ffmpeg_dir=find_ffmpeg_dir(PROJECT_ROOT),
    )
    last_print = 0.0

    def progress(info: dict[str, object]) -> None:
        nonlocal last_print
        now = time.monotonic()
        status = str(info.get("status") or "")
        if status not in {"retrying", "finished"} and now - last_print < 3:
            return
        last_print = now
        print(
            "EVENT "
            f"status={status} downloaded={info.get('downloaded_bytes')} total={info.get('total_bytes')} "
            f"speed={info.get('_speed_str')} eta={info.get('_eta_str')} reason={info.get('reason')}",
            flush=True,
        )

    try:
        result = download_douyin_url(args.url, options, progress)
    except Exception as exc:
        print(f"ERROR_TYPE={type(exc).__name__}", flush=True)
        print(f"ERROR={exc}", flush=True)
        traceback.print_exc()
        return 1
    print(f"SUCCESS_FILES={','.join(str(path) for path in result.files)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
