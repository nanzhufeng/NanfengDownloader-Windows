from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import http.cookiejar
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any
import urllib.request
from urllib.parse import urlencode, urlparse


XIAOHONGSHU_HOSTS = {
    "xiaohongshu.com",
    "www.xiaohongshu.com",
    "xhslink.com",
    "www.xhslink.com",
}


@dataclass(frozen=True)
class XiaohongshuInfo:
    note_id: str
    title: str
    creator_name: str
    creator_id: str | None
    publish_date: str | None
    video_url: str
    width: int | None = None
    height: int | None = None


def is_xiaohongshu_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in XIAOHONGSHU_HOSTS or host.endswith(".xiaohongshu.com")


def _date_from_timestamp(value: Any) -> str | None:
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    timestamp = float(value)
    if timestamp > 10_000_000_000:
        timestamp /= 1000
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")


def _quality_limit(quality: str) -> int | None:
    return {
        "1080p 及以下": 1080,
        "720p 及以下": 720,
        "360p 及以下": 360,
    }.get(quality)


def _stream_candidates(note: dict[str, Any]) -> list[dict[str, Any]]:
    stream = (
        ((note.get("video") or {}).get("media") or {}).get("stream") or {}
        if isinstance(note.get("video"), dict)
        else {}
    )
    candidates: list[dict[str, Any]] = []
    if isinstance(stream, dict):
        for codec in ("h264", "h265", "av1"):
            values = stream.get(codec)
            if isinstance(values, list):
                candidates.extend(item for item in values if isinstance(item, dict))
    return candidates


def _stream_url(stream: dict[str, Any]) -> str | None:
    for key in ("masterUrl", "master_url", "url"):
        value = stream.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().replace("http://", "https://", 1)
    backups = stream.get("backupUrls") or stream.get("backup_urls")
    if isinstance(backups, list):
        for value in backups:
            if isinstance(value, str) and value.strip():
                return value.strip().replace("http://", "https://", 1)
    return None


def _stream_short_edge(stream: dict[str, Any]) -> int:
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    dimensions = [value for value in (width, height) if value > 0]
    return min(dimensions) if dimensions else 0


def _select_stream(note: dict[str, Any], quality: str) -> dict[str, Any] | None:
    candidates = [item for item in _stream_candidates(note) if _stream_url(item)]
    if not candidates:
        return None
    limit = _quality_limit(quality)
    if limit is None:
        return max(candidates, key=_stream_short_edge)
    matching = [item for item in candidates if 0 < _stream_short_edge(item) <= limit]
    if matching:
        return max(matching, key=_stream_short_edge)
    return min(candidates, key=_stream_short_edge)


def parse_xiaohongshu_note(
    note: dict[str, Any],
    quality: str = "最佳画质",
) -> XiaohongshuInfo:
    """解析小红书单条视频笔记；图文笔记不会伪装为视频。"""
    if str(note.get("type") or "").lower() != "video":
        raise RuntimeError("该小红书笔记不是视频笔记，当前版本不会把图片或封面伪装成视频。")
    selected = _select_stream(note, quality)
    if not selected:
        raise RuntimeError("小红书页面没有返回可下载的视频流，请先登录小红书后重试。")

    user = note.get("user") if isinstance(note.get("user"), dict) else {}
    note_id = str(note.get("noteId") or note.get("note_id") or note.get("id") or "").strip()
    if not note_id:
        raise RuntimeError("小红书页面没有返回笔记 ID，无法确认目标视频。")
    creator_name = str(user.get("nickname") or note.get("nickname") or "未知作者").strip()
    creator_id_value = user.get("userId") or user.get("user_id")
    creator_id = str(creator_id_value).strip() if creator_id_value else None
    width = int(selected.get("width") or 0) or None
    height = int(selected.get("height") or 0) or None
    return XiaohongshuInfo(
        note_id=note_id,
        title=str(note.get("title") or note.get("desc") or "小红书视频").strip(),
        creator_name=creator_name,
        creator_id=creator_id,
        publish_date=_date_from_timestamp(
            note.get("time") or note.get("createTime") or note.get("create_time")
        ),
        video_url=_stream_url(selected) or "",
        width=width,
        height=height,
    )


def catalog_items_from_user_packet(
    packet: dict[str, Any],
    target_creator_id: str | None = None,
) -> list[Any]:
    """只保留目标作者、具有真实 note_id 的视频笔记。"""
    from .catalog import CatalogItem

    data = packet.get("data") if isinstance(packet.get("data"), dict) else {}
    notes = data.get("notes") if isinstance(data, dict) else None
    if not isinstance(notes, list):
        return []

    items: list[CatalogItem] = []
    seen: set[str] = set()
    for note in notes:
        if not isinstance(note, dict) or str(note.get("type") or "").lower() != "video":
            continue
        user = note.get("user") if isinstance(note.get("user"), dict) else {}
        creator_id_value = user.get("user_id") or user.get("userId")
        creator_id = str(creator_id_value).strip() if creator_id_value else None
        if target_creator_id and creator_id and creator_id != target_creator_id:
            continue
        note_id = str(note.get("note_id") or note.get("noteId") or note.get("id") or "").strip()
        if not note_id or note_id in seen:
            continue
        seen.add(note_id)
        token = str(note.get("xsec_token") or "").strip()
        query = {"xsec_token": token, "xsec_source": "pc_user"} if token else {}
        url = f"https://www.xiaohongshu.com/explore/{note_id}"
        if query:
            url = f"{url}?{urlencode(query)}"
        items.append(
            CatalogItem(
                platform="小红书",
                title=str(note.get("display_title") or note.get("title") or "小红书视频").strip(),
                url=url,
                publish_date=_date_from_timestamp(
                    note.get("time") or note.get("create_time") or note.get("createTime")
                ),
                creator_name=str(user.get("nickname") or "未知作者").strip(),
            )
        )
    return items


def _cookie_jar(options: Any) -> http.cookiejar.CookieJar | None:
    from .auth_profile import AUTH_COOKIE_MODE, cookie_jar_from_auth_profile

    if options.cookie_mode == AUTH_COOKIE_MODE:
        return cookie_jar_from_auth_profile()
    if options.cookie_mode == "cookies.txt" and options.cookie_file:
        jar = http.cookiejar.MozillaCookieJar(str(options.cookie_file))
        jar.load(ignore_discard=True, ignore_expires=True)
        return jar
    return None


def _playwright_cookies(options: Any) -> list[dict[str, Any]]:
    jar = _cookie_jar(options)
    if not jar:
        return []
    cookies: list[dict[str, Any]] = []
    for cookie in jar:
        domain = cookie.domain or ""
        if "xiaohongshu" not in domain:
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


def _new_browser_context(playwright: Any, options: Any) -> tuple[Any, Any]:
    from .auth_profile import USER_AGENT, find_browser_path

    browser_path = find_browser_path()
    if not browser_path:
        raise RuntimeError("没有找到 Chrome 或 Edge，无法读取小红书页面。")
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
    return browser, context


def _note_id_from_url(url: str) -> str | None:
    match = re.search(r"/(?:explore|discovery/item)/([0-9a-fA-F]+)", url)
    return match.group(1) if match else None


def _read_note_from_page(page: Any, note_id: str) -> dict[str, Any] | None:
    for _ in range(20):
        note = page.evaluate(
            """
            noteId => {
                const state = window.__INITIAL_STATE__;
                const detailMap = state?.note?.noteDetailMap;
                const entry = detailMap?.[noteId];
                const note = entry?.note || entry?.noteData?.data?.noteData || entry?.noteData;
                if (!note) return null;
                return JSON.parse(JSON.stringify(note));
            }
            """,
            note_id,
        )
        if isinstance(note, dict):
            return note
        page.wait_for_timeout(250)
    return None


def fetch_xiaohongshu_info(
    url: str,
    options: Any,
    quality: str | None = None,
) -> tuple[XiaohongshuInfo, str]:
    """在后台浏览器中读取单条笔记的真实元数据和视频流。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser, context = _new_browser_context(playwright, options)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(1200)
        final_url = page.url
        note_id = _note_id_from_url(final_url)
        if not note_id:
            context.close()
            browser.close()
            raise RuntimeError("没有从小红书链接解析到具体视频笔记，请复制笔记分享链接。")
        note = _read_note_from_page(page, note_id)
        context.close()
        browser.close()
    if not note:
        raise RuntimeError(
            "小红书没有返回笔记详情。请先点击顶部小红书按钮，确认能看到该笔记后重试。"
        )
    return parse_xiaohongshu_note(note, quality or options.quality), final_url


def discover_xiaohongshu_items(url: str, options: Any, max_items: int = 500) -> list[Any]:
    """读取小红书单视频或作者主页；作者页只接收真实 user_posted 数据。"""
    from playwright.sync_api import sync_playwright

    from .catalog import CatalogItem

    if _note_id_from_url(url) or "xhslink.com" in url.lower():
        info, final_url = fetch_xiaohongshu_info(url, options)
        return [
            CatalogItem(
                platform="小红书",
                title=info.title,
                url=final_url,
                publish_date=info.publish_date,
                creator_name=info.creator_name,
            )
        ]

    creator_match = re.search(r"/user/profile/([A-Za-z0-9]+)", url)
    if not creator_match:
        raise RuntimeError("请粘贴小红书视频笔记链接或作者主页链接。")
    target_creator_id = creator_match.group(1)
    items: list[CatalogItem] = []
    seen: set[str] = set()
    hidden_note_seen = False
    has_more = True

    def add_packet(packet: dict[str, Any]) -> None:
        nonlocal hidden_note_seen, has_more
        data = packet.get("data") if isinstance(packet.get("data"), dict) else {}
        notes = data.get("notes") if isinstance(data, dict) else []
        if isinstance(notes, list):
            hidden_note_seen = hidden_note_seen or any(
                isinstance(note, dict)
                and str(note.get("type") or "").lower() == "video"
                and not str(note.get("note_id") or note.get("noteId") or "").strip()
                for note in notes
            )
        if isinstance(data, dict) and "has_more" in data:
            has_more = bool(data.get("has_more"))
        for item in catalog_items_from_user_packet(packet, target_creator_id):
            if item.url in seen or len(items) >= max_items:
                continue
            seen.add(item.url)
            items.append(item)

    with sync_playwright() as playwright:
        browser, context = _new_browser_context(playwright, options)
        page = context.new_page()

        def on_response(response: Any) -> None:
            if "/api/sns/web/v1/user_posted" not in response.url:
                return
            try:
                packet = response.json()
            except Exception:
                return
            if isinstance(packet, dict):
                add_packet(packet)

        page.on("response", on_response)
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(1800)
        idle_rounds = 0
        previous_count = len(items)
        for _ in range(min(100, max(10, max_items // 8))):
            if len(items) >= max_items or not has_more:
                break
            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(900)
            if len(items) == previous_count:
                idle_rounds += 1
                if idle_rounds >= 4:
                    break
            else:
                previous_count = len(items)
                idle_rounds = 0
        context.close()
        browser.close()

    if not items and hidden_note_seen:
        raise RuntimeError(
            "小红书未连接时隐藏了作者作品 ID。请点击顶部小红书按钮，完成连接后重新读取。"
        )
    if not items:
        raise RuntimeError(
            "没有读取到该作者的可下载视频笔记。请先点击顶部小红书按钮后重试；"
            "图文笔记不会加入视频队列。"
        )
    return items[:max_items]


def _safe_file_name(text: str, fallback: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\r\n\t]+', " ", text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return (cleaned or fallback)[:120]


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"无法生成不重名文件名：{path}")


def _format_speed(value: float) -> str:
    if value >= 1024 * 1024:
        return f"{value / 1024 / 1024:.2f} MiB/s"
    return f"{value / 1024:.0f} KiB/s"


def _format_eta(value: float) -> str:
    if value <= 0:
        return "--"
    minutes, seconds = divmod(int(value), 60)
    return f"{minutes:02d}:{seconds:02d}"


def _content_range_total(value: str | None) -> int:
    match = re.fullmatch(r"bytes\s+\d+-\d+/(\d+|\*)", (value or "").strip())
    if not match or match.group(1) == "*":
        return 0
    return int(match.group(1))


def _download_video(
    info: XiaohongshuInfo,
    referer: str,
    target: Path,
    options: Any,
    progress_callback: Any,
    cancel_callback: Any,
) -> None:
    from .auth_profile import USER_AGENT
    from .downloader import DownloadStopped, raise_if_cancelled

    handlers: list[Any] = []
    jar = _cookie_jar(options)
    if jar:
        handlers.append(urllib.request.HTTPCookieProcessor(jar))
    opener = urllib.request.build_opener(*handlers)
    target.parent.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    total = 0
    started = time.monotonic()
    attempts = 0
    max_attempts = 5
    try:
        while total <= 0 or downloaded < total:
            raise_if_cancelled(cancel_callback)
            headers = {"User-Agent": USER_AGENT, "Accept": "*/*", "Referer": referer}
            if downloaded:
                headers["Range"] = f"bytes={downloaded}-"
            request = urllib.request.Request(info.video_url, headers=headers)
            attempts += 1
            before_request = downloaded
            with opener.open(request, timeout=40) as response:
                content_type = str(response.headers.get("Content-Type") or "").lower()
                if "text/html" in content_type or "application/json" in content_type:
                    raise RuntimeError("小红书返回的是网页或接口文本，不是视频流。")
                content_range = str(response.headers.get("Content-Range") or "")
                ranged_total = _content_range_total(content_range)
                if downloaded and int(getattr(response, "status", 0) or 0) != 206:
                    raise RuntimeError("小红书服务器未接受断点续传，无法保证视频文件完整。")
                if ranged_total:
                    total = ranged_total
                elif not downloaded:
                    total = int(response.headers.get("Content-Length") or 0)
                with target.open("ab" if downloaded else "wb") as file_obj:
                    while True:
                        raise_if_cancelled(cancel_callback)
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        file_obj.write(chunk)
                        downloaded += len(chunk)
                        elapsed = max(time.monotonic() - started, 0.001)
                        speed = downloaded / elapsed
                        eta = (total - downloaded) / speed if total and speed else 0
                        progress_callback(
                            {
                                "status": "downloading",
                                "filename": str(target),
                                "downloaded_bytes": downloaded,
                                "total_bytes": total,
                                "_speed_str": _format_speed(speed),
                                "_eta_str": _format_eta(eta),
                            }
                        )
            if total <= 0 or downloaded >= total:
                break
            if downloaded <= before_request:
                raise RuntimeError("小红书视频下载提前结束，续传时没有收到新数据。")
            if attempts >= max_attempts:
                raise RuntimeError(
                    f"小红书视频下载不完整：已收到 {downloaded} / {total} 字节，"
                    "多次断点续传仍未完成。"
                )
            time.sleep(min(0.25 * attempts, 1.0))
    except DownloadStopped:
        target.unlink(missing_ok=True)
        raise
    if downloaded <= 0:
        target.unlink(missing_ok=True)
        raise RuntimeError("小红书下载结束，但没有收到视频数据。")
    if total and downloaded != total:
        raise RuntimeError(f"小红书视频下载不完整：已收到 {downloaded} / {total} 字节。")


def _extract_mp3(
    source: Path,
    target: Path,
    options: Any,
    cancel_callback: Any,
) -> None:
    from .downloader import DownloadStopped, raise_if_cancelled

    if not options.ffmpeg_dir:
        raise RuntimeError("仅音频 MP3 需要 FFmpeg，但当前没有找到 FFmpeg。")
    ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    command = [
        str(options.ffmpeg_dir / ffmpeg_name),
        "-y",
        "-i",
        str(source),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(target),
    ]
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
    )
    while process.poll() is None:
        try:
            raise_if_cancelled(cancel_callback)
        except DownloadStopped:
            process.terminate()
            process.wait(timeout=5)
            target.unlink(missing_ok=True)
            raise
        time.sleep(0.15)
    if process.returncode != 0:
        detail = (process.stderr.read() if process.stderr else b"").decode("utf-8", errors="replace")
        target.unlink(missing_ok=True)
        raise RuntimeError(f"小红书音频转换失败：{detail[-300:]}")


def download_xiaohongshu_url(
    url: str,
    options: Any,
    progress_callback: Any,
    cancel_callback: Any = None,
) -> Any:
    from .downloader import DownloadResult, raise_if_cancelled, safe_path_name
    from .media_validation import InvalidMediaError, validate_media_file

    raise_if_cancelled(cancel_callback)
    info, referer = fetch_xiaohongshu_info(url, options, options.quality)
    creator_dir = safe_path_name(options.creator_name or info.creator_name)
    file_name = _safe_file_name(info.title, f"小红书视频 {info.note_id}")
    publish_date = info.publish_date or "未知日期"
    base_dir = options.output_dir / "Xiaohongshu" / creator_dir
    final_target = base_dir / f"{publish_date} {file_name}.mp4"
    if options.quality == "仅音频 MP3":
        final_target = final_target.with_suffix(".mp3")
    if final_target.exists() and final_target.stat().st_size > 0:
        try:
            validate_media_file(final_target, options.ffmpeg_dir)
        except InvalidMediaError:
            # 保留用户现有文件，另存一份重新下载的完整结果。
            final_target = _unique_path(final_target)
        else:
            return DownloadResult(
                files=[final_target],
                skipped=True,
                message="保存目录中已存在对应文件，已跳过下载。",
            )
    final_target = _unique_path(final_target)
    if options.quality == "仅音频 MP3":
        temp_video = final_target.with_suffix(".source.mp4")
    else:
        temp_video = final_target.with_name(f"{final_target.stem}.downloading{final_target.suffix}")
    try:
        _download_video(info, referer, temp_video, options, progress_callback, cancel_callback)
        if options.quality == "仅音频 MP3":
            _extract_mp3(temp_video, final_target, options, cancel_callback)
            temp_video.unlink(missing_ok=True)
            validate_media_file(final_target, options.ffmpeg_dir)
        else:
            validate_media_file(temp_video, options.ffmpeg_dir)
            temp_video.replace(final_target)
    except Exception:
        temp_video.unlink(missing_ok=True)
        if options.quality == "仅音频 MP3":
            final_target.unlink(missing_ok=True)
        raise
    progress_callback({"status": "finished", "filename": str(final_target)})
    return DownloadResult(files=[final_target])
