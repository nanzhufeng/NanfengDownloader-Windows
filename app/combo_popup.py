"""Shared Qt combo popup surface: one rounded contour, no native frame/shadow."""
import math
import weakref

from PySide6.QtCore import QObject, QEvent, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QStyledItemDelegate, QStyle

SHADOW_MARGIN = 16
CARD_PADDING = 6


class ComboOptionDelegate(QStyledItemDelegate):
    def __init__(self, combo):
        super().__init__(combo.view())
        self.combo = weakref.ref(combo)

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(max(190, size.width() + 34), max(30, size.height() + 10))

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        row = QRectF(option.rect).adjusted(0, 1, 0, -1)
        active = bool(option.state & (QStyle.State_Selected | QStyle.State_MouseOver))
        combo = self.combo()
        checked = combo is not None and combo.currentIndex() == index.row()
        if active or checked:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#edf3ef' if checked else '#f0f2f1'))
            painter.drawRoundedRect(row, 6, 6)
        if checked:
            tick = QPainterPath()
            tick.moveTo(row.left() + 8, row.center().y())
            tick.lineTo(row.left() + 12, row.center().y() + 4)
            tick.lineTo(row.left() + 19, row.center().y() - 4)
            painter.setPen(QPen(QColor('#07975b'), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(tick)
        painter.setFont(option.font)
        painter.setPen(QColor('#405362' if option.state & QStyle.State_Enabled else '#75818c'))
        painter.drawText(row.adjusted(30, 0, -10, 0), Qt.AlignLeft | Qt.AlignVCenter, str(index.data(Qt.DisplayRole) or ''))
        painter.restore()


class ComboPopupSurface(QObject):
    def __init__(self, combo):
        popup = combo.view().window()
        super().__init__(popup)
        self.popup = popup
        popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        popup.setAttribute(Qt.WA_TranslucentBackground)
        popup.setFrameShape(QFrame.NoFrame)
        popup.installEventFilter(self)
        margin = SHADOW_MARGIN + CARD_PADDING
        popup.layout().setContentsMargins(margin, margin, margin, margin)
        view = combo.view()
        view.setItemDelegate(ComboOptionDelegate(combo))
        view.setFrameShape(QFrame.NoFrame)
        view.setUniformItemSizes(True)
        view.setMouseTracking(True)
        view.setStyleSheet('''
            QAbstractItemView { background: #ffffff; border: none; outline: none; padding: 0; }
            QAbstractItemView::item { border: none; }
            QScrollBar:vertical { background: transparent; width: 6px; border: none; }
            QScrollBar::handle:vertical { background: #d7deda; border: none; border-radius: 3px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; border: none; }
        ''')

    def card_rect(self):
        return QRectF(self.popup.rect()).adjusted(SHADOW_MARGIN, SHADOW_MARGIN, -SHADOW_MARGIN, -SHADOW_MARGIN)

    def eventFilter(self, watched, event):
        if event.type() != QEvent.Paint:
            return False
        painter = QPainter(watched)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(watched.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        card = self.card_rect()
        shadow = card.translated(0, 2)
        painter.setPen(Qt.NoPen)
        for spread in range(SHADOW_MARGIN - 2, 0, -1):
            outer = QPainterPath()
            outer.addRoundedRect(shadow.adjusted(-spread, -spread, spread, spread), 11 + spread, 11 + spread)
            inner = QPainterPath()
            inner.addRoundedRect(shadow.adjusted(1 - spread, 1 - spread, spread - 1, spread - 1), 10 + spread, 10 + spread)
            painter.setBrush(QColor(0, 0, 0, round(36 * math.exp(-spread * spread / (2 * 4.5 ** 2)))))
            painter.drawPath(outer.subtracted(inner))
        painter.setBrush(QColor('#ffffff'))
        painter.drawRoundedRect(card, 11, 11)
        painter.end()
        return True
