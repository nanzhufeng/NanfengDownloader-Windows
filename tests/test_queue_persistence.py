import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton, QDialog

from app.main import (
    COL_CREATOR,
    COL_LINK,
    COL_QUALITY,
    COL_SELECT,
    COL_STATUS,
    MainWindow,
    AppSettingsDialog,
    SETTING_QUEUE_STATE,
    SETTING_RETAIN_QUEUE_HISTORY,
)


class QueuePersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _settings(path: Path) -> QSettings:
        return QSettings(str(path), QSettings.Format.IniFormat)

    def test_disabling_history_keeps_current_rows_but_restarts_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'settings.ini'
            window = MainWindow(settings=self._settings(path))
            try:
                self.assertTrue(window.retain_queue_history)
                window._add_queue_row('https://example.test/video', '通用', 'test')
                window._persist_queue_state()
                dialog = AppSettingsDialog(True, True, False)
                dialog.retain_queue_history_checkbox.setChecked(False)
                with patch('app.main.AppSettingsDialog', return_value=dialog), patch.object(dialog, 'exec', return_value=QDialog.DialogCode.Accepted):
                    window._open_settings()
                self.assertEqual(window.table.rowCount(), 1)
                self.assertFalse(window.settings.contains(SETTING_QUEUE_STATE))
                window._persist_queue_state()
                self.assertFalse(window.settings.contains(SETTING_QUEUE_STATE))
            finally:
                window.close()
            restarted = MainWindow(settings=self._settings(path))
            try:
                self.assertFalse(restarted.retain_queue_history)
                self.assertEqual(restarted.table.rowCount(), 0)
            finally:
                restarted.close()

    def test_disabled_setting_ignores_old_saved_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = self._settings(Path(temp_dir) / 'settings.ini')
            settings.setValue(SETTING_RETAIN_QUEUE_HISTORY, False)
            settings.setValue(SETTING_QUEUE_STATE, json.dumps({'version': 1, 'rows': [{'url': 'https://example.test/old'}]}))
            window = MainWindow(settings=settings)
            try:
                self.assertEqual(window.table.rowCount(), 0)
                self.assertFalse(settings.contains(SETTING_QUEUE_STATE))
            finally:
                window.close()

    def test_restarting_restores_link_quality_creator_and_resumable_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "preferences.ini"
            first = MainWindow(settings=self._settings(settings_path))
            try:
                self.assertTrue(
                    first._add_queue_row(
                        "https://www.youtube.com/watch?v=queue-test",
                        "YouTube",
                        "恢复测试视频",
                        creator_name="测试作者",
                    )
                )
                quality = first.table.cellWidget(0, COL_QUALITY)
                self.assertIsInstance(quality, QComboBox)
                quality.setCurrentText("1080p 及以下")
                first._set_row_status(0, "下载中")
                first._persist_queue_state()
            finally:
                first.close()

            restored = MainWindow(settings=self._settings(settings_path))
            try:
                self.assertEqual(restored.table.rowCount(), 1)
                self.assertEqual(restored.table.item(0, COL_LINK).text(), "https://www.youtube.com/watch?v=queue-test")
                self.assertEqual(restored.table.item(0, COL_CREATOR).text(), "测试作者")
                self.assertEqual(restored.table.item(0, COL_STATUS).text(), "等待")
                self.assertEqual(restored.table.item(0, COL_SELECT).checkState(), Qt.Checked)
                restored_quality = restored.table.cellWidget(0, COL_QUALITY)
                self.assertIsInstance(restored_quality, QComboBox)
                self.assertEqual(restored_quality.currentText(), "1080p 及以下")
            finally:
                restored.close()

    def test_completed_row_restores_only_in_history_and_keeps_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings_path = root / "preferences.ini"
            media_file = root / "output" / "done.mp4"
            media_file.parent.mkdir()
            media_file.write_bytes(b"media")
            first = MainWindow(settings=self._settings(settings_path))
            try:
                first._add_queue_row("https://www.bilibili.com/video/BV1test", "哔哩哔哩", "已完成视频")
                first._set_row_status(0, "完成")
                first._set_row_output_files(0, [str(media_file)])
                first._persist_queue_state()
            finally:
                first.close()

            restored = MainWindow(settings=self._settings(settings_path))
            try:
                self.assertEqual(restored.table.rowCount(), 0)
                records = restored.history_store.query()
                self.assertEqual(len(records), 1)
                self.assertEqual(records[0].title, "已完成视频")
                self.assertEqual(tuple(Path(path).resolve() for path in records[0].files), (media_file.resolve(),))
                self.assertTrue(media_file.exists())
            finally:
                restored.close()

    def test_stored_queue_contains_only_queue_metadata_not_login_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "preferences.ini"
            window = MainWindow(settings=self._settings(settings_path))
            try:
                window._add_queue_row("https://www.youtube.com/watch?v=metadata-test", "YouTube", "元数据测试")
                window._persist_queue_state()
                payload = json.loads(str(window.settings.value(SETTING_QUEUE_STATE)))
            finally:
                window.close()

        self.assertEqual(set(payload), {"version", "rows"})
        self.assertEqual(set(payload["rows"][0]), {"url", "platform", "creator", "quality", "title", "source_title", "history_id", "status", "selected", "output_files"})


if __name__ == "__main__":
    unittest.main()
