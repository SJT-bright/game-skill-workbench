#!/usr/bin/env python3
"""v7.8 (总表 B30 D/E/B, S8 补, U1, H4, A12): the pure rules of the layout_state / button_sweep / ad_entries suites
(runtime_regression/layout_rules.mjs), run in Node on node lists shaped like the real dumps (boxes in phone points).
The browser half (hosts, geometry, real taps) is proven on real packages: references/runtime-regression.md and
briefs/out/W87/RESULT.md (全民飞车漂移 v1 / v3 refused, v3.1 and HappyCup v20.7.1 pass).
Run: python3 -B test_layout_gates.py
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULES = HERE / 'runtime_regression' / 'layout_rules.mjs'
I14 = {'W': 390, 'H': 844, 'cap': {'x0': 293, 'y0': 51, 'x1': 380, 'y1': 83}, 'safeBottom': 810}
SE = {'W': 375, 'H': 667, 'cap': {'x0': 278, 'y0': 24, 'x1': 365, 'y1': 56}, 'safeBottom': 667, 'capXUnmeasured': True}
MiB = 1048576


def node(body):
    exe = shutil.which('node')
    if not exe:
        raise unittest.SkipTest('node is required')
    js = 'const R = await import(%s);\nconst out = await (async () => {\n%s\n})();\nconsole.log(JSON.stringify(out));\n' % (
        json.dumps(RULES.as_uri()), body)
    r = subprocess.run([exe, '--input-type=module', '-e', js], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-1500:])
    return json.loads(r.stdout)


def btn(path, x0, y0, x1, y1, **kw):
    return dict({'path': path, 'kind': 'button', 'box': {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1}, 'interactable': True}, **kw)


def label(path, x0, y0, x1, y1, text='T', **kw):
    return dict({'path': path, 'kind': 'label', 'text': text, 'box': {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1}}, **kw)


def codes(findings):
    return sorted(set(f['code'] for f in findings))


class Level(unittest.TestCase):
    def test_new_blocks_legacy_warns_3x_only_startup(self):
        got = node('''return ['offscreen', 'startup_size', 'startup_audio', 'covered_3d', 'invalid_run', 'dead_button'].map(c => [c,
          R.level(c, {engine: '2.x', policy: 'new'}), R.level(c, {engine: '2.x', policy: 'legacy'}), R.level(c, {engine: '3.x', policy: 'new'})]);''')
        table = {c: (a, b, d) for c, a, b, d in got}
        self.assertEqual(table['offscreen'], ('block', 'warn', 'warn'))
        self.assertEqual(table['dead_button'], ('block', 'warn', 'warn'))
        self.assertEqual(table['startup_size'], ('block', 'warn', 'block'))     # 3.x: only the startup download blocks
        self.assertEqual(table['startup_audio'], ('block', 'warn', 'block'))
        self.assertEqual(table['invalid_run'], ('block', 'block', 'block'))      # never a game verdict: re-run


class Pass(unittest.TestCase):
    def test_edge_capsule_band(self):
        nodes = [btn('Canvas/cut', 350, 400, 400, 450), btn('Canvas/list/item', 380, 400, 460, 450, clipped=True),
                 btn('Canvas/gear', 300, 55, 340, 80), label('Canvas/title', 290, 60, 330, 75),
                 btn('Canvas/low', 100, 815, 200, 840), btn('Canvas/edge', 100, 790, 200, 816), btn('Canvas/ok', 100, 100, 200, 150),
                 btn('Canvas/full', 0, 0, 390, 844, layer=True)]
        got = node('return R.passFindings(%s, %s);' % (json.dumps(nodes), json.dumps(I14)))
        by = {(f['code'], f['path']): f for f in got}
        self.assertIn(('offscreen', 'Canvas/cut'), by)
        self.assertNotIn(('offscreen', 'Canvas/list/item'), by)                  # fix 2: scroll list items
        self.assertIn(('capsule', 'Canvas/gear'), by)
        self.assertIn(('capsule', 'Canvas/title'), by)
        self.assertFalse(by[('capsule', 'Canvas/gear')]['warnOnly'])
        self.assertFalse(by[('safe_area', 'Canvas/low')]['warnOnly'])           # centre in the band blocks
        self.assertTrue(by[('safe_area', 'Canvas/edge')]['warnOnly'])           # fix 3: only reaching in warns
        self.assertFalse([k for k in by if k[1] in ('Canvas/ok', 'Canvas/full')])
        se = node('return R.passFindings(%s, %s);' % (json.dumps([btn('Canvas/gear', 290, 30, 330, 50)]), json.dumps(SE)))
        self.assertTrue(se[0]['warnOnly'])                                       # SE capsule x is not measured

    def test_unit_shift_driftracer_v2(self):
        pt = [label('Canvas/MenuTop/Level/levelTxt', 60, 90, 120, 110), btn('Canvas/MenuTop/set', 10, 85, 50, 120),
              {'path': 'Canvas/wall', 'kind': 'sprite', 'box': {'x0': 0, 'y0': 300, 'x1': 50, 'y1': 400}},
              label('Canvas/timer', 10, 200, 60, 220, moving=True)]
        px = [label('Canvas/MenuTop/Level/levelTxt', 60, 256, 120, 276), btn('Canvas/MenuTop/set', 10, 251, 50, 286),
              {'path': 'Canvas/wall', 'kind': 'sprite', 'box': {'x0': 0, 'y0': 500, 'x1': 50, 'y1': 600}},
              label('Canvas/timer', 10, 260, 60, 280)]
        got = node('return R.unitShift(%s, %s);' % (json.dumps(pt), json.dumps(px)))
        self.assertEqual(sorted(s['path'] for s in got), ['Canvas/MenuTop/Level/levelTxt', 'Canvas/MenuTop/set'])
        self.assertEqual(got[0]['dy'], 166)                                     # the top bar fell 166 pt (v2 phone)
        same = node('return R.unitShift(%s, %s);' % (json.dumps(pt), json.dumps(pt)))
        self.assertEqual(same, [])                                               # a game reading the capsule right


class HomeRules(unittest.TestCase):
    REMAKE_OK = [btn('Canvas/top/settings', 10, 50, 50, 90, sig='settings gear'), btn('Canvas/play', 120, 500, 270, 580, sig='play'),
                 btn('Canvas/bottom/profile', 30, 740, 180, 790, sig='profile'), btn('Canvas/bottom/addhome', 210, 740, 360, 790, sig='add to home')]

    def run_rules(self, nodes, board, **kw):
        return node('return R.homeRules(%s, %s, %s, %s);' % (json.dumps(nodes), json.dumps(I14), json.dumps(board), json.dumps(kw)))

    def test_remake(self):
        self.assertEqual(self.run_rules(self.REMAKE_OK, 'remake')['findings'], [])
        bad = [dict(n) for n in self.REMAKE_OK]
        bad[0] = btn('Canvas/settings', 330, 400, 370, 440, sig='settings')
        bad.append(btn('Canvas/bottom/shop', 160, 745, 220, 785, sig='shop'))
        got = self.run_rules(bad, 'remake')
        self.assertEqual(codes(got['findings']), ['bottom_row', 'settings_pos'])
        none = self.run_rules(self.REMAKE_OK[1:], 'remake')
        self.assertIn('settings_pos', codes(none['findings']))

    def test_localize_keeps_original_buttons(self):
        orig = [btn('Canvas/set', 300, 400, 360, 440, sig='settings'), btn('Canvas/MenuBottom/shop', 20, 700, 100, 760, sig='shop'),
                btn('Canvas/__homeBottom/icon_profile_box', 20, 770, 180, 805, sig='profile'),
                btn('Canvas/__homeBottom/icon_add_home_box', 210, 770, 370, 805, sig='add to home')]
        self.assertEqual(self.run_rules(orig, 'localize')['findings'], [])      # settings anywhere, shop in the row: fine
        one = self.run_rules(orig[:3], 'localize')
        self.assertEqual(codes(one['findings']), ['platform_entries'])
        on_top = [orig[0], btn('Canvas/MenuBottom/shop', 20, 760, 170, 800, sig='shop')] + orig[2:]
        self.assertIn('sits on top of Canvas/MenuBottom/shop', ' '.join(f['msg'] for f in self.run_rules(on_top, 'localize')['findings']))
        kit = [orig[0], btn('Canvas/home/HomeEntries/a', 20, 770, 180, 805, sig='x'), btn('Canvas/home/HomeEntries/b', 210, 770, 370, 805, sig='y')]
        self.assertEqual(self.run_rules(kit, 'localize', kitEntries=['Canvas/home/HomeEntries/a', 'Canvas/home/HomeEntries/b'])['findings'], [])
        self.assertEqual(self.run_rules(orig[:1], None)['findings'], [])        # unknown board: not checked


class Startup(unittest.TestCase):
    def test_size_audio_and_cut(self):
        # DriftRacer v1: main 7.0 MiB + a 17.75 MiB subpackage requested before home (1.26 MiB of sound)
        got = node('''const per = {res: {total: 17.75 * %d, audio: 1.26 * %d}, later: {total: 3 * %d, audio: 2 * %d}};
          const subs = [{name: 'res', root: 'subpackages/res'}, {name: 'later', root: 'subpackages/later'}];
          const all = {total: 27.75 * %d, audio: 3.26 * %d};
          const cut = R.startupCut([{loading: 'GameScene', t: 900}, {launched: 'GameScene', t: 950}],
            [{t: 100, name: 'res'}, {t: 2000, name: 'later'}], 'GameScene');
          const sz = R.startupBytes(all, subs, per, cut.names);
          const small = R.startupBytes({total: 5.68 * %d, audio: 0}, [], {}, []);
          const url3 = R.startupCut([{loading: 'db://assets/start_menu.scene', t: 500}], [{t: 400, name: 'a'}, {t: 600, name: 'b'}], 'start_menu');
          return {cut, sz, f: R.startupFindings(sz, cut.names), small: R.startupFindings(small, []), url3};''' % ((MiB,) * 7))
        self.assertEqual(got['cut']['names'], ['res'])
        self.assertAlmostEqual(got['sz']['startupMiB'], 24.75, places=2)
        self.assertEqual(codes(got['f']), ['startup_audio', 'startup_size'])
        self.assertEqual(got['small'], [])
        self.assertEqual(got['url3']['names'], ['a'])                           # 3.x: scene URL matched by file name


class Sweep(unittest.TestCase):
    def test_diff_buttons_dead(self):
        got = node('''
          const a = {m: {'C/x': {uuid: 'u1', box: {x0: 0, y0: 0, x1: 10, y1: 10}, text: 'RETRY'}, 'C/t': {box: {x0: 0, y0: 0, x1: 5, y1: 5}, text: '1'}}};
          const b = {m: {'C/x': {uuid: 'u2', box: {x0: 0, y0: 0, x1: 10, y1: 10}, text: 'RETRY'}, 'C/t': {box: {x0: 0, y0: 0, x1: 5, y1: 5}, text: '2'}}};
          const d = R.snapDiff(a, b, new Set(['C/t']));
          const s = {m: {'C/p': {path: 'C/p', kind: 'button', box: {x0: 10, y0: 10, x1: 100, y1: 60}},
                         'C/p/inner': {path: 'C/p/inner', kind: 'button', box: {x0: 20, y0: 20, x1: 60, y1: 50}},
                         'C/list/i9': {path: 'C/list/i9', kind: 'button', maskHidden: true, box: {x0: 10, y0: 100, x1: 100, y1: 150}},
                         'C/off': {path: 'C/off', kind: 'button', interactable: false, box: {x0: 10, y0: 200, x1: 100, y1: 250}}}};
          return {d, buttons: R.sweepButtons(s, {W: 390, H: 844}).map(n => n.path),
            dead: [R.deadWhy({path: 'C/tab_skin', sig: 'skins'}), R.deadWhy({path: 'C/Skin1/SkinAction', sig: 'skinaction txt_equipped_button'}), R.deadWhy({path: 'C/b', handlers: 0}), R.deadWhy({path: 'C/b', handlers: 2})],
            pop: R.popupGeom({box: {x0: 300, y0: 60, x1: 360, y1: 90}}, %s), plat: R.PLATFORM_BEACON.test('mission'), ad: R.AD_WORDS.test('watch ad x2')};''' % json.dumps(I14))
        self.assertEqual(got['d']['moved'], ['C/x'])                            # fix 5: a rebuilt view counts
        self.assertEqual(got['d']['text'], [])                                   # the noisy label is ignored
        self.assertEqual(got['buttons'], ['C/p'])
        self.assertTrue(got['dead'][0].startswith('warn:') and got['dead'][1].startswith('warn:'))
        self.assertEqual(got['dead'][2], 'fail:cc.Button with no click handler at all (a fake button)')
        self.assertTrue(got['dead'][3].startswith('fail:'))
        self.assertEqual(got['pop'][0], ['on the TikTok capsule'])
        self.assertTrue(got['plat'] and got['ad'])


class AdEntries(unittest.TestCase):
    def test_adapter_shape_and_natural_revive(self):
        good = [{'id': 'revive', 'button': 'Canvas/__revive/btn_watch_ad', 'states': [{'name': 'natural_fall', 'actions': [
            {'tap': 'Canvas/btnks'}, {'wait_node': 'Canvas/__revive/btn_watch_ad', 'timeout': 45000, 'optional': True}]}]},
                {'id': 'offline_x2', 'button': 'Canvas/loading/anim/btnwj', 'states': [{'name': 'reward_zero', 'setup_js': 'return 1;'}]}]
        forced = [{'id': 'revive', 'button': 'Canvas/__revive/btn_watch_ad', 'states': [{'name': 'forced', 'setup_js': "comp('pysTouchEvent').finish(false);"}]}]
        got = node('return [R.adEntriesProblems(%s), R.adEntriesProblems(%s), R.adEntriesProblems([]), R.adEntriesProblems([{id: "a", states: []}])];'
                   % (json.dumps(good), json.dumps(forced)))
        self.assertEqual(got[0], [])
        self.assertIn('must let the hero fail by itself', got[1][0])
        self.assertTrue(got[2] and got[3])


class SuiteFiles(unittest.TestCase):
    """The suites keep the prototype's calibrated fixes in code (not only in this file)."""

    def test_suites_use_the_rules_and_the_shared_geometry(self):
        suites = HERE / 'runtime_regression' / 'suites'
        for name in ('layout_state', 'button_sweep', 'ad_entries', 'trial_link'):
            text = (suites / (name + '.mjs')).read_text(encoding='utf-8')
            self.assertIn("layout_rules.mjs", text, name)
        geom = (HERE / 'runtime_regression' / 'geom.mjs').read_text(encoding='utf-8')
        self.assertIn('getViewportRect', geom)                                   # fix 1: letterboxed 2.4 games
        self.assertIn('// cam-point:begin', geom)                                # 3.x: the Canvas camera
        gates = (HERE / 'runtime_regression' / 'gates.mjs').read_text(encoding='utf-8')
        self.assertIn('MIN_FPS = 20', gates)                                     # fix 3.x-3: throttled tab = invalid run
        self.assertIn('st.inflight', gates)                                      # fix 8: no home while downloading


if __name__ == '__main__':
    unittest.main(verbosity=1)
