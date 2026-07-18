import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.downloader import _validated_media_files
from app.media_validation import (
    InvalidMediaError,
    is_probable_existing_media,
    validate_media_file,
)


def _fake_mp4_bytes() -> bytes:
    return b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2" + b"\x00" * 128


class MediaValidationTests(unittest.TestCase):
    def test_valid_mp4_header_passes_without_ffprobe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "valid.mp4"
            target.write_bytes(_fake_mp4_bytes())

            result = validate_media_file(target)

        self.assertEqual(result.method, "header")
        self.assertGreater(result.size, 0)

    def test_html_disguised_as_mp4_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "fake.mp4"
            target.write_text("<!doctype html><html>blocked</html>", encoding="utf-8")

            with self.assertRaisesRegex(InvalidMediaError, "网页或接口文本"):
                validate_media_file(target)

            self.assertFalse(is_probable_existing_media(target))

    def test_ffprobe_must_report_format_and_positive_duration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "probe.mp4"
            target.write_bytes(_fake_mp4_bytes())
            ffmpeg_dir = Path(temp_dir) / "ffmpeg"
            ffmpeg_dir.mkdir()
            (ffmpeg_dir / "ffprobe.exe").touch()

            completed = SimpleNamespace(
                returncode=0,
                stdout='{"format":{"format_name":"mov,mp4","duration":"2.5","size":"152"}}',
                stderr="",
            )
            with patch("app.media_validation.subprocess.run", return_value=completed):
                result = validate_media_file(target, ffmpeg_dir)

        self.assertEqual(result.method, "ffprobe")
        self.assertEqual(result.duration, 2.5)

    def test_invalid_new_file_is_removed_before_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "fake.mp4"
            target.write_text("<html>not media</html>", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "网页或接口文本"):
                _validated_media_files([target], None)

            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
