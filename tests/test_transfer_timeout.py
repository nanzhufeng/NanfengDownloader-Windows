import unittest
from unittest.mock import patch
from app.downloader import _download_with_adaptive_concurrency


class TransferTimeoutTests(unittest.TestCase):
    def test_timeout_steps_down_and_keeps_resume(self):
        events = []
        with patch('app.downloader._run_ytdlp_download', side_effect=[TimeoutError('read timed out'), 0]) as run:
            result = _download_with_adaptive_concurrency('https://example.org/a.m3u8',
                {'concurrent_fragment_downloads': 16, 'continuedl': True}, events.append, None)
        self.assertEqual(result, 0)
        self.assertEqual(run.call_args_list[1].args[1]['concurrent_fragment_downloads'], 8)
        self.assertTrue(run.call_args_list[1].args[1]['continuedl'])
        self.assertIn('超时', events[0]['reason'])
