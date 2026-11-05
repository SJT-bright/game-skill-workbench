#!/usr/bin/env python3
"""F2 (发版自检 C4): the platform parts ResLoader, AudioService and rewarded-guard pass the package resource check.

What it proves, in a few seconds (needs node; skipped without it):
  1. the three parts as shipped give 0 findings in audit_runtime_resources.discover() (the C4 rule: no load call whose
     paths the scanner cannot list, no loader escape); the old lines of each part (11.13 F/H/D batch) are found;
  2. a fixture 2.4 game that uses ResLoader + a ResKeys table made by make_res_keys.py and AudioService passes the
     package resource check (required_requests against the bundle config.json): every table path is listed, with
     bundle and type, from the game's own table;
  3. a fixture game whose own code builds a path ('ui/' + name) is still reported, at its own file and line.
  python3 -B test_kit_parts_resources.py
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_runtime_resources as R  # noqa: E402
import make_res_keys as M  # noqa: E402

KIT = HERE.parent / 'assets' / 'platform-kit' / 'parts'
PARTS = ('ResLoader.js', 'AudioService.js', 'rewarded-guard.js')
# The lines C4 reported on the 11.13 candidate (report v7.9-en11.13-dev_20261104-184311, checks.C4), cut to the
# smallest program that still has the call: what the parts did before F2.
OLD = {
    'ResLoader.js:179': "function fetch(b, key, Type, cb) { b.load(key.path, Type, cb); }\n",
    'AudioService.js:107/238': ("function S(b) { this.backend = b; }\n"
                                "S.prototype._load = function (e, done) { this.backend.load(e.file, done); };\n"
                                "function backend24(cc) { return { load: function (path, cb) {\n"
                                "  if (cc.resources && typeof cc.resources.load === 'function') cc.resources.load(path, cc.AudioClip, cb);\n"
                                "  else cc.loader.loadRes(path, cc.AudioClip, cb); } }; }\n"),
    'rewarded-guard.js:148': ("function wrap(raw) { var proxy = {};\n"
                              "  if (typeof raw.load === 'function') proxy.load = function () { return raw.load.apply(raw, arguments); };\n"
                              "  return proxy; }\n"),
}
GAME = ("var Res = require('ResLoader'); var ResKeys = require('ResKeys'); var AudioService = require('AudioService');\n"
        "var audio = AudioService.create({backend: AudioService.backend24(cc)});\n"
        "audio.register({click: {file: 'audio/click'}, bgm: {key: ResKeys.audio_bgm, kind: 'music'}});\n"
        "Res.request(ResKeys.ui_gift_box).then(function (f) { node.spriteFrame = f; });\n"
        "Res.request(ResKeys['skin_' + level]);\n")
DYNAMIC = "function show(name, cb) { cc.resources.load('ui/' + name, cc.SpriteFrame, cb); }\n"
PNG = b'\x89PNG\r\n\x1a\n' + b'\0' * 16


def findings(report):
    out = [s for s in report.get('sites') or [] if not (isinstance(s.get('paths'), list) and s['paths'])]
    return out + list(report.get('escapes') or [])


def put(path, data=b'', meta=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
    if meta is not None:
        path.with_name(path.name + '.meta').write_text(json.dumps(meta), encoding='utf-8')


@unittest.skipUnless(shutil.which('node'), 'node not on PATH')
class KitParts(unittest.TestCase):
    def test_parts_have_no_findings(self):
        for name in PARTS:
            report = R.discover({'parts/' + name: (KIT / name).read_bytes()})
            self.assertEqual(findings(report), [], name)

    def test_old_lines_are_found(self):
        for label, src in OLD.items():
            report = R.discover({'old.js': src.encode()})
            self.assertTrue(findings(report), 'old %s was not reported' % label)


@unittest.skipUnless(shutil.which('node'), 'node not on PATH')
class FixtureGame(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='f2 kit parts ')
        root = Path(self.temp.name) / 'Game'
        put(root / 'project.json', json.dumps({'engine': 'cocos-creator-js', 'version': '2.4.15'}))
        res = root / 'assets' / 'resources'
        put(res.with_name('resources.meta'), '{}')
        put(res / 'ui' / 'gift_box.png', PNG, {'type': 'sprite'})
        put(res / 'skin_1.png', PNG, {'type': 'sprite'})
        put(res / 'skin_2.png', PNG, {'type': 'sprite'})
        put(res / 'audio' / 'click.mp3', b'ID3', {})
        put(res / 'audio' / 'bgm.mp3', b'ID3', {})
        self.assertEqual(M.main(['--project', str(root)]), 0)
        self.table = (root / 'assets' / 'scripts' / 'generated' / 'ResKeys.js').read_bytes()
        self.entries = M.build(root, 2)['entries']
        # The built resources bundle catalog (Cocos 2.4 debug form: class name per path).
        self.config = json.dumps({'name': 'resources', 'types': [], 'paths': {
            str(i): [e['path'], 'cc.' + e['type']] for i, e in enumerate(self.entries)}}).encode()

    def tearDown(self):
        self.temp.cleanup()

    def package(self, game):
        files = {'src/project.js': game.encode(), 'src/ResKeys.js': self.table,
                 'assets/resources/config.json': self.config}
        files.update({'src/' + n: (KIT / n).read_bytes() for n in PARTS})
        return files

    def test_table_paths_listed_and_check_passes(self):
        required, inventory, _ = R.required_requests(self.package(GAME))
        want = {('resources', e['path'], 'cc.' + e['type']) for e in self.entries}
        self.assertEqual(len(want), 5)
        self.assertEqual(required, want, 'every ResKeys path is a required request, nothing else')
        listed = {(s['source'], p) for s in inventory['sites'] for p in s['paths']}
        self.assertEqual({p for _, p in listed}, {e['path'] for e in self.entries})
        self.assertEqual({src for src, _ in listed}, {'src/ResKeys.js'}, 'paths come from the game table, not the parts')

    def test_missing_file_is_reported(self):
        files = self.package(GAME)
        files['assets/resources/config.json'] = json.dumps({'name': 'resources', 'types': [], 'paths': {
            str(i): [e['path'], 'cc.' + e['type']] for i, e in enumerate(self.entries) if e['path'] != 'ui/gift_box'}}).encode()
        with self.assertRaisesRegex(ValueError, 'missing/type mismatch: resources:ui/gift_box'):
            R.required_requests(files)

    def test_dynamic_path_in_game_code_still_reported(self):
        with self.assertRaises(ValueError) as caught:
            R.required_requests(self.package(GAME + DYNAMIC))
        text = str(caught.exception)
        self.assertIn('unresolved dynamic resource calls', text)
        self.assertIn('"source": "src/project.js"', text)
        self.assertIn("'ui/' + name", text)
        self.assertNotIn('src/ResLoader.js', text)
        self.assertNotIn('src/AudioService.js', text)


if __name__ == '__main__':
    unittest.main()
