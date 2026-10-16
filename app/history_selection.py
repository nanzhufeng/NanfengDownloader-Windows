"""One timeline circle serves both file status and bulk selection."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QPushButton


class HistorySelectionCircle(QPushButton):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.selection_mode = False
        self.status = 'checking'
        self.setObjectName('HistorySelectionCircle')
        self.setFixedSize(32, 28)
        self.setAccessibleName('选择历史记录：' + title)
        self.set_selection_mode(False)

    def set_selection_mode(self, enabled):
        self.selection_mode = enabled
        self.setCheckable(enabled)
        self.setFocusPolicy(Qt.StrongFocus if enabled else Qt.NoFocus)
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
        self.update()

    def set_status(self, status):
        self.status = status
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width()/2, self.height()/2
        if self.selection_mode and (self.underMouse() or self.hasFocus()):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(100, 112, 149, 22))
            painter.drawEllipse(QPointF(cx, cy), 13, 13)
        selected = self.selection_mode and self.isChecked()
        complete = not self.selection_mode and self.status == 'present'
        color = '#626fbd' if selected else '#8d9aaa' if self.selection_mode else '#278575' if complete else '#8d9aaa' if self.status == 'checking' else '#916039'
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(color), 1.5))
        if not complete: painter.drawEllipse(QRectF(cx-8, cy-8, 16, 16))
        if selected or complete:
            painter.drawLine(QPointF(cx-5, cy), QPointF(cx-1, cy+3))
            painter.drawLine(QPointF(cx-1, cy+3), QPointF(cx+5, cy-4))
        elif not self.selection_mode:
            if self.status == 'checking':
                painter.drawLine(QPointF(cx, cy-4), QPointF(cx, cy))
                painter.drawLine(QPointF(cx, cy), QPointF(cx+3, cy+2))
            else:
                painter.drawLine(QPointF(cx, cy-4), QPointF(cx, cy+1))
                painter.drawPoint(QPointF(cx, cy+4))
