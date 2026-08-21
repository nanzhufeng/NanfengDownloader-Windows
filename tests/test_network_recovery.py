import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidgetItem

from app.main import COL_ETA, COL_LINK, COL_PROGRESS, COL_SELECT, COL_SPEED, COL_STATUS, MainWindow, is_network_error_text


class NetworkRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()
        self.window.table.setRowCount(1)
        select_item = QTableWidgetItem()
        select_item.setCheckState(Qt.Checked)
        self.window.table.setItem(0, COL_SELECT, select_item)
        self.window.table.setItem(0, COL_STATUS, QTableWidgetItem("等待联网"))
        self.window.table.setItem(0, COL_LINK, QTableWidgetItem("https://example.test/video"))
        self.window.waiting_for_network = True

    def tearDown(self) -> None:
        self.window.close()

    def test_online_transition_restores_waiting_row_and_restarts_queue(self) -> None:
        callbacks = []
        with patch("app.main.QTimer.singleShot", side_effect=lambda delay, callback: callbacks.append(callback)):
            with patch.object(self.window, "_start_downloads") as start_downloads:
                self.window._on_network_check_finished(True)
                self.assertEqual(self.window.table.item(0, COL_STATUS).text(), "等待")
                self.assertFalse(self.window.waiting_for_network)
                self.assertEqual(len(callbacks), 1)
                callbacks[0]()

        start_downloads.assert_called_once_with()

    def test_offline_transition_keeps_waiting_state(self) -> None:
        with patch("app.main.QTimer.singleShot") as single_shot:
            self.window._on_network_check_finished(False)

        self.assertEqual(self.window.table.item(0, COL_STATUS).text(), "等待联网")
        self.assertTrue(self.window.waiting_for_network)
        single_shot.assert_not_called()

    def test_certificate_errors_are_not_misclassified_as_recoverable_network_errors(self) -> None:
        self.assertFalse(is_network_error_text("SSL: CERTIFICATE_VERIFY_FAILED"))
        self.assertFalse(is_network_error_text("<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]>"))

    def test_retrying_download_is_visible_and_keeps_current_progress(self) -> None:
        self.window._set_row_status(0, "下载中")
        self.window._set_cell(0, COL_PROGRESS, "62%")
        self.window._on_item_progress(
            0,
            {
                "status": "retrying",
                "reason": "抖音视频连接中断，正在断点续传（2/8）。",
            },
        )

        self.assertEqual(self.window.table.item(0, COL_STATUS).text(), "续传中")
        self.assertEqual(self.window.table.item(0, COL_SPEED).text(), "正在续传")
        self.assertEqual(self.window.table.item(0, COL_ETA).text(), "重新连接")
        self.assertEqual(self.window.table.item(0, COL_PROGRESS).text(), "62%")
        self.assertIn("断点续传", self.window.status_label.text())


if __name__ == "__main__":
    unittest.main()
