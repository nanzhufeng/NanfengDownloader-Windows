"""Original work title survives a real browser -> CDN -> Qt history download."""
import functools
import http.server
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

# Warm lazy imports before the native Qt event loop holds the calling thread.
import yt_dlp
import playwright.sync_api

from app.downloader import DownloadOptions, download_url, find_ffmpeg_dir
from tests.ui_fixtures import isolated_main_window


class GenericOriginalTitleTests(unittest.TestCase):
    def test_dynamic_work_title_reaches_filename_and_history_instead_of_cdn_hash(self):
        from PySide6.QtWidgets import QApplication
        tools=find_ffmpeg_dir(Path.cwd())
        self.assertIsNotNone(tools)
        app=QApplication.instance() or QApplication([])
        title='原视频标题：设备演示 #细节'
        media_id='597868911b17134bd2a65d4ec40ef79d'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            web=root/'web'
            web.mkdir()
            subprocess.run([str(tools/'ffmpeg.exe'),'-nostdin','-v','error','-f','lavfi',
                '-i','color=c=blue:s=160x90:d=1','-c:v','libx264','-pix_fmt','yuv420p',
                str(web/(media_id+'.mp4'))],check=True,timeout=20)
            encoded=','.join(str(ord(c)) for c in '/'+media_id+'.mp4')
            (web/'watch.html').write_text(f'''<!doctype html><meta charset="utf-8">
                <title>{title}</title><h1>{title}</h1><video style="width:320px;height:180px"></video>
                <script>const media=document.querySelector('video');
                media.src=URL.createObjectURL(new Blob(['fixture']));
                window.my_player={{media:media,config:{{url:String.fromCharCode({encoded})}}}};
                </script>''',encoding='utf-8')
            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(web)))
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            output=root/'output'
            url=f'http://127.0.0.1:{server.server_port}/watch.html'
            window=None
            try:
                updates=[]
                result=download_url(url,DownloadOptions(output,'最佳画质','不使用登录态',None,tools),updates.append)
                window=isolated_main_window()
                window.ffmpeg_dir=tools
                window.history_page.tools=tools
                window._add_queue_row(url,'其他网站','网页媒体（下载时解析）')
                window._on_item_started(0)
                for update in updates:
                    window._on_item_progress(0,update)
                window._on_item_finished(0,result.files[0].name,[str(p) for p in result.files])
                records=window.history_store.query()
                self.assertEqual(len(records),1,window.latest_failure_detail)
                self.assertEqual(records[0].title,title)
                self.assertNotIn(media_id,Path(records[0].files[0]).name)
                self.assertTrue(Path(records[0].files[0]).is_file())
            finally:
                if window:
                    window.close()
                    app.processEvents()
                    window.history_page.pool.waitForDone()
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
