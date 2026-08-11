import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app.auth_profile import _write_cookies_txt, has_youtube_account_cookies
from app.downloader import (
    friendly_youtube_auth_error,
    is_youtube_auth_error_text,
    should_retry_public_youtube_request,
)


class YouTubeAuthCookieTests(unittest.TestCase):
    def _write_cookie_file(self, directory: str, lines: list[str]) -> Path:
        target = Path(directory) / "cookies.txt"
        target.write_text(
            "# Netscape HTTP Cookie File\n" + "\n".join(lines) + "\n",
            encoding="utf-8",
        )
        return target

    def test_visitor_cookies_do_not_count_as_account_login(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cookie_file = self._write_cookie_file(
                temp_dir,
                [".youtube.com\tTRUE\t/\tTRUE\t0\tVISITOR_INFO1_LIVE\tvalue"],
            )

            self.assertFalse(has_youtube_account_cookies(cookie_file))

    def test_valid_secure_account_cookie_counts_as_login(self) -> None:
        expires = int(time.time()) + 3600
        with tempfile.TemporaryDirectory() as temp_dir:
            cookie_file = self._write_cookie_file(
                temp_dir,
                [f".youtube.com\tTRUE\t/\tTRUE\t{expires}\t__Secure-1PSID\tvalue"],
            )

            self.assertTrue(has_youtube_account_cookies(cookie_file))

    def test_expired_account_cookie_does_not_count_as_login(self) -> None:
        expires = int(time.time()) - 60
        with tempfile.TemporaryDirectory() as temp_dir:
            cookie_file = self._write_cookie_file(
                temp_dir,
                [f".youtube.com\tTRUE\t/\tTRUE\t{expires}\tSAPISID\tvalue"],
            )

            self.assertFalse(has_youtube_account_cookies(cookie_file))

    def test_playwright_session_cookie_is_written_with_netscape_session_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "cookies.txt"
            _write_cookies_txt(
                [
                    {
                        "domain": ".youtube.com",
                        "name": "YSC",
                        "value": "value",
                        "path": "/",
                        "secure": True,
                        "expires": -1,
                    }
                ],
                target,
            )

            cookie_line = target.read_text(encoding="utf-8").splitlines()[-1]
            self.assertEqual(cookie_line.split("\t")[4], "0")


class YouTubeAuthErrorTests(unittest.TestCase):
    def test_detects_youtube_bot_confirmation_error(self) -> None:
        self.assertTrue(
            is_youtube_auth_error_text("Sign in to confirm you’re not a bot. Use --cookies")
        )

    @patch("app.downloader.youtube_pot_provider_ready", return_value=False)
    @patch("app.downloader.has_youtube_account_cookies", return_value=False)
    def test_missing_login_gets_actionable_message(self, _has_login, _provider_ready) -> None:
        error = friendly_youtube_auth_error(
            RuntimeError("Sign in to confirm you're not a bot. Use --cookies")
        )

        self.assertIsNotNone(error)
        self.assertIn("当前未连接", str(error))
        self.assertIn("YouTube 按钮", str(error))

    @patch("app.downloader.youtube_pot_provider_ready", return_value=True)
    @patch("app.downloader.has_youtube_account_cookies", return_value=False)
    def test_no_login_mode_recommends_network_change_before_login(self, _has_login, _provider_ready) -> None:
        error = friendly_youtube_auth_error(
            RuntimeError("Sign in to confirm you're not a bot. Use --cookies")
        )

        self.assertIn("无登录兼容模式", str(error))
        self.assertIn("切换代理节点或网络", str(error))

    @patch("app.downloader.youtube_pot_provider_ready", return_value=True)
    @patch("app.downloader.has_youtube_account_cookies", return_value=False)
    def test_public_bot_challenge_is_retried_once(self, _has_login, _provider_ready) -> None:
        self.assertTrue(
            should_retry_public_youtube_request(
                RuntimeError("Sign in to confirm you're not a bot. Use --cookies")
            )
        )

    @patch("app.downloader.youtube_pot_provider_ready", return_value=True)
    @patch("app.downloader.has_youtube_account_cookies", return_value=True)
    def test_logged_in_bot_challenge_is_not_treated_as_public_retry(self, _has_login, _provider_ready) -> None:
        self.assertFalse(
            should_retry_public_youtube_request(
                RuntimeError("Sign in to confirm you're not a bot. Use --cookies")
            )
        )


if __name__ == "__main__":
    unittest.main()
