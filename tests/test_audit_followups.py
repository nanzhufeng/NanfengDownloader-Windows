import unittest
import tempfile
import subprocess
import json
from pathlib import Path
from unittest.mock import patch
from app.downloader import DownloadOptions, DownloadResult
from app.quality_fallback import verify_output_resolution
from app import auth_profile


class AuditFollowupsTests(unittest.TestCase):
    def test_auto_quality_downloads_without_prompt_and_names_actual_dimensions(self):
        from app.quality_fallback import download_with_quality_choice
        for width, height in [(1280, 720), (1920, 1080)]:
            with self.subTest(height=height), tempfile.TemporaryDirectory() as root:
                source = Path(root) / 'sample 1080p.mp4'
                source.touch()
                options = DownloadOptions(Path(root), '自动识别', '', None, Path(root))
                probe = subprocess.CompletedProcess([], 0, json.dumps({'streams': [{'width': width, 'height': height}]}).encode())
                def download(url, opts, progress, cancel):
                    self.assertEqual(opts.quality, '最佳画质')
                    return DownloadResult([source])
                def choose(quality):
                    self.fail('自动画质不应弹出选择对话框')
                with patch('app.quality_fallback.subprocess.run', return_value=probe):
                    result = download_with_quality_choice('https://example.test/video', options, lambda e: None, lambda: False, choose, download)
                self.assertEqual(result.files[0].name, f'sample {height}p.mp4')

    def test_cookie_cleanup_does_not_touch_live_owner(self):
        with tempfile.TemporaryDirectory() as root:
            live = Path(root)/'runtime-cookies-123-youtube-live.txt'
            dead = Path(root)/'runtime-cookies-456-youtube-dead.txt'
            live.write_text('fixture'); dead.write_text('fixture')
            with patch.object(auth_profile,'runtime_cookie_dir',return_value=Path(root)), patch.object(auth_profile,'_export_owner_exited',side_effect=lambda p:p==dead):
                auth_profile.cleanup_runtime_cookie_exports()
            self.assertTrue(live.exists())
            self.assertFalse(dead.exists())

    def test_probe_corrects_new_filename_and_rejects_over_limit(self):
        with tempfile.TemporaryDirectory() as root:
            source=Path(root)/'sample 1080p.mp4'
            source.write_bytes(b'fixture')
            options=DownloadOptions(Path(root),'720p 及以下','',None,Path(root))
            probe=subprocess.CompletedProcess([],0,json.dumps({'streams':[{'width':1280,'height':720}]}).encode())
            with patch('app.quality_fallback.subprocess.run',return_value=probe):
                result=verify_output_resolution(DownloadResult([source]),options,lambda e:None)
            self.assertEqual(result.files[0].name,'sample 720p.mp4')
            probe.stdout=json.dumps({'streams':[{'width':1920,'height':1080}]}).encode()
            with patch('app.quality_fallback.subprocess.run',return_value=probe), self.assertRaisesRegex(RuntimeError,'源站没有符合'):
                verify_output_resolution(result,options,lambda e:None)
