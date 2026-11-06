#!/usr/bin/env python3
"""11.17 R4Q7 item 5b (SLS14-1, rollout 04-20-45 :315): the local ad simulator threw "host.attachShadow is not a
function" when the page's createElement gave no real Element, so its badge and ad window never drew. Now it draws into
the div itself with scoped styles. Runs assets/ad-simulator.js under node with a fake page (no browser).
OLD_ASSETS=<base-tree remake-core/assets> runs it against the old simulator.
  python3 -B test_r4q7_ad_simulator_host.py
"""
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = Path(os.environ.get('OLD_ASSETS') or HERE.parent / 'assets') / 'ad-simulator.js'

HARNESS = r"""
const vm = require('vm'), fs = require('fs');
const [simPath, simMode] = process.argv.slice(-2); const shadowOk = simMode === 'shadow';
function el(tag) {
  const e = { tagName: tag, id: '', style: {}, children: [], _html: '', textContent: '',
    appendChild(c) { this.children.push(c); return c; }, replaceChildren() { this.children = []; },
    set innerHTML(v) { this._html = v; this._kids = { badge: el('button'), box: el('section') }; },
    get innerHTML() { return this._html; },
    querySelector(sel) { return this._kids && this._kids[sel.replace('#', '')] || null; } };
  if (shadowOk) e.attachShadow = function () { const s = el('shadow'); s.getElementById = id => s._kids[id]; this._shadow = s; return s; };
  return e;
}
const body = el('body');
const document = { body, readyState: 'complete', createElement: el, querySelector: () => null, addEventListener() {} };
const window = { location: { hostname: '127.0.0.1', search: '' }, localStorage: { length: 0, key() {}, getItem() {} },
  document, setTimeout, clearTimeout };
const out = {};
try {
  vm.runInNewContext(fs.readFileSync(simPath, 'utf8'), { window, document, setTimeout, clearTimeout, console, JSON, Object, String, Date });
  const host = body.children.find(c => c.id === '__ad-simulator');
  out.drawn = !!host;
  out.html = host ? (host._shadow ? host._shadow._html : host._html) : '';
  out.ad = typeof window.tt.createRewardedVideoAd;
} catch (e) { out.error = String(e && e.message || e); }
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which('node'), 'node not installed')
class SimulatorHost(unittest.TestCase):
    def run_sim(self, mode):
        p = subprocess.run(['node', '-e', HARNESS, '--', str(SIM), mode], capture_output=True, text=True, timeout=30,
                           stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout.strip().splitlines()[-1])

    def test_no_attach_shadow_still_draws_with_scoped_styles(self):
        r = self.run_sim('plain')
        self.assertNotIn('error', r, r)
        self.assertTrue(r['drawn'], r)
        self.assertIn('#__ad-simulator button{', r['html'])      # styles do not leak into the game page
        self.assertEqual(r['ad'], 'function')

    def test_real_shadow_root_unchanged(self):
        r = self.run_sim('shadow')
        self.assertNotIn('error', r, r)
        self.assertTrue(r['drawn'], r)
        self.assertIn('<style>*{box-sizing:border-box}button{', r['html'])


if __name__ == '__main__':
    unittest.main()
