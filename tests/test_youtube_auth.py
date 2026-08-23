import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app.auth_profile import (
    _append_cookie_snapshot,
    _load_cookie_vault,
    _write_cookies_txt,
    cookie_vault_file,
    export_auth_cookies_txt,
    has_youtube_account_cookies,
    migrate_legacy_cookie_files,
    migrate_legacy_browser_profile_cookies,
    platform_cookie_file,
    release_auth_cookie_export,
)
from app.downloader import (
    friendly_youtube_auth_error,
    friendly_youtube_unavailable_error,
    is_youtube_auth_error_text,
    is_youtube_unavailable_error_text,
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

    def test_platform_export_is_short_lived_and_does_not_merge_unrelated_platform_cookies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            youtube_text = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tYSC\tyoutube\n"
            bilibili_text = "# Netscape HTTP Cookie File\n.bilibili.com\tTRUE\t/\tTRUE\t0\tSESSDATA\tbili\n"
            with patch("app.auth_profile.auth_data_dir", return_value=root):
                _append_cookie_snapshot("youtube", youtube_text, source="test")
                _append_cookie_snapshot("bilibili", bilibili_text, source="test")
                exported = export_auth_cookies_txt("youtube")
                try:
                    self.assertIn("youtube", exported.read_text(encoding="utf-8"))
                    self.assertNotIn("bili", exported.read_text(encoding="utf-8"))
                finally:
                    release_auth_cookie_export(exported)
                self.assertFalse(exported.exists())

    def test_cookie_history_keeps_changed_snapshots_in_a_dpapi_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tYSC\tfirst\n"
            second = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tYSC\tsecond\n"
            with patch("app.auth_profile.auth_data_dir", return_value=root):
                _append_cookie_snapshot("youtube", first, source="test")
                _append_cookie_snapshot("youtube", second, source="test")
                _append_cookie_snapshot("youtube", second, source="test")
                vault = _load_cookie_vault("youtube")
                self.assertEqual(len(vault["snapshots"]), 2)
                self.assertEqual(vault["snapshots"][0]["cookies"], first)
                self.assertEqual(vault["snapshots"][1]["cookies"], second)
                self.assertTrue(cookie_vault_file("youtube").exists())

    def test_legacy_browser_cookie_recovery_stays_platform_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            browser_cookies = [
                {"domain": ".youtube.com", "name": "SID", "value": "youtube", "path": "/", "secure": True},
                {"domain": ".bilibili.com", "name": "SESSDATA", "value": "bilibili", "path": "/", "secure": True},
            ]
            with patch("app.auth_profile.auth_data_dir", return_value=root), patch(
                "app.auth_profile._load_browser_cookies", return_value=browser_cookies
            ):
                exported = export_auth_cookies_txt("youtube")
                try:
                    contents = exported.read_text(encoding="utf-8")
                finally:
                    release_auth_cookie_export(exported)
                self.assertIn("youtube", contents)
                self.assertNotIn("bilibili", contents)
                stored = _load_cookie_vault("youtube")["snapshots"][-1]["cookies"]
                self.assertNotIn("bilibili", stored)

    def test_migration_encrypts_legacy_cookie_files_and_removes_plaintext(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch("app.auth_profile.auth_data_dir", return_value=root):
                legacy_platform_file = platform_cookie_file("youtube")
                legacy_platform_file.write_text(
                    "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tYSC\tlegacy\n",
                    encoding="utf-8",
                )
                self.assertEqual(migrate_legacy_cookie_files(), 1)
                self.assertFalse(legacy_platform_file.exists())
                self.assertEqual(
                    _load_cookie_vault("youtube")["snapshots"][0]["source"],
                    "legacy-plaintext",
                )

    def test_legacy_generic_browser_profile_is_archived_by_platform(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "browser-profile").mkdir()
            browser_cookies = [
                {"domain": ".youtube.com", "name": "SID", "value": "youtube", "path": "/", "secure": True},
                {"domain": ".douyin.com", "name": "sessionid", "value": "douyin", "path": "/", "secure": True},
            ]
            with patch("app.auth_profile.auth_data_dir", return_value=root), patch(
                "app.auth_profile._load_browser_cookies", return_value=browser_cookies
            ):
                self.assertEqual(migrate_legacy_browser_profile_cookies(), 2)
                self.assertEqual(len(_load_cookie_vault("youtube")["snapshots"]), 1)
                self.assertEqual(len(_load_cookie_vault("douyin")["snapshots"]), 1)
                self.assertEqual(len(_load_cookie_vault("bilibili")["snapshots"]), 0)


class YouTubeAuthErrorTests(unittest.TestCase):
    def test_detects_youtube_bot_confirmation_error(self) -> None:
        self.assertTrue(
            is_youtube_auth_error_text("Sign in to confirm you’re not a bot. Use --cookies")
        )

    def test_unavailable_youtube_video_gets_an_actionable_chinese_message(self) -> None:
        source = RuntimeError("ERROR: [youtube] test: Video unavailable")

        self.assertTrue(is_youtube_unavailable_error_text(str(source)))
        converted = friendly_youtube_unavailable_error(source)
        self.assertIsNotNone(converted)
        self.assertIn("浏览器确认", str(converted))

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
