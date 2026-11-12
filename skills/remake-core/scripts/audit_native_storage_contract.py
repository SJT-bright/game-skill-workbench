#!/usr/bin/env python3
"""Fail-closed storage-contract gate for the actual Native bundle and adapter.

The project runner produces raw case results. This tool binds those results to
the final Native bytes, checks the required matrix, and verifies that the same
runner reproduced the reported defect on an older bundle.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

BASE_CASES = (
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


POLICY_VERSION = 3
UPGRADE_CASES = ('legacy_numeric_nonbinary_typed', 'legacy_numeric_boundary_typed',
                 'legacy_unreadable_preserved', 'legacy_upgrade_touch_play')
CASES = BASE_CASES + UPGRADE_CASES


def json_only_scope(trace, binding):
    """Only schemas plus current, source-backed per-key read/write inventory opt out.

    This is an explicit project evidence boundary, not a broad static proof of
    JavaScript. A reason string alone or an unknown schema cannot opt out.
    """
    scope = trace.get('numeric_scope', {})
    if not isinstance(scope, dict) or scope.get('mode') != 'json_only':
        return False, []
    errors = []
    try:
        from maintenance_scope import checked_ref
        base = Path(trace.get('trace_base', '.')); project = Path(trace.get('project', '')).resolve()
        schema = read(checked_ref(scope.get('schema'), base))
        inventory = read(checked_ref(scope.get('access_inventory'), base))
        fields = schema.get('fields', {})
        if (schema.get('schema') != 'storage_value_schema.v1' or not isinstance(fields, dict) or not fields or
                any(not isinstance(key, str) or not key or not isinstance(row, dict) or
                    row.get('encoding') != 'json_object' or row.get('legacy_encodings') != ['json_object']
                    for key, row in fields.items())):
            raise ValueError('actual schema must declare every current and legacy field as JSON object')
        if (inventory.get('schema') != 'storage_access_inventory.v1' or inventory.get('binding') != binding or
                inventory.get('schema_sha256') != scope['schema']['sha256'] or
                inventory.get('complete') is not True or inventory.get('unknown_or_dynamic_keys') != []):
            raise ValueError('current complete schema-bound access inventory required')
        rows = inventory.get('keys', [])
        if (not isinstance(rows, list) or len(rows) != len(fields) or
                {row.get('key') for row in rows if isinstance(row, dict)} != set(fields)):
            raise ValueError('all schema keys need exact read/write inventory')
        for row in rows:
            for operation in ('read', 'write'):
                sites = row.get(operation, [])
                if not isinstance(sites, list) or not sites:
                    raise ValueError('each schema key needs actual read and write sites')
                for site in sites:
                    source = checked_ref(site.get('source'), base)
                    expression = site.get('expression')
                    if (not source.is_relative_to(project / 'assets') or source.suffix not in ('.js', '.ts') or
                            not isinstance(expression, str) or not expression.strip() or
                            source.read_text(encoding='utf-8').count(expression) != 1):
                        raise ValueError('read/write source identity or exact call expression invalid')
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        errors.append('json_only numeric_not_applicable refused: ' + str(exc))
    return not errors, errors


def upgrade_errors(result, *, negative=False, json_only=False):
    """Check raw semantics; pass labels alone cannot establish preservation.

    This validates/replays supplied runner observations. It does not turn a
    synthetic host into a physical phone or prove a dishonest runner truthful.
    Keys are project/schema supplied, never a global Coin-name assumption.
    """
    errors = []
    observations = result.get('upgrade_observations', {})
    if not isinstance(observations, dict):
        return ['upgrade raw observations missing']
    if json_only:
        if negative:
            row = observations.get('json_unreadable_preserved', {})
            if not isinstance(row, dict): return ['upgrade JSON negative raw observation missing']
            key = row.get('key'); before = row.get('storage_before', {}); after = row.get('storage_after', {})
            sync = row.get('sync_read', {})
            if not isinstance(before, dict) or not isinstance(after, dict): return ['upgrade JSON negative raw storage objects required']
            try: valid_json = isinstance(json.loads(before.get(key, '')), dict)
            except (ValueError, TypeError): valid_json = False
            if (not isinstance(key, str) or key not in before or not isinstance(before.get(key), str) or
                    not valid_json or
                    row.get('fixture_installed_before_entry') is not True or
                    not isinstance(sync, dict) or sync.get('type') != 'boolean' or type(sync.get('value')) is not bool or
                    result.get('cases', {}).get('json_unreadable_preserved') != 'fail' or
                    row.get('failure_kind') != 'existing_json_silently_reset' or
                    json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True)):
                errors.append('upgrade JSON negative must reproduce an existing unreadable JSON save being reset')
        else:
            legacy = observations.get('valid_legacy_record', {})
            if not isinstance(legacy, dict): return ['JSON-only legacy raw observation missing']
            key = legacy.get('key'); before = legacy.get('storage_before', {}); after = legacy.get('storage_after', {})
            if not isinstance(before, dict) or not isinstance(after, dict): return ['JSON-only legacy raw storage objects required']
            try: valid_json = isinstance(json.loads(before.get(key, '')), dict)
            except (ValueError, TypeError): valid_json = False
            if (not isinstance(key, str) or not valid_json or
                    legacy.get('fixture_installed_before_entry') is not True or
                    json.dumps(before, sort_keys=True) != json.dumps(after, sort_keys=True)):
                errors.append('JSON-only legacy fixture must precede entry and preserve actual JSON data')
            business = observations.get('legacy_upgrade_touch_play', {})
            if not isinstance(business, dict) or business.get('fixture_case') != 'valid_legacy_record':
                errors.append('JSON-only upgrade play must use valid legacy JSON fixture')
            else:
                from startup_business_contract import validate_business
                errors.extend('upgrade ' + e for e in validate_business(business))
        return errors
    names = UPGRADE_CASES[:1] if negative else UPGRADE_CASES[:3]
    for name in names:
        row = observations.get(name, {})
        if not isinstance(row, dict):
            errors.append(name + ': raw observation missing'); continue
        key = row.get('key'); before = row.get('storage_before', {}); after = row.get('storage_after', {})
        value = row.get('expected_numeric', 0 if name == 'legacy_numeric_boundary_typed' else 45)
        expected_text = row.get('expected_text', str(value))
        numeric = lambda n: type(n) in (int, float) and math.isfinite(n)
        def numeric_text(text):
            if not isinstance(text, str) or not text or text.strip() != text: return False
            try: number = float(text)
            except (ValueError, OverflowError): return False
            return math.isfinite(number) and number == value
        valid_value = numeric(value) and numeric_text(expected_text)
        if name == 'legacy_numeric_nonbinary_typed': valid_value = valid_value and value not in (0, 1)
        elif name == 'legacy_numeric_boundary_typed': valid_value = valid_value and value in (0, 1)
        valid_before = (isinstance(key, str) and bool(key) and isinstance(before, dict) and
                        isinstance(after, dict) and key in before and
                        valid_value and numeric(before[key]) and before[key] == value)
        if not valid_before:
            errors.append(name + ': preboot project-valid numeric fixture and exact expected_text required'); continue
        if row.get('fixture_installed_before_entry') is not True:
            errors.append(name + ': fixture must precede Native entry')
        sync = row.get('sync_read', {})
        if not isinstance(sync, dict) or sync.get('type') != 'boolean' or type(sync.get('value')) is not bool:
            errors.append(name + ': actual sync Boolean bridge observation required')
        writes = row.get('writes')
        if not isinstance(writes, list):
            errors.append(name + ': raw writes required'); writes = []
        if negative:
            actual_failure = (key not in after or after.get(key) not in (value, expected_text) or
                              bool(row.get('first_exception')) and row.get('loading_overlay_visible') is True)
            if (result.get('cases', {}).get(name) != 'fail' or
                    row.get('failure_kind') != 'legacy_numeric_bridge' or not actual_failure):
                errors.append('upgrade negative did not reproduce legacy numeric bridge failure')
            continue
        if row.get('removed_keys') != []:
            errors.append(name + ': key removal/default reset forbidden')
        # Unrelated raw data must remain exact, not just the selected scalar.
        if json.dumps({k:v for k,v in before.items() if k != key}, sort_keys=True) != json.dumps({k:v for k,v in after.items() if k != key}, sort_keys=True):
            errors.append(name + ': unrelated saved data changed')
        async_read = row.get('async_read', {})
        if name == 'legacy_unreadable_preserved':
            if (json.dumps(after, sort_keys=True) != json.dumps(before, sort_keys=True) or writes or not isinstance(async_read, dict) or
                    async_read.get('status') not in ('unreadable', 'error', 'timeout', 'unavailable') or
                    row.get('recovery_feedback_visible') is not True or
                    row.get('loading_overlay_visible') is not False or
                    row.get('retry_or_exit_available') is not True):
                errors.append(name + ': unreadable data must be preserved with visible recovery/exit')
            continue
        typed_original = (isinstance(async_read, dict) and
                          (async_read.get('type') == 'number' and numeric(async_read.get('value')) and async_read['value'] == value or
                           async_read.get('type') == 'string' and numeric_text(async_read.get('value'))))
        if not typed_original:
            errors.append(name + ': typed async original value required (Boolean is not numeric)')
        if after.get(key) != expected_text or type(after.get(key)) is not str:
            errors.append(name + ': recovered original value must be text without default reset')
        if not writes or any(not isinstance(w, dict) or w.get('key') != key or
                             type(w.get('value')) is not str or w.get('value') != expected_text for w in writes):
            errors.append(name + ': recovery writes must preserve the exact typed value')
        if row.get('first_exception'):
            errors.append(name + ': recovery left an exception')
    if not negative:
        from startup_business_contract import validate_business
        business = observations.get('legacy_upgrade_touch_play', {})
        if not isinstance(business, dict) or business.get('fixture_case') != 'legacy_numeric_nonbinary_typed':
            errors.append('upgrade play must use the recovered nonbinary project-valid legacy fixture')
        else:
            errors.extend('upgrade ' + e for e in validate_business(business))
    return errors


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def inside(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    return path.is_file() and path.is_relative_to(root)


def validate(trace, native, expected_binding):
    errors = []
    if trace.get('schema') not in ('native_storage_trace.v1', 'native_storage_trace.v2', 'native_storage_trace.v3'):
        errors.append('trace schema')
    if trace.get('binding') != expected_binding:
        errors.append('current build binding')
    if trace.get('schema') != 'native_storage_trace.v3':
        errors.append('needs_upgrade: v1/v2 do not prove cold-upgrade bridge coverage')
    execution = trace.get('execution', {})
    runner = Path(execution.get('runner', ''))
    command = execution.get('command', [])
    if (not runner.is_file() or digest(runner) != execution.get('runner_sha256') or
            not isinstance(command, list) or not all(isinstance(part, str) for part in command) or str(runner) not in command or
            '{bundle}' not in command or '{adapter}' not in command):
        errors.append('real runner identity and command')
    routes = None
    if trace.get('schema') in ('native_storage_trace.v2', 'native_storage_trace.v3'):
        try:
            from maintenance_scope import source_inventory
            from check_known_issues import tree_sha
            if tree_sha(native) != expected_binding.get('native_tree_sha256'):
                raise ValueError('final Native tree differs from binding')
            routes = source_inventory(trace.get('route_inventory'), Path(trace.get('trace_base', '.')), trace.get('project', ''), expected_binding)['routes']
        except (ValueError, OSError, TypeError, KeyError) as exc:
            errors.append('verified existing routes: '+str(exc))
    json_only, scope_errors = json_only_scope(trace, expected_binding)
    errors.extend(scope_errors)
    current = trace.get('current', {})
    old = trace.get('negative_control', {})
    records = [('current', current), ('negative', old)]
    if trace.get('schema') == 'native_storage_trace.v3':
        records.append(('upgrade_negative', trace.get('upgrade_negative_control', {})))
    for label, record in records:
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
            for name in (CASES if trace.get('schema') == 'native_storage_trace.v3' else BASE_CASES):
                route = {'reopen_map':'map', 'reopen_stage_details':'stage_details'}.get(name)
                expected = 'not_applicable' if (route and routes and routes[route]['present'] is False or json_only and name in UPGRADE_CASES[:3]) else 'pass'
                if cases.get(name) != expected:
                    errors.append('current case missing or failed: ' + name + ' (requires '+expected+')')
            if trace.get('schema') == 'native_storage_trace.v3':
                errors.extend(upgrade_errors(result, json_only=json_only))
        elif label == 'upgrade_negative':
            errors.extend(upgrade_errors(result, negative=True, json_only=json_only))
            if not json_only:
                current_row = read(current['raw_report']).get('upgrade_observations', {}).get('legacy_numeric_nonbinary_typed', {})
                negative_row = result.get('upgrade_observations', {}).get('legacy_numeric_nonbinary_typed', {})
                if (current_row.get('key') != negative_row.get('key') or
                        current_row.get('expected_numeric', 45) != negative_row.get('expected_numeric', 45)):
                    errors.append('upgrade negative must use the same project key and nonbinary fixture value')
            try:
                from maintenance_scope import checked_ref
                if record.get('kind') not in ('historical_release', 'controlled_legacy_fixture'):
                    raise ValueError('upgrade negative provenance kind required')
                checked_ref(record.get('provenance'), Path(trace.get('trace_base', '.')))
                if record.get('kind') == 'controlled_legacy_fixture':
                    base = checked_ref(record.get('base_bundle'), Path(trace.get('trace_base', '.')))
                    patch = record.get('patch', {}); before, after = patch.get('before'), patch.get('after')
                    if (not isinstance(before, str) or not before or not isinstance(after, str) or before == after or
                            '\n' in before or '\n' in after or not record.get('mechanism') or
                            base.read_bytes().count(before.encode()) != 1 or
                            base.read_bytes().replace(before.encode(), after.encode(), 1) != bundle.read_bytes()):
                        raise ValueError('upgrade fixture must be an exact documented one-line defect mutation')
            except (ValueError, OSError, TypeError, KeyError) as exc:
                errors.append('upgrade negative provenance: ' + str(exc))
        else:
            if cases.get('missing_empty_string') != 'fail':
                errors.append('negative did not reproduce missing-empty-string defect')
            if trace.get('schema') in ('native_storage_trace.v2', 'native_storage_trace.v3'):
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
                        for name in BASE_CASES:
                            if name == 'missing_empty_string':continue
                            route = {'reopen_map':'map', 'reopen_stage_details':'stage_details'}.get(name)
                            expected = 'not_applicable' if route and routes and routes[route]['present'] is False else 'pass'
                            if cases.get(name)!=expected:errors.append('fixture unrelated failure/missing case: '+name)
                except (ValueError,OSError,TypeError,KeyError) as exc:
                    errors.append('negative provenance: '+str(exc))
    upgrade = trace.get('upgrade_negative_control', {})
    if trace.get('schema') == 'native_storage_trace.v3' and current.get('bundle_sha256') == upgrade.get('bundle_sha256'):
        errors.append('upgrade negative and current bundle are identical')
    if current.get('bundle_sha256') == old.get('bundle_sha256'):
        errors.append('negative and current bundle are identical')
    return errors


def replay(trace):
    """Run both recorded cases, rather than trusting a hand-authored raw JSON."""
    errors = []
    command = trace['execution']['command']
    for label in ('current', 'negative_control') + (('upgrade_negative_control',) if trace.get('schema') == 'native_storage_trace.v3' else ()):
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
              'checked': len(CASES) + 2, 'failed': len(errors), 'passed': not errors,
              'policy_version': POLICY_VERSION, 'status': ('needs_upgrade' if trace.get('schema') != 'native_storage_trace.v3' else 'passed' if not errors else 'failed'), 'required_cases': list(CASES),
              'negative_kind': trace.get('negative_control',{}).get('kind','historical_release'),
              'route_policy': 'verified_existing_routes' if trace.get('schema') in ('native_storage_trace.v2','native_storage_trace.v3') else 'all_three_required',
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
