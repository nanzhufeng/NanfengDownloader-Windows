from __future__ import annotations

import unittest
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import urllib.request

from app.bilibili import catalog_items_from_bilibili_info
from app.downloader import (
    _apply_bilibili_page_download_options,
    detect_platform,
    split_urls,
)
from app.xiaohongshu import (
    XiaohongshuInfo,
    _download_video,
    catalog_items_from_user_packet,
    parse_xiaohongshu_note,
)


class PlatformInputTests(unittest.TestCase):
    def test_split_urls_keeps_bilibili_and_xiaohongshu_links(self) -> None:
        text = "\n".join(
            [
                "https://www.bilibili.com/video/BV13x41117TL",
                "https://b23.tv/example",
                "https://www.xiaohongshu.com/explore/6479aae50000000013009798?xsec_token=token",
                "https://xhslink.com/example",
            ]
        )

        self.assertEqual(
            split_urls(text),
            [
                "https://www.bilibili.com/video/BV13x41117TL",
                "https://b23.tv/example",
                "https://www.xiaohongshu.com/explore/6479aae50000000013009798?xsec_token=token",
                "https://xhslink.com/example",
            ],
        )

    def test_detect_platform_recognizes_new_platforms(self) -> None:
        self.assertEqual(detect_platform("https://www.bilibili.com/video/BV13x41117TL"), "哔哩哔哩")
        self.assertEqual(detect_platform("https://b23.tv/example"), "哔哩哔哩")
        self.assertEqual(
            detect_platform("https://www.xiaohongshu.com/explore/6479aae50000000013009798"),
            "小红书",
        )
        self.assertEqual(detect_platform("https://xhslink.com/example"), "小红书")


class PlatformLoginLayoutTests(unittest.TestCase):
    def test_four_platform_login_buttons_keep_the_original_row_width(self) -> None:
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
            ]
            self.assertEqual(
                [button.text() for button in buttons],
                ["登录抖音", "登录 YouTube", "登录哔哩哔哩", "登录小红书"],
            )
            self.assertEqual([button.width() for button in buttons], [150, 150, 150, 150])
            self.assertEqual(len({button.geometry().y() for button in buttons}), 1)
            self.assertEqual(window.output_edit.width(), window.url_text.width())
            self.assertGreater(
                window.output_edit.width(),
                window.import_button.width() * 3,
                "新增登录按钮不得压缩保存位置和链接输入区域",
            )
        finally:
            window.close()
            app.processEvents()


class BilibiliCatalogTests(unittest.TestCase):
    def test_space_catalog_filters_foreign_creator_and_normalizes_urls(self) -> None:
        info = {
            "id": "3985676",
            "uploader": "目标UP主",
            "entries": [
                {
                    "id": "BV1o84y1y7Hd",
                    "title": "目标作品",
                    "uploader": "目标UP主",
                    "uploader_id": "3985676",
                    "timestamp": 1668758400,
                },
                {
                    "id": "BV1foreign123",
                    "title": "其他作者作品",
                    "uploader": "其他作者",
                    "uploader_id": "999",
                },
            ],
        }

        items = catalog_items_from_bilibili_info(info, max_items=50)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].platform, "哔哩哔哩")
        self.assertEqual(items[0].creator_name, "目标UP主")
        self.assertEqual(items[0].url, "https://www.bilibili.com/video/BV1o84y1y7Hd")
        self.assertEqual(items[0].publish_date, "2022-11-18")

    def test_multipart_video_keeps_each_page_as_a_distinct_queue_item(self) -> None:
        info = {
            "_type": "playlist",
            "id": "BV1YGNm6MEPq",
            "title": "Agent Skills 教程",
            "entries": [
                {
                    "id": "BV1YGNm6MEPq_p1",
                    "title": "p01 入门",
                    "webpage_url": (
                        "https://www.bilibili.com/video/BV1YGNm6MEPq"
                        "?p=1&spm_id_from=333.1007"
                    ),
                    "uploader": "AI应用全栈开发",
                    "uploader_id": "3706956061608447",
                    "upload_date": "20260713",
                },
                {
                    "id": "BV1YGNm6MEPq_p2",
                    "title": "p02 环境搭建",
                    "webpage_url": (
                        "https://www.bilibili.com/video/BV1YGNm6MEPq"
                        "?spm_id_from=333.1007&p=2"
                    ),
                    "uploader": "AI应用全栈开发",
                    "uploader_id": "3706956061608447",
                    "upload_date": "20260713",
                },
            ],
        }

        items = catalog_items_from_bilibili_info(info, max_items=50)

        self.assertEqual(len(items), 2)
        self.assertEqual(
            [item.url for item in items],
            [
                "https://www.bilibili.com/video/BV1YGNm6MEPq?p=1",
                "https://www.bilibili.com/video/BV1YGNm6MEPq?p=2",
            ],
        )
        self.assertEqual([item.title for item in items], ["p01 入门", "p02 环境搭建"])

    def test_multipart_page_download_is_single_and_gets_unique_prefix(self) -> None:
        options = {
            "outtmpl": (
                r"D:\南枫下载\%(extractor_key)s\%(uploader)s"
                r"\%(upload_date)s %(title).120B.%(ext)s"
            ),
            "noplaylist": False,
        }

        _apply_bilibili_page_download_options(
            "https://www.bilibili.com/video/BV1YGNm6MEPq?p=2",
            options,
        )

        self.assertTrue(options["noplaylist"])
        self.assertIn(r"\P02 %(upload_date)s", options["outtmpl"])


class XiaohongshuParserTests(unittest.TestCase):
    def test_parse_video_note_returns_creator_date_and_best_matching_stream(self) -> None:
        note = {
            "noteId": "6479aae50000000013009798",
            "title": "粘土教程",
            "type": "video",
            "time": 1685695205000,
            "user": {
                "userId": "5d08aa4a000000001002a61e",
                "nickname": "小鳄鱼的粘土手册",
            },
            "video": {
                "media": {
                    "stream": {
                        "h264": [
                            {
                                "masterUrl": "https://sns-video.example/720.mp4",
                                "width": 720,
                                "height": 960,
                                "duration": 57378,
                            },
                            {
                                "masterUrl": "https://sns-video.example/1080.mp4",
                                "width": 1080,
                                "height": 1440,
                                "duration": 57378,
                            },
                        ]
                    }
                }
            },
        }

        parsed = parse_xiaohongshu_note(note, quality="720p 及以下")

        self.assertEqual(parsed.note_id, "6479aae50000000013009798")
        self.assertEqual(parsed.title, "粘土教程")
        self.assertEqual(parsed.creator_name, "小鳄鱼的粘土手册")
        self.assertEqual(parsed.creator_id, "5d08aa4a000000001002a61e")
        self.assertEqual(parsed.publish_date, "2023-06-02")
        self.assertEqual(parsed.video_url, "https://sns-video.example/720.mp4")

    def test_user_catalog_keeps_only_target_creators_video_notes(self) -> None:
        packet = {
            "data": {
                "notes": [
                    {
                        "note_id": "note-video",
                        "type": "video",
                        "display_title": "目标视频",
                        "xsec_token": "target-token",
                        "user": {
                            "user_id": "creator-1",
                            "nickname": "目标作者",
                        },
                    },
                    {
                        "note_id": "note-image",
                        "type": "normal",
                        "display_title": "图文",
                        "user": {
                            "user_id": "creator-1",
                            "nickname": "目标作者",
                        },
                    },
                    {
                        "note_id": "foreign-video",
                        "type": "video",
                        "display_title": "其他作者视频",
                        "user": {
                            "user_id": "creator-2",
                            "nickname": "其他作者",
                        },
                    },
                ]
            }
        }

        items = catalog_items_from_user_packet(packet, target_creator_id="creator-1")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].platform, "小红书")
        self.assertEqual(items[0].creator_name, "目标作者")
        self.assertEqual(
            items[0].url,
            "https://www.xiaohongshu.com/explore/note-video"
            "?xsec_token=target-token&xsec_source=pc_user",
        )


class XiaohongshuDownloadTests(unittest.TestCase):
    def test_premature_eof_resumes_with_http_range(self) -> None:
        class FakeResponse:
            def __init__(self, payload: bytes, headers: dict[str, str], status: int) -> None:
                self.payload = payload
                self.headers = headers
                self.status = status
                self.offset = 0

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self, size: int) -> bytes:
                if self.offset >= len(self.payload):
                    return b""
                chunk = self.payload[self.offset : self.offset + size]
                self.offset += len(chunk)
                return chunk

        requests: list[urllib.request.Request] = []
        responses = iter(
            [
                FakeResponse(
                    b"abc",
                    {
                        "Content-Length": "10",
                        "Content-Type": "video/mp4",
                        "Accept-Ranges": "bytes",
                    },
                    200,
                ),
                FakeResponse(
                    b"defghij",
                    {
                        "Content-Length": "7",
                        "Content-Range": "bytes 3-9/10",
                        "Content-Type": "video/mp4",
                    },
                    206,
                ),
            ]
        )

        class FakeOpener:
            def open(self, request: urllib.request.Request, timeout: int) -> FakeResponse:
                requests.append(request)
                return next(responses)

        info = XiaohongshuInfo(
            note_id="note",
            title="title",
            creator_name="creator",
            creator_id="creator-id",
            publish_date="2026-07-26",
            video_url="https://sns-video.example/video.mp4",
        )
        target = Path(self.id().replace(".", "_") + ".mp4")
        try:
            with (
                patch("app.xiaohongshu._cookie_jar", return_value=None),
                patch("app.xiaohongshu.urllib.request.build_opener", return_value=FakeOpener()),
            ):
                _download_video(
                    info,
                    "https://www.xiaohongshu.com/explore/note",
                    target,
                    SimpleNamespace(),
                    lambda _: None,
                    None,
                )

            self.assertEqual(target.read_bytes(), b"abcdefghij")
            self.assertEqual(len(requests), 2)
            self.assertIsNone(requests[0].get_header("Range"))
            self.assertEqual(requests[1].get_header("Range"), "bytes=3-")
        finally:
            target.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
