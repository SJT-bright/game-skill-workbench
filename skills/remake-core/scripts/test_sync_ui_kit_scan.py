#!/usr/bin/env python3
"""生成时预防 R4J2 (R4F3 leftover): `tiktok_finalize.py sync` runs ui_kit_scan, so a hand-built popup or a developer word
in player text (回家快跑 ad toast "LOCAL PREVIEW") is reported at the first build, not only at `source` before packaging.
Cases:
  1 wiring   ui_kit_scan stays in sync; the existing R4F1 Sprite check also runs before the first build
  2 new      sync on a new remake game with HANDMADE + DEV: K_dev_text block, K_W_ui_handmade_popup warning in the sync
             record (old code: neither, the sync record is clean)
  3 legacy   a legacy game: ui_kit_scan only reported, no block or warning
  4 speed    sync on the fixture plus 200 scripts stays well under the 1 s budget the step adds (whole sync < 3 s)
Run: python3 test_sync_ui_kit_scan.py
"""
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402
from test_ui_kit_scan import DEV, HANDMADE, WITH_KIT, project  # noqa: E402


def step(rec, name):
    return next((s for s in rec['steps'] if s.get('step') == name), None)


class SyncUiKitScan(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='sync_ui_kit_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_wiring(self):
        self.assertEqual(F.SYNC_SOURCE_STEPS[-1], 'ui_kit_scan')
        self.assertIn('art_static', F.SYNC_SOURCE_STEPS)
        self.assertIn('art_static', F.SOURCE_STEPS)

    def test_2_new_game_reported_at_sync(self):
        project(self.tmp, {'assets/scripts/Revive.js': HANDMADE, 'assets/scripts/Ad.js': DEV})
        P.write_marker(self.tmp, 'remake', T.load_manifest().version, reason='init')
        rec = F.finalize_sync(self.tmp, 'remake')
        self.assertIsNotNone(step(rec, 'ui_kit_scan'), [s.get('step') for s in rec['steps']])
        self.assertIn('K_dev_text', {b['id'] for b in rec['blocks']})
        self.assertIn('K_W_ui_handmade_popup', {w['id'] for w in rec['warnings']})

    def test_3_legacy_report_only(self):
        project(self.tmp, {'assets/scripts/Revive.js': HANDMADE, 'assets/scripts/Ad.js': DEV})
        rec = F.finalize_sync(self.tmp, 'remake', policy='legacy')
        s = step(rec, 'ui_kit_scan')
        self.assertEqual((s['blocks'], s['warnings']), ([], []))
        self.assertNotIn('K_dev_text', {b['id'] for b in rec['blocks']})

    def test_4_speed(self):
        files = {'assets/scripts/S%03d.js' % i: WITH_KIT * 5 for i in range(200)}
        project(self.tmp, files)
        P.write_marker(self.tmp, 'remake', T.load_manifest().version, reason='init')
        t = time.time()
        rec = F.finalize_sync(self.tmp, 'remake')
        self.assertLess(time.time() - t, 3.0)
        self.assertNotIn('K_dev_text', {b['id'] for b in rec['blocks']})


if __name__ == '__main__':
    unittest.main(verbosity=2)
