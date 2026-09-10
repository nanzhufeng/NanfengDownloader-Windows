import unittest
from app.downloader import normalize_vimeo_download_url


class VimeoRoutingTests(unittest.TestCase):
    def test_public_player_route(self):
        self.assertEqual(normalize_vimeo_download_url('https://vimeo.com/227128119?fl=pl&fe=cm'),
                         'https://player.vimeo.com/video/227128119')

    def test_unlisted_hash_preserved(self):
        self.assertEqual(normalize_vimeo_download_url('https://vimeo.com/123/abc'),
                         'https://player.vimeo.com/video/123?h=abc')

    def test_other_urls_unchanged(self):
        for url in ['https://vimeo.com/channels/example', 'https://example.org/vimeo.com/123']:
            self.assertEqual(normalize_vimeo_download_url(url), url)
