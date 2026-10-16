"""Small interface symbols painted as vectors at the requested display scale."""
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


PATHS = {
    0xE721: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/>',
    0xE8BB: '<path d="m6 6 12 12M6 18 18 6"/>',
    0xE73A: '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="m7 12 3 3 7-7"/>',
    0xE734: '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z"/>',
    0xE735: '<path fill="currentColor" d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z"/>',
    0xE8A7: '<path d="M14 3h7v7m0-7L11 13M10 5H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5"/>',
    0xE8C8: '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
    0xE9D9: '<path d="M14 3H5v18h14V8Zm0 0v5h5M8 16v2m4-6v6m4-3v3"/>',
    0xE72D: '<path d="M15 4l6 6-6 6v-4c-6 0-9 2-12 7 0-8 4-11 12-11Z"/>',
    0xE74D: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
    0xE72B: '<path d="m12 5-7 7 7 7M5 12h15"/>',
    0xE70D: '<path d="m6 9 6 6 6-6"/>',
    0xE712: '<circle cx="5" cy="12" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="19" cy="12" r="1" fill="currentColor"/>',
    0xE73E: '<circle cx="12" cy="12" r="9"/><path d="m7.5 12 3 3 6-6"/>',
    0xE7BA: '<path d="M12 3 2 21h20ZM12 9v5m0 3v.2"/>',
    0xE917: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
}


class SvgIconEngine(QIconEngine):
    def __init__(self, source):
        super().__init__()
        self.source = source
        self.renderer = QSvgRenderer(QByteArray(source))

    def clone(self):
        return SvgIconEngine(self.source)

    def paint(self, painter, rect, mode, state):
        painter.save()
        if mode == QIcon.Disabled:
            painter.setOpacity(.45)
        self.renderer.render(painter, QRectF(rect))
        painter.restore()

    def pixmap(self, size, mode, state):
        image = QPixmap(size)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        self.paint(painter, image.rect(), mode, state)
        painter.end()
        return image


def vector_shell_icon(code, color):
    paths = PATHS.get(code)
    if paths is None:
        return None
    source = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
              f'fill="none" color="{color}" stroke="{color}" stroke-width="1.9" '
              f'stroke-linecap="round" stroke-linejoin="round">{paths}</svg>').encode()
    return QIcon(SvgIconEngine(source))
