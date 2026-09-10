import unittest
from app.web_media import select_media, clean_page_title


class PlayerSelectionTests(unittest.TestCase):
    def test_episode_title_retained(self):
        self.assertEqual(clean_page_title("海贼王 第1177集 在线播放 - 樱花动漫"), "海贼王 第1177集")

    def test_placeholder_is_not_title(self):
        self.assertIsNone(clean_page_title("index"))
    def test_duplicate_source_is_one_player(self):
        self.assertEqual(select_media(["https://example.org/v.mp4"] * 2), "https://example.org/v.mp4")

    def test_blob_is_not_download_url(self):
        self.assertIsNone(select_media(["blob:https://example.org/1"]))

    def test_ambiguous_players_are_not_guessed(self):
        with self.assertRaises(RuntimeError):
            select_media(["https://example.org/ad.mp4", "https://example.org/movie.mp4"])
