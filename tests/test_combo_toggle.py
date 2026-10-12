import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from app.main import CenterComboBox


class ComboToggleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')

    def test_repeated_trigger_clicks_close_captured_popup(self):
        combo = CenterComboBox()
        window = QWidget()
        layout = QVBoxLayout(window)
        layout.addWidget(combo)
        combo.addItems(['自动识别', '1080P', '720P'])
        # Match the application's styled Qt popup rather than Windows' native menu.
        combo.setStyleSheet('QComboBox { border: 1px solid #d6dfed; padding: 6px; }')
        combo.resize(300, 40)
        window.resize(340, 120)
        window.show()
        window.activateWindow()
        QTest.qWaitForWindowExposed(window)
        QTest.qWait(100)
        try:
            for trigger, point in [(combo, combo.rect().center()),
                                   (combo, QPoint(combo.width() - 8, 20))]:
                for _ in range(3):
                    QTest.mouseClick(trigger, Qt.LeftButton, pos=point)
                    self.app.processEvents()
                    self.assertTrue(combo.view().isVisible(), f'trigger={type(trigger).__name__} cycle={_} active={combo._trigger_press_active}')
                    popup = combo.view().window()
                    captured_point = popup.mapFromGlobal(trigger.mapToGlobal(point))
                    QTest.mouseClick(popup, Qt.LeftButton, pos=captured_point)
                    self.app.processEvents()
                    self.assertFalse(combo.view().isVisible())
                    self.assertEqual(combo.currentText(), '自动识别')
            QTest.mouseClick(combo, Qt.LeftButton)
            QTest.keyClick(combo.view(), Qt.Key_Escape)
            self.app.processEvents()
            self.assertFalse(combo.view().isVisible())
            QTest.mousePress(combo, Qt.LeftButton)
            self.assertTrue(combo.view().isVisible())
            # A replay of the same press must not toggle a second time.
            QTest.mousePress(combo, Qt.LeftButton)
            self.assertTrue(combo.view().isVisible())
            QTest.mouseRelease(combo, Qt.LeftButton)
            QTest.keyClick(combo.view(), Qt.Key_Down)
            QTest.keyClick(combo.view(), Qt.Key_Return)
            self.app.processEvents()
            self.assertFalse(combo.view().isVisible())
            QTest.mouseClick(combo, Qt.LeftButton)
            self.assertTrue(combo.view().isVisible())
            # Mouse capture can target a popup child, not its outer window.
            receiver = combo.view().viewport()
            point = receiver.mapFromGlobal(combo.mapToGlobal(combo.rect().center()))
            QTest.mouseClick(receiver, Qt.LeftButton, pos=point)
            self.app.processEvents()
            self.assertFalse(combo.view().isVisible())
        finally:
            window.close()
