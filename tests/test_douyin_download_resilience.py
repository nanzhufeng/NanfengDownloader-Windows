import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.douyin import _download_binary


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
