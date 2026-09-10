import hashlib
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from app.torrent import read_torrent, torrent_job, download_torrent, local_torrent_path
from app.downloader import DownloadOptions, find_aria2c


def encode(value):
    if isinstance(value, bytes):
        return str(len(value)).encode()+b':'+value
    if isinstance(value, int):
        return b'i'+str(value).encode()+b'e'
    if isinstance(value, list):
        return b'l'+b''.join(map(encode,value))+b'e'
    return b'd'+b''.join(encode(k)+encode(v) for k,v in sorted(value.items()))+b'e'


class TorrentTests(unittest.TestCase):
    def test_file_uri_decodes_once_and_reads_same_torrent(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'[测试] 100%25.torrent'
            path.write_bytes(encode({b'info':{b'name':b'video.bin',b'length':3}}))
            self.assertEqual(local_torrent_path(path.as_uri()), path)
            self.assertEqual(read_torrent(path.as_uri()), read_torrent(path))
            self.assertEqual(local_torrent_path('"'+str(path)+'"'), path)
        with self.assertRaises(ValueError):
            local_torrent_path('file://remote-server/share/file.torrent')

    def test_reject_path_traversal(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'bad.torrent'
            path.write_bytes(encode({b'info':{b'name':b'..',b'length':3}}))
            with self.assertRaises(ValueError):
                read_torrent(path)

    @unittest.skipUnless(find_aria2c(), 'aria2 unavailable')
    def test_real_engine_downloads_local_webseed_and_retains_filename(self):
        payload = b'local controlled torrent fixture\n'*2048
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                start, end = 0, len(payload)-1
                if self.headers.get('Range'):
                    values = self.headers['Range'].removeprefix('bytes=').split('-')
                    start = int(values[0]); end = int(values[1]) if values[1] else end
                    self.send_response(206)
                    self.send_header('Content-Range', f'bytes {start}-{end}/{len(payload)}')
                else:
                    self.send_response(200)
                self.send_header('Content-Length',str(end-start+1)); self.end_headers()
                self.wfile.write(payload[start:end+1])
            def log_message(self,*args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as root:
                path = Path(root)/'sample.torrent'
                info = {b'name':b'original.bin',b'length':len(payload),b'piece length':16384,
                        b'pieces':b''.join(hashlib.sha1(payload[i:i+16384]).digest() for i in range(0,len(payload),16384))}
                raw = encode({b'info':info,b'url-list':[f'http://127.0.0.1:{server.server_port}/original.bin'.encode()]})
                path.write_bytes(raw)
                self.assertEqual(read_torrent(path)[1][0][1].name,'original.bin')
                events = []; started = time.monotonic()
                result = download_torrent(torrent_job(path,[1],raw), DownloadOptions(Path(root)/'out','自动识别','',None,None),events.append,lambda:time.monotonic()-started>25)
                self.assertEqual(result.files[0].name,'original.bin')
                self.assertEqual(result.files[0].read_bytes(),payload)
                self.assertEqual(events[-1]['downloaded_bytes'],len(payload))
        finally:
            server.shutdown(); server.server_close(); thread.join()
