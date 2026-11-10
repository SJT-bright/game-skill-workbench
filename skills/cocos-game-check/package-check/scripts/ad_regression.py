#!/usr/bin/env python3
"""Mandatory pre-package rewarded-ad regression (TikTok, engine-generic).

Runs the 10 rewarded-ad cases (200 s video, playback after 16 s, background 200 s during
playback / loading, close midway, error, show failure, never starts, starts but never calls
back then X, normal; v7.8: plus double_watch / double_quit / double_free for a claim window with the "watch ad x2"
checkbox when the adapter has double_claim) against the package's REAL game.js inside the simulated TikTok host,
in the Ego browser. After each case it checks: reward count, no pending ad, no lock, music
resumed, and that an immediate second request starts and pays its reward.

The only game-specific input is the adapter JSON (see remake-ads/references/
ad-timeout-and-regression.md). The regression fails closed: no browser, no adapter, a boot
failure or a missing result is a refusal, never a pass.

  python3 -B ad_regression.py --package <unzipped dir or .zip> --adapter <adapter.json> [--report out.json]

Exit 0 passed, 1 包不通过 (a case failed or the run refused), 2 环境不完整 (v7.8, 总表 A6 补: a Cocos package without the
kit touch part, or a ZIP given here without the writer receipt for its bytes; the writers' in-process call is never
asked for a receipt).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import watched_run  # noqa: E402 - v7.9 (出包检查提速 S7): a stuck browser step is stopped after 240 s without progress
TOOL = HERE / 'ad_regression'
CASES = ['long200', 'late16', 'bgplay', 'bgload', 'cancel', 'error', 'showfail', 'hang', 'nocallback', 'normal']
# v7.8 (Saul 2026-10-31): check-in / spin result / gift pack window with the ticked-by-default "watch ad x2" checkbox.
# Run (and required) only when the adapter has double_claim = {open, claim, balance}; see cases.mjs double-claim block.
DOUBLE_CASES = ['double_watch', 'double_quit', 'double_free']
DOUBLE_KEYS = ('open', 'claim', 'balance')
ENV_ADAPTER = 'TIKTOK_AD_REGRESSION_ADAPTER'
ENV_BROWSER = 'EGO_BROWSER'
_which = shutil.which  # patch point for tests; shutil.which itself is shared
ADAPTER_KEYS = {'request', 'state', 'ready', 'exit', 'exit_label', 'no_music', 'boot_timeout_s', 'note', 'double_claim'}
# v7.7.5 (总表 A14): adapter.exit returns the X node (or {node, x, y} in its anchor space) and the tool finds where it
# is on screen. Before v7.7.4 the tool's formula was wrong, so adapters converted the position themselves to
# compensate (全民飞车漂移, 回家快跑, 狐狸回窝, 珊瑚守卫). With the corrected formula that compensation moves the tap
# off the X and nocallback / cancel look like ad bugs in the game.
SELF_CONVERT = re.compile(r'getScreenToWorldPoint|convertToNodeSpace(?:AR)?|devicePixelRatio|canvas\.(?:width|height)'
                          r'|getBoundingClientRect')


class RegressionRefused(ValueError):
    """The regression could not run or did not pass; the package must not ship."""


class EnvironmentIncomplete(RegressionRefused):
    """v7.8 (总表 A6 补): 「环境不完整」, not 「包不通过」: a Cocos package without the kit touch part (a real tap on the X
    misses, 企鹅雪道 v4), or a ZIP given on the command line without its writer receipt. Still a refusal; the CLI exits 2."""


def _environment():
    """runtime_regression holds the one environment check both regressions use (touch_problem, receipt_problem)."""
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import runtime_regression
    except Exception as error:  # noqa: BLE001 - never skip the check silently
        raise RegressionRefused('ad regression: environment check unavailable (%s)' % error)
    return runtime_regression


def environment_problem(package_dir):
    """Why this unzipped package cannot be judged here (no touch part), or None."""
    root = Path(package_dir)
    rr = _environment()
    return rr.touch_problem(rr.package_files(root))


def needs_regression(files):
    """files: {relative name: bytes}. True when the package can request a rewarded video.
    简化.11.14 R4A: the platform kit's own rewarded-guard.js (main.js v1.7 puts it in every 2.4 package; recognised by
    its KIT_MANIFEST hash, runtime_regression.rewarded_callers) is not a caller; a changed copy still is."""
    try:
        return bool(_environment().rewarded_callers(files))
    except RegressionRefused:
        return any(name.endswith('.js') and b'createRewardedVideoAd' in data for name, data in files.items())


def allowed_adapter_keys():
    """Ad keys plus the runtime-regression keys: one adapter file serves both regressions.
    If the runtime suite catalog cannot be read, only the ad keys are accepted (stricter, never looser)."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import runtime_regression
        return set(ADAPTER_KEYS) | runtime_regression.adapter_keys(runtime_regression.load_suites())
    except Exception:
        return set(ADAPTER_KEYS)
    finally:
        try:
            sys.path.remove(str(Path(__file__).resolve().parent))
        except ValueError:
            pass


def load_adapter(path):
    if not path:
        raise RegressionRefused('rewarded-ad regression required: the package calls createRewardedVideoAd; '
                                'pass --ad-regression <adapter.json> (or set %s)' % ENV_ADAPTER)
    path = Path(path)
    try:
        adapter = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise RegressionRefused('ad regression adapter unreadable: %s' % error)
    if not isinstance(adapter, dict) or not isinstance(adapter.get('request'), str) or not adapter['request'].strip():
        raise RegressionRefused('ad regression adapter needs a nonempty "request" (page JavaScript that starts one '
                                'rewarded request and calls grant() when the game pays)')
    # 11.17 R4Q7: keys starting with "_" are comments (e.g. "_scope", SLS16-3) and are never unknown.
    unknown = {k for k in set(adapter) - allowed_adapter_keys() if not str(k).startswith('_')}
    if unknown:
        raise RegressionRefused('ad regression adapter has unknown keys: ' + ', '.join(sorted(unknown)))
    for key in ('state', 'ready', 'exit', 'exit_label'):
        if key in adapter and not isinstance(adapter[key], str):
            raise RegressionRefused('ad regression adapter "%s" must be a string' % key)
    if 'double_claim' in adapter:
        d = adapter['double_claim']
        if not isinstance(d, dict) or set(d) - set(DOUBLE_KEYS) - {'note'} or \
                not all(isinstance(d.get(k), str) and d[k].strip() for k in DOUBLE_KEYS):
            raise RegressionRefused('ad regression adapter "double_claim" must be {"open", "claim", "balance"}: page JavaScript '
                                    'that opens a fresh claim window and returns its 1x amount, sets the x2 checkbox to '
                                    '`checked` and presses CLAIM, and returns the currency balance')
    return adapter


def default_cases(adapter):
    """The 10 cases, plus the three claim-window cases when the adapter describes the x2 checkbox."""
    return CASES + (DOUBLE_CASES if isinstance(adapter, dict) and 'double_claim' in adapter else [])


def adapter_warnings(adapter):
    """Hints about the adapter itself (they never refuse): adapter.exit doing its own screen-coordinate math."""
    code = adapter.get('exit') if isinstance(adapter, dict) else None
    hits = sorted(set(SELF_CONVERT.findall(code))) if isinstance(code, str) else []
    if not hits:
        return []
    return ['adapter.exit converts screen coordinates itself (%s): since v7.7.4 the tool converts the node correctly, '
            'so this compensation can move the tap off the X and make nocallback / cancel fail although the game is '
            'fine. Return the X node itself (or {node, x: 0, y: 0}).' % ', '.join(hits)]


def find_browser():
    """EGO_ONLY_TEST_POLICY: the official Ego CLI, never a Chrome transport override."""
    browser = _which('ego-browser')
    requested = os.environ.get(ENV_BROWSER)
    if requested and (not browser or Path(requested).resolve() != Path(browser).resolve()):
        raise RegressionRefused('测试只允许官方 Ego CLI（用户 2026-11-06）；EGO_BROWSER 不能指向 Chrome/Playwright 替身。')
    if not browser or not Path(browser).exists():
        raise RegressionRefused('Ego CLI 不可用；本项未执行，不能回退 Chrome 或跳过浏览器验收。')
    return browser


def judge(result, cases=CASES):
    """Pure verdict over the cases.mjs result document. Returns (passed, problems)."""
    problems = []
    if not isinstance(result, dict):
        return False, ['no regression result']
    if result.get('fatal'):
        problems.append('regression aborted: ' + str(result['fatal']))
    rows = {row.get('case'): row for row in result.get('cases') or [] if isinstance(row, dict)}
    for name in cases:
        row = rows.get(name)
        if row is None:
            problems.append(name + ': case did not run')
        elif row.get('ok') is not True or row.get('problems'):
            problems.append(name + ': ' + '; '.join(row.get('problems') or ['not ok']))
    return not problems, problems


def _free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _wait_port(port, proc, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RegressionRefused('ad regression host server exited early')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise RegressionRefused('ad regression host server did not start')


def tool_digest():
    h = hashlib.sha256()
    for name in ('host.js', 'play.html', 'server.py', 'cases.mjs'):
        h.update(name.encode() + b'\0' + (TOOL / name).read_bytes())
    h.update(b'watched_run.py\0' + (HERE / 'watched_run.py').read_bytes())     # v7.9: it decides when a step is stuck
    h.update(b'session.mjs\0' + (HERE / 'runtime_regression/session.mjs').read_bytes())
    h.update(Path(__file__).read_bytes())
    return h.hexdigest()


def _space_name(package_dir):
    """Ego space for this run (生成时预防 P21). browser_env.space_name when the English pack's browser_env.py is next to
    this skill; otherwise the same format here (the remake tree ships no browser_env.py)."""
    prefix = os.environ.get('AD_REGRESSION_SPACE')
    try:
        scripts = HERE.parents[2] / 'cocos-game-to-english' / 'scripts'
        if str(scripts) not in sys.path and (scripts / 'browser_env.py').is_file():
            sys.path.append(str(scripts))
        import browser_env
        name = browser_env.space_name('ad-regression', game=Path(package_dir).name)
    except Exception:  # noqa: BLE001 - never fail a regression over a name
        name = 'tiktok-ad-regression-%s-%d-%s' % (re.sub(r'[^A-Za-z0-9]+', '-', Path(package_dir).name)[:24],
                                                  os.getpid(), secrets.token_hex(3))
    return '%s-%s' % (prefix, name) if prefix else name


def run(package_dir, adapter_path, cases=None, work=None, timeout=None):
    import ad_incremental
    return ad_incremental.run(sys.modules[__name__],package_dir,adapter_path,cases,work,timeout)


def _run_uncached(package_dir, adapter_path, cases=None, work=None, timeout=None):
    """Run the regression against an unzipped package directory. Raises RegressionRefused unless all pass."""
    package_dir = Path(package_dir).resolve()
    if not (package_dir / 'game.js').is_file():
        raise RegressionRefused('ad regression: no game.js at package root ' + str(package_dir))
    adapter = load_adapter(adapter_path)
    problem = environment_problem(package_dir)
    if problem:
        raise EnvironmentIncomplete(problem)
    browser = find_browser()
    cases = list(cases or default_cases(adapter))
    unknown = [c for c in cases if c not in CASES + DOUBLE_CASES]
    if unknown:
        raise RegressionRefused('unknown ad regression cases: ' + ', '.join(unknown))
    if any(c in DOUBLE_CASES for c in cases) and 'double_claim' not in adapter:
        raise RegressionRefused('ad regression cases %s need adapter "double_claim"' % ', '.join(c for c in cases if c in DOUBLE_CASES))
    owned = work is None
    work = Path(work or tempfile.mkdtemp(prefix='tiktok-ad-regression-')).resolve()
    work.mkdir(parents=True, exist_ok=True)
    port = _free_port()
    log = work / 'host-log.jsonl'
    result_file = work / 'ad-regression-result.json'
    result_file.unlink(missing_ok=True)
    server = subprocess.Popen([sys.executable, '-B', str(TOOL / 'server.py'), str(port), str(package_dir), str(log)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    started = time.monotonic()
    try:
        _wait_port(port, server)
        boot_ms = int(adapter.get('boot_timeout_s', 60) * 1000)
        # Unique space per run: Ego taskSpace(name) RESUMES a same-name space, so two runs would drive one page.
        # 生成时预防 P21: the name comes from browser_env.space_name (<game>-<pid>-ad-regression-<random>); a set
        # AD_REGRESSION_SPACE is only a prefix now, so two sessions that both set it still get different spaces.
        space = _space_name(package_dir)
        cfg = {'space': space, 'url': 'http://127.0.0.1:%d/__host/play.html?mouse=1&ad=manual' % port,
               'sessionFile':os.environ.get('ENGLISH_CHECK_EGO_SESSION'),
               'adapter': adapter, 'cases': cases, 'bootTimeoutMs': boot_ms, 'resultFile': str(result_file),
               'progressFile': str(work / 'progress.txt')}
        entry = work / 'run-ad-regression.mjs'
        entry.write_text('globalThis.CFG = %s;\nawait import(%s);\n' % (
            json.dumps(cfg, ensure_ascii=False), json.dumps((TOOL / 'cases.mjs').as_uri())), encoding='utf-8')
        # Real need: boot + ~12 s per case on a loaded machine.
        limit = timeout or (boot_ms / 1000 + 60 + 25 * len(cases))
        try:
            # stdin closed (v7.7.5, Holly v3): an inherited open stdin pipe made ego-browser nodejs -e wait forever.
            # v7.9 (出包检查提速 S7): watched_run stops the step when nothing moved for 240 s (no output line, and no
            # change in the work folder: host log, the result cases.mjs saves after every case).
            proc = watched_run.run([browser, 'nodejs', '-e', 'await import(%s)' % json.dumps(entry.as_uri())], limit,
                                   [work])
        except watched_run.TimedOut:
            raise RegressionRefused('ad regression timed out after %d s' % limit)
        except watched_run.Stalled as stalled:
            raise RegressionRefused('ad regression stopped: %s - the browser or the game page is stuck; refused without '
                                    'waiting for the %d s limit (总表 19 ③)' % (stalled, limit))
        try:
            result = json.loads(result_file.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            tail = (proc.stdout[-400:] + proc.stderr[-400:]).strip()
            raise RegressionRefused('ad regression produced no result (browser exit %s): %s' % (proc.returncode, tail))
        if proc.returncode:result['fatal']=result.get('fatal') or 'Ego process exited %s after writing results'%proc.returncode
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
        if owned:
            shutil.rmtree(work, ignore_errors=True)
    passed, problems = judge(result, cases)
    hints = adapter_warnings(adapter)
    if not passed:
        problems = problems + hints          # shown next to the failure, where a session reads it
    summary = {'id': 'rewarded_ad_regression', 'passed': passed, 'cases': [
        dict({k: row.get(k) for k in ('case', 'ok', 'want', 'granted', 'problems')}, **({'paid': row['paid']} if 'paid' in row else {}))
        for row in result.get('cases', [])],
        'boot': result.get('boot'), 'fatal':result.get('fatal'), 'raw_files':[str(p) for p in (result_file,log) if p.is_file()],
        'warnings': (result.get('warnings') or []) + hints, 'tool_sha256': tool_digest(),
        'adapter_sha256': hashlib.sha256(Path(adapter_path).read_bytes()).hexdigest(),
        'seconds': round(time.monotonic() - started, 1)}
    # 简化.11.14 R4D: the case list is default_cases(adapter); a --cases subset is 「没跑完」, never 通过 (main()).
    summary['planned_not_run'] = planned_not_run(adapter, cases)
    summary['complete'] = not summary['planned_not_run']
    if not passed:
        error = RegressionRefused('rewarded-ad regression failed: ' + ' | '.join(problems))
        error.summary = summary
        raise error
    return summary


INCOMPLETE_EXIT = 3          # 简化.11.14 R4D: the selected cases passed, but the case list was not run to the end


def planned_not_run(adapter, cases):
    """Cases of the full list (default_cases(adapter)) that this run did not include."""
    ran = set(cases or [])
    return [c for c in default_cases(adapter if isinstance(adapter, dict) else {}) if c not in ran]


def finish(summary, code):
    """Exit code and Chinese verdict. A passing run that left planned cases out is 「没跑完」 (exit 3), not 通过."""
    if code == 0 and summary.get('planned_not_run'):
        code = INCOMPLETE_EXIT
        summary.update(passed=False, selected_passed=True, status='incomplete')
    summary['verdict'] = {0: '通过', 1: '包不通过', 2: str(summary.get('environment', ''))[:200],
                          INCOMPLETE_EXIT: '覆盖记录尚缺：%s（只补未通过项，已通过项沿用；不要重跑整套）'
                          % '、'.join(summary.get('planned_not_run') or [])}[code]
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--package', required=True, type=Path, help='unzipped TikTok package dir or .zip')
    parser.add_argument('--adapter', type=Path, default=os.environ.get(ENV_ADAPTER) or None)
    parser.add_argument('--cases', help='comma-separated subset (default: all 10, plus double_watch / double_quit / '
                                        'double_free when the adapter has double_claim)')
    parser.add_argument('--work', type=Path, help='keep host log and raw result here')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    cases = args.cases.split(',') if args.cases else None
    try:
        # v7.8 (总表 A6 补): by hand, a ZIP must carry the writer receipt for its bytes; the writers call run() on their
        # staged bytes before the receipt exists and are never asked for it.
        problem = _environment().receipt_problem(args.package) if args.package.is_file() else None
        if problem:
            raise EnvironmentIncomplete(problem)
        if args.package.is_file():
            with tempfile.TemporaryDirectory(prefix='tiktok-ad-regression-pkg-') as folder:
                with zipfile.ZipFile(args.package) as archive:
                    archive.extractall(folder)
                summary = run(folder, args.adapter, cases, args.work)
        else:
            summary = run(args.package, args.adapter, cases, args.work)
        code = 0
    except RegressionRefused as error:
        summary = getattr(error, 'summary', {'id': 'rewarded_ad_regression', 'passed': False})
        summary['error'] = str(error)
        code = 1
        if isinstance(error, EnvironmentIncomplete):
            summary.update(status='environment_incomplete', environment=str(error))
            code = 2
    code = finish(summary, code)
    if args.report:
        args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))
    print('结论: %s' % summary['verdict'], file=sys.stderr)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
