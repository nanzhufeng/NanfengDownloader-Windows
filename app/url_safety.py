"""外部链接的主机名校验，禁止把 URL 任意位置的域名文本当作可信来源。"""

from __future__ import annotations

from urllib.parse import urlparse


def url_host(url: str) -> str:
    """返回规范化主机名；不可信或非 HTTP 链接返回空字符串。"""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return ""
    if parsed.scheme.lower() not in {"http", "https"}:
        return ""
    return (parsed.hostname or "").casefold().rstrip(".")


def url_host_matches(url: str, *domains: str) -> bool:
    """仅匹配精确域名或其合法子域名，拒绝路径、参数和伪造后缀匹配。"""
    host = url_host(url)
    return bool(host) and any(host == domain or host.endswith(f".{domain}") for domain in domains)
