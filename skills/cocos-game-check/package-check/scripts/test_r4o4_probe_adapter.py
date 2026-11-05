#!/usr/bin/env python3
"""R4O4 (R4N3 没做完的, 补查2 第 1 组 1b): the runtime_regression and ad_regression page probes read the engine through
the same adapter as ui_dump.js (remake-core/scripts/engine_adapter.js adapt()).

火箭三消 / 弹球传奇: the probes said "cc.director not found" (a 3.x page keeps cc in a module, System.import('cc'));
奔跑吧巨人 3.x: node.convertToWorldSpaceAR (a 2.x call on a 3.x node). No browser: Node runs the probes against three
fake windows (2.4 shape, 3.x shape with cc only in a module, engine not up yet) through a fake page whose evaluate
runs the probe text in Node.

- the ENGINE-ADAPTER blocks of runtime_regression/engine_adapter.mjs and ad_regression/cases.mjs are the text of
  remake-core/scripts/engine_adapter.js (leading spaces ignored, the rule of test_r4n3_engine_adapter.js);
- lib.mjs findLabels finds a 2.4 label and a 3.x label (UITransform, no node.convertToWorldSpaceAR, cc only in
  window.__tiktokKitCc); engine not up -> [] after asking again (3 page calls), no throw;
- lib.mjs waitFor with the default READY: true on the 3.x shape, {ok:false, notReady:'引擎还没起来：…'} when not up;
- geom.mjs GEOM_JS: no throw when the engine is not up (ENGINE_READY false, walkScene finds nothing), V3 on 3.x;
- cases.mjs: the default ready and findExit go through window.__ccAdapt, findExit has no node.convertToWorldSpaceAR.
Old code (base tree): R4O4_TREE=<base tree> python3 -B test_r4o4_probe_adapter.py -> fails.
Run: python3 -B test_r4o4_probe_adapter.py
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TREE = Path(os.environ['R4O4_TREE']).resolve() if os.environ.get('R4O4_TREE') else HERE.parents[2]
SCRIPTS = TREE / 'cocos-game-check' / 'package-check' / 'scripts'
RR = SCRIPTS / 'runtime_regression'
ADAPTER_JS = TREE / 'remake-core' / 'scripts' / 'engine_adapter.js'
NODE = shutil.which('node')
BLOCK = re.compile(r'// ENGINE-ADAPTER-BEGIN\n([\s\S]*?)// ENGINE-ADAPTER-END')


def block(path):
    if not path.is_file():
        return None
    m = BLOCK.search(path.read_text(encoding='utf-8'))
    return m and re.sub(r'(?m)^ +', '', m.group(1))


# Fake windows and a fake page. page.evaluate(fn|string, arg) runs the probe in Node with globalThis.window = the fake.
HARNESS = r"""
const shape = process.argv[2], what = process.argv[3], rr = process.argv[4];
class Vec3 { constructor(x, y, z) { this.x = x || 0; this.y = y || 0; this.z = z || 0; } }
const canvas = { width: 780, height: 1688, getBoundingClientRect: () => ({ left: 0, top: 0, width: 390, height: 844 }) };
const node = (name, extra) => Object.assign({ name, activeInHierarchy: true, children: [], parent: null, comps: {},
  getComponent(K) { return this.comps[K && (K.__n || K)] || null; },
  walk(fn) { fn(this); this.children.forEach((c) => c.walk(fn)); } }, extra || {});
function scene24() {
  const lab = { string: 'PLAY' };
  const n = node('Play', { convertToWorldSpaceAR: (p) => ({ x: p.x + 195, y: p.y + 422 }) });
  n.comps.Label = lab;
  const s = node('Scene', { children: [n] }); n.parent = s;
  const Label = { __n: 'Label' };
  const cc = { Label, v2: (x, y) => ({ x, y }), visibleRect: { width: 390, height: 844 }, game: { canvas },
    Camera: { __n: 'Camera', findCamera: () => ({ getWorldToScreenPoint: (w) => ({ x: w.x, y: w.y }) }) },
    director: { getScene: () => s, getTotalFrames: () => 100 }, ENGINE_VERSION: '2.4.15' };
  return { cc };
}
function scene3x() {
  const Label = { __n: 'Label' }, UITransform = { __n: 'UITransform' }, Canvas = { __n: 'Canvas' }, Camera = { __n: 'Camera' };
  const cam = { worldToScreen: (w, p) => { p.x = w.x * 2; p.y = w.y * 2; return p; } };
  const n = node('Play');   // a 3.x node: no convertToWorldSpaceAR on the node itself
  n.comps.Label = { string: 'PLAY' };
  n.comps.UITransform = { contentSize: { width: 200, height: 80 }, anchorPoint: { x: 0.5, y: 0.5 },
    convertToWorldSpaceAR: (v) => new Vec3(v.x + 195, v.y + 422, 0) };
  const cv = node('Canvas', { children: [n] }); cv.comps.Canvas = { cameraComponent: cam }; n.parent = cv;
  const s = node('Scene', { children: [cv] }); cv.parent = s;
  const cc = { Label, UITransform, Canvas, Camera, Vec3, game: { canvas }, ENGINE_VERSION: '3.8.8',
    director: { getScene: () => s, getTotalFrames: () => 100 } };
  // 火箭三消 / 弹球传奇: cc only in the module (System.import('cc')); the kit keeps it in window.__tiktokKitCc
  return { __tiktokKitCc: cc, System: { import: async () => cc } };
}
function notUp() { return { cc: { director: { getScene: () => null } } }; }
globalThis.window = shape === '24' ? scene24() : shape === '3x' ? scene3x() : notUp();
if (window.cc) globalThis.cc = window.cc;   // in a page the global cc is window.cc
globalThis.Element = { prototype: { getBoundingClientRect() { return this.getBoundingClientRect(); } } };
let calls = 0;
const page = { evaluate: async (fn, a) => { calls++; return typeof fn === 'function' ? fn(a) : (0, eval)(fn); } };
globalThis.CFG = {};
const out = { calls: 0 };
try {
  if (what === 'labels') {
    const L = await import(rr + '/lib.mjs');
    out.value = await L.findLabels(page, '^PLAY$');
  } else if (what === 'ready') {
    const L = await import(rr + '/lib.mjs');
    const code = L.READY || "return !!(window.cc && cc.director && cc.director.getScene && cc.director.getScene());";
    globalThis.cc = window.cc;   // the old READY reads the global cc, as in the page
    out.value = await L.waitFor(page, code, 1200, 200);
  } else if (what === 'geom') {
    const G = await import(rr + '/geom.mjs');
    globalThis.cc = window.cc;
    out.value = (0, eval)('(function(){' + G.GEOM_JS + '; var k = 0; walkScene(function(){ k++; }); return { ready: typeof ENGINE_READY === "undefined" ? null : ENGINE_READY, v3: V3, walked: k, reason: typeof ENGINE_REASON === "undefined" ? null : ENGINE_REASON }; })()');
  }
} catch (e) { out.threw = String(e && e.message || e); }
out.calls = calls;
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(NODE, 'node not found')
class ProbeAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='r4o4_'))
        (cls.tmp / 'h.mjs').write_text(HARNESS, encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_probe(self, shape, what):
        r = subprocess.run([NODE, str(self.tmp / 'h.mjs'), shape, what, RR.as_uri()], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_blocks_are_engine_adapter_js(self):
        want = block(ADAPTER_JS)
        self.assertTrue(want, 'remake-core/scripts/engine_adapter.js has no ENGINE-ADAPTER block')
        for rel in ('runtime_regression/engine_adapter.mjs', 'ad_regression/cases.mjs'):
            self.assertEqual(block(SCRIPTS / rel), want, rel + ': the ENGINE-ADAPTER block must be engine_adapter.js adapt()')

    def test_labels_24(self):
        r = self.run_probe('24', 'labels')
        self.assertNotIn('threw', r, r)
        self.assertEqual(len(r['value']), 1, r)
        self.assertAlmostEqual(r['value'][0]['x'], 195, delta=1)
        self.assertAlmostEqual(r['value'][0]['y'], 844 - 422, delta=1)

    def test_labels_3x_module_cc_uitransform(self):
        r = self.run_probe('3x', 'labels')
        self.assertNotIn('threw', r, r)
        self.assertEqual(len(r.get('value') or []), 1, '3.x label (cc only in the module, UITransform) not found: %s' % r)
        hit = r['value'][0]
        self.assertNotIn('error', hit, hit)
        self.assertAlmostEqual(hit['x'], 195, delta=1)      # world 195 -> camera 390 px -> css 195 (canvas 780 / css 390)
        self.assertAlmostEqual(hit['y'], 844 - 422, delta=1)

    def test_labels_engine_not_up_asks_again(self):
        r = self.run_probe('none', 'labels')
        self.assertNotIn('threw', r, r)
        self.assertEqual(r['value'], [], r)
        self.assertEqual(r['calls'], 3, 'engine not up: findLabels must ask the page again (3 calls), got %s' % r)

    def test_ready_3x_and_not_up(self):
        r = self.run_probe('3x', 'ready')
        self.assertTrue(r['value']['ok'], '3.x page with cc only in the module must count as ready: %s' % r)
        r = self.run_probe('none', 'ready')
        self.assertFalse(r['value']['ok'], r)
        self.assertIn('引擎还没起来', r['value'].get('notReady') or '', 'waitFor must say why: %s' % r)

    def test_geom_not_up_no_throw(self):
        r = self.run_probe('none', 'geom')
        self.assertNotIn('threw', r, 'GEOM_JS threw while the engine was not up: %s' % r)
        self.assertIs(r['value']['ready'], False, r)
        self.assertEqual(r['value']['walked'], 0, r)
        self.assertIn('引擎还没起来', r['value']['reason'] or '', r)
        r = self.run_probe('3x', 'geom')
        self.assertNotIn('threw', r, r)
        self.assertTrue(r['value']['v3'], r)
        self.assertGreater(r['value']['walked'], 0, r)

    def test_cases_probes_use_adapter(self):
        text = (SCRIPTS / 'ad_regression' / 'cases.mjs').read_text(encoding='utf-8')
        m = re.search(r'const findExit = \(\) => [\s\S]*?\n\}, A\);', text)
        self.assertTrue(m, 'findExit not found')
        self.assertNotIn('n.convertToWorldSpaceAR', m.group(0), 'findExit: world points through engine_adapter, not node.convertToWorldSpaceAR')
        self.assertIn('window.__ccAdapt(window)', m.group(0))
        self.assertRegex(text, r"window\.__adq\.ready = A\.ready \? new Function\(A\.ready\) : function \(\) \{ return window\.__ccAdapt\(window\)\.ready === true; \}")


if __name__ == '__main__':
    unittest.main()
