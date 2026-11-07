#!/usr/bin/env python3
"""生成时预防 P21 (2026-11-04 普查: Ego 卡死 / 空间冲突 45 次, Creator 卡死 11, 试玩链接旧版 / 打不开 24).

Fixtures only: fake Ego / fake Node / fake Chrome scripts, a local HTTP server on a temporary folder. No real browser,
no Ego, no Cocos Creator is started; nothing outside temporary folders is touched (browser_slots is never called).
Each part shows the old behaviour next to the new one:
  ① two runs with the same space name share one Ego space (one run's finish() closes the other's page) / names differ
  ② an Ego call that times out, loses its space or goes silent preserves its result and records the Ego error
  ③ an outer time limit counts the queue for the lock / --run-timeout counts only from the lock
  ④ the build command lacks the sandbox switches, a sandboxed terminal is retried / switches always there, exit 3
  ⑤ a link that serves an old copy of the export is handed out / refused after reading the link back
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_p21_browser_env.py   (about 10 s)
"""
import importlib.util
import io
import json
import os
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'remake-core' / 'scripts'))
sys.path.insert(0, str(ROOT / 'cocos-game-check' / 'package-check' / 'scripts'))
import browser_env as BE  # noqa: E402
import find_creator as FC  # noqa: E402

POSIX = os.name != 'nt'
PY = sys.executable


def write(path, text, mode=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    if mode:
        path.chmod(mode)
    return path


class FakeEgo:
    """Ego's space rule: taskSpace(name) resumes a same-name space; finish() closes every page in it."""

    def __init__(self):
        self.spaces = {}

    def open(self, name, page):
        self.spaces.setdefault(name, set()).add(page)

    def finish(self, name):
        self.spaces.pop(name, None)

    def alive(self, name, page):
        return page in self.spaces.get(name, set())


class SpaceNames(unittest.TestCase):
    OLD_LINE = "os.environ.get('AD_REGRESSION_SPACE') or 'tiktok-ad-regression-%d-%s'"

    def test_old_fixed_name_lets_one_run_close_the_other(self):
        # 11.12 ad_regression: a session that set AD_REGRESSION_SPACE (v7.4 docs: tiktok-ad-regression) used it as is
        env = {'AD_REGRESSION_SPACE': 'tiktok-ad-regression'}
        old = lambda: env.get('AD_REGRESSION_SPACE') or 'unique'
        ego = FakeEgo()
        a, b = old(), old()
        ego.open(a, 'HappyCup page')
        ego.open(b, 'MabelsBus page')
        ego.finish(b)                                   # MabelsBus run ends first
        self.assertEqual(a, b)
        self.assertFalse(ego.alive(a, 'HappyCup page'))  # HappyCup's page is gone in the middle of its run

    def test_new_names_differ_between_runs_and_games(self):
        ego = FakeEgo()
        env = {'AD_REGRESSION_SPACE': 'tiktok-ad-regression'}
        names = {BE.space_name('ad-regression', game=g, pid=p, env={}) for g, p in
                 (('HappyCup', 100), ('HappyCup', 101), ('MabelsBus', 100), ('水杯传奇', 100), ('切个水果', 100))}
        self.assertEqual(len(names), 5)
        a = BE.space_name('ad', game='HappyCup', pid=100, env={})
        b = BE.space_name('ad', game='HappyCup', pid=100, env={})   # same game, same process, twice: random part
        self.assertNotEqual(a, b)
        ego.open(a, 'page A')
        ego.open(b, 'page B')
        ego.finish(b)
        self.assertTrue(ego.alive(a, 'page A'))
        self.assertTrue(a.startswith('HappyCup-100-ad-'))
        self.assertTrue(BE.space_name('ad', env={BE.SPACE_ENV: 'Game-7'}).startswith('Game-7-ad-'))
        self.assertTrue(all(ord(c) < 128 for c in BE.space_name('ad', game='1夜曲-MabelsMeadow（自制）', pid=1, env={})))

    def test_ad_regression_takes_its_name_from_browser_env(self):
        import ad_regression as AR
        old_text = (Path(AR.__file__)).read_text(encoding='utf-8')
        self.assertNotIn(self.OLD_LINE, old_text)
        saved = os.environ.pop('AD_REGRESSION_SPACE', None)
        try:
            x, y = AR._space_name('/g/HappyCup'), AR._space_name('/g/HappyCup')
            self.assertNotEqual(x, y)
            self.assertIn('HappyCup-%d-ad-regression-' % os.getpid(), x)
            os.environ['AD_REGRESSION_SPACE'] = 'tiktok-ad-regression'   # an old session's setting: now only a prefix
            self.assertNotEqual(AR._space_name('/g/HappyCup'), AR._space_name('/g/HappyCup'))
        finally:
            os.environ.pop('AD_REGRESSION_SPACE', None)
            if saved is not None:
                os.environ['AD_REGRESSION_SPACE'] = saved

    def test_guess_game_skips_build_folders(self):
        self.assertEqual(BE.guess_game(['x', '--package', '/a/HappyCup/build/bytedance-mini-game']), 'HappyCup')
        self.assertEqual(BE.guess_game(['x', '--package=/a/Pine_fix2.zip']), 'Pine_fix2')


class EgoFailures(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.dir = Path(self.td.name)
        self.calls = self.dir / 'ego-calls.txt'
        self.events = self.dir / 'events.jsonl'
        self.node = write(self.dir / 'fakenode', '#!%s\nfrom pathlib import Path\nPath(%r).touch()\n' %
                          (PY, str(self.dir / 'fallback-ran')), 0o755)
        self.browser = write(self.dir / 'FakeChrome', '')

    def ego(self, body):
        return write(self.dir / 'fake_ego.py', 'import sys, time\nopen(%r, "a").write("call\\n")\n%s\n' % (str(self.calls),
                                                                                                    textwrap.dedent(body)))

    def env(self, **extra):
        return dict(os.environ, **{BE.EVENTS_ENV: str(self.events), BE.FALLBACK_NODE_ENV: str(self.node),
                                   BE.FALLBACK_BROWSER_ENV: str(self.browser)}, **extra)

    def relay(self, ego, args, env, stdin_data=None, stall=None):
        out, err = io.StringIO(), io.StringIO()
        code = BE.relay(str(ego), args, env=env, stdin_data=stdin_data, stall=stall, out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def test_old_ego_timeout_just_fails(self):
        ego = self.ego('sys.stderr.write("Error: Page.captureScreenshot timed out after 15000ms\\n"); sys.exit(1)')
        r = subprocess.run([PY, str(ego), 'nodejs', '-e', 'x'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)               # 11.12: the check is refused, the session stops and asks

    def test_old_silent_ego_hangs_until_outer_limit(self):
        ego = self.ego('time.sleep(30)')
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run([PY, str(ego), 'nodejs', '-e', 'x'], capture_output=True, timeout=2)

    def assert_no_fallback(self):
        self.assertFalse((self.dir / 'fallback-ran').exists())

    def test_timeout_is_recorded_without_switch_or_sticky_route(self):
        ego = self.ego('sys.stderr.write("Error: Page.captureScreenshot timed out after 15000ms\\n"); sys.exit(1)')
        code, out, err = self.relay(ego, ['nodejs', '-e', 'await run()'], self.env())
        self.assertEqual(code, 1)
        self.assertEqual(out, '')
        self.assertIn('不回退 Chrome', err)
        rows = BE.read_events(self.events)
        self.assertEqual([(r['kind'], r['route']) for r in rows], [('ego_error', 'ego')])
        self.assertIn('captureScreenshot', rows[0]['reason'])
        code, _, _ = self.relay(ego, ['nodejs', '-e', 'second'], self.env())
        self.assertEqual(code, 1)
        self.assertEqual(self.calls.read_text().count('call'), 2)
        self.assert_no_fallback()

    def test_lost_space_stays_failed(self):
        ego = self.ego('sys.stderr.write("Error: task space not found: 89\\n"); sys.exit(4)')
        code, _, err = self.relay(ego, ['nodejs', '-e', 'x'], self.env())
        self.assertEqual(code, 4)
        self.assertIn('task space not found', err)
        self.assertEqual(BE.read_events(self.events)[0]['kind'], 'ego_error')
        self.assert_no_fallback()

    def test_silent_ego_is_stopped_without_switch(self):
        ego = self.ego('time.sleep(30)')
        started = time.monotonic()
        code, _, _ = self.relay(ego, ['nodejs', '-e', 'x'], self.env(), stall=1)
        self.assertLess(time.monotonic() - started, 10)
        self.assertNotEqual(code, 0)
        self.assertIn('没有任何输出', BE.read_events(self.events)[0]['reason'])
        self.assert_no_fallback()

    def test_stdin_script_runs_once_in_ego(self):
        ego = self.ego('print(sys.stdin.read()); sys.stderr.write("CDP request timed out\\n"); sys.exit(1)')
        code, out, _ = self.relay(ego, ['nodejs'], self.env(), stdin_data='const CONFIG = 1;')
        self.assertEqual(code, 1)
        self.assertIn('const CONFIG = 1;', out)
        self.assertEqual(self.calls.read_text().count('call'), 1)
        self.assert_no_fallback()

    def test_game_failure_is_not_a_browser_error(self):
        ego = self.ego('print("nocallback: reward count 1"); sys.stderr.write("rewarded-ad regression failed\\n"); sys.exit(1)')
        code, out, _ = self.relay(ego, ['nodejs', '-e', 'x'], self.env())
        self.assertEqual(code, 1)
        self.assertIn('nocallback', out)
        self.assertEqual(BE.read_events(self.events), [])
        self.assert_no_fallback()

    def test_wrapper_report_preserves_ego_route_and_child_status(self):
        report = self.dir / 'browser-report.json'
        for code in (0, 4):
            with self.subTest(exit_code=code), patch.object(BE, 'find_ego', return_value=str(self.dir / 'official-ego')), \
                    patch.dict(os.environ, {'EGO_BROWSER': '', BE.FALLBACK_NODE_ENV: str(self.node),
                                            BE.FALLBACK_BROWSER_ENV: str(self.browser)}):
                caller = ('import os; '
                          'assert os.environ["EGO_BROWSER"].endswith("official-ego"); '
                          'assert os.environ[%r].startswith("HappyCup-"); '
                          'assert %r not in os.environ; '
                          'raise SystemExit(%d)' % (BE.SPACE_ENV, BE.FALLBACK_BROWSER_ENV, code))
                self.assertEqual(BE.main(['--game', 'HappyCup', '--report', str(report), '--', PY, '-c', caller]), code)
                doc = json.loads(report.read_text(encoding='utf-8'))
                self.assertEqual((doc['route'], doc['switched_to_chrome'], doc['exit_code']), ('ego', False, code))
                self.assertEqual(doc['fallbacks'], [])
                self.assertFalse(doc['fallback_available'])
                self.assert_no_fallback()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LockClock(unittest.TestCase):
    """Two build jobs of the same game: the second queues ~2 s, then runs 1.5 s; the job's own limit is 3 s."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.env = dict(os.environ, GAME_SKILL_LOCK_DIR=str(Path(self.td.name) / 'locks'), HEAVY_LOCK_POLL_S='0.1')
        self.project = Path(self.td.name) / 'HappyCup'
        self.project.mkdir()
        self.tool = ROOT / 'remake-core' / 'scripts' / 'heavy_lock.py'

    def job(self, seconds, *extra, tool=None):
        code = 'import os,time; time.sleep(%s); print("waited", os.environ.get("HEAVY_LOCK_WAITED_S"))' % seconds
        return [PY, '-B', str(tool or self.tool), 'run', '--project', str(self.project), '--name', 'web build', *extra,
                '--', PY, '-c', code]

    def hold(self, seconds=2.0):
        first = subprocess.Popen(self.job(seconds), env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(first.wait)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not any(Path(self.env['GAME_SKILL_LOCK_DIR']).glob('project-*/owner.json')):
            time.sleep(0.05)
        return first

    def test_old_outer_limit_counts_the_queue(self):
        self.hold()
        with self.assertRaises(subprocess.TimeoutExpired):     # 11.12 pattern: subprocess timeout around heavy_lock
            subprocess.run(self.job(1.5), env=self.env, capture_output=True, timeout=3)

    def test_run_timeout_starts_at_the_lock(self):
        self.hold()
        r = subprocess.run(self.job(1.5, '--run-timeout', '0.05'), env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        held = json.loads(next(l for l in r.stdout.splitlines() if '"lock_held"' in l))
        self.assertGreaterEqual(held['waited_s'], 1.0)
        self.assertIn('waited ', r.stdout)

    def test_run_timeout_still_stops_a_stuck_job(self):
        r = subprocess.run(self.job(20, '--run-timeout', '0.02'), env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 124)
        self.assertIn('run_timeout', r.stdout)


class CreatorSandbox(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.ed = {'version': '2.4.15', 'exe': str(self.root / 'CocosCreator'), 'source': 't'}

    def test_old_command_had_no_sandbox_switches(self):
        old = load(ROOT.parent / 'backup' / 'cocos-game-to-english' / 'scripts' / 'find_creator.py', 'fc_old') \
            if (ROOT.parent / 'backup').is_dir() else None
        if old is None:
            self.skipTest('11.12 copy of find_creator.py is only in the patch work folder')
        self.assertNotIn('--no-sandbox', old.build_argv(self.ed, self.root, 2, 'web-mobile'))

    def test_commands_always_carry_the_switches(self):
        for major, name in ((2, 'web-mobile'), (3, 'bytedance-mini-game')):
            argv = FC.build_argv(self.ed, self.root, major, name)
            self.assertEqual(argv[-3:], ['--no-sandbox', '--disable-gpu-sandbox', '--disable-gpu'])
        self.assertIn('--no-sandbox', FC.quote(FC.build_argv(self.ed, self.root, 2, 'web-mobile'), 'win32'))

    def test_sandbox_found_by_env_and_by_unwritable_home(self):
        home = self.root / 'home'
        home.mkdir()
        self.assertIsNone(FC.sandbox_problem(env={}, home=home))
        self.assertIn('CODEX_SANDBOX', FC.sandbox_problem(env={'CODEX_SANDBOX': 'seatbelt'}, home=home))
        if POSIX and os.geteuid() != 0:
            home.chmod(0o500)
            try:
                self.assertIn('不能写用户文件夹', FC.sandbox_problem(env={}, home=home))
            finally:
                home.chmod(0o700)

    def test_sandboxed_terminal_exits_3_without_retry(self):
        project = write(self.root / 'p' / 'project.json', json.dumps({'version': '2.4.15'})).parent
        env = dict(os.environ, CODEX_SANDBOX='seatbelt')
        r = subprocess.run([PY, '-B', str(HERE / 'find_creator.py'), '--preflight'], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 3)
        self.assertIn('不要重试', r.stdout)
        r = subprocess.run([PY, '-B', str(HERE / 'find_creator.py'), '--project', str(project)], capture_output=True,
                           text=True, env=env)
        self.assertEqual(r.returncode, 3)
        self.assertTrue(r.stdout.startswith('现在不能构建'))


class PreviewReadback(unittest.TestCase):
    def setUp(self):
        self.SP = load(ROOT / 'remake-core' / 'scripts' / 'serve_preview.py', 'serve_preview_p21_readback')
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.export = Path(self.td.name) / 'web-mobile'
        write(self.export / 'index.html', '<html><script src="src/settings.js"></script>'
                                          '<script src="main.js?v=1"></script><script src="https://cdn.x/a.js"></script></html>')
        write(self.export / 'src' / 'settings.js', 'settings v2')
        write(self.export / 'main.js', 'main v2 (fixed leaderboard)')

    def serve(self, folder, injected=False):
        handler = partial(self.SP.Handler, directory=str(folder), phone_size=(390, 844), preview_token='abcd1234',
                          ad_simulator=injected)
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return 'http://127.0.0.1:%d/' % server.server_port

    def old_copy(self):
        old = Path(self.td.name) / 'old-snapshot'
        shutil.copytree(self.export, old)
        write(old / 'main.js', 'main v1 (old leaderboard)')
        return old

    def test_old_server_hands_out_an_old_copy(self):
        url = self.serve(self.old_copy())
        from urllib.request import urlopen
        served = urlopen(url + '__preview/abcd1234/main.js', timeout=5).read()
        self.assertNotEqual(served, (self.export / 'main.js').read_bytes())   # what Saul would see: the old build
        base = ROOT.parent / 'base'
        old = next(base.glob('*/remake-core/scripts/serve_preview.py'), None) if base.is_dir() else None
        if old:
            self.assertNotIn('entry_readback', old.read_text(encoding='utf-8'))   # 11.12 printed the link anyway

    def test_current_export_passes(self):
        ok, rows, problem = self.SP.entry_readback(self.serve(self.export), self.export)
        self.assertTrue(ok, problem)
        self.assertEqual(sorted(r['file'] for r in rows), ['index.html', 'main.js', 'src/settings.js'])

    def test_old_copy_is_refused(self):
        ok, rows, problem = self.SP.entry_readback(self.serve(self.old_copy()), self.export)
        self.assertFalse(ok)
        self.assertIn('main.js', problem)
        self.assertNotIn('settings.js', problem)

    def test_old_entry_page_is_refused(self):
        old = self.old_copy()
        write(old / 'main.js', 'main v2 (fixed leaderboard)')
        write(old / 'index.html', '<html><script src="main.js?v=043"></script></html>')
        ok, _, problem = self.SP.entry_readback(self.serve(old), self.export)
        self.assertFalse(ok)
        self.assertIn('index.html', problem)

    def test_ad_simulator_pages_compare_scripts_only(self):
        ok, rows, problem = self.SP.entry_readback(self.serve(self.export, injected=True), self.export, html_injected=True)
        self.assertTrue(ok, problem)
        self.assertNotIn('index.html', [r['file'] for r in rows])

    def test_dead_link_is_refused(self):
        ok, _, problem = self.SP.entry_readback('http://127.0.0.1:9/', self.export)
        self.assertFalse(ok)
        self.assertIn('读不回', problem)


if __name__ == '__main__':
    unittest.main(verbosity=1)
