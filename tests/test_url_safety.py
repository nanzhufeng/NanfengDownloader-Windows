from __future__ import annotations

import unittest

from app.downloader import detect_platform
from app.url_safety import url_host_matches


class UrlSafetyTests(unittest.TestCase):
    def test_platform_detection_accepts_real_platform_hosts(self) -> None:
        self.assertEqual(detect_platform("https://www.douyin.com/video/1234567890123456"), "抖音")
        self.assertEqual(detect_platform("https://www.youtube.com/watch?v=abc"), "YouTube")
        self.assertEqual(detect_platform("https://space.bilibili.com/123"), "哔哩哔哩")
        self.assertEqual(detect_platform("https://www.xiaohongshu.com/explore/abc"), "小红书")
        self.assertEqual(detect_platform("https://www.tiktok.com/@creator/video/1"), "TikTok")

    def test_platform_detection_rejects_domains_hidden_in_path_or_query(self) -> None:
        self.assertEqual(detect_platform("https://example.test/douyin.com/video/1"), "未知")
        self.assertEqual(detect_platform("https://example.test/?redirect=https://youtube.com/watch?v=x"), "未知")
        self.assertEqual(detect_platform("https://notbilibili.com/video/BV1"), "未知")
        self.assertEqual(detect_platform("https://evil.tiktok.com.example/video/1"), "未知")
        self.assertFalse(url_host_matches("https://example.test/xhslink.com", "xhslink.com"))
