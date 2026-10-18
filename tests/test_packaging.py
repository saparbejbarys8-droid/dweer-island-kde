"""Regression checks for portable paths, shipped files and backup restoration."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('theme', REPO / 'src/theme.py')
theme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(theme)


class PackagingTests(unittest.TestCase):
    def test_no_personal_paths_or_media(self):
        for path in (REPO / 'src').rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts:
                continue
            self.assertNotIn(path.suffix.lower(), ['.png', '.jpg', '.jpeg', '.mp4', '.webp'])
            text = path.read_text()
            self.assertNotIn('/home/dweer', text, str(path))
            self.assertNotIn('Windswept', text, str(path))
        assets = (REPO / 'src/build_assets.py').read_text()
        self.assertNotIn('make_wallpaper', assets)
        layout = (REPO / 'src/layout.js').read_text()
        self.assertNotIn('wallpaperPlugin =', layout)
        self.assertNotIn('PreviewImage:', layout)

    def test_backup_restores_missing_and_present_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, state = Path(tmp) / 'config', Path(tmp) / 'state'
            config.mkdir()
            original = '[General]\nName=before\n'
            (config / 'kdeglobals').write_text(original)
            with patch.object(theme, 'CONFIG', config), patch.object(theme, 'STATE', state), \
                    patch.object(theme, 'display_config', return_value={}), \
                    patch.object(theme, 'stop_shell', return_value=False), \
                    patch.object(theme, 'start_shell'), patch.object(theme, 'run'):
                backup = theme.snapshot()
                (config / 'kdeglobals').write_text('changed')
                (config / 'kwinrc').write_text('new file')
                theme.restore_backup(backup)
                self.assertEqual((config / 'kdeglobals').read_text(), original)
                self.assertFalse((config / 'kwinrc').exists())
                self.assertEqual(Path((state / 'original').read_text()), backup)
                second = theme.snapshot()
                self.assertNotEqual(second, backup)
                self.assertEqual(Path((state / 'original').read_text()), backup)


if __name__ == '__main__':
    unittest.main()
