"""Verify only the declared ad UI cases with the existing art production checker.

This module does not generate an aggregate art receipt or certify visual style.
It replays the original scoped checker and asks the original capture tool which
frames are fresh/reusable. Other pages are outside this node's scope.
"""
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


def evaluate_plan(plan, required):
    """Interpret actual checker output; a plan's advisory status is not approval."""
    problems = []
    if not isinstance(plan, dict) or plan.get('schema') != 'art_iteration_plan.v1':
        return ['ad UI checker did not return an art_iteration_plan.v1'], []
    first = plan.get('first_piece') or {}
    for key in ('current', 'passed', 'capture_verified'):
        if first.get(key) is not True:
            problems.append('ad UI first piece is not ' + key)
    selected = set(first.get('selected_cases') or [])
    if not set(required) <= selected:
        problems.append('ad UI first-piece scope does not cover: ' + ', '.join(sorted(set(required) - selected)))
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
    checked = sorted(set(required) & selected) if not problems else []
    return problems, checked


def check_project(project, *, manifest, stage='writer', ui=None):
    """Read the original captures and replay the current scoped art checker."""
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
        problems, checked = evaluate_plan(actual, required)
        result.update(problems=problems, checked_visual_case_ids=checked,
                      checker_replays=actual.get('checker_replays', 0),
                      source_status=actual.get('source_status'),
                      first_piece=actual.get('first_piece'),
                      other_visual_cases_untouched=actual.get('remaining_visual_cases', []),
                      passed=not problems)
    except (OSError, ValueError, TypeError, KeyError, ImportError) as error:
        result['problems'].append(str(error))
    return result
