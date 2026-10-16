import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QSettings,Qt,QPoint,QEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtMultimedia import QMediaPlayer
from app.media_player import MediaPlayerPage
from app.downloader import find_ffmpeg_dir
from tests.ui_fixtures import isolated_main_window


class HistoryPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')

    def wait_until(self,predicate,seconds=5):
        deadline=time.monotonic()+seconds
        while not predicate() and time.monotonic()<deadline:QTest.qWait(20)
        self.assertTrue(predicate())

    def test_real_video_decodes_controls_seek_and_remembers_position(self):
        tools=find_ffmpeg_dir(Path.cwd())
        if not tools or not (tools/'ffmpeg.exe').is_file():self.skipTest('bundled ffmpeg unavailable')
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);media=root/'video.mp4'
            subprocess.run([str(tools/'ffmpeg.exe'),'-nostdin','-v','error','-f','lavfi','-i',
                'color=c=0x607580:s=640x360:d=60','-c:v','libx264','-pix_fmt','yuv420p','-y',str(media)],
                check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            settings=QSettings(str(root/'playback.ini'),QSettings.IniFormat)
            player=MediaPlayerPage(media,'播放器验收',settings)
            frames=[]
            player.video.videoSink().videoFrameChanged.connect(lambda frame:frames.append(frame.isValid()))
            try:
                player.show()
                self.wait_until(lambda:any(frames))
                self.assertEqual(player.player.duration(),60000)
                player.play_button.click();self.assertEqual(player.player.playbackState(),QMediaPlayer.PausedState)
                player.player.setPosition(20000)
                self.app.processEvents()
                stable_geometry=player.video.geometry()
                QTest.mouseDClick(player.video,Qt.LeftButton,pos=QPoint(player.width()-30,100))
                QTest.mouseRelease(player.video,Qt.LeftButton,pos=QPoint(player.width()-30,100))
                self.assertEqual(player.player.playbackState(),QMediaPlayer.PausedState)
                self.assertEqual(player.player.position(),30000)
                self.assertEqual(player.feedback_right.text(),'快进 10 秒')
                center=player.seek_feedback.geometry().center()
                target=player.video.mapToGlobal(player.video.rect().center())
                self.assertLessEqual(abs(center.x()-target.x()),1)
                self.assertLessEqual(abs(center.y()-target.y()),1)
                self.assertTrue(player.seek_feedback.isVisible())
                QTest.mouseClick(player.video,Qt.LeftButton,pos=QPoint(player.width()-30,100))
                self.assertEqual(player.player.position(),40000)
                self.assertEqual(player.feedback_right.text(),'快进 20 秒')
                self.app.processEvents()
                self.assertEqual(player.video.geometry(),stable_geometry)
                QTest.qWait(player.FEEDBACK_MS+30)
                self.assertFalse(player.seek_feedback.isVisible())
                self.assertEqual(player.video.geometry(),stable_geometry)
                self.assertTrue(player.controls.isVisible())
                QTest.qWait(player.BURST_MS+30)
                QTest.mouseClick(player.video,Qt.LeftButton,pos=QPoint(100,100))
                QTest.qWait(self.app.doubleClickInterval()+30)
                self.assertFalse(player.controls.isVisible())
                QTest.mouseDClick(player.video,Qt.LeftButton,pos=QPoint(player.video.width()//2,100))
                QTest.mouseRelease(player.video,Qt.LeftButton,pos=QPoint(player.video.width()//2,100))
                self.assertEqual(player.player.playbackState(),QMediaPlayer.PlayingState)
                QTest.mouseDClick(player.video,Qt.LeftButton,pos=QPoint(player.video.width()//2,100))
                QTest.mouseRelease(player.video,Qt.LeftButton,pos=QPoint(player.video.width()//2,100))
                self.assertEqual(player.player.playbackState(),QMediaPlayer.PausedState)
                self.assertGreaterEqual(player.player.position(),40000)
                self.assertLess(player.player.position(),41000)
                self.assertEqual(player._gesture_zone(player.video.width()*.29),-1)
                self.assertEqual(player._gesture_zone(player.video.width()*.30),0)
                self.assertEqual(player._gesture_zone(player.video.width()*.69),0)
                self.assertEqual(player._gesture_zone(player.video.width()*.70),1)
                player._set_controls(True);self.app.processEvents()
                QTest.mouseClick(player.seek,Qt.LeftButton,pos=QPoint(player.seek.width()*3//4,player.seek.height()//2))
                self.assertAlmostEqual(player.player.position()/player.player.duration(),.75,delta=.035)
                QTest.mouseClick(player.volume,Qt.LeftButton,pos=QPoint(player.volume.width()//4,player.volume.height()//2))
                self.assertAlmostEqual(player.audio.volume(),.25,delta=.07)
                QTest.mouseClick(player.volume,Qt.LeftButton,pos=QPoint(0,player.volume.height()//2))
                self.assertEqual(player.volume.value(),0)
                QTest.mouseClick(player.volume,Qt.LeftButton,pos=QPoint(player.volume.width()-1,player.volume.height()//2))
                self.assertEqual(player.volume.value(),100)
                # Track clicks can continue into a drag without a second press.
                QTest.mousePress(player.seek,Qt.LeftButton,pos=QPoint(player.seek.width()//4,player.seek.height()//2))
                QTest.mouseRelease(player.seek,Qt.LeftButton,pos=QPoint(player.seek.width()//2,player.seek.height()//2))
                self.assertAlmostEqual(player.player.position()/player.player.duration(),.5,delta=.035)
                player.player.pause();player.seek.setValue(2000);player.seek.sliderReleased.emit()
                self.wait_until(lambda:player.player.position()>=1900)
                player.volume.setValue(45);self.assertAlmostEqual(player.audio.volume(),.45,places=2)
                player.speed.setCurrentIndex(player.speed.findData(1.5));self.assertEqual(player.player.playbackRate(),1.5)
                player.toggle_fullscreen();self.assertTrue(player.isFullScreen())
                QTest.keyClick(player,Qt.Key_Escape);self.assertFalse(player.isFullScreen())
                player.play_button.click()
                self.assertEqual(player.player.playbackState(),QMediaPlayer.PlayingState)
                QTest.mouseMove(player.video,QPoint(80,90))
                geometry=player.video.geometry()
                QTest.qWait(player.CONTROLS_MS+150)
                self.assertFalse(player.controls.isVisible(), 'windowed controls hide after idle timeout')
                self.assertFalse(player.seek.isVisible())
                self.assertEqual(player.video.geometry(),geometry)
                player.toggle_fullscreen()
                QTest.mouseMove(player.video,QPoint(80,90))
                QTest.qWait(player.CONTROLS_MS+150)
                self.assertFalse(player.controls.isVisible())
                QApplication.sendEvent(player.video,QEvent(QEvent.Enter))
                self.assertTrue(player.controls.isVisible(), 'video surface movement must reveal fullscreen controls')
                player._set_controls(False)
                QTest.mouseClick(player.video,Qt.LeftButton,pos=QPoint(80,90))
                QTest.qWait(self.app.doubleClickInterval()+30)
                self.assertTrue(player.controls.isVisible())
                player.toggle_fullscreen()
                self.assertTrue(player.controls.isVisible())
            finally:
                player.close();self.app.processEvents();QTest.qWait(50)
            self.assertGreaterEqual(int(settings.value(player.position_key)),1900)
            resumed=MediaPlayerPage(media,'续播验收',settings)
            try:
                resumed.show();self.wait_until(lambda:resumed.player.position()>=1900)
                self.assertEqual(resumed.player.playbackRate(),1.5)
            finally:
                resumed.close();self.app.processEvents();QTest.qWait(50)

    def test_embedded_fullscreen_returns_to_same_history_and_navigation_releases_media(self):
        window=isolated_main_window();page=window.history_page;page.tools=None
        root=Path(window.settings.fileName()).parent;media=root/'video.mp4';media.write_bytes(b'fixture')
        window.history_store.archive('video',title='作品',url='https://example.test/video',platform='抖音',
            creator='作者',quality='自动识别',files=[str(media)],completed_at=100)
        try:
            window.show();window.history_button.click();self.app.processEvents()
            page.search.setText('作品');page.refresh()
            page.cards['video']['cover'].click();self.app.processEvents()
            player=page.player_page
            self.assertIs(player.window(),window)
            player.fullscreen.click();self.app.processEvents()
            self.assertTrue(window.isFullScreen())
            self.assertFalse(window.sidebar.isVisible())
            self.assertIs(page.player_page,player)
            QTest.keyClick(player,Qt.Key_Escape);self.app.processEvents()
            self.assertFalse(window.isFullScreen())
            self.assertTrue(window.sidebar.isVisible())
            self.assertIs(page.player_page,player)
            player.fullscreen.click();self.app.processEvents()
            self.assertTrue(window.isFullScreen())
            player.close_button.click();self.app.processEvents()
            self.assertFalse(window.isFullScreen())
            self.assertTrue(window.sidebar.isVisible())
            self.assertIsNone(page.player_page)
            self.assertEqual(page.search.text(),'作品')
            self.assertIs(page.content_stack.currentWidget(),page.library)
            self.assertTrue(player.player.source().isEmpty())
            page.cards['video']['cover'].click();self.app.processEvents()
            second=page.player_page
            window._show_history(False);self.app.processEvents()
            self.assertIsNone(page.player_page)
            import shiboken6
            self.assertTrue(not shiboken6.isValid(second) or second.player.source().isEmpty())
        finally:
            window.close();self.app.processEvents();page.pool.waitForDone()

    def test_segment_switch_saves_independent_positions_and_restores_near_end(self):
        import shutil
        tools=find_ffmpeg_dir(Path.cwd())
        if not tools:self.skipTest('bundled ffmpeg unavailable')
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);first=root/'first.mp4';second=root/'second.mp4'
            subprocess.run([str(tools/'ffmpeg.exe'),'-nostdin','-v','error','-f','lavfi','-i',
                'color=c=black:s=320x180:d=60','-c:v','libx264','-pix_fmt','yuv420p','-y',str(first)],
                check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            shutil.copyfile(first,second)
            settings=QSettings(str(root/'playback.ini'),QSettings.IniFormat)
            page=MediaPlayerPage(first,'原作品标题',settings,files=[first,second])
            try:
                page.show();self.wait_until(lambda:page.player.duration()>0)
                page.player.pause();page.player.setPosition(58500)
                key1=page.position_key
                page.segments.setCurrentIndex(1)
                self.wait_until(lambda:page.player.duration()>0 and page._restored)
                page.player.pause();page.player.setPosition(12000)
                key2=page.position_key
                page.segments.setCurrentIndex(0)
                self.wait_until(lambda:page.player.position()>=58500)
                self.assertEqual(int(settings.value(key1)),58500)
                self.assertEqual(int(settings.value(key2)),12000)
                self.assertIn('第 1/2 段',page.caption.toolTip() or page.caption.text())
                page.player.pause();page.player.setPosition(0);page.seek.setValue(0);page.seek.sliderReleased.emit()
                self.assertEqual(int(settings.value(key1)),0)
            finally:
                page.close();self.app.processEvents();QTest.qWait(30)

    def test_unreadable_source_preserves_bookmark(self):
        import hashlib
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);media=root/'missing.mp4'
            settings=QSettings(str(root/'playback.ini'),QSettings.IniFormat)
            key='playback/positions/'+hashlib.sha256(str(media.resolve()).encode()).hexdigest()
            settings.setValue(key,35000)
            page=MediaPlayerPage(media,'缺失文件',settings)
            try:
                page.show();self.wait_until(lambda:page.error_panel.isVisible())
            finally:
                page.close();self.app.processEvents()
            self.assertEqual(int(settings.value(key)),35000)

    def test_cover_uses_internal_player_and_mobile_menu_semantics(self):
        window=isolated_main_window();page=window.history_page;page.tools=None
        root=Path(window.settings.fileName()).parent;media=root/'video.mp4';media.write_bytes(b'fixture')
        window.history_store.archive('video',title='作品',url='https://example.test/video',platform='抖音',
            creator='作者',quality='自动识别',files=[str(media)],completed_at=100)
        try:
            window.show();window.history_button.click();self.app.processEvents()
            record=page.records[0]
            with patch('app.history_page.MediaPlayerPage',wraps=MediaPlayerPage) as player,patch('app.history_page.QDesktopServices.openUrl') as external:
                page.cards[record.id]['cover'].click()
                player.assert_called_once();external.assert_not_called()
                embedded=page.player_page
                self.assertFalse(embedded.isWindow())
                self.assertIs(embedded.window(),window)
                self.assertIs(page.content_stack.currentWidget(),embedded)
                from PySide6.QtWidgets import QLabel
                title=page.findChild(QLabel,'HistoryTitle')
                self.assertLessEqual(abs(title.mapTo(page,QPoint(title.width()//2,0)).x()-page.width()/2),2)
                page.back_button.click()
                self.assertIsNone(page.player_page)
                self.assertIs(page.content_stack.currentWidget(),page.library)
                self.assertIs(window.pages.currentWidget(),page)
            page.cards[record.id]['frame'].findChild(__import__('PySide6.QtWidgets',fromlist=['QPushButton']).QPushButton,'HistoryMore').click()
            self.app.processEvents()
            names=[button.property('actionText') for button in page.action_popup.buttons]
            self.assertEqual(names,['收藏视频','用外部播放器打开','复制原链接','分享原链接','删除历史记录'])
            page.action_popup.close()
            page.platform.click();self.app.processEvents()
            popup=page.platform.popup;self.assertIsNotNone(popup)
            QTest.keyClick(popup,Qt.Key_End);QTest.keyClick(popup,Qt.Key_Return);self.app.processEvents()
            self.assertEqual(page.platform.currentData(),'TikTok')
        finally:
            page.pool.waitForDone();window.close();self.app.processEvents()


if __name__=='__main__':unittest.main()
