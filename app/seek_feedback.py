"""Transient, input-transparent video feedback above Windows native video surfaces."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect


class SeekFeedback(QWidget):
    def __init__(self, video, parent):
        # A non-activating owned tooltip surface can cover QVideoWidget's native
        # QWindow without moving or replacing the video, unlike widget siblings.
        super().__init__(parent, Qt.ToolTip | Qt.FramelessWindowHint |
                         Qt.NoDropShadowWindowHint | Qt.WindowTransparentForInput |
                         Qt.WindowDoesNotAcceptFocus)
        self.video = video
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAccessibleName('播放跳转提示')
        self.setObjectName('SeekFeedbackOverlay')
        self.setStyleSheet('QWidget#SeekFeedbackOverlay { background:transparent; border:none; } '
                           'QLabel { color:white; background:transparent; border:none; '
                           'font-size:14px; padding:0; }')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.left = QLabel()
        self.right = QLabel()
        for label in (self.left, self.right):
            label.setAlignment(Qt.AlignCenter)
            shadow = QGraphicsDropShadowEffect(label)
            shadow.setBlurRadius(10)
            shadow.setOffset(0, 2)
            shadow.setColor(QColor(0, 0, 0, 180))
            label.setGraphicsEffect(shadow)
            label.hide()
            layout.addWidget(label)
        self.hide()

    def show_centered(self):
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()

    def reposition(self):
        center = self.video.mapToGlobal(self.video.rect().center())
        self.move(center.x()-self.width()//2, center.y()-self.height()//2)
