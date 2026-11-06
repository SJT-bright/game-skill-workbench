#!/usr/bin/env python3
"""生成时预防 R4L1 (R4F3 leftover): hand-built popups and hard-coded mask values block a new game STARTED with GameUIKit.

R4F3 left K_ui_handmade_popup / K_ui_mask_hardcoded as warnings for every new game, because 8 of 9 remake games in
progress were begun before GameUIKit (11.13). A game begun with the kit has no reason to build a popup by hand, so for
it the two findings block. "Begun with the kit" = GameUIKit.js / .ts installed AND .tiktok-kit/policy.json written by
`init` with ui_kit_at_start (init from R4L1) or at / after 11.13. Cases:
  1 kit era   init now + GameUIKit.js installed: popup + mask block (old code: both K_W_ warnings)
  2 3.x       the same with assets/tiktok-platform/GameUIKit.ts
  3 before    init 2026-10-31 (the calibration games) + GameUIKit.js installed by a later sync: still warnings
  4 adopt     marker by adopt / source (auto) after 11.13 + GameUIKit.js: warnings (a game taken over)
  5 no kit    init now but GameUIKit not installed: warnings
  6 boards    English (localize) with the kit: warnings; legacy: report only; K_dev_text unchanged
  7 marker    init writes ui_kit_at_start, a later adopt keeps it, a marker first written by adopt never gets it
  8 flow      init -> sync (installs GameUIKit) -> source: the source record blocks K_ui_handmade_popup, K5 refuses
Run: python3 test_r4l1_ui_kit_era.py
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402
from tiktok_finalize_steps import ui_kit_scan as U  # noqa: E402
from test_ui_kit_scan import DEV, HANDMADE, project  # noqa: E402

KIT_JS = 'assets/tiktok-platform/GameUIKit.js'
KIT_TS = 'assets/tiktok-platform/GameUIKit.ts'


def marker(root, by='init', created=None, **extra):
    P.write_marker(root, 'remake', '2.0', reason=by)
    if created or extra:
        p = root / P.MARKER
        data = json.loads(p.read_text(encoding='utf-8'))
        if created:
            data['created'] = created
        data.pop('ui_kit_at_start', None)
        data.update(extra)
        p.write_text(json.dumps(data), encoding='utf-8')


def run(root, board='remake', policy='new', engine=2):
    return U.apply(T.Ctx('source', root, project=root, board=board, engine=engine, policy=policy,
                         manifest=T.load_manifest()))


def split(r):
    return {b['id'] for b in r['blocks']}, {w['id'] for w in r['warnings']}


class UiKitEra(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4l1_uikit_'))
        project(self.tmp, {'assets/scripts/Revive.js': HANDMADE})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def kit(self, rel=KIT_JS):
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('// GameUIKit\n', encoding='utf-8')

    def test_1_kit_era_blocks(self):
        marker(self.tmp)
        self.kit()
        blocks, warns = split(run(self.tmp))
        self.assertEqual(blocks, {'K_ui_handmade_popup', 'K_ui_mask_hardcoded'})
        self.assertEqual(warns, set())

    def test_2_3x(self):
        marker(self.tmp)
        self.kit(KIT_TS)
        self.assertIn('K_ui_handmade_popup', split(run(self.tmp, engine=3))[0])

    def test_3_begun_before_kit(self):
        marker(self.tmp, created='2026-10-31T19:12:14-0700')   # NimsNightJars' marker
        self.kit()
        blocks, warns = split(run(self.tmp))
        self.assertEqual(blocks, set())
        self.assertEqual(warns, {'K_W_ui_handmade_popup', 'K_W_ui_mask_hardcoded'})
        marker(self.tmp, created='2026-11-04T20:05:00-0800')    # init after 11.13, no ui_kit_at_start field yet
        self.assertIn('K_ui_handmade_popup', split(run(self.tmp))[0])

    def test_4_adopted(self):
        for by in ('adopt', 'source (auto: starter)'):
            shutil.rmtree(self.tmp / '.tiktok-kit', ignore_errors=True)
            marker(self.tmp, by=by, created='2026-11-05T09:00:00-0800')
            self.kit()
            self.assertEqual(split(run(self.tmp))[0], set(), by)

    def test_5_kit_not_installed(self):
        marker(self.tmp)
        self.assertEqual(split(run(self.tmp)), (set(), {'K_W_ui_handmade_popup', 'K_W_ui_mask_hardcoded'}))

    def test_6_boards(self):
        project(self.tmp, {'assets/scripts/Ad.js': DEV})
        marker(self.tmp)
        self.kit()
        self.assertEqual(split(run(self.tmp, board='localize'))[0], set())
        leg = run(self.tmp, policy='legacy')
        self.assertEqual((leg['blocks'], leg['warnings']), ([], []))
        self.assertIn('K_dev_text', split(run(self.tmp))[0])

    def test_7_marker_field(self):
        self.assertTrue(P.write_marker(self.tmp, 'remake', '2.0').get('ui_kit_at_start'))
        self.assertTrue(P.write_marker(self.tmp, 'remake', '2.0', reason='adopt').get('ui_kit_at_start'))
        other = self.tmp / 'other'
        other.mkdir()
        self.assertNotIn('ui_kit_at_start', P.write_marker(other, 'remake', '2.0', reason='adopt'))
        self.assertNotIn('ui_kit_at_start', P.write_marker(other, 'remake', '2.0', reason='init'))

    def test_8_flow_init_sync_source(self):
        P.write_marker(self.tmp, 'remake', T.load_manifest().version, reason='init')
        F.finalize_sync(self.tmp, 'remake')
        self.assertTrue((self.tmp / KIT_JS).is_file(), 'sync installs GameUIKit.js')
        rec = F.finalize_source(self.tmp, 'remake')
        self.assertIn('K_ui_handmade_popup', {b['id'] for b in rec['blocks']})
        self.assertTrue(any('K_ui_handmade_popup' in f['message'] for f in F.check_source_record(self.tmp)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
