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

    def test_runtime_gate_passes_policy_to_suites(self):
        """v7.8: dead_shell blocks a new game and only warns a legacy one, so the runtime suites must get the same
        policy as the package gates (W85 RESULT 1: FoxDenDash v1's finalize record says new, its bytes say legacy)."""
        with patch('runtime_regression.required_suites', return_value=['dead_shell']), \
                patch('runtime_regression.run', return_value={'id': 'runtime_regression', 'passed': True}) as run:
            runtime_gate({'game.js': b'x'}, self.root, 'adapter.json', policy='new')
            self.assertEqual(run.call_args.kwargs.get('policy'), 'new')
            runtime_gate({'game.js': b'x'}, self.root, 'adapter.json')
            self.assertIsNone(run.call_args.kwargs.get('policy'))

    def test_check_gives_runtime_gate_the_package_gate_policy(self):
        archive = self.root / 'plain.zip'
        write_archive(archive, fixture())
        for policy in ('new', 'legacy'):
            with patch('check_package.runtime_gate', side_effect=ValueError('runtime regression required')) as gate:
                with self.assertRaisesRegex(ValueError, 'runtime regression required'):
                    check(archive, APP, ad_regression='adapter.json', policy=policy)
            self.assertEqual(gate.call_args.kwargs.get('policy'), policy)


class Environment(unittest.TestCase):
    """v7.8 (总表 A6 补): 企鹅雪道 v4 ran the ad regression on an unfinished build (tiktok-touch-3x.js not installed), the X
    tap missed and nocallback looked like a broken ad. Such a run is 「环境不完整」 (exit 2), not 「包不通过」 (exit 1)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ad regression env ')
        self.root = Path(self.temp.name)
        self.package = self.root / 'pkg'
        (self.package / 'cocos-js').mkdir(parents=True)
        (self.package / 'cocos-js' / 'cc.js').write_text('')
        (self.package / 'web-adapter.js').write_text('')
        (self.package / 'game.js').write_text("require('./web-adapter');")
        (self.package / 'assets').mkdir()
        (self.package / 'assets' / 'index.js').write_bytes(AD_JS)
        self.adapter = self.root / 'adapter.json'
        self.adapter.write_text(json.dumps({'request': 'grant();'}))
        import sys
        sys.path.insert(0, str(runtime_regression.SHARED))
        import audit_upload_startup
        self.probe = patch.object(audit_upload_startup, 'audit_files', return_value={'errors': [
            'Cocos3 native touch coordinates rejected: SDK identifier/screenX/screenY/force touches must reach ...']})

    def tearDown(self):
        self.temp.cleanup()

    def test_run_without_touch_part_is_environment_incomplete(self):
        with self.probe, patch.dict(os.environ, {'EGO_BROWSER': ''}), patch('ad_regression._which', return_value=None):
            with self.assertRaises(ad_regression.EnvironmentIncomplete) as ctx:
                ad_regression.run(self.package, self.adapter)
        self.assertTrue(str(ctx.exception).startswith('环境不完整：'))
        self.assertIn('tiktok-touch-3x.js', str(ctx.exception))
        self.assertIsInstance(ctx.exception, ad_regression.RegressionRefused)

    def test_writer_gate_still_refuses_and_names_the_environment(self):
        files = {'game.js': b'', 'assets/index.js': AD_JS}
        with self.probe:
            with self.assertRaisesRegex(ValueError, '^环境不完整：'):
                rewarded_ad_gate(files, self.package, self.adapter)

    def main(self, package):
        import sys
        report = self.root / 'report.json'
        report.unlink(missing_ok=True)
        argv = ['ad_regression.py', '--package', str(package), '--adapter', str(self.adapter), '--report', str(report)]
        with patch.object(sys, 'argv', argv):
            code = ad_regression.main()
        return code, json.loads(report.read_text())

    def test_cli_exit_codes(self):
        with self.probe:
            code, doc = self.main(self.package)                     # a folder: only the touch part is checked
        self.assertEqual((code, doc['status']), (2, 'environment_incomplete'))
        archive = self.root / 'Game.zip'
        write_archive(archive, fixture())
        code, doc = self.main(archive)                              # a ZIP by hand: the writer receipt is needed
        self.assertEqual(code, 2)
        self.assertIn('no writer receipt', doc['environment'])
        self.assertTrue(doc['verdict'].startswith('环境不完整：'))
        failed = ad_regression.RegressionRefused('rewarded-ad regression failed: nocallback: reward count 1')
        with patch('ad_regression.run', side_effect=failed):
            code, doc = self.main(self.package)
        self.assertEqual((code, doc['verdict']), (1, '包不通过'))


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

    def test_adapter_that_converts_coordinates_itself_gets_a_hint(self):
        """v7.7.5 (总表 A14): the 全民飞车漂移 / 回家快跑 / 狐狸回窝 exit compensated the pre-v7.7.4 formula and now
        moves the tap off the X. Such an adapter gets a warning (never a refusal); one returning the node does not."""
        compensating = ("var c=cc.find('Canvas/x');var cam=cc.Camera.findCamera(c),p=cam.getWorldToScreenPoint("
                        "c.convertToWorldSpaceAR(cc.v2(0,0))),vs=cc.view.getVisibleSize(),cv=cc.game.canvas;"
                        "var w2=cam.getScreenToWorldPoint(cc.v2(p.x*cv.width/vs.width,p.y*cv.height/vs.height));"
                        "var l=c.convertToNodeSpaceAR(w2);return {node:c,x:l.x,y:l.y};")
        hint = ad_regression.adapter_warnings({'request': 'x', 'exit': compensating})
        self.assertEqual(len(hint), 1)
        self.assertIn('getScreenToWorldPoint', hint[0])
        self.assertIn('Return the X node', hint[0])
        for good in ("var b=cc.find('Canvas/adExitLayer/adExitButton');return b&&b.activeInHierarchy?{node:b,x:0,y:0}:null;",
                     "var x=cc.find('Canvas/__adExit');return x&&x.activeInHierarchy?x:null;", None):
            self.assertEqual(ad_regression.adapter_warnings({'request': 'x', 'exit': good}), [], good)

    def test_negative_control_v773_formula_misses_at_dpr_2(self):
        old = self.block().replace('vis.w', 'canvas.width').replace('vis.h', 'canvas.height')
        got = self.points(old)
        for s, g in list(zip(self.SCENARIOS, got))[:2]:
            with self.subTest(scenario=s):
                self.assertGreater(abs(g['x'] - s['want'][0]) + abs(g['y'] - s['want'][1]), 40, g)


class DoubleClaim(unittest.TestCase):
    """v7.8 (Saul 2026-10-31): check-in / spin result / gift pack window with the ticked-by-default "watch ad x2"
    checkbox. Ticked + watched -> 2x; ticked + closed midway -> nothing, the window stays and unticked pays 1x;
    unticked -> 1x, no video. The double-claim block of cases.mjs runs in Node against fake games."""
    CASES_MJS = Path(__file__).resolve().parent / 'ad_regression' / 'cases.mjs'
    GOOD = {'open': 'return 30;', 'claim': 'x', 'balance': 'return 0;'}
    # A fake claim window. flags turn on one bug each.
    GAME = r'''
const fake = (flags) => {
  const g = { balance: 100, base: 30, open: false, claimed: false, pending: null, shown: 0 };
  return {
    open: async () => { g.open = true; g.claimed = false; return flags.noBase ? null : { base: g.base }; },
    claim: async (checked) => {
      if (!g.open || g.claimed) return null;
      if (checked || flags.alwaysAd) { g.shown++; g.pending = { paid: false }; if (flags.payOnShow) g.balance += 2 * g.base; return null; }
      g.balance += (flags.freePays2x ? 2 : 1) * g.base; g.claimed = true; g.open = false; return null;
    },
    balance: async () => g.balance,
    shown: async () => g.shown,
    step: async (s) => {
      if (s === 'end' && g.pending) { g.balance += (flags.watchPays1x ? 1 : 2) * g.base; g.claimed = true; g.open = false; g.pending = null; }
      if (s === 'quit' && g.pending) { if (flags.quitPays) g.balance += g.base; if (flags.quitSwallows) { g.claimed = true; g.open = false; } g.pending = null; }
    },
    sleep: async () => {},
  };
};
'''

    def block(self):
        text = self.CASES_MJS.read_text(encoding='utf-8')
        return text[text.index('// double-claim:begin'):text.index('// double-claim:end')]

    def run_fake(self, flags):
        import shutil
        import subprocess
        node = shutil.which('node')
        self.assertIsNotNone(node, 'node is required for the ad regression and this test')
        js = (self.block() + self.GAME + '(async () => { const r = {};\n'
              'for (const k of Object.keys(DOUBLE_PLAN)) r[k] = await runDouble(k, fake(' + json.dumps(flags) + '));\n'
              'console.log(JSON.stringify(r)); })();\n')
        r = subprocess.run([node, '--input-type=module', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_good_window_passes_all_three(self):
        rows = self.run_fake({})
        self.assertEqual(sorted(rows), sorted(ad_regression.DOUBLE_CASES))
        for name, row in rows.items():
            self.assertTrue(row['ok'], (name, row['problems']))
        self.assertEqual((rows['double_watch']['paid'], rows['double_quit']['paid'], rows['double_quit']['thenFree'],
                          rows['double_free']['paid']), (60, 0, 30, 30))

    def test_bad_windows_fail_the_right_case(self):
        for flags, case, words in (
                ({'quitPays': True}, 'double_quit', 'paid 30, expected 0'),          # closed midway still pays
                ({'quitSwallows': True}, 'double_quit', 'not lost'),                 # closing the video ate the 1x
                ({'alwaysAd': True}, 'double_free', 'unticked CLAIM played a video'),  # must watch to claim
                ({'freePays2x': True}, 'double_free', 'expected 30'),
                ({'watchPays1x': True}, 'double_watch', 'expected 60'),
                ({'payOnShow': True}, 'double_quit', 'expected 0'),                  # paid before the video ended
                ({'noBase': True}, 'double_watch', 'return its 1x amount')):
            with self.subTest(flags=flags):
                row = self.run_fake(flags)[case]
                self.assertFalse(row['ok'], row)
                self.assertIn(words, ' '.join(row['problems']))

    def tmp(self):
        t = tempfile.TemporaryDirectory(prefix='ad regression double ')
        self.addCleanup(t.cleanup)
        return Path(t.name)

    def test_adapter_field_is_validated_and_adds_the_cases(self):
        root = self.tmp()
        path = root / 'adapter.json'
        for bad in ('return 1;', {'open': 'return 1;'}, dict(self.GOOD, extra='x'), dict(self.GOOD, claim='')):
            path.write_text(json.dumps({'request': 'grant();', 'double_claim': bad}))
            with self.assertRaisesRegex(ad_regression.RegressionRefused, 'double_claim'):
                ad_regression.load_adapter(path)
        path.write_text(json.dumps({'request': 'grant();', 'double_claim': self.GOOD}))
        adapter = ad_regression.load_adapter(path)
        self.assertEqual(ad_regression.default_cases(adapter), ad_regression.CASES + ad_regression.DOUBLE_CASES)
        self.assertEqual(ad_regression.default_cases({'request': 'grant();'}), ad_regression.CASES)

    def test_judge_requires_the_double_cases_when_asked(self):
        cases = ad_regression.CASES + ad_regression.DOUBLE_CASES
        result = passing_result()
        self.assertFalse(ad_regression.judge(result, cases)[0])
        result['cases'] += [{'case': c, 'ok': True, 'problems': []} for c in ad_regression.DOUBLE_CASES]
        self.assertEqual(ad_regression.judge(result, cases), (True, []))
        result['cases'][-2] = {'case': 'double_quit', 'ok': False, 'problems': ['paid 30, expected 0 (0x of 30)']}
        self.assertIn('double_quit: paid 30', ad_regression.judge(result, cases)[1][0])

    def test_double_case_without_adapter_field_refuses(self):
        root = self.tmp()
        (root / 'game.js').write_text('')
        path = root / 'adapter.json'
        path.write_text(json.dumps({'request': 'grant();'}))
        with patch('ad_regression.environment_problem', return_value=None), \
                patch('ad_regression.find_browser', return_value='ego-browser'):
            with self.assertRaisesRegex(ad_regression.RegressionRefused, 'need adapter "double_claim"'):
                ad_regression.run(root, path, ['double_free'])


if __name__ == '__main__':
    unittest.main()
