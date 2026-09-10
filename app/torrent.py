"""Local torrent import and isolated aria2 jobs. Never rename torrent payloads."""
import base64
import hashlib
import json
import re
import secrets
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import quote, unquote, urlparse, parse_qs
from urllib.request import build_opener, ProxyHandler, Request
from urllib.request import url2pathname


def local_torrent_path(value):
    text = str(value).strip().strip('"')
    if text.lower().startswith('file:'):
        parsed = urlparse(text)
        if parsed.netloc.lower() not in {'', 'localhost'} or parsed.query or parsed.fragment:
            raise ValueError('请使用本机种子文件链接，不支持远程共享地址或带查询参数的链接')
        text = url2pathname(parsed.path)
    if '\x00' in text or not text:
        raise ValueError('种子路径无效')
    return Path(text)


def read_torrent(path, *, with_metadata=False):
    path = local_torrent_path(path)
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('种子文件过大（上限16MB）')
    raw = path.read_bytes()
    pos = 0
    def decode(depth=0):
        nonlocal pos
        if depth > 32 or pos >= len(raw):
            raise ValueError('种子结构无效')
        token = raw[pos:pos+1]
        if token == b'i':
            end = raw.index(b'e', pos)
            value = int(raw[pos+1:end]); pos = end+1
            return value
        if token in (b'l', b'd'):
            pos += 1
            value = [] if token == b'l' else {}
            while pos < len(raw) and raw[pos:pos+1] != b'e':
                item = decode(depth+1)
                if token == b'l':
                    value.append(item)
                else:
                    if not isinstance(item, bytes) or item in value:
                        raise ValueError('种子字典无效')
                    value[item] = decode(depth+1)
            if pos >= len(raw):
                raise ValueError('种子数据不完整')
            pos += 1
            return value
        end = raw.index(b':', pos)
        size = int(raw[pos:end]); pos = end+1
        if size < 0 or pos+size > len(raw):
            raise ValueError('种子长度无效')
        value = raw[pos:pos+size]; pos += size
        return value
    metadata = decode()
    if pos != len(raw) or not isinstance(metadata, dict):
        raise ValueError('种子结构无效')
    info = metadata[b'info']
    def name(value):
        value = value.decode('utf-8', errors='strict')
        if (not value or value in {'.', '..'} or re.search(r'[<>:"/\\|?*\x00-\x1f]', value)
                or value.endswith((' ', '.')) or value.split('.')[0].upper() in
                {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(10)],*[f'LPT{i}' for i in range(10)]}):
            raise ValueError('种子包含不安全或 Windows 不支持的文件名')
        return value
    root = name(info.get(b'name.utf-8', info[b'name']))
    entries = info.get(b'files')
    files = []
    if entries is None:
        entries = [{b'length': info[b'length'], b'path': []}]
    for i, entry in enumerate(entries, 1):
        if b'l' in entry.get(b'attr', b'') or b'symlink path' in entry:
            raise ValueError('不支持种子中的符号链接')
        parts = entry.get(b'path.utf-8', entry[b'path'])
        length = entry[b'length']
        if not isinstance(length, int) or length < 0:
            raise ValueError('种子文件大小无效')
        files.append((i, Path(root, *(name(p) for p in parts)), length))
    if not files or len({str(p).casefold() for _, p, _ in files}) != len(files):
        raise ValueError('种子文件列表为空或文件名冲突')
    return (raw, files, metadata) if with_metadata else (raw, files)


def torrent_job(path, indices, raw):
    return 'torrent:' + quote(str(Path(path).resolve()), safe='') + '?files=' + ','.join(map(str, indices)) + '&sha256=' + hashlib.sha256(raw).hexdigest()


def download_torrent(url, options, progress, cancel, *, diagnostics=False):
    from .downloader import find_aria2c, DownloadResult, raise_if_cancelled
    parsed = urlparse(url)
    path = Path(unquote(parsed.path))
    raw, files, metadata = read_torrent(path, with_metadata=True)
    query = parse_qs(parsed.query)
    if query.get('sha256') != [hashlib.sha256(raw).hexdigest()]:
        raise ValueError('种子文件已变化，请重新智能读取并选择文件')
    selected = {int(i) for i in query['files'][0].split(',')}
    if not selected or not selected <= {i for i, _, _ in files}:
        raise ValueError('种子文件选择无效')
    engine = find_aria2c()
    if not engine:
        raise RuntimeError('缺少 aria2 下载引擎')
    output = (options.output_dir / 'BT' / hashlib.sha256(raw).hexdigest()[:16]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    for _, rel, _ in files:
        if not (output / rel).resolve().is_relative_to(output):
            raise ValueError('输出路径越界')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    secret = secrets.token_hex(24)
    opener = build_opener(ProxyHandler({}))
    def rpc(method, *params):
        request = Request(f'http://127.0.0.1:{port}/jsonrpc', data=json.dumps(
            {'jsonrpc':'2.0','id':'download','method':'aria2.'+method,'params':['token:'+secret,*params]}).encode(), headers={'Content-Type':'application/json'})
        with opener.open(request, timeout=2) as response:
            result = json.load(response)
        if 'error' in result:
            raise RuntimeError('BT引擎错误：'+str(result['error'].get('message')))
        return result['result']
    process = subprocess.Popen([str(engine),'--no-conf','--enable-rpc=true','--rpc-listen-all=false',f'--rpc-listen-port={port}',
        f'--rpc-secret={secret}','--seed-time=0','--enable-dht=true','--enable-dht6=false','--bt-enable-lpd=false',
        f'--dht-file-path={output / ".dht.dat"}',
        '--dht-entry-point=router.bittorrent.com:6881',
        '--enable-peer-exchange=true','--console-log-level=error'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for _ in range(50):
            raise_if_cancelled(cancel)
            if process.poll() is not None:
                raise RuntimeError('BT引擎启动失败')
            try:
                rpc('getVersion'); break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('BT引擎连接超时')
        job_options = {'dir':str(output), 'select-file':','.join(map(str,sorted(selected))),
            'seed-time':'0','check-integrity':'true','continue':'true','allow-overwrite':'false','auto-file-renaming':'false'}
        if not metadata[b'info'].get(b'private'):
            job_options['bt-tracker'] = ','.join([
                'udp://tracker.opentrackr.org:1337/announce',
                'udp://open.demonii.com:1337/announce',
                'udp://tracker.therarbg.to:6969/announce',
            ])
        gid = rpc('addTorrent', base64.b64encode(raw).decode(), [], job_options)
        diagnostic_at = 0
        diagnostic = {}
        while True:
            raise_if_cancelled(cancel)
            state = rpc('tellStatus', gid)
            if state['status'] == 'error':
                raise RuntimeError('BT下载失败：'+state.get('errorMessage', state.get('errorCode','未知错误')))
            total = sum(n for i, _, n in files if i in selected)
            done = sum(int(f['completedLength']) for f in state.get('files',[]) if int(f['index']) in selected)
            speed = int(state.get('downloadSpeed',0))
            connections = int(state.get('connections', 0))
            if diagnostics and time.monotonic() - diagnostic_at >= 10:
                peers = rpc('getPeers', gid)
                diagnostic = {'peer_count': len(peers),
                    'peers_with_pieces': sum(bool(int(p.get('bitfield') or '0', 16)) for p in peers),
                    'peers_choking': sum(p.get('peerChoking') == 'true' for p in peers),
                    'interested_peers': sum(p.get('amInterested') == 'true' for p in peers)}
                diagnostic_at = time.monotonic()
            checking = state.get('verifyIntegrityPending') == 'true' or 'verifiedLength' in state
            waiting = speed == 0 and state['status'] != 'complete'
            progress({'status':'bt_waiting' if waiting else 'downloading','downloaded_bytes':done,'total_bytes':total,
                'reason': '正在校验已有文件' if checking else f'已连接 {connections} 个节点，等待对方提供数据；若长时间无变化，可能暂无可用做种者',
                'connections': connections,
                'seeders': int(state.get('numSeeders', 0)),
                'diagnostic': diagnostic,
                '_speed_str':f'{speed/1024:.1f} KiB/s' if speed else '等待可用节点',
                '_eta_str':f'{int(max(total-done,0)/speed)}秒' if speed else '未知'})
            if state['status'] == 'complete':
                result = [output / rel for i, rel, _ in files if i in selected]
                if any(not (output/rel).is_file() or (output/rel).stat().st_size != n for i,rel,n in files if i in selected):
                    raise RuntimeError('BT下载结果不完整')
                return DownloadResult(result)
            if state['status'] in {'removed','paused'}:
                raise RuntimeError('BT任务意外停止')
            time.sleep(.5)
    finally:
        if process.poll() is None:
            try:
                rpc('shutdown')
            except (OSError, RuntimeError):
                process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()
