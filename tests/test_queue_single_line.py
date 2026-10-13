import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QProxyStyle, QStyle, QStyleOptionViewItem, QWidget

from app.main import COL_CREATOR, COL_LINK, COL_TITLE
from tests.ui_fixtures import isolated_main_window


class RecordingItemStyle(QProxyStyle):
    def __init__(self):
        super().__init__('Fusion')
        self.items = []

    def drawControl(self, element, option, painter, widget=None):
        if element == QStyle.CE_ItemViewItem:
            self.items.append(QStyleOptionViewItem(option))
        super().drawControl(element, option, painter, widget)


class QueueSingleLineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_long_queue_values_paint_one_line_without_changing_full_values(self):
        window = isolated_main_window()
        table = window.table
        style = RecordingItemStyle()
        paint_surface = QWidget()
        paint_surface.setStyle(style)
        samples = {
            COL_TITLE: '2026-10-11 社保过亿的缺口怎么填？ 看不到未来的年轻人\n社保 | 国新办发布会 | 李忠 1080p.mp4',
            COL_CREATOR: '作者名称很长\r\n频道名称很长',
            COL_LINK: 'https://example.test/video/very-long-public-link?description=full-value',
        }
        table.setRowCount(1)
        try:
            for column, value in samples.items():
                window._set_cell(0, column, value)
            window.show()
            self.app.processEvents()
            for column, value in samples.items():
                with self.subTest(column=column):
                    index = table.model().index(0, column)
                    option = QStyleOptionViewItem()
                    table.initViewItemOption(option)
                    option.widget = paint_surface
                    option.rect = table.visualRect(index)
                    # A narrow cell reproduces the user's long-title case.
                    option.rect.setWidth(110)
                    pixels = QPixmap(option.rect.size())
                    painter = QPainter(pixels)
                    painter.translate(-option.rect.topLeft())
                    style.items.clear()
                    try:
                        table.itemDelegateForIndex(index).paint(painter, option, index)
                    finally:
                        painter.end()
                    painted = style.items[-1]
                    self.assertFalse(painted.features & QStyleOptionViewItem.WrapText)
                    self.assertEqual(painted.textElideMode, Qt.ElideRight)
                    self.assertFalse(any(c in painted.text for c in '\r\n\u2028\u2029'))
                    self.assertEqual(table.item(0, column).text(), value)
                    self.assertEqual(table.item(0, column).toolTip(), value)
        finally:
            window.close()
            paint_surface.close()


if __name__ == '__main__':
    unittest.main()
