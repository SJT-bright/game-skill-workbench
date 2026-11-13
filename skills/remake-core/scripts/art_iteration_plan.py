"""Plan the next art action from existing contracts; never execute product actions or approve art.

No game-specific names or time cutoffs. Capture reuse remains exclusively the
decision of art_capture_round. State is only a bounded last-plan record, outside
assets and the capture/production declarations.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time

from art_round_check import run as capture_check


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode()


def read(path, default=None):
    return json.loads(Path(path).read_text()) if Path(path).is_file() else default


def issue(layer, code, targets=()):
    return dict(layer=layer, code=code, targets=sorted(set(str(x) for x in targets)))


def mapping(visual, capture):
    """Map two different ID spaces only by exact declared state/viewport or explicit link."""
    rows, errors = {}, []
    states = capture.get('cases', [])
    visual_cases = visual.get('cases', [])
    if not isinstance(states, list) or not isinstance(visual_cases, list):
        raise ValueError('case collections must be arrays')
    ids = [s.get('id') for s in states]
    vids = [s.get('id') for s in visual_cases]
    if any(not isinstance(x, str) or not x for x in ids+vids) or len(set(ids)) != len(ids) or len(set(vids)) != len(vids):
        raise ValueError('case IDs must be nonempty and unique in each namespace')
    for slot in visual_cases:
        candidates = [s for s in states if s.get('screen') == slot.get('screen')
                      and s.get('width') == slot.get('viewport_width')
                      and ('viewport_height' not in slot or s.get('height') == slot['viewport_height'])]
        if 'capture_case' in slot:
            candidates = [s for s in candidates if s['id'] == slot['capture_case']]
        if len(candidates) != 1:
            errors.append(issue('scope', 'missing_or_ambiguous_capture_mapping', [slot['id']]))
        else:
            rows[slot['id']] = candidates[0]['id']
    for asset in visual.get('production_assets', []):
        required = asset.get('expected_cases')
        if not isinstance(required, list) or not required:
            errors.append(issue('scope', 'production_consumers_not_declared', [asset.get('id', '?')]))
        elif any(x not in vids for x in required):
            errors.append(issue('scope', 'production_consumer_missing_visual_rule',
                                [x for x in required if x not in vids]))
    return rows, errors


def first_piece_state(project, path, slots, dumps=None, board=None):
    """Reuse a sealed exact-input result; replay only a missing/stale first piece.

    External passed scalars never confer trust or capture/full-art approval.
    """
    if path is None:
        return dict(current=False, reason='not_supplied', selected_cases=[], remaining_cases=sorted(slots))
    data = read(path)
    if not isinstance(data, dict) or data.get('tool') != 'art_production_preflight':
        raise ValueError('first-piece input must be an actual production-preflight report')
    declared = data.get('input_binding', {})
    selected = data.get('selected_cases', [])
    result = dict(current=False, passed=False, reason='binding_unavailable',
                  selected_cases=selected, remaining_cases=sorted(set(slots)-set(selected)), report=str(path))
    if (not isinstance(selected, list) or not selected or len(set(selected)) != len(selected)
            or any(x not in slots for x in selected)):
        result['reason'] = 'invalid_selected_scope'
        return result, data
    if not declared.get('available'):
        return result, data
    from art_preflight import sealed_first_piece, seal_first_piece, run as check_first_piece
    scope = declared.get('scope', {})
    if scope.get('board') != board or board not in (None, 'localize', 'remake'):
        result['reason'] = 'board_does_not_match_current_request'
        return result, None
    files = [Path(x['file']) for x in declared.get('documents', [])]
    binding = scope.get('binding')
    if binding is not None and (not isinstance(binding, dict) or not isinstance(binding.get('path'), str)):
        result['reason'] = 'invalid_binding'
        return result, None
    binding = binding.get('path') if binding else None
    policy = scope.get('clarity_policy')
    actual, checked, cache = sealed_first_piece(project, path, files, selected, board, binding, policy)
    if not actual.get('available'):
        result['reason'] = 'current_input_binding_unavailable'
        return result, data
    if checked is not None:
        result.update(current=True, passed=checked['passed'], checker_replays=0,
                      reason='trusted_first_piece_reused',
                      binding_sha256=hashlib.sha256(encoded(actual)).hexdigest())
        return result, checked
    with tempfile.TemporaryDirectory(prefix='art-first-piece-recheck-') as temporary:
        out = Path(temporary)/'result'
        with contextlib.redirect_stdout(io.StringIO()):
            code = check_first_piece(project, None, out, board, binding, selected, dump_files=files, clarity_policy=policy)
        checked = read(out/'production-preflight.json')
    result['checker_replays'] = 1
    if (checked.get('input_binding') != actual or checked.get('selected_cases') != selected
            or checked.get('full_art_passed') is not None or checked.get('receipt_written') is not False):
        result['reason'] = 'rechecked_evidence_or_inputs_differ'
        return result, checked
    seal_first_piece(cache, path, checked)
    result.update(current=True, passed=code == 0 and checked.get('passed') is True,
                  reason='trusted_first_piece_rechecked',
                  recheck_seconds=checked.get('elapsed_seconds'),
                  binding_sha256=hashlib.sha256(encoded(actual)).hexdigest())
    # Temporary report paths are not durable evidence. Original input binding and
    # structured findings below are retained; use the original checker for reports.
    return result, checked


def findings(data):
    """Use report structure, not translated error wording, to choose the repair layer."""
    found = []
    if data.get('reason_code') == 'capture_not_ready':
        return [issue('capture', 'target_state_not_ready', [data.get('case', '?')])]
    if data.get('reason_code') == 'capture_command_failed':
        return [issue('capture', 'capture_command_needs_diagnosis')]
    if data.get('status') == 'blocked_inputs' or data.get('input_errors'):
        return [issue('capture', 'full_check_input_contract_unready')]
    if data.get('tool') == 'art_input_preflight' and not data.get('ready'):
        return [issue('capture', 'capture_contract_unready',
                      [s['id'] for s in (data.get('capture_round') or {}).get('cases', [])
                       if s.get('action') == 'recapture'])]
    prod = data.get('production')
    if isinstance(prod, dict) and prod.get('passed') is False:
        found.append(issue('production', 'producer_inputs_or_output_invalid',
                           [a.get('id', '?') for a in prod.get('assets', []) if a.get('passed') is False]))
    layout = data.get('layout', {})
    if layout.get('status') == 'error' or layout.get('extraction', {}).get('passed') is False:
        found.append(issue('capture', 'layout_adapter_unready'))
    slots = data.get('slots', {})
    if slots.get('error'):
        found.append(issue('capture', 'slot_checker_unready'))
    elif slots.get('passed') is False:
        found.append(issue('integration', 'visual_slot_failed',
                           [c.get('id', '?') for c in slots.get('cases', []) if c.get('passed') is False]))
    text = data.get('text', {})
    if text.get('status') == 'error':
        found.append(issue('capture', 'text_checker_unready'))
    elif text.get('passed') is False:
        found.append(issue('integration', 'text_geometry_failed',
                           [f.get('path', f.get('node', '?')) for f in text.get('findings', [])]))
    pages = data.get('pages', {})
    if pages.get('setup'):
        found.append(issue('capture', 'pixel_checker_setup_unready'))
    if pages.get('findings'):
        found.append(issue('visual', 'inspect_original_page_pixels'))
    rows = data.get('rows', [])
    if isinstance(rows, list):
        failed = [str(r.get('check', '?')) for r in rows if r.get('status') in
                  {'需处理', '缺采集', '未执行', '未测', '错误'}]
        if failed:
            found.append(issue('visual', 'full_art_findings_need_triage', failed))
    if (data.get('passed') is False or data.get('error') or data.get('status') == 'error') and not found:
        found.append(issue('unknown', 'inspect_failure_evidence'))
    return found


def capture_groups(states, ids):
    """Suggest batches only for the same declared action-plan identity, preserving original order.

    A recipe string is not a navigation proof. These groups never remove steps,
    restart commands, state setup or captures from the actual touch plan.
    """
    groups, previous_key = [], None
    for s in states:
        if s['id'] not in ids:
            continue
        key = ((s.get('planSha'), s.get('environment'), s.get('storageSha'),
                s.get('width'), s.get('height'), s.get('dpr')) if s.get('planSha') else ('single', s['id']))
        if not groups or key != previous_key:
            groups.append(dict(ids=[], viewport=[s.get('width'), s.get('height'), s.get('dpr')],
                               route_plan_sha256=s.get('planSha'), preserve_action_order=True))
        groups[-1]['ids'].append(s['id'])
        previous_key = key
    return groups


def resolved_capture_file(capture, dumps, capture_id):
    """Use owning collector originals when supplied; never copy or rewrite dumps."""
    name = 'capture-ui-dump-'+capture_id+'.json'
    originals = capture.get('resolved_dumps')
    if originals is None:
        return (Path(dumps)/name).resolve()
    if (not isinstance(originals, list) or any(not isinstance(p, str) or not Path(p).is_absolute()
                                             for p in originals)):
        raise ValueError('collector resolved_dumps must list absolute original files')
    matches = [Path(p).resolve() for p in originals if Path(p).name == name]
    if len(matches) != 1:
        raise ValueError('missing or ambiguous collector original for '+capture_id)
    return matches[0]


def first_piece_capture_current(data, links, capture, dumps):
    """Bind planning input to the existing collector's actual selected-case proofs.

    Other required cases may still be missing at this stage. No new proof or
    relaxed reuse rule is introduced; a first piece can only use original files
    the collector has classified fresh/reuse for the actual current export.
    """
    if not capture or capture.get('error') or not dumps:
        return False
    selected = data.get('selected_cases', [])
    if not selected or any(value not in links for value in selected):
        return False
    states = {row['id']: row for row in capture.get('cases', [])}
    ids = {links[value] for value in selected}
    if any(states.get(value, {}).get('action') not in ('fresh', 'reuse') for value in ids):
        return False
    try:
        expected = {resolved_capture_file(capture, dumps, value) for value in ids}
        files = {Path(row['file']).resolve() for row in data['input_binding']['documents']}
        return files == expected
    except (KeyError, TypeError, ValueError):
        return False


def plan(project, build=None, dumps=None, first_piece=None, diagnostics=(), previous=None, board=None):
    started = time.monotonic()
    project = Path(project).resolve()
    if not (project/'assets').is_dir():
        raise ValueError('not a Cocos project')
    visual = read(project/'docs/art/visual-slots.json', {'cases': []})
    policy = read(project/'docs/art/capture-plan.json', {'cases': []})
    links, problems = mapping(visual, policy)
    required = [s['id'] for s in policy['cases']]
    status = capture_check('status', project, Path(build).resolve()) if build else dict(
        suggested_action='unknown', reason_code='no_web_export_supplied')
    capture = None
    if build and dumps and status.get('suggested_action') == 'keep_round':
        command = 'verify' if any((Path(dumps)/name).is_file() for name in
                                  ('same-build-rounds.json', 'capture-inheritance.json')) else 'plan'
        capture = capture_check(command, project, Path(build).resolve(), Path(dumps).resolve())
    raw = read(first_piece) if first_piece else None
    captured = isinstance(raw, dict) and first_piece_capture_current(raw, links, capture, dumps)
    selected = first_piece_state(project, first_piece if captured else None,
                                 {c['id']: c for c in visual['cases']}, dumps, board)
    fp, report = selected if isinstance(selected, tuple) else (selected, None)
    fp['capture_verified'] = captured
    if first_piece and not captured:
        fp['reason'] = 'selected_original_captures_not_verified_for_current_export'
    if report and fp.get('current'):
        problems.extend(findings(report))
    diagnostic_paths, diagnostic_hashes = [], {}
    for path in diagnostics:
        data = read(path)
        if not isinstance(data, dict):
            raise ValueError('diagnostic must be an object')
        diagnostic_paths.append(str(Path(path).resolve()))
        diagnostic_hashes[str(Path(path).resolve())] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        problems.extend(findings(data))
    problems = sorted({encoded(x): x for x in problems}.values(), key=lambda x: encoded(x))
    actions = []
    def add(kind, reason, **fields):
        actions.append(dict(action=kind, reason=reason, **fields))
    layers = {p['layer'] for p in problems}
    if not required or not links or 'scope' in layers:
        add('complete_scope_mapping', 'Map actual consumers and the distinct visual/capture case IDs; do not shrink required coverage.')
    elif 'production' in layers:
        add('inspect_production_batch', 'Replay the affected producer/budget inputs before any build; a failure does not itself authorize image regeneration.')
    elif 'capture' in layers:
        add('repair_capture_contract', 'Confirm state, resources, coordinates and adapter; preserve valid cases and retry only failed ones.')
    elif 'unknown' in layers:
        add('inspect_failure_evidence', 'The failure layer is not established. Inspect original evidence before choosing a generation, integration, build or capture action.')
    elif layers:
        add('inspect_shared_integration_cause', 'Check original pixels versus actual binding, layout writers, inner regions and draw order; consolidate the proven shared repair before building.')
    elif status.get('suggested_action') == 'rebuild_web':
        add('build_web_once', 'The source changed while this Web export did not. Finish the current shared repair batch, then build once.')
    elif status.get('suggested_action') == 'verify_export_then_new_round':
        add('verify_export_then_new_round', 'Check the actual new export; both changed is not compiler provenance. Do not automatically build a second time.')
    elif status.get('suggested_action') == 'new_round':
        add('start_new_capture_round', 'Only matrix/collector changed; do not regenerate or rebuild source for this reason.')
    elif status.get('suggested_action') != 'keep_round':
        add('verify_initial_export_and_baseline', 'Unknown is not reusable. Establish the real initial source/export relationship and capture baseline.')
    elif not fp.get('current'):
        add('check_representative_first_piece', 'Use explicit first-piece cases for the narrowest/ largest/most layered uses. Missing or stale evidence does not approve a batch.',
            visual_cases=sorted(links), capture_case_mapping=links)
    elif not fp.get('passed'):
        add('inspect_first_piece_failure', 'The current representative is not ready; diagnose it before copying the method.')
    elif capture is None:
        add('capture_remaining_consumers', 'The method may be applied to the remaining consumers; every required state still needs its own evidence.', capture_cases=required)
    elif capture.get('error'):
        add('repair_capture_contract', 'Use the original collector error; never treat this as a request to redraw art.')
    else:
        todo = [c['id'] for c in capture.get('cases', []) if c.get('action') == 'recapture']
        if todo:
            add('capture_required_cases', 'Only the original collector decides fresh/reuse/recapture; shared changes may invalidate all states.',
                capture_cases=todo, groups=capture_groups(policy['cases'], todo))
        elif capture.get('ready') is True:
            from art_check_record import read as read_trial_art, trial_recheck_plan
            from feature_policy import board_of
            recorded = read_trial_art(project) if board_of(project, board)[0] == 'localize' else None
            if recorded and (recorded.get('last') or {}).get('status') in ('pass', 'fail'):
                try:
                    _, followup = trial_recheck_plan(project)
                except (ValueError, OSError, KeyError) as exc:
                    add('restore_trial_art_evidence', str(exc))
                else:
                    add('resume_trial_art', 'Resolve the recorded findings and run --resume-trial for pending and affected groups. '
                        'When the previous evidence remains current and no findings are open, continue to the formal preview.',
                        **followup)
            else:
                add('run_input_then_full_art_check', 'Run the original input preflight and full art gate. This plan is not visual approval.')
        else:
            add('repair_capture_contract', 'Capture readiness is incomplete or unknown.')
    symptom = hashlib.sha256(encoded(problems)).hexdigest() if problems else None
    state = {k: status.get(k) for k in ('source_hash', 'export_hash', 'matrix_hash', 'collector_hash')}
    signature = hashlib.sha256(encoded(dict(state=state, issues=problems, diagnostics=diagnostic_hashes,
                                             first_piece=fp.get('binding_sha256')))).hexdigest()
    repeats = 0
    if previous and problems and previous.get('schema') == 'art_iteration_plan.v1' and previous.get('project') == str(project):
        if previous.get('symptom_signature') == symptom:
            repeats = previous.get('same_symptom_count', 0) + 1
            actions.insert(0, dict(action='diagnose_repeated_cause', reason=(
                'The same failure family remains. Read its source/consumer evidence and change the repair hypothesis; '
                'do not repeat a full check, build or generation with no new information.'),
                identical_inputs=previous.get('input_signature') == signature))
    return dict(schema='art_iteration_plan.v1', project=str(project), advisory_only=True,
                full_art_passed=None, receipt_written=False, product_actions_executed=0,
                checker_replays=fp.get('checker_replays', 0),
                source_status=status, required_capture_cases=required, visual_to_capture=links,
                scope_basis='declared_only', consumer_discovery_proves_complete=False,
                first_piece=fp, remaining_visual_cases=fp.get('remaining_cases', sorted(links)),
                capture_plan=capture, issues=problems, next_actions=actions,
                input_signature=signature, symptom_signature=symptom, same_symptom_count=repeats,
                diagnostic_reports=diagnostic_paths, diagnostic_sha256=diagnostic_hashes,
                notes=['A first piece approves only a method for further integration, not all consumers.',
                       'No timeout, prior pass or plan can waive actual art/interaction checks.',
                       'Ordinary art/fonts outside production_assets still require their original production rules.',
                       'Read-only reference discovery is not a proof of complete dynamic consumers.'],
                elapsed_seconds=round(time.monotonic()-started, 6))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--build', type=Path)
    ap.add_argument('--dumps', type=Path)
    ap.add_argument('--first-piece', type=Path)
    ap.add_argument('--board', choices=['localize', 'remake'])
    ap.add_argument('--diagnostic', type=Path, action='append', default=[])
    ap.add_argument('--out', type=Path, help='default: project/.tiktok-kit/art-workflow/latest.json')
    a = ap.parse_args()
    project = a.project.resolve()
    output = (a.out or project/'.tiktok-kit/art-workflow/latest.json').resolve()
    if output.is_relative_to(project) and not output.is_relative_to(project/'.tiktok-kit/art-workflow'):
        ap.error('in-project plan output must be under .tiktok-kit/art-workflow')
    if any(output == value.resolve() for value in [a.first_piece, *a.diagnostic] if value):
        ap.error('plan output cannot overwrite an input report')
    try:
        previous = read(output)
        if output.exists() and (not isinstance(previous, dict)
                or previous.get('schema') != 'art_iteration_plan.v1' or previous.get('project') != str(project)):
            raise ValueError('existing output is not this project\'s previous art iteration plan')
        result = plan(project, a.build, a.dumps, a.first_piece, a.diagnostic, previous, a.board)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', dir=output.parent, delete=False, encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2); f.write('\n'); name=f.name
        os.replace(name, output)
        print(json.dumps(dict(plan=str(output), next_actions=result['next_actions'],
                              full_art_passed=None, elapsed_seconds=result['elapsed_seconds']), ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        ap.exit(1, str(exc)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
