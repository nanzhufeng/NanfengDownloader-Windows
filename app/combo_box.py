"""Shared combo interaction and placement; popup painting lives in combo_popup."""
import weakref
from shiboken6 import isValid
from PySide6.QtCore import QEvent, QObject, QPoint, QTimer, Qt
from PySide6.QtWidgets import QApplication, QComboBox, QStyle, QStylePainter, QStyleOptionComboBox
from .combo_popup import ComboPopupSurface, SHADOW_MARGIN, CARD_PADDING

class ComboTriggerFilter(QObject):
    def __init__(self, combo):
        super().__init__(combo)
        self.combo = weakref.ref(combo)

    def eventFilter(self, watched, event):
        if event.type() not in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            return False
        combo = self.combo()
        if combo is None or not isValid(combo):
            return False
        return combo.filter_trigger_click(event)


class CenterComboBox(QComboBox):
    def __init__(self) -> None:
        super().__init__()
        self._trigger_press_active = False
        self._popup_open_at_press = False
        self._trigger_filter = ComboTriggerFilter(self)
        self.setEditable(False)
        self._popup_surface = None

    def showPopup(self) -> None:
        if self._popup_surface is None:
            self._popup_surface = ComboPopupSurface(self)
        self.view().setMinimumHeight(0)
        self.view().setMaximumHeight(16777215)
        # Only an open popup captures clicks outside the combo. Registering every
        # queue combo globally makes widget creation dispatch events to every row.
        QApplication.instance().installEventFilter(self._trigger_filter)
        super().showPopup()
        self._position_popup()
        # Reapply after Qt finishes laying out the native popup container.
        QTimer.singleShot(0, self._position_popup)

    def hidePopup(self) -> None:
        super().hidePopup()
        QApplication.instance().removeEventFilter(self._trigger_filter)

    def _position_popup(self) -> None:
        if not self.view().isVisible():
            return
        popup = self.view().window()
        screen_rect = self.screen().availableGeometry()
        anchor = self.mapToGlobal(QPoint(-SHADOW_MARGIN, self.height() + 8 - SHADOW_MARGIN))
        width = min(max(self.width(), 190) + 2 * SHADOW_MARGIN, screen_rect.width())
        row_height = max(30, self.view().sizeHintForRow(0))
        height = min(self.count(), self.maxVisibleItems()) * row_height + 2 * (SHADOW_MARGIN + CARD_PADDING)
        below = screen_rect.bottom() - anchor.y() + 1
        minimum_popup_height = row_height + 2 * (SHADOW_MARGIN + CARD_PADDING)
        if below >= minimum_popup_height:
            height = min(height, below)
            y = anchor.y()
        else:
            top = self.mapToGlobal(QPoint(0, 0)).y() - 8 + SHADOW_MARGIN
            height = min(height, max(minimum_popup_height, top - screen_rect.top()))
            y = max(screen_rect.top(), top - height)
        x = max(screen_rect.left(), min(anchor.x(), screen_rect.right() - width + 1))
        popup.resize(width, height)
        popup.move(x, y)
        # Qt's native menu-style scrollers reserve bands even when every row
        # fits after our resize. Remove those bands only for the full menu.
        if height >= self.count() * row_height + 2 * (SHADOW_MARGIN + CARD_PADDING):
            self.view().setFixedHeight(self.count() * row_height)
            popup_layout = popup.layout()
            for index in range(popup_layout.count()):
                widget = popup_layout.itemAt(index).widget()
                if widget is not None and widget is not self.view():
                    widget.hide()
            popup_layout.activate()
            self.view().scrollToTop()

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        option.currentText = ""
        painter.drawComplexControl(QStyle.CC_ComboBox, option)
        field = self.style().subControlRect(QStyle.CC_ComboBox, option, QStyle.SC_ComboBoxEditField, self)
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(field, Qt.AlignCenter, self.currentText())

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        self.filter_trigger_click(event)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.filter_trigger_click(event)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def filter_trigger_click(self, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            position = self.mapFromGlobal(event.globalPosition().toPoint())
            if not self.rect().contains(position):
                return False
            self._trigger_press_active = True
            self._popup_open_at_press = self.view().isVisible()
            if self._popup_open_at_press:
                self.hidePopup()
                event.accept()
                return True
            return False

        if event.type() == QEvent.MouseButtonRelease and self._trigger_press_active:
            position = self.mapFromGlobal(event.globalPosition().toPoint())
            should_open = not self._popup_open_at_press and self.rect().contains(position)
            self._trigger_press_active = False
            self._popup_open_at_press = False
            if should_open:
                # Open only after the trigger click is complete, so its release cannot
                # be interpreted by Qt as a selection inside the newly opened popup.
                self.showPopup()
            event.accept()
            return True
        return False
