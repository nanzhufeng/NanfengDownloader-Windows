from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


def _load_release_metadata_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "release_metadata.py"
    spec = importlib.util.spec_from_file_location("release_metadata", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


release_metadata = _load_release_metadata_module()


class ReleaseMetadataTests(unittest.TestCase):
    def test_version_generates_one_consistent_tag_and_installer_name(self) -> None:
        metadata = release_metadata.release_metadata("2026.08.21")

        self.assertEqual(metadata.tag, "v2026.08.21-windows")
        self.assertEqual(metadata.app_version, "2026.8.21")
        self.assertEqual(metadata.version_info, "2026.8.21.0")
        self.assertEqual(metadata.installer_name, "NanfengDownloader-Windows-v2026.08.21-Setup.exe")

    def test_tag_round_trip_rejects_unpadded_or_wrong_platform_tags(self) -> None:
        self.assertEqual(
            release_metadata.release_metadata_from_tag("v2026.08.21-windows").output_version,
            "2026.08.21",
        )
        with self.assertRaises(ValueError):
            release_metadata.release_metadata_from_tag("v2026.8.21-windows")
        with self.assertRaises(ValueError):
            release_metadata.release_metadata_from_tag("v2026.08.21-macos")


class InstallerContractTests(unittest.TestCase):
    def test_installer_requires_explicit_version_and_never_force_closes_apps(self) -> None:
        root = Path(__file__).resolve().parents[1]
        content = (root / "packaging" / "windows" / "NanfengDownloader.iss").read_text(encoding="utf-8-sig")

        self.assertIn("#ifndef MyAppVersion", content)
        self.assertIn("#ifndef MyOutputVersion", content)
        self.assertNotIn("CloseApplications=force", content)
        self.assertIn("CloseApplications=no", content)

    def test_release_workflow_rejects_existing_tags_instead_of_clobbering_assets(self) -> None:
        root = Path(__file__).resolve().parents[1]
        content = (root / ".github" / "workflows" / "release-windows.yml").read_text(encoding="utf-8")

        self.assertIn("already exists", content)
        self.assertNotIn("--clobber", content)
        self.assertIn("release_metadata.py --tag", content)


if __name__ == "__main__":
    unittest.main()
