#!/usr/bin/env python3
"""v7.8 (总表 P16 第 3 步): the frame_rate runtime suite (60 Hz and 120 Hz display, same operation, positions compared
at the same real time, more than 5 % apart = not passed).

Pieces: runtime_regression/frame_rate_compare.mjs runs in Node: the display clock (RAF_JS) really ticks at 60 / 120 Hz,
compare() refuses a body that runs faster at 120 Hz (the DriftRacer3D v3.1 shape: physics and pushes per frame) and passes
the same motion with a start offset and sampling jitter; a body that never moves is no_motion; a busy clock is an invalid
run. Wiring: the runner's precheck (needs_new / na_field / uncovered) on the fake browser of test_runtime_regression.py.
The browser half is proven on the real package (briefs/out/W92/RESULT.md: DriftRacer3D v3.1 19.9 % apart, refused; the same
package with enabledAccumulator and every push scaled by dt x 60 at most 1.05 %, passes).
Run: python3 -B test_frame_rate_gate.py
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from unittest.mock import patch

import runtime_regression as rr
from test_runtime_regression import Base, SIDECAR

HERE = Path(__file__).resolve().parent
COMPARE = HERE / 'runtime_regression' / 'frame_rate_compare.mjs'
SUITE = HERE / 'runtime_regression' / 'suites' / 'frame_rate.mjs'

HARNESS = r'''
const FR = await import(%(mod)s);
// a body pushed by a constant force, per engine frame (broken) or per real second (fixed); x(t) in world units
function run(hz, opt) {
  const dt = 1 / hz, rows = [];
  let x = 0, v = 0, t = 0;
  const startAt = opt.startAt || 0, jitter = opt.jitter || 0;
  const perFrame = opt.broken ? (1 / 60) : dt;            // broken: each frame steps physics 1/60 s
  for (let i = 0; t < (opt.runS || 5); i++) {
    t = i * dt;
    if (t >= startAt && t < (opt.stopAt || 1e9)) { v += 300 * perFrame; v *= opt.broken ? 0.98 : Math.pow(0.98, dt * 60); x += v * perFrame; }
    if (i %% Math.max(1, Math.round(hz / 100)) === 0) rows.push([Math.round((t + (i %% 3) * jitter) * 10000) / 10, opt.still ? 0 : x, 0, 0]);
  }
  return { hz, samples: rows, seconds: opt.runS || 5, ticks: (opt.ticks || hz) * (opt.runS || 5), frames: hz * (opt.runS || 5) };
}
const out = {};
%(body)s
console.log(JSON.stringify(out));
process.exit(0);    // the display clock keeps its timer running
'''


def node(body):
    exe = shutil.which('node')
    if not exe:
        raise unittest.SkipTest('node is required')
    js = HARNESS % {'mod': json.dumps(COMPARE.as_uri()), 'body': body}
    r = subprocess.run([exe, '--input-type=module', '-e', js], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-2000:])
    return json.loads(r.stdout)


class Compare(unittest.TestCase):
    def test_per_frame_physics_is_refused(self):
        r = node("out.v = FR.compare(run(60, {broken: true}), run(120, {broken: true}));")
        self.assertFalse(r['v']['passed'], r['v'])
        self.assertEqual(r['v']['code'], 'same_motion')
        self.assertGreater(r['v']['worst']['rel'], 0.3)          # 120 Hz runs about twice as fast

    def test_time_scaled_motion_passes_with_offset_and_jitter(self):
        r = node("out.v = FR.compare(run(60, {startAt: 0.7, jitter: 0.004}), run(120, {startAt: 0.43, jitter: 0.003}));"
                 "out.same = FR.compare(run(60, {}), run(120, {}));")
        self.assertTrue(r['v']['passed'], r['v']['worst'])
        self.assertLessEqual(r['v']['worst']['rel'], 0.05)
        self.assertGreaterEqual(len(r['v']['checkpoints']), 10)
        self.assertTrue(r['same']['passed'])

    def test_five_percent_is_the_line(self):
        r = node("var a = run(60, {}), b = run(120, {});"
                 "var scaled = (k) => Object.assign({}, b, {samples: b.samples.map((s) => [s[0], s[1] * k, 0, 0])});"
                 "out.in = FR.compare(a, scaled(1.04)); out.over = FR.compare(a, scaled(1.07));")
        self.assertTrue(r['in']['passed'], r['in']['worst'])
        self.assertFalse(r['over']['passed'], r['over']['worst'])

    def test_no_motion(self):
        r = node("out.v = FR.compare(run(60, {still: true}), run(120, {still: true}));"
                 "out.stops = FR.compare(run(60, {stopAt: 0.05}), run(120, {stopAt: 0.05}));")
        self.assertEqual((r['v']['code'], r['v']['passed']), ('no_motion', False))
        self.assertEqual(r['stops']['code'], 'no_motion')          # moved less than min_move

    def test_clock_check(self):
        r = node("out.ok = FR.clockCheck(run(120, {})); out.busy = FR.clockCheck(run(120, {ticks: 70}));"
                 "out.half = FR.clockCheck(Object.assign(run(120, {}), {frames: 300}));")
        self.assertEqual(r['ok'], {'invalid': [], 'warnings': []})
        self.assertTrue(r['busy']['invalid'] and 'display clock ran at 70.0 Hz' in r['busy']['invalid'][0], r['busy'])
        self.assertEqual(r['half']['invalid'], [])
        self.assertTrue(r['half']['warnings'])                     # frameRate 30 or skipped frames: reported only

    def test_display_clock_ticks_at_the_rate(self):
        r = node("globalThis.window = globalThis;"
                 "const count = (hz) => new Promise((done) => { (0, eval)(FR.RAF_JS(hz)); let n = 0; const t0 = performance.now();"
                 "  const f = () => { n++; if (performance.now() - t0 < 1000) requestAnimationFrame(f); else done(n); }; requestAnimationFrame(f); });"
                 "out.a = await count(60); out.b = await count(120); out.hz = window.__fr.hz;")
        self.assertTrue(54 <= r['a'] <= 63, r)
        self.assertTrue(108 <= r['b'] <= 123, r)
        self.assertEqual(r['hz'], 120)


class Wiring(Base):
    """The runner: frame_rate is required for every TikTok package; a new game needs adapter.frame_rate, a legacy game
    warns; {"n/a": reason} and Cocos 3.x are decided without the browser."""

    def fr(self):
        self.sidecar('fr', {**SIDECAR, 'name': 'fr', 'needs': [], 'needs_new': ['frame_rate'], 'na_field': 'frame_rate',
                            'uncovered': {'3.x': 'not calibrated on 3.x'}, 'fields': ['fake_mode', 'frame_rate']})
        (self.suites / 'fake.json').unlink()
        (self.suites / 'fake.mjs').unlink()

    def test_real_sidecar_and_required(self):
        catalog = rr.load_suites()
        meta = catalog['frame_rate']
        self.assertEqual((meta['applies'], meta['needs'], meta['needs_new'], meta['na_field'], meta['engines']),
                         (['tiktok'], [], ['frame_rate'], 'frame_rate', ['2.x', '3.x']))
        self.assertIn('3.x', meta['uncovered'])
        self.assertIn('frame_rate', rr.required_suites({'game.js': b'x'}, {}, catalog))
        self.assertIn('frame_rate', rr.adapter_keys(catalog))
        import check_package
        seen = {}
        with patch.object(rr, 'run', side_effect=lambda folder, adapter, names, **k: seen.update(names=names) or {}):
            check_package.runtime_gate({'game.js': b'x'}, self.package, self.adapter({'home': 'return true'}), policy='new')
        self.assertIn('frame_rate', seen['names'])                    # the writers run it (check_package.runtime_gate)

    def test_na_passes_without_the_browser(self):
        self.fr()
        summary = self.run_fake({'home': 'return true', 'frame_rate': {'n/a': 'match-3 board, nothing moves on its own'}})
        row = summary['suites'][0]
        self.assertTrue(summary['passed'])
        self.assertEqual((row['cases'][0]['id'], row['browser']), ('n_a', False))

    def test_missing_or_bad_field_refuses_new_warns_legacy(self):
        self.fr()
        with self.assertRaisesRegex(rr.RuntimeRefused, 'fr/adapter: adapter has no "frame_rate"'):
            self.run_fake({'home': 'return true'}, policy='new')
        summary = self.run_fake({'home': 'return true'}, policy='legacy')
        self.assertTrue(summary['passed'])
        self.assertTrue(any('legacy game: warning' in w for w in summary['warnings']), summary['warnings'])
        for bad, why in (({'track': 'return n'}, 'frame_rate.drive_js missing'), ({'n/a': ' '}, 'needs the reason'),
                         ({'n/a': 'x', 'track': 'p'}, 'no other keys')):
            with self.assertRaisesRegex(rr.RuntimeRefused, re.escape(why)):
                self.run_fake({'home': 'return true', 'frame_rate': bad}, policy='new')

    def test_uncovered_engine_warns(self):
        self.fr()
        summary = self.run_fake({'home': 'return true', 'engine': '3.x'}, policy='new')
        self.assertTrue(summary['passed'])
        self.assertEqual(summary['suites'][0]['cases'][0]['id'], 'uncovered')

    def test_complete_field_runs_the_suite(self):
        self.fr()
        summary = self.run_fake({'home': 'return true', 'frame_rate': {'track': 'return cc.find("Canvas/car")',
                                                                       'drive_js': 'go()', 'run_s': 6}})
        self.assertTrue(summary['passed'])
        self.assertIn('"drive_js": "go()"', (self.root / 'work' / 'fr' / 'entry.mjs').read_text())

    def test_frame_rate_problems(self):
        ok = {'track': 'return car', 'drive_js': 'race()'}
        self.assertEqual(rr.frame_rate_problems(ok), [])
        self.assertEqual(rr.frame_rate_problems({'n/a': 'no physics'}), [])
        self.assertEqual(rr.frame_rate_problems({**ok, 'start': [{'tap': 'Canvas/buy'}], 'prepare_js': 'x()', 'run_s': 10,
                                                 'steps': [{'at_s': 2, 'js': 'turn()'}], 'align': 'drive', 'min_move': 30}), [])
        self.assertIn("frame_rate has unknown key 'speed'", rr.frame_rate_problems({**ok, 'speed': 3}))
        self.assertIn('frame_rate.run_s must be 2..20 seconds', rr.frame_rate_problems({**ok, 'run_s': 30}))
        self.assertTrue(any('align' in p for p in rr.frame_rate_problems({**ok, 'align': 'end'})))
        self.assertTrue(any('steps[0]' in p for p in rr.frame_rate_problems({**ok, 'steps': [{'at_s': 9, 'js': 'x'}]})))
        self.assertEqual(rr.frame_rate_problems([]), ['frame_rate must be an object'])

    def test_suite_has_no_game_names(self):
        """DriftRacer3D names (RunUI, pysTouchEvent, btnks, PreUI) live in the adapter, not in the suite."""
        for path in (SUITE, COMPARE):
            code = '\n'.join(line for line in path.read_text(encoding='utf-8').splitlines() if not line.lstrip().startswith('//'))
            for name in ('RunUI', 'pysTouchEvent', 'btnks', 'PreUI', 'carBody'):
                self.assertNotIn(name, code, (path.name, name))
        text = SUITE.read_text(encoding='utf-8')
        self.assertIn('RATES = [60, 120]', text)
        self.assertIn('Page.addScriptToEvaluateOnNewDocument', text)
        self.assertIn('TOLERANCE = 0.05', COMPARE.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main(verbosity=1)
