#!/usr/bin/env python3
"""简化.11.14 R4D: a test entry reports 通过 only after its whole case list ran (喵咪小吃铺 ran the first round only
and closed). runtime_regression.py --suites / ad_regression.py --cases subsets are 「没跑完」 (exit 3), listing what
did not run. R4D_OLD_TREE=<untouched base tree> also runs the old runtime_regression.py: the same half run said 通过.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_r4d_case_list_complete.py   (seconds, fake browser)"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ad_regression as ar  # noqa: E402
import runtime_regression as rr  # noqa: E402
from test_runtime_regression import Base, SIDECAR  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RuntimeHalfRun(Base):
    def setUp(self):
        super().setUp()
        self.sidecar('fake2', dict(SIDECAR, name='fake2'))
        self.feedback = tempfile.TemporaryDirectory(prefix='r4d-feedback-')

    def tearDown(self):
        self.feedback.cleanup()
        super().tearDown()

    def cli(self, mod, suites):
        argv = ['run', '--package', str(self.package), '--adapter', str(self.adapter({'home': 'return true'})), '--work', str(self.root / 'w')]
        if suites:
            argv += ['--suites', suites]
        err = io.StringIO()
        with patch.dict(os.environ, {'EGO_BROWSER': self.browser, 'COCOS_SKILL_FEEDBACK_DIR': self.feedback.name}), \
                patch.object(mod, 'SUITES_DIR', self.suites), contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(err):
            code = mod.main(argv)
        return code, json.loads(out.getvalue().splitlines()[0]), err.getvalue()

    def test_library_summary_lists_what_did_not_run(self):
        s = self.run_fake({'home': 'return true'}, suites=['fake'])
        self.assertEqual((s['complete'], s['planned_not_run']), (False, ['fake2']))
        s = self.run_fake({'home': 'return true'})
        self.assertEqual((s['complete'], s['planned_not_run']), (True, []))

    def test_half_run_is_not_finished(self):
        code, out, err = self.cli(rr, 'fake')
        self.assertEqual(code, rr.INCOMPLETE_EXIT)
        self.assertFalse(out['passed'])
        self.assertEqual(out['planned_not_run'], ['fake2'])
        self.assertIn('结论: 没跑完', err)
        self.assertIn('fake2', err)

    def test_full_run_passes(self):
        code, out, err = self.cli(rr, None)
        self.assertEqual(code, 0)
        self.assertIn('结论: 通过', err)

    @unittest.skipUnless(os.environ.get('R4D_OLD_TREE'), 'set R4D_OLD_TREE to the untouched base tree')
    def test_old_half_run_said_passed(self):
        old = load(Path(os.environ['R4D_OLD_TREE']) / 'cocos-game-check/package-check/scripts/runtime_regression.py',
                   'runtime_regression_old')
        code, out, err = self.cli(old, 'fake')
        self.assertEqual(code, 0)                       # the bug: half the case list, 通过
        self.assertIn('结论: 通过', err)


class AdHalfRun(unittest.TestCase):
    def test_planned_not_run(self):
        self.assertEqual(ar.planned_not_run({}, ar.CASES), [])
        self.assertEqual(ar.planned_not_run({}, ar.CASES[:3]), ar.CASES[3:])

    def test_finish(self):
        s = {'passed': True, 'planned_not_run': ar.CASES[5:]}
        self.assertEqual(ar.finish(s, 0), ar.INCOMPLETE_EXIT)
        self.assertFalse(s['passed'])
        self.assertTrue(s['verdict'].startswith('没跑完'))
        self.assertIn(ar.CASES[5], s['verdict'])
        s = {'passed': True, 'planned_not_run': []}
        self.assertEqual((ar.finish(s, 0), s['verdict']), (0, '通过'))
        s = {'passed': False, 'planned_not_run': ar.CASES[5:]}
        self.assertEqual((ar.finish(s, 1), s['verdict']), (1, '包不通过'))   # a failure stays a failure

    def test_run_records_the_case_list(self):
        src = (HERE / 'ad_regression.py').read_text(encoding='utf-8')
        self.assertIn("summary['planned_not_run'] = planned_not_run(adapter, cases)", src)
        self.assertIn('code = finish(summary, code)', src)


if __name__ == '__main__':
    unittest.main(verbosity=2)
