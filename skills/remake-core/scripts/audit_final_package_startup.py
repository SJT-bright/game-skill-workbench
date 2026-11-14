"""Final upload gate: reuse actual Native renderer and loading-recovery contracts.
No browser substitutions, executable paths, or pass flags are accepted from callers.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import audit_native_startup_renderer as renderer
from audit_loading_recovery import validate as validate_recovery
from audit_startup_contract import validate_runtime_report


KIT_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'platform-kit'


class StartupRefused(ValueError):
    def __init__(self, check_id, message):
        super().__init__(message)
        self.check_id = check_id


def platform_kit_covers_retry(native, project):
    """Remake (user 2026-10-27): a game that ships the TikTok Platform Kit unchanged gets the kit's tested boot
    (stall -> visible Retry -> new request, old callbacks ignored, background not counted). Then the per-game Retry
    fault matrix is not repeated; HOME/real-input startup evidence is still required."""
    manifest = json.loads((KIT_DIR / 'KIT_MANIFEST.json').read_text(encoding='utf-8'))
    for rel in ('build-templates/bytedance/main.js', 'build-templates/bytedance/touch-coordinates.js'):
        built = Path(native) / Path(rel).name
        if not built.is_file() or hashlib.sha256(built.read_bytes()).hexdigest() != manifest['files'][rel]['sha256']:
            return False, 'Native %s is not the platform kit file' % Path(rel).name
    r = subprocess.run([sys.executable, '-B', str(KIT_DIR / 'tools' / 'check_kit_project.py'), '--project', str(project)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return False, 'check_kit_project.py failed: ' + (r.stdout or r.stderr)[-400:]
    return True, '%s v%s unchanged' % (manifest['name'], manifest['version'])


def audit_final_startup(native, project, startup_contract, recovery_runtime, *, reuse_only=False):
    if project and startup_contract and (Path(project)/'docs/checks/creator1-compatibility.json').is_file():
        from cocos1_compat import engine_file
        engines={n:(Path(native)/n).read_bytes() for n in ('cocos2d-js-min.js','cocos2d-js.js') if (Path(native)/n).is_file()}
        if engine_file(engines):
            from creator1_compatibility_contract import consume
            saved=json.loads((Path(project)/'docs/checks/creator1-compatibility.json').read_bytes())
            checked=consume(project,native,saved['web'])
            if (Path(saved['startup']['path']).resolve()!=Path(startup_contract).resolve()
                    or not recovery_runtime or Path(saved['recovery']['path']).resolve()!=Path(recovery_runtime).resolve()):
                raise ValueError('Creator1 exact startup/recovery evidence required')
            return dict(passed=True,native_tree_sha256=checked['binding']['native_tree_sha256'],
                        startup_contract_sha256=hashlib.sha256(Path(startup_contract).read_bytes()).hexdigest(),
                        loading_recovery_runtime_sha256=hashlib.sha256(Path(recovery_runtime).read_bytes()).hexdigest(),
                        current_binding=checked['binding'],registered_renderer_replayed=False,
                        checks=[dict(id='creator1.compatibility',action='reused',evidence=[saved['startup']['path'],saved['recovery']['path']],
                                     original_at=checked['original_at'],reason='Exact original registered Native controls revalidated')],
                        scope=checked['boundary'])
    if project and startup_contract:
        from startup_scoped_evidence import consume
        scoped = consume(project, native, startup_contract)
        if scoped is not None:
            original = scoped['original_binding']
            contract_bytes = Path(startup_contract).read_bytes()
            if recovery_runtime:
                recovery_path = Path(recovery_runtime).resolve()
                recovery_bytes = recovery_path.read_bytes()
                errors = validate_recovery(json.loads(recovery_bytes), original, recovery_path.parent)
                if errors:
                    raise StartupRefused('startup.native.retry', 'scoped original Retry evidence refused: ' + '; '.join(errors))
                if recovery_path.read_bytes() != recovery_bytes:
                    raise StartupRefused('startup.native.retry', 'Retry evidence changed during scoped validation')
            else:
                covered, why = platform_kit_covers_retry(Path(native), Path(project))
                if not covered:
                    raise StartupRefused('startup.native.retry', 'current unchanged kit does not cover Retry: ' + why)
                recovery_bytes = None
            # Repeat only the cheap identity boundary, never a renderer/helper.
            after = consume(project, native, startup_contract)
            if after['current_binding'] != scoped['current_binding'] or Path(startup_contract).read_bytes() != contract_bytes:
                raise ValueError('startup scope inputs changed during final validation')
            return {'passed': True, 'native_tree_sha256': scoped['current_binding']['native_tree_sha256'],
                    'current_binding': scoped['current_binding'], 'original_binding': original,
                    'startup_contract_sha256': hashlib.sha256(contract_bytes).hexdigest(),
                    'loading_recovery_runtime_sha256': hashlib.sha256(recovery_bytes).hexdigest() if recovery_bytes else None,
                    'registered_renderer_replayed': False,
                    'checks': [{k: v for k, v in scoped.items() if k not in ('contract', 'proof')},
                               {'id': 'startup.native.retry', 'action': 'rejudged',
                                'reason': '原 Retry 观察按启动请求闭包沿用；当前依赖未变'}],
                    'scope': 'Existing original startup observation; current dependency scope and actual artifact identity verified'}
    if not project or not startup_contract:
        raise ValueError('final Native startup evidence required: --project and --startup-contract; file/Web checks cannot prove HOME')
    native, project = Path(native).resolve(), Path(project).resolve()
    if not native.is_dir() or not project.is_dir():
        raise ValueError('final Native startup project/Native directory missing')
    kit_retry = None
    if not recovery_runtime:
        covered, why = platform_kit_covers_retry(native, project)
        if not covered:
            raise StartupRefused('startup.native.retry',
                                 '--loading-recovery-runtime required unless the unchanged TikTok Platform Kit covers Retry: ' + why)
        kit_retry = why
    contract_path = Path(startup_contract).resolve()
    recovery_path = Path(recovery_runtime).resolve() if recovery_runtime else None
    contract_bytes = contract_path.read_bytes()
    recovery_bytes = recovery_path.read_bytes() if recovery_path else b'{}'
    contract = json.loads(contract_bytes)
    if not isinstance(contract, dict) or contract.get('tool') != 'audit_startup_contract' or contract.get('passed') is not True:
        raise ValueError('final Native startup contract missing or failed')
    if contract.get('policy_version') != 2 or contract.get('runtime_required') is not True:
        raise ValueError('final Native startup requires runtime policy v2; source-only evidence refused')
    if any(not isinstance(contract.get(key), str) or not contract[key]
           for key in ('native', 'project')):
        raise ValueError('final Native startup identity paths must be nonempty strings')
    runtime_project = Path(contract.get('project', '')).resolve()
    # Ant's existing reviewed runner binds the Web-source child while the
    # package/issue ledger belongs to its exact registered workspace. Keep both
    # fixed identities; do not create a second empty issue ledger in Web output.
    workspace_source_pair = False
    if runtime_project != project:
        registry = json.loads(Path(renderer.__file__).with_name('native_startup_trusted_runners.json').read_text())
        proof_ref = contract.get('startup_renderer_report', {})
        proof_file = Path(proof_ref.get('path', '')) if isinstance(proof_ref.get('path'), str) else Path('missing')
        candidate_proof = json.loads(proof_file.read_text()) if proof_file.is_file() else {}
        key = candidate_proof.get('execution', {}).get('registered_runner')
        policy = registry.get(key, {})
        expected = renderer.ANT_EXACT_NATIVE_CANDIDATES.get(key)
        workspace_source_pair = (str(project) == renderer.ANT_R3H_WORKSPACE and
            str(runtime_project) == renderer.ANT_R3H_PROJECT and runtime_project == project/'ant' and
            policy.get('workspace') == str(project) and policy.get('project') == str(runtime_project) and
            policy.get('runner_scope') == 'workspace_root' and expected is not None and
            native == (project/expected).resolve())
    if Path(contract.get('native', '')).resolve() != native or (runtime_project != project and not workspace_source_pair):
        raise ValueError('final Native startup contract project/Native identity mismatch')
    binding = contract.get('binding')
    if not isinstance(binding, dict) or binding.get('native_tree_sha256') != renderer.digest(renderer.tree(native)):
        raise ValueError('final Native startup evidence is stale for this Native tree')
    ref = contract.get('startup_renderer_report', {})
    if not isinstance(ref, dict) or not isinstance(ref.get('path'), str) or not ref['path'] or not isinstance(ref.get('sha256'), str):
        raise ValueError('final Native renderer evidence reference must contain path and sha256')
    proof_path = Path(ref.get('path', ''))
    if not proof_path.is_file() or renderer.sha(proof_path) != ref.get('sha256'):
        raise ValueError('final Native renderer evidence missing or changed')
    proof_bytes = proof_path.read_bytes()
    if hashlib.sha256(proof_bytes).hexdigest() != ref['sha256']:
        raise ValueError('final Native renderer evidence changed while reading')
    proof = json.loads(proof_bytes)
    if not isinstance(proof, dict):
        raise ValueError('final Native renderer proof must be an object')
    errors = renderer.validate(proof, native, binding, runtime_project)
    recovery = json.loads(recovery_bytes)
    if not isinstance(recovery, dict):
        raise ValueError('final loading-recovery runtime must be an object')
    if errors:
        raise ValueError('final Native startup/Retry refused: ' + '; '.join(errors))
    if recovery_path:
        errors = validate_recovery(recovery, binding, recovery_path.parent)
        if errors:
            raise StartupRefused('startup.native.retry', 'final Native startup/Retry refused: ' + '; '.join(errors))
    replay = {}
    # All official callers use the same checked ledger. Passing raw reports alone
    # is never a substitute for a successful, still-valid registered execution.
    from functools import partial
    from regression_scope_gate import startup_replay
    runner = partial(startup_replay, reuse_only=reuse_only, plan_project=project)
    errors = validate_runtime_report(contract, binding, detail=replay, replay_runner=runner)
    if errors:
        raise StartupRefused('startup.native.renderer', 'final Native startup replay refused: ' + '; '.join(errors))
    # Runtime execution and other tasks may touch the candidate/evidence.
    # Rechecking identity is cheap; re-running the browser a second time is not.
    if (renderer.digest(renderer.tree(native)) != binding['native_tree_sha256'] or
            contract_path.read_bytes() != contract_bytes or
            (recovery_path and recovery_path.read_bytes() != recovery_bytes) or
            proof_path.read_bytes() != proof_bytes):
        raise ValueError('Native or startup evidence changed during validation; discard this run')
    # These validators also hash referenced raw files; prevent a late raw-file
    # replacement from inheriting the earlier successful observations.
    errors = renderer.validate(proof, native, binding, runtime_project)
    if recovery_path:
        errors += validate_recovery(recovery, binding, recovery_path.parent)
    elif platform_kit_covers_retry(native, project)[0] is not True:
        errors.append('platform kit changed during validation')
    if errors:
        raise ValueError('final Native startup raw evidence changed during validation: ' + '; '.join(errors))
    checks = [
        {'id': 'startup.native.current_evidence', 'action': 'rejudged',
         'reason': '本版 Native、启动合同、加载遮罩和真实触控结果已核对',
         'evidence': [str(contract_path), str(proof_path)]},
        replay,
        {'id': 'startup.native.retry', 'action': 'rejudged',
         'reason': '核对本版 Retry 原始证据' if recovery_path else kit_retry,
         'evidence': [str(recovery_path)] if recovery_path else [str(KIT_DIR / 'KIT_MANIFEST.json')]},
    ]
    return {'passed': True, 'native_tree_sha256': binding['native_tree_sha256'],
            'startup_contract_sha256': hashlib.sha256(contract_bytes).hexdigest(),
            'loading_recovery_runtime_sha256': hashlib.sha256(recovery_bytes).hexdigest() if recovery_path else None,
            'retry_covered_by_platform_kit': kit_retry,
            'registered_renderer_replayed': replay.get('action') == 'rerun',
            'checks': checks,
            'scope': 'local actual Native entry/adapter/renderer, HOME/input and loading recovery; no physical scan claim'}
