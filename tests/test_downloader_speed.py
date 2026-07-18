import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_dlp import YoutubeDL

from app.downloader import (
    DownloadOptions,
    _download_with_adaptive_concurrency,
    _is_fragment_rate_limit_error,
    build_format_selector,
    build_format_sort,
    build_youtube_runtime_options,
    build_ydl_options,
    find_node_runtime,
    youtube_pot_provider_home,
)


class DownloadSpeedOptionsTests(unittest.TestCase):
    def _options(self, temp_dir: str, quality: str = "720p 及以下") -> DownloadOptions:
        return DownloadOptions(
            output_dir=Path(temp_dir),
            quality=quality,
            cookie_mode="不使用登录态",
            cookie_file=None,
            ffmpeg_dir=None,
        )

    def test_ytdlp_uses_parallel_fragments_and_larger_buffers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_options = build_ydl_options(self._options(temp_dir), lambda info: None)

        self.assertEqual(ydl_options["concurrent_fragment_downloads"], 16)
        self.assertEqual(ydl_options["buffersize"], 1024 * 1024)
        self.assertEqual(ydl_options["http_chunk_size"], 10 * 1024 * 1024)
        self.assertEqual(ydl_options["progress_delta"], 0.2)

    def test_video_selector_prefers_separate_https_dash_streams(self) -> None:
        selector = build_format_selector("720p 及以下")

        self.assertTrue(selector.startswith("bv[protocol^=https][ext=mp4]+ba[protocol^=https][ext=m4a]"))
        self.assertNotIn("height<=720", selector)

    def test_portrait_resolution_uses_short_edge_limit(self) -> None:
        self.assertEqual(
            build_format_sort("720p 及以下"),
            ["res:720", "proto:https", "vext:mp4", "aext:m4a"],
        )

    def test_360p_resolution_uses_short_edge_limit(self) -> None:
        self.assertEqual(build_format_sort("360p 及以下")[0], "res:360")

    def test_portrait_720p_selects_dash_video_and_audio(self) -> None:
        formats = [
            {
                "format_id": "93",
                "url": "https://hls.example/93.m3u8",
                "protocol": "m3u8_native",
                "ext": "mp4",
                "width": 360,
                "height": 640,
                "vcodec": "avc1",
                "acodec": "mp4a",
                "tbr": 962,
            },
            {
                "format_id": "136",
                "url": "https://dash.example/136.mp4",
                "protocol": "https",
                "ext": "mp4",
                "width": 720,
                "height": 1280,
                "vcodec": "avc1",
                "acodec": "none",
                "tbr": 1800,
            },
            {
                "format_id": "140",
                "url": "https://dash.example/140.m4a",
                "protocol": "https",
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "mp4a",
                "abr": 128,
            },
        ]
        params = {
            "format": build_format_selector("720p 及以下"),
            "format_sort": build_format_sort("720p 及以下"),
            "quiet": True,
        }

        with YoutubeDL(params) as ydl:
            result = ydl.process_ie_result(
                {
                    "id": "test",
                    "title": "test",
                    "formats": formats,
                    "extractor": "test",
                    "extractor_key": "Test",
                    "webpage_url": "https://example.test/video",
                },
                download=False,
            )

        selected = result.get("requested_formats") or [result]
        self.assertEqual([item["format_id"] for item in selected], ["136", "140"])

    def test_ydl_options_include_resolution_sort(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_options = build_ydl_options(self._options(temp_dir), lambda info: None)

        self.assertEqual(ydl_options["format_sort"][0], "res:720")
        self.assertIn("node", ydl_options["js_runtimes"])

    @patch("app.downloader.find_node_runtime", return_value=None)
    @patch("app.downloader.youtube_pot_provider_home")
    def test_youtube_runtime_uses_background_pot_provider_when_ready(self, provider_home, _node_runtime) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            provider_home.return_value = Path(temp_dir)
            script = Path(temp_dir) / "build" / "generate_once.js"
            script.parent.mkdir()
            script.touch()

            runtime_options = build_youtube_runtime_options()

        self.assertEqual(runtime_options["js_runtimes"], {"node": {}})
        self.assertEqual(
            runtime_options["extractor_args"]["youtubepot-bgutilscript"]["server_home"],
            [str(Path(temp_dir))],
        )

    @patch("app.downloader.find_node_runtime")
    def test_youtube_runtime_passes_bundled_node_path(self, node_runtime) -> None:
        node_runtime.return_value = Path(r"C:\tool\node.exe")

        runtime_options = build_youtube_runtime_options()

        self.assertEqual(runtime_options["js_runtimes"], {"node": {"path": r"C:\tool\node.exe"}})

    @patch("app.downloader.shutil.which", return_value=None)
    def test_missing_node_runtime_keeps_yt_dlp_default_discovery(self, _which) -> None:
        with patch("app.downloader._runtime_resource_roots", return_value=[]):
            self.assertIsNone(find_node_runtime())

    def test_parallel_rate_limit_detection_excludes_bot_challenge(self) -> None:
        self.assertTrue(_is_fragment_rate_limit_error(RuntimeError("HTTP Error 429: Too Many Requests")))
        self.assertTrue(_is_fragment_rate_limit_error(RuntimeError("HTTP Error 403: Forbidden")))
        self.assertFalse(
            _is_fragment_rate_limit_error(RuntimeError("Sign in to confirm you're not a bot"))
        )

    @patch("app.downloader._run_ytdlp_download")
    def test_rate_limit_retries_once_with_lower_fragment_concurrency(self, run_download) -> None:
        run_download.side_effect = [RuntimeError("HTTP Error 429: Too Many Requests"), 0]
        progress_events: list[dict[str, object]] = []

        result = _download_with_adaptive_concurrency(
            "https://www.youtube.com/watch?v=test",
            {"concurrent_fragment_downloads": 16},
            progress_events.append,
            None,
        )

        self.assertEqual(result, 0)
        self.assertEqual(run_download.call_count, 2)
        self.assertEqual(
            [item.args[1]["concurrent_fragment_downloads"] for item in run_download.call_args_list],
            [16, 8],
        )
        self.assertEqual(progress_events[-1]["fragment_concurrency"], 8)

    @patch("app.downloader._run_ytdlp_download")
    def test_bot_challenge_does_not_retry(self, run_download) -> None:
        error = RuntimeError("Sign in to confirm you're not a bot")
        run_download.side_effect = error

        with self.assertRaisesRegex(RuntimeError, "not a bot"):
            _download_with_adaptive_concurrency(
                "https://www.youtube.com/watch?v=test",
                {"concurrent_fragment_downloads": 16},
                lambda info: None,
                None,
            )

        self.assertEqual(run_download.call_count, 1)


if __name__ == "__main__":
    unittest.main()
