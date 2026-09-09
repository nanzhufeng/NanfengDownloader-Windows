import tempfile
import unittest
from pathlib import Path

from app.catalog import discover_links
from app.downloader import DownloadOptions, assert_supported_platform_url, detect_platform


class PornhubSupportTests(unittest.TestCase):
    def _options(self, output_dir: Path) -> DownloadOptions:
        return DownloadOptions(
            output_dir=output_dir,
            quality="720p 及以下",
            cookie_mode="软件内登录",
            cookie_file=None,
            ffmpeg_dir=None,
        )

    def test_cn_pornhub_video_url_is_recognized_as_supported_platform(self) -> None:
        url = "https://cn.pornhub.com/view_video.php?viewkey=example"
        self.assertEqual(detect_platform(url), "Pornhub")
        self.assertEqual(assert_supported_platform_url(url), "Pornhub")

    def test_single_pornhub_video_uses_direct_queue_item_without_login_requirement(self) -> None:
        url = "https://cn.pornhub.com/view_video.php?viewkey=example"
        with tempfile.TemporaryDirectory() as temp_dir:
            items = discover_links(url, self._options(Path(temp_dir)))

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].platform, "Pornhub")
        self.assertEqual(items[0].url, url)
        self.assertIn("下载时解析", items[0].title)

    def test_ytdlp_has_the_required_pornhub_extractor(self) -> None:
        from yt_dlp.extractor import get_info_extractor

        extractor = get_info_extractor("PornHub")
        self.assertTrue(extractor.suitable("https://cn.pornhub.com/view_video.php?viewkey=example"))


if __name__ == "__main__":
    unittest.main()
