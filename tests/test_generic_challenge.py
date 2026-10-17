"""Generic challenge recovery stays bounded and preserves truthful UI state."""
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from yt_dlp.utils import DownloadError
from app.downloader import DownloadOptions, DownloadStopped, download_url, find_ffmpeg_dir

CHALLENGE = 'ERROR: [generic] Got HTTP Error 403 caused by Cloudflare anti-bot challenge; try again with --extractor-args "generic:impersonate"'
FORBIDDEN = 'ERROR: [generic] video: Unable to download webpage: HTTP Error 403: Forbidden'


class GenericChallengeTests(unittest.TestCase):
    def options(self, root):
        return DownloadOptions(Path(root), '最佳画质', '软件内登录', None, None)

    def test_challenge_retries_once_with_browser_compatible_extraction(self):
        tools = find_ffmpeg_dir(Path.cwd())
        if not tools:
            self.skipTest('FFmpeg is required for a real media fixture')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / 'fixture.mp4'
            subprocess.run([str(tools/'ffmpeg.exe'), '-nostdin', '-v', 'error', '-f', 'lavfi',
                            '-i', 'color=c=blue:s=160x90:d=1', '-c:v', 'libx264', '-pix_fmt',
                            'yuv420p', '-y', str(fixture)], check=True, timeout=20)
            events, attempts = [], []
            def run(url, options, cancel):
                args = options.get('extractor_args', {}).get('generic', {})
                attempts.append(args)
                if args.get('impersonate') != ['']:
                    raise DownloadError(CHALLENGE)
                self.assertNotIn('cookiefile', options)
                self.assertNotIn('cookiesfrombrowser', options)
                self.assertTrue(options['continuedl'])
                output = root/'out'/'resolved.mp4'
                shutil.copyfile(fixture, output)
                options['progress_hooks'][0]({'status':'finished', 'filename':str(output)})
                return 0
            with patch('app.downloader._run_ytdlp_download', side_effect=run):
                result = download_url('https://example.test/watch/1', self.options(root/'out'), events.append)
            self.assertEqual(len(attempts), 2)
            self.assertEqual(len(result.files), 1)
            self.assertTrue(result.files[0].is_file())
            self.assertTrue(any('浏览器兼容' in event.get('reason', '') for event in events))

    def test_still_blocked_finishes_after_two_requests_with_actionable_error(self):
        with tempfile.TemporaryDirectory() as root, patch('app.downloader._run_ytdlp_download',
                side_effect=[DownloadError(CHALLENGE), DownloadError(FORBIDDEN)]) as run:
            with patch('playwright.sync_api.sync_playwright') as browser, self.assertRaisesRegex(RuntimeError, '浏览器验证') as error:
                download_url('https://example.test/watch/1', self.options(root), lambda _:None)
            self.assertEqual(run.call_count, 2)
            browser.assert_not_called()
            self.assertNotIn('窗口', str(error.exception))
            self.assertNotIn('右键', str(error.exception))

    def test_cancel_during_challenge_does_not_start_another_request(self):
        stopped = False
        def run(*args):
            nonlocal stopped
            stopped = True
            raise DownloadError(CHALLENGE)
        with tempfile.TemporaryDirectory() as root, patch('app.downloader._run_ytdlp_download', side_effect=run) as boundary:
            with self.assertRaises(DownloadStopped):
                download_url('https://example.test/watch/1', self.options(root), lambda _:None, lambda:stopped)
            self.assertEqual(boundary.call_count, 1)

    def test_start_button_failure_keeps_title_and_clears_reconnecting_state(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtTest import QTest
        from app.main import COL_TITLE, COL_STATUS, COL_PROGRESS, COL_SPEED, COL_ETA
        from tests.ui_fixtures import isolated_main_window
        app = QApplication.instance() or QApplication([])
        window = isolated_main_window()
        window.ffmpeg_dir = None
        window.history_page.tools = None
        title = '原作品标题'
        window._add_queue_row('https://example.test/watch/1', '其他网站', title)
        try:
            with patch('app.downloader._run_ytdlp_download', side_effect=DownloadError(CHALLENGE)), \
                 patch.object(window, '_show_download_summary'):
                window.start_button.click()
                deadline = time.monotonic()+5
                while window.worker_thread is not None and time.monotonic()<deadline:
                    QTest.qWait(10)
                self.assertIsNone(window.worker_thread)
                self.assertEqual(window.table.item(0, COL_STATUS).text(), '失败')
                self.assertEqual(window.table.item(0, COL_TITLE).text(), title)
                self.assertEqual(window.table.item(0, COL_PROGRESS).text(), '失败')
                self.assertEqual(window.table.item(0, COL_SPEED).text(), '-')
                self.assertEqual(window.table.item(0, COL_ETA).text(), '-')
                self.assertEqual(window.history_store.query(), [])
                self.assertFalse(window.waiting_for_network)
                self.assertIn('浏览器验证', window.latest_failure_detail)
        finally:
            window.close()
            app.processEvents()
            window.history_page.pool.waitForDone()
