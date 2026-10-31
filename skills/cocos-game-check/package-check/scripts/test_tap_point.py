#!/usr/bin/env python3
"""v7.7.5 (总表 A13): every tool that turns a Cocos node into a screen tap point uses the same conversion.

v7.7.4 fixed the X tap in ad_regression/cases.mjs (A5) but left the old formula `p * rect.width / canvas.width` in
runtime_regression/lib.mjs (findLabels and locate). Cocos 2.x getWorldToScreenPoint works in cc.visibleRect units,
so at DPR 2 the lifecycle cases tapped below PLAY (全民飞车漂移 hit PROFILE) and reported "home locked" for a game
that was fine. This test
  1. runs every `// css-point:begin ... // css-point:end` block under cocos-game-check in Node with fake Cocos
     values (2.x at DPR 2 and DPR 3 with a page offset, 3.x) and checks the point lands on the control;
  2. fails when any .js/.mjs/.cjs under cocos-game-check divides by canvas.width / canvas.height outside such a
     block, so a copied old formula cannot come back unnoticed.
v7.8 (总表 A13 补): the step before it, world point -> screen point, picked `cams[0]` on Cocos 3.x, which is the 3D world
camera in a 3D game (企鹅雪道 v4: the ad X came out at (818, -918), nocallback failed). Every
`// cam-point:begin ... // cam-point:end` block (same text in cases.mjs and both lib.mjs sites) must pick the camera of the
node's Canvas, fall back to the first camera only without one, keep 2.x on cc.Camera.findCamera, and land on the control
together with the css-point block in a "3D scene + UI camera" scene; a first-camera pick outside such a block fails.
Run: python3 test_tap_point.py
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parents[1]                                   # cocos-game-check/
BLOCK = re.compile(r'(// css-point:begin.*?)// css-point:end', re.S)   # group 1 keeps the marker line a comment
CAM = re.compile(r'(// cam-point:begin.*?)// cam-point:end', re.S)
DIVIDE = re.compile(r'/\s*(?:cc\.game\.)?canvas\.(?:width|height)\b')
# v7.8 (总表 A13 补): a 3.x screen point taken from the scene's first camera (the 3D world camera in a 3D game).
FIRST_CAMERA = re.compile(r'(?:cams|cameras)\s*\[\s*0\s*\]\s*\.\s*worldToScreen|getComponentsInChildren\(\s*cc\.Camera\s*\)\s*\[\s*0\s*\]')
SUFFIXES = ('.js', '.mjs', '.cjs')
WANT_BLOCKS = {'package-check/scripts/ad_regression/cases.mjs': 1, 'package-check/scripts/runtime_regression/lib.mjs': 2}
SCENARIOS = [
    # 2.x, design = screen, DPR 2: control at (330, 760) in visible units -> css (330, 52)
    {'cc': {'visibleRect': {'width': 375, 'height': 812}}, 'v2api': True, 'canvas': {'width': 750, 'height': 1624},
     'rect': {'left': 0, 'top': 0, 'width': 375, 'height': 812}, 'p': {'x': 330, 'y': 760}, 'want': [330, 52]},
    # 2.x, 720x1280 fit-height on a 375x812 screen, DPR 3, page offset (10, 20)
    {'cc': {'visibleRect': {'width': 1280 * 375 / 812, 'height': 1280}}, 'v2api': True,
     'canvas': {'width': 1125, 'height': 2436}, 'rect': {'left': 10, 'top': 20, 'width': 375, 'height': 812},
     'p': {'x': 1280 * 375 / 812 * 0.9, 'y': 1200}, 'want': [10 + 375 * 0.9, 20 + 812 - 1200 * 812 / 1280]},
    # 3.x: worldToScreen returns canvas pixels
    {'cc': {}, 'v2api': False, 'canvas': {'width': 750, 'height': 1624},
     'rect': {'left': 0, 'top': 0, 'width': 375, 'height': 812}, 'p': {'x': 660, 'y': 1520}, 'want': [330, 52]},
]


# Fake Cocos scenes for the cam-point block, built in Node: `S(name)` -> {cc, v2api, n, w, want}. A camera maps a world
# point to (w.x * k + dx, w.y * k + dy). World camera numbers are what a 3D camera gives for a UI point (企鹅雪道 v4).
CAM_SCENES = r'''
class Vec3 { constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; } }
const cam = (k, dx, dy) => ({ worldToScreen(w, out) { out.x = w.x * k + dx; out.y = w.y * k + dy; return out; } });
const node = (parent, comps = {}) => ({ parent, getComponent(c) { return comps[c.__name] || null; } });
const Canvas = { __name: 'Canvas' }, Camera = { __name: 'Camera' };
function S(name) {
  const w = new Vec3(330, 760, 0);
  const world = cam(3.1, -205, -3274), ui = cam(2, 0, 0);
  const scene = (cams) => ({ getComponentsInChildren(c) { return c === Camera ? cams : []; } });
  if (name === '2x') {
    const own = { getWorldToScreenPoint: (p) => ({ x: p.x, y: p.y }) };
    const cc = { Camera: { findCamera: () => own }, director: { getScene: () => scene([world]) }, Vec3, Canvas };
    return { cc, v2api: true, n: node(null), w, want: { x: 330, y: 760 } };
  }
  const canvasNode = node(null, { Canvas: name === '3x_private' ? { _cameraComponent: ui } : { cameraComponent: ui } });
  const panel = node(canvasNode);
  const cams = name === '3x_2d' ? [ui] : [world, ui];
  const cc = { Camera, Canvas, Vec3, director: { getScene: () => scene(cams) } };
  if (name === '3x_no_canvas') return { cc, v2api: false, n: node(node(null)), w, want: world.worldToScreen(w, new Vec3()) };
  return { cc, v2api: false, n: node(panel), w, want: { x: 660, y: 1520 } };
}
'''
CAM_NAMES = ['2x', '3x_2d', '3x_3d_ui', '3x_private', '3x_no_canvas']
# v7.7.5 3.x branch (the A13 bug), for the negative control.
V775_CAM = ('if (v2api) p = cc.Camera.findCamera(n).getWorldToScreenPoint(w);\n'
            'else { const cams = cc.director.getScene().getComponentsInChildren(cc.Camera); p = new cc.Vec3(); '
            'cams[0].worldToScreen(w, p); }\n')


def run_cam(block, names=CAM_NAMES):
    node = shutil.which('node')
    if not node:
        raise unittest.SkipTest('node is required for the tap-point check')
    js = (CAM_SCENES + 'const f = (cc, v2api, n, w) => { let p;\n' + block + '\nreturn { x: p.x, y: p.y }; };\n'
          'console.log(JSON.stringify(' + json.dumps(names) + '.map(k => { const s = S(k); '
          'return { got: f(s.cc, s.v2api, s.n, s.w), want: { x: s.want.x, y: s.want.y } }; })));\n')
    r = subprocess.run([node, '-e', js], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-800:])
    return json.loads(r.stdout)


def flat(block):
    return '\n'.join(line.strip() for line in block.strip().splitlines())


def tool_files():
    return sorted(p for p in SKILL.rglob('*') if p.suffix in SUFFIXES and p.is_file() and 'node_modules' not in p.parts)


def outside_blocks(text):
    """(line number, line) of every division by the canvas size that is not inside a css-point block."""
    spans = [m.span() for m in BLOCK.finditer(text)]
    out = []
    for m in DIVIDE.finditer(text):
        if not any(a <= m.start() < b for a, b in spans):
            line = text.count('\n', 0, m.start()) + 1
            out.append((line, text.splitlines()[line - 1].strip()[:160]))
    return out


def run_block(block):
    node = shutil.which('node')
    if not node:
        raise unittest.SkipTest('node is required for the tap-point check')
    js = ('const f = (cc, v2api, canvas, rect, p) => {\n' + block + '\n};\n'
          'const S = ' + json.dumps(SCENARIOS) + ';\n'
          'console.log(JSON.stringify(S.map(s => f(s.cc, s.v2api, s.canvas, s.rect, s.p))));\n')
    r = subprocess.run([node, '-e', js], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-800:])
    return json.loads(r.stdout)


class TapPoint(unittest.TestCase):
    def test_every_conversion_block_lands_on_the_control(self):
        found = {}
        for p in tool_files():
            rel = p.relative_to(SKILL).as_posix()
            for i, m in enumerate(BLOCK.finditer(p.read_text(encoding='utf-8', errors='replace'))):
                found[rel] = found.get(rel, 0) + 1
                for s, got in zip(SCENARIOS, run_block(m.group(1))):
                    with self.subTest(file=rel, block=i, scenario=s['p']):
                        self.assertAlmostEqual(got['x'], s['want'][0], places=3)
                        self.assertAlmostEqual(got['y'], s['want'][1], places=3)
        for rel, n in WANT_BLOCKS.items():
            self.assertEqual(found.get(rel), n, '%s should hold %d css-point block(s)' % (rel, n))

    def test_no_canvas_size_division_outside_a_block(self):
        bad = []
        for p in tool_files():
            for line, src in outside_blocks(p.read_text(encoding='utf-8', errors='replace')):
                bad.append('%s:%d  %s' % (p.relative_to(SKILL).as_posix(), line, src))
        self.assertFalse(bad, 'convert node positions with a css-point block (see ad_regression/cases.mjs), '
                              'not by dividing by the canvas size:\n' + '\n'.join(bad))

    def test_negative_controls(self):
        v774 = 'hits.push({ text: l.string, x: rect.left + p.x * rect.width / canvas.width, y: 0 });'
        self.assertEqual(len(outside_blocks(v774)), 1)              # the v7.7.4 lib.mjs line is caught
        block = BLOCK.search((HERE / 'runtime_regression' / 'lib.mjs').read_text(encoding='utf-8')).group(1)
        old = block.replace('vis.w', 'canvas.width').replace('vis.h', 'canvas.height')
        for s, g in list(zip(SCENARIOS, run_block(old)))[:2]:       # the old formula misses at DPR 2 and 3
            with self.subTest(scenario=s['p']):
                self.assertGreater(abs(g['x'] - s['want'][0]) + abs(g['y'] - s['want'][1]), 40, g)

    # ---- v7.8 (总表 A13 补): which camera turns the world point into a screen point
    def cam_blocks(self):
        found = {}
        for p in tool_files():
            rel = p.relative_to(SKILL).as_posix()
            for m in CAM.finditer(p.read_text(encoding='utf-8', errors='replace')):
                found.setdefault(rel, []).append(m.group(1))
        return found

    def test_every_camera_block_picks_the_canvas_camera(self):
        found = self.cam_blocks()
        for rel, n in WANT_BLOCKS.items():
            self.assertEqual(len(found.get(rel, [])), n, '%s should hold %d cam-point block(s)' % (rel, n))
        texts = {flat(b) for blocks in found.values() for b in blocks}
        self.assertEqual(len(texts), 1, 'the cam-point blocks differ between the tools: keep one conversion')
        for rel, blocks in found.items():
            for i, block in enumerate(blocks):
                for name, row in zip(CAM_NAMES, run_cam(block)):
                    with self.subTest(file=rel, block=i, scene=name):
                        self.assertAlmostEqual(row['got']['x'], row['want']['x'], places=3)
                        self.assertAlmostEqual(row['got']['y'], row['want']['y'], places=3)

    def test_3d_scene_with_ui_camera_lands_on_the_control(self):
        """cam-point + css-point together, per file in source order: a 3.x UI button in a 3D game (world camera first in
        the scene, the Canvas camera second) maps to css (330, 52) on a 375x812 page at DPR 2; 2.x stays as before."""
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node is required for the tap-point check')
        for rel, want in WANT_BLOCKS.items():
            p = SKILL / rel
            text = p.read_text(encoding='utf-8')
            pairs = list(zip(CAM.finditer(text), BLOCK.finditer(text)))
            self.assertEqual(len(pairs), want, '%s: one cam-point block before each css-point block' % rel)
            for i, (cam, css) in enumerate(pairs):
                js = (CAM_SCENES + 'const f = (cc, v2api, n, w, canvas, rect) => { let p;\n' + cam.group(1) + '\n' +
                      css.group(1) + '\n};\nconst out = [];\n'
                      'const s3 = S("3x_3d_ui"); out.push(f(s3.cc, false, s3.n, s3.w, {width: 750, height: 1624}, '
                      '{left: 0, top: 0, width: 375, height: 812}));\n'
                      'const s2 = S("2x"); s2.cc.visibleRect = {width: 375, height: 812}; s2.w.y = 760; '
                      'out.push(f(s2.cc, true, s2.n, s2.w, {width: 750, height: 1624}, {left: 0, top: 0, width: 375, height: 812}));\n'
                      'console.log(JSON.stringify(out));\n')
                r = subprocess.run([node, '-e', js], capture_output=True, text=True, timeout=30)
                self.assertEqual(r.returncode, 0, r.stderr[-800:])
                for got, want in zip(json.loads(r.stdout), ([330, 52], [330, 52])):
                    with self.subTest(file=p.name, pair=i, want=want):
                        self.assertAlmostEqual(got['x'], want[0], places=3)
                        self.assertAlmostEqual(got['y'], want[1], places=3)

    def test_no_first_camera_pick_outside_a_block(self):
        bad = []
        for p in tool_files():
            text = p.read_text(encoding='utf-8', errors='replace')
            spans = [m.span() for m in CAM.finditer(text)]
            for m in FIRST_CAMERA.finditer(text):
                if not any(a <= m.start() < b for a, b in spans):
                    line = text.count('\n', 0, m.start()) + 1
                    bad.append('%s:%d  %s' % (p.relative_to(SKILL).as_posix(), line, text.splitlines()[line - 1].strip()[:160]))
        self.assertFalse(bad, 'pick the 3.x camera with a cam-point block (Canvas camera first), not cams[0]:\n' + '\n'.join(bad))

    def test_camera_negative_control(self):
        """The v7.7.5 3.x branch (cams[0]) misses in the 3D scene; it is also caught by the pattern check."""
        rows = dict(zip(CAM_NAMES, run_cam(V775_CAM)))
        bad = rows['3x_3d_ui']
        self.assertGreater(abs(bad['got']['x'] - bad['want']['x']) + abs(bad['got']['y'] - bad['want']['y']), 400, bad)
        self.assertAlmostEqual(rows['2x']['got']['x'], rows['2x']['want']['x'])     # 2.x was already right
        self.assertTrue(FIRST_CAMERA.search(V775_CAM))


if __name__ == '__main__':
    unittest.main(verbosity=1)
