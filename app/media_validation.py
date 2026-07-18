from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


MEDIA_FILE_SUFFIXES = {".mp4", ".webm", ".mkv", ".mov", ".m4a", ".mp3", ".ts"}


class InvalidMediaError(RuntimeError):
    """下载结果不是可识别的音视频文件。"""


@dataclass(frozen=True)
class MediaProbe:
    path: Path
    size: int
    method: str
    format_name: str = ""
    duration: float | None = None


def _is_obvious_text_payload(header: bytes) -> bool:
    normalized = header.lstrip().lower()
    return normalized.startswith(
        (
            b"<!doctype html",
            b"<html",
            b"<?xml",
            b"{\"",
            b"{'",
            b"[{",
        )
    )


def looks_like_media_header(header: bytes) -> bool:
    if not header or _is_obvious_text_payload(header):
        return False
    return (
        b"ftyp" in header[:128]
        or header.startswith(b"\x1aE\xdf\xa3")
        or header.startswith((b"ID3", b"OggS", b"fLaC", b"RIFF"))
        or (len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0)
        or (len(header) >= 189 and header[0] == 0x47 and header[188] == 0x47)
    )


def is_probable_existing_media(path: Path) -> bool:
    """用于批量预索引的快速本地检查，不启动 ffprobe。"""
    try:
        if path.suffix.lower() not in MEDIA_FILE_SUFFIXES or path.stat().st_size <= 0:
            return False
        with path.open("rb") as file_obj:
            header = file_obj.read(512)
    except OSError:
        return False

    if _is_obvious_text_payload(header):
        return False
    if looks_like_media_header(header):
        return True
    return path.stat().st_size >= 64 * 1024


def _ffprobe_executable(ffmpeg_dir: Path | None) -> Path | None:
    if not ffmpeg_dir:
        return None
    name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    candidate = ffmpeg_dir / name
    return candidate if candidate.is_file() else None


def validate_media_file(
    path: Path,
    ffmpeg_dir: Path | None = None,
    *,
    timeout_seconds: float = 20.0,
) -> MediaProbe:
    """验证最终输出；可用时以 ffprobe 为准，否则使用严格文件头检查。"""
    try:
        size = path.stat().st_size
        with path.open("rb") as file_obj:
            header = file_obj.read(512)
    except OSError as exc:
        raise InvalidMediaError(f"无法读取下载结果：{path.name}") from exc

    if size <= 0:
        raise InvalidMediaError(f"下载结果为空文件：{path.name}")
    if path.suffix.lower() not in MEDIA_FILE_SUFFIXES:
        raise InvalidMediaError(f"下载结果不是支持的媒体格式：{path.name}")
    if _is_obvious_text_payload(header):
        raise InvalidMediaError(f"平台返回的是网页或接口文本，不是媒体：{path.name}")

    ffprobe = _ffprobe_executable(ffmpeg_dir)
    if not ffprobe:
        if not looks_like_media_header(header):
            raise InvalidMediaError(f"下载结果没有可识别的媒体文件头：{path.name}")
        return MediaProbe(path=path, size=size, method="header")

    command = [
        str(ffprobe),
        "-v",
        "error",
        "-show_entries",
        "format=format_name,duration,size",
        "-of",
        "json",
        str(path),
    ]
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            creationflags=creationflags,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InvalidMediaError(f"ffprobe 无法验证下载结果：{path.name}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip()[:240]
        raise InvalidMediaError(f"下载结果无法被 ffprobe 识别：{path.name}。{detail}")

    try:
        format_info = json.loads(completed.stdout).get("format") or {}
        format_name = str(format_info.get("format_name") or "").strip()
        duration_text = str(format_info.get("duration") or "").strip()
        duration = float(duration_text) if duration_text else None
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InvalidMediaError(f"ffprobe 返回了无法解析的媒体信息：{path.name}") from exc

    if not format_name or duration is None or duration <= 0:
        raise InvalidMediaError(f"下载结果缺少有效的媒体格式或时长：{path.name}")
    return MediaProbe(
        path=path,
        size=size,
        method="ffprobe",
        format_name=format_name,
        duration=duration,
    )
