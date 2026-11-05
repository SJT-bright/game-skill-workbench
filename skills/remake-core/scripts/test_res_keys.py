#!/usr/bin/env python3
"""生成时预防 P12: make_res_keys.py writes assets/scripts/generated/ResKeys.js (2.4) / ResKeys.ts (3.x) from the project.
Adding a picture adds a constant (and --check reports the old table as stale); deleting it lists every ResKeys.<id> in the
game scripts that now points at nothing; types come from the file and its .meta (2.4 sprite/raw, 3.x sprite-frame/texture
with the sub-asset path); direct engine loads are listed, and fail only with --strict. The generated 2.4 table is fed to
the platform part ResLoader in Node (when node is on PATH): a table entry loads, a string path throws.
Synthetic projects only, static, about a second. Run: python3 -B test_res_keys.py"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_res_keys as M  # noqa: E402

RES_LOADER = HERE.parent / 'assets' / 'platform-kit' / 'parts' / 'ResLoader.js'
PNG = b'\x89PNG\r\n\x1a\n' + b'\0' * 16
HOME_JS = ("var ResKeys = require('ResKeys');\n"
           "Res.request(ResKeys.ui_gift_box);\n"
           "Res.request(ResKeys['game_bg']);\n"
           "// ResKeys.in_a_comment is ignored\n")


def put(path, data=b'', meta=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
    if meta is not None:
        path.with_name(path.name + '.meta').write_text(json.dumps(meta), encoding='utf-8')


def img_meta(engine, kind):
    if engine == 2:
        return {'type': {'sprite-frame': 'sprite', 'texture': 'raw'}[kind]}
    return {'importer': 'image', 'userData': {'type': kind}}


class Base(unittest.TestCase):
    engine = 2

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='res keys ')
        self.root = Path(self.temp.name) / 'Game'
        a = self.root / 'assets'
        e = self.engine
        if e == 2:
            put(self.root / 'project.json', json.dumps({'engine': 'cocos-creator-js', 'version': '2.4.15'}))
            put(a / 'game.meta', json.dumps({'isBundle': True, 'bundleName': 'game'}))
        else:
            put(self.root / 'package.json', json.dumps({'name': 'g', 'creator': {'version': '3.8.6'}}))
            put(a / 'game.meta', json.dumps({'importer': 'directory', 'userData': {'isBundle': True, 'bundleName': 'game'}}))
        put(a / 'resources' / 'ui' / 'gift_box.png', PNG, img_meta(e, 'sprite-frame'))
        put(a / 'resources' / 'ui' / 'map_tex.png', PNG, img_meta(e, 'texture'))
        put(a / 'game' / 'bg.jpg', PNG, img_meta(e, 'sprite-frame'))
        put(a / 'resources' / 'cfg' / 'levels.json', '{"levels": [1]}', {})
        put(a / 'resources' / 'cfg' / 'words.txt', 'a', {})
        put(a / 'resources' / 'sfx' / 'click.mp3', b'ID3', {})
        put(a / 'resources' / 'Main.fire', '[]', {})
        put(a / 'outside' / 'not_loadable.png', PNG, img_meta(e, 'sprite-frame'))
        put(a / 'scripts' / 'Home.js', HOME_JS)
        self.out = a / 'scripts' / 'generated' / ('ResKeys.ts' if e == 3 else 'ResKeys.js')

    def tearDown(self):
        self.temp.cleanup()

    def run_tool(self, *extra):
        return M.main(['--project', str(self.root)] + list(extra))

    def entries(self):
        return {x['id']: x for x in M.build(self.root, self.engine)['entries']}

    def common_types(self):
        t = self.entries()
        self.assertEqual(set(t), {'ui_gift_box', 'ui_map_tex', 'game_bg', 'cfg_levels', 'cfg_words', 'sfx_click'},
                         'scenes skipped; files outside a bundle are not loadable by path')
        self.assertEqual((t['ui_gift_box']['type'], t['ui_gift_box']['bundle']), ('SpriteFrame', 'resources'))
        self.assertEqual(t['ui_map_tex']['type'], 'Texture2D', 'texture import is never asked for as a SpriteFrame')
        self.assertEqual(t['game_bg']['bundle'], 'game')
        self.assertEqual((t['cfg_levels']['type'], t['cfg_words']['type'], t['sfx_click']['type']), ('JsonAsset', 'TextAsset', 'AudioClip'))
        return t


class Cocos24(Base):
    engine = 2

    def test_types_and_paths(self):
        t = self.common_types()
        self.assertEqual(t['ui_gift_box']['path'], 'ui/gift_box')
        self.assertEqual(t['game_bg']['path'], 'bg')

    def test_add_picture_adds_constant_and_check_sees_stale(self):
        start = time.time()
        self.assertEqual(self.run_tool(), 0)
        text = self.out.read_text(encoding='utf-8')
        self.assertIn('ui_gift_box: k("ui_gift_box", "ui/gift_box", "SpriteFrame", "resources")', text)
        self.assertNotIn('coin', text)
        self.assertEqual(self.run_tool('--check'), 0, 'fresh table is up to date')
        put(self.root / 'assets' / 'resources' / 'ui' / 'coin.png', PNG, img_meta(2, 'sprite-frame'))
        self.assertEqual(self.run_tool('--check'), 1, 'a new picture makes the table stale')
        self.assertEqual(self.run_tool(), 0)
        self.assertIn('ui_coin: k("ui_coin", "ui/coin", "SpriteFrame", "resources")', self.out.read_text(encoding='utf-8'))
        self.assertLess(time.time() - start, 5)

    def test_delete_picture_lists_dangling_references(self):
        self.assertEqual(self.run_tool(), 0)
        (self.root / 'assets' / 'resources' / 'ui' / 'gift_box.png').unlink()
        report = self.report()
        self.assertFalse(report['ok'])
        self.assertEqual([(d['file'], d['line'], d['id']) for d in report['dangling']],
                         [('assets/scripts/Home.js', 2, 'ui_gift_box')], 'the comment line is not counted')

    def test_raw_loads_info_unless_strict(self):
        put(self.root / 'assets' / 'scripts' / 'Old.js', "cc.resources.load('ui/' + name, cc.SpriteFrame, cb);\n")
        self.assertEqual(self.run_tool(), 0, 'English games: original direct loads are information only')
        self.assertEqual(len(self.report()['raw_loads']), 1)
        self.assertEqual(self.run_tool('--strict'), 1, 'new games: a direct engine load fails')

    def test_generated_table_works_with_res_loader(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not on PATH')
        self.assertEqual(self.run_tool(), 0)
        js = ("var K=require(process.argv[1]);var R=require(process.argv[2]);var ok=R.isKey(K.ui_gift_box)&&Object.isFrozen(K);"
              "try{R.load('ui/gift_box');ok=false}catch(e){ok=ok&&e.code==='not_a_key'}"
              "try{K.zzz=1}catch(e){}ok=ok&&K.zzz===undefined;console.log(ok?'OK':'BAD')")
        r = subprocess.run([node, '-e', js, str(self.out), str(RES_LOADER)], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.stdout.strip(), 'OK', r.stdout + r.stderr)

    def report(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            M.main(['--project', str(self.root), '--json'])
        return json.loads(buf.getvalue())


class Cocos3(Base):
    engine = 3

    def test_sub_asset_paths_and_ts_table(self):
        t = self.common_types()
        self.assertEqual(t['ui_gift_box']['path'], 'ui/gift_box/spriteFrame')
        self.assertEqual(t['ui_map_tex']['path'], 'ui/map_tex/texture')
        self.assertEqual(self.run_tool(), 0)
        text = self.out.read_text(encoding='utf-8')
        self.assertIn('export const ResKeys', text)
        self.assertIn('"ui/gift_box/spriteFrame"', text)


if __name__ == '__main__':
    unittest.main()
