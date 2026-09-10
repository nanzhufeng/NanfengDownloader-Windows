"""Anonymous dynamic-player fallback; never guess from unrelated network traffic."""
import time
import re
from urllib.parse import urlparse


def clean_page_title(title):
    title = re.sub(r"\s+", " ", title or "").strip()
    title = re.sub(r"\s*(?:在线播放|在线观看).*?$", "", title).strip()
    return title if title.lower() not in {"", "index", "player", "视频播放器"} else None


def select_media(sources):
    urls = list(dict.fromkeys(url for url in sources if urlparse(url).scheme in {"http", "https"}))
    if len(urls) > 1:
        raise RuntimeError("页面存在多个播放器，无法确认目标视频；请使用具体播放器链接。")
    return urls[0] if urls else None


def preferred_episode_source(page_url, links):
    """Only use an explicitly listed source from this episode, never other episodes."""
    page = urlparse(page_url)
    if page.hostname not in {"yhdm.one", "www.yhdm.one"} or not re.fullmatch(r"/vod-play/\d+/ep\d+\.html", page.path):
        return None
    for label, href in links:
        link = urlparse(href)
        prefix = "/_player_x_/"
        if label.strip() != "IK" or link.hostname != page.hostname or not link.path.startswith(prefix):
            continue
        media = href.split(prefix, 1)[1]
        target = urlparse(media)
        if target.scheme == "https" and target.hostname and not target.username and target.path.endswith(".m3u8"):
            return media, href
    return None


def resolve_browser_media(url, cancel=None):
    from playwright.sync_api import sync_playwright, Error
    from .douyin import _find_chrome_path, _background_browser_args
    from .downloader import raise_if_cancelled

    path = _find_chrome_path()
    if not path:
        raise RuntimeError("动态播放器解析需要安装 Chrome 或 Edge。")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=path, headless=True, args=_background_browser_args(), timeout=15000)
        try:
            context = browser.new_context(accept_downloads=False)
            context.set_default_timeout(3000)
            page = context.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
            if response and response.status in {401, 403, 429}:
                raise RuntimeError(f"网站拒绝浏览器访问（HTTP {response.status}）；未绕过访问验证。")
            links = page.locator("a[href]").evaluate_all("els => els.map(e => [e.textContent.trim(), e.href])")
            preferred = preferred_episode_source(url, links)
            if preferred:
                return preferred[0], preferred[1], clean_page_title(page.title())
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                raise_if_cancelled(cancel)
                found = []
                for frame in page.frames:
                    try:
                        sources = frame.locator("video, audio").evaluate_all(
                            "els => els.filter(e => e.getClientRects().length).map(e => e.currentSrc || e.src || e.querySelector('source')?.src || '')")
                        found.extend((src, frame.url) for src in sources)
                    except Error:
                        continue  # frame may detach during player initialization
                chosen = select_media([src for src, _ in found])
                if chosen:
                    # Source links may be populated with the player after DOMContentLoaded.
                    links = page.locator("a[href]").evaluate_all("els => els.map(e => [e.textContent.trim(), e.href])")
                    preferred = preferred_episode_source(url, links)
                    # Metadata belongs to the original work page, not the CDN/iframe.
                    heading = page.locator("h1").first
                    title = clean_page_title(heading.inner_text() if heading.count() else page.title())
                    if not title:
                        title = clean_page_title(page.title())
                    return (preferred[0], preferred[1], title) if preferred else (chosen, next(ref for src, ref in found if src == chosen), title)
                page.wait_for_timeout(250)
            raise RuntimeError("浏览器未发现唯一可下载的播放器地址（可能为 blob、加密或需交互播放）；未下载广告或猜测视频。")
        finally:
            browser.close()
