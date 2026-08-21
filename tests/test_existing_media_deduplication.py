import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.main import MainWindow


class ExistingMediaDeduplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()

    def test_same_creator_and_title_are_deduplicated_only_within_the_same_platform(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            douyin = root / "Douyin" / "同名作者" / "同名视频.mp4"
            bilibili = root / "Bilibili" / "同名作者" / "同名视频.mp4"
            for path in (douyin, bilibili):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"x" * (64 * 1024))

            self.window._add_queue_row(
                url="https://www.bilibili.com/video/BV1test",
                platform="哔哩哔哩",
                title="同名视频",
                creator_name="同名作者",
            )
            existing = self.window._existing_media_index(root)

            self.assertEqual(self.window._row_existing_file(0, existing), bilibili.resolve())


if __name__ == "__main__":
    unittest.main()
