import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from app import main as desktop


class ReleaseRuntimeIsolationTests(unittest.TestCase):
    def test_startup_does_not_launch_browser_before_showing_window(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(desktop, 'QApplication') as application, patch.object(desktop, 'MainWindow') as window, patch.object(desktop, 'cleanup_runtime_cookie_exports'), patch.object(desktop, 'migrate_legacy_cookie_files', return_value=0), patch('app.auth_profile._load_browser_cookies', side_effect=AssertionError('Startup must not wait for a browser')), patch('app.auth_profile.auth_data_dir') as auth_root:
            auth_root.return_value.__truediv__.return_value.exists.return_value = True
            application.return_value.exec.return_value = 0
            self.assertEqual(desktop.main(), 0)
            window.return_value.show.assert_called_once()

    def test_release_qa_entry_uses_explicit_temporary_ini(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'NANFENG_DOWNLOADER_QA_ROOT': directory, 'NANFENG_DOWNLOADER_QA_PREVIEW': '0'}), patch.object(desktop, 'QApplication') as application, patch.object(desktop, 'MainWindow') as window, patch.object(desktop, 'cleanup_runtime_cookie_exports'), patch.object(desktop, 'migrate_legacy_cookie_files', return_value=0):
            application.return_value.exec.return_value = 0
            self.assertEqual(desktop.main(), 0)
            settings = window.call_args.kwargs['settings']
            self.assertEqual(settings.format(), QSettings.IniFormat)
            self.assertEqual(Path(settings.fileName()).resolve(), Path(directory).resolve() / 'preferences.ini')

    def test_normal_entry_keeps_native_settings_behavior(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(desktop, 'QApplication') as application, patch.object(desktop, 'MainWindow') as window, patch.object(desktop, 'cleanup_runtime_cookie_exports'), patch.object(desktop, 'migrate_legacy_cookie_files', return_value=0):
            application.return_value.exec.return_value = 0
            self.assertEqual(desktop.main(), 0)
            self.assertIsNone(window.call_args.kwargs['settings'])
