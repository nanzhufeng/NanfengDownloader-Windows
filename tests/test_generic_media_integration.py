"""Real local HTTP + yt-dlp + FFmpeg integration, no platform credentials."""
import functools
import http.server
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from app.downloader import DownloadOptions, download_url, find_ffmpeg_dir


class GenericMediaIntegrationTests(unittest.TestCase):
    def test_embedded_video_download_has_progress_and_valid_output(self):
        ffmpeg = find_ffmpeg_dir(Path(__file__).resolve().parents[1])
        if not ffmpeg:
            self.skipTest("FFmpeg is required for real media integration")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            web = root / "web"
            web.mkdir()
            subprocess.run([str(ffmpeg / "ffmpeg.exe"), "-v", "error", "-f", "lavfi", "-i",
                            "color=c=blue:s=160x90:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            str(web / "sample.mp4")], check=True, timeout=30)
            (web / "index.html").write_text('<html><title>Local sample</title><video src="sample.mp4" controls></video></html>', encoding="utf-8")
            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *args):
                    pass
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(web)))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                updates = []
                options = DownloadOptions(root / "output", "最佳画质", "不使用登录态", None, ffmpeg)
                result = download_url(f"http://127.0.0.1:{server.server_port}/index.html", options, updates.append)
                self.assertEqual(len(result.files), 1)
                self.assertGreater(result.files[0].stat().st_size, 0)
                self.assertIn("127.0.0.1", str(result.files[0]))
                self.assertTrue(any(item.get("downloaded_bytes", 0) > 0 for item in updates))
                self.assertTrue(any(item.get("status") == "finished" for item in updates))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
