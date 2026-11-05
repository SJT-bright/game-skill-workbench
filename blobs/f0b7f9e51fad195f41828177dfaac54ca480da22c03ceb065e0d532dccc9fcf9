#!/usr/bin/env python3
"""生成时预防 P06 第 4 点: the source step capsule_auto puts CapsuleLayout + CapsuleAuto into new games by default.

Census: element overlap first (99 times in 64 games), 16 top bars / coin counters under the TikTok capsule; the kit's
CapsuleLayout.js was opt-in, so nothing installed it. Cases:
  1 old way     the steps that ran before (kit_sources) leave a new 2.4 game without CapsuleLayout / CapsuleAuto
  2 remake      capsule_auto copies both kit files to assets/tiktok-platform/ (KIT_MANIFEST bytes) and lists TopBar and
                Settings (the full-screen bg and a mid-screen CoinPanel are not top bars); second run: no change
  3 localize    English game: nothing written, warning K_W_capsule_auto naming TopBar
  4 legacy      legacy game: nothing written, warning
  5 conflict    the game has its own different CapsuleLayout.js elsewhere: nothing written, K_W_capsule_auto_conflict
  6 unregistered  kit without a CapsuleAuto entry in KIT_MANIFEST files: K_kit_unusable block (never a guessed hash)
  7 runtime     node tests/capsule-auto.test.js passes (the part moves the bar on a fake 2.4 engine)
Run: python3 test_capsule_auto.py
"""
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import capsule_auto, kit_sources  # noqa: E402

MAN = json.loads(T.MANIFEST.read_text(encoding='utf-8'))
AUTO = 'parts/CapsuleAuto.js'


def manifest(register=True):
    data = copy.deepcopy(MAN)
    if register and AUTO not in data['files']:          # the I3 handoff entry (KIT_MANIFEST is merged at release)
        data['files'][AUTO] = {'sha256': hashlib.sha256((T.KIT_DIR / AUTO).read_bytes()).hexdigest(),
                               'project_path': 'assets/tiktok-platform/CapsuleAuto.js', 'engine': 2}
    if not register:
        data['files'].pop(AUTO, None)
    return T.Manifest(data, T.KIT_DIR)


def node(name, parent, x, y, w, h, comps=(), kids=()):
    return {'__type__': 'cc.Node', '_name': name, '_parent': None if parent is None else {'__id__': parent},
            '_children': [{'__id__': k} for k in kids], '_components': [{'__id__': c} for c in comps], '_active': True,
            '_contentSize': {'__type__': 'cc.Size', 'width': w, 'height': h}, '_anchorPoint': {'x': 0.5, 'y': 0.5},
            '_trs': {'__type__': 'TypedArray', 'ctor': 'Float64Array', 'array': [x, y, 0, 0, 0, 0, 1, 1, 1, 1]}}


def home_fire():
    # 0 asset, 1 scene, 2 Canvas, 3 cc.Canvas, 4 bg, 5 sprite, 6 TopBar, 7 coinLabel, 8 CoinPanel (mid), 9 Settings
    objs = [{'__type__': 'cc.SceneAsset'}, {'__type__': 'cc.Scene', '_children': [{'__id__': 2}]},
            node('Canvas', 1, 360, 640, 720, 1280, comps=[3], kids=[4, 6, 8, 9]),
            {'__type__': 'cc.Canvas', 'node': {'__id__': 2}, '_designResolution': {'width': 720, 'height': 1280}},
            node('bg', 2, 0, 0, 720, 1280, comps=[5]), {'__type__': 'cc.Sprite', 'node': {'__id__': 4}},
            node('TopBar', 2, 0, 580, 720, 120, kids=[7]), node('coinLabel', 6, 250, 0, 120, 60),
            node('CoinPanel', 2, 0, -80, 600, 300), node('Settings', 2, 290, 570, 100, 100)]
    return json.dumps(objs)


def project(root, own_capsule=False):
    (root / 'assets' / 'scenes').mkdir(parents=True)
    (root / 'assets' / 'scenes' / 'Home.fire').write_text(home_fire())
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    if own_capsule:
        (root / 'assets' / 'scripts').mkdir()
        (root / 'assets' / 'scripts' / 'CapsuleLayout.js').write_text('module.exports = {mine: true};\n')
    return root


def ctx(root, board='remake', policy='new', register=True):
    return T.Ctx('source', root, project=root, board=board, engine=2, policy=policy, manifest=manifest(register))


class CapsuleAuto(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='capsule_auto_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_old_way_nothing_installs_it(self):
        root = project(self.tmp / 'p')
        kit_sources.apply(ctx(root))
        self.assertEqual(list((root / 'assets').rglob('Capsule*.js')), [])

    def test_2_remake_installs_kit_bytes_and_lists_bars(self):
        root = project(self.tmp / 'p')
        out = capsule_auto.apply(ctx(root))
        self.assertEqual(out['blocks'], [])
        for key in ('parts/CapsuleLayout.js', AUTO):
            dest = root / 'assets' / 'tiktok-platform' / key.split('/')[-1]
            self.assertEqual(dest.read_bytes(), (T.KIT_DIR / key).read_bytes(), key)
        self.assertEqual(len(out['changed']), 2)
        bars = capsule_auto.scan(capsule_auto.project_files(root))['bars']
        self.assertEqual(sorted(b['node'].split('/')[-1] for b in bars), ['Settings', 'TopBar'])
        again = capsule_auto.apply(ctx(root))
        self.assertEqual(again['changed'], [])
        self.assertEqual(again['state'], 'kit_current')

    def test_3_localize_warns_only(self):
        root = project(self.tmp / 'p')
        out = capsule_auto.apply(ctx(root, board='localize'))
        self.assertFalse((root / 'assets' / 'tiktok-platform').exists())
        self.assertEqual([w['id'] for w in out['warnings']], ['K_W_capsule_auto'])
        self.assertIn('TopBar', out['warnings'][0]['message'])
        self.assertEqual(out['blocks'], [])

    def test_4_legacy_warns_only(self):
        root = project(self.tmp / 'p')
        out = capsule_auto.apply(ctx(root, policy='legacy'))
        self.assertFalse((root / 'assets' / 'tiktok-platform').exists())
        self.assertEqual([w['id'] for w in out['warnings']], ['K_W_capsule_auto'])

    def test_5_own_copy_elsewhere_is_not_doubled(self):
        root = project(self.tmp / 'p', own_capsule=True)
        out = capsule_auto.apply(ctx(root))
        self.assertFalse((root / 'assets' / 'tiktok-platform').exists())
        self.assertEqual([w['id'] for w in out['warnings']], ['K_W_capsule_auto_conflict'])

    def test_6_unregistered_part_refuses(self):
        root = project(self.tmp / 'p')
        out = capsule_auto.apply(ctx(root, register=False))
        self.assertEqual([b['id'] for b in out['blocks']], ['K_kit_unusable'])
        self.assertFalse((root / 'assets' / 'tiktok-platform').exists())

    def test_7_runtime_part(self):
        r = subprocess.run(['node', str(T.KIT_DIR / 'tests' / 'capsule-auto.test.js')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
