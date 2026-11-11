"""Extract original per-entry observations from older atomic runtime reports.

This module does not register a pass for a new build. The caller must independently
verify dependency and assertion equivalence before using the returned observation.
Original binding, failure status, execution time and frozen evidence are retained.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys


CORE = Path(__file__).resolve().parents[3] / 'remake-core/scripts'
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))
import check_ledger as ledger


def need(condition, message):
    if not condition:
        raise ValueError('runtime split migration: ' + message)


def file_ref(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def _document(record, path):
    expected = {row['path']: row['sha256'] for row in record.get('files', [])}
    need(isinstance(path, str) and path in expected, 'report is not part of the frozen source observation')
    actual = file_ref(path)
    need(actual['sha256'] == expected[path], 'source evidence changed: ' + path)
    value = json.loads(Path(path).read_text())
    need(isinstance(value, dict), 'source evidence must be an object')
    return value, actual


def _case(rows, identity):
    matching = [row for row in rows if isinstance(row, dict) and row.get('id') == identity]
    need(len(matching) == 1 and matching[0].get('passed') is True,
         'original case did not pass independently: ' + identity)
    return copy.deepcopy(matching[0])


def extract_unit(record, suite, unit):
    """Return an original observation, retaining the exact source identity.

    A failed aggregate may contain successful ad entries. Each entry needs both
    original cancellation and completion verdicts and detailed report rows. A
    save step requires a successful original cold restart, never only earnings.
    """
    need(isinstance(record, dict), 'source record missing')
    need(record.get('check_id') == 'runtime.' + suite + '/@suite',
         'source is not the original atomic suite')
    need(record.get('binding', {}).get('check_id') == record['check_id'],
         'source binding and record disagree')
    need(bool(record.get('key')) and bool(record.get('executed_at')), 'original execution identity missing')
    for item in record.get('files', []):
        actual = file_ref(item['path'])
        need(actual['sha256'] == item['sha256'], 'original frozen file changed: ' + item['path'])
    source = record.get('result', {})
    need(source.get('suite') == suite, 'source result names another suite')
    need(not source.get('fatal') and not source.get('proof_error') and not source.get('batch_problems'),
         'source observation has a fatal or batch-level error')
    report, report_ref = _document(record, source.get('evidence', {}).get('report'))
    need(report.get('suite') == suite, 'detailed report names another suite')
    cases = source.get('cases') or []
    if suite == 'ad_outcome':
        entries = report.get('entries')
        need(isinstance(entries, list), 'original entry catalogue missing')
        if unit == '@discovered':
            ids = [row['id'] for row in entries if row.get('from') == 'button_sweep']
        else:
            matched = [row for row in entries if row.get('id') == unit]
            need(len(matched) == 1 and matched[0].get('from') in ('ad_entries', 'resume_play.ad'),
                 'entry was not in the original declared catalogue: ' + unit)
            ids = [unit]
        selected = []
        for identity in ids:
            rows = [row for row in report.get('cases', []) if row.get('id') == identity]
            need(len(rows) == 1, 'detailed entry observation is missing: ' + identity)
            row = rows[0]
            need(row.get('cancel_result') == 'pass' and row.get('complete_result') == 'pass',
                 'entry cancellation and completion were not both observed passing: ' + identity)
            selected.extend([_case(cases, identity + '/cancel'), _case(cases, identity + '/complete')])
        if not selected:
            selected = [{'id': '@discovered', 'passed': True,
                         'detail': 'original observed entry catalogue contains no additional discovered routes'}]
    elif suite == 'save_restart':
        if unit == '@kinds':
            kinds = report.get('kinds')
            need(isinstance(kinds, dict) and kinds.get('missing') == [],
                 'original home-derived kind coverage did not pass')
            selected = [{'id': '@kinds', 'passed': True,
                         'detail': 'original observed home and full step declarations covered the required kinds'}]
        else:
            need(unit.startswith('step/'), 'unknown save restart unit')
            name = unit[len('step/'):]
            need(record.get('passed') is True and source.get('passed') is True,
                 'original aggregate did not complete a successful cold restart')
            _case(cases, 'restart')
            need(report.get('result') == 'pass' and bool(report.get('after_png')),
                 'original successful cold-restart report is missing')
            steps = [row for row in report.get('steps', []) if row.get('name') == name]
            need(len(steps) == 1, 'original save step missing or ambiguous: ' + name)
            step = steps[0]
            need(all(key in step for key in ('before', 'after', 'after_restart')) and not step.get('stuck'),
                 'step has no completed before/after/restart observation')
            need(step['before'] != step['after'] and step['after'] == step['after_restart'],
                 'step did not earn and retain the original value')
            selected = [{'id': unit, 'passed': True, 'detail': {
                'name': name, 'kind': step.get('kind'), 'before': copy.deepcopy(step['before']),
                'after': copy.deepcopy(step['after']), 'after_restart': copy.deepcopy(step['after_restart'])}}]
    else:
        raise ValueError('runtime split migration: unsupported suite ' + str(suite))
    return {
        'suite': suite, 'unit': unit, 'passed': True, 'cases': selected, 'problems': [],
        'warnings': list(source.get('warnings') or []), 'evidence': copy.deepcopy(source.get('evidence')),
        'raw_files': list(source.get('raw_files') or []), 'seconds': record.get('seconds'),
        'browser': source.get('browser', True),
        'inheritance': {
            'schema': 'runtime-unit-observation.v1', 'source_key': record['key'],
            'source_check_id': record['check_id'], 'source_passed': record.get('passed') is True,
            'executed_at': record['executed_at'], 'source_binding': copy.deepcopy(record['binding']),
            'source_roots': copy.deepcopy(record.get('roots', {})), 'report': report_ref,
            'case_ids': [row['id'] for row in selected], 'execution_repeated': False,
            'target_dependency_validation': 'required_from_independently_reviewed_caller'
        }
    }


INHERITANCE_SCHEMA = 'runtime-unit-inheritance.v1'


def _inheritance_need(condition, message):
    if not condition:
        raise ledger.NeedsScope('runtime unit inheritance: ' + message)


def _inheritance_ref(value, label, *, python=False):
    """Resolve an explicitly hash-bound local file, never a command string."""
    _inheritance_need(isinstance(value, dict), label + ' must be a path/sha256 object')
    path, expected = value.get('path'), value.get('sha256')
    _inheritance_need(isinstance(path, str) and Path(path).is_absolute(),
                      label + ' requires an absolute path')
    _inheritance_need(isinstance(expected, str) and len(expected) == 64
                      and all(ch in '0123456789abcdef' for ch in expected),
                      label + ' requires an exact SHA-256')
    path = Path(path).resolve()
    _inheritance_need(path.is_file(), label + ' file is missing: ' + str(path))
    _inheritance_need(not python or path.suffix == '.py',
                      label + ' must be a Python .py file')
    actual = file_ref(path)
    _inheritance_need(actual['sha256'] == expected, label + ' bytes do not match: ' + str(path))
    return actual


def _unchanged_refs(refs):
    for ref in refs:
        actual = file_ref(ref['path'])
        _inheritance_need(actual == ref, 'file changed during validation: ' + ref['path'])


def _dependency_equivalence(declaration, source, plan):
    proof = declaration.get('dependency_proof')
    _inheritance_need(isinstance(proof, dict),
                      plan['check_id'] + ': changed package dependencies require dependency_proof')
    validator = _inheritance_ref(proof.get('validator'), 'dependency proof validator', python=True)
    report = _inheritance_ref(proof.get('report'), 'dependency proof report')
    try:
        completed = subprocess.run(
            [sys.executable, '-B', validator['path'], '--verify', report['path']],
            check=False, capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ledger.NeedsScope('runtime unit inheritance: offline dependency validator failed: '
                                + str(error)) from error
    # Validate immutable inputs even when the subprocess refuses its report.
    _unchanged_refs([validator, report])
    _inheritance_need(completed.returncode == 0,
                      'offline dependency validator refused the report: '
                      + (completed.stderr.strip() or completed.stdout.strip())[:1000])
    try:
        verified = json.loads(completed.stdout)
    except (ValueError, TypeError) as error:
        raise ledger.NeedsScope('runtime unit inheritance: offline validator must return one JSON object') from error
    _inheritance_need(isinstance(verified, dict) and verified.get('passed') is True,
                      'offline dependency validator did not prove equivalence')
    _inheritance_need(verified.get('source_package_tree') == ledger.sha(source['roots']['package']),
                      'dependency proof names another source package tree')
    _inheritance_need(verified.get('target_package_tree') == ledger.sha(plan['roots']['package']),
                      'dependency proof names another target package tree')
    units = verified.get('units')
    _inheritance_need(isinstance(units, (list, dict)) and plan['check_id'] in units,
                      'dependency proof does not cover this exact unit: ' + plan['check_id'])
    return {'validator': validator, 'report': report, 'verification': verified}


def prepare_inherited_unit(store, plan, suite, unit):
    """Reuse an independently observed old unit after explicit identity validation.

    No new execution or database pass is written. The returned plan retains the
    current binding, while its derived record retains the source binding, roots,
    observation time and aggregate verdict. A missing declaration leaves a run
    untouched; an invalid declaration raises NeedsScope without mutating it.

    A changed selected package dependency additionally requires a reviewed local
    Python validator and report, each bound by absolute path and SHA-256. The
    validator is invoked directly, without a shell, and must independently verify
    the report against both full package trees and this exact target unit ID.
    """
    if plan.get('action') != 'run':
        return plan
    project = Path(store.project).resolve()
    declaration_path = project / 'docs/checks/runtime-unit-inheritance.json'
    if not declaration_path.is_file():
        return plan
    cid = 'runtime.' + suite + '/' + unit
    try:
        declaration_ref = file_ref(declaration_path)
        document = json.loads(declaration_path.read_text())
        _inheritance_need(isinstance(document, dict) and document.get('schema') == INHERITANCE_SCHEMA,
                          'invalid inheritance declaration schema')
        declarations = document.get('units')
        _inheritance_need(isinstance(declarations, dict), 'inheritance units must be an object')
        if cid not in declarations:
            _unchanged_refs([declaration_ref])
            return plan
        declaration = declarations[cid]
        _inheritance_need(isinstance(declaration, dict), cid + ': declaration must be an object')
        _inheritance_need(unit != '@suite' and plan.get('check_id') == cid,
                          cid + ': declaration must identify the exact split unit')
        binding = plan.get('binding')
        _inheritance_need(isinstance(binding, dict) and binding.get('check_id') == cid
                          and plan.get('key') == ledger.sha(binding),
                          cid + ': current plan binding/key mismatch')
        scope = ledger.scope_for(project, cid)
        _inheritance_need(scope is not None and scope == plan.get('scope')
                          and ledger.sha(scope) == binding.get('scope_sha256'),
                          cid + ': current explicit dependency scope is missing or changed')
        _inheritance_need(all(name in scope['inputs'] for name in ('package', 'adapter')),
                          cid + ': scope must bind both package and adapter dependencies')
        roots = plan.get('roots')
        _inheritance_need(isinstance(roots, dict)
                          and all(isinstance(roots.get(name), dict) for name in ('package', 'adapter')),
                          cid + ': current package/adapter roots are missing')
        current_inputs = ledger.select_inputs(roots, scope)
        _inheritance_need(current_inputs == binding.get('inputs'), cid + ': current selected inputs changed')
        source_key = declaration.get('source_key')
        _inheritance_need(isinstance(source_key, str) and len(source_key) == 64
                          and all(ch in '0123456789abcdef' for ch in source_key),
                          cid + ': source_key must identify one real ledger row')
        found = store.db.execute('SELECT key,check_id,data FROM records WHERE key=?', (source_key,)).fetchone()
        _inheritance_need(found is not None, cid + ': source ledger row does not exist: ' + source_key)
        source = json.loads(found[2])
        source_cid = 'runtime.' + suite + '/@suite'
        _inheritance_need(isinstance(source, dict) and found[0] == source_key
                          and found[1] == source_cid and source.get('check_id') == source_cid,
                          cid + ': source row is not the declared original atomic suite')
        source_binding = source.get('binding')
        _inheritance_need(isinstance(source_binding, dict) and source_binding.get('check_id') == source_cid
                          and ledger.sha(source_binding) == source_key
                          and source.get('key', source_key) == source_key,
                          cid + ': original source binding/key mismatch')
        _inheritance_need(isinstance(declaration.get('source_tool_sha256'), str)
                          and declaration['source_tool_sha256'] == source_binding.get('tool_sha256'),
                          cid + ': original source tool identity mismatch')
        _inheritance_need(isinstance(declaration.get('target_tool_sha256'), str)
                          and declaration['target_tool_sha256'] == binding.get('tool_sha256'),
                          cid + ': current target tool identity mismatch')
        _inheritance_need(source_binding.get('conditions') == binding.get('conditions'),
                          cid + ': original and current execution conditions differ')
        assertions = declaration.get('assertion_files')
        _inheritance_need(isinstance(assertions, list) and bool(assertions),
                          cid + ': reviewed assertion_files must be non-empty')
        assertion_refs = [_inheritance_ref(item, 'reviewed assertion file') for item in assertions]
        _inheritance_need(len({ref['path'] for ref in assertion_refs}) == len(assertion_refs),
                          cid + ': assertion_files contains duplicate files')
        source_roots = source.get('roots')
        _inheritance_need(isinstance(source_roots, dict)
                          and all(isinstance(source_roots.get(name), dict) for name in ('package', 'adapter')),
                          cid + ': original package/adapter roots are missing')
        source_inputs = ledger.select_inputs(source_roots, scope)
        _inheritance_need({name: value for name, value in source_inputs.items() if name != 'package'}
                          == {name: value for name, value in current_inputs.items() if name != 'package'},
                          cid + ': original and current adapter/non-package dependencies differ')
        # The SQL key, rather than a caller-supplied JSON field, identifies the
        # exact source observation. extract_unit rehashes every original raw file.
        source['key'] = found[0]
        observation = extract_unit(source, suite, unit)
        _inheritance_need(observation.get('passed') is True,
                          cid + ': original unit did not independently pass')
        proof = None
        if source_inputs['package'] != current_inputs['package']:
            proof = _dependency_equivalence(declaration, source, plan)
        metadata = observation['inheritance']
        metadata.update({
            'declaration': declaration_ref,
            'target_check_id': cid,
            'target_key': plan['key'],
            'target_binding': copy.deepcopy(binding),
            'source_tool_sha256': declaration['source_tool_sha256'],
            'target_tool_sha256': declaration['target_tool_sha256'],
            'assertion_files': assertion_refs,
            'source_package_tree': ledger.sha(source_roots['package']),
            'target_package_tree': ledger.sha(roots['package']),
            'source_selected_inputs': copy.deepcopy(source_inputs),
            'target_selected_inputs': copy.deepcopy(current_inputs),
            'target_dependency_validation': 'offline_validator' if proof else 'identical_selected_inputs',
            'dependency_proof': proof,
        })
        final_refs = [declaration_ref, *assertion_refs, *source.get('files', [])]
        if proof:
            final_refs.extend([proof['validator'], proof['report']])
        _unchanged_refs(final_refs)
        # The source DB row must remain the same observation throughout validation.
        unchanged = store.db.execute('SELECT check_id,data FROM records WHERE key=?', (source_key,)).fetchone()
        _inheritance_need(unchanged is not None and unchanged[0] == found[1] and unchanged[1] == found[2],
                          cid + ': original ledger row changed during validation')
        observation['evidence'] = copy.deepcopy(observation.get('evidence') or {})
        _inheritance_need(isinstance(observation['evidence'], dict), cid + ': source evidence must be an object')
        observation['evidence'].setdefault('runtime_unit_inheritance', {})[cid] = copy.deepcopy(metadata)
        # Runtime aggregate receipts flatten cases and select one suite evidence
        # object. Carry provenance per case so no unit's dependency proof is lost.
        for case in observation.get('cases', []):
            case['runtime_unit_inheritance'] = copy.deepcopy(metadata)
        record = copy.deepcopy(source)
        record.update(result=observation, passed=True, source_passed=source.get('passed') is True,
                      derived_for=cid, inheritance=copy.deepcopy(metadata))
        record['files'] = copy.deepcopy(final_refs)
        inherited = copy.deepcopy(plan)
        inherited.update(action='reuse', record=record,
                         why='原始独立观察及当前依赖已核对；保留原执行时间，不重新执行',
                         inheritance=copy.deepcopy(metadata))
        return inherited
    except ledger.NeedsScope:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise ledger.NeedsScope('runtime unit inheritance: ' + cid + ': ' + str(error)) from error
