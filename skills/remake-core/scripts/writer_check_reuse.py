"""Bounded reuse of writer checks. Final ZIP / CLI verification never uses this cache.

Native audit reuse is restricted to one writer invocation and re-reads all package,
source-preparation, kit and process dependencies before returning its original result.
Persistence coverage is a pure file validator. The reward VM is only memoized when
its real output says not_applicable; applicable probes have an unbound clock today.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
SCHEMA = 'writer-check-reuse.v1'


def digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def file_state(path):
    p = Path(path)
    if p.is_symlink():
        # No silently followed link can extend a declared dependency root.
        raise ValueError('writer reuse dependency contains symlink: ' + str(p))
    if not p.exists():
        return {'missing': True}
    if not p.is_file():
        return {'directory': True}
    return {'sha256': digest(p.read_bytes())}


def tree_state(root, suffixes=None, skip=()):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        return {'@root': file_state(root)}
    out = {}
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if set(rel.parts) & set(skip):
            continue
        if p.is_symlink():
            raise ValueError('writer reuse dependency contains symlink: ' + str(p))
        if p.is_file() and (suffixes is None or p.suffix in suffixes):
            out[rel.as_posix()] = file_state(p)
    return out


def environment():
    node = shutil.which('node')
    # Store only a digest, never values of credentials in environment variables.
    return {'env_sha256': digest(dict(os.environ)), 'python': sys.version,
            'python_binary': file_state(Path(sys.executable).resolve()),
            'node': str(Path(node).resolve()) if node else None,
            'node_binary': file_state(Path(node).resolve()) if node else None}


def tools_state():
    # Includes dynamically imported gate modules and their non-Python helpers.
    return {'scripts': tree_state(HERE, {'.py', '.cjs', '.js', '.mjs', '.json'}, {'__pycache__'}),
            'kit': tree_state(HERE.parent/'assets/platform-kit'),
            'guard': file_state(HERE.parents[1]/'cocos-game-check/package-check/scripts/check_guard.cjs')}


def native_identity(native, board, policy, context):
    import package_gates
    from package_gates import audio
    known = ('network', 'mission', 'startup', 'webp', 'ads_static', 'adapter_fix', 'kit_parts', 'tiktok_compat',
             'portrait', 'secrets', 'audio', 'sound')
    if package_gates.GATE_MODULES != known:
        raise ValueError('unregistered Native gate dependencies; perform the actual audit')
    context = context or {}
    if set(context) - {'writer', 'finalize_record', 'project', 'finalize_options'}:
        raise ValueError('unknown external Native audit dependency')
    project = Path(context['project']).resolve() if context.get('project') else None
    source = {}
    if project:
        # This canonical read-only validator also re-binds preparation's external
        # OCR images and peer project inputs. Do not duplicate or cache that logic.
        import tiktok_finalize
        if tiktok_finalize.check_source_record(project, options=context.get('finalize_options')):
            raise ValueError('source preparation is not current; perform the actual audit')
        # K5 reads all three source trees; kit_parts also reads platform config,
        # policy and source receipts; audio/sound read board/type/silent records.
        source = {n: tree_state(project/n) for n in ('assets', 'settings', 'build-templates', '.tiktok-kit')}
        source['docs/audio'] = tree_state(project/'docs/audio')
        source.update({n: file_state(project/n) for n in ('package.json', 'project.json', 'docs/board.txt')})
    ffmpeg = audio.find_ffmpeg()
    return {'native_root': str(Path(native).resolve()), 'files': tree_state(native),
            'project': str(project) if project else None, 'source': source,
            'board': board, 'policy': policy, 'context': json.loads(json.dumps(context, default=str)),
            'ffmpeg': str(Path(ffmpeg).resolve()) if ffmpeg else None,
            'ffmpeg_binary': file_state(Path(ffmpeg).resolve()) if ffmpeg else None,
            'tools': tools_state(), 'environment': environment()}


class NativeAuditMemo:
    """No process-global or persistent Native verdict. A changed hook invalidates reuse."""
    def __init__(self):
        self.key = None
        self.result = None
        self.proof = None

    def run(self, native, board, policy, context, check):
        started = time.monotonic()
        try:
            before = native_identity(native, board, policy, context)
        except (OSError, ValueError, TypeError):
            # Unknown dependencies mean normal validation, never an assumed pass.
            return check(native, board, policy, context)
        key = digest(before)
        if self.key == key:
            result = copy.deepcopy(self.result)
            result[2]['audit_reuse'] = dict(self.proof, reused=True,
                current_binding_seconds=round(time.monotonic()-started, 6))
            return result
        executed = time.monotonic()
        result = check(native, board, policy, context)
        if native_identity(native, board, policy, context) != before:
            raise ValueError('Native audit inputs changed during validation; prepare the affected candidate again')
        proof = {'schema': SCHEMA, 'reused': False, 'binding_sha256': key,
                 'original_executed_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                 'original_seconds': round(time.monotonic()-executed, 6)}
        result[2]['audit_reuse'] = dict(proof)
        # Refused candidates are not stored as a positive result.
        if not result[0]:
            self.key, self.result, self.proof = key, copy.deepcopy(result), proof
        return result


def command_identity(kind, native, web, source=None, coverage=None):
    inputs = {'native_root': str(Path(native).resolve()), 'web_root': str(Path(web).resolve())}
    if kind == 'reward-storage':
        # Discovery visits ALL JS, including new files; settings.js is among them.
        inputs.update(native=tree_state(native, {'.js'}), web=tree_state(web, {'.js'}))
        names = ['run_reward_storage_probe.py', 'probe_cocos2_reward_storage.cjs',
                 'probe_cocos2_papercut_storage.cjs', 'papercut_production_loader.cjs']
    elif kind == 'runtime-coverage':
        import audit_runtime_coverage as coverage_tool
        roots = {'source': Path(source).resolve(), 'native': Path(native).resolve(), 'web': Path(web).resolve()}
        # Use precisely the validator's discovery function (including its new-file
        # and ignored-directory semantics), not a second approximation.
        inputs['artifacts'], inputs['sites'] = coverage_tool.inventory(roots)
        path = Path(coverage).resolve()
        raw = path.read_bytes()
        doc = json.loads(raw)
        refs = {}
        def visit(obj):
            if isinstance(obj, dict):
                if isinstance(obj.get('path'), str) and 'sha256' in obj:
                    target = (path.parent/obj['path']).resolve()
                    refs[str(target)] = file_state(target)
                for value in obj.values(): visit(value)
            elif isinstance(obj, list):
                for value in obj: visit(value)
        visit(doc)
        inputs.update(source_root=str(roots['source']), coverage=str(path), coverage_sha256=digest(raw), evidence=refs)
        names = ['audit_runtime_coverage.py']
    else:
        raise ValueError('unknown writer check: ' + kind)
    return {'schema': SCHEMA, 'kind': kind, 'inputs': inputs, 'environment': environment(),
            'tools': {name: file_state(HERE/name) for name in [*names, 'writer_check_reuse.py']},
            'guard': file_state(HERE.parents[1]/'cocos-game-check/package-check/scripts/check_guard.cjs')}


def run_command(project, kind, command, *, native, web, source=None, coverage=None):
    """One process owns a named writer check; followers read its finished evidence."""
    if kind not in ('reward-storage', 'runtime-coverage'):
        raise ValueError('unknown writer check: '+kind)
    home = Path(project)/'docs/checks/writer-check-reuse'
    try:
        home.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(home/(kind+'-execution-lock.sqlite3'), timeout=10, isolation_level=None)
    except (OSError, sqlite3.Error):
        # Missing telemetry storage cannot suppress a necessary actual check.
        return subprocess.run(command, capture_output=True, text=True)
    try:
        try:
            db.execute('BEGIN IMMEDIATE')
        except sqlite3.OperationalError as error:
            raise ValueError(kind+': another writer owns this check; wait for its existing result, do not duplicate it') from error
        return _run_command(project, kind, command, native=native, web=web, source=source, coverage=coverage)
    finally:
        db.rollback()
        db.close()


def _run_command(project, kind, command, *, native, web, source=None, coverage=None):
    """Preserve the actual subprocess output. Missing identity falls back to the real check."""
    started = time.monotonic()
    identity_args = dict(native=native, web=web, source=source, coverage=coverage)
    def binding():
        value = command_identity(kind, **identity_args)
        value['command'] = list(map(str, command))
        value['command_script'] = file_state(Path(command[1]).resolve())
        return value
    try:
        before = binding()
    except (OSError, ValueError, TypeError):
        return subprocess.run(command, capture_output=True, text=True)
    key = digest(before)
    home = Path(project)/'docs/checks/writer-check-reuse'
    record = home/(kind+'-'+key+'.json')
    try:
        stored = json.loads(record.read_text())
        payload = stored['execution']
        if (stored.get('schema') == SCHEMA and stored.get('binding_sha256') == key
                and stored.get('execution_sha256') == digest(payload)
                and payload.get('returncode') == 0):
            report = json.loads(payload['stdout'].strip().splitlines()[-1])
            allowed = report.get('passed') is True and (kind == 'runtime-coverage' or report.get('status') == 'not_applicable')
            if allowed:
                result = subprocess.CompletedProcess(command, payload['returncode'], payload['stdout'], payload['stderr'])
                result.check_reuse = {'schema': SCHEMA, 'reused': True, 'record': str(record),
                    'original_executed_at': stored['executed_at'], 'original_seconds': stored['seconds'],
                    'binding_seconds': round(time.monotonic()-started, 6)}
                return result
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        pass
    executed = time.monotonic()
    result = subprocess.run(command, capture_output=True, text=True)
    elapsed = round(time.monotonic()-executed, 6)
    if binding() != before:
        raise ValueError(kind+': inputs changed during execution; result cannot certify the new bytes')
    result.check_reuse = {'schema': SCHEMA, 'reused': False, 'seconds': elapsed}
    try:
        report = json.loads(result.stdout.strip().splitlines()[-1])
        allowed = result.returncode == 0 and report.get('passed') is True and (
            kind == 'runtime-coverage' or report.get('status') == 'not_applicable')
        if allowed:
            payload = {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
            row = {'schema': SCHEMA, 'binding_sha256': key, 'execution': payload, 'execution_sha256': digest(payload),
                   'executed_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'seconds': elapsed}
            home.mkdir(parents=True, exist_ok=True)
            tmp = record.with_name(record.name+'.'+uuid.uuid4().hex+'.tmp')
            try:
                tmp.write_text(json.dumps(row, ensure_ascii=False, indent=2)+'\n')
                os.replace(tmp, record)
            finally:
                tmp.unlink(missing_ok=True)
            result.check_reuse['record'] = str(record)
    except (OSError, ValueError, TypeError, IndexError):
        # Statistics/cache failure is not a validation failure. The real verdict remains.
        pass
    return result
