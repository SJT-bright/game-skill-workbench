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
  python3 -B runtime_regression.py trial --url http://127.0.0.1:<port>/ [--adapter <adapter.json>] [--out result.json]
  python3 -B runtime_regression.py list

v7.8 (总表 B30): suites layout_state (D) and button_sweep (E) apply to every TikTok package (new game blocks, legacy
warns, Cocos 3.x blocks only on the startup download), ad_entries (B) when the adapter has ad_entries, trial_link (F)
only with a trial link (`run --trial`, `trial --url`, serve_preview.py --keep). `run --board remake|localize` picks the
home rules (the writers pass their board). The summary lists not_run (suite, reason) and startup_measured.

v7.8 (总表 P2 补): suite popin applies to every TikTok package: 4 screens, invincible player, 18 s flight and a revive,
no obstacle may appear / vanish / jump on screen. adapter.popin is required for a new game (legacy: warning), {"n/a":
"reason"} passes a game without scrolling obstacles without a browser, Cocos 3.x only warns 「未覆盖」 (precheck()).

v7.8 (总表 P16 第 3 步): suite frame_rate applies to every TikTok package: the same operation (adapter.frame_rate) at a
60 Hz and a 120 Hz display clock, the tracked node's positions at the same real time may differ by at most 5 %.
adapter.frame_rate is required for a new game (legacy: warning), {"n/a": "reason"} passes a game where nothing moves on
its own without a browser, Cocos 3.x only warns 「未覆盖」.

v7.8 (总表 A6 补): `run` exits 0 passed, 1 包不通过 (a case failed or the run refused), 2 环境不完整 (EnvironmentIncomplete:
a Cocos package without the kit touch part, or a ZIP given here without the writer receipt for its bytes). The writers
call run() in-process on staged bytes and are never asked for a receipt; the touch check applies to both.
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
AD_KEYS = {'request', 'state', 'ready', 'exit', 'exit_label', 'no_music', 'boot_timeout_s', 'note',
           'double_claim'}   # v7.8 (Saul 10-31, W100): ad_regression double_watch / double_quit / double_free
CORE_KEYS = {'home', 'retry', 'retry_label', 'enter_level', 'host_query', 'engine', 'remake_home',
             'save_keys', 'level_timeout_s', 'runtime_note'}
PREDICATES = ('tiktok', 'rewarded_ads', 'missions', 'remake_home', 'trial_url')
# v7.8 (总表 B30): "host": "none" = the suite opens a page of its own (trial_link: CFG.trialUrl), no package host server.
# v7.8 (总表 P2 补, popin): "needs_new" = adapter fields a new game must have (missing: new game refused, legacy game
# warned and the suite not run); "na_field" = a field whose value {"n/a": "reason"} passes the suite without a browser
# (a game without scrolling obstacles); "uncovered" = {engine: why}: on that engine the suite only warns 「未覆盖」.
SIDECAR_KEYS = {'name', 'about', 'applies', 'needs', 'fields', 'engines', 'timeout_s', 'owner', 'proof', 'host',
                'needs_new', 'na_field', 'uncovered'}
BOARDS = ('remake', 'localize')
POPIN_REQUIRED = ('player', 'invincible_js', 'revive_js', 'game_node')
POPIN_OPTIONAL = {'start': list, 'first_touch': bool, 'fly_s': (int, float), 'settle_ms': int, 'after_start_js': str,
                  'ignore': str, 'ignore_groups': list, 'query': str, 'note': str}


def popin_problems(value):
    """v7.8 (总表 P2 补): what is wrong with adapter.popin, [] when it is usable. {"n/a": "reason"} is the whole block of
    a game without scrolling obstacles; otherwise the four required strings (references/runtime-regression.md)."""
    if not isinstance(value, dict):
        return ['popin must be an object']
    if 'n/a' in value:
        if set(value) != {'n/a'}:
            return ['popin {"n/a": ...} must have no other keys']
        return [] if isinstance(value['n/a'], str) and value['n/a'].strip() else ['popin "n/a" needs the reason (text)']
    out = ['popin.%s missing (a non-empty string)' % k for k in POPIN_REQUIRED
           if not (isinstance(value.get(k), str) and value[k].strip())]
    for key in sorted(set(value) - set(POPIN_REQUIRED) - set(POPIN_OPTIONAL)):
        out.append('popin has unknown key %r' % key)
    for key, kind in POPIN_OPTIONAL.items():
        if key in value and (not isinstance(value[key], kind) or (kind is not bool and isinstance(value[key], bool))):
            out.append('popin.%s has the wrong type' % key)
    if isinstance(value.get('fly_s'), (int, float)) and not 5 <= value['fly_s'] <= 60:
        out.append('popin.fly_s must be 5..60 seconds')
    if isinstance(value.get('ignore'), str):
        try:
            re.compile(value['ignore'])
        except re.error as error:
            out.append('popin.ignore is not a regular expression: %s' % error)
    return out


FRAME_RATE_REQUIRED = ('track', 'drive_js')
FRAME_RATE_OPTIONAL = {'start': list, 'prepare_js': str, 'steps': list, 'run_s': (int, float), 'settle_ms': int,
                       'min_move': (int, float), 'align': str, 'query': str, 'note': str}


def frame_rate_problems(value):
    """v7.8 (总表 P16 第 3 步): what is wrong with adapter.frame_rate, [] when it is usable. {"n/a": "reason"} is the whole
    block of a game where nothing moves on its own (no 2.4 physics, no per-frame movement); otherwise track (JS body
    returning the node or {x, y[, z]}) and drive_js (the operation, run at t0) (references/runtime-regression.md)."""
    if not isinstance(value, dict):
        return ['frame_rate must be an object']
    if 'n/a' in value:
        if set(value) != {'n/a'}:
            return ['frame_rate {"n/a": ...} must have no other keys']
        return [] if isinstance(value['n/a'], str) and value['n/a'].strip() else ['frame_rate "n/a" needs the reason (text)']
    out = ['frame_rate.%s missing (a non-empty string)' % k for k in FRAME_RATE_REQUIRED
           if not (isinstance(value.get(k), str) and value[k].strip())]
    for key in sorted(set(value) - set(FRAME_RATE_REQUIRED) - set(FRAME_RATE_OPTIONAL)):
        out.append('frame_rate has unknown key %r' % key)
    for key, kind in FRAME_RATE_OPTIONAL.items():
        if key in value and (not isinstance(value[key], kind) or isinstance(value[key], bool)):
            out.append('frame_rate.%s has the wrong type' % key)
    if isinstance(value.get('run_s'), (int, float)) and not 2 <= value['run_s'] <= 20:
        out.append('frame_rate.run_s must be 2..20 seconds')
    if value.get('align', 'move') not in ('move', 'drive'):
        out.append('frame_rate.align must be "move" (compare from the moment the node starts moving) or "drive"')
    for i, step in enumerate(value.get('steps') or [] if isinstance(value.get('steps'), list) else []):
        if not (isinstance(step, dict) and set(step) == {'at_s', 'js'} and isinstance(step['js'], str)
                and isinstance(step['at_s'], (int, float)) and not isinstance(step['at_s'], bool)
                and 0 <= step['at_s'] <= value.get('run_s', 5)):
            out.append('frame_rate.steps[%d] must be {"at_s": seconds within run_s, "js": "..."}' % i)
    return out


# na_field values the runner can judge without a browser (sidecar "na_field")
FIELD_SHAPES = {'popin': popin_problems, 'frame_rate': frame_rate_problems}


def is_na(value):
    return isinstance(value, dict) and set(value) == {'n/a'} and isinstance(value['n/a'], str) and bool(value['n/a'].strip())


class RuntimeRefused(ValueError):
    """The runtime regression could not run or did not pass; the package must not ship."""


class EnvironmentIncomplete(RuntimeRefused):
    """v7.8 (总表 A6 补): the run cannot judge the package (no touch part, or a ZIP without its writer receipt).
    Still a refusal (a subclass of RuntimeRefused), but reported as 「环境不完整」, not as 「包不通过」; the CLI exits 2."""


ENV_PREFIX = '环境不完整：'
SHARED = HERE.parents[2] / 'remake-core' / 'scripts'    # verify_native_zip (receipts), tiktok_finalize_steps (policy)
_TOUCH24 = re.compile(rb"require\(\s*['\"]\./touch-coordinates(?:\.js)?['\"]\s*\)\.install\(\s*cc\s*\)")
_TOUCH3X = re.compile(rb"require\(\s*['\"]\./tiktok-touch-3x(?:\.js)?['\"]\s*\)\.install\(")
_REQUIRE_MAIN = re.compile(rb"require\(\s*['\"]\./main(?:\.js)?['\"]\s*\)")
_TOUCH_ERROR = re.compile(r'touch coordinates|touch-coordinate probe', re.I)


def _cocos_engine(files):
    """'2.x' (legacy getTouchesByEvent converter), '3.x' (cocos-js/ or SystemJS bundle) or None."""
    if any(b'getTouchesByEvent' in (files.get(n) or b'') for n in ('cocos/cocos2d-js-min.js', 'cocos/cocos2d-js.js')):
        return '2.x'
    if any(n.startswith('cocos-js/') and n.endswith('.js') for n in files) or 'src/system.bundle.js' in files:
        return '3.x'
    return None


def kit_touch_installed(files, engine):
    """The platform-kit touch part is in the package and wired: 2.4 touch-coordinates.js installed from game.js or from
    the kit main.js that game.js loads; 3.x tiktok-touch-3x.js installed from game.js."""
    game = files.get('game.js') or b''
    if engine == '2.x':
        main_loaded = bool(_REQUIRE_MAIN.search(game))
        return 'touch-coordinates.js' in files and bool(
            _TOUCH24.search(game) or (main_loaded and _TOUCH24.search(files.get('main.js') or b'')))
    return 'tiktok-touch-3x.js' in files and bool(_TOUCH3X.search(game))


def touch_problem(files):
    """files: {relative name: bytes}. Why a real tap cannot reach this Cocos package in the host, or None.
    TikTok touches carry only screenX/screenY; Cocos reads clientX/clientY. Without a working touch fix a real tap on X /
    PLAY misses in the host and a failed case looks like a broken ad or a locked home (企鹅雪道 v4 ran the ad regression on
    an unfinished build: tiktok-touch-3x.js in the folder, not installed in game.js). The judge is the upload touch probe
    (remake-core/scripts/audit_upload_startup.py, probe_cocos2/3_touch_coordinates.cjs, the check the writers apply):
    it runs the package's own game.js prefix and engine converter. Only when it cannot run, the kit touch part being
    installed counts. Not a Cocos package -> None."""
    engine = _cocos_engine(files)
    if engine is None:
        return None
    why = None
    try:
        if str(SHARED) not in sys.path:
            sys.path.insert(0, str(SHARED))
        from audit_upload_startup import audit_files
        errors = [e for e in audit_files(files).get('errors') or [] if _TOUCH_ERROR.search(str(e))]
        if not errors:
            return None
        why = errors[0]
    except Exception as error:  # noqa: BLE001 - the probe could not run: fall back to the kit part
        if kit_touch_installed(files, engine):
            return None
        why = 'touch probe could not run (%s) and the kit touch part is not installed' % (str(error)[:200],)
    if engine == '2.x':
        kit = ("Cocos 2.x needs the kit touch-coordinates.js (root file, require('./touch-coordinates').install(cc) in "
               'game.js or in the kit main.js that game.js loads)')
    else:
        kit = ("Cocos 3.x needs the kit tiktok-touch-3x.js (root file, require('./tiktok-touch-3x.js').install(...) in game.js "
               "before require('./web-adapter'))")
    installed = 'installed' if kit_touch_installed(files, engine) else 'not installed'
    return (ENV_PREFIX + 'TikTok touches (screenX/screenY only) do not reach the engine: %s. %s; here it is %s. A real tap '
            'on X / PLAY misses in the host, so a failed case would not mean the game is broken. Finish the build first '
            '(remake-core/scripts/tiktok_finalize.py native, or write the package with build_checked_zip.py / '
            'make_tiktok_zip.py, which run this regression themselves)' % (why[:300], kit, installed))


def receipt_problem(archive):
    """A ZIP given on the command line: why it has no writer receipt for exactly its bytes (verify_native_zip.receipt_status),
    or None. The writers call run() on their own staged bytes before the receipt exists, so run() never asks for it."""
    archive = Path(archive)
    try:
        if str(SHARED) not in sys.path:
            sys.path.insert(0, str(SHARED))
        import verify_native_zip as verifier
        data = archive.read_bytes()
        with zipfile.ZipFile(archive) as z:
            file_sha256 = {i.filename: hashlib.sha256(z.read(i)).hexdigest() for i in z.infolist() if not i.is_dir()}
        status = verifier.receipt_status(archive, hashlib.sha256(data).hexdigest(), file_sha256)
    except Exception as error:  # noqa: BLE001 - an unreadable receipt state is never "official"
        return ENV_PREFIX + 'could not read the writer receipt of %s (%s)' % (archive.name, error)
    if status.get('entry') == 'official':
        return None
    return (ENV_PREFIX + 'no writer receipt beside %s for these ZIP bytes (%s). Only a ZIP written by build_checked_zip.py / '
            'make_tiktok_zip.py is a finished package; those writers run this regression on their own bytes. To diagnose '
            'another build, run on its unzipped folder' % (archive.name, status.get('entry_reason')))


def package_policy(files, policy=None):
    """-> (policy, reason): the caller's policy, else judged from the package bytes like package_gates (scene / asset
    uuids against LEGACY_GAMES.json, not listed = new; a failed decision = new, never legacy)."""
    if policy is not None:
        if policy not in ('new', 'legacy'):
            raise RuntimeRefused('runtime regression policy must be new or legacy, not %r' % (policy,))
        return policy, 'given by the caller'
    try:
        if str(SHARED) not in sys.path:
            sys.path.insert(0, str(SHARED))
        from tiktok_finalize_steps import policy as _P
        out = _P.decide(files=files)
        return out['policy'], 'judged from the package: ' + out['reason']
    except Exception as error:  # noqa: BLE001
        return 'new', 'policy decision failed (%r) -> new game' % (error,)


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
        if meta.get('host', 'package') not in ('package', 'none'):
            problems.append('"host" must be "package" or "none"')
        if not isinstance(meta.get('needs_new', []), list) or not all(isinstance(x, str) for x in meta.get('needs_new', [])):
            problems.append('"needs_new" must be a list of strings')
        if 'na_field' in meta and meta['na_field'] not in FIELD_SHAPES:
            problems.append('"na_field" must be one of ' + ', '.join(sorted(FIELD_SHAPES)))
        uncovered = meta.get('uncovered', {})
        if not isinstance(uncovered, dict) or not set(uncovered) <= {'2.x', '3.x'} or not all(
                isinstance(v, str) and v.strip() for v in uncovered.values()):
            problems.append('"uncovered" must map "2.x" / "3.x" to a reason')
        if not (folder / (name + '.mjs')).is_file():
            problems.append('missing script ' + name + '.mjs')
        if problems:
            raise RuntimeRefused('runtime suite %s: %s' % (name, '; '.join(problems)))
        meta = dict(meta)
        meta.setdefault('needs', [])
        meta.setdefault('fields', [])
        meta.setdefault('needs_new', [])
        meta.setdefault('uncovered', {})
        meta['engines'] = engines
        meta.setdefault('timeout_s', 300)
        meta.setdefault('host', 'package')
        meta['script'] = folder / (name + '.mjs')
        suites[name] = meta
    return suites


def adapter_keys(suites):
    keys = set(AD_KEYS) | CORE_KEYS
    for meta in suites.values():
        keys.update(meta['needs'])
        keys.update(meta['fields'])
        keys.update(meta.get('needs_new', []))
        if meta.get('na_field'):
            keys.add(meta['na_field'])
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


def predicate(name, files, adapter, trial_url=None):
    if name == 'tiktok':
        return 'game.js' in files
    if name == 'rewarded_ads':
        return _js_contains(files, b'createRewardedVideoAd')
    if name == 'missions':
        return any(_js_contains(files, n) for n in (b'startEntranceMission', b'addShortcut', b'navigateToScene'))
    if name == 'remake_home':
        return bool(adapter.get('remake_home'))
    if name == 'trial_url':
        return bool(trial_url)
    if name.startswith('adapter:'):
        return name[8:] in adapter
    return False


def required_suites(files, adapter, suites=None, trial_url=None):
    """files: {relative name: bytes}; adapter: dict, path or None. Suites this package must pass.
    trial_url (v7.8): the local trial link, when there is one (trial_link applies only then)."""
    suites = load_suites() if suites is None else suites
    if not isinstance(adapter, dict):
        adapter = load_adapter(adapter, suites) if adapter else {}
    engine = detect_engine(files, adapter)
    return sorted(name for name, meta in suites.items()
                  if engine in meta['engines'] and any(predicate(p, files, adapter, trial_url) for p in meta['applies']))


_NOT_RUN = {'trial_url': 'no trial link given (serve_preview.py --keep runs it before it prints the link; '
                         'runtime_regression.py trial --url <link> runs it by hand)',
            'rewarded_ads': 'no createRewardedVideoAd call in the package JavaScript',
            'missions': 'no mission / shortcut call in the package JavaScript', 'remake_home': 'adapter.remake_home is not set'}


def not_run(files, adapter, names, suites, trial_url=None):
    """[{suite, reason}] for every catalogued suite this run does not include (v7.8, 总表 B30: the summary says which
    suites did not run and why, e.g. ad_entries without adapter.ad_entries, trial_link without a trial link)."""
    if not isinstance(adapter, dict):
        adapter = {}
    engine = detect_engine(files, adapter)
    out = []
    for name, meta in sorted(suites.items()):
        if name in names:
            continue
        if engine not in meta['engines']:
            reason = 'Cocos %s not supported (engines %s)' % (engine, ', '.join(meta['engines']))
        elif any(predicate(p, files, adapter, trial_url) for p in meta['applies']):
            reason = 'applies, but not selected in this run (--suites)'
        else:
            reason = '; '.join('adapter has no "%s"' % p[8:] if p.startswith('adapter:') else _NOT_RUN.get(p, p + ' does not apply')
                               for p in meta['applies'])
        out.append({'suite': name, 'reason': reason})
    return out


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


def run_suite(name, meta, package_dir, adapter, adapter_path, engine, browser, work, timeout=None, policy=None,
              policy_reason=None, board=None, trial_url=None):
    serves = meta.get('host', 'package') != 'none'
    host = HOST3 if engine == '3.x' else HOST2
    if serves and not (host / 'server.py').is_file():
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
    port = _free_port() if serves else None
    server = subprocess.Popen([sys.executable, '-B', str(host / 'server.py'), str(port), str(package_dir), str(log)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if serves else None
    started = time.monotonic()
    try:
        if server is not None:
            _wait_port(port, server)
        cfg = {'suite': name, 'space': os.environ.get(ENV_SPACE) or 'tiktok-runtime-%s-%d-%s' % (name, os.getpid(), secrets.token_hex(3)), 'engine': engine,
               'base': 'http://127.0.0.1:%d' % port if serves else None, 'hostPage': '/__host/play.html',
               'hostQuery': 'mouse=1&run=' + name + ('&' + adapter['host_query'] if adapter.get('host_query') else ''),
               'package': str(package_dir) if package_dir else None, 'port': port, 'adapter': adapter,
               'adapterPath': str(adapter_path) if adapter_path else None,
               'bootTimeoutMs': int(adapter.get('boot_timeout_s', 60) * 1000), 'logFile': str(log),
               'resultFile': str(result_file), 'evidenceDir': str(folder), 'lib': (TOOL / 'lib.mjs').as_uri(),
               'policy': policy, 'policyReason': policy_reason, 'board': board, 'trialUrl': trial_url}
        entry = folder / 'entry.mjs'
        entry.write_text('globalThis.CFG = %s;\nawait import(%s);\n' % (
            json.dumps(cfg, ensure_ascii=False), json.dumps(meta['script'].as_uri())), encoding='utf-8')
        limit = timeout or meta['timeout_s']
        try:
            # stdin closed (v7.7.5, Holly v3): with the caller's stdin left open as a pipe, ego-browser nodejs -e
            # waited on it, the probe never wrote a line and the run timed out twice.
            proc = subprocess.run([browser, 'nodejs', '-e', 'await import(%s)' % json.dumps(entry.as_uri())],
                                  capture_output=True, text=True, timeout=limit, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            raise RuntimeRefused('runtime suite %s timed out after %d s' % (name, limit))
        try:
            result = json.loads(result_file.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            tail = ((proc.stdout or '')[-400:] + (proc.stderr or '')[-400:]).strip()
            raise RuntimeRefused('runtime suite %s produced no result (browser exit %s): %s' % (name, proc.returncode, tail))
    finally:
        if server is not None:
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


def _row(name, cases, warnings=(), problems=()):
    return {'suite': name, 'passed': not problems, 'problems': list(problems), 'cases': cases, 'warnings': list(warnings),
            'evidence': None, 'seconds': 0.0, 'browser': False}


def precheck(name, meta, adapter, engine, policy):
    """v7.8 (总表 P2 补): decide a suite without the browser when its sidecar says how. Returns a finished row, or None
    (run the suite). na_field = {"n/a": reason} passes (case n_a); an engine in "uncovered" passes with a 「未覆盖」
    warning; a needs_new field missing or a malformed na_field refuses a new game and warns on a legacy game."""
    field = meta.get('na_field')
    if field and is_na(adapter.get(field)):
        return _row(name, [{'id': 'n_a', 'passed': True, 'detail': adapter[field]['n/a']}])
    why = (meta.get('uncovered') or {}).get(engine)
    if why:
        return _row(name, [{'id': 'uncovered', 'passed': True, 'detail': why}],
                    ['%s: Cocos %s 未覆盖（只警告）：%s' % (name, engine, why)])
    problems = ['adapter has no "%s"' % k for k in meta.get('needs_new', []) if k not in adapter]
    if field and field in adapter:
        problems += FIELD_SHAPES[field](adapter[field])
    if not problems:
        return None
    text = '; '.join(problems)
    if policy == 'legacy':
        return _row(name, [{'id': 'adapter', 'passed': True, 'detail': 'legacy game: warning'}],
                    ['%s not run: %s [legacy game: warning]' % (name, text)])
    return _row(name, [{'id': 'adapter', 'passed': False, 'detail': text}], (),
                ['%s/adapter: %s (new game: write the field, see references/runtime-regression.md)' % (name, text)])


def run(package_dir, adapter_path, suites=None, work=None, timeout=None, suites_dir=None, policy=None, board=None,
        trial_url=None):
    """Run suites (default: required_suites) against an unzipped package. Raises RuntimeRefused unless all pass.
    policy: 'new' | 'legacy' for suites that warn on a legacy game (dead_shell); None = judged from the package bytes.
    v7.8 (总表 A6 补): a Cocos package without a touch part raises EnvironmentIncomplete before any suite runs.
    v7.8 (总表 B30): board 'remake' | 'localize' | None picks layout_state's home rules (None: not checked, warning);
    trial_url adds trial_link. The summary's not_run lists every catalogued suite that did not run, with the reason."""
    package_dir = Path(package_dir).resolve()
    if not (package_dir / 'game.js').is_file():
        raise RuntimeRefused('runtime regression: no game.js at package root ' + str(package_dir))
    if board is not None and board not in BOARDS:
        raise RuntimeRefused('runtime regression board must be remake or localize, not %r' % (board,))
    catalog = load_suites(suites_dir)
    adapter = load_adapter(adapter_path, catalog)
    files = package_files(package_dir)
    problem = touch_problem(files)
    if problem:
        raise EnvironmentIncomplete(problem)
    browser = find_browser()
    engine = detect_engine(files, adapter)
    policy, policy_reason = package_policy(files, policy)
    names = list(suites) if suites else required_suites(files, adapter, catalog, trial_url)
    skipped = not_run(files, adapter, names, catalog, trial_url)
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
            row = precheck(name, meta, adapter, engine, policy)
            if row is not None:
                rows.append(row)
                problems.extend(row['problems'])
                continue
            row = run_suite(name, meta, package_dir, adapter, adapter_path, engine, browser, work, timeout, policy,
                            policy_reason, board, trial_url)
            rows.append(row)
            problems.extend(row['problems'])
    finally:
        if owned:
            shutil.rmtree(work, ignore_errors=True)
    summary = {'id': 'runtime_regression', 'passed': not problems, 'engine': engine, 'suites': rows,
               'required': names, 'not_run': skipped, 'board': board, 'problems': problems, 'policy': policy,
               'policy_reason': policy_reason, 'startup_measured': _startup_measured(rows),
               'warnings': [w for r in rows for w in r['warnings']],
               'tool_sha256': tool_digest(catalog),
               'adapter_sha256': hashlib.sha256(Path(adapter_path).read_bytes()).hexdigest(),
               'seconds': round(time.monotonic() - started, 1)}
    if problems:
        error = RuntimeRefused('runtime regression failed: ' + ' | '.join(problems))
        error.summary = summary
        raise error
    return summary


def _startup_measured(rows):
    """layout_state's measured startup download {MiB, audioBytes, beforeHome, cutoff} (S8 补), or None."""
    for row in rows:
        if row.get('suite') == 'layout_state' and isinstance(row.get('evidence'), dict):
            return row['evidence'].get('startup')
    return None


def trial_smoke(url, adapter_path=None, work=None, suites_dir=None, timeout=None):
    """v7.8 (总表 B21 / B30 F): run the trial_link suite on a local trial link (no package, no host server).
    adapter_path is optional: its "trial" field names the taps to the ad and the reward reader. Returns a summary
    {passed, not_run, problems, warnings, evidence}; raises RuntimeRefused when the smoke failed (the link must not be
    given out) or could not run at all (no browser). "not run" (no ad entry known or found) passes with not_run set."""
    if not re.match(r'^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?/', str(url or '')):
        raise RuntimeRefused('trial smoke: only a local trial link (http://127.0.0.1:<port>/...) is checked, not %r' % (url,))
    catalog = load_suites(suites_dir)
    if 'trial_link' not in catalog:
        raise RuntimeRefused('trial smoke: no trial_link suite in ' + str(suites_dir or SUITES_DIR))
    adapter = load_adapter(adapter_path, catalog) if adapter_path else {}
    browser = find_browser()
    owned = work is None
    work = Path(work or tempfile.mkdtemp(prefix='tiktok-trial-smoke-')).resolve()
    work.mkdir(parents=True, exist_ok=True)
    try:
        row = run_suite('trial_link', catalog['trial_link'], None, adapter, adapter_path, adapter.get('engine') or '2.x',
                        browser, work, timeout, trial_url=url)
    finally:
        if owned:
            shutil.rmtree(work, ignore_errors=True)
    ev = row.get('evidence') or {}
    summary = {'id': 'trial_smoke', 'url': url, 'passed': row['passed'], 'not_run': ev.get('notRun'),
               'problems': row['problems'], 'warnings': row['warnings'], 'cases': row['cases'], 'evidence': ev,
               'seconds': row['seconds']}
    if not row['passed']:
        error = RuntimeRefused('trial smoke failed: ' + ' | '.join(row['problems']))
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
    r.add_argument('--policy', choices=['new', 'legacy'], help='tests and calibration only: judge the package as a new '
                   'or a legacy game (dead_shell warns on legacy). Default: from the package bytes')
    r.add_argument('--board', choices=list(BOARDS), help='layout_state home rules: remake (settings top-left, bottom row = '
                   'two platform entries) or localize (only the two platform entries). Default: not checked (warning)')
    r.add_argument('--trial', help='a local trial link: adds the trial_link suite')
    q = sub.add_parser('required')
    q.add_argument('--package', required=True, type=Path)
    q.add_argument('--adapter', type=Path, default=os.environ.get(ENV_ADAPTER) or None)
    t = sub.add_parser('trial', help='v7.8: trial-link smoke on any local link (serve_preview.py runs it before --keep prints the link)')
    t.add_argument('--url', required=True)
    t.add_argument('--adapter', type=Path, help='optional: its "trial" field names the taps to the ad (else ad-like home buttons)')
    t.add_argument('--work', type=Path)
    t.add_argument('--out', type=Path)
    sub.add_parser('list')
    args = parser.parse_args(argv)
    if args.cmd == 'trial':
        try:
            summary, code = trial_smoke(args.url, args.adapter, args.work), 0
        except RuntimeRefused as error:
            summary, code = getattr(error, 'summary', {'id': 'trial_smoke', 'passed': False}), 1
            summary['error'] = str(error)
        summary['verdict'] = '试玩链接冒烟没跑：' + summary['not_run'] if code == 0 and summary.get('not_run') else (
            '通过' if code == 0 else '不通过')
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: summary.get(k) for k in ('id', 'passed', 'not_run', 'problems', 'warnings', 'error')}, ensure_ascii=False))
        print('结论: %s' % summary['verdict'], file=sys.stderr)
        return code
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
        # v7.8 (总表 A6 补): a ZIP given by hand must be a writer's ZIP (receipt for these bytes). The writers call run()
        # on staged bytes before their receipt exists, so only this command entry asks for it.
        problem = receipt_problem(args.package) if args.package.is_file() else None
        if problem:
            raise EnvironmentIncomplete(problem)
        summary = _with_package(args.package, lambda d: run(d, args.adapter, suites, args.work, policy=args.policy,
                                                            board=args.board, trial_url=args.trial))
        code = 0
    except RuntimeRefused as error:
        summary = getattr(error, 'summary', {'id': 'runtime_regression', 'passed': False})
        summary['error'] = str(error)
        code = 1
        if isinstance(error, EnvironmentIncomplete):
            summary.update(status='environment_incomplete', environment=str(error))
            code = 2
    summary['verdict'] = {0: '通过', 1: '包不通过', 2: str(summary.get('environment', ''))[:200]}[code]
    # v7.8 (总表 B32 d): a copied / changed runtime tool says so (企鹅雪道 ran its own edited copy) and leaves a draft
    try:
        import tool_identity
        ident = tool_identity.identity(HERE)
        if ident.get('status') == 'modified':
            summary['modified_tools'] = ident['summary']
            summary['tool_feedback_draft'] = str(tool_identity.write_draft(ident, args.package.stem) or '')
            print('改过的工具: %s' % '; '.join(ident['summary']), file=sys.stderr)
    except Exception as error:  # noqa: BLE001 - reporting only
        summary['tool_identity_error'] = repr(error)[:200]
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: summary.get(k) for k in ('id', 'passed', 'status', 'engine', 'policy', 'board', 'required',
                                                  'not_run', 'startup_measured', 'problems', 'warnings', 'error')},
                     ensure_ascii=False))
    print('结论: %s' % summary['verdict'], file=sys.stderr)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
