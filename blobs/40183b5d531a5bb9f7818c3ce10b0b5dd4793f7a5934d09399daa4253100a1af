#!/usr/bin/env python3
"""v7.8 (总表 E1 补): the dead_shell runtime suite (VIS_DEAD_SHELL) without a browser.

runtime_regression/suites/dead_shell.mjs is run in Node against a fake lib.mjs and a fake Cocos 2.x scene tree, so its
own scan and verdict are what is tested. The fake trees copy the real packages (proof on the real ZIPs: RESULT of W85):
  holly_v1  Canvas/gameLayer/gameView/info/gameBox active, its bg Sprite 'gameIcon' drawn on screen -> refused in game
  holly_v2  gameBox set inactive (the Holly v2 fix)                                                 -> passes
  base      gameBox active but bg inactive (方块冲冲 BUGFIX7: WxGameBox hid it)                        -> passes
A slot is a hit only when the player can see it (active, opacity > 0 down the parents, drawn, > 4 px, on screen); a legacy
game gets warnings instead of a refusal; a missing adapter.play / enter_level fails instead of skipping the game screen.
Run: python3 test_dead_shell.py
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE / 'runtime_regression' / 'suites' / 'dead_shell.mjs'
BRIEF_SLOTS = {'gameBox', 'leftGameBox', 'leftGameBtn', 'gameIcon', 'popBox', 'fullScreenBox', 'leftBox', 'moreGame',
               'moreGames', 'more', 'bannerAdv', 'banner_border', 'item_bg', 'friendRank', 'phb',
               'jxyx', 'hy', 'tj'}

# Fake lib.mjs: the subset dead_shell.mjs uses. Scenes are built per tree; window.__state is 'home' or 'game'.
FAKE_LIB = r'''
const fs = await import('node:fs');
export const C = globalThis.CFG; export const A = C.adapter || {}; export const sleep = async () => {};
globalThis.window = globalThis;
class Node {
  constructor(name, o = {}, kids = []) { this.name = name; this.active = o.active !== false; this.opacity = o.opacity === undefined ? 255 : o.opacity;
    this.comps = {}; if (o.sprite !== undefined) this.comps.Sprite = { enabled: true, spriteFrame: o.sprite === null ? null : { name: o.sprite } };
    if (o.label !== undefined) this.comps.Label = { enabled: true, string: o.label };
    this.box = o.box || [100, 100, 80, 80]; this.children = kids; this.when = o.when; kids.forEach(k => k.parent = this); }
  get activeInHierarchy() { let n = this; while (n) { if (!n.active) return false; if (n.when && n.when !== window.__state) return false; n = n.parent; } return true; }
  getComponent(c) { return this.comps[c.__n] || null; }
  getBoundingBoxToWorld() { const [x, y, width, height] = this.box; return { x, y, width, height }; }
}
const T = JSON.parse(process.env.TREE);
const build = (t) => new Node(t[0], t[1] || {}, (t[2] || []).map(build));
const scene = { name: 'Main', active: true, children: [build(T)] }; scene.children[0].parent = scene;
globalThis.cc = { director: { getScene: () => scene }, Sprite: { __n: 'Sprite' }, Label: { __n: 'Label' },
  view: { getVisibleSize: () => ({ width: 720, height: 1560 }), getVisibleOrigin: () => ({ x: 0, y: 0 }) } };
export const ev = async (page, fn, a) => fn(a);
export const adapterCall = async (page, code) => { try { return new Function(code)(); } catch (e) { return { adapterError: String(e.message || e) }; } };
export async function boot() { window.__state = 'home'; return { ok: true, ms: 5, errors: [] }; }
export async function locate(page, code) { const r = new Function(code)(); return r ? Object.assign({ onCanvas: true }, r) : null; }
export async function touchTap() { if (!process.env.DEAD_PLAY) window.__state = 'game'; }
export async function suite(body) {
  const out = { suite: C.suite, cases: [], warnings: [], evidence: {}, fatal: null };
  out.add = (id, passed, detail) => out.cases.push({ id, passed: passed === true, detail });
  out.warn = (m) => out.warnings.push(String(m));
  const page = { screenshot: async () => {} };
  try { await body({ out, page }); } catch (e) { out.fatal = String(e && e.stack || e); }
  fs.writeFileSync(C.resultFile, JSON.stringify(out));
}
'''

HOME = 'return window.__state === "home"'
PLAY = 'return {x: 10, y: 10}'
ENTER = 'window.__state = "game"; return true'


def tree(game_box, bg, extra_game=(), extra_home=()):
    """Canvas with a home view and a game view; the in-game info/gameBox/bg slot is set by the arguments."""
    return ['Canvas', {}, [
        ['homeView', {'when': 'home'}, [['beginGame', {'sprite': 'btn_play'}]] + list(extra_home)],
        ['gameView', {'when': 'game'}, [['info', {}, [
            ['settings', {'sprite': 'settings'}],
            ['gameBox', game_box, [['bg', dict({'sprite': 'gameIcon', 'box': [44, 375, 118, 133]}, **bg)]]]]]] +
         list(extra_game)]]]


class DeadShell(unittest.TestCase):
    def setUp(self):
        if not shutil.which('node'):
            raise unittest.SkipTest('node is required')
        self.tmp = tempfile.TemporaryDirectory(prefix='dead shell tests ')
        self.root = Path(self.tmp.name)
        (self.root / 'lib.mjs').write_text(FAKE_LIB, encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def run_suite(self, t, adapter=None, policy='new', play_sticks=False):
        import os
        adapter = {'home': HOME, 'play': PLAY, 'enter_level': ENTER} if adapter is None else adapter
        result = self.root / 'result.json'
        cfg = {'suite': 'dead_shell', 'adapter': adapter, 'policy': policy, 'resultFile': str(result),
               'evidenceDir': str(self.root), 'lib': (self.root / 'lib.mjs').as_uri(), 'logFile': None}
        entry = self.root / 'entry.mjs'
        entry.write_text('globalThis.CFG = %s;\nawait import(%s);\n' % (json.dumps(cfg), json.dumps(SUITE.as_uri())))
        env = dict(os.environ, TREE=json.dumps(t))
        if play_sticks:
            env['DEAD_PLAY'] = '1'
        r = subprocess.run(['node', str(entry)], capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        doc = json.loads(result.read_text())
        self.assertIsNone(doc['fatal'], doc['fatal'])
        return doc, {c['id']: c for c in doc['cases']}

    def test_holly_v1_shell_in_game_is_refused_with_path_and_sprite(self):
        doc, cases = self.run_suite(tree({}, {}))
        self.assertTrue(cases['home']['passed'])
        for cid in ('after_play', 'enter_level'):
            self.assertFalse(cases[cid]['passed'], cid)
            hit = cases[cid]['detail']['hits'][0]
            self.assertEqual(hit['path'], 'Canvas/gameView/info/gameBox/bg')
            self.assertEqual((hit['slot'], hit['under'], hit['frame'], hit['box'][2:]),
                             ('gameIcon', 'gameBox', 'gameIcon', [118, 133]))
            self.assertIn('VIS_DEAD_SHELL', cases[cid]['detail']['problems'][0])
            self.assertIn('init(nodes)', cases[cid]['detail']['problems'][0])

    def test_holly_v2_and_base_pass(self):
        for name, t in (('holly_v2', tree({'active': False}, {})), ('base', tree({}, {'active': False}))):
            doc, cases = self.run_suite(t)
            with self.subTest(tree=name):
                self.assertEqual(sorted(cases), ['after_play', 'enter_level', 'home'])
                self.assertTrue(all(c['passed'] for c in cases.values()), cases)
                self.assertEqual(doc['warnings'], [])
                self.assertTrue(any(h['reason'] == 'inactive' for h in cases['after_play']['detail']['hidden']))

    def test_only_visible_slots_count(self):
        """Slot names that are invisible are not hits; a visible slot by sprite frame or by ancestor is."""
        quiet = [['fade', {'opacity': 0}, [['moreGames', {'sprite': 'mg'}]]],   # transparent parent
                 ['hy', {'sprite': 'hy_bg', 'box': [900, 100, 80, 80]}],          # off screen (visible width 720)
                 ['phb', {'sprite': 'p', 'box': [10, 10, 4, 30]}],                # 4 px wide
                 ['jxyx', {'label': '  '}],                                       # empty Label
                 ['tj', {'sprite': None}],                                        # Sprite without a frame
                 ['rankings_panel', {'sprite': 'board'}],                         # not a slot name (exact names only)
                 ['item_bg_2', {'sprite': 'x'}],
                 # Meteor Blaster r9: the playfield is Canvas/gameBox; its bricks are not slots by inheritance
                 ['gameBox', {}, [['block', {'sprite': 'brick'}, [['boxtext', {'label': '12'}]]]]],
                 # Finger Mahjong v56: the coin bar uses an item_bg frame outside any slot
                 ['Coins', {'sprite': 'item_bg'}, [['CoinAmount', {'label': '120'}]]]]
        doc, cases = self.run_suite(tree({'active': False}, {}, extra_game=quiet))
        self.assertTrue(cases['after_play']['passed'], cases['after_play']['detail'])
        reasons = {h['path'].split('/')[-1]: h['reason'] for h in cases['after_play']['detail']['hidden']}
        self.assertEqual(reasons.get('moreGames'), 'opacity 0')
        self.assertEqual(reasons.get('hy'), 'off screen')
        self.assertEqual(reasons.get('phb'), 'not larger than 4 px')
        self.assertEqual(reasons.get('jxyx'), 'draws nothing')
        loud = [['icon', {'sprite': 'moreGame'}], ['friendRank', {'label': 'Friends'}],
                ['jxyx', {}, [['item', {'sprite': 'item_bg'}]]]]                # item_bg inside a slot counts
        doc, cases = self.run_suite(tree({'active': False}, {}, extra_home=loud))
        self.assertFalse(cases['home']['passed'])
        self.assertEqual(sorted((h['path'], h['slot']) for h in cases['home']['detail']['hits']),
                         [('Canvas/homeView/friendRank', 'friendRank'), ('Canvas/homeView/icon', 'moreGame'),
                          ('Canvas/homeView/jxyx/item', 'item_bg')])

    def test_local_match_places_are_not_slots(self):
        """Saul 2026-10-31: 68 小熊拳击's in-match score tags (rank / ranking, drawn on screen) are allowed; friendRank is not."""
        local = [['rank', {'sprite': 'spr_crown1'}, [['lbl_rank', {'label': '1'}]]],
                 ['ranking', {'label': '3rd'}],
                 ['RANK', {'sprite': 'rank_bg'}]]
        doc, cases = self.run_suite(tree({'active': False}, {}, extra_game=local))
        self.assertTrue(all(c['passed'] for c in cases.values()), cases)
        self.assertEqual(cases['after_play']['detail']['hits'], [])
        doc, cases = self.run_suite(tree({'active': False}, {}, extra_game=[['friendRank', {'sprite': 'friend_bg'}]]))
        self.assertFalse(cases['after_play']['passed'])

    def test_legacy_game_warns_instead_of_refusing(self):
        doc, cases = self.run_suite(tree({}, {}), policy='legacy')
        self.assertTrue(all(c['passed'] for c in cases.values()), cases)
        self.assertEqual(cases['after_play']['detail']['level'], 'warning')
        self.assertEqual(len(doc['warnings']), 2)
        self.assertTrue(all('legacy game: warning' in w and 'gameBox/bg' in w for w in doc['warnings']))

    def test_game_screen_is_never_skipped(self):
        doc, cases = self.run_suite(tree({}, {}), adapter={'home': HOME})
        self.assertFalse(cases['in_game']['passed'])
        self.assertIn('adapter.play is missing', cases['in_game']['detail']['problems'][0])
        # PLAY that does not leave home: the in-game screen was not scanned -> fail, not pass
        doc, cases = self.run_suite(tree({'active': False}, {}), adapter={'home': HOME, 'play': PLAY}, play_sticks=True)
        self.assertFalse(cases['after_play']['passed'])
        self.assertIn('did not leave the home page', cases['after_play']['detail']['problems'][0])
        # enter_level alone (Fox Den Dash's adapter has no play) still scans the game
        doc, cases = self.run_suite(tree({}, {}), adapter={'home': HOME, 'enter_level': ENTER})
        self.assertEqual(sorted(cases), ['enter_level', 'home'])
        self.assertFalse(cases['enter_level']['passed'])

    def test_slot_list_is_the_e1_list(self):
        text = SUITE.read_text(encoding='utf-8')
        strong = re.search(r"^const SLOT = '\^\(([^)]*)\)\$';", text, re.M)
        weak = re.search(r"^const WEAK = '\^\(([^)]*)\)\$';", text, re.M)
        self.assertIsNotNone(strong)
        self.assertIsNotNone(weak)
        self.assertEqual(set(strong.group(1).split('|')) | set(weak.group(1).split('|')), BRIEF_SLOTS)
        self.assertEqual(weak.group(1), 'item_bg')


if __name__ == '__main__':
    unittest.main(verbosity=1)
