"""Windows history workbench; database truth lives in HistoryStore."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, QUrl, Signal, QSettings, QSize
from PySide6.QtGui import QDesktopServices, QPixmap, QFont, QIcon, QPainter, QColor
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QPushButton, QScrollArea, QStyle,
    QVBoxLayout, QWidget, QSizePolicy, QStackedWidget,
)

from .action_popup import ActionPopup, MenuFilterButton
from .icon_button import IconButton
from .ui_icons import vector_shell_icon
from .history_selection import HistorySelectionCircle
from .history_cover import HistoryCoverButton
from .media_player import MediaPlayerPage
from .history_store import HistoryRecord, HistoryStore, file_availability
from .windows_shell import reveal_file_in_explorer


STATES = {'present': '已完成', 'partial': '部分文件缺失', 'missing': '文件已不存在',
          'unavailable': '暂时无法访问'}
PAGE_STYLE = '''
QWidget#HistoryPage { background: transparent; color: #2d3033; }
QFrame#HistoryToolbar { background:transparent; border:none; }
QFrame#HistoryCard { background: #ffffff; border: none; border-radius: 14px; }
QLabel { background: transparent; color: #2d3033; }
QLabel#HistoryDay { font-size: 14px; font-weight: 600; }
QLabel#HistoryTitle { font-size: 20px; font-weight: 600; }
QLabel#HistorySecondary { color: #707579; font-size: 12px; }
QLabel#HistoryFeedback { color: #707579; }
QLineEdit { background: #ffffff; color:#303438; border: none; border-radius: 20px; padding: 0 12px; font-size:13px; }
QLineEdit QToolButton { background:transparent; border:none; border-radius:10px; padding:0;
    min-width:20px; max-width:20px; min-height:20px; max-height:20px; }
QLineEdit QToolButton:hover, QLineEdit QToolButton:focus { background:#e8eaed; }
QLineEdit QToolButton:pressed { background:#dce0e6; }
QPushButton, QComboBox { background: #f0f0f0; color: #41484c; border: none;
    border-radius: 18px; min-height: 36px; padding: 0 14px; }
QPushButton:hover { background: #e5e5e5; }
QPushButton:pressed, QPushButton:checked { background: #e2e5e3; color:#287452; }
QPushButton:focus { background: #e5e7e5; }
QPushButton#HistoryFilter, QPushButton#HistoryFavorites { background:#ffffff; }
QPushButton#HistoryFilter QLabel { color:#536777; background:transparent; }
QPushButton#HistoryFilter:hover, QPushButton#HistoryFavorites:hover { background:#e8eaed; }
QPushButton#HistoryFavorites:checked { background:#e4e6eb; color:#5b62a4; }
QPushButton#HistorySelectAction { background:#e5e7ec; color:#5c66a1; min-width:0; padding:0 12px; }
QPushButton#HistorySelectAction:hover, QPushButton#HistorySelectAction:focus { background:#dce0e8; }
QPushButton#HistorySelectDelete { background:#e5e7ec; color:#bd4944; min-width:0; padding:0 12px; }
QPushButton#HistorySelectDelete:disabled { color:#a2a7ad; background:#e9eaed; }
QPushButton#HistorySelectionCircle { min-width:0; max-width:32px; min-height:28px; max-height:28px; padding:0; background:transparent; }
QPushButton#HistorySelectionCircle:hover, QPushButton#HistorySelectionCircle:focus { background:transparent; }
QPushButton#HistoryBack { background:transparent; color:#555d62; padding:0; min-width:36px; max-width:36px; min-height:36px; max-height:36px; border-radius:18px; }
QPushButton#HistoryBack:hover, QPushButton#HistoryBack:focus { background:#e5e5e5; }
QPushButton#HistoryBack:pressed { background:#dce0e4; }
QPushButton#HistoryManageAction { background:#e5e7ec; color:#bd4944; padding:0 12px; min-width:0; }
QPushButton#HistoryManageAction:hover, QPushButton#HistoryManageAction:focus { background:#eeeeee; }
QPushButton:disabled { color: #9aa3ad; background: #f4f4f4; }
QPushButton#HistoryMedia { background: transparent; border-radius: 10px; padding: 0;
    min-width: 116px; max-width: 116px; min-height: 84px; max-height: 84px; }
QPushButton#HistoryName { background: transparent; border-radius: 6px; padding: 0;
    text-align: left; font-weight: 600; min-height:0; max-height:36px; }
QPushButton#HistoryName:hover, QPushButton#HistoryName:focus { background: #eeeeee; }
QPushButton#HistoryMore { background:transparent; padding:0; border-radius:18px; min-width:36px;
    max-width:36px; min-height:36px; max-height:36px; }
QPushButton#HistoryMore:hover, QPushButton#HistoryMore:focus { background:#dfe4e8; }
QPushButton#HistoryMore:pressed { background:#d3dbe1; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QScrollArea#HistoryScroll QScrollBar:vertical { background:transparent; border:none; width:12px; margin:4px 0; }
QScrollArea#HistoryScroll QScrollBar:horizontal { background:transparent; border:none; height:12px; margin:0 4px; }
QScrollArea#HistoryScroll QScrollBar::handle { background:#b2b7be; border:none; border-radius:4px; }
QScrollArea#HistoryScroll QScrollBar::handle:vertical { min-height:40px; margin:0 2px; }
QScrollArea#HistoryScroll QScrollBar::handle:horizontal { min-width:40px; margin:2px 0; }
QScrollArea#HistoryScroll QScrollBar::handle:hover { background:#969da6; }
QScrollArea#HistoryScroll QScrollBar::handle:pressed { background:#7c8590; }
QScrollArea#HistoryScroll QScrollBar::add-line, QScrollArea#HistoryScroll QScrollBar::sub-line {
    background:transparent; border:none; width:0; height:0;
}
QScrollArea#HistoryScroll QScrollBar::add-page, QScrollArea#HistoryScroll QScrollBar::sub-page {
    background:transparent; border:none;
}
QScrollArea#HistoryScroll::corner { background:transparent; border:none; }
'''
DIALOG_STYLE = '''
QDialog { background: #ffffff; color: #303438; }
QLabel, QListWidget { color: #303438; background: white; border: none; }
QPushButton { background: #eeeeee; color: #41484c; border: none; padding: 0 16px;
    min-height: 36px; border-radius: 18px; }
QPushButton:hover, QPushButton:focus { background: #e1e5ea; }
QListWidget::item { padding: 8px; border-radius: 6px; }
QListWidget::item:selected { background: #eeeeee; color: #233342; }
'''


def shell_icon(code: int, color='#667782') -> QIcon:
    """Prefer scalable interface vectors; retain the native font for uncommon symbols."""
    vector = vector_shell_icon(code, color)
    if vector is not None: return vector
    image = QPixmap(20, 20); image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setFont(QFont('Segoe MDL2 Assets', 12))
    painter.setPen(QColor(color)); painter.drawText(image.rect(), Qt.AlignCenter, chr(code))
    painter.end()
    return QIcon(image)


class ResultSignals(QObject):
    done = Signal(object)


class Work(QRunnable):
    def __init__(self, operation):
        super().__init__()
        self.operation = operation
        self.signals = ResultSignals()

    def run(self):
        try:
            value = self.operation()
        except Exception as exc:
            value = exc
        self.signals.done.emit(value)


def _tool(path: Path | None, name: str) -> Path | None:
    if path is None:
        return None
    candidate = path / (name + '.exe' if os.name == 'nt' else name)
    return candidate if candidate.is_file() else None


def _run_tool(args, *, timeout, cancel=None):
    if cancel is not None and cancel.is_set():
        raise InterruptedError('媒体读取已取消')
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)
    deadline = time.monotonic() + timeout
    try:
        while True:
            if cancel is not None and cancel.is_set():
                raise InterruptedError('媒体读取已取消')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(args, timeout)
            try:
                stdout, stderr = process.communicate(timeout=min(remaining, 0.1))
                if process.returncode:
                    raise subprocess.CalledProcessError(process.returncode, args, stdout, stderr)
                return stdout
            except subprocess.TimeoutExpired:
                continue
    finally:
        if process.poll() is None: process.kill()
        process.communicate()


def read_media(record: HistoryRecord, tools: Path | None, cache: Path, cancel=None):
    state, size = file_availability(record.files)
    result = {'state': state, 'size': size, 'duration': None, 'resolution': None, 'thumbnail': None}
    if state != 'present':
        return result
    probe = _tool(tools, 'ffprobe')
    durations, resolutions = [], []
    if probe:
        # A large multi-file task must not occupy a probe worker indefinitely.
        for source in record.files[:8]:
            if cancel is not None and cancel.is_set(): return result
            try:
                output = _run_tool(
                    [str(probe), '-v', 'error', '-show_entries',
                     'format=duration:stream=codec_type,width,height', '-of', 'json', source],
                    timeout=8, cancel=cancel,
                )
                info = json.loads(output)
                durations.append(float(info['format']['duration']))
                resolutions.extend((s.get('width'), s.get('height')) for s in info.get('streams', [])
                                   if s.get('codec_type') == 'video' and s.get('width') and s.get('height'))
            except (OSError, subprocess.SubprocessError, ValueError, KeyError):
                durations = []
                break
        if len(durations) == len(record.files):
            result['duration'] = sum(durations)
        if resolutions and len(record.files) <= 8 and len(set(resolutions)) == 1:
            result['resolution'] = '%d×%d' % resolutions[0]
    ffmpeg = _tool(tools, 'ffmpeg')
    if cancel is not None and cancel.is_set(): return result
    if ffmpeg and record.kind == 'video':
        cache.mkdir(parents=True, exist_ok=True)
        identity = [(path, Path(path).stat().st_mtime_ns, Path(path).stat().st_size) for path in record.files]
        digest = hashlib.sha256(json.dumps(['cover-fill-v2', identity]).encode()).hexdigest()
        target = cache / (digest + '.png')
        if not target.is_file():
            try:
                _run_tool([str(ffmpeg), '-nostdin', '-v', 'error', '-i', record.files[0],
                                '-frames:v', '1', '-vf', 'scale=348:252:force_original_aspect_ratio=increase,crop=348:252,setsar=1',
                                '-y', str(target)], timeout=12, cancel=cancel)
            except (OSError, subprocess.SubprocessError):
                target.unlink(missing_ok=True)
        if target.is_file():
            result['thumbnail'] = str(target)
        # Only this reconstructible thumbnail cache is bounded; media is never pruned.
        cached = sorted(cache.glob('*.png'), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in cached[256:]:
            old.unlink(missing_ok=True)
    return result


def size_text(size):
    if size is None:
        return '大小未知'
    for suffix in ('B', 'KB', 'MB', 'GB', 'TB'):
        if size < 1024 or suffix == 'TB':
            return f'{size:.1f} {suffix}'
        size /= 1024


def duration_text(value):
    if value is None:
        return '时长未知'
    seconds = int(value)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'


class HistoryPage(QWidget):
    back_requested = Signal()
    playback_fullscreen_changed = Signal(bool)

    def __init__(self, store: HistoryStore | None, tools: Path | None, parent=None, settings=None):
        super().__init__(parent)
        self.setObjectName('HistoryPage')
        self.setStyleSheet(PAGE_STYLE)
        self.store, self.tools = store, tools
        self.settings = settings if settings is not None else (QSettings(str(store.path.parent/'playback.ini'),QSettings.IniFormat) if store else QSettings())
        self.player_page = None
        self.action_popup = None
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.cache = store.path.parent / 'history-thumbnails' if store else Path()
        self.records, self.cards, self.metadata, self.jobs = [], {}, {}, {}
        self.selected = set()
        self.selection_mode = False
        self.generation = 0
        self.columns = 2
        self._busy = False
        self._dirty = True
        self._closing = False
        self.cancelled = threading.Event()
        self.elide_timer = QTimer(self)
        self.elide_timer.setSingleShot(True)
        self.elide_timer.timeout.connect(self._update_card_texts)
        self._build()

    def _button(self, text, callback, parent_layout):
        button = QPushButton(text)
        button.clicked.connect(callback)
        parent_layout.addWidget(button)
        return button

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        heading = QGridLayout()
        for column in range(3): heading.setColumnStretch(column, 1)
        back=IconButton()
        back.clicked.connect(self._back)
        back.setObjectName('HistoryBack');back.setIcon(shell_icon(0xE72B))
        back.setFixedSize(36, 36)
        back.setToolTip('返回下载');back.setAccessibleName('返回下载')
        self.back_button = back
        title = QLabel('下载历史'); title.setObjectName('HistoryTitle')
        heading.addWidget(back, 0, 0, Qt.AlignLeft)
        title.setAlignment(Qt.AlignCenter)
        heading.addWidget(title, 0, 1)
        self.heading_widget = QWidget()
        self.heading_widget.setLayout(heading)
        root.addWidget(self.heading_widget)
        self.content_stack = QStackedWidget()
        self.library = QWidget()
        self.content_stack.addWidget(self.library)
        root.addWidget(self.content_stack, 1)
        root = QVBoxLayout(self.library)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        toolbar = QFrame(); toolbar.setObjectName('HistoryToolbar')
        toolbar_layout=QVBoxLayout(toolbar);toolbar_layout.setContentsMargins(0,0,0,0);toolbar_layout.setSpacing(6)
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索标题、博主或原链接')
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName('搜索下载历史')
        self.search.setFixedHeight(40)
        self.search.addAction(shell_icon(0xE721), QLineEdit.LeadingPosition)
        toolbar_layout.addWidget(self.search)
        filters = QHBoxLayout()
        self.platform = MenuFilterButton(shell_icon(0xE70D)); self.platform.addItem('全部平台', None)
        self.platform.setMinimumWidth(120)
        self.period = MenuFilterButton(shell_icon(0xE70D))
        for label, days in [('全部时间', None), ('近 7 天', 7), ('近 30 天', 30)]:
            self.period.addItem(label, days)
        self.period.setMinimumWidth(120)
        filters.addWidget(self.platform); filters.addWidget(self.period)
        self.favorites = QPushButton('收藏'); self.favorites.setObjectName('HistoryFavorites'); self.favorites.setCheckable(True)
        self.favorites.setIcon(shell_icon(0xE734))
        self.favorites.toggled.connect(self._favorites_changed)
        filters.addWidget(self.favorites); filters.addStretch()
        self.bulk = self._button('批量删除', self._toggle_selection, filters)
        self.cleanup = self._button('清理失效', self._scan_missing, filters)
        self.cleanup.setIcon(shell_icon(0xE74D, '#bd4944'))
        self.cleanup.setIconSize(QSize(20, 20))
        self.bulk.setObjectName('HistoryManageAction');self.cleanup.setObjectName('HistoryManageAction')
        self.selection_bar = QWidget(); selection = QHBoxLayout(self.selection_bar)
        selection.setContentsMargins(0, 0, 0, 0); selection.setSpacing(6)
        self.selection_count = QLabel('已选 0 项'); selection.addWidget(self.selection_count)
        cancel = self._button('取消选择', self._toggle_selection, selection)
        cancel.setObjectName('HistorySelectAction'); cancel.setIcon(shell_icon(0xE8BB))
        self.select_all = self._button('全选', self._select_filtered, selection)
        self.select_all.setObjectName('HistorySelectAction'); self.select_all.setIcon(shell_icon(0xE73A))
        self.select_all.setToolTip('全选当前筛选结果')
        self.delete_selected = self._button('删除所选', self._delete_selected, selection)
        self.delete_selected.setObjectName('HistorySelectDelete'); self.delete_selected.setIcon(shell_icon(0xE74D))
        self.selection_bar.hide(); filters.addWidget(self.selection_bar)
        self.bulk.setIcon(shell_icon(0xE74D))
        toolbar_layout.addLayout(filters)
        root.addWidget(toolbar)
        self.feedback = QLabel(); self.feedback.setObjectName('HistoryFeedback')
        self.feedback.setWordWrap(True);self.feedback.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        policy=self.feedback.sizePolicy();policy.setRetainSizeWhenHidden(True);self.feedback.setSizePolicy(policy)
        heading.addWidget(self.feedback, 0, 2)
        self.scroll = QScrollArea(); self.scroll.setObjectName('HistoryScroll')
        self.scroll.setFrameShape(QFrame.NoFrame); self.scroll.setWidgetResizable(True)
        self.body = QWidget(); self.grid = QGridLayout(self.body)
        self.grid.setContentsMargins(0, 0, 0, 0); self.grid.setSpacing(12)
        self.grid.setColumnStretch(0, 1); self.grid.setColumnStretch(1, 1)
        self.scroll.setWidget(self.body); root.addWidget(self.scroll, 1)
        self.load_more = QPushButton('加载更多'); self.load_more.clicked.connect(self._load_more)
        root.addWidget(self.load_more, alignment=Qt.AlignCenter)
        self.debounce = QTimer(self); self.debounce.setSingleShot(True); self.debounce.setInterval(180)
        self.debounce.timeout.connect(self.refresh)
        self.search.textChanged.connect(self._schedule_refresh)
        self.platform.currentIndexChanged.connect(self._filters_changed)
        self.period.currentIndexChanged.connect(self._filters_changed)

    def notify_changed(self):
        self._dirty = True
        if self.isVisible():
            self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        if self._dirty:
            self.refresh()
        else:
            generation = self.generation
            for record in self.records:
                self._work(lambda record=record: file_availability(record.files),
                           lambda result, id=record.id: self._availability_ready(id, result)
                           if generation == self.generation else None)

    def _availability_ready(self, id, result):
        if isinstance(result, Exception): return
        state, size = result
        previous = self.metadata.get(id, {})
        if previous.get('state') != state:
            self._media_ready(id, {'state': state, 'size': size})

    def shutdown(self):
        self._close_player()
        self._closing = True
        self.cancelled.set()
        self.generation += 1
        self.pool.clear()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        columns = 2 if self.width() >= 900 else 1
        if self.columns != columns:
            self.columns = columns
            self._layout_cards()
        self.elide_timer.start(0)

    def _update_card_texts(self):
        for id in self.cards: self._card_text(id)

    def _schedule_refresh(self):
        self.selected.clear()
        self.debounce.start()

    def _filters_changed(self):
        self.selected.clear()
        self.refresh()

    def _favorites_changed(self, checked):
        self.favorites.setIcon(shell_icon(0xE735 if checked else 0xE734))
        if checked:
            self.search.blockSignals(True); self.search.clear(); self.search.blockSignals(False)
            self.platform.blockSignals(True); self.platform.setCurrentIndex(0); self.platform.blockSignals(False)
            self.period.blockSignals(True); self.period.setCurrentIndex(0); self.period.blockSignals(False)
        self.selected.clear(); self.selection_mode = False; self.selection_bar.hide()
        self.cleanup.setVisible(not checked)
        self.refresh()

    def _query(self, **kwargs):
        return self.store.query(query=self.search.text(), platform=self.platform.currentData(),
                                days=self.period.currentData(), favorites=self.favorites.isChecked(), **kwargs)

    def refresh(self):
        self.debounce.stop()
        self._dirty = False
        if self.store is None:
            self.feedback.setText('下载历史暂时不可用，请检查本地数据目录的可写权限后重启。')
            self.load_more.hide(); self.bulk.setEnabled(False); self.cleanup.setEnabled(False)
            return
        old_scroll = self.scroll.verticalScrollBar().value()
        try:
            current = self.platform.currentData()
            self.platform.blockSignals(True)
            self.platform.clear(); self.platform.addItem('全部平台', None)
            platforms = list(dict.fromkeys(['抖音', 'YouTube', '哔哩哔哩', '小红书', 'TikTok'] + self.store.platforms()))
            for platform in platforms: self.platform.addItem(platform, platform)
            self.platform.setCurrentIndex(max(0, self.platform.findData(current)))
            self.platform.blockSignals(False)
            records = self._query(limit=48)
        except (OSError, sqlite3.Error) as exc:
            self.platform.blockSignals(False)
            self.feedback.setText(f'读取历史记录失败：{exc}')
            return
        if records and records == self.records and len(self.cards) == len(records):
            # Keep unchanged card trees, decoded covers and scroll position.
            # Filter changes can still clear selection without rebuilding them.
            for id, card in self.cards.items():
                previous = card['check'].blockSignals(True)
                card['check'].setChecked(id in self.selected)
                card['check'].set_selection_mode(self.selection_mode)
                card['check'].blockSignals(previous)
            self.feedback.setText('')
            self._update_selection()
            return
        self.generation += 1
        self.records = records
        for widgets in self.cards.values(): widgets['frame'].deleteLater()
        self.cards.clear()
        for record in records: self._create_card(record)
        self._layout_cards()
        self.scroll.verticalScrollBar().setValue(old_scroll)
        self.load_more.setVisible(len(records) == 48)
        self.bulk.setEnabled(bool(records))
        self.feedback.setText('' if records else ('暂无匹配的收藏视频' if self.favorites.isChecked() else
                              '还没有下载历史，完成的下载会归档到这里。' if not self.search.text() and not self.platform.currentData() and not self.period.currentData() else '没有匹配结果'))
        self._update_selection()

    def _load_more(self):
        try:
            records = self._query(limit=48, offset=len(self.records))
        except Exception as exc:
            self.feedback.setText(f'读取历史记录失败：{exc}'); return
        self.records.extend(records)
        for record in records: self._create_card(record)
        self._layout_cards(); self.load_more.setVisible(len(records) == 48)

    def _layout_cards(self):
        if not hasattr(self, 'grid'): return
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget and widget.objectName() == 'HistoryDay': widget.deleteLater()
        self.grid.setColumnStretch(1, 1 if self.columns == 2 else 0)
        row, column, last_day = -1, 0, None
        for record in self.records:
            day = datetime.fromtimestamp(record.completed_at).strftime('%Y-%m-%d') if record.completed_at is not None else '较早记录 · 完成时间未知'
            if day != last_day:
                row += 1
                heading = QLabel(day); heading.setObjectName('HistoryDay')
                self.grid.addWidget(heading, row, 0, 1, self.columns)
                row += 1; column = 0; last_day = day
            frame = self.cards[record.id]['frame']
            self.grid.addWidget(frame, row, column)
            column += 1
            if column == self.columns: row += 1; column = 0
        for index in range(self.grid.rowCount()): self.grid.setRowStretch(index, 0)
        self.grid.setRowStretch(row + 1, 1)

    def _create_card(self, record):
        frame = QWidget(); frame.setObjectName('HistoryTimelineItem'); frame.setMinimumWidth(0)
        frame.setFixedHeight(120)
        outer=QHBoxLayout(frame);outer.setContentsMargins(0,0,0,0);outer.setSpacing(8)
        time_group = QWidget(); time_group.setObjectName('HistoryTimeColumn')
        time_group.setFixedSize(44,78)
        time_column = QVBoxLayout(time_group)
        time_column.setContentsMargins(0,0,0,0);time_column.setSpacing(6)
        time_column.setAlignment(Qt.AlignCenter)
        check = HistorySelectionCircle(record.title)
        check.set_selection_mode(self.selection_mode); check.setChecked(record.id in self.selected)
        check.toggled.connect(lambda checked, id=record.id: self._selected_changed(id, checked))
        time_column.addWidget(check, 0, Qt.AlignHCenter)
        time_label = QLabel(datetime.fromtimestamp(record.completed_at).strftime('%H:%M') if record.completed_at is not None else '—')
        time_label.setObjectName('HistorySecondary');time_label.setAlignment(Qt.AlignCenter); time_label.setFixedHeight(18); time_column.addWidget(time_label)
        outer.addWidget(time_group,0,Qt.AlignVCenter)
        card_surface=QFrame();card_surface.setObjectName('HistoryCard');outer.addWidget(card_surface,1)
        layout=QHBoxLayout(card_surface);layout.setContentsMargins(14,12,12,12);layout.setSpacing(12)
        cover = HistoryCoverButton(record.kind in {'audio','video'}); cover.setFixedSize(116, 84)
        cover.setAccessibleName('播放：' + record.title); cover.setToolTip('在软件内播放')
        cover.clicked.connect(lambda: self._open(record)); layout.addWidget(cover)
        text = QVBoxLayout(); text.setSpacing(5)
        source_row=QHBoxLayout();source_row.setSpacing(6)
        source_icon=QLabel();source_icon.setFixedSize(16,16)
        platform_key={'抖音':'douyin','YouTube':'youtube','哔哩哔哩':'bilibili','小红书':'xiaohongshu','TikTok':'tiktok'}.get(record.platform)
        if platform_key:source_icon.setPixmap(QIcon(str(Path(__file__).parent/'assets'/'platforms'/f'{platform_key}.svg')).pixmap(16,16))
        source_row.addWidget(source_icon)
        platform = QLabel(record.platform);platform.setObjectName('HistorySecondary');source_row.addWidget(platform)
        if record.favorite:
            star=QLabel();star.setPixmap(shell_icon(0xE735,'#5a9479').pixmap(14,14));source_row.addWidget(star)
        source_row.addStretch();text.addLayout(source_row)
        title = QPushButton(); title.setObjectName('HistoryName'); title.setMinimumWidth(0)
        title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        title.setToolTip(record.title); title.setAccessibleName(record.title)
        title.clicked.connect(lambda: self._details(record)); text.addWidget(title)
        subtitle = QLabel(); subtitle.setObjectName('HistorySecondary')
        subtitle.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        text.addWidget(subtitle)
        state = QLabel('正在检查本地文件'); state.setObjectName('HistorySecondary'); text.addWidget(state)
        text.addStretch(); layout.addLayout(text, 1)
        more = IconButton(); more.setObjectName('HistoryMore')
        more.setIcon(shell_icon(0xE712, '#43515d')); more.setIconSize(QSize(24,24))
        more.setAccessibleName('更多操作'); more.setToolTip('更多操作')
        more.clicked.connect(lambda: self._menu(record, more)); layout.addWidget(more, 0, Qt.AlignTop)
        self.cards[record.id] = dict(frame=frame, cover=cover, title=title, subtitle=subtitle,
                                     state=state, check=check, record=record,status_mark=check)
        # Defer elision until the card has its actual layout width.
        self.elide_timer.start(0)
        if record.id in self.metadata:
            self._media_ready(record.id, self.metadata[record.id])
        else:
            generation = self.generation
            self._work(lambda: read_media(record, self.tools, self.cache, self.cancelled) if generation == self.generation else None,
                       lambda result, id=record.id: self._media_ready(id, result) if generation == self.generation else None)

    def _card_text(self, id):
        card = self.cards.get(id)
        if not card: return
        record = card['record']
        width = max(40, card['title'].width())
        metrics = card['title'].fontMetrics()
        title = ' '.join(record.title.split())
        if metrics.horizontalAdvance(title) > width:
            lo, hi = 0, len(title)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if metrics.horizontalAdvance(title[:mid]) <= width: lo = mid
                else: hi = mid - 1
            title = title[:lo] + '\n' + metrics.elidedText(title[lo:], Qt.ElideRight, width)
        card['title'].setText(title)
        meta = self.metadata.get(id, {})
        info = ' · '.join(value for value in (record.creator, meta.get('resolution'), duration_text(meta.get('duration')), size_text(meta.get('size'))) if value)
        card['subtitle'].setText(card['subtitle'].fontMetrics().elidedText(info, Qt.ElideRight, width))
        card['subtitle'].setToolTip(info)

    def _media_ready(self, id, result):
        if isinstance(result, Exception):
            result = {'state': 'unavailable', 'size': None}
        self.metadata[id] = result
        card = self.cards.get(id)
        if not card: return
        card['state'].setText(STATES[result['state']])
        card['check'].set_status(result['state'])
        card['state'].setStyleSheet('color: #278575;' if result['state']=='present' else 'color: #916039;')
        if result.get('thumbnail'):
            pixmap = QPixmap(result['thumbnail'])
            if not pixmap.isNull():
                card['cover'].set_cover(pixmap)
        self._card_text(id)

    def _work(self, operation, callback):
        if self._closing: return
        work = Work(operation); key = id(work); self.jobs[key] = work
        def finished(result):
            self.jobs.pop(key, None)
            if not self._closing: callback(result)
        work.signals.done.connect(finished)
        self.pool.start(work)

    def _toggle_selection(self):
        self.selection_mode = not self.selection_mode
        self.selected.clear()
        for card in self.cards.values():
            previous=card['check'].blockSignals(True)
            card['check'].setChecked(False); card['check'].set_selection_mode(self.selection_mode)
            card['check'].blockSignals(previous)
        self._update_selection()

    def _selected_changed(self, id, checked):
        if checked: self.selected.add(id)
        else: self.selected.discard(id)
        self._update_selection()

    def _update_selection(self):
        self.selection_count.setText(f'已选 {len(self.selected)} 项')
        self.delete_selected.setEnabled(bool(self.selected))
        self.selection_bar.setVisible(self.selection_mode)
        self.bulk.setVisible(not self.selection_mode)
        self.cleanup.setVisible(not self.selection_mode and not self.favorites.isChecked())

    def _select_filtered(self):
        try:
            self.selected = {record.id for record in self._query(limit=-1)}
            for card in self.cards.values(): card['check'].setChecked(card['record'].id in self.selected)
            self._update_selection()
        except Exception as exc: self.feedback.setText(f'读取记录失败：{exc}')

    def _dialog(self, title):
        dialog = QDialog(self); dialog.setWindowTitle(title); dialog.setMinimumWidth(460)
        dialog.setStyleSheet(DIALOG_STYLE)
        layout = QVBoxLayout(dialog); layout.setContentsMargins(24, 24, 24, 24); layout.setSpacing(14)
        heading = QLabel(title); heading.setWordWrap(True); layout.addWidget(heading)
        return dialog, layout

    def _confirm(self, title, text, action):
        dialog, layout = self._dialog(title)
        label = QLabel(text); label.setWordWrap(True); layout.addWidget(label)
        buttons = QHBoxLayout(); buttons.addStretch()
        cancel = self._button('取消', dialog.reject, buttons); cancel.setDefault(True)
        self._button(action, dialog.accept, buttons); layout.addLayout(buttons)
        return dialog.exec() == QDialog.Accepted

    def _delete_selected(self): self._delete(list(self.selected))

    def _delete(self, ids):
        if not ids: return
        if not self._confirm('删除历史记录？', f'将删除 {len(ids)} 条历史记录，不会删除已保存的媒体文件。', '删除记录'): return
        try: self.store.delete(ids)
        except Exception as exc: self.feedback.setText(f'删除失败：{exc}'); return
        self.selected.clear(); self.refresh(); self.feedback.setText(f'已删除 {len(ids)} 条记录，媒体文件已保留。')

    def _scan_missing(self):
        if self._busy or self.store is None: return
        self._busy = True; self.cleanup.setEnabled(False); self.feedback.setText('正在检查本地文件…')
        def scan():
            missing = []; offset = 0
            while True:
                records = self.store.query(limit=250, offset=offset)
                if not records: break
                missing.extend(record for record in records if file_availability(record.files)[0] == 'missing')
                offset += len(records)
            return missing
        self._work(scan, self._scan_ready)

    def _scan_ready(self, result):
        self._busy = False; self.cleanup.setEnabled(True)
        if isinstance(result, Exception): self.feedback.setText(f'检查失败：{result}'); return
        if not result: self.feedback.setText('没有确认失效的记录；暂时无法访问和部分缺失的记录已保留。'); return
        if not self._confirm('清理失效记录？', f'检测到 {len(result)} 条记录的本地文件已不存在。只删除这些记录，不删除媒体文件。', '清理记录'):
            self.feedback.setText('已取消清理。'); return
        self._busy = True; self.cleanup.setEnabled(False)
        def clean():
            ids = [record.id for record in result if file_availability(record.files)[0] == 'missing']
            self.store.delete(ids)
            return len(ids)
        def finished(count):
            self._busy = False; self.cleanup.setEnabled(True); self.refresh()
            self.feedback.setText(f'清理失败：{count}' if isinstance(count, Exception) else f'已清理 {count} 条失效记录。')
        self._work(clean, finished)

    def _menu(self, record, button):
        entries=[]
        if record.kind == 'video':
            entries.append(('取消收藏' if record.favorite else '收藏视频',shell_icon(0xE735 if record.favorite else 0xE734),lambda:self._favorite(record),False,True))
        entries.append(('用外部播放器打开',shell_icon(0xE8A7),lambda:self._open(record,external=True),False,True))
        entries.append(('复制原链接',shell_icon(0xE8C8),lambda:self._copy(record),False,True))
        if getattr(record,'report',{}).get('network_bytes',0)>0:
            entries.append(('查看下载报告',shell_icon(0xE9D9),lambda:self._report(record),False,True))
        entries.append(('分享原链接',shell_icon(0xE72D),lambda:self._share(record),False,True))
        entries.extend([None,('删除历史记录',shell_icon(0xE74D),lambda:self._delete([record.id]),False,True)])
        self.action_popup=ActionPopup(entries,self)
        popup=self.action_popup
        popup.destroyed.connect(lambda:self._popup_destroyed(popup))
        self.action_popup.open_for(button)

    def _popup_destroyed(self,popup):
        if self.action_popup is popup:self.action_popup=None

    def _back(self):
        if self.player_page is not None:
            self._close_player()
        else:
            self.back_requested.emit()

    def _close_player(self):
        page = self.player_page
        if page is None: return
        self.player_page = None
        page.release()
        self.content_stack.setCurrentWidget(self.library)
        self.content_stack.removeWidget(page)
        page.deleteLater()
        self.heading_widget.show()
        self.feedback.show()
        self.back_button.setToolTip('返回下载')
        self.back_button.setAccessibleName('返回下载')
        self.back_button.setFocus(Qt.OtherFocusReason)

    def _playback_fullscreen(self, enabled):
        self.heading_widget.setVisible(not enabled)
        self.playback_fullscreen_changed.emit(enabled)

    def hideEvent(self, event):
        if self.isHidden():
            self._close_player()
        elif self.player_page is not None:
            self.player_page._snapshot(flush=True)
        super().hideEvent(event)

    def _favorite(self, record):
        try: self.store.set_favorite(record.id, not record.favorite)
        except Exception as exc: self.feedback.setText(f'收藏保存失败：{exc}'); return
        self.selected.clear(); self.refresh(); self.feedback.setText('已取消收藏。' if record.favorite else '已收藏视频。')

    def _copy(self, record):
        QApplication.clipboard().setText(record.url); self.feedback.setText('已复制原链接。')

    def _choose_file(self, record):
        if len(record.files) == 1: return record.files[0]
        dialog, layout = self._dialog('选择文件')
        files = QListWidget(); files.addItems([Path(path).name for path in record.files]); files.setCurrentRow(0)
        layout.addWidget(files)
        buttons = QHBoxLayout(); self._button('取消', dialog.reject, buttons); self._button('打开所选', dialog.accept, buttons)
        layout.addLayout(buttons); files.itemDoubleClicked.connect(lambda _: dialog.accept())
        return record.files[files.currentRow()] if dialog.exec() == QDialog.Accepted and files.currentRow() >= 0 else None

    def _open(self, record, reveal=False, external=False):
        internal = not reveal and not external and record.kind in {'audio', 'video'}
        path = record.files[0] if internal and record.files else self._choose_file(record)
        if not path: return
        try:
            if not Path(path).is_file():
                self.metadata.pop(record.id, None); self.refresh()
                self.feedback.setText('文件不存在或暂时无法访问，请检查文件是否移动、磁盘是否连接。'); return
            if reveal: reveal_file_in_explorer(Path(path))
            elif external or record.kind not in {'audio','video'}:
                if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
                    self.feedback.setText('无法打开文件，请检查系统默认播放器或文件关联。'); return
            else:
                self._close_player()
                page = MediaPlayerPage(Path(path), record.title, self.settings, self.content_stack,
                                       files=record.files, auto_advance=record.kind == 'audio')
                self.player_page = page
                page.close_requested.connect(self._close_player)
                page.fullscreen_changed.connect(self._playback_fullscreen)
                self.content_stack.addWidget(page)
                self.content_stack.setCurrentWidget(page)
                self.feedback.hide()
                self.back_button.setToolTip('返回历史')
                self.back_button.setAccessibleName('返回历史')
                page.setFocus(Qt.OtherFocusReason)
                return
            self.feedback.setText('已定位文件。' if reveal else '已交给系统默认应用打开。')
        except OSError as exc: self.feedback.setText(f'打开文件失败：{exc}')

    def _details(self, record):
        dialog, layout = self._dialog('下载详情')
        meta = self.metadata.get(record.id, {})
        completed = datetime.fromtimestamp(record.completed_at).strftime('%Y-%m-%d %H:%M:%S') if record.completed_at is not None else '未知（旧记录）'
        text = '\n\n'.join([record.title, f'平台：{record.platform}    博主：{record.creator or "未知"}',
                            f'完成时间：{completed}', f'请求画质：{record.quality or "未知"}',
                            f'实际分辨率：{meta.get("resolution") or "未知"}',
                            f'时长：{duration_text(meta.get("duration"))}    大小：{size_text(meta.get("size"))}',
                            f'原链接：{record.url}', '文件：\n' + '\n'.join(record.files)])
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        label = QLabel(text); label.setTextFormat(Qt.PlainText);label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        scroll.setWidget(label); layout.addWidget(scroll); dialog.resize(620, 540)
        buttons = QHBoxLayout()
        self._button('播放', lambda: (dialog.accept(), self._open(record)), buttons)
        self._button('定位文件', lambda: self._open(record, True), buttons)
        self._button('复制原链接', lambda: self._copy(record), buttons)
        self._button('关闭', dialog.accept, buttons); layout.addLayout(buttons)
        dialog.exec()

    def _share(self, record):
        dialog,layout=self._dialog('分享原链接')
        title=QLabel(record.title);title.setTextFormat(Qt.PlainText);title.setWordWrap(True);layout.addWidget(title)
        link=QLineEdit(record.url);link.setReadOnly(True);link.setAccessibleName('分享链接');layout.addWidget(link)
        hint=QLabel('复制后可粘贴到微信、浏览器或其他应用。');hint.setWordWrap(True);layout.addWidget(hint)
        buttons=QHBoxLayout()
        def copy():self._copy(record);dialog.accept()
        self._button('复制分享链接',copy,buttons);self._button('关闭',dialog.reject,buttons);layout.addLayout(buttons)
        dialog.exec()

    def _report(self, record):
        report=record.report
        dialog,layout=self._dialog('下载报告')
        values=[('网络传输',size_text(report.get('network_bytes'))),
                ('总用时',f'{report.get("elapsed",0):.1f} 秒'),
                ('平均传输速度',size_text(report.get('average_speed'))+'/s'),
                ('峰值速度',size_text(report.get('peak_speed'))+'/s'),
                ('最高并发连接',str(report.get('connections',1))),('重试次数',str(report.get('retries',0)))]
        for label,value in values:layout.addWidget(QLabel(f'{label}：{value}'))
        self._button('关闭',dialog.accept,layout);dialog.exec()
