import unittest
from unittest.mock import MagicMock, patch
from app.web_media import preferred_episode_source


class EpisodeSourceTests(unittest.TestCase):
    def test_player_initialization_refreshes_late_source_links(self):
        from app.web_media import resolve_browser_media
        page_url = 'https://yhdm.one/vod-play/1999457734/ep1163.html'
        media = 'https://bfikuncdn.com/20260526/GVMy3prs/index.m3u8'
        wrapper = 'https://yhdm.one/_player_x_/' + media
        runtime = MagicMock()
        browser = runtime.__enter__.return_value.chromium.launch.return_value
        page = browser.new_context.return_value.new_page.return_value
        page.goto.return_value.status = 200
        anchors = MagicMock()
        anchors.evaluate_all.side_effect = [[], [('IK', wrapper)]]
        heading = MagicMock()
        heading.first.count.return_value = 0
        page.locator.side_effect = lambda selector: anchors if selector == 'a[href]' else heading
        page.title.return_value = '海贼王 第1163集'
        frame = MagicMock()
        frame.url = page_url
        frame.locator.return_value.evaluate_all.return_value = ['https://slow.example/index.m3u8']
        page.frames = [frame]
        with patch('playwright.sync_api.sync_playwright', return_value=runtime), patch('app.douyin._find_chrome_path', return_value='chrome'):
            result = resolve_browser_media(page_url)
        self.assertEqual(result, (media, wrapper, '海贼王 第1163集'))
        browser.close.assert_called_once()

    def test_only_explicit_same_episode_source_is_selected(self):
        page = 'https://yhdm.one/vod-play/1999457734/ep1149.html'
        media = 'https://bfikuncdn.com/20251109/8l5KHJ4q/index.m3u8'
        wrapper = 'https://yhdm.one/_player_x_/' + media
        self.assertEqual(preferred_episode_source(page, [('IK', wrapper)]), (media, wrapper))
        self.assertIsNone(preferred_episode_source(page, [('IK', 'https://other.test/_player_x_/' + media)]))
        self.assertIsNone(preferred_episode_source('https://other.test/video', [('IK', wrapper)]))
        self.assertIsNone(preferred_episode_source(page, [('下一集', wrapper)]))
        self.assertIsNone(preferred_episode_source(page, []))
