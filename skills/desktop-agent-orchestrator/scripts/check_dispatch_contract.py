#!/usr/bin/env python3
"""Check declared delegation contracts; never dispatches, sandboxes or certifies UI truth."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROLE_TYPES = {
    'intake': {'A01', 'A02', 'A03', 'A04', 'A05'},
    'resources': {'A06', 'A07', 'A08', 'A18', 'B01'},
    'ui': {'B02', 'B03'},
    'patch': {'B04', 'B06'},
    'build': {'A09', 'A10', 'A11', 'A12', 'A13', 'A14', 'A15', 'A16'},
    'qa': {'A10', 'A11', 'A13', 'A14', 'A15', 'A16', 'B05'},
    'package_writer': {'A17', 'A18'},
    'package': {'A16', 'A17', 'A18'},
    'literal': {'literal_copy', 'clear_text_ocr'},
}
PREFERRED = {
    'intake': ['workbuddy', 'astudio', 'opencode'],
    'resources': ['astudio', 'workbuddy', 'qoder_cn', 'qoder'],
    'ui': ['qoder_cn', 'astudio', 'qoder'],
    'patch': ['qoder', 'qoder_cn', 'astudio'],
    'build': ['opencode', 'qoder', 'workbuddy'],
    'qa': ['workbuddy_ai', 'qoder', 'astudio'],
    'package_writer': ['opencode', 'workbuddy'],
    'package': ['grok', 'workbuddy_ai', 'opencode'],
    'literal': ['grok'],
}
APP_ROLES = {
    'workbuddy': {'intake', 'resources', 'build', 'package_writer'},
    'astudio': {'intake', 'resources', 'ui', 'patch', 'qa'},
    'workbuddy_ai': {'qa', 'package'},
    'qoder_cn': {'resources', 'ui', 'patch'},
    'qoder': {'resources', 'ui', 'patch', 'build', 'qa'},
    'opencode': {'intake', 'build', 'package_writer', 'package'},
    'grok': {'literal', 'package'},
}
BUSY = {'sent', 'running', 'artifact_ready', 'independent_review', 'needs_main_decision',
        'rework', 'stopping', 'uncertain'}
USER_LIMITS = {'qoder': 3, 'workbuddy': 3, 'workbuddy_ai': 3,
               'astudio': 1, 'grok': 6, 'opencode': 1}
APP_GROUPS = {x: x for x in USER_LIMITS}
APP_GROUPS['qoder_cn'] = 'qoder'
BOUNDARY = ('Declared contract only: main agent must judge classification and evidence truth; '
            'not a sandbox, dispatch receipt, quota probe or product acceptance.')


def absolute(value):
    p = Path(value)
    if not p.is_absolute() or any(c in str(value) for c in '*?[]'):
        raise ValueError(f'Absolute non-glob path required: {value}')
    return p.resolve()


def below(path, roots):
    return any(path == root or root in path.parents for root in roots)


def overlaps(left, right):
    return below(left, [right]) or below(right, [left])


def ref_ok(ref):
    if not isinstance(ref, dict):
        return False
    try:
        p = absolute(ref['path'])
        return p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == ref['sha256']
    except (KeyError, OSError, TypeError, ValueError):
        return False


def inspect(task, ledger, now=None, max_age=900):
    now = now or datetime.now(timezone.utc)
    errors, unavailable = [], []
    kind, role = task.get('task_type', ''), task.get('role', '')
    result = {'task_id': task.get('task_id'), 'status': 'needs_main_decision',
              'errors': errors, 'eligible_apps': [], 'unavailable_apps': unavailable,
              'boundary': BOUNDARY}
    activation = ledger.get('activation', {})
    if (not isinstance(activation, dict) or not isinstance(activation.get('run_id'), str)
            or not activation['run_id'].strip() or activation.get('run_id') != task.get('run_id')
            or activation.get('user_confirmed') is not True
            or not isinstance(activation.get('authorization_ref'), str)
            or not activation['authorization_ref'].strip()
            or activation.get('mode') not in {'desktop_multi', 'single'}):
        result['status'] = 'activation_required'
        errors.append('Current human mode selection and authorization reference required.')
        return result
    if activation['mode'] == 'single':
        result['status'] = 'single_agent'
        return result
    if kind in {f'C{i:02}' for i in range(1, 9)} or task.get('critical_logic') is True:
        result['status'] = 'main_only'
        errors.append('Critical decisions/implementation stay with main agent.')
        return result
    if not task.get('task_id') or kind not in ROLE_TYPES.get(role, set()):
        errors.append('Missing identity, unknown task type or role/type mismatch.')
    for field in ('steps', 'expected_outputs'):
        if not isinstance(task.get(field), list) or not task[field] or any(
            not isinstance(x, str) or not x.strip() for x in task[field]
        ):
            errors.append(f'Concrete {field} required before delegation.')
    if task.get('decision_owner') != 'main' or task.get('acceptance_owner') != 'main':
        errors.append('Decision and final acceptance must belong to main.')
    if task.get('subdelegate') is not False or task.get('critical_logic') is not False:
        errors.append('Explicit no-subdelegation and noncritical classification required.')
    if type(task.get('change_tests')) is not bool or (task.get('change_tests') is True and kind != 'B06'):
        errors.append('Only approved B06 may implement predetermined test cases.')
    if not ref_ok(task.get('input_ref')):
        errors.append('Pinned input manifest is missing, changed or unreadable.')
    if (kind.startswith('B') or kind in {'A06', 'A07', 'A08', 'A17'}) and not ref_ok(task.get('spec_ref')):
        errors.append('Main-decided spec/mapping with current SHA is required.')
    independent = task.get('independent_of', [])
    if role in {'qa', 'package'} and (not independent or task.get('task_id') in independent):
        errors.append('Independent review must name a different producer task.')
    if role in {'qa', 'package'} and any(
        not any(t.get('task_id') == producer and t.get('app') and t.get('conversation')
                for t in ledger.get('tasks', [])) for producer in independent
    ):
        errors.append('Producer identity/conversation must be recorded for independent review.')
    try:
        project = absolute(task['project_root'])
        roots = [absolute(x) for x in ledger['allowed_roots']]
        protected = [absolute(x) for x in ledger['protected_paths']]
        for field in ('input_ref', 'spec_ref'):
            if isinstance(task.get(field), dict) and task[field].get('path'):
                protected.append(absolute(task[field]['path']))
        evidence = [absolute(x) for x in ledger['evidence_roots']]
        writes = [absolute(x) for x in task['write_paths']]
        if not roots or not evidence or not project.is_dir() or not writes:
            errors.append('Existing project, scope roots and explicit writes are required.')
        if not below(project, roots):
            errors.append('Project is outside approved scope roots.')
        for p in writes:
            if p in roots or not below(p, roots):
                errors.append(f'Write scope is outside approved roots or too broad: {p}')
            if any(overlaps(p, q) for q in protected):
                errors.append(f'Worker write intersects main-protected scope: {p}')
            if role in {'qa', 'package_writer', 'package', 'literal'} and not below(p, evidence):
                errors.append(f'Review/literal role may only write its evidence: {p}')
        locks = task.get('resource_locks', [])
        if not isinstance(locks, list) or any(not isinstance(x, str) or not x.strip() for x in locks):
            errors.append('Resource locks must be a list of concrete lock names.')
            locks = []
        prefix = {'A09': 'creator:', 'A12': 'service:', 'B05': 'browser:'}.get(kind)
        if kind == 'A13':
            if task.get('capture_mode') not in {'offline_assets', 'runtime_gui'}:
                errors.append('A13 must declare offline_assets or runtime_gui capture mode.')
            if task.get('capture_mode') == 'runtime_gui':
                prefix = 'browser:'
        if prefix and not any(x.startswith(prefix) and len(x) > len(prefix) for x in locks):
            errors.append(f'This execution requires a concrete {prefix} resource lock.')
        for other in ledger.get('tasks', []):
            if other.get('state') not in BUSY or other.get('task_id') == task.get('task_id'):
                continue
            if set(locks) & set(other.get('resource_locks', [])):
                errors.append(f'Resource lock occupied by {other.get("task_id")}.')
            for raw in other.get('write_paths', []):
                if any(overlaps(p, absolute(raw)) for p in writes):
                    errors.append(f'Write lease occupied by {other.get("task_id")}.')
    except (KeyError, OSError, TypeError, ValueError) as exc:
        errors.append(f'Invalid scope/lease: {exc}')
    if errors:
        return result

    capabilities = {'files'}
    if role in {'intake', 'build', 'patch', 'package_writer', 'package'} or (role == 'qa' and kind != 'B05'):
        capabilities.add('terminal')
    if role in {'ui', 'patch'} or kind in {'A06', 'A07', 'A08'}:
        capabilities.add('edit')
    if kind == 'B05':
        capabilities.update({'browser', 'trusted_touch'})
    if kind == 'A13' and task.get('capture_mode') == 'runtime_gui':
        capabilities.add('browser')
    if kind == 'clear_text_ocr':
        capabilities.add('vision')
    apps = ledger.get('apps', [])
    for app in apps:
        reasons = []
        app_id = app.get('id', '')
        if app_id not in APP_ROLES:
            reasons.append('application_outside_explicit_seven_app_pool')
        elif role not in APP_ROLES[app_id]:
            reasons.append('role_outside_application_policy')
        if role not in app.get('roles', []):
            reasons.append('role_not_verified')
        if app.get('roles_approved') is not True:
            reasons.append('roles_not_approved_by_main')
        if not capabilities <= set(app.get('capabilities', [])):
            reasons.append('required_tools_not_verified')
        transport = app.get('transport', 'desktop')
        readiness = ['project_verified', 'tools_verified', 'model_verified', 'quota_ok']
        if transport == 'grok_cli' and app_id == 'grok':
            readiness.append('cli_ready')
        elif transport == 'desktop':
            readiness.append('ui_readable')
        else:
            reasons.append('unsupported_transport_for_this_application')
        if not all(app.get(k) is True for k in readiness):
            reasons.append('channel_qualification_unknown_or_blocked')
        try:
            app_path = absolute(app['app_path'])
            if not app_path.exists() or not all(app.get(x) for x in ('conversation', 'observation_ref')):
                reasons.append('missing_exact_identity_or_observation')
            if transport == 'desktop' and not app.get('bundle_id'):
                reasons.append('missing_desktop_application_identity')
            if transport == 'grok_cli' and not app_path.is_file():
                reasons.append('missing_verified_Grok_CLI_executable')
            observed = datetime.fromisoformat(app['observed_at'].replace('Z', '+00:00'))
            if observed.tzinfo is None or not -60 <= (now - observed).total_seconds() <= max_age:
                reasons.append('observation_stale_or_invalid')
            group = app['capacity_group']
            if group != APP_GROUPS.get(app_id, app_id):
                reasons.append('application_capacity_group_mismatch')
            members = [a for a in apps if a.get('capacity_group') == group]
            occupied = {a.get('global_occupied') for a in members}
            limits = [a.get('configured_limit') for a in members]
            if len(occupied) != 1 or any(type(a.get('global_occupied')) is not int for a in members):
                reasons.append('global_occupancy_unknown_or_inconsistent')
            elif any(type(x) is not int or x <= 0 for x in limits) or not 0 <= next(iter(occupied)) < min(limits):
                reasons.append('no_global_capacity')
            if any(type(x) is not int or x > USER_LIMITS.get(group, 1) for x in limits):
                reasons.append('configured_limit_exceeds_current_policy')
            if app_id in {'qoder', 'qoder_cn'} and group != 'qoder':
                reasons.append('qoder_variants_must_share_capacity_group')
            member_ids = {a.get('id') for a in members}
            busy_ids = {t.get('conversation') or t.get('task_id') for t in ledger.get('tasks', [])
                        if t.get('app') in member_ids and t.get('state') in BUSY}
            if len(occupied) == 1 and type(next(iter(occupied))) is int and next(iter(occupied)) < len(busy_ids):
                reasons.append('global_occupancy_undercounts_recorded_tasks')
        except (KeyError, OSError, TypeError, ValueError, AttributeError):
            reasons.append('invalid_channel_observation')
        if role in {'qa', 'package'} and (app_id, app.get('conversation')) in {
            (t.get('app'), t.get('conversation')) for t in ledger.get('tasks', []) if t.get('task_id') in independent
        }:
            reasons.append('same_conversation_as_producer')
        if reasons:
            unavailable.append({'app': app_id, 'reasons': sorted(set(reasons))})
        else:
            result['eligible_apps'].append(app_id)
    preferred = PREFERRED.get(role, [])
    result['eligible_apps'].sort(key=lambda x: preferred.index(x) if x in preferred else len(preferred))
    result['status'] = 'ready' if result['eligible_apps'] else 'channel_unavailable'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = inspect(json.loads(args.task.read_text()), json.loads(args.ledger.read_text()))
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        result = {'status': 'needs_main_decision', 'errors': [str(exc)], 'boundary': BOUNDARY}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'eligible_apps': result.get('eligible_apps', []),
                      'report': str(args.report)}, ensure_ascii=False))
    return 0 if result['status'] == 'ready' else 2


if __name__ == '__main__':
    raise SystemExit(main())
