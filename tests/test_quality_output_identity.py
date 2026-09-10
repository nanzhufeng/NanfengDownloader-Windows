import unittest
from app.downloader import generic_output_name


class QualityOutputIdentityTests(unittest.TestCase):
    def test_actual_resolution_not_requested_quality(self):
        from yt_dlp import YoutubeDL
        template = generic_output_name('海贼王 第1177集', '720p 及以下')
        with YoutubeDL({'outtmpl': template, 'quiet': True}) as ydl:
            for height in (720, 1080):
                name = ydl.prepare_filename({'id': 'sample', 'title': 'sample', 'height': height, 'ext': 'mp4'})
                self.assertEqual(name, f'海贼王 第1177集 {height}p.mp4')
        self.assertNotIn('选项', template)

    def test_audio_not_marked_as_video_resolution(self):
        self.assertNotIn('height', generic_output_name('标题', '仅音频 MP3'))
