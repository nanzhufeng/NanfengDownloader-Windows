from __future__ import annotations

import os
import re
import shutil
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from .media_validation import (
    MEDIA_FILE_SUFFIXES,
    InvalidMediaError,
    is_probable_existing_media,
    validate_media_file,
)
from .auth_profile import (
    AUTH_COOKIE_MODE,
    auth_data_dir,
    export_auth_cookies_txt,
    has_youtube_account_cookies,
    release_auth_cookie_export,
)
from .url_safety import url_host, url_host_matches


ProgressCallback = Callable[[dict[str, Any]], None]
CancelCallback = Callable[[], bool]


FRAGMENT_DOWNLOAD_CONCURRENCY = 16
FALLBACK_FRAGMENT_DOWNLOAD_CONCURRENCY = 8
STABLE_FRAGMENT_DOWNLOAD_CONCURRENCY = 1
DOWNLOAD_BUFFER_SIZE = 1024 * 1024
HTTP_DOWNLOAD_CHUNK_SIZE = 10 * 1024 * 1024
PROGRESS_UPDATE_INTERVAL = 0.2
EXTERNAL_PROGRESS_STATE_KEY = "_nanfeng_external_progress_state"
YOUTUBE_POT_PROVIDER_DIRECTORY = "bgutil-ytdlp-pot-provider"
YOUTUBE_PUBLIC_REQUEST_ATTEMPTS = 2
YOUTUBE_PUBLIC_RETRY_DELAY_SECONDS = 1.0


class DownloadStopped(RuntimeError):
    """用户主动停止当前下载。"""


def raise_if_cancelled(cancel_callback: CancelCallback | None) -> None:
    if cancel_callback and cancel_callback():
        raise DownloadStopped("用户已停止下载。")


@dataclass(frozen=True)
class DownloadOptions:
    output_dir: Path
    quality: str
    cookie_mode: str
    cookie_file: Path | None
    ffmpeg_dir: Path | None
    creator_name: str | None = None
    organize_by_creator: bool = False


@dataclass(frozen=True)
class DownloadResult:
    files: list[Path]
    skipped: bool = False
    message: str = ""


class _ExternalProgressState:
    """保存 aria2 直链下载的总大小；由 yt-dlp 解析线程写入、采样线程读取。"""

    def __init__(self) -> None:
        self._lock = Lock()
        self._total_bytes = 0
        self._media_url = ""
        self._http_headers: dict[str, str] = {}

    def set_total_bytes(self, value: object) -> None:
        try:
            total = max(0, int(value or 0))
        except (TypeError, ValueError):
            total = 0
        with self._lock:
            self._total_bytes = total

    def total_bytes(self) -> int:
        with self._lock:
            return self._total_bytes

    def set_media_request(self, url: object, headers: object) -> None:
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return
        safe_headers = {
            str(key): str(value)
            for key, value in (headers.items() if isinstance(headers, dict) else [])
            if str(key).casefold() not in {"range", "content-length"}
        }
        with self._lock:
            self._media_url = url
            self._http_headers = safe_headers

    def media_request(self) -> tuple[str, dict[str, str]]:
        with self._lock:
            return self._media_url, dict(self._http_headers)


def _external_download_total_bytes(info: dict[str, Any]) -> int:
    """优先取得 yt-dlp 已选媒体流的精确体积，必要时使用近似值。"""
    formats = info.get("requested_formats") or [info]
    total = 0
    for media_format in formats:
        if not isinstance(media_format, dict):
            continue
        value = media_format.get("filesize") or media_format.get("filesize_approx")
        try:
            total += max(0, int(value or 0))
        except (TypeError, ValueError):
            continue
    if total:
        return total
    try:
        return max(0, int(info.get("filesize") or info.get("filesize_approx") or 0))
    except (TypeError, ValueError):
        return 0


def _format_transfer_size(value: float) -> str:
    units = ("B", "KB", "MB", "GB")
    amount = max(0.0, float(value))
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f}{unit}" if unit != "B" else f"{int(amount)}B"
        amount /= 1024
    return "0B"


def _format_transfer_eta(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    minutes, sec = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}时{minutes:02d}分"
    if minutes:
        return f"{minutes}分{sec:02d}秒"
    return f"{sec}秒"


def _content_length_from_headers(headers: Any, *, range_request: bool) -> int:
    content_range = str(headers.get("Content-Range") or "")
    match = re.search(r"/(\d+)\s*$", content_range)
    if match:
        return int(match.group(1))
    if range_request:
        return 0
    try:
        return max(0, int(headers.get("Content-Length") or 0))
    except (TypeError, ValueError):
        return 0


def _probe_direct_media_total_bytes(url: str, headers: dict[str, str]) -> int:
    """不下载正文，只用 HEAD/首字节 Range 取得直链媒体总大小。"""
    if not url:
        return 0
    for method, range_request in (("HEAD", False), ("GET", True)):
        request_headers = dict(headers)
        if range_request:
            request_headers["Range"] = "bytes=0-0"
        request = urllib.request.Request(url, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                total = _content_length_from_headers(response.headers, range_request=range_request)
                if total:
                    return total
                if range_request:
                    response.read(1)
        except Exception:
            continue
    return 0


class _ExternalDirectProgressMonitor:
    """补齐 yt-dlp 外部 aria2 直链下载过程没有 progress hook 的缺口。"""

    POLL_INTERVAL_SECONDS = 0.4
    # NTFS 的文件修改时间可能比 Python 记录的启动纳秒时间略早；不给容差会漏掉刚生成的 .part。
    PART_FILE_DISCOVERY_GRACE_SECONDS = 5

    def __init__(
        self,
        output_dir: Path,
        state: _ExternalProgressState,
        progress_callback: ProgressCallback,
        cancel_callback: CancelCallback | None,
    ) -> None:
        self.output_dir = output_dir
        self.state = state
        self.progress_callback = progress_callback
        self.cancel_callback = cancel_callback
        self.started_at_ns = time.time_ns()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._active_path: Path | None = None
        self._last_size = 0
        self._last_speed = 0.0
        self._last_sample_at = time.monotonic()
        self._total_probe_started = False

    def start(self) -> None:
        self._thread = Thread(target=self._run, name="NanfengAria2Progress", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _find_active_part_file(self) -> Path | None:
        if self._active_path and self._active_path.is_file():
            return self._active_path
        if not self.output_dir.is_dir():
            return None
        candidates: list[Path] = []
        minimum_mtime_ns = self.started_at_ns - int(self.PART_FILE_DISCOVERY_GRACE_SECONDS * 1_000_000_000)
        try:
            for candidate in self.output_dir.rglob("*.part"):
                try:
                    if candidate.is_file() and candidate.stat().st_mtime_ns >= minimum_mtime_ns:
                        candidates.append(candidate)
                except OSError:
                    continue
        except OSError:
            return None
        if not candidates:
            return None
        self._active_path = max(candidates, key=lambda candidate: candidate.stat().st_mtime_ns)
        self._last_size = 0
        self._last_speed = 0.0
        self._last_sample_at = time.monotonic()
        return self._active_path

    def _start_total_probe_if_needed(self) -> None:
        if self._total_probe_started or self.state.total_bytes() > 0:
            return
        url, headers = self.state.media_request()
        if not url:
            return
        self._total_probe_started = True

        def probe() -> None:
            total = _probe_direct_media_total_bytes(url, headers)
            if total:
                self.state.set_total_bytes(total)

        Thread(target=probe, name="NanfengAria2Length", daemon=True).start()

    def sample_progress(self) -> dict[str, Any] | None:
        part_file = self._find_active_part_file()
        if not part_file:
            return None
        try:
            downloaded = part_file.stat().st_size
        except OSError:
            self._active_path = None
            return None

        now = time.monotonic()
        elapsed = max(now - self._last_sample_at, 0.001)
        sampled_speed = max(0.0, (downloaded - self._last_size) / elapsed)
        if sampled_speed > 0:
            self._last_speed = sampled_speed
        self._last_size = downloaded
        self._last_sample_at = now
        self._start_total_probe_if_needed()
        total = self.state.total_bytes()
        event: dict[str, Any] = {
            "status": "downloading",
            "downloaded_bytes": downloaded,
            "progress_label": f"已下载 {_format_transfer_size(downloaded)}",
            "_speed_str": f"{_format_transfer_size(self._last_speed)}/s" if self._last_speed else "测速中",
            "_eta_str": "-",
            "external_progress": True,
        }
        if total > 0:
            event["total_bytes"] = total
            if self._last_speed > 0 and downloaded < total:
                event["_eta_str"] = _format_transfer_eta((total - downloaded) / self._last_speed)
        return event

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if self.cancel_callback and self.cancel_callback():
                return
            event = self.sample_progress()
            if event:
                self.progress_callback(event)
            self._stop_event.wait(self.POLL_INTERVAL_SECONDS)


def split_urls(text: str) -> list[str]:
    """从多行文本里提取链接，保留输入顺序并去重。"""
    stripped = text.strip()
    candidates = re.findall(r"https?://[^\s，。；;]+", stripped)
    for url in re.findall(r"(?<![\w./:-])(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s，。；;]+", stripped, flags=re.IGNORECASE):
        clean = url
        if clean.lower().startswith("youtube.com/"):
            clean = f"www.{clean}"
        candidates.append(f"https://{clean}")
    candidates.extend(f"https://www.youtube.com/@{handle}" for handle in re.findall(r"(?<![\w./-])@([A-Za-z0-9._-]{3,60})", stripped))
    for line in stripped.splitlines():
        handle = line.strip().strip(" @")
        if re.fullmatch(r"[A-Za-z0-9._-]{3,60}", handle) and not re.fullmatch(r"\d{16,22}", handle):
            candidates.append(f"https://www.youtube.com/@{handle}")
    text_without_urls = re.sub(r"https?://[^\s，。；;]+", " ", text)
    candidates.extend(
        f"https://www.douyin.com/video/{item_id}"
        for item_id in re.findall(r"(?<!\d)(\d{16,22})(?!\d)", text_without_urls)
    )
    seen: set[str] = set()
    urls: list[str] = []
    for url in candidates:
        clean_url = url.strip().rstrip(".,)")
        if clean_url and clean_url not in seen:
            seen.add(clean_url)
            urls.append(clean_url)
    return urls


def detect_platform(url: str) -> str:
    if url_host_matches(url, "douyin.com", "iesdouyin.com"):
        return "抖音"
    if url_host_matches(url, "youtube.com", "youtu.be"):
        return "YouTube"
    if url_host_matches(url, "bilibili.com", "b23.tv"):
        return "哔哩哔哩"
    if url_host_matches(url, "xiaohongshu.com", "xhslink.com"):
        return "小红书"
    if url_host_matches(url, "tiktok.com"):
        return "TikTok"
    if url_host_matches(url, "pornhub.com"):
        return "Pornhub"
    return "未知"


SUPPORTED_PLATFORM_LABELS = ("抖音", "YouTube", "哔哩哔哩", "小红书", "TikTok", "Pornhub")


def assert_supported_platform_url(url: str) -> str:
    """拒绝未纳入产品范围的站点，避免误走软件内登录分支。"""
    platform = detect_platform(url)
    if platform == "未知":
        names = "、".join(SUPPORTED_PLATFORM_LABELS)
        raise RuntimeError(f"当前版本仅支持 {names} 链接，暂不支持此平台。")
    return platform


def _auth_platform_for_url(url: str) -> str | None:
    """只把目标平台自己的软件内 Cookie 传给 yt-dlp。"""
    platform = detect_platform(url)
    return {
        "YouTube": "youtube",
        "哔哩哔哩": "bilibili",
        "TikTok": "tiktok",
    }.get(platform)


def find_ffmpeg_dir(project_root: Path) -> Path | None:
    """优先复用当前工具包里的 FFmpeg，找不到时交给系统 PATH。"""
    configured = os.environ.get("NANFENG_FFMPEG_DIR")
    candidates = [
        Path(configured) if configured else project_root / "tools" / "ffmpeg",
        project_root.parent / "JHlib" / "ffmpeg",
        project_root.parent / "江湖工具箱" / "JHlib" / "ffmpeg",
        project_root / "JHlib" / "ffmpeg",
        Path("/opt/homebrew/bin"),
        Path("/usr/local/bin"),
        Path("/usr/bin"),
    ]
    ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    for candidate in candidates:
        if (candidate / ffmpeg_name).exists() and (candidate / ffprobe_name).exists():
            return candidate
    return None


def build_format_selector(quality: str) -> str:
    if quality == "仅音频 MP3":
        return "bestaudio/best"
    return (
        "bv[protocol^=https][ext=mp4]+ba[protocol^=https][ext=m4a]/"
        "bv[ext=mp4]+ba[ext=m4a]/bv+ba/b[ext=mp4]/best"
    )


def build_format_sort(quality: str) -> list[str]:
    """按视频短边限制分辨率，竖屏 720x1280 也会正确归入 720p。"""
    if quality == "仅音频 MP3":
        return ["abr", "proto:https", "aext:m4a"]
    resolution_limits = {
        "1080p 及以下": 1080,
        "720p 及以下": 720,
        "360p 及以下": 360,
    }
    resolution = resolution_limits.get(quality)
    resolution_sort = f"res:{resolution}" if resolution else "res"
    return [resolution_sort, "proto:https", "vext:mp4", "aext:m4a"]


def youtube_pot_provider_home() -> Path:
    """软件专用的访客 PO Token Provider 安装位置。"""
    installed_home = auth_data_dir() / YOUTUBE_POT_PROVIDER_DIRECTORY / "server"
    if (installed_home / "build" / "generate_once.js").exists():
        return installed_home

    for root in _runtime_resource_roots():
        bundled_home = root / "tools" / YOUTUBE_POT_PROVIDER_DIRECTORY / "server"
        if (bundled_home / "build" / "generate_once.js").exists():
            return bundled_home
    return installed_home


def _runtime_resource_roots() -> list[Path]:
    if not getattr(sys, "frozen", False):
        return [Path(__file__).resolve().parents[1]]

    roots = [Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))]
    executable_root = Path(sys.executable).resolve().parent
    if executable_root not in roots:
        roots.append(executable_root)
    return roots


def find_node_runtime() -> Path | None:
    """优先使用发布包携带的 Node，未打包时再复用本机 Node。"""
    node_name = "node.exe" if os.name == "nt" else "node"
    for root in _runtime_resource_roots():
        bundled_node = root / "tools" / "node" / node_name
        if bundled_node.is_file():
            return bundled_node

    node_path = shutil.which(node_name)
    return Path(node_path) if node_path else None


def find_aria2c() -> Path | None:
    """查找随软件分发的 aria2；只作为 HTTP(S) 直链加速器使用。"""
    aria2_name = "aria2c.exe" if os.name == "nt" else "aria2c"
    configured = os.environ.get("NANFENG_ARIA2C")
    candidates: list[Path] = [Path(configured)] if configured else []
    for root in _runtime_resource_roots():
        candidates.extend(
            (
                root / "tools" / "aria2" / aria2_name,
                root / "tools" / aria2_name,
            )
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    aria2_path = shutil.which(aria2_name)
    return Path(aria2_path) if aria2_path else None


def build_direct_http_acceleration_options(platform: str | None) -> dict[str, Any]:
    """只加速可恢复的直链，绝不把 aria2 用到 HLS/DASH 清单。"""
    if platform != "Pornhub":
        return {}
    aria2c = find_aria2c()
    if not aria2c:
        return {}
    return {
        # yt-dlp 会按协议选择下载器。清单流固定走 native，避免 aria2 输入清单风险。
        "external_downloader": {
            "http": str(aria2c),
            "https": str(aria2c),
            "m3u8": "native",
            "dash": "native",
        },
        "external_downloader_args": {
            "aria2c": [
                "--max-connection-per-server=16",
                "--split=16",
                "--min-split-size=8M",
                "--file-allocation=none",
            ]
        },
    }


def youtube_pot_provider_ready() -> bool:
    return (youtube_pot_provider_home() / "build" / "generate_once.js").exists()


def build_youtube_runtime_options() -> dict[str, Any]:
    """为公开 YouTube 内容启用 Node 挑战求解和可选的访客 PO Token。"""
    node_runtime = find_node_runtime()
    node_options = {"path": str(node_runtime)} if node_runtime else {}
    options: dict[str, Any] = {"js_runtimes": {"node": node_options}}
    provider_home = youtube_pot_provider_home()
    if youtube_pot_provider_ready():
        options["extractor_args"] = {
            "youtubepot-bgutilscript": {"server_home": [str(provider_home)]}
        }
    return options


def safe_path_name(text: str | None, fallback: str = "未知作者") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\r\n\t]+', " ", text or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        cleaned = fallback
    return cleaned[:80]


def build_ydl_options(
    options: DownloadOptions,
    progress_callback: ProgressCallback,
    cancel_callback: CancelCallback | None = None,
    auth_platform: str | None = None,
    managed_cookie_file: Path | None = None,
    download_platform: str | None = None,
) -> dict[str, Any]:
    def checked_progress(info: dict[str, Any]) -> None:
        raise_if_cancelled(cancel_callback)
        progress_callback(info)
        raise_if_cancelled(cancel_callback)

    relative_dir = Path("%(extractor_key)s")
    if options.organize_by_creator:
        creator_dir = safe_path_name(options.creator_name) if options.creator_name else "%(uploader|未知作者).80B"
        relative_dir /= creator_dir
    output_template = str(options.output_dir / relative_dir / "%(upload_date)s %(title).120B.%(ext)s")
    ydl_options: dict[str, Any] = {
        "outtmpl": output_template,
        "format": build_format_selector(options.quality),
        "format_sort": build_format_sort(options.quality),
        "merge_output_format": "mp4",
        "noplaylist": False,
        "ignoreerrors": False,
        "continuedl": True,
        "retries": 3,
        "fragment_retries": 3,
        "concurrent_fragment_downloads": FRAGMENT_DOWNLOAD_CONCURRENCY,
        "buffersize": DOWNLOAD_BUFFER_SIZE,
        "http_chunk_size": HTTP_DOWNLOAD_CHUNK_SIZE,
        "progress_delta": PROGRESS_UPDATE_INTERVAL,
        "windowsfilenames": True,
        "progress_hooks": [checked_progress],
        "quiet": True,
        "no_warnings": False,
    }
    if download_platform == "YouTube":
        ydl_options.update(build_youtube_runtime_options())
    ydl_options.update(build_direct_http_acceleration_options(download_platform))
    if ydl_options.get("external_downloader"):
        progress_state = _ExternalProgressState()

        def capture_external_total(info: dict[str, Any], *, incomplete: bool = False) -> None:
            if not incomplete:
                progress_state.set_total_bytes(_external_download_total_bytes(info))
                media_info = info
                requested_formats = info.get("requested_formats")
                if isinstance(requested_formats, list):
                    media_info = next(
                        (
                            media_format
                            for media_format in requested_formats
                            if isinstance(media_format, dict) and media_format.get("url")
                        ),
                        info,
                    )
                if isinstance(media_info, dict):
                    progress_state.set_media_request(
                        media_info.get("url"),
                        media_info.get("http_headers") or info.get("http_headers"),
                    )
            return None

        ydl_options[EXTERNAL_PROGRESS_STATE_KEY] = progress_state
        ydl_options["match_filter"] = capture_external_total

    if options.ffmpeg_dir:
        ydl_options["ffmpeg_location"] = str(options.ffmpeg_dir)

    if options.quality == "仅音频 MP3":
        ydl_options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    else:
        ydl_options["postprocessors"] = [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ]

    if options.cookie_mode == AUTH_COOKIE_MODE and auth_platform:
        cookie_file = managed_cookie_file or export_auth_cookies_txt(auth_platform)
        ydl_options["cookiefile"] = str(cookie_file)
    elif options.cookie_mode in {"Chrome", "Edge", "Firefox"}:
        ydl_options["cookiesfrombrowser"] = (options.cookie_mode.lower(),)
    elif options.cookie_mode == "cookies.txt" and options.cookie_file:
        ydl_options["cookiefile"] = str(options.cookie_file)

    return ydl_options


def _apply_bilibili_page_download_options(
    url: str,
    ydl_options: dict[str, Any],
) -> None:
    """让 B站分 P 队列项只下载当前页，并在文件名前保留稳定页码。"""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not (host == "bilibili.com" or host.endswith(".bilibili.com")) or "/video/" not in parsed.path.lower():
        return
    page_values = parse_qs(parsed.query).get("p") or []
    if not page_values or not str(page_values[0]).isdigit():
        return
    page_number = int(page_values[0])
    if page_number <= 0:
        return

    output_template = Path(str(ydl_options.get("outtmpl") or ""))
    if output_template.name:
        ydl_options["outtmpl"] = str(
            output_template.with_name(f"P{page_number:02d} {output_template.name}")
        )
    ydl_options["noplaylist"] = True


def _is_single_media_url(url: str) -> bool:
    """明确的单视频地址不得悄悄扩展成整张播放列表。"""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()
    if host == "youtube.com" or host.endswith(".youtube.com"):
        return (path == "/watch" and bool(parse_qs(parsed.query).get("v"))) or path.startswith("/shorts/")
    if host == "youtu.be" or host.endswith(".youtu.be"):
        return bool(path.strip("/"))
    if host == "bilibili.com" or host.endswith(".bilibili.com"):
        return "/video/" in path or "/bangumi/play/" in path
    if host == "b23.tv" or host.endswith(".b23.tv"):
        return bool(path.strip("/"))
    if host == "tiktok.com" or host.endswith(".tiktok.com"):
        return "/video/" in path
    return False


def _apply_single_media_download_options(url: str, ydl_options: dict[str, Any]) -> None:
    if _is_single_media_url(url):
        ydl_options["noplaylist"] = True


def _is_fragment_rate_limit_error(exc: Exception) -> bool:
    detail = str(exc).lower()
    if "sign in to confirm" in detail or "not a bot" in detail:
        return False
    return any(
        marker in detail
        for marker in (
            "http error 403",
            "http error 429",
            "too many requests",
            "rate limit",
            "rate-limit",
            "throttled",
            "throttling",
        )
    )


def _youtube_download_profiles(ydl_options: dict[str, Any]) -> list[tuple[int, int]]:
    """高速优先，403/429 后逐级减少请求数，并最终关闭 HTTP 分块。"""
    primary_concurrency = int(
        ydl_options.get("concurrent_fragment_downloads", FRAGMENT_DOWNLOAD_CONCURRENCY)
    )
    primary_chunk_size = int(ydl_options.get("http_chunk_size", HTTP_DOWNLOAD_CHUNK_SIZE) or 0)
    profiles = [(primary_concurrency, primary_chunk_size)]
    if primary_concurrency > FALLBACK_FRAGMENT_DOWNLOAD_CONCURRENCY:
        profiles.append((FALLBACK_FRAGMENT_DOWNLOAD_CONCURRENCY, primary_chunk_size))
    if profiles[-1] != (STABLE_FRAGMENT_DOWNLOAD_CONCURRENCY, 0):
        profiles.append((STABLE_FRAGMENT_DOWNLOAD_CONCURRENCY, 0))
    return profiles


def is_youtube_auth_error_text(detail: str) -> bool:
    normalized = detail.lower().replace("’", "'")
    return (
        "sign in to confirm" in normalized
        and ("not a bot" in normalized or "you're not a bot" in normalized)
    ) or "youtube 需要账号验证" in normalized


def is_youtube_unavailable_error_text(detail: str) -> bool:
    normalized = detail.lower()
    return "video unavailable" in normalized or "this video is unavailable" in normalized


def friendly_youtube_unavailable_error(exc: Exception) -> RuntimeError | None:
    if not is_youtube_unavailable_error_text(str(exc)):
        return None
    return RuntimeError(
        "YouTube 当前无法提供这条视频。它可能已删除、设为私密、受地区或年龄限制，"
        "或原链接已失效；请先在浏览器确认该视频可正常播放，再重新读取下载。"
    )


def friendly_youtube_auth_error(exc: Exception) -> RuntimeError | None:
    if not is_youtube_auth_error_text(str(exc)):
        return None
    if not has_youtube_account_cookies():
        if youtube_pot_provider_ready():
            return RuntimeError(
                "YouTube 暂时拒绝当前网络出口的公开访问。软件已启用无登录兼容模式，"
                "请切换代理节点或网络后重试；登录仅作为需要账号权限内容的可选后备。"
            )
        return RuntimeError(
            "YouTube 需要账号验证，软件内 YouTube 当前未连接。请点击顶部 YouTube 按钮，"
            "完成登录并确认页面右上角显示账号头像；关闭登录窗口后，再重新下载。"
        )
    return RuntimeError(
        "YouTube 需要账号验证，当前会话已失效或被平台临时限制。请重新点击顶部 YouTube 按钮，"
        "确认账号仍处于登录状态并关闭窗口，然后重试；批量请求过快时也可能需要稍后再试。"
    )


def should_retry_public_youtube_request(exc: Exception) -> bool:
    """仅为偶发的公开访问风控重新建立一次游客会话。"""
    return (
        is_youtube_auth_error_text(str(exc))
        and youtube_pot_provider_ready()
        and not has_youtube_account_cookies()
    )


def wait_before_public_youtube_retry(cancel_callback: CancelCallback | None = None) -> None:
    raise_if_cancelled(cancel_callback)
    time.sleep(YOUTUBE_PUBLIC_RETRY_DELAY_SECONDS)
    raise_if_cancelled(cancel_callback)


def _run_ytdlp_download(
    url: str,
    ydl_options: dict[str, Any],
    cancel_callback: CancelCallback | None,
) -> int | None:
    from yt_dlp import YoutubeDL

    runtime_options = dict(ydl_options)
    progress_state = runtime_options.pop(EXTERNAL_PROGRESS_STATE_KEY, None)
    output_template = str(runtime_options.get("outtmpl") or "")
    output_directory = Path(output_template.split("%(", 1)[0]) if "%(" in output_template else Path(output_template).parent
    monitor: _ExternalDirectProgressMonitor | None = None
    if isinstance(progress_state, _ExternalProgressState) and runtime_options.get("external_downloader"):
        progress_hooks = runtime_options.get("progress_hooks") or []
        progress_callback = progress_hooks[0] if progress_hooks else (lambda _info: None)
        monitor = _ExternalDirectProgressMonitor(
            output_directory,
            progress_state,
            progress_callback,
            cancel_callback,
        )
        monitor.start()
    try:
        with YoutubeDL(runtime_options) as ydl:
            raise_if_cancelled(cancel_callback)
            result_code = ydl.download([url])
            raise_if_cancelled(cancel_callback)
            return result_code
    finally:
        if monitor:
            monitor.stop()


def _download_with_adaptive_concurrency(
    url: str,
    ydl_options: dict[str, Any],
    progress_callback: ProgressCallback,
    cancel_callback: CancelCallback | None,
) -> int | None:
    """优先高速分片；遇到平台 403/429 时退到低请求的稳定传输。"""
    profiles = _youtube_download_profiles(ydl_options)
    acceleration_enabled = bool(ydl_options.get("external_downloader"))

    for attempt_index, (concurrency, chunk_size) in enumerate(profiles):
        current_options = dict(ydl_options)
        current_options["concurrent_fragment_downloads"] = concurrency
        current_options["http_chunk_size"] = chunk_size
        try:
            return _run_ytdlp_download(url, current_options, cancel_callback)
        except DownloadStopped:
            raise
        except Exception as exc:
            if acceleration_enabled:
                # 直链站点不接受多连接或 Range 时，立即退回原生下载，避免长时间卡住。
                acceleration_enabled = False
                native_options = dict(ydl_options)
                native_options.pop("external_downloader", None)
                native_options.pop("external_downloader_args", None)
                native_options.pop(EXTERNAL_PROGRESS_STATE_KEY, None)
                native_options.pop("match_filter", None)
                native_options["concurrent_fragment_downloads"] = STABLE_FRAGMENT_DOWNLOAD_CONCURRENCY
                native_options["http_chunk_size"] = 0
                progress_callback(
                    {
                        "status": "retrying",
                        "reason": "高速直连被站点限制，已切换兼容下载继续。",
                        "fragment_concurrency": STABLE_FRAGMENT_DOWNLOAD_CONCURRENCY,
                        "http_chunk_size": 0,
                    }
                )
                return _run_ytdlp_download(url, native_options, cancel_callback)
            can_retry = attempt_index + 1 < len(profiles) and _is_fragment_rate_limit_error(exc)
            if not can_retry:
                raise
            raise_if_cancelled(cancel_callback)
            next_concurrency, next_chunk_size = profiles[attempt_index + 1]
            if next_concurrency == STABLE_FRAGMENT_DOWNLOAD_CONCURRENCY and next_chunk_size == 0:
                reason = "平台仍拒绝分片请求，已切换稳定单连接继续下载"
            else:
                reason = "平台限制高速分片，已自动降低并发并继续下载"
            progress_callback(
                {
                    "status": "retrying",
                    "reason": reason,
                    "fragment_concurrency": next_concurrency,
                    "http_chunk_size": next_chunk_size,
                }
            )

    raise RuntimeError("下载重试流程异常结束。")


def _friendly_cookie_error(exc: Exception) -> RuntimeError | None:
    detail = str(exc)
    if "Could not copy Chrome cookie database" not in detail:
        return None
    return RuntimeError(
        "无法读取 Chrome 登录态：Chrome 正在占用 Cookie 文件。\n\n"
        "处理方式：\n"
        "1. 完全关闭 Chrome，包括右下角托盘里的后台 Chrome。\n"
        "2. 回到本软件，保持登录态为 Chrome，再重新操作。\n"
        "3. 如果仍失败，请用浏览器扩展导出 Netscape 格式 cookies.txt，"
        "然后在本软件里把登录态改成 cookies.txt。"
    )


def _clean_title_stem(stem: str) -> str:
    """统一清理下载后的文件名，去掉平台状态词和多余标点。"""
    cleaned = stem
    cleaned = re.sub(r"[“”\"'‘’]", "", cleaned)
    cleaned = re.sub(r"\s*(正在直播|直播中|正在首播|Premiere|LIVE)\s*[！!]*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\[[A-Za-z0-9_-]{6,24}\]\s*$", "", cleaned)
    cleaned = re.sub(r"^(?P<date>\d{4})(?P<month>\d{2})(?P<day>\d{2})\s+", r"\g<date>-\g<month>-\g<day> ", cleaned)
    cleaned = re.sub(r"^(NA|N/A|None|null)\s+", "未知日期 ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-_")
    return cleaned or stem


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"无法生成不重名文件名：{path}")


def _normalize_downloaded_files(files: list[Path]) -> list[Path]:
    normalized: list[Path] = []
    for file_path in files:
        if not file_path.exists():
            continue
        new_stem = _clean_title_stem(file_path.stem)
        new_path = file_path.with_name(f"{new_stem}{file_path.suffix.lower()}")
        if new_path != file_path:
            new_path = _unique_path(new_path)
            file_path.rename(new_path)
            file_path = new_path
        normalized.append(file_path)
    return normalized


def _snapshot_files(directory: Path) -> dict[Path, tuple[int, int]]:
    if not directory.exists():
        return {}
    snapshot: dict[Path, tuple[int, int]] = {}
    for file_path in directory.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() in {".part", ".ytdl", ".tmp", ".temp"}:
            continue
        stat = file_path.stat()
        snapshot[file_path] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


def _changed_files(before: dict[Path, tuple[int, int]], after: dict[Path, tuple[int, int]]) -> list[Path]:
    changed: list[Path] = []
    for file_path, signature in after.items():
        if before.get(file_path) != signature:
            changed.append(file_path)
    return sorted(changed, key=lambda item: item.stat().st_mtime_ns, reverse=True)


def _validated_media_files(files: list[Path], ffmpeg_dir: Path | None) -> list[Path]:
    validated: list[Path] = []
    errors: list[str] = []
    for file_path in files:
        if file_path.suffix.lower() not in MEDIA_FILE_SUFFIXES:
            continue
        try:
            validate_media_file(file_path, ffmpeg_dir)
        except InvalidMediaError as exc:
            errors.append(str(exc))
            file_path.unlink(missing_ok=True)
            continue
        validated.append(file_path)
    if not validated:
        detail = errors[0] if errors else "下载流程没有生成支持的音视频文件。"
        raise RuntimeError(detail)
    return validated


def download_url(
    url: str,
    options: DownloadOptions,
    progress_callback: ProgressCallback,
    cancel_callback: CancelCallback | None = None,
) -> DownloadResult:
    """执行单个链接下载。

    这里延迟导入 yt_dlp，方便界面启动时给出清晰的依赖缺失提示。
    """
    raise_if_cancelled(cancel_callback)
    platform = assert_supported_platform_url(url)

    from .douyin import download_douyin_url, is_douyin_url
    from .xiaohongshu import download_xiaohongshu_url, is_xiaohongshu_url

    if is_douyin_url(url):
        return download_douyin_url(url, options, progress_callback, cancel_callback)
    if is_xiaohongshu_url(url):
        return download_xiaohongshu_url(url, options, progress_callback, cancel_callback)

    options.output_dir.mkdir(parents=True, exist_ok=True)
    before = _snapshot_files(options.output_dir)

    auth_platform = _auth_platform_for_url(url)
    managed_cookie_file: Path | None = None
    try:
        if options.cookie_mode == AUTH_COOKIE_MODE and auth_platform:
            managed_cookie_file = export_auth_cookies_txt(auth_platform)
        ydl_options = build_ydl_options(
            options,
            progress_callback,
            cancel_callback,
            auth_platform=auth_platform,
            managed_cookie_file=managed_cookie_file,
            download_platform=platform,
        )
        _apply_single_media_download_options(url, ydl_options)
        _apply_bilibili_page_download_options(url, ydl_options)
        for attempt in range(YOUTUBE_PUBLIC_REQUEST_ATTEMPTS):
            try:
                result_code = _download_with_adaptive_concurrency(
                    url,
                    ydl_options,
                    progress_callback,
                    cancel_callback,
                )
                break
            except Exception as exc:
                if attempt + 1 >= YOUTUBE_PUBLIC_REQUEST_ATTEMPTS or not should_retry_public_youtube_request(exc):
                    raise
                progress_callback(
                    {
                        "status": "retrying",
                        "reason": "YouTube 正在重新建立公开访问会话，请稍候重试。",
                    }
                )
                wait_before_public_youtube_retry(cancel_callback)
    except Exception as exc:
        if isinstance(exc, DownloadStopped):
            raise
        youtube_unavailable_error = friendly_youtube_unavailable_error(exc)
        if youtube_unavailable_error:
            raise youtube_unavailable_error from exc
        youtube_auth_error = friendly_youtube_auth_error(exc)
        if youtube_auth_error:
            raise youtube_auth_error from exc
        friendly_error = _friendly_cookie_error(exc)
        if friendly_error:
            raise friendly_error from exc
        raise
    finally:
        release_auth_cookie_export(managed_cookie_file)

    after = _snapshot_files(options.output_dir)
    changed = _changed_files(before, after)
    if result_code not in (None, 0):
        raise RuntimeError(f"yt-dlp 返回失败状态：{result_code}")
    if not changed:
        if any(is_probable_existing_media(path) for path in before):
            return DownloadResult(files=[], skipped=True, message="保存目录中已存在对应文件，已跳过下载。")
        raise RuntimeError("下载流程结束，但保存目录里没有新增文件。可能是链接解析失败、平台限制，或需要选择浏览器登录态。")
    validated = _validated_media_files(changed, options.ffmpeg_dir)
    return DownloadResult(files=_normalize_downloaded_files(validated))
