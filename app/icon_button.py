"""Icon-only actions with transparent idle and one antialiased circular hit surface."""
from PySide6.QtCore import Qt, QRect, QRectF, QSize
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtWidgets import QPushButton


class IconButton(QPushButton):
    def __init__(self, parent=None, *, dark=False):
        super().__init__(parent)
        self._keyboard_focus = False
        self._hover_color = QColor(255, 255, 255, 36) if dark else QColor('#e5e5e5')
        self._press_color = QColor(255, 255, 255, 55) if dark else QColor('#dce0e4')
        self.setFixedSize(36, 36)
        self.setIconSize(QSize(20, 20))
        # Local size contract survives page-wide text-button padding/minimums.
        self.setStyleSheet('QPushButton { min-width:36px; max-width:36px; '
                           'min-height:36px; max-height:36px; padding:0; border:none; outline:none; }')

    def focusInEvent(self, event):
        self._keyboard_focus = event.reason() in (
            Qt.TabFocusReason, Qt.BacktabFocusReason, Qt.ShortcutFocusReason)
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event):
        self._keyboard_focus = False
        super().focusOutEvent(event)
        self.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def mousePressEvent(self, event):
        self._keyboard_focus = False
        super().mousePressEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.isEnabled() and (self.isDown() or self.underMouse() or
                                  (self.hasFocus() and self._keyboard_focus)):
            painter.setPen(Qt.NoPen)
            painter.setBrush(self._press_color if self.isDown() else self._hover_color)
            side = min(self.width(), self.height())
            painter.drawEllipse(QRectF((self.width()-side)/2, (self.height()-side)/2, side, side))
        size = self.iconSize()
        icon_rect = QRect((self.width()-size.width())//2, (self.height()-size.height())//2,
                          size.width(), size.height())
        self.icon().paint(painter, icon_rect, Qt.AlignCenter,
                          QIcon.Normal if self.isEnabled() else QIcon.Disabled)
