"""Reviewed per-project QA registration. No project paths live in the Skill.

Registration trusts code identity only; reports must still pass production gates.
Changing a registered module invalidates its registration, not unrelated games.
"""
import argparse
from contextlib import contextmanager
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PureWindowsPath
import sys
import tempfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def store_path():
    override = os.environ.get('COCOS_QA_TRUST_FILE')
    return Path(override).expanduser().resolve() if override else Path.home()/'.codex/cocos-qa/trust.json'


def read_store():
    path = store_path()
    if not path.exists():
        return {'schema': 'cocos_qa_trust.v1', 'projects': {}, 'legacy': {}}
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get('schema') != 'cocos_qa_trust.v1' or not isinstance(data.get('projects'), dict) or not isinstance(data.get('legacy'), dict):
        raise ValueError('invalid machine-local QA trust registry')
    return data


def write_store(data):
    path = store_path();path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError('QA trust registration is being updated') from exc
    os.close(fd)
    temporary = None
    try:
        current = read_store()
        for key, value in data.get('projects', {}).items():
            current['projects'][key] = value
        for key in ('legacy_profile_files','legacy_registry_files','legacy_runner_validator','legacy_contracts','legacy_evidence_profiles','legacy_export_validator'):
            if key in data:current.setdefault(key,{}).update(data[key])
        for kind, rows in data.get('legacy', {}).items():
            current['legacy'].setdefault(kind, {}).update(rows)
        fd, name = tempfile.mkstemp(prefix='.qa-trust-', dir=path.parent)
        temporary = Path(name)
        with os.fdopen(fd, 'w') as stream:
            json.dump(current, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if temporary:temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def relative_file(project, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute() or PureWindowsPath(value).drive or '..' in Path(value).parts or '\\' in value:
        raise ValueError('QA paths must be project-relative, without parent traversal')
    path = project/value
    if path.is_symlink() or not path.resolve().is_relative_to(project) or not path.is_file():
        raise ValueError('QA file missing or outside the project: '+value)
    return path.resolve()


def register(project, manifest, reviewed=False):
    if not reviewed:
        raise ValueError('inspect the actual runner, validators and dependencies before --reviewed registration')
    project = Path(project).resolve();manifest = Path(manifest).resolve()
    if not project.is_dir() or not manifest.is_relative_to(project) or not manifest.is_file():
        raise ValueError('QA manifest must be a saved file within the project')
    policy = json.loads(manifest.read_text())
    if not isinstance(policy, dict) or policy.get('schema') != 'cocos_project_qa.v1':
        raise ValueError('QA manifest schema must be cocos_project_qa.v1')
    if set(policy)-{'schema','runners','reviews','validators','resource_scanners','resource_profiles','evidence_profiles','ui_runners'}:
        raise ValueError('unsupported project QA manifest fields')
    files = {manifest.relative_to(project).as_posix(): sha(manifest)}
    for key in ('runners', 'reviews', 'validators', 'resource_scanners', 'resource_profiles', 'evidence_profiles', 'ui_runners'):
        collection = policy.get(key, {})
        if not isinstance(collection, dict):raise ValueError(key+' must be an object')
        for identity, row in collection.items():
            if not isinstance(identity, str) or not identity or not isinstance(row, dict):raise ValueError('invalid QA policy identity')
            allowed = {'path', 'dependencies'}
            if key in ('runners', 'ui_runners'):allowed |= {'timeout_seconds', 'control_profile','native_binding'}
            if key == 'ui_runners':allowed |= {'contract','variants'}
            if key == 'ui_runners':
                files[row['contract']] = sha(relative_file(project, row.get('contract')))
                import re
                if not isinstance(row.get('variants'),list) or not row['variants'] or any(not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',v) for v in row['variants']):raise ValueError('reviewed UI variants must be nonempty safe IDs')
            if key == 'reviews':allowed |= {'review_schema', 'game_id', 'native', 'web', 'review', 'writer_path'}
            if set(row)-allowed:raise ValueError('unsupported QA policy fields: '+str(sorted(set(row)-allowed)))
            main = relative_file(project, row.get('path'))
            if key not in ('resource_profiles','evidence_profiles') and main.suffix not in ('.py', '.cjs', '.js', '.mjs'):raise ValueError('QA code must use a supported interpreter')
            if key == 'resource_profiles':
                if identity not in ('reviewed_resource_profiles.json','systemjs_finite_profiles.json','cocos2_finite_profiles.json') or main.suffix!='.json':raise ValueError('unknown resource profile registry')
                json.loads(main.read_text())
            if key == 'evidence_profiles':
                if identity != 'sound_settings_trace.v1' or main.suffix!='.json':raise ValueError('unknown evidence profile')
                if 'project' in json.loads(main.read_text()):raise ValueError('evidence profile scope is its registered project, no absolute project field')
            files[row['path']] = sha(main)
            dependencies = row.get('dependencies', [])
            if not isinstance(dependencies, list):raise ValueError('QA dependencies must be a relative path array')
            if key == 'ui_runners' and not dependencies:raise ValueError('nonempty reviewed UI runner dependencies required')
            for rel in dependencies:files[rel] = sha(relative_file(project, rel))
            if key in ('runners', 'ui_runners'):
                if main.suffix != '.py':raise ValueError('registered browser runner must be a fixed Python entrypoint')
                timeout = row.get('timeout_seconds')
                if type(timeout) is not int or not 1 <= timeout <= 120:raise ValueError('runner timeout must be 1..120 seconds')
                if key == 'runners' and not isinstance(row.get('control_profile'), str):raise ValueError('renderer control_profile required')
            if key == 'reviews':
                if row.get('review_schema') != 3 or identity != '3:'+str(row.get('game_id','')):
                    raise ValueError('new review adapters supplement schema 3; cannot replace the common gate')
                for field in ('review_schema', 'native', 'web', 'review'):
                    if field not in row:raise ValueError('review adapter requires '+field)
                for field in ('native', 'web', 'review'):
                    rel = row[field]
                    if not isinstance(rel, str) or Path(rel).is_absolute() or '..' in Path(rel).parts:raise ValueError('review scope must be project-relative')
                if 'writer_path' in row:
                    files[row['writer_path']] = sha(relative_file(project, row['writer_path']))
    before = sha(manifest)
    for rel, expected in files.items():
        if sha(relative_file(project, rel)) != expected:
            raise ValueError('QA code changed during registration: '+rel)
    data = {'projects': {}, 'legacy': {}}
    data['projects'][str(project)] = {'manifest': manifest.relative_to(project).as_posix(), 'files': files,
                                     'policy': policy, 'reviewed': True}
    if sha(manifest) != before:raise ValueError('QA manifest changed during registration')
    write_store(data)
    return {'project': str(project), 'files': len(files), 'scope': 'Code identity registration only; no game or report accepted.'}


def project_policy(project, required_paths=None):
    project = Path(project).resolve();entry = read_store()['projects'].get(str(project))
    if entry is None:return None
    if not isinstance(entry, dict) or not entry.get('reviewed') or not isinstance(entry.get('files'), dict):raise ValueError('unreviewed project QA registration')
    selected = set(entry['files']) if required_paths is None else set(required_paths) | {entry['manifest']}
    for rel in selected:
        expected = entry['files'].get(rel)
        if sha(relative_file(project, rel)) != expected:raise ValueError('registered project QA file changed: '+rel)
    return entry


def lookup(project, kind, key):
    project = Path(project).resolve();entry = project_policy(project, required_paths=[])
    if entry is not None and key in entry['policy'].get(kind, {}):
        row = copy.deepcopy(entry['policy'][kind][key]);row['project'] = str(project)
        selected = [row['path'], *row.get('dependencies', [])]
        if 'writer_path' in row:selected.append(row['writer_path'])
        if kind == 'ui_runners':selected.append(row['contract'])
        project_policy(project, required_paths=selected)
        row['path'] = str(relative_file(project, row['path']))
        row['sha256'] = sha(row['path'])
        row['dependencies'] = {str(relative_file(project, rel)): entry['files'][rel] for rel in selected}
        row['allowed_root'] = str(project)
        if 'writer_path' in row:row['writer_path'] = str(relative_file(project, row['writer_path']))
        if kind == 'ui_runners':
            row['contract'] = str(relative_file(project, row['contract']))
            row['contract_sha256'] = sha(row['contract'])
        return row
    # Legacy installations retain a separately configured compatibility source.
    # This bridge is absent on a clean install; new manifests cannot enable it.
    machine = read_store()
    compatibility = dict(machine['legacy'].get(kind, {}))
    live_path = machine.get('legacy_registry_files', {}).get(kind)
    if live_path and kind == 'runners':
        live = json.loads(Path(live_path).read_text())
        for identity, registered in live.items():
            if registered.get('project') != str(project):continue
            row = dict(machine.get('legacy_runner_validator', {}), **registered, id=identity)
            row['allowed_root'] = registered.get('workspace') or registered['project']
            if registered.get('workspace'):row['excluded_root'] = registered['project']
            if not registered.get('control_profile'):
                row.update(control_profile='ember_canvas_context_conflict_v1',allow_legacy_missing_profile=True)
            compatibility[identity] = row
    # Legacy installations are migrated into a machine-local store, never exported.
    for row in compatibility.values():
        if (row.get('project') == str(project) or (row.get('project') is None and row.get('template') is True)) and row.get('id') == key:
            result = copy.deepcopy(row)
            result['project'] = str(project)
            for name, expected in result.get('trusted_files', {}).items():
                if not Path(name).is_file() or sha(name) != expected:raise ValueError('legacy project adapter changed: '+name)
            return result
    raise ValueError('no reviewed project QA registration for '+kind+'/'+str(key)+'; register the project QA manifest')


def module(policy, name='project_qa_adapter', field='path'):
    path = Path(policy[field]).resolve()
    expected = policy.get('trusted_files', {}).get(str(path), policy.get('sha256') if field == 'path' else None)
    if expected is None:
        dependencies = policy.get('dependencies', {})
        expected = dependencies.get(str(path))
    if not path.is_file() or sha(path) != expected:raise ValueError('project QA module missing or changed')
    spec = importlib.util.spec_from_file_location(name+'_'+sha(path)[:12], path)
    imported = importlib.util.module_from_spec(spec);spec.loader.exec_module(imported)
    return imported


def review_policy(args, review):
    key = str(review.get('schema'))+':'+str(review.get('game_id', ''))
    try:
        policy = lookup(args.project, 'reviews', key)
    except ValueError as exc:
        if not str(exc).startswith('no reviewed project QA registration'):raise
        return None
    for field in ('native', 'web', 'review'):
        if policy.get('template') and policy.get(field) is None:continue
        expected = Path(policy[field])
        if not expected.is_absolute():expected = Path(args.project)/expected
        if getattr(args, field).resolve() != expected.resolve():raise ValueError('project review '+field+' scope mismatch')
    expected_app = policy.get('app_id')
    if expected_app and getattr(args, 'app_id', expected_app) != expected_app:raise ValueError('project review target App ID mismatch')
    return policy


def adjusted_args(args, policy):
    result = copy.copy(args)
    if policy.get('audit_project'):result.project = Path(policy['audit_project'])
    return result


def invoke(policy, function, *args, field='path', **kwargs):
    """Keep reviewed local adapter imports scoped to this call."""
    parent = str(Path(policy[field]).resolve().parent)
    previous = sys.path[:]
    try:
        sys.path.insert(0, parent)
        result = getattr(module(policy, field=field), function)(*args, **kwargs)
        for name, expected in policy.get('dependencies', {}).items():
            if sha(name) != expected:raise ValueError('project adapter dependency changed during execution')
        for name, expected in policy.get('trusted_files', {}).items():
            if sha(name) != expected:raise ValueError('project adapter changed during execution')
        return result
    finally:
        sys.path[:] = previous


def resource_profile_path(project, name):
    if name not in ('reviewed_resource_profiles.json','systemjs_finite_profiles.json','cocos2_finite_profiles.json'):
        raise ValueError('unknown resource registry name')
    if project:
        try:return Path(lookup(project,'resource_profiles',name)['path'])
        except ValueError as exc:
            if not str(exc).startswith('no reviewed project QA registration'):raise
    # Existing installations retain their private compatibility data. A clean
    # installation has no game profile table, and unknown domains stay refused.
    saved = read_store().get('legacy_profile_files', {}).get(name)
    return Path(saved) if saved else store_path().parent/'resource-profiles'/name


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['register', 'check'])
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--reviewed', action='store_true')
    args = parser.parse_args()
    try:
        result = register(args.project, args.manifest, args.reviewed) if args.command == 'register' else project_policy(args.project)
        if result is None:raise ValueError('project QA registration missing')
        print(json.dumps({'status': 'passed', 'result': result}, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'status': 'refuse', 'error': str(exc)}, ensure_ascii=False));sys.exit(1)


def evidence_profile(location, identity):
    location = Path(location).resolve()
    for project, entry in read_store()['projects'].items():
        if location.is_relative_to(Path(project)) and identity in entry['policy'].get('evidence_profiles', {}):
            policy = lookup(project, 'evidence_profiles', identity)
            profile = json.loads(Path(policy['path']).read_text())
            return dict(profile, project=project)
    for policy in read_store().get('legacy_evidence_profiles', {}).values():
        if policy.get('id') == identity and location.is_relative_to(Path(policy['project'])):
            path = Path(policy['path'])
            if sha(path) != policy['sha256']:raise ValueError('local evidence profile changed')
            return json.loads(path.read_text())
    raise ValueError('no reviewed evidence profile: '+identity)


def local_contract(identity, location):
    location = Path(location).resolve()
    for project, entry in read_store()['projects'].items():
        if location.is_relative_to(Path(project)) and identity in entry.get('policy', {}).get('validators', {}):
            return lookup(project, 'validators', identity)
    for policy in read_store().get('legacy_contracts', {}).values():
        if policy.get('id') == identity and location.is_relative_to(Path(policy['project'])):
            return policy
    return None
