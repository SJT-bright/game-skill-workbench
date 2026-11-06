#!/usr/bin/env python3
"""R4K1 (发版自检 C4/C11): the package resource check does not take the platform-kit SaveStore for a resource loader.

Before R4K1, `save.load()` on a platform-kit SaveStore was an `unknown_receiver` load site, so every game that read
its save the documented way was refused by required_requests ("unresolved dynamic resource calls"):
  - 3.x CubeDigits (CC3x立方体数字.zip, delivered 2026-10-31): `this.store = new t.SaveStore(...), this.store.load()`
    with `t = this.kit`, `get kit(){ return globalThis.TikTokKit }`;
  - 2.4 ReefGuard pkg_v8 `c = new i(s) ... c.load()` and MeteorBlaster `(s = new i(c())).load()`, `i = e("SaveStore")`
    (e = the 2.4 bundle wrapper's require).
What it proves, in a few seconds (needs node; skipped without it):
  1. those shapes (cut from the real packages) and the shapes README_接入说明.md documents give no load site;
  2. a real loader is still reported in the same file: cc.resources.load(variable), a game variable named SaveStore
     that holds cc.resources, a SaveStore parameter, a SaveStore instance whose load was replaced, a file that
     overwrites TikTokKit.SaveStore, a static TikTokKit.SaveStore.load(path), and ResLoader (it calls Cocos loaders).
Old code: R4K1_SCRIPTS=<base-tree>/remake-core/scripts python3 -B test_kit_instance_resources.py  (group 1 fails).
  python3 -B test_kit_instance_resources.py
"""
import os
import shutil
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = Path(os.environ.get('R4K1_SCRIPTS') or HERE).resolve()
sys.path.insert(0, str(SCRIPTS))
import audit_runtime_resources as R  # noqa: E402

KIT = HERE.parent / 'assets' / 'platform-kit'
LOADS = ('load(', 'loadDir(', 'preload(')

# 3.x, cut from CubeDigits assets/main/index.js (SystemJS module, minified class with a compiled `kit` getter).
CUBE_3X = (
    'System.register("chunks:///_virtual/Platform.ts",["./rollupPluginModLoBabelHelpers.js","cc"],function(e){'
    'var t,n,o;return{setters:[function(e){t=e.createClass},function(e){n=e.sys;o=e.director}],execute:function(){'
    'e("Platform",function(){function i(){this.store=void 0,this.ads=void 0,this.initialized=!1}var e=i.prototype;'
    'return e.getSaveStore=function(){return this.init(),this.store},'
    'e.init=function(){if(!this.initialized){var e=this.kit;if(!(e&&e.SaveStore&&e.RewardedService))throw new Error("Platform services could not load.");'
    'this.store=new e.SaveStore({level:0,meta:{}},{storage:n.localStorage}),this.store.load(),this.ads=new e.RewardedService,this.initialized=!0}},'
    't(i,[{key:"kit",get:function(){return globalThis.TikTokKit}}]),i}());'
    'e("Skins",function(){function s(){this.store=void 0}s.prototype.open=function(e){this.store=e.getSaveStore(),this.store.load()};return s}());'
    '}}});\n')
# 3.x, the shapes README_接入说明.md documents (TikTokKit.SaveStore, kit.SaveStore, a kit() helper with `|| {}`).
DOC_3X = ('var kit = globalThis.TikTokKit;\nvar save = new kit.SaveStore({coins: 0});\nsave.load();\n'
          'var other = new TikTokKit.SaveStore({coins: 0}); other.load();\n'
          'var P = {kit: function () { return globalThis.TikTokKit || {}; }};\n'
          'var third = null; function boot() { third = new (P.kit().SaveStore)({}); third.load(); }\n')
# 2.4 bundle, cut from MeteorBlaster and ReefGuard assets/main/index.js; the real kit SaveStore.js is a module of it.
BUNDLE_24 = (
    'window.__require=function e(t,n,r){return t}({'
    'GameServices:[function(e,t,i){"use strict";var n=e("SaveStore"),s=null;function c(){return{best:0}}'
    't.exports={init:function(){if(s)return s;(s=new n(c())).load();return s},'
    'store:function(){var o=null;if(!o){var r=e("SaveStore");(o=new r(c())).load()}return o}}},{SaveStore:"SaveStore"}],'
    'ReefSave:[function(e,t){var i=e("SaveStore"),c=null,s={pearls:500};function m(){if(!c){var t=(c=new i(s))._fill;'
    'c._fill=function(e){return t.call(c,e)};var r=c.load();c._fill=t;var u=c.update;c.update=function(e){return "unavailable"===c.status&&c.load(),u.call(c,e)}}return c}'
    't.exports={get:m}},{SaveStore:"SaveStore"}],'
    'SaveStore:[function(require,module,exports){%s},{}]'
    '},{},["GameServices","ReefSave"]);\n')
# 2.4 source shape from README_接入说明.md (a plain require()).
DOC_24 = "var SaveStore = require('SaveStore');\nvar save = new SaveStore({coins: 0, level: 1, skins: {}});\nsave.load();\n"

# Real loads that must stay reported, old and new scanner alike.
REAL = {
    'cc.resources.load(variable)': "function show(name, cb) { cc.resources.load('ui/' + name, cc.SpriteFrame, cb); }\n",
    'game variable SaveStore = cc.resources': "var SaveStore = cc.resources;\nfunction f(p) { SaveStore.load(p, cc.SpriteFrame, function () {}); }\n",
    'SaveStore parameter': "function f(SaveStore, p) { SaveStore.load(p); }\nf(cc.resources, 'ui/a');\n",
    'instance load replaced': ("var kit = globalThis.TikTokKit; var s = new kit.SaveStore({});\n"
                               "s.load = function (p) { return cc.resources.load(p); };\ns.load(name);\n"),
    'TikTokKit.SaveStore overwritten': ("globalThis.TikTokKit.SaveStore = function () { return cc.resources; };\n"
                                        "var s = new TikTokKit.SaveStore(); s.load(name);\n"),
    'static TikTokKit.SaveStore.load(path)': "TikTokKit.SaveStore.load(name);\n",
    'ResLoader instance': "var Res = require('ResLoader'); var r = new Res(); r.load(name);\n",
    'unknown object': "function f(o) { o.store.load(name); }\n",
}


def load_sites(report, source=None):
    rows = [s for s in report.get('sites') or [] if source is None or s['source'] == source]
    rows = [s for s in rows if not (isinstance(s.get('paths'), list) and s['paths'] and not s.get('unknown_receiver'))]
    return [s['expression'] for s in rows] + [e['expression'] for e in report.get('escapes') or []
                                              if source is None or e['source'] == source]


def systemjs_files(game):
    return {'src/settings.json': b'{"CocosEngine":"3.7.1","assets":{},"scripting":{"scriptPackages":[]}}',
            'cocos-js/cc.js': b'System.register("cc",[],function(){return{execute:function(){}}});',
            'assets/main/index.js': game.encode(),
            'src/assets/tiktok-platform/SaveStore.plugin.js': (KIT / 'plugins-3x' / 'SaveStore.plugin.js').read_bytes(),
            'src/assets/tiktok-platform/RewardedService.plugin.js': (KIT / 'plugins-3x' / 'RewardedService.plugin.js').read_bytes()}


def bundle_24():
    kit = (KIT / 'assets' / 'tiktok-platform' / 'SaveStore.js').read_text(encoding='utf-8')
    return BUNDLE_24 % kit


@unittest.skipUnless(shutil.which('node'), 'node not on PATH')
class KitInstanceIsNotALoader(unittest.TestCase):
    def test_3x_cubedigits_shape(self):
        report = R.discover(systemjs_files(CUBE_3X))
        self.assertEqual(load_sites(report, 'assets/main/index.js'), [])
        self.assertEqual(load_sites(report), [], 'the 3.x kit plugins themselves stay clean')

    def test_3x_documented_shapes(self):
        report = R.discover(systemjs_files(DOC_3X))
        self.assertEqual(load_sites(report, 'assets/main/index.js'), [])

    def test_24_bundle_shapes(self):
        report = R.discover({'assets/main/index.js': bundle_24().encode()})
        self.assertEqual(load_sites(report), [])

    def test_24_documented_require(self):
        report = R.discover({'src/project.js': DOC_24.encode(),
                             'src/SaveStore.js': (KIT / 'assets' / 'tiktok-platform' / 'SaveStore.js').read_bytes()})
        self.assertEqual(load_sites(report), [])

    def test_24_package_check_passes(self):
        required, _, _ = R.required_requests({'assets/main/index.js': bundle_24().encode()})
        self.assertEqual(required, set())


@unittest.skipUnless(shutil.which('node'), 'node not on PATH')
class RealLoadsStillReported(unittest.TestCase):
    def test_24(self):
        for label, src in REAL.items():
            with self.subTest(label):
                report = R.discover({'src/game.js': src.encode()})
                self.assertTrue([x for x in load_sites(report, 'src/game.js') if any(k in x for k in LOADS) or 'load' in x],
                                '%s was not reported' % label)

    def test_3x(self):
        game = ('System.register("chunks:///_virtual/Shop.ts",["cc"],function(e){var r;return{setters:[function(e){r=e.resources}],'
                'execute:function(){var kit=globalThis.TikTokKit;var s=new kit.SaveStore({});s.load();'
                'e("show",function(n){r.load("ui/"+n)});}}});\n')
        sites = load_sites(R.discover(systemjs_files(game)), 'assets/main/index.js')
        self.assertIn('r.load("ui/"+n)', sites)  # old and new scanner
        if SCRIPTS == HERE:
            self.assertEqual(sites, ['r.load("ui/"+n)'], 'only the real load, not the kit SaveStore next to it')

    def test_same_bundle_real_load_next_to_kit(self):
        src = bundle_24().replace('t.exports={get:m}', 't.exports={get:m,art:function(n){cc.resources.load(n)}}')
        with self.assertRaisesRegex(ValueError, r'cc\.resources\.load\(n\)'):
            R.required_requests({'assets/main/index.js': src.encode()})


if __name__ == '__main__':
    unittest.main()
