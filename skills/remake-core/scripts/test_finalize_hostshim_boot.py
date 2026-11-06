#!/usr/bin/env python3
"""生成时预防 R4B (Round4 剩余清单第 9、38 条): finalize installs host-shim / boot-guard-3x, sync installs GameUIKit.ts.

问题普查 20261104: startup_stuck 34 款、startup_retry_broken 27 款、host_api_mismatch 12 款、button_covered 14 款。
Before R4B the kit shipped parts/host-shim.js and parts-3x/boot-guard-3x.js, but no finalize step put their load line
in game.js, so every game hand-wrote it (or forgot it); `sync` returned n/a for 3.x, so 3.x games copied GameUIKit.ts
by hand. Every case below fails on the 简化.11.14 base (old way) and passes with this patch.
  1 2.4 source+native   source puts host-shim.js in build-templates/bytedance; native (what the writer and
                        `sync --native` run) adds ONE marked line right before require('adapter-min.js'); 2nd run = no change
  2 3.x source          a build-templates/bytedance-mini-game/game.js gets hostshim3x before web-adapter and boot3x
                        before System.warmup(; the build made from it needs no change in native
  3 3.x native          a build game.js without template gets both lines, in that order
  4 legacy              2.4 and 3.x legacy builds: no file changes (report only)
  5 boot-loading        a 3.x game with its own start page: host-shim installed, boot3x NOT stacked (warning)
  6 anchor twice        System.warmup( twice refuses (K2), game.js unchanged
  7 verify              a package with host-shim.js but no load line is refused by startup.verify (K2: never loaded)
  8 sync 3.x            sync on a 3.x project installs assets/tiktok-platform/GameUIKit.ts (kit bytes); 2nd sync no change
The 2.4 part hostshim24 lives in KIT_MANIFEST.json (owned by another batch in Round 4): until it is merged there, this
test adds the same entry in memory (HOSTSHIM24 below = the text handed over in 交接).
Run: python3 test_finalize_hostshim_boot.py
"""
import copy
import hashlib
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
from tiktok_finalize_steps import startup  # noqa: E402

APP = '7683427172773644296'
HOSTSHIM24 = {
    'engine': 2, 'phase': 'native', 'step': 'hostshim',
    'file': {'src': 'parts/host-shim.js', 'template': 'build-templates/bytedance/host-shim.js', 'dest': 'host-shim.js',
             'sha256': '7b325cd2f684dcbe86388f2cc12f0f3a98d7427b2eb632130a4111ae0c16d872', 'previous_sha256': []},
    'wiring': [{'in': 'game.js',
                'insert_before': "require\\(\\s*['\"](?:\\./)?adapter(?:-min)?(?:\\.js)?['\"]\\s*\\)\\s*;?",
                'line': "try { require('./host-shim.js').install(globalThis.TTMinis&&TTMinis.game||globalThis.tt); } "
                        "catch (e) { console.error('host shim', e); } // tiktok-kit:hostshim24:2.0"}],
    'own_markers': [], 'policy': {'new': 'replace', 'legacy': 'report'}}
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
const importMap = require("src/import-map.js").default;
System.warmup({ importMap, importMapUrl: 'src/import-map.js' });
System.import('./application.js').then(function (m) { return m; });
"""


def manifest():
    data = copy.deepcopy(json.loads(T.MANIFEST.read_text(encoding='utf-8')))
    data.setdefault('parts', {}).setdefault('hostshim24', HOSTSHIM24)
    return T.Manifest(data, T.KIT_DIR)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree_sha(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob('*')):
        if p.is_file() and '.tiktok-kit' not in p.parts:
            h.update(p.relative_to(root).as_posix().encode() + b'\0' + p.read_bytes())
    return h.hexdigest()


def project(root, engine, template_game=None, own_boot=False):
    (root / 'assets' / 'tiktok-platform').mkdir(parents=True)
    (root / 'project.json').write_text('{"version": "%s"}' % ('2.4.15' if engine == 2 else '3.8.8'))
    if template_game is not None:
        t = root / 'build-templates' / 'bytedance-mini-game'
        t.mkdir(parents=True)
        (t / 'game.js').write_text(template_game)
        if own_boot:
            (t / 'boot-loading.js').write_text('// own start page\nrequire("./native-recovery");\n')
    return root


def build(root, engine, game=None):
    root.mkdir(parents=True, exist_ok=True)
    if engine == 2:
        (root / 'cocos').mkdir()
        (root / 'cocos' / 'cocos2d-js-min.js').write_text('var ENGINE_VERSION = "2.4.15"; window.cc = {};\n')
        (root / 'adapter-min.js').write_text('/* adapter */\n')
        (root / 'main.js').write_text('window.boot = function () { /* editor main */ };\n')
        (root / 'ccRequire.js').write_text('/* ccRequire */\n')
        (root / 'src').mkdir()
        (root / 'src' / 'settings.js').write_text('window._CCSettings = {};\n')
    else:
        (root / 'cocos-js').mkdir()
        (root / 'cocos-js' / 'cc.js').write_text('/* engine */\n')
        (root / 'web-adapter.js').write_text('/* web adapter */\n')
    (root / 'game.js').write_text(game if game is not None else (GAME24 if engine == 2 else GAME3X))
    (root / 'game.json').write_text('{"deviceOrientation": "portrait"}\n')
    (root / 'project.config.json').write_text('{"appid": "%s"}\n' % APP)
    return root


def copy_templates(proj, out, engine):
    """What the Cocos build does with build-templates/<platform>/: copy every file over the build output."""
    base = proj / 'build-templates' / ('bytedance' if engine == 2 else 'bytedance-mini-game')
    for p in base.rglob('*') if base.is_dir() else []:
        if p.is_file() and not p.name.endswith('.meta'):
            dest = out / p.relative_to(base)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)


def native(b, m, policy='new'):
    ctx = T.Ctx('native', b, engine=2 if (b / 'cocos').is_dir() else 3, policy=policy, manifest=m)
    return startup.apply(ctx)


def line_index(text, needle):
    lines = text.split('\n')
    hits = [i for i, l in enumerate(lines) if needle in l]
    return hits


class HostShimBoot(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix='r4b-'))
        self.addCleanup(shutil.rmtree, self.d, True)
        self.m = manifest()

    def test_1_24_source_then_native(self):
        p = project(self.d / 'p', 2)
        F.finalize_source(p, 'remake', policy='new', manifest=self.m, steps=('kit_sources', 'build_templates', 'startup'))
        tmpl = p / 'build-templates' / 'bytedance' / 'host-shim.js'
        self.assertTrue(tmpl.is_file(), 'source: host-shim.js not in build-templates/bytedance')
        self.assertEqual(sha(tmpl), HOSTSHIM24['file']['sha256'])
        b = build(self.d / 'b', 2)
        copy_templates(p, b, 2)
        r = native(b, self.m)
        self.assertEqual([x for x in r['blocks']], [])
        g = (b / 'game.js').read_text()
        shim = line_index(g, "require('./host-shim.js')")
        adapter = line_index(g, "require('adapter-min.js')")
        self.assertEqual(len(shim), 1, g)
        self.assertEqual(shim[0] + 1, adapter[0], 'host-shim line must be right before the adapter line')
        self.assertIn('tiktok-kit:hostshim24:', g)
        before = (b / 'game.js').read_bytes()
        native(b, self.m)
        self.assertEqual((b / 'game.js').read_bytes(), before, 'second run must not change game.js')

    def test_2_3x_source_template(self):
        p = project(self.d / 'p', 3, template_game=GAME3X)
        rec = F.finalize_source(p, 'remake', policy='new', manifest=self.m,
                                steps=('kit_sources', 'build_templates', 'startup'))
        t = p / 'build-templates' / 'bytedance-mini-game'
        g = (t / 'game.js').read_text()
        shim, adapter = line_index(g, "require('./host-shim.js')"), line_index(g, "require('./web-adapter')")
        boot, warm = line_index(g, "require('./boot-guard-3x.js')"), line_index(g, 'System.warmup(')
        self.assertEqual((len(shim), len(boot)), (1, 1), g)
        self.assertEqual(shim[0] + 1, adapter[0])
        self.assertEqual(boot[0] + 1, warm[0])
        self.assertTrue(g.split('\n')[shim[0]].startswith('    require'), 'indentation of the anchor line kept')
        for name in ('host-shim.js', 'boot-guard-3x.js'):
            self.assertEqual(sha(t / name), (self.m.parts['hostshim3x' if 'host' in name else 'boot3x']['file']['sha256']))
        self.assertFalse([b for b in rec['blocks'] if b.get('step') == 'startup'], rec['blocks'])
        b = build(self.d / 'b', 3)
        copy_templates(p, b, 3)
        before = tree_sha(b)
        r = native(b, self.m)
        self.assertEqual(r['blocks'], [])
        self.assertEqual(tree_sha(b), before, 'a build made from the wired template needs no change')
        again = F.finalize_source(p, 'remake', policy='new', manifest=self.m, steps=('startup',))
        self.assertEqual(again['steps'][0]['changed'], [])

    def test_3_3x_native(self):
        b = build(self.d / 'b', 3)
        r = native(b, self.m)
        self.assertEqual(r['blocks'], [])
        g = (b / 'game.js').read_text()
        self.assertEqual(len(line_index(g, "require('./host-shim.js')")), 1, g)
        self.assertEqual(len(line_index(g, "require('./boot-guard-3x.js')")), 1, g)
        self.assertLess(g.index('host-shim'), g.index("require('./web-adapter')"))
        self.assertLess(g.index('boot-guard-3x'), g.index('System.warmup('))
        self.assertEqual(sha(b / 'boot-guard-3x.js'), self.m.parts['boot3x']['file']['sha256'])
        self.assertEqual(startup.verify(T.Ctx('native', b).files(), self.m, 'new', 3), [])

    def test_4_legacy_report_only(self):
        for engine in (2, 3):
            b = build(self.d / ('b%d' % engine), engine)
            before = tree_sha(b)
            r = native(b, self.m, policy='legacy')
            self.assertEqual(tree_sha(b), before, 'legacy %d.x build changed' % engine)
            self.assertTrue(any('report only' in i for i in r['info']), r['info'])

    def test_5_own_boot_loading_not_stacked(self):
        game = GAME3X.replace("System.import('./application.js')", "require('./boot-loading');\nSystem.import('./application.js')")
        b = build(self.d / 'b', 3, game=game)
        (b / 'boot-loading.js').write_text('// own start page\n')
        r = native(b, self.m)
        g = (b / 'game.js').read_text()
        self.assertEqual(len(line_index(g, "require('./host-shim.js')")), 1, 'host-shim still installed')
        self.assertNotIn('boot-guard-3x', g)
        self.assertFalse((b / 'boot-guard-3x.js').exists())
        self.assertTrue(any(w['id'] == 'K_W_own_startup' and 'boot3x' in w['message'] for w in r['warnings']))
        p = project(self.d / 'p', 3, template_game=GAME3X, own_boot=True)
        rec = F.finalize_source(p, 'remake', policy='new', manifest=self.m,
                                steps=('kit_sources', 'build_templates', 'startup'))
        g = (p / 'build-templates' / 'bytedance-mini-game' / 'game.js').read_text()
        self.assertIn('host-shim', g)
        self.assertNotIn("require('./boot-guard-3x.js')", g)
        self.assertTrue(any(w['id'] == 'K_W_own_startup' and 'boot3x' in w['message'] for w in rec['warnings']))

    def test_6_anchor_twice_refused(self):
        game = GAME3X.replace("System.warmup(", "System.warmup({});\nSystem.warmup(", 1)
        b = build(self.d / 'b', 3, game=game)
        r = native(b, self.m)
        self.assertTrue(any(x['id'] == 'K2_kit_wiring' and 'found 2 times' in x['message'] for x in r['blocks']),
                        r['blocks'])
        self.assertNotIn('boot-guard-3x', (b / 'game.js').read_text())

    def test_7_verify_never_loaded(self):
        b = build(self.d / 'b', 2)
        shutil.copyfile(T.KIT_DIR / 'parts' / 'host-shim.js', b / 'host-shim.js')
        out = startup.verify(T.Ctx('native', b).files(), self.m, 'new', 2)
        self.assertTrue(any(x['id'] == 'K2_kit_wiring' and 'hostshim24' in x['message'] for x in out), out)

    def test_8_sync_3x_gameuikit(self):
        p = project(self.d / 'p', 3)
        rec = F.finalize_sync(p, 'remake', policy='new', manifest=self.m)
        ts = p / 'assets' / 'tiktok-platform' / 'GameUIKit.ts'
        self.assertTrue(ts.is_file(), [s for s in rec['steps'] if s['step'] == 'ui_kit'])
        self.assertEqual(sha(ts), self.m.files['parts-3x/GameUIKit.ts']['sha256'])
        again = F.finalize_sync(p, 'remake', policy='new', manifest=self.m)
        self.assertEqual(again['changed'], [])
        legacy = project(self.d / 'l', 3)
        F.finalize_sync(legacy, 'remake', policy='legacy', manifest=self.m)
        self.assertFalse((legacy / 'assets' / 'tiktok-platform' / 'GameUIKit.ts').exists(), 'legacy: report only')


if __name__ == '__main__':
    unittest.main(verbosity=2)
