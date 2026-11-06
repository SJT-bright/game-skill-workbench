#!/usr/bin/env python3
"""生成时预防 R4F1: `tiktok_finalize.py sync` closes three gaps the census found (Round 4 剩余清单 #17, #28, R4A).

  #17 art_static   a squashed SIMPLE/CUSTOM sprite (丛林荡藤 v4 btn_reward 255x296 drawn 120x90, 1.55x) is reported by
                   sync, before the build: new remake game blocks K_art_aspect, English game only warns; the scan stays
                   read only (project bytes unchanged) and under 1 s on the fixture. Before, only `source` saw it.
  #28 run_parts    a new remake game gets assets/tiktok-platform/RunSession.js and FxPool.js (KIT_MANIFEST bytes) from
                   sync; 3.x also gets the import-as-plugin .meta; a second sync changes nothing; English (localize)
                   and legacy games get neither; a game script already named RunSession.js is not overwritten (warning).
                   Before, both parts were copied by hand when someone remembered (割草 / 方块迷阵 shape bugs).
  R4A rewarded24   a 2.4 build that keeps its own main.js (engine 2.4.9, outside startup24.needs) gets rewarded-guard.js
                   and one marked game.js line after adaptEngine() and before require('./main'); a second run adds no
                   second line; a kit-main build (2.4.15) gets no game.js line (main.js v1.7 loads it); legacy: nothing.
Run: python3 test_r4f1_sync_closure.py
"""
import hashlib
import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize as F  # noqa: E402
import test_finalize_sync as S  # noqa: E402  (project24 / build24 fixtures)

MAN = json.loads((HERE.parent / 'assets' / 'platform-kit' / 'KIT_MANIFEST.json').read_text(encoding='utf-8'))
FRAME = 'bbbbbbbb-0000-4000-8000-000000000001'
GUARD_MARK = '// tiktok-kit:rewarded24:'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree_sha(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob('*')):
        if p.is_file() and '.tiktok-kit' not in p.parts:
            h.update(p.relative_to(root).as_posix().encode() + b'\0' + p.read_bytes())
    return h.hexdigest()


def add_squashed_button(p):
    """丛林荡藤 v4 shape: a 255x296 picture on a 120x90 SIMPLE sprite with size mode CUSTOM."""
    objs = [{'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
            {'__type__': 'cc.Node', '_name': 'btn_reward', '_active': True, '_parent': None, '_children': [],
             '_components': [{'__id__': 2}], '_contentSize': {'width': 120, 'height': 90}},
            {'__type__': 'cc.Sprite', '_enabled': True, 'node': {'__id__': 1}, '_sizeMode': 0, '_type': 0,
             '_spriteFrame': {'__uuid__': FRAME}}]
    (p / 'assets' / 'ui').mkdir(parents=True, exist_ok=True)
    (p / 'assets' / 'ui' / 'pop.prefab').write_text(json.dumps(objs))
    (p / 'assets' / 'ui' / 'btn.png.meta').write_text(json.dumps({
        'ver': '2.3.7', 'uuid': FRAME[:-1] + 'f', 'importer': 'texture', 'width': 255, 'height': 296,
        'subMetas': {'btn': {'uuid': FRAME, 'width': 255, 'height': 296, 'rawWidth': 255, 'rawHeight': 296,
                             'trimX': 0, 'trimY': 0}}}))


def project3x(root):
    (root / 'assets' / 'scenes').mkdir(parents=True)
    (root / 'assets' / 'scenes' / 'Main.scene.meta').write_text('{"ver": "1.1.50", "uuid": "%s", "importer": "scene"}'
                                                                % S.SCENE)
    (root / 'package.json').write_text('{"name": "g", "creator": {"version": "3.8.6"}}')
    return root


def own_main_build(root, version='2.4.9'):
    S.build24(root)
    (root / 'cocos' / 'cocos2d-js-min.js').write_text('var ENGINE_VERSION = "%s"; window.cc = {};\n' % version)
    return root


def step(rec, name):
    return next(s for s in rec['steps'] if s['step'] == name)


def guard_blocks(rec):
    return [b for b in rec['blocks'] if b.get('step') == 'rewarded' or 'rewarded' in b.get('message', '')]


def ids(items):
    return sorted({i['id'] for i in items})


class ArtStaticInSync(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4f1-art-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_squashed_picture_reported_before_the_build(self):
        p = S.project24(self.tmp / 'p')
        F.finalize_sync(p, 'remake')
        add_squashed_button(p)
        before = tree_sha(p)
        t = time.time()
        rec = F.finalize_sync(p, 'remake')
        took = time.time() - t
        self.assertIn('art_static', [s['step'] for s in rec['steps']])
        self.assertIn('K_art_aspect', ids(rec['blocks']))
        self.assertEqual(tree_sha(p), before, 'art_static in sync is read only')
        self.assertLess(took, 1.0, 'sync with art_static took %.2f s on the fixture' % took)

    def test_english_game_only_warns(self):
        p = S.project24(self.tmp / 'p')
        add_squashed_button(p)
        rec = F.finalize_sync(p, 'localize')
        self.assertNotIn('K_art_aspect', ids(rec['blocks']))
        self.assertIn('K_W_art_aspect', ids(rec['warnings']))

    def test_clean_project_has_no_art_finding(self):
        rec = F.finalize_sync(S.project24(self.tmp / 'p'), 'remake')
        self.assertEqual(rec['blocks'], [])
        self.assertEqual(step(rec, 'art_static')['blocks'], [])


class RunPartsInSync(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4f1-run-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def check_installed(self, p):
        for key in ('parts/RunSession.js', 'parts/FxPool.js'):
            spec = MAN['files'][key]
            self.assertEqual(sha(p / spec['project_path']), spec['sha256'], key)

    def test_new_remake_24_gets_both_and_second_sync_is_quiet(self):
        p = S.project24(self.tmp / 'p')
        rec = F.finalize_sync(p, 'remake')
        self.assertEqual(rec['blocks'], [])
        self.check_installed(p)
        self.assertFalse((p / 'assets' / 'tiktok-platform' / 'RunSession.js.meta').exists(), '2.4: no plugin meta')
        (p / 'assets' / 'tiktok-platform' / 'FxPool.js').write_text('// edited by hand\n')
        again = F.finalize_sync(p, 'remake')
        self.assertEqual(again['changed'], ['assets/tiktok-platform/FxPool.js'])
        self.check_installed(p)
        self.assertEqual(F.finalize_sync(p, 'remake')['changed'], [])

    def test_new_remake_3x_gets_plugin_meta(self):
        p = project3x(self.tmp / 'p')
        F.finalize_sync(p, 'remake')
        self.check_installed(p)
        for name in ('RunSession.js', 'FxPool.js'):
            meta = json.loads((p / 'assets' / 'tiktok-platform' / (name + '.meta')).read_text())
            self.assertTrue(meta['userData']['isPlugin'] and meta['userData']['loadPluginInMiniGame'], name)

    def test_english_and_legacy_get_none(self):
        p = S.project24(self.tmp / 'en')
        rec = F.finalize_sync(p, 'localize')
        self.assertEqual(step(rec, 'run_parts')['state'], 'n/a')
        self.assertFalse((p / 'assets' / 'tiktok-platform' / 'RunSession.js').exists())
        old = S.project24(self.tmp / 'old')
        legacy = {'games': [{'name': 'g', 'folder': 'J/g', 'scene_uuids': [S.SCENE]}]}
        F.finalize_sync(old, 'remake', legacy=legacy)
        self.assertFalse((old / 'assets' / 'tiktok-platform' / 'FxPool.js').exists())

    def test_game_script_with_the_same_name_is_kept(self):
        p = S.project24(self.tmp / 'p')
        (p / 'assets' / 'scripts').mkdir(parents=True)
        (p / 'assets' / 'scripts' / 'RunSession.js').write_text('module.exports = {mine: 1};\n')
        rec = F.finalize_sync(p, 'remake')
        self.assertIn('K_W_kit_module_duplicate', ids(step(rec, 'run_parts')['warnings']))
        self.assertFalse((p / 'assets' / 'tiktok-platform' / 'RunSession.js').exists())
        self.assertTrue((p / 'assets' / 'tiktok-platform' / 'FxPool.js').exists())


class RewardedGuardOwnMain(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4f1-guard-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_own_main_gets_one_guard_line_in_the_right_place(self):
        p = S.project24(self.tmp / 'p')
        b = own_main_build(self.tmp / 'build')
        rec = F.finalize_native(b, p, 'localize')
        self.assertEqual(guard_blocks(rec), [])   # the fixture has no login / real App ID: only this step counts
        self.assertNotEqual(sha(b / 'main.js'), MAN['parts']['startup24']['file']['sha256'], 'keeps its own main.js')
        self.assertEqual(sha(b / 'rewarded-guard.js'), MAN['parts']['rewarded24']['file']['sha256'])
        game = (b / 'game.js').read_text()
        self.assertEqual(game.count(GUARD_MARK), 1)
        at = game.index(GUARD_MARK)
        self.assertLess(game.index('__globalAdapter.adaptEngine()'), at)
        self.assertLess(at, game.index("require('./main')"))
        F.finalize_native(b, p, 'localize')
        self.assertEqual((b / 'game.js').read_text().count(GUARD_MARK), 1, 'second run adds no second line')

    def test_sync_native_does_the_same(self):
        p = S.project24(self.tmp / 'p')
        b = own_main_build(self.tmp / 'build')
        rec = F.finalize_sync(p, 'localize', native=b)
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        self.assertEqual((b / 'game.js').read_text().count(GUARD_MARK), 1)

    def test_kit_main_is_not_wired_twice(self):
        p = S.project24(self.tmp / 'p')
        b = own_main_build(self.tmp / 'build', '2.4.15')
        rec = F.finalize_native(b, p, 'localize')
        self.assertEqual(guard_blocks(rec), [])   # the fixture has no login / real App ID: only this step counts
        self.assertEqual(sha(b / 'main.js'), MAN['parts']['startup24']['file']['sha256'])
        self.assertIn("require('./rewarded-guard')(cc, platform)", (b / 'main.js').read_text())
        self.assertNotIn(GUARD_MARK, (b / 'game.js').read_text())
        self.assertEqual(sha(b / 'rewarded-guard.js'), MAN['parts']['rewarded24']['file']['sha256'])

    def test_legacy_build_untouched(self):
        p = S.project24(self.tmp / 'p')
        b = own_main_build(self.tmp / 'build')
        legacy = {'games': [{'name': 'g', 'folder': 'J/g', 'scene_uuids': [S.SCENE]}]}
        F.finalize_sync(p, 'localize', native=b, legacy=legacy)
        self.assertFalse((b / 'rewarded-guard.js').exists())
        self.assertNotIn(GUARD_MARK, (b / 'game.js').read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
