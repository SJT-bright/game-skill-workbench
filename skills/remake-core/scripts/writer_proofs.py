#!/usr/bin/env python3
"""Explicit preparation of storage probes; writers only consume exact existing proofs.

No consume path invokes a VM, command, browser, or a check producer. Independent
proofs keep unrelated passing work when one producer's actual inputs change.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SCHEMA = 'writer-proofs.v1'
DEFAULT = Path('docs/checks/writer-evidence.json')
KINDS = ('reward-storage', 'runtime-coverage')
OPTIONS = {'clock_ms': 1761955200000, 'seed': 1, 'timezone': 'UTC'}


def digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('writer producer dependency missing/linked: ' + str(path))
    return digest(path.read_bytes())


def tree(root, suffixes):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError('writer producer artifact directory missing/linked: ' + str(root))
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('writer producer artifact contains symlink: ' + str(path))
        if path.is_file() and (suffixes is None or path.suffix in suffixes):
            result[path.relative_to(root).as_posix()] = file_sha(path)
    return result


def paths(project, native, web, coverage=None, *, require_source=True):
    project, native, web = (Path(value).resolve() for value in (project, native, web))
    source = project / ('assets' if (project / 'assets').is_dir() else 'src')
    for root in (project, native, web, source) if require_source else (project, native, web):
        if not root.is_dir():
            raise ValueError('writer producer artifact root missing: ' + str(root))
    coverage = Path(coverage).resolve() if coverage else project / 'docs/test/runtime-coverage.json'
    return {'project': project, 'native': native, 'web': web, 'source': source, 'coverage': coverage}


def options(value=None):
    result = dict(OPTIONS if value is None else value)
    if (set(result) != set(OPTIONS) or type(result['clock_ms']) is not int or result['clock_ms'] < 0
            or type(result['seed']) is not int or not 0 <= result['seed'] <= 0xffffffff
            or result['timezone'] != 'UTC'):
        raise ValueError('writer producer needs an explicit nonnegative clock, uint32 seed, and UTC timezone')
    return result


def binding(kind, roots, configured):
    configured = options(configured)
    identity = {'schema': SCHEMA, 'kind': kind,
                'roots': {name: str(path) for name, path in roots.items() if name != 'coverage'},
                'python': {'version': sys.version, 'binary_sha256': file_sha(Path(sys.executable).resolve())}}
    if kind == 'reward-storage':
        node = shutil.which('node')
        if not node:
            raise ValueError('reward-storage producer: Node executable missing')
        identity['discovery'] = {name: tree(roots[name], {'.js'}) for name in ('native', 'web')}
        identity['node'] = {'path': str(Path(node).resolve()), 'sha256': file_sha(Path(node).resolve()),
                            'options': [], 'node_path': None}
        identity['options'] = configured
        names = ['run_reward_storage_probe.py', 'probe_cocos2_reward_storage.cjs',
                 'probe_cocos2_papercut_storage.cjs', 'papercut_production_loader.cjs', 'reward_probe_clock.cjs']
    elif kind == 'runtime-coverage':
        import audit_runtime_coverage as coverage_tool
        artifact_roots = {key: roots[key] for key in ('source', 'native', 'web')}
        artifacts, sites = coverage_tool.inventory(artifact_roots)
        path = roots['coverage']
        document = json.loads(path.read_bytes())
        refs = {}
        def visit(value):
            if isinstance(value, dict):
                if isinstance(value.get('path'), str) and 'sha256' in value:
                    target = (path.parent / value['path']).resolve()
                    refs[str(target)] = file_sha(target)
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)
        visit(document)
        identity.update(artifacts=artifacts, sites=sites, coverage=str(path),
                        coverage_sha256=file_sha(path), evidence=refs)
        names = ['audit_runtime_coverage.py']
    else:
        raise ValueError('unknown writer producer: ' + str(kind))
    identity['tools'] = {name: file_sha(HERE / name) for name in [*names, 'writer_proofs.py']}
    guard = HERE.parents[1] / 'cocos-game-check/package-check/scripts/check_guard.cjs'
    identity['guard_sha256'] = file_sha(guard)
    return identity


def qa_result_passed(result, *, review_audit=False):
    """An explicit failed/incomplete result outranks an aggregate pass marker."""
    if not isinstance(result, dict):
        return False
    if ('passed' in result and result['passed'] is not True
            or 'complete' in result and result['complete'] is not True
            or 'failed' in result and (type(result['failed']) is not int or result['failed'] != 0)):
        return False
    if any(result.get(field) for field in ('error', 'errors', 'problems', 'fatal', 'proof_error',
                                           'not_run', 'planned_not_run', 'missing', 'pending')):
        return False
    if review_audit or 'status' in result:
        return result.get('status') in ('pass', 'passed', 'ready', 'test_stage_complete', 'success', 'clear', 'completed')
    return True  # Historical coverage adapters may return only their validated evidence fields.


def report_passed(kind, report, *, required_checks=None):
    if not isinstance(report, dict) or report.get('passed') is not True:
        return False
    if kind == 'runtime-coverage':
        return report.get('tool') == 'audit_runtime_coverage' and report.get('errors') == []
    if kind == 'project-qa':
        if report.get('tool') != 'project_qa_writer_evidence' or not qa_result_passed(report):
            return False
        rows = report.get('checks')
        if (not isinstance(required_checks, list) or not required_checks
                or len(required_checks) != len(set(required_checks))
                or not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows)):
            return False
        ids = [row.get('id') for row in rows]
        if (not all(isinstance(identity, str) and identity for identity in ids)
                or len(ids) != len(set(ids)) or set(ids) != set(required_checks)):
            return False
        return all(qa_result_passed(row.get('result'), review_audit=row['id'] == 'review_audit') for row in rows)
    if report.get('tool') != 'run_reward_storage_probe':
        return False
    if report.get('status') == 'not_applicable':
        return report.get('applicable') is False
    if report.get('status') != 'passed' or report.get('applicable') is not True:
        return False
    execution = report.get('execution')
    parts = execution if isinstance(execution, list) else [execution]
    return bool(parts) and all(isinstance(part, dict) and part.get('passed') is True
                               and bool(part.get('checks')) for part in parts)


def read_proof(path, kind, expected):
    path = Path(path).resolve()
    record = json.loads(path.read_bytes())
    execution = record.get('execution')
    if (record.get('schema') != SCHEMA or record.get('kind') != kind
            or record.get('binding') != expected or record.get('key') != digest(expected)
            or not isinstance(execution, dict) or execution.get('returncode') != 0
            or record.get('execution_sha256') != digest(execution)):
        raise ValueError(kind + ': producer proof missing, stale or failed: ' + str(path))
    raw = path.parent / record['raw']['path']
    if file_sha(raw) != record['raw']['sha256']:
        raise ValueError(kind + ': raw producer output missing or changed')
    if json.loads(raw.read_bytes()) != execution:
        raise ValueError(kind + ': raw producer output differs from proof')
    report = json.loads(execution['stdout'].strip().splitlines()[-1])
    if not report_passed(kind, report, required_checks=expected.get('required_checks')):
        raise ValueError(kind + ': raw output does not establish the producer result')
    return {'id': kind, 'action': 'reused', 'proof': str(path), 'key': record['key'],
            'original_at': record['executed_at'], 'original_seconds': record['seconds'],
            'raw': str(raw.resolve()), 'report': report,
            'refs': {str(path): file_sha(path), str(raw.resolve()): file_sha(raw)}}


def manifest_path(project, value=None):
    return Path(value).resolve() if value else Path(project).resolve() / DEFAULT


@contextmanager
def producer_lock(home, kind):
    """A second caller waits for this producer's original result, never duplicates it."""
    home.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(home / (kind + '-execution.sqlite3'), timeout=10, isolation_level=None)
    try:
        try:
            connection.execute('BEGIN IMMEDIATE')
        except sqlite3.OperationalError as error:
            raise ValueError(kind + ': another explicit producer owns this node; wait for its existing result') from error
        yield
    finally:
        connection.rollback()
        connection.close()


def load_manifest(project, value=None):
    path = manifest_path(project, value)
    if not path.is_file():
        raise ValueError('writer.producers: missing evidence; run writer_proofs.py prepare at the affected producer node: ' + str(path))
    document = json.loads(path.read_bytes())
    if document.get('schema') != SCHEMA or document.get('project') != str(Path(project).resolve()):
        raise ValueError('writer.producers: evidence manifest belongs to another project')
    return path, document


def store_manifest(index, document):
    with producer_lock(index.parent / 'writer-producer-proofs', 'manifest'):
        if index.is_file():
            latest = json.loads(index.read_bytes())
            if latest.get('schema') != SCHEMA or latest.get('project') != document['project']:
                raise ValueError('writer producer manifest changed identity before publication')
            proofs = dict(latest.get('proofs', {}))
            proofs.update(document.get('proofs', {}))
            document = dict(document, proofs=proofs)
        temporary = index.with_name(index.name + '.tmp-' + str(os.getpid()))
        try:
            temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
            os.replace(temporary, index)
        finally:
            temporary.unlink(missing_ok=True)


def resolve_web(project, native, web=None, evidence=None, startup_contract=None):
    if web is not None:
        return Path(web).resolve()
    _, document = load_manifest(project, evidence)
    roots = document.get('roots', {})
    if roots.get('native') != str(Path(native).resolve()):
        raise ValueError('writer.producers: existing artifact record names a different Native directory; supply the actual --web')
    web = Path(roots.get('web', ''))
    if not web.is_absolute() or not web.is_dir():
        raise ValueError('writer.producers: no exact Web path in existing producer record')
    # The receipt is an identity source, not a guessed folder/version.
    return web.resolve()


def resolve_registered_review(project, native, web):
    """Only a registered exact path can supply a nonstandard legacy review."""
    import project_qa
    entry = project_qa.project_policy(project, required_paths=[])
    reviews = (entry or {}).get('policy', {}).get('reviews', {})
    if not reviews:
        return None
    project = Path(project).resolve()
    matches = []
    for row in reviews.values():
        def target(field):
            value = Path(row[field])
            return value.resolve() if value.is_absolute() else (project / value).resolve()
        if target('native') == Path(native).resolve() and target('web') == Path(web).resolve():
            matches.append(target('review'))
    if len(set(matches)) != 1:
        raise ValueError('project-qa: registered review scope does not uniquely match the actual Native/Web')
    review = matches[0]
    if not review.is_file():
        raise ValueError('project-qa: registered original review is missing: ' + str(review))
    return review


def selected_kinds(kind, require_coverage=True):
    if kind == 'all':
        return KINDS if require_coverage else ('reward-storage',)
    if kind not in KINDS:
        raise ValueError('unknown writer producer selector: ' + str(kind))
    return (kind,)


def consume(project, native, web, coverage=None, evidence=None, *, require_coverage=True, kind='all'):
    """Verify original proof and current producer inputs. Never execute its producer."""
    index, document = load_manifest(project, evidence)
    selected = selected_kinds(kind, require_coverage)
    roots = paths(project, native, web, coverage, require_source='runtime-coverage' in selected)
    if 'options' not in document:
        raise ValueError('writer.producers: explicit clock/seed/timezone record missing')
    configured = options(document['options'])
    result = {'schema': SCHEMA, 'manifest': str(index), 'checks': [], 'refs': {str(index): file_sha(index)},
              'roots': {name: str(path) for name, path in roots.items()}, 'options': configured, 'producer_bindings': {}}
    for current in selected:
        expected = binding(current, roots, configured)
        reference = document.get('proofs', {}).get(current)
        if not isinstance(reference, dict) or not reference.get('path'):
            raise ValueError(current + ': missing producer proof; run writer_proofs.py prepare --kind ' + current)
        proof = (index.parent / reference['path']).resolve()
        if file_sha(proof) != reference.get('sha256'):
            raise ValueError(current + ': producer proof reference changed; return to this producer only')
        try:
            checked = read_proof(proof, current, expected)
        except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
            raise ValueError(current + ': existing evidence invalid; return to this producer only: ' + str(error)) from error
        result['checks'].append(checked)
        result['refs'].update(checked['refs'])
        result['producer_bindings'][current] = digest(expected)
    return result


def unchanged(result):
    for path, expected in result['refs'].items():
        if file_sha(path) != expected:
            raise ValueError('writer producer evidence changed before publication: ' + path)
    if result.get('producer_bindings'):
        roots = {name: Path(path) for name, path in result['roots'].items()}
        for kind, expected in result['producer_bindings'].items():
            if digest(binding(kind, roots, result['options'])) != expected:
                raise ValueError(kind + ': producer inputs changed before publication')
    for root, expected in result.get('qa_artifacts', {}).items():
        if tree(root, None) != expected:
            raise ValueError('project-qa: actual supplement inputs changed before publication')


def qa_binding(args, reviewed, profile):
    """The registered adapter sees these actual files; no writer hook is executed."""
    if not args.review or not Path(args.review).is_file():
        raise ValueError('project-qa: registered supplement requires its existing review artifact')
    dependencies = {**profile.get('dependencies', {}), **profile.get('trusted_files', {})}
    for field in ('path', 'writer_path'):
        if profile.get(field):
            dependencies[profile[field]] = file_sha(profile[field])
    refs = {}
    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get('path'), str) and 'sha256' in value:
                path = (Path(args.review).parent / value['path']).resolve()
                refs[str(path)] = file_sha(path)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(reviewed)
    result = {'schema': SCHEMA, 'kind': 'project-qa',
              'required_checks': ['review_audit'] + (['writer_coverage'] if profile.get('writer_path') else []),
              'project': str(Path(args.project).resolve()),
              'arguments': {key: str(Path(getattr(args, key)).resolve()) if key in ('native', 'web', 'review')
                            else str(getattr(args, key, None)) for key in ('native', 'web', 'review', 'build_tag', 'board', 'app_id')},
              'review_sha256': file_sha(args.review), 'profile_sha256': digest(profile),
              'dependencies': {name: file_sha(name) for name in dependencies}, 'evidence': refs,
              'tools': {'writer_proofs.py': file_sha(__file__), 'project_qa.py': file_sha(HERE / 'project_qa.py')},
              'artifacts': {name: tree(getattr(args, name), None) for name in ('native', 'web')}}
    for name in ('assets', 'src', 'settings', 'build-templates', '.tiktok-kit'):
        path = Path(args.project) / name
        if path.is_dir():
            result['artifacts']['project/' + name] = tree(path, None)
    for name in ('coverage', 'startup_contract', 'loading_recovery_runtime', 'resource_manifest'):
        value = getattr(args, name, None)
        if value:
            result[name] = {'path': str(Path(value).resolve()), 'sha256': file_sha(value)}
    return result


def consume_project_qa(args, reviewed, profile, evidence=None):
    index, document = load_manifest(args.project, evidence)
    reference = document.get('proofs', {}).get('project-qa')
    if not reference:
        raise ValueError('project-qa: registered supplement missing; run writer_proofs.py prepare --kind project-qa with its original review/options')
    target = (index.parent / reference['path']).resolve()
    if file_sha(target) != reference.get('sha256'):
        raise ValueError('project-qa: registered supplement proof changed')
    expected = qa_binding(args, reviewed, profile)
    checked = read_proof(target, 'project-qa', expected)
    checked['refs'][str(index)] = file_sha(index)
    checked['refs'].update(expected['dependencies'])
    checked['refs'].update(expected['evidence'])
    checked['refs'][str(Path(args.review).resolve())] = expected['review_sha256']
    checked['qa_artifacts'] = {
        str(Path(args.project) / name[8:]) if name.startswith('project/') else str(Path(getattr(args, name)).resolve()): files
        for name, files in expected['artifacts'].items()}
    return checked


def prepare_project_qa(args, reviewed, profile, evidence=None):
    index = manifest_path(args.project, evidence)
    with producer_lock(index.parent / 'writer-producer-proofs', 'project-qa'):
        return _prepare_project_qa(args, reviewed, profile, evidence)


def _prepare_project_qa(args, reviewed, profile, evidence=None):
    """Only this explicit producer may invoke the registered project supplement."""
    import project_qa
    import check_known_issues as known
    index, document = load_manifest(args.project, evidence)
    before = qa_binding(args, reviewed, profile)
    target = index.parent / 'writer-producer-proofs' / ('project-qa-' + digest(before) + '.json')
    if target.exists():
        checked = read_proof(target, 'project-qa', before)
    else:
        started = time.monotonic()
        audit_args = project_qa.adjusted_args(args, profile)
        if profile.get('legacy_context'):
            audit_args, _ = project_qa.invoke(profile, 'prepare_context', args)
        checks = []
        error = None
        try:
            extension = project_qa.invoke(profile, 'audit', audit_args, reviewed, known.binding, known.load(known.CATALOG))
            checks.append({'id': 'review_audit', 'result': extension})
            if not qa_result_passed(extension, review_audit=True):
                raise ValueError('registered review supplement did not pass')
            if profile.get('writer_path'):
                addition = project_qa.invoke(profile, 'legacy_coverage', args, Path(args.native), reviewed, HERE, field='writer_path')
                checks.append({'id': 'writer_coverage', 'result': addition})
                if not qa_result_passed(addition):
                    raise ValueError('registered writer coverage supplement did not pass')
        except (ValueError, OSError, RuntimeError, TypeError, KeyError) as exception:
            error = type(exception).__name__ + ': ' + str(exception)
        report = {'tool': 'project_qa_writer_evidence', 'passed': error is None, 'checks': checks, 'error': error}
        execution = {'command': ['project_qa.audit', 'project_qa.legacy_coverage'], 'returncode': int(error is not None),
                     'stdout': json.dumps(report, ensure_ascii=False) + '\n', 'stderr': ''}
        if qa_binding(args, reviewed, profile) != before:
            raise ValueError('project-qa: registered supplement inputs changed during execution')
        raw = target.with_suffix('.raw.json')
        with raw.open('x', encoding='utf-8') as stream:
            json.dump(execution, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        record = {'schema': SCHEMA, 'kind': 'project-qa', 'binding': before, 'key': digest(before),
                  'execution': execution, 'execution_sha256': digest(execution),
                  'raw': {'path': raw.name, 'sha256': file_sha(raw)},
                  'executed_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'seconds': round(time.monotonic() - started, 6)}
        with target.open('x', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        checked = read_proof(target, 'project-qa', before)
        checked['action'] = 'rerun'
    document['proofs'] = {'project-qa': {'path': os.path.relpath(target, index.parent), 'sha256': file_sha(target)}}
    store_manifest(index, document)
    return checked


def prepare(project, native, web, coverage=None, evidence=None, *, kind='all', configured=None):
    """Explicit producer node. Each unchanged passing producer is consumed once."""
    selected = selected_kinds(kind)
    roots = paths(project, native, web, coverage, require_source='runtime-coverage' in selected)
    configured = options(configured)
    index = manifest_path(project, evidence)
    home = index.parent / 'writer-producer-proofs'
    home.mkdir(parents=True, exist_ok=True)
    proofs = {}
    if index.is_file():
        old = json.loads(index.read_bytes())
        if old.get('schema') != SCHEMA or old.get('project') != str(roots['project']):
            raise ValueError('existing writer evidence index cannot be replaced for another project')
    checks = []
    for current in selected:
        with producer_lock(home, current):
            before = binding(current, roots, configured)
            target = home / (current + '-' + digest(before) + '.json')
            if target.exists():
                checked = read_proof(target, current, before)
            else:
                started = time.monotonic()
                command = [sys.executable, '-B', str(HERE / 'run_reward_storage_probe.py'), '--native', str(roots['native']), '--web', str(roots['web'])]
                if current == 'reward-storage':
                    env = dict(os.environ, TZ=configured['timezone'], COCOS_REWARD_PROBE_NOW_MS=str(configured['clock_ms']),
                               COCOS_REWARD_PROBE_SEED=str(configured['seed']))
                    # Explicit producers use only the recorded Node inputs. A
                    # user preload must not import unbound code into this VM.
                    env.pop('NODE_OPTIONS', None)
                    env.pop('NODE_PATH', None)
                    process = subprocess.run(command, env=env, capture_output=True, text=True)
                    execution = {'command': command, 'returncode': process.returncode,
                                 'stdout': process.stdout, 'stderr': process.stderr}
                else:
                    import audit_runtime_coverage as coverage_tool
                    errors = coverage_tool.verify(json.loads(roots['coverage'].read_bytes()),
                        {key: roots[key] for key in ('source', 'native', 'web')}, roots['coverage'].parent)
                    report = {'tool': 'audit_runtime_coverage', 'passed': not errors, 'errors': errors,
                              'boundary': 'Ownership/evidence validation only; not real platform or observation truth.'}
                    execution = {'command': ['audit_runtime_coverage.verify'], 'returncode': int(bool(errors)),
                                 'stdout': json.dumps(report) + '\n', 'stderr': ''}
                if binding(current, roots, configured) != before:
                    raise ValueError(current + ': actual producer inputs changed during execution')
                raw = target.with_suffix('.raw.json')
                with raw.open('x', encoding='utf-8') as stream:
                    json.dump(execution, stream, ensure_ascii=False, indent=2)
                    stream.write('\n')
                record = {'schema': SCHEMA, 'kind': current, 'binding': before, 'key': digest(before),
                          'execution': execution, 'execution_sha256': digest(execution),
                          'raw': {'path': raw.name, 'sha256': file_sha(raw)},
                          'executed_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'seconds': round(time.monotonic() - started, 6)}
                with target.open('x', encoding='utf-8') as stream:
                    json.dump(record, stream, ensure_ascii=False, indent=2)
                    stream.write('\n')
                # A failure is kept as raw evidence and never rewritten to pass.
                checked = read_proof(target, current, before)
                checked['action'] = 'rerun'
            proofs[current] = {'path': os.path.relpath(target, index.parent), 'sha256': file_sha(target)}
            checks.append(checked)
    document = {'schema': SCHEMA, 'project': str(roots['project']), 'roots': {name: str(path) for name, path in roots.items()},
                'options': configured, 'proofs': proofs}
    index.parent.mkdir(parents=True, exist_ok=True)
    store_manifest(index, document)
    return {'schema': SCHEMA, 'manifest': str(index), 'checks': checks,
            'boundary': 'Explicit controlled storage producers only; no browser, real ads or physical-device acceptance.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'check'])
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--native', required=True, type=Path)
    parser.add_argument('--web', required=True, type=Path)
    parser.add_argument('--coverage', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--kind', choices=['all', *KINDS, 'project-qa'], default='all')
    parser.add_argument('--review', type=Path)
    parser.add_argument('--build-tag')
    parser.add_argument('--board', choices=['localize', 'remake'])
    parser.add_argument('--app-id', '--expected-app-id', dest='app_id')
    parser.add_argument('--startup-contract', type=Path)
    parser.add_argument('--loading-recovery-runtime', type=Path)
    parser.add_argument('--resource-manifest', type=Path)
    parser.add_argument('--clock-ms', type=int, default=OPTIONS['clock_ms'])
    parser.add_argument('--seed', type=int, default=OPTIONS['seed'])
    args = parser.parse_args(argv)
    try:
        kwargs = dict(project=args.project, native=args.native, web=args.web, coverage=args.coverage, evidence=args.evidence)
        if args.kind == 'project-qa':
            import project_qa
            if not args.review:
                raise ValueError('project-qa producer requires its existing --review')
            reviewed = json.loads(args.review.read_bytes())
            profile = project_qa.review_policy(args, reviewed)
            if not profile:
                raise ValueError('project-qa: no registered supplement for this original review')
            result = (prepare_project_qa(args, reviewed, profile, args.evidence) if args.command == 'prepare'
                      else consume_project_qa(args, reviewed, profile, args.evidence))
        else:
            result = (prepare(**kwargs, kind=args.kind, configured={'clock_ms': args.clock_ms, 'seed': args.seed, 'timezone': 'UTC'})
                      if args.command == 'prepare' else consume(**kwargs, kind=args.kind))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError, IndexError) as error:
        print(json.dumps({'status': 'blocked', 'node': 'writer.producers', 'error': str(error),
                          'task_terminal': False, 'verification_scope': 'affected_or_missing_only'}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
