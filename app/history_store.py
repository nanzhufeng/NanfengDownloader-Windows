"""Download completion archive. Queue snapshots and media files have separate lifetimes."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path


VIDEO_SUFFIXES = {'.mp4', '.webm', '.mkv', '.mov', '.ts', '.avi', '.m4v'}
AUDIO_SUFFIXES = {'.mp3', '.m4a', '.wav', '.flac', '.ogg', '.opus', '.aac'}


@dataclass(frozen=True)
class HistoryRecord:
    id: str
    title: str
    url: str
    platform: str
    creator: str
    quality: str
    files: tuple[str, ...]
    completed_at: float | None
    favorite: bool
    kind: str
    report: dict = field(default_factory=dict)


def is_placeholder_title(title: str) -> bool:
    return bool(re.fullmatch(r'抖音作品\s*\d+\s*[（(]下载时解析[）)]', title.strip()))


def media_kind(files) -> str:
    suffixes = {Path(path).suffix.lower() for path in files}
    if suffixes and suffixes <= VIDEO_SUFFIXES:
        return 'video'
    if suffixes and suffixes <= AUDIO_SUFFIXES:
        return 'audio'
    return 'other'


def file_availability(files) -> tuple[str, int | None]:
    """Only confirmed missing files on reachable volumes may be cleaned up."""
    if not files:
        return 'unavailable', None
    present = missing = 0
    total = 0
    for value in files:
        path = Path(value)
        try:
            stat = path.stat()
            if not path.is_file():
                missing += 1
            else:
                present += 1
                total += stat.st_size
        except FileNotFoundError:
            # A disconnected drive/share is not evidence that a file was deleted.
            try:
                if not Path(path.anchor).is_dir():
                    return 'unavailable', None
            except OSError:
                return 'unavailable', None
            missing += 1
        except OSError:
            return 'unavailable', None
    if missing == len(files):
        return 'missing', 0
    return ('partial', None) if missing else ('present', total)


class HistoryStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            if db.execute('PRAGMA user_version').fetchone()[0] > 2:
                raise ValueError('历史数据库来自更高版本，请使用更新的软件打开。')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS history (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL,
                    platform TEXT NOT NULL, creator TEXT NOT NULL, quality TEXT NOT NULL,
                    files TEXT NOT NULL, completed_at REAL, favorite INTEGER NOT NULL DEFAULT 0,
                    kind TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS history_time ON history(completed_at DESC);
                CREATE TABLE IF NOT EXISTS archive_receipts (id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
            ''')
            if 'report' not in {row[1] for row in db.execute('PRAGMA table_info(history)')}:
                db.execute("ALTER TABLE history ADD COLUMN report TEXT NOT NULL DEFAULT '{}'")
            db.execute('PRAGMA user_version=2')

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def correct_placeholder_titles(self, url: str, title: str, creator: str = '') -> int:
        """Repair only generated placeholders for the exact source; never alter files or user titles."""
        if not title.strip() or is_placeholder_title(title):
            return 0
        updated = 0
        with self._connect() as db:
            for row in db.execute('SELECT id,title,creator FROM history WHERE url=?', (url,)).fetchall():
                if is_placeholder_title(row['title']):
                    updated += db.execute('UPDATE history SET title=?,creator=? WHERE id=? AND title=?',
                        (title, creator or row['creator'], row['id'], row['title'])).rowcount
        return updated

    def archive(self, attempt_id: str, *, title: str, url: str, platform: str,
                creator: str, quality: str, files, completed_at: float | None, report: dict | None = None) -> None:
        if not isinstance(attempt_id, str) or not attempt_id.strip():
            raise ValueError('下载记录缺少稳定标识，无法归档。')
        files = tuple(dict.fromkeys(str(Path(path).absolute()) for path in files))
        if not files or not url.strip():
            raise ValueError('没有准确的输出文件或原链接，无法归档下载历史。')
        with self._connect() as db:
            if not db.execute('INSERT OR IGNORE INTO archive_receipts VALUES (?)', (attempt_id,)).rowcount:
                return
            db.execute('INSERT INTO history (id,title,url,platform,creator,quality,files,completed_at,favorite,kind,report) VALUES (?,?,?,?,?,?,?,?,0,?,?)',
                       (attempt_id, title, url, platform, creator, quality,
                        json.dumps(files, ensure_ascii=False), completed_at, media_kind(files), json.dumps(report or {},allow_nan=False)))

    def query(self, query='', platform=None, days=None, favorites=False, now=None,
              limit=48, offset=0) -> list[HistoryRecord]:
        conditions, args = [], []
        if query.strip():
            # instr treats %, _ and backslashes literally and avoids LIKE wildcards.
            conditions.append('(instr(lower(title),?) OR instr(lower(creator),?) OR instr(lower(url),?))')
            args.extend([query.strip().lower()] * 3)
        if platform:
            conditions.append('platform=?')
            args.append(platform)
        if days is not None:
            conditions.append('completed_at>=?')
            args.append((time.time() if now is None else now) - days * 86400)
        if favorites:
            conditions.append("favorite=1 AND kind='video'")
        where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        sql = 'SELECT * FROM history' + where + ' ORDER BY completed_at DESC, id DESC LIMIT ? OFFSET ?'
        with self._connect() as db:
            rows = db.execute(sql, (*args, limit, offset)).fetchall()
        return [HistoryRecord(row['id'], row['title'], row['url'], row['platform'],
                              row['creator'], row['quality'], tuple(json.loads(row['files'])),
                              row['completed_at'], bool(row['favorite']), row['kind'],json.loads(row['report'])) for row in rows]

    def platforms(self):
        with self._connect() as db:
            return [row[0] for row in db.execute('SELECT DISTINCT platform FROM history ORDER BY platform')]

    def set_favorite(self, record_id: str, desired: bool):
        with self._connect() as db:
            db.execute("UPDATE history SET favorite=? WHERE id=? AND kind='video'", (int(desired), record_id))

    def delete(self, ids):
        with self._connect() as db:
            db.executemany('DELETE FROM history WHERE id=?', ((value,) for value in ids))

    def archive_completed_queue_row(self, row: dict) -> bool:
        """Safely retire a saved completion, using the same receipt as legacy import."""
        if not isinstance(row, dict) or row.get('status') != '完成':
            return False
        files = row.get('output_files')
        if not isinstance(files, list) or not files or not row.get('url'):
            return False
        if not all(isinstance(path, str) and path.strip() and Path(path).is_absolute() for path in files):
            return False
        legacy_id = 'legacy-' + hashlib.sha256(json.dumps([row['url'], files], ensure_ascii=False).encode()).hexdigest()
        history_id = row.get('history_id')
        self.archive(history_id if isinstance(history_id, str) and history_id else legacy_id,
                     title=str(row.get('source_title') or row.get('title') or '未命名'),
                     url=str(row['url']), platform=str(row.get('platform') or '未知'),
                     creator=str(row.get('creator') or ''), quality=str(row.get('quality') or ''),
                     files=files, completed_at=None)
        return True

    def import_queue(self, payload: dict):
        """Idempotent legacy import; preserve unknown completion times explicitly."""
        if payload.get('version') != 1 or not isinstance(payload.get('rows'), list):
            return
        with self._connect() as db:
            if db.execute("SELECT 1 FROM metadata WHERE key='legacy_imported'").fetchone():
                return
        for row in payload['rows']:
            self.archive_completed_queue_row(row)
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('legacy_imported','1')")
