from pathlib import Path
import unittest
from unittest.mock import patch

from app.catalog import discover_youtube_items
from app.downloader import DownloadOptions


class YouTubeCatalogFastPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.options = DownloadOptions(
            output_dir=Path("D:/test-output"),
            quality="720p 及以下",
            cookie_mode="软件内登录",
            cookie_file=None,
            ffmpeg_dir=None,
        )

    @patch("app.catalog.build_youtube_runtime_options")
    @patch("app.catalog._discover_youtube_items_once")
    def test_single_video_is_queued_without_network_metadata_lookup(
        self,
        discover_once,
        build_runtime_options,
    ) -> None:
        url = "https://www.youtube.com/watch?v=PONo81nwVy4"

        items = discover_youtube_items(url, self.options)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, url)
        self.assertEqual(items[0].platform, "YouTube")
        self.assertEqual(items[0].title, "YouTube 视频（下载时解析）")
        self.assertIsNone(items[0].creator_name)
        discover_once.assert_not_called()
        build_runtime_options.assert_not_called()

    @patch("app.catalog.build_youtube_runtime_options", return_value={})
    @patch("app.catalog._discover_youtube_items_once", return_value=[])
    def test_channel_still_uses_the_catalog_reader(self, discover_once, _build_runtime_options) -> None:
        discover_youtube_items("https://www.youtube.com/@OpenAI/videos", self.options)

        discover_once.assert_called_once()


if __name__ == "__main__":
    unittest.main()
