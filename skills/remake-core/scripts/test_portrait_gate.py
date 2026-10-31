#!/usr/bin/env python3
"""v7.8 (总表 B31) portrait gate: package half package_gates/portrait.py (game.json deviceOrientation) and source half
tiktok_finalize_steps/orientation.py (cc.Canvas _designResolution, 3.x designResolution). Bad fixtures are refused,
fixed ones pass, and both halves are wired into what the package entries run. Synthetic fixtures only (the bad one
copies 校准样例/坏_横屏: one scene, Canvas 1280x720). Run: python3 -B test_portrait_gate.py"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_gates as gates  # noqa: E402
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from package_gates import portrait  # noqa: E402
from tiktok_finalize_steps import orientation  # noqa: E402


def pkg(game):
    return {'game.json': json.dumps(game).encode(), 'project.config.json': b'{}', 'game.js': b'',
            'cocos/cocos2d-js-min.js': b'/* engine */', 'adapter-min.js': b'/* adapter */'}


def ids(files, policy='new'):
    return sorted(f['id'] for f in portrait.check(gates.PackageView(files, policy=policy)) if f['level'] == 'block')


def scene(width, height, kind='cc.SceneAsset'):
    return json.dumps([{'__type__': kind}, {'__type__': 'cc.Node', '_name': 'Canvas'},
                       {'__type__': 'cc.Canvas', '_designResolution': {'__type__': 'cc.Size', 'width': width,
                                                                       'height': height},
                        '_fitWidth': True, '_fitHeight': False}])


class PackageHalf(unittest.TestCase):
    def test_landscape_refused_both_policies(self):
        for policy in ('new', 'legacy'):
            self.assertEqual(ids(pkg({'deviceOrientation': 'landscape'}), policy), ['O1_device_orientation'])

    def test_odd_value_refused_missing_key_is_the_portrait_default(self):
        self.assertEqual(ids(pkg({'deviceOrientation': 'Portrait'})), ['O1_device_orientation'])
        self.assertEqual(ids(pkg({'deviceOrientation': ''})), ['O1_device_orientation'])
        self.assertEqual(ids(pkg({'deviceOrientation': None})), ['O1_device_orientation'])
        self.assertEqual(ids(pkg({'subpackages': []})), [])       # no key: TikTok's default is portrait

    def test_portrait_passes(self):
        self.assertEqual(ids(pkg({'deviceOrientation': 'portrait', 'subpackages': []}), 'new'), [])
        self.assertEqual(ids(pkg({'deviceOrientation': 'portrait'}), 'legacy'), [])

    def test_registered_and_run_by_every_entry(self):
        self.assertIn('portrait', gates.GATE_MODULES)
        bad = gates.run(pkg({'deviceOrientation': 'landscape'}), policy='legacy')
        self.assertIn('portrait', bad['gates'])
        self.assertIn('O1_device_orientation', [f['id'] for f in bad['blocks']])
        good = gates.run(pkg({'deviceOrientation': 'portrait'}), policy='legacy')
        self.assertNotIn('O1_device_orientation', [f['id'] for f in good['blocks']])


class SourceHalf(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='portrait-'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def project(self, name, files, version='2.4.15'):
        root = self.tmp / name
        (root / 'assets').mkdir(parents=True)
        (root / 'project.json').write_text(json.dumps({'engine': 'cocos-creator-js', 'version': version}))
        for rel, text in files.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text, encoding='utf-8')
        return root

    def step(self, root, policy='new'):
        out = orientation.apply(T.Ctx('source', root, policy=policy))
        return [b['id'] for b in out['blocks']], [w['id'] for w in out['warnings']], out['state']

    def test_bad_sample_landscape_canvas_refused(self):
        # 校准样例/坏_横屏/assets/main.fire, byte for byte
        bad = '[{"__type__":"cc.SceneAsset"},{"__type__":"cc.Canvas","_designResolution":{"__type__":"cc.Size",' \
              '"width":1280,"height":720}}]'
        root = self.project('bad', {'assets/main.fire': bad})
        for policy in ('new', 'legacy'):
            self.assertEqual(self.step(root, policy)[0], ['K_portrait_design'])
        self.assertEqual(orientation.detect(T.Ctx('source', root)), 'conflict')

    def test_portrait_canvas_passes(self):
        root = self.project('good', {'assets/Game.fire': scene(720, 1280), 'assets/ui/Popup.prefab':
                                     scene(750, 1334, 'cc.Prefab')})
        self.assertEqual(self.step(root), ([], [], 'kit_current'))

    def test_one_landscape_scene_among_portrait_refused(self):
        root = self.project('mixed', {'assets/Game.fire': scene(720, 1280), 'assets/scenes/Result.fire':
                                      scene(1280, 720)})
        self.assertEqual(self.step(root)[0], ['K_portrait_design'])

    def test_landscape_prefab_refused(self):
        root = self.project('prefab', {'assets/Game.fire': scene(720, 1280),
                                       'assets/ui/Hud.prefab': scene(960, 640, 'cc.Prefab')})
        self.assertEqual(self.step(root)[0], ['K_portrait_design'])

    def test_square_passes(self):
        self.assertEqual(self.step(self.project('square', {'assets/Game.fire': scene(1000, 1000)}))[0], [])

    def test_build_and_library_folders_ignored(self):
        root = self.project('ignored', {'assets/Game.fire': scene(720, 1280),
                                        'library/imports/aa/x.fire': scene(1280, 720),
                                        'build/bytedance/assets/y.fire': scene(1280, 720)})
        self.assertEqual(self.step(root)[0], [])

    def test_cocos3_setting_landscape_refused_portrait_passes(self):
        bad = json.dumps({'general': {'designResolution': {'width': 1280, 'height': 720, 'fitWidth': True}}})
        root = self.project('c3bad', {'settings/v2/packages/project.json': bad}, '3.8.6')
        self.assertEqual(self.step(root)[0], ['K_portrait_design'])
        good = json.dumps({'general': {'designResolution': {'width': 720, 'height': 1280}}})
        root = self.project('c3good', {'settings/v2/packages/project.json': good}, '3.8.6')
        self.assertEqual(self.step(root), ([], [], 'kit_current'))

    def test_nothing_found_or_unreadable_only_warned(self):
        self.assertEqual(self.step(self.project('none', {})), ([], ['K_W_portrait_unknown'], 'n/a'))
        root = self.project('broken', {'assets/Game.fire': scene(720, 1280), 'assets/Bad.fire': '{not json'})
        self.assertEqual(self.step(root)[:2], ([], ['K_W_portrait_unreadable']))

    def test_wired_into_source_phase_and_writer_check(self):
        self.assertIn('orientation', T.SOURCE_STEPS)
        self.assertIn('orientation', F.SOURCE_STEPS)
        bad = self.project('wired-bad', {'assets/main.fire': scene(1280, 720)})
        rec = F.finalize_source(bad, 'remake')
        self.assertIn('K_portrait_design', [b['id'] for b in rec['blocks']])
        k5 = F.check_source_record(bad)
        self.assertTrue(any(f['id'] == 'K5_source_finalized' and 'K_portrait_design' in f['message'] for f in k5), k5)
        good = self.project('wired-good', {'assets/main.fire': scene(720, 1280)})
        rec = F.finalize_source(good, 'remake')
        self.assertNotIn('K_portrait_design', [b['id'] for b in rec['blocks']])
        self.assertIn('orientation', [s['step'] for s in rec['steps']])


if __name__ == '__main__':
    unittest.main(verbosity=2)
