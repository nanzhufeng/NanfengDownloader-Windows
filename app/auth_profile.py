from __future__ import annotations

import atexit
import ctypes
import hashlib
import http.cookiejar
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUTH_COOKIE_MODE = "软件内登录"
AUTH_DATA_DIRECTORY_NAME = "NanfengDownloader"
LEGACY_AUTH_DATA_DIRECTORY_NAME = "NanzhufengVideoDownloader"
SUPPORTED_LOGIN_PLATFORMS = {"douyin", "youtube", "bilibili", "xiaohongshu", "tiktok"}
PLATFORM_COOKIE_DOMAINS = {
    "douyin": ("douyin.com", "iesdouyin.com"),
    "youtube": ("youtube.com", "google.com", "googleusercontent.com"),
    "bilibili": ("bilibili.com",),
    "xiaohongshu": ("xiaohongshu.com", "xhslink.com"),
    "tiktok": ("tiktok.com",),
}
YOUTUBE_ACCOUNT_COOKIE_NAMES = {
    "SID",
    "HSID",
    "SSID",
    "APISID",
    "SAPISID",
    "__Secure-1PSID",
    "__Secure-3PSID",
    "__Secure-1PAPISID",
    "__Secure-3PAPISID",
}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
COOKIE_VAULT_SCHEMA = 1
COOKIE_VAULT_SUFFIX = ".cookie-vault.dpapi"
RUNTIME_COOKIE_PREFIX = "runtime-cookies-"
_RUNTIME_COOKIE_EXPORTS: set[Path] = set()


def auth_data_dir() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    path = base / AUTH_DATA_DIRECTORY_NAME
    legacy_path = base / LEGACY_AUTH_DATA_DIRECTORY_NAME
    # 保留旧版登录数据，避免品牌改名后要求用户重新登录。
    if not path.exists() and legacy_path.exists():
        return legacy_path
    path.mkdir(parents=True, exist_ok=True)
    return path


def auth_profile_dir(platform: str | None = None) -> Path:
    profile_name = f"browser-profile-{platform}" if platform in SUPPORTED_LOGIN_PLATFORMS else "browser-profile"
    path = auth_data_dir() / profile_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def auth_cookie_file() -> Path:
    """旧版明文合并 Cookie 路径，仅用于一次性迁移。"""
    return auth_data_dir() / "managed-cookies.txt"


def platform_cookie_file(platform: str) -> Path:
    """旧版明文平台 Cookie 路径，仅用于一次性迁移。"""
    return auth_data_dir() / f"managed-cookies-{platform}.txt"


def cookie_vault_file(platform: str) -> Path:
    """平台登录 Cookie 的 Windows DPAPI 加密历史库。"""
    if platform not in SUPPORTED_LOGIN_PLATFORMS:
        raise RuntimeError("未知的登录平台。")
    return auth_data_dir() / f"{platform}{COOKIE_VAULT_SUFFIX}"


def legacy_cookie_vault_file() -> Path:
    """保留品牌改名前的合并 Cookie 历史，不作为跨平台下载凭据使用。"""
    return auth_data_dir() / f"legacy{COOKIE_VAULT_SUFFIX}"


def runtime_cookie_dir() -> Path:
    path = auth_data_dir() / "runtime-cookie-exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _data_blob(data: bytes) -> tuple[Any, Any]:
    """构造由调用方持有缓冲区生命周期的 Windows DATA_BLOB。"""
    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    buffer = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    return DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _dpapi_protect(data: bytes) -> bytes:
    """使用当前 Windows 用户的 DPAPI 加密，不依赖额外 Python 包。"""
    if os.name != "nt":
        raise RuntimeError("登录 Cookie 加密仅支持 Windows 版南枫下载。")
    input_blob, input_buffer = _data_blob(data)
    output_blob, _ = _data_blob(b"x")
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    crypt32.CryptProtectData.restype = ctypes.c_int
    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        "Nanfeng Downloader Cookie Vault",
        None,
        None,
        None,
        0x1,  # CRYPTPROTECT_UI_FORBIDDEN
        ctypes.byref(output_blob),
    ):
        raise OSError(ctypes.get_last_error(), "Windows 无法加密登录 Cookie。")
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)
        del input_buffer


def _dpapi_unprotect(data: bytes) -> bytes:
    """解密仅属于当前 Windows 用户的 Cookie 历史库。"""
    if os.name != "nt":
        raise RuntimeError("登录 Cookie 解密仅支持 Windows 版南枫下载。")
    input_blob, input_buffer = _data_blob(data)
    output_blob, _ = _data_blob(b"x")
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    crypt32.CryptUnprotectData.restype = ctypes.c_int
    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0x1,  # CRYPTPROTECT_UI_FORBIDDEN
        ctypes.byref(output_blob),
    ):
        raise OSError(ctypes.get_last_error(), "无法解密登录 Cookie：它可能来自其他 Windows 用户或已损坏。")
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)
        del input_buffer


def _empty_vault(platform: str) -> dict[str, Any]:
    return {"schema": COOKIE_VAULT_SCHEMA, "platform": platform, "snapshots": []}


def _load_cookie_vault(platform: str, *, legacy: bool = False) -> dict[str, Any]:
    target = legacy_cookie_vault_file() if legacy else cookie_vault_file(platform)
    if not target.exists():
        return _empty_vault(platform)
    try:
        payload = json.loads(_dpapi_unprotect(target.read_bytes()).decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取 {platform} 的加密 Cookie 历史：{exc}") from exc
    if payload.get("schema") != COOKIE_VAULT_SCHEMA or not isinstance(payload.get("snapshots"), list):
        raise RuntimeError(f"{platform} 的加密 Cookie 历史格式不受支持。")
    return payload


def _save_cookie_vault(platform: str, payload: dict[str, Any], *, legacy: bool = False) -> Path:
    target = legacy_cookie_vault_file() if legacy else cookie_vault_file(platform)
    target.write_bytes(_dpapi_protect(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))
    return target


def _cookie_text_from_items(cookies: list[dict[str, Any]]) -> str:
    lines = ["# Netscape HTTP Cookie File", "# Generated by Nanfeng Downloader"]
    for item in cookies:
        domain = str(item.get("domain") or "")
        name = str(item.get("name") or "")
        value = str(item.get("value") or "")
        if not domain or not name:
            continue
        include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
        path = str(item.get("path") or "/")
        secure = "TRUE" if item.get("secure") else "FALSE"
        raw_expires = item.get("expires")
        expires = str(int(raw_expires)) if raw_expires and float(raw_expires) > 0 else "0"
        lines.append("\t".join([domain, include_subdomains, path, secure, expires, name, value]))
    return "\n".join(lines) + "\n"


def _append_cookie_snapshot(platform: str, cookie_text: str, *, source: str, legacy: bool = False) -> Path:
    payload = _load_cookie_vault(platform, legacy=legacy)
    digest = hashlib.sha256(cookie_text.encode("utf-8")).hexdigest()
    snapshots = payload["snapshots"]
    if not any(entry.get("sha256") == digest for entry in snapshots if isinstance(entry, dict)):
        snapshots.append(
            {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "sha256": digest,
                "cookies": cookie_text,
            }
        )
    return _save_cookie_vault(platform, payload, legacy=legacy)


def _latest_cookie_text(platform: str) -> str | None:
    payload = _load_cookie_vault(platform)
    snapshots = [entry for entry in payload["snapshots"] if isinstance(entry, dict)]
    if not snapshots:
        return None
    latest = snapshots[-1].get("cookies")
    return latest if isinstance(latest, str) else None


def migrate_legacy_cookie_files() -> int:
    """将旧版明文 Cookie 完整归档到 DPAPI 历史库后删除明文副本。"""
    migrated = 0
    for platform in sorted(SUPPORTED_LOGIN_PLATFORMS):
        legacy_file = platform_cookie_file(platform)
        if not legacy_file.exists():
            continue
        cookie_text = legacy_file.read_text(encoding="utf-8", errors="strict")
        _append_cookie_snapshot(platform, cookie_text, source="legacy-plaintext")
        legacy_file.unlink()
        migrated += 1

    merged_file = auth_cookie_file()
    if merged_file.exists():
        cookie_text = merged_file.read_text(encoding="utf-8", errors="strict")
        _append_cookie_snapshot("legacy", cookie_text, source="legacy-merged", legacy=True)
        merged_file.unlink()
        migrated += 1
    return migrated


def migrate_legacy_browser_profile_cookies() -> int:
    """把旧版通用软件资料夹中的平台 Cookie 归档到独立加密历史库。"""
    legacy_profile = auth_data_dir() / "browser-profile"
    if not legacy_profile.exists():
        return 0

    browser_cookies = _load_browser_cookies()
    migrated = 0
    for platform in sorted(SUPPORTED_LOGIN_PLATFORMS):
        selected = _cookies_for_platform(platform, browser_cookies)
        if not selected:
            continue
        before = len(_load_cookie_vault(platform)["snapshots"])
        _save_platform_cookie_snapshot(platform, selected)
        if len(_load_cookie_vault(platform)["snapshots"]) > before:
            migrated += 1
    return migrated


def cleanup_runtime_cookie_exports() -> None:
    """删除已失效或上次异常退出遗留的短时明文 Cookie 文件。"""
    directory = runtime_cookie_dir()
    for file_path in directory.glob(f"{RUNTIME_COOKIE_PREFIX}*.txt"):
        try:
            file_path.unlink()
        except OSError:
            continue
    _RUNTIME_COOKIE_EXPORTS.clear()


@contextmanager
def exported_auth_cookies(platform: str) -> Any:
    """仅在调用下载器期间提供平台专属的短时明文 Cookie 文件。"""
    cookie_file = export_auth_cookies_txt(platform)
    try:
        yield cookie_file
    finally:
        release_auth_cookie_export(cookie_file)


def release_auth_cookie_export(cookie_file: Path | None) -> None:
    if cookie_file is None or cookie_file not in _RUNTIME_COOKIE_EXPORTS:
        return
    try:
        cookie_file.unlink(missing_ok=True)
    finally:
        _RUNTIME_COOKIE_EXPORTS.discard(cookie_file)


def has_youtube_account_cookies(cookie_file: Path | None = None) -> bool:
    """判断软件内 Cookie 是否包含尚未过期的 YouTube 账号登录凭据。"""
    if cookie_file is not None:
        if not cookie_file.exists():
            return False
        cookie_text = cookie_file.read_text(encoding="utf-8", errors="ignore")
    else:
        migrate_legacy_cookie_files()
        cookie_text = _latest_cookie_text("youtube") or ""

    now = time.time()
    for line in cookie_text.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, expires_text, name = parts[0].lower(), parts[4], parts[5]
        if "youtube.com" not in domain and "google.com" not in domain:
            continue
        if name not in YOUTUBE_ACCOUNT_COOKIE_NAMES:
            continue
        try:
            expires = int(expires_text or 0)
        except ValueError:
            continue
        if expires == 0 or expires > now:
            return True
    return False


def find_browser_path() -> str | None:
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path.home() / "Applications" / "Google Chrome.app" / "Contents" / "MacOS" / "Google Chrome",
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        Path.home() / "Applications" / "Microsoft Edge.app" / "Contents" / "MacOS" / "Microsoft Edge",
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/chromium"),
        Path("/usr/bin/microsoft-edge"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _write_cookies_txt(cookies: list[dict[str, Any]], target: Path | None = None) -> Path:
    """测试或用户显式导出时写 Netscape 格式文件；内部登录不再调用它持久化。"""
    target = target or auth_cookie_file()
    target.write_text(_cookie_text_from_items(cookies), encoding="utf-8")
    return target


def _save_platform_cookie_snapshot(platform: str, cookies: list[dict[str, Any]]) -> Path:
    """保留每次发生变化的 Cookie 历史，不再覆盖旧的有效会话。"""
    return _append_cookie_snapshot(platform, _cookie_text_from_items(cookies), source="software-login")


def open_login_browser(platform: str) -> None:
    """打开软件独立登录窗口，关闭窗口后导出 Cookie 供后续读取/下载使用。"""
    from playwright.sync_api import sync_playwright

    browser_path = find_browser_path()
    if not browser_path:
        raise RuntimeError("没有找到 Chrome 或 Edge，无法打开软件内登录窗口。")

    platform_url = {
        "douyin": "https://www.douyin.com/",
        "youtube": "https://www.youtube.com/",
        "bilibili": "https://www.bilibili.com/",
        "xiaohongshu": "https://www.xiaohongshu.com/explore",
        "tiktok": "https://www.tiktok.com/",
    }.get(platform)
    if not platform_url:
        raise RuntimeError("未知的登录平台。")

    with sync_playwright() as playwright:
        try:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(auth_profile_dir(platform)),
                executable_path=browser_path,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 820},
                locale="zh-CN",
                user_agent=USER_AGENT,
            )
        except Exception as exc:
            if "Target page, context or browser has been closed" in str(exc):
                raise RuntimeError("软件内登录窗口已经在运行，或上一次登录窗口还没有完全关闭。请先关闭那个登录窗口后再试。") from exc
            raise
        first_page = context.pages[0] if context.pages else context.new_page()
        try:
            first_page.goto(platform_url, wait_until="domcontentloaded", timeout=30_000)
        except Exception as exc:
            try:
                context.close()
            except Exception:
                pass
            raise RuntimeError(f"打开 {platform} 登录页失败：{exc}") from exc

        save_error: Exception | None = None
        try:
            last_saved = 0.0
            while context.pages:
                now = time.monotonic()
                if now - last_saved > 2:
                    try:
                        _save_platform_cookie_snapshot(platform, context.cookies())
                        last_saved = now
                    except Exception as exc:
                        save_error = exc
                time.sleep(0.5)
            _save_platform_cookie_snapshot(platform, context.cookies())
        except Exception as exc:
            save_error = exc
        try:
            context.close()
        except Exception as exc:
            if save_error is None:
                save_error = exc
        if save_error is not None:
            raise RuntimeError(f"{platform} 登录资料保存失败：{save_error}") from save_error


def launch_login_browser(platform: str) -> None:
    """用独立进程打开登录窗口，让主软件关闭后登录浏览器仍可保留。"""
    if platform not in SUPPORTED_LOGIN_PLATFORMS:
        raise RuntimeError("未知的登录平台。")
    if not find_browser_path():
        raise RuntimeError("没有找到 Chrome 或 Edge，无法打开软件内登录窗口。")

    if getattr(sys, "frozen", False):
        command = [sys.executable, "--login-browser", platform]
        cwd = str(Path(sys.executable).resolve().parent)
    else:
        start_script = Path(__file__).resolve().parents[1] / "start.py"
        command = [sys.executable, str(start_script), "--login-browser", platform]
        cwd = str(start_script.parent)

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    log_path = auth_data_dir() / f"login-browser-{platform}.log"
    with log_path.open("ab") as login_log:
        subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=login_log,
            stderr=login_log,
            close_fds=True,
            creationflags=creationflags,
        )


def _load_browser_cookies() -> list[dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    browser_path = find_browser_path()
    if not browser_path:
        raise RuntimeError("没有找到 Chrome 或 Edge，无法读取软件内登录态。")

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(auth_profile_dir()),
            executable_path=browser_path,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
            locale="zh-CN",
            user_agent=USER_AGENT,
        )
        cookies = context.cookies(
            [
                "https://www.douyin.com/",
                "https://www.iesdouyin.com/",
                "https://www.youtube.com/",
                "https://youtube.com/",
                "https://www.google.com/",
                "https://www.bilibili.com/",
                "https://space.bilibili.com/",
                "https://www.xiaohongshu.com/",
                "https://www.tiktok.com/",
            ]
        )
        context.close()
    return cookies


def _cookies_for_platform(platform: str, cookies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """只把目标平台 Cookie 写入其独立历史库，禁止跨平台混存。"""
    allowed_domains = PLATFORM_COOKIE_DOMAINS.get(platform)
    if not allowed_domains:
        raise RuntimeError("未知的登录平台。")
    return [
        item
        for item in cookies
        if any(domain in str(item.get("domain") or "").lower() for domain in allowed_domains)
    ]


def _cookie_jar_from_text(cookie_text: str) -> http.cookiejar.CookieJar:
    """短暂落盘仅供标准库解析，读取后立即删除。"""
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        prefix="cookie-jar-",
        dir=runtime_cookie_dir(),
        delete=False,
    ) as handle:
        handle.write(cookie_text)
        temporary_path = Path(handle.name)
    try:
        jar = http.cookiejar.MozillaCookieJar(str(temporary_path))
        jar.load(ignore_discard=True, ignore_expires=True)
        return jar
    finally:
        temporary_path.unlink(missing_ok=True)


def cookie_jar_from_auth_profile(platform: str | None = None) -> http.cookiejar.CookieJar:
    migrate_legacy_cookie_files()
    if platform in SUPPORTED_LOGIN_PLATFORMS:
        cookie_text = _latest_cookie_text(platform)
        if cookie_text:
            return _cookie_jar_from_text(cookie_text)

    browser_cookies = _load_browser_cookies()
    if platform in SUPPORTED_LOGIN_PLATFORMS:
        browser_cookies = _cookies_for_platform(platform, browser_cookies)
        if browser_cookies:
            _save_platform_cookie_snapshot(platform, browser_cookies)

    jar = http.cookiejar.CookieJar()
    for item in browser_cookies:
        domain = item.get("domain") or ""
        if not domain:
            continue
        cookie = http.cookiejar.Cookie(
            version=0,
            name=str(item.get("name") or ""),
            value=str(item.get("value") or ""),
            port=None,
            port_specified=False,
            domain=domain,
            domain_specified=domain.startswith("."),
            domain_initial_dot=domain.startswith("."),
            path=str(item.get("path") or "/"),
            path_specified=True,
            secure=bool(item.get("secure")),
            expires=int(item["expires"]) if item.get("expires") else None,
            discard=not bool(item.get("expires")),
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False,
        )
        jar.set_cookie(cookie)
    return jar


def export_auth_cookies_txt(platform: str | None = None) -> Path:
    """导出目标平台专属的短时 Cookie 文件，供 yt-dlp 调用后清理。"""
    migrate_legacy_cookie_files()
    if platform not in SUPPORTED_LOGIN_PLATFORMS:
        raise RuntimeError("没有可用于该目标的独立软件内登录 Cookie。")
    cookie_text = _latest_cookie_text(platform)
    if not cookie_text:
        browser_cookies = _cookies_for_platform(platform, _load_browser_cookies())
        if browser_cookies:
            _save_platform_cookie_snapshot(platform, browser_cookies)
        cookie_text = _latest_cookie_text(platform)
    if not cookie_text:
        raise RuntimeError(f"{platform} 尚未保存软件内登录 Cookie。")
    target = runtime_cookie_dir() / f"{RUNTIME_COOKIE_PREFIX}{platform}-{uuid.uuid4().hex}.txt"
    target.write_text(cookie_text, encoding="utf-8")
    _RUNTIME_COOKIE_EXPORTS.add(target)
    return target


atexit.register(cleanup_runtime_cookie_exports)
