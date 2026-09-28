import tempfile
import unittest
from pathlib import Path

from file_inspection import cleanup_identity, scan_files, trash_selected


class CleanupTests(unittest.TestCase):
    def test_selected_only_and_changed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            roots = [(root, "Temporário", True)]
            selected, changed, untouched = [root / name for name in ("selected", "changed", "untouched")]
            for path in (selected, changed, untouched):
                path.write_text("original")
            items = [(str(path), cleanup_identity(path, roots)) for path in (selected, changed)]
            changed.write_text("changed content")
            trash = root / "trash"
            trash.mkdir()

            def move(path):
                Path(path).rename(trash / Path(path).name)
                return True

            completed, errors = trash_selected(items, roots, move)
            self.assertEqual(completed, [str(selected)])
            self.assertEqual(len(errors), 1)
            self.assertTrue(changed.exists())
            self.assertTrue(untouched.exists())
            self.assertEqual((trash / "selected").read_text(), "original")

    def test_links_packages_and_outside_paths_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "cache"
            cache.mkdir()
            outside = root / "private"
            outside.write_text("private")
            (cache / "link").symlink_to(outside)
            roots = [(cache, "Cache de aplicativo", True)]
            for path in (outside, cache / "link"):
                with self.assertRaises(ValueError):
                    cleanup_identity(path, roots)
            with self.assertRaises(ValueError):
                cleanup_identity(outside, [(root, "Pacote baixado", False)])

    def test_failed_trash_preserves_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file"
            path.write_text("data")
            roots = [(Path(directory), "Temporário", True)]
            completed, errors = trash_selected(
                [(str(path), cleanup_identity(path, roots))], roots, lambda _path: False)
            self.assertFalse(completed)
            self.assertEqual(len(errors), 1)
            self.assertTrue(path.exists())

    def test_browser_cache_category(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            browser = root / "google-chrome" / "Default"
            browser.mkdir(parents=True)
            (browser / "cache-file").write_text("cache")
            rows, errors = scan_files([(root, "Cache de aplicativo", True)], {}, lambda _name: None)
            self.assertFalse(errors)
            self.assertEqual(rows[0][1], "Cache de navegador")


if __name__ == "__main__":
    unittest.main()
