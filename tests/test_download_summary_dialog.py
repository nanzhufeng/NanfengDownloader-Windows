import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QDialog, QLabel

from app.main import AppSettingsDialog, DownloadSummaryDialog, MainWindow


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
        dialog = DownloadSummaryDialog(
            {"完成": 2, "已跳过": 0, "失败": 1, "已停止": 1},
            failure_detail="抖音视频数据不完整，已重试后仍失败。",
        )

        self.assertEqual(dialog.headline_label.text(), "下载任务存在失败项")
        self.assertEqual(dialog.headline_label.objectName(), "DownloadSummaryTitleFailure")
        self.assertEqual(dialog.failure_count_label.text(), "1")
        self.assertEqual(dialog.stopped_count_label.text(), "1")
        self.assertIsNotNone(dialog.failure_detail_label)
        self.assertIn("已重试后仍失败", dialog.failure_detail_label.text())

    def test_compact_layout_uses_smaller_dialog_and_cards(self) -> None:
        dialog = DownloadSummaryDialog({"完成": 1, "已跳过": 0, "失败": 0, "已停止": 0})

        self.assertEqual(dialog.minimumWidth(), 420)
        self.assertGreaterEqual(dialog.success_card.minimumWidth(), 78)
        self.assertLessEqual(dialog.success_card.minimumHeight(), 64)

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

    def test_settings_dialog_reflects_completion_sound_preference(self) -> None:
        dialog = AppSettingsDialog(False, True, False)

        self.assertFalse(dialog.completion_sound_enabled())
        self.assertTrue(dialog.result_summary_enabled())
        self.assertFalse(dialog.auto_reveal_output_enabled())
        self.assertFalse(dialog.creator_subfolders_enabled())
        feature_review = dialog.findChild(QLabel, "AppSettingsHint")
        self.assertIsNone(feature_review)
        dialog.completion_sound_checkbox.setChecked(True)
        dialog.result_summary_checkbox.setChecked(False)
        dialog.auto_reveal_output_checkbox.setChecked(True)
        dialog.creator_subfolders_checkbox.setChecked(True)
        self.assertTrue(dialog.completion_sound_enabled())
        self.assertFalse(dialog.result_summary_enabled())
        self.assertTrue(dialog.auto_reveal_output_enabled())
        self.assertTrue(dialog.creator_subfolders_enabled())

    def test_completion_sound_preference_persists_in_the_app_settings_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "preferences.ini"
            settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
            window = MainWindow(settings=settings)
            try:
                self.assertTrue(window.completion_sound_enabled)
                self.assertTrue(window.result_summary_enabled)
                self.assertFalse(window.auto_reveal_output_enabled)
                self.assertFalse(window.creator_subfolders_enabled)
                window._set_completion_preferences(
                    completion_sound_enabled=False,
                    result_summary_enabled=False,
                    auto_reveal_output_enabled=True,
                    creator_subfolders_enabled=True,
                )
            finally:
                window.close()

            reloaded = MainWindow(settings=QSettings(str(settings_path), QSettings.Format.IniFormat))
            try:
                self.assertFalse(reloaded.completion_sound_enabled)
                self.assertFalse(reloaded.result_summary_enabled)
                self.assertTrue(reloaded.auto_reveal_output_enabled)
                self.assertTrue(reloaded.creator_subfolders_enabled)
            finally:
                reloaded.close()

    def test_saving_preferences_shows_a_green_bottom_bar_confirmation_without_replacing_status(self) -> None:
        window = MainWindow()
        try:
            window.status_label.setText("FFmpeg 已就绪 | 队列: 0 项")
            with patch("app.main.AppSettingsDialog") as dialog_type:
                dialog = dialog_type.return_value
                dialog.exec.return_value = QDialog.DialogCode.Accepted
                dialog.completion_sound_enabled.return_value = False
                dialog.result_summary_enabled.return_value = True
                dialog.auto_reveal_output_enabled.return_value = True
                dialog.creator_subfolders_enabled.return_value = True

                window._open_settings()

            self.assertEqual(window.status_label.text(), "FFmpeg 已就绪 | 队列: 0 项")
            self.assertEqual(window.copy_tip_label.text(), "设置已保存")
            self.assertEqual(window.copy_tip_label.property("active"), "true")
        finally:
            window.close()

    def test_summary_plays_system_notification_once_when_enabled(self) -> None:
        window = MainWindow()
        try:
            window.completion_sound_enabled = True
            window.result_summary_enabled = True
            with patch("app.main.play_download_completion_sound") as play_sound, patch(
                "app.main.DownloadSummaryDialog"
            ) as dialog_type:
                dialog_type.return_value.exec.return_value = 0

                window._show_download_summary({"完成": 1, "已跳过": 0, "失败": 0, "已停止": 0})

            play_sound.assert_called_once_with()
        finally:
            window.close()

    def test_summary_stays_silent_when_completion_sound_is_disabled(self) -> None:
        window = MainWindow()
        try:
            window.completion_sound_enabled = False
            window.result_summary_enabled = True
            with patch("app.main.play_download_completion_sound") as play_sound, patch(
                "app.main.DownloadSummaryDialog"
            ) as dialog_type:
                dialog_type.return_value.exec.return_value = 0

                window._show_download_summary({"完成": 1, "已跳过": 0, "失败": 0, "已停止": 0})

            play_sound.assert_not_called()
        finally:
            window.close()

    def test_summary_can_be_disabled_without_disabling_completion_sound(self) -> None:
        window = MainWindow()
        try:
            window.completion_sound_enabled = True
            window.result_summary_enabled = False
            with patch("app.main.play_download_completion_sound") as play_sound, patch(
                "app.main.DownloadSummaryDialog"
            ) as dialog_type:
                window._show_download_summary({"完成": 1, "已跳过": 0, "失败": 0, "已停止": 0})

            play_sound.assert_called_once_with()
            dialog_type.assert_not_called()
        finally:
            window.close()

    def test_all_success_auto_reveals_the_last_completed_row_when_summary_opens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first_file = Path(temp_dir) / "first.mp4"
            second_file = Path(temp_dir) / "second.mp4"
            first_file.write_bytes(b"first")
            second_file.write_bytes(b"second")
            window = MainWindow()
            try:
                for index, file_path in enumerate((first_file, second_file)):
                    window._add_queue_row(
                        url=f"https://example.test/{index}",
                        platform="测试平台",
                        title=file_path.stem,
                    )
                    window._on_item_finished(index, file_path.name, [file_path])
                window.active_download_rows = {0, 1}
                window.completion_sound_enabled = False
                window.result_summary_enabled = True
                window.auto_reveal_output_enabled = True
                events: list[str] = []
                with patch("app.main.DownloadSummaryDialog") as dialog_type, patch(
                    "app.main.reveal_file_in_explorer", return_value=second_file.resolve()
                ) as reveal:
                    dialog_type.return_value.exec.side_effect = lambda: events.append("summary")
                    reveal.side_effect = lambda _path: events.append("reveal") or second_file.resolve()

                    window._show_download_summary({"完成": 2, "已跳过": 0, "失败": 0, "已停止": 0})

                reveal.assert_called_once_with(second_file.resolve())
                self.assertEqual(events, ["reveal", "summary"])
                self.assertEqual(window.table.currentRow(), 1)
            finally:
                window.close()

    def test_auto_reveal_does_not_run_when_the_batch_has_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "completed.mp4"
            output_file.write_bytes(b"done")
            window = MainWindow()
            try:
                for index in range(2):
                    window._add_queue_row(
                        url=f"https://example.test/{index}",
                        platform="测试平台",
                        title=f"视频 {index}",
                    )
                window._on_item_finished(0, output_file.name, [output_file])
                window._set_row_status(1, "失败")
                window.active_download_rows = {0, 1}
                window.completion_sound_enabled = False
                window.result_summary_enabled = False
                window.auto_reveal_output_enabled = True
                with patch("app.main.reveal_file_in_explorer") as reveal:
                    window._show_download_summary({"完成": 1, "已跳过": 0, "失败": 1, "已停止": 0})

                reveal.assert_not_called()
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
