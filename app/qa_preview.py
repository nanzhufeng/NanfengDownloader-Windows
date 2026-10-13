"""Opt-in release screenshots with synthetic rows and isolated runtime settings."""
import json
from PySide6.QtCore import QTimer


def capture_release_preview(window, root):
    from .main import AppSettingsDialog, APP_VERSION, COL_PROGRESS, COL_QUALITY

    window.resize(1820, 1000)
    window.output_edit.setText('D:\\南枫下载')
    window.url_text.setPlainText('https://www.youtube.com/watch?v=preview-demo\nhttps://www.douyin.com/video/1234567890123456789')
    window._add_queue_row('https://www.youtube.com/watch?v=preview-demo', 'YouTube', '示例视频 · 城市慢行与公共空间记录\n沿河步道、街区更新与日常生活观察 1080p.mp4', creator_name='示例频道')
    window._add_queue_row('https://www.douyin.com/video/1234567890123456789', '抖音', '示例作品 · 旅行片段', creator_name='示例作者')
    window._set_status_cell(0, '完成')
    window._set_cell(0, COL_PROGRESS, '100%')
    window.table.cellWidget(0, COL_QUALITY).setCurrentText('1080p 及以下')
    window.status_label.setText('界面预览：脱敏演示数据，未启动下载。')

    def capture_main():
        window.grab().save(str(root / 'workbench.png'))
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
                (root / 'preview.json').write_text(json.dumps({'version': APP_VERSION, 'synthetic': True, 'downloads_started': window.worker_thread is not None, 'pages': ['workbench.png', 'settings.png', 'popup.png']}, ensure_ascii=False), encoding='utf-8')

            QTimer.singleShot(200, capture_popup)

        QTimer.singleShot(200, capture_settings)

    QTimer.singleShot(200, capture_main)
