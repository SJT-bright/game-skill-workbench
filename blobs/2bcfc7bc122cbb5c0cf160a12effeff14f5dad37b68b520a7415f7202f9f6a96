#!/usr/bin/env python3
"""Fail-closed storage-contract gate for the actual Native bundle and adapter.

The project runner produces raw case results. This tool binds those results to
the final Native bytes, checks the required matrix, and verifies that the same
runner reproduced the reported defect on an older bundle.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

CASES = (
    'missing_null', 'missing_undefined', 'missing_empty_string',
    'valid_json_string', 'valid_typed_object', 'valid_legacy_record',
    'pending_restart_recovery', 'malformed_json_blocked',
    'empty_object_blocked', 'zero_blocked', 'false_blocked',
    'wrong_schema_blocked', 'wrong_scope_blocked',
    'read_throw_diagnostic', 'write_throw_no_grant',
    'readback_mismatch_no_grant', 'typed_readback_verified',
    'retry_after_transient_failure', 'reopen_home',
    'reopen_map', 'reopen_stage_details',
    'ad_cancel_no_grant', 'completed_reward_once',
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def inside(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    return path.is_file() and path.is_relative_to(root)


def validate(trace, native, expected_binding):
    errors = []
    if trace.get('schema') not in ('native_storage_trace.v1', 'native_storage_trace.v2'):
        errors.append('trace schema')
    if trace.get('binding') != expected_binding:
        errors.append('current build binding')
    execution = trace.get('execution', {})
    runner = Path(execution.get('runner', ''))
    command = execution.get('command', [])
    if (not runner.is_file() or digest(runner) != execution.get('runner_sha256') or
            not isinstance(command, list) or not all(isinstance(part, str) for part in command) or str(runner) not in command or
            '{bundle}' not in command or '{adapter}' not in command):
        errors.append('real runner identity and command')
    routes = None
    if trace.get('schema') == 'native_storage_trace.v2':
        try:
            from maintenance_scope import source_inventory
            from check_known_issues import tree_sha
            if tree_sha(native) != expected_binding.get('native_tree_sha256'):
                raise ValueError('final Native tree differs from binding')
            routes = source_inventory(trace.get('route_inventory'), Path(trace.get('trace_base', '.')), trace.get('project', ''), expected_binding)['routes']
        except (ValueError, OSError, TypeError, KeyError) as exc:
            errors.append('verified existing routes: '+str(exc))
    current = trace.get('current', {})
    old = trace.get('negative_control', {})
    for label, record in (('current', current), ('negative', old)):
        bundle = Path(record.get('bundle', ''))
        adapter = Path(record.get('adapter', ''))
        raw = Path(record.get('raw_report', ''))
        if not all(p.is_file() for p in (bundle, adapter, raw)):
            errors.append(label + ' files missing')
            continue
        if label == 'current' and (not inside(native, bundle) or not inside(native, adapter)):
            errors.append('current bundle/adapter outside final Native tree')
        if digest(bundle) != record.get('bundle_sha256') or digest(adapter) != record.get('adapter_sha256') or digest(raw) != record.get('raw_sha256'):
            errors.append(label + ' bytes changed')
            continue
        try:
            result = read(raw)
        except (ValueError, OSError):
            errors.append(label + ' raw result invalid')
            continue
        if not isinstance(result, dict):
            errors.append(label + ' raw result is not an object')
            continue
        if result.get('runner_sha256') != execution.get('runner_sha256') or result.get('bundle_sha256') != record.get('bundle_sha256') or result.get('adapter_sha256') != record.get('adapter_sha256'):
            errors.append(label + ' raw execution identity mismatch')
        cases = result.get('cases', {})
        if not isinstance(cases, dict):
            errors.append(label + ' cases invalid')
            continue
        if label == 'current':
            for name in CASES:
                route = {'reopen_map':'map', 'reopen_stage_details':'stage_details'}.get(name)
                expected = 'not_applicable' if route and routes and routes[route]['present'] is False else 'pass'
                if cases.get(name) != expected:
                    errors.append('current case missing or failed: ' + name + ' (requires '+expected+')')
        else:
            if cases.get('missing_empty_string') != 'fail':
                errors.append('negative did not reproduce missing-empty-string defect')
            if trace.get('schema') == 'native_storage_trace.v2':
                kind = record.get('kind')
                if kind not in ('historical_release','controlled_legacy_fixture'):
                    errors.append('negative provenance kind required')
                try:
                    from maintenance_scope import checked_ref
                    checked_ref(record.get('provenance'), Path(trace.get('trace_base', '.')))
                    if kind == 'controlled_legacy_fixture':
                        base = checked_ref(record.get('base_bundle'), Path(trace.get('trace_base', '.')))
                        patch = record.get('patch', {})
                        before, after = patch.get('before'), patch.get('after')
                        if (not isinstance(before,str) or not before or not isinstance(after,str) or before==after or '\n' in before or '\n' in after or
                                not record.get('mechanism') or base.read_bytes().count(before.encode())!=1 or
                                base.read_bytes().replace(before.encode(),after.encode(),1)!=bundle.read_bytes()):
                            errors.append('controlled fixture must be an exact documented one-line defect mutation')
                        for name in CASES:
                            if name == 'missing_empty_string':continue
                            route = {'reopen_map':'map', 'reopen_stage_details':'stage_details'}.get(name)
                            expected = 'not_applicable' if route and routes and routes[route]['present'] is False else 'pass'
                            if cases.get(name)!=expected:errors.append('fixture unrelated failure/missing case: '+name)
                except (ValueError,OSError,TypeError,KeyError) as exc:
                    errors.append('negative provenance: '+str(exc))
    if current.get('bundle_sha256') == old.get('bundle_sha256'):
        errors.append('negative and current bundle are identical')
    return errors


def replay(trace):
    """Run both recorded cases, rather than trusting a hand-authored raw JSON."""
    errors = []
    command = trace['execution']['command']
    for label in ('current', 'negative_control'):
        record = trace[label]
        actual = [part.replace('{bundle}', record['bundle']).replace('{adapter}', record['adapter']) for part in command]
        try:
            proc = subprocess.run(actual, capture_output=True, text=True, timeout=120, check=False)
            result = json.loads(proc.stdout)
            if proc.returncode != 0 or result != read(record['raw_report']):
                errors.append(label + ' actual runner output does not match raw report')
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            errors.append(label + ' runner failed: ' + type(exc).__name__)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', required=True, type=Path)
    parser.add_argument('--native', required=True, type=Path)
    parser.add_argument('--binding', required=True, type=Path, help='current known-issue review JSON')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    trace = read(args.trace)
    binding = read(args.binding).get('binding')
    errors = validate(trace, args.native, binding)
    if not errors:
        errors.extend(replay(trace))
    report = {'tool': 'audit_native_storage_contract', 'binding': binding,
              'checked': len(CASES) + 1, 'failed': len(errors), 'passed': not errors,
              'policy_version': 2 if trace.get('schema') == 'native_storage_trace.v2' else 1, 'required_cases': list(CASES),
              'negative_kind': trace.get('negative_control',{}).get('kind','historical_release'),
              'route_policy': 'verified_existing_routes' if trace.get('schema') == 'native_storage_trace.v2' else 'all_three_required',
              'trace': str(args.trace.resolve()), 'trace_sha256': digest(args.trace),
              'native': str(args.native.resolve()), 'errors': errors}
    try:
        observed = read(trace['current']['raw_report']).get('cases', {})
        report['checked_routes'] = [name for name in ('home','map','stage_details') if observed.get('reopen_'+name) == 'pass']
        report['excluded_routes'] = [name for name in ('map','stage_details') if observed.get('reopen_'+name) == 'not_applicable']
    except (KeyError,OSError,ValueError,AttributeError):
        report['checked_routes'], report['excluded_routes'] = [], []
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'failed': len(errors), 'out': str(args.out)}))
    raise SystemExit(0 if not errors else 1)


if __name__ == '__main__':
    main()
