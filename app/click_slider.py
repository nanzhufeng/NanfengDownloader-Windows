"""Playback sliders: a track click sets the absolute position and can continue dragging."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider


class ClickJumpSlider(QSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self._pointer_drag = False

    def _position_at(self, point):
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        groove = self.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderGroove, self)
        handle = self.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self)
        if self.orientation() == Qt.Horizontal:
            span = max(1, groove.width()-handle.width())
            position = point.x()-groove.left()-handle.width()/2
        else:
            span = max(1, groove.height()-handle.height())
            position = point.y()-groove.top()-handle.height()/2
        return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(),
                    max(0, min(span, round(position))), span, option.upsideDown)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        self.setFocus(Qt.MouseFocusReason)
        self._pointer_drag = True
        self.setSliderDown(True)
        self.setSliderPosition(self._position_at(event.position()))
        event.accept()

    def mouseMoveEvent(self, event):
        if self._pointer_drag:
            self.setSliderPosition(self._position_at(event.position()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._pointer_drag and event.button() == Qt.LeftButton:
            self.setSliderPosition(self._position_at(event.position()))
            self._pointer_drag = False
            self.setSliderDown(False)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
