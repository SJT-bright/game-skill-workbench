#!/usr/bin/env python3
"""The two read-only AST workers expose an explicit help/input/result protocol."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

HERE = Path(__file__).resolve().parent
WORKERS = ('scan_tiktok_host_refs.cjs', 'scan_free_claim_ad_lock.cjs')


@unittest.skipUnless(shutil.which('node'), 'Node.js is required for the AST workers')
class AstWorkerCli(unittest.TestCase):
    def invoke(self, name, body=None, *args):
        kwargs = {'input': body} if body is not None else {'stdin': subprocess.DEVNULL}
        return subprocess.run(['node', str(HERE / name), *args],
                              capture_output=True, text=True, timeout=20, **kwargs)

    def assert_not_run(self, result, reason=None):
        self.assertEqual(result.returncode, 2, result)
        self.assertEqual(result.stderr, '')
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'not_run')
        self.assertEqual(report['checked'], 0)
        if reason is not None:
            self.assertEqual(report['reason'], reason)
        self.assertTrue(report['reason'])
        self.assertNotIn('findings', report)  # no partial batch can look like a zero-hit check
        return report

    def test_help_exits_success_without_reading_input(self):
        for name in WORKERS:
            with self.subTest(worker=name):
                result = self.invoke(name, None, '--help')
                self.assertEqual(result.returncode, 0, result)
                self.assertEqual(result.stderr, '')
                self.assertIn('Usage: node ' + name, result.stdout)
                self.assertIn('{files:[{file,code}]}', result.stdout)

    def test_eof_empty_and_whitespace_are_input_required(self):
        for name in WORKERS:
            for body in (None, '', ' \n\t'):
                with self.subTest(worker=name, body=body):
                    self.assert_not_run(self.invoke(name, body), 'input required')

    def test_missing_files_or_source_are_input_required(self):
        missing = (None, {}, [], {'files': []}, {'files': [{}]},
                   {'files': [{'file': 'entry.js'}]},
                   {'files': [{'file': 'entry.js', 'code': ' \n'}]},
                   {'files': [{'file': ' ', 'code': 'boot();'}]})
        for name in WORKERS:
            for value in missing:
                with self.subTest(worker=name, value=value):
                    self.assert_not_run(self.invoke(name, json.dumps(value)), 'input required')

    def test_invalid_json_is_not_a_checked_empty_batch(self):
        for name in WORKERS:
            with self.subTest(worker=name):
                report = self.assert_not_run(self.invoke(name, '{"files":'))
                self.assertTrue(report['reason'].startswith('invalid JSON input:'))

    def test_invalid_javascript_does_not_count_a_partial_batch(self):
        body = json.dumps({'files': [{'file': 'valid.js', 'code': 'boot();'},
                                     {'file': 'broken.js', 'code': 'function ('}]})
        for name in WORKERS:
            with self.subTest(worker=name):
                report = self.assert_not_run(self.invoke(name, body))
                self.assertTrue(report['reason'].startswith('JavaScript parse failed:'))

    def test_valid_source_is_actually_checked(self):
        body = json.dumps({'files': [{'file': 'entry.js', 'code': 'var text = "wx.login()";'}]})
        for name in WORKERS:
            with self.subTest(worker=name):
                result = self.invoke(name, body)
                self.assertEqual(result.returncode, 0, result)
                self.assertEqual(result.stderr, '')
                report = json.loads(result.stdout)
                self.assertEqual(report['status'], 'checked')
                self.assertEqual(report['checked'], 1)
                self.assertEqual(report['findings'], [])

    def test_real_findings_retain_worker_semantics(self):
        from test_free_claim_ad_lock import SOURCE
        for name, code in ((WORKERS[0], 'wx.login();'), (WORKERS[1], SOURCE)):
            with self.subTest(worker=name):
                result = self.invoke(name, json.dumps({'files': [{'file': 'entry.js', 'code': code}]}))
                self.assertEqual(result.returncode, 0, result)
                report = json.loads(result.stdout)
                self.assertEqual(report['status'], 'risk_detected')
                self.assertEqual(report['checked'], 1)
                self.assertEqual(len(report['findings']), 1)
                self.assertEqual(report['findings'][0]['file'], 'entry.js')
                if name == WORKERS[1]:
                    self.assertTrue(report['requires_runtime_verification'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
