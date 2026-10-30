#!/usr/bin/env python3
"""Rewarded-ad regression gate: fail-closed wiring and verdict, without a browser.

The browser cases themselves are proven on real packages (Marlows r4 must fail
'nocallback', r5 must pass all 10); see remake-ads/references/ad-timeout-and-regression.md.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ad_regression
import runtime_regression
from check_package import check, rewarded_ad_gate, runtime_gate, write_archive
from test_package_checks import fixture, APP

AD_JS = b"var ad=tt.createRewardedVideoAd({adUnitId:'x'});"


def passing_result():
    return {'fatal': None, 'cases': [{'case': c, 'ok': True, 'problems': []} for c in ad_regression.CASES]}


class Verdict(unittest.TestCase):
    def test_all_cases_pass(self):
        self.assertEqual(ad_regression.judge(passing_result()), (True, []))

    def test_one_failed_case_fails(self):
        result = passing_result()
        result['cases'][8] = {'case': 'nocallback', 'ok': False,
                              'problems': ['immediate next ad failed (did not start)']}
        passed, problems = ad_regression.judge(result)
        self.assertFalse(passed)
        self.assertIn('nocallback: immediate next ad failed', problems[0])

    def test_missing_case_or_fatal_fails(self):
        result = passing_result()
        result['cases'].pop()
        self.assertFalse(ad_regression.judge(result)[0])
        result = passing_result()
        result['fatal'] = 'game did not become ready'
        self.assertFalse(ad_regression.judge(result)[0])
        self.assertFalse(ad_regression.judge(None)[0])

    def test_ok_flag_with_problems_still_fails(self):
        result = passing_result()
        result['cases'][0]['problems'] = ['music not resumed']
        self.assertFalse(ad_regression.judge(result)[0])


class FailClosed(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ad regression tests ')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def adapter(self, data):
        path = self.root / 'adapter.json'
        path.write_text(json.dumps(data))
        return path

    def test_needs_regression_detects_rewarded_calls_only(self):
        self.assertTrue(ad_regression.needs_regression({'assets/main/index.js': AD_JS}))
        self.assertFalse(ad_regression.needs_regression({'a.js': b'var x=1;', 'b.json': AD_JS}))

    def test_adapter_required_and_validated(self):
        for bad in (None, self.root / 'missing.json'):
            with self.assertRaises(ad_regression.RegressionRefused):
                ad_regression.load_adapter(bad)
        for data in ({}, {'request': ''}, {'request': 'x', 'surprise': 1}, {'request': 'x', 'exit': 3}):
            with self.assertRaises(ad_regression.RegressionRefused):
                ad_regression.load_adapter(self.adapter(data))
        self.assertEqual(ad_regression.load_adapter(self.adapter({'request': 'grant();'}))['request'], 'grant();')

    def test_no_browser_refuses_never_passes(self):
        package = self.root / 'pkg'
        package.mkdir()
        (package / 'game.js').write_text('')
        with patch.dict(os.environ, {'EGO_BROWSER': ''}), patch('ad_regression._which', return_value=None):
            with self.assertRaisesRegex(ad_regression.RegressionRefused, 'needs the Ego browser'):
                ad_regression.run(package, self.adapter({'request': 'grant();'}))

    def staged(self):
        """An ad package staged as check() stages verified bytes (game.js at the root)."""
        folder = self.root / 'staged'
        files = {'game.js': b'', 'assets/main/index.js': AD_JS}
        for name, data in files.items():
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            (folder / name).write_bytes(data)
        return files, folder

    def test_gate_refuses_ad_package_without_adapter(self):
        files, folder = self.staged()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ad_regression.ENV_ADAPTER, None)
            with self.assertRaisesRegex(ValueError, 'rewarded-ad regression required'):
                rewarded_ad_gate(files, folder)

    def test_gate_refuses_when_browser_missing(self):
        files, folder = self.staged()
        adapter = self.adapter({'request': 'grant();'})
        with patch.dict(os.environ, {'EGO_BROWSER': ''}), patch('ad_regression._which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'needs the Ego browser'):
                rewarded_ad_gate(files, folder, adapter)

    def test_gate_refuses_failed_regression_and_reads_env_adapter(self):
        files, folder = self.staged()
        adapter = self.adapter({'request': 'grant();'})
        error = ad_regression.RegressionRefused('rewarded-ad regression failed: nocallback: immediate next ad failed')
        with patch.dict(os.environ, {ad_regression.ENV_ADAPTER: str(adapter)}), \
                patch('ad_regression.run', side_effect=error) as run:
            with self.assertRaisesRegex(ValueError, 'nocallback'):
                rewarded_ad_gate(files, folder)
        self.assertEqual(run.call_args[0], (folder, str(adapter)))

    def test_check_wires_the_gate_on_verified_bytes(self):
        archive = self.root / 'plain.zip'
        write_archive(archive, fixture())
        with patch('check_package.rewarded_ad_gate', side_effect=ValueError('rewarded-ad regression required')) as gate:
            with self.assertRaisesRegex(ValueError, 'rewarded-ad regression required'):
                check(archive, APP, ad_regression='adapter.json')
        files, folder, adapter = gate.call_args[0]
        self.assertIn('game.js', files)
        self.assertEqual(adapter, 'adapter.json')

    def test_package_without_rewarded_ads_is_not_applicable(self):
        archive = self.root / 'plain.zip'
        write_archive(archive, fixture())
        # The runtime regression is mandatory for every package with game.js; patched here like rewarded_ad_gate.
        with patch('check_package.runtime_gate', return_value={'id': 'runtime_regression', 'status': 'patched'}):
            self.assertEqual(check(archive, APP)['rewarded_ad_regression']['status'], 'not_applicable')


class RuntimeGateFailClosed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_runtime_gate_refuses_without_adapter(self):
        (self.root / 'game.js').write_bytes(b'x')
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(runtime_regression.ENV_ADAPTER, None)
            with self.assertRaisesRegex(ValueError, 'runtime regression required'):
                runtime_gate({'game.js': b'x'}, self.root)

    def test_runtime_gate_runs_required_suites_with_env_adapter(self):
        with patch.dict(os.environ, {runtime_regression.ENV_ADAPTER: 'adapter.json'}), \
                patch('runtime_regression.required_suites', return_value=['startup']) as req, \
                patch('runtime_regression.run', return_value={'id': 'runtime_regression', 'passed': True}) as run:
            self.assertTrue(runtime_gate({'game.js': b'x'}, self.root)['passed'])
        self.assertEqual(req.call_args[0], ({'game.js': b'x'}, 'adapter.json'))
        self.assertEqual(run.call_args[0], (self.root, 'adapter.json', ['startup']))

    def test_runtime_gate_failure_refuses(self):
        error = runtime_regression.RuntimeRefused('runtime regression failed: startup/pkg_stall_40pct: no Retry')
        with patch('runtime_regression.required_suites', return_value=['startup']), \
                patch('runtime_regression.run', side_effect=error):
            with self.assertRaisesRegex(ValueError, 'pkg_stall_40pct'):
                runtime_gate({'game.js': b'x'}, self.root, 'adapter.json')

    def test_check_wires_runtime_gate_on_verified_bytes(self):
        archive = self.root / 'plain.zip'
        write_archive(archive, fixture())
        with patch('check_package.runtime_gate', side_effect=ValueError('runtime regression required')) as gate:
            with self.assertRaisesRegex(ValueError, 'runtime regression required'):
                check(archive, APP, ad_regression='adapter.json')
        files, folder, adapter = gate.call_args[0]
        self.assertIn('game.js', files)
        self.assertEqual(adapter, 'adapter.json')


class ExitTapPoint(unittest.TestCase):
    """v7.7.4 (总表 A5): the X control is tapped where it really is on screen.

    Runs the css-point block of ad_regression/cases.mjs in Node with fake Cocos values. Cocos 2.x
    getWorldToScreenPoint returns cc.visibleRect units; v7.7.3 divided by canvas.width (physical pixels), so at DPR 2
    the X was tapped off screen and nocallback failed games whose ads were fine (MusicSlice v31, Meteor Blaster r3).
    """
    CASES_MJS = Path(__file__).resolve().parent / 'ad_regression' / 'cases.mjs'
    SCENARIOS = [
        # 2.x, design = screen, DPR 2: X at (330, 760) in visible units -> css (330, 52)
        {'cc': {'visibleRect': {'width': 375, 'height': 812}}, 'v2api': True, 'canvas': {'width': 750, 'height': 1624},
         'rect': {'left': 0, 'top': 0, 'width': 375, 'height': 812}, 'p': {'x': 330, 'y': 760}, 'want': [330, 52]},
        # 2.x, 720x1280 fit-height on a 375x812 screen, DPR 3, page offset (10, 20)
        {'cc': {'visibleRect': {'width': 1280 * 375 / 812, 'height': 1280}}, 'v2api': True,
         'canvas': {'width': 1125, 'height': 2436}, 'rect': {'left': 10, 'top': 20, 'width': 375, 'height': 812},
         'p': {'x': 1280 * 375 / 812 * 0.9, 'y': 1200}, 'want': [10 + 375 * 0.9, 20 + 812 - 1200 * 812 / 1280]},
        # 3.x: worldToScreen returns canvas pixels, unchanged behaviour
        {'cc': {}, 'v2api': False, 'canvas': {'width': 750, 'height': 1624},
         'rect': {'left': 0, 'top': 0, 'width': 375, 'height': 812}, 'p': {'x': 660, 'y': 1520}, 'want': [330, 52]},
    ]

    def block(self):
        text = self.CASES_MJS.read_text(encoding='utf-8')
        return text[text.index('// css-point:begin'):text.index('// css-point:end')]

    def points(self, block):
        import shutil
        import subprocess
        node = shutil.which('node')
        self.assertIsNotNone(node, 'node is required for the ad regression and this test')
        js = ('const f = (cc, v2api, canvas, rect, p) => {\n' + block + '\n};\n'
              'const S = ' + json.dumps(self.SCENARIOS) + ';\n'
              'console.log(JSON.stringify(S.map(s => f(s.cc, s.v2api, s.canvas, s.rect, s.p))));\n')
        r = subprocess.run([node, '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_tap_lands_on_the_x(self):
        for s, got in zip(self.SCENARIOS, self.points(self.block())):
            with self.subTest(scenario=s):
                self.assertAlmostEqual(got['x'], s['want'][0], places=3)
                self.assertAlmostEqual(got['y'], s['want'][1], places=3)

    def test_negative_control_v773_formula_misses_at_dpr_2(self):
        old = self.block().replace('vis.w', 'canvas.width').replace('vis.h', 'canvas.height')
        got = self.points(old)
        for s, g in list(zip(self.SCENARIOS, got))[:2]:
            with self.subTest(scenario=s):
                self.assertGreater(abs(g['x'] - s['want'][0]) + abs(g['y'] - s['want'][1]), 40, g)


if __name__ == '__main__':
    unittest.main()
