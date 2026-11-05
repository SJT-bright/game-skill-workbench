#!/usr/bin/env python3
"""生成时预防 P07 第 3 点: the source step bg_cover requires ScreenFit.cover on the home / play / result backgrounds.

Census: screen_fit_wrong 28 times (backgrounds sized to the design leave bars on long phones, both Canvas fits squash
the picture). Cases:
  1 old way     a home scene whose bg is a plain 720x1280 sprite (sized to the design, no cover call): new remake game
                -> K_bg_cover block; the same project before this step had no finding at all (art_static is clean)
  2 component   the bg node carries a script that calls ScreenFit.cover(cc, this.node, ...) -> no finding
  3 property    a page script elsewhere in the scene has a property pointing at bg and calls ScreenFit.cover -> none
  4 literal     a script calls ScreenFit.cover(cc, cc.find('Canvas/bg')) -> no finding
  5 localize / legacy  the bad project gives K_W_bg_cover (warning), never a block
  6 no part     a kit without parts/ScreenFit.js in KIT_MANIFEST: warning only, even for a new game
  7 pages only  a non-page prefab (Coin.prefab) with a big sprite is not checked; GameOver.prefab is
Run: python3 test_bg_cover.py
"""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import art_static, bg_cover  # noqa: E402

MAN = json.loads(T.MANIFEST.read_text(encoding='utf-8'))
SCRIPT_UUID = '4f1a2b3c-5d6e-4f70-8a9b-0c1d2e3f4a5b'


def manifest(screenfit=True):
    data = copy.deepcopy(MAN)
    if screenfit:
        data['files'].setdefault('parts/ScreenFit.js', {'sha256': '0' * 64, 'reference': True, 'optional': True})
    else:
        data['files'].pop('parts/ScreenFit.js', None)
    return T.Manifest(data, T.KIT_DIR)


def node(name, parent, w, h, comps=(), kids=()):
    return {'__type__': 'cc.Node', '_name': name, '_parent': None if parent is None else {'__id__': parent},
            '_children': [{'__id__': k} for k in kids], '_components': [{'__id__': c} for c in comps],
            '_contentSize': {'__type__': 'cc.Size', 'width': w, 'height': h}, '_anchorPoint': {'x': 0.5, 'y': 0.5}}


def home_fire(bg_script=False, page_script=False):
    objs = [{'__type__': 'cc.SceneAsset'}, {'__type__': 'cc.Scene', '_children': [{'__id__': 2}]},
            node('Canvas', 1, 720, 1280, comps=[3], kids=[4, 6]),
            {'__type__': 'cc.Canvas', 'node': {'__id__': 2}, '_designResolution': {'width': 720, 'height': 1280}},
            node('bg', 2, 720, 1280, comps=[5]), {'__type__': 'cc.Sprite', 'node': {'__id__': 4}},
            node('PlayButton', 2, 200, 80)]
    if bg_script:
        objs.append({'__type__': bg_cover.compress_uuid(SCRIPT_UUID), 'node': {'__id__': 4}})
        objs[4]['_components'].append({'__id__': len(objs) - 1})
    if page_script:
        objs.append({'__type__': bg_cover.compress_uuid(SCRIPT_UUID), 'node': {'__id__': 2}, 'bgNode': {'__id__': 4}})
        objs[2]['_components'].append({'__id__': len(objs) - 1})
    return json.dumps(objs)


def script(root, text):
    d = root / 'assets' / 'scripts'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'Page.js').write_text(text)
    (d / 'Page.js.meta').write_text(json.dumps({'ver': '1.0.8', 'uuid': SCRIPT_UUID}))


def project(root, **kw):
    (root / 'assets' / 'scenes').mkdir(parents=True)
    (root / 'assets' / 'scenes' / 'Home.fire').write_text(home_fire(**kw))
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    return root


def run(root, board='remake', policy='new', screenfit=True):
    c = T.Ctx('source', root, project=root, board=board, engine=2, policy=policy, manifest=manifest(screenfit))
    return bg_cover.apply(c)


COVER_SELF = "var ScreenFit = require('ScreenFit');\ncc.Class({extends: cc.Component, onLoad: function () {\n" \
             "  ScreenFit.cover(cc, this.node, {watch: true}); }});\n"
COVER_PROP = "var ScreenFit = require('ScreenFit');\ncc.Class({extends: cc.Component, properties: {bgNode: cc.Node},\n" \
             "  onLoad: function () { ScreenFit.cover(cc, this.bgNode, {watch: true}); }});\n"
COVER_FIND = "var ScreenFit = require('ScreenFit');\nmodule.exports = function () {\n" \
             "  ScreenFit.cover(cc, cc.find('Canvas/bg')); };\n"


class BgCover(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='bg_cover_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_compress_uuid_matches_cocos(self):
        # real pairs from a Cocos 2.4.15 project (EsmesPulpPress source: script .meta uuid -> Main.fire __type__)
        for uuid, packed in (('b60e7599-2342-4571-9296-e022fe0d5d34', 'b60e7WZI0JFcZKW4CL+DV00'),
                             ('cd14b5f1-db12-4d61-ab53-860668b73148', 'cd14bXx2xJNYatThgZotzFI'),
                             ('50635dc9-dbf6-497c-b374-d6d18477be92', '506353J2/ZJfLN01tGEd76S')):
            self.assertEqual(bg_cover.compress_uuid(uuid), packed)

    def test_1_old_way_design_sized_bg_blocks(self):
        root = project(self.tmp / 'p')
        old = art_static.apply(T.Ctx('source', root, project=root, board='remake', engine=2, policy='new',
                                     manifest=manifest()))
        self.assertEqual(old['blocks'] + old['warnings'], [], 'before this step nothing looked at the background')
        out = run(root)
        self.assertEqual([b['id'] for b in out['blocks']], ['K_bg_cover'])
        self.assertIn('Canvas/bg', out['blocks'][0]['message'])

    def test_2_component_on_bg(self):
        root = project(self.tmp / 'p', bg_script=True)
        script(root, COVER_SELF)
        out = run(root)
        self.assertEqual(out['blocks'] + out['warnings'], [])

    def test_3_property_points_at_bg(self):
        root = project(self.tmp / 'p', page_script=True)
        script(root, COVER_PROP)
        self.assertEqual(run(root)['blocks'], [])

    def test_3b_script_without_cover_does_not_count(self):
        root = project(self.tmp / 'p', page_script=True)
        script(root, COVER_PROP.replace('ScreenFit.cover(cc, this.bgNode, {watch: true});',
                                        'this.bgNode.setContentSize(720, 1280);'))
        self.assertEqual([b['id'] for b in run(root)['blocks']], ['K_bg_cover'])

    def test_4_find_by_name(self):
        root = project(self.tmp / 'p')
        script(root, COVER_FIND)
        self.assertEqual(run(root)['blocks'], [])

    def test_5_localize_and_legacy_warn(self):
        root = project(self.tmp / 'p')
        for kw in ({'board': 'localize'}, {'policy': 'legacy'}):
            out = run(root, **kw)
            self.assertEqual(out['blocks'], [], kw)
            self.assertEqual([w['id'] for w in out['warnings']], ['K_W_bg_cover'], kw)

    def test_6_kit_without_screenfit_warns(self):
        root = project(self.tmp / 'p')
        out = run(root, screenfit=False)
        self.assertEqual(out['blocks'], [])
        self.assertEqual([w['id'] for w in out['warnings']], ['K_W_bg_cover'])

    def test_7_page_prefabs_only(self):
        root = self.tmp / 'p'
        (root / 'assets' / 'prefabs').mkdir(parents=True)
        (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
        objs = [{'__type__': 'cc.Prefab'}, node('Root', None, 720, 1280, kids=[2]),
                node('panelBg', 1, 720, 1280, comps=[3]), {'__type__': 'cc.Sprite', 'node': {'__id__': 2}}]
        objs[1]['_parent'] = None
        (root / 'assets' / 'prefabs' / 'Coin.prefab').write_text(json.dumps(objs))
        self.assertEqual(run(root)['blocks'], [])
        (root / 'assets' / 'prefabs' / 'GameOver.prefab').write_text(json.dumps(objs))
        out = run(root)
        self.assertEqual([b['id'] for b in out['blocks']], ['K_bg_cover'])
        self.assertIn('GameOver.prefab', out['blocks'][0]['message'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
