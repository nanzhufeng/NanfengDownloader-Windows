"""Embedded history playback. Gesture timings follow Android VideoPlayerGestureController."""
from __future__ import annotations
import hashlib
import time
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QTimer, Signal, QEvent
from PySide6.QtGui import QShortcut, QKeySequence, QDesktopServices, QPainter, QColor, QPen, QIcon, QPixmap, QWindow
from PySide6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStyle, QApplication)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from .action_popup import MenuFilterButton
from .icon_button import IconButton
from .seek_feedback import SeekFeedback
from .click_slider import ClickJumpSlider


def clock(milliseconds):
    seconds = max(0, int(milliseconds)//1000)
    hours, remain = divmod(seconds, 3600)
    minutes, seconds = divmod(remain, 60)
    return f'{hours}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'


def white_icon(style, standard):
    pixmap = style.standardIcon(standard).pixmap(20, 20)
    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), Qt.white)
    painter.end()
    return QIcon(pixmap)


class BufferIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setAccessibleName('视频缓冲中')
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.setInterval(60)
        self.timer.timeout.connect(self._advance)
        self.hide()

    def _advance(self):
        self.angle = (self.angle+24) % 360
        self.update()

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 255, 115), 1.5))
        painter.drawArc(3, 3, 18, 18, self.angle*16, 270*16)


class MediaPlayerPage(QWidget):
    close_requested = Signal()
    fullscreen_changed = Signal(bool)
    STEP_MS = 10_000
    BURST_MS = 600
    CONTROLS_MS = 2500
    FEEDBACK_MS = 800
    BUFFER_MS = 350

    def __init__(self, path: Path, title: str, settings, parent=None, *, files=None, auto_advance=False):
        super().__init__(parent)
        self.settings = settings
        self.path = Path(path)
        self.files = [Path(value) for value in (files or [path])]
        self.auto_advance = auto_advance
        self.original_title = title or self.path.name
        self._restored = self._closing = self._fullscreen = False
        self._last_stored = 0
        self._last_side, self._last_seek, self._steps = None, -10000, 0
        self._ignore_release = False
        self.setObjectName('MediaPlayerPage')
        self.setAttribute(Qt.WA_StyledBackground)
        self.setAttribute(Qt.WA_NativeWindow)
        self.setFocusPolicy(Qt.StrongFocus)
        QApplication.instance().applicationStateChanged.connect(self._application_state)
        self.setMinimumSize(400, 280)
        self.setStyleSheet('''
            QWidget#MediaPlayerPage { background:#000000; border-radius:14px; }
            QWidget#VideoChrome { background:transparent; }
            QFrame#VideoTitle, QFrame#VideoControls { background:#0a0d12; border:none; }
            QFrame#VideoTitle { border-top-left-radius:14px; border-top-right-radius:14px; }
            QFrame#VideoControls { border-bottom-left-radius:14px; border-bottom-right-radius:14px; }
            QLabel { background:transparent; color:white; border:none; }
            QPushButton { background:transparent; color:white; border:none; outline:none;
                min-width:0; min-height:32px; max-height:36px; border-radius:16px; padding:0 8px; }
            QPushButton:hover, QPushButton:focus { background:rgba(255,255,255,36); }
            QPushButton:pressed { background:rgba(255,255,255,55); }
            QPushButton#PlaybackSpeed { background:#2c2c2c; min-width:72px; max-width:72px; padding:0 4px; }
            QPushButton#PlaybackSegments { background:#2c2c2c; min-width:112px; max-width:132px; padding:0 4px; }
            QSlider::groove:horizontal { background:#626977;height:4px;border-radius:2px; }
            QSlider::sub-page:horizontal { background:#f28c28;border-radius:2px; }
            QSlider::handle:horizontal { background:white;border:none;width:12px;margin:-4px 0;border-radius:6px; }
            QComboBox { background:#2c2c2c;color:white;border:none;border-radius:14px;
                min-width:0; min-height:28px; padding:0 8px; }
            QLabel#SeekFeedback { background:rgba(0,0,0,80);color:rgba(255,255,255,180);
                border-radius:12px;padding:6px 10px;font-size:12px; }
        ''')
        # QVideoWidget uses a native QWindowContainer on Windows. Sibling widget
        # overlays are covered by that native surface, so transport lives outside it.
        self.player_layout = QVBoxLayout(self)
        self.player_layout.setContentsMargins(0, 0, 0, 0)
        self.player_layout.setSpacing(0)
        self.video = QVideoWidget()
        self.video.setAspectRatioMode(Qt.KeepAspectRatio)
        self.video.setStyleSheet("background:black;")
        self.video.setMouseTracking(True)
        self.chrome = QWidget()
        self.chrome.setObjectName('VideoChrome')
        self.chrome.setMouseTracking(True)
        self._gesture_targets = {self.video, self.chrome}
        self.video.installEventFilter(self)
        self.chrome.installEventFilter(self)
        QTimer.singleShot(0, self._watch_video_inputs)
        overlay = self.player_layout
        self.title_bar = QFrame()
        self.title_bar.setObjectName('VideoTitle')
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(16, 4, 4, 4)
        self.caption = QLabel()
        self.caption.setMinimumWidth(0)
        self.caption.setTextFormat(Qt.PlainText)
        self.caption.setToolTip(self.original_title)
        title_layout.addWidget(self.caption, 1)
        self.close_button = self._icon_button('关闭视频播放', QStyle.SP_DialogCloseButton, self.close_requested.emit)
        title_layout.addWidget(self.close_button)
        overlay.addWidget(self.title_bar)
        overlay.addWidget(self.video, 1)
        middle = QHBoxLayout(self.chrome)
        middle.setContentsMargins(16, 0, 16, 0)
        self.seek_feedback = SeekFeedback(self.video, self)
        self.feedback_left = self.seek_feedback.left
        self.feedback_right = self.seek_feedback.right
        self.buffering = BufferIndicator()
        middle.addWidget(self.buffering)
        self.chrome.setFixedHeight(32)
        title_layout.insertWidget(1, self.chrome)
        self.title_bar.setFixedHeight(40)
        self.error_panel = QFrame()
        errors = QVBoxLayout(self.error_panel)
        self.error = QLabel()
        self.error.setWordWrap(True)
        errors.addWidget(self.error)
        self.external = QPushButton('用外部播放器打开')
        self.external.clicked.connect(self._external)
        errors.addWidget(self.external, 0, Qt.AlignCenter)
        overlay.addWidget(self.error_panel)
        self.error_panel.hide()
        self.controls = QFrame()
        self.controls.setObjectName('VideoControls')
        self.controls.setFixedHeight(66)
        for strip in (self.title_bar, self.controls):
            policy = strip.sizePolicy()
            policy.setRetainSizeWhenHidden(True)
            strip.setSizePolicy(policy)
        bottom = QVBoxLayout(self.controls)
        bottom.setContentsMargins(12, 8, 12, 8)
        bottom.setSpacing(2)
        self.seek = ClickJumpSlider(Qt.Horizontal)
        self.seek.setRange(0, 0)
        self.seek.setAccessibleName('播放进度')
        bottom.addWidget(self.seek)
        row = QHBoxLayout()
        row.setSpacing(4)
        self.play_button = self._icon_button('播放', QStyle.SP_MediaPlay, self.toggle)
        self.rewind = self._icon_button('快退10秒', QStyle.SP_MediaSeekBackward, lambda: self.seek_by(-self.STEP_MS))
        self.forward = self._icon_button('快进10秒', QStyle.SP_MediaSeekForward, lambda: self.seek_by(self.STEP_MS))
        row.addWidget(self.play_button)
        row.addWidget(self.rewind)
        row.addWidget(self.forward)
        self.time_label = QLabel('00:00 / 00:00')
        row.addWidget(self.time_label)
        row.addStretch()
        self.segments = MenuFilterButton(white_icon(self.style(), QStyle.SP_ArrowDown))
        self.segments.setObjectName('PlaybackSegments')
        self.segments.setProperty('popupAccent', '#f28c28')
        self.segments.setAccessibleName('播放分段')
        for index in range(len(self.files)):
            self.segments.addItem(f'第 {index+1}/{len(self.files)} 段', index)
        self.segments.setVisible(len(self.files) > 1)
        self.segments.currentIndexChanged.connect(self._segment_changed)
        row.addWidget(self.segments)
        self.mute_button = self._icon_button('静音', QStyle.SP_MediaVolume, lambda: self.audio.setMuted(not self.audio.isMuted()))
        row.addWidget(self.mute_button)
        self.volume = ClickJumpSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setFixedWidth(80)
        self.volume.setAccessibleName('音量')
        row.addWidget(self.volume)
        self.speed = MenuFilterButton(white_icon(self.style(), QStyle.SP_ArrowDown))
        for value in (.5, .75, 1., 1.25, 1.5, 2.):
            self.speed.addItem(f'{value:g}×', value)
        self.speed.setObjectName('PlaybackSpeed')
        self.speed.setProperty('popupAccent', '#f28c28')
        self.speed.setAccessibleName('播放速度')
        row.addWidget(self.speed)
        self.fullscreen = self._icon_button('全屏', QStyle.SP_TitleBarMaxButton, self.toggle_fullscreen)
        row.addWidget(self.fullscreen)
        bottom.addLayout(row)
        overlay.addWidget(self.controls)
        self.audio = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.positionChanged.connect(self._position)
        self.player.durationChanged.connect(self._duration)
        self.player.seekableChanged.connect(lambda _: self._restore_position())
        self.player.mediaStatusChanged.connect(self._status)
        self.player.playbackStateChanged.connect(self._state)
        self.player.errorOccurred.connect(self._error)
        self.seek.sliderPressed.connect(lambda: self._set_controls(True))
        self.seek.sliderReleased.connect(self._seek_released)
        self.seek.sliderMoved.connect(lambda value: self.time_label.setText(f'{clock(value)} / {clock(self.player.duration())}'))
        self.volume.valueChanged.connect(lambda value: self.audio.setVolume(value/100))
        self.volume.sliderPressed.connect(lambda: self._set_controls(True))
        self.volume.sliderReleased.connect(lambda: self._set_controls(True))
        self.audio.mutedChanged.connect(self._muted)
        self.speed.currentIndexChanged.connect(lambda _: self.player.setPlaybackRate(self.speed.currentData()))
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._auto_hide)
        self.single_tap = QTimer(self)
        self.single_tap.setSingleShot(True)
        self.single_tap.timeout.connect(lambda: self._set_controls(self.controls.isHidden()))
        self.feedback_timer = QTimer(self)
        self.feedback_timer.setSingleShot(True)
        self.feedback_timer.timeout.connect(self._clear_feedback)
        self.buffer_timer = QTimer(self)
        self.buffer_timer.setSingleShot(True)
        self.buffer_timer.timeout.connect(self._show_buffering)
        self.save_timer = QTimer(self)
        self.save_timer.setInterval(500)
        self.save_timer.timeout.connect(self._snapshot)
        self.save_timer.start()
        for key, action in [('Space', self.toggle), ('Left', lambda: self.seek_by(-self.STEP_MS)),
                            ('Right', lambda: self.seek_by(self.STEP_MS)), ('F', self.toggle_fullscreen),
                            ('M', lambda: self.audio.setMuted(not self.audio.isMuted())),
                            ('Up', lambda: self.volume.setValue(self.volume.value()+5)),
                            ('Down', lambda: self.volume.setValue(self.volume.value()-5)), ('Esc', self._escape)]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(action)
        try: volume = int(settings.value('playback/volume', 70))
        except (TypeError, ValueError): volume = 70
        self.volume.setValue(volume)
        try: speed = float(settings.value('playback/speed', 1.0))
        except (TypeError, ValueError): speed = 1.
        self.speed.setCurrentIndex(max(0, self.speed.findData(speed)) if self.speed.findData(speed) >= 0 else 2)
        self._load(self.path)
        self._set_controls(True)

    def _icon_button(self, text, icon, action):
        button = IconButton(dark=True)
        button.setIcon(white_icon(self.style(), icon))
        button.setFixedSize(36, 36)
        button.setToolTip(text)
        button.setAccessibleName(text)
        button.clicked.connect(action)
        return button

    def _load(self, path):
        self.path = Path(path)
        self.position_key = 'playback/positions/'+hashlib.sha256(str(self.path.resolve()).encode()).hexdigest()
        self._restored = False
        self._last_stored = 0
        self._clear_feedback()
        self._last_side, self._last_seek, self._steps = None, -10000, 0
        self.single_tap.stop()
        self.error_panel.hide()
        self.player.setSource(QUrl.fromLocalFile(str(self.path.resolve())))
        QTimer.singleShot(0, self._autoplay)
        self._caption()

    def _autoplay(self):
        if not self._closing: self.player.play()

    def _segment_changed(self, index):
        if index < 0 or not hasattr(self, 'player'): return
        self._snapshot(flush=True)
        self.player.stop()
        self._load(self.files[index])

    def _caption(self):
        text = self.original_title
        if len(self.files) > 1: text += f' · 第 {self.segments.currentIndex()+1}/{len(self.files)} 段'
        self.caption.setToolTip(text)
        self.caption.setText(self.caption.fontMetrics().elidedText(text, Qt.ElideRight, max(1, self.caption.width())))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._caption()
        self.volume.setVisible(self.width() >= 620)
        if self.seek_feedback.isVisible():
            QTimer.singleShot(0, self.seek_feedback.reposition)
        # Native video stays between the fixed title/footer rows. Their styled
        # antialiased corners replace the jagged binary QRegion window mask.

    def _set_controls(self, visible):
        if self._closing: return
        self.title_bar.setVisible(visible)
        self.controls.setVisible(visible)
        self.hide_timer.stop()
        if visible: self.hide_timer.start(self.CONTROLS_MS)

    def _auto_hide(self):
        popup_open = any(control.popup is not None and control.popup.isVisible() for control in (self.speed, self.segments))
        if self.seek.isSliderDown() or self.volume.isSliderDown() or self.controls.underMouse() or popup_open:
            self.hide_timer.start(self.CONTROLS_MS)
        elif self.player.playbackState() == QMediaPlayer.PlayingState and not self.error_panel.isVisible():
            self._set_controls(False)

    def hideEvent(self, event):
        self._clear_feedback()
        super().hideEvent(event)

    def _watch_video_inputs(self):
        self.window().installEventFilter(self)
        # Windows delivers pointer input to the native video child, not always
        # to QVideoWidget. Watch both without changing the media rendering path.
        for child in self.video.findChildren(QWidget) + self.video.findChildren(QWindow):
            self._gesture_targets.add(child)
            child.installEventFilter(self)
            if isinstance(child, QWidget):
                child.setMouseTracking(True)

    def eventFilter(self, watched, event):
        if watched is self.window() and event.type() in (QEvent.Move, QEvent.Resize, QEvent.WindowStateChange):
            if self.seek_feedback.isVisible():
                QTimer.singleShot(0, self.seek_feedback.reposition)
        if watched is self.window() and event.type() in (QEvent.Hide, QEvent.Close):
            self._clear_feedback()
        if watched in self._gesture_targets:
            if event.type() in (QEvent.MouseMove, QEvent.Enter):
                self._set_controls(True)
            elif event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
                self.single_tap.stop()
                self._ignore_release = True
                zone = self._gesture_zone(event.position().x())
                if zone == 0:
                    self._last_side = None
                    self.toggle()
                else:
                    self._gesture_seek(zone < 0)
                return True
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                if self._ignore_release:
                    self._ignore_release = False
                    return True
                zone = self._gesture_zone(event.position().x())
                left = zone < 0
                if zone != 0 and left == self._last_side and 0 <= time.monotonic()*1000-self._last_seek <= self.BURST_MS:
                    self._gesture_seek(left)
                else:
                    self.single_tap.start(QApplication.doubleClickInterval())
                return True
        return super().eventFilter(watched, event)

    def _gesture_zone(self, x):
        # Broad center pause zone, with the two outer 30% reserved for seeking.
        ratio = x/max(1, self.video.width())
        return -1 if ratio < .30 else 1 if ratio >= .70 else 0

    def _gesture_seek(self, left):
        now = time.monotonic()*1000
        self._steps = self._steps+1 if left == self._last_side and 0 <= now-self._last_seek <= self.BURST_MS else 1
        self._last_side, self._last_seek = left, now
        self._set_controls(True)
        self.seek_by(-self.STEP_MS if left else self.STEP_MS, reveal=False)
        self._clear_feedback()
        label = self.feedback_left if left else self.feedback_right
        label.setText(f'{"快退" if left else "快进"} {self._steps*10} 秒')
        label.show()
        self.seek_feedback.show_centered()
        self.feedback_timer.start(self.FEEDBACK_MS)

    def _clear_feedback(self):
        self.feedback_left.hide()
        self.feedback_right.hide()
        self.seek_feedback.hide()
        self._update_status_strip()

    def _update_status_strip(self):
        visible = not self.buffering.isHidden()
        self.chrome.setVisible(visible)

    def toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState: self.player.pause()
        else:
            if self.player.mediaStatus() == QMediaPlayer.EndOfMedia: self.player.setPosition(0)
            self.player.play()
        self._set_controls(True)
        self._snapshot(flush=True)

    def _seek_released(self):
        self.player.setPosition(self.seek.value())
        self._snapshot(flush=True)
        self._set_controls(True)

    def seek_by(self, delta, reveal=True):
        target = max(0, self.player.position()+delta)
        if self.player.duration() > 0: target = min(self.player.duration(), target)
        self.player.setPosition(target)
        self._snapshot(flush=True)
        if reveal: self._set_controls(True)

    def toggle_fullscreen(self):
        host = self.window()
        if self._fullscreen:
            self._fullscreen = False
            host.setWindowState(self._previous_window_state)
        else:
            self._previous_window_state = host.windowState()
            self._fullscreen = True
            host.showFullScreen()
        self.fullscreen.setToolTip('退出全屏' if self._fullscreen else '全屏')
        self.fullscreen.setAccessibleName(self.fullscreen.toolTip())
        self.fullscreen_changed.emit(self._fullscreen)
        self._set_controls(True)

    def _escape(self):
        if self._fullscreen: self.toggle_fullscreen()
        else: self.close_requested.emit()

    def _state(self, state):
        playing = state == QMediaPlayer.PlayingState
        text = '暂停' if playing else '播放'
        self.play_button.setToolTip(text)
        self.play_button.setAccessibleName(text)
        self.play_button.setIcon(white_icon(self.style(), QStyle.SP_MediaPause if playing else QStyle.SP_MediaPlay))
        if not playing: self._set_controls(True)

    def _muted(self, muted):
        text = '取消静音' if muted else '静音'
        self.mute_button.setToolTip(text)
        self.mute_button.setAccessibleName(text)
        self.mute_button.setIcon(white_icon(self.style(), QStyle.SP_MediaVolumeMuted if muted else QStyle.SP_MediaVolume))

    def _duration(self, duration):
        self.seek.setRange(0, min(duration, 2147483647))
        self._restore_position()
        self._position(self.player.position())

    def _restore_position(self):
        duration = self.player.duration()
        if self._closing or self._restored or duration <= 0 or not self.player.isSeekable(): return
        if self.player.mediaStatus() not in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia): return
        try: position = max(0, int(self.settings.value(self.position_key, 0)))
        except (TypeError, ValueError): position = 0
        self._restored = True
        self._last_stored = min(position, duration)
        if position > 0: self.player.setPosition(min(position, duration))

    def _position(self, position):
        if not self.seek.isSliderDown(): self.seek.setValue(position)
        self.time_label.setText(f'{clock(position)} / {clock(self.player.duration())}')

    def _show_buffering(self):
        self.buffering.show()
        self._update_status_strip()

    def _status(self, status):
        if self._closing: return
        self.buffer_timer.stop()
        self.buffering.hide()
        self._update_status_strip()
        if status in (QMediaPlayer.LoadingMedia, QMediaPlayer.BufferingMedia):
            self.buffer_timer.start(self.BUFFER_MS)
        elif status in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia):
            self._restore_position()
        elif status == QMediaPlayer.EndOfMedia:
            self._snapshot(flush=True, ended=True)
            if self.auto_advance and self.segments.currentIndex()+1 < len(self.files):
                self.segments.setCurrentIndex(self.segments.currentIndex()+1)

    def _error(self, error, message):
        if self._closing or error == QMediaPlayer.NoError: return
        self.buffer_timer.stop()
        self.buffering.hide()
        self._update_status_strip()
        self.error.setText('内置播放器无法读取该文件，请确认文件未损坏，或使用外部播放器打开。')
        self.error_panel.show()
        self._set_controls(True)

    def _external(self):
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path.resolve()))):
            self.error.setText('未能打开外部播放器，请检查系统默认媒体应用。')

    def _application_state(self, state):
        if state != Qt.ApplicationActive and not self._closing:
            self._clear_feedback()
            self._snapshot(flush=True)

    def _snapshot(self, flush=False, ended=False):
        if self._closing: return
        # A missing/not-ready source must never erase a previously stored bookmark.
        if self._restored and self.player.duration() > 0 and self.player.mediaStatus() != QMediaPlayer.InvalidMedia:
            position = 0 if ended or self.player.mediaStatus() == QMediaPlayer.EndOfMedia else self.player.position()
            if flush or abs(position-self._last_stored) >= 1000:
                self.settings.setValue(self.position_key, position)
                self._last_stored = position
        if flush:
            self.settings.setValue('playback/volume', self.volume.value())
            self.settings.setValue('playback/speed', self.speed.currentData())
            self.settings.sync()

    def release(self):
        if self._closing: return
        if self._fullscreen: self.toggle_fullscreen()
        self._snapshot(flush=True)
        self._closing = True
        for timer in (self.save_timer, self.hide_timer, self.single_tap, self.feedback_timer, self.buffer_timer): timer.stop()
        self.buffering.hide()
        self._clear_feedback()
        self.player.stop()
        self.player.setSource(QUrl())

    def closeEvent(self, event):
        self.release()
        super().closeEvent(event)
