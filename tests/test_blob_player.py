"""Real Chromium reads sources bound to the visible player, never ad traffic."""
import http.server
import threading
import unittest

from app.downloader import DownloadStopped
from app.web_media import resolve_browser_media


class BlobPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                # The browser creates a MediaSource-style blob after page startup.
                binding = 'visible' if self.path != '/unbound' else 'document.createElement("video")'
                drm = 'Object.defineProperty(visible,"mediaKeys",{value:{}});' if self.path == '/drm' else ''
                body = f'''<!doctype html><title>Original work</title><h1>Original work</h1>
                    <video id="visible" style="width:320px;height:180px"></video>
                    <script>
                    const visible=document.querySelector('video');
                    visible.src=URL.createObjectURL(new Blob(['fixture']));
                    window.player={{media:document.createElement('video'),config:{{url:'/advert.mp4'}}}};
                    window.my_player={{media:{binding},config:{{url:'/target.m3u8?token=fixture'}}}};
                    {drm}
                    </script>'''.encode()
                self.send_response(200)
                self.send_header('Content-Type','text/html; charset=utf-8')
                self.send_header('Content-Length',str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self,*args):
                pass
        cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_blob_source_comes_from_its_visible_player_and_retains_work_title(self):
        root=f'http://127.0.0.1:{self.server.server_port}'
        self.assertEqual(resolve_browser_media(root+'/blob'),
                         (root+'/target.m3u8?token=fixture',root+'/blob','Original work'))

    def test_unbound_and_drm_sources_are_not_used_and_can_be_cancelled(self):
        for route in ('/unbound','/drm'):
            with self.subTest(route=route):
                checks=0
                def cancel():
                    nonlocal checks
                    checks+=1
                    return checks>=4
                with self.assertRaises(DownloadStopped):
                    resolve_browser_media(f'http://127.0.0.1:{self.server.server_port}'+route,cancel)
