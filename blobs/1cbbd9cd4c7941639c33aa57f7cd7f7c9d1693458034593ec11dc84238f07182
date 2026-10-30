#!/usr/bin/env python3
"""tiktok_finalize core (v7.7 W-B): step states, anchors, idempotence, both policies, self-check, records.

Synthetic 2.4 / 3.x builds cover absent / kit_current / kit_old / own / conflict; real packages (read-only copies
of J/ packages, skipped when J is not on this machine) prove the same on pkg81, SorensRivet r22, Marlows R4 / R6.
Run: python3 test_tiktok_finalize.py   (KIROCREW_SCRATCH, when set, holds the temporary folders)
"""
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import appid, build_templates, kit_sources, login, settings, startup, storage  # noqa
from tiktok_finalize_steps import structure, touch  # noqa: E402

J = Path('/Users/sijunting/Downloads/！自制游戏/！交付游戏')
TMP_ROOT = os.environ.get('KIROCREW_SCRATCH') or None
APP = '7683427172773644296'


# ------------------------------------------------------------------ manifest fixture (design 1.5 format)
def manifest_data():
    """The real KIT_MANIFEST.json (kit 2.0, W-A1). parts-3x is included when W-A1 has not added the include yet."""
    data = copy.deepcopy(json.loads(T.MANIFEST.read_text(encoding='utf-8')))
    if not data.get('includes') and (T.KIT_DIR / 'parts-3x' / 'KIT_PARTS_3X.json').is_file():
        data['includes'] = ['parts-3x/KIT_PARTS_3X.json']
    return data


def manifest(mutate=None):
    data = manifest_data()
    if mutate:
        mutate(data)
    return T.Manifest(data, T.KIT_DIR)


def tmpdir(test):
    d = Path(tempfile.mkdtemp(prefix='tfin-', dir=TMP_ROOT))
    test.addCleanup(shutil.rmtree, d, True)
    return d


def tree_sha(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob('*')):
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode() + b'\0' + p.read_bytes())
    return h.hexdigest()


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
GAME3X = """loadCC();
function loadCC() {
    require('./web-adapter');
    require("src/polyfills.bundle.js");
}
"""


def build24(root, main=b'window.boot = function () { /* editor main */ };\n', game=GAME24):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'cocos').mkdir(exist_ok=True)
    (root / 'cocos' / 'cocos2d-js-min.js').write_text('var ENGINE_VERSION = "2.4.15"; window.cc = {};\n')
    (root / 'adapter-min.js').write_text('/* adapter */\n')
    (root / 'game.js').write_text(game)
    (root / 'main.js').write_bytes(main)
    (root / 'ccRequire.js').write_text('/* ccRequire */\n')
    (root / 'src').mkdir(exist_ok=True)
    (root / 'src' / 'settings.js').write_text('window._CCSettings = {};\n')
    (root / 'game.json').write_text('{"deviceOrientation": "portrait"}\n')
    (root / 'project.config.json').write_text('{\n  "appid": "testappid",\n  "projectname": "t"\n}\n')
    return root


def build3x(root, game=GAME3X):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'cocos-js').mkdir(exist_ok=True)
    (root / 'cocos-js' / 'cc.js').write_text('/* engine */\n')
    (root / 'web-adapter.js').write_text('/* web adapter */\n')
    (root / 'game.js').write_text(game)
    (root / 'game.json').write_text('{}\n')
    (root / 'project.config.json').write_text('{"appid":"%s"}\n' % APP)
    return root


def add_plugins3x(root, m=None, game_id='fixture', coins=12):
    """What Creator puts in a 3.x build from the kit plugin scripts of a finalized project: src/settings.json
    plugins.jsList naming the five kit plugins, and each script (re-wrapped, as Creator 3.8.8 does) keeping its
    tiktok-kit:plugin3x marker and BEGIN / END lines. PlatformConfig carries this game's values (K_platform_config)."""
    from package_gates import kit_parts
    m = m or manifest()
    dests = [d for _, d in kit_parts.kit_plugins(m)]
    (root / 'src').mkdir(exist_ok=True)
    (root / 'src' / 'settings.json').write_text(json.dumps({'plugins': {'jsList': dests}}))
    for dest in dests:
        name = dest.rsplit('/', 1)[-1]
        text = (T.KIT_DIR / 'plugins-3x' / name).read_text(encoding='utf-8')
        if name == 'PlatformConfig.plugin.js':
            text = text.replace("gameId: 'change-me'", "gameId: '%s'" % game_id)
            text = text.replace('normalLevelCoins: 0,', 'normalLevelCoins: %s,' % coins)
        (root / 'src' / dest).parent.mkdir(parents=True, exist_ok=True)
        (root / 'src' / dest).write_text('(function(root){var exports=undefined;(function(){%s})()})(globalThis);'
                                         % text, encoding='utf-8')
    return dests


def ctx(root, engine, policy='new', m=None, **kw):
    return T.Ctx('native', root, engine=engine, policy=policy, manifest=m or manifest(), **kw)


def kit_bytes(m, name):
    return m.kit_bytes(name)


class StatesAndAnchors(unittest.TestCase):
    def test_five_states_touch24(self):
        m = manifest()
        d = tmpdir(self)
        b = build24(d / 'absent')
        self.assertEqual(touch.detect(ctx(b, 2, m=m)), 'absent')
        b = build24(d / 'current')
        touch.apply(ctx(b, 2, m=m))
        self.assertEqual(touch.detect(ctx(b, 2, m=m)), 'kit_current')
        b = build24(d / 'old')
        touch.apply(ctx(b, 2, m=m))
        g = (b / 'game.js').read_text().replace('tiktok-kit:touch24:%s' % m.version, 'tiktok-kit:touch24:1.9')
        (b / 'game.js').write_text(g)
        self.assertEqual(touch.detect(ctx(b, 2, m=m)), 'kit_old')
        b = build24(d / 'own')
        (b / 'touch-coordinates.js').write_text('cc.internal.inputManager.getTouchesByEvent = function () {};\n')
        self.assertEqual(touch.detect(ctx(b, 2, m=m)), 'own')
        b = build24(d / 'conflict', game=GAME24.replace('__globalAdapter.adaptEngine();',
                                                         '__globalAdapter.adaptEngine();\n__globalAdapter.adaptEngine();'))
        r = touch.apply(ctx(b, 2, m=m))
        self.assertTrue(any(x['id'] == 'K2_kit_wiring' and 'found 2 times' in x['message'] for x in r['blocks']))

    def test_kit_old_line_is_replaced_in_place(self):
        m = manifest()
        b = build24(tmpdir(self) / 'b')
        touch.apply(ctx(b, 2, m=m))
        g = (b / 'game.js').read_text()
        (b / 'game.js').write_text(g.replace('tiktok-kit:touch24:%s' % m.version, 'tiktok-kit:touch24:1.9'))
        r = touch.apply(ctx(b, 2, m=m))
        self.assertEqual(r['blocks'], [])
        self.assertEqual((b / 'game.js').read_text(), g)

    def test_anchor_zero_times_refused(self):
        b = build24(tmpdir(self) / 'b', game=GAME24.replace('__globalAdapter.adaptEngine();\n', ''))
        before = (b / 'game.js').read_bytes()
        r = touch.apply(ctx(b, 2))
        self.assertTrue(any('found 0 times' in x['message'] for x in r['blocks']), r['blocks'])
        self.assertEqual((b / 'game.js').read_bytes(), before)

    def test_anchor_twice_refused_3x(self):
        b = build3x(tmpdir(self) / 'b', game=GAME3X.replace("    require('./web-adapter');\n",
                                                           "    require('./web-adapter');\n    require('./web-adapter');\n"))
        r = touch.apply(ctx(b, 3))
        self.assertTrue(any('found 2 times' in x['message'] for x in r['blocks']), r['blocks'])

    def test_indentation_kept_3x(self):
        b = build3x(tmpdir(self) / 'b')
        touch.apply(ctx(b, 3))
        storage.apply(ctx(b, 3))
        lines = (b / 'game.js').read_text().split('\n')
        i = next(n for n, l in enumerate(lines) if "require('./web-adapter')" in l)
        self.assertTrue(lines[i].startswith('    require'))
        self.assertTrue(lines[i - 1].startswith('    require(\'./tiktok-touch-3x.js\')'))
        self.assertTrue(lines[i + 1].startswith('    require(\'./storage-guard.js\')'))


class Policies(unittest.TestCase):
    def test_new_replaces_own_touch_legacy_keeps_it(self):
        own = b"module.exports = function (tt) { tt.onTouchStart = function () {}; };\n"
        game = GAME3X.replace("    require('./web-adapter');",
                              "    require('./my-touch')(tt);\n    require('./web-adapter');")
        d = tmpdir(self)
        for policy in ('new', 'legacy'):
            b = build3x(d / policy, game=game)
            (b / 'my-touch.js').write_bytes(own)
            r = touch.apply(ctx(b, 3, policy=policy))
            self.assertEqual(r['blocks'], [], r)
            g = (b / 'game.js').read_text()
            if policy == 'new':
                self.assertFalse((b / 'my-touch.js').exists())
                self.assertIn("// tiktok-kit-removed:touch3x: require('./my-touch')(tt);", g)
                self.assertIn('tiktok-kit:touch3x:', g)
            else:
                self.assertEqual((b / 'my-touch.js').read_bytes(), own)
                self.assertNotIn('tiktok-kit:touch3x', g)
                self.assertTrue(any(w['id'] == 'K_W_own_touch3x' for w in r['warnings']))

    def test_own_layer_inside_bundle_blocks_new(self):
        b = build3x(tmpdir(self) / 'b')
        (b / 'assets').mkdir()
        (b / 'assets' / 'index.js').write_text('tt.onTouchStart = function (e) {};\n')
        r = touch.apply(ctx(b, 3))
        self.assertTrue(any(x['id'] == 'K3_single_layer' for x in r['blocks']), r)

    def test_storage_new_installs_legacy_skips(self):
        d = tmpdir(self)
        b = build24(d / 'new')
        r = storage.apply(ctx(b, 2))
        self.assertEqual(r['blocks'], [])
        self.assertEqual(T.sha256((b / 'storage-guard.js').read_bytes()),
                         manifest().parts['storage24']['file']['sha256'])
        b = build24(d / 'legacy')
        before = tree_sha(b)
        storage.apply(ctx(b, 2, policy='legacy'))
        self.assertEqual(tree_sha(b), before)

    def test_kit_main_wires_through_main_not_game(self):
        m = manifest()
        b = build24(tmpdir(self) / 'b', main=kit_bytes(m, 'startup24'))
        for step in (startup, touch, storage):
            r = step.apply(ctx(b, 2, m=m))
            self.assertEqual(r['blocks'], [], r)
        self.assertEqual((b / 'game.js').read_text(), GAME24)
        self.assertTrue((b / 'touch-coordinates.js').is_file() and (b / 'storage-guard.js').is_file())

    def test_webp_exception_installs_kit_probe(self):
        m = manifest()
        b = build24(tmpdir(self) / 'b', main=kit_bytes(m, 'startup24'))
        (b / 'a.webp').write_bytes(b'RIFF0000WEBPVP8 ')
        opts = {'keep_webp_exception': 'JaspersKelp still over 30 MB after resize'}
        self.assertTrue(structure.apply(ctx(b, 2, m=m))['blocks'])
        r = startup.apply(ctx(b, 2, m=m, options=opts))
        self.assertEqual(r['blocks'], [], r['blocks'])
        g = (b / 'game.js').read_text()
        self.assertLess(g.index('__TIKTOK_KIT_WEBP_PROBE__'), g.index("require('./main')"))
        self.assertTrue((b / 'webp-decode-probe.js').is_file() and (b / 'loading' / 'webp-probe.webp').is_file())
        self.assertEqual(structure.apply(ctx(b, 2, m=m, options=opts))['blocks'], [])
        snap = tree_sha(b)
        startup.apply(ctx(b, 2, m=m, options=opts))
        self.assertEqual(tree_sha(b), snap)

    def test_editor_main_replaced_for_new_and_kept_for_legacy(self):
        d = tmpdir(self)
        b = build24(d / 'new')
        r = startup.apply(ctx(b, 2))
        self.assertEqual(r['blocks'], [])
        self.assertEqual(T.sha256((b / 'main.js').read_bytes()), T.kit_main_current(manifest()))
        b = build24(d / 'legacy')
        startup.apply(ctx(b, 2, policy='legacy'))
        self.assertIn(b'editor main', (b / 'main.js').read_bytes())

    def test_unknown_engine_version_keeps_editor_main(self):
        b = build24(tmpdir(self) / 'b')
        # v7.7 W-D3: startup24 covers 2.4.4 / 2.4.6 / 2.4.13 / 2.4.15; 2.4.3 is outside the list
        (b / 'cocos' / 'cocos2d-js-min.js').write_text('var ENGINE_VERSION = "2.4.3";\n')
        r = startup.apply(ctx(b, 2))
        self.assertTrue(any(w['id'] == 'K_W_startup_engine' for w in r['warnings']))
        self.assertIn(b'editor main', (b / 'main.js').read_bytes())
        self.assertEqual(touch.apply(ctx(b, 2))['blocks'], [])
        self.assertIn('tiktok-kit:touch24', (b / 'game.js').read_text())

    def test_bound_require_is_never_commented_out(self):
        game = "'use strict';\nvar boot = require('./srr-native-boot');\nboot.launch(function () {\n" + GAME24 + '});\n'
        b = build24(tmpdir(self) / 'b', game=game)
        (b / 'srr-native-boot.js').write_text('module.exports = {launch: function (f) { f(); }};\n')
        r = startup.apply(ctx(b, 2))
        self.assertTrue((b / 'srr-native-boot.js').is_file())
        self.assertIn("var boot = require('./srr-native-boot');", (b / 'game.js').read_text())
        self.assertTrue(any(w['id'] == 'K_W_own_startup_kept' for w in r['warnings']))


class IdempotenceAndSelfCheck(unittest.TestCase):
    def run_all(self, b, engine, policy='new'):
        out = []
        for step in (startup, touch, storage, login, appid, structure):
            out.append(step.apply(ctx(b, engine, policy=policy, app_id=APP)))
        return out

    def test_two_runs_byte_identical_both_engines_both_policies(self):
        d = tmpdir(self)
        for engine, maker in ((2, build24), (3, build3x)):
            for policy in ('new', 'legacy'):
                b = maker(d / ('%s-%s' % (engine, policy)))
                first = self.run_all(b, engine, policy)
                self.assertEqual([x for r in first for x in r['blocks']], [], (engine, policy, first))
                snap = tree_sha(b)
                second = self.run_all(b, engine, policy)
                self.assertEqual(tree_sha(b), snap, (engine, policy))
                self.assertEqual(sum(len(r['changed']) for r in second), 0)

    def test_self_check_failure_refuses(self):
        b = build24(tmpdir(self) / 'b')
        with mock.patch.object(T, 'wire_line', lambda text, *a, **k: (text, 'absent', 'pretend')):
            r = touch.apply(ctx(b, 2))
        self.assertTrue(any(x['message'].startswith('after install:') for x in r['blocks']), r['blocks'])

    def test_kit_file_differing_from_manifest_refuses(self):
        def bad(data):
            data['parts']['touch24']['file']['sha256'] = '0' * 64
        r = touch.apply(ctx(build24(tmpdir(self) / 'b'), 2, m=manifest(bad)))
        self.assertTrue(any(x['id'] == 'K_kit_unusable' for x in r['blocks']))


class AppIdAndStructure(unittest.TestCase):
    def test_appid_written_and_mismatch_blocks(self):
        d = tmpdir(self)
        b = build24(d / 'b')
        r = appid.apply(ctx(b, 2, app_id=APP))
        self.assertEqual(r['blocks'], [])
        self.assertIn('"appid": "%s"' % APP, (b / 'project.config.json').read_text())
        proj = d / 'proj'
        (proj / 'assets' / 'tiktok-platform').mkdir(parents=True)
        (proj / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').write_text("appId: '1234567890123',\n")
        r = appid.apply(ctx(build24(d / 'c'), 2, app_id=APP, project=proj))
        self.assertTrue(any(x['id'] == 'K_appid_mismatch' for x in r['blocks']))
        r = appid.apply(ctx(build24(d / 'e'), 2, options={'ad_config': str(d / 'none.json')}))
        self.assertTrue(any(x['id'] == 'K_appid_missing' for x in r['blocks']))

    def test_structure(self):
        b = build24(tmpdir(self) / 'b')
        (b / 'empty.json').write_bytes(b'')
        (b / 'a.webp').write_bytes(b'RIFF0000WEBP')
        new = structure.apply(ctx(b, 2))
        legacy = structure.apply(ctx(b, 2, policy='legacy'))
        self.assertEqual({x['id'] for x in new['blocks']}, {'K_S_zero_byte', 'K_S_webp'})
        self.assertEqual({x['id'] for x in legacy['blocks']}, {'K_S_zero_byte'})
        (b / 'empty.json').unlink()
        (b / 'a.webp').unlink()
        (b / 'dbg.js').write_text('cc.debug.setDisplayStats(true);\n')
        self.assertEqual({x['id'] for x in structure.apply(ctx(b, 2))['blocks']}, {'L4_debug_code'})


def project24(root, app=APP):
    (root / 'assets' / 'scenes').mkdir(parents=True)
    (root / 'assets' / 'scenes' / 'Main.fire.meta').write_text('{"ver": "1.2.9", "uuid": "%s", "importer": "scene"}'
                                                              % '1b2c3d4e-0000-4000-8000-00000000abcd')
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    (root / 'build-templates' / 'bytedance').mkdir(parents=True)
    (root / 'build-templates' / 'bytedance' / 'native-load-guard.js').write_text('/* own */\n')
    (root / 'assets' / 'tiktok-platform').mkdir()
    (root / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').write_text("var c = {appId: '%s'};\n" % app)
    return root


class Records(unittest.TestCase):
    def test_source_record_and_k5(self):
        p = project24(tmpdir(self) / 'p')
        rec = F.finalize_source(p, 'remake', steps=('kit_sources', 'build_templates', 'settings'))
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        self.assertEqual(rec['policy'], 'new')
        self.assertTrue((p / '.tiktok-kit' / 'removed' / 'build-templates' / 'bytedance' / 'native-load-guard.js').is_file())
        self.assertEqual(json.loads((p / 'settings' / 'bytedance.json').read_text())['appid'], APP)
        self.assertEqual(F.check_source_record(p), [])
        again = F.finalize_source(p, 'remake', steps=('kit_sources', 'build_templates', 'settings'))
        self.assertEqual(sum(len(s['changed']) for s in again['steps']), 0)
        (p / 'assets' / 'x.js').write_text('changed')
        self.assertTrue(any('changed after' in f['message'] for f in F.check_source_record(p)))
        self.assertTrue(F.check_source_record(None))
        old = manifest(lambda d: d.update(version='1.9'))
        self.assertTrue(any('kit 2' in f['message'] or 'current kit' in f['message']
                            for f in F.check_source_record(p, old)))

    def test_native_record_and_k4(self):
        d = tmpdir(self)
        b = build24(d / 'native')
        rec = F.finalize_native(b, None, 'remake', APP, policy='new',
                                steps=('startup', 'touch', 'storage', 'login', 'appid', 'structure'))
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        files = T.Ctx('native', b).files()
        self.assertEqual(F.check_finalize_record(rec, files), [])
        files['touch-coordinates.js'] = b'changed'
        self.assertTrue(F.check_finalize_record(rec, files))
        self.assertTrue(F.check_finalize_record(None, files))
        self.assertTrue(rec['table'])

    def test_marker_from_source_keeps_native_new(self):
        p = project24(tmpdir(self) / 'p')
        F.finalize_source(p, 'remake', policy='new', steps=('settings',))
        out = F.decide_policy(project=p, record={'policy': 'new', 'decision': {'reason': 'x'}},
                              legacy={'games': [{'name': 'g', 'folder': 'J/g',
                                                 'scene_uuids': ['1b2c3d4e-0000-4000-8000-00000000abcd']}]})
        self.assertEqual(out['policy'], 'new')

    def test_override_record_rejected_by_k5(self):
        p = project24(tmpdir(self) / 'p')
        F.finalize_source(p, 'remake', policy='new', steps=('settings',))
        self.assertTrue(any('--policy' in f['message'] for f in F.check_source_record(p)))


def unzip(test, src, name):
    d = tmpdir(test) / name
    with zipfile.ZipFile(src) as z:
        z.extractall(d)
    return d


@unittest.skipUnless(J.is_dir(), 'real packages not on this machine')
class RealPackages(unittest.TestCase):
    """Copies of real packages in a temporary folder; the originals are only read."""

    def finalize_twice(self, b, engine, policy='new'):
        steps = ('startup', 'touch', 'storage', 'login', 'appid', 'structure')
        rec = F.finalize_native(b, None, 'localize', APP, policy=policy, steps=steps)
        snap = tree_sha(b)
        rec2 = F.finalize_native(b, None, 'localize', APP, policy=policy, steps=steps)
        self.assertEqual(tree_sha(b), snap)
        self.assertEqual(sum(len(s['changed']) for s in rec2['steps']), 0)
        return rec

    def test_pkg81_new_kit_main_installed(self):
        # v7.7 W-D3: 2.4.13 is in startup24's engine list, so pkg81 gets the kit main.js, which loads the touch and
        # storage parts itself (no load lines in game.js)
        b = tmpdir(self) / 'pkg81'
        shutil.copytree(J / '1香吉士-射击高手2048/检测修复_20261029/pkg81', b)
        rec = self.finalize_twice(b, 2)
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        self.assertEqual(T.sha256((b / 'main.js').read_bytes()), T.kit_main_current(manifest()))
        g = (b / 'game.js').read_text()
        self.assertEqual(g.count('tiktok-kit:touch24:'), 0)
        self.assertEqual(g.count('tiktok-kit:storage24:'), 0)
        self.assertTrue((b / 'touch-coordinates.js').is_file())
        self.assertTrue((b / 'storage-guard.js').is_file())
        self.assertIn('// tiktok-kit-removed:startup24:', g)          # native-load-guard taken out
        self.assertTrue((b / 'native-preload.js').is_file())          # wraps the engine: kept, warned

    def test_marlows_r4_and_r6_3x(self):
        base = J / '4周燎原-Marlows（自制）'
        r4 = unzip(self, base / 'MarlowsMarbleCut_PortionV2_R4_TikTok_Test_20261027.zip', 'r4')
        rec = self.finalize_twice(r4, 3)
        self.assertEqual([b['id'] for b in rec['blocks']], ['K_S_webp'])   # images belong to the source phase
        g = (r4 / 'game.js').read_text()
        self.assertLess(g.index('tiktok-touch-3x'), g.index("require('./web-adapter')"))
        self.assertGreater(g.index('storage-guard'), g.index("require('./web-adapter')"))
        r6 = unzip(self, base / 'MarlowsMarbleCut_PortionV2_R6_TikTok_Test_20261029.zip', 'r6')
        legacy = unzip(self, base / 'MarlowsMarbleCut_PortionV2_R6_TikTok_Test_20261029.zip', 'r6legacy')
        self.finalize_twice(r6, 3)
        self.assertFalse((r6 / 'marlow-touch.js').exists())
        rec = self.finalize_twice(legacy, 3, policy='legacy')
        self.assertTrue((legacy / 'marlow-touch.js').is_file())
        self.assertNotIn('tiktok-touch-3x', (legacy / 'game.js').read_text())
        self.assertTrue(any(w['id'] == 'K_W_own_touch3x' for w in rec['warnings']))

    def test_sorensrivet_r22_kit_main(self):
        b = unzip(self, J / '1林子健-SorensRivet（自制）/SorensRivetRack_NativeTest_20261028_r22_存档广告难度.zip', 's')
        rec = self.finalize_twice(b, 2)
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        self.assertEqual(T.sha256((b / 'main.js').read_bytes()), T.kit_main_current(manifest()))
        g = (b / 'game.js').read_text()
        self.assertIn("var nativeBoot = require('./srr-native-boot');", g)
        self.assertNotIn('tiktok-kit:touch24', g)                    # loaded by the kit main.js
        self.assertIn('// tiktok-kit-removed:touch24-double:', g)    # its own second load line taken out


if __name__ == '__main__':
    unittest.main(verbosity=1)
