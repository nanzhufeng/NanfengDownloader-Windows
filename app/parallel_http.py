"""Bounded HTTP range transfer. Every segment must prove its exact byte range."""
from __future__ import annotations

import os
import re
import shutil
import tempfile
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path

from .downloader import DownloadStopped, raise_if_cancelled


def parallel_download(url, target: Path, total: int, headers, opener_factory,
                      progress, cancel, *, connections=6) -> bool:
    """Return False without touching target if a CDN rejects/changes a range."""
    if total <= 0: return False
    connections = min(connections, total)
    stop = threading.Event(); lock = threading.Lock()
    counts = [0] * connections
    started = time.monotonic()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.http-ranges-', dir=target.parent) as root:
        root = Path(root)
        def transfer(index):
            start = total * index // connections
            end = total * (index + 1) // connections - 1
            request_headers = {**headers, 'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity'}
            request = urllib.request.Request(url, headers=request_headers)
            with opener_factory().open(request, timeout=8) as response:
                match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                if int(response.status) != 206 or not match or tuple(map(int, match.groups())) != (start, end, total):
                    raise ValueError('CDN没有返回准确的请求分段')
                if response.headers.get('Content-Encoding', 'identity') not in ('', 'identity'):
                    raise ValueError('CDN分段使用了不同的传输编码')
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' in content_type or 'json' in content_type:
                    raise ValueError('CDN分段返回了网页')
                remaining = end - start + 1
                with (root / str(index)).open('wb') as output:
                    while remaining:
                        raise_if_cancelled(cancel)
                        if stop.is_set(): return
                        chunk = response.read(min(1024 * 1024, remaining))
                        if not chunk: raise ValueError('CDN分段提前结束')
                        output.write(chunk); remaining -= len(chunk)
                        with lock: counts[index] += len(chunk)
                    if response.read(1): raise ValueError('CDN分段超出范围')
        def report():
            with lock: downloaded = sum(counts)
            elapsed = max(time.monotonic()-started, .001)
            speed = downloaded/elapsed
            progress({'status':'downloading', 'filename':str(target), 'downloaded_bytes':downloaded,
                      'total_bytes':total, 'connections':connections,
                      'speed':speed,
                      '_speed_str':f'{speed/1024/1024:.1f} MB/s',
                      '_eta_str':f'{max(0, int((total-downloaded)/speed))}秒' if speed else '测速中'})
        try:
            with ThreadPoolExecutor(max_workers=connections, thread_name_prefix='media-range') as pool:
                futures = [pool.submit(transfer, index) for index in range(connections)]
                pending = set(futures)
                try:
                    while pending:
                        raise_if_cancelled(cancel)
                        done, pending = wait(pending, timeout=.15)
                        for future in done: future.result()
                        report()
                finally:
                    stop.set()
            joined = root / 'complete'
            with joined.open('wb') as output:
                for index in range(connections):
                    with (root / str(index)).open('rb') as part: shutil.copyfileobj(part, output)
            if joined.stat().st_size != total: return False
            raise_if_cancelled(cancel)
            os.replace(joined, target)
            report()
            return True
        except DownloadStopped:
            raise
        except Exception:
            # The caller owns the sequential/resumable fallback; never append bad pieces.
            return False
