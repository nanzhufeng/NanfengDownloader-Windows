from __future__ import annotations

import os
import unittest

from app.auth_profile import SUPPORTED_LOGIN_PLATFORMS
from app.downloader import detect_platform, split_urls


MAC_DOUYIN_SHARE_TEXT = (
    "1.74 e@o.qE :2pm PKj:/ 07/19 Mark Cuban谈AI泡沫：谁会先被淘汰？ "
    "https://v.douyin.com/8V9vbgG9Idk/ 复制此链接，打开Dou音搜索，直接观看视频！"
)


class MacDouyinShareInputTests(unittest.TestCase):
    def test_mac_share_text_extracts_the_douyin_short_link(self) -> None:
        self.assertEqual(
            split_urls(MAC_DOUYIN_SHARE_TEXT),
            ["https://v.douyin.com/8V9vbgG9Idk/"],
        )


class TikTokInputTests(unittest.TestCase):
    def test_share_text_extracts_tiktok_links_and_detects_platform(self) -> None:
        text = (
            "Watch this video https://www.tiktok.com/@corgibobaa/video/7668895435855039757 "
            "or profile https://www.tiktok.com/@corgibobaa"
        )

        self.assertEqual(
            split_urls(text),
            [
                "https://www.tiktok.com/@corgibobaa/video/7668895435855039757",
                "https://www.tiktok.com/@corgibobaa",
            ],
        )
        self.assertEqual(
            detect_platform("https://www.tiktok.com/@corgibobaa/video/7668895435855039757"),
            "TikTok",
        )

    def test_tiktok_has_an_independent_managed_login_profile(self) -> None:
        self.assertIn("tiktok", SUPPORTED_LOGIN_PLATFORMS)

    def test_tiktok_mobile_short_link_is_recognized(self) -> None:
        self.assertEqual(detect_platform("https://vm.tiktok.com/ZMexample/"), "TikTok")


class TikTokCatalogTests(unittest.TestCase):
    def test_profile_catalog_keeps_only_the_requested_creator(self) -> None:
        from app.tiktok import catalog_items_from_tiktok_info

        info = {
            "title": "corgibobaa",
            "entries": [
                {
                    "id": "7668895435855039757",
                    "title": "目标短视频",
                    "url": "https://www.tiktok.com/@corgibobaa/video/7668895435855039757",
                    "uploader": "corgibobaa",
                    "uploader_id": "6935371178089399301",
                    "timestamp": 1785553870,
                },
                {
                    "id": "7653329176426040589",
                    "title": "目标长视频",
                    "url": "https://www.tiktok.com/@corgibobaa/video/7653329176426040589",
                    "uploader": "corgibobaa",
                    "uploader_id": "6935371178089399301",
                    "upload_date": "20260714",
                },
                {
                    "id": "7000000000000000000",
                    "title": "推荐作者视频",
                    "url": "https://www.tiktok.com/@other/video/7000000000000000000",
                    "uploader": "other",
                    "uploader_id": "other-id",
                },
            ],
        }

        items = catalog_items_from_tiktok_info(
            info,
            source_url="https://www.tiktok.com/@corgibobaa",
            max_items=50,
        )

        self.assertEqual(len(items), 2)
        self.assertEqual({item.platform for item in items}, {"TikTok"})
        self.assertEqual({item.creator_name for item in items}, {"corgibobaa"})
        self.assertEqual(
            [item.url for item in items],
            [
                "https://www.tiktok.com/@corgibobaa/video/7668895435855039757",
                "https://www.tiktok.com/@corgibobaa/video/7653329176426040589",
            ],
        )


class TikTokLoginLayoutTests(unittest.TestCase):
    def test_tiktok_login_is_added_without_moving_existing_input_rows(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from app.main import MainWindow

        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        try:
            window.resize(1820, 1130)
            window.show()
            app.processEvents()
            buttons = [
                window.login_douyin_button,
                window.login_youtube_button,
                window.login_bilibili_button,
                window.login_xiaohongshu_button,
                window.login_tiktok_button,
            ]
            self.assertEqual([button.width() for button in buttons], [150] * 5)
            self.assertEqual(len({button.geometry().y() for button in buttons}), 1)
            self.assertEqual(window.output_edit.width(), window.url_text.width())
            self.assertEqual(window.clear_url_button.geometry().x(), window.import_button.geometry().x())
            self.assertGreater(window.clear_url_button.geometry().y(), window.import_button.geometry().y())
        finally:
            window.close()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
