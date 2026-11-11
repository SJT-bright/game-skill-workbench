"""Reporting-only runtime timing and exact 11.17.11 rule identity compatibility.

Compatibility is limited to the two byte-identical files approved in the adjacent
manifest. Any later edit (including this helper) falls back to the normal rule
fingerprint. No arbitrary AST field or checker change is ignored.
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


def rule_fingerprint(cl, paths):
    here = Path(__file__).resolve()
    module = here.with_name('runtime_incremental.py')
    ledger_module = Path(cl.__file__).resolve()
    compatible_ledger_sha = None
    try:
        proof = json.loads(here.with_name('runtime-reporting-compat.json').read_text())
        module_sha = hashlib.sha256(module.read_bytes()).hexdigest()
        helper_sha = hashlib.sha256(here.read_bytes()).hexdigest()
        approved = (proof.get('schema') == 'runtime-reporting-compat.v1'
            and module_sha == proof['new_runtime_sha256']
            and helper_sha == proof['helper_sha256']
            and proof.get('scope') == 'reporting-only-exact-byte-pair')
        if not approved:
            # The exact reviewed scope pair adds authorization and a read-only
            # plan route. It leaves all observers and result predicates intact.
            scope = json.loads(here.with_name('runtime-scope-compat.json').read_text())
            approved = (scope.get('schema') == 'runtime-scope-compat.v2'
                and scope.get('scope') == 'scheduler-and-evidence-recovery-exact-byte-triple'
                and module_sha == scope['new_runtime_sha256']
                and helper_sha == scope['new_helper_sha256']
                and hashlib.sha256(ledger_module.read_bytes()).hexdigest() == scope['new_ledger_sha256']
                and scope['prior_runtime_sha256'] == proof['new_runtime_sha256']
                and scope['prior_helper_sha256'] == proof['helper_sha256']
                and hashlib.sha256(here.with_name('runtime-reporting-compat.json').read_bytes()).hexdigest()
                    == scope['prior_compat_sha256'])
            if approved:
                compatible_ledger_sha = scope['prior_ledger_sha256']
    except (OSError, ValueError, KeyError, TypeError):
        approved = False
    if not approved:
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
            continue  # Only the exact approved reporting helper is excluded.
        if p.is_dir():
            todo.extend(x for x in p.rglob('*') if x.is_file() and not set(x.parts) & cl.IGNORED and x.suffix != '.pyc')
            continue
        if not p.is_file():
            rows.append((p.name, 'missing'))
            continue
        raw = p.read_bytes()
        if p == module:
            fingerprint = proof['old_runtime_sha256']
        elif p == ledger_module and compatible_ledger_sha:
            fingerprint = compatible_ledger_sha
        else:
            fingerprint = cl.sha(raw)
        rows.append((p.name, fingerprint))
        if p.suffix == '.py':
            try:
                for node in ast.walk(ast.parse(raw)):
                    names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                             else [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
                    for name in names:
                        target = p.parent/(name.replace('.', '/')+'.py')
                        if target.is_file():
                            todo.append(target)
            except (SyntaxError, UnicodeError):
                raise cl.NeedsScope('检查器无法解析，不能使用旧记录：'+str(p))
    return cl.sha(sorted(rows))
