"""Anonymous, bounded yt-dlp collection adapter. Never follows arbitrary page links."""
import re
from itertools import islice
from urllib.parse import urlparse


def is_collection_candidate(url):
    parsed = urlparse(url)
    if parsed.path.lower().endswith(('.mp4', '.m3u8', '.mpd', '.mp3', '.webm')):
        return False
    if re.search(r'(?:^|/)(?:playlists?|albums?|collections?|series|channels?|showcase|sets|users?)(?:/|$)', parsed.path, re.I):
        return True
    from yt_dlp.extractor import gen_extractor_classes
    for extractor in gen_extractor_classes():
        if extractor.IE_NAME != 'generic' and extractor.suitable(url):
            return bool(re.search(r'playlist|album|collection|series|channel|showcase|:user', extractor.IE_NAME, re.I))
    return False


def catalog_from_info(info, source, limit):
    from .catalog import CatalogItem
    from .catalog_rules import normalize_catalog_items
    if not isinstance(info, dict) or info.get('_type') not in {'playlist', 'multi_video'}:
        return None
    items = []
    for entry in islice(info.get('entries') or [], max(0, limit)):
        if not isinstance(entry, dict):
            continue
        target = entry.get('webpage_url') or entry.get('original_url') or entry.get('url')
        if not isinstance(target, str):
            continue
        parsed = urlparse(target)
        if parsed.scheme not in {'https', 'http'} or not parsed.hostname or parsed.username or parsed.password or target == source:
            continue
        # Nested collections are not silently downloaded as individual works.
        if entry.get('_type') in {'playlist', 'multi_video'}:
            continue
        items.append(CatalogItem('其他网站', str(entry.get('title') or '未提供标题'), target,
            creator_name=entry.get('uploader') or info.get('uploader') or urlparse(source).hostname))
    return normalize_catalog_items(items)


def discover_generic_collection(url, limit):
    if not is_collection_candidate(url):
        return None
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError
    options = {'quiet': True, 'extract_flat': 'in_playlist', 'lazy_playlist': True,
               'playlistend': limit, 'socket_timeout': 15, 'retries': 1,
               'extractor_retries': 1, 'skip_download': True, 'ignoreerrors': False}
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            items = catalog_from_info(info, url, limit)
    except DownloadError as exc:
        raise RuntimeError('合集解析失败，未自动按单集下载。该站可能需要登录、暂不支持或不可访问。') from exc
    if items == []:
        raise RuntimeError('合集没有可确认的独立作品链接，未把集合或推荐内容加入队列。')
    return items
