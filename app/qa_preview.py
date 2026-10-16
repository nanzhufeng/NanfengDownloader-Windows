"""Opt-in release screenshots with synthetic rows and isolated runtime settings."""
import json
import subprocess
from datetime import datetime
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage, QPainter, QPolygonF, QLinearGradient
from PySide6.QtCore import QTimer


def capture_release_preview(window, root):
    from .main import AppSettingsDialog, APP_VERSION, COL_PROGRESS, COL_QUALITY

    window.resize(1820, 1000)
    window.output_edit.setText('D:\\南枫下载')
    window.url_text.setPlainText('https://www.youtube.com/watch?v=preview-demo\nhttps://www.douyin.com/video/1234567890123456789')
    window._add_queue_row('https://www.youtube.com/watch?v=preview-demo', 'YouTube', '示例视频 · 城市慢行与公共空间记录\n沿河步道、街区更新与日常生活观察 1080p.mp4', creator_name='示例频道')
    window._add_queue_row('https://www.douyin.com/video/1234567890123456789', '抖音', '示例作品 · 旅行片段', creator_name='示例作者')
    for number in range(3, 15):
        window._add_queue_row(
            f'https://www.youtube.com/watch?v=preview-demo-{number}',
            'YouTube', f'示例视频 {number:02d} · 城市与自然记录', creator_name='示例频道',
        )
    window._set_status_cell(0, '完成')
    window._set_cell(0, COL_PROGRESS, '100%')
    window.table.cellWidget(0, COL_QUALITY).setCurrentText('1080p 及以下')
    window.status_label.setText('界面预览：脱敏演示数据，未启动下载。')

    def capture_main():
        window.grab().save(str(root / 'workbench.png'))
        # Real local media with synthetic scenery; never read the user's library.
        for index, colors in enumerate((('#a5cbd7', '#5f828c'), ('#e3c5a6', '#9e8c76'))):
            image = QImage(640, 360, QImage.Format_RGB32)
            painter = QPainter(image)
            gradient = QLinearGradient(0, 0, 0, 360)
            gradient.setColorAt(0, QColor(colors[0])); gradient.setColorAt(1, QColor('#edf1ec'))
            painter.fillRect(image.rect(), gradient)
            painter.setPen(QColor(colors[1])); painter.setBrush(QColor(colors[1]))
            painter.drawPolygon(QPolygonF([QPointF(0, 270), QPointF(160, 130), QPointF(320, 250),
                                          QPointF(460, 180), QPointF(640, 250), QPointF(640, 360), QPointF(0, 360)]))
            painter.end()
            still = root / f'scenery-{index}.png'; image.save(str(still))
            media = root / f'scenery-{index}.mp4'
            subprocess.run([str(window.ffmpeg_dir/'ffmpeg.exe'), '-nostdin', '-v', 'error', '-loop', '1',
                            '-i', str(still), '-t', '1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', str(media)],
                           check=True, timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            for item in range(2):
                identity = f'preview-{index}-{item}'
                window.history_store.archive(identity, title=(('城市与自然 · 沿河步道的慢行记录', '旅行片段 · 山间日落与远行日记')[index]),
                    url=f'https://example.test/{identity}', platform=('抖音', 'YouTube')[index], creator='示例作者',
                    quality='自动识别', files=[str(media)], completed_at=datetime(2026, 10, 16-index, 14, 42-item).timestamp())
        window._show_history(True)
        wait_for_history(0)

    def wait_for_history(attempt):
        if window.history_page.jobs:
            if attempt >= 150: raise RuntimeError('History preview metadata timed out')
            QTimer.singleShot(100, lambda: wait_for_history(attempt+1))
            return
        window.grab().save(str(root / 'history.png'))
        window._show_history(False)
        settings = AppSettingsDialog(True, True, False, False, window, retain_queue_history=True)
        settings.resize(760, 620)
        settings.show()

        def capture_settings():
            settings.grab().save(str(root / 'settings.png'))
            settings.close()
            window.quality_combo.setCurrentIndex(3)
            window.quality_combo.showPopup()

            def capture_popup():
                popup = window.quality_combo.view().window()
                popup.grab().save(str(root / 'popup.png'))
                window.quality_combo.hidePopup()
                (root / 'preview.json').write_text(json.dumps({'version': APP_VERSION, 'synthetic': True,
                    'downloads_started': window.worker_thread is not None,
                    'pages': ['workbench.png', 'history.png', 'settings.png', 'popup.png']}, ensure_ascii=False), encoding='utf-8')

            QTimer.singleShot(200, capture_popup)

        QTimer.singleShot(200, capture_settings)

    QTimer.singleShot(200, capture_main)
