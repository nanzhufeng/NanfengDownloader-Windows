import tempfile
import unittest
import urllib.request
from unittest.mock import patch
from pathlib import Path


class ParallelHttpTests(unittest.TestCase):
    def test_parallel_ranges_reassemble_exactly_and_report_real_progress(self):
        from app.parallel_http import parallel_download
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread
        data = bytes(range(256)) * 4096
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                requested = self.headers.get('Range')
                start, end = map(int, requested[6:].split('-')) if requested else (0, len(data)-1)
                if self.path == '/ignore' or not requested:
                    self.send_response(200); self.send_header('Content-Length', str(len(data)))
                    self.send_header('Accept-Ranges', 'bytes')
                    self.end_headers(); payload = data
                else:
                    self.send_response(206)
                    range_end = end - 1 if self.path == '/wrong-range' else end
                    self.send_header('Content-Range', f'bytes {start}-{range_end}/{len(data)}')
                    self.send_header('Content-Length', str(end-start+1))
                    self.end_headers(); payload=data[start:end+1]
                try: self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as root:
                target = Path(root)/'media.mp4'; progress=[]
                self.assertTrue(parallel_download(f'http://127.0.0.1:{server.server_port}/media', target,
                    len(data), {}, urllib.request.build_opener, progress.append, None, connections=4))
                self.assertEqual(target.read_bytes(), data)
                self.assertEqual(progress[-1]['downloaded_bytes'], len(data))
                self.assertEqual(list(Path(root).iterdir()), [target])
                from app.douyin import _download_binary
                from app.downloader import DownloadOptions
                fallback = Path(root)/'fallback.mp4'
                with patch('app.douyin.DOUYIN_PARALLEL_MIN_BYTES', 1):
                    _download_binary(f'http://127.0.0.1:{server.server_port}/ignore', fallback,
                        DownloadOptions(Path(root), 'best', 'anonymous', None, None), lambda _: None)
                self.assertEqual(fallback.read_bytes(), data, 'range rejection must really fall back to the full sequential response')
                fallback.unlink()
                for route in ('ignore', 'wrong-range'):
                    self.assertFalse(parallel_download(f'http://127.0.0.1:{server.server_port}/{route}', target,
                        len(data), {}, urllib.request.build_opener, lambda _: None, None, connections=4))
                    self.assertEqual(target.read_bytes(), data, 'bad responses must never overwrite the existing target')
                    self.assertEqual(list(Path(root).iterdir()), [target])
                from app.downloader import DownloadStopped
                with self.assertRaises(DownloadStopped):
                    parallel_download(f'http://127.0.0.1:{server.server_port}/media', target,
                        len(data), {}, urllib.request.build_opener, lambda _: None, lambda: True, connections=4)
                self.assertEqual(list(Path(root).iterdir()), [target])
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__': unittest.main()
