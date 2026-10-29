#!/usr/bin/env python3
"""Check scoped button contracts against raw observations; never operates a game.

One validator is used by local repairs and R06. Contracts come from business
rules, not button.enabled/reason. File hashes prove identity, not truth of UI
observations; touch capture and visual review remain the tester's work.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from input_owner_inventory import inspect_sources


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def file_ref(root, path):
    path = Path(path).resolve()
    return {'path': path.relative_to(Path(root).resolve()).as_posix(), 'sha256': sha(path)}


def read_ref(root, ref, json_file=False):
    if not isinstance(ref, dict) or not isinstance(ref.get('path'), str):
        raise ValueError('missing file reference')
    root = Path(root).resolve()
    path = (root / ref['path']).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size == 0:
        raise ValueError('missing/empty/outside-project artifact: ' + str(path))
    if sha(path) != ref.get('sha256'):
        raise ValueError('changed artifact: ' + str(path))
    return json.loads(path.read_text()) if json_file else path


def expression(value, context, depth=0):
    """Small declarative oracle; no eval, controller code or arbitrary imports."""
    if depth > 24:
        raise ValueError('business expression too deep')
    if not isinstance(value, dict):
        return value
    if 'path' in value:
        current = context
        try:
            for key in value['path'].split('.'):
                if key in {'reason', 'enabled', 'buttonState'}:
                    raise ValueError('expected result must not read button presentation fields')
                current = current[int(key)] if isinstance(current, list) else current[key]
            return current
        except (KeyError, IndexError):
            if 'default' in value:
                return value['default']
            raise ValueError('missing observed business fact: ' + value['path'])
    if len(value) != 1:
        raise ValueError('invalid business expression')
    op, args = next(iter(value.items()))
    if op == 'format':
        raise ValueError('format belongs in expected message')
    values = [expression(a, context, depth + 1) for a in (args if isinstance(args, list) else [args])]
    ops = {
        'eq': lambda: values[0] == values[1], 'ne': lambda: values[0] != values[1],
        'lt': lambda: values[0] < values[1], 'le': lambda: values[0] <= values[1],
        'gt': lambda: values[0] > values[1], 'ge': lambda: values[0] >= values[1],
        'in': lambda: values[0] in values[1], 'not': lambda: not values[0],
        'all': lambda: all(values), 'any': lambda: any(values),
        'add': lambda: sum(values), 'sub': lambda: values[0] - values[1],
        'mul': lambda: math.prod(values), 'div': lambda: values[0] / values[1],
        'floor': lambda: math.floor(values[0]), 'min': lambda: min(values),
        'max': lambda: max(values),
    }
    if op not in ops:
        raise ValueError('unsupported business operation: ' + op)
    return ops[op]()


def message(spec, context):
    if isinstance(spec, str):
        return spec
    # Only named scalar placeholders; no attribute/index traversal in templates.
    import string
    template = spec['template']
    vals = {k: expression(v, context) for k, v in spec['values'].items()}
    for _, name, fmt, conversion in string.Formatter().parse(template):
        if name is not None and (not name.isidentifier() or fmt or conversion):
            raise ValueError('only simple named message placeholders are supported')
    return template.format_map(vals)


def changed_paths(before, after, prefix):
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in before.keys() | after.keys():
            name = prefix + '.' + str(key)
            if key not in before or key not in after:
                result.append(name)
            else:
                result.extend(changed_paths(before[key], after[key], name))
        return result
    return [] if before == after else [prefix]



def validate_input_lifecycle(plan, rows, root):
    """Required scope declaration + raw counter traces, not an attestation of capture truth."""
    errors = []
    def need(ok, why):
        if not ok:
            errors.append('input_lifecycle: ' + why)
    scope = plan.get('input_lifecycle')
    if not isinstance(scope, dict) or type(scope.get('applicable')) is not bool:
        return ['input_lifecycle: explicit applicability and coverage declaration required']
    if not scope['applicable']:
        need(len(scope.get('reason', '').strip()) >= 24, 'specific source-based non-applicability required')
        # Do not let an obvious production touch owner opt out by prose alone.
        sources = [(ref, read_ref(root, ref)) for ref in plan.get('business_sources', [])]
        sources = [(ref, path) for ref, path in sources if path.suffix in {'.ts', '.js', '.cjs', '.mjs'}]
        inventories = inspect_sources([path for _, path in sources])
        for (ref, _), inventory in zip(sources, inventories):
            need(inventory['status'] != 'owner', 'touch ownership found in bound source; cannot opt out: ' + ref['path'])
            need(inventory['status'] != 'unresolved', 'input ownership unresolved; cannot establish non-applicability: ' + ref['path'] + ': ' + inventory['reason'])
        return errors
    groups = scope.get('groups', [])
    need(isinstance(groups, list) and bool(groups), 'nonempty binding group inventory required')
    expected = {
        'missing_terminal': [('start', 'old'), ('hide', None), ('show', None), ('start', 'new'), ('end', 'new')],
        'late_terminal': [('start', 'old'), ('hide', None), ('show', None), ('end', 'old'), ('start', 'new'), ('end', 'new')],
        'cancel': [('start', 'old'), ('cancel', 'old'), ('end', 'old'), ('start', 'new'), ('end', 'new')],
        'disable_reenable': [('start', 'old'), ('disable', None), ('enable', None), ('end', 'old'), ('start', 'new'), ('end', 'new')],
    }
    ids, covered = set(), set()
    affected = {c['id'] for c in plan.get('controls', [])}
    observed = {r.get('id'): r for r in rows if isinstance(r, dict)}
    for group in groups:
        gid = group['id']
        need(gid not in ids, 'duplicate binding group: ' + gid); ids.add(gid)
        controls = group.get('controls', [])
        need(bool(controls) and len(controls) == len(set(controls)) and set(controls) <= affected,
             gid + ': invalid affected controls')
        need(not covered.intersection(controls), gid + ': duplicate binding ownership')
        covered.update(controls)
        trace = read_ref(root, group['trace'], True)
        need(trace.get('schema') == 'input-lifecycle-run.v1', gid + ': raw trace schema required')
        need(trace.get('business_sources') == plan.get('business_sources'), gid + ': stale production source binding')
        need(trace.get('layer') in {'browser_touch', 'isolated_production', 'native_module'}, gid + ': explicit execution layer required')
        scenarios = trace.get('scenarios', {})
        need(set(scenarios) == set(expected), gid + ': missing/unknown interruption scenarios')
        for name, sequence in expected.items():
            events = scenarios.get(name, [])
            need(isinstance(events, list) and len(events) == len(sequence), gid + '/' + name + ': incomplete event sequence')
            if not isinstance(events, list) or len(events) != len(sequence):
                continue
            for i, (event, wanted) in enumerate(zip(events, sequence)):
                need((event.get('type'), event.get('finger')) == wanted, gid + '/' + name + ': wrong/missing termination boundary')
                # Every pre-commit observation must stay at zero; the fresh valid end commits once.
                need(type(event.get('commits')) is int and event['commits'] == int(i == len(events) - 1),
                     gid + '/' + name + ': stale/duplicate commit or new input blocked')
        recovery = group.get('recovery_cases', [])
        need(isinstance(recovery, list) and bool(recovery) and len(recovery) == len(set(recovery)), gid + ': GUI recovery business cases required')
        for key in recovery:
            row = observed.get(key, {})
            need(row.get('control') in controls and row.get('layer') == 'browser_touch', gid + ': recovery must observe affected real UI')
            cid, state = row.get('control'), row.get('state')
            contract = next((c.get('states', {}).get(state, {}) for c in plan['controls'] if c['id'] == cid), {})
            need(contract.get('expect', {}).get('kind') == 'effect', gid + ': recovery needs actual business effect')
            need(row.get('input', {}).get('after_interruption') is True, gid + ': ordinary tap is not recovery input')
    need(covered == affected, 'binding groups must cover all affected controls')
    return errors


def validate(plan, run, root):
    errors, checked = [], []
    def need(ok, why):
        if not ok:
            errors.append(why)
    try:
        if not isinstance(plan, dict) or not isinstance(run, dict):
            raise ValueError('plan and run must be objects')
        need(plan.get('schema') == 'button-state-plan.v1', 'invalid plan schema')
        need(run.get('schema') == 'button-state-run.v1', 'invalid run schema')
        refs = plan.get('business_sources', [])
        need(isinstance(refs, list) and bool(refs), 'business source/config binding required')
        for ref in refs:
            read_ref(root, ref)
        need(run.get('business_sources') == refs, 'run does not bind the planned business sources')
        controls = plan.get('controls', [])
        need(isinstance(controls, list) and bool(controls), 'nonempty affected control inventory required')
        domains = plan.get('business_domains')
        need(isinstance(domains, list) and bool(domains) and all(isinstance(x, str) and x for x in domains),
             'protected business_domains required')
        expected, pages, known, visibility = {}, {}, set(), {}
        for control in controls:
            if not isinstance(control, dict):
                raise ValueError('control must be an object')
            cid, page = control['id'], control['page']
            need(cid not in known, 'duplicate control: ' + cid)
            known.add(cid)
            pages.setdefault(page, set()).add(cid)
            visibility[cid] = control.get('visible_when', True)
            states = control.get('states')
            need(isinstance(states, dict) and bool(states), 'applicable states missing: ' + cid)
            for state, contract in (states or {}).items():
                if not isinstance(contract, dict):
                    raise ValueError('state contract must be an object')
                key = cid + '::' + state
                expected[key] = (page, cid, state, contract)
        for excluded in plan.get('excluded_controls', []):
            if not isinstance(excluded, dict):
                raise ValueError('excluded control must be an object')
            cid, page = excluded['id'], excluded['page']
            need(cid not in known, 'duplicate/excluded affected control: ' + cid)
            need(isinstance(excluded.get('why'), str) and len(excluded['why'].strip()) >= 12,
                 'specific scope exclusion required: ' + cid)
            known.add(cid)
            pages.setdefault(page, set()).add(cid)
            visibility[cid] = excluded.get('visible_when', True)
        rows = run.get('cases', [])
        need(isinstance(rows, list) and bool(rows), 'nonempty observed case inventory required')
        actual = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('case must be an object')
            key = row.get('id')
            need(key not in actual, 'duplicate observed case: ' + str(key))
            actual[key] = row
        errors.extend(validate_input_lifecycle(plan, rows, root))
        for key in sorted(expected.keys() - actual.keys()):
            errors.append('missing control/state: ' + key)
        for key in sorted(actual.keys() - expected.keys()):
            errors.append('unplanned observed case: ' + str(key))
        for key in sorted(expected.keys() & actual.keys()):
            start = len(errors)
            page, cid, state, contract = expected[key]
            row = actual[key]
            context = {'before': row['before'], 'after': row['after']}
            need((row.get('page'), row.get('control'), row.get('state')) == (page, cid, state), key + ': identity mismatch')
            need(row.get('status') == 'tested', key + ': untested/fail/n/a cannot pass')
            layer = contract.get('layer', 'browser_touch')
            need(layer in {'browser_touch', 'isolated_production'}, key + ': invalid planned input layer')
            need(row.get('layer') == layer, key + ': observation layer mismatch')
            if layer == 'isolated_production':
                need(len(contract.get('why_isolated', '').strip()) >= 12, key + ': state needs explicit isolated-test boundary')
            need(row.get('input', {}).get('performed') is True, key + ': actual input receipt required')
            visible = row.get('visible_controls', [])
            if not isinstance(visible, list) or not all(isinstance(x, str) for x in visible):
                raise ValueError('visible_controls must be a string list')
            need(isinstance(visible, list) and len(visible) == len(set(visible)), key + ': invalid/duplicate visible control inventory')
            wanted_visible = {x for x in pages[page] if expression(visibility[x], {'before': row['before']}) is True}
            need(cid in wanted_visible and set(visible) == wanted_visible,
                 key + ': visible inventory differs from business-derived expected controls')
            evidence = row.get('evidence', [])
            need(isinstance(evidence, list) and bool(evidence), key + ': raw evidence required')
            for ref in evidence:
                read_ref(root, ref)
            need('when' in contract and expression(contract['when'], {'before': row['before']}) is True,
                 key + ': observed business facts do not reach the planned state')
            expect = contract['expect']
            kind = expect.get('kind')
            need(kind in {'blocked', 'effect'}, key + ': expected blocked/effect outcome required')
            if kind == 'blocked':
                feedback = row.get('feedback', {})
                need(bool(feedback.get('after_id')) and feedback.get('after_id') != feedback.get('before_id'),
                     key + ': no fresh feedback')
                wanted = message(expect['message'], context)
                need(bool(wanted) and feedback.get('text') == wanted, key + ': feedback does not match business condition')
                need(bool(expect.get('unchanged')), key + ': blocked outcome must protect business data')
            if kind == 'effect':
                need(bool(expect.get('after') or expect.get('assert')), key + ': business effect assertions required')
            for assertion in expect.get('assert', []):
                need(expression(assertion, context) is True, key + ': business result assertion failed')
            for field in expect.get('unchanged', []):
                need(expression({'path': 'before.' + field}, context) == expression({'path': 'after.' + field}, context),
                     key + ': changed protected business data: ' + field)
            for field, wanted in expect.get('after', {}).items():
                need(expression({'path': 'after.' + field}, context) == expression(wanted, {'before': row['before']}),
                     key + ': wrong business result: ' + field)
            allowed = list(expect.get('after', {})) + expect.get('allow_changes', []) if kind == 'effect' else []
            for domain in domains or []:
                need(domain not in allowed, key + ': whole protected business domain cannot be exempted')
                before = expression({'path': 'before.' + domain}, context)
                after = expression({'path': 'after.' + domain}, context)
                for changed in changed_paths(before, after, domain):
                    need(any(changed == x or changed.startswith(x + '.') for x in allowed),
                         key + ': unexpected business mutation: ' + changed)
            checked.append({'id': key, 'layer': layer, 'passed': start == len(errors)})
    except (KeyError, TypeError, ValueError, OSError, IndexError, ZeroDivisionError, AttributeError) as exc:
        errors.append('invalid contract/observation: ' + str(exc))
    return {'tool': 'button_state_check', 'schema': 1, 'policy_version': 2, 'passed': not errors,
            'required': len(expected) if 'expected' in locals() else 0,
            'observed': len(actual) if 'actual' in locals() else 0,
            'cases': checked, 'errors': errors}


def make_report(root, plan_path, run_path):
    root = Path(root).resolve()
    p, r = file_ref(root, plan_path), file_ref(root, run_path)
    plan, run = read_ref(root, p, True), read_ref(root, r, True)
    result = validate(plan, run, root)
    result['project_root'] = str(root)
    result['inputs'] = {'plan': p, 'run': r}
    return result


def current_report(root, ref):
    """Revalidate raw inputs and business bindings; do not trust a pass flag."""
    try:
        report = read_ref(root, ref, True)
        if report.get('tool') != 'button_state_check' or report.get('schema') != 1 or report.get('passed') is not True:
            return False
        plan = read_ref(root, report['inputs']['plan'], True)
        run = read_ref(root, report['inputs']['run'], True)
        return validate(plan, run, root)['passed']
    except (KeyError, TypeError, ValueError, OSError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        result = make_report(args.project, args.plan, args.run)
    except (ValueError, OSError) as exc:
        result = {'tool': 'button_state_check', 'schema': 1, 'passed': False, 'errors': [str(exc)]}
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: result.get(k) for k in ('passed', 'required', 'observed', 'errors')}, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
