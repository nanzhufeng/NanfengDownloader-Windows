import unittest
from pathlib import Path
from unittest.mock import patch

from app.catalog import discover_links
from app.downloader import DownloadOptions


class CatalogRequestContractTests(unittest.TestCase):
    def test_bilibili_single_work_does_not_ask_extractor_to_expand_related_playlist(self):
        url = 'https://www.bilibili.com/video/BV1testfixture?p=2'
        options = DownloadOptions(Path('unused-offline-output'), '自动识别', '', None, None)
        info = {'id': 'BV1testfixture', 'title': '指定分P', 'webpage_url': url, 'uploader': '测试作者'}
        with patch('yt_dlp.YoutubeDL') as factory:
            factory.return_value.__enter__.return_value.extract_info.return_value = info
            items = discover_links(url, options)
        self.assertEqual([item.url for item in items], [url])
        self.assertTrue(factory.call_args.args[0]['noplaylist'], 'single work must not implicitly expand a collection')

    def test_bilibili_multi_part_page_without_p_preserves_part_selection(self):
        url = 'https://www.bilibili.com/video/BV1testfixture'
        options = DownloadOptions(Path('unused-offline-output'), '自动识别', '', None, None)
        info = {'_type': 'playlist', 'entries': [
            {'id': 'part1', 'title': '第一部分', 'webpage_url': url + '?p=1'},
            {'id': 'part2', 'title': '第二部分', 'webpage_url': url + '?p=2'},
        ]}
        with patch('yt_dlp.YoutubeDL') as factory:
            factory.return_value.__enter__.return_value.extract_info.return_value = info
            items = discover_links(url, options)
        self.assertEqual([item.url for item in items], [url + '?p=1', url + '?p=2'])
        self.assertFalse(factory.call_args.args[0]['noplaylist'])
