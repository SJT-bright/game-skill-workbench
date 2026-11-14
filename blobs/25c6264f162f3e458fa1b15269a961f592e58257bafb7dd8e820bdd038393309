"""Deduplicate the reviewed Native browser replay without reusing a delivery verdict."""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile

import audit_native_startup_renderer as renderer
import check_ledger as cl
import project_qa


CHECK_ID = 'startup.native.renderer'


def environment():
    variables = {k: v for k, v in os.environ.items()
                 if k in {'PATH', 'PYTHONPATH', 'LANG', 'TZ', 'NODE_OPTIONS', 'DISPLAY', 'WAYLAND_DISPLAY'}
                 or k.startswith(('EGO_', 'PLAYWRIGHT_', 'CHROME_', 'COCOS_', 'LC_'))}
    executables = {}
    for name in ('ego-browser', 'ego', 'node', 'chromium', 'google-chrome'):
        location = shutil.which(name)
        if location:
            p = Path(location).resolve()
            stat = p.stat()
            executables[name] = [str(p), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]
    return cl.sha([platform.platform(), sys.version, str(Path(sys.executable).resolve()), variables, executables])




_STARTUP_TOOL_IDENTITY_SHA256 = '27a71b05088b78a997f3cca3d697653dc24bcdcbe26772d3578554b1b001e036'
_STARTUP_TOOL_IDENTITY_BODY_SHA256 = '7b6702970ab2c4fcf84f3073cde6a73a0fa37a21b9a2f69060f5cc5a75827895'


def _startup_tools(paths, *, proof=None, native=None, project=None):
    """Startup observation identity only; unknown code keeps its actual identity."""
    helper = Path(__file__).resolve().with_name('startup_tool_identity.py')
    if not helper.is_file() or helper.is_symlink():
        return cl.tool_fingerprint(paths)
    import re
    raw = helper.read_bytes()
    manifest_slot = re.compile(rb"^_MANIFEST_SHA256 = '([0-9a-f]{64})'$", re.M)
    if (hashlib.sha256(raw).hexdigest() != _STARTUP_TOOL_IDENTITY_SHA256
            or len(manifest_slot.findall(raw)) != 1
            or hashlib.sha256(manifest_slot.sub(b"_MANIFEST_SHA256 = '<projection-manifest-sha256>'", raw)).hexdigest() != _STARTUP_TOOL_IDENTITY_BODY_SHA256):
        return cl.tool_fingerprint(paths)
    import startup_tool_identity as identity_helper
    if Path(identity_helper.__file__).resolve() != helper:
        return cl.tool_fingerprint(paths)
    return identity_helper.fingerprint(paths, proof=proof, native=native, project=project)


def identity(proof, native, project, *, _compat_native=None):
    runner_id, runner, _, _ = renderer.registered_execution(proof, native, project)
    profile = proof.get('control_profile')
    extra = None
    if profile not in {'native_loading_recovery_v1', 'cocos3_systemjs_native_v1',
                       'native_startup_controls.v1', 'canvas_context_conflict_v1'} and not runner.get('legacy_full_validation'):
        extra = project_qa.lookup(project, 'validators', profile)
    tools = _startup_tools([__file__, renderer.__file__,
                                 Path(renderer.__file__).with_name('cocos3_native_renderer_contract.py')], proof=proof, native=_compat_native or native, project=project)
    conditions = {'native_path': str(native), 'runner': runner_id,
                  'profile': profile, 'policy_sha256': cl.sha([runner, extra]),
                  'environment_sha256': environment()}
    return conditions, tools


def capture_replay(output, actual, project, target):
    """Keep the successful replay itself and the raw files the validator read."""
    files = []

    def keep(path, expected=None):
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if expected is not None and expected != digest:
            raise ValueError('Native replay evidence changed while preserving it: ' + str(path))
        copy = target / (digest + path.suffix)
        copy.write_bytes(data)
        files.append(str(copy))

    def refs(value):
        if isinstance(value, dict):
            if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
                path = (project / value['path']).resolve()
                if path.is_relative_to(project) and path.is_file():
                    keep(path, value['sha256'])
            for child in value.values():
                refs(child)
        elif isinstance(value, list):
            for child in value:
                refs(child)

    keep(output)
    refs(actual)
    return list(dict.fromkeys(files))


def replay(proof, native, binding, project):
    native, project = Path(native).resolve(), Path(project).resolve()
    current = renderer.tree(native)
    if renderer.digest(current) != binding.get('native_tree_sha256'):
        raise ValueError('Native changed before the registered replay')
    def current_identity(tree_digest):
        conditions, tools = identity(proof, native, project)
        conditions['native_tree_sha256'] = tree_digest
        return conditions, tools
    conditions, tools = current_identity(binding['native_tree_sha256'])
    ledger = cl.Ledger(project)
    try:
        # Native digest is a mandatory condition, not a project-editable selector.
        plan = ledger.prepare(CHECK_ID, {}, conditions, tools,
                              label='真实 Native 启动 / 首次触控', domain='startup')
        if plan['action'] == 'run':
            previous = ledger.previous(CHECK_ID)
            if previous:
                old = previous[0]['binding']
                names = {'native_path': 'Native 路径', 'native_tree_sha256': 'Native 内容',
                         'policy_sha256': '登记的运行器或依赖', 'environment_sha256': '运行环境',
                         'profile': '检查场景', 'runner': '运行器'}
                changes = [label for key, label in names.items() if old['conditions'].get(key) != conditions[key]]
                if old['tool_sha256'] != tools:
                    changes.append('启动检查规则')
                if changes:
                    plan['why'] = '、'.join(changes) + '变化，只重跑正式启动项'
        with tempfile.TemporaryDirectory(prefix='startup-ledger-') as folder:
            def run():
                files = []
                def capture(output, actual):
                    files.extend(capture_replay(output, actual, project, Path(folder)))
                errors = renderer.execute_registered(proof, native, binding, project, capture=capture)
                if errors:
                    raise ValueError('; '.join(errors))
                if not files:
                    raise ValueError('Native replay returned no evidence to preserve')
                return {'native_tree_sha256': binding['native_tree_sha256'],
                        'original_binding': binding, 'observed_at': cl.stamp(), 'raw_evidence': files}

            def verify():
                if current_identity(renderer.digest(renderer.tree(native))) != (conditions, tools):
                    raise ValueError('Native, replay tool, runner or environment changed during validation')
                return {}

            result, detail = ledger.execute(plan, run, lambda row: bool(row['raw_evidence']), verify_inputs=verify)
        if detail['reused'] and verify() != plan['binding']['inputs']:
            raise ValueError('Native inputs changed while reusing the registered replay')
        return dict(detail, id=CHECK_ID, action='reused' if detail['reused'] else 'rerun',
                    reason=('Native 全树、运行条件、规则和原始证据一致'
                            if detail['reused'] else plan['why']),
                    evidence=result['raw_evidence'], original_build_tag=result['original_binding']['build_tag'],
                    original_binding=result['original_binding'], observed_at=result['observed_at'],
                    native_tree_sha256=result['native_tree_sha256'])
    finally:
        ledger.close()
