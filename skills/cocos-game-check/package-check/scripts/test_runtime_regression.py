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


if __name__ == '__main__':
    unittest.main()
