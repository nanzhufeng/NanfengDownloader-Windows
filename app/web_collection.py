"""Bounded collection reading; no recursive crawling."""
import re
from urllib.parse import urlparse, urljoin


def episode_links(source, anchors, max_items):
    host = urlparse(source).hostname
    match = re.search(r'/vod(?:-detail|-play)?/(\d+)', urlparse(source).path)
    found = {}
    for href, title in anchors:
        url = urljoin(source, href)
        parsed = urlparse(url)
        episode = re.fullmatch(r'/vod-play/(\d+)/ep(\d+)\.html', parsed.path)
        if parsed.hostname != host or not episode:
            continue
        if match and episode.group(1) != match.group(1):
            continue
        number = int(episode.group(2))
        found.setdefault(url, (f'第{number}集', episode.group(1), number))
    if len({x[1] for x in found.values()}) > 1:
        raise RuntimeError('页面包含多个不同合集，请粘贴具体作品的合集页链接，不自动下载全站。')
    return [(url, data[0]) for url, data in sorted(found.items(), key=lambda x: x[1][2])][:max_items]


def discover_collection(url, max_items):
    from .catalog import CatalogItem
    if urlparse(url).hostname not in {'yhdm.one', 'www.yhdm.one'} or urlparse(url).path.lower().endswith(('.m3u8', '.mp4', '.mpd')):
        from .generic_collection import discover_generic_collection
        return discover_generic_collection(url, max_items)
    from playwright.sync_api import sync_playwright
    from .douyin import _find_chrome_path
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=_find_chrome_path(), headless=True)
        try:
            page = browser.new_page()
            response = page.goto(url, wait_until='domcontentloaded', timeout=20000)
            if response and response.status >= 400:
                raise RuntimeError(f'合集页面访问失败：HTTP {response.status}')
            anchors = page.locator('a[href]').evaluate_all("els => els.map(e => [e.href, e.textContent || ''])")
            # The page already contains the full series; do not truncate it at the
            # generic paginated-platform default of 500 entries.
            pairs = episode_links(url, anchors, len(anchors))
            if not pairs:
                raise RuntimeError('此页面未发现可确认的剧集，请打开作品合集页后复制地址。')
            return [CatalogItem('其他网站', title, link, creator_name=urlparse(url).hostname) for link, title in pairs]
        finally:
            browser.close()
