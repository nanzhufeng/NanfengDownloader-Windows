from __future__ import annotations

import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .auth_profile import (
    AUTH_COOKIE_MODE,
    auth_data_dir,
    export_auth_cookies_txt,
    has_youtube_account_cookies,
)


ProgressCallback = Callable[[dict[str, Any]], None]
CancelCallback = Callable[[], bool]


FRAGMENT_DOWNLOAD_CONCURRENCY = 16
FALLBACK_FRAGMENT_DOWNLOAD_CONCURRENCY = 8
DOWNLOAD_BUFFER_SIZE = 1024 * 1024
HTTP_DOWNLOAD_CHUNK_SIZE = 10 * 1024 * 1024
PROGRESS_UPDATE_INTERVAL = 0.2
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


@dataclass(frozen=True)
class DownloadResult:
    files: list[Path]
    skipped: bool = False
    message: str = ""


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
    candidates.extend(f"https://www.douyin.com/video/{item_id}" for item_id in re.findall(r"(?<!\d)(\d{16,22})(?!\d)", text))
    seen: set[str] = set()
    urls: list[str] = []
    for url in candidates:
        clean_url = url.strip().rstrip(".,)")
        if clean_url and clean_url not in seen:
            seen.add(clean_url)
            urls.append(clean_url)
    return urls


def detect_platform(url: str) -> str:
    lower = url.lower()
    if "douyin.com" in lower:
        return "抖音"
    if "youtube.com" in lower or "youtu.be" in lower:
        return "YouTube"
    return "未知"


def find_ffmpeg_dir(project_root: Path) -> Path | None:
    """优先复用当前工具包里的 FFmpeg，找不到时交给系统 PATH。"""
    candidates = [
        project_root / "tools" / "ffmpeg",
        project_root.parent / "JHlib" / "ffmpeg",
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
) -> dict[str, Any]:
    def checked_progress(info: dict[str, Any]) -> None:
        raise_if_cancelled(cancel_callback)
        progress_callback(info)
        raise_if_cancelled(cancel_callback)

    creator_dir = safe_path_name(options.creator_name) if options.creator_name else "%(uploader|未知作者).80B"
    output_template = str(options.output_dir / "%(extractor_key)s" / creator_dir / "%(upload_date)s %(title).120B.%(ext)s")
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
    ydl_options.update(build_youtube_runtime_options())

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

    if options.cookie_mode == AUTH_COOKIE_MODE:
        ydl_options["cookiefile"] = str(export_auth_cookies_txt())
    elif options.cookie_mode in {"Chrome", "Edge", "Firefox"}:
        ydl_options["cookiesfrombrowser"] = (options.cookie_mode.lower(),)
    elif options.cookie_mode == "cookies.txt" and options.cookie_file:
        ydl_options["cookiefile"] = str(options.cookie_file)

    return ydl_options


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


def is_youtube_auth_error_text(detail: str) -> bool:
    normalized = detail.lower().replace("’", "'")
    return (
        "sign in to confirm" in normalized
        and ("not a bot" in normalized or "you're not a bot" in normalized)
    ) or "youtube 需要账号验证" in normalized


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
            "YouTube 需要账号验证，软件内 YouTube 当前未登录。请点击顶部“登录 YouTube”，"
            "完成登录并确认页面右上角显示账号头像；关闭登录窗口后，再重新下载。"
        )
    return RuntimeError(
        "YouTube 需要账号验证，当前登录态已失效或被平台临时限制。请重新点击顶部“登录 YouTube”，"
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

    with YoutubeDL(ydl_options) as ydl:
        raise_if_cancelled(cancel_callback)
        result_code = ydl.download([url])
        raise_if_cancelled(cancel_callback)
        return result_code


def _download_with_adaptive_concurrency(
    url: str,
    ydl_options: dict[str, Any],
    progress_callback: ProgressCallback,
    cancel_callback: CancelCallback | None,
) -> int | None:
    """优先高速分片；平台限流时仅降并发重试一次并复用断点文件。"""
    primary_concurrency = int(
        ydl_options.get("concurrent_fragment_downloads", FRAGMENT_DOWNLOAD_CONCURRENCY)
    )
    attempts = [primary_concurrency]
    if primary_concurrency > FALLBACK_FRAGMENT_DOWNLOAD_CONCURRENCY:
        attempts.append(FALLBACK_FRAGMENT_DOWNLOAD_CONCURRENCY)

    for attempt_index, concurrency in enumerate(attempts):
        current_options = dict(ydl_options)
        current_options["concurrent_fragment_downloads"] = concurrency
        try:
            return _run_ytdlp_download(url, current_options, cancel_callback)
        except DownloadStopped:
            raise
        except Exception as exc:
            can_retry = attempt_index == 0 and len(attempts) > 1 and _is_fragment_rate_limit_error(exc)
            if not can_retry:
                raise
            raise_if_cancelled(cancel_callback)
            progress_callback(
                {
                    "status": "retrying",
                    "reason": "平台限制并发，已自动降低分片并继续下载",
                    "fragment_concurrency": FALLBACK_FRAGMENT_DOWNLOAD_CONCURRENCY,
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


def download_url(
    url: str,
    options: DownloadOptions,
    progress_callback: ProgressCallback,
    cancel_callback: CancelCallback | None = None,
) -> DownloadResult:
    """执行单个链接下载。

    这里延迟导入 yt_dlp，方便界面启动时给出清晰的依赖缺失提示。
    """
    from .douyin import download_douyin_url, is_douyin_url

    raise_if_cancelled(cancel_callback)

    if is_douyin_url(url):
        return download_douyin_url(url, options, progress_callback, cancel_callback)

    options.output_dir.mkdir(parents=True, exist_ok=True)
    before = _snapshot_files(options.output_dir)

    ydl_options = build_ydl_options(options, progress_callback, cancel_callback)
    try:
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
        youtube_auth_error = friendly_youtube_auth_error(exc)
        if youtube_auth_error:
            raise youtube_auth_error from exc
        friendly_error = _friendly_cookie_error(exc)
        if friendly_error:
            raise friendly_error from exc
        raise

    after = _snapshot_files(options.output_dir)
    changed = _changed_files(before, after)
    if result_code not in (None, 0):
        raise RuntimeError(f"yt-dlp 返回失败状态：{result_code}")
    if not changed:
        if before:
            return DownloadResult(files=[], skipped=True, message="保存目录中已存在对应文件，已跳过下载。")
        raise RuntimeError("下载流程结束，但保存目录里没有新增文件。可能是链接解析失败、平台限制，或需要选择浏览器登录态。")
    return DownloadResult(files=_normalize_downloaded_files(changed))
