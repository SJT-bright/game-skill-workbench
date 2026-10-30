#!/usr/bin/env python3
"""Mandatory pre-package runtime regression runner (TikTok, Cocos 2.x and 3.x).

Runs runtime suites (v7.5: startup faults, network log, fps timing validity) against the package's
REAL game.js inside the strict simulated TikTok host, in the Ego browser. Each suite is one
`runtime_regression/suites/<name>.mjs` script plus a `<name>.json` sidecar (contract:
runtime_regression/README.md). The only game-specific input is the adapter JSON: the v7.4
rewarded-ad adapter extended with the optional runtime fields listed in
references/runtime-regression.md.

Fail closed: no browser, no adapter, an adapter field a required suite needs, a suite that
writes no result, or any failed case is a refusal, never a skip. Warnings never refuse.

  python3 -B runtime_regression.py run --package <unzipped dir or .zip> --adapter <adapter.json>
      [--suites a,b] [--out result.json] [--work dir]
  python3 -B runtime_regression.py required --package <dir> --adapter <adapter.json>
  python3 -B runtime_regression.py list
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
TOOL = HERE / 'runtime_regression'
SUITES_DIR = TOOL / 'suites'
HOST2 = HERE / 'ad_regression'          # Cocos 2.x strict host (host.js, play.html, server.py)
HOST3 = TOOL / 'host3x'                 # Cocos 3.x strict host (host.js, play.html, server.py)
ENV_ADAPTER = 'TIKTOK_AD_REGRESSION_ADAPTER'   # one adapter file serves ad + runtime regression
ENV_BROWSER = 'EGO_BROWSER'
ENV_SPACE = 'RUNTIME_REGRESSION_SPACE'   # optional Ego task-space name; default is unique per run (taskSpace(name) resumes a same-name space)
_which = shutil.which  # patch point for tests
# Keys of the v7.4 rewarded-ad adapter (ad_regression.ADAPTER_KEYS) plus runtime core keys.
AD_KEYS = {'request', 'state', 'ready', 'exit', 'exit_label', 'no_music', 'boot_timeout_s', 'note'}
CORE_KEYS = {'home', 'retry', 'retry_label', 'enter_level', 'host_query', 'engine', 'remake_home',
             'save_keys', 'level_timeout_s', 'runtime_note'}
PREDICATES = ('tiktok', 'rewarded_ads', 'missions', 'remake_home')
SIDECAR_KEYS = {'name', 'about', 'applies', 'needs', 'fields', 'engines', 'timeout_s', 'owner', 'proof'}


class RuntimeRefused(ValueError):
    """The runtime regression could not run or did not pass; the package must not ship."""


# ---------------------------------------------------------------- suites

def load_suites(folder=None):
    """Read every suites/<name>.json sidecar. Returns {name: meta}. A malformed sidecar refuses."""
    folder = Path(folder or SUITES_DIR)
    suites = {}
    for side in sorted(folder.glob('*.json')):
        try:
            meta = json.loads(side.read_text(encoding='utf-8'))
        except ValueError as error:
            raise RuntimeRefused('runtime suite sidecar unreadable %s: %s' % (side.name, error))
        name = side.stem
        problems = []
        if not isinstance(meta, dict):
            raise RuntimeRefused('runtime suite sidecar %s must be an object' % side.name)
        if meta.get('name') != name:
            problems.append('"name" must equal the file stem')
        unknown = set(meta) - SIDECAR_KEYS
        if unknown:
            problems.append('unknown keys ' + ', '.join(sorted(unknown)))
        applies = meta.get('applies')
        if not isinstance(applies, list) or not applies:
            problems.append('"applies" must be a nonempty list')
        else:
            for p in applies:
                if not (p in PREDICATES or (isinstance(p, str) and p.startswith('adapter:') and len(p) > 8)):
                    problems.append('unknown applies predicate %r' % p)
        for key in ('needs', 'fields'):
            if not isinstance(meta.get(key, []), list) or not all(isinstance(x, str) for x in meta.get(key, [])):
                problems.append('"%s" must be a list of strings' % key)
        engines = meta.get('engines', ['2.x', '3.x'])
        if not isinstance(engines, list) or not set(engines) <= {'2.x', '3.x'} or not engines:
            problems.append('"engines" must be a subset of ["2.x", "3.x"]')
        if not isinstance(meta.get('timeout_s', 300), int) or meta.get('timeout_s', 300) <= 0:
            problems.append('"timeout_s" must be a positive integer')
        if not (folder / (name + '.mjs')).is_file():
            problems.append('missing script ' + name + '.mjs')
        if problems:
            raise RuntimeRefused('runtime suite %s: %s' % (name, '; '.join(problems)))
        meta = dict(meta)
        meta.setdefault('needs', [])
        meta.setdefault('fields', [])
        meta['engines'] = engines
        meta.setdefault('timeout_s', 300)
        meta['script'] = folder / (name + '.mjs')
        suites[name] = meta
    return suites


def adapter_keys(suites):
    keys = set(AD_KEYS) | CORE_KEYS
    for meta in suites.values():
        keys.update(meta['needs'])
        keys.update(meta['fields'])
    return keys


def load_adapter(path, suites=None):
    if not path:
        raise RuntimeRefused('runtime regression required: pass the adapter JSON (--adapter, check_package '
                             '--ad-regression, or $%s)' % ENV_ADAPTER)
    try:
        adapter = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise RuntimeRefused('runtime regression adapter unreadable: %s' % error)
    if not isinstance(adapter, dict):
        raise RuntimeRefused('runtime regression adapter must be a JSON object')
    unknown = set(adapter) - adapter_keys(load_suites() if suites is None else suites)
    if unknown:
        raise RuntimeRefused('runtime regression adapter has unknown keys: ' + ', '.join(sorted(unknown)))
    for key in ('home', 'retry', 'retry_label', 'enter_level', 'host_query', 'ready', 'state'):
        if key in adapter and not isinstance(adapter[key], str):
            raise RuntimeRefused('runtime regression adapter "%s" must be a string' % key)
    if 'engine' in adapter and adapter['engine'] not in ('2.x', '3.x'):
        raise RuntimeRefused('runtime regression adapter "engine" must be "2.x" or "3.x"')
    return adapter


def detect_engine(files, adapter=None):
    """'3.x' for Cocos Creator 3.x (SystemJS bundle), else '2.x'. The adapter may pin it."""
    if adapter and adapter.get('engine'):
        return adapter['engine']
    names = set(files)
    if 'src/system.bundle.js' in names or any(re.search(r'(^|/)cocos-js/cc(\.[0-9a-f]+)?\.js$', n) for n in names):
        return '3.x'
    return '2.x'


def _js_contains(files, needle):
    return any(name.endswith('.js') and needle in data for name, data in files.items())


def predicate(name, files, adapter):
    if name == 'tiktok':
        return 'game.js' in files
    if name == 'rewarded_ads':
        return _js_contains(files, b'createRewardedVideoAd')
    if name == 'missions':
        return any(_js_contains(files, n) for n in (b'startEntranceMission', b'addShortcut', b'navigateToScene'))
    if name == 'remake_home':
        return bool(adapter.get('remake_home'))
    if name.startswith('adapter:'):
        return name[8:] in adapter
    return False


def required_suites(files, adapter, suites=None):
    """files: {relative name: bytes}; adapter: dict, path or None. Suites this package must pass."""
    suites = load_suites() if suites is None else suites
    if not isinstance(adapter, dict):
        adapter = load_adapter(adapter, suites) if adapter else {}
    engine = detect_engine(files, adapter)
    return sorted(name for name, meta in suites.items()
                  if engine in meta['engines'] and any(predicate(p, files, adapter) for p in meta['applies']))


def package_files(package_dir):
    root = Path(package_dir)
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob('*')) if p.is_file()}


# ---------------------------------------------------------------- run

def find_browser():
    browser = os.environ.get(ENV_BROWSER) or _which('ego-browser')
    if not browser or not Path(browser).exists():
        raise RuntimeRefused('runtime regression needs the Ego browser (ego-browser CLI not found); '
                             'package refused instead of skipping the runtime regression')
    return browser


def judge(result, suite):
    """Pure verdict over one suite result {suite, passed, cases:[{id, passed, detail}], evidence}."""
    if not isinstance(result, dict):
        return False, [suite + ': no result']
    problems = []
    if result.get('suite') != suite:
        problems.append('%s: result names suite %r' % (suite, result.get('suite')))
    if result.get('fatal'):
        problems.append('%s: aborted: %s' % (suite, result['fatal']))
    cases = [c for c in result.get('cases') or [] if isinstance(c, dict)]
    if not cases:
        problems.append(suite + ': no cases ran')
    for case in cases:
        if case.get('passed') is not True:
            problems.append('%s/%s: %s' % (suite, case.get('id'), _short(case.get('detail')) or 'not passed'))
    if result.get('passed') is not True and not problems:
        problems.append(suite + ': suite reported passed=%r' % result.get('passed'))
    return not problems, problems


def _short(detail):
    if detail is None:
        return ''
    text = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)
    return text[:300]


def _free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _wait_port(port, proc, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeRefused('runtime regression host server exited early')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeRefused('runtime regression host server did not start')


def tool_digest(suites):
    h = hashlib.sha256()
    for path in sorted(list(HOST2.glob('*.js')) + list(HOST2.glob('*.py')) + list(HOST2.glob('*.html')) +
                       list(TOOL.glob('*.mjs')) + list(HOST3.glob('*'))):
        if path.is_file():
            h.update(path.name.encode() + b'\0' + path.read_bytes())
    for name in sorted(suites):
        h.update(name.encode() + b'\0' + suites[name]['script'].read_bytes())
    h.update(Path(__file__).read_bytes())
    return h.hexdigest()


def run_suite(name, meta, package_dir, adapter, adapter_path, engine, browser, work, timeout=None):
    host = HOST3 if engine == '3.x' else HOST2
    if not (host / 'server.py').is_file():
        raise RuntimeRefused('runtime regression: no %s host at %s' % (engine, host))
    missing = [k for k in meta['needs'] if k not in adapter]
    if missing:
        raise RuntimeRefused('runtime suite %s needs adapter field(s) %s' % (name, ', '.join(missing)))
    folder = work / name
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / 'host-log.jsonl'
    result_file = folder / 'result.json'
    for f in (log, result_file):
        f.unlink(missing_ok=True)
    port = _free_port()
    server = subprocess.Popen([sys.executable, '-B', str(host / 'server.py'), str(port), str(package_dir), str(log)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    started = time.monotonic()
    try:
        _wait_port(port, server)
        cfg = {'suite': name, 'space': os.environ.get(ENV_SPACE) or 'tiktok-runtime-%s-%d-%s' % (name, os.getpid(), secrets.token_hex(3)), 'engine': engine,
               'base': 'http://127.0.0.1:%d' % port, 'hostPage': '/__host/play.html',
               'hostQuery': 'mouse=1&run=' + name + ('&' + adapter['host_query'] if adapter.get('host_query') else ''),
               'package': str(package_dir), 'port': port, 'adapter': adapter, 'adapterPath': str(adapter_path),
               'bootTimeoutMs': int(adapter.get('boot_timeout_s', 60) * 1000), 'logFile': str(log),
               'resultFile': str(result_file), 'evidenceDir': str(folder), 'lib': (TOOL / 'lib.mjs').as_uri()}
        entry = folder / 'entry.mjs'
        entry.write_text('globalThis.CFG = %s;\nawait import(%s);\n' % (
            json.dumps(cfg, ensure_ascii=False), json.dumps(meta['script'].as_uri())), encoding='utf-8')
        limit = timeout or meta['timeout_s']
        try:
            proc = subprocess.run([browser, 'nodejs', '-e', 'await import(%s)' % json.dumps(entry.as_uri())],
                                  capture_output=True, text=True, timeout=limit)
        except subprocess.TimeoutExpired:
            raise RuntimeRefused('runtime suite %s timed out after %d s' % (name, limit))
        try:
            result = json.loads(result_file.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            tail = ((proc.stdout or '')[-400:] + (proc.stderr or '')[-400:]).strip()
            raise RuntimeRefused('runtime suite %s produced no result (browser exit %s): %s' % (name, proc.returncode, tail))
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
    passed, problems = judge(result, name)
    return {'suite': name, 'passed': passed, 'problems': problems,
            'cases': [{k: c.get(k) for k in ('id', 'passed', 'detail')} for c in result.get('cases') or [] if isinstance(c, dict)],
            'warnings': result.get('warnings') or [], 'evidence': result.get('evidence'),
            'seconds': round(time.monotonic() - started, 1)}


def run(package_dir, adapter_path, suites=None, work=None, timeout=None, suites_dir=None):
    """Run suites (default: required_suites) against an unzipped package. Raises RuntimeRefused unless all pass."""
    package_dir = Path(package_dir).resolve()
    if not (package_dir / 'game.js').is_file():
        raise RuntimeRefused('runtime regression: no game.js at package root ' + str(package_dir))
    catalog = load_suites(suites_dir)
    adapter = load_adapter(adapter_path, catalog)
    browser = find_browser()
    files = package_files(package_dir)
    engine = detect_engine(files, adapter)
    names = list(suites) if suites else required_suites(files, adapter, catalog)
    unknown = [n for n in names if n not in catalog]
    if unknown:
        raise RuntimeRefused('unknown runtime suites: ' + ', '.join(unknown))
    if not names:
        raise RuntimeRefused('runtime regression: no suite applies (the startup suite applies to every TikTok package)')
    owned = work is None
    work = Path(work or tempfile.mkdtemp(prefix='tiktok-runtime-regression-')).resolve()
    work.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    rows, problems = [], []
    try:
        for name in names:
            meta = catalog[name]
            if engine not in meta['engines']:
                raise RuntimeRefused('runtime suite %s does not support Cocos %s' % (name, engine))
            row = run_suite(name, meta, package_dir, adapter, adapter_path, engine, browser, work, timeout)
            rows.append(row)
            problems.extend(row['problems'])
    finally:
        if owned:
            shutil.rmtree(work, ignore_errors=True)
    summary = {'id': 'runtime_regression', 'passed': not problems, 'engine': engine, 'suites': rows,
               'required': names, 'problems': problems,
               'warnings': [w for r in rows for w in r['warnings']],
               'tool_sha256': tool_digest(catalog),
               'adapter_sha256': hashlib.sha256(Path(adapter_path).read_bytes()).hexdigest(),
               'seconds': round(time.monotonic() - started, 1)}
    if problems:
        error = RuntimeRefused('runtime regression failed: ' + ' | '.join(problems))
        error.summary = summary
        raise error
    return summary


def _with_package(path, fn):
    path = Path(path)
    if path.is_file():
        with tempfile.TemporaryDirectory(prefix='tiktok-runtime-regression-pkg-') as folder:
            with zipfile.ZipFile(path) as archive:
                archive.extractall(folder)
            return fn(Path(folder))
    return fn(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--package', required=True, type=Path, help='unzipped TikTok package dir or .zip')
    r.add_argument('--adapter', type=Path, default=os.environ.get(ENV_ADAPTER) or None)
    r.add_argument('--suites', help='comma-separated suites (default: every required suite)')
    r.add_argument('--work', type=Path, help='keep host logs, entries and raw suite results here')
    r.add_argument('--out', type=Path)
    q = sub.add_parser('required')
    q.add_argument('--package', required=True, type=Path)
    q.add_argument('--adapter', type=Path, default=os.environ.get(ENV_ADAPTER) or None)
    sub.add_parser('list')
    args = parser.parse_args(argv)
    if args.cmd == 'list':
        for name, meta in load_suites().items():
            print('%-18s %-8s applies=%s needs=%s  %s' % (name, ','.join(meta['engines']), ','.join(meta['applies']),
                                                       ','.join(meta['needs']) or '-', meta.get('about', '')))
        return 0
    if args.cmd == 'required':
        print(json.dumps(_with_package(args.package, lambda d: required_suites(package_files(d), args.adapter))))
        return 0
    suites = args.suites.split(',') if args.suites else None
    try:
        summary = _with_package(args.package, lambda d: run(d, args.adapter, suites, args.work))
        code = 0
    except RuntimeRefused as error:
        summary = getattr(error, 'summary', {'id': 'runtime_regression', 'passed': False})
        summary['error'] = str(error)
        code = 1
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: summary.get(k) for k in ('id', 'passed', 'engine', 'required', 'problems', 'warnings', 'error')},
                     ensure_ascii=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
