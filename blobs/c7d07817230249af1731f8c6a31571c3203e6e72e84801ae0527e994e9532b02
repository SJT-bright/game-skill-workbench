#!/usr/bin/env python3
"""R4K2: a stock Cocos 3.6/3.7 mini-game export is not refused whole-package by the SystemJS resource check.

Before R4K2 every 3.6/3.7 bytedance export hit one of three refusals in discover() before any resource call was
looked at (CubeDigits 3.7.1, StreetBreakout 3.6.1, BubbleAxolotl 3.6.2 on this machine):
  - src/import-map.js maps "virtual:///prerequisite-imports/main" to "chunks:///_virtual/main" ->
    'nonlocal SystemJS import target';
  - the stock 3.6/3.7 template's handler 'plugin:': (u) => { requirePlugin(u); } -> 'unknown SystemJS namespace handler';
  - src/settings.json scriptPackages ["../src/chunks/bundle.js"] -> 'nonlocal/missing SystemJS script package'.
chunks:///<name> is a SystemJS module name; the package script with a literal System.register("chunks:///<name>", ...)
defines it. Fixtures below are cut from the real CubeDigits 3.7.1 export and Creator 3.7.1's bytedance game.ejs.
What it proves (needs node; skipped without it):
  1. the stock 3.7 / 3.6 shapes pass discover() and required_requests(); the chunk files become module targets;
  2. still refused, old and new: a chunks:/// name no script registers, one registered by two scripts, a
     chunks:/// name with '..', http(s)/protocol-relative/absolute targets, a remote or missing scriptPackage,
     a bare requirePlugin handler under any key but 'plugin:';
  3. a real dynamic load inside the chunk module is still reported.
Old code: R4K2_SCRIPTS=<base-tree>/remake-core/scripts python3 -B test_systemjs_chunks_import_map.py  (group 1 fails).
  python3 -B test_systemjs_chunks_import_map.py
"""
import json
import os
import shutil
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = Path(os.environ.get('R4K2_SCRIPTS') or HERE).resolve()
sys.path.insert(0, str(SCRIPTS))
import audit_runtime_resources as R  # noqa: E402

# Creator 3.7.1 templates/bytedance-mini-game/game.ejs (also 3.6.2), as exported into CubeDigits game.js.
WARMUP_37 = ('const importMap = require("src/import-map.js").default;\n'
             'System.warmup({\n importMap,\n importMapUrl: \'src/import-map.js\',\n'
             ' defaultHandler: (urlNoSchema) => {\n  require(\'.\' + urlNoSchema);\n },\n'
             ' handlers: {\n  \'plugin:\': (urlNoSchema) => {\n   requirePlugin(urlNoSchema);\n  },\n },\n});\n'
             "System.import('./application.js').then(({ Application }) => new Application());\n")
# StreetBreakout 3.6.1 export: conditional plugin handler.
WARMUP_36 = WARMUP_37.replace('requirePlugin(urlNoSchema);',
                              "typeof requirePlugin === 'function' ? requirePlugin(urlNoSchema) : require(urlNoSchema);")
IMPORT_MAP_37 = ('"use strict";\n\nObject.defineProperty(exports, "__esModule", {\n  value: true\n});\n'
                 'exports["default"] = void 0;\nvar _default = {\n  "imports": {\n'
                 '    "virtual:///prerequisite-imports/internal": "chunks:///_virtual/internal",\n'
                 '    "virtual:///prerequisite-imports/resources": "chunks:///_virtual/resources",\n'
                 '    "virtual:///prerequisite-imports/main": "chunks:///_virtual/main",\n'
                 '    "cc": "./../cocos-js/cc.js"\n  }\n};\nexports["default"] = _default;\n')
MAIN_37 = ('System.register("chunks:///_virtual/Const.ts",["cc"],(function(e){"use strict";var n;return{setters:[function(e){n=e.cclegacy}],'
           'execute:function(){e("LEVELS",60)}}}));\n'
           'System.register("chunks:///_virtual/main",["./Const.ts"],(function(){"use strict";return{setters:[null],execute:function(){}}}));\n')
BUNDLE_37 = ('System.register([], function(_export, _context) { return { execute: function () {\n'
             'System.register("chunks:///_virtual/rollupPluginModLoBabelHelpers.js",[],(function(e){"use strict";return{execute:function(){e({extends:Object.assign})}}}));\n'
             '} }; });\n')
SETTINGS_37 = {'CocosEngine': '3.7.1', 'assets': {}, 'scripting': {'scriptPackages': ['../src/chunks/bundle.js']}}


def package(warmup=WARMUP_37, import_map=IMPORT_MAP_37, main=MAIN_37, settings=None, extra=None):
    files = {'game.js': warmup.encode(),
             'src/import-map.js': import_map.encode(),
             'src/settings.json': json.dumps(settings or SETTINGS_37).encode(),
             'src/chunks/bundle.js': BUNDLE_37.encode(),
             'cocos-js/cc.js': b'System.register("cc",[],function(){return{execute:function(){}}});',
             'application.js': b'System.register([],function(e){return{execute:function(){e("Application",function(){})}}});',
             'assets/main/index.js': main.encode(),
             'assets/internal/index.js': b'System.register("chunks:///_virtual/internal",[],(function(){"use strict";return{execute:function(){}}}));\n',
             'subpackages/resources/game.js': b'System.register("chunks:///_virtual/resources",[],(function(){"use strict";return{execute:function(){}}}));\n'}
    files.update(extra or {})
    return files


def refusal(files):
    try:
        R.discover(files)
    except ValueError as error:
        return str(error)
    return None


@unittest.skipUnless(shutil.which('node'), 'node not on PATH')
class StockExportPasses(unittest.TestCase):
    def test_37_stock_export(self):
        report = R.discover(package())
        targets = {row['path'] for row in report['module_file_sites']}
        self.assertTrue({'assets/main/index.js', 'assets/internal/index.js', 'subpackages/resources/game.js',
                         'src/import-map.js', 'cocos-js/cc.js'} <= targets, targets)
        self.assertEqual(report['escapes'], [], 'the plugin: handler is the exact stock one')
        required, _, _ = R.required_requests(package())
        self.assertEqual(required, set())

    def test_36_conditional_plugin_handler(self):
        self.assertIsNone(refusal(package(warmup=WARMUP_36)))

    def test_38_project_script_package_unchanged(self):
        settings = dict(SETTINGS_37, CocosEngine='3.8.8', scripting={'scriptPackages': ['project://src/chunks/bundle.js']})
        only_cc = '\n'.join(line for line in IMPORT_MAP_37.split('\n') if 'chunks:///' not in line)
        self.assertIsNone(refusal(package(warmup=WARMUP_36, settings=settings, import_map=only_cc)),
                          'control (3.8.8 shape): passes old and new')


@unittest.skipUnless(shutil.which('node'), 'node not on PATH')
class StillRefused(unittest.TestCase):
    def assertRefused(self, files, pattern=None):
        message = refusal(files)
        self.assertIsNotNone(message, 'package was not refused')
        if pattern and SCRIPTS == HERE:
            self.assertRegex(message, pattern)

    def test_unregistered_chunk(self):
        self.assertRefused(package(main=MAIN_37.replace('chunks:///_virtual/main"', 'chunks:///_virtual/other"')),
                           'not registered by a package script')

    def test_chunk_registered_twice(self):
        self.assertRefused(package(extra={'assets/extra/index.js': b'System.register("chunks:///_virtual/main",[],function(){return{execute:function(){}}});'}),
                           'registered by several package scripts')

    def test_chunk_name_with_dotdot(self):
        bad = 'chunks:///_virtual/../main'
        self.assertRefused(package(import_map=IMPORT_MAP_37.replace('chunks:///_virtual/main', bad),
                                   main=MAIN_37.replace('chunks:///_virtual/main', bad)), 'nonlocal SystemJS import target')

    def test_remote_targets(self):
        for target in ('https://cdn.example.com/main.js', 'http://cdn.example.com/main.js', '//cdn.example.com/main.js',
                       '/abs/main.js', 'plugin:remote/main'):
            with self.subTest(target):
                self.assertRefused(package(import_map=IMPORT_MAP_37.replace('chunks:///_virtual/main', target)),
                                   'nonlocal SystemJS import target')

    def test_bad_script_packages(self):
        for script in ('https://cdn.example.com/bundle.js', '../src/chunks/missing.js', 'src/chunks/bundle.js', 'project://src/none.js'):
            with self.subTest(script):
                self.assertRefused(package(settings=dict(SETTINGS_37, scripting={'scriptPackages': [script]})),
                                   'nonlocal/missing SystemJS script package')

    def test_bare_require_plugin_only_under_plugin_key(self):
        self.assertRefused(package(warmup=WARMUP_37.replace("'plugin:'", "'project:'")), 'unknown SystemJS namespace handler')
        self.assertRefused(package(warmup=WARMUP_37.replace("defaultHandler: (urlNoSchema) => {\n  require('.' + urlNoSchema);",
                                                           "defaultHandler: (urlNoSchema) => {\n  requirePlugin(urlNoSchema);")),
                           'unknown SystemJS namespace handler')


@unittest.skipUnless(shutil.which('node'), 'node not on PATH')
class RealLoadsInChunksStillReported(unittest.TestCase):
    def test_dynamic_load_in_chunk_module(self):
        main = MAIN_37.replace('execute:function(){e("LEVELS",60)}',
                               'execute:function(){e("show",function(p){n.resources.load("ui/"+p)})}')
        files = package(main=main)
        if SCRIPTS != HERE and refusal(files):
            self.skipTest('old code refuses the whole package first')
        with self.assertRaisesRegex(ValueError, 'unresolved dynamic resource calls'):
            R.required_requests(files)


if __name__ == '__main__':
    unittest.main()
