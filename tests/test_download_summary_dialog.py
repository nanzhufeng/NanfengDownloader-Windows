import unittest

from PySide6.QtWidgets import QApplication

from app.main import DownloadSummaryDialog, MainWindow


class DownloadSummaryDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_all_success_uses_success_headline_and_green_count(self) -> None:
        dialog = DownloadSummaryDialog({"完成": 3, "已跳过": 1, "失败": 0, "已停止": 0})

        self.assertEqual(dialog.headline_label.text(), "下载全部完成")
        self.assertEqual(dialog.headline_label.objectName(), "DownloadSummaryTitleSuccess")
        self.assertEqual(dialog.success_count_label.text(), "3")
        self.assertEqual(dialog.failure_count_label.text(), "0")
        self.assertEqual(dialog.failure_card.objectName(), "DownloadSummaryFailure")

    def test_failed_items_use_failure_headline_and_red_count(self) -> None:
        dialog = DownloadSummaryDialog({"完成": 2, "已跳过": 0, "失败": 1, "已停止": 1})

        self.assertEqual(dialog.headline_label.text(), "下载任务存在失败项")
        self.assertEqual(dialog.headline_label.objectName(), "DownloadSummaryTitleFailure")
        self.assertEqual(dialog.failure_count_label.text(), "1")
        self.assertEqual(dialog.stopped_count_label.text(), "1")

    def test_summary_counts_only_the_active_batch_rows(self) -> None:
        window = MainWindow()
        try:
            for index in range(3):
                window._add_queue_row(
                    url=f"https://example.test/{index}",
                    platform="测试平台",
                    title=f"视频 {index}",
                )
            window._set_row_status(0, "完成")
            window._set_row_status(1, "失败")
            window._set_row_status(2, "完成")
            window.active_download_rows = {0, 1}

            self.assertEqual(
                window._download_summary_counts(),
                {"完成": 1, "已跳过": 0, "失败": 1, "已停止": 0},
            )
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
