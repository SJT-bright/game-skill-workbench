#!/usr/bin/env python3
"""v7.7 W-F1a: native-stage and platform-kit fixes found by the wave-2 real-package runs.

1. W-D1 request 1  the kit main.js always ships with webp-decode-probe.js (startup24.extra_files; script only, no
                   probe image and no switch line), so the static startup-dependency check no longer refuses every
                   package that got the kit main.js (SorensRivet r22: "missing startup dependency: webp-decode-probe").
2. W-D1 request 2  an own startup file another package file still requires is kept with a warning, and a moved
                   file's commented load line no longer reads as a require (MergeShot pkg81: "missing entry require:
                   ./native-load-guard" came from that comment).
3. W-D3 request 5  a game script with the same Cocos 2.4 module name as a kit module (MabelsMeadow r8) is moved out
                   with its .meta for a new game, reported for a legacy game.
4. W-D3 request 2  the Cocos 2.4.4 adapter (DotsDelivery v40) is recognised: no SDKVersion test, pass-through
                   in-package handler -> already the fixed form; the sub-context form is still rewritten.
Each item has cases that failed on the code before W-F1a (11 of the 15 tests); the other 4 are controls that must
keep passing (proof: briefs/out/W-F1a/evidence/old_code_run.txt).
Real-package checks are skipped when the package is not on this machine.
Run: python3 test_finalize_native_fixes.py
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import kit_sources, startup  # noqa: E402
from package_gates import adapter_fix  # noqa: E402
import audit_upload_startup  # noqa: E402

TMP_ROOT = os.environ.get('KIROCREW_SCRATCH') or None
APP = '7683427172773644296'
J = Path('/Users/sijunting/Downloads/！自制游戏/！交付游戏')
DOTS = J / '1记得住-DotsDelivery（自制）/DotsDeliveryDepot_TikTok_test_v40.zip'
ENTRY_REQUIRE = re.compile(r'''require\(\s*["']([^"']+)["']\s*\)''')   # audit_packed_assets entry scan (no comments)

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


def tmpdir(test):
    d = Path(tempfile.mkdtemp(prefix='wf1a-', dir=TMP_ROOT))
    test.addCleanup(shutil.rmtree, d, True)
    return d


def build24(root, game=GAME24, extra=None):
    """Synthetic Cocos 2.4.15 ByteDance build with an editor main.js."""
    root.mkdir(parents=True, exist_ok=True)
    files = {'cocos/cocos2d-js-min.js': 'var ENGINE_VERSION = "2.4.15"; window.cc = {};\n',
             'adapter-min.js': '/* adapter */\n', 'game.js': game,
             'main.js': 'window.boot = function () { /* editor main */ };\n', 'ccRequire.js': '/* ccRequire */\n',
             'src/settings.js': 'window._CCSettings = {};\n', 'game.json': '{"deviceOrientation": "portrait"}\n',
             'project.config.json': '{\n  "appid": "testappid",\n  "projectname": "t"\n}\n'}
    files.update(extra or {})
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    return root


def native_files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(Path(root).rglob('*')) if p.is_file()}


def finalize(root, policy='new'):
    return F.finalize_native(root, board='remake', app_id=APP, policy=policy)


def step(rec, name):
    return [s for s in rec['steps'] if s['step'] == name][0]


def probe_spec():
    return startup.main_extras(T.load_manifest())[0]


# ------------------------------------------------------------------------------------------------ item 1
class KitMainShipsWithProbeScript(unittest.TestCase):
    def test_manifest_lists_the_probe_script_under_startup24(self):
        spec = probe_spec()
        self.assertEqual(spec['dest'], 'webp-decode-probe.js')
        m = T.load_manifest()
        self.assertEqual(T.sha256((m.kit_dir / spec['src']).read_bytes()), spec['sha256'])
        self.assertEqual(spec['sha256'], m.part('webp_probe24')['file']['sha256'], 'same file as the WebP part')

    def test_kit_main_install_places_only_the_probe_script(self):
        root = build24(tmpdir(self) / 'native')
        rec = finalize(root)
        self.assertEqual(rec['blocks'], [])
        files = native_files(root)
        self.assertEqual(T.sha256(files['main.js']), T.kit_main_current(T.load_manifest()))
        self.assertEqual(T.sha256(files['webp-decode-probe.js']), probe_spec()['sha256'])
        self.assertNotIn('loading/webp-probe.webp', files, 'no probe image without the WebP exception')
        self.assertNotIn('__TIKTOK_KIT_WEBP_PROBE__', files['game.js'].decode(), 'no switch line: the probe never runs')
        deps = [e for e in audit_upload_startup.audit_files(files)['errors'] if 'startup dependency' in e]
        self.assertEqual(deps, [], 'r22: "missing startup dependency: webp-decode-probe from main.js"')
        again = finalize(root)
        self.assertEqual([s['step'] for s in again['steps'] if s['changed']], [], 'second run changes nothing')

    def test_probe_script_missing_or_changed_blocks_K1(self):
        root = build24(tmpdir(self) / 'native')
        finalize(root)
        m = T.load_manifest()
        files = native_files(root)
        self.assertEqual([f for f in startup.verify(files, m, 'new', 2) if f['level'] == 'block'], [])
        for broken in ({k: v for k, v in files.items() if k != 'webp-decode-probe.js'},
                       dict(files, **{'webp-decode-probe.js': b'module.exports = function () {};'})):
            ids = [f['id'] for f in startup.verify(broken, m, 'new', 2) if f['level'] == 'block']
            self.assertIn('K1_kit_bytes', ids)
            legacy = [f for f in startup.verify(broken, m, 'legacy', 2) if f['id'] == 'K1_kit_bytes']
            self.assertEqual({f['level'] for f in legacy}, {'warn'}, 'legacy game: warning only')

    def test_own_probe_file_is_replaced_for_a_new_game(self):
        root = build24(tmpdir(self) / 'native', extra={'webp-decode-probe.js': 'module.exports = 1;\n'})
        rec = finalize(root)
        self.assertEqual(rec['blocks'], [])
        self.assertEqual(T.sha256((root / 'webp-decode-probe.js').read_bytes()), probe_spec()['sha256'])

    def test_editor_main_of_an_unknown_engine_gets_no_probe_script(self):
        root = build24(tmpdir(self) / 'native')
        (root / 'cocos/cocos2d-js-min.js').write_text('var ENGINE_VERSION = "2.4.3"; window.cc = {};\n')
        finalize(root)
        self.assertFalse((root / 'webp-decode-probe.js').exists(), 'the editor main.js does not require it')


# ------------------------------------------------------------------------------------------------ item 2
GUARDED = GAME24.replace("__globalAdapter.adaptEngine();\n",
                         "__globalAdapter.adaptEngine();\nrequire('./native-load-guard')(cc, tt);\n")


class OwnStartupFileStillRequired(unittest.TestCase):
    def test_moved_file_leaves_no_require_behind(self):
        root = build24(tmpdir(self) / 'native', game=GUARDED, extra={'native-load-guard.js': 'module.exports = 1;\n'})
        rec = finalize(root)
        self.assertEqual(rec['blocks'], [])
        self.assertFalse((root / 'native-load-guard.js').exists(), 'own startup file moved away')
        game = (root / 'game.js').read_text()
        self.assertIn('// tiktok-kit-removed:startup24:', game)
        missing = [n for n in ENTRY_REQUIRE.findall(game) if not (root / n).is_file()
                   and not (root / n).with_suffix('.js').is_file()]
        self.assertEqual(missing, [], 'pkg81: "missing entry require: ./native-load-guard" from the commented line')

    def test_file_another_package_file_requires_is_kept_with_a_warning(self):
        root = build24(tmpdir(self) / 'native', game=GUARDED, extra={
            'native-load-guard.js': 'module.exports = 1;\n',
            'native-helper.js': "var g = require('./native-load-guard');\nmodule.exports = g;\n"})
        rec = finalize(root)
        self.assertEqual(rec['blocks'], [])
        self.assertTrue((root / 'native-load-guard.js').is_file(), 'kept: native-helper.js still loads it')
        self.assertIn("\nrequire('./native-load-guard')(cc, tt);\n", (root / 'game.js').read_text(),
                      'its game.js line is left as it was')
        kept = [w for w in step(rec, 'startup')['warnings'] if w['id'] == 'K_W_own_startup_kept'
                and (w.get('evidence') or {}).get('file') == 'native-load-guard.js']
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]['evidence']['required_by'], ['native-helper.js'])

    def test_a_comment_that_names_the_file_does_not_keep_it(self):
        root = build24(tmpdir(self) / 'native', game=GUARDED, extra={
            'native-load-guard.js': 'module.exports = 1;\n',
            'notes.js': "// old: require('./native-load-guard')\nmodule.exports = 0;\n"})
        finalize(root)
        self.assertFalse((root / 'native-load-guard.js').exists())


# ------------------------------------------------------------------------------------------------ item 3
def project24(root, extra):
    (root / 'assets').mkdir(parents=True, exist_ok=True)
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}\n')
    for rel, text in extra.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    return root


def kit_text(name):
    return (T.KIT_DIR / 'assets' / 'tiktok-platform' / name).read_text(encoding='utf-8')


class SameNameModules(unittest.TestCase):
    def mabel_like(self):
        return project24(tmpdir(self) / 'project', {
            'assets/scripts/platform/TikTokMissionService.js': kit_text('TikTokMissionService.js'),
            'assets/scripts/platform/TikTokMissionService.js.meta': '{"uuid": "a1"}\n',
            'assets/scripts/platform/MissionFlow.js': 'module.exports = {old: true};\n',
            'assets/scripts/platform/MissionFlow.js.meta': '{"uuid": "a2"}\n',
            'assets/scripts/Game.js': "var flow = require('./platform/MissionFlow');\n"})

    def run_step(self, root, policy):
        ctx = T.Ctx('source', root, board='remake', engine=2, policy=policy, manifest=T.load_manifest())
        return kit_sources.apply(ctx), ctx

    @staticmethod
    def module_names(root):
        names = {}
        for p in (root / 'assets').rglob('*'):
            if p.suffix in ('.js', '.ts') and p.is_file():
                names.setdefault(p.stem, []).append(p.relative_to(root).as_posix())
        return names

    def test_new_game_keeps_one_file_per_module_name(self):
        root = self.mabel_like()
        out, ctx = self.run_step(root, 'new')
        self.assertEqual(out['blocks'], [])
        names = self.module_names(root)
        for name in ('TikTokMissionService', 'MissionFlow'):
            self.assertEqual(names[name], ['assets/tiktok-platform/%s.js' % name],
                             'Creator 2.4: "Filename conflict, the module %s both defined in ..."' % name)
            removed = root / '.tiktok-kit/removed/assets/scripts/platform' / (name + '.js')
            self.assertTrue(removed.is_file() and Path(str(removed) + '.meta').is_file(), 'moved with its .meta')
        warns = [w for w in out['warnings'] if w['id'] == 'K_W_kit_module_duplicate']
        self.assertEqual(sorted(w['evidence']['file'] for w in warns),
                         ['assets/scripts/platform/MissionFlow.js', 'assets/scripts/platform/TikTokMissionService.js'])
        self.assertEqual({w['evidence']['file'].rsplit('/', 1)[-1]: w['evidence']['same_bytes'] for w in warns},
                         {'MissionFlow.js': False, 'TikTokMissionService.js': True})
        self.assertEqual(kit_sources.verify(ctx), [])
        again, _ = self.run_step(root, 'new')
        self.assertEqual((again['changed'], again['warnings']), ([], []), 'second run changes nothing')

    def test_legacy_game_is_reported_only(self):
        root = self.mabel_like()
        out, ctx = self.run_step(root, 'legacy')
        self.assertTrue((root / 'assets/scripts/platform/MissionFlow.js').is_file())
        self.assertTrue((root / 'assets/scripts/platform/TikTokMissionService.js').is_file())
        self.assertEqual(len([w for w in out['warnings'] if w['id'] == 'K_W_kit_module_duplicate']), 2)
        self.assertEqual({f['level'] for f in kit_sources.verify(ctx) if f['id'] == 'K_kit_module_duplicate'},
                         {'warn'})

    def test_typescript_with_the_kit_name_counts_too(self):
        root = project24(tmpdir(self) / 'project', {'assets/game/SaveStore.ts': 'export default {};\n'})
        self.run_step(root, 'new')
        self.assertEqual(self.module_names(root)['SaveStore'], ['assets/tiktok-platform/SaveStore.js'])


# ------------------------------------------------------------------------------------------------ item 4
# Shapes copied from the DotsDelivery v40 adapter-min.js (Cocos 2.4.4).
LABEL_244 = ('cc&&cc.Label&&(cc.gfx,r=cc.Label,__globalAdapter.isSubContext||(i=(o=document.createElement("canvas"))'
             '.getContext("2d"),a={canvas:o,context:i},cc.game.on(cc.game.EVENT_ENGINE_INITED,function(){Object.assign('
             'r._canvasPool,{get:function(){return a},put:function(){}})})));')
PASS_244 = 'function A(e,t,n){n(null,e)}function C(e,t,n){S(e,A,t,t.onFileProgress,n)}'
SUB_OLD = 'r.isSubContext=void 0===tt.getOpenDataContext;'
SDK_OLD = 'u=tt.getSystemInfoSync(),Number.parseInt(u.SDKVersion[0])<2&&(s=1);'
FS_OLD = 'function N(t,e,n){c(t,function(e){e?n(null,t):n(new Error("file ".concat(t," does not exist!")))})}'


def native_adapter(adapter, version='2.4.4'):
    return {'game.js': b'require("adapter-min.js");', 'game.json': b'{}', 'project.config.json': b'{}',
            'cocos/cocos2d-js-min.js': ('cc.ENGINE_VERSION="%s";' % version).encode(),
            'adapter-min.js': ('tt.getSystemInfoSync();' + adapter).encode()}


class Adapter244(unittest.TestCase):
    def test_244_forms_count_as_fixed_and_sub_context_is_rewritten(self):
        files = native_adapter(LABEL_244 + SUB_OLD + PASS_244)
        self.assertEqual(adapter_fix.detect(files)['rules'],
                         {'sdk_version': 'fixed', 'sub_context': 'old', 'pkg_fs_access': 'fixed'})
        d = tmpdir(self)
        for rel, data in files.items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_bytes(data)
        out = adapter_fix.apply(d)
        self.assertEqual(out['blocks'], [])
        self.assertEqual([c['rule'] for c in out['changed']], ['sub_context'])
        self.assertEqual(adapter_fix.detect(native_files(d))['rules'], {r: 'fixed' for r in adapter_fix.RULES})

    def test_244_rules_need_their_whole_shape(self):
        # no Label canvas-pool module: an adapter without any SDK test is still not recognised (v7.5 behaviour)
        self.assertEqual(adapter_fix.detect(native_adapter(SUB_OLD + PASS_244))['rules']['sdk_version'], 'unknown')
        # a pass-through that is not the in-package download handler
        self.assertEqual(adapter_fix.detect(native_adapter(LABEL_244 + SUB_OLD + 'function A(e,t,n){n(null,e)}'))
                         ['rules']['pkg_fs_access'], 'unknown')

    def test_later_adapters_with_the_old_forms_are_still_rewritten(self):
        files = native_adapter(LABEL_244 + SDK_OLD + SUB_OLD + FS_OLD + PASS_244, version='2.4.6')
        self.assertEqual(adapter_fix.detect(files)['rules'],
                         {'sdk_version': 'old', 'sub_context': 'old', 'pkg_fs_access': 'old'})

    @unittest.skipUnless(DOTS.is_file(), 'DotsDelivery v40 package not on this machine')
    def test_dots_delivery_v40_passes_the_adapter_step(self):
        d = tmpdir(self) / 'native'
        with zipfile.ZipFile(DOTS) as z:
            z.extractall(d)
        rec = finalize(d)
        self.assertEqual([b['id'] for b in step(rec, 'adapter')['blocks']], [],
                         'v7.7 wave 2: ADAPTER_FIX_sdk_version, ADAPTER_FIX_pkg_fs_access')
        self.assertEqual([c['what'] for c in step(rec, 'adapter')['changed']],
                         [adapter_fix.LABEL['sub_context']])


if __name__ == '__main__':
    unittest.main()
