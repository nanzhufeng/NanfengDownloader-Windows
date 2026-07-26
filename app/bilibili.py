from __future__ import annotations

from datetime import datetime, timezone
import http.cookiejar
import re
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


BILIBILI_HOSTS = {"bilibili.com", "www.bilibili.com", "m.bilibili.com", "space.bilibili.com", "b23.tv"}


def is_bilibili_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in BILIBILI_HOSTS or host.endswith(".bilibili.com")


def _publish_date(entry: dict[str, Any]) -> str | None:
    raw_date = entry.get("upload_date") or entry.get("release_date")
    if isinstance(raw_date, str) and len(raw_date) == 8 and raw_date.isdigit():
        return f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    timestamp = entry.get("timestamp") or entry.get("release_timestamp")
    if isinstance(timestamp, (int, float)) and timestamp > 0:
        return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")
    return None


def _creator_name(entry: dict[str, Any], fallback: str | None = None) -> str | None:
    for key in ("uploader", "channel", "playlist_uploader"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _creator_id(entry: dict[str, Any]) -> str | None:
    for key in ("uploader_id", "channel_id", "playlist_uploader_id"):
        value = entry.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _video_url(entry: dict[str, Any]) -> str | None:
    for key in ("webpage_url", "url"):
        value = entry.get(key)
        if isinstance(value, str):
            value = value.strip()
            if "/video/" in value and is_bilibili_url(value):
                parsed = urlparse(value)
                page_values = parse_qs(parsed.query).get("p") or []
                query = ""
                if page_values and str(page_values[0]).isdigit():
                    query = urlencode({"p": int(page_values[0])})
                return urlunparse(
                    (
                        parsed.scheme or "https",
                        parsed.netloc,
                        parsed.path.rstrip("/"),
                        "",
                        query,
                        "",
                    )
                )

    video_id = str(entry.get("id") or "").strip()
    if video_id.upper().startswith("BV"):
        return f"https://www.bilibili.com/video/{video_id}"
    if video_id.lower().startswith("av") and video_id[2:].isdigit():
        return f"https://www.bilibili.com/video/{video_id}"
    return None


def catalog_items_from_bilibili_info(
    info: dict[str, Any],
    max_items: int = 500,
) -> list[Any]:
    """把 yt-dlp 的 B站空间/合集结果转换为严格归属的作品条目。"""
    from .catalog import CatalogItem

    fallback_creator = _creator_name(info)
    target_creator_id = _creator_id(info)
    if not target_creator_id:
        root_id = info.get("id")
        root_id_text = str(root_id).strip() if root_id is not None else ""
        entry_creator_ids = {
            creator_id
            for entry in (info.get("entries") or [])
            if isinstance(entry, dict)
            for creator_id in [_creator_id(entry)]
            if creator_id
        }
        if root_id_text.isdigit() and root_id_text in entry_creator_ids:
            target_creator_id = root_id_text

    entries = info.get("entries")
    if not entries:
        entries = [info]

    items: list[CatalogItem] = []
    seen: set[str] = set()
    for entry in entries:
        if len(items) >= max_items:
            break
        if not isinstance(entry, dict):
            continue
        entry_creator_id = _creator_id(entry)
        if target_creator_id and entry_creator_id and entry_creator_id != target_creator_id:
            continue
        url = _video_url(entry)
        if not url or url in seen:
            continue
        seen.add(url)
        items.append(
            CatalogItem(
                platform="哔哩哔哩",
                title=str(entry.get("title") or "哔哩哔哩视频").strip(),
                url=url,
                publish_date=_publish_date(entry),
                creator_name=_creator_name(entry, fallback_creator),
            )
        )
    return items


def _is_single_video_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return "/video/" in path or "/bangumi/play/" in path


def _playwright_cookies(options: Any) -> list[dict[str, Any]]:
    from .auth_profile import AUTH_COOKIE_MODE, cookie_jar_from_auth_profile

    if options.cookie_mode != AUTH_COOKIE_MODE:
        return []
    try:
        jar: http.cookiejar.CookieJar = cookie_jar_from_auth_profile()
    except Exception:
        return []
    cookies: list[dict[str, Any]] = []
    for cookie in jar:
        domain = cookie.domain or ""
        if "bilibili" not in domain:
            continue
        item: dict[str, Any] = {
            "name": cookie.name,
            "value": cookie.value,
            "domain": domain,
            "path": cookie.path or "/",
            "secure": bool(cookie.secure),
        }
        if cookie.expires:
            item["expires"] = float(cookie.expires)
        cookies.append(item)
    return cookies


def _discover_space_with_browser(url: str, options: Any, max_items: int) -> list[Any]:
    """B站接口触发 412 时，使用真实空间页中的作品链接作为保守回退。"""
    from playwright.sync_api import sync_playwright

    from .auth_profile import USER_AGENT, find_browser_path
    from .catalog import CatalogItem

    browser_path = find_browser_path()
    if not browser_path:
        raise RuntimeError("没有找到 Chrome 或 Edge，无法读取哔哩哔哩 UP 主作品列表。")

    items: list[CatalogItem] = []
    seen: set[str] = set()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=browser_path,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
        )
        cookies = _playwright_cookies(options)
        if cookies:
            context.add_cookies(cookies)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(1800)
        page_title = page.title()
        creator_name = re.split(
            r"(?:投稿视频|的个人空间|视频分享|[-_]\s*哔哩哔哩)",
            page_title,
            maxsplit=1,
        )[0].strip(" -_") or "未知UP主"

        idle_rounds = 0
        for _ in range(min(80, max(8, max_items // 10))):
            anchors = page.locator('a[href*="/video/BV"]').evaluate_all(
                """
                nodes => nodes.map(node => ({
                    href: node.href,
                    title: node.getAttribute("title") || node.textContent || ""
                }))
                """
            )
            before = len(items)
            for anchor in anchors:
                href = str(anchor.get("href") or "").split("?", 1)[0]
                match = re.search(r"/video/(BV[A-Za-z0-9]+)", href, re.IGNORECASE)
                if not match:
                    continue
                item_url = f"https://www.bilibili.com/video/{match.group(1)}"
                if item_url in seen:
                    continue
                seen.add(item_url)
                title = re.sub(r"\s+", " ", str(anchor.get("title") or "")).strip()
                items.append(
                    CatalogItem(
                        platform="哔哩哔哩",
                        title=title or f"哔哩哔哩视频 {match.group(1)}",
                        url=item_url,
                        creator_name=creator_name,
                    )
                )
                if len(items) >= max_items:
                    break
            if len(items) >= max_items:
                break
            if len(items) == before:
                idle_rounds += 1
                if idle_rounds >= 3:
                    break
            else:
                idle_rounds = 0
            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(900)
        context.close()
        browser.close()

    if not items:
        raise RuntimeError(
            "哔哩哔哩没有返回可确认归属的 UP 主视频。请先点击“登录哔哩哔哩”后重试。"
        )
    return items[:max_items]


def discover_bilibili_items(url: str, options: Any, max_items: int = 500) -> list[Any]:
    """读取 B站单视频、UP 主空间、合集或播放列表。"""
    from yt_dlp import YoutubeDL

    from .auth_profile import AUTH_COOKIE_MODE, export_auth_cookies_txt

    single_video = _is_single_video_url(url)
    ydl_options: dict[str, Any] = {
        "extract_flat": False if single_video else "in_playlist",
        "skip_download": True,
        "quiet": True,
        "ignoreerrors": False,
        "noplaylist": False,
        "playlistend": max_items,
    }
    if options.ffmpeg_dir:
        ydl_options["ffmpeg_location"] = str(options.ffmpeg_dir)
    if options.cookie_mode == AUTH_COOKIE_MODE:
        ydl_options["cookiefile"] = str(export_auth_cookies_txt())
    elif options.cookie_mode in {"Chrome", "Edge", "Firefox"}:
        ydl_options["cookiesfrombrowser"] = (options.cookie_mode.lower(),)
    elif options.cookie_mode == "cookies.txt" and options.cookie_file:
        ydl_options["cookiefile"] = str(options.cookie_file)

    try:
        with YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(url, download=False)
        if not isinstance(info, dict):
            return []
        return catalog_items_from_bilibili_info(info, max_items=max_items)
    except Exception as exc:
        detail = str(exc).lower()
        is_space = "space.bilibili.com" in url.lower()
        if is_space and (
            "412" in detail
            or "precondition failed" in detail
            or "request is blocked by server" in detail
        ):
            return _discover_space_with_browser(url, options, max_items)
        if "412" in detail or "precondition failed" in detail:
            raise RuntimeError(
                "哔哩哔哩触发了访问保护（HTTP 412）。请先点击“登录哔哩哔哩”，"
                "或稍后更换网络后重试。"
            ) from exc
        raise
