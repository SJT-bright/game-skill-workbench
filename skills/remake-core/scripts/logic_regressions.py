#!/usr/bin/env python3
"""Evidence requirements learned from real reviews; does not operate a game.

Static findings are suspects. Runtime rows are tester observations with hashed
artifacts and a current source/data binding, never proof inferred from a regex.
"""
import hashlib
import math
from pathlib import Path
import re
import button_state_check
from input_owner_inventory import inspect_sources

CASES = [
    ('R01', '循环列表与边界', 'L-CYCLIC', ('browser_touch',),
     ('inventory', 'reverse_cycles', 'forward_cycles', 'empty_singleton_boundaries', 'controls_remain_usable')),
    ('R02', '坏存档与迁移恢复', 'L-SAVE-RECOVERY', ('browser_fault',),
     ('malformed_json', 'missing_fields', 'wrong_types_and_ranges', 'valid_fields_preserved', 'retry_or_recovery_works', 'native_missing_key_semantics', 'actual_reward_ledger_and_adapter', 'storage_failure_diagnostics')),
    ('R03', '挂起加载与真实重试', 'L-LOAD-RETRY', ('browser_fault', 'mixed_runtime'),
     ('held_real_transport', 'held_callback_and_timer', 'frame_recovery', 'fresh_underlying_request',
      'late_result_isolated', 'ready_then_input', 'explicit_failure_and_normal_controls')),
    ('R04', '资源扣除与实际消费者', 'L-CONSUMER', ('browser_touch', 'browser_fault'),
     ('consuming_entries', 'non_play_pages_no_spend', 'active_consumer_effect', 'close_leave_duplicate_safety', 'effect_visibility_and_next_input')),
    ('R05', '失败与暂停标准控件', 'L-EXIT', ('browser_touch',),
     ('failure_home_retry', 'optional_ad_separate', 'pause_resume_restart_home', 'destinations_and_costs', 'two_aspect_ratios')),
    ('R06', '按钮按状态产生业务反馈', 'L-BUTTON-EFFECT', ('browser_touch',),
     ('page_state_inventory', 'visible_button_outcomes', 'mode_specific_tools', 'close_restores_input', 'legitimate_noop_feedback', 'nonfunctional_legacy_entries_removed', 'disabled_state_outcomes')),
    ('R07', '触点归属与取消', 'L-POINTER', ('browser_touch',),
     ('input_policy', 'second_contact_ownership', 'secondary_cancel_safety', 'primary_cancel_no_commit', 'next_gesture_works', 'legal_drag_actual_effect',
      'outside_end_vs_system_cancel', 'rendered_vs_hit_coordinates', 'actual_loaded_artifacts')),
    ('R08', '当前运行数据与测试绑定', 'L-RUNTIME-DATA', ('production_data_replay', 'mixed_runtime'),
     ('runtime_data_paths', 'actual_counts', 'all_runtime_configurations', 'suite_targets_match_runtime', 'ui_sampling_scope')),
    ('R09', '实际音频输出与失败恢复', 'L-AUDIO-OUTPUT', ('browser_touch', 'browser_fault', 'mixed_runtime'),
     ('channel_inventory', 'actual_loaded_artifacts', 'settings_and_pcm_output',
      'independent_channels', 'partial_load_failure_recovery', 'current_clip_retry_recovery',
      'settings_close_and_background_restore')),
]


def source_digest(project):
    """Bind observations to scripts/configs in assets, not prior report counts."""
    skip = {'node_modules', 'library', 'temp', 'build', '.git'}
    digest = hashlib.sha256()
    for p in sorted((Path(project) / 'assets').rglob('*')):
        rel = p.relative_to(project).as_posix()
        if not p.is_file() or p.suffix not in {'.js', '.ts', '.json'} or skip & set(p.parts):
            continue
        digest.update(rel.encode('utf-8') + b'\0' + hashlib.sha256(p.read_bytes()).digest())
    return digest.hexdigest()


def templates():
    return [{'id': ident, 'title': title, 'status': 'untested', 'layer': '',
             'observations': {}, 'evidence': [], 'note': ''} for ident, title, *_ in CASES]


def static_suspects(files):
    found = []
    for rel, code in files:
        # JS remainder retains the dividend sign: adding one length is not
        # sufficient for an unbounded backwards cursor. Fully normalized modulo
        # does not match; a bounded cursor still needs human triage.
        pattern = r'\(\s*(?:index|idx|cursor|page|selected\w*)\s*\+\s*(?P<n>[\w.]+(?:\.length)?)\s*\)\s*%\s*(?P=n)\b'
        for m in re.finditer(pattern, code):
            tail = code[m.end():m.end() + len(m['n']) * 2 + 30]
            if re.match(r'\s*\+\s*' + re.escape(m['n']) + r'\s*\)\s*%\s*' + re.escape(m['n']) + r'\b', tail):
                continue  # ((index + n) % n + n) % n
            found.append({'rule': 'L-CYCLIC', 'severity': 'fail', 'file': rel,
                          'line': code.count('\n', 0, m.start()) + 1,
                          'message': 'signed remainder after adding one length can become negative after repeated reverse navigation; inspect cursor bounds and test >=3 full cycles (R01); use normalized modulo if unbounded'})
        if re.search(r'JSON\.parse\s*\(', code) and re.search(r'getItem\s*\(', code):
            found.append({'rule': 'L-SAVE-RECOVERY', 'severity': 'hint', 'file': rel, 'line': 1,
                          'message': 'saved JSON is parsed: run R02 against malformed/partial/type/range records and verify a usable recovery path; try/catch or a Retry label alone does not prove recovery'})
        if re.search(r'setInterval\s*\(', code) and re.search(r'loadBundle|resources\.load|loadResource', code):
            found.append({'rule': 'L-LOAD-RETRY', 'severity': 'hint', 'file': rel, 'line': 1,
                          'message': 'loading uses an interval: R03 must hold the real transport and original watchdog together, then verify a fresh underlying request and playable input; never infer retry success from a button'})
    return found



def input_owner_sources(project):
    """Conservative inventory for explicit contact ownership; not a bug verdict."""
    sources = [p.resolve() for p in sorted((Path(project) / 'assets').rglob('*'))
               if p.is_file() and p.suffix in {'.js', '.ts', '.cjs', '.mjs'} and
               not {'node_modules', 'library', 'temp', 'build', '.git'} & set(p.parts)]
    # Unknown executable input must be covered, not declared absent.
    return [p for p, inventory in zip(sources, inspect_sources(sources)) if inventory['status'] != 'none']



def _observable_effects(rec, ident):
    """Check measured outcomes, not input receipts or playing/volume flags.

    Raw logs/recordings remain mandatory hashed row evidence. These numerical
    checks cannot establish that observations were honestly captured.
    """
    errors = []
    def need(ok, message):
        if not ok:
            errors.append(message)
    def viewport(value):
        return (isinstance(value, list) and len(value) == 2 and
                all(type(n) in (int, float) and math.isfinite(n) and n > 0 for n in value))
    if ident == 'R07':
        applicable = rec.get('drag_applicable')
        need(type(applicable) is bool, 'R07 declare drag_applicable from the actual input inventory')
        if applicable is False:
            need(bool(str(rec.get('drag_absence_reason') or '').strip()), 'R07 no-drag scope needs an actual reason')
        elif applicable is True:
            rows = rec.get('drag_samples', [])
            need(isinstance(rows, list) and bool(rows), 'R07 missing drag_samples with business before/after')
            groups = {}
            for row in rows if isinstance(rows, list) else []:
                if not isinstance(row, dict) or not viewport(row.get('viewport')):
                    errors.append('R07 invalid measured viewport'); continue
                groups.setdefault(tuple(row['viewport']), set()).add(row.get('kind'))
                need(row.get('trusted_touch') is True and row.get('picked') is True and row.get('held_after') is False,
                     'R07 real pickup/release required')
                before, after = row.get('before'), row.get('after')
                need(before is not None and after is not None and type(before) is type(after), 'R07 missing comparable business states')
                if row.get('kind') == 'legal':
                    need(before != after, 'R07 legal drag produced no business effect')
                elif row.get('kind') in ('system_cancel', 'invalid'):
                    need(before == after, 'R07 cancelled/invalid drag changed business state')
                else:
                    errors.append('R07 unsupported drag sample kind')
            need(len({round(v[0]/v[1], 6) for v in groups}) >= 2 and all({'legal', 'system_cancel', 'invalid'} <= kinds for kinds in groups.values()),
                 'R07 both viewports require legal, original system_cancel and invalid drops')
    elif ident == 'R09':
        channels = rec.get('audio_channels', [])
        need(isinstance(channels, list) and bool(channels) and len(set(channels)) == len(channels) and
             all(c in ('music', 'sfx') for c in channels), 'R09 declare actual music/sfx channels')
        channels = channels if isinstance(channels, list) else []
        for absent in {'music', 'sfx'} - set(channels):
            need(bool(str(rec.get('absent_channels', {}).get(absent) or '').strip()), 'R09 explain absent channel: ' + absent)
        rows = rec.get('audio_samples', [])
        need(isinstance(rows, list) and bool(rows), 'R09 missing actual audio output samples')
        groups = {}
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict) or not viewport(row.get('viewport')):
                errors.append('R09 invalid measured viewport'); continue
            channel, mode = row.get('channel'), row.get('mode')
            need(channel in channels and mode in ('zero', 'mid', 'full', 'off', 'on'), 'R09 invalid channel/mode')
            key = (tuple(row['viewport']), channel)
            samples = groups.setdefault(key, {})
            need(mode not in samples, 'R09 duplicate channel/mode observation')
            values = row.get('rms_samples', [])
            valid = (isinstance(values, list) and len(values) >= 3 and
                     all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in values))
            need(valid and row.get('trusted_touch') is True, 'R09 requires finite measured RMS and real settings input')
            if valid:
                peak = max(values); samples[mode] = (peak, row.get('signal_id'))
                need(peak <= 1e-5 if mode in ('zero', 'off') else peak > 1e-5, 'R09 silent/audible output mismatch: ' + str(mode))
        views = {key[0] for key in groups}
        need(len({round(v[0]/v[1], 6) for v in views}) >= 2, 'R09 requires two actual aspect ratios')
        for view in views:
            for channel in channels:
                modes = groups.get((view, channel), {})
                need({'zero', 'mid', 'full', 'off', 'on'} <= modes.keys(), 'R09 incomplete output matrix: ' + channel)
                if 'mid' in modes and 'full' in modes:
                    mid, full = modes['mid'], modes['full']
                    need(bool(mid[1]) and mid[1] == full[1], 'R09 compare the same decoded signal/segment at mid/full')
                    need(0 < mid[0] < full[0] * .8, 'R09 mid/full measured output did not change')
    return errors


def observable_effects(rec, ident):
    try:
        return _observable_effects(rec, ident)
    except (TypeError, ValueError, KeyError, AttributeError, IndexError) as exc:
        return ['invalid measured effect evidence: ' + str(exc)]


def validate(document, project, digest):
    """Check completeness/integrity; cannot decide if observation text is true."""
    records = document.get('regressions', [])
    records = records if isinstance(records, list) else []
    rows, problems = [], []
    for ident, title, rule, layers, required in CASES:
        matches = [r for r in records if isinstance(r, dict) and r.get('id') == ident]
        rec = matches[0] if len(matches) == 1 else {}
        row = dict(rec, id=ident, title=title, rule=rule)
        status = rec.get('status', 'missing')
        row['status'] = status
        errors = []
        if len(matches) > 1:
            errors.append('duplicate regression id')
        if status == 'n/a':
            if not str(rec.get('note') or '').strip():
                errors.append('n/a requires the actual missing feature or explicit scope reason')
            if ident == 'R06':
                errors.append('R06 button coverage cannot use n/a; scope the affected control inventory instead')
        elif status == 'pass':
            if document.get('regression_binding') != {'source_sha256': digest}:
                errors.append('stale/missing current script and runtime-data binding; rerun affected cases')
            if rec.get('layer') not in layers:
                errors.append('required observation layer: ' + ', '.join(layers))
            obs = rec.get('observations')
            if not isinstance(obs, dict):
                obs = {}
            missing = [key for key in required if not isinstance(obs.get(key), str) or
                       obs[key].strip().lower() in {'', 'pass', 'true', 'ok', 'tested', '通过', '已测'}]
            if missing:
                errors.append('concrete observations missing: ' + ', '.join(missing))
            refs = rec.get('evidence')
            if not isinstance(refs, list) or not refs:
                errors.append('nonempty hashed evidence files required')
                refs = []
            for ref in refs:
                try:
                    p = Path(project) / ref['path']
                    if not p.is_file() or p.stat().st_size == 0 or hashlib.sha256(p.read_bytes()).hexdigest() != ref.get('sha256'):
                        errors.append('evidence missing, empty or changed: ' + str(p))
                except (TypeError, KeyError, OSError):
                    errors.append('invalid evidence reference')
            if ident in ('R07', 'R09'):
                errors.extend(observable_effects(rec, ident))
            if ident == 'R06':
                root = Path(rec.get('button_check_root', project)).resolve()
                if (not Path(project).resolve().is_relative_to(root) or
                        not button_state_check.current_report(root, rec.get('button_check'))):
                    errors.append('R06 requires a current scoped button_state_check report; prose cannot replace per-control/state outcomes')
                else:
                    # Full baseline must not omit the production owner from the
                    # hand-written button plan and then claim non-applicability.
                    owners = input_owner_sources(project)
                    if owners:
                        try:
                            report = button_state_check.read_ref(root, rec['button_check'], True)
                            plan = button_state_check.read_ref(root, report['inputs']['plan'], True)
                            bound = {button_state_check.read_ref(root, ref).resolve() for ref in plan['business_sources']}
                            if plan.get('input_lifecycle', {}).get('applicable') is not True:
                                errors.append('R06 production touch owners require input lifecycle coverage')
                            missing_owners = [p.relative_to(Path(project).resolve()).as_posix() for p in owners if p not in bound]
                            if missing_owners:
                                errors.append('R06 omitted production input owner source binding: ' + ', '.join(missing_owners))
                        except (KeyError, TypeError, ValueError, OSError):
                            errors.append('R06 invalid production input owner coverage')

        else:
            errors.append({'missing': 'case missing; run --init to append without resetting prior results',
                           'untested': 'not tested; cannot pass', 'fail': 'reproduced failure; fix and rerun'}.get(status, 'unknown status'))
        if errors:
            row['problem'] = '; '.join(errors)
            problems.append(row)
        rows.append(row)
    return rows, problems


def current_report(report, base):
    """Main gate must not accept pre-regression or subsequently edited evidence."""
    digest = report.get('current_source_sha256', '')
    if (report.get('mode') != 'build' or report.get('regression_version') != 1 or
            report.get('regression_problems') != 0 or not isinstance(digest, str) or
            re.fullmatch(r'[0-9a-f]{64}', digest) is None or
            report.get('regression_binding') != {'source_sha256': digest}):
        return False
    _, errors = validate(report, base, digest)
    return not errors
