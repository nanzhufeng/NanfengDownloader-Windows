"""Explicit user-approved quality fallback; original files are never overwritten."""
import json
import re
import subprocess
import tempfile
from pathlib import Path
from dataclasses import replace


class QualityChoiceCancelled(Exception):
    """Cancel this item only, not the batch."""


def verify_output_resolution(result, options, progress):
    """Probe actual output for every platform, including dedicated downloaders."""
    if not options.ffmpeg_dir or options.quality == '仅音频 MP3':
        return result
    limit = {'720p 及以下':720, '1080p 及以下':1080, '360p 及以下':360}.get(options.quality)
    verified_files = []
    for path in result.files:
        probe = subprocess.run([str(options.ffmpeg_dir / 'ffprobe.exe'), '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height', '-of', 'json', str(path)], capture_output=True, check=True, timeout=30,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        streams = json.loads(probe.stdout).get('streams', [])
        if not streams:
            raise RuntimeError('最终文件缺少可验证的视频尺寸，未标记画质成功。')
        w, h = int(streams[0]['width']), int(streams[0]['height'])
        if limit and min(w,h) > limit:
            raise RuntimeError(f'源站没有符合“{options.quality}”的输出，实际为{min(w,h)}p；原文件保留。')
        if not result.skipped:
            from .downloader import _unique_path
            stem = re.sub(r'\s*\[?(?:\d{3,4}|未知)p\]?$', '', path.stem)
            named = path.with_name(f'{stem} {min(w,h)}p{path.suffix}')
            if named != path:
                named = _unique_path(named)
                path.rename(named)
                path = named
        verified_files.append(path)
        progress({'status':'finished', 'filename':str(path), 'info_dict':{'width':w,'height':h}, 'verified_resolution':True})
    return replace(result, files=verified_files)


def download_with_quality_choice(url, options, progress, cancel, choose, download=None):
    if url.startswith('torrent:'):
        from .torrent import download_torrent
        return download_torrent(url, options, progress, cancel)
    from .downloader import download_url, DownloadStopped
    from yt_dlp.utils import DownloadError
    download_url = download or download_url
    if options.quality in {"自动识别", "自动识别原画质"}:
        options = replace(options, quality="最佳画质")
    try:
        return verify_output_resolution(download_url(url, options, progress, cancel), options, progress)
    except (RuntimeError, DownloadError) as exc:
        if isinstance(exc, DownloadStopped):
            raise
        if not ("Requested format is not available" in str(exc) or "源站没有符合" in str(exc)):
            raise
        limit = {"720p 及以下": 720, "1080p 及以下": 1080, "360p 及以下": 360}.get(options.quality)
        if not limit:
            raise
        choice = choose(options.quality)
        if cancel():
            raise DownloadStopped("已取消画质选择")
        if choice not in {"original", "convert"}:
            raise QualityChoiceCancelled("已取消本项")
        if choice == "convert" and not options.ffmpeg_dir:
            raise RuntimeError("转换画质需要 FFmpeg，未开始下载。")
        result = download_url(url, replace(options, quality="最佳画质"), progress, cancel)
        if choice == "original":
            return verify_output_resolution(result, replace(options, quality='最佳画质'), progress)
        from .downloader import DownloadResult
        return DownloadResult([convert_quality(p, limit, options.ffmpeg_dir, progress, cancel) for p in result.files])


def convert_quality(source, limit, ffmpeg_dir, progress, cancel):
    from .downloader import raise_if_cancelled, _unique_path
    from .media_validation import validate_media_file
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    def dimensions(path):
        result = subprocess.run([str(ffmpeg_dir / 'ffprobe.exe'), '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height', '-of', 'json', str(path)], capture_output=True, check=True, timeout=30, creationflags=flags)
        stream = json.loads(result.stdout)['streams'][0]
        return int(stream['width']), int(stream['height'])
    raise_if_cancelled(cancel)
    width, height = dimensions(source)
    if min(width, height) <= limit:
        return source
    progress({'status': 'converting', 'reason': f'正在转为{limit}p；原文件保留，转码可能比下载更久'})
    # Keep exact temporary output ownership so cancellation cannot affect user files.
    with tempfile.TemporaryDirectory(prefix='.quality-', dir=source.parent) as temp:
        output = Path(temp) / 'converted.mp4'
        scale = f'scale=-2:{limit}' if width >= height else f'scale={limit}:-2'
        with (Path(temp) / 'error.log').open('wb') as log:
            process = subprocess.Popen([str(ffmpeg_dir / 'ffmpeg.exe'), '-nostdin', '-v', 'error', '-i', str(source),
                '-map', '0:v:0', '-map', '0:a?', '-vf', scale, '-c:v', 'libx264', '-preset', 'fast',
                '-crf', '20', '-c:a', 'aac', '-movflags', '+faststart', str(output)], stdout=subprocess.DEVNULL, stderr=log, creationflags=flags)
            try:
                while process.poll() is None:
                    raise_if_cancelled(cancel)
                    try:
                        process.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        pass
                if process.returncode:
                    raise RuntimeError('画质转换失败，原文件已保留。')
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
        validate_media_file(output, ffmpeg_dir)
        w, h = dimensions(output)
        if min(w, h) > limit:
            raise RuntimeError('转码分辨率校验失败，原文件已保留。')
        stem = re.sub(r'\s*\[?\d{3,4}p\]?$', '', source.stem)
        target = _unique_path(source.with_name(f'{stem} {min(w,h)}p.mp4'))
        output.rename(target)
        progress({'status': 'finished', 'filename': str(target), 'info_dict': {'width': w, 'height': h}})
        return target
