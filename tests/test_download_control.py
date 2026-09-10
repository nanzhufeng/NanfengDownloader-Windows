import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.douyin import _run_ffmpeg
from app.downloader import (
    DownloadOptions,
    DownloadResult,
    DownloadStopped,
    assert_supported_platform_url,
    build_ydl_options,
)
from app.main import DownloadWorker, QueueItem


class DownloadCancellationTests(unittest.TestCase):
    def test_unknown_platform_uses_generic_route(self) -> None:
        self.assertEqual(assert_supported_platform_url("https://unsupported.example/video/1"), "其他网站")

    def test_unknown_platform_does_not_export_a_managed_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            options = DownloadOptions(
                output_dir=Path(temp_dir),
                quality="360p 及以下",
                cookie_mode="软件内登录",
                cookie_file=None,
                ffmpeg_dir=None,
            )
            with patch("app.downloader.export_auth_cookies_txt") as export_cookie:
                ydl_options = build_ydl_options(
                    options,
                    lambda info: None,
                    auth_platform=None,
                )

        export_cookie.assert_not_called()
        self.assertNotIn("cookiefile", ydl_options)

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
    def test_convert_choice_reuses_target_for_batch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            options = DownloadOptions(Path(temp_dir), "720p 及以下", "不使用登录态", None, Path(temp_dir))
            items = [QueueItem(f"https://example.test/{i}", "其他网站", None, "1080p 及以下" if i else "720p 及以下", i) for i in range(3)]
            worker = DownloadWorker(items, options)
            worker.should_download_row.connect(lambda row: worker.receive_row_check(True))
            prompts = []
            def answer(quality):
                prompts.append(quality)
                worker.receive_quality_choice("convert")
            worker.quality_choice_requested.connect(answer)
            def download(url, opts, progress, cancel):
                if opts.quality != "最佳画质":
                    raise RuntimeError("Requested format is not available")
                return DownloadResult(files=[Path(temp_dir) / "source.mp4"])
            with patch("app.main.download_url", side_effect=download), patch("app.quality_fallback.convert_quality", return_value=Path(temp_dir) / "720p.mp4") as convert:
                worker.run()
            self.assertEqual(prompts, ["720p 及以下"])
            self.assertEqual([call.args[1] for call in convert.call_args_list], [720, 720, 720])

    def test_original_choice_applies_to_remaining_batch_and_not_next_batch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            options = DownloadOptions(Path(temp_dir), "720p 及以下", "不使用登录态", None, None)
            items = [QueueItem(f"https://example.test/{i}", "其他网站", None, "720p 及以下", i) for i in range(3)]
            prompts = []
            qualities = []
            def download(url, opts, progress, cancel):
                qualities.append(opts.quality)
                if opts.quality != "最佳画质":
                    raise RuntimeError("Requested format is not available")
                return DownloadResult(files=[])
            for batch in range(2):
                worker = DownloadWorker(items, options)
                worker.should_download_row.connect(lambda row, w=worker: w.receive_row_check(True, "720p 及以下"))
                def answer(quality, w=worker):
                    prompts.append(quality)
                    w.receive_quality_choice("original")
                worker.quality_choice_requested.connect(answer)
                with patch("app.main.download_url", side_effect=download):
                    worker.run()
            self.assertEqual(prompts, ["720p 及以下", "720p 及以下"])
            self.assertEqual(qualities, ["720p 及以下", "最佳画质", "最佳画质", "最佳画质"] * 2)

    def test_waiting_item_uses_latest_quality_not_batch_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            options = DownloadOptions(Path(temp_dir), "720p 及以下", "不使用登录态", None, None)
            items = [QueueItem("https://example.test/1", "其他网站", None, "720p 及以下", 0),
                     QueueItem("https://example.test/2", "其他网站", None, "720p 及以下", 1)]
            worker = DownloadWorker(items, options)
            worker.should_download_row.connect(
                lambda row: worker.receive_row_check(True, "720p 及以下" if row == 0 else "1080p 及以下")
            )
            with patch("app.main.download_url", return_value=DownloadResult(files=[])) as download:
                worker.run()
            self.assertEqual([call.args[1].quality for call in download.call_args_list],
                             ["720p 及以下", "1080p 及以下"])

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
