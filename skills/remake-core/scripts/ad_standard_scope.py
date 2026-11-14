"""Resolve the six-standard production scope without retrofitting old deliveries."""
import json
import importlib.util
from pathlib import Path

STANDARD = 'strict_six_standard_families'


def requirement(project=None, policy=None):
    if project is None:
        return {'required': policy != 'legacy', 'reason': 'new production package needs its actual project evidence'}
    project = Path(project)
    marker = project / '.tiktok-kit/policy.json'
    data = {}
    if marker.is_file():
        try:
            data = json.loads(marker.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {'required': True, 'reason': 'project policy is unreadable; cannot downgrade the ad standard'}
    if data.get('ad_standard') == STANDARD or (project / 'docs/adboost/ad_nodes.json').is_file():
        return {'required': True, 'reason': 'six-standard production is enabled for this project'}
    from compatibility_scope import verified
    preserved = verified(project)
    if preserved:
        return {'required': False,
                'reason': 'reviewed current platform-only repair retains the supplied feature/UI contract; no complete six-family runtime approval claimed',
                'compatibility_native_inputs': preserved['native_inputs']}
    if _verified_confirmed_trial(project):
        return {'required': False, 'reason': 'machine-registered user approval retains this confirmed trial scope; evidence and production dependencies match'}
    if marker.is_file() and data.get('policy') == 'new' and data.get('created'):
        if _verified_maintenance(project):
            return {'required': False, 'reason': 'verified prior delivery and scoped maintenance plan retain their recorded contract'}
        return {'required': True, 'reason': 'an inherited project marker alone cannot exempt a complete production flow'}
    if policy == 'legacy':
        return {'required': False, 'reason': 'recognized legacy artifact; no new six-standard production contract'}
    return {'required': True, 'reason': 'new or unclassified production cannot omit the six-standard contract'}


def _verified_maintenance(project):
    """Use the existing owner plan and exact prior delivery receipt, not a loose flag."""
    path = Path(__file__).with_name('regression_scope_gate.py')
    if not path.is_file():
        return False
    try:
        spec = importlib.util.spec_from_file_location('ad_standard_existing_scope', path)
        owner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(owner)
        plan, _ = owner._load_plan(project.resolve())
        if plan.get('mode') not in ('scoped', 'reuse-only') or not plan.get('baseline'):
            return False
        baseline = plan['baseline']
        return owner.baseline_identity(baseline['path'], {}) == baseline
    except (Exception, SystemExit):
        return False


def _verified_confirmed_trial(project):
    """Only machine-registered approvals apply; project self-declarations confer no authority."""
    import hashlib
    from project_qa import read_store, relative_file
    try:
        project = project.resolve()
        registered = read_store().get('confirmed_trial_scopes', {}).get(str(project))
        if not isinstance(registered, dict):
            return False
        record = relative_file(project, registered['path'])
        if hashlib.sha256(record.read_bytes()).hexdigest() != registered['sha256']:
            return False
        scope = json.loads(record.read_text())
        trial = relative_file(project, scope['trial_record'])
        if (scope.get('schema') != 'ad-standard-user-scope.v1'
                or scope.get('authority') != 'explicit_current_user_instruction'
                or scope.get('scope') != 'retain_confirmed_trial'
                or not scope.get('instruction')
                or hashlib.sha256(trial.read_bytes()).hexdigest() != scope['trial_sha256']
                or json.loads(trial.read_text()).get('status') not in ('ready', 'handoff_ready')):
            return False
        dependencies = scope['production_dependencies']
        return isinstance(dependencies, dict) and bool(dependencies) and all(
            hashlib.sha256(relative_file(project, name).read_bytes()).hexdigest() == expected
            for name, expected in dependencies.items())
    except (KeyError, OSError, ValueError, TypeError):
        return False
