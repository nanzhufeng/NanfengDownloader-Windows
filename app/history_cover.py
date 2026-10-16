"""History thumbnail: cover crop, rounded clipping and one play affordance."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QPushButton, QStyle


class HistoryCoverButton(QPushButton):
    def __init__(self, playable=True, parent=None):
        super().__init__(parent)
        self.playable = playable
        self.cover = QPixmap()
        self.setObjectName('HistoryMedia')

    def set_cover(self, pixmap):
        self.cover = pixmap
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        bounds = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(bounds, 10, 10)
        painter.setClipPath(path)
        if self.cover.isNull():
            painter.fillRect(bounds, QColor('#171a1e'))
        else:
            width, height = self.cover.width(), self.cover.height()
            ratio = bounds.width()/bounds.height()
            if width/height > ratio:
                cropped = height*ratio
                source = QRectF((width-cropped)/2, 0, cropped, height)
            else:
                cropped = width/ratio
                source = QRectF(0, (height-cropped)/2, width, cropped)
            painter.drawPixmap(bounds, self.cover, source)
        if self.underMouse():
            painter.fillRect(bounds, QColor(0, 0, 0, 22))
        center = bounds.center()
        if self.playable:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 225))
            painter.drawEllipse(center, 10, 10)
            triangle = QPainterPath()
            triangle.moveTo(center+QPointF(-2, -4))
            triangle.lineTo(center+QPointF(4, 0))
            triangle.lineTo(center+QPointF(-2, 4))
            triangle.closeSubpath()
            painter.fillPath(triangle, QColor('#28323b'))
        else:
            self.style().standardIcon(QStyle.SP_FileIcon).paint(
                painter, int(center.x()-12), int(center.y()-12), 24, 24)
        if self.hasFocus():
            painter.setPen(QColor(255, 255, 255, 180))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(bounds.adjusted(1, 1, -1, -1), 9, 9)
