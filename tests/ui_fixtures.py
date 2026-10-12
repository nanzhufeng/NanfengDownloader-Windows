"""Desktop test windows never share the user's native settings or output root."""
import atexit
import tempfile
from pathlib import Path

_directories = []


def _cleanup():
    for directory in _directories:
        directory.cleanup()


atexit.register(_cleanup)


def isolated_main_window():
    from PySide6.QtCore import QSettings
    from app.main import MainWindow

    directory = tempfile.TemporaryDirectory(prefix='nanfeng-ui-test-')
    _directories.append(directory)
    root = Path(directory.name)
    settings = QSettings(str(root / 'preferences.ini'), QSettings.IniFormat)
    window = MainWindow(settings=settings)
    window.output_edit.setText(str(root / 'output'))
    return window
