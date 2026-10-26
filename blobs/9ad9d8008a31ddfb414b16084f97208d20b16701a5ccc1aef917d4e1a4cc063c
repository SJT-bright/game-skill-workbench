"""Append-only reported defects and dependency-scoped executable retests.
No issues are inferred from prose or cleared by a hand-written status flag.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def paths(project):
    project = Path(project).resolve()
    if not project.is_dir():
        raise ValueError('issue ledger requires an existing --project')
    ledger = project/'docs/test/package-issues.jsonl'
    return project, ledger, ledger.with_suffix('.head.json')


@contextmanager
def editing(project):
    _, ledger, _ = paths(project)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    lock = ledger.with_suffix('.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError('issue ledger is being edited; do not reset it or overwrite its head') from error
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def _write(path, raw):
    fd, name = tempfile.mkstemp(prefix='.issue-update-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def load(project):
    project, ledger, head = paths(project)
    if not ledger.is_file() or not head.is_file():
        raise ValueError('reported-issue ledger/head missing; initialize once and register existing feedback before packaging')
    before = head.read_bytes()
    raw = ledger.read_bytes()
    anchor = json.loads(before)
    if not isinstance(anchor, dict):
        raise ValueError('invalid issue ledger head')
    if anchor.get('project') != str(project) or anchor.get('ledger_sha256') != hashlib.sha256(raw).hexdigest():
        raise ValueError('issue ledger was changed/truncated or belongs to another project')
    events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    previous = '0'*64
    for number, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError('invalid issue event')
        body = {k: v for k, v in event.items() if k != 'hash'}
        if event.get('seq') != number or event.get('previous') != previous or event.get('hash') != digest(body):
            raise ValueError('broken issue event chain')
        previous = event['hash']
    if not events or events[0].get('event') != 'init' or anchor.get('last_hash') != previous or anchor.get('events') != len(events) or head.read_bytes() != before:
        raise ValueError('issue ledger/head inconsistent or changed during read')
    return events, {'ledger_sha256': hashlib.sha256(raw).hexdigest(), 'head_sha256': hashlib.sha256(before).hexdigest()}


def append(project, kind, payload, initial=False):
    project, ledger, head = paths(project)
    with editing(project):
        if initial:
            if ledger.exists() or head.exists():
                raise ValueError('issue history already exists; initialization cannot reset it')
            events = []
        else:
            events, _ = load(project)
            current = issue_state(events)
            if kind == 'reported' and payload['id'] in current:
                raise ValueError('issue already registered')
            if kind in ('retested', 'scope_updated') and payload.get('id') not in current:
                raise ValueError('cannot retest an unknown issue')
        body = {'seq': len(events), 'previous': events[-1]['hash'] if events else '0'*64,
                'event': kind, 'payload': payload}
        events.append(dict(body, hash=digest(body)))
        raw = b''.join((json.dumps(e, ensure_ascii=False, sort_keys=True)+'\n').encode() for e in events)
        anchor = {'project': str(project), 'events': len(events), 'last_hash': events[-1]['hash'],
                  'ledger_sha256': hashlib.sha256(raw).hexdigest()}
        _write(ledger, raw)
        _write(head, json.dumps(anchor, sort_keys=True).encode())
    return events[-1]


def initialize(project):
    return append(project, 'init', {'schema': 'package_issue_events.v1'}, initial=True)


def issue_state(events):
    issues = {}
    for event in events[1:]:
        data = event['payload']
        if not isinstance(data, dict):
            raise ValueError('invalid issue event payload')
        if event['event'] == 'reported':
            if data['id'] in issues:
                raise ValueError('duplicate reported issue ID')
            issues[data['id']] = {'contract': data, 'proof': None}
        elif event['event'] == 'runner_revised' and data.get('id') in issues:
            state = issues[data['id']]
            if data.get('previous_runner') != state['contract']['runner'] or not data.get('reason'):
                raise ValueError('runner revision must preserve the previous identity and reason')
            runner = data.get('runner', {})
            if not isinstance(runner.get('path'), str) or not isinstance(runner.get('sha256'), str):
                raise ValueError('invalid revised runner identity')
            state['contract'] = dict(state['contract'], runner=runner)
            state['proof'] = None  # Revision never clears the issue; every case must execute again.
        elif event['event'] == 'retested' and data.get('id') in issues:
            issues[data['id']]['proof'] = data['proof']
        elif event['event'] == 'scope_updated' and data.get('id') in issues:
            original = issues[data['id']]['contract']
            updated = data['contract']
            if (data.get('previous_contract_signature') != digest(original)
                    or not isinstance(updated, dict) or set(updated) != set(original)
                    or any(updated.get(k) != original.get(k) for k in ('id', 'message', 'cases'))
                    or not data.get('reason', '').strip()):
                raise ValueError('issue scope revision may not erase the original report or weaken its postconditions')
            issues[data['id']] = {'contract': updated, 'proof': None}
        else:
            raise ValueError('unsupported issue event; manual closed/pass flags do not resolve defects')
    return issues


def target_hashes(native, targets):
    native = Path(native).resolve()
    result = {}
    for value in targets:
        rel = PurePosixPath(value)
        if rel.is_absolute() or any(p in ('', '.', '..') for p in rel.parts) or rel.suffix not in ('.js', '.cjs', '.mjs', '.json', '.png', '.mp3'):
            raise ValueError('issue target must be a relative production JS/JSON/PNG/MP3 dependency')
        path = (native/value).resolve()
        if not path.is_relative_to(native) or not path.is_file():
            raise ValueError('reported issue target missing: '+value)
        result[value] = sha(path)
    if not result:
        raise ValueError('reported issue needs implicated production targets')
    return result


def register(project, native, issue_id, message, targets, cases, runner):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', issue_id) or not message.strip():
        raise ValueError('issue ID/message required')
    target_hashes(native, targets)
    if not isinstance(cases, list) or not cases or any(not isinstance(c, dict) or not isinstance(c.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', c['id']) or not isinstance(c.get('assertions'), list) or not c['assertions'] for c in cases):
        raise ValueError('issue needs specific cases and postcondition assertions')
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('duplicate issue case ID')
    for case in cases:
        for assertion in case['assertions']:
            if not isinstance(assertion, dict) or assertion.get('op') not in ('eq', 'ne', 'gt', 'ge', 'lt', 'le') or not isinstance(assertion.get('path'), list) or not assertion['path'] or any(not isinstance(k, (str, int)) for k in assertion['path']):
                raise ValueError('unsupported/empty issue postcondition assertion')
    runner = Path(runner).resolve()
    if not runner.is_file() or runner.suffix not in ('.py', '.cjs', '.js', '.mjs'):
        raise ValueError('reviewed project runner must be a real Python/Node file')
    events, _ = load(project)
    if issue_id in issue_state(events):
        raise ValueError('issue already registered; do not replace its original report')
    contract = {'id': issue_id, 'message': message, 'targets': sorted(set(targets)), 'cases': cases,
                'runner': {'path': str(runner), 'sha256': sha(runner)}}
    return append(project, 'reported', contract)


def revise_runner(project, issue_id, runner, reason):
    events, _ = load(project)
    state = issue_state(events)
    if issue_id not in state or not str(reason).strip():
        raise ValueError('known issue and revision reason required')
    runner = Path(runner).resolve()
    if not runner.is_file() or runner.suffix not in ('.py', '.cjs', '.js', '.mjs'):
        raise ValueError('revised reviewed runner must be a real Python/Node file')
    previous = state[issue_id]['contract']['runner']
    replacement = {'path': str(runner), 'sha256': sha(runner)}
    if replacement == previous:
        raise ValueError('runner identity did not change')
    return append(project, 'runner_revised', {'id': issue_id, 'previous_runner': previous,
                  'runner': replacement, 'reason': str(reason)})


def assertions_pass(observed, assertions):
    outcomes = []
    for row in assertions:
        try:
            value = observed
            for key in row['path']:
                value = value[key]
            expected = row.get('value')
            op = row['op']
            if op not in ('eq', 'ne') and (type(value) not in (int, float) or type(expected) not in (int, float)):
                return None
            same = type(value) is type(expected) and value == expected
            ok = same if op == 'eq' else not same if op == 'ne' else (
                value > expected if op == 'gt' else value >= expected if op == 'ge' else
                value < expected if op == 'lt' else value <= expected)
            outcomes.append(bool(ok))
        except (KeyError, IndexError, TypeError):
            return None  # A broken harness is not a reproduced gameplay defect.
    return all(outcomes)


def revise_scope(project, native, issue_id, targets, runner, reason):
    """Append a reviewed target/runner update; retain the original defect and cases."""
    events, _ = load(project)
    state = issue_state(events)
    if issue_id not in state or not isinstance(reason, str) or not reason.strip():
        raise ValueError('scope revision needs an existing issue and an explicit reason')
    target_hashes(native, targets)
    runner = Path(runner).resolve()
    if not runner.is_file() or runner.suffix not in ('.py', '.cjs', '.js', '.mjs'):
        raise ValueError('reviewed project runner must be a real Python/Node file')
    previous = state[issue_id]['contract']
    updated = dict(previous, targets=sorted(set(targets)),
                   runner={'path': str(runner), 'sha256': sha(runner)})
    return append(project, 'scope_updated', {'id': issue_id, 'reason': reason,
        'previous_contract_signature': digest(previous), 'contract': updated})


def _ref(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha(path)}


def read_ref(ref):
    if not isinstance(ref, dict) or not isinstance(ref.get('path'), str) or not Path(ref['path']).is_file() or sha(ref['path']) != ref.get('sha256'):
        raise ValueError('issue evidence file missing/changed')
    return json.loads(Path(ref['path']).read_text())


def validate_proof(contract, ref, native):
    proof = read_ref(ref)
    runner = contract['runner']
    if not Path(runner['path']).is_file() or sha(runner['path']) != runner['sha256']:
        raise ValueError('issue runner changed; perform the affected retest again')
    current_targets = target_hashes(native, contract['targets'])
    if (proof.get('schema') != 'package_issue_retest.v1' or proof.get('issue_signature') != digest(contract)
            or proof.get('target_sha256') != current_targets):
        raise ValueError('issue retest is stale, incomplete or belongs to another defect')
    if proof.get('checker_sha256') != sha(__file__):
        raise ValueError('issue retest checker changed; regenerate affected evidence')
    if set(proof.get('cases', {})) != {c['id'] for c in contract['cases']}:
        raise ValueError('issue retest case coverage incomplete')
    roots = proof.get('executed_native_roots')
    if (not isinstance(roots, dict) or set(roots) != {'current', 'negative', 'normal'}
            or any(not isinstance(root, str) or not Path(root).is_absolute()
                   or not Path(root).is_dir() for root in roots.values())):
        raise ValueError('issue original executed Native/control roots missing or invalid')
    for case in contract['cases']:
        for kind, expected in [('current', True), ('negative', False), ('normal', True)]:
            raw = read_ref(proof['cases'][case['id']][kind])
            if raw.get('runner') != runner or raw.get('case') != case['id'] or raw.get('harness_error'):
                raise ValueError('issue raw execution identity/harness invalid')
            if raw.get('executed_native_root') != roots[kind]:
                raise ValueError('issue raw executed Native identity mismatch')
            executed_root = Path(roots[kind]).resolve()
            artifacts = raw.get('artifacts', {})
            if set(artifacts) != set(contract['targets']):
                raise ValueError('issue raw production coverage incomplete')
            for target, artifact in artifacts.items():
                path = Path(artifact['path'])
                if not path.is_file() or sha(path) != artifact.get('sha256'):
                    raise ValueError('issue production artifact missing/changed')
                expected_path = (executed_root/target).resolve()
                if not expected_path.is_relative_to(executed_root) or path.resolve() != expected_path:
                    raise ValueError('issue artifact differs from the original executed Native target')
                # Retain the original execution and compare its bytes with this
                # candidate. A directory name alone is not a production change.
                if kind == 'current' and artifact.get('sha256') != current_targets[target]:
                    raise ValueError('current Native targets differ from the actual issue execution')
            actual = assertions_pass(raw.get('observed'), case['assertions'])
            if actual is None or actual != expected:
                raise ValueError('issue %s/%s postconditions not verified' % (case['id'], kind))
    return proof


def retest(project, native, issue_id, negative_native, normal_native, output):
    events, _ = load(project)
    state = issue_state(events)
    if issue_id not in state:
        raise ValueError('unknown reported issue')
    contract = state[issue_id]['contract']
    runner = contract['runner']
    if sha(runner['path']) != runner['sha256']:
        raise ValueError('reviewed issue runner changed')
    output = Path(output).resolve()
    if output.exists() or any(output.is_relative_to(Path(tree).resolve()) for tree in (native, negative_native, normal_native)):
        raise ValueError('retest output must be new and outside all Native/control trees')
    output.mkdir(parents=True)
    proof = {'schema': 'package_issue_retest.v1', 'issue_signature': digest(contract),
             'checker_sha256': sha(__file__), 'target_sha256': target_hashes(native, contract['targets']),
             'executed_native_roots': {kind: str(Path(tree).resolve()) for kind, tree in
                 [('current', native), ('negative', negative_native), ('normal', normal_native)]}, 'cases': {}}
    try:
        for case in contract['cases']:
            refs = {}
            for kind, tree in [('current', native), ('negative', negative_native), ('normal', normal_native)]:
                tree = Path(tree).resolve()
                before_targets = target_hashes(tree, contract['targets'])
                program = sys.executable if Path(runner['path']).suffix == '.py' else __import__('shutil').which('node')
                if not program:
                    raise ValueError('issue runner runtime unavailable')
                result = subprocess.run([program, runner['path'], '--native', str(tree), '--case', case['id']], capture_output=True, text=True, timeout=120)
                if before_targets != target_hashes(tree, contract['targets']) or sha(runner['path']) != runner['sha256']:
                    raise ValueError('issue production targets/runner changed during retest')
                raw = json.loads(result.stdout)
                if result.returncode or not isinstance(raw, dict) or not isinstance(raw.get('observed'), dict) or raw.get('harness_error'):
                    raise ValueError('issue runner failed; not a valid defect negative control')
                raw.update(runner=runner, case=case['id'], harness_error=False,
                           executed_native_root=str(tree),
                           artifacts={name: _ref(tree/name) for name in contract['targets']})
                path = output/(case['id']+'-'+kind+'.json')
                path.write_text(json.dumps(raw, ensure_ascii=False, indent=2))
                refs[kind] = _ref(path)
            proof['cases'][case['id']] = refs
        path = output/'retest.json'
        path.write_text(json.dumps(proof, ensure_ascii=False, indent=2))
        ref = _ref(path)
        validate_proof(contract, ref, native)
        append(project, 'retested', {'id': issue_id, 'proof': ref})
        return ref
    except (ValueError, OSError, subprocess.TimeoutExpired):
        # Keep failed observations for repair; no success event is appended.
        raise


def audit(project, native):
    events, binding = load(project)
    issues = issue_state(events)
    checked = []
    for issue_id, state in issues.items():
        if state['proof'] is None:
            raise ValueError('reported issue has no passed retest: '+issue_id)
        try:
            proof = validate_proof(state['contract'], state['proof'], native)
        except (ValueError, KeyError, TypeError, OSError) as error:
            raise ValueError('reported issue %s blocks packaging: %s' % (issue_id, error)) from error
        executed_root = proof['executed_native_roots']['current']
        current_root = str(Path(native).resolve())
        checked.append({'id': issue_id, 'proof': state['proof'], 'target_sha256': proof['target_sha256'],
                        'executed_native_root': executed_root, 'current_native_root': current_root,
                        'dependency_bytes_reused': executed_root != current_root})
    return {'passed': True, **binding, 'checked_issues': checked, 'scope': 'Registered defects only; no unrelated gameplay/level/art CI replay.'}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['init', 'report', 'revise-scope', 'retest', 'check'])
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--native', type=Path)
    ap.add_argument('--id')
    ap.add_argument('--message', default='')
    ap.add_argument('--targets', nargs='+')
    ap.add_argument('--cases', type=Path)
    ap.add_argument('--runner', type=Path)
    ap.add_argument('--negative-native', type=Path)
    ap.add_argument('--normal-native', type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        if a.command == 'init':
            result = initialize(a.project)
        elif a.command == 'report':
            result = register(a.project, a.native, a.id, a.message, a.targets, json.loads(a.cases.read_text()), a.runner)
        elif a.command == 'revise-scope':
            result = revise_scope(a.project, a.native, a.id, a.targets, a.runner, a.message)
        elif a.command == 'retest':
            result = retest(a.project, a.native, a.id, a.negative_native, a.normal_native, a.out)
        else:
            result = audit(a.project, a.native)
        print(json.dumps({'status': 'passed', 'result': result}, ensure_ascii=False))
    except (ValueError, TypeError, KeyError, OSError, subprocess.TimeoutExpired) as error:
        print(json.dumps({'status': 'refuse', 'error': str(error)}, ensure_ascii=False))
        raise SystemExit(1)
