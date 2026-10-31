#!/usr/bin/env python3
"""Generate/check the accumulated pre-scan checklist; never performs UI or uploads.

This checks coverage, postcondition fields, artifact hashes and current version
binding. It cannot establish that a screenshot or an operator's observation is true.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

from audit_mobile_input import snapshot
from logic_regressions import current_report as current_logic_report

SKILL = Path(__file__).resolve().parents[1]
CATALOG = SKILL / 'assets/known-issues.json'
# Two separate work boards (remake-core/references/two-boards.md, user 2026-10-21).
BOARDS = ('localize', 'remake')
DEFAULT_BOARD = 'remake'  # strictest; old reviews without a board keep their previous behaviour


ART_STYLES = ('original', 'remake')


def applies(item, board, art_style='original'):
    """Items tagged boards:["remake"] are not checked for a localize (Chinese-to-English) review, except items marked
    localize_remake_style when the user chose "按重塑画风重做" for a localize game (art_style remake, user 2026-10-21)."""
    if board in item.get('boards', BOARDS):
        return True
    return board == 'localize' and art_style == 'remake' and bool(item.get('localize_remake_style'))


def recorded_art_style(project):
    """docs/art-style.txt: original (英化 default) or remake (user said 按重塑画风重做)."""
    f = Path(project) / 'docs' / 'art-style.txt'
    value = f.read_text(encoding='utf-8').strip().lower() if f.is_file() else ''
    return value if value in ART_STYLES else None


# User 2026-10-24 (remake-core/references/check-stages.md): design and art are checked at their own stage, not again at the end.
# gate "design" = design_check.py (英化 1.5 / 重塑 round 1); gate "art" = art_check.py (英化 1.8 / 重塑 round 2 / art-redo).
# The final audit only checks the rest (loading, ads/rewards, storage, async, input/buttons, logic, no ad skip, build,
# English copy, flicker ...): items with an earlier gate are not expected in the review, and rows left there are ignored.
EARLIER_GATES = {'design': 'design_check.py', 'art': 'art_check.py'}


def final_gate(item):
    return item.get('gate', 'final') not in EARLIER_GATES


def earlier_stage_checks(catalog, board, art_style='original'):
    out = {}
    for x in catalog['items']:
        if applies(x, board, art_style) and not final_gate(x):
            out.setdefault(x['gate'], []).append(x['id'])
    return out


def project_records(project):
    """The decisions made at the design stage, read straight from the project (no design report needed at the end)."""
    from feature_policy import read_record
    from audit_level_plan import plan_mode
    skins = read_record(project, 'docs/modules.json').get('skins')
    return {'league': read_record(project, 'docs/league/decision.json').get('decision'),
            'features': read_record(project, 'docs/features.json'),
            'skins': skins.get('user_choice') if isinstance(skins, dict) else None,
            'level_mode': plan_mode(project)}


def auto_tools(item, board):
    by_board = item.get('auto_check_by_board', {})
    return by_board[board] if isinstance(by_board, dict) and board in by_board else item.get('auto_check', [])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique)


def tree_sha(root):
    root = Path(root)
    if not root.is_dir():
        raise ValueError('Missing build directory: ' + str(root))
    files = {}
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if p.name == '.DS_Store' or '__MACOSX' in rel.parts:
            continue
        if p.is_symlink():
            raise ValueError('Unexpected build symlink: ' + str(rel))
        if p.is_file():
            files[rel.as_posix()] = sha(p.read_bytes())
    if not files:
        raise ValueError('Empty build directory')
    return sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode())


def binding(args):
    return {'source_sha256': snapshot(args.project.resolve())[2],
            'native_tree_sha256': tree_sha(args.native),
            'web_tree_sha256': tree_sha(args.web), 'build_tag': args.build_tag}




def inventory_signature(entries):
    if not isinstance(entries, list):
        raise ValueError('Inventory snapshot must be an entry array')
    result = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not entry['id'].strip():
            raise ValueError('Inventory has an invalid entry ID')
        eid = entry['id']
        if eid in result:
            raise ValueError('Inventory has duplicate entry ID: ' + eid)
        group = entry.get('independent_group', '')
        if not isinstance(group, str):
            raise ValueError('independent_group must be a string')
        if entry.get('trigger') not in {'rewarded_video', 'platform_mission', 'direct'}:
            raise ValueError(eid + ': trigger must be rewarded_video/platform_mission/direct')
        if entry.get('persistence') not in {'durable', 'session'}:
            raise ValueError(eid + ': persistence must distinguish durable/session rewards')
        if entry['trigger'] in {'rewarded_video', 'platform_mission'} and (
                not isinstance(entry.get('api'), str) or not entry['api'].strip()):
            raise ValueError(eid + ': api must name the platform method this entry calls '
                                   '(e.g. getShortcutMissionReward, createRewardedVideoAd)')
        result[eid] = {key: entry.get(key, '') for key in
                       ('policy', 'binding', 'independent_group', 'trigger', 'persistence', 'api')}
    return result


def independent_pairs(entries):
    signature = inventory_signature(entries)
    return {left + '->' + right: {'claimed_entry': left, 'other_entry': right,
                                'independent_group': value['independent_group']}
            for left, value in signature.items() for right, other in signature.items()
            if left != right and value['independent_group'] and
               value['independent_group'] == other['independent_group']}


def result_failure(row):
    """Explicit failure wins over contradictory success fields (merged from the 2026-10-19 local edition)."""
    return (row.get('passed') is False or
            ('failed' in row and (type(row['failed']) is not int or row['failed'] != 0)) or
            row.get('status') in {'blocked', 'fail', 'failed', 'pending', 'limited', 'error'})


def result_cases(raw):
    cases = []
    for field in ('checks', 'rows', 'results'):
        values = raw.get(field, [])
        if not isinstance(values, list):
            raise ValueError('Raw cases must be arrays')
        cases.extend(row for row in values if isinstance(row, dict))
    named = [str(row.get('id', row.get('name', ''))) for row in cases]
    named = [value for value in named if value]
    if len(named) != len(set(named)):
        raise ValueError('Duplicate raw case ID')
    return cases


def visual_verdict(review, base, expected_binding):
    """Runtime faults only after user art approval; art review happens before trial.

    Check black screens, flicker and missing runtime resources, not approved
    typography, palette, layout, clarity or composition. Keep runtime evidence binding.
    """
    v = review.get('visual_verdict')
    if not isinstance(v, dict):
        return ['visual_verdict: missing GPT verdict on this build\'s contact sheets (make_contact_sheet.py)']
    errors = []
    if v.get('reviewer') != 'gpt':
        errors.append('visual_verdict: reviewer must be "gpt" (only a GPT/Codex session judges the screens)')
    ref = v.get('contact_sheets', {})
    try:
        if not isinstance(ref, dict) or not ref.get('path') or not ref.get('sha256'):
            raise ValueError('needs contact_sheets {path, sha256}')
        p = Path(ref['path'])
        if not p.is_absolute():
            p = base / p
        if not p.is_file() or sha(p.read_bytes()) != ref['sha256']:
            raise ValueError('contact-sheets.json missing or changed')
        manifest = load(p)
        if manifest.get('tool') != 'make_contact_sheet':
            raise ValueError('not a make_contact_sheet manifest')
        if manifest.get('binding') != expected_binding:
            raise ValueError('sheets belong to another build (run make_contact_sheet.py with --binding)')
        sheets = manifest.get('sheets', [])
        total = sum(len(s.get('items', [])) for s in sheets if isinstance(s, dict))
        if not sheets or total < 1 or total != manifest.get('total'):
            raise ValueError('sheets list is empty or inconsistent')
        for s in sheets:
            f = p.parent / str(s.get('file', ''))
            if not f.is_file() or sha(f.read_bytes()) != s.get('sha256'):
                raise ValueError('sheet image missing or changed: ' + str(s.get('file')))
        if v.get('images_reviewed') != total:
            raise ValueError('images_reviewed must equal the number of screenshots on the sheets')
    except (ValueError, OSError, TypeError, AttributeError) as e:
        errors.append('visual_verdict: ' + str(e))
    if v.get('verdict') != 'pass':
        errors.append('visual_verdict: verdict is not pass')
    if v.get('open_issues') not in ([], None) and v.get('open_issues') != 0:
        errors.append('visual_verdict: open screen issues remain')
    if len(' '.join(str(v.get('observed', '')).split())) < 15:
        errors.append('visual_verdict: write what was actually checked on the sheets')
    return errors


def evidence(refs, base, errors, label, expected_binding, require_current=False):
    if not isinstance(refs, list) or not refs:
        errors.append(label + ': missing evidence'); return
    current = 0
    roles = {'current_result', 'current_artifact', 'historical_reference', 'negative_control'}
    for ref in refs:
        if not isinstance(ref, dict) or not ref.get('path') or not ref.get('sha256'):
            errors.append(label + ': invalid evidence reference'); continue
        role = ref.get('role')
        if role not in roles:
            errors.append(label + ': missing or invalid evidence role'); continue
        p = Path(ref['path'])
        if not p.is_absolute():
            p = base / p
        if not p.is_file() or sha(p.read_bytes()) != ref['sha256']:
            errors.append(label + ': missing or changed evidence ' + str(p)); continue
        if role == 'current_result':
            try:
                result = load(p)
            except (ValueError, OSError):
                errors.append(label + ': current_result requires a JSON result wrapper'); continue
            if (not isinstance(result, dict) or result.get('schema') != 'known_issue_current_result.v1' or
                    result.get('binding') != expected_binding or result.get('status') != 'pass' or
                    type(result.get('failed')) is not int or result['failed'] != 0):
                errors.append(label + ': stale or failed current_result wrapper'); continue
            trace = result.get('execution', {})
            command = trace.get('command', []) if isinstance(trace, dict) else []
            if (not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command)
                    or type(trace.get('exit_code')) is not int or trace['exit_code'] != 0):
                errors.append(label + ': execution command and zero exit code required'); continue
            traced = {}
            for field in ('tool', 'raw_report'):
                source = trace.get(field, {})
                if not isinstance(source, dict) or not source.get('path') or not source.get('sha256'):
                    errors.append(label + ': missing execution ' + field); continue
                origin = Path(source['path'])
                if not origin.is_absolute():
                    origin = p.parent / origin
                if not origin.is_file() or sha(origin.read_bytes()) != source['sha256']:
                    errors.append(label + ': missing or changed execution ' + field); continue
                traced[field] = origin
            if len(traced) != 2:
                continue
            if not any(token in {str(traced['tool']), trace['tool']['path']} for token in command):
                errors.append(label + ': execution command does not identify the recorded tool'); continue
            try:
                raw = load(traced['raw_report'])
                if not isinstance(raw, dict):
                    raise ValueError('Raw execution result is not an object')
                raw_binding = raw.get('binding', {})
                if (not isinstance(raw_binding, dict) or 'source_sha256' not in raw_binding or
                        not {'native_tree_sha256', 'web_tree_sha256'} & set(raw_binding) or
                        any(raw_binding[k] != expected_binding[k] for k in set(raw_binding) & set(expected_binding))):
                    raise ValueError('Raw execution inputs are missing or stale')
                success = (raw.get('passed') is True or raw.get('status') in {'pass', 'passed', 'clear', 'success'} or
                           type(raw.get('failed')) is int and raw['failed'] == 0)
                cases = result_cases(raw)
                if not success or result_failure(raw) or any(result_failure(row) for row in cases):
                    raise ValueError('Raw execution report is failed, pending or unrecognized')
            except (ValueError, OSError, TypeError):
                errors.append(label + ': raw execution report does not support pass'); continue
            current += 1
        elif role == 'current_artifact':
            # An explicit operator assertion of artifact provenance, not proof of
            # image truth or execution. Read the original artifact during review.
            if ref.get('binding') != expected_binding:
                errors.append(label + ': current_artifact requires current build binding'); continue
            if p.suffix.lower() == '.json':
                try:
                    artifact = load(p)
                except ValueError:
                    errors.append(label + ': invalid JSON artifact'); continue
                if isinstance(artifact, dict) and any(key in artifact for key in ('status', 'passed', 'failed')):
                    errors.append(label + ': execution reports require current_result, not current_artifact'); continue
            current += 1
    if require_current and not current:
        errors.append(label + ': historical/negative evidence alone cannot support current pass')


def auto_reports(item, row, base, errors, expected_binding, board=DEFAULT_BOARD):
    """Each automatic tool named by the catalog must have a current, passing, unedited report."""
    refs = row.get('auto_reports', [])
    if not isinstance(refs, list):
        refs = []
    for tool in auto_tools(item, board):
        ok = False
        for ref in refs:
            if not isinstance(ref, dict) or not ref.get('path') or not ref.get('sha256'):
                continue
            p = Path(ref['path'])
            if not p.is_absolute():
                p = base / p
            try:
                if not p.is_file() or sha(p.read_bytes()) != ref['sha256']:
                    continue
                report = load(p)
            except (ValueError, OSError):
                continue
            if not isinstance(report, dict) or report.get('tool') != tool:
                continue
            if tool in {'audit_page_readiness', 'audit_loading_recovery'} and report.get('stage') != 'runtime':
                continue  # Static preflight is never page-entry acceptance.
            if tool == 'logic_check' and not current_logic_report(report, p.parent):
                continue  # F01-F20 alone, stale cases or changed raw evidence cannot pass LOGIC-01.
            if tool == 'audit_native_storage_contract':
                try:
                    from audit_native_storage_contract import CASES, validate as validate_storage, replay as replay_storage
                    trace_path = Path(report['trace'])
                    native_path = Path(report['native'])
                    if (report.get('policy_version') != (2 if load(trace_path).get('schema') == 'native_storage_trace.v2' else 1) or report.get('required_cases') != list(CASES) or
                            sha(trace_path.read_bytes()) != report.get('trace_sha256') or
                            tree_sha(native_path) != expected_binding['native_tree_sha256'] or
                            validate_storage(load(trace_path), native_path, expected_binding) or
                            replay_storage(load(trace_path))):
                        continue
                except (KeyError, ValueError, TypeError, OSError):
                    continue
            if tool in {'audit_game_modules','audit_optional_features','audit_acquisition_progression'} and report.get('implementation') == 'production_js':
                try:
                    from maintenance_scope import audit_scope
                    scope_file = Path(report['maintenance_scope'])
                    scope, scope_errors = audit_scope(scope_file, report['project'], expected_binding)
                    if sha(scope_file.read_bytes()) != report.get('maintenance_scope_sha256') or scope_errors:
                        continue
                    if tool == 'audit_acquisition_progression' and 'collection' not in scope.get('existing_features',[]):
                        continue
                except (KeyError,ValueError,TypeError,OSError):
                    continue
            if tool == 'test_writer_refusal':
                ids = {case.get('id') for case in report.get('checks', []) if isinstance(case, dict) and case.get('passed') is True}
                if not {'missing_review', 'failed_check', 'stale_binding', 'missing_storage', 'normal'} <= ids:
                    continue
            if tool == 'audit_loading_recovery':
                from audit_loading_recovery import SCENARIOS, POLICY_VERSION
                if report.get('policy_version') != POLICY_VERSION or type(report.get('checked')) is not int or report['checked'] < len(SCENARIOS):
                    continue  # Old ten-case passes cannot cover the final font/clock regressions.
                try:
                    from audit_loading_recovery import validate as validate_recovery
                    runtime_path = Path(report['runtime_file'])
                    if not runtime_path.is_absolute():
                        runtime_path = p.parent / runtime_path
                    if sha(runtime_path.read_bytes()) != report.get('runtime_sha256') or validate_recovery(load(runtime_path), expected_binding, runtime_path.parent):
                        continue
                except (KeyError, ValueError, TypeError, OSError):
                    continue  # A stamped pass is not executable, current evidence.
            if tool == 'audit_startup_contract':
                from audit_startup_contract import validate_runtime_report
                if validate_runtime_report(report, expected_binding):
                    continue  # Source-only or static legacy passes cannot satisfy final LOAD-01.
            if tool == 'audit_startup_loading':
                from audit_startup_loading import validate_report as validate_startup_report
                if validate_startup_report(report, expected_binding):
                    continue
            checked = report.get('checked')
            if (report.get('binding') == expected_binding and report.get('passed') is True and
                    report.get('failed') == 0 and type(checked) is int and
                    (checked >= 1 or tool == 'audit_audio_sources')):
                ok = True
                break
        if not ok:
            errors.append(item['id'] + ': automatic check ' + tool +
                          ' needs a current passing report in auto_reports (run it with --binding on this build)')


NEGATIVE_SCHEMA = 'known_issue_negative_control.v1'


def calibration(row, base, errors, label):
    """Monkey Dash 2026-10-21: a check that never failed on a known-bad version proves nothing.
    Needs a negative_control run of the SAME tool (same SHA) as a current_result in this row."""
    refs = row.get('evidence') if isinstance(row.get('evidence'), list) else []
    current_tools, negatives = set(), []
    for ref in refs:
        if not isinstance(ref, dict) or not ref.get('path') or not ref.get('sha256'):
            continue
        path = Path(ref['path'])
        if not path.is_absolute():
            path = base / path
        try:
            if not path.is_file() or sha(path.read_bytes()) != ref['sha256']:
                continue
            data = load(path)
        except (ValueError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        if ref.get('role') == 'current_result':
            tool = (data.get('execution') or {}).get('tool') if isinstance(data.get('execution'), dict) else None
            if isinstance(tool, dict) and tool.get('sha256'):
                current_tools.add(tool['sha256'])
        elif ref.get('role') == 'negative_control':
            negatives.append((path, data))
    for path, data in negatives:
        tool = data.get('tool') if isinstance(data.get('tool'), dict) else {}
        origin = Path(str(tool.get('path', '')))
        if not origin.is_absolute():
            origin = path.parent / origin
        if (data.get('schema') == NEGATIVE_SCHEMA and len(str(data.get('mutant', '')).strip()) >= 4 and
                data.get('status') in {'fail', 'failed'} and type(data.get('failed')) is int and data['failed'] > 0 and
                tool.get('sha256') in current_tools and origin.is_file() and sha(origin.read_bytes()) == tool['sha256']):
            return
    errors.append(label + ': needs a known-bad run of the same check that failed (negative_control, schema ' +
                  NEGATIVE_SCHEMA + ', same tool SHA as a current_result in this row)')


def current_report(row, base, expected_binding, tool):
    """The row's unedited auto report of `tool` for this build, or None."""
    for ref in row.get('auto_reports', []) if isinstance(row.get('auto_reports'), list) else []:
        if not isinstance(ref, dict) or not ref.get('path'):
            continue
        path = Path(ref['path'])
        if not path.is_absolute():
            path = base / path
        try:
            if not path.is_file() or sha(path.read_bytes()) != ref.get('sha256'):
                continue
            data = load(path)
        except (ValueError, OSError):
            continue
        if isinstance(data, dict) and data.get('tool') == tool and data.get('binding') == expected_binding:
            return data
    return None


def discovered_apis(row, base, expected_binding):
    """Reward APIs that audit_async_contracts.py found in code/Native for this build, or None."""
    for ref in row.get('auto_reports', []) if isinstance(row.get('auto_reports'), list) else []:
        if not isinstance(ref, dict) or not ref.get('path'):
            continue
        path = Path(ref['path'])
        if not path.is_absolute():
            path = base / path
        try:
            if not path.is_file() or sha(path.read_bytes()) != ref.get('sha256'):
                continue
            data = load(path)
        except (ValueError, OSError):
            continue
        if isinstance(data, dict) and data.get('tool') == 'audit_async_contracts' and data.get('binding') == expected_binding:
            apis = data.get('reward_apis', [])
            return {x for x in apis if isinstance(x, str)} if isinstance(apis, list) else set()
    return None


def spot_check(review, base, expected_binding, applicable_ids, declared):
    """User 2026-10-21: tests may run on a cheaper AI; GPT must re-run the automatic checks and redo >= 3 flows itself."""
    v = review.get('gpt_spot_check')
    if not isinstance(v, dict):
        return ['gpt_spot_check: tests were run by ' + str(review.get('test_executor')) + '; GPT must re-run the automatic '
                'checks and redo at least 3 flows itself before anything passes']
    errors = []
    if v.get('reviewer') != 'gpt':
        errors.append('gpt_spot_check: reviewer must be "gpt"')
    if v.get('code_changes_reviewed') is not True or not str(v.get('locked_commit', '')).strip():
        errors.append('gpt_spot_check: GPT must read every code change the test AI made since the lock '
                      '(git diff <locked_commit>..HEAD): set locked_commit and code_changes_reviewed: true')
    if v.get('rerun_auto_checks') is not True:
        errors.append('gpt_spot_check: GPT must re-run every automatic check script itself (rerun_auto_checks: true)')
    flows = v.get('flows')
    flows = [f for f in flows if isinstance(f, dict)] if isinstance(flows, list) else []
    if len(flows) < 3:
        errors.append('gpt_spot_check: redo at least 3 flows (one ad entry, one platform task if any, one free restart)')
    texts = set()
    for f in flows:
        cid = f.get('check_id')
        label = 'gpt_spot_check/' + str(cid)
        if cid not in applicable_ids:
            errors.append(label + ': unknown or not applicable check ID'); continue
        text = ' '.join(str(f.get('observed', '')).split())
        if len(text) < 15 or text in texts:
            errors.append(label + ': write what GPT itself saw (own text per flow)')
        texts.add(text)
        evidence(f.get('evidence'), base, errors, label, expected_binding, require_current=True)
    ids = {f.get('check_id') for f in flows}
    if any(e.get('trigger') == 'rewarded_video' for e in declared) and not any(str(i).startswith(('AD-', 'CLAIM-')) for i in ids):
        errors.append('gpt_spot_check: include one rewarded-ad flow (AD-* or CLAIM-*)')
    # v7.5 (Mabel 1.2): every TikTok game has add-to-desktop and profile revisit, declared or not.
    if not ids & {'GROW-01', 'ASYNC-01', 'LIFE-02'}:
        errors.append('gpt_spot_check: include one platform-task leave-and-return flow (GROW-01/ASYNC-01/LIFE-02)')
    if v.get('disagreements') not in ([], None):
        errors.append('gpt_spot_check: GPT found records that do not match; re-test that whole category and clear the list')
    return errors


def check_row(row, base, errors, label, expected_binding):
    if not isinstance(row, dict):
        errors.append(label + ': review row must be an object'); return
    if row.get('status') == 'not_applicable':
        if not str(row.get('reason', '')).strip():
            errors.append(label + ': not-applicable requires a concrete reason')
        evidence(row.get('evidence'), base, errors, label, expected_binding, require_current=True)
        return
    if row.get('status') != 'pass':
        errors.append(label + ': ' + str(row.get('status', 'missing'))); return
    if not str(row.get('observed', '')).strip():
        errors.append(label + ': missing actual observation')
    if row.get('layer') not in {'source', 'native', 'gui_mouse', 'gui_touch', 'device', 'mixed'}:
        errors.append(label + ': missing or invalid evidence layer')
    evidence(row.get('evidence'), base, errors, label, expected_binding, require_current=row.get('status') == 'pass')


def audit(args):
    from audit_no_social_features import audit as audit_no_social
    review = load(args.review)
    import project_qa
    policy = project_qa.review_policy(args, review)
    audit_args = project_qa.adjusted_args(args, policy) if policy else args
    social_project = args.project.resolve()
    if policy and policy.get('legacy_context'):
        audit_args, social_project = project_qa.invoke(policy, 'prepare_context', args)
    social = audit_no_social(social_project, native=args.native, web=args.web)
    if not social['passed']:
        return {'status': 'blocked', 'stage': args.stage, 'binding': binding(audit_args), 'errors': ['Forbidden sharing/ranking feature present'], 'no_social_features': social}
    catalog = load(CATALOG); errors = []
    if not isinstance(review, dict):
        raise ValueError('Review must be an object')
    if policy:
        extension = project_qa.invoke(policy, 'audit', audit_args, review, binding, catalog)
        if policy.get('legacy_coverage_override'):
            return extension
        if not isinstance(extension, dict) or extension.get('status') not in ('pass','passed','ready'):
            return {'status':'blocked','stage':args.stage,'errors':['Project review supplement failed'],'extension':extension}
    if review.get('schema') == 'export_maintenance_review.v1':
        import audit_export_maintenance
        return audit_export_maintenance.audit(args)
    if review.get('schema') != 3:
        errors.append('Review schema changed; declare reward trigger/persistence and review added states')
    board = review.get('board', DEFAULT_BOARD)
    if board not in BOARDS:
        errors.append('Review board must be localize or remake'); board = DEFAULT_BOARD
    if getattr(args, 'board', None) and args.board != board:
        errors.append('Review was created for board ' + board + ', not ' + args.board +
                      '; the board is decided once per game (docs/board.txt)')
    art_style = review.get('art_style', 'original')
    if art_style not in ART_STYLES:
        errors.append('Review art_style must be original or remake'); art_style = 'original'
    on_disk = recorded_art_style(args.project)
    if on_disk and on_disk != art_style:
        errors.append('docs/art-style.txt says ' + on_disk + ' but the review was made for ' + art_style +
                      ' (user chose 按重塑画风重做: make a new review with --art-style remake)')
    expected_binding = binding(args)
    if review.get('catalog_sha256') != sha(CATALOG.read_bytes()):
        errors.append('Checklist catalog changed; review added/changed checks')
    if review.get('binding') != expected_binding:
        errors.append('Source/Native/Web/build tag differs from the reviewed inputs')
    base = args.review.resolve().parent
    executor_exit = bool(getattr(args, 'executor_exit', False))
    left_for_codex = []
    rows = review.get('checks', {})
    if not isinstance(rows, dict):
        raise ValueError('checks must be an ID-keyed object')
    all_ids = {x['id'] for x in catalog['items']}
    expected = {x['id'] for x in catalog['items'] if applies(x, board, art_style) and final_gate(x)}
    declared = review.get('reward_entries', [])
    if not isinstance(declared, list):
        declared = []
    declared = [entry for entry in declared if isinstance(entry, dict)]
    required_checks = set()
    if any(entry.get('trigger') == 'rewarded_video' for entry in declared):
        required_checks.update({'AD-01', 'AD-02', 'AD-03', 'AD-04', 'AD-05'})
    if declared:
        required_checks.update({'CLAIM-01', 'CLAIM-02', 'CLAIM-03', 'CLAIM-04', 'CLAIM-05', 'CLAIM-06'})
    # v7.5 (Mabel 1.2 / Fangkuai 2): add-to-desktop and profile revisit are required for every TikTok game, so GROW-01
    # can no longer be marked not_applicable because no reward entry declared trigger=platform_mission.
    required_checks.add('GROW-01')
    if any(entry.get('trigger') == 'platform_mission' for entry in declared):
        # Monkey Dash 2026-10-20: a declared platform task must run its own leave/return checks.
        required_checks.update({'GROW-01', 'LIFE-02'})
    if any(entry.get('policy') == 'daily' for entry in declared):
        required_checks.add('STATE-03')
    if any(entry.get('persistence') == 'durable' for entry in declared):
        required_checks.update({'STATE-01', 'STATE-02'})
    if (expected - set(rows)) | (set(rows) - all_ids):
        errors.append('Missing/unknown catalog IDs: ' + str(sorted((expected - set(rows)) | (set(rows) - all_ids))))
    from feature_policy import economy_disabled
    module_report = current_report(rows.get('MOD-01', {}), base, expected_binding, 'audit_game_modules')
    no_collection = economy_disabled(args.project, module_report)
    maintenance_scope = None
    if module_report and module_report.get('implementation') == 'production_js':
        try:
            from maintenance_scope import audit_scope
            scope_file = Path(module_report['maintenance_scope'])
            if sha(scope_file.read_bytes()) == module_report.get('maintenance_scope_sha256'):
                maintenance_scope, scope_errors = audit_scope(scope_file, args.project, expected_binding)
                if scope_errors:errors.extend('maintenance scope: '+x for x in scope_errors)
        except (KeyError,ValueError,TypeError,OSError) as exc:
            errors.append('maintenance scope: '+str(exc))

    for item in catalog['items']:
        if not applies(item, board, art_style) or not final_gate(item):
            continue
        if args.stage == 'pre_scan' and item['phase'] in {'device', 'post_package'}:
            continue
        if args.stage == 'post_package' and item['phase'] == 'device':
            continue
        if item.get('always_applicable') and rows.get(item['id'], {}).get('status') == 'not_applicable':
            errors.append(item['id'] + ': baseline/build/test integrity checks cannot be waived as not-applicable')
        if board in item.get('required_boards', []) and rows.get(item['id'], {}).get('status') == 'not_applicable' and not (no_collection and item['id'] in ('ECON-01', 'ECON-02')):
            errors.append(item['id'] + ': required for ' + board + ' (英化＋优化 adds this to every game)')
        if item['id'] in required_checks and rows.get(item['id'], {}).get('status') == 'not_applicable':
            errors.append(item['id'] + (': required for every TikTok game (add-to-desktop and profile revisit)'
                                        if item['id'] == 'GROW-01' else ': required by declared reward mechanisms'))
        # User 2026-10-22: the test stage ends only when everything is done except what only Codex may fill.
        if executor_exit and item.get('reviewer') and rows.get(item['id'], {}).get('status') in (None, 'pending'):
            left_for_codex.append(item['id'])
            continue
        check_row(rows.get(item['id'], {}), base, errors, item['id'], expected_binding)
        row = rows.get(item['id'], {})
        if row.get('status') == 'pass' and auto_tools(item, board):
            auto_reports(item, row, base, errors, expected_binding, board)
        if row.get('status') == 'pass' and item.get('requires_gui'):
            layers = row.get('layers', []) if row.get('layer') == 'mixed' else [row.get('layer')]
            if not isinstance(layers, list) or not set(layers) & {'gui_mouse', 'gui_touch', 'device'}:
                errors.append(item['id'] + ': current GUI/device observation required; source/HTTP alone is insufficient')
        required_observations = (item.get('maintenance_observations') if maintenance_scope and item.get('maintenance_observations') else item.get('required_observations'))
        if row.get('status') == 'pass' and required_observations:
            observations = row.get('observations', {})
            if not isinstance(observations, dict) or any(not observations.get(k) for k in required_observations):
                errors.append(item['id'] + ': missing required observations ' + ', '.join(required_observations))
        if row.get('status') == 'pass' and item.get('requires_negative_control'):
            calibration(row, base, errors, item['id'])
        if row.get('status') == 'pass' and item.get('reviewer') and row.get('reviewer') != item['reviewer']:
            errors.append(item['id'] + ': only a ' + item['reviewer'].upper() + ' session can mark this pass (row reviewer = "' +
                          item['reviewer'] + '")')
    executor = str(review.get('test_executor') or '').strip()
    if executor_exit:
        left_for_codex += ['gpt_spot_check', 'visual_verdict']
    elif executor and executor.lower() not in {'gpt', 'codex'}:
        errors.extend(spot_check(review, base, expected_binding, expected, declared))
    # Monkey Dash 2026-10-21: a mechanism found in code must produce its own checks.
    async_row = rows.get('ASYNC-01')
    if any(x['id'] == 'ASYNC-01' and applies(x, board, art_style) for x in catalog['items']) and isinstance(async_row, dict) \
            and async_row.get('status') == 'pass':
        found = discovered_apis(async_row, base, expected_binding)
        declared_apis = {str(e.get('api', '')).strip() for e in declared}
        if found is None:
            errors.append('ASYNC-01: needs the audit_async_contracts report of this build to list the reward APIs in code')
        else:
            missing = sorted(api for api in found if api not in declared_apis)
            if missing:
                errors.append('Reward APIs found in code without a declared reward entry (api field): ' + ', '.join(missing))
    # Features decided at the design stage must be tested in the browser (user 2026-10-21/22/23). Since 2026-10-24 the
    # decisions are read from the project records (design_check.py checked them earlier), not from MOD-01/RANK-01 rows.
    rec = project_records(args.project)
    if board == 'remake' and rec['league'] in ('add', 'keep_original') and rows.get('RANK-02', {}).get('status') == 'not_applicable':
        errors.append('RANK-02: this game has a Weekly League (docs/league/decision.json decision ' + str(rec['league']) +
                      '); test it in the browser, it cannot be marked not applicable')
    for key, cid in (('skin_bonus', 'FEAT-01'), ('daily_checkin', 'FEAT-02')):
        if rec['features'].get(key) is True and rows.get(cid, {}).get('status') == 'not_applicable':
            errors.append(cid + ': the user chose this feature (docs/features.json ' + key + ': true); test it, it cannot be not applicable')
    if rec['skins'] is True and rows.get('FEAT-01', {}).get('status') == 'not_applicable':
        errors.append('FEAT-01: this game has the skin module (docs/modules.json skins.user_choice yes); test it, '
                      'it cannot be not applicable')
    if rec['level_mode'] == 'levels' and rows.get('LEVEL-02', {}).get('status') == 'not_applicable':
        errors.append('LEVEL-02: this is a level game (level_plan.json mode levels); test the map, bonus and limited levels, '
                      'it cannot be not applicable')
    if not executor_exit and any(item.get('visual_verdict') and applies(item, board, art_style) and final_gate(item) and isinstance(rows.get(item['id']), dict) and
           rows[item['id']].get('status') == 'pass' for item in catalog['items']):
        errors.extend(visual_verdict(review, base, expected_binding))
    # Copied text is not evidence: each check must describe its own observation (2026-10-20 postmortem).
    seen_text = {}
    for item in catalog['items']:
        row = rows.get(item['id'], {})
        if not applies(item, board, art_style) or not final_gate(item) or not isinstance(row, dict) or row.get('status') != 'pass':
            continue
        text = ' '.join(str(row.get('observed', '')).split())
        if len(text) >= 15:
            seen_text.setdefault(text, []).append(item['id'])
        obs = row.get('observations', {})
        if isinstance(obs, dict):
            values = [' '.join(str(v).split()) for v in obs.values() if str(v).strip()]
            if len(values) >= 2 and len(set(values)) < len(values):
                errors.append(item['id'] + ': observation fields repeat the same text; describe each one separately')
    for text, ids in seen_text.items():
        if len(ids) >= 2:
            errors.append('Same observed text copied into ' + ', '.join(ids) + '; each check needs its own observation')
    inventory = review.get('reward_entries')
    if not isinstance(inventory, list):
        errors.append('reward_entries must be an actual entry inventory'); inventory = []
    if review.get('inventory_complete') is not True:
        errors.append('Actual prefab/scene/runtime entry inventory has not been completed')
    evidence(review.get('inventory_evidence'), base, errors, 'inventory', expected_binding, require_current=True)
    captured = []
    try:
        ref = review.get('inventory_snapshot', {})
        relative = Path(ref.get('path', ''))
        if relative.is_absolute() or len(relative.parts) != 1:
            raise ValueError('Inventory snapshot must be a local sidecar file')
        snapshot_path = base / relative
        if not snapshot_path.is_file() or sha(snapshot_path.read_bytes()) != ref.get('sha256'):
            raise ValueError('Inventory snapshot is missing or changed')
        snapshot_record = load(snapshot_path)
        if snapshot_record.get('binding') != expected_binding:
            raise ValueError('Inventory snapshot belongs to another build')
        captured = snapshot_record.get('entries')
        if inventory_signature(captured) != inventory_signature(inventory):
            raise ValueError('Review entry IDs/policy/binding/independent_group differ from captured inventory')
    except (ValueError, OSError, TypeError, AttributeError) as error:
        errors.append('inventory snapshot: ' + str(error))
    try:
        pairs = independent_pairs(captured)
        checks = review.get('independent_reward_checks', {})
        if not isinstance(checks, dict) or set(checks) != set(pairs):
            errors.append('Independent reward cross-state checks are missing or unknown')
        else:
            for key, pair in pairs.items():
                row = checks[key]; label = 'independent/' + key
                if row.get('status') != 'pass':
                    errors.append(label + ': declared independent group requires a passing cross-state observation')
                if any(row.get(field) != value for field, value in pair.items()):
                    errors.append(label + ': cross-state identities differ from captured inventory')
                check_row(row, base, errors, label, expected_binding)
                post = row.get('postconditions', {})
                if row.get('status') == 'pass' and any(post.get(field) is not True for field in
                    ('claimed_entry_applied_once', 'other_reward_still_eligible', 'other_reward_unchanged')):
                    errors.append(label + ': claim A then verify independent B eligibility and unchanged model')
    except (ValueError, TypeError, AttributeError) as error:
        errors.append('independent reward checks: ' + str(error))
    seen = set()
    for entry in inventory:
        if not isinstance(entry, dict):
            errors.append('reward entry must be an object'); continue
        eid = str(entry.get('id', ''))
        if not eid or eid in seen:
            errors.append('Empty or duplicate reward entry ID')
        seen.add(eid)
        if entry.get('policy') not in catalog['reward_policy_kinds']:
            errors.append(eid + ': reward policy must distinguish once/daily/per-run/repeatable/navigation')
        if not entry.get('reach_steps') or not entry.get('binding'):
            errors.append(eid + ': missing reach steps or actual button binding')
        states = entry.get('states', {})
        if set(states) != set(catalog['reward_states']):
            errors.append(eid + ': missing/unknown reward states')
        for state in catalog['reward_states']:
            row = states.get(state, {}); label = eid + '/' + state
            required = {'eligible', 'completed', 'apply_or_consume'}
            if entry.get('trigger') == 'rewarded_video':
                required |= {'pending', 'cancelled', 'error', 'timeout', 'duplicate_or_late_callback', 'return_contracts'}
            if entry.get('trigger') == 'platform_mission':
                required |= {'pending', 'error', 'timeout', 'duplicate_or_late_callback', 'leave_and_return', 'return_contracts'}
            if entry.get('persistence') == 'durable':
                required.add('save_failure_retry')
            if state in required and row.get('status') == 'not_applicable':
                errors.append(label + ': required for the declared reward mechanism')
            check_row(row, base, errors, label, expected_binding)
            if row.get('status') != 'pass':
                continue
            if state == 'completed':
                post = row.get('postconditions', {})
                if post.get('reward_applied_once') is not True or post.get('model_updated') is not True:
                    errors.append(label + ': reward and model must both be checked')
                if any(post.get(field) is not True for field in
                       ('reward_identity_verified', 'current_reward_display_consistent',
                        'success_feedback_consistent')):
                    errors.append(label + ': verify this reward identity/display and consistent committed-success feedback')
                outcome = post.get('presentation')
                valid = {'hidden', 'disabled_claimed', 'navigated'}
                if entry.get('policy') == 'repeatable':
                    valid.add('next_eligible')
                if entry.get('policy') == 'navigation_reward':
                    valid = {'claimed_navigation', 'retained_navigation', 'navigated'}
                if outcome not in valid:
                    errors.append(label + ': no valid claimed button presentation for this policy')
                if outcome == 'hidden' and post.get('button_visible') is not False:
                    errors.append(label + ': hidden requires actual button_visible=false')
                if outcome == 'disabled_claimed' and (post.get('interactable') is not False or not post.get('claimed_text_visible')):
                    errors.append(label + ': disabled must also visibly say claimed')
                if outcome == 'navigated' and post.get('claim_page_left') is not True:
                    errors.append(label + ': claim page was not confirmed closed')
                if outcome == 'claimed_navigation' and post.get('claimed_text_visible') is not True:
                    errors.append(label + ': retained navigation must show claimed state')
                if outcome == 'retained_navigation' and (post.get('navigation_available') is not True or
                                                        post.get('claim_state_visible') is not True):
                    errors.append(label + ': navigation and visible claim state must be checked separately')
            elif state == 'pending':
                post = row.get('postconditions', {})
                if post.get('checking_state_visible') is not True or post.get('bounded_wait') is not True:
                    errors.append(label + ': show a visible checking/waiting state and end the wait within a bounded time')
                if entry.get('trigger') in {'rewarded_video', 'platform_mission'} and any(
                        post.get(field) is not True for field in ('sdk_and_timer_held_recovers', 'retry_after_recovery_works')):
                    errors.append(label + ': hold the SDK result AND the original timeout callback; the screen must still end the wait '
                                          'and a real-touch retry must work (having timeout code is not proof)')
            elif state == 'return_contracts':
                post = row.get('postconditions', {})
                channels = post.get('channels_tested')
                channels = set(channels) if isinstance(channels, list) else set()
                needed = {'callback', 'promise', 'both', 'void_or_incomplete', 'reject_or_throw'}
                if entry.get('trigger') == 'rewarded_video':
                    needed = {'event', 'promise', 'reject_or_throw'}
                if not needed <= channels:
                    errors.append(label + ': return channels not all tested; missing ' + ', '.join(sorted(needed - channels)))
                if any(post.get(field) is not True for field in
                       ('each_channel_settles_once', 'non_eligible_results_no_reward', 'every_result_visible_end_state',
                        'test_double_supports_each_channel')):
                    errors.append(label + ': each return channel must reach one single settle with a visible end state, '
                                          'and the SDK test double must be able to answer through each channel')
            elif state == 'leave_and_return':
                post = row.get('postconditions', {})
                if any(post.get(field) is not True for field in
                       ('stale_request_invalidated', 'new_check_started', 'late_result_ignored', 'visible_result_feedback')):
                    errors.append(label + ': leave the game while a check is pending, return, and verify the old check is dropped, '
                                          'a new check runs, the late old result changes nothing and the player sees the result')
            elif state in {'cancelled', 'error', 'timeout'}:
                post = row.get('postconditions', {})
                if post.get('reward_delta_zero') is not True or post.get('can_retry_or_exit') is not True:
                    errors.append(label + ': check no reward and recovery, not just request failure')
                if post.get('failure_feedback_visible') is not True:
                    errors.append(label + ': the player must see a message for this result; a silent return looks like a dead button')
                if entry.get('trigger') == 'rewarded_video':
                    if post.get('no_automatic_replay') is not True:
                        errors.append(label + ': explicit retries only; no automatic replay')
                    if state == 'error' and post.get('terminal_failure_retry_available') is not True:
                        errors.append(label + ': SDK terminal failure must permit a later explicit retry, exit alone is insufficient')
                    if state == 'timeout' and post.get('unconfirmed_session_not_reopened') is not True:
                        errors.append(label + ': business timeout must not reopen an unconfirmed SDK session')
            elif state in {'reopen', 'reload', 'duplicate_or_late_callback'}:
                post = row.get('postconditions', {})
                if post.get('no_extra_reward_or_request') is not True:
                    errors.append(label + ': missing repeat/persistence postcondition')
                if state in {'reopen', 'reload'} and post.get('model_and_presentation_consistent') is not True:
                    errors.append(label + ': verify model and visible state after reopening/reloading')
            elif state == 'save_failure_retry':
                post = row.get('postconditions', {})
                fields = ('same_transaction_retried', 'no_additional_ad_request',
                          'reward_applied_once', 'commit_readback_ambiguity_checked',
                          'no_premature_success_ui', 'proof_target_preserved')
                if any(post.get(field) is not True for field in fields):
                    errors.append(label + ': verify the same completed proof, no replay, uncertain commit and exactly-once saving')
                if post.get('recovery_scope') not in {'process_only', 'durable_restart'}:
                    errors.append(label + ': declare process_only or durable_restart recovery scope')
            elif state == 'apply_or_consume':
                post = row.get('postconditions', {})
                if any(post.get(field) is not True for field in
                       ('actual_effect_verified', 'correct_target', 'quantity_and_effect_consistent',
                        'ownership_and_usage_distinguished', 'related_views_consistent')):
                    errors.append(label + ': verify actual usable reward/effect and matching quantity, not balance alone')
    if executor_exit:
        return {'status': 'test_stage_complete' if not errors else 'test_stage_incomplete', 'stage': args.stage, 'board': board,
                'binding': binding(args), 'catalog_revision': catalog['revision'], 'catalog_checks': len(expected),
                'earlier_stage_checks': earlier_stage_checks(catalog, board, art_style),
                'left_for_codex': left_for_codex, 'errors': errors,
                'rule': 'The test stage may end (and hand over to 最终验收) only with status test_stage_complete: every check '
                        'passed or justly not applicable, except the Codex-only rows listed in left_for_codex.'}
    return {'status': 'passed' if not errors else 'blocked', 'stage': args.stage, 'board': board,
            'binding': binding(args), 'catalog_revision': catalog['revision'],
            'catalog_checks': len(expected), 'reward_entries': len(inventory),
            'earlier_stage_checks': earlier_stage_checks(catalog, board, art_style),
            'errors': errors, 'limits': 'Coverage/hash/postcondition review only. Does not prove screenshots, actual UI actions, physical device, IAA or upload. Existing mobile gates remain separate.'}


def init(args):
    catalog = load(CATALOG)
    pending = lambda: {'status': 'pending', 'layer': '', 'observed': '', 'evidence': []}
    def pending_state(state):
        row = pending()
        fields = {'completed': ['reward_identity_verified', 'current_reward_display_consistent',
                                'success_feedback_consistent'],
                  'pending': ['checking_state_visible', 'bounded_wait', 'sdk_and_timer_held_recovers',
                              'retry_after_recovery_works'],
                  'return_contracts': ['each_channel_settles_once', 'non_eligible_results_no_reward',
                                       'every_result_visible_end_state', 'test_double_supports_each_channel'],
                  'leave_and_return': ['stale_request_invalidated', 'new_check_started', 'late_result_ignored',
                                       'visible_result_feedback'],
                  'cancelled': ['reward_delta_zero', 'can_retry_or_exit', 'failure_feedback_visible'],
                  'error': ['reward_delta_zero', 'can_retry_or_exit', 'failure_feedback_visible'],
                  'timeout': ['reward_delta_zero', 'can_retry_or_exit', 'failure_feedback_visible'],
                  'reopen': ['model_and_presentation_consistent'],
                  'reload': ['model_and_presentation_consistent'],
                  'save_failure_retry': ['same_transaction_retried', 'no_additional_ad_request',
                                        'reward_applied_once', 'commit_readback_ambiguity_checked',
                                        'no_premature_success_ui', 'proof_target_preserved'],
                  'apply_or_consume': ['actual_effect_verified', 'correct_target', 'quantity_and_effect_consistent',
                                       'ownership_and_usage_distinguished', 'related_views_consistent']}
        if state in fields:
            row['postconditions'] = {field: None for field in fields[state]}
        if state == 'save_failure_retry':
            row['postconditions']['recovery_scope'] = ''
        if state == 'return_contracts':
            row['postconditions']['channels_tested'] = []
        return row
    board = getattr(args, 'board', None) or DEFAULT_BOARD
    art_style = getattr(args, 'art_style', None) or recorded_art_style(args.project) or 'original'
    items = [x for x in catalog['items'] if applies(x, board, art_style) and final_gate(x)]
    entries = load(args.inventory) if args.inventory else []
    if not isinstance(entries, list):
        raise ValueError('Inventory input must be a JSON array of real reward entries')
    inventory_signature(entries)
    review = {'schema': 3, 'board': board, 'art_style': art_style, 'catalog_sha256': sha(CATALOG.read_bytes()),
              'binding': binding(args), 'inventory_complete': False,
              'inventory_evidence': [], 'checks': {x['id']: {**pending(), **({'observations': {k: '' for k in x['required_observations']}} if x.get('required_observations') else {}), **({'auto_reports': []} if auto_tools(x, board) else {})} for x in items},
              'reward_entries': [{**e, 'states': {s: pending_state(s) for s in catalog['reward_states']}} for e in entries],
              'independent_reward_checks': {key: {**pair, **pending()} for key, pair in independent_pairs(entries).items()},
              'test_executor': '',
              'gpt_spot_check': {'reviewer': '', 'locked_commit': '', 'code_changes_reviewed': False,
                                 'rerun_auto_checks': False, 'flows': [], 'disagreements': [],
                                 'note': 'Required when test_executor is another AI: GPT re-runs all automatic checks and redoes >= 3 flows.'},
              'visual_verdict': {'reviewer': '', 'contact_sheets': {'path': '', 'sha256': ''}, 'images_reviewed': 0,
                                 'verdict': 'pending', 'open_issues': [], 'observed': '',
                                 'note': 'Only a GPT/Codex session fills this after looking at the contact sheets of this build.'}}
    if args.review.exists():
        raise ValueError('Existing review is preserved; update it without erasing observations')
    if args.markdown and args.markdown.exists():
        raise ValueError('Existing Markdown is preserved')
    args.review.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path = args.review.with_name(args.review.stem + '.inventory.json')
    if snapshot_path.exists():
        raise ValueError('Existing inventory snapshot is preserved')
    snapshot_path.write_text(json.dumps({'schema': 1, 'binding': review['binding'], 'entries': entries},
                                        ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    review['inventory_snapshot'] = {'path': snapshot_path.name, 'sha256': sha(snapshot_path.read_bytes())}
    args.review.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n')
    if args.markdown:
        lines = ['# ' + args.build_tag + ' 累积问题检查清单（' + ('英化' if board == 'localize' else '重塑') + '）', '',
                 '每项填真实观察和证据。待测、失败或受限不能标成通过；不适用需原因与依据。',
                 '先看"常见症状"列：这是以前真实出过的问题，测试时专门去找它。"自动检查"列有脚本的，必须用 --binding 跑出当前版本的通过报告。', '',
                 '| 编号 | 检查 | 常见症状 | 自动检查 | 操作 | 预期 | 结果/证据 |', '| --- | --- | --- | --- | --- | --- | --- |']
        for row in items:
            auto = '、'.join(x + '.py' for x in auto_tools(row, board)) or '—'
            if row.get('requires_negative_control'):
                auto += '（另附：同一检查在故意改坏的版本上失败的记录）'
            note = row.get('board_notes', {}).get(board, '') if isinstance(row.get('board_notes'), dict) else ''
            expected_text = row['expected'] + ('（' + note + '）' if note else '')
            lines.append('| ' + ' | '.join([row['id'], row['title'], row.get('symptom', ''), auto,
                                             row['steps'], expected_text, '待测']) + ' |')
        skipped = [x['id'] for x in catalog['items'] if not applies(x, board, art_style)]
        if skipped:
            lines += ['', '本板块不检查（只属于另一个板块，见 two-boards.md）：' + '、'.join(skipped)]
        earlier = earlier_stage_checks(catalog, board, art_style)
        if earlier:
            lines += ['', '前面阶段已查、最终总检测不再查（用户 2026-10-24，check-stages.md）：' + '；'.join(
                {'design': '设计关 design_check.py', 'art': '美术关 art_check.py'}[g] + '：' + '、'.join(ids)
                for g, ids in earlier.items()) + '。锁定后又改了设计或美术，只对改动重跑对应脚本，不进本清单。']
        lines += ['', '## 每个奖励入口的状态检查', '',
                  '| 入口 / 规则 | ' + ' | '.join(catalog['reward_states']) + ' |',
                  '| --- | ' + ' | '.join(['---'] * len(catalog['reward_states'])) + ' |']
        for e in entries:
            lines.append('| ' + str(e.get('id', '')) + ' / ' + str(e.get('policy', '')) + ' | ' + ' | '.join(['待测'] * len(catalog['reward_states'])) + ' |')
        lines += ['', '## 同组独立奖励交叉状态', '']
        for key in review['independent_reward_checks']:
            lines.append('- ' + key + ': 领取前者后，后者仍可领取且状态/奖励未被改变。待测。')
        args.markdown.write_text('\n'.join(lines) + '\n')
    return {'status': 'review_initialized_all_pending', 'board': board, 'art_style': art_style, 'catalog_checks': len(items),
            'earlier_stage_checks': earlier_stage_checks(catalog, board, art_style), 'reward_entries': len(entries)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['init', 'check'])
    p.add_argument('--project', type=Path, required=True)
    p.add_argument('--native', type=Path, required=True)
    p.add_argument('--web', type=Path, required=True)
    p.add_argument('--build-tag', required=True)
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--inventory', type=Path)
    p.add_argument('--markdown', type=Path)
    p.add_argument('--report', type=Path)
    p.add_argument('--stage', choices=['pre_scan', 'post_package', 'device'], default='pre_scan')
    p.add_argument('--board', choices=list(BOARDS),
                   help='localize = 英化（中文源码转英文）, remake = 重塑（启动包做游戏）; init records it, check verifies it')
    p.add_argument('--executor-exit', action='store_true',
                   help='test stage exit check (user 2026-10-22): everything must be done except Codex-only rows; '
                        'status test_stage_complete is the only allowed end of the test stage')
    p.add_argument('--art-style', choices=list(ART_STYLES),
                   help='英化 only: original = 沿用原游戏画风 (default), remake = 用户说"按重塑画风重做" (ART-02/ART-03 then apply); '
                        'default reads docs/art-style.txt')
    a = p.parse_args()
    try:
        result = init(a) if a.action == 'init' else audit(a)
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as e:
        result = {'status': 'blocked', 'errors': [str(e)]}
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] in {'passed', 'review_initialized_all_pending', 'test_stage_complete'} else 2


if __name__ == '__main__':
    sys.exit(main())
