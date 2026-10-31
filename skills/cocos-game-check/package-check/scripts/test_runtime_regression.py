#!/usr/bin/env python3
"""Runtime regression runner: suite contract, fail-closed wiring and verdict, without a browser.

A fake `ego-browser` (this file run with --fake-browser) reads the entry the runner wrote, fetches
game.js from the real host server, and writes the suite result the test asked for. The browser
suites themselves are proven on real packages (references/runtime-regression.md).
"""
import json
import os
from pathlib import Path
import re
import socket
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.request

import runtime_regression as rr

FAKE = '''
import json, sys, urllib.request
from urllib.parse import unquote, urlparse
code = sys.argv[sys.argv.index('-e') + 1]
entry = unquote(urlparse(json.loads(code[len('await import('):-1])).path)
cfg = json.loads(open(entry, encoding='utf-8').read().split('\\n', 1)[0][len('globalThis.CFG = '):-1])
mode = cfg['adapter'].get('fake_mode', 'pass')
body = urllib.request.urlopen(cfg['base'] + '/game.js').read().decode()
cases = [{'id': 'served', 'passed': body == 'GAME', 'detail': None}]
if mode == 'fail':
    cases.append({'id': 'stall', 'passed': False, 'detail': 'RETRY not shown within 20 s'})
doc = {'suite': cfg['suite'] if mode != 'wrongsuite' else 'other', 'passed': True, 'cases': cases,
       'warnings': ['w1'] if mode == 'warn' else [], 'evidence': {'port': cfg['port']}, 'fatal': None}
if mode != 'none':
    open(cfg['resultFile'], 'w').write(json.dumps(doc))
print('fake done', mode)
'''

SIDECAR = {'name': 'fake', 'about': 'fake suite', 'applies': ['tiktok'], 'needs': ['home'],
           'fields': ['fake_mode'], 'engines': ['2.x', '3.x'], 'timeout_s': 60}


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='runtime regression tests ')
        self.root = Path(self.temp.name)
        self.suites = self.root / 'suites'
        self.suites.mkdir()
        self.sidecar('fake', SIDECAR)
        self.package = self.root / 'pkg'
        self.package.mkdir()
        (self.package / 'game.js').write_text('GAME')
        browser = self.root / 'ego-browser'
        browser.write_text('#!%s\n%s' % (sys.executable, FAKE))
        browser.chmod(browser.stat().st_mode | stat.S_IEXEC)
        self.browser = str(browser)

    def tearDown(self):
        self.temp.cleanup()

    def sidecar(self, name, meta, script=True):
        (self.suites / (name + '.json')).write_text(json.dumps(meta))
        if script:
            (self.suites / (name + '.mjs')).write_text('// fake')

    def adapter(self, data):
        path = self.root / 'adapter.json'
        path.write_text(json.dumps(data))
        return path

    def run_fake(self, adapter, **kw):
        with patch.dict(os.environ, {'EGO_BROWSER': self.browser}):
            return rr.run(self.package, self.adapter(adapter), suites_dir=self.suites, work=self.root / 'work', **kw)


class Contract(Base):
    def test_real_sidecars_are_valid(self):
        catalog = rr.load_suites()
        self.assertIn('startup', catalog)
        for meta in catalog.values():
            self.assertTrue(meta['script'].is_file())

    def test_bad_sidecars_refuse(self):
        for bad in ({**SIDECAR, 'name': 'other'}, {**SIDECAR, 'applies': []}, {**SIDECAR, 'applies': ['sometimes']},
                    {**SIDECAR, 'engines': ['1.x']}, {**SIDECAR, 'surprise': 1}, {**SIDECAR, 'timeout_s': 0}):
            self.sidecar('fake', bad)
            with self.assertRaises(rr.RuntimeRefused):
                rr.load_suites(self.suites)
        self.sidecar('fake', SIDECAR)
        (self.suites / 'fake.mjs').unlink()
        with self.assertRaisesRegex(rr.RuntimeRefused, 'missing script'):
            rr.load_suites(self.suites)

    def test_required_suites_predicates_and_engine(self):
        self.sidecar('ads', {**SIDECAR, 'name': 'ads', 'applies': ['rewarded_ads'], 'needs': []})
        self.sidecar('opt', {**SIDECAR, 'name': 'opt', 'applies': ['adapter:fake_mode'], 'needs': []})
        self.sidecar('only3', {**SIDECAR, 'name': 'only3', 'engines': ['3.x']})
        self.sidecar('home', {**SIDECAR, 'name': 'home', 'applies': ['remake_home']})
        catalog = rr.load_suites(self.suites)
        plain = {'game.js': b'x'}
        ads = {'game.js': b'x', 'assets/main/index.js': b'tt.createRewardedVideoAd({})'}
        v3 = {'game.js': b'x', 'src/system.bundle.js': b''}
        self.assertEqual(rr.required_suites(plain, {}, catalog), ['fake'])
        self.assertEqual(rr.required_suites(ads, {}, catalog), ['ads', 'fake'])
        self.assertEqual(rr.required_suites(plain, {'fake_mode': 'x', 'remake_home': True}, catalog), ['fake', 'home', 'opt'])
        self.assertEqual(rr.required_suites(v3, {}, catalog), ['fake', 'only3'])
        self.assertEqual(rr.required_suites({'other.js': b''}, {}, catalog), [])
        self.assertEqual(rr.detect_engine(plain, {'engine': '3.x'}), '3.x')

    def test_adapter_required_and_keys_checked(self):
        catalog = rr.load_suites(self.suites)
        with self.assertRaisesRegex(rr.RuntimeRefused, 'runtime regression required'):
            rr.load_adapter(None, catalog)
        with self.assertRaisesRegex(rr.RuntimeRefused, 'unknown keys: surprise'):
            rr.load_adapter(self.adapter({'request': 'grant();', 'surprise': 1}), catalog)
        with self.assertRaises(rr.RuntimeRefused):
            rr.load_adapter(self.adapter({'home': 3}), catalog)
        # v7.4 ad keys, core keys and a field a suite registered are all accepted.
        # v7.8 (Saul 10-31, W100): the ad regression's double_claim field is a known key of the shared adapter
        rr.load_adapter(self.adapter({'request': 'grant();', 'double_claim': {'open_js': 'open();'}}), catalog)
        ok = rr.load_adapter(self.adapter({'request': 'grant();', 'home': 'return true', 'fake_mode': 'pass'}), catalog)
        self.assertEqual(ok['fake_mode'], 'pass')

    def test_ad_regression_accepts_runtime_keys(self):
        # R1: one adapter file serves both regressions; unknown keys are still refused.
        import ad_regression
        path = self.adapter({'request': 'grant();', 'home': 'return true', 'enter_level': 'return true'})
        self.assertEqual(ad_regression.load_adapter(path)['home'], 'return true')
        with self.assertRaisesRegex(ad_regression.RegressionRefused, 'unknown keys: surprise'):
            ad_regression.load_adapter(self.adapter({'request': 'grant();', 'surprise': 1}))
        with patch.object(rr, 'load_suites', side_effect=rr.RuntimeRefused('broken catalog')):
            path = self.adapter({'request': 'grant();', 'home': 'return true'})
            with self.assertRaisesRegex(ad_regression.RegressionRefused, 'unknown keys: home'):
                ad_regression.load_adapter(path)

    def test_verdict(self):
        good = {'suite': 's', 'passed': True, 'cases': [{'id': 'a', 'passed': True}]}
        self.assertEqual(rr.judge(good, 's'), (True, []))
        self.assertFalse(rr.judge(None, 's')[0])
        self.assertFalse(rr.judge({**good, 'cases': []}, 's')[0])
        self.assertFalse(rr.judge({**good, 'fatal': 'boom'}, 's')[0])
        self.assertFalse(rr.judge({**good, 'suite': 't'}, 's')[0])
        self.assertFalse(rr.judge({**good, 'passed': False}, 's')[0])
        # The runner never trusts the suite's own passed flag.
        bad = {'suite': 's', 'passed': True, 'cases': [{'id': 'a', 'passed': True}, {'id': 'b', 'passed': 'yes'}]}
        passed, problems = rr.judge(bad, 's')
        self.assertFalse(passed)
        self.assertIn('s/b', problems[0])


class FailClosed(Base):
    def test_no_browser_refuses(self):
        with patch.dict(os.environ, {'EGO_BROWSER': ''}), patch('runtime_regression._which', return_value=None):
            with self.assertRaisesRegex(rr.RuntimeRefused, 'needs the Ego browser'):
                rr.run(self.package, self.adapter({'home': 'return true'}), suites_dir=self.suites)

    def test_missing_needed_field_refuses(self):
        with self.assertRaisesRegex(rr.RuntimeRefused, r'fake needs adapter field\(s\) home'):
            self.run_fake({'request': 'grant();'})

    def test_no_game_js_or_no_suite_refuses(self):
        (self.package / 'game.js').unlink()
        with self.assertRaisesRegex(rr.RuntimeRefused, 'no game.js'):
            self.run_fake({'home': 'return true'})

    def test_unknown_suite_refuses(self):
        with self.assertRaisesRegex(rr.RuntimeRefused, 'unknown runtime suites: nope'):
            self.run_fake({'home': 'return true'}, suites=['nope'])

    def test_pass_serves_package_logs_gets_and_stops_server(self):
        summary = self.run_fake({'home': 'return true', 'fake_mode': 'warn'})
        self.assertTrue(summary['passed'])
        self.assertEqual(summary['required'], ['fake'])
        self.assertEqual(summary['warnings'], ['w1'])
        row = summary['suites'][0]
        self.assertEqual(row['cases'][0], {'id': 'served', 'passed': True, 'detail': None})
        log = (self.root / 'work' / 'fake' / 'host-log.jsonl').read_text()
        self.assertIn('{"kind": "http-get", "data": {"path": "/game.js", "status": 200, "method": "GET"}}', log)
        entry = (self.root / 'work' / 'fake' / 'entry.mjs').read_text()
        self.assertIn('"hostQuery": "mouse=1&run=fake"', entry)
        port = row['evidence']['port']
        with self.assertRaises(OSError):
            socket.create_connection(('127.0.0.1', port), timeout=0.5).close()

    def test_failed_case_refuses_with_summary(self):
        with self.assertRaisesRegex(rr.RuntimeRefused, 'fake/stall: RETRY not shown') as ctx:
            self.run_fake({'home': 'return true', 'fake_mode': 'fail'})
        self.assertFalse(ctx.exception.summary['passed'])

    def test_no_result_or_wrong_suite_refuses(self):
        with self.assertRaisesRegex(rr.RuntimeRefused, 'produced no result'):
            self.run_fake({'home': 'return true', 'fake_mode': 'none'})
        with self.assertRaisesRegex(rr.RuntimeRefused, "result names suite 'other'"):
            self.run_fake({'home': 'return true', 'fake_mode': 'wrongsuite'})

    def test_cli_writes_out_and_exit_code(self):
        out = self.root / 'out.json'
        with patch.dict(os.environ, {'EGO_BROWSER': self.browser}), patch('runtime_regression.SUITES_DIR', self.suites):
            code = rr.main(['run', '--package', str(self.package), '--adapter',
                            str(self.adapter({'home': 'return true', 'fake_mode': 'fail'})), '--out', str(out)])
        self.assertEqual(code, 1)
        doc = json.loads(out.read_text())
        self.assertFalse(doc['passed'])
        self.assertIn('fake/stall', doc['error'])


class DeadShellWiring(Base):
    """v7.8 (总表 E1 补): the dead_shell suite is mandatory for every 2.x TikTok package and gets the game's policy."""

    def test_dead_shell_is_required_for_tiktok_2x(self):
        catalog = rr.load_suites()
        meta = catalog['dead_shell']
        self.assertEqual((meta['applies'], meta['needs'], meta['engines']), (['tiktok'], ['home'], ['2.x']))
        self.assertTrue({'play', 'enter_level', 'in_level'} <= set(meta['fields']))
        self.assertIn('dead_shell', rr.required_suites({'game.js': b'x'}, {}, catalog))
        self.assertNotIn('dead_shell', rr.required_suites({'game.js': b'x', 'src/system.bundle.js': b''}, {}, catalog))

    def test_policy_reaches_the_suite(self):
        summary = self.run_fake({'home': 'return true'}, policy='legacy')
        self.assertEqual((summary['policy'], summary['policy_reason']), ('legacy', 'given by the caller'))
        self.assertIn('"policy": "legacy"', (self.root / 'work' / 'fake' / 'entry.mjs').read_text())
        summary = self.run_fake({'home': 'return true'})
        self.assertEqual(summary['policy'], 'new')                  # judged from the bytes; unlisted = new
        self.assertTrue(summary['policy_reason'].startswith(('judged from the package', 'policy decision failed')))
        with self.assertRaises(rr.RuntimeRefused):
            self.run_fake({'home': 'return true'}, policy='old')


ENGINE2 = b'cc.internal={inputManager:{getTouchesByEvent:function(e){return []},registerSystemEvent:function(){}}};'


class Environment(Base):
    """v7.8 (总表 A6 补): 「环境不完整」 is reported apart from 「包不通过」."""

    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(rr.SHARED))
        import audit_upload_startup
        self.aus = audit_upload_startup

    def cocos2(self, touch=False):
        (self.package / 'cocos').mkdir(exist_ok=True)
        (self.package / 'cocos' / 'cocos2d-js-min.js').write_bytes(ENGINE2)
        game = "require('adapter-min.js');require('cocos/cocos2d-js-min.js');"
        if touch:
            game += "require('./touch-coordinates').install(cc);"
            (self.package / 'touch-coordinates.js').write_text('module.exports={install(){}};')
        (self.package / 'game.js').write_text(game)

    def probe(self, errors=None, raises=None):
        if raises:
            return patch.object(self.aus, 'audit_files', side_effect=raises)
        return patch.object(self.aus, 'audit_files', return_value={'errors': errors or []})

    def test_touch_problem_follows_the_upload_touch_probe(self):
        self.assertIsNone(rr.touch_problem({'game.js': b'GAME'}))           # not a Cocos package: no probe
        self.cocos2()
        files = rr.package_files(self.package)
        bad = 'Cocos2 native touch coordinates rejected: SDK screenX/screenY must reach finite engine coordinates'
        with self.probe([bad, 'unrelated startup error']):
            msg = rr.touch_problem(files)
        self.assertTrue(msg.startswith('环境不完整：'), msg)
        self.assertIn(bad, msg)
        self.assertIn('touch-coordinates.js', msg)
        self.assertIn('not installed', msg)
        with self.probe(['unrelated startup error']):                          # another working touch fix
            self.assertIsNone(rr.touch_problem(files))
        with self.probe(raises=ValueError('Node.js required')):                # probe cannot run: kit part decides
            self.assertIn('could not run', rr.touch_problem(files))
        self.cocos2(touch=True)
        with self.probe(raises=ValueError('Node.js required')):
            self.assertIsNone(rr.touch_problem(rr.package_files(self.package)))
        three = {'game.js': b"require('./web-adapter');", 'cocos-js/cc.js': b'', 'web-adapter.js': b''}
        with self.probe(['Cocos3 native touch coordinates rejected: x']):
            self.assertIn('tiktok-touch-3x.js', rr.touch_problem(three))

    def test_run_reports_environment_before_any_suite_or_browser(self):
        self.cocos2()
        with self.probe(['Cocos2 native touch coordinates rejected']), patch.dict(os.environ, {'EGO_BROWSER': ''}), \
                patch('runtime_regression._which', return_value=None):
            with self.assertRaises(rr.EnvironmentIncomplete) as ctx:
                rr.run(self.package, self.adapter({'home': 'return true'}), suites_dir=self.suites)
        self.assertIsInstance(ctx.exception, rr.RuntimeRefused)               # still a refusal for the writers
        self.assertTrue(str(ctx.exception).startswith('环境不完整：'))

    def zipped(self):
        import zipfile
        archive = self.root / 'Game.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('game.js', 'GAME')
        return archive

    def cli(self, package, adapter):
        out = self.root / 'cli.json'
        with patch.dict(os.environ, {'EGO_BROWSER': self.browser}), patch('runtime_regression.SUITES_DIR', self.suites):
            code = rr.main(['run', '--package', str(package), '--adapter', str(self.adapter(adapter)), '--out', str(out)])
        return code, json.loads(out.read_text())

    def test_cli_zip_without_writer_receipt_is_environment_not_failure(self):
        code, doc = self.cli(self.zipped(), {'home': 'return true'})
        self.assertEqual(code, 2)
        self.assertEqual(doc['status'], 'environment_incomplete')
        self.assertTrue(doc['verdict'].startswith('环境不完整：'))
        self.assertIn('no writer receipt', doc['error'])
        self.assertNotIn('suites', doc)                                          # nothing ran

    def test_cli_zip_with_receipt_and_directory_run(self):
        archive = self.zipped()
        import verify_native_zip
        with patch.object(verify_native_zip, 'receipt_status', return_value={'entry': 'official'}):
            self.assertIsNone(rr.receipt_problem(archive))
            code, doc = self.cli(archive, {'home': 'return true'})
        self.assertEqual((code, doc['verdict']), (0, '通过'))
        code, doc = self.cli(self.package, {'home': 'return true', 'fake_mode': 'fail'})    # a folder: no receipt asked
        self.assertEqual((code, doc['verdict']), (1, '包不通过'))

    def test_writer_call_never_asks_for_a_receipt(self):
        with patch('runtime_regression.receipt_problem', side_effect=AssertionError('asked for a receipt')):
            self.assertTrue(self.run_fake({'home': 'return true'})['passed'])


# v7.8 (总表 B30): a fake browser for suites without a package host ("host": "none"): reads CFG.trialUrl / board.
FAKE_NOHOST = '''
import json, sys
from urllib.parse import unquote, urlparse
code = sys.argv[sys.argv.index('-e') + 1]
entry = unquote(urlparse(json.loads(code[len('await import('):-1])).path)
cfg = json.loads(open(entry, encoding='utf-8').read().split('\\n', 1)[0][len('globalThis.CFG = '):-1])
mode = (cfg['adapter'].get('trial') or {}).get('mode', 'pass')
cases = [{'id': 'ad_window_visible', 'passed': mode != 'hidden', 'detail': {'url': cfg['trialUrl'], 'base': cfg['base'], 'board': cfg['board']}}]
ev = {'notRun': 'no ad entry known' if mode == 'notrun' else None}
open(cfg['resultFile'], 'w').write(json.dumps({'suite': cfg['suite'], 'passed': True, 'cases': cases, 'warnings': [], 'evidence': ev, 'fatal': None}))
'''


class B30Wiring(Base):
    """v7.8 (总表 B30, 22.6 q2): layout_state (D) and button_sweep (E) run for every TikTok package (2.x and 3.x),
    ad_entries (B) only with adapter.ad_entries, trial_link (F) only with a trial link; the summary says what did not
    run and why; the board reaches the suites; the 2.x and 3.x hosts carry the same device switches."""

    def test_sidecars_and_required(self):
        catalog = rr.load_suites()
        for name in ('layout_state', 'button_sweep'):
            self.assertEqual((catalog[name]['applies'], catalog[name]['needs'], catalog[name]['engines']), (['tiktok'], [], ['2.x', '3.x']))
        self.assertEqual((catalog['ad_entries']['applies'], catalog['ad_entries']['needs']), (['adapter:ad_entries'], ['ad_entries']))
        self.assertEqual((catalog['trial_link']['applies'], catalog['trial_link']['host']), (['trial_url'], 'none'))
        v2, v3 = {'game.js': b'x'}, {'game.js': b'x', 'src/system.bundle.js': b''}
        for files in (v2, v3):
            req = rr.required_suites(files, {}, catalog)
            self.assertTrue({'layout_state', 'button_sweep'} <= set(req), req)
            self.assertNotIn('ad_entries', req)
            self.assertNotIn('trial_link', req)
        self.assertIn('ad_entries', rr.required_suites(v2, {'ad_entries': []}, catalog))
        self.assertIn('trial_link', rr.required_suites(v2, {}, catalog, trial_url='http://127.0.0.1:1/'))
        skipped = {r['suite']: r['reason'] for r in rr.not_run(v3, {}, rr.required_suites(v3, {}, catalog), catalog)}
        self.assertIn('adapter has no "ad_entries"', skipped['ad_entries'])
        self.assertIn('no trial link given', skipped['trial_link'])
        self.assertIn('Cocos 3.x not supported', skipped['dead_shell'])
        # every new field is an accepted adapter key (one adapter file for the ad and runtime regressions)
        keys = rr.adapter_keys(catalog)
        for k in ('layout_states', 'home_scene', 'settings', 'platform_entries', 'after_home_js', 'sweep_skip', 'ad_entries', 'trial'):
            self.assertIn(k, keys)

    def test_board_and_not_run_reach_the_summary(self):
        summary = self.run_fake({'home': 'return true'}, board='localize')
        self.assertEqual(summary['board'], 'localize')
        self.assertIn('"board": "localize"', (self.root / 'work' / 'fake' / 'entry.mjs').read_text())
        self.assertEqual(summary['not_run'], [])
        self.assertIsNone(summary['startup_measured'])
        with self.assertRaisesRegex(rr.RuntimeRefused, 'board must be remake or localize'):
            self.run_fake({'home': 'return true'}, board='english')
        self.sidecar('extra', {**SIDECAR, 'name': 'extra', 'applies': ['adapter:ad_entries']})
        summary = self.run_fake({'home': 'return true'})
        self.assertEqual(summary['not_run'], [{'suite': 'extra', 'reason': 'adapter has no "ad_entries"'}])

    def nohost(self, mode):
        browser = self.root / 'ego-nohost'
        browser.write_text('#!%s\n%s' % (sys.executable, FAKE_NOHOST))
        browser.chmod(browser.stat().st_mode | stat.S_IEXEC)
        self.sidecar('trial_link', {'name': 'trial_link', 'applies': ['trial_url'], 'fields': ['trial'], 'host': 'none', 'timeout_s': 60})
        with patch.dict(os.environ, {'EGO_BROWSER': str(browser)}), patch('runtime_regression._free_port', side_effect=AssertionError('served')):
            return rr.trial_smoke('http://127.0.0.1:5/', self.adapter({'trial': {'mode': mode}}), suites_dir=self.suites, work=self.root / 'w')

    def test_trial_smoke_runs_without_a_package_server(self):
        summary = self.nohost('pass')
        self.assertTrue(summary['passed'])
        self.assertIsNone(summary['not_run'])
        self.assertEqual(summary['cases'][0]['detail'], {'url': 'http://127.0.0.1:5/', 'base': None, 'board': None})
        self.assertEqual(self.nohost('notrun')['not_run'], 'no ad entry known')
        with self.assertRaisesRegex(rr.RuntimeRefused, 'trial smoke failed: trial_link/ad_window_visible'):
            self.nohost('hidden')
        with self.assertRaisesRegex(rr.RuntimeRefused, 'only a local trial link'):
            rr.trial_smoke('https://example.com/', None, suites_dir=self.suites)

    def test_check_package_passes_the_board(self):
        import check_package
        seen = {}
        with patch.object(rr, 'run', side_effect=lambda *a, **k: seen.update(k) or {'id': 'runtime_regression'}):
            check_package.runtime_gate({'game.js': b'x'}, self.package, self.adapter({'home': 'return true'}), policy='new', board='remake')
        self.assertEqual((seen['policy'], seen['board']), ('new', 'remake'))
        with patch.object(rr, 'run', side_effect=lambda *a, **k: seen.update(k) or {}):
            check_package.runtime_gate({'game.js': b'x'}, self.package, self.adapter({'home': 'return true'}), board='other')
        self.assertIsNone(seen['board'])

    def test_hosts_share_the_device_switches(self):
        h2 = (rr.HOST2 / 'host.js').read_text(encoding='utf-8')
        h3 = (rr.HOST3 / 'host.js').read_text(encoding='utf-8')
        for text in (h2, h3):
            for needle in ("iphone14: { model: 'iPhone 14', W: 390, H: 844, pr: 3, sb: 47, cap: { left: 293, top: 51, right: 380, bottom: 83 }, safeBottom: 810 }",
                           "Q.get('capsule') === 'px' ? DEV.pr : 1", "gateLog('capsule-rect', r)", "gateLog('ad-create', unit)",
                           "gateLog('toast'", 'window.__gateNow', "beacon('scene-loading'"):
                self.assertIn(needle, text)
        self.assertIn("Q.get('reset') === '1'", h3)
        self.assertIn("Q.get('ad')", h3)


if __name__ == '__main__':
    unittest.main()
