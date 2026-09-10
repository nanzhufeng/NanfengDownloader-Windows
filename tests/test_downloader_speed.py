import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_dlp import YoutubeDL
from yt_dlp.downloader import get_suitable_downloader

from app.downloader import (
    DownloadOptions,
    _ExternalDirectProgressMonitor,
    _ExternalProgressState,
    _content_length_from_headers,
    _external_download_total_bytes,
    _download_with_adaptive_concurrency,
    _is_fragment_rate_limit_error,
    _youtube_download_profiles,
    _apply_single_media_download_options,
    build_format_selector,
    build_format_sort,
    build_direct_http_acceleration_options,
    build_youtube_runtime_options,
    build_ydl_options,
    find_aria2c,
    find_node_runtime,
    youtube_pot_provider_home,
)


class DownloadSpeedOptionsTests(unittest.TestCase):
    def test_empty_and_tls_eof_retry_with_bounded_lower_concurrency(self):
        from yt_dlp.utils import DownloadError
        for message in ["The downloaded file is empty", "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol"]:
            with self.subTest(message=message):
                events = []
                with patch('app.downloader._run_ytdlp_download', side_effect=[DownloadError(message), 0]) as run:
                    self.assertEqual(_download_with_adaptive_concurrency('https://example.test/index.m3u8', {}, events.append, None), 0)
                if 'SSL' in message:
                    self.assertEqual(run.call_args_list[1].args[1]['proxy'], '')
                else:
                    self.assertLess(run.call_args_list[1].args[1]['concurrent_fragment_downloads'], run.call_args_list[0].args[1]['concurrent_fragment_downloads'])
                self.assertTrue(events)
                self.assertNotIn('nocheckcertificate', run.call_args_list[1].args[1])
                with patch('app.downloader._run_ytdlp_download', side_effect=DownloadError(message)) as run:
                    with self.assertRaises(DownloadError):
                        _download_with_adaptive_concurrency('https://example.test/index.m3u8', {}, events.append, None)
                self.assertEqual(run.call_count, len(_youtube_download_profiles({})) + (1 if 'SSL' in message else 0))

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

    def test_default_output_groups_files_by_platform_without_creator_subfolder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            options = DownloadOptions(
                output_dir=Path(temp_dir),
                quality="720p 及以下",
                cookie_mode="不使用登录态",
                cookie_file=None,
                ffmpeg_dir=None,
                creator_name="不应成为默认目录",
            )
            ydl_options = build_ydl_options(options, lambda info: None)

        normalized = ydl_options["outtmpl"].replace("/", "\\")
        self.assertIn(r"\%(extractor_key)s\%(upload_date)s", normalized)
        self.assertNotIn("不应成为默认目录", normalized)

    def test_creator_subfolder_is_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            options = DownloadOptions(
                output_dir=Path(temp_dir),
                quality="720p 及以下",
                cookie_mode="不使用登录态",
                cookie_file=None,
                ffmpeg_dir=None,
                creator_name="目标作者",
                organize_by_creator=True,
            )
            ydl_options = build_ydl_options(options, lambda info: None)

        self.assertIn("目标作者", ydl_options["outtmpl"])

    def test_external_direct_monitor_reports_bytes_total_and_speed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            state = _ExternalProgressState()
            events: list[dict[str, object]] = []
            monitor = _ExternalDirectProgressMonitor(output_dir, state, events.append, None)
            part_file = output_dir / "PornHub" / "creator" / "video.mp4.part"
            part_file.parent.mkdir(parents=True)
            part_file.write_bytes(b"x" * 400)
            state.set_total_bytes(1000)

            event = monitor.sample_progress()

        self.assertIsNotNone(event)
        self.assertEqual(event["status"], "downloading")
        self.assertEqual(event["downloaded_bytes"], 400)
        self.assertEqual(event["total_bytes"], 1000)
        self.assertEqual(event["progress_label"], "已下载 400B")
        self.assertTrue(str(event["_speed_str"]).endswith("/s"))

    def test_external_direct_monitor_without_total_reports_downloaded_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            state = _ExternalProgressState()
            monitor = _ExternalDirectProgressMonitor(output_dir, state, lambda event: None, None)
            part_file = output_dir / "PornHub" / "video.mp4.part"
            part_file.parent.mkdir(parents=True)
            part_file.write_bytes(b"x" * 1536)

            event = monitor.sample_progress()

        self.assertIsNotNone(event)
        self.assertEqual(event["progress_label"], "已下载 1.5KB")
        self.assertEqual(event["_eta_str"], "-")

    def test_direct_media_size_prefers_content_range_for_range_request(self) -> None:
        self.assertEqual(
            _content_length_from_headers(
                {"Content-Range": "bytes 0-0/987654"},
                range_request=True,
            ),
            987654,
        )

    def test_external_total_uses_all_selected_media_streams(self) -> None:
        total = _external_download_total_bytes(
            {
                "requested_formats": [
                    {"filesize": 1000},
                    {"filesize_approx": 200},
                ]
            }
        )

        self.assertEqual(total, 1200)

    @patch("app.downloader.find_aria2c")
    def test_pornhub_match_filter_passes_selected_total_to_monitor(self, find_aria2c) -> None:
        find_aria2c.return_value = Path(r"C:\tool\aria2c.exe")
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_options = build_ydl_options(
                self._options(temp_dir),
                lambda info: None,
                download_platform="Pornhub",
            )
        state = ydl_options["_nanfeng_external_progress_state"]

        self.assertIsNone(
            ydl_options["match_filter"](
                {
                    "requested_formats": [
                        {
                            "filesize": 800,
                            "url": "https://media.example/video.mp4",
                            "http_headers": {"Referer": "https://example.com/video"},
                        },
                        {"filesize": 200},
                    ]
                }
            )
        )
        self.assertEqual(state.total_bytes(), 1000)
        self.assertEqual(
            state.media_request(),
            ("https://media.example/video.mp4", {"Referer": "https://example.com/video"}),
        )

    def test_video_selector_prefers_separate_https_dash_streams(self) -> None:
        selector = build_format_selector("720p 及以下")

        self.assertTrue(selector.startswith("bv[protocol^=https][ext=mp4][height<=720]+ba[protocol^=https][ext=m4a]"))
        self.assertIn("height<=720", selector)

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
            ydl_options = build_ydl_options(
                self._options(temp_dir),
                lambda info: None,
                download_platform="YouTube",
            )

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

    @patch("app.downloader.shutil.which", return_value=None)
    def test_bundled_aria2_is_discovered_before_path_lookup(self, _which) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundled = Path(temp_dir) / "tools" / "aria2" / "aria2c.exe"
            bundled.parent.mkdir(parents=True)
            bundled.touch()
            with patch("app.downloader._runtime_resource_roots", return_value=[Path(temp_dir)]):
                self.assertEqual(find_aria2c(), bundled)

    @patch("app.downloader.find_aria2c")
    def test_pornhub_direct_http_uses_aria2_but_keeps_manifests_native(self, find_aria2c) -> None:
        find_aria2c.return_value = Path(r"C:\tool\aria2c.exe")

        acceleration = build_direct_http_acceleration_options("Pornhub")

        self.assertEqual(acceleration["external_downloader"]["https"], r"C:\tool\aria2c.exe")
        self.assertEqual(acceleration["external_downloader"]["m3u8"], "native")
        self.assertEqual(acceleration["external_downloader"]["dash"], "native")
        self.assertIn("--split=16", acceleration["external_downloader_args"]["aria2c"])

    @patch("app.downloader.find_aria2c")
    def test_other_platforms_do_not_receive_pornhub_acceleration(self, find_aria2c) -> None:
        find_aria2c.return_value = Path(r"C:\tool\aria2c.exe")

        self.assertEqual(build_direct_http_acceleration_options("YouTube"), {})

    def test_aria2_selection_is_limited_to_direct_http_media(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            options = build_ydl_options(
                self._options(temp_dir),
                lambda info: None,
                download_platform="Pornhub",
            )

        direct = get_suitable_downloader(
            {"url": "https://cdn.example/video.mp4", "protocol": "https"},
            options,
        )
        manifest = get_suitable_downloader(
            {"url": "https://cdn.example/video.m3u8", "protocol": "m3u8_native"},
            options,
        )
        self.assertEqual(direct.__name__, "Aria2cFD")
        self.assertEqual(manifest.__name__, "HlsFD")

    @patch("app.downloader._run_ytdlp_download")
    def test_direct_http_acceleration_falls_back_to_native_once(self, run_download) -> None:
        run_download.side_effect = [RuntimeError("aria2c exited with code 22"), 0]
        progress_events: list[dict[str, object]] = []
        options = {
            "concurrent_fragment_downloads": 16,
            "http_chunk_size": 10 * 1024 * 1024,
            "external_downloader": {"https": r"C:\tool\aria2c.exe"},
            "external_downloader_args": {"aria2c": ["--split=16"]},
        }

        result = _download_with_adaptive_concurrency(
            "https://cn.pornhub.com/view_video.php?viewkey=test",
            options,
            progress_events.append,
            None,
        )

        self.assertEqual(result, 0)
        self.assertEqual(run_download.call_count, 2)
        first_options = run_download.call_args_list[0].args[1]
        fallback_options = run_download.call_args_list[1].args[1]
        self.assertIn("external_downloader", first_options)
        self.assertNotIn("external_downloader", fallback_options)
        self.assertNotIn("external_downloader_args", fallback_options)
        self.assertEqual(fallback_options["concurrent_fragment_downloads"], 1)
        self.assertEqual(fallback_options["http_chunk_size"], 0)
        self.assertIn("高速直连被站点限制", str(progress_events[-1]["reason"]))

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
    def test_repeated_403_falls_back_to_single_connection_without_http_chunks(self, run_download) -> None:
        run_download.side_effect = [
            RuntimeError("HTTP Error 403: Forbidden"),
            RuntimeError("HTTP Error 403: Forbidden"),
            0,
        ]
        progress_events: list[dict[str, object]] = []

        result = _download_with_adaptive_concurrency(
            "https://www.youtube.com/watch?v=test",
            {
                "concurrent_fragment_downloads": 16,
                "http_chunk_size": 10 * 1024 * 1024,
            },
            progress_events.append,
            None,
        )

        self.assertEqual(result, 0)
        self.assertEqual(
            [
                (
                    item.args[1]["concurrent_fragment_downloads"],
                    item.args[1]["http_chunk_size"],
                )
                for item in run_download.call_args_list
            ],
            [(16, 10 * 1024 * 1024), (8, 10 * 1024 * 1024), (1, 0)],
        )
        self.assertIn("稳定单连接", str(progress_events[-1]["reason"]))

    def test_adaptive_profiles_do_not_duplicate_single_connection_fallback(self) -> None:
        self.assertEqual(
            _youtube_download_profiles(
                {"concurrent_fragment_downloads": 1, "http_chunk_size": 0}
            ),
            [(1, 0)],
        )

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

    def test_single_video_urls_do_not_expand_to_playlists(self) -> None:
        cases = (
            "https://www.youtube.com/watch?v=video-id&list=playlist-id",
            "https://www.bilibili.com/video/BV1xx411c7mD?p=2",
            "https://www.tiktok.com/@creator/video/123456789",
        )
        for url in cases:
            ydl_options = {"noplaylist": False}
            _apply_single_media_download_options(url, ydl_options)
            self.assertTrue(ydl_options["noplaylist"], url)


if __name__ == "__main__":
    unittest.main()
