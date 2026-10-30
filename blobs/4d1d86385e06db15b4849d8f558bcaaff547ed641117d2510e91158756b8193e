#!/usr/bin/env python3
"""Mandatory pre-package rewarded-ad regression (TikTok, engine-generic).

Runs the 10 rewarded-ad cases (200 s video, playback after 16 s, background 200 s during
playback / loading, close midway, error, show failure, never starts, starts but never calls
back then X, normal) against the package's REAL game.js inside the simulated TikTok host,
in the Ego browser. After each case it checks: reward count, no pending ad, no lock, music
resumed, and that an immediate second request starts and pays its reward.

The only game-specific input is the adapter JSON (see remake-ads/references/
ad-timeout-and-regression.md). The regression fails closed: no browser, no adapter, a boot
failure or a missing result is a refusal, never a pass.

  python3 -B ad_regression.py --package <unzipped dir or .zip> --adapter <adapter.json> [--report out.json]
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = Path(__file__).resolve().parent
TOOL = HERE / 'ad_regression'
CASES = ['long200', 'late16', 'bgplay', 'bgload', 'cancel', 'error', 'showfail', 'hang', 'nocallback', 'normal']
ENV_ADAPTER = 'TIKTOK_AD_REGRESSION_ADAPTER'
ENV_BROWSER = 'EGO_BROWSER'
_which = shutil.which  # patch point for tests; shutil.which itself is shared
ADAPTER_KEYS = {'request', 'state', 'ready', 'exit', 'exit_label', 'no_music', 'boot_timeout_s', 'note'}


class RegressionRefused(ValueError):
    """The regression could not run or did not pass; the package must not ship."""


def needs_regression(files):
    """files: {relative name: bytes}. True when the package can request a rewarded video."""
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
    unknown = set(adapter) - allowed_adapter_keys()
    if unknown:
        raise RegressionRefused('ad regression adapter has unknown keys: ' + ', '.join(sorted(unknown)))
    for key in ('state', 'ready', 'exit', 'exit_label'):
        if key in adapter and not isinstance(adapter[key], str):
            raise RegressionRefused('ad regression adapter "%s" must be a string' % key)
    return adapter


def find_browser():
    browser = os.environ.get(ENV_BROWSER) or _which('ego-browser')
    if not browser or not Path(browser).exists():
        raise RegressionRefused('rewarded-ad regression needs the Ego browser (ego-browser CLI not found); '
                                'package refused instead of skipping the ad regression')
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
    h.update(Path(__file__).read_bytes())
    return h.hexdigest()


def run(package_dir, adapter_path, cases=None, work=None, timeout=None):
    """Run the regression against an unzipped package directory. Raises RegressionRefused unless all pass."""
    package_dir = Path(package_dir).resolve()
    if not (package_dir / 'game.js').is_file():
        raise RegressionRefused('ad regression: no game.js at package root ' + str(package_dir))
    adapter = load_adapter(adapter_path)
    browser = find_browser()
    cases = list(cases or CASES)
    unknown = [c for c in cases if c not in CASES]
    if unknown:
        raise RegressionRefused('unknown ad regression cases: ' + ', '.join(unknown))
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
        space = os.environ.get('AD_REGRESSION_SPACE') or 'tiktok-ad-regression-%d-%s' % (os.getpid(), secrets.token_hex(3))
        cfg = {'space': space, 'url': 'http://127.0.0.1:%d/__host/play.html?mouse=1&ad=manual' % port,
               'adapter': adapter, 'cases': cases, 'bootTimeoutMs': boot_ms, 'resultFile': str(result_file)}
        entry = work / 'run-ad-regression.mjs'
        entry.write_text('globalThis.CFG = %s;\nawait import(%s);\n' % (
            json.dumps(cfg, ensure_ascii=False), json.dumps((TOOL / 'cases.mjs').as_uri())), encoding='utf-8')
        # Real need: boot + ~12 s per case on a loaded machine.
        limit = timeout or (boot_ms / 1000 + 60 + 25 * len(cases))
        try:
            proc = subprocess.run([browser, 'nodejs', '-e', 'await import(%s)' % json.dumps(entry.as_uri())],
                                  capture_output=True, text=True, timeout=limit)
        except subprocess.TimeoutExpired:
            raise RegressionRefused('ad regression timed out after %d s' % limit)
        try:
            result = json.loads(result_file.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            tail = (proc.stdout[-400:] + proc.stderr[-400:]).strip()
            raise RegressionRefused('ad regression produced no result (browser exit %s): %s' % (proc.returncode, tail))
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
    summary = {'id': 'rewarded_ad_regression', 'passed': passed, 'cases': [
        {k: row.get(k) for k in ('case', 'ok', 'want', 'granted', 'problems')} for row in result.get('cases', [])],
        'boot': result.get('boot'), 'warnings': result.get('warnings') or [], 'tool_sha256': tool_digest(),
        'adapter_sha256': hashlib.sha256(Path(adapter_path).read_bytes()).hexdigest(),
        'seconds': round(time.monotonic() - started, 1)}
    if not passed:
        error = RegressionRefused('rewarded-ad regression failed: ' + ' | '.join(problems))
        error.summary = summary
        raise error
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--package', required=True, type=Path, help='unzipped TikTok package dir or .zip')
    parser.add_argument('--adapter', type=Path, default=os.environ.get(ENV_ADAPTER) or None)
    parser.add_argument('--cases', help='comma-separated subset (default: all 10)')
    parser.add_argument('--work', type=Path, help='keep host log and raw result here')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    cases = args.cases.split(',') if args.cases else None
    try:
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
    if args.report:
        args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
