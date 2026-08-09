from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from app.main import COL_LOCATE, COL_STATUS, MainWindow
from app.windows_shell import reveal_file_in_explorer


class WindowsExplorerSelectionTests(unittest.TestCase):
    def test_reveal_rejects_a_missing_file_before_opening_explorer(self) -> None:
        missing = Path(tempfile.gettempdir()) / "nanfeng-missing-video.mp4"
        if missing.exists():
            missing.unlink()

        with patch("app.windows_shell._open_folder_and_select_item") as select_item:
            with self.assertRaises(FileNotFoundError):
                reveal_file_in_explorer(missing)

        select_item.assert_not_called()

    def test_reveal_passes_the_exact_unicode_file_to_windows_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "作者 A 2026-08-01 视频标题.mp4"
            file_path.write_bytes(b"test media")

            with patch("app.windows_shell._open_folder_and_select_item") as select_item:
                selected = reveal_file_in_explorer(file_path)

        self.assertEqual(selected, file_path.resolve())
        select_item.assert_called_once_with(file_path.resolve())


class QueueLocateButtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()

    def test_completed_row_enables_locate_and_targets_its_exact_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "作者 A" / "2026-08-01 精确视频.mp4"
            output_file.parent.mkdir(parents=True)
            output_file.write_bytes(b"test media")
            self.window._add_queue_row(
                url="https://example.test/video-a",
                platform="测试平台",
                title="精确视频",
                creator_name="作者 A",
            )

            button = self.window.table.cellWidget(0, COL_LOCATE)
            self.assertIsInstance(button, QPushButton)
            self.assertFalse(button.isEnabled())

            self.window._on_item_finished(0, output_file.name, [str(output_file)])

            self.assertEqual(self.window.table.item(0, COL_STATUS).text(), "完成")
            self.assertTrue(button.isEnabled())
            with patch("app.main.reveal_file_in_explorer", return_value=output_file.resolve()) as reveal:
                self.window._reveal_row_output(0)

            reveal.assert_called_once_with(output_file.resolve())
            self.assertIn(output_file.name, self.window.status_label.text())

    def test_each_row_keeps_its_own_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            files = [Path(temp_dir) / f"video-{index}.mp4" for index in (1, 2)]
            for index, file_path in enumerate(files):
                file_path.write_bytes(b"test media")
                self.window._add_queue_row(
                    url=f"https://example.test/video-{index}",
                    platform="测试平台",
                    title=file_path.stem,
                )
                self.window._on_item_finished(index, file_path.name, [file_path])

            with patch("app.main.reveal_file_in_explorer", return_value=files[1].resolve()) as reveal:
                self.window._reveal_row_output(1)

            reveal.assert_called_once_with(files[1].resolve())

    def test_locating_a_long_filename_does_not_resize_the_main_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / (("很长的视频标题文件名" * 18) + ".mp4")
            output_file.write_bytes(b"test media")
            self.window.resize(1200, 800)
            self.window.show()
            self.app.processEvents()
            self.window._add_queue_row(
                url="https://example.test/long-title",
                platform="测试平台",
                title="长标题",
            )
            self.window._on_item_finished(0, output_file.name, [str(output_file)])
            self.app.processEvents()
            size_before = self.window.size()
            minimum_width_before = self.window.minimumSizeHint().width()

            with patch("app.main.reveal_file_in_explorer", return_value=output_file.resolve()):
                self.window._reveal_row_output(0)
            self.app.processEvents()

            self.assertEqual(self.window.size(), size_before)
            self.assertLessEqual(self.window.minimumSizeHint().width(), minimum_width_before)
            self.assertIn(output_file.name, self.window.status_label.toolTip())


if __name__ == "__main__":
    unittest.main()
