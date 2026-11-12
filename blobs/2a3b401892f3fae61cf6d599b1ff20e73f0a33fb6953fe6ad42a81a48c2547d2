"""Runtime timing and exact reviewed scheduling identity compatibility.

The adjacent fixed manifest binds every changed scheduler/helper and the original
import sources. Real observers always retain their actual file hashes. Unknown
bytes use the ordinary fingerprint; legacy overlays then require diagnosis.
"""
import ast
import hashlib
import json
from pathlib import Path


def suite_seconds(report, name, reused):
    if reused:
        return 0.0
    row = next((r for r in report.get('suites', []) if r.get('suite') == name), {})
    value = row.get('seconds')
    # An unmeasured suite stays unknown. Do not substitute its whole batch.
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else None


def suite_metadata(report, name, reused):
    return {'schema': 'runtime-timing.v1', 'reused': reused,
            'scope': 'reused' if reused else 'suite' if suite_seconds(report, name, False) is not None else 'shared_batch',
            'batch_id': None if reused else report.get('_timing_batch_id'),
            'additive': False, 'note': 'Use summary.seconds for total wall time; suites may overlap.'}


def rule_fingerprint(cl, paths, *, source_overrides=None):
    """Hash real observers, with one fixed reviewed scheduler import tree.

    Old suite overlays are private migration inputs: they must equal the pinned
    legacy fixture and its whole-file reviewed target. They never affect normal
    runner fingerprints, and unknown scheduler bytes disable every overlay.
    """
    overrides = {Path(path).resolve(): raw for path, raw in (source_overrides or {}).items()}
    if any(not isinstance(raw, bytes) for raw in overrides.values()):
        raise ValueError('fingerprint source overrides must contain bytes')
    here = Path(__file__).resolve()
    module = here.with_name('runtime_incremental.py')
    ledger_module = Path(cl.__file__).resolve()
    fixtures = ledger_module.parent/'fixtures/reviewed-legacy-suites'
    approved = False
    try:
        proof = json.loads(here.with_name('runtime-reporting-compat.json').read_text())
        scope = json.loads(here.with_name('runtime-scope-compat.json').read_text())
        prior_scope_raw = (fixtures/'runtime-scope-compat.prior.json').read_bytes()
        prior_scope = json.loads(prior_scope_raw)
        runtime_source = (fixtures/'runtime_incremental.py').read_bytes()
        ledger_raw = ledger_module.read_bytes()
        ledger_identity, ledger_source = cl._tool_compat_source(ledger_module, ledger_raw)
        review_raw = (fixtures/'unit-rule-review.json').read_bytes()
        approved = (scope.get('schema') == 'runtime-scope-compat.v3'
            and scope.get('scope') == 'scoped-module-input-and-unit-scheduler-exact-byte-set'
            and cl.sha(module.read_bytes()) == scope['new_runtime_sha256']
            and cl.sha(here.read_bytes()) == scope['new_helper_sha256']
            and cl.sha(ledger_raw) == scope['new_ledger_sha256']
            and cl.sha(ledger_module.with_name('bundle_module_inputs.py').read_bytes()) == scope['module_helper_sha256']
            and cl.sha(ledger_module.with_name('runtime_unit_reuse.py').read_bytes()) == scope['unit_reuse_sha256']
            and cl.sha(review_raw) == scope['unit_review_sha256']
            and cl.sha(runtime_source) == scope['scheduler_source_sha256']
            and cl.sha(ledger_source) == scope['ledger_source_sha256']
            and cl.sha(prior_scope_raw) == scope['scheduler_prior_compat_sha256']
            and prior_scope.get('schema') == 'runtime-scope-compat.v2'
            and prior_scope['new_runtime_sha256'] == scope['scheduler_source_sha256']
            and prior_scope['new_ledger_sha256'] == scope['ledger_source_sha256']
            and scope['prior_runtime_sha256'] == prior_scope['prior_runtime_sha256'] == proof['new_runtime_sha256']
            and scope['prior_helper_sha256'] == prior_scope['prior_helper_sha256'] == proof['helper_sha256']
            and scope['prior_compat_sha256'] == prior_scope['prior_compat_sha256']
                == cl.sha(here.with_name('runtime-reporting-compat.json').read_bytes())
            and ledger_identity == scope['prior_ledger_sha256'] == prior_scope['prior_ledger_sha256'])
        if approved and overrides:
            reviewed = json.loads(review_raw)['suites']
            for path, raw in overrides.items():
                suite = path.stem
                if (suite not in reviewed or path != (here.parent/'runtime_regression/suites'/(suite+'.mjs')).resolve()
                        or cl.sha(raw) != reviewed[suite]['old_sha256']
                        or raw != (fixtures/(suite+'.mjs')).read_bytes()
                        or cl.sha(path.read_bytes()) != reviewed[suite]['new_sha256']):
                    raise cl.NeedsScope('旧断言 overlay 不属于固定整文件规则审查对')
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        approved = False
    if not approved:
        if overrides:
            raise cl.NeedsScope('旧断言指纹迁移需要已核准的精确调度/规则版本')
        return cl.tool_fingerprint(paths)
    todo = [Path(p).resolve() for p in paths]
    seen = set()
    rows = []
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        if p == here:
            continue
        if p.is_dir():
            todo.extend(x for x in p.rglob('*') if x.is_file() and not set(x.parts) & cl.IGNORED and x.suffix != '.pyc')
            continue
        if not p.is_file():
            rows.append((p.name, 'missing'))
            continue
        raw = overrides.get(p, p.read_bytes())
        if p == module:
            fingerprint, import_source = proof['old_runtime_sha256'], runtime_source
        elif p == ledger_module:
            fingerprint, import_source = ledger_identity, ledger_source
        else:
            fingerprint, import_source = cl.sha(raw), raw
        rows.append((p.name, fingerprint))
        if p.suffix == '.py':
            try:
                for node in ast.walk(ast.parse(import_source)):
                    names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                             else [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
                    for name in names:
                        target = p.parent/(name.replace('.', '/')+'.py')
                        if target.is_file():
                            todo.append(target)
            except (SyntaxError, UnicodeError):
                raise cl.NeedsScope('检查器无法解析，不能使用旧记录：'+str(p))
    return cl.sha(sorted(rows))
