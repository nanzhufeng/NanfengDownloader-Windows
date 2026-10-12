import unittest
from PySide6.QtCore import QMimeData, QUrl, QPointF, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from app.torrent_input import DownloadInput


class TorrentDropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_drop_emits_decoded_path_without_inserting_file_uri(self):
        widget = DownloadInput()
        paths = []
        widget.torrent_dropped.connect(paths.append)
        mime = QMimeData()
        url = QUrl.fromLocalFile('C:/Downloads/[中文] 种子.torrent')
        mime.setUrls([url])
        event = QDropEvent(QPointF(2, 2), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        widget.dropEvent(event)
        self.assertEqual(paths, [url.toLocalFile()])
        self.assertEqual(widget.toPlainText(), '')
        self.assertTrue(event.isAccepted())
        widget.close()

    def test_web_url_is_not_treated_as_local_torrent(self):
        mime = QMimeData()
        mime.setUrls([QUrl('https://example.test/sample.torrent')])
        self.assertEqual(DownloadInput.torrent_paths(mime), [])

    def test_keyboard_paste_replaces_existing_links_and_can_be_undone(self):
        widget = DownloadInput()
        clipboard = self.app.clipboard()
        previous_text = clipboard.text()
        old = 'https://example.test/old\nhttps://example.test/another'
        new = '分享新视频 https://example.test/new\nhttps://example.test/newer'
        try:
            widget.setPlainText(old)
            widget.show()
            QTest.mouseClick(widget.viewport(), Qt.LeftButton)
            clipboard.setText(new)
            QTest.keyClick(widget, Qt.Key_V, Qt.ControlModifier)
            self.assertEqual(widget.toPlainText(), new)
            widget.undo()
            self.assertEqual(widget.toPlainText(), old)
        finally:
            clipboard.setText(previous_text)
            widget.close()
