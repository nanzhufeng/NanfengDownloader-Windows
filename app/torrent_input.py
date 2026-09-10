from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPlainTextEdit


class DownloadInput(QPlainTextEdit):
    torrent_dropped = Signal(str)

    @staticmethod
    def torrent_paths(mime):
        urls = mime.urls() if mime.hasUrls() else []
        if urls and all(url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() == '.torrent' for url in urls):
            return list(dict.fromkeys(url.toLocalFile() for url in urls))
        return []

    def dragEnterEvent(self, event):
        if self.torrent_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self.torrent_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        paths = self.torrent_paths(event.mimeData())
        if not paths:
            return super().dropEvent(event)
        event.acceptProposedAction()
        for path in paths:
            self.torrent_dropped.emit(path)
