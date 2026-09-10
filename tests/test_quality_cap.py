import unittest
from yt_dlp import YoutubeDL
from app.downloader import build_format_selector


class QualityCapTests(unittest.TestCase):
    def test_720_never_falls_back_to_1080(self):
        with YoutubeDL({'quiet': True}) as ydl:
            select = ydl.build_format_selector(build_format_selector('720p 及以下'))
            high = dict(format_id='high', height=1080, width=1920, ext='mp4', vcodec='h264', acodec='aac', url='https://example.org/v.mp4', protocol='https')
            self.assertEqual(list(select({'formats': [high], 'incomplete_formats': False})), [])
            low = dict(high, format_id='low', height=720, width=1280)
            chosen = list(select({'formats': [low, high], 'incomplete_formats': False}))
            self.assertEqual(chosen[0]['height'], 720)
