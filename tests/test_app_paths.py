import os
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

from app_paths import DATA_DIR, RESOURCE_DIR


class AppPathsTests(unittest.TestCase):
    def test_source_and_frozen_share_user_storage_not_install_directory(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": str(Path.home() / "test-app-data")}):
            source = runpy.run_path(str(RESOURCE_DIR / "app_paths.py"))
            with (patch("sys.frozen", True, create=True),
                  patch("sys.executable", str(RESOURCE_DIR / "dist" / "app.exe"))):
                frozen = runpy.run_path(str(RESOURCE_DIR / "app_paths.py"))
        self.assertEqual(source["DATA_DIR"], frozen["DATA_DIR"])
        self.assertNotEqual(frozen["DATA_DIR"], frozen["INSTALL_DIR"])
        self.assertEqual(frozen["RESOURCE_DIR"], RESOURCE_DIR)
        self.assertTrue((RESOURCE_DIR / "assets" / "haohao.ico").is_file())
        self.assertNotEqual(DATA_DIR, RESOURCE_DIR / "data")


if __name__ == "__main__":
    unittest.main()
