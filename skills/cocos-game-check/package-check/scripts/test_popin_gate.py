#!/usr/bin/env python3
"""v7.8 (总表 P2 补): the popin runtime suite (obstacles may not appear, vanish or jump on screen).

Watch: runtime_regression/popin_watch.mjs runs in Node on a fake Cocos 2.4 engine, frame by frame: a v2.1-style recycle
into a wide screen, a revive that moves a visible pillar, a pop-in, an on-screen destroy / deactivate must be caught;
scrolling off both edges, a 0.3 s fade, the player's own children, ignored groups, an invisible trigger, an opaque
cover and a hitch frame must not. Wiring: the runner's precheck (needs_new / na_field / uncovered) on the fake browser
of test_runtime_regression.py. The browser half is proven on real packages (briefs/out/W89/RESULT.md: BreezyBalloon
v2.1 refused on 390x844, 375x667, 768x1024, 1115x791; v2.2 and v2.1 with platform-kit CourseLane pass).
Run: python3 -B test_popin_gate.py
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from unittest.mock import patch

import runtime_regression as rr
from test_runtime_regression import Base, SIDECAR

HERE = Path(__file__).resolve().parent
WATCH = HERE / 'runtime_regression' / 'popin_watch.mjs'
SUITE = HERE / 'runtime_regression' / 'suites' / 'popin.mjs'

FAKE_ENGINE = r'''
const { WATCH_JS } = await import(%(watch)s);
let T = 0;
Object.defineProperty(globalThis, 'performance', { value: { now: () => T }, configurable: true, writable: true });
class RC { constructor() { this.enabled = true; } }
class Sprite extends RC { constructor(f) { super(); this.spriteFrame = f === undefined ? 'frame' : f; } }
class Label extends RC { constructor(s) { super(); this.string = s; } }
class PhysicsCollider {}
class Collider {}
class Node {
  constructor(name, o = {}) { Object.assign(this, { name, x: 0, y: 0, w: 160, h: 400, opacity: 255, scaleX: 1, scaleY: 1, active: true, group: 'default', comps: [], children: [], parent: null }, o); }
  get activeInHierarchy() { for (let n = this; n; n = n.parent) if (!n.active) return false; return true; }
  getComponent(K) { return this.comps.find((c) => c instanceof K) || null; }
  walk(fn) { fn(this); this.children.forEach((c) => c.walk(fn)); }
  add(c) { c.parent = this; this.children.push(c); return c; }
  remove() { const p = this.parent; if (p) p.children = p.children.filter((c) => c !== this); this.parent = null; }
  wx() { let x = 0; for (let n = this; n; n = n.parent) x += n.x; return x; }
  wy() { let y = 0; for (let n = this; n; n = n.parent) y += n.y; return y; }
  getBoundingBoxToWorld() { return { x: this.wx() - this.w / 2, y: this.wy() - this.h / 2, width: this.w, height: this.h }; }
}
function world(W, H) {
  const handlers = [];
  const scene = new Node('Scene', { w: 0, h: 0 });
  const canvas = scene.add(new Node('Main', { w: 0, h: 0 }));
  globalThis.window = globalThis;
  globalThis.cc = { RenderComponent: RC, Sprite, Label, PhysicsCollider, Collider, Graphics: class extends RC {},
    v2: (x, y) => ({ x, y }), visibleRect: { width: W, height: H },
    view: { getVisibleSize: () => ({ width: W, height: H }), getVisibleOrigin: () => ({ x: 0, y: 0 }) },
    director: { getScene: () => scene, on: (e, fn) => handlers.push(fn), off: () => {} }, Director: { EVENT_AFTER_DRAW: 'draw' } };
  const frame = (dt = 16.7) => { T += dt; handlers.forEach((f) => f()); };
  return { scene, canvas, frame };
}
// obstacle: collider + sprite on the node (draws = true); opts.noSprite: an invisible trigger
function pillar(parent, name, x, o = {}) {
  const n = parent.add(new Node(name, Object.assign({ x, y: 600 }, o)));
  n.comps.push(new PhysicsCollider());
  if (!o.noSprite) n.comps.push(new Sprite());
  return n;
}
const run = (W, H, opts, body) => {
  const w = world(W, H);
  const setup = body(w);
  (0, eval)(WATCH_JS)(opts || {});
  for (const step of setup) step();
  const P = window.__popin;
  return { counts: P.counts, watched: P.watched, covered: P.covered, kinds: P.ev.map((e) => e.phase + ':' + e.kind + ':' + e.node) };
};
const repeat = (n, fn) => Array.from({ length: n }, (_, i) => () => fn(i));
const out = {};
%(body)s
console.log(JSON.stringify(out));
'''


def node_run(body):
    exe = shutil.which('node')
    if not exe:
        raise unittest.SkipTest('node is required')
    js = FAKE_ENGINE % {'watch': json.dumps(WATCH.as_uri()), 'body': body}
    r = subprocess.run([exe, '--input-type=module', '-e', js], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-2000:])
    return json.loads(r.stdout)


class Watch(unittest.TestCase):
    def test_bad_courses_are_caught(self):
        got = node_run(r'''
// BreezyBalloon v2.1 on 1115x791 (visible 1880 wide): a pillar leaving the left edge is recycled to x 816 (design width)
out.recycle_into_wide = run(1880, 1334, {}, ({ canvas, frame }) => { const p = pillar(canvas, 'top', -40);
  return [...repeat(10, () => { p.x -= 5; frame(); }), () => { p.x = 816; frame(); }, ...repeat(5, () => { p.x -= 5; frame(); })]; });
// revive moves a visible pillar 796 to the right in one frame (v2.1 resumeSameDive, 390x844)
out.revive_move = run(750, 1623, {}, ({ canvas, frame }) => { const p = pillar(canvas, 'bottom', 273);
  return [...repeat(5, frame), () => { window.__popin.phase = 'revive'; p.x += 796; frame(); }, frame]; });
// a new obstacle created on screen
out.pop_in = run(750, 1334, {}, ({ canvas, frame }) => [...repeat(4, frame), () => { pillar(canvas, 'rock', 400); frame(); }, frame]);
// destroyed / deactivated on screen
out.destroyed = run(750, 1334, {}, ({ canvas, frame }) => { const p = pillar(canvas, 'rock', 300); return [...repeat(4, frame), () => { p.remove(); frame(); }]; });
out.inactive = run(750, 1334, {}, ({ canvas, frame }) => { const p = pillar(canvas, 'rock', 300); return [...repeat(4, frame), () => { p.active = false; frame(); }]; });
// a pillar teleporting under a half-transparent dim (opacity 150) still counts
out.dim_cover = run(750, 1334, {}, ({ canvas, frame }) => { const p = pillar(canvas, 'top', 300);
  const dim = canvas.add(new Node('dim', { x: 375, y: 667, w: 750, h: 1334, opacity: 150 })); dim.comps.push(new Sprite());
  return [...repeat(4, frame), () => { p.x = 900; frame(); }]; });
''')
        self.assertEqual(got['recycle_into_wide']['counts'], {'flight:jumped_on_screen': 1})
        self.assertEqual(got['revive_move']['kinds'], ['revive:jumped_on_screen:bottom'])
        self.assertEqual(got['pop_in']['kinds'], ['flight:appeared_on_screen:rock'])
        self.assertEqual(got['destroyed']['kinds'], ['flight:vanished_on_screen:rock'])
        self.assertEqual(got['inactive']['kinds'], ['flight:vanished_on_screen:rock'])
        self.assertEqual(got['dim_cover']['counts'], {'flight:jumped_on_screen': 1})

    def test_good_courses_pass(self):
        got = node_run(r'''
// CourseLane: spawn beyond the real right edge, scroll across, recycle only after fully leaving the left edge
out.scroll_recycle = run(1880, 1334, {}, ({ canvas, frame }) => { const p = pillar(canvas, 'top', 1880 + 80 + 100);
  return repeat(460, () => { p.x -= 5; if (p.x + 80 < 0) p.x = 1880 + 80 + 100; frame(); }); });
// revive: the visible pillar in front of the player fades out over 0.35 s (21 frames), then moves off screen
out.fade_then_move = run(750, 1623, {}, ({ canvas, frame }) => { const p = pillar(canvas, 'top', 273);
  return [...repeat(3, frame), () => { window.__popin.phase = 'revive'; }, ...repeat(21, (i) => { p.opacity = Math.round(255 * (1 - (i + 1) / 21)); frame(); }),
    () => { p.x = 1000; p.opacity = 255; frame(); }, frame]; });
// fade in on screen
out.fade_in = run(750, 1334, {}, ({ canvas, frame }) => { let p; return [...repeat(3, frame), () => { p = pillar(canvas, 'rock', 400, { opacity: 0 }); frame(); },
  ...repeat(20, (i) => { p.opacity = Math.round(255 * (i + 1) / 20); frame(); })]; });
// the player's own collider children, ignored groups, an invisible trigger: not watched
out.left_out = run(750, 1334, { player: 'submarineItem', ignore_groups: ['bottom'] }, ({ canvas, frame }) => {
  const pl = canvas.add(new Node('submarineItem', { x: 200 })); const body = pillar(pl, 'hull', 0);
  const ground = pillar(canvas, 'ground', 300, { group: 'bottom' }); const trig = pillar(canvas, 'trigger', 300, { noSprite: true });
  return [...repeat(3, frame), () => { body.x = 500; ground.x = 900; trig.x = 900; frame(); }, frame]; });
// under a full-screen opaque cover drawn after the obstacles (revive popup), moving pillars is allowed
out.opaque_cover = run(750, 1334, {}, ({ canvas, frame }) => { const p = pillar(canvas, 'top', 300);
  const cover = canvas.add(new Node('cover', { x: 375, y: 667, w: 760, h: 1340 })); cover.comps.push(new Sprite());
  return [...repeat(3, frame), () => { p.x = 900; frame(); }, frame]; });
// a 100 ms hitch: a pillar moving 200 in that frame is not a jump (40 x 100/16.7 = 240), a teleport of 800 still is
out.hitch = run(750, 1334, {}, ({ canvas, frame }) => { const p = pillar(canvas, 'top', 600); const q = pillar(canvas, 'bottom', 100);
  return [...repeat(3, () => frame()), () => { p.x -= 200; frame(100); }, () => { q.x += 600; frame(100); }]; });
''')
        for name in ('scroll_recycle', 'fade_then_move', 'fade_in', 'left_out', 'opaque_cover'):
            self.assertEqual(got[name]['counts'], {}, (name, got[name]))
        self.assertEqual(got['scroll_recycle']['watched'], 1)
        self.assertEqual(got['left_out']['watched'], 0)              # hull (player), ground (group), trigger (draws nothing)
        self.assertEqual(got['opaque_cover']['covered'], 1)
        self.assertEqual(got['hitch']['kinds'], ['flight:jumped_on_screen:bottom'])


class PopinWiring(Base):
    """The runner: popin is required for every TikTok package; a new game needs adapter.popin, a legacy game warns;
    {"n/a": reason} and Cocos 3.x are decided without the browser."""

    def pp(self):
        self.sidecar('pp', {**SIDECAR, 'name': 'pp', 'needs': [], 'needs_new': ['popin'], 'na_field': 'popin',
                            'uncovered': {'3.x': 'not calibrated on 3.x'}, 'fields': ['fake_mode', 'popin']})
        (self.suites / 'fake.json').unlink()
        (self.suites / 'fake.mjs').unlink()

    def test_real_sidecar_and_required(self):
        catalog = rr.load_suites()
        meta = catalog['popin']
        self.assertEqual((meta['applies'], meta['needs'], meta['needs_new'], meta['na_field'], meta['engines']),
                         (['tiktok'], [], ['popin'], 'popin', ['2.x', '3.x']))
        self.assertIn('3.x', meta['uncovered'])
        for files in ({'game.js': b'x'}, {'game.js': b'x', 'src/system.bundle.js': b''}):
            self.assertIn('popin', rr.required_suites(files, {}, catalog))
        self.assertIn('popin', rr.adapter_keys(catalog))
        import check_package
        seen = {}
        with patch.object(rr, 'run', side_effect=lambda folder, adapter, names, **k: seen.update(names=names) or {}):
            check_package.runtime_gate({'game.js': b'x'}, self.package, self.adapter({'home': 'return true'}), policy='new')
        self.assertIn('popin', seen['names'])                         # the writers run it (check_package.runtime_gate)

    def test_na_passes_without_the_browser(self):
        self.pp()
        summary = self.run_fake({'home': 'return true', 'popin': {'n/a': 'no scrolling obstacles (match-3 board)'}})
        row = summary['suites'][0]
        self.assertTrue(summary['passed'])
        self.assertEqual((row['cases'][0]['id'], row['browser']), ('n_a', False))
        self.assertFalse((self.root / 'work' / 'pp' / 'entry.mjs').exists())

    def test_missing_or_bad_popin_refuses_new_warns_legacy(self):
        self.pp()
        with self.assertRaisesRegex(rr.RuntimeRefused, 'pp/adapter: adapter has no "popin"'):
            self.run_fake({'home': 'return true'}, policy='new')
        summary = self.run_fake({'home': 'return true'}, policy='legacy')
        self.assertTrue(summary['passed'])
        self.assertTrue(any('legacy game: warning' in w for w in summary['warnings']), summary['warnings'])
        for bad, why in (({'player': 'hero'}, 'popin.invincible_js missing'), ({'n/a': ' '}, 'needs the reason'),
                         ({'n/a': 'x', 'player': 'p'}, 'no other keys')):
            with self.assertRaisesRegex(rr.RuntimeRefused, re.escape(why)):
                self.run_fake({'home': 'return true', 'popin': bad}, policy='new')

    def test_uncovered_engine_warns(self):
        self.pp()
        summary = self.run_fake({'home': 'return true', 'engine': '3.x'}, policy='new')
        self.assertTrue(summary['passed'])
        self.assertEqual(summary['suites'][0]['cases'][0]['id'], 'uncovered')
        self.assertTrue(any('未覆盖' in w for w in summary['warnings']))

    def test_complete_popin_runs_the_suite(self):
        self.pp()
        popin = {'player': 'hero', 'invincible_js': 'return true', 'revive_js': 'return true', 'game_node': 'Level'}
        summary = self.run_fake({'home': 'return true', 'popin': popin})
        self.assertTrue(summary['passed'])
        self.assertIn('"game_node": "Level"', (self.root / 'work' / 'pp' / 'entry.mjs').read_text())

    def test_popin_problems(self):
        ok = {'player': 'hero', 'invincible_js': 'return true', 'revive_js': 'r()', 'game_node': 'Level'}
        self.assertEqual(rr.popin_problems(ok), [])
        self.assertEqual(rr.popin_problems({'n/a': 'puzzle board, nothing scrolls'}), [])
        self.assertEqual(rr.popin_problems({**ok, 'start': [{'tap': 'Canvas/play'}], 'fly_s': 20, 'first_touch': False,
                                            'ignore': '^Main/ground', 'ignore_groups': ['bottom']}), [])
        self.assertIn("popin has unknown key 'speed'", rr.popin_problems({**ok, 'speed': 3}))
        self.assertIn('popin.fly_s must be 5..60 seconds', rr.popin_problems({**ok, 'fly_s': 2}))
        self.assertIn('popin.first_touch has the wrong type', rr.popin_problems({**ok, 'first_touch': 'no'}))
        self.assertTrue(any('not a regular expression' in p for p in rr.popin_problems({**ok, 'ignore': '('})))
        self.assertEqual(rr.popin_problems([]), ['popin must be an object'])

    def test_suite_has_no_game_names(self):
        """The prototype's 潜艇冲冲 names (submarineItem, LevelView, HomeView, SubmarineItem.safeUntil) are adapter fields."""
        for path in (SUITE, WATCH):
            code = '\n'.join(line for line in path.read_text(encoding='utf-8').splitlines() if not line.lstrip().startswith('//'))
            for name in ('submarineItem', 'LevelView', 'HomeView', 'safeUntil', 'resumeSameDive', "'bottom'"):
                self.assertNotIn(name, code, (path.name, name))
        text = SUITE.read_text(encoding='utf-8')
        self.assertIn('[[390, 844], [375, 667], [768, 1024], [1115, 791]]', text)
        self.assertIn('+P.fly_s || 18', text)
        self.assertIn('40 * Math.max(1, dt / 16.7)', WATCH.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main(verbosity=1)
