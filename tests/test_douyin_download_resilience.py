import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.douyin import DouyinInfo, _download_binary, download_douyin_url
from app.downloader import DownloadOptions


class FakeResponse:
    def __init__(self, payload: bytes, headers: dict[str, str], status: int) -> None:
        self.payload = payload
        self.headers = headers
        self.status = status
        self.offset = 0

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        if self.offset >= len(self.payload):
            return b""
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


class DouyinDownloadResilienceTests(unittest.TestCase):
    def test_packet_validation_failure_refreshes_url_and_redownloads_once(self) -> None:
        info = DouyinInfo(
            aweme_id="1234567890123456789",
            title="测试视频",
            video_url="https://video.example/first.mp4",
            publish_date="2026-08-21",
            author_name="测试作者",
        )
        progress: list[dict[str, object]] = []

        def write_media(_: str, target: Path, *__: object) -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"\x00\x00\x00\x18ftyp" + b"a" * 1024)

        with tempfile.TemporaryDirectory() as temp_dir:
            options = DownloadOptions(
                output_dir=Path(temp_dir),
                quality="720p 及以下",
                cookie_mode="软件内登录",
                cookie_file=None,
                ffmpeg_dir=None,
            )
            with (
                patch("app.douyin._fetch_douyin_info", side_effect=[info, info]) as fetch,
                patch("app.douyin._download_binary", side_effect=write_media) as download,
                patch(
                    "app.douyin._validate_douyin_output",
                    side_effect=[
                        RuntimeError("抖音下载结果校验失败：下载结果的数据包不完整：测试.mp4"),
                        None,
                    ],
                ),
                patch("app.douyin.time.sleep"),
            ):
                result = download_douyin_url(
                    "https://www.douyin.com/video/1234567890123456789",
                    options,
                    progress.append,
                )

            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(download.call_count, 2)
            self.assertEqual(len(result.files), 1)
            self.assertTrue(result.files[0].exists())
            self.assertTrue(any(item.get("status") == "retrying" for item in progress))

    def test_other_validation_errors_do_not_trigger_blind_redownload(self) -> None:
        info = DouyinInfo(
            aweme_id="1234567890123456789",
            title="测试视频",
            video_url="https://video.example/first.mp4",
            publish_date="2026-08-21",
            author_name="测试作者",
        )

        def write_media(_: str, target: Path, *__: object) -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"\x00\x00\x00\x18ftyp" + b"a" * 1024)

        with tempfile.TemporaryDirectory() as temp_dir:
            options = DownloadOptions(
                output_dir=Path(temp_dir),
                quality="720p 及以下",
                cookie_mode="软件内登录",
                cookie_file=None,
                ffmpeg_dir=None,
            )
            with (
                patch("app.douyin._fetch_douyin_info", return_value=info) as fetch,
                patch("app.douyin._download_binary", side_effect=write_media) as download,
                patch(
                    "app.douyin._validate_douyin_output",
                    side_effect=RuntimeError("抖音下载结果校验失败：ffprobe 无法验证下载结果"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "ffprobe 无法验证"):
                    download_douyin_url(
                        "https://www.douyin.com/video/1234567890123456789",
                        options,
                        lambda _: None,
                    )

            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(download.call_count, 1)

    def test_premature_eof_resumes_with_http_range(self) -> None:
        requests: list[urllib.request.Request] = []
        responses = iter(
            [
                FakeResponse(
                    b"\x00\x00\x00\x18ftyp" + b"a" * 8,
                    {"Content-Length": "24", "Content-Type": "video/mp4"},
                    200,
                ),
                FakeResponse(
                    b"b" * 8,
                    {"Content-Range": "bytes 16-23/24", "Content-Type": "video/mp4"},
                    206,
                ),
            ]
        )

        class FakeOpener:
            def open(self, request: urllib.request.Request, timeout: int) -> FakeResponse:
                requests.append(request)
                return next(responses)

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "video.mp4"
            with (
                patch("app.douyin._build_opener", return_value=FakeOpener()),
                patch("app.douyin.time.sleep"),
            ):
                _download_binary(
                    "https://video.example/video.mp4",
                    target,
                    SimpleNamespace(),
                    lambda _: None,
                )

            self.assertEqual(target.read_bytes(), b"\x00\x00\x00\x18ftyp" + b"a" * 8 + b"b" * 8)
            self.assertEqual(len(requests), 2)
            self.assertIsNone(requests[0].get_header("Range"))
            self.assertEqual(requests[1].get_header("Range"), "bytes=16-")

    def test_connection_reset_before_response_is_retried(self) -> None:
        attempts = 0
        payload = b"\x00\x00\x00\x18ftyp" + b"a" * (64 * 1024)

        class FakeOpener:
            def open(self, request: urllib.request.Request, timeout: int) -> FakeResponse:
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    raise urllib.error.URLError(ConnectionResetError(10054, "reset"))
                return FakeResponse(
                    payload,
                    {"Content-Length": str(len(payload)), "Content-Type": "video/mp4"},
                    200,
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "video.mp4"
            with (
                patch("app.douyin._build_opener", return_value=FakeOpener()),
                patch("app.douyin.time.sleep"),
            ):
                _download_binary(
                    "https://video.example/video.mp4",
                    target,
                    SimpleNamespace(),
                    lambda _: None,
                )

            self.assertEqual(attempts, 2)
            self.assertEqual(target.read_bytes(), payload)

    def test_repeated_connection_resets_keep_retry_headroom(self) -> None:
        attempts = 0
        payload = b"\x00\x00\x00\x18ftyp" + b"a" * (64 * 1024)

        class FakeOpener:
            def open(self, request: urllib.request.Request, timeout: int) -> FakeResponse:
                nonlocal attempts
                attempts += 1
                if attempts <= 5:
                    raise urllib.error.URLError(ConnectionResetError(10054, "reset"))
                return FakeResponse(
                    payload,
                    {"Content-Length": str(len(payload)), "Content-Type": "video/mp4"},
                    200,
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "video.mp4"
            with (
                patch("app.douyin._build_opener", return_value=FakeOpener()),
                patch("app.douyin.time.sleep"),
            ):
                _download_binary(
                    "https://video.example/video.mp4",
                    target,
                    SimpleNamespace(),
                    lambda _: None,
                )

            self.assertEqual(attempts, 6)
            self.assertEqual(target.read_bytes(), payload)

    def test_ignored_range_restarts_without_appending_duplicate_bytes(self) -> None:
        payload = b"\x00\x00\x00\x18ftyp" + b"a" * 16
        responses = iter(
            [
                FakeResponse(
                    payload[:12],
                    {"Content-Length": str(len(payload)), "Content-Type": "video/mp4"},
                    200,
                ),
                FakeResponse(
                    payload,
                    {"Content-Length": str(len(payload)), "Content-Type": "video/mp4"},
                    200,
                ),
            ]
        )

        class FakeOpener:
            def open(self, request: urllib.request.Request, timeout: int) -> FakeResponse:
                return next(responses)

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "video.mp4"
            with (
                patch("app.douyin._build_opener", return_value=FakeOpener()),
                patch("app.douyin.time.sleep"),
            ):
                _download_binary(
                    "https://video.example/video.mp4",
                    target,
                    SimpleNamespace(),
                    lambda _: None,
                )

            self.assertEqual(target.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
