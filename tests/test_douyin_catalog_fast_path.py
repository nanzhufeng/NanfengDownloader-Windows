import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.catalog import discover_links
from app.downloader import DownloadOptions


class DouyinCatalogFastPathTests(unittest.TestCase):
    def setUp(self):
        self.options = DownloadOptions(Path('unused-offline-output'), '自动识别', '', None, None)
        self.video_id = '7694986028188257599'
        self.video = f'https://www.douyin.com/video/{self.video_id}'

    def response(self, final_url, html=''):
        opener = MagicMock()
        response = opener.open.return_value.__enter__.return_value
        response.geturl.return_value = final_url
        response.headers.get_content_charset.return_value = 'utf-8'
        response.read.return_value = html.encode('utf-8')
        return opener

    def test_direct_works_are_queued_without_network_or_media_resolution(self):
        for url in (self.video, f'https://www.douyin.com/note/{self.video_id}',
                    f'https://www.douyin.com/?modal_id={self.video_id}'):
            with self.subTest(url=url), patch('app.douyin._build_opener', return_value=self.response(url)) as opener, patch('app.douyin._fetch_douyin_info', return_value=None) as media:
                items = discover_links(url, self.options)
                self.assertEqual(len(items), 1)
                self.assertIn(self.video_id, items[0].url)
                if '/note/' in url:
                    self.assertEqual(items[0].url, url)
                self.assertIn('下载时解析', items[0].title)
                opener.assert_not_called()
                media.assert_not_called()

    def test_shared_video_resolves_once_with_bounded_request_and_no_download_probe(self):
        opener = self.response(self.video)
        text = '2026款理想i6 全新升级！ https://v.douyin.com/fnbl_eklrjM/ 复制此链接'
        with patch('app.douyin._build_opener', return_value=opener), patch('app.douyin._fetch_douyin_info', return_value=None) as media:
            items = discover_links(text, self.options)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].url, self.video)
            self.assertIn('下载时解析', items[0].title)
            media.assert_not_called()
            self.assertEqual(opener.open.call_count, 1)
            self.assertLessEqual(opener.open.call_args.kwargs['timeout'], 8)

    def test_redirect_identity_response_is_closed_without_fetching_target_body(self):
        response = MagicMock()

        def opener_for_redirect(options, redirect_handler=None):
            opener = MagicMock()
            opener.open.side_effect = lambda req, timeout: redirect_handler.redirect_request(req, response, 302, 'Found', {}, self.video)
            return opener

        with patch('app.douyin._build_opener', side_effect=opener_for_redirect):
            items = discover_links('https://v.douyin.com/redirect-fixture/', self.options)
        self.assertEqual([item.url for item in items], [self.video])
        response.close.assert_called_once()
        response.read.assert_not_called()

    def test_complete_author_api_page_does_not_launch_redundant_browser_crawl(self):
        packet = {'aweme_list': [{'aweme_id': self.video_id, 'desc': '真实作品标题',
                                 'author': {'nickname': '测试作者', 'sec_uid': 'author-fixture'}}],
                  'has_more': 0, 'max_cursor': 0}
        with patch('app.douyin._build_opener', return_value=self.response('https://www.douyin.com/user/author-fixture')) as opener, patch('app.douyin._request_douyin_author_api', return_value=packet), patch('app.douyin._discover_douyin_with_browser', return_value=[]) as browser:
            items = discover_links('https://www.douyin.com/user/author-fixture', self.options)
            self.assertEqual([item.title for item in items], ['真实作品标题'])
            self.assertEqual(items[0].creator_name, '测试作者')
            browser.assert_not_called()
            opener.return_value.open.assert_not_called()

    def test_duplicate_source_links_are_not_read_twice(self):
        opener = self.response(self.video)
        url = 'https://v.douyin.com/fnbl_eklrjM/'
        with patch('app.douyin._build_opener', return_value=opener), patch('app.douyin._fetch_douyin_info', return_value=None):
            items = discover_links(f'{url}\n{url}', self.options)
            self.assertEqual(len(items), 1)
            self.assertEqual(opener.open.call_count, 1)

    def test_failed_author_api_still_uses_browser_for_catalog_only(self):
        with patch('app.douyin._build_opener', return_value=self.response('https://www.douyin.com/user/author-fixture')), patch('app.douyin._request_douyin_author_api', return_value=None), patch('app.douyin._discover_douyin_with_browser', return_value=[{'url': self.video, 'title': '作者作品', 'creator_name': '测试作者'}]) as browser:
            items = discover_links('https://www.douyin.com/user/author-fixture', self.options)
            self.assertEqual(len(items), 1)
            browser.assert_called_once()

    def test_browser_author_end_packet_does_not_trigger_idle_scroll_waits(self):
        playwright = MagicMock()
        page = playwright.chromium.launch.return_value.new_context.return_value.new_page.return_value
        response = MagicMock()
        response.url = 'https://www.douyin.com/aweme/v1/web/aweme/post/?sec_user_id=author-fixture'
        response.json.return_value = {'aweme_list': [{'aweme_id': self.video_id, 'desc': '最后一个作品',
                                                    'author': {'nickname': '测试作者', 'sec_uid': 'author-fixture'}}],
                                      'has_more': 0}
        page.goto.side_effect = lambda *args, **kwargs: page.on.call_args.args[1](response)
        manager = MagicMock()
        manager.__enter__.return_value = playwright
        with patch('app.douyin._build_opener'), patch('app.douyin._request_douyin_author_api', return_value=None), patch('app.douyin._find_chrome_path', return_value='fixture-browser'), patch('playwright.sync_api.sync_playwright', return_value=manager):
            items = discover_links('https://www.douyin.com/user/author-fixture', self.options)
            self.assertEqual([item.title for item in items], ['最后一个作品'])
            page.wait_for_timeout.assert_not_called()
            page.evaluate.assert_not_called()

    def test_expired_short_link_is_not_reinterpreted_as_an_author_from_recommendations(self):
        opener = self.response('https://www.douyin.com/', '{"aweme_id":"1234567890123456789","sec_uid":"recommended-author"}')
        with patch('app.douyin._build_opener', return_value=opener), patch('app.douyin._request_douyin_author_api', return_value=None), patch('app.douyin._discover_douyin_with_browser', return_value=[]), self.assertRaisesRegex(RuntimeError, '没有从抖音链接解析'):
            discover_links('https://v.douyin.com/expired-fixture/', self.options)

    def test_short_link_timeout_does_not_launch_media_or_browser_fallback(self):
        opener = MagicMock()
        opener.open.side_effect = TimeoutError('fixture timeout')
        with patch('app.douyin._build_opener', return_value=opener), patch('app.douyin._sniff_douyin_with_browser') as browser, self.assertRaises((TimeoutError, RuntimeError)):
            discover_links('https://v.douyin.com/timeout-fixture/', self.options)
        browser.assert_not_called()

    def test_author_api_pagination_keeps_all_target_items_until_explicit_end(self):
        def packet(item_id, more, cursor):
            return {'aweme_list': [{'aweme_id': item_id, 'desc': f'作品 {cursor}',
                                   'author': {'nickname': '测试作者', 'sec_uid': 'author-fixture'}}],
                    'has_more': more, 'max_cursor': cursor}
        with patch('app.douyin._build_opener'), patch('app.douyin._request_douyin_author_api', side_effect=[packet(self.video_id, 1, 20), packet('7694986028188257600', 0, 40)]), patch('app.douyin._discover_douyin_with_browser') as browser:
            items = discover_links('https://www.douyin.com/user/author-fixture', self.options)
            self.assertEqual([item.title for item in items], ['作品 20', '作品 40'])
            browser.assert_not_called()
