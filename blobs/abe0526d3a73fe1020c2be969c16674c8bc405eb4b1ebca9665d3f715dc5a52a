"""Validate bound adapter-storage evidence, not real TikTok ad availability.
A reviewed runner and its dependencies remain a human review boundary. Hashes
bind evidence to bytes; they cannot authenticate an execution or discover all ads.
"""
import hashlib
import json
from pathlib import Path
import package_issue_gate as issues

AD_MARKERS = (b'createRewardedVideoAd', b'showRewarded', b'rewardedVideoAd')
REQUIRED_SHAPES = {'null', 'false', 'true', 'string_0', 'string_1', 'number_0', 'number_1', 'invalid_object', 'invalid_string'}


def tree_sha(root):
    root = Path(root).resolve()
    rows = [(p.relative_to(root).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()]
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def _find_contract(project):
    for rel in ('qa/storage-boolean-contract.json', 'docs/test/storage-boolean-contract.json'):
        path = Path(project).resolve() / rel
        if path.is_file():
            return path
    return None


def _ref(project, ref, label):
    if not isinstance(ref, dict) or not isinstance(ref.get('path'), str) or not isinstance(ref.get('sha256'), str):
        raise ValueError('invalid storage evidence reference: '+label)
    root = Path(project).resolve()
    rel = Path(ref['path'])
    path = (root / rel).resolve()
    if rel.is_absolute() or not path.is_relative_to(root) or not path.is_file():
        raise ValueError('storage reference must be a project file: '+label)
    if hashlib.sha256(path.read_bytes()).hexdigest() != ref['sha256']:
        raise ValueError('storage evidence missing or changed: '+label)
    return path


def _object(path, label):
    try:
        obj = json.loads(path.read_text())
    except (ValueError, OSError) as error:
        raise ValueError('invalid storage JSON: '+label) from error
    if not isinstance(obj, dict):
        raise ValueError('storage JSON must be an object: '+label)
    return obj


def verify(files, native, project):
    ad_present = any(any(marker in data for marker in AD_MARKERS) for data in files.values())
    if not project:
        raise ValueError('storage contract audit requires project context')
    contract_path = _find_contract(project)
    # A known contract must not disappear merely because an SDK wrapper is renamed.
    if not ad_present and contract_path is None:
        return {'passed': True, 'required': False,
                'reason': 'no marker or registered contract; ad absence still requires inventory review'}
    if contract_path is None:
        raise ValueError('rewarded-ad Native storage contract missing')
    data = _object(contract_path, 'contract')
    if data.get('schema') != 'native_ad_storage_contract.v2':
        raise ValueError('storage contract v2 required; v1 declarations do not prove per-shape execution')
    expected = tree_sha(native)
    if data.get('native_tree_sha256') != expected:
        raise ValueError('storage contract is bound to a different Native tree')
    if data.get('evidence_layer') != 'native_adapter_simulation':
        raise ValueError('storage contract must identify adapter simulation, not claim device/IAA proof')
    shapes = data.get('shapes')
    if not isinstance(shapes, list) or any(not isinstance(s, str) for s in shapes) or set(shapes) != REQUIRED_SHAPES or len(shapes) != len(REQUIRED_SHAPES):
        raise ValueError('storage contract requires each shape exactly once')
    runner = data.get('runner')
    runner_path = _ref(project, runner, 'runner')
    if runner_path.suffix not in ('.py', '.js', '.mjs', '.cjs'):
        raise ValueError('storage runner must be executable Python/Node source')
    dependencies = data.get('harness_dependencies')
    if not isinstance(dependencies, list) or not dependencies:
        raise ValueError('storage harness dependencies required')
    for index, ref in enumerate(dependencies):
        _ref(project, ref, 'harness dependency '+str(index))
    refs, cases = data.get('evidence_refs'), data.get('cases')
    if not isinstance(refs, dict) or not isinstance(cases, dict) or set(refs) != REQUIRED_SHAPES or set(cases) != REQUIRED_SHAPES:
        raise ValueError('raw evidence and assertions required for every storage shape')
    for shape in sorted(REQUIRED_SHAPES):
        assertions = cases[shape]
        if not isinstance(assertions, list) or not assertions:
            raise ValueError('storage case requires business assertions: '+shape)
        for row in assertions:
            if (not isinstance(row, dict) or row.get('op') not in ('eq', 'ne', 'gt', 'ge', 'lt', 'le')
                    or 'value' not in row or not isinstance(row.get('path'), list) or not row['path']
                    or any(type(k) not in (str, int) for k in row['path'])):
                raise ValueError('invalid storage business assertion: '+shape)
        result = _object(_ref(project, refs[shape], shape), shape)
        if (result.get('schema') != 'native_storage_shape_case.v2' or result.get('shape') != shape
                or result.get('native_tree_sha256') != expected or result.get('runner') != runner
                or result.get('harness_dependencies') != dependencies):
            raise ValueError('storage raw result identity mismatch: '+shape)
        injection = result.get('injection')
        if (not isinstance(injection, dict) or injection.get('api') != 'tt.getStorageSync'
                or injection.get('shape') != shape or type(injection.get('read_count')) is not int
                or injection['read_count'] < 1):
            raise ValueError('storage result lacks exercised adapter injection: '+shape)
        if result.get('errors') != [] or not isinstance(result.get('observed'), dict):
            raise ValueError('storage result has harness errors or lacks observations: '+shape)
        if issues.assertions_pass(result['observed'], assertions) is not True:
            raise ValueError('storage business postconditions failed: '+shape)
    # Retain the existing narrow source-bypass guard. This known layout check
    # does not discover every source module or prove a shared reader is correct.
    source_root = Path(project).resolve() / 'EnglishProject/assets/script'
    watched = ('Reward', 'Checkin', 'SkinCollection', 'shopitem', 'gift', 'cjbar', 'jiangli', 'HomeMissions', 'GameScene')
    if source_root.is_dir():
        direct = [str(p.relative_to(source_root)) for p in source_root.rglob('*')
                  if p.suffix in ('.ts', '.js') and p.name != 'Globle.ts'
                  and any(token.lower() in str(p).lower() for token in watched)
                  and 'cc.sys.localStorage.getItem' in p.read_text(errors='replace')]
        if direct:
            raise ValueError('reward/ad source bypasses shared storage reader: '+', '.join(direct))
    import audit_ad_local_retest
    local_retest = audit_ad_local_retest.verify(project, expected, data.get('local_player_retest'))
    return {'passed': True, 'required': True, 'contract': str(contract_path),
            'contract_sha256': hashlib.sha256(contract_path.read_bytes()).hexdigest(),
            'native_tree_sha256': expected, 'shapes': sorted(REQUIRED_SHAPES),
            'runner': runner, 'harness_dependencies': dependencies, 'evidence_refs': refs,
            'evidence_layer': 'native_adapter_simulation', 'coverage': 'adapter_storage_and_local_player_chain', 'local_player_retest': local_retest}
