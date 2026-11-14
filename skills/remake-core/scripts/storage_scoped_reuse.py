"""Reuse an original STORAGE-01 observation through a reviewed dependency scope.

No extension-based exemption and no runner replay. A producer seals immutable
old bytes once. Consumers retain the original binding and compare every scoped
input, original raw record, rule, runner and helper identity. Unknown files need
an ownership update, never a full-game fallback.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
SCHEMA = 'storage_dependency_receipt.v1'
PROFILE = 'storage_dependency_scope.v1'
MANDATORY = {'.js', '.mjs', '.cjs', '.ts', '.json', '.fire', '.scene', '.prefab', '.meta', '.wasm'}
_TOKEN = object()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def approval_identity(report):
    return {k: v for k, v in report.items() if k not in ('trace', 'trace_sha256', 'storage_scope', 'storage_scope_status')}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def read(path):
    return json.loads(Path(path).read_bytes())


def file_sha(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('storage scope: missing or linked file: ' + str(path))
    return digest(path.read_bytes())


def snapshot(root, source=False):
    from audit_mobile_input import snapshot as source_snapshot
    from check_known_issues import tree_sha
    root = Path(root).resolve()
    if source:
        names, _, identity = source_snapshot(root)
    else:
        names = {}
        for path in sorted(root.rglob('*')):
            rel = path.relative_to(root)
            if path.name == '.DS_Store' or '__MACOSX' in rel.parts:
                continue
            if path.is_symlink():
                raise ValueError('storage scope: linked artifact: ' + str(path))
            if path.is_file():
                names[rel.as_posix()] = file_sha(path)
        identity = tree_sha(root)
    if not names:
        raise ValueError('storage scope: empty actual artifact: ' + str(root))
    return names, identity


def tool_identity():
    return {p: file_sha(HERE / p) for p in ('storage_scoped_reuse.py',
        'audit_native_storage_contract.py', 'maintenance_scope.py',
        'startup_storage_consumers.py', 'scan_storage_consumers.cjs',
        'startup_business_contract.py', 'numeric_snapshot_contract.py', 'vendor/acorn.cjs')}


# Exact formal 11.17.29 lineage. Original observations are still rejudged by the
# current validator; only these audited producer/rule changes are compatible.
REVIEWED_FORMAL29_TOOLS = {'storage_scoped_reuse.py': '6a58e411590495ace5a05025dc7bef8866ee8af3fd1be3fe567388cb3c67f826', 'audit_native_storage_contract.py': '3703a36dbc934e5a84787a411ca4d3275be189e9dcc022db4be727ba022dab30', 'maintenance_scope.py': '0c4147f64a9a32e4f27b2a30257d86193bbbcfffe7abb07dc5db0ee276daa391', 'startup_storage_consumers.py': '3c832d4be8447f87e177cf27102d6374bf2b28ec684f389ca4ac68608d454ed8', 'scan_storage_consumers.cjs': 'b31e37f94db9c47d0646fbfcf5f9a394e99e27b3a28ec8b1d5c9b995ea9f4805', 'startup_business_contract.py': 'c8600b73ea380b841e5d7d9065b4053a35c76a7dff8bf1ac8f6b9d42173ee007', 'numeric_snapshot_contract.py': '8b94ca6a0fc899c0e7401a1cb6df413d561d1f295436aff9c36dda0d6951fabe', 'vendor/acorn.cjs': 'fdb08546776ec6228b03e8d02b40d4ab3255bae5f401adba7ff5dad927ac5c9c'}

def compatible_tool_identity(previous, current):
    if previous == current:
        return True
    changed = {'storage_scoped_reuse.py', 'audit_native_storage_contract.py', 'maintenance_scope.py'}
    return (previous == REVIEWED_FORMAL29_TOOLS and set(previous) == set(current)
            and all(previous[name] == current[name] for name in previous if name not in changed))


def profile(project):
    import project_qa
    policy = project_qa.lookup(project, 'validators', PROFILE)
    if Path(policy['path']).suffix != '.py':
        raise ValueError('storage scope: dependency helper must be a reviewed Python validator')
    return policy


def safe_name(value):
    p = PurePosixPath(value)
    if (not isinstance(value, str) or not value or p.is_absolute() or '..' in p.parts
            or '\\' in value or ':' in value or any(ch in value for ch in '*?[')):
        raise ValueError('storage scope: exact artifact-relative input required: ' + str(value))
    return p.as_posix()


def validate_scope(scope, manifests):
    if (not isinstance(scope, dict) or scope.get('schema') != PROFILE
            or scope.get('complete') is not True or not isinstance(scope.get('basis'), str)
            or not scope['basis'].strip() or scope.get('unknown') != []):
        raise ValueError('storage scope_required: reviewed helper must resolve every actual read domain')
    inputs = scope.get('inputs')
    names = scope.get('artifact_names')
    if not isinstance(inputs, dict) or set(inputs) != set(manifests) or not isinstance(names, dict):
        raise ValueError('storage scope_required: source/package inputs and full artifact_names required')
    for role, inventory in manifests.items():
        selected = inputs[role]
        if (not isinstance(selected, list) or not selected or len(set(selected)) != len(selected)
                or sorted(names.get(role, [])) != sorted(inventory)):
            raise ValueError('storage scope_required: complete original file inventory required: ' + role)
        selected = {safe_name(name) for name in selected}
        if not selected <= set(inventory):
            raise ValueError('storage scope_required: selected dependency missing from ' + role)
        required = {name for name in inventory if PurePosixPath(name).suffix.lower() in MANDATORY}
        if not required <= selected:
            raise ValueError('storage scope_required: mandatory code/data/scene inputs omitted: ' + str(sorted(required - selected)))
    raw = scope.get('raw_evidence')
    if not isinstance(raw, list) or not raw:
        raise ValueError('storage scope_required: actual dependency derivation evidence required')
    return scope


def all_refs(trace):
    """Preserve the original reference closure, not a new approval or new hashes."""
    found = set()
    base = Path(trace.get('trace_base', '.')).resolve()
    todo = [trace]
    seen_json = set()
    while todo:
        value = todo.pop()
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, str) and key in ('runner', 'bundle', 'adapter', 'raw_report'):
                    p = Path(item)
                    if not p.is_absolute():
                        p = base / p
                    if p.is_file():
                        found.add(p.resolve())
                elif key == 'path' and isinstance(item, str) and isinstance(value.get('sha256'), str):
                    p = Path(item)
                    if not p.is_absolute():
                        p = base / p
                    if file_sha(p) != value['sha256']:
                        raise ValueError('storage scope: original referenced evidence changed: ' + str(p))
                    p = p.resolve(); found.add(p)
                todo.append(item)
        elif isinstance(value, list):
            todo.extend(value)
        for path in list(found - seen_json):
            seen_json.add(path)
            if path.suffix.lower() == '.json':
                try:
                    todo.append(read(path))
                except (ValueError, UnicodeError):
                    pass
    return sorted(found)


class _Projection:
    def __init__(self, token, record, home, native, project):
        if token is not _TOKEN:
            raise ValueError('storage projection requires a verified scope record')
        self.record, self.home = record, home
        self.native, self.project = Path(native).resolve(), Path(project).resolve()
        self.source_snapshot = home / 'source'

    def native_identity(self, native, binding):
        if (Path(native).resolve() != Path(self.record['origin_native']).resolve()
                or binding != self.record['original_binding']):
            raise ValueError('storage scope: original artifact identity mismatch')
        return self.record['original_binding']['native_tree_sha256']


def home_path(project, report, native=None, *, tools=None):
    run = report.get('execution_receipt', {}).get('run_id')
    if not isinstance(run, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,120}', run):
        raise ValueError('storage scope: original approval run_id missing')
    target = str(Path(native or report['native']).resolve())
    revision = digest(canonical({'native': target, 'tools': tool_identity() if tools is None else tools, 'helper': profile(project)}))[:24]
    return Path(project).resolve() / 'docs/checks/storage-scopes' / run / revision


def seal_approval(report, trace, native, project, *, baseline_native=None, baseline_source=None):
    # Reuse the existing cross-process/thread project owner. The second caller
    # sees the original result after the first commit; it never runs the helper.
    from preparation_cache import project_lock
    with project_lock(project):
        return _seal_approval(report, trace, native, project,
            baseline_native=baseline_native, baseline_source=baseline_source)


def _seal_approval(report, trace, native, project, *, baseline_native=None, baseline_source=None):
    """Producer-only registration. Explicit old snapshots support post-art migration."""
    import audit_native_storage_contract as gate
    import project_qa
    project, native = Path(project).resolve(), Path(native).resolve()
    native_old = Path(baseline_native or native).resolve()
    source_old = Path(baseline_source or trace.get('project', project)).resolve()
    old_binding = trace.get('binding')
    if (report.get('passed') is not True or report.get('failed') != 0
            or report.get('binding') != old_binding or report.get('required_cases') != list(gate.CASES)
            or report.get('policy_version') != gate.POLICY_VERSION
            or report.get('execution_receipt', {}).get('identity', {}).get('trace_sha256') != gate.canonical_sha(trace)):
        raise ValueError('storage scope: an actual complete original approval is required')
    home = home_path(project, report, native)
    if (home / 'scope.json').is_file():
        record = read(home / 'scope.json')
        verify_record(record, home, native, project, report, trace)
        return {'path': str(home / 'scope.json'), 'sha256': file_sha(home / 'scope.json')}
    manifests, identities = {}, {}
    for role, root in (('source', source_old), ('package', native_old)):
        manifests[role], identities[role] = snapshot(root, role == 'source')
    if (identities['source'] != old_binding.get('source_sha256')
            or identities['package'] != old_binding.get('native_tree_sha256')):
        raise ValueError('storage scope_required: preserved Source/Native do not match the original binding')
    policy = profile(project)
    helper = project_qa.module(policy, 'storage_scope_helper')
    if not hasattr(helper, 'storage_dependency_scope'):
        raise ValueError('storage scope_required: reviewed helper lacks storage_dependency_scope')
    tools = tool_identity()
    scope = validate_scope(helper.storage_dependency_scope(project=project, native=native_old,
        source=source_old, trace=trace, binding=old_binding), manifests)
    refs = all_refs(trace)
    for ref in scope['raw_evidence']:
        path = Path(ref['path'])
        if not path.is_absolute():
            path = project / path
        if file_sha(path) != ref.get('sha256'):
            raise ValueError('storage scope: dependency derivation evidence changed')
        refs.append(path.resolve())
    home.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.storage-scope-', dir=home.parent))
    try:
        for role, root in (('source', source_old), ('package', native_old)):
            for name, expected in manifests[role].items():
                dest = temporary / role / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                data = (root / name).read_bytes()
                if digest(data) != expected:
                    raise ValueError('storage scope: original artifact moved during registration')
                dest.write_bytes(data)
        evidence = {}
        for path in sorted(set(refs)):
            data = path.read_bytes(); identity = digest(data)
            name = 'evidence/' + identity + path.suffix
            (temporary / 'evidence').mkdir(exist_ok=True)
            (temporary / name).write_bytes(data)
            evidence[str(path)] = {'path': name, 'sha256': identity}
        record = {'schema': SCHEMA, 'original_binding': old_binding,
            'origin_native': str(Path(report['native']).resolve()),
            'origin_project': str(Path(trace['project']).resolve()),
            'current_native': str(native), 'current_project': str(project),
            'manifests': manifests, 'scope': scope, 'helper': policy,
            'tools': tools, 'trace': trace, 'report': report,
            'trace_sha256': gate.canonical_sha(trace),
            'report_sha256': digest(canonical(approval_identity(report))), 'evidence': evidence,
            'original_at': report['execution_receipt']['verified_at'],
            'registered_at': datetime.now(timezone.utc).isoformat()}
        # Verify current mandatory inputs and original execution before any commit.
        current = current_inputs(record, native, project)
        projection = _Projection(_TOKEN, record, temporary, native, project)
        errors = gate.validate(trace, Path(record['origin_native']), old_binding, _scope=projection)
        errors.extend(gate.validate_execution_receipt(report, trace))
        if errors:
            raise ValueError('storage scope: original approval invalid: ' + '; '.join(errors))
        if tools != tool_identity() or profile(project) != policy:
            raise ValueError('storage scope: rules/helper changed during registration')
        if current_inputs(record, native, project) != current:
            raise ValueError('storage scope: current dependencies changed during registration')
        record['key'] = digest(canonical(record))
        (temporary / 'scope.json').write_bytes(canonical(record) + b'\n')
        if home.exists():
            raise ValueError('storage scope: another producer registered this approval; consume its record')
        temporary.rename(home)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return {'path': str(home / 'scope.json'), 'sha256': file_sha(home / 'scope.json')}


def current_inputs(record, native, project):
    result = {}
    for role, root in (('source', project), ('package', native)):
        inventory, _ = snapshot(root, role == 'source')
        if set(inventory) != set(record['manifests'][role]):
            changes = sorted(set(inventory) ^ set(record['manifests'][role]))
            raise ValueError('storage scope_required: file ownership changed in ' + role + ': ' + repr(changes))
        selected = record['scope']['inputs'][role]
        changed = [name for name in selected if inventory.get(name) != record['manifests'][role].get(name)]
        if changed:
            raise ValueError('storage.native.contract: affected dependencies require only this node: ' + role + ':' + repr(changed))
        result[role] = {name: inventory[name] for name in selected}
    return result


def verify_record(record, home, native, project, report, trace):
    import audit_native_storage_contract as gate
    if (record.get('schema') != SCHEMA or record.get('key') != digest(canonical({k: v for k, v in record.items() if k != 'key'}))
            or record.get('trace_sha256') != gate.canonical_sha(trace)
            or record.get('report_sha256') != digest(canonical(approval_identity(report)))
            or record.get('original_binding') != report.get('binding')):
        raise ValueError('storage scope: immutable original approval changed')
    if (Path(record['current_project']).resolve() != Path(project).resolve()
            or Path(record['current_native']).resolve() != Path(native).resolve()):
        raise ValueError('storage scope: current artifact path differs; explicitly register its actual roots')
    if not compatible_tool_identity(record['tools'], tool_identity()) or record['helper'] != profile(project):
        raise ValueError('storage scope_required: storage rules, runner policy or helper changed')
    validate_scope(record['scope'], record['manifests'])
    for role in ('source', 'package'):
        actual, identity = snapshot(home / role, role == 'source')
        key = 'source_sha256' if role == 'source' else 'native_tree_sha256'
        if actual != record['manifests'][role] or identity != record['original_binding'][key]:
            raise ValueError('storage scope: original frozen artifact missing or changed: ' + role)
    for ref in record['evidence'].values():
        if file_sha(home / ref['path']) != ref['sha256']:
            raise ValueError('storage scope: original raw evidence missing or changed')
    current_inputs(record, native, project)


def validate_report(report, native, expected_binding, *, project):
    if report.get('profile') == 'creator1_first_platform_release.v1':
        from creator1_storage_contract import consume
        return consume(report, native, expected_binding, project)
    """Read-only real consumer entry. Returns errors; never runs a helper or VM."""
    import audit_native_storage_contract as gate
    try:
        if (report.get('tool') != 'audit_native_storage_contract' or report.get('passed') is not True
                or report.get('failed') != 0 or report.get('policy_version') != gate.POLICY_VERSION
                or report.get('required_cases') != list(gate.CASES) or type(report.get('checked')) is not int
                or report['checked'] < 1):
            raise ValueError('storage original approval is failed, incomplete or inconsistent')
        trace_path = Path(report['trace'])
        if file_sha(trace_path) != report.get('trace_sha256'):
            raise ValueError('storage original trace missing or changed')
        trace = read(trace_path)
        native = Path(native).resolve()
        if (report.get('binding') == expected_binding
                and Path(report['native']).resolve() == native):
            return gate.validate(trace, native, expected_binding) + gate.validate_execution_receipt(report, trace)
        # Build labels and a separately produced Web tree are not Native
        # storage dependencies. Exact original Source + Native bytes need no
        # newly prepared scope or new execution, even if those metadata differ.
        old = report.get('binding', {})
        if (project is not None and old.get('source_sha256')
                and all(old.get(k) == expected_binding.get(k) for k in ('source_sha256', 'native_tree_sha256'))):
            from check_known_issues import tree_sha, snapshot as source_snapshot
            origin = Path(report['native']).resolve()
            if (tree_sha(native) == old['native_tree_sha256']
                    and source_snapshot(Path(project).resolve())[2] == old['source_sha256']
                    and origin.is_dir() and tree_sha(origin) == old['native_tree_sha256']):
                return gate.validate(trace, origin, old) + gate.validate_execution_receipt(report, trace)
        if project is None:
            raise ValueError('storage scope_required: actual current source project required')
        project = Path(project).resolve()
        home = home_path(project, report, native)
        if not (home / 'scope.json').is_file():
            # The producer's immutable path included its exact tool identities.
            # Resolve only the audited formal29 revision, then verify all original
            # bytes, current dependencies and the same reviewed helper below.
            predecessor = home_path(project, report, native, tools=REVIEWED_FORMAL29_TOOLS)
            if (predecessor / 'scope.json').is_file():
                home = predecessor
        record = read(home / 'scope.json')
        verify_record(record, home, native, project, report, trace)
        from check_known_issues import tree_sha, snapshot as source_snapshot
        if (tree_sha(native) != expected_binding.get('native_tree_sha256')
                or source_snapshot(project)[2] != expected_binding.get('source_sha256')):
            raise ValueError('storage scope: requested current binding differs from actual artifacts')
        # The original observation stays original. Only aggregate identities use
        # the preserved baseline; every executable/data dependency is unchanged.
        projection = _Projection(_TOKEN, record, home, native, project)
        errors = gate.validate(trace, Path(record['origin_native']), record['original_binding'], _scope=projection)
        errors.extend(gate.validate_execution_receipt(report, trace))
        return errors
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        return ['storage.native.contract scope_required: ' + str(exc)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=['prepare'])
    for name in ('report', 'project', 'native'):
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--baseline-native', type=Path)
    p.add_argument('--baseline-source', type=Path)
    args = p.parse_args()
    try:
        report = read(args.report); trace = read(report['trace'])
        value = seal_approval(report, trace, args.native, args.project,
            baseline_native=args.baseline_native, baseline_source=args.baseline_source)
        print(json.dumps({'status': 'scope_registered', 'original_at': report['execution_receipt']['verified_at'],
            'scope': value, 'game_executed': False, 'helper_executed_only_if_new': True}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'scope_required', 'node': 'storage.native.contract',
            'error': str(exc), 'next': 'Restore the original artifacts/evidence or complete the reviewed dependency helper; continue this node only.'}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
