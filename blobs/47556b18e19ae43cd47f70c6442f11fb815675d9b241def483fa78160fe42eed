#!/usr/bin/env python3
"""v7.8 W97: make_tiktok_zip.py (the remake games' writer) runs the rewarded-ad and runtime regressions too.

Before v7.8 only build_checked_zip ran them (through check_package.check()); make_tiktok_zip wrote the ZIP without
startup / network / dead_shell / layout_state / button_sweep / ad_entries / popin / frame_rate and without the rewarded-
ad regression. Now check_package.writer_regressions runs both on the extraction of the ZIP about to be published, with
the finalize policy and the board: a new game is refused, a game on the frozen legacy list gets warnings.

Synthetic fixtures: every earlier writer gate is stubbed (their own tests cover them), the regression gates themselves
are real except where a test replaces runtime_regression.run / ad_regression.run with a pass or a failure.
Run: python3 test_writer_regressions.py
"""
import contextlib
import hashlib
import inspect
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
CHECK = HERE.parents[1] / 'cocos-game-check' / 'package-check' / 'scripts'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(CHECK))
import make_tiktok_zip as M  # noqa: E402
import check_package as C  # noqa: E402
import runtime_regression as RR  # noqa: E402
import ad_regression as AR  # noqa: E402
import verify_native_zip as V  # noqa: E402

APP = 'ttfixture000000001'
REAL_RUN = subprocess.run
FAKED = ('run_reward_storage_probe.py', 'check_known_issues.py', 'audit_runtime_coverage.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fake_subprocess(cmd, *args, **kwargs):
    """The writer's three earlier subprocess gates pass; everything else (the regressions) runs for real."""
    if isinstance(cmd, list) and any(str(c).endswith(FAKED) for c in cmd):
        return subprocess.CompletedProcess(cmd, 0, '{"passed": true}\n', '')
    return REAL_RUN(cmd, *args, **kwargs)


def fake_verify(path, app_id=None, **kwargs):
    with zipfile.ZipFile(path) as z:
        digests = {i.filename: sha(z.read(i)) for i in z.infolist() if not i.is_dir()}
    return {'sha256': sha(Path(path).read_bytes()), 'file_sha256': digests, 'files': len(digests),
            'not_verified': [], 'warnings': []}


class WriterRegressions(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix='W97 writer regressions '))
        self.addCleanup(shutil.rmtree, self.d, True)
        self.native = self.d / 'native'
        self.native.mkdir()
        self.files = {'game.js': b'console.log("fixture game");\n', 'game.json': b'{"deviceOrientation": "portrait"}',
                      'project.config.json': json.dumps({'appid': APP}).encode()}
        for name, data in self.files.items():
            (self.native / name).write_bytes(data)
        self.project = self.d / 'project'
        (self.project / 'assets').mkdir(parents=True)
        (self.project / 'docs' / 'test').mkdir(parents=True)
        (self.project / 'docs' / 'test' / 'runtime-coverage.json').write_text('{}')
        self.review = self.d / 'review.json'
        self.review.write_text('{}')
        self.out = self.d / 'out' / 'Fixture_TikTok_v1.zip'
        env = mock.patch.dict(os.environ, {AR.ENV_ADAPTER: '', RR.ENV_ADAPTER: ''})
        env.start()
        self.addCleanup(env.stop)

    def stubs(self, policy):
        sizes = {n: len(d) for n, d in self.files.items()}
        info = {'independent': {}, 'normal': {}, 'total': sum(sizes.values()), 'main': sum(sizes.values()),
                'appId': APP, 'package_gates': {'blocks': [], 'warnings': [], 'gates': [], 'policy': policy},
                'pre_home_bytes': {'bytes': 1}}
        record = {'policy': policy, 'kit_version': 'fixture', 'steps': [], 'blocks': [], 'warnings': [], 'table': []}
        import audit_native_resource_paths, audit_packed_assets, package_obligations, audit_final_package_startup
        import project_qa
        try:
            import delivery_folder
            tidy = [mock.patch.object(delivery_folder, 'tidy', return_value={}),
                    mock.patch.object(delivery_folder, 'describe', return_value=[])]
        except ImportError:             # v7.7.5 has no delivery_folder: the comparison run still reaches the regressions
            tidy = []
        return tidy + [
            mock.patch.object(M, 'finalize_for_writer', return_value=(record, {'writer': True}, [])),
            mock.patch.object(audit_native_resource_paths, 'audit', return_value={'status': 'pass', 'errors': []}),
            mock.patch.object(M, 'native_problems', return_value=([], sizes, info)),
            mock.patch.object(audit_packed_assets, 'audit', return_value={'passed': True, 'errors': []}),
            mock.patch.object(package_obligations, 'verify', return_value={'fixture': True}),
            mock.patch.object(package_obligations, 'publication_guard', return_value=contextlib.nullcontext()),
            mock.patch.object(audit_final_package_startup, 'audit_final_startup', return_value={}),
            mock.patch.object(project_qa, 'review_policy', return_value=None),
            mock.patch.object(subprocess, 'run', side_effect=fake_subprocess),
            mock.patch.object(V, 'verify', side_effect=fake_verify),
            mock.patch.object(V, 'make_receipt', return_value={'schema': 'fixture'}),
            mock.patch.object(V, 'receipt_status', return_value={'entry': 'official'}),
            mock.patch.object(M, 'finalize_report', return_value={'table_markdown': ''}),
        ]

    def make(self, policy='new', adapter=None, extra=()):
        argv = ['make_tiktok_zip.py', '--native', self.native, '--app-id', APP, '--out', self.out, '--project',
                self.project, '--web', self.native, '--build-tag', 'v1', '--review', self.review, '--board', 'remake',
                '--keep-old-packages']
        if adapter:
            argv += ['--ad-regression', adapter]
        err = io.StringIO()
        with contextlib.ExitStack() as stack:
            for patch in list(self.stubs(policy)) + list(extra):
                stack.enter_context(patch)
            stack.enter_context(mock.patch.object(sys, 'argv', [str(x) for x in argv]))
            stack.enter_context(contextlib.redirect_stderr(err))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            code = M.main()
        report = self.out.with_name(self.out.stem + '.report.json')
        return code, err.getvalue(), json.loads(report.read_text()) if report.is_file() else None

    def adapter(self, data=None):
        path = self.d / 'qa-ad-regression.json'
        path.write_text(json.dumps(data or {}))
        return path

    def passing_runtime(self, seen):
        def run(folder, adapter, names, policy=None, board=None, **kw):
            folder = Path(folder)
            seen.append({'files': {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*')
                                   if p.is_file()}, 'adapter': adapter, 'names': names, 'policy': policy,
                         'board': board})
            return {'id': 'runtime_regression', 'passed': True, 'required': names, 'policy': policy, 'board': board,
                    'warnings': ['fixture warning'], 'startup_measured': {'MiB': 1.0}, 'suites': []}
        return mock.patch.object(RR, 'run', side_effect=run)

    # ---- new game

    def test_new_game_without_adapter_refused_no_zip(self):
        code, err, report = self.make('new')
        self.assertEqual(code, 1, err)
        self.assertIn('runtime regression required', err)
        self.assertIn('qa/ad-regression.json', err)
        self.assertIn('policy new', err)
        self.assertFalse(self.out.exists())
        self.assertIsNone(report)
        self.assertFalse(V.receipt_path(self.out).exists())

    def test_new_game_failed_suite_refused(self):
        def fail(*a, **kw):
            error = RR.RuntimeRefused('runtime regression failed: button_sweep/home: PLAY did nothing')
            error.summary = {'id': 'runtime_regression', 'passed': False, 'problems': ['button_sweep/home']}
            raise error
        code, err, report = self.make('new', self.adapter(), [mock.patch.object(RR, 'run', side_effect=fail)])
        self.assertEqual(code, 1, err)
        self.assertIn('button_sweep/home: PLAY did nothing', err)
        self.assertFalse(self.out.exists())

    def test_new_game_without_browser_refused(self):
        code, err, _ = self.make('new', self.adapter(),
                                 [mock.patch.dict(os.environ, {RR.ENV_BROWSER: str(self.d / 'no-ego-browser')})])
        self.assertEqual(code, 1, err)
        self.assertIn('needs the Ego browser', err)
        self.assertFalse(self.out.exists())

    def test_new_game_incomplete_environment_refused(self):
        def incomplete(*a, **kw):
            raise RR.EnvironmentIncomplete(RR.ENV_PREFIX + 'TikTok touches do not reach the engine')
        code, err, _ = self.make('new', self.adapter(), [mock.patch.object(RR, 'run', side_effect=incomplete)])
        self.assertEqual(code, 1, err)
        self.assertIn(RR.ENV_PREFIX, err)
        self.assertFalse(self.out.exists())

    def test_new_game_rewarded_ad_regression_failure_refused(self):
        self.files['game.js'] += b'tt.createRewardedVideoAd({adUnitId: "x"});\n'
        (self.native / 'game.js').write_bytes(self.files['game.js'])
        seen = []

        def ad_fail(*a, **kw):
            raise AR.RegressionRefused('ad regression failed: timeout_200s rewarded twice')
        code, err, _ = self.make('new', self.adapter(), [mock.patch.object(AR, 'run', side_effect=ad_fail),
                                                          self.passing_runtime(seen)])
        self.assertEqual(code, 1, err)
        self.assertIn('timeout_200s rewarded twice', err)
        self.assertEqual(len(seen), 1)                     # both gates ran: every reason is listed at once
        self.assertFalse(self.out.exists())

    def test_passing_regressions_write_zip_and_report_them(self):
        self.files['game.js'] += b'tt.createRewardedVideoAd({adUnitId: "x"});\n'
        (self.native / 'game.js').write_bytes(self.files['game.js'])
        seen, ads = [], []

        def ad_pass(folder, adapter, **kw):
            ads.append(adapter)
            return {'id': 'rewarded_ad_regression', 'passed': True, 'cases': 10}
        adapter = self.adapter()
        code, err, report = self.make('new', adapter, [mock.patch.object(AR, 'run', side_effect=ad_pass),
                                                       self.passing_runtime(seen)])
        self.assertEqual(code, 0, err)
        self.assertTrue(self.out.is_file())
        self.assertEqual(ads, [str(adapter)])
        self.assertEqual(seen[0]['adapter'], str(adapter))
        self.assertEqual((seen[0]['policy'], seen[0]['board']), ('new', 'remake'))
        with zipfile.ZipFile(self.out) as z:                 # the suites saw exactly the bytes in the ZIP
            self.assertEqual(seen[0]['files'], {i.filename: z.read(i) for i in z.infolist()})
        self.assertTrue(report['runtime_regression']['passed'])
        self.assertEqual(report['rewarded_ad_regression']['cases'], 10)
        self.assertIn('fixture warning', report['warnings'])
        self.assertEqual(report['regressions']['problems'], [])
        self.assertEqual(report['pre_home_bytes']['measured'], {'MiB': 1.0})

    def test_env_adapter_is_used_like_build_checked_zip(self):
        seen = []
        adapter = self.adapter()
        code, err, report = self.make('new', None, [mock.patch.dict(os.environ, {RR.ENV_ADAPTER: str(adapter)}),
                                                    self.passing_runtime(seen)])
        self.assertEqual(code, 0, err)
        self.assertEqual(seen[0]['adapter'], str(adapter))
        self.assertEqual(report['rewarded_ad_regression']['status'], 'not_applicable')

    # ---- legacy game

    def test_legacy_game_without_adapter_warned_and_written(self):
        code, err, report = self.make('legacy')
        self.assertEqual(code, 0, err)
        self.assertTrue(self.out.is_file())
        warned = [w for w in report['warnings'] if '[legacy game: warning]' in w]
        self.assertTrue(any('runtime regression required' in w for w in warned), report['warnings'])
        self.assertEqual(report['runtime_regression']['status'], 'failed')
        self.assertEqual(report['regressions']['policy'], 'legacy')

    def test_legacy_game_failed_suite_warned(self):
        def fail(*a, **kw):
            raise RR.RuntimeRefused('runtime regression failed: layout_state/home: overlap')
        code, err, report = self.make('legacy', self.adapter(), [mock.patch.object(RR, 'run', side_effect=fail)])
        self.assertEqual(code, 0, err)
        self.assertTrue(any('layout_state/home: overlap' in w for w in report['warnings']))


class Interface(unittest.TestCase):
    def test_writer_regressions_never_raises_and_legacy_only_warns(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {RR.ENV_ADAPTER: ''}):
            (Path(d) / 'game.js').write_bytes(b'//g')
            files = {'game.js': b'//g'}
            new = C.writer_regressions(files, d, None, policy='new', board='remake')
            old = C.writer_regressions(files, d, None, policy='legacy', board='remake')
        self.assertTrue(new['blocked'])
        self.assertIn('qa/ad-regression.json', new['problems'][0])
        self.assertFalse(old['blocked'])
        self.assertEqual(old['problems'], [])
        self.assertTrue(old['warnings'])

    def test_wiring_runs_before_the_receipt_and_check_is_unchanged(self):
        body = inspect.getsource(M.main)
        self.assertIn('writer_regressions(check, a.ad_regression, gate_policy, a.board)', body)
        self.assertLess(body.index('writer_regressions(check'), body.index('vnz.make_receipt('))
        self.assertIn('runtime_gate(verified_files, folder, ad_regression, policy=gates.get(\'policy\'), board=board)',
                      inspect.getsource(C.check))


if __name__ == '__main__':
    unittest.main()
