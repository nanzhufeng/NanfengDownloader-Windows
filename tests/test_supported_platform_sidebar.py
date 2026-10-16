from __future__ import annotations

from tests.ui_fixtures import isolated_main_window

import os
import unittest


class SupportedPlatformSidebarTests(unittest.TestCase):
    def test_sidebar_avoids_duplicate_platform_cards_and_keeps_steps(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QFrame

        from app.main import MainWindow

        app = QApplication.instance() or QApplication([])
        window = isolated_main_window()
        try:
            window.resize(1820, 1130)
            window.show()
            app.processEvents()

            self.assertFalse(
                [frame.objectName() for frame in window.findChildren(QFrame) if frame.objectName().startswith("Platform")],
                "platforms are already listed in the login card, so the sidebar must not repeat them",
            )
            self.assertGreaterEqual(window.output_edit.width(), 320)
            self.assertIs(window.platform_login_card.parentWidget(), window.sidebar)
            self.assertGreater(window.download_settings_card.width(), window.sidebar.width())
            self.assertIs(window.table.parentWidget(), window.queue_card)
            self.assertFalse(window.table.showGrid())
            self.assertEqual(len(window.workflow_step_rows), 4)
            self.assertEqual([row[2].text() for row in window.workflow_step_rows], ["登录账号", "粘贴链接", "读取列表", "勾选下载"])
            self.assertEqual([row[1].number for row in window.workflow_step_rows], [1, 2, 3, 4])
            self.assertTrue(all(row[0].layout().count() == 2 for row in window.workflow_step_rows))
            self.assertIn("QPushButton#LoginDouyinButton, QPushButton#LoginYoutubeButton", window.styleSheet())
            self.assertIn("background: #f1f3f5", window.styleSheet())
            self.assertIs(window.settings_button.parentWidget(), window.sidebar)
            actions = window.start_button.parentWidget()
            self.assertIs(window.open_folder_button.parentWidget(), actions)
            self.assertIs(actions.layout().itemAt(actions.layout().count() - 1).widget(), window.open_folder_button)
            self.assertLess(window.invert_button.geometry().right(), window.open_folder_button.geometry().left())
        finally:
            window.close()
            app.processEvents()

    def test_login_buttons_use_platform_icons_and_show_the_optional_login_rule(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QSize
        from PySide6.QtWidgets import QApplication

        from app.main import MainWindow

        app = QApplication.instance() or QApplication([])
        window = isolated_main_window()
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
            self.assertEqual(len({button.geometry().x() for button in buttons}), 1)
            positions = [button.geometry().y() for button in buttons]
            self.assertTrue(all(first < second for first, second in zip(positions, positions[1:])))
            self.assertTrue(all(window.sidebar.isAncestorOf(button) for button in buttons))
            self.assertLess(window.platform_login_card.geometry().bottom(), window.workflow_step_rows[0][0].geometry().top())
            self.assertIs(window.import_button.parentWidget(), window.clear_url_button.parentWidget())
            self.assertIn("background: #fff0e4", window.styleSheet())
            self.assertIn(
                "粘贴平台链接、其他网站作品页或音视频直链，可一次多行；原有平台支持作者/频道列表，其他网站下载时解析单条媒体。支持拖入种子文件（.torrent）。",
                window.url_text.placeholderText(),
            )
            self.assertIn("公开单条视频通常无需登录", window.paste_hint.text())
            self.assertIn("批量列表", window.paste_hint.text())
            self.assertIn("可能要求登录", window.paste_hint.text())
        finally:
            window.close()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
