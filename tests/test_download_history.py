import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


class DownloadHistoryTests(unittest.TestCase):
    def test_title_repair_only_touches_matching_generated_placeholders(self):
        from app.history_store import HistoryStore
        with tempfile.TemporaryDirectory() as root:
            store=HistoryStore(Path(root)/'history.sqlite3')
            placeholder='抖音作品 123（下载时解析）'
            for id,title,url in [('old',placeholder,'https://example.test/1'),('normal','正常原标题','https://example.test/1'),
                                 ('other',placeholder,'https://example.test/2')]:
                store.archive(id,title=title,url=url,platform='抖音',creator='待解析',quality='best',
                    files=['C:/media.mp4'],completed_at=1)
            store.set_favorite('old',True)
            self.assertEqual(store.correct_placeholder_titles('https://example.test/1','真实原标题？ #标签','真实作者'),1)
            records={r.id:r for r in store.query()}
            self.assertEqual(records['old'].title,'真实原标题？ #标签')
            self.assertTrue(records['old'].favorite)
            self.assertEqual(records['normal'].title,'正常原标题')
            self.assertEqual(records['other'].title,placeholder)
            self.assertEqual(store.correct_placeholder_titles('https://example.test/1',placeholder),0)

    def test_schema_upgrade_preserves_favorites_and_reports_only_real_values(self):
        import sqlite3,json
        from app.history_store import HistoryStore
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'history.sqlite3'
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE history(id TEXT PRIMARY KEY,title TEXT,url TEXT,platform TEXT,creator TEXT,quality TEXT,files TEXT,completed_at REAL,favorite INTEGER,kind TEXT)')
                db.execute('INSERT INTO history VALUES (?,?,?,?,?,?,?,?,?,?)',('old','旧作品','https://example.test','抖音','','best','["C:/media.mp4"]',123,1,'video'))
                db.execute('PRAGMA user_version=1')
            db.close()
            store=HistoryStore(path);old=store.query()[0]
            self.assertTrue(old.favorite);self.assertEqual(old.completed_at,123);self.assertEqual(old.report,{})
            store.archive('new',title='新作品',url='https://example.test/2',platform='抖音',creator='',quality='best',files=['C:/media2.mp4'],completed_at=456,
                report={'network_bytes':1024,'elapsed':2.,'average_speed':512.,'peak_speed':700.,'connections':6,'retries':0})
            self.assertEqual(HistoryStore(path).query()[0].report['network_bytes'],1024)

    def test_media_worker_cancellation_reaps_its_child_promptly(self):
        import sys, threading, time
        from app.history_page import _run_tool
        cancelled = threading.Event()
        timer = threading.Timer(0.15, cancelled.set)
        started = time.monotonic(); timer.start()
        try:
            with self.assertRaises(InterruptedError):
                _run_tool([sys.executable, '-c', 'import time; time.sleep(20)'], timeout=25, cancel=cancelled)
            self.assertLess(time.monotonic() - started, 2)
        finally: timer.cancel()

    def test_archive_survives_restart_and_delete_keeps_media(self):
        from app.history_store import HistoryStore
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            media = root / 'finished.mp4'
            media.write_bytes(b'fixture')
            store = HistoryStore(root / 'history.sqlite3')
            store.archive('attempt-1', title='作品标题', url='https://example.test/1',
                          platform='直链', creator='作者', quality='自动识别',
                          files=[str(media)], completed_at=100)
            store.set_favorite('attempt-1', True)
            store.archive('attempt-1', title='作品标题', url='https://example.test/1',
                          platform='直链', creator='作者', quality='自动识别',
                          files=[str(media)], completed_at=101)
            reloaded = HistoryStore(root / 'history.sqlite3')
            records = reloaded.query()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].completed_at, 100)
            self.assertTrue(records[0].favorite)
            reloaded.delete(['attempt-1'])
            self.assertEqual(reloaded.query(), [])
            self.assertTrue(media.exists())

    def test_filters_favorites_and_literal_search(self):
        from app.history_store import HistoryStore
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / 'history.sqlite3')
            for id, title, platform, suffix, completed in [
                ('1', 'Title 100%_done', 'YouTube', '.mp4', 1000000),
                ('2', 'Older video', '抖音', '.mp4', 1),
                ('3', 'Music', 'YouTube', '.mp3', 1000000),
            ]:
                store.archive(id, title=title, url=f'https://example.test/{id}', platform=platform,
                              creator='作者', quality='自动识别', files=[directory + '/' + id + suffix], completed_at=completed)
                store.set_favorite(id, True)
            self.assertEqual([r.id for r in store.query(query='100%_')], ['1'])
            self.assertEqual([r.id for r in store.query(platform='YouTube', days=7, now=1000000, favorites=True)], ['1'])
            self.assertEqual([r.id for r in store.query(query='older')], ['2'])
            self.assertEqual([r.id for r in store.query(favorites=True)], ['1', '2'])

    def test_legacy_import_never_invents_time_or_resurrects_deleted_records(self):
        from app.history_store import HistoryStore
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / 'history.sqlite3')
            payload = {'version': 1, 'rows': [
                {'url': 'https://example.test/video', 'title': '旧作品', 'status': '完成', 'output_files': [directory + '/old.mp4']},
                {'url': 'https://example.test/failed', 'status': '失败', 'output_files': [directory + '/bad.mp4']},
            ]}
            store.import_queue(payload)
            record, = store.query()
            self.assertIsNone(record.completed_at)
            self.assertEqual(store.query(days=30), [])
            store.delete([record.id]); store.import_queue(payload)
            self.assertEqual(store.query(), [])

    def test_missing_partial_and_disconnected_media_are_distinct(self):
        from app.history_store import file_availability
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); present = root / 'present.mp4'; present.write_bytes(b'123')
            missing = str(root / 'missing.mp4')
            self.assertEqual(file_availability([str(present)]), ('present', 3))
            self.assertEqual(file_availability([missing]), ('missing', 0))
            self.assertEqual(file_availability([str(present), missing]), ('partial', None))
            with patch('pathlib.Path.is_dir', return_value=False):
                self.assertEqual(file_availability([missing]), ('unavailable', None))


class HistoryNavigationTests(unittest.TestCase):
    def test_history_search_favorites_and_confirmed_bulk_delete(self):
        import os, time
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        from PySide6.QtTest import QTest
        from tests.ui_fixtures import isolated_main_window
        app = QApplication.instance() or QApplication([])
        window = isolated_main_window(); page = window.history_page; page.tools = None
        root = Path(window.settings.fileName()).parent
        media = root / 'sample.mp4'; media.write_bytes(b'fixture')
        try:
            for id, title, platform in [('a', '收藏作品', 'YouTube'), ('b', '搜索目标', '抖音'), ('c', '其他作品', 'YouTube')]:
                window.history_store.archive(id, title=title, url=f'https://example.test/{id}',
                    platform=platform, creator='作者', quality='自动识别', files=[str(media)], completed_at=time.time())
            window.history_store.set_favorite('a', True)
            window.show(); window.history_button.click(); app.processEvents()
            page.search.setText('搜索目标'); QTest.qWait(220)
            self.assertEqual([record.id for record in page.records], ['b'])
            page.platform.setCurrentIndex(page.platform.findData('抖音'))
            page.favorites.click(); app.processEvents()
            self.assertEqual(page.search.text(), '')
            self.assertIsNone(page.platform.currentData())
            self.assertEqual([record.id for record in page.records], ['a'])
            self.assertFalse(page.cleanup.isVisible())
            page.favorites.click(); page.bulk.click(); app.processEvents()
            circle=page.cards['b']['check']
            self.assertIs(circle,page.cards['b']['status_mark'])
            circle.click()
            self.assertEqual(page.selected,{'b'})
            self.assertEqual(page.selection_count.text(),'已选 1 项')
            page._media_ready('b',{'state':'present','size':media.stat().st_size})
            self.assertTrue(circle.isChecked())
            self.assertIs(page.selection_bar.parentWidget(),page.search.parentWidget())
            QTimer.singleShot(0, lambda: app.activeModalWidget().accept())
            page.delete_selected.click(); app.processEvents()
            self.assertEqual({record.id for record in window.history_store.query()}, {'a', 'c'})
            self.assertTrue(media.exists())
        finally:
            page.pool.waitForDone(); window.close(); app.processEvents()

    def test_cleanup_checks_files_and_keeps_existing_media(self):
        import os, time
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        from PySide6.QtTest import QTest
        from tests.ui_fixtures import isolated_main_window
        app = QApplication.instance() or QApplication([])
        window = isolated_main_window(); page = window.history_page; page.tools = None
        root = Path(window.settings.fileName()).parent
        media = root / 'sample.mp4'; media.write_bytes(b'fixture')
        timer = QTimer(); timer.setInterval(10)
        def confirm():
            dialog = app.activeModalWidget()
            if dialog:
                dialog.accept(); timer.stop()
        timer.timeout.connect(confirm)
        try:
            for id, file in [('good', media), ('missing', root / 'missing.mp4')]:
                window.history_store.archive(id, title=id, url=f'https://example.test/{id}',
                    platform='直链', creator='', quality='自动识别', files=[str(file)], completed_at=time.time())
            window.show(); window.history_button.click(); app.processEvents()
            timer.start(); page.cleanup.click()
            deadline = time.monotonic() + 3
            while page._busy and time.monotonic() < deadline: QTest.qWait(10)
            self.assertFalse(page._busy)
            self.assertEqual([record.id for record in window.history_store.query()], ['good'])
            self.assertTrue(media.exists())
        finally:
            timer.stop(); page.pool.waitForDone(); window.close(); app.processEvents()

    def test_success_archives_original_title_and_navigation_preserves_input(self):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        from tests.ui_fixtures import isolated_main_window
        from app.main import MainWindow
        app = QApplication.instance() or QApplication([])
        window = isolated_main_window()
        try:
            window._add_queue_row('https://www.youtube.com/watch?v=abcdefghijk', 'YouTube', '原始作品标题', creator_name='作者')
            window.url_text.setPlainText('尚未提交的输入')
            window._on_item_progress(0, {'status': 'downloading', 'filename': '处理中间文件.mp4', 'downloaded_bytes': 1, 'total_bytes': 2})
            media = Path(window.settings.fileName()).parent / 'finished.mp4'; media.write_bytes(b'fixture')
            window._on_item_finished(0, '实际文件名.mp4', [str(media)])
            window._on_item_finished(0, '实际文件名.mp4', [str(media)])
            records = window.history_store.query()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].title, '原始作品标题')
            window.history_button.click(); app.processEvents()
            self.assertIs(window.pages.currentWidget(), window.history_page)
            self.assertEqual(window.table.rowCount(), 0)
            window.history_page.back_requested.emit(); app.processEvents()
            self.assertIs(window.pages.currentWidget(), window.download_page)
            self.assertEqual(window.url_text.toPlainText(), '尚未提交的输入')
            window._clear_queue()
            self.assertEqual(len(window.history_store.query()), 1)
            from PySide6.QtCore import QSettings
            reloaded = MainWindow(settings=QSettings(window.settings.fileName(), QSettings.IniFormat))
            try:
                self.assertEqual(len(reloaded.history_store.query()), 1)
                self.assertEqual(reloaded.table.rowCount(), 0)
            finally: reloaded.close()
        finally:
            window.history_page.pool.waitForDone()
            window.close(); app.processEvents()


if __name__ == '__main__':
    unittest.main()
