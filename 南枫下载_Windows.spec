# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('app/assets', 'app/assets')]
binaries = []
hiddenimports = []
hiddenimports += collect_submodules('playwright')
hiddenimports += collect_submodules('yt_dlp_plugins')
tmp_ret = collect_all('yt_dlp')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('yt_dlp_ejs')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('curl_cffi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

configured_ffmpeg = os.environ.get('NANFENG_FFMPEG_DIR')
ffmpeg_candidates = [
    Path(configured_ffmpeg) if configured_ffmpeg else Path.cwd() / 'tools' / 'ffmpeg',
    Path.cwd() / 'tools' / 'ffmpeg',
    Path.cwd().parent / 'JHlib' / 'ffmpeg',
    Path.cwd().parent / '江湖工具箱' / 'JHlib' / 'ffmpeg',
]
for ffmpeg_dir in ffmpeg_candidates:
    if (ffmpeg_dir / 'ffmpeg.exe').is_file() and (ffmpeg_dir / 'ffprobe.exe').is_file():
        datas.append((str(ffmpeg_dir), 'tools/ffmpeg'))
        break
else:
    raise SystemExit('没有找到 FFmpeg。请设置 NANFENG_FFMPEG_DIR，或放到 tools/ffmpeg。')

local_app_data = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
provider_build = local_app_data / 'NanfengDownloader' / 'bgutil-ytdlp-pot-provider' / 'server' / 'build'
if not provider_build.exists():
    provider_build = local_app_data / 'NanzhufengVideoDownloader' / 'bgutil-ytdlp-pot-provider' / 'server' / 'build'
if provider_build.exists():
    datas.append((str(provider_build), 'tools/bgutil-ytdlp-pot-provider/server/build'))

node_executable = Path(os.environ.get('ProgramFiles', r'C:\\Program Files')) / 'nodejs' / 'node.exe'
if node_executable.exists():
    datas.append((str(node_executable), 'tools/node'))


a = Analysis(
    ['start.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='南枫下载',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app/assets/nanzhufeng-icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='南枫下载',
)
