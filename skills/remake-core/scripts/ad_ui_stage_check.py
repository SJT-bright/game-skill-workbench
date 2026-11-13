"""Verify only the declared ad UI cases with the existing art production checker.

This module does not generate an aggregate art receipt or certify visual style.
It verifies a sealed representative and reuses hash-bound full-art page results
with the original collector's current provenance. Other pages are out of scope.
"""
import hashlib
import json
from pathlib import Path


def _relative(project, value, *, directory=False):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError('ad UI evidence paths must be project-relative')
    path = (project / value).resolve(strict=True)
    path.relative_to(project)
    if directory and not path.is_dir():
        raise ValueError('ad UI evidence directory missing: ' + value)
    if not directory and not path.is_file():
        raise ValueError('ad UI evidence file missing: ' + value)
    return path


def evaluate_plan(plan, required, coverage=None):
    """Interpret actual checker output; a plan's advisory status is not approval."""
    problems = []
    if not isinstance(plan, dict) or plan.get('schema') != 'art_iteration_plan.v1':
        return ['ad UI checker did not return an art_iteration_plan.v1'], []
    first = plan.get('first_piece') or {}
    for key in ('current', 'passed', 'capture_verified'):
        if first.get(key) is not True:
            problems.append('ad UI first piece is not ' + key)
    selected = set(first.get('selected_cases') or [])
    if not selected.intersection(required):
        problems.append('ad UI needs a real representative from its declared cases')
    coverage = coverage or {}
    problems.extend(coverage.get('problems') or [])
    verified = set(coverage.get('checked_visual_case_ids') or []) if coverage.get('verified') is True else set()
    for case in sorted(set(required) - verified):
        problems.append('ad UI has no verified full-art analysis for ' + case)
    links = plan.get('visual_to_capture') or {}
    capture = plan.get('capture_plan') or {}
    if capture.get('error'):
        problems.append('ad UI capture checker: ' + str(capture['error']))
    states = {row.get('id'): row for row in capture.get('cases', []) if isinstance(row, dict)}
    for case in required:
        capture_id = links.get(case)
        if not capture_id or states.get(capture_id, {}).get('action') not in ('fresh', 'reuse'):
            problems.append('ad UI has no verified current capture for ' + case)
    # The owning plan already triages failures by their producer, capture or UI
    # layer. Never clear them merely because a JSON scalar says passed.
    for issue in plan.get('issues') or []:
        problems.append('owning art checker finding: ' + json.dumps(issue, ensure_ascii=False))
    checked = sorted(set(required) & verified) if not problems else []
    return problems, checked


def _read_analysis(report, name, checker):
    proofs = report.get('analysis_reports') or {}
    proof = proofs.get(name) if isinstance(proofs, dict) else None
    if not isinstance(proof, dict):
        raise ValueError('missing bound analysis: ' + name)
    path = Path(proof.get('path') or '')
    tool = Path(__file__).with_name(checker)
    raw = path.read_bytes() if path.is_absolute() and path.is_file() else b''
    if (not raw
            or hashlib.sha256(raw).hexdigest() != proof.get('sha256')
            or hashlib.sha256(tool.read_bytes()).hexdigest() != proof.get('checker_sha256')):
        raise ValueError('missing or changed bound analysis: ' + name)
    return json.loads(raw)


def full_art_coverage(project, plan, required, dumps, board):
    """Reuse original per-page analyses; a saved pass scalar alone is insufficient."""
    result = dict(verified=False, problems=[], checked_visual_case_ids=[])
    try:
        from art_check_record import read
        record = read(project) or {}
        last = record.get('last') or {}
        if not isinstance(last, dict):
            raise ValueError('invalid owning art-check record')
        path = Path(last.get('report') or '')
        raw = path.read_bytes() if path.is_absolute() and path.is_file() else b''
        if (not raw or last.get('scoped')
                or hashlib.sha256(raw).hexdigest() != last.get('report_sha256')):
            raise ValueError('full-art original report is absent, scoped or changed')
        report = json.loads(raw)
        if not isinstance(report, dict):
            raise ValueError('invalid owning art-check report')
        rows = report.get('rows')
        if (record.get('board') != board or report.get('board') != board
                or report.get('tool') != 'art_check' or not isinstance(rows, list) or not rows
                or any(not isinstance(row, dict) for row in rows)
                or report.get('checked') != len(rows) or report.get('status') != last.get('status')
                or report.get('status') not in ('pass', 'fail')
                or report.get('failed') != sum(r.get('status') == '需处理' for r in rows)):
            raise ValueError('full-art report has no consistent owning-check results')
        capture = plan.get('capture_plan') or {}
        original = report.get('capture_round') or {}
        same_round = all(original.get(k) == capture.get(k) for k in ('round', 'version'))
        inherited = any(isinstance(ref, dict) and ref.get('path') == str(path)
                        and ref.get('sha256') == last['report_sha256']
                        for ref in capture.get('quality_refs', []))
        if (original.get('ready') is not True or capture.get('error')
                or not original.get('round') or not original.get('version')
                or not (same_round or inherited)):
            raise ValueError('full-art analysis lacks a current round or verified original quality reference')
        pages = _read_analysis(report, 'page_richness.json', 'audit_page_richness.py')
        slots = _read_analysis(report, 'visual-slots-result.json', 'audit_art_slots.py')
        if (not isinstance(pages, dict) or not isinstance(slots, dict)
                or not isinstance(pages.get('pages'), list) or not isinstance(slots.get('cases'), list)
                or any(not isinstance(p, dict) for p in pages['pages']+slots['cases'])):
            raise ValueError('invalid bound page/slot results')
        if pages.get('setup'):
            raise ValueError('full-art pixel analysis has unresolved setup findings')
        old_cases = {c['id']: c for c in original.get('cases', [])}
        current_cases = {c['id']: c for c in capture.get('cases', [])}
        for case in sorted(required):
            try:
                capture_id = plan['visual_to_capture'][case]
                old, current = old_cases[capture_id], current_cases[capture_id]
                if (current.get('action') not in ('fresh', 'reuse') or not old.get('origin')
                        or old['origin'] != current.get('origin')):
                    raise ValueError('capture origin or verified artifacts changed')
                from art_iteration_plan import resolved_capture_file
                file = resolved_capture_file(capture, dumps, capture_id).resolve(strict=True)
                doc = json.loads(file.read_bytes())
                if doc.get('art_capture_id') != current['origin']:
                    raise ValueError('dump is not the collector-verified original')
                page = [p for p in pages.get('pages', []) if Path(p.get('file') or '').resolve() == file]
                slot = [p for p in slots.get('cases', []) if p.get('id') == case]
                if (len(page) != 1 or not isinstance(page[0].get('problems'), list) or page[0]['problems']
                        or len(slot) != 1 or slot[0].get('passed') is not True
                        or not isinstance(slot[0].get('checks'), list) or not slot[0]['checks']
                        or any(not isinstance(c, dict) or c.get('passed') is not True for c in slot[0]['checks'])):
                    raise ValueError('missing or failed actual pixel/slot checks')
                result['checked_visual_case_ids'].append(case)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                result['problems'].append(case + ': ' + str(exc))
        result.update(verified=True, report=str(path), report_sha256=last['report_sha256'])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result['problems'].append(str(exc))
    return result


def check_project(project, *, manifest, stage='writer', ui=None):
    """Verify current original captures and reuse the exact completed art analyses."""
    project = Path(project).resolve()
    result = {'schema': 'ad_ui_stage_check.v1', 'passed': False, 'problems': [],
              'checked_visual_case_ids': [], 'full_art_passed': None,
              'aggregate_receipt_written': False, 'stage': stage,
              'boundary': 'Scoped production/capture checks; style and visible state still require Agent inspection.'}
    try:
        section = manifest.get('ui') or {}
        required = set(section.get('visual_case_ids') or [])
        for node in manifest.get('nodes') or []:
            required.update((node.get('ui') or {}).get('visual_case_ids') or [])
        if not required or any(not isinstance(case, str) or not case for case in required):
            raise ValueError('six-node UI needs explicit visual_case_ids from existing visual-slots')
        build = _relative(project, section.get('web_export'), directory=True)
        dumps = _relative(project, section.get('dumps'), directory=True)
        first = _relative(project, section.get('first_piece_report'))
        from feature_policy import board_of
        board = board_of(project, None)[0]
        if board not in ('remake', 'localize'):
            raise ValueError('ad UI project board is not resolved')
        from art_iteration_plan import plan as owning_plan
        actual = owning_plan(project, build=build, dumps=dumps, first_piece=first, board=board)
        coverage = full_art_coverage(project, actual, required, dumps, board)
        problems, checked = evaluate_plan(actual, required, coverage)
        result.update(problems=problems, checked_visual_case_ids=checked, full_art_coverage=coverage,
                      checker_replays=actual.get('checker_replays', 0),
                      source_status=actual.get('source_status'),
                      first_piece=actual.get('first_piece'),
                      other_visual_cases_untouched=actual.get('remaining_visual_cases', []),
                      passed=not problems)
    except (OSError, ValueError, TypeError, KeyError, ImportError) as error:
        result['problems'].append(str(error))
    return result
