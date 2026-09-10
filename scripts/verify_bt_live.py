"""Bounded user-authorized torrent connectivity verification."""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.torrent import read_torrent, torrent_job, download_torrent
from app.downloader import DownloadOptions, DownloadStopped

if __name__ == '__main__':
    path = Path(sys.argv[1])
    raw, files = read_torrent(path)
    start = time.monotonic()
    seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    state = {'last': 0, 'bytes': 0}
    def progress(event):
        state['bytes'] = event.get('downloaded_bytes', 0)
        if time.monotonic() - state['last'] > 10:
            print({k: event.get(k) for k in ['status', 'downloaded_bytes', 'connections', 'seeders', 'diagnostic', '_speed_str', 'reason']}, flush=True)
            state['last'] = time.monotonic()
    print('LIMIT', seconds, 'seconds or 8 MiB; first file only', flush=True)
    try:
        download_torrent(torrent_job(path, [1], raw), DownloadOptions(Path(__file__).resolve().parents[1]/'.verification-downloads/bt-live', '自动识别', '', None, None), progress,
                         lambda: time.monotonic()-start > seconds or state['bytes'] >= 8*1024*1024, diagnostics=True)
    except DownloadStopped:
        print('STOPPED', state['bytes'], 'bytes', round(time.monotonic()-start, 1), 'seconds', flush=True)
