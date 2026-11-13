"""Register immutable old startup observations and consume their exact dependency scope.

Only a reviewed project scope helper may derive a closed request domain from the
original runner trace. Consumers never invoke that helper or a browser. Missing
ownership is a scope repair, never permission to rerun the whole game.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile

import audit_native_startup_renderer as renderer
import check_ledger as cl
import native_startup_ledger as startup
import project_qa
from preparation_cache import serialized

SCHEMA = 'native-startup-scoped-evidence.v1'
PROVIDER = 'startup_dependency_scope.v1'
CHECK_ID = 'startup.native.dependency_scope'
HOME = Path('docs/checks/startup-scoped')
MANDATORY = {'.js', '.cjs', '.mjs', '.ts', '.json', '.wasm', '.html', '.plist', '.xml'}
COVERAGE = {'entry', 'adapter', 'renderer', 'home', 'first_input', 'retry'}


def load(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_name(name):
    if (not isinstance(name, str) or not name or '\\' in name or ':' in name
            or PurePosixPath(name).is_absolute() or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('startup scope has unsafe relative file: ' + str(name))
    return name


def files(root, *, source=False):
    root = Path(root).resolve()
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('startup dependency tree contains symlink: ' + str(path))
    return cl.manifest(root, project=source)


def fingerprint():
    # Bind the actual validator and consumers, not only scheduling text.
    return cl.tool_fingerprint([__file__, renderer.__file__, startup.__file__,
        Path(__file__).with_name('audit_startup_contract.py'),
        Path(__file__).with_name('audit_final_package_startup.py')])


def policy_identity(proof, native, project):
    conditions, tools = startup.identity(proof, native, project)
    provider = project_qa.lookup(project, 'validators', PROVIDER)
    return {'startup': conditions, 'startup_tools': tools, 'provider': provider,
            'scope_tools': fingerprint()}


def original_record(proof, original_native, project, binding, preserved_native):
    conditions, tools = startup.identity(proof, original_native, project)
    conditions['native_tree_sha256'] = binding['native_tree_sha256']
    store = cl.Ledger(project)
    try:
        matches = [row for row in store.previous(startup.CHECK_ID)
                   if row['binding']['conditions'] == conditions]
        if not matches:
            raise ValueError('startup scope needs the original passing registered execution')
        # Preserve the original old tools/key. Current semantic validation below
        # rejudges the actual frozen replay output, so a scheduling/tool update
        # does not force another browser run. A newer failure still wins.
        row = matches[0]
        if (not row.get('passed') or row.get('error') or not store._evidence_valid(row)
                or row['result'].get('original_binding') != binding or not row['result'].get('raw_evidence')):
            raise ValueError('startup scope original execution/binding is incomplete')
        for candidate in row['result']['raw_evidence']:
            path = Path(candidate)
            if not path.is_file(): continue
            try: actual = load(path)
            except (ValueError, OSError): continue
            if (not isinstance(actual, dict) or actual.get('schema') != 'native_startup_renderer.v1'
                    or actual.get('execution', {}).get('registered_runner') != proof['execution']['registered_runner']
                    or actual.get('control_profile') != proof.get('control_profile')):
                continue
            renderer.registered_execution(actual, original_native, project)
            errors = renderer.validate(actual, preserved_native, binding, project)
            if not errors:
                return row, actual, path
        raise ValueError('startup original frozen replay does not satisfy current renderer semantics')
    finally:
        store.close()


def references(document, base, project):
    """Read every hashed reference reachable from the original JSON evidence."""
    result = {}
    pending = [(document, Path(base))]
    seen = set()
    while pending:
        value, parent = pending.pop()
        if isinstance(value, dict):
            if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
                path = Path(value['path'])
                possibilities = [path] if path.is_absolute() else [parent / path, Path(project) / path]
                path = next((p.resolve() for p in possibilities if p.is_file()), possibilities[0].resolve())
                if path.is_symlink() or not path.is_file() or sha(path) != value['sha256']:
                    raise ValueError('startup original evidence missing or changed: ' + str(path))
                result[str(path)] = value['sha256']
                if str(path) not in seen and path.suffix.lower() == '.json':
                    seen.add(str(path))
                    pending.append((load(path), path.parent))
            pending.extend((child, parent) for child in value.values())
        elif isinstance(value, list):
            pending.extend((child, parent) for child in value)
    return result


def derive_scope(provider, roots, proof, raw, binding, project, manifests):
    scope = project_qa.invoke(provider, 'derive_startup_scope',
        native=roots['native'], source=roots['source'], web=roots['web'],
        proof=proof, raw=raw, binding=binding, project=project)
    if (not isinstance(scope, dict) or scope.get('schema') != 'startup-read-scope.v1'
            or set(scope.get('coverage', [])) != COVERAGE or scope.get('registered_runner') != proof['execution']['registered_runner']
            or scope.get('control_profile') != proof['control_profile']):
        raise ValueError('startup scope provider did not establish every checked request domain')
    # A hand-filled complete:true is insufficient: the reviewed helper must bind
    # its closed domain to the hashed original runner trace, not a new claim.
    trace = scope.get('trace')
    if not isinstance(trace, dict) or trace != raw.get('startup_dependency_trace'):
        raise ValueError('startup scope requires the original runner-owned dependency trace reference')
    trace_path = Path(trace.get('path', ''))
    if not trace_path.is_absolute():
        trace_path = project / trace_path
    if (trace_path.is_symlink() or not trace_path.resolve().is_relative_to(project)
            or not trace_path.is_file() or sha(trace_path) != trace.get('sha256')):
        raise ValueError('startup dependency trace missing or changed')
    observed = load(trace_path)
    if (observed.get('binding') != binding or observed.get('native_tree_sha256') != binding['native_tree_sha256']
            or observed.get('runner_sha256') != proof['runner']['sha256']
            or set(observed.get('coverage', [])) != COVERAGE):
        raise ValueError('startup dependency trace belongs to another execution/domain')
    domains = scope.get('inputs')
    if not isinstance(domains, dict) or set(domains) != set(roots):
        raise ValueError('startup scope needs native/source/web actual dependencies')
    selected = {}
    for domain, manifest in manifests.items():
        names = domains[domain]
        if not isinstance(names, list) or len(names) != len(set(names)):
            raise ValueError('startup scope duplicate/malformed ' + domain + ' dependencies')
        names = set(map(safe_name, names))
        required = {name for name in manifest if Path(name).suffix.lower() in MANDATORY}
        if domain == 'native':
            required |= {row['relative_path'] for row in proof.get('inputs', [])}
            requested = observed.get('native_reads')
            if not isinstance(requested, list) or not requested:
                raise ValueError('startup trace must enumerate actual native reads')
            required |= set(map(safe_name, requested))
        if not required <= names or not names <= set(manifest):
            raise ValueError('startup scope omits actual executable/config/observed inputs: ' + domain)
        # All file names are bound separately: newly introduced files cannot
        # silently inherit a prior observed closed domain.
        selected[domain] = {name: manifest[name] for name in sorted(names)}
    return scope, selected


@serialized
def approve(project, native, contract, web, *, source=None, target_native=None, target_web=None):
    """Import an exact prior pass, or freeze a newly passed original execution."""
    project, native, contract, web = map(lambda p: Path(p).resolve(), (project, native, contract, web))
    source = Path(source).resolve() if source else project
    roots = {'native': native, 'source': source, 'web': web}
    contract_bytes = contract.read_bytes(); report = load(contract)
    if report.get('passed') is not True or report.get('tool') != 'audit_startup_contract':
        raise ValueError('startup scope refuses failed/non-startup contract')
    binding = report['binding']
    original_native = Path(report['native']).resolve()
    target_native = Path(target_native).resolve() if target_native else original_native
    target_web = Path(target_web).resolve() if target_web else web
    index = project / HOME / (sha(contract) + '.json')
    if index.is_file():
        # Existing precise approval already knows which actual old artifacts
        # were imported. Repeating it is a read, not another ownership review.
        link = load(index)
        store = cl.Ledger(project)
        try:
            found = store.db.execute('SELECT data FROM records WHERE key=?', (link.get('record_key'),)).fetchone()
            previous = json.loads(found[0])['result'] if found else {}
        finally: store.close()
        imported = json.loads(previous.get('artifact_roots_json', '{}'))
        accepted = {'native': {str(target_native), imported.get('native')},
                    'source': {str(project), imported.get('source')},
                    'web': {str(target_web), imported.get('web')}}
        if all(str(roots[k]) in accepted[k] for k in roots):
            try:
                existing = consume(project, target_native, contract)
            except ValueError as error:
                if 'runner/environment/consumer rules changed' not in str(error): raise
                # A genuine rule update may rejudge the preserved original
                # evidence under current semantics; unchanged inputs do not.
            else:
                if existing is not None and Path(previous['web_path']) == target_web:
                    return {'status': 'startup_scope_registered', 'record': str(index),
                            'executed_renderer': False, 'original_at': existing['observed_at'],
                            'reused': True}
    proof_path = Path(report['startup_renderer_report']['path']).resolve()
    if sha(proof_path) != report['startup_renderer_report']['sha256']:
        raise ValueError('startup proof changed')
    proof = load(proof_path)
    manifests = {k: files(v, source=k == 'source') for k, v in roots.items()}
    from audit_mobile_input import snapshot
    if (renderer.digest(renderer.tree(native)) != binding['native_tree_sha256']
            or renderer.digest(renderer.tree(web)) != binding['web_tree_sha256']
            or snapshot(source)[2] != binding['source_sha256']):
        raise ValueError('startup scope import requires exact preserved Native/Source/Web artifacts')
    errors = renderer.validate(proof, native, binding, project)
    if errors:
        raise ValueError('startup original observation refused: ' + '; '.join(errors))
    original, observed_proof, observed_path = original_record(proof, original_native, project, binding, native)
    identity = policy_identity(observed_proof, original_native, project)
    raw_path = Path(observed_proof['raw']['path'])
    if not raw_path.is_absolute(): raw_path = project / raw_path
    raw = load(raw_path)
    scope, selected = derive_scope(identity['provider'], roots, observed_proof, raw, binding, project, manifests)
    refs = references(report, contract.parent, project)
    refs.update(references(observed_proof, project, project))
    refs[str(observed_path)] = sha(observed_path)
    refs[str(contract)] = sha(contract)
    for ref in original['files']:
        p = Path(ref['path'])
        if not p.is_file() or sha(p) != ref['sha256']:
            raise ValueError('startup original ledger evidence missing')
        refs[str(p)] = ref['sha256']
    conditions = {'contract_sha256': sha(contract), 'binding': binding,
                  'target_native': str(target_native), 'target_web': str(target_web),
                  'original_record': cl.sha(original['binding']),
                  'original_tool_sha256': original['binding']['tool_sha256'],
                  'policy': identity, 'scope': scope, 'selected': selected,
                  'names': {k: sorted(v) for k, v in manifests.items()}}
    store = cl.Ledger(project)
    try:
        plan = store.prepare(CHECK_ID, {}, conditions, fingerprint(), domain='startup', label='启动依赖登记 · 原观察沿用')
        def verify():
            if ({k: files(v, source=k == 'source') for k, v in roots.items()} != manifests
                    or contract.read_bytes() != contract_bytes or policy_identity(observed_proof, original_native, project) != identity
                    or any(sha(Path(p)) != digest for p, digest in refs.items())):
                raise ValueError('startup baseline/scope/evidence changed during approval')
            return {}
        def register():
            return {'schema': SCHEMA, 'passed': True, 'binding': binding,
                    'original_record': cl.sha(original['binding']), 'observed_at': original['result']['observed_at'],
                    'original_seconds': original['seconds'], 'policy_json': json.dumps(identity, sort_keys=True),
                    'scope_json': json.dumps(scope, sort_keys=True), 'selected': selected, 'manifests': manifests,
                    'target_native': str(target_native), 'source_path': str(project), 'web_path': str(target_web),
                    'original_tool_sha256': original['binding']['tool_sha256'],
                    'contract_sha256': sha(contract), 'proof_json': json.dumps(observed_proof, sort_keys=True),
                    'contract_json': json.dumps(report, sort_keys=True),
                    'artifact_roots_json': json.dumps({k: str(v) for k, v in roots.items()}, sort_keys=True),
                    'frozen_original_files': list(refs)}
        captured = list(refs) + [str(root / name) for key, root in roots.items() for name in manifests[key]]
        result, detail = store.execute(plan, register, lambda row: row['passed'],
            capture=lambda: captured, verify_inputs=verify)
        record_key = detail.get('source_key', detail['key'])
        try:
            verify()
            frozen_row = json.loads(store.db.execute('SELECT data FROM records WHERE key=?', (record_key,)).fetchone()[0])
            expected_hashes = set(refs.values()) | {digest for domain in manifests.values() for digest in domain.values()}
            if (frozen_row.get('error') or not store._evidence_valid(frozen_row)
                    or not expected_hashes <= {entry['sha256'] for entry in frozen_row['files']}):
                raise ValueError('startup snapshot changed while freezing original artifacts')
        except BaseException as error:
            if not detail['reused']:
                row = json.loads(store.db.execute('SELECT data FROM records WHERE key=?', (record_key,)).fetchone()[0])
                row.update(passed=False, error='scope commit refused: ' + str(error))
                with store.db: store.db.execute('UPDATE records SET data=? WHERE key=?', (cl.canonical(row), record_key))
            raise
        index = project / HOME / (sha(contract) + '.json')
        index.parent.mkdir(parents=True, exist_ok=True)
        document = {'schema': SCHEMA, 'record_key': record_key,
                    'contract_sha256': sha(contract)}
        from preparation_cache import project_lock
        with project_lock(project):
            previous = load(index) if index.exists() else None
            if previous:
                if previous.get('schema') != SCHEMA or previous.get('contract_sha256') != sha(contract):
                    raise ValueError('startup scope index identity changed')
                history = [previous['record_key'], *previous.get('previous_records', [])]
                document['previous_records'] = list(dict.fromkeys(key for key in history if key != record_key))
            if previous != document:
                with tempfile.NamedTemporaryFile(mode='w', dir=index.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    json.dump(document, stream, sort_keys=True)
                try: os.replace(temporary, index)
                finally: temporary.unlink(missing_ok=True)
        return {'status': 'startup_scope_registered', 'record': str(index), 'executed_renderer': False,
                'original_at': result['observed_at'], 'reused': detail['reused']}
    finally:
        store.close()


def consume(project, native, contract, *, current_binding=None):
    """Return None when no scope was registered; otherwise consume or refuse it."""
    project, native, contract = map(lambda p: Path(p).resolve(), (project, native, contract))
    index = project / HOME / (sha(contract) + '.json')
    if not index.is_file(): return None
    link = load(index)
    if link.get('schema') != SCHEMA or link.get('contract_sha256') != sha(contract):
        raise ValueError('startup dependency scope index changed')
    store = cl.Ledger(project)
    try:
        row = store.db.execute('SELECT data FROM records WHERE key=?', (link['record_key'],)).fetchone()
        record = json.loads(row[0]) if row else None
        if (not record or record.get('check_id') != CHECK_ID or not record.get('passed')
                or record.get('error') or not store._evidence_valid(record)):
            raise ValueError('startup dependency scope original evidence missing or failed')
        saved = record['result']; original = saved['binding']; proof = json.loads(saved['proof_json'])
        original_contract = json.loads(saved['contract_json'])
        # Policies are verified by identity only. Never invoke derive_startup_scope
        # or registered execution from this read-only consumer.
        identity = policy_identity(proof, Path(original_contract['native']), project)
        if identity != json.loads(saved['policy_json']) or record['binding']['tool_sha256'] != fingerprint():
            raise ValueError('startup runner/environment/consumer rules changed; repair startup scope only')
        if native != Path(saved['target_native']):
            raise ValueError('startup scoped evidence targets another Native candidate')
        roots = {'native': native, 'source': project, 'web': Path(saved['web_path'])}
        now = {k: files(v, source=k == 'source') for k, v in roots.items()}
        for domain, previous in saved['manifests'].items():
            if set(now[domain]) != set(previous):
                raise ValueError('startup.' + domain + ': names changed; repair dependency ownership, no full-suite replay')
            changed = [name for name, digest in saved['selected'][domain].items() if now[domain].get(name) != digest]
            if changed:
                raise ValueError('startup.' + domain + ': affected dependencies: ' + ', '.join(changed[:12]))
        from audit_mobile_input import snapshot
        binding = {'source_sha256': snapshot(project)[2], 'native_tree_sha256': renderer.digest(renderer.tree(native)),
                   'web_tree_sha256': renderer.digest(renderer.tree(roots['web'])),
                   'build_tag': (current_binding or {}).get('build_tag', original['build_tag'])}
        if any((not row.get('passed') or row.get('error')) and row['binding']['conditions'].get('native_tree_sha256') == binding['native_tree_sha256']
               for row in store.previous(startup.CHECK_ID)):
            raise ValueError('startup current candidate has a recorded failure; repair that startup item')
        if current_binding and any(current_binding.get(k) != v for k, v in binding.items()):
            raise ValueError('startup scoped current binding does not match actual Source/Native/Web')
        if {k: files(v, source=k == 'source') for k, v in roots.items()} != now:
            raise ValueError('startup inputs changed while consuming scoped evidence')
        store.event(CHECK_ID, 'reused', source_key=link['record_key'], original_at=saved['observed_at'],
                    domain='startup', label='启动依赖登记 · 原观察沿用')
        return {'id': startup.CHECK_ID, 'action': 'reused', 'reused': True,
                'scope_record': str(index), 'original_binding': original, 'current_binding': binding,
                'original_build_tag': original['build_tag'], 'observed_at': saved['observed_at'],
                'original_seconds': saved['original_seconds'], 'seconds': 0.0,
                'native_tree_sha256': binding['native_tree_sha256'], 'scope': json.loads(saved['scope_json']),
                'evidence': [ref['path'] for ref in record['files']],
                'reason': '原观察和冻结旧产物保留；当前真实启动依赖未变；未执行 renderer',
                'contract': original_contract, 'proof': proof}
    finally:
        store.close()


def auto_approve(project, native, contract, web):
    try:
        project_qa.lookup(project, 'validators', PROVIDER)
    except ValueError as error:
        if str(error).startswith('no reviewed project QA registration'):
            return {'status': 'scope_mapping_required', 'node': CHECK_ID, 'executed_renderer': False}
        raise
    return approve(project, native, contract, web)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['approve', 'check'])
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--native', required=True, type=Path)
    parser.add_argument('--contract', required=True, type=Path)
    parser.add_argument('--web', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--target-native', type=Path)
    parser.add_argument('--target-web', type=Path, help='actual current Web location when importing preserved old artifacts')
    args = parser.parse_args()
    try:
        if args.command == 'approve':
            if not args.web: raise ValueError('approve requires the preserved exact --web artifact')
            result = approve(args.project, args.native, args.contract, args.web,
                             source=args.source, target_native=args.target_native, target_web=args.target_web)
        else:
            result = consume(args.project, args.native, args.contract)
            if result is None: raise ValueError('startup scope missing; register original artifacts/trace first')
        print(json.dumps(result, ensure_ascii=False)); return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'scope_repair_required', 'node': CHECK_ID,
                          'error': str(error), 'executed_renderer': False}, ensure_ascii=False)); return 1


if __name__ == '__main__':
    raise SystemExit(main())
