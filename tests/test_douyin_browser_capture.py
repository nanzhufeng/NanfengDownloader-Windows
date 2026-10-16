import unittest
from pathlib import Path
from unittest.mock import patch

from app.downloader import DownloadOptions

from app.douyin import (
    _background_browser_args,
    _capture_is_ready,
    _capture_wait_rounds,
    _wait_for_catalog_growth,
)


class BackgroundBrowserArgsTests(unittest.TestCase):
    def test_cookie_recovery_finishes_before_opening_browser_capture(self):
        from app import douyin
        recovered = []
        class BrowserBoundaryReached(Exception):
            pass
        class BrowserScope:
            def __enter__(scope):
                self.assertTrue(recovered, 'recovering cookies inside a running Playwright scope nests the Sync API')
                raise BrowserBoundaryReached()
            def __exit__(scope, *args):
                pass
        options = DownloadOptions(Path('.'), 'best', 'software', None, None)
        for capture in (lambda: douyin._sniff_douyin_with_browser('1234567890123456789', options),
                        lambda: douyin._discover_douyin_with_browser('author', options, 5)):
            recovered.clear()
            with patch('app.douyin._find_chrome_path', return_value='browser.exe'), \
                 patch('app.douyin._playwright_cookies_from_options', side_effect=lambda _: recovered.append(True) or []), \
                 patch('playwright.sync_api.sync_playwright', return_value=BrowserScope()):
                with self.assertRaises(BrowserBoundaryReached): capture()

    def test_windows_args_hide_background_browser_window(self) -> None:
        args = _background_browser_args("nt")

        self.assertIn("--headless=new", args)
        self.assertIn("--no-startup-window", args)
        self.assertIn("--window-position=-32000,-32000", args)

    def test_non_windows_args_keep_only_cross_platform_browser_flags(self) -> None:
        args = _background_browser_args("posix")

        self.assertIn("--disable-blink-features=AutomationControlled", args)
        self.assertNotIn("--window-position=-32000,-32000", args)


class CaptureReadyTests(unittest.TestCase):
    def test_ready_when_video_and_metadata_are_available(self) -> None:
        self.assertTrue(
            _capture_is_ready(
                ["https://cdn.example/video.mp4"],
                [],
                "作品标题",
                "2026-07-15",
                "博主",
                "抖音视频 1",
            )
        )

    def test_not_ready_when_metadata_is_incomplete(self) -> None:
        self.assertFalse(
            _capture_is_ready(
                ["https://cdn.example/video.mp4"],
                [],
                "作品标题",
                None,
                "博主",
                "抖音视频 1",
            )
        )

    def test_ready_for_image_post_when_metadata_is_available(self) -> None:
        self.assertTrue(
            _capture_is_ready(
                [],
                ["https://cdn.example/image.jpg"],
                "图文标题",
                "2026-07-15",
                "博主",
                "抖音视频 1",
            )
        )


class CapturePollingTests(unittest.TestCase):
    def test_wait_rounds_use_250ms_polling_with_a_12_second_upper_bound(self) -> None:
        self.assertEqual(_capture_wait_rounds(timeout_ms=12_000, poll_ms=250), 48)

    def test_wait_rounds_never_returns_zero(self) -> None:
        self.assertEqual(_capture_wait_rounds(timeout_ms=100, poll_ms=250), 1)


class _FakePage:
    def __init__(self, callback) -> None:
        self.callback = callback
        self.wait_calls = 0

    def wait_for_timeout(self, milliseconds: int) -> None:
        self.wait_calls += 1
        self.callback(self.wait_calls)


class CatalogGrowthWaitTests(unittest.TestCase):
    def test_returns_as_soon_as_catalog_grows(self) -> None:
        catalog = []
        page = _FakePage(
            lambda calls: catalog.append({"url": "https://example.com/1"}) if calls == 2 else None
        )

        changed = _wait_for_catalog_growth(page, catalog, previous_count=0, timeout_ms=2_000)

        self.assertTrue(changed)
        self.assertEqual(page.wait_calls, 2)

    def test_returns_false_after_timeout_without_catalog_growth(self) -> None:
        catalog = []
        page = _FakePage(lambda calls: None)

        changed = _wait_for_catalog_growth(page, catalog, previous_count=0, timeout_ms=500)

        self.assertFalse(changed)
        self.assertEqual(page.wait_calls, 2)


if __name__ == "__main__":
    unittest.main()
