"""Completion leaves the visible queue only after durable history archival."""
import json
from contextlib import ExitStack
import os
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import Qt,QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app.main import MainWindow,COL_LINK,COL_STATUS,COL_SELECT,COL_LOCATE,SETTING_QUEUE_STATE
from app.downloader import DownloadResult
from tests.ui_fixtures import isolated_main_window


class CompletedQueueRetirementTests(unittest.TestCase):
    def wait_for(self, predicate, seconds=4):
        deadline=time.monotonic()+seconds
        while not predicate() and time.monotonic()<deadline:QTest.qWait(10)
        self.assertTrue(predicate())

    def test_success_disappears_mid_batch_without_changing_later_task_identity(self):
        import yt_dlp.utils
        app=QApplication.instance() or QApplication([])
        window=isolated_main_window();window.ffmpeg_dir=None;window.history_page.tools=None
        root=Path(window.settings.fileName()).parent
        names=('first','unselected','second','existing','failure')
        urls={name:f'https://www.youtube.com/watch?v={name}' for name in names}
        for name in names:window._add_queue_row(urls[name],'YouTube',name)
        window.table.item(1,COL_SELECT).setCheckState(Qt.Unchecked)
        window.table.cellWidget(2,5).setCurrentText('720p 及以下')
        waiting,release=threading.Event(),threading.Event();calls=[];errors=[]
        existing=root/'existing.mp4';existing.write_bytes(b'fixture')
        def download(url,options,progress,cancelled):
            calls.append((url,options.quality))
            if url==urls['second']:
                waiting.set()
                if not release.wait(5):raise RuntimeError('fixture release timed out')
            if url==urls['failure']:raise RuntimeError('controlled media failure')
            if url==urls['existing']:return DownloadResult(files=[existing],skipped=True)
            output=root/(('first' if url==urls['first'] else 'second')+'.mp4')
            output.write_bytes(b'fixture')
            return DownloadResult(files=[output])
        window.show();app.processEvents()
        patches=ExitStack()
        patches.enter_context(patch('app.main.download_url',side_effect=download))
        summary=patches.enter_context(patch.object(window,'_show_download_summary'))
        patches.enter_context(patch('sys.excepthook',side_effect=lambda *args:errors.append(args)))
        try:
            window.start_button.click();self.wait_for(waiting.is_set)
            visible=[window.table.item(r,COL_LINK).text() for r in range(window.table.rowCount()) if not window.table.isRowHidden(r)]
            self.assertNotIn(urls['first'],visible)
            self.assertEqual(visible,[urls[name] for name in names[1:]])
            self.assertEqual([record.url for record in window.history_store.query()],[urls['first']])
            saved=json.loads(window.settings.value(SETTING_QUEUE_STATE))
            self.assertNotIn(urls['first'],[row['url'] for row in saved['rows']])
            window.history_button.click();app.processEvents()
            release.set();self.wait_for(lambda:window.worker_thread is None)
            self.assertFalse(errors)
            self.assertEqual(calls,[(urls['first'],'最佳画质'),(urls['second'],'720p 及以下'),(urls['existing'],'最佳画质'),(urls['failure'],'最佳画质')])
            self.assertEqual([window.table.item(r,COL_LINK).text() for r in range(window.table.rowCount())],[urls['unselected'],urls['existing'],urls['failure']])
            self.assertEqual(window.table.item(2,COL_STATUS).text(),'失败')
            self.assertEqual({record.url:record.title for record in window.history_store.query()},{urls['first']:'first',urls['second']:'second'})
            self.assertTrue((root/'first.mp4').exists());self.assertTrue((root/'second.mp4').exists())
            self.assertEqual(summary.call_args.args[0],{'完成':2,'已跳过':1,'失败':1,'已停止':0})
            with patch('app.main.reveal_file_in_explorer') as reveal:
                window.table.cellWidget(1,COL_LOCATE).click();reveal.assert_called_once_with(existing.resolve())
        finally:
            release.set()
            if window.worker_thread is not None:self.wait_for(lambda:window.worker_thread is None,6)
            window.close();app.processEvents();window.history_page.pool.waitForDone()
            patches.close()

    def test_archive_failure_keeps_completed_file_recoverable_until_restart(self):
        app=QApplication.instance() or QApplication([])
        window=isolated_main_window();window.history_page.tools=None
        settings_path=window.settings.fileName();root=Path(settings_path).parent
        media=root/'done.mp4';media.write_bytes(b'fixture')
        window._add_queue_row('https://www.youtube.com/watch?v=archive-failure','YouTube','完成作品')
        try:
            with patch.object(window.history_store,'archive',side_effect=OSError('history unavailable')):
                window._on_item_finished(0,media.name,[str(media)])
            self.assertEqual(window.table.rowCount(),1);self.assertFalse(window.table.isRowHidden(0))
            self.assertTrue(media.exists());self.assertEqual(window.history_store.query(),[])
            window.close();app.processEvents()
            restored=MainWindow(settings=QSettings(settings_path,QSettings.IniFormat))
            try:
                self.assertEqual(restored.table.rowCount(),0)
                self.assertEqual([record.title for record in restored.history_store.query()],['完成作品'])
                self.assertTrue(media.exists())
            finally:restored.close();app.processEvents();restored.history_page.pool.waitForDone()
        finally:window.close();app.processEvents();window.history_page.pool.waitForDone()
