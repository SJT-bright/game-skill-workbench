#!/usr/bin/env python3
"""生成时预防 R4M2 (补查第 12 组; R4L1 and R4L3 leftovers). Synthetic fixtures, seconds to run. Cases:
  1 display    a new remake game (2.4) with a pass receipt: changing a label's text in a prefab, a font file, a node's
               position, or the text a script writes into a label -> ART_receipt block, state display_changed
               (old code: the receipt still matched, the art check was never redone)
  2 not layout a gameplay value on a script component in the same prefab changes -> still ok (no false stale)
  3 levels     legacy game: the same display change only warns
  4 old        a receipt written before R4M2 (no `display`) still passes, display_state unrecorded (projects in
               progress keep their receipts until the next art_check)
  5 carry      current preparation leaves historical display evidence intact
  6 speed      display fingerprints of 300 prefabs + 300 scripts under 1 s
  7 sync       home_entry_scan is in SYNC_SOURCE_STEPS (ui_kit_scan still last); finalize_sync on a new 3.x game with
               hand-placed entries writes K_W_home_entry_coords; the whole sync of 200 scripts stays about 1 s
               (old code: no home_entry_scan step in the sync record)
  8 ShopTx     the 'not installed' info of sync's run_parts names ShopTx with RunSession and FxPool
               (old code: 'RunSession / FxPool not installed')
Run: python3 test_r4m2_receipt_display_sync.py
"""
import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import art_receipt as R  # noqa: E402
from test_art_receipt_fixtures import write_fixture
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402


def prefab(text='PLAY', x=0, y=-300, speed=3):
    """Cocos 2.4 prefab as the game generator writes it: a button node with a Label and a game script component."""
    return json.dumps([
        {'__type__': 'cc.Prefab', '_name': '', 'data': {'__id__': 1}},
        {'__type__': 'cc.Node', '_name': 'PlayBtn', '_id': 'a1', '_active': True, '_components': [{'__id__': 2}],
         '_contentSize': {'__type__': 'cc.Size', 'width': 300, 'height': 96},
         '_trs': {'__type__': 'TypedArray', 'ctor': 'Float64Array', 'array': [x, y, 0, 0, 0, 0, 1, 1, 1, 1]}},
        {'__type__': 'cc.Label', 'node': {'__id__': 1}, '_id': 'b2', '_string': text, '_N$string': text,
         '_fontSize': 40, '_N$file': {'__uuid__': 'font-uuid'}},
        {'__type__': '9f1c2Kx7aBC', 'node': {'__id__': 1}, '_id': 'c3', 'speed': speed},
    ], indent=2)


SCRIPT = "cc.Class({ extends: cc.Component, onLoad () { this.title.string = 'Tap to start'; this.n = 3; } });\n"


def game(root, engine3=False):
    (root / 'assets' / 'prefabs').mkdir(parents=True, exist_ok=True)
    (root / 'assets' / 'fonts').mkdir(parents=True, exist_ok=True)
    (root / 'assets' / 'scripts').mkdir(parents=True, exist_ok=True)
    if engine3:
        (root / 'package.json').write_text('{"creator": {"version": "3.8.6"}}')
    else:
        (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    (root / 'assets' / 'ui.png').write_bytes(b'\x89PNG\r\n\x1a\n' + b'pixels')
    (root / 'assets' / 'fonts' / 'Title.ttf').write_bytes(b'\x00\x01\x00\x00font-v1')
    (root / 'assets' / 'prefabs' / 'Home.prefab').write_text(prefab(), encoding='utf-8')
    (root / 'assets' / 'scripts' / 'Home.js').write_text(SCRIPT, encoding='utf-8')
    return root


class ReceiptDisplay(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4m2_receipt_'))
        game(self.tmp)
        P.write_marker(self.tmp, 'remake', T.load_manifest().version, reason='init')
        write_fixture(self.tmp, 'pass', {'passed': True, 'status': 'pass'})
        self.assertEqual(R.check_history(self.tmp, 'remake')['level'], 'ok')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def stale(self, policy=None):
        out = R.check_history(self.tmp, 'remake', policy)
        return out['level'], out['state'], out['message']

    def test_1_text_font_layout_code_text(self):
        home = self.tmp / 'assets' / 'prefabs' / 'Home.prefab'
        for change in (lambda: home.write_text(prefab(text='START'), encoding='utf-8'),
                       lambda: (self.tmp / 'assets' / 'fonts' / 'Title.ttf').write_bytes(b'\x00\x01\x00\x00font-v2'),
                       lambda: home.write_text(prefab(x=40), encoding='utf-8'),
                       lambda: (self.tmp / 'assets' / 'scripts' / 'Home.js').write_text(
                           SCRIPT.replace('Tap to start', 'Tap to begin now'), encoding='utf-8')):
            game(self.tmp)                     # back to the receipt's bytes
            self.assertEqual(R.check_history(self.tmp, 'remake')['level'], 'ok')
            change()
            level, state, message = self.stale()
            self.assertEqual((level, state), ('block', 'display_changed'), message)
            self.assertIn('重跑 art_check', message)
            self.assertIn('display_changed', R.finding(R.check_history(self.tmp, 'remake'))['evidence'])

    def test_2_gameplay_value_is_not_layout(self):
        (self.tmp / 'assets' / 'prefabs' / 'Home.prefab').write_text(prefab(speed=9), encoding='utf-8')
        (self.tmp / 'assets' / 'scripts' / 'Home.js').write_text(SCRIPT.replace('this.n = 3', 'this.n = 7'),
                                                                 encoding='utf-8')
        self.assertEqual(self.stale()[:2], ('ok', 'match_pass'))

    def test_3_legacy_warns(self):
        (self.tmp / 'assets' / 'prefabs' / 'Home.prefab').write_text(prefab(text='START'), encoding='utf-8')
        self.assertEqual(self.stale(policy='legacy')[:2], ('warn', 'display_changed'))

    def test_4_old_receipt_still_passes(self):
        path = R.receipt_path(self.tmp)
        data = json.loads(path.read_text(encoding='utf-8'))
        for key in ('display', 'display_sha256', 'display_schema'):
            data.pop(key, None)
        path.write_text(json.dumps(data), encoding='utf-8')
        (self.tmp / 'assets' / 'prefabs' / 'Home.prefab').write_text(prefab(text='START'), encoding='utf-8')
        out = R.check_history(self.tmp, 'remake')
        self.assertEqual((out['level'], out['state'], out['display_state']), ('ok', 'match_pass', 'unrecorded'))

    def test_5_carry_leaves_history_intact(self):
        before = R.receipt_path(self.tmp).read_bytes()
        self.assertIsNone(R.carry(self.tmp, 'tiktok_finalize source', R.check_history(self.tmp, 'remake')))
        self.assertEqual(R.receipt_path(self.tmp).read_bytes(), before)

    def test_6_speed(self):
        for i in range(300):
            (self.tmp / 'assets' / 'prefabs' / ('P%03d.prefab' % i)).write_text(prefab(text='T%d' % i))
            (self.tmp / 'assets' / 'scripts' / ('S%03d.js' % i)).write_text(SCRIPT * 20)
        t = time.time()
        found = R.display_fingerprints(self.tmp)
        self.assertLess(time.time() - t, 1.0)
        self.assertGreaterEqual(len(found), 600)


class SyncSteps(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4m2_sync_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_7_home_entry_scan_in_sync(self):
        from test_r4l1_home_entry_coords import HAND, KIT_WAY, project
        self.assertIn('home_entry_scan', F.SYNC_SOURCE_STEPS)
        self.assertEqual(F.SYNC_SOURCE_STEPS[-1], 'ui_kit_scan')
        files = {'assets/scripts/S%03d.ts' % i: KIT_WAY.replace('placeLater', 'placeNot') * 5 for i in range(200)}
        files['assets/scripts/Home.ts'] = HAND
        project(self.tmp, files)
        P.write_marker(self.tmp, 'remake', T.load_manifest().version, reason='init')
        t = time.time()
        rec = F.finalize_sync(self.tmp, 'remake')
        spent = time.time() - t
        step = next((s for s in rec['steps'] if s.get('step') == 'home_entry_scan'), None)
        self.assertIsNotNone(step, [s.get('step') for s in rec['steps']])
        self.assertIn('K_W_home_entry_coords', {w['id'] for w in rec['warnings']})
        print('\n  sync of 201 scripts: %.2f s' % spent, file=sys.stderr)
        self.assertLess(spent, 2.0)

    def test_8_shoptx_named(self):
        ctx = T.Ctx('source', self.tmp, project=self.tmp, board='localize', engine=2, policy='new',
                    manifest=T.load_manifest())
        info = ' '.join(F.sync_run_parts(ctx)['info'])
        for name in ('RunSession', 'FxPool', 'ShopTx'):
            self.assertIn(name, info)


if __name__ == '__main__':
    unittest.main(verbosity=2)
