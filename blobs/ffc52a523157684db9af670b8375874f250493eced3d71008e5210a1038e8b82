#!/usr/bin/env python3
"""生成时预防 R4Q1 (补查3 group 1): tiktok_finalize_steps/slot_overlap_scan.py reports old and new art both active on a
button slot, at source / sync, read only.

Sample shaped after 奔跑吧巨人 / 合成进化恐龙 (11-05): the x2 button got a whole new picture, lbBtnMultiple still drew
"双倍领取" over it, the button's Widget and the result panel's Layout both moved it.
  1 hits     old way -> text_over_picture + two_layout_owners, warning K_W_slot_overlap (new game and English)
  2 bound    a slot in docs/art/bind_log.json with an English label still on -> text_over_picture
  3 fixed    the same prefab bound with remake-art bind_art.py (button slot) -> clean
  4 legacy   not checked
  5 wired    in SOURCE_STEPS; in SYNC_SOURCE_STEPS before ui_kit_scan (still last); finalize_sync carries the warning
Old code: the step does not exist (ImportError), nothing reports these.
Run: python3 test_slot_overlap_scan.py
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

ART = HERE.parent.parent / 'remake-art' / 'scripts'
OLD = '0a0a0a0a-1111-4000-8000-00000000000f'


def node(name, parent, comps, children=(), w=200, h=200):
    return {'__type__': 'cc.Node', '_name': name, '_parent': parent, '_active': True,
            '_children': [{'__id__': c} for c in children], '_components': [{'__id__': c} for c in comps],
            '_contentSize': {'__type__': 'cc.Size', 'width': w, 'height': h},
            '_trs': {'__type__': 'TypedArray', 'ctor': 'Float64Array', 'array': [0, 0, 0, 0, 0, 0, 1, 1, 1, 1]}}


def prefab(frame=OLD, text='双倍领取'):
    return [{'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
            node('Result', None, [2], [3], 720, 1280),
            {'__type__': 'cc.Layout', 'node': {'__id__': 1}, '_enabled': True, '_N$layoutType': 2},
            node('btn_x2', {'__id__': 1}, [4, 5, 6], [7]),
            {'__type__': 'cc.Sprite', 'node': {'__id__': 3}, '_spriteFrame': {'__uuid__': frame}, '_type': 0,
             '_sizeMode': 0, '_isTrimmedMode': True},
            {'__type__': 'cc.Button', 'node': {'__id__': 3}, '_N$transition': 3, '_N$target': {'__id__': 3}},
            {'__type__': 'cc.Widget', 'node': {'__id__': 3}, '_enabled': True, '_alignFlags': 36},
            node('lbBtnMultiple', {'__id__': 3}, [8], w=150, h=50),
            {'__type__': 'cc.Label', 'node': {'__id__': 7}, '_enabled': True, '_string': text}]


def project(tmp, data=None, board='remake'):
    root = Path(tmp)
    (root / 'assets' / 'prefabs').mkdir(parents=True, exist_ok=True)
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}', encoding='utf-8')
    (root / 'assets/prefabs/Result.prefab').write_text(json.dumps(data or prefab()), encoding='utf-8')
    P.write_marker(root, board, '2.0', reason='init')
    return root


def run(root, policy='new', board='remake'):
    from tiktok_finalize_steps import slot_overlap_scan as S
    return S.apply(T.Ctx('source', root, policy=policy, board=board))


class SlotOverlapScan(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='slot_overlap_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_old_way_warns(self):
        for board in ('remake', 'localize'):
            root = project(Path(tempfile.mkdtemp(dir=self.tmp)), board=board)
            r = run(root, board=board)
            self.assertEqual(r['blocks'], [])
            self.assertEqual([w['id'] for w in r['warnings']], ['K_W_slot_overlap'])
            kinds = sorted(h['kind'] for h in r['warnings'][0]['evidence'])
            self.assertEqual(kinds, ['text_over_picture', 'two_layout_owners'])

    def test_2_bound_slot_english_label_on(self):
        root = project(self.tmp, prefab(text='X2'))
        from tiktok_finalize_steps import slot_overlap_scan as S
        self.assertEqual([h['kind'] for h in S.scan(root)['hits']], ['two_layout_owners'])  # English text, not bound
        (root / 'docs/art').mkdir(parents=True)
        (root / 'docs/art/bind_log.json').write_text(json.dumps(
            {'bindings': {'assets/prefabs/Result.prefab#Result/btn_x2': {}}}), encoding='utf-8')
        hits = S.scan(root)['hits']
        self.assertIn('text_over_picture', [h['kind'] for h in hits])
        self.assertTrue(next(h for h in hits if h['kind'] == 'text_over_picture')['bound_by_bind_art'])

    def test_3_bind_art_slot_is_clean(self):
        from PIL import Image
        root = project(self.tmp)
        ui = root / 'assets' / 'ui'
        ui.mkdir()
        Image.new('RGBA', (300, 120), (200, 120, 40, 255)).save(ui / 'x2_en.png')
        Image.new('RGBA', (200, 200), (90, 90, 200, 255)).save(ui / 'old.png')
        for name, uu, size in (('x2_en', '0b0b0b0b-1111-4000-8000-000000000001', (300, 120)),
                               ('old', OLD[:-2] + 'aa', (200, 200))):
            sub = {'ver': '1.0.6', 'uuid': uu if name == 'x2_en' else OLD, 'trimType': 'auto', 'trimThreshold': 1,
                   'trimX': 0, 'trimY': 0, 'width': size[0], 'height': size[1], 'rawWidth': size[0],
                   'rawHeight': size[1]}
            (ui / (name + '.png.meta')).write_text(json.dumps({'ver': '2.3.7', 'uuid': uu + '-t', 'type': 'sprite',
                                                               'subMetas': {name: sub}}))
        sys.path.insert(0, str(ART))
        import bind_art
        m = root / 'bind.json'
        m.write_text(json.dumps({'bindings': [{'prefab': 'assets/prefabs/Result.prefab', 'node': 'Result/btn_x2',
                                               'image': 'assets/ui/x2_en.png'}]}))
        bind_art.run_bind(root, m, '', False)
        r = run(root)
        self.assertEqual((r['blocks'], r['warnings']), ([], []))

    def test_4_legacy_not_checked(self):
        r = run(project(self.tmp), policy='legacy')
        self.assertEqual((r['blocks'], r['warnings']), ([], []))
        self.assertIn('not checked', r['info'][0])

    def test_5_wired(self):
        self.assertIn('slot_overlap_scan', T.SOURCE_STEPS)
        self.assertEqual(F.SYNC_SOURCE_STEPS[-1], 'ui_kit_scan')
        self.assertLess(F.SYNC_SOURCE_STEPS.index('slot_overlap_scan'), F.SYNC_SOURCE_STEPS.index('ui_kit_scan'))
        root = project(self.tmp)
        P.write_marker(root, 'remake', T.load_manifest().version, reason='init')
        rec = F.finalize_sync(root, 'remake', write_record=False)
        self.assertIn('slot_overlap_scan', [s.get('step') for s in rec['steps']])
        self.assertIn('K_W_slot_overlap', {w['id'] for w in rec['warnings']})


if __name__ == '__main__':
    unittest.main()
