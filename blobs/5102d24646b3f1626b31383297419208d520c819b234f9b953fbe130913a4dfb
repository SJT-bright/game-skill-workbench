#!/usr/bin/env python3
"""生成时预防 R4P4 (R4O2 leftover): tiktok_finalize_steps/skin_preview_scan.py runs check_skin_preview at source / sync.

Sample shaped after SLS35's store before its fix (preview bound to TileIn.png, skin = colour on the whole node).
  1 no table   no unlock_table.json / skins.json with skin rows -> n/a, nothing reported (tint code alone is ignored)
  2 block      new remake game, table written by make_skin_table (previewFrame TODO) + tinted preview -> K_skin_preview
  3 good       own previewFrame per row, no tint -> clean
  4 warn       table without any previewFrame (older generator / frozen table) -> K_W_skin_preview; English -> warning
  5 legacy     legacy -> not checked
  6 wired      in SOURCE_STEPS; in SYNC_SOURCE_STEPS before ui_kit_scan (still last); finalize_sync reports the block
Run: python3 test_skin_preview_scan.py
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

STORE = '''
cc.Class({ extends: cc.Component,
  show(skin) {
    this.preview.getComponent(cc.Sprite).spriteFrame = this.tileFrame; // TileIn.png
    this.previewNode.color = cc.color(skin.tint[0], skin.tint[1], skin.tint[2]);
  }
});
'''
GOOD_STORE = '''
cc.Class({ extends: cc.Component,
  show(skin) { this.preview.getComponent(cc.Sprite).spriteFrame = this.frames[skin.previewFrame];
               this.previewNode.color = cc.Color.WHITE; }
});
'''


def rows(frames):
    out = [{'id': 'hero_%02d' % i, 'group': 'skin', 'order': i, 'unlock': 'coins', 'coins': 10 * i} for i in range(1, 4)]
    for r, f in zip(out, frames):
        if f is not None:
            r['previewFrame'] = f
    return out


def project(tmp, frames=('TODO: own preview picture of hero_01',) * 3, code=STORE, table=True, by='init',
            board='remake'):
    root = Path(tmp)
    (root / 'assets' / 'scripts').mkdir(parents=True, exist_ok=True)
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}', encoding='utf-8')
    (root / 'assets/scripts/SkinStore.js').write_text(code, encoding='utf-8')
    if table:
        (root / 'assets/resources/config').mkdir(parents=True, exist_ok=True)
        (root / 'assets/resources/config/unlock_table.json').write_text(
            json.dumps({'module': 'skin.v1', 'items': rows(frames)}), encoding='utf-8')
    P.write_marker(root, board, '2.0', reason=by)
    return root


def run(root, policy='new', board='remake'):
    from tiktok_finalize_steps import skin_preview_scan as S
    return S.apply(T.Ctx('source', root, policy=policy, board=board))


class SkinPreviewScan(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='skin_preview_scan_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_no_table_not_checked(self):
        r = run(project(self.tmp, table=False))
        self.assertEqual((r['state'], r['blocks'], r['warnings']), ('n/a', [], []))
        # a skins.json in another format (no "items" with skin rows) is not a skin table either
        (self.tmp / 'data').mkdir()
        (self.tmp / 'data/skins.json').write_text('{"default": {"id": "default"}}', encoding='utf-8')
        self.assertEqual(run(self.tmp)['state'], 'n/a')

    def test_2_new_generated_table_blocks(self):
        r = run(project(self.tmp))
        self.assertEqual([b['id'] for b in r['blocks']], ['K_skin_preview'])
        kinds = {h['kind'] for h in r['blocks'][0]['evidence']}
        self.assertEqual(kinds, {'preview_frame_todo', 'tint_as_skin'})
        self.assertEqual(r['state'], 'conflict')

    def test_3_good_project_clean(self):
        r = run(project(self.tmp, frames=('skins/hero_01.png', 'skins/hero_02.png', 'skins/hero_03.png'),
                        code=GOOD_STORE))
        self.assertEqual((r['blocks'], r['warnings'], r['state']), ([], [], 'kit_current'))

    def test_4_old_table_and_english_warn(self):
        r = run(project(self.tmp, frames=(None, None, None)))
        self.assertEqual((len(r['blocks']), [w['id'] for w in r['warnings']]), (0, ['K_W_skin_preview']))
        other = Path(tempfile.mkdtemp(dir=self.tmp))
        r = run(project(other, board='localize'), board='localize')
        self.assertEqual((len(r['blocks']), [w['id'] for w in r['warnings']]), (0, ['K_W_skin_preview']))

    def test_5_legacy_not_checked(self):
        r = run(project(self.tmp), policy='legacy')
        self.assertEqual((r['blocks'], r['warnings']), ([], []))
        self.assertIn('not checked', r['info'][0])

    def test_6_wired(self):
        self.assertIn('skin_preview_scan', T.SOURCE_STEPS)
        self.assertIn('skin_preview_scan', F.SYNC_SOURCE_STEPS)
        self.assertEqual(F.SYNC_SOURCE_STEPS[-1], 'ui_kit_scan')
        self.assertLess(F.SYNC_SOURCE_STEPS.index('skin_preview_scan'), F.SYNC_SOURCE_STEPS.index('ui_kit_scan'))
        root = project(self.tmp)
        P.write_marker(root, 'remake', T.load_manifest().version, reason='init')
        rec = F.finalize_sync(root, 'remake', write_record=False)
        self.assertIn('skin_preview_scan', [s.get('step') for s in rec['steps']])
        self.assertIn('K_skin_preview', {b['id'] for b in rec['blocks']})


if __name__ == '__main__':
    unittest.main()
