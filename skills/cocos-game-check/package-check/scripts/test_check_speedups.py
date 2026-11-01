#!/usr/bin/env python3
"""v7.9 出包检查提速 (总表 19 ①②③; 提速调查_20261031/出包检查提速_读代码.md S1, S3 + S8, S7). The verdicts do not change;
only work that could not change them is skipped:

1. S3: what the adapter lacks for any runtime suite of a run is refused before the first suite opens a browser, all
   problems at once (飞车 v3.1 waited 883 s for frame_rate / popin, FoxDenDash v1 457 s, partly for play). A legacy
   game still only gets warnings for needs_new fields. The rewarded-ad regression (about 1.5 minutes) runs first.
2. S8 (D7): build_checked_zip compares the finalize record with the bytes before the startup runtime check and the
   regressions (until v7.8 only after check() had run them all).
3. S1: an official writer's receipt keeps a record of the two regressions it passed; prepare_delivery's check() reuses
   it for the same bytes, adapter and check tools and runs them again otherwise.
4. S7: a browser step with no output line and no file change for the stall window is stopped and refused instead of
   waiting for the suite limit (startup / ad_entries 1500 s); lib.mjs and gates.mjs touch the progress file after
   every page round trip, so a slow suite is not mistaken for a stuck one.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_check_speedups.py
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SHARED = HERE.parents[2] / 'remake-core' / 'scripts'
for p in (str(HERE), str(SHARED)):
    if p not in sys.path:
        sys.path.insert(0, p)

import ad_regression                 # noqa: E402
import check_package                 # noqa: E402
import runtime_regression            # noqa: E402
import watched_run                   # noqa: E402

GAME = {'game.js': b"tt.createRewardedVideoAd({adUnitId: 'x'});", 'main.js': b'1'}
PARTIAL = {'request': 'window.__ad()', 'home': 'return true'}                     # no play, frame_rate, popin
COMPLETE = dict(PARTIAL, play='return {x: 1, y: 1}', frame_rate={'n/a': 'nothing moves on its own'},
                popin={'n/a': 'no scrolling obstacles'},
                resume_play={'n/a': 'v7.9: fixture without levels'}, save_restart={'n/a': 'v7.9: fixture without saves'})


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, (dict, list)):
        data = json.dumps(data)
    path.write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
    return path


class Tmp(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='speedups '))
        self.addCleanup(shutil.rmtree, self.root, True)

    def adapter(self, doc, name='adapter.json'):
        return write(self.root / name, doc)


# ---------------------------------------------------------------- 1. S3: adapter problems before the browser

class AdapterPreflight(Tmp):
    """S3: the adapter problems of every suite of a runtime regression refuse before the first suite opens a browser."""

    def setUp(self):
        super().setUp()
        self.mark = self.root / 'browser-ran'
        self.browser = script(self.root / 'ego-browser', 'import pathlib\npathlib.Path(%r).write_text("ran")\n'
                              % str(self.mark))
        self.package = self.root / 'pkg'
        for name, data in GAME.items():
            write(self.package / name, data)
        env = mock.patch.dict(os.environ, {runtime_regression.ENV_BROWSER: str(self.browser)})
        env.start()
        self.addCleanup(env.stop)

    def problems(self, adapter, policy):
        catalog = runtime_regression.load_suites()
        names = runtime_regression.required_suites(GAME, adapter, catalog)
        return runtime_regression.config_problems(names, catalog, adapter, '2.x', policy)[0]

    def test_every_missing_field_is_listed_at_once_for_a_new_game(self):
        text = ' | '.join(self.problems(PARTIAL, 'new'))
        for item in ('runtime suite startup needs adapter field(s) play', 'frame_rate/adapter: adapter has no "frame_rate"',
                     'popin/adapter: adapter has no "popin"'):
            self.assertIn(item, text, item)

    def test_a_legacy_game_only_keeps_the_hard_needs(self):
        self.assertEqual(self.problems(PARTIAL, 'legacy'), ['runtime suite startup needs adapter field(s) play'])

    def test_complete_adapter_has_no_problem(self):
        self.assertEqual(self.problems(COMPLETE, 'new'), [])

    def test_run_refuses_before_any_browser(self):
        with self.assertRaises(runtime_regression.RuntimeRefused) as caught:
            runtime_regression.run(self.package, self.adapter(PARTIAL), policy='new', work=self.root / 'work')
        text = str(caught.exception)
        for item in ('before the browser', 'startup needs adapter field(s) play', 'popin/adapter', 'frame_rate/adapter'):
            self.assertIn(item, text, item)
        self.assertTrue(caught.exception.summary['stopped_before_browser'])
        self.assertFalse(self.mark.exists(), 'a browser was started')

    def test_writer_regressions_and_check_stop_there_too(self):
        ad = mock.Mock(return_value={'id': 'rewarded_ad_regression', 'passed': True, 'warnings': []})
        with mock.patch.object(check_package, 'rewarded_ad_gate', ad):
            out = check_package.writer_regressions(GAME, str(self.package), str(self.adapter(PARTIAL)), policy='new')
            self.assertTrue(out['blocked'])
            self.assertIn('startup needs adapter field(s) play', out['problems'][0])
            self.assertTrue(out['runtime_regression']['stopped_before_browser'])
            archive = write(self.root / 'pkg.zip', b'zip bytes')
            with fake_static(GAME, archive):
                with self.assertRaises(ValueError) as caught:
                    check_package.check(archive, ad_regression=str(self.adapter(PARTIAL)))
        self.assertIn('before the browser', str(caught.exception))
        self.assertFalse(self.mark.exists(), 'a browser was started')


def fake_static(files, archive, entry='unofficial', receipt=None, policy='new', blocks=()):
    """The verifier and the static package gates replaced: check() then only does what this change touched.
    blocks: package-gate blocks ({id, message}) the fake gates report, for a package the static checks refuse."""
    sha = hashlib.sha256(Path(archive).read_bytes()).hexdigest()

    def verify(path, expected_app_id=None, _verified_files=None):
        _verified_files.update(files)
        out = {'sha256': sha, 'file_sha256': {n: hashlib.sha256(d).hexdigest() for n, d in files.items()}, 'entry': entry}
        if receipt:
            out['receipt'] = str(receipt)
        return out
    gates = types.ModuleType('package_gates')
    gates.run = lambda *a, **k: {'blocks': list(blocks), 'policy': policy, 'policy_reason': 'test'}
    gates.messages = lambda found: ['%s: %s' % (b['id'], b['message']) for b in found]
    gates.summary = lambda g: {'blocks': []}
    stack = mock.patch.multiple(check_package, packed_assets=mock.Mock(return_value={'passed': True, 'errors': []}),
                                tools_in_use=mock.Mock(return_value={'status': 'release'}))
    patches = [mock.patch.object(check_package.verifier, 'verify', verify), mock.patch.dict(sys.modules, {'package_gates': gates}),
               stack, mock.patch('make_tiktok_zip.pre_home', return_value=None)]

    class All:
        def __enter__(self):
            for p in patches:
                p.__enter__()

        def __exit__(self, *exc):
            for p in reversed(patches):
                p.__exit__(*exc)
    return All()


# ---------------------------------------------------------------- 2. S8: finalize record before the expensive steps

class FinalizeBeforeRuntime(Tmp):
    def test_mismatch_refuses_before_startup_runtime_and_regressions(self):
        import build_checked_zip
        native = self.root / 'Native'
        write(native / 'game.js', GAME['game.js'])
        write(native / 'project.config.json', {'appid': 'tt0000000000000000'})
        manifest = write(self.root / 'resources.json', {'requests': []})
        finalized = {'kind': 'finalize-native', 'policy': 'new', 'decision': {'reason': 'test'}, 'blocks': [],
                     'files_after': {'game.js': '0' * 64}, 'steps': [], 'table': []}
        startup, checker = mock.Mock(), mock.Mock()
        with mock.patch('make_tiktok_zip.finalize_for_writer', return_value=(finalized, {}, [])), \
                mock.patch('make_tiktok_zip.native_problems', return_value=([], None, {})), \
                mock.patch('make_tiktok_zip.english_image_problems', return_value=[]), \
                mock.patch.object(build_checked_zip.package_obligations, 'verify', return_value={}), \
                mock.patch.object(check_package, 'packed_assets', return_value={'passed': True, 'errors': []}), \
                mock.patch.object(build_checked_zip, 'audit_final_startup', startup), \
                mock.patch.object(build_checked_zip, 'check', checker):
            with self.assertRaises(ValueError) as caught:
                build_checked_zip.build(native, 'tt0000000000000000', self.root / 'out' / 'Game.zip',
                                        resource_manifest=manifest, project=self.root, ad_regression=str(self.adapter(COMPLETE)))
        self.assertIn('finalize record does not match the ZIP', str(caught.exception))
        startup.assert_not_called()
        checker.assert_not_called()


# ---------------------------------------------------------------- 3. S1: delivery reuses the writer's passed regressions

def passed_summaries(files, adapter_path):
    adapter_sha = hashlib.sha256(Path(adapter_path).read_bytes()).hexdigest()
    catalog = runtime_regression.load_suites()
    ad = {'id': 'rewarded_ad_regression', 'passed': True, 'cases': [{'case': c, 'ok': True} for c in ad_regression.CASES],
          'warnings': [], 'tool_sha256': ad_regression.tool_digest(), 'adapter_sha256': adapter_sha, 'seconds': 90.0}
    rt = {'id': 'runtime_regression', 'passed': True, 'engine': '2.x', 'required':
          runtime_regression.required_suites(files, str(adapter_path), catalog), 'policy': 'new', 'board': 'localize',
          'suites': [], 'warnings': [], 'startup_measured': None, 'tool_sha256': runtime_regression.tool_digest(catalog),
          'adapter_sha256': adapter_sha, 'seconds': 600.0}
    return ad, rt


class WriterReceiptReuse(Tmp):
    def receipt(self, record):
        return write(self.root / 'Game.zip.receipt.json', {'tool': 'build_checked_zip', 'regressions': record})

    def test_record_needs_both_passed(self):
        adapter = self.adapter(COMPLETE)
        ad, rt = passed_summaries(GAME, adapter)
        self.assertEqual(check_package.regression_record(ad, rt)['schema'], check_package.REUSE_SCHEMA)
        self.assertIsNone(check_package.regression_record(dict(ad, passed=False), rt))
        self.assertIsNone(check_package.regression_record(ad, dict(rt, status='failed', passed=False)))
        na = check_package.regression_record({'id': 'rewarded_ad_regression', 'status': 'not_applicable', 'reason': 'x'}, rt)
        self.assertEqual(na['rewarded_ad_regression']['status'], 'not_applicable')

    def test_same_bytes_adapter_and_tools_reuse(self):
        adapter = self.adapter(COMPLETE)
        receipt = self.receipt(check_package.regression_record(*passed_summaries(GAME, adapter)))
        out = check_package.reusable_regressions(receipt, GAME, str(adapter), 'new')
        self.assertTrue(out['reused'], out)
        self.assertEqual(out['runtime_regression']['reused_from'], str(receipt))

    def test_any_difference_runs_them_again(self):
        adapter = self.adapter(COMPLETE)
        record = check_package.regression_record(*passed_summaries(GAME, adapter))
        changed = self.adapter(dict(COMPLETE, home='return 1 === 1'), 'changed.json')
        cases = {
            'adapter differs': (record, changed, 'new'),
            'tool differs': (dict(record, rewarded_ad_regression=dict(record['rewarded_ad_regression'], tool_sha256='0' * 64)),
                             adapter, 'new'),
            'runtime tools differ': (dict(record, runtime_regression=dict(record['runtime_regression'], tool_sha256='0' * 64)),
                                     adapter, 'new'),
            'suites differ': (dict(record, runtime_regression=dict(record['runtime_regression'], required=['startup'])),
                              adapter, 'new'),
            'writer judged it legacy': (dict(record, runtime_regression=dict(record['runtime_regression'], policy='legacy')),
                                        adapter, 'new'),
            'no record (receipt before v7.9)': (None, adapter, 'new'),
        }
        for label, (rec, adp, policy) in cases.items():
            out = check_package.reusable_regressions(self.receipt(rec), GAME, str(adp), policy)
            self.assertFalse(out['reused'], label)
            self.assertTrue(out['why'], label)

    def test_check_reuses_only_for_an_official_writer_zip(self):
        adapter = self.adapter(COMPLETE)
        archive = write(self.root / 'Game.zip', b'zip bytes')
        receipt = self.receipt(check_package.regression_record(*passed_summaries(GAME, adapter)))
        ad, rt = mock.Mock(), mock.Mock()
        with fake_static(GAME, archive, entry='official', receipt=receipt), \
                mock.patch.object(check_package, 'rewarded_ad_gate', ad), mock.patch.object(check_package, 'runtime_gate', rt):
            result = check_package.check(archive, ad_regression=str(adapter), reuse_writer_regressions=True)
        ad.assert_not_called()
        rt.assert_not_called()
        self.assertTrue(result['regression_reuse']['reused'])
        self.assertEqual(result['runtime_regression']['reused_from'], str(receipt))
        ok = {'id': 'x', 'passed': True, 'warnings': []}
        ad, rt = mock.Mock(return_value=ok), mock.Mock(return_value=ok)
        with fake_static(GAME, archive, entry='unofficial', receipt=receipt), \
                mock.patch.object(check_package, 'rewarded_ad_gate', ad), mock.patch.object(check_package, 'runtime_gate', rt):
            result = check_package.check(archive, ad_regression=str(adapter), reuse_writer_regressions=True)
        ad.assert_called_once()
        rt.assert_called_once()
        self.assertFalse(result['regression_reuse']['reused'])
        with fake_static(GAME, archive, entry='official', receipt=receipt), \
                mock.patch.object(check_package, 'rewarded_ad_gate', ad), mock.patch.object(check_package, 'runtime_gate', rt):
            result = check_package.check(archive, ad_regression=str(adapter))         # writers: never reuse
        self.assertEqual(ad.call_count, 2)
        self.assertNotIn('regression_reuse', result)

    def test_writers_keep_the_record_and_delivery_asks_for_it(self):
        src = (HERE / 'build_checked_zip.py').read_text(encoding='utf-8')
        self.assertIn("'regressions': package_checks.regression_record(", src)
        mtz = (SHARED / 'make_tiktok_zip.py').read_text(encoding='utf-8')
        self.assertIn("'regressions': regression_receipt(regressions)", mtz)
        self.assertIn('reuse_writer_regressions=True', (HERE / 'prepare_delivery.py').read_text(encoding='utf-8'))


# ---------------------------------------------------------------- 5. 总表 19 ④: static refusal, no browser suites

class StaticRefusalSkipsBrowser(Tmp):
    """A package the static checks already refuse has to be rebuilt anyway: check() lists every static reason at once
    and does not spend 7.5-15 minutes on the rewarded-ad and runtime regressions (Kiro 10-31, 总表 19 ④)."""

    BLOCKS = [{'id': 'G1_growth_apis', 'message': 'addShortcut missing'}, {'id': 'G4_webp', 'message': 'webp found'}]
    OK = {'id': 'x', 'passed': True, 'warnings': []}

    def run_check(self, blocks, ad, rt):
        adapter = self.adapter(COMPLETE)
        archive = write(self.root / 'Game.zip', b'zip bytes')
        with fake_static(GAME, archive, blocks=blocks), mock.patch.object(check_package, 'rewarded_ad_gate', ad), \
                mock.patch.object(check_package, 'runtime_gate', rt):
            return check_package.check(archive, ad_regression=str(adapter))

    def test_static_reasons_listed_and_browser_suites_skipped(self):
        for blocks in (self.BLOCKS, self.BLOCKS[:1]):
            ad, rt = mock.Mock(return_value=self.OK), mock.Mock(return_value=self.OK)
            with self.assertRaises(ValueError) as caught:
                self.run_check(blocks, ad, rt)
            ad.assert_not_called()
            rt.assert_not_called()
            text = str(caught.exception)
            for b in blocks:
                self.assertIn('%s: %s' % (b['id'], b['message']), text)
            self.assertTrue(text.endswith(check_package.BROWSER_SKIPPED_NOTE), text)
            self.assertIn('浏览器套件没跑', text)
        self.assertTrue(str(caught.exception).startswith('G1_growth_apis'))          # one reason: no count prefix

    def test_nothing_static_runs_both_regressions(self):
        ad, rt = mock.Mock(return_value=self.OK), mock.Mock(return_value=self.OK)
        result = self.run_check((), ad, rt)
        ad.assert_called_once()
        rt.assert_called_once()
        self.assertEqual(result['runtime_regression'], self.OK)

    def test_a_browser_refusal_alone_has_no_skip_note(self):
        ad, rt = mock.Mock(return_value=self.OK), mock.Mock(side_effect=ValueError('runtime regression failed: startup'))
        with self.assertRaises(ValueError) as caught:
            self.run_check((), ad, rt)
        self.assertEqual(str(caught.exception), 'runtime regression failed: startup')


# ---------------------------------------------------------------- 4. S7: stuck steps stop early

def script(path, body):
    write(path, '#!%s\n%s' % (sys.executable, textwrap.dedent(body)))
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


class StuckStep(Tmp):
    def test_output_keeps_a_step_alive(self):
        cmd = [sys.executable, '-c', 'import time\nfor i in range(6):\n    print(i, flush=True); time.sleep(0.3)']
        done = watched_run.run(cmd, 30, [], stall=1.5, poll=0.1)
        self.assertEqual(done.returncode, 0)
        self.assertIn('5', done.stdout)

    def test_file_changes_keep_a_silent_step_alive(self):
        folder = self.root / 'suite'
        folder.mkdir()
        cmd = [sys.executable, '-c', 'import time, pathlib\nfor i in range(8):\n'
               '    pathlib.Path(%r).write_text(str(i)); time.sleep(0.4)' % str(folder / 'progress.txt')]
        self.assertEqual(watched_run.run(cmd, 30, [folder], stall=1.5, poll=0.1).returncode, 0)

    def test_silent_step_and_its_children_are_stopped(self):
        pid_file = self.root / 'child.pid'
        cmd = [sys.executable, '-c', 'import subprocess, sys, time, pathlib\n'
               'c = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])\n'
               'pathlib.Path(%r).write_text(str(c.pid)); time.sleep(60)' % str(pid_file)]
        started = time.monotonic()
        with self.assertRaises(watched_run.Stalled) as caught:
            watched_run.run(cmd, 60, [self.root / 'nothing'], stall=1.5, poll=0.1)
        self.assertLess(time.monotonic() - started, 15)
        self.assertIn('no progress for 1 s', str(caught.exception))
        child = int(pid_file.read_text())
        for _ in range(50):
            try:
                os.kill(child, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            self.fail('the step\'s child process is still running')

    def test_total_limit_still_holds(self):
        cmd = [sys.executable, '-c', 'import time\nwhile True:\n    print(1, flush=True); time.sleep(0.2)']
        with self.assertRaises(watched_run.TimedOut):
            watched_run.run(cmd, 1.5, [], stall=30, poll=0.1)

    def test_window_comes_from_the_environment(self):
        with mock.patch.dict(os.environ, {watched_run.ENV_STALL: '7'}):
            self.assertEqual(watched_run.stall_window(), 7.0)
        with mock.patch.dict(os.environ, {watched_run.ENV_STALL: 'zero'}):
            self.assertEqual(watched_run.stall_window(), 240.0)

    def suite_meta(self):
        return {'needs': [], 'script': write(self.root / 'noop.mjs', ''), 'timeout_s': 120, 'host': 'none'}

    def test_runtime_suite_refuses_a_stuck_browser_quickly(self):
        browser = script(self.root / 'ego-browser', 'import time\ntime.sleep(60)\n')
        started = time.monotonic()
        with mock.patch.dict(os.environ, {watched_run.ENV_STALL: '1.5'}):
            with self.assertRaises(runtime_regression.RuntimeRefused) as caught:
                runtime_regression.run_suite('startup', self.suite_meta(), None, {}, None, '2.x', str(browser),
                                             self.root / 'work')
        self.assertIn('runtime suite startup stopped: no progress', str(caught.exception))
        self.assertLess(time.monotonic() - started, 20)

    def test_runtime_suite_with_progress_is_not_stopped(self):
        # A fake browser that, like lib.mjs, touches progress.txt (CFG.progressFile) while it works, then saves a result.
        browser = script(self.root / 'ego-browser', '''
            import json, pathlib, re, sys, time
            from urllib.parse import unquote
            entry = pathlib.Path(unquote(re.search(r'file://([^"]+)', sys.argv[3]).group(1)))
            cfg = json.loads(entry.read_text().split('globalThis.CFG = ', 1)[1].split(';\\n', 1)[0])
            for i in range(8):
                pathlib.Path(cfg['progressFile']).write_text(str(i)); time.sleep(0.4)
            pathlib.Path(cfg['resultFile']).write_text(json.dumps({'suite': cfg['suite'], 'passed': True, 'fatal': None,
                'cases': [{'id': 'ok', 'passed': True}], 'warnings': [], 'evidence': {}}))
            ''')
        with mock.patch.dict(os.environ, {watched_run.ENV_STALL: '1.5'}):
            row = runtime_regression.run_suite('startup', self.suite_meta(), None, {}, None, '2.x', str(browser),
                                               self.root / 'work')
        self.assertEqual(row['suite'], 'startup')

    def test_both_runners_use_the_watch_and_count_it_in_their_tool_digest(self):
        for name in ('ad_regression.py', 'runtime_regression.py'):
            src = (HERE / name).read_text(encoding='utf-8')
            self.assertIn('watched_run.run(', src, name)
            self.assertIn("b'watched_run.py\\0'", src, name)
            self.assertNotIn('capture_output=True, text=True, timeout=limit', src, name)


class SuiteHelpersTouchProgress(Tmp):
    def test_lib_and_gates_touch_the_progress_file(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        lib = HERE / 'runtime_regression' / 'lib.mjs'
        progress = self.root / 'progress.txt'
        js = textwrap.dedent('''
            globalThis.CFG = { progressFile: %s, lib: %s };
            const L = await import(globalThis.CFG.lib);
            const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
            const fs = await import('node:fs');
            const page = { evaluate: async () => 42, cdp: async () => ({}) };
            if (await L.ev(page, () => 1) !== 42) throw new Error('ev changed the value');
            if (!fs.existsSync(CFG.progressFile)) throw new Error('lib.mjs ev did not touch the progress file');
            fs.unlinkSync(CFG.progressFile);
            await new Promise((r) => setTimeout(r, 1100));
            await G.evalJs(page, 'return 1');
            if (!fs.existsSync(CFG.progressFile)) throw new Error('gates.mjs evalJs did not touch the progress file');
            fs.unlinkSync(CFG.progressFile);
            await new Promise((r) => setTimeout(r, 1100));
            await L.tap(page, 1, 1);
            if (!fs.existsSync(CFG.progressFile)) throw new Error('lib.mjs tap did not touch the progress file');
            console.log('ok');
            ''') % (json.dumps(str(progress)), json.dumps(lib.as_uri()))
        r = subprocess.run([node, '--input-type=module', '-e', js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('ok', r.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
