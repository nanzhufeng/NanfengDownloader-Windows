import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock
from app.downloader import DownloadOptions, DownloadResult, DownloadStopped, find_ffmpeg_dir
from app.quality_fallback import download_with_quality_choice, convert_quality, QualityChoiceCancelled


class QualityFallbackTests(unittest.TestCase):
    def test_real_ytdlp_error_requests_choice(self):
        from yt_dlp.utils import DownloadError
        download = Mock(side_effect=[DownloadError('ERROR: [generic] index: Requested format is not available. Use --list-formats for a list of available formats'), DownloadResult([])])
        choose = Mock(return_value='original')
        options = DownloadOptions(Path('.'), '720p 及以下', '', None, None)
        download_with_quality_choice('https://example.org', options, lambda x: None, lambda: False, choose, download)
        choose.assert_called_once_with('720p 及以下')
        self.assertEqual(download.call_count, 2)

    def test_other_download_errors_do_not_request_quality_choice(self):
        from yt_dlp.utils import DownloadError
        choose = Mock()
        options = DownloadOptions(Path('.'), '720p 及以下', '', None, None)
        with self.assertRaises(DownloadError):
            download_with_quality_choice('https://example.org', options, lambda x: None, lambda: False, choose,
                Mock(side_effect=DownloadError('HTTP Error 403')))
        choose.assert_not_called()

    def test_cancel_does_not_download_original(self):
        download = Mock(side_effect=RuntimeError('Requested format is not available'))
        options = DownloadOptions(Path('.'), '720p 及以下', '', None, None)
        with self.assertRaises(QualityChoiceCancelled):
            download_with_quality_choice('https://example.org', options, lambda x: None, lambda: False, lambda q: 'cancel', download)
        self.assertEqual(download.call_count, 1)

    def test_original_requires_choice_and_keeps_setting(self):
        download = Mock(side_effect=[RuntimeError('Requested format is not available'), DownloadResult([])])
        options = DownloadOptions(Path('.'), '720p 及以下', '', None, None)
        download_with_quality_choice('https://example.org', options, lambda x: None, lambda: False, lambda q: 'original', download)
        self.assertEqual(download.call_args.args[1].quality, '最佳画质')
        self.assertEqual(options.quality, '720p 及以下')

    def test_real_conversion_retains_source_and_checks_dimensions(self):
        ffmpeg = find_ffmpeg_dir(Path(__file__).resolve().parents[1])
        if not ffmpeg:
            self.skipTest('FFmpeg required')
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / 'sample 1080p.mp4'
            subprocess.run([str(ffmpeg / 'ffmpeg.exe'), '-v', 'error', '-f', 'lavfi', '-i',
                'color=c=blue:s=1920x1080:d=0.2', '-c:v', 'libx264', str(source)], check=True, timeout=30)
            before = source.read_bytes()
            events = []
            result = convert_quality(source, 720, ffmpeg, events.append, lambda: False)
            self.assertEqual(result.name, 'sample 720p.mp4')
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(events[-1]['info_dict'], {'width': 1280, 'height': 720})
