import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.douyin import _run_ffmpeg
from app.downloader import DownloadOptions, DownloadResult, DownloadStopped, build_ydl_options
from app.main import DownloadWorker, QueueItem


class DownloadCancellationTests(unittest.TestCase):
    def test_ytdlp_progress_hook_interrupts_current_download(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            options = DownloadOptions(
                output_dir=Path(temp_dir),
                quality="360p 及以下",
                cookie_mode="不使用登录态",
                cookie_file=None,
                ffmpeg_dir=None,
            )
            ydl_options = build_ydl_options(options, lambda info: None, lambda: True)

            with self.assertRaises(DownloadStopped):
                ydl_options["progress_hooks"][0]({"status": "downloading"})

    def test_ffmpeg_process_is_terminated_when_stop_is_requested(self) -> None:
        class FakeProcess:
            def __init__(self) -> None:
                self.terminated = False

            def poll(self):
                return None

            def terminate(self) -> None:
                self.terminated = True

            def wait(self, timeout=None) -> int:
                return 0

        process = FakeProcess()
        with patch("app.douyin.subprocess.Popen", return_value=process):
            with self.assertRaises(DownloadStopped):
                _run_ffmpeg(["ffmpeg", "-version"], lambda: True)

        self.assertTrue(process.terminated)


class DownloadSelectionTests(unittest.TestCase):
    def test_worker_rechecks_each_row_and_skips_newly_unchecked_item(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            options = DownloadOptions(
                output_dir=Path(temp_dir),
                quality="360p 及以下",
                cookie_mode="不使用登录态",
                cookie_file=None,
                ffmpeg_dir=None,
            )
            items = [
                QueueItem("https://example.test/1", "YouTube", "作者", "360p 及以下", 0),
                QueueItem("https://example.test/2", "YouTube", "作者", "360p 及以下", 1),
            ]
            worker = DownloadWorker(items, options)
            stopped_rows: list[int] = []
            worker.item_stopped.connect(stopped_rows.append)

            with patch.object(worker, "_ask_should_download", side_effect=[True, False]):
                with patch(
                    "app.main.download_url",
                    return_value=DownloadResult(files=[Path(temp_dir) / "done.mp4"]),
                ) as download:
                    worker.run()

        self.assertEqual(download.call_count, 1)
        self.assertEqual(stopped_rows, [1])


if __name__ == "__main__":
    unittest.main()
