"""Mở game từ lối tắt (pythonw, không console): log ra file, lỗi thì hiện hộp thoại thay vì im lặng."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import helpers  # noqa: F401
from spaceship import __main__ as launcher
from spaceship.config import ASSETS_DIR


class LauncherTest(unittest.TestCase):
    def test_windowless_crash_is_logged_and_shown(self):
        folder = Path(tempfile.mkdtemp())
        shown = []
        old_out, old_err = sys.stdout, sys.stderr
        try:
            with patch.object(sys, "stderr", None), \
                 patch.object(launcher, "_log_path", return_value=folder / "spaceship.log"), \
                 patch.object(launcher, "_show_error", side_effect=shown.append), \
                 patch("spaceship.app.Game", side_effect=RuntimeError("hong camera")):
                launcher.main(["--no-camera"])
                sys.stdout.flush()
        finally:
            sys.stdout, sys.stderr = old_out, old_err
        text = (folder / "spaceship.log").read_text(encoding="utf-8")
        self.assertIn("hong camera", text)
        self.assertEqual(len(shown), 1)
        self.assertIn("spaceship.log", shown[0])

    def test_console_crash_still_raises(self):
        with patch("spaceship.app.Game", side_effect=RuntimeError("loi")):
            with self.assertRaises(RuntimeError):
                launcher.main(["--no-camera"])

    def test_icon_and_shortcut_script_exist(self):
        self.assertTrue((ASSETS_DIR / "icon.ico").exists())
        self.assertTrue((ASSETS_DIR / "icon.png").exists())
        root = ASSETS_DIR.parent
        for name in ("Tao loi tat.bat", "scripts/create_shortcut.ps1"):
            (root / name).read_bytes().decode("ascii")      # Windows đọc ANSI: phải thuần ASCII
