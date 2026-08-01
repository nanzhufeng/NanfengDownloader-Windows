from __future__ import annotations

import os
import unittest


class SupportedPlatformSidebarTests(unittest.TestCase):
    def test_sidebar_lists_every_supported_platform_with_a_rendered_icon(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QLabel

        from app.main import MainWindow

        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        try:
            window.resize(1820, 1130)
            window.show()
            app.processEvents()

            expected = [
                ("PlatformDouyin", "抖音", "作者 / 作品"),
                ("PlatformYoutube", "YouTube", "频道 / 播放列表"),
                ("PlatformBilibili", "哔哩哔哩", "UP主 / 视频"),
                ("PlatformXiaohongshu", "小红书", "作者 / 视频笔记"),
                ("PlatformTiktok", "TikTok", "作者 / 作品"),
            ]

            self.assertEqual([card.objectName() for card in window.platform_cards], [item[0] for item in expected])
            for card, (_, title, subtitle) in zip(window.platform_cards, expected, strict=True):
                labels = card.findChildren(QLabel)
                self.assertIn(title, [label.text() for label in labels])
                self.assertIn(subtitle, [label.text() for label in labels])
                icon_labels = [label for label in labels if label.objectName() == "PlatformCardIcon"]
                self.assertEqual(len(icon_labels), 1)
                self.assertFalse(icon_labels[0].pixmap().isNull())

            self.assertEqual(window.output_edit.width(), window.url_text.width())
            self.assertLess(window.platform_cards[-1].geometry().bottom(), window.open_folder_button.geometry().top())
        finally:
            window.close()
            app.processEvents()

    def test_login_buttons_use_platform_icons_and_show_the_optional_login_rule(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QSize
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
            self.assertTrue(all(not button.icon().isNull() for button in buttons))
            self.assertEqual([button.iconSize() for button in buttons], [QSize(18, 18)] * 5)
            self.assertEqual(len({button.geometry().y() for button in buttons}), 1)
            self.assertIn("公开单条视频通常无需登录", window.paste_hint.text())
            self.assertIn("批量列表", window.paste_hint.text())
            self.assertIn("可能要求登录", window.paste_hint.text())
        finally:
            window.close()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
