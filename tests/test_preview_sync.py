"""Behavioral checks for editable preview preservation and conflict handling."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sync_preview', REPO / 'scripts/sync-preview.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class PreviewSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.original_root = sync.ROOT
        sync.ROOT = self.root
        (self.root / 'content').mkdir()
        (self.root / 'main.tex').write_text('before\n  \\input{content/a.tex}after\n')
        (self.root / 'content/a.tex').write_text('original\n')

    def tearDown(self):
        sync.ROOT = self.original_root
        self.temp.cleanup()

    def test_exact_round_trip_and_noop(self):
        text, _ = sync.render('it', 'single-column')
        sources = sync.unpack(text, 'it', 'single-column')
        for name, body in sources.items():
            self.assertEqual(body, (self.root / name).read_text())
        preview = sync.sync('it', 'single-column')
        before = preview.stat().st_mtime_ns
        sync.sync('it', 'single-column')
        self.assertEqual(before, preview.stat().st_mtime_ns)

    def test_editor_edits_update_modular_source(self):
        preview = sync.sync('it', 'single-column')
        preview.write_text(preview.read_text().replace('original', 'edited in editor'))
        sync.sync('it', 'single-column')
        self.assertEqual((self.root / 'content/a.tex').read_text(), 'edited in editor\n')

    def test_modular_edits_refresh_preview(self):
        preview = sync.sync('it', 'single-column')
        (self.root / 'content/a.tex').write_text('edited in source\n')
        sync.sync('it', 'single-column')
        self.assertIn('edited in source', preview.read_text())

    def test_conflicting_edits_preserve_both_files(self):
        preview = sync.sync('it', 'single-column')
        preview.write_text(preview.read_text().replace('original', 'editor version'))
        (self.root / 'content/a.tex').write_text('source version\n')
        with self.assertRaisesRegex(ValueError, 'Concurrent edits'):
            sync.sync('it', 'single-column')
        self.assertIn('editor version', preview.read_text())
        self.assertEqual((self.root / 'content/a.tex').read_text(), 'source version\n')

    def test_missing_markers_preserve_preview(self):
        preview = sync.sync('it', 'single-column')
        preview.write_text('unmarked user document')
        with self.assertRaises(ValueError):
            sync.sync('it', 'single-column')
        self.assertEqual(preview.read_text(), 'unmarked user document')

    def test_clean_preserves_preview_and_imports_pending_edits(self):
        (self.root / 'scripts').mkdir()
        (self.root / 'themes/single-column').mkdir(parents=True)
        shutil.copy(REPO / 'scripts/sync-preview.py', self.root / 'scripts')
        shutil.copy(REPO / 'scripts/build.sh', self.root / 'scripts')
        preview = sync.sync('it', 'single-column')
        preview.write_text(preview.read_text().replace('original', 'pending edit'))
        backup = preview.with_suffix('.pre-sync.tex')
        backup.write_text('original unmarked backup')
        (self.root / 'build/single-column').mkdir()
        (self.root / 'build/single-column/test.log').write_text('generated')
        result = subprocess.run(['bash', str(self.root / 'scripts/build.sh'), 'clean'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(preview.exists())
        self.assertEqual(backup.read_text(), 'original unmarked backup')
        self.assertEqual((self.root / 'content/a.tex').read_text(), 'pending edit\n')
        self.assertFalse((self.root / 'build/single-column').exists())


if __name__ == '__main__':
    unittest.main()
