import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.downloader import DownloadOptions, download_url


class ExistingTaskOutputTests(unittest.TestCase):
    def test_exact_finished_file_is_skipped_not_failed(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / 'episode.mp4'
            target.write_bytes(b'fixture')
            def run(url, opts, progress, cancel):
                for hook in opts['progress_hooks']:
                    hook({'status': 'finished', 'filename': str(target)})
                return 0
            with patch('app.downloader._download_with_adaptive_concurrency', side_effect=run), patch('app.downloader.validate_media_file') as validate:
                result = download_url('https://example.org/episode', DownloadOptions(Path(root), '720p 及以下', '不使用登录态', None, None), lambda event: None)
            self.assertTrue(result.skipped)
            self.assertEqual(result.files, [target.resolve()])
            validate.assert_called_once()
