#!/usr/bin/env python3
"""English 11.1 (SorensRivet, 补丁_手机才出的五类问题 测试记录): runtime_regression/geom.mjs cssBox() on Cocos 2.x mapped a
node's world box through cc.view only, so a game that draws through a moved camera got boxes off its buttons and every
tap by path (button_sweep, dead_shell, the phone suites' "tap") missed. cssBox now sends the two corners through the
node's camera (cc.Camera.findCamera) when that camera does not map world points to themselves.

GEOM_JS runs in Node on a fake Cocos 2.x engine (cc.view, cc.Camera.findCamera, cc.v2, node.getBoundingBoxToWorld):
  - default camera (identity): the box is exactly the old cc.view box, letterboxed and plain (no change for any game);
  - moved camera and zoomed camera: the box is where the camera draws the node;
  - findCamera missing, throwing or returning nothing: the old box.
Run: python3 test_geom_camera.py
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEOM = HERE / 'runtime_regression' / 'geom.mjs'

JS = r"""
const { GEOM_JS } = await import(%(geom)s);
const cases = %(cases)s;
const out = {};
for (const [name, c] of Object.entries(cases)) {
  const view = {
    getFrameSize: () => ({ width: c.frame[0], height: c.frame[1] }),
    getVisibleSize: () => ({ width: c.visible[0], height: c.visible[1] }),
    getVisibleOrigin: () => ({ x: 0, y: 0 }),
    getViewportRect: () => ({ x: c.vp[0], y: c.vp[1], width: c.vp[2], height: c.vp[3] }),
    getScaleX: () => c.scale, getScaleY: () => c.scale, getDevicePixelRatio: () => c.dpr,
  };
  const cam = c.cam === 'none' ? null : {
    getWorldToScreenPoint(p) {
      if (c.cam === 'throws') throw new Error('no camera');
      const [dx, dy, zoom, cx, cy] = c.cam;            // screen = (world - centre) * zoom + centre - shift
      return { x: (p.x - cx) * zoom + cx - dx, y: (p.y - cy) * zoom + cy - dy };
    },
  };
  const cc = { view, v2: (x, y) => ({ x, y }), Camera: c.noFind ? {} : { findCamera: () => cam } };
  const node = { getBoundingBoxToWorld: () => ({ x: c.box[0], y: c.box[1], width: c.box[2], height: c.box[3] }) };
  const cssBox = new Function('window', 'Element', GEOM_JS + '\nreturn cssBox;')({ cc }, function () {});
  out[name] = cssBox(node);
}
console.log(JSON.stringify(out));
"""

# 750 x 1624 design on a 375 x 812 pt phone at DPR 2 (0.5 pt a design unit); a button at x 100..300, y 1400..1500.
PLAIN = {'frame': [375, 812], 'visible': [750, 1624], 'vp': [0, 0, 750, 1624], 'scale': 1, 'dpr': 2,
         'box': [100, 1400, 200, 100]}
# letterboxed: 720 x 1280 shown 75 pt lower (bars), 375 / 720 pt a unit (MergeShot2048 style)
BARS = {'frame': [375, 812], 'visible': [720, 1280], 'vp': [0, 150, 750, 1333.33], 'scale': 750 / 720, 'dpr': 2,
        'box': [100, 1000, 200, 100]}


def run(cases):
    node = shutil.which('node')
    if not node:
        raise unittest.SkipTest('node is required for the geometry check')
    js = JS % {'geom': json.dumps(GEOM.as_uri()), 'cases': json.dumps(cases)}
    r = subprocess.run([node, '--input-type=module', '-e', js], capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise AssertionError(r.stderr[-2000:])
    return json.loads(r.stdout)


def old_box(c):
    """The cc.view-only formula cssBox used before 11.1 (map2, real viewport)."""
    kx = ky = c['scale'] / c['dpr']
    ox, oy = c['vp'][0] / c['dpr'], c['vp'][1] / c['dpr']
    x, y, w, h = c['box']
    return {'x0': ox + x * kx, 'x1': ox + (x + w) * kx, 'y0': c['frame'][1] - (oy + (y + h) * ky),
            'y1': c['frame'][1] - (oy + y * ky)}


class Cocos2Camera(unittest.TestCase):
    def assertBox(self, got, want):
        for k in ('x0', 'x1', 'y0', 'y1'):
            self.assertAlmostEqual(got[k], want[k], places=3, msg='%s %s %s' % (k, got, want))

    def test_default_camera_keeps_the_old_box(self):
        cases = {'plain': dict(PLAIN, cam=[0, 0, 1, 375, 812]), 'bars': dict(BARS, cam=[0, 0, 1, 360, 640]),
                 'tiny_shift': dict(PLAIN, cam=[0.2, -0.3, 1, 375, 812])}          # rounding noise is still identity
        got = run(cases)
        for name in cases:
            self.assertBox(got[name], old_box(cases[name]))

    def test_moved_camera_box_follows_the_camera(self):
        got = run({'moved': dict(PLAIN, cam=[50, -100, 1, 375, 812])})['moved']
        # world x 100..300 drawn 50 units left, y 1400..1500 drawn 100 units higher
        self.assertBox(got, old_box(dict(PLAIN, box=[50, 1500, 200, 100])))
        self.assertNotAlmostEqual(got['x0'], old_box(PLAIN)['x0'], places=1)

    def test_zoomed_camera_box_follows_the_camera(self):
        got = run({'zoom': dict(PLAIN, cam=[0, 0, 2, 375, 812])})['zoom']
        # zoom 2 about the centre: x (100..300 - 375) * 2 + 375 = -175..225, y (1400..1500 - 812) * 2 + 812 = 1988..2188
        self.assertBox(got, old_box(dict(PLAIN, box=[-175, 1988, 400, 200])))

    def test_letterboxed_and_moved_camera(self):
        got = run({'bars_moved': dict(BARS, cam=[-40, 20, 1, 360, 640])})['bars_moved']
        self.assertBox(got, old_box(dict(BARS, box=[140, 980, 200, 100])))

    def test_no_usable_camera_keeps_the_old_box(self):
        cases = {'none': dict(PLAIN, cam='none'), 'throws': dict(PLAIN, cam='throws'),
                 'no_find': dict(PLAIN, cam=[50, 0, 1, 375, 812], noFind=True)}
        got = run(cases)
        for name in cases:
            self.assertBox(got[name], old_box(PLAIN))


if __name__ == '__main__':
    unittest.main()
