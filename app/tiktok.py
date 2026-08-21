from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any
from urllib.parse import urlparse


TIKTOK_HOSTS = {
    "tiktok.com",
    "www.tiktok.com",
    "m.tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com",
}


def is_tiktok_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in TIKTOK_HOSTS or host.endswith(".tiktok.com")


def _profile_handle(url: str) -> str | None:
    match = re.search(r"tiktok\.com/@([^/?#]+)", url, re.IGNORECASE)
    return match.group(1).strip().lower() if match else None


def _creator_name(entry: dict[str, Any], fallback: str | None = None) -> str | None:
    for key in ("uploader", "creator", "channel", "playlist_uploader"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _publish_date(entry: dict[str, Any]) -> str | None:
    raw_date = entry.get("upload_date") or entry.get("release_date")
    if isinstance(raw_date, str) and len(raw_date) == 8 and raw_date.isdigit():
        return f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    timestamp = entry.get("timestamp") or entry.get("release_timestamp")
    if isinstance(timestamp, (int, float)) and timestamp > 0:
        return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")
    return None


def _video_url(entry: dict[str, Any], fallback_handle: str | None = None) -> str | None:
    for key in ("webpage_url", "url"):
        value = entry.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        value = value.strip()
        if is_tiktok_url(value) and "/video/" in urlparse(value).path.lower():
            return value.split("?", 1)[0]

    video_id = str(entry.get("id") or "").strip()
    creator = _creator_name(entry, fallback_handle)
    if video_id.isdigit() and creator:
        return f"https://www.tiktok.com/@{creator.lstrip('@')}/video/{video_id}"
    return None


def catalog_items_from_tiktok_info(
    info: dict[str, Any],
    source_url: str,
    max_items: int = 500,
) -> list[Any]:
    """把 TikTok 单条或作者页结果转换为严格归属的队列条目。"""
    from .catalog import CatalogItem

    requested_handle = _profile_handle(source_url)
    fallback_creator = _creator_name(info) or str(info.get("title") or "").strip() or requested_handle
    entries = info.get("entries") or [info]
    items: list[CatalogItem] = []
    seen: set[str] = set()

    for entry in entries:
        if len(items) >= max_items:
            break
        if not isinstance(entry, dict):
            continue
        creator = _creator_name(entry, fallback_creator)
        creator_handle = creator.lstrip("@").lower() if creator else None
        if requested_handle and creator_handle and creator_handle != requested_handle:
            continue
        url = _video_url(entry, requested_handle or fallback_creator)
        if not url or url in seen:
            continue
        if requested_handle:
            url_handle = _profile_handle(url)
            if url_handle and url_handle != requested_handle:
                continue
        seen.add(url)
        items.append(
            CatalogItem(
                platform="TikTok",
                title=str(entry.get("title") or entry.get("description") or "TikTok 视频").strip(),
                url=url,
                publish_date=_publish_date(entry),
                creator_name=creator or requested_handle,
            )
        )
    return items


def _is_single_video_url(url: str) -> bool:
    return "/video/" in urlparse(url).path.lower()


def _friendly_tiktok_error(exc: Exception) -> RuntimeError:
    detail = str(exc)
    normalized = detail.lower()
    if "ip address is blocked" in normalized or "geo restricted" in normalized:
        return RuntimeError(
            "TikTok 拒绝了当前网络出口访问该作品。请切换网络或代理节点后重试；"
            "如网页中连接后能够正常观看，也可以点击顶部 TikTok 按钮后重试。"
        )
    if any(
        marker in normalized
        for marker in ("login required", "sign in", "private", "captcha", "cookies")
    ):
        return RuntimeError(
            "TikTok 需要连接或验证当前访问。请点击顶部 TikTok 按钮，"
            "确认能在独立窗口中查看该作品后关闭窗口，再重新读取。"
        )
    return RuntimeError(detail)


def discover_tiktok_items(url: str, options: Any, max_items: int = 500) -> list[Any]:
    """读取 TikTok 单视频、分享短链或作者主页。"""
    from yt_dlp import YoutubeDL

    from .auth_profile import AUTH_COOKIE_MODE, export_auth_cookies_txt

    single_video = _is_single_video_url(url)
    ydl_options: dict[str, Any] = {
        "extract_flat": False if single_video else "in_playlist",
        "skip_download": True,
        "quiet": True,
        "ignoreerrors": False,
        "noplaylist": single_video,
        "playlistend": max_items,
        "socket_timeout": 30,
        "retries": 2,
    }
    if options.ffmpeg_dir:
        ydl_options["ffmpeg_location"] = str(options.ffmpeg_dir)
    if options.cookie_mode == AUTH_COOKIE_MODE:
        ydl_options["cookiefile"] = str(export_auth_cookies_txt("tiktok"))
    elif options.cookie_mode in {"Chrome", "Edge", "Firefox"}:
        ydl_options["cookiesfrombrowser"] = (options.cookie_mode.lower(),)
    elif options.cookie_mode == "cookies.txt" and options.cookie_file:
        ydl_options["cookiefile"] = str(options.cookie_file)

    try:
        with YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise _friendly_tiktok_error(exc) from exc
    if not isinstance(info, dict):
        return []
    return catalog_items_from_tiktok_info(info, source_url=url, max_items=max_items)
