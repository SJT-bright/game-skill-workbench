#!/usr/bin/env python3
"""11.17.15 native step upload_compat (鸽鸽小羊 upload fix): subpackage root '/', game.js './x.js', project.config.
Run: python3 -B test_upload_compat.py"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tiktok_finalize_steps import Ctx  # noqa: E402
from tiktok_finalize_steps import upload_compat as U  # noqa: E402

STOCK_GAME_JS = """"use strict";

try { require('./host-shim.js').install(globalThis.TTMinis&&TTMinis.game||globalThis.tt); } catch (e) { } // tiktok-kit:hostshim24:2.0
require('adapter-min.js');

__globalAdapter.init();

require('cocos/cocos2d-js-min.js');

__globalAdapter.adaptEngine();

require('./ccRequire');

require('./src/settings'); // Introduce Cocos Service here


require('./main'); // TODO: move to common
window.boot();
"""
FIXED_GAME_JS = (STOCK_GAME_JS.replace("require('adapter-min.js')", "require('./adapter-min.js')")
                 .replace("require('cocos/cocos2d-js-min.js')", "require('./cocos/cocos2d-js-min.js')")
                 .replace("require('./ccRequire')", "require('./ccRequire.js')")
                 .replace("require('./src/settings')", "require('./src/settings.js')")
                 .replace("require('./main')", "require('./main.js')"))
GAME_JSON = """{
    "deviceOrientation": "portrait",
    "subpackages": [
        {
            "name": "MainScene",
            "root": "subpackages/MainScene"
        },
        {
            "name": "AudioAssets",
            "root": "subpackages/AudioAssets"
        }
    ]
}
"""
CONFIG = {'setting': {'urlCheck': False, 'es6': True, 'postcss': True, 'minified': False, 'newFeature': True},
          'appid': '7683427172773644296', 'projectname': 'game'}


def build(root, game_js=STOCK_GAME_JS, game_json=GAME_JSON, config=None, indent=4):
    for name in ('host-shim.js', 'adapter-min.js', 'cocos/cocos2d-js-min.js', 'ccRequire.js', 'src/settings.js',
                 'main.js', 'subpackages/MainScene/game.js', 'subpackages/AudioAssets/game.js'):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('// ' + name)
    (root / 'game.js').write_text(game_js)
    (root / 'game.json').write_text(game_json)
    (root / 'project.config.json').write_text(json.dumps(config or CONFIG, indent=indent))


class UploadCompat(unittest.TestCase):
    def run_step(self, root, engine=2):
        return U.apply(Ctx('native', root, engine=engine))

    def test_stock_24_build_gets_all_three_fixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root)
            out = self.run_step(root)
            self.assertEqual(out['blocks'], [])
            self.assertEqual(sorted(c['file'] for c in out['changed']), ['game.js', 'game.json', 'project.config.json'])
            self.assertEqual((root / 'game.js').read_text(), FIXED_GAME_JS)
            self.assertEqual((root / 'game.json').read_text(),
                             GAME_JSON.replace('"root": "subpackages/MainScene"', '"root": "subpackages/MainScene/"')
                             .replace('"root": "subpackages/AudioAssets"', '"root": "subpackages/AudioAssets/"'))
            cfg = json.loads((root / 'project.config.json').read_text())
            self.assertEqual(cfg, {'setting': {'urlCheck': True, 'es6': False, 'minified': True},
                                   'appid': '7683427172773644296', 'projectname': 'game'})
            self.assertTrue((root / 'project.config.json').read_text().split('\n')[1].startswith('    "'),
                            'keeps the 4-space indentation Cocos writes')
            self.assertEqual(self.run_step(root)['state'], 'kit_current', 'second run changes nothing')
            self.assertEqual(U.verify(Ctx('native', root).files(), 2), [])

    def test_only_listed_things_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root)
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.run_step(root)
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(sorted(n for n in after if after[n] != before.get(n)),
                             ['game.js', 'game.json', 'project.config.json'])
            self.assertEqual(set(after), set(before), 'no file added or removed')

    def test_missing_target_is_reported_never_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root, game_js=STOCK_GAME_JS + "require('./missing-file');\n")
            out = self.run_step(root)
            self.assertIn("require('./missing-file')", (root / 'game.js').read_text())
            self.assertTrue(any(w['id'] == 'K_W_upload_compat_require' for w in out['warnings']))

    def test_commented_require_is_not_a_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root, game_js=STOCK_GAME_JS + "// require('./native-load-guard')(cc, tt);  moved away by startup\n")
            out = self.run_step(root)
            self.assertIn("// require('./native-load-guard')(cc, tt);", (root / 'game.js').read_text())
            self.assertEqual([w for w in out['warnings'] if w['id'] == 'K_W_upload_compat_require'], [])

    def test_root_that_is_not_a_folder_is_left_alone_and_subPackages_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gj = json.dumps({'subPackages': [{'name': 'a', 'root': 'subpackages/MainScene'},
                                             {'name': 'b', 'root': 'not/here'}]}, indent=2)
            build(root, game_json=gj)
            self.run_step(root)
            roots = [s['root'] for s in json.loads((root / 'game.json').read_text())['subPackages']]
            self.assertEqual(roots, ['subpackages/MainScene/', 'not/here'])

    def test_cocos3_es6_only_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root)
            out = self.run_step(root, engine=3)
            cfg = json.loads((root / 'project.config.json').read_text())
            self.assertIs(cfg['setting']['es6'], True)
            self.assertIs(cfg['setting']['minified'], True)
            self.assertIs(cfg['setting']['urlCheck'], True)
            self.assertNotIn('postcss', cfg['setting'])
            self.assertTrue(any(w['id'] == 'K_W_upload_compat_config' for w in out['warnings']))

    def test_registered_last_in_native_steps(self):
        import tiktok_finalize
        self.assertEqual(tiktok_finalize.NATIVE_STEPS[-1], 'upload_compat')


if __name__ == '__main__':
    unittest.main()
