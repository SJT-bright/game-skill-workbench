#!/usr/bin/env python3
"""R4F2 (生成时预防, census #7 and #8): fonts, 3.x scene list and `source` without first-screen.json. Seconds.

  python3 -B test_first_screen_fonts.py

Fixtures are tiny Cocos projects in a temp folder (font files are sparse; fontTools is not needed, it is mocked):
  * 蛋壳特工队's way: a whole 600 KB TTF in the main package, used by the home page's Label. The old first_screen.py
    reports nothing about fonts; the new one lists its bytes, blocks a new game (warns an English game) and says
    "not_run" instead of passing when fontTools is missing.
  * a font subset_fonts.py wrote (sha256 in docs/startup/font-subset.json) passes; a font changed afterwards does not.
  * Cocos 3.x: an unused scene. Old: make_level_plan writes no scene list (3.x has no excludeScenes) and the scene
    stays an error. New: docs/startup/build-config-3x.json lists the kept scenes and first_screen stops counting it.
  * `tiktok_finalize.py source` on a project without docs/startup/first-screen.json writes it first.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import first_screen as FS  # noqa: E402
import test_first_screen_budget as T  # noqa: E402
try:
    import subset_fonts as SF  # noqa: E402
except ImportError:            # old tree: no subset step at all
    SF = None
KB = 1024


def font(fx, rel, size):
    p = fx.root / 'assets' / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('wb') as f:
        f.write(b'\x00\x01\x00\x00')
        f.truncate(size)
    u = str(T.uuidlib.uuid4())
    fx.meta(rel, {'uuid': u, 'subMetas': {}})
    return u


def label_scene(fx, rel, font_uuid, text='PLAY', scripts=()):
    objs = [{'__type__': 'cc.SceneAsset'}, {'__type__': 'cc.Node', '_name': 'root'},
            {'__type__': 'cc.Label', 'node': {'__id__': 1}, '_N$string': text, '_N$file': {'__uuid__': font_uuid}}]
    objs += [{'__type__': s, 'node': {'__id__': 1}} for s in scripts]
    p = fx.root / 'assets' / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(objs, ensure_ascii=False), encoding='utf-8')
    u = str(T.uuidlib.uuid4())
    fx.meta(rel, {'uuid': u, 'subMetas': {}})
    return u


def font_game(root, size=600 * KB, in_sub=False):
    """Loading scene -> Home scene whose Label uses assets/fonts/Title.ttf (in main, or in a later subpackage)."""
    fx = T.Fixture(root)
    if in_sub:
        fx.bundle('level')
    u = font(fx, ('level/' if in_sub else '') + 'fonts/Title.ttf', size)
    load_js = fx.script('scripts/Loading.js', "cc.Class({ extends: cc.Component, onLoad: function () {\n"
                        "  cc.director.loadScene('Home'); } });\n")
    boot = fx.serialized('scenes/Loading.fire', 'scene', scripts=[load_js])
    label_scene(fx, 'scenes/Home.fire', u, 'Ünlock 金币')
    fx.save_builder(boot)
    return fx


class Fonts(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory(prefix='r4f2 fonts ')
        self.root = Path(self.td.name) / 'game'

    def tearDown(self):
        self.td.cleanup()

    def fonts_of(self, report):
        self.assertIn('fonts', report, 'first_screen reports no font bytes')
        return report['fonts']

    def test_whole_font_in_main_blocks_new_game(self):
        font_game(self.root)
        with mock.patch.object(SF, 'fonttools_available', return_value=True):
            r = FS.analyze(self.root, 'new')
        f = self.fonts_of(r)
        self.assertEqual(f['first_download_font_bytes'], 600 * KB)
        self.assertEqual(f['over_threshold'], ['assets/fonts/Title.ttf'])
        self.assertEqual(f['status'], 'needs_subset')
        self.assertTrue(any(p.startswith('font_not_subset') for p in r['problems']), r['problems'])

    def test_english_game_only_warns(self):
        font_game(self.root)
        with mock.patch.object(SF, 'fonttools_available', return_value=True):
            r = FS.analyze(self.root, 'localize')
        self.assertFalse(any(p.startswith('font_not_subset') for p in r['problems']))
        self.assertTrue(any(w.startswith('font_not_subset') for w in r['warnings']))

    def test_no_fonttools_is_not_run_never_ok(self):
        font_game(self.root)
        with mock.patch.object(SF, 'fonttools_available', return_value=False):
            r = FS.analyze(self.root, 'new')
            out = SF.subset(self.root)
            code = SF.main(['--project', str(self.root)])
        self.assertEqual(self.fonts_of(r)['status'], 'not_run')
        self.assertTrue(any('not_run' in p for p in r['problems']))
        self.assertEqual(out['status'], 'not_run')
        self.assertEqual(out['would_cut'], ['assets/fonts/Title.ttf'])
        self.assertEqual(code, 3)
        self.assertEqual((self.root / 'assets/fonts/Title.ttf').stat().st_size, 600 * KB)   # nothing changed

    def test_small_font_and_later_subpackage_pass(self):
        font_game(self.root, size=60 * KB)
        r = FS.analyze(self.root, 'new')
        self.assertEqual(self.fonts_of(r)['status'], 'ok')
        self.assertFalse(any(p.startswith('font_not_subset') for p in r['problems']))
        other = Path(self.td.name) / 'sub'
        fx = T.Fixture(other)
        fx.bundle('level')
        font(fx, 'level/fonts/Big.ttf', 900 * KB)
        fx.serialized('level/Level.prefab', 'prefab')
        load_js = fx.script('scripts/Loading.js', "cc.Class({ extends: cc.Component, onLoad: function () {\n"
                            "  cc.director.loadScene('Home'); } });\n")
        boot = fx.serialized('scenes/Loading.fire', 'scene', scripts=[load_js])
        fx.serialized('scenes/Home.fire', 'scene')
        fx.save_builder(boot)
        r = FS.analyze(other, 'new')
        self.assertEqual(self.fonts_of(r)['over_threshold'], [])

    def test_recorded_subset_passes_changed_font_fails(self):
        font_game(self.root)
        rel = 'assets/fonts/Title.ttf'
        rec = self.root / 'docs/startup/font-subset.json'
        rec.parent.mkdir(parents=True)
        rec.write_text(json.dumps({'fonts': {rel: {'sha256': SF.sha256(self.root / rel)}}}), encoding='utf-8')
        r = FS.analyze(self.root, 'new')
        self.assertEqual(self.fonts_of(r)['status'], 'ok')
        self.assertTrue(r['fonts']['fonts'][0]['subset'])
        with (self.root / rel).open('r+b') as f:
            f.write(b'\x00\x01\x00\x01')
        r = FS.analyze(self.root, 'new')
        self.assertEqual(r['fonts']['over_threshold'], [rel])

    def test_charset_from_game_text(self):
        fx = font_game(self.root)
        fx.script('scripts/Pause.js', "var t = '暂停'; var s = \"Résumé\";\n")
        (self.root / 'assets/levels.json').write_text(json.dumps({'title': '第一关'}, ensure_ascii=False), encoding='utf-8')
        chars = SF.collect_chars(self.root, extra='★')
        for c in 'Ü金币暂停é第一关★0aZ!':
            self.assertIn(c, chars)
        self.assertEqual(SF.subset(self.root, dry_run=True)['status'], 'dry_run')

    def test_preflight_hint(self):
        font_game(self.root)
        line = SF.preflight_line(self.root, available=False)
        self.assertIn('fontTools', line)
        self.assertIn('未执行', line)
        self.assertIsNone(SF.preflight_line(self.root, available=True))
        empty = Path(self.td.name) / 'empty'
        (empty / 'assets').mkdir(parents=True)
        self.assertIsNone(SF.preflight_line(empty, available=False))


class Scenes3x(unittest.TestCase):
    def test_unused_scene_listed_out_for_3x(self):
        import make_level_plan as MLP
        with tempfile.TemporaryDirectory(prefix='r4f2 3x ') as td:
            root = Path(td) / 'g3'
            fx = T.Fixture(root)
            (root / 'project.json').unlink()
            (root / 'package.json').write_text(json.dumps({'creator': {'version': '3.8.8'}}), encoding='utf-8')
            load_js = fx.script('scripts/Loading.ts', "import { director } from 'cc';\n"
                                "export class Loading { onLoad() { director.loadScene('Home'); } }\n")
            fx.serialized('scenes/Loading.scene', 'scene', scripts=[load_js])
            fx.serialized('scenes/Home.scene', 'scene')
            fx.serialized('scenes/OldDemo.scene', 'scene')
            before = FS.analyze(root, 'new')
            self.assertEqual(before['unused_scenes'], ['assets/scenes/OldDemo.scene'])
            out = MLP.write_build_scenes(root)
            cfg = root / 'docs/startup/build-config-3x.json'
            self.assertTrue(cfg.is_file(), 'no 3.x scene list written: %s' % out)
            data = json.loads(cfg.read_text(encoding='utf-8'))
            self.assertEqual(data['platform'], 'bytedance-mini-game')
            self.assertEqual(sorted(s['url'] for s in data['scenes']),
                             ['db://assets/scenes/Home.scene', 'db://assets/scenes/Loading.scene'])
            self.assertTrue(data.get('startScene'))
            after = FS.analyze(root, 'new')
            self.assertEqual(after['unused_scenes'], [])
            self.assertFalse(any(p.startswith('unused_scene_in_main') for p in after['problems']))
            self.assertNotIn('assets/scenes/OldDemo.scene', after['build_scenes'])


class SourceWritesFirstScreen(unittest.TestCase):
    def test_source_without_first_screen_generates_it(self):
        import tiktok_finalize as TF
        with tempfile.TemporaryDirectory(prefix='r4f2 source ') as td:
            root = Path(td) / 'game'
            font_game(root, size=40 * KB)
            out = root / 'docs/startup/first-screen.json'
            self.assertTrue(hasattr(TF, 'ensure_first_screen'), 'source does not make first-screen.json')
            note = TF.ensure_first_screen(root, 'remake')
            self.assertTrue(out.is_file())
            self.assertIn('first-screen.json', note)
            self.assertEqual(json.loads(out.read_text(encoding='utf-8'))['board'], 'new')
            self.assertIsNone(TF.ensure_first_screen(root, 'remake'))        # an existing list is left alone
            self.assertTrue((root / 'docs/startup/budget.json').is_file())


if __name__ == '__main__':
    unittest.main(verbosity=1)
