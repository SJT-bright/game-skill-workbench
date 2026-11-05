#!/usr/bin/env python3
"""生成时预防 #41 (普查 hit_area_misaligned 13/17、multitouch_conflict 9/12; BrothersRush「本地预览鼠标划不动」):
the 2.x native host (ad_regression/host.js, also served by runtime_regression for 2.x) turned the mouse into TikTok
touches only with ?mouse=1. The runners pass it; a person or AI opening /__host/play.html by hand did not, and the
game ignored every click and drag. Now it is on by default (?mouse=0 turns it off), left button only, and a mouse
event caused by a real touch (finger down, or within 800 ms after one) is not delivered a second time.

No browser: the input block of host.js (from "// ---------- events ----------" to "var hidden = false;") runs in
node with a fake canvas and window; the test reads what the game's tt.onTouchStart/Move/End listeners got.
Old host.js: no ?mouse -> mousedown gives no touchstart -> fails. Run: python3 -B test_ad_host_mouse_touch.py
(AD_HOST_JS=<other host.js> runs it against another copy)
"""
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
HOST = Path(os.environ.get('AD_HOST_JS') or SCRIPTS / 'ad_regression' / 'host.js')

DRIVER = r"""
const src = require('fs').readFileSync(process.argv[process.argv.length - 1], 'utf8');
const a = src.indexOf('// ---------- events ----------'), b = src.indexOf('var hidden = false;', a);
if (a < 0 || b < 0) { console.log(JSON.stringify({ error: 'input block not found' })); process.exit(0); }
const block = src.slice(a, b) + '\nreturn H_;';
function target() { const L = {}; return { L, addEventListener(t, f) { (L[t] = L[t] || []).push(f); },
  fire(t, e) { (L[t] || []).forEach(f => f(Object.assign({ preventDefault() {} }, e))); } }; }
let clock = 1000;
const now = () => clock;
function run(query, steps) {
  const main = target(), win = target(), got = [];
  const H_ = new Function('Q', 'main', 'window', 'beacon', 'now', block)(new URLSearchParams(query), main, win, () => {}, now);
  ['touchstart', 'touchmove', 'touchend'].forEach(t => H_[t].on(v => got.push([t, v.changedTouches.map(p => [p.identifier, p.screenX, p.screenY])])));
  for (const [where, type, e, wait] of steps) { clock += wait || 0; (where === 'w' ? win : main).fire(type, e); }
  return got;
}
const M = (x, y, button) => ({ clientX: x, clientY: y, button: button || 0, timeStamp: 1 });
const T = (x, y, down) => { const p = { identifier: 3, clientX: x, clientY: y, force: 1 }; return { touches: down ? [p] : [], changedTouches: [p], timeStamp: 1 }; };
const drag = [['m', 'mousedown', M(10, 20)], ['w', 'mousemove', M(15, 30), 16], ['w', 'mouseup', M(15, 30), 16]];
console.log(JSON.stringify({
  plain: run('', drag),
  off: run('mouse=0', drag),
  runner: run('mouse=1&run=x', drag),
  right: run('', [['m', 'mousedown', M(10, 20, 2)], ['w', 'mouseup', M(10, 20, 2), 16]]),
  touchThenCompatMouse: run('', [['m', 'touchstart', T(5, 6, true)], ['m', 'touchend', T(5, 6, false), 30],
                                 ['m', 'mousedown', M(5, 6), 5], ['w', 'mouseup', M(5, 6), 5]]),
  mouseLongAfterTouch: run('', [['m', 'touchstart', T(5, 6, true)], ['m', 'touchend', T(5, 6, false), 30],
                                ['m', 'mousedown', M(7, 8), 2000], ['w', 'mouseup', M(7, 8), 16]]),
}));
"""


@unittest.skipUnless(shutil.which('node'), 'node not installed')
class AdHostMouseToTouch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(['node', '-e', DRIVER, str(HOST)], capture_output=True, text=True, timeout=30)
        cls.r = json.loads(out.stdout.strip().splitlines()[-1]) if out.stdout.strip() else {'error': out.stderr[-500:]}

    def test_mouse_works_without_query(self):
        self.assertNotIn('error', self.r)
        self.assertEqual([e[0] for e in self.r['plain']], ['touchstart', 'touchmove', 'touchend'],
                         'host page opened without ?mouse=1: a mouse drag must reach the game as touches')
        self.assertEqual(self.r['plain'][0][1], [[0, 10, 20]])
        self.assertEqual(self.r['plain'], self.r['runner'], 'runner query mouse=1 keeps the same behaviour')

    def test_off_switch_and_right_button(self):
        self.assertEqual(self.r['off'], [])
        self.assertEqual(self.r['right'], [])

    def test_real_touch_not_delivered_twice(self):
        self.assertEqual([e[0] for e in self.r['touchThenCompatMouse']], ['touchstart', 'touchend'])
        self.assertEqual([e[0] for e in self.r['mouseLongAfterTouch']], ['touchstart', 'touchend', 'touchstart', 'touchend'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
