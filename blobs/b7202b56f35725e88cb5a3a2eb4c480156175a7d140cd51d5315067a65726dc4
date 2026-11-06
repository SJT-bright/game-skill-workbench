#!/usr/bin/env python3
"""R4P3 (R4O4 没做完的): the last runtime_regression page probes read the engine through engine_adapter.mjs adapt()
like the rest (R4O4): suites/trial_link.mjs GW (game window, top or iframe), popin_watch.mjs WATCH_JS,
frame_rate_compare.mjs SAMPLER_JS, suites/layout_state.mjs hookScenes and the director pause / resume.

No browser: Node runs the probe text against three fake windows (2.4 shape with a global cc, 3.x shape with cc only in a
module behind System.import('cc'), engine not up yet: cc without a scene). The suites need a live page, so GW, texts,
hookScenes and director are cut out of the suite text and evaluated in Node with the real engine_adapter.mjs.

- trial_link GW / texts: 2.4 top window found; 3.x game in an iframe with cc only in its module found on the second call
  (System.import started in that window); engine not up -> null and window.__gwWhy '引擎还没起来：…';
- popin WATCH_JS: 3.x shape -> {notCovered} (no throw), not up -> {notReady: '引擎还没起来：…'} (no throw), 2.4 runs;
- frame_rate SAMPLER_JS: 3.x module cc -> frame counter read (f0 100), not up -> W.err '引擎还没起来：…', 2.4 track point;
- layout_state: hookScenes hooks the scene events on the 3.x shape; director('pause') -> {notReady} when not up, no throw.
Old code (base tree): R4P3_TREE=<base tree> python3 -B test_r4p3_probe_adapter.py -> fails.
Run: python3 -B test_r4p3_probe_adapter.py
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TREE = Path(os.environ['R4P3_TREE']).resolve() if os.environ.get('R4P3_TREE') else HERE.parents[2]
RR = TREE / 'cocos-game-check' / 'package-check' / 'scripts' / 'runtime_regression'
NODE = shutil.which('node')

HARNESS = r"""
import fs from 'node:fs';
const shape = process.argv[2], what = process.argv[3], rr = process.argv[4];
const EA = await import(rr + '/engine_adapter.mjs').catch(() => ({ INSTALL: '', inPage: (fn, a) => '(' + fn + ')(' + JSON.stringify(a) + ')' }));
class Vec3 { constructor(x, y, z) { this.x = x || 0; this.y = y || 0; this.z = z || 0; } }
const canvas = { width: 780, height: 1688, getBoundingClientRect: () => ({ left: 0, top: 0, width: 390, height: 844 }) };
const handlers = [];
const node = (name, extra) => Object.assign({ name, activeInHierarchy: true, children: [], parent: null, comps: {}, opacity: 255, scaleX: 1, scaleY: 1,
  getComponent(K) { return this.comps[K && (K.__n || K)] || null; },
  getBoundingBoxToWorld() { return { x: 100, y: 300, width: 190, height: 80 }; },
  walk(fn) { fn(this); this.children.forEach((c) => c.walk(fn)); } }, extra || {});
const director = (s) => ({ getScene: () => s, getTotalFrames: () => 100, on: (e, fn) => handlers.push(e), off() {}, pause() { this.paused = true; }, resume() {} });
const Director = { EVENT_AFTER_DRAW: 'draw', EVENT_BEFORE_SCENE_LOADING: 'loading', EVENT_AFTER_SCENE_LAUNCH: 'launch' };
function scene24() {
  const n = node('Play', { convertToWorldSpaceAR: (p) => ({ x: p.x + 195, y: p.y + 422 }) });
  n.comps.Label = { string: 'PLAY' };
  const s = node('Scene', { children: [n] }); n.parent = s;
  const cc = { Label: { __n: 'Label' }, v2: (x, y) => ({ x, y }), visibleRect: { width: 390, height: 844 }, game: { canvas },
    view: { getVisibleSize: () => ({ width: 390, height: 844 }), getVisibleOrigin: () => ({ x: 0, y: 0 }) },
    find: (p) => null, director: director(s), Director, ENGINE_VERSION: '2.4.15' };
  return { cc, track: n };
}
function scene3x() {
  const Label = { __n: 'Label' }, UITransform = { __n: 'UITransform' };
  const n = node('Play', { worldPosition: new Vec3(195, 422, 0) });
  n.comps.Label = { string: 'PLAY' };
  n.comps.UITransform = { contentSize: { width: 200, height: 80 }, anchorPoint: { x: 0.5, y: 0.5 }, convertToWorldSpaceAR: (v) => new Vec3(v.x + 195, v.y + 422, 0) };
  const cv = node('Canvas', { children: [n] }); n.parent = cv;
  const s = node('Scene', { children: [cv] }); cv.parent = s;
  const cc = { Label, UITransform, Vec3, game: { canvas }, find: () => null, ENGINE_VERSION: '3.8.8', director: director(s), Director };
  return { cc, track: n };
}
const notUp = () => ({ cc: { director: director(null), Director, game: { canvas } }, track: null });
const made = shape === '24' ? scene24() : shape === '3x' ? scene3x() : notUp();
// 2.4: global cc in the top window. 3.x: the game runs in an iframe, cc only in its module (System.import('cc')).
// not up: global cc without a scene.
const top = { __hostState: () => ({ t: 1 }) };
let frame = null;
if (shape === '3x') {
  frame = { System: { import: async () => made.cc }, __hostState: () => ({ t: 1 }), document: {} };
  if (what === 'popin' || what === 'sampler' || what === 'hook' || what === 'director') Object.assign(top, frame);   // these run in the game window
} else top.cc = made.cc;
globalThis.window = top;
globalThis.document = { querySelectorAll: (q) => (q === 'iframe' && frame && what !== 'popin' && what !== 'sampler' ? [{ contentWindow: frame }] : []), querySelector: () => canvas };
for (const k of Object.keys(top)) if (k === 'cc' || k === 'System') globalThis[k] = top[k];
globalThis.__track = made.track;
const tick = () => new Promise((r) => setTimeout(r, 20));
const page = { evaluate: async (fn, a) => (typeof fn === 'function' ? fn(a) : (0, eval)(fn)) };
const cut = (file, re) => { const m = fs.readFileSync(new URL(rr + '/' + file), 'utf8').match(re); return m ? m[0] : null; };
const out = {};
try {
  if (what === 'gw' || what === 'texts') {
    const src = cut('suites/trial_link.mjs', /const GW = `[\s\S]*?\}\)\(\)`;/);
    const GW = (0, eval)('(function(EA){ ' + src.replace('const GW =', 'return') + ' })')(EA);
    if (what === 'gw') {
      let g = (0, eval)(GW); await tick(); if (!g) g = (0, eval)(GW);
      out.value = g ? { found: true, scene: g.E ? g.E.scene && g.E.scene.name : null, hasCc: !!g.cc } : { found: false, why: window.__gwWhy || null };
    } else {
      const tsrc = cut('suites/trial_link.mjs', /const texts = \(page\) => page\.evaluate\(`[\s\S]*?`\);/);
      const texts = (0, eval)('(function(GW, page){ ' + tsrc.replace('const texts =', 'return') + ' })')(GW, page);
      let v = await texts(page); await tick(); if (!v) v = await texts(page);
      out.value = v;
    }
  } else if (what === 'popin') {
    const { WATCH_JS } = await import(rr + '/popin_watch.mjs');
    if (shape === '3x') { (0, eval)('(function(){' + EA.INSTALL + '})()'); await tick(); }   // the page has polled once before
    out.value = (0, eval)(WATCH_JS)({ player: '' });
    if (out.value && out.value.V === undefined) delete out.value.V;
  } else if (what === 'sampler') {
    const F = await import(rr + '/frame_rate_compare.mjs');
    if (shape === '3x') { (0, eval)('(function(){' + EA.INSTALL + '})()'); await tick(); }   // the page has polled once before
    const ok = (0, eval)(F.SAMPLER_JS)({ track: 'return globalThis.__track;', drive_js: 'return 1;', steps: [], run_s: 0.05 });
    await new Promise((r) => setTimeout(r, 150));
    const W = window.__fps;
    out.value = { ok, err: W.err, f0: W.f0, first: (W.s.find((r) => r[1] != null) || null) };
  } else if (what === 'hook' || what === 'director') {
    const hsrc = cut('suites/layout_state.mjs', /const hookScenes = \(page\) => [\s\S]*?\.catch\(\(\) => false\);/);
    const dsrc = cut('suites/layout_state.mjs', /const director = \(page, m\) => [\s\S]*?\}, m\)\);/);
    if (what === 'hook') {
      const hookScenes = (0, eval)('(function(EA){ ' + hsrc.replace('const hookScenes =', 'return') + ' })')(EA);
      let v = await hookScenes(page); await tick(); if (v !== true) v = await hookScenes(page);
      out.value = { hooked: v, events: handlers.slice() };
    } else {
      if (!dsrc) throw Error('layout_state.mjs has no director() going through the engine adapter');
      const dir = (0, eval)('(function(EA){ ' + dsrc.replace('const director =', 'return') + ' })')(EA);
      if (shape === '3x') { (0, eval)('(function(){' + EA.INSTALL + '})()'); await tick(); }
      out.value = await dir(page, 'pause');
    }
  }
} catch (e) { out.threw = String(e && e.message || e); }
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(NODE, 'node not found')
class ProbeAdapterR4P3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='r4p3_'))
        (cls.tmp / 'h.mjs').write_text(HARNESS, encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_probe(self, shape, what):
        r = subprocess.run([NODE, str(self.tmp / 'h.mjs'), shape, what, RR.as_uri()], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_trial_link_gw(self):
        r = self.run_probe('24', 'gw')
        self.assertTrue(r.get('value', {}).get('found'), '2.4 top window: %s' % r)
        r = self.run_probe('3x', 'gw')
        self.assertNotIn('threw', r, r)
        self.assertEqual(r['value'], {'found': True, 'scene': 'Scene', 'hasCc': True},
                         '3.x iframe with cc only in its module must be found (System.import in that window): %s' % r)
        r = self.run_probe('none', 'gw')
        self.assertNotIn('threw', r, r)
        self.assertFalse(r['value']['found'], r)
        self.assertIn('引擎还没起来', r['value'].get('why') or '', 'GW must say why the game window was not found: %s' % r)

    def test_trial_link_texts_3x(self):
        r = self.run_probe('3x', 'texts')
        self.assertNotIn('threw', r, r)
        self.assertIn('Play=PLAY', r.get('value') or '', r)
        r = self.run_probe('24', 'texts')
        self.assertIn('Play=PLAY', r.get('value') or '', r)

    def test_popin_watch(self):
        r = self.run_probe('3x', 'popin')
        self.assertNotIn('threw', r, 'WATCH_JS threw on a 3.x page with cc only in the module: %s' % r)
        self.assertIn('notCovered', r['value'], r)
        r = self.run_probe('none', 'popin')
        self.assertNotIn('threw', r, 'WATCH_JS threw while the engine was not up: %s' % r)
        self.assertIn('引擎还没起来', r['value'].get('notReady') or '', r)
        r = self.run_probe('24', 'popin')
        self.assertNotIn('threw', r, r)
        self.assertNotIn('notReady', r['value'], r)

    def test_frame_rate_sampler(self):
        r = self.run_probe('3x', 'sampler')
        self.assertNotIn('threw', r, r)
        self.assertIs(r['value']['ok'], True, r)
        self.assertEqual(r['value']['f0'], 100, '3.x module cc: the frame counter must be read through the adapter: %s' % r)
        self.assertEqual(r['value']['first'][1:3], [195, 422], r)
        r = self.run_probe('none', 'sampler')
        self.assertIn('引擎还没起来', r['value']['err'] or '', 'sampler must say the engine is not up: %s' % r)
        r = self.run_probe('24', 'sampler')
        self.assertIsNone(r['value']['err'], r)
        self.assertEqual(r['value']['first'][1:4], [195, 422, 0], r)

    def test_layout_state_hooks_and_director(self):
        r = self.run_probe('3x', 'hook')
        self.assertNotIn('threw', r, r)
        self.assertIs(r['value']['hooked'], True, '3.x module cc: scene events must be hooked: %s' % r)
        self.assertEqual(r['value']['events'], ['loading', 'launch'], r)
        r = self.run_probe('none', 'director')
        self.assertNotIn('threw', r, r)
        self.assertIn('引擎还没起来', (r.get('value') or {}).get('notReady') or '', r)
        r = self.run_probe('3x', 'director')
        self.assertIs(r.get('value'), True, r)


if __name__ == '__main__':
    unittest.main()
