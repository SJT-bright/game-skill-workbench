#!/usr/bin/env python3
"""生成时预防 P02: `tiktok_finalize.py sync` puts the standard parts back before every build, in about a second.

Before, the parts were only installed by `source` right before packaging, so trial builds ran without them
(射击高手 v81 and 小熊拳击 R27 shipped without touch-coordinates.js, 指尖麻将 v55 lost a patch on rebuild,
拇指弹球 kept an old RewardedService.js). Cases:
  1 old way     a project broken the way those games were (touch file deleted, RewardedService.js an older kit text,
                the storage-guard line taken out of main.js) stays broken until packaging: no step before the build
                looks at it (detect says own / absent)
  2 remake      sync restores all three to the KIT_MANIFEST sha256 and adds parts/GameUIKit.js; a second sync
                changes nothing
  3 native      sync --native on an English (localize) 2.4 build folder installs the kit main.js, touch and storage
  4 legacy      a legacy game is only reported: no file in the project or the build changes
  5 speed       one sync on the fixture takes under 3 seconds
Run: python3 test_finalize_sync.py
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
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import build_templates, kit_sources  # noqa: E402

KIT = T.KIT_DIR
MAN = json.loads(T.MANIFEST.read_text(encoding='utf-8'))
SCENE = '1b2c3d4e-0000-4000-8000-00000000abcd'
OLD_RS = 'd8c32935330fabb9c95b0bfd84392a78b73c0efaffd24a56d8ec5ac992ead3f1'
GAME24 = """"use strict";
require('adapter-min.js');
__globalAdapter.init();
require('cocos/cocos2d-js-min.js');
__globalAdapter.adaptEngine();
require('./ccRequire');
require('./src/settings');
require('./main');
window.boot();
"""


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree_sha(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob('*')):
        if p.is_file() and '.tiktok-kit' not in p.parts:
            h.update(p.relative_to(root).as_posix().encode() + b'\0' + p.read_bytes())
    return h.hexdigest()


def project24(root):
    (root / 'assets' / 'scenes').mkdir(parents=True)
    (root / 'assets' / 'scenes' / 'Main.fire.meta').write_text('{"ver": "1.2.9", "uuid": "%s", "importer": "scene"}'
                                                              % SCENE)
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    (root / 'assets' / 'tiktok-platform').mkdir()
    (root / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').write_text("var c = {appId: '1'};\n")
    return root


def build24(root):
    root.mkdir(parents=True)
    (root / 'cocos').mkdir()
    (root / 'cocos' / 'cocos2d-js-min.js').write_text('var ENGINE_VERSION = "2.4.15"; window.cc = {};\n')
    (root / 'adapter-min.js').write_text('/* adapter */\n')
    (root / 'game.js').write_text(GAME24)
    (root / 'main.js').write_text('window.boot = function () { /* editor main */ };\n')
    (root / 'ccRequire.js').write_text('/* ccRequire */\n')
    (root / 'src').mkdir()
    (root / 'src' / 'settings.js').write_text('window._CCSettings = {};\n')
    (root / 'game.json').write_text('{"deviceOrientation": "portrait"}\n')
    (root / 'project.config.json').write_text('{"appid": "1"}\n')
    return root


def break_like_old_games(p):
    """The three ways the old flow lost a part between builds."""
    (p / 'build-templates' / 'bytedance' / 'touch-coordinates.js').unlink()
    old = (KIT / 'tools' / 'kit_versions' / 'RewardedService' / (OLD_RS + '.txt')).read_bytes()
    (p / 'assets' / 'tiktok-platform' / 'RewardedService.js').write_bytes(old)
    main = p / 'build-templates' / 'bytedance' / 'main.js'
    text = main.read_text(encoding='utf-8')
    line = "  try { require('./storage-guard')(cc, platform); }"
    assert line in text, 'kit main.js no longer has the storage-guard line this test removes'
    main.write_text('\n'.join(l for l in text.split('\n') if not l.startswith(line)), encoding='utf-8')


def want(rel):
    """KIT_MANIFEST sha256 of a project file."""
    if rel == 'build-templates/bytedance/storage-guard.js':
        return MAN['parts']['storage24']['file']['sha256']
    if rel == 'assets/tiktok-platform/GameUIKit.js':
        return MAN['files']['parts/GameUIKit.js']['sha256']
    return MAN['files'][rel]['sha256']


CHECKED = ('build-templates/bytedance/touch-coordinates.js', 'build-templates/bytedance/main.js',
           'build-templates/bytedance/storage-guard.js', 'assets/tiktok-platform/RewardedService.js',
           'assets/tiktok-platform/GameUIKit.js')


class Sync(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='tfsync-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def remake(self):
        p = project24(self.tmp / 'p')
        rec = F.finalize_sync(p, 'remake')
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        for rel in CHECKED:
            self.assertEqual(sha(p / rel), want(rel), rel)
        return p

    def test_1_old_way_stays_broken_until_packaging(self):
        p = self.remake()
        break_like_old_games(p)
        ctx = T.Ctx('source', p, board='remake', engine=2, policy='new', manifest=T.load_manifest())
        self.assertNotEqual(kit_sources.detect(ctx), 'kit_current')
        self.assertNotEqual(build_templates.detect(ctx), 'kit_current')
        self.assertFalse((p / 'build-templates' / 'bytedance' / 'touch-coordinates.js').is_file())
        self.assertEqual(sha(p / 'assets' / 'tiktok-platform' / 'RewardedService.js'), OLD_RS)

    def test_2_remake_sync_restores(self):
        p = self.remake()
        break_like_old_games(p)
        rec = F.finalize_sync(p, 'remake')
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        self.assertEqual(rec['policy'], 'new')
        for rel in CHECKED:
            self.assertEqual(sha(p / rel), want(rel), rel)
        self.assertTrue((p / '.tiktok-kit' / 'removed' / 'assets' / 'tiktok-platform' / 'RewardedService.js').is_file(),
                        'the old file is moved away, never deleted')
        self.assertTrue((p / F.SYNC_RECORD).is_file())
        again = F.finalize_sync(p, 'remake')
        self.assertEqual(again['changed'], [])
        self.assertFalse((p / F.SOURCE_RECORD).exists(), 'sync does not pretend to be the source phase')

    def test_3_native_localize(self):
        p = project24(self.tmp / 'p')
        b = build24(self.tmp / 'build')
        rec = F.finalize_sync(p, 'localize', native=b)
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        self.assertEqual(sha(b / 'main.js'), MAN['parts']['startup24']['file']['sha256'])
        self.assertEqual(sha(b / 'touch-coordinates.js'), MAN['parts']['touch24']['file']['sha256'])
        self.assertEqual(sha(b / 'storage-guard.js'), MAN['parts']['storage24']['file']['sha256'])
        self.assertEqual(sha(p / 'assets' / 'tiktok-platform' / 'RewardedService.js'),
                         want('assets/tiktok-platform/RewardedService.js'))
        self.assertFalse((p / 'build-templates').exists(), 'localize: the original build-templates are left alone')

    def test_4_legacy_report_only(self):
        p = project24(self.tmp / 'p')
        b = build24(self.tmp / 'build')
        legacy = {'games': [{'name': 'g', 'folder': 'J/g', 'scene_uuids': [SCENE]}]}
        before_p, before_b = tree_sha(p), tree_sha(b)
        rec = F.finalize_sync(p, 'localize', native=b, legacy=legacy)
        self.assertEqual(rec['policy'], 'legacy')
        self.assertEqual(rec['changed'], [])
        self.assertEqual(tree_sha(p), before_p)
        self.assertEqual(tree_sha(b), before_b)
        self.assertTrue(any(s['step'] == 'touch' for s in rec['steps']))

    def test_5_under_three_seconds(self):
        p = self.remake()
        break_like_old_games(p)
        b = build24(self.tmp / 'build')
        t = time.time()
        F.finalize_sync(p, 'remake', native=b)
        self.assertLess(time.time() - t, 3.0)

    def test_6_cli(self):
        p = project24(self.tmp / 'p')
        self.assertEqual(F.main(['sync', '--project', str(p), '--board', 'remake']), 0)
        self.assertEqual(sha(p / 'assets' / 'tiktok-platform' / 'GameUIKit.js'),
                         want('assets/tiktok-platform/GameUIKit.js'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
