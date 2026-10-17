"""Exercise the actual start button and Qt worker lifecycle, without a network."""
import os
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from app.downloader import DownloadResult
from tests.ui_fixtures import isolated_main_window


class DownloadStartTests(unittest.TestCase):
    def test_parsed_title_reaches_queue_history_and_is_not_replaced_by_filename(self):
        app = QApplication.instance() or QApplication([])
        window = isolated_main_window()
        from app.main import COL_TITLE, COL_CREATOR
        url = 'https://www.douyin.com/video/7696764946419289395'
        placeholder = '抖音作品 7696764946419289395（下载时解析）'
        title = '3个月长测收官，奥迪E7X、问界M6、理想i6 怎么选？ #汽车人共创计划 #dou是好车'
        try:
            window._add_queue_row(url, '抖音', placeholder)
            output = Path(window.history_store.path.parent) / 'filesystem-safe.mp4'
            output.write_bytes(b'fixture')
            window.history_store.archive('old', title=placeholder, url=url, platform='抖音',
                creator='待解析', quality='自动识别', files=[output], completed_at=1)
            window._on_item_started(0)
            window._on_item_progress(0, {'status':'resolving','info_dict':{'title':title,'uploader':'实测作者'}})
            window._on_item_progress(0, {'status':'downloading','filename':str(output),
                'downloaded_bytes':1,'total_bytes':2})
            self.assertEqual(window.table.item(0,COL_TITLE).text(), title)
            self.assertEqual(window.table.item(0,COL_CREATOR).text(), '实测作者')
            window._on_item_finished(0, output.name, [str(output)])
            self.assertEqual(window.table.rowCount(), 0)
            self.assertEqual({record.title for record in window.history_store.query()}, {title})
            self.assertEqual(tuple(Path(f).resolve() for f in window.history_store.query()[0].files), (output.resolve(),))
            self.assertTrue(output.exists())
        finally:
            window.close(); app.processEvents()

    def test_start_button_runs_worker_and_archives_even_when_history_is_open(self):
        # Keep cold third-party import time outside the Qt button/worker deadline.
        import yt_dlp.utils
        app = QApplication.instance() or QApplication([])
        window = isolated_main_window()
        window.history_page.tools = None
        # Network and installed media tools are external boundaries of this start-flow test.
        window.ffmpeg_dir = None
        window._add_queue_row('https://www.douyin.com/video/7696541371562547049', '抖音', '原始标题')
        started, release = threading.Event(), threading.Event()
        errors = []
        def download(url, options, progress, cancelled):
            started.set()
            if not release.wait(3): raise RuntimeError('test did not release worker')
            output = options.output_dir / 'downloaded.mp4'
            output.write_bytes(b'isolated media fixture')
            return DownloadResult(files=[output])
        window.show(); app.processEvents()
        try:
            with patch('app.main.download_url', side_effect=download), \
                 patch.object(window, '_show_download_summary'), \
                 patch.object(sys, 'excepthook', side_effect=lambda *args: errors.append(args)):
                QTest.mouseClick(window.start_button, Qt.LeftButton)
                deadline = time.monotonic() + 2
                while not started.is_set() and not errors and time.monotonic() < deadline:
                    QTest.qWait(10)
                self.assertFalse(errors, 'start button raised before worker startup: ' + repr(errors))
                self.assertTrue(started.is_set(), 'clicking Start must actually reach the download worker')
                window.history_button.click(); app.processEvents()
                self.assertTrue(window.worker_thread.isRunning())
                release.set()
                deadline = time.monotonic() + 3
                while window.worker_thread is not None and time.monotonic() < deadline:
                    QTest.qWait(10)
                self.assertIsNone(window.worker_thread)
                self.assertEqual(window.table.rowCount(), 0)
                self.assertEqual(len(window.history_store.query()), 1)
                self.assertEqual(window.history_store.query()[0].title, '原始标题')
                self.assertIs(window.pages.currentWidget(), window.history_page)
                self.assertTrue(window.start_button.isEnabled())
                self.assertFalse(errors)
        finally:
            release.set()
            if window.worker_thread is not None:
                deadline = time.monotonic() + 4
                while window.worker_thread is not None and time.monotonic() < deadline: QTest.qWait(10)
            window.history_page.pool.waitForDone()
            window.close(); app.processEvents()


if __name__ == '__main__':
    unittest.main()
