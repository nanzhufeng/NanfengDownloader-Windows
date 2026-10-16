import os
import unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from app.main import DownloadWorker, COL_PROGRESS, COL_TITLE
from tests.ui_fixtures import isolated_main_window


class UiResponsivenessTests(unittest.TestCase):
    def test_progress_burst_keeps_latest_row_and_coalesces_batch_indicator(self):
        app = QApplication.instance() or QApplication([])
        window = isolated_main_window()
        try:
            window._add_queue_row('https://example.test/video', '抖音', '原始标题')
            window.active_download_rows = {0}
            worker = DownloadWorker([], None)
            worker.item_progress.connect(window._on_item_progress)
            values = []
            window.main_progress.valueChanged.connect(values.append)
            for amount in range(1, 1001):
                worker.item_progress.emit(0, {'status':'downloading', 'downloaded_bytes':amount,
                    'total_bytes':1000, '_speed_str':'8 MB/s', '_eta_str':'1s',
                    'info_dict':{'title':'源视频原标题','uploader':'作者'}})
            QTest.qWait(160)
            self.assertEqual(window.table.item(0, COL_PROGRESS).text(), '99%')
            self.assertEqual(window.table.item(0, COL_TITLE).text(), '源视频原标题')
            self.assertEqual(window.main_progress.value(), 99)
            self.assertLessEqual(len(values), 2, 'a transfer burst must not repaint the aggregate indicator for every chunk')
        finally:
            window.close(); app.processEvents(); window.history_page.pool.waitForDone()

    def test_search_with_same_results_clears_batch_checks_and_returns_new_archive(self):
        app = QApplication.instance() or QApplication([])
        window = isolated_main_window(); page = window.history_page; page.tools = None
        try:
            window.history_store.archive('one', title='视频性能夹具', url='https://example.test/one',
                platform='抖音', creator='作者', quality='自动', files=['missing-fixture.mp4'], completed_at=100)
            window.show(); window.history_button.click(); app.processEvents()
            page.bulk.click(); page.cards['one']['check'].click()
            self.assertEqual(page.selection_count.text(), '已选 1 项')
            page.search.setText('性能'); QTest.qWait(220)
            self.assertEqual(page.selection_count.text(), '已选 0 项')
            self.assertFalse(page.cards['one']['check'].isChecked())
            self.assertEqual([record.id for record in page.records], ['one'])
            window.history_store.archive('two', title='新性能夹具', url='https://example.test/two',
                platform='抖音', creator='作者', quality='自动', files=['missing-fixture.mp4'], completed_at=200)
            page.notify_changed(); app.processEvents()
            self.assertEqual([record.id for record in page.records], ['two', 'one'])
        finally:
            window.close(); app.processEvents(); page.pool.waitForDone()
