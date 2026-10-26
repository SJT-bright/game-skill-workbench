#!/usr/bin/env python3
"""Audit loading-recovery coverage and hashed runtime evidence; never runs a game.

See references/loading-recovery-regression.md for the trace contract and limits.
Missing cases, stale bindings and a Retry that reuses an abandoned request fail.
"""
import argparse
import hashlib
import math
import json
from pathlib import Path
import sys

TOOL = 'audit_loading_recovery'
POLICY_VERSION = 'sock-first-retry-v2'
SCENARIOS = {
    'sdk_and_watchdog_held': ('sdk_callback_held', 'watchdog_held', 'frame_watchdog_active'),
    'explicit_failure': ('explicit_failure_observed',),
    'image_inflight_retry': ('real_image_response_held', 'engine_inflight_released', 'old_transport_aborted_or_late_isolated', 'same_url_requested_again'),
    'slow_progress': ('progress_advanced', 'crossed_old_deadline', 'no_premature_timeout'),
    'background_wait': ('background_longer_than_idle', 'background_time_excluded'),
    'late_success': ('old_success_delivered', 'old_result_ignored', 'current_state_unchanged'),
    'late_failure': ('old_failure_delivered', 'old_result_ignored', 'current_state_unchanged'),
    'callback_promise': ('callback_only', 'promise_only', 'both_channels', 'settled_once', 'progress_api_absent'),
    'warm_reentry': ('ready_assets_retained', 'no_redundant_request', 'replay_reset_verified'),
    'optional_font': ('font_failure_nonblocking', 'font_hang_nonblocking', 'late_font_no_page_restart'),
    'request_local_clock': ('clock_starts_at_request', 'progress_before_frame_preserved'),
    'normal_control': ('no_fault_injection', 'cold_cache', 'save_preserved'),
}
RETRY = {'sdk_and_watchdog_held', 'explicit_failure', 'late_success', 'late_failure', 'image_inflight_retry'}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate(data, binding, base):
    if isinstance(data, dict) and data.get('profile') == 'runhome_native_loading_v1':
        from runhome_native_loading_contract import validate_loading
        return validate_loading(data, binding, base)
    if isinstance(data, dict) and data.get('profile') == 'dessert_cocos24_facade_retry_v1':
        from dessert_cocos24_startup_contract import validate_loading
        return validate_loading(data,binding,base)
    if isinstance(data, dict) and data.get('profile') == 'googly_native_recovery_v1':
        from googly_native_recovery_contract import validate_loading
        return validate_loading(data, binding, base)
    if isinstance(data, dict) and data.get('profile') == 'cat_cocos3_loading_v1':
        from cat_cocos3_loading_contract import validate_loading
        return validate_loading(data, binding, base)
    if isinstance(data, dict) and data.get('profile') == 'duo_sdk_ui_retry_v1':
        from duo_sdk_ui_retry_contract import validate_loading
        return validate_loading(data, binding, base)
    if isinstance(data, dict) and data.get('profile') == 'cocos24_adapter_coordinates_v1':
        from cocos24_adapter_coordinates_contract import validate_loading
        return validate_loading(data, binding, base)
    if isinstance(data, dict) and data.get('profile') == 'cocos24_sdk_screen_input_v1':
        from cocos24_screen_input_contract import validate_loading
        return validate_loading(data, binding, base)
    errors = []
    def need(ok, message):
        if not ok:
            errors.append(message)
    need(all(binding.get(k) for k in ('source_sha256', 'native_tree_sha256', 'web_tree_sha256', 'build_tag')), 'complete current build binding required')
    need(data.get('binding') == binding, 'stale/missing runtime binding')
    need(data.get('execution_binding', binding) == binding, 'execution binding differs: rerun affected current candidate; do not relabel old execution')
    need(type(data.get('image_format_change')) is bool, 'declare whether image format changed')
    if data.get('image_format_change') is True or data.get('native_codec_verified') is True or data.get('codec_evidence_refs'):
        need(data.get('native_codec_verified') is True and bool(data.get('codec_evidence_refs')) and all(type(i) is int and 0 <= i < len(data.get('raw_evidence', [])) for i in data.get('codec_evidence_refs', [])), 'changed format requires actual Native decoder evidence; encoding capability is insufficient')
    need(data.get('producer') == 'real_browser_touch_trace', 'runtime touch evidence required; isolated tests are supplementary')
    refs = data.get('raw_evidence', [])
    need(bool(refs), 'raw_evidence missing')
    for ref in refs:
        try:
            p = (base / ref['path']).resolve()
            p.relative_to(base.resolve())
            need(p.is_file() and p.stat().st_size > 0 and hashlib.sha256(p.read_bytes()).hexdigest() == ref.get('sha256'), 'raw evidence missing/empty/changed: ' + str(p))
        except (KeyError, TypeError, OSError, ValueError) as e:
            errors.append('invalid raw evidence: ' + str(e))
    cases = data.get('cases', [])
    for scenario, fields in SCENARIOS.items():
        rows = [r for r in cases if r.get('scenario') == scenario]
        need(len(rows) == 1, scenario + ': exactly one case required')
        if len(rows) != 1:
            continue
        row = rows[0]
        for field in fields:
            need(row.get(field) is True, scenario + ': missing/failed ' + field)
        observed = row.get('observed_viewports', [])
        need(all(v in observed for v in data.get('viewports', [])) and len(observed) >= 2, scenario + ': actual per-case two-viewport observations required')
        indexes = row.get('evidence_refs', [])
        need(bool(indexes) and all(type(i) is int and 0 <= i < len(refs) for i in indexes), scenario + ': evidence_refs invalid')
        need(bool(str(row.get('injection_boundary', '')).strip()), scenario + ': record actual external boundary (normal_control: none)')
        need(row.get('production_code_unchanged') is True, scenario + ': do not replace production loader/watchdog with fixture')
        if scenario == 'image_inflight_retry':
            need(row.get('retry_gesture_count') == 1 and type(row.get('retry_gesture_count')) is int and row.get('manual_intervention') is False, scenario + ': exactly one real Retry, no manual rescue')
            before, after = row.get('request_count_before'), row.get('request_count_after')
            need(type(before) is int and before >= 1 and type(after) is int and after == before + 1 and bool(str(row.get('resource_id', '')).strip()), scenario + ': same resource must have exactly one additional underlying request after Retry')
        if scenario in RETRY:
            events = row.get('events', [])
            def event(kind):
                return next((e for e in events if e.get('kind') == kind), {})
            start, fail, touch, fresh, ready, action = [event(k) for k in ('request', 'retry_visible', 'retry_touch', 'new_request', 'ready', 'input_effect')]
            times = [e.get('t_ms') for e in (start, fail, touch, fresh, ready, action)]
            need(all(type(t) in (int, float) and math.isfinite(t) and t >= 0 for t in times) and times == sorted(times), scenario + ': require ordered request/Retry/touch/new-request/ready/input-effect trace')
            need(len([e for e in events if e.get('kind') == 'retry_touch']) == 1, scenario + ': duplicate Retry gestures cannot count as first-Retry recovery')
            old_id, new_id = start.get('request_id'), fresh.get('request_id')
            need(bool(old_id) and bool(new_id) and old_id != new_id, scenario + ': Retry reused abandoned request')
            need(ready.get('request_id') == new_id and bool(new_id), scenario + ': ready must belong to new request')
            need(touch.get('trusted_touch') is True and action.get('trusted_touch') is True and bool(str(action.get('effect', '')).strip()), scenario + ': real Retry touch and changed gameplay required')
            if scenario == 'sdk_and_watchdog_held':
                idle, since = row.get('idle_budget_ms'), row.get('last_progress_ms')
                need(type(idle) in (int, float) and 0 < idle <= 10000 and type(since) in (int, float) and type(fail.get('t_ms')) in (int, float) and idle <= fail['t_ms'] - since <= idle + 2000, scenario + ': bounded foreground no-progress recovery missing')
        else:
            need(row.get('trusted_touch') is True and bool(str(row.get('interaction_effect', '')).strip()), scenario + ': playable interaction evidence required')
    vps = data.get('viewports', [])
    need(len({round(v[0] / v[1], 3) for v in vps if isinstance(v, list) and len(v) == 2 and all(type(n) is int and n > 0 for n in v)}) >= 2, 'two different phone aspect ratios required')
    need(data.get('native_boundary_verified') is True and bool(str(data.get('native_boundary_description', '')).strip()), 'verify adapter capture order and real subpackage boundary; Web-only success cannot substitute')
    calibration = data.get('calibration', {})
    need(calibration.get('old_failed') is True and calibration.get('fixed_passed') is True and bool(calibration.get('evidence_refs')) and all(type(i) is int and 0 <= i < len(refs) for i in calibration.get('evidence_refs', [])), 'known-bad/fixed calibration evidence required; never manufacture old failure')
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime', required=True, type=Path)
    p.add_argument('--binding', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    binding, checked = None, 0
    try:
        b = load(a.binding); binding = b.get('binding', b)
        data = load(a.runtime)
        errors = validate(data, binding, a.runtime.parent)
        checked = len(SCENARIOS)
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        errors = ['invalid input: ' + str(e)]
    report = dict(tool=TOOL, policy_version=POLICY_VERSION, runtime_file=str(a.runtime.resolve()), runtime_sha256=hashlib.sha256(a.runtime.read_bytes()).hexdigest() if a.runtime.is_file() else None, stage='runtime', binding=binding, checked=checked, failed=len(errors), passed=not errors, errors=errors,
                  limits='Coverage, trace and hash audit only. Codex must read raw evidence. No physical TikTok, real SDK or portal acceptance implied.')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return int(bool(errors))


if __name__ == '__main__':
    sys.exit(main())
