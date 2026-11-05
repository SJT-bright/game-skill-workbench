#!/usr/bin/env python3
"""P04 (生成时预防): home-page resource list + size ledger, checked when work starts. Runs in a few seconds.

  python3 -B test_first_screen_budget.py

Fixtures are tiny Cocos 2.4 projects written to a temp folder (big files are sparse, nothing is built):
  * the plan's fixture: home scene shows 3 pictures, the level page (a prefab in the "level" subpackage) 40 big
    pictures, the loading scene's script calls cc.resources.load('bgm', cc.AudioClip) before cc.director.loadScene.
  * 美女快跑's way: the loading script calls loadBundle for resources, hallScene and gameScene before the home page
    (15.7 MiB in the census).
  * 喂小动物's way: 61 abandoned scenes left in the main package.
For each, the old start-of-work flow (audit_package_estimate.py, the only source-stage size tool before P04) says
nothing, and first_screen.py / startup_budget.py report it at once.
"""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid as uuidlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_package_estimate as old_estimate  # noqa: E402
import first_screen as FS  # noqa: E402
import startup_budget as B  # noqa: E402
import make_res_keys as RK  # noqa: E402

B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + (64).to_bytes(4, 'big') * 2 + b'\x08\x06\x00\x00\x00'
MiB = 1024 * 1024


def compress(u):
    h = u.replace('-', '')
    out, rest = h[:5], h[5:]
    for i in range(0, len(rest), 3):
        v = int(rest[i:i + 3], 16)
        out += B64[v >> 6] + B64[v & 63]
    return out


class Fixture:
    def __init__(self, root: Path):
        self.root = root
        (root / 'assets').mkdir(parents=True)
        (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}', encoding='utf-8')
        (root / 'settings').mkdir()
        self.builder = {'excludeScenes': []}

    def meta(self, rel, data):
        (self.root / 'assets' / (rel + '.meta')).write_text(json.dumps(data), encoding='utf-8')

    def bundle(self, folder, name=None, sub=True):
        (self.root / 'assets' / folder).mkdir(parents=True, exist_ok=True)
        self.meta(folder, {'uuid': str(uuidlib.uuid4()), 'isBundle': True, 'bundleName': name or folder.split('/')[-1],
                           'compressionType': {'bytedance': 'subpackage' if sub else 'merge_all_json'}, 'subMetas': {}})

    def image(self, rel, size=4096):
        p = self.root / 'assets' / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('wb') as f:
            f.write(PNG)
            f.truncate(size)
        frame = str(uuidlib.uuid4())
        self.meta(rel, {'uuid': str(uuidlib.uuid4()), 'type': 'sprite', 'subMetas': {p.stem: {'uuid': frame}}})
        return frame

    def raw(self, rel, size):
        p = self.root / 'assets' / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('wb') as f:
            f.write(b'ID3')
            f.truncate(size)
        self.meta(rel, {'uuid': str(uuidlib.uuid4()), 'subMetas': {}})

    def script(self, rel, text):
        p = self.root / 'assets' / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        u = str(uuidlib.uuid4())
        self.meta(rel, {'uuid': u, 'isPlugin': False, 'subMetas': {}})
        return compress(u)

    def serialized(self, rel, kind, frames=(), scripts=()):
        objs = [{'__type__': 'cc.SceneAsset' if kind == 'scene' else 'cc.Prefab'}, {'__type__': 'cc.Node', '_name': 'root'}]
        for f in frames:
            objs.append({'__type__': 'cc.Sprite', 'node': {'__id__': 1}, '_spriteFrame': {'__uuid__': f}})
        for s in scripts:
            objs.append({'__type__': s, 'node': {'__id__': 1}})
        p = self.root / 'assets' / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(objs), encoding='utf-8')
        u = str(uuidlib.uuid4())
        self.meta(rel, {'uuid': u, 'subMetas': {}})
        return u

    def save_builder(self, start_uuid):
        self.builder['startScene'] = start_uuid
        (self.root / 'settings' / 'builder.json').write_text(json.dumps(self.builder), encoding='utf-8')


def plan_fixture(root):
    """The plan's fixture: 3 home pictures, 40 big level pictures, BGM loaded on the loading page."""
    fx = Fixture(root)
    fx.bundle('resources')
    fx.raw('resources/bgm.mp3', 900 * 1024)
    fx.bundle('level')
    big = [fx.image('level/img/tile_%02d.png' % i, 300 * 1024) for i in range(40)]
    fx.serialized('level/LevelPage.prefab', 'prefab', frames=big)
    home_frames = [fx.image('ui/%s.png' % n, 120 * 1024) for n in ('home_bg', 'btn_play', 'logo')]
    fx.script('scripts/HomeUtil.js', 'module.exports = { fmt: function (n) { return String(n); } };\n')
    home_js = fx.script('scripts/Home.js', "var U = require('HomeUtil');\ncc.Class({ extends: cc.Component,\n"
                        "  play: function () { cc.assetManager.loadBundle('level', function (e, b) { b.load('LevelPage'); }); } });\n")
    load_js = fx.script('scripts/Loading.js', "cc.Class({ extends: cc.Component, onLoad: function () {\n"
                        "  cc.resources.load('bgm', cc.AudioClip, function (err, clip) { cc.audioEngine.playMusic(clip, true); });\n"
                        "  cc.director.loadScene('Home'); } });\n")
    boot = fx.serialized('scenes/Loading.fire', 'scene', scripts=[load_js])
    fx.serialized('scenes/Home.fire', 'scene', frames=home_frames, scripts=[home_js])
    fx.save_builder(boot)
    return fx


def meinv_fixture(root):
    """美女快跑: resources, hallScene and gameScene all requested before the home page."""
    fx = Fixture(root)
    for b in ('resources', 'hallScene', 'gameScene'):
        fx.bundle(b)
    fx.image('resources/atlas/common.png', int(5.2 * MiB))
    hall = fx.image('hallScene/hall_bg.png', int(5.0 * MiB))
    fx.image('gameScene/road.png', int(5.5 * MiB))
    load_js = fx.script('scripts/Loading.js', "cc.Class({ extends: cc.Component, onLoad: function () {\n"
                        "  var n = 0, done = function () { if (++n === 3) cc.director.loadScene('Home'); };\n"
                        "  cc.assetManager.loadBundle('resources', done);\n  cc.assetManager.loadBundle('hallScene', done);\n"
                        "  cc.assetManager.loadBundle('gameScene', done); } });\n")
    boot = fx.serialized('scenes/Loading.fire', 'scene', scripts=[load_js])
    fx.serialized('scenes/Home.fire', 'scene', frames=[hall])
    fx.save_builder(boot)
    return fx


def feed_fixture(root):
    """喂小动物: 61 abandoned scenes left in the main package, each with its own 100 KB picture."""
    fx = Fixture(root)
    fx.bundle('resources')
    play = fx.image('ui/btn_play.png', 50 * 1024)
    home_js = fx.script('scripts/Home.js', "cc.Class({ extends: cc.Component, play: function () { cc.director.loadScene('Game'); } });\n")
    boot = fx.serialized('scenes/Home.fire', 'scene', frames=[play], scripts=[home_js])
    fx.serialized('scenes/Game.fire', 'scene', frames=[fx.image('ui/board.png', 80 * 1024)])
    for i in range(61):
        fx.serialized('scenes/old/level_old_%02d.fire' % i, 'scene', frames=[fx.image('old/bg_%02d.png' % i, 100 * 1024)])
    fx.save_builder(boot)
    return fx


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


class FirstScreenBudget(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='p04_first_screen_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def project(self, make, name):
        return make(self.tmp / name).root

    def test_plan_fixture_old_flow_silent_new_flow_reports(self):
        p = self.project(plan_fixture, 'plan')
        old = old_estimate.audit(p)
        self.assertTrue(old['passed'], old['problems'])          # old start-of-work flow: nothing reported
        r = FS.analyze(p)
        home = {x['file'] for x in r['home_needs']['files']}
        for n in ('home_bg', 'btn_play', 'logo'):
            self.assertIn('assets/ui/%s.png' % n, home)
        self.assertIn('assets/scripts/HomeUtil.js', home)        # found through parse_package_requires.cjs
        deferred = {x['file']: x for x in r['deferred']}
        for i in range(40):
            row = deferred['assets/level/img/tile_%02d.png' % i]
            self.assertFalse(row['in_first_download'])
        self.assertEqual(r['home_scene'], 'assets/scenes/Home.fire')
        self.assertTrue(any(x.startswith('audio_before_first_frame') and 'bgm' in x for x in r['problems']), r['problems'])
        self.assertIn('home_bg', r['home_assets_allowed'])
        self.assertEqual(quiet(FS.main, ['--project', str(p)]), 1)
        self.assertTrue((p / 'docs/startup/first-screen.json').is_file() and (p / 'docs/startup/budget.json').is_file())
        # English board: the same finding is a warning, not a stop
        loc = FS.analyze(p, 'localize')
        self.assertFalse(loc['problems'])
        self.assertTrue(any('audio_before_first_frame' in w for w in loc['warnings']))

    def test_ledger_refuses_an_11mb_home_picture_at_once(self):
        p = self.project(plan_fixture, 'ledger')
        quiet(FS.main, ['--project', str(p)])
        before = (p / 'docs/startup/budget.json').read_bytes()
        small = Fixture.__new__(Fixture)
        small.root = p
        small.image('ui/home_banner.png', 400 * 1024)
        ok = B.record(p, 'assets/ui/home_banner.png', source='test')
        self.assertTrue(ok['first_download'] and not ok['summary']['over'])
        small.image('ui/home_huge.png', 11 * MiB)
        mid = (p / 'docs/startup/budget.json').read_bytes()
        self.assertNotEqual(before, mid)
        with self.assertRaises(B.BudgetError) as cm:
            B.record(p, 'assets/ui/home_huge.png', source='postprocess')
        self.assertIn('10 MiB', str(cm.exception))
        self.assertEqual(mid, (p / 'docs/startup/budget.json').read_bytes())      # nothing written on refusal
        self.assertEqual(quiet(B.main, ['--project', str(p), 'add', '--file', 'assets/ui/home_huge.png']), 1)
        # the same 11 MB file inside a subpackage loaded after the home page is fine
        small.bundle('shop')
        small.image('shop/huge.png', 11 * MiB)
        quiet(FS.main, ['--project', str(p)])
        self.assertFalse(B.record(p, 'assets/shop/huge.png', need='deferred')['first_download'])

    def test_audio_rows_from_import_audio(self):
        p = self.project(plan_fixture, 'audio')
        quiet(FS.main, ['--project', str(p)])
        out = B.record_many(p, [('assets/resources/audio/sfx_click.wav', 20000, 'deferred')], 'import_audio')
        self.assertTrue(out['warnings'])          # the loading page loads bgm from resources: resources is downloaded early
        q = self.project(feed_fixture, 'audio2')
        quiet(FS.main, ['--project', str(q)])
        out = B.record_many(q, [('assets/resources/audio/sfx_click.wav', 20000, 'deferred')], 'import_audio')
        self.assertFalse(out['warnings'])         # resources is a subpackage nobody asks for before home: not counted
        self.assertFalse(B.load(q)['files']['assets/resources/audio/sfx_click.wav']['first_download'])
        out = B.record_many(p, [('assets/audio/sfx_tap.wav', 20000, 'deferred')], 'import_audio')
        self.assertTrue(out['warnings'] and 'own subpackage' in out['warnings'][0])
        with self.assertRaises(B.BudgetError):
            B.record_many(p, [('assets/audio/bgm_long.wav', 12 * MiB, 'deferred')], 'import_audio', dry_run=True)

    def test_meinv_prehome_subpackages(self):
        p = self.project(meinv_fixture, 'meinv')
        old = old_estimate.audit(p)
        self.assertTrue(old['passed'], old['problems'])
        r = FS.analyze(p)
        self.assertEqual(sorted(r['pre_home_bundles']), ['gameScene', 'hallScene', 'resources'])
        self.assertGreater(r['estimate']['first_download_bytes'], B.LIMIT)
        kinds = [x.split(':')[0] for x in r['problems']]
        self.assertIn('first_download_over_limit', kinds)
        self.assertEqual(sum(1 for x in r['problems'] if x.startswith('prehome_bundle_not_home')), 2)   # resources, gameScene
        self.assertFalse(any('hallScene' in x and x.startswith('prehome') for x in r['problems']))
        self.assertTrue(FS.analyze(p, 'localize')['problems'])   # over 10 MiB stops an English game too

    def test_feed_abandoned_scenes_and_level_plan_whitelist(self):
        p = self.project(feed_fixture, 'feed')
        old = old_estimate.audit(p)
        self.assertTrue(old['passed'], old['problems'])
        r = FS.analyze(p)
        self.assertEqual(len(r['unused_scenes']), 61)
        self.assertTrue(any(x.startswith('unused_scene_in_main: 61') for x in r['problems']), r['problems'])
        before = r['estimate']['first_download_bytes']
        run = subprocess.run([sys.executable, '-B', str(HERE / 'make_level_plan.py'), '--project', str(p), '--seed', '7',
                              '--out', str(p / 'assets/resources/config/level_plan.json')], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        wl = json.loads((p / 'docs/startup/build-scenes.json').read_text(encoding='utf-8'))
        self.assertEqual(wl['scenes'], ['Game', 'Home'])
        self.assertEqual(len(wl['excluded']), 61)
        builder = json.loads((p / 'settings/builder.json').read_text(encoding='utf-8'))
        self.assertEqual(len(builder['excludeScenes']), 61)
        r2 = FS.analyze(p)
        self.assertFalse(r2['problems'], r2['problems'])
        self.assertLess(r2['estimate']['first_download_bytes'], before - 61 * 100 * 1024)

    def test_res_keys_reads_home_and_deferred_groups(self):
        p = self.project(plan_fixture, 'reskeys')
        quiet(RK.main, ['--project', str(p)])
        plain = (p / 'assets/scripts/generated/ResKeys.js').read_text(encoding='utf-8')
        self.assertNotIn('ResKeys.HOME', plain)                  # without first-screen.json: table as before
        quiet(FS.main, ['--project', str(p)])
        quiet(RK.main, ['--project', str(p)])
        text = (p / 'assets/scripts/generated/ResKeys.js').read_text(encoding='utf-8')
        home = json.loads(text.split('ResKeys.HOME = Object.freeze(')[1].split(');')[0])
        later = json.loads(text.split('ResKeys.DEFERRED = Object.freeze(')[1].split(');')[0])
        self.assertEqual(home, ['bgm'])                          # the loading page loads it (and is told not to)
        self.assertIn('level_img_tile_00', later)

    def test_no_machine_paths(self):
        for name in ('first_screen.py', 'startup_budget.py'):
            text = (HERE / name).read_text(encoding='utf-8')
            for bad in ('/Users/', '/opt/homebrew', 'C:\\\\', 'GameAudioLibrary'):
                self.assertNotIn(bad, text, name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
