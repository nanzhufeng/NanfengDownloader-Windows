import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTableWidget, QWidget, QVBoxLayout
from app.main import CenterComboBox
from tests.ui_fixtures import isolated_main_window


class ComboToggleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')

    def test_popup_stays_below_trigger_for_each_selected_item(self):
        window = QWidget()
        window.setGeometry(100, 100, 360, 150)
        combo = CenterComboBox()
        QVBoxLayout(window).addWidget(combo)
        combo.addItems(['自动识别', '1080P', '720P', '360P', 'MP3'])
        combo.setStyleSheet('QComboBox { padding: 8px; border: none; background: #f6f7f9; }')
        window.show()
        self.app.processEvents()
        try:
            for index in (0, 3, 4):
                combo.setCurrentIndex(index)
                combo.showPopup()
                self.app.processEvents()
                popup = combo.view().window()
                self.assertEqual(popup.y() + 16, combo.mapToGlobal(QPoint(0, combo.height() + 8)).y())
                self.assertGreaterEqual(popup.width(), combo.width())
                combo.hidePopup()
        finally:
            window.close()

    def test_popup_has_transparent_soft_edge_and_shows_all_five_choices(self):
        window = QWidget()
        combo = CenterComboBox()
        combo.addItems(['自动识别', '1080p 及以下', '720p 及以下', '360p 及以下', '仅音频 MP3'])
        QVBoxLayout(window).addWidget(combo)
        window.resize(420, 120)
        window.show()
        self.app.processEvents()
        try:
            combo.setCurrentIndex(4)
            combo.showPopup()
            self.app.processEvents()
            popup = combo.view().window()
            self.assertTrue(popup.windowFlags() & Qt.FramelessWindowHint)
            self.assertTrue(popup.windowFlags() & Qt.NoDropShadowWindowHint)
            pixels = popup.grab().toImage()
            self.assertEqual(pixels.pixelColor(0, 0).alpha(), 0)
            self.assertLessEqual(pixels.pixelColor(15, pixels.height() // 2).alpha(), 36)
            self.assertEqual(pixels.pixelColor(17, pixels.height() // 2).getRgb(), (255, 255, 255, 255))
            for row in range(5):
                rect = combo.view().visualRect(combo.model().index(row, 0))
                self.assertTrue(combo.view().viewport().rect().contains(rect))
        finally:
            combo.hidePopup()
            window.close()

    def test_main_workbench_style_does_not_clip_last_resolution_choice(self):
        window = isolated_main_window()
        window.resize(1820, 1000)
        window.show()
        self.app.processEvents()
        combo = window.quality_combo
        try:
            combo.setCurrentIndex(3)
            combo.showPopup()
            self.app.processEvents()
            for row in range(combo.count()):
                rect = combo.view().visualRect(combo.model().index(row, 0))
                self.assertTrue(combo.view().viewport().rect().contains(rect), f'choice {row} is clipped in the real workbench style')
        finally:
            combo.hidePopup()
            window.close()

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
            self.assertFalse(combo.view().isVisible())
            # Replayed presses cannot open the menu before the click is released.
            QTest.mousePress(combo, Qt.LeftButton)
            self.assertFalse(combo.view().isVisible())
            QTest.mouseRelease(combo, Qt.LeftButton)
            self.assertTrue(combo.view().isVisible())
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

    def test_table_resolution_combo_stays_open_after_single_click_release(self):
        table = QTableWidget(1, 1)
        table.resize(320, 120)
        combo = CenterComboBox()
        combo.setObjectName("TableCombo")
        combo.addItems(["自动识别", "1080p 及以下", "720p 及以下"])
        combo.setStyleSheet("""
            QComboBox#TableCombo { min-width: 104px; padding: 4px 6px; border: none; }
            QComboBox#TableCombo::drop-down { width: 0px; border: none; }
            QComboBox#TableCombo::down-arrow { image: none; width: 0px; height: 0px; }
        """)
        table.setCellWidget(0, 0, combo)
        table.show()
        self.app.processEvents()
        try:
            QTest.mouseClick(combo, Qt.LeftButton, pos=combo.rect().center())
            self.app.processEvents()
            self.assertTrue(combo.view().isVisible(), "a normal click must leave the table menu open")
            QTest.qWait(120)
            self.assertTrue(combo.view().isVisible(), "the menu must not disappear after the click release")
            combo.hidePopup()
        finally:
            table.close()
