"""Offline smart-read regression; only the network boundary is replaced."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog
from app.catalog import CatalogItem
from app.collection_dialog import CollectionDialog
from app.main import MainWindow, COL_LINK


class DiscoveryPerformanceTests(unittest.TestCase):
    def test_smart_read_adds_500_results_without_minute_long_ui_stall(self):
        app = QApplication.instance() or QApplication([])
        items = [CatalogItem('YouTube', f'Offline video {i}', f'https://example.test/{i}') for i in range(500)]

        def accept_all(dialog):
            dialog.check_visible(True)
            return QDialog.Accepted

        with tempfile.TemporaryDirectory() as directory:
            window = MainWindow(settings=QSettings(str(Path(directory) / 'preferences.ini'), QSettings.IniFormat))
            window.output_edit.setText(directory)
            window.url_text.setPlainText('https://www.youtube.com/playlist?list=offline-fixture')
            window.show()
            app.processEvents()
            try:
                with patch('app.main.discover_links', return_value=items), patch.object(CollectionDialog, 'exec', accept_all):
                    started = time.perf_counter()
                    QTest.mouseClick(window.import_button, Qt.LeftButton)
                    while window.discovery_thread is not None and time.perf_counter() - started < 10:
                        app.processEvents()
                        QTest.qWait(5)
                    elapsed = time.perf_counter() - started
                    self.assertEqual(window.table.rowCount(), 500)
                    self.assertEqual(window.table.item(499, COL_LINK).text(), 'https://example.test/499')
                    self.assertLess(elapsed, 10, '500 offline results must not block the UI for a minute')
                    self.assertTrue(window.import_button.isEnabled())
            finally:
                if window.discovery_thread is not None:
                    window.discovery_thread.quit()
                    window.discovery_thread.wait(3000)
                    app.processEvents()
                window.close()
                window.deleteLater()
                app.processEvents()
