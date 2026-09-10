import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.catalog import discover_links
from app.downloader import DownloadOptions, assert_supported_platform_url, download_url


class GenericWebsitesTests(unittest.TestCase):
    def options(self, root):
        return DownloadOptions(Path(root), "720p 及以下", "软件内登录", None, None)

    def test_http_only_without_embedded_credentials(self):
        for url in ("file:///C:/secret", "ftp://example.org/v", "https://user:pass@example.org/v", "https:///v"):
            with self.subTest(url=url), self.assertRaises(RuntimeError):
                assert_supported_platform_url(url)

    def test_generic_catalog_is_fast_and_never_uses_youtube(self):
        with tempfile.TemporaryDirectory() as root, patch("app.catalog.discover_youtube_items") as youtube:
            items = discover_links("https://vimeo.com/123 https://media.example/a.mp4", self.options(root))
        youtube.assert_not_called()
        self.assertEqual(len(items), 2)
        self.assertTrue(all(item.platform == "其他网站" for item in items))
        self.assertEqual(items[0].url, "https://vimeo.com/123")

    def test_generic_download_routes_anonymously_and_limits_playlist(self):
        with tempfile.TemporaryDirectory() as root:
            def run(url, options, progress, cancel):
                self.assertNotIn("cookiefile", options)
                self.assertNotIn("cookiesfrombrowser", options)
                self.assertTrue(options["noplaylist"])
                self.assertEqual(options["playlistend"], 1)
                self.assertIn("example.org", options["outtmpl"])
                raise RuntimeError("Unsupported URL")
            with patch("app.downloader._download_with_adaptive_concurrency", side_effect=run), patch("app.downloader.export_auth_cookies_txt") as cookie, patch("app.web_media.resolve_browser_media", side_effect=RuntimeError("未发现可下载媒体")):
                with self.assertRaisesRegex(RuntimeError, "未发现可下载媒体"):
                    download_url("https://example.org/watch/1", self.options(root), lambda info: None)
            cookie.assert_not_called()

    def test_unrelated_existing_file_does_not_mean_success(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "unrelated.mp4").write_bytes(b"not a real video")
            with patch("app.downloader._download_with_adaptive_concurrency", return_value=0):
                with self.assertRaisesRegex(RuntimeError, "没有新增文件"):
                    download_url("https://example.org/watch/1", self.options(root), lambda info: None)
