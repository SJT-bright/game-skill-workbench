#!/usr/bin/env python3
"""R4N3 (补查2 第 1 组 1c): serve_preview.py --snapshot falls back to <project>/.tiktok-kit/snapshots/.

蛋壳特工队: the shared folder ~/.game-skill-locks/web-snapshots answered `Operation not permitted` and the trial
link never came up. A read-only shared folder stands in for it here. No server, no browser.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_r4n3_snapshot_fallback.py
"""
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import types
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import browser_slots  # noqa: E402
import serve_preview as SP  # noqa: E402


class SnapshotFallback(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4n3-snap-'))
        self.project = self.tmp / '蛋壳特工队'
        (self.project / 'assets').mkdir(parents=True)
        (self.project / 'project.json').write_text('{"version": "2.4.15"}')
        self.export = self.project / 'build' / 'web-mobile'
        self.export.mkdir(parents=True)
        (self.export / 'index.html').write_text('<html></html>')
        (self.export / 'main.js').write_text('1')

    def tearDown(self):
        for p in [self.tmp] + list(self.tmp.rglob('*')):
            try:
                os.chmod(p, stat.S_IRWXU)
            except OSError:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def slots(self, shared):
        return types.SimpleNamespace(SNAPSHOTS=shared, snapshot=lambda src: _copy(shared, src))  # browser_slots stand-in

    def test_real_browser_slots_has_what_make_snapshot_uses(self):
        self.assertTrue(hasattr(browser_slots, 'SNAPSHOTS') and callable(browser_slots.snapshot))

    def test_read_only_shared_folder_falls_back_to_the_project(self):
        shared = self.tmp / 'locks' / 'web-snapshots'
        shared.mkdir(parents=True)
        os.chmod(shared, stat.S_IREAD | stat.S_IXUSR)  # like Operation not permitted
        copy, where, own = SP.make_snapshot(self.export, None, self.slots(shared))
        self.assertEqual(where, 'project')
        self.assertTrue(own)
        self.assertTrue(Path(copy).is_relative_to(self.project / '.tiktok-kit' / 'snapshots'))
        self.assertEqual((Path(copy) / 'main.js').read_text(), '1')
        self.assertEqual(list(shared.iterdir()), [])

    def test_explicit_project_is_used(self):
        shared = self.tmp / 'ro'
        shared.mkdir()
        os.chmod(shared, stat.S_IREAD | stat.S_IXUSR)
        other = self.tmp / 'other_project'
        other.mkdir()
        copy, where, _ = SP.make_snapshot(self.export, other, self.slots(shared))
        self.assertTrue(Path(copy).is_relative_to(other / '.tiktok-kit' / 'snapshots'))

    def test_writable_shared_folder_is_used_first(self):
        shared = self.tmp / 'locks' / 'web-snapshots'
        copy, where, own = SP.make_snapshot(self.export, None, self.slots(shared))
        self.assertEqual(where, 'shared')
        self.assertFalse(own)  # browser_slots.release deletes it, as before
        self.assertTrue(Path(copy).is_relative_to(shared))
        self.assertFalse((self.project / '.tiktok-kit').exists())

    def test_nothing_writable_says_both_folders(self):
        shared = self.tmp / 'ro'
        shared.mkdir()
        os.chmod(shared, stat.S_IREAD | stat.S_IXUSR)
        os.chmod(self.project, stat.S_IREAD | stat.S_IXUSR)
        with self.assertRaises(SystemExit) as cm:
            SP.make_snapshot(self.export, None, self.slots(shared))
        self.assertIn('.tiktok-kit', str(cm.exception))


def _copy(shared, src):
    dest = Path(shared) / ('snap-' + Path(src).name)
    shutil.copytree(src, dest)
    return dest


if __name__ == '__main__':
    unittest.main(verbosity=2)
