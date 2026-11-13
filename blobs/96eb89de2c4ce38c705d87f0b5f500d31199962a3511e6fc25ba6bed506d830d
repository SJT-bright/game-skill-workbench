#!/usr/bin/env python3
"""Fail-closed storage-contract gate for the actual Native bundle and adapter.

The project runner produces raw case results. This tool binds those results to
the final Native bytes, checks the required matrix, and verifies that the same
runner reproduced the reported defect on an older bundle.

2026-11-12, saved data never stops the game: a legacy value that cannot be read
is proved by a start with the fallback value (home -> trusted touch -> play),
see fallback_start_errors(). The earlier proof (value left untouched behind a
visible recovery / exit page) stays valid only for receipts issued before this
text; approve_runtime() no longer accepts it. Case names and POLICY_VERSION are
unchanged, so reports of both kinds are read by the same consumers.
"""
import argparse
import hashlib
import json
import math
import datetime
import uuid
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
STORAGE_POLICY = 'unreadable_starts_with_fallback.2026-11-12'
FALLBACK_OUTCOME = 'started_with_fallback'
STOPPED_START = 'unreadable_stops_startup'
ASYNC_FAILED = ('unreadable', 'error', 'timeout', 'unavailable')


def raw_history(trace):
    """Whether a released build of this game may have written raw numbers / Booleans.

    Only an explicit statement with its basis turns the typed-recovery cases off
    (first release, or every released build wrote text through the kit guard).
    Missing or anything else keeps them required, as before 2026-11-12.
    """
    row = trace.get('legacy_data') if isinstance(trace, dict) else None
    return not (isinstance(row, dict) and row.get('earlier_release_wrote_raw_values') is False and
                isinstance(row.get('basis'), str) and bool(row['basis'].strip()))


def unrelated_changed(before, after, key):
    return (json.dumps({k: v for k, v in before.items() if k != key}, sort_keys=True) !=
            json.dumps({k: after.get(k) for k in before if k != key and k in after}, sort_keys=True) or
            any(k not in after for k in before if k != key))


def fallback_start_errors(row, label, key):
    """One unreadable legacy value: the game starts and plays with its fallback value.

    The value itself may be overwritten or backed up by the game; what is proved
    is that nothing else is lost and that the player reaches gameplay.
    """
    from startup_business_contract import validate_business
    errors = []
    before = row.get('storage_before'); after = row.get('storage_after')
    sync = row.get('sync_read'); async_read = row.get('async_read')
    if (row.get('fixture_installed_before_entry') is not True or not isinstance(before, dict) or
            not isinstance(after, dict) or not isinstance(key, str) or key not in before):
        return [label + ': unreadable fixture of the named key must precede Native entry']
    if not isinstance(sync, dict) or sync.get('type') != 'boolean' or type(sync.get('value')) is not bool:
        errors.append(label + ': actual sync Boolean bridge observation required')
    if not isinstance(async_read, dict) or async_read.get('status') not in ASYNC_FAILED:
        errors.append(label + ': the async read must actually fail in the unreadable branch')
    if row.get('first_exception') or row.get('loading_overlay_visible') is not False:
        errors.append(label + ': an unreadable value left an exception or the loading overlay')
    if row.get('removed_keys') != [] or unrelated_changed(before, after, key):
        errors.append(label + ': other saved data was removed or changed')
    errors.extend(label + ': start with fallback ' + e for e in validate_business(row))
    return errors


def stopped_start_errors(result, row, label):
    """Negative control of the fallback proof: the same fixture stops this older / mutated bundle."""
    from startup_business_contract import validate_business
    if not isinstance(row, dict):
        return [label + ': raw observation missing']
    sync = row.get('sync_read')
    stopped = bool(row.get('first_exception')) or row.get('loading_overlay_visible') is True or bool(validate_business(row))
    if (result.get('cases', {}).get('legacy_unreadable_preserved') != 'fail' or row.get('failure_kind') != STOPPED_START or
            row.get('fixture_installed_before_entry') is not True or not isinstance(row.get('storage_before'), dict) or
            row.get('key') not in row['storage_before'] or
            not isinstance(sync, dict) or sync.get('type') != 'boolean' or type(sync.get('value')) is not bool or not stopped):
        return [label + ': negative must show the same unreadable fixture stopping the start (exception, loading overlay or no gameplay)']
    return []


def json_only_scope(trace, binding, native=None):
    """Proven non-numeric storage encodings may exclude only numeric cases.

    Explicit schema/access inventory is an operator evidence boundary, not a
    general static proof of JavaScript. Unknown or primitive-number legacy keys
    cannot opt out. The old json_only mode remains readable.
    """
    scope = trace.get('numeric_scope', {})
    if not isinstance(scope, dict) or scope.get('mode') not in ('json_only', 'schema_backed_non_numeric'):
        return False, []
    errors = []
    try:
        from maintenance_scope import checked_ref
        base = Path(trace.get('trace_base', '.')); project = Path(trace.get('project', '')).resolve()
        schema = read(checked_ref(scope.get('schema'), base))
        inventory = read(checked_ref(scope.get('access_inventory'), base))
        fields = schema.get('fields', {})
        allowed = {'json_object'} if scope['mode'] == 'json_only' else {'json_object', 'boolean', 'string'}
        if (schema.get('schema') != 'storage_value_schema.v1' or not isinstance(fields, dict) or not fields or
                any(not isinstance(key, str) or not key or not isinstance(row, dict) or
                    row.get('encoding') not in allowed or not isinstance(row.get('legacy_encodings'), list) or
                    not row['legacy_encodings'] or set(row['legacy_encodings']) - allowed
                    for key, row in fields.items())):
            raise ValueError('actual schema must declare every current and legacy field with supported non-numeric encoding')
        if (inventory.get('schema') != 'storage_access_inventory.v1' or inventory.get('binding') != binding or
                inventory.get('schema_sha256') != scope['schema']['sha256'] or
                inventory.get('complete') is not True or inventory.get('unknown_or_dynamic_keys') != []):
            raise ValueError('current complete schema-bound access inventory required')
        rows = inventory.get('keys', [])
        if (not isinstance(rows, list) or len(rows) != len(fields) or
                {row.get('key') for row in rows if isinstance(row, dict)} != set(fields)):
            raise ValueError('all schema keys need exact read/write inventory')
        roots = [project / n for n in ('assets', 'packages', 'build-templates')]
        if native is not None: roots.append(Path(native).resolve())
        for row in rows:
            for operation in ('read', 'write'):
                sites = row.get(operation, [])
                if not isinstance(sites, list) or not sites:
                    raise ValueError('each schema key needs actual read and write sites')
                for site in sites:
                    source = checked_ref(site.get('source'), base)
                    expression = site.get('expression')
                    if (not any(source.is_relative_to(root) for root in roots) or source.suffix not in ('.js', '.ts') or
                            not isinstance(expression, str) or not expression.strip() or
                            source.read_text(encoding='utf-8').count(expression) != 1):
                        raise ValueError('read/write source identity or exact call expression invalid')
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        errors.append('schema-backed numeric_not_applicable refused: ' + str(exc))
    return not errors, errors


def valid_encoded(value, encodings):
    for encoding in encodings:
        if encoding == 'string' and isinstance(value, str): return True
        if encoding == 'boolean' and (type(value) is bool or type(value) is str and value in ('true', 'false')): return True
        if encoding == 'json_object':
            try:
                if isinstance(value, dict) or isinstance(value, str) and isinstance(json.loads(value), dict): return True
            except (ValueError, TypeError): pass
    return False


def decoded_encoded(value, encoding):
    if encoding == 'boolean' and valid_encoded(value, ['boolean']):
        return value if type(value) is bool else value == 'true'
    if encoding == 'json_object' and valid_encoded(value, ['json_object']):
        return value if isinstance(value, dict) else json.loads(value)
    if encoding == 'string' and isinstance(value, str): return value
    raise ValueError('saved value does not match current encoding')


def _json_preserves_existing(before, after):
    """Allow object default-field additions; every existing leaf/array stays exact."""
    if isinstance(before, dict):
        return (isinstance(after, dict) and set(before).issubset(after) and
                all(_json_preserves_existing(value, after[key]) for key, value in before.items()))
    return canonical_sha(before) == canonical_sha(after)


JSON_RETRY_POLICY = 'preserve_json_unreadable_retry.v1'
JSON_RETRY_OUTCOME = 'preserved_with_retry_then_resumed'


def json_retry_upgrade_errors(result, fields, negative=False):
    """An unreadable JSON envelope remains untouched, then a real Retry resumes original data."""
    from startup_business_contract import validate_business
    from maintenance_scope import checked_ref
    errors = []
    observations = result.get('upgrade_observations', {})
    row = observations.get('legacy_unreadable_preserved', {}) if isinstance(observations, dict) else {}
    if not isinstance(row, dict): return ['JSON retry: raw observation required']
    key = row.get('key'); before = row.get('storage_before'); sync = row.get('sync_read', {})
    if (not isinstance(key, str) or fields.get(key, {}).get('encoding') != 'json_object' or
            not isinstance(before, dict) or key not in before or
            not valid_encoded(before.get(key), ['json_object']) or row.get('fixture_installed_before_entry') is not True):
        return ['JSON retry: schema-valid original fixture before entry required']
    fault_read = (isinstance(sync, dict) and
                  (sync.get('type') == 'boolean' and type(sync.get('value')) is bool or
                   sync.get('type') == 'exception' and isinstance(sync.get('error'), str) and bool(sync['error'])))
    if not fault_read: errors.append('JSON retry: actual Boolean or thrown SDK read required')
    if negative:
        after = row.get('storage_after_fault', row.get('storage_after'))
        writes = row.get('writes_fault', [])
        changed = isinstance(after, dict) and after.get(key) != before[key]
        if (row.get('failure_kind') != 'unreadable_original_overwritten' or
                result.get('cases', {}).get('legacy_unreadable_preserved') != 'fail' or not changed or
                not isinstance(writes, list) or not any(isinstance(w, dict) and w.get('key') == key and
                                                       w.get('value') != before[key] for w in writes)):
            errors.append('JSON retry negative: same unreadable original must actually be overwritten by controlled defect')
        return errors
    if row.get('outcome') != JSON_RETRY_OUTCOME:
        errors.append('JSON retry: preserve-visible-Retry-resume outcome required')
    if (row.get('storage_after_fault') != before or row.get('writes_fault') != [] or
            row.get('removed_keys_fault') != [] or row.get('runtime_initialized_fault') is not False or
            row.get('unsafe_grant_or_spend') is not False or row.get('first_exception')):
        errors.append('JSON retry: fault must preserve every key with no writes, no runtime, no unsafe transaction or unhandled exception')
    recovery = row.get('recovery', {}); action = row.get('recovery_action', {})
    if (not isinstance(recovery, dict) or recovery.get('visible') is not True or
            recovery.get('retry_visible') is not True or recovery.get('retry_interactable') is not True or
            not isinstance(recovery.get('node_path'), str) or not recovery['node_path']):
        errors.append('JSON retry: actual visible interactable LoadingRecovery Retry required')
    if (not isinstance(action, dict) or action.get('transport') != 'ego_page_cdp' or
            not isinstance(action.get('event'), dict) or action['event'].get('isTrusted') is not True):
        errors.append('JSON retry: real trusted Retry input required')
    business = row.get('business', {})
    home = business.get('home', {}) if isinstance(business, dict) else {}
    moments = [row.get('fault_observed_at_ms'), recovery.get('at_ms') if isinstance(recovery, dict) else None,
               row.get('sdk_restored_at_ms'), action.get('at_ms') if isinstance(action, dict) else None,
               home.get('at_ms') if isinstance(home, dict) else None]
    if (any(type(t) not in (int, float) or not math.isfinite(t) or t < 0 for t in moments) or
            not moments[0] <= moments[1] < moments[2] <= moments[3] < moments[4]):
        errors.append('JSON retry: fault -> visible Retry -> SDK recovery -> trusted Retry -> HOME timing required')
    after = row.get('storage_after_retry'); loaded = row.get('restored_data')
    try:
        original = decoded_encoded(before[key], 'json_object')
        restored = decoded_encoded(after[key], 'json_object') if isinstance(after, dict) and key in after else None
        if (not isinstance(after, dict) or not _json_preserves_existing(original, restored) or
                not isinstance(loaded, dict) or not _json_preserves_existing(original, loaded) or
                any(k not in after or canonical_sha(after[k]) != canonical_sha(v) for k, v in before.items() if k != key)):
            errors.append('JSON retry: original data and every unrelated key must survive actual Retry and reach production consumer')
    except (ValueError, TypeError, KeyError):
        errors.append('JSON retry: actual restored JSON snapshots invalid')
    evidence = row.get('raw_evidence')
    if not isinstance(evidence, list) or not evidence:
        errors.append('JSON retry: original captured evidence refs required')
    else:
        for ref in evidence:
            try: checked_ref(ref, Path(result.get('trace_base', '.')))
            except (ValueError, OSError, TypeError, KeyError): errors.append('JSON retry: captured evidence missing or changed')
    errors.extend('JSON retry restored ' + e for e in validate_business(row))
    play = observations.get('legacy_upgrade_touch_play', {})
    if (not isinstance(play, dict) or play.get('fixture_case') != 'legacy_unreadable_preserved' or
            play.get('business') != row.get('business')):
        errors.append('JSON retry: upgrade touch-play must be the same recovered fixture run')
    return errors


def non_numeric_upgrade_errors(result, fields, negative=False, new_approval=False):
    errors = []
    observations = result.get('upgrade_observations', {})
    if not isinstance(observations, dict): return ['non-numeric upgrade raw observations missing']
    if negative and isinstance(observations.get('legacy_unreadable_preserved'), dict) and \
            observations['legacy_unreadable_preserved'].get('failure_kind') == STOPPED_START:
        return stopped_start_errors(result, observations['legacy_unreadable_preserved'], 'upgrade non-numeric negative')
    if negative and new_approval:
        return ['upgrade non-numeric negative: a reset of an unreadable save is no longer the defect; reproduce ' + STOPPED_START]
    if negative:
        name = ('non_numeric_unreadable_preserved' if 'non_numeric_unreadable_preserved' in observations
                else 'json_unreadable_preserved')
        row = observations.get(name, {})
    else:
        name = 'valid_legacy_record'; row = observations.get(name, {})
    if not isinstance(row, dict): return ['non-numeric legacy raw observation missing']
    key = row.get('key'); before = row.get('storage_before', {}); after = row.get('storage_after', {})
    if not isinstance(before, dict) or not isinstance(after, dict): return ['non-numeric raw storage objects required']
    encodings = fields.get(key, {}).get('legacy_encodings', []) if isinstance(key, str) else []
    if (not encodings or key not in before or not valid_encoded(before.get(key), encodings) or
            row.get('fixture_installed_before_entry') is not True):
        errors.append('non-numeric legacy fixture must match actual schema and precede Native entry')
    if negative:
        sync = row.get('sync_read', {})
        if (not isinstance(sync, dict) or sync.get('type') != 'boolean' or type(sync.get('value')) is not bool or
                result.get('cases', {}).get(name) != 'fail' or
                row.get('failure_kind') not in ('existing_json_silently_reset', 'existing_non_numeric_silently_reset') or
                json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True)):
            errors.append('upgrade non-numeric negative must reproduce an existing unreadable save being reset')
        return errors
    try:
        before_value = decoded_encoded(before.get(key), fields.get(key, {}).get('encoding'))
        after_value = decoded_encoded(after.get(key), fields.get(key, {}).get('encoding'))
        preserved = (_json_preserves_existing(before_value, after_value)
                     if fields.get(key, {}).get('encoding') == 'json_object'
                     else canonical_sha(before_value) == canonical_sha(after_value))
        if (not preserved or
                canonical_sha({k:v for k,v in before.items() if k != key}) != canonical_sha({k:v for k,v in after.items() if k != key})):
            errors.append('non-numeric legacy fixture data changed')
    except (ValueError, TypeError, KeyError):
        errors.append('non-numeric legacy fixture data changed or failed current schema')
    blocked = observations.get('legacy_unreadable_preserved', {})
    if not isinstance(blocked, dict): blocked = {}
    sync = blocked.get('sync_read', {}); async_read = blocked.get('async_read', {})
    if blocked.get('outcome') == FALLBACK_OUTCOME:
        if blocked.get('key') != key or blocked.get('storage_before') != before:
            errors.append('non-numeric unreadable start must use the same key and legacy fixture')
        errors.extend(fallback_start_errors(blocked, 'non-numeric unreadable data', key))
    elif new_approval:
        errors.append('non-numeric unreadable data: a blocking recovery page is no longer accepted; prove outcome ' + FALLBACK_OUTCOME)
    elif (blocked.get('key') != key or blocked.get('storage_before') != before or
            blocked.get('storage_after') != before or blocked.get('fixture_installed_before_entry') is not True or
            not isinstance(sync, dict) or sync.get('type') != 'boolean' or type(sync.get('value')) is not bool or
            blocked.get('removed_keys') != [] or blocked.get('writes') != [] or
            not isinstance(async_read, dict) or async_read.get('status') not in ('unreadable', 'error', 'timeout', 'unavailable') or
            blocked.get('recovery_feedback_visible') is not True or blocked.get('loading_overlay_visible') is not False or
            blocked.get('retry_or_exit_available') is not True):
        errors.append('non-numeric unreadable data must be preserved with visible recovery/exit')
    business = observations.get('legacy_upgrade_touch_play', {})
    if not isinstance(business, dict) or business.get('fixture_case') != 'valid_legacy_record':
        errors.append('non-numeric upgrade play must use valid legacy fixture')
    else:
        from startup_business_contract import validate_business
        errors.extend('upgrade ' + e for e in validate_business(business))
    return errors


def upgrade_errors(result, *, negative=False, json_only=False, fields=None, typed=True, new_approval=False, policy=None):
    """Check raw semantics; pass labels alone cannot establish preservation.

    typed=False (raw_history() is False): the two typed-recovery rows are not applicable; only the
    unreadable start and the play with that fixture are checked.

    This validates/replays supplied runner observations. It does not turn a
    synthetic host into a physical phone or prove a dishonest runner truthful.
    Keys are project/schema supplied, never a global Coin-name assumption.
    """
    errors = []
    observations = result.get('upgrade_observations', {})
    if not isinstance(observations, dict):
        return ['upgrade raw observations missing']
    if policy == JSON_RETRY_POLICY:
        if not json_only: return ['JSON retry policy requires current schema-backed JSON-only domain']
        return json_retry_upgrade_errors(result, fields or {}, negative)
    if json_only:
        return non_numeric_upgrade_errors(result, fields or {}, negative, new_approval)
    stopped = observations.get('legacy_unreadable_preserved')
    if negative and isinstance(stopped, dict) and stopped.get('failure_kind') == STOPPED_START:
        return stopped_start_errors(result, stopped, 'upgrade negative')
    if negative and not typed:
        return ['upgrade negative: without typed recovery the negative must reproduce ' + STOPPED_START]
    names = UPGRADE_CASES[:1] if negative else (UPGRADE_CASES[:3] if typed else UPGRADE_CASES[2:3])
    for name in names:
        row = observations.get(name, {})
        if not isinstance(row, dict):
            errors.append(name + ': raw observation missing'); continue
        if not typed and row.get('outcome') == FALLBACK_OUTCOME:
            # No typed recovery in this game: the stored value may be of any type, only its Boolean sync read matters.
            errors.extend(fallback_start_errors(row, name, row.get('key'))); continue
        key = row.get('key'); before = row.get('storage_before', {}); after = row.get('storage_after', {})
        value = row.get('expected_numeric', 0 if name == 'legacy_numeric_boundary_typed' else 45)
        def numeric(n):
            try: return type(n) in (int, float) and math.isfinite(n)
            except (OverflowError, ValueError): return False
        expected_text = row.get('expected_text') if 'expected_text' in row else (str(value) if numeric(value) else '')
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
        fallback = name == 'legacy_unreadable_preserved' and row.get('outcome') == FALLBACK_OUTCOME
        if row.get('removed_keys') != [] and not fallback:
            errors.append(name + ': key removal/default reset forbidden')
        # Unrelated raw data must remain exact, not just the selected scalar. (A fallback start may add keys,
        # e.g. a backup of the unreadable value; fallback_start_errors() checks that nothing else changed.)
        if not fallback and json.dumps({k:v for k,v in before.items() if k != key}, sort_keys=True) != json.dumps({k:v for k,v in after.items() if k != key}, sort_keys=True):
            errors.append(name + ': unrelated saved data changed')
        async_read = row.get('async_read', {})
        if name == 'legacy_unreadable_preserved' and row.get('outcome') == FALLBACK_OUTCOME:
            errors.extend(fallback_start_errors(row, name, key))
            continue
        if name == 'legacy_unreadable_preserved' and new_approval:
            errors.append(name + ': a blocking recovery page is no longer accepted; prove outcome ' + FALLBACK_OUTCOME)
            continue
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
        if not typed and (not isinstance(business, dict) or business.get('fixture_case') != 'legacy_unreadable_preserved'):
            errors.append('upgrade play must use the unreadable legacy fixture when typed recovery is not applicable')
        elif typed and (not isinstance(business, dict) or business.get('fixture_case') != 'legacy_numeric_nonbinary_typed'):
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


def validate(trace, native, expected_binding, new_approval=False, *, _scope=None):
    """new_approval=True (approve_runtime only): evidence of the earlier blocking-recovery policy is refused."""
    if isinstance(trace, dict) and trace.get('numeric_snapshot_encoding'):
        from numeric_snapshot_contract import validate as validate_numeric_snapshot
        return validate_numeric_snapshot(trace, native, expected_binding, **({'_scope': _scope} if _scope else {}))
    errors = []
    if not isinstance(trace, dict): return ['storage trace must be an object']
    if not isinstance(expected_binding, dict): return ['current binding must be an object']
    if trace.get('schema') not in ('native_storage_trace.v1', 'native_storage_trace.v2', 'native_storage_trace.v3'):
        errors.append('trace schema')
    if trace.get('binding') != expected_binding:
        errors.append('current build binding')
    if trace.get('schema') != 'native_storage_trace.v3':
        errors.append('needs_upgrade: v1/v2 do not prove cold-upgrade bridge coverage')
    execution = trace.get('execution', {})
    if not isinstance(execution, dict):
        errors.append('execution record must be an object'); execution = {}
    try: runner = Path(execution.get('runner', ''))
    except TypeError: runner = Path('')
    command = execution.get('command', [])
    if (not runner.is_file() or digest(runner) != execution.get('runner_sha256') or
            not isinstance(command, list) or not all(isinstance(part, str) for part in command) or str(runner) not in command or
            '{bundle}' not in command or '{adapter}' not in command):
        errors.append('real runner identity and command')
    if trace.get('schema') == 'native_storage_trace.v3':
        try:
            execution_identity(trace)
        except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
            errors.append('runner dependency identity: ' + str(exc))
    routes = None
    if trace.get('schema') in ('native_storage_trace.v2', 'native_storage_trace.v3'):
        try:
            from maintenance_scope import source_inventory
            from check_known_issues import tree_sha
            if (_scope.native_identity(native, expected_binding) if _scope else tree_sha(native)) != expected_binding.get('native_tree_sha256'):
                raise ValueError('final Native tree differs from binding')
            routes = source_inventory(trace.get('route_inventory'), Path(trace.get('trace_base', '.')), trace.get('project', ''), expected_binding, **({'source_snapshot': _scope.source_snapshot} if _scope else {}))['routes']
        except (ValueError, OSError, TypeError, KeyError) as exc:
            errors.append('verified existing routes: '+str(exc))
    json_only, scope_errors = json_only_scope(trace, expected_binding, native)
    errors.extend(scope_errors)
    typed = raw_history(trace)
    fields = {}
    if json_only:
        from maintenance_scope import checked_ref
        fields = read(checked_ref(trace['numeric_scope']['schema'], Path(trace.get('trace_base', '.'))))['fields']
    current = trace.get('current', {})
    old = trace.get('negative_control', {})
    if not isinstance(current, dict): errors.append('current record invalid'); current = {}
    if not isinstance(old, dict): errors.append('negative record invalid'); old = {}
    records = [('current', current), ('negative', old)]
    if trace.get('schema') == 'native_storage_trace.v3':
        records.append(('upgrade_negative', trace.get('upgrade_negative_control', {})))
    loaded_results = {}
    for label, record in records:
        if not isinstance(record, dict):
            errors.append(label + ' record invalid'); continue
        try:
            bundle = Path(record.get('bundle', '')); adapter = Path(record.get('adapter', '')); raw = Path(record.get('raw_report', ''))
        except TypeError:
            errors.append(label + ' paths invalid'); continue
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
        loaded_results[label] = result
        cases = result.get('cases', {})
        if not isinstance(cases, dict):
            errors.append(label + ' cases invalid')
            continue
        if label == 'current':
            for name in (CASES if trace.get('schema') == 'native_storage_trace.v3' else BASE_CASES):
                route = {'reopen_map':'map', 'reopen_stage_details':'stage_details'}.get(name)
                expected = 'not_applicable' if (route and routes and routes[route]['present'] is False or (json_only or not typed) and name in UPGRADE_CASES[:2]) else 'pass'
                if cases.get(name) != expected:
                    errors.append('current case missing or failed: ' + name + ' (requires '+expected+')')
            if trace.get('schema') == 'native_storage_trace.v3':
                errors.extend(upgrade_errors(result, json_only=json_only, fields=fields, typed=typed, new_approval=new_approval, policy=trace.get('storage_policy')))
        elif label == 'upgrade_negative':
            errors.extend(upgrade_errors(result, negative=True, json_only=json_only, fields=fields, typed=typed, new_approval=new_approval, policy=trace.get('storage_policy')))
            current_raw = loaded_results.get('current', {})
            if not current_raw:
                errors.append('upgrade negative cannot be compared without valid current raw evidence')
            else:
                observations = current_raw.get('upgrade_observations', {})
                negative_observations = result.get('upgrade_observations', {})
                if not isinstance(observations, dict) or not isinstance(negative_observations, dict):
                    errors.append('upgrade negative current comparison observations invalid')
                else:
                    current_name = 'valid_legacy_record' if json_only else 'legacy_numeric_nonbinary_typed'
                    negative_name = (('non_numeric_unreadable_preserved' if 'non_numeric_unreadable_preserved' in negative_observations else 'json_unreadable_preserved')
                                     if json_only else current_name)
                    stopped_row = negative_observations.get('legacy_unreadable_preserved')
                    stopped_kind = isinstance(stopped_row, dict) and stopped_row.get('failure_kind') == STOPPED_START
                    if stopped_kind or isinstance(stopped_row, dict) and stopped_row.get('failure_kind') == 'unreadable_original_overwritten':      # the fallback proof and its negative use the same unreadable fixture
                        current_name = negative_name = 'legacy_unreadable_preserved'
                    current_row = observations.get(current_name, {}); negative_row = negative_observations.get(negative_name, {})
                    if (not isinstance(current_row, dict) or not isinstance(negative_row, dict) or
                            current_row.get('key') != negative_row.get('key') or
                            current_row.get('storage_before') != negative_row.get('storage_before') or
                            not json_only and not stopped_kind and current_row.get('expected_numeric', 45) != negative_row.get('expected_numeric', 45)):
                        errors.append('upgrade negative must use the same project key and legacy fixture value')
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
    if not isinstance(upgrade, dict): upgrade = {}
    if trace.get('schema') == 'native_storage_trace.v3' and current.get('bundle_sha256') == upgrade.get('bundle_sha256'):
        errors.append('upgrade negative and current bundle are identical')
    if current.get('bundle_sha256') == old.get('bundle_sha256'):
        errors.append('negative and current bundle are identical')
    if trace.get('schema') == 'native_storage_trace.v3' and 'current' in loaded_results:
        try:
            from startup_storage_consumers import coverage_errors
            errors.extend(coverage_errors(trace, loaded_results['current'], native, new_approval=new_approval))
        except (ValueError, OSError, TypeError, KeyError) as exc:
            errors.append('legacy consumer coverage unavailable: ' + str(exc))
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


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def execution_identity(trace):
    """Identity only; no SDK execution and no claim of cryptographic signing."""
    from maintenance_scope import checked_ref
    execution = trace.get('execution', {})
    dependencies = execution.get('dependencies')
    if not isinstance(dependencies, list): raise ValueError('explicit runner dependencies list required (self-contained runner: [])')
    base = Path(trace.get('trace_base', '.'))
    deps = []
    for ref in dependencies:
        p = checked_ref(ref, base)
        deps.append({'path': str(p), 'sha256': digest(p)})
    runner = Path(execution['runner'])
    if not runner.is_file() or digest(runner) != execution.get('runner_sha256'): raise ValueError('runner changed')
    return {'runner': str(runner.resolve()), 'runner_sha256': digest(runner),
            'command': execution.get('command'), 'dependencies': deps}


def contract_identity(trace=None):
    here = Path(__file__).resolve().parent
    rows = {}
    names = ('audit_native_storage_contract.py', 'maintenance_scope.py', 'startup_business_contract.py', 'startup_storage_consumers.py', 'scan_storage_consumers.cjs', 'vendor/acorn.cjs')
    if isinstance(trace, dict) and trace.get('numeric_snapshot_encoding'):
        names += ('numeric_snapshot_contract.py',)
    for name in names:
        file = here / name
        if not file.is_file():
            # Staged evaluation can borrow unchanged dependencies from their imported modules.
            module = __import__(name[:-3]); file = Path(module.__file__)
        rows[name] = digest(file)
    return rows


def receipt_identity(trace):
    labels = ('current', 'negative_control', 'upgrade_negative_control')
    return {'trace_sha256': canonical_sha(trace), 'contract_files': contract_identity(trace),
            'execution': execution_identity(trace),
            'raw_reports': {label: {'path': str(Path(trace[label]['raw_report']).resolve()),
                                    'sha256': digest(trace[label]['raw_report'])} for label in labels}}


def unchanged_nonconsumer_receipt(report, trace, expected):
    """A known previous rule adds no obligations when this Native has no raw consumers.
    Preserve the original execution time; never rewrite old evidence as a fresh run.
    """
    previous = report.get('execution_receipt', {}).get('identity')
    if not isinstance(previous, dict): return False
    old = previous.get('contract_files', {})
    baseline = '499c175aff78232fc57e5b8a7a6a78dd245bf090ed295f3b87491752b23d42ae'
    retained = ('maintenance_scope.py', 'startup_business_contract.py')
    if (set(old) != {'audit_native_storage_contract.py', *retained} or
            old.get('audit_native_storage_contract.py') != baseline or
            any(old.get(k) != expected['contract_files'].get(k) for k in retained) or
            {k:v for k,v in previous.items() if k != 'contract_files'} !=
            {k:v for k,v in expected.items() if k != 'contract_files'}): return False
    from check_known_issues import tree_sha
    from startup_storage_consumers import inventory
    name = report.get('native')
    if not isinstance(name,str) or not Path(name).is_absolute():return False
    native = Path(name)
    return native.is_dir() and tree_sha(native) == trace.get('binding', {}).get('native_tree_sha256') and not inventory(native)


def unchanged_text_codec_receipt(report, trace, expected):
    """Keep the actual old execution for an unchanged text-codec branch.

    The reviewed predecessor differs only by the opt-in snapshot branch and
    conditional fingerprint. All raw data, runner/dependencies and the full
    original default validator are rechecked; no execution is invented.
    """
    if trace.get('numeric_snapshot_encoding'): return False
    previous = report.get('execution_receipt', {}).get('identity')
    if not isinstance(previous, dict): return False
    old = previous.get('contract_files', {})
    if old.get('audit_native_storage_contract.py') != '35002eea8cdd657b4eb87a523ebf4ef2118a6205c90ed41501c7a666f11e439f': return False
    current = expected['contract_files']
    return (set(old) == set(current) and
            all(old[name] == current[name] for name in current if name != 'audit_native_storage_contract.py') and
            {k:v for k,v in previous.items() if k != 'contract_files'} ==
            {k:v for k,v in expected.items() if k != 'contract_files'})


# Earlier reviewed texts of the contract files whose receipts keep their original execution.
# 2026-11-12 (fallback start): against these texts the current one only adds accepted evidence for new approvals;
# validate() still applies every earlier obligation to the unchanged raw data of an earlier receipt.
REVIEWED_PREDECESSORS = {
    'numeric_snapshot_contract.py': ('bc89284895eafd0dd61b84cb68bdce8f4ee40307081601ed30afc31c14870d74',),
    'maintenance_scope.py': ('61b612615382eb079994df5013b0dbf90e7064314f1f7cee68ee07cede373017', '0c4147f64a9a32e4f27b2a30257d86193bbbcfffe7abb07dc5db0ee276daa391'),
    'audit_native_storage_contract.py': ('35002eea8cdd657b4eb87a523ebf4ef2118a6205c90ed41501c7a666f11e439f',
                                         '4f65642d5b7c702826045f82c3896b010fcb403af510126c8b58b91d6999e3fc', '80bc479c1f6d9c93c2ae862ea34924affe99b680b729467b0321ecd1b1659ddb', '3703a36dbc934e5a84787a411ca4d3275be189e9dcc022db4be727ba022dab30'),
    'startup_storage_consumers.py': ('ab3159de99f437ff14d17e6cfd34b9d39d66c48e92c7b450e2d0d5894828edc2',),
}


def reviewed_predecessor_receipt(report, trace, expected):
    """Keep the actual old execution of a receipt issued by a reviewed earlier text.

    Every other contract file, the trace, the runner, its dependencies and the raw
    reports must be identical; no execution is invented and nothing is re-run.
    """
    previous = report.get('execution_receipt', {}).get('identity')
    if not isinstance(previous, dict): return False
    old = previous.get('contract_files', {}); current = expected['contract_files']
    if not isinstance(old, dict) or set(old) != set(current): return False
    if any(old[name] != current[name] and old[name] not in REVIEWED_PREDECESSORS.get(name, ()) for name in current): return False
    # 35002eea predates the opt-in snapshot branch and never approved such a trace.
    if old.get('audit_native_storage_contract.py') == REVIEWED_PREDECESSORS['audit_native_storage_contract.py'][0] and trace.get('numeric_snapshot_encoding'):
        return False
    return ({k:v for k,v in previous.items() if k != 'contract_files'} ==
            {k:v for k,v in expected.items() if k != 'contract_files'})


def _valid_execution_mode(report, trace, receipt):
    labels = ['current', 'negative_control', 'upgrade_negative_control']
    if receipt.get('mode') == 'produced-once':
        if receipt.get('executed_once') != labels or 'replayed' in receipt:
            return False
        execution = report.get('production_execution', {})
        if not isinstance(execution, dict) or execution.get('mode') != 'execute-once-then-validate':
            return False
        runs = execution.get('runs')
        if not isinstance(runs, list) or len(runs) != len(labels):
            return False
        for label, run in zip(labels, runs):
            if not isinstance(run, dict) or set(run) != {'label', 'command', 'returncode', 'raw_sha256', 'stderr_sha256'}:
                return False
            record = trace[label]
            command = [part.replace('{bundle}', record['bundle']).replace('{adapter}', record['adapter'])
                       for part in trace['execution']['command']]
            if (run['label'] != label or type(run['returncode']) is not int or run['returncode'] != 0 or
                    run['command'] != command or run['raw_sha256'] != record.get('raw_sha256') or
                    run['raw_sha256'] != digest(record['raw_report']) or
                    not isinstance(run['stderr_sha256'], str) or len(run['stderr_sha256']) != 64 or
                    any(c not in '0123456789abcdef' for c in run['stderr_sha256'])):
                return False
        return True
    return ('mode' not in receipt and 'executed_once' not in receipt and
            receipt.get('replayed') == labels)


def validate_execution_receipt(report, trace):
    """Read-only rejudgment: valid evidence is not re-executed at each writer."""
    receipt = report.get('execution_receipt', {})
    try:
        if (not isinstance(receipt, dict) or receipt.get('schema') != 'native_storage_execution_receipt.v1' or
                not isinstance(receipt.get('run_id'), str) or not receipt['run_id'] or
                not isinstance(receipt.get('verified_at'), str) or not receipt['verified_at'] or
                not _valid_execution_mode(report, trace, receipt) or
                (receipt.get('identity') != receipt_identity(trace) and not unchanged_nonconsumer_receipt(report, trace, receipt_identity(trace)) and not unchanged_text_codec_receipt(report, trace, receipt_identity(trace)) and
                 not reviewed_predecessor_receipt(report, trace, receipt_identity(trace)))):
            return ['missing, stale or mismatched storage execution receipt']
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        return ['storage execution receipt identity invalid: ' + str(exc)]
    return []


def _approve_runtime(trace, native, binding, *, replay_required=True, production_errors=(), seal_scope=True):
    """Validate and execute once; consumers later rejudge the unchanged receipt.

    Project runners retain existing incremental plan/ledger semantics. Replaying
    orchestration does not license rerunning unrelated cases or changing data.
    """
    errors = list(production_errors) + validate(trace, native, binding, new_approval=True)
    if not errors and replay_required: errors.extend(replay(trace))
    report = {'tool': 'audit_native_storage_contract', 'binding': binding, 'storage_policy': (JSON_RETRY_POLICY if trace.get('storage_policy') == JSON_RETRY_POLICY else STORAGE_POLICY),
              'checked': len(CASES) + 2, 'failed': len(errors), 'passed': not errors,
              'policy_version': POLICY_VERSION, 'status': ('needs_upgrade' if trace.get('schema') != 'native_storage_trace.v3' else 'passed' if not errors else 'failed'),
              'required_cases': list(CASES), 'native': str(Path(native).resolve()),
              'negative_kind': trace.get('negative_control', {}).get('kind', 'historical_release'),
              'route_policy': 'verified_existing_routes' if trace.get('schema') in ('native_storage_trace.v2', 'native_storage_trace.v3') else 'all_three_required',
              'errors': errors}
    if not errors:
        try: identity = receipt_identity(trace)
        except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
            errors.append('execution receipt unavailable: ' + str(exc))
            report.update(passed=False, failed=len(errors), status='failed')
    if not errors:
        report['execution_receipt'] = {'schema': 'native_storage_execution_receipt.v1', 'run_id': str(uuid.uuid4()),
            'verified_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'replayed': ['current', 'negative_control', 'upgrade_negative_control'], 'identity': identity}
    try:
        observed = read(trace['current']['raw_report']).get('cases', {})
        report['checked_routes'] = [name for name in ('home', 'map', 'stage_details') if observed.get('reopen_' + name) == 'pass']
        report['excluded_routes'] = [name for name in ('map', 'stage_details') if observed.get('reopen_' + name) == 'not_applicable']
    except (KeyError, OSError, ValueError, AttributeError, TypeError):
        report['checked_routes'], report['excluded_routes'] = [], []
    if not errors and seal_scope and trace.get('project'):
        from storage_scoped_reuse import seal_approval
        try:
            report['storage_scope'] = seal_approval(report, trace, native, trace['project'])
        except (ValueError, OSError, KeyError, TypeError) as exc:
            report['storage_scope_status'] = {'status': 'scope_required', 'node': 'storage.native.contract', 'reason': str(exc)}
    return report


def approve_runtime(trace, native, binding):
    """Compatibility entry: existing raw evidence is replayed once as before."""
    return _approve_runtime(trace, native, binding)


def produce_runtime_once(trace, native, binding, produced_trace):
    """Execute three fixed recorded commands once, seal raw bytes, then validate.

    Caller supplied case/pass labels are never used as execution evidence. Raw
    targets and produced_trace must be new files. Consumers retain the ordinary
    immutable execution receipt checks; the historical replay API is unchanged.
    """
    import copy
    trace = copy.deepcopy(trace)
    errors = []
    produced_trace = Path(produced_trace).resolve()
    if produced_trace.exists():
        raise ValueError('produced trace already exists; consume its approval instead of rerunning')
    if trace.get('schema') != 'native_storage_trace.v3' or trace.get('binding') != binding:
        raise ValueError('producer requires current v3 trace binding')
    execution_identity(trace)  # verifies exact runner and explicit dependencies before execution
    command = trace['execution']['command']
    runner = Path(trace['execution']['runner']).resolve()
    if (not isinstance(command, list) or not all(isinstance(x, str) for x in command) or
            str(Path(trace['execution']['runner'])) not in command or '{bundle}' not in command or '{adapter}' not in command):
        raise ValueError('fixed production runner command with bundle/adapter slots required')
    labels = ('current', 'negative_control', 'upgrade_negative_control')
    paths = set()
    before_identity = execution_identity(trace)
    for label in labels:
        row = trace.get(label, {})
        bundle, adapter, raw = (Path(row.get(k, '')).resolve() for k in ('bundle', 'adapter', 'raw_report'))
        if (not bundle.is_file() or not adapter.is_file() or raw.exists() or raw in paths or
                raw == produced_trace or raw in (bundle, adapter, runner) or raw.is_relative_to(Path(native).resolve())):
            raise ValueError('new distinct raw outputs outside Native and actual input files required: ' + label)
        if label == 'current' and (not inside(native, bundle) or not inside(native, adapter)):
            raise ValueError('current producer inputs must be in final Native tree')
        if digest(bundle) != row.get('bundle_sha256') or digest(adapter) != row.get('adapter_sha256'):
            raise ValueError('production input bytes changed before execution: ' + label)
        paths.add(raw)
    records = []
    for label in labels:
        row = trace[label]
        raw = Path(row['raw_report']).resolve()
        actual = [x.replace('{bundle}', row['bundle']).replace('{adapter}', row['adapter']) for x in command]
        try:
            proc = subprocess.run(actual, capture_output=True, text=True, timeout=120, check=False)
            # Persist exact actual stdout, never the caller's asserted JSON. Invalid output remains diagnostic evidence.
            raw.parent.mkdir(parents=True, exist_ok=True)
            with raw.open('x', encoding='utf-8') as stream: stream.write(proc.stdout)
            row['raw_sha256'] = digest(raw)
            records.append({'label': label, 'command': actual, 'returncode': proc.returncode,
                            'raw_sha256': row['raw_sha256'], 'stderr_sha256': hashlib.sha256(proc.stderr.encode()).hexdigest()})
            result = json.loads(proc.stdout)
            if not isinstance(result, dict) or proc.returncode != 0:
                errors.append(label + ' actual producer failed')
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            errors.append(label + ' actual producer failed: ' + type(exc).__name__)
        if digest(Path(row['bundle'])) != row['bundle_sha256'] or digest(Path(row['adapter'])) != row['adapter_sha256']:
            errors.append(label + ' production input bytes changed during execution')
    if execution_identity(trace) != before_identity:
        errors.append('runner or dependency bytes changed during production')
    # New trace is part of the raw-evidence closure; no old trace is overwritten.
    produced_trace.parent.mkdir(parents=True, exist_ok=True)
    with produced_trace.open('x', encoding='utf-8') as stream:
        json.dump(trace, stream, ensure_ascii=False, indent=2); stream.write('\n')
    report = _approve_runtime(trace, native, binding, replay_required=False, production_errors=errors, seal_scope=False)
    report.update(trace=str(produced_trace), trace_sha256=digest(produced_trace),
                  production_execution={'mode': 'execute-once-then-validate', 'runs': records})
    if report.get('passed') is True and 'execution_receipt' in report:
        receipt = report['execution_receipt']
        receipt.pop('replayed', None)
        receipt.update(mode='produced-once', executed_once=list(labels))
        # Scope identity must freeze the complete final producer receipt. Sealing
        # the compatibility replay form before this point makes later reuse stale.
        if trace.get('project'):
            from storage_scoped_reuse import seal_approval
            try:
                report['storage_scope'] = seal_approval(report, trace, native, trace['project'])
            except (ValueError, OSError, KeyError, TypeError) as exc:
                report['storage_scope_status'] = {'status': 'scope_required', 'node': 'storage.native.contract', 'reason': str(exc)}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', required=True, type=Path)
    parser.add_argument('--native', required=True, type=Path)
    parser.add_argument('--binding', required=True, type=Path, help='current known-issue review JSON')
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--produce-once', action='store_true', help='execute each fixed runner once before full approval validation')
    parser.add_argument('--produced-trace', type=Path, help='new trace output required with --produce-once')
    args = parser.parse_args()
    trace = read(args.trace)
    binding = read(args.binding).get('binding')
    if args.produce_once:
        if args.produced_trace is None: parser.error('--produce-once requires --produced-trace')
        report = produce_runtime_once(trace, args.native, binding, args.produced_trace)
    else:
        report = approve_runtime(trace, args.native, binding)
        report.update(trace=str(args.trace.resolve()), trace_sha256=digest(args.trace))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'failed': report['failed'], 'out': str(args.out)}))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
