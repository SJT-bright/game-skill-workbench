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
DIVIDE = re.compile(r'/\s*(?:cc\.game\.)?canvas\.(?:width|height)\b')
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


if __name__ == '__main__':
    unittest.main(verbosity=1)
