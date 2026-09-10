"""Bounded in-memory HLS transport benchmark; does not save media."""
import concurrent.futures
import json
import time
import urllib.request
import threading
import hashlib
from urllib.parse import urljoin


def measure(url, workers, count=48, reuse=False):
    for _ in range(3):
        with urllib.request.urlopen(url, timeout=15) as response:
            manifest = response.read().decode()
        links = [urljoin(url, line) for line in manifest.splitlines() if line and not line.startswith('#')]
        if '#EXT-X-STREAM-INF' not in manifest:
            break
        url = links[0]
    local = threading.local()
    sessions = []
    def fetch(link):
        if reuse:
            import requests
            if not hasattr(local, 'session'):
                local.session = requests.Session()
                sessions.append(local.session)
            response = local.session.get(link, timeout=(10, 20), stream=True)
            response.raise_for_status()
            chunks = response.iter_content(1024 * 1024)
        else:
            response = urllib.request.urlopen(link, timeout=20)
            chunks = iter(lambda: response.read(1024 * 1024), b'')
        with response:
            total = 0
            digest = hashlib.sha256()
            for data in chunks:
                total += len(data)
                digest.update(data)
            return total, digest.hexdigest()
    start = time.monotonic()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(fetch, links[:count]))
    finally:
        for session in sessions:
            session.close()
    size = sum(item[0] for item in results)
    elapsed = time.monotonic() - start
    return dict(reuse=reuse, segments=len(results), workers=workers, bytes=size, seconds=round(elapsed, 3), MiB_s=round(size/elapsed/1048576, 3), digest=hashlib.sha256(''.join(x[1] for x in results).encode()).hexdigest())


if __name__ == '__main__':
    import sys
    for reuse, workers in ((False,16), (True,16), (True,8), (True,16)):
        try:
            print(json.dumps(measure(sys.argv[1], workers, int(sys.argv[2]) if len(sys.argv)>2 else 48, reuse)), flush=True)
        except Exception as exc:
            print(json.dumps({'reuse':reuse,'workers':workers,'error':type(exc).__name__}), flush=True)
