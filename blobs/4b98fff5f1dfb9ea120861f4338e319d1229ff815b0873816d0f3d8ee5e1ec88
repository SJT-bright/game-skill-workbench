#!/usr/bin/env python3
"""List levels requiring real-touch play, including each new mechanic's intro.

Baseline: 1-15 all; 16-30 every 2nd; 31-40 every 3rd; 41-50 every 4th;
+1 step per further block of 10. Always include the final level and every
level with tags containing "intro". Reaching a level via QA jump does not
replace playing the tested level with real touch.

In level_plan.json mark a mechanic's FIRST appearance, for example:
  {"level": 17, "tags": ["intro"], "mechanics": ["wind"]}
Use stable mechanic IDs in each level's mechanics list to detect missing intro
marks. An intro tag alone is valid, but cannot prove all mechanics were listed.

Usage:
  python plan_level_tests.py --level-plan level_plan.json [--out plan.json]
  python plan_level_tests.py --total 120 [--level-plan level_plan.json] [--out plan.json]
  python plan_level_tests.py --level-plan level_plan.json --scope changed \
    --changed-levels 18,25-26 --related-levels 27 --regression-levels 69
The default full sample is unchanged. The changed scope only plans a local
regression; it never satisfies or bypasses a release gate or proves a baseline.
The --total-only mode remains available and warns that intro coverage is unknown.
Warnings are printed on stderr and included in JSON; they do not claim play passed.
"""
import argparse
import json
from pathlib import Path
import sys


def step_for(level):
    if level <= 15:
        return 1
    if level <= 30:
        return 2
    return 3 + (level - 31) // 10


def block_start(level):
    if level <= 15:
        return 1
    if level <= 30:
        return 16
    return 31 + (level - 31) // 10 * 10


def plan(total):
    """Keep the original baseline API for callers that only supply a count."""
    if type(total) is not int or total < 1:
        raise ValueError('total must be a positive integer')
    tested = [n for n in range(1, total + 1) if (n - block_start(n)) % step_for(n) == 0]
    if total not in tested:
        tested.append(total)
    return tested


def read_level_plan(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or data.get('mode') != 'levels':
        raise ValueError('level plan must be an object with mode "levels"; endless games have no level sampling')
    total, rows = data.get('total_levels'), data.get('levels')
    if type(total) is not int or total < 1 or not isinstance(rows, list):
        raise ValueError('level plan needs positive total_levels and a levels array')
    by = {}
    for row in rows:
        n = row.get('level') if isinstance(row, dict) else None
        if type(n) is not int or not 1 <= n <= total or n in by:
            raise ValueError('invalid or duplicate level: %r' % n)
        for field in ('tags', 'mechanics'):
            values = row.get(field, [])
            if not isinstance(values, list) or any(not isinstance(x, str) or not x.strip() for x in values):
                raise ValueError('level %d: %s must be an array of nonempty strings' % (n, field))
        by[n] = row
    if len(by) != total:
        raise ValueError('level plan must list every level 1-%d; missing %s' %
                         (total, sorted(set(range(1, total + 1)) - by.keys())[:20]))
    return total, [by[n] for n in sorted(by)]


def parse_levels(value):
    """Parse a bounded explicit set; a typo must not silently omit a level."""
    if not value:
        return []
    levels = set()
    for token in value.split(','):
        token = token.strip()
        parts = token.split('-')
        if not token or len(parts) > 2 or any(not p.isdigit() for p in parts):
            raise ValueError('levels must be comma-separated positive numbers or ascending ranges')
        start, end = int(parts[0]), int(parts[-1])
        if start < 1 or end < start or end > 100000:
            raise ValueError('invalid level range: ' + token)
        levels.update(range(start, end + 1))
    return sorted(levels)


STROKE_INPUTS = ('cut', 'slice', 'draw', 'line', 'swipe', 'stroke')   # 划线、切割类 (总表 T7)
INSIDE_PX = 8


def stroke_touch_cases():
    """总表 T7 (剪刀达人 10-30): auto cuts always started outside the strip and let go inside the screen, so "划了剪不到"
    never showed. Three fixed real-touch cases a person does, for every stroke game, on the first tested level of each
    mechanic and on every level whose target is thin."""
    return [
        {'id': 'release_outside', 'expect': 'same as the design stroke',
         'how': 'start the design stroke normally, keep moving and let go OUTSIDE the game canvas (past the screen edge); '
                'the cut / line must still count, nothing may stay stuck in the dragging state'},
        {'id': 'start_inside_%dpx' % INSIDE_PX, 'expect': 'same as the design stroke',
         'how': 'start the stroke %d px INSIDE the target (not before it), end normally' % INSIDE_PX},
        {'id': 'end_inside_%dpx' % INSIDE_PX, 'expect': 'same as the design stroke',
         'how': 'start normally, let go %d px INSIDE the target (stop short of its far edge)' % INSIDE_PX},
    ]


def solution_cases(levels):
    """总表 T7: the level runner plays two kinds of solution on every listed level. The design solution must pass;
    wrong solutions must NOT pass (剪刀达人: a 40-50 degree slant passed levels it should not)."""
    out = []
    for n in levels:
        out += [{'level': n, 'case': 'design_solution', 'expect': 'pass'},
                {'level': n, 'case': 'wrong_offset', 'expect': 'fail',
                 'how': 'the design stroke moved sideways by 1.5x the thinnest part of its target (at least 24 px)'},
                {'level': n, 'case': 'wrong_slant', 'expect': 'fail',
                 'how': 'the design stroke turned 45 degrees around its middle'}]
    return out


def build_report(total, rows=None, *, scope='full', changed_levels=None,
                 related_levels=None, regression_levels=None, input_kind=None):
    baseline = plan(total)
    if scope not in {'full', 'changed'}:
        raise ValueError('scope must be full or changed')
    selections = {'changed': changed_levels or [], 'related': related_levels or [],
                  'known_failure': regression_levels or []}
    for values in selections.values():
        if any(type(n) is not int or not 1 <= n <= total for n in values):
            raise ValueError('selected levels must be integers in 1-%d' % total)
    if scope == 'changed' and not any(selections.values()):
        raise ValueError('changed scope requires changed, related or regression levels')
    intros, first, missing = [], {}, {}
    warnings = []
    if rows is None:
        warnings.append('No level plan supplied: intro coverage cannot be checked. Supply --level-plan and mark each new mechanic first appearance with tags: ["intro"].')
    else:
        # read_level_plan supplies sorted rows; keep ordering deterministic for direct callers too.
        for row in sorted(rows, key=lambda r: r['level']):
            n = row['level']
            if 'intro' in row.get('tags', []):
                intros.append(n)
            for mechanic in row.get('mechanics', []):
                if mechanic not in first:
                    first[mechanic] = n
                    if 'intro' not in row.get('tags', []):
                        missing.setdefault(n, []).append(mechanic)
        if not intros:
            warnings.append('No "intro" tags found: mark the first level of every new mechanic; otherwise it may be skipped by baseline sampling.')
        if not first:
            warnings.append('No mechanics IDs recorded: tagged intro levels are included, but unmarked first appearances cannot be identified automatically. Review the gameplay specification against the level table.')
        for n, mechanics in missing.items():
            warnings.append('Level %d first introduces %s but is missing tags: ["intro"]. Add the tag and regenerate this checklist.' % (n, ', '.join(mechanics)))
    reasons = {}
    def include(levels, reason):
        for n in levels:
            reasons.setdefault(n, set()).add(reason)
    if scope == 'full':
        include(baseline, 'baseline_sample')
        include(intros, 'mechanic_intro')
    for reason, values in selections.items():
        include(values, reason)
    # A local level change can affect a mechanic's first-use teaching path.
    # Include those representatives, not all unrelated intro levels.
    if scope == 'changed' and rows is not None:
        affected = set(selections['changed']) | set(selections['related']) | set(selections['known_failure'])
        mechanics = {m for row in rows if row['level'] in affected for m in row.get('mechanics', [])}
        include([first[m] for m in sorted(mechanics)], 'affected_mechanic_intro')
    tested = sorted(reasons)
    if total > 15 and len(tested) == total:
        warnings.append('The selected sample covers every level. Inspect selection_reasons and intro tags; do not silently drop genuine first-use mechanics to reduce coverage.')
    stroke = {}
    if input_kind in STROKE_INPUTS:
        stroke = {'input_kind': input_kind, 'stroke_touch_cases': stroke_touch_cases(),
                  'solution_cases': solution_cases(tested),
                  'stroke_rule': ('总表 T7: a stroke game runs the 3 fixed touch cases with real touch, and its level '
                                  'runner plays the design solution (must pass) and two wrong ones, offset and slant '
                                  '(must fail), on every listed level. A runner without wrong solutions is not done.')}
    elif input_kind is None and rows is not None and any(
            m in STROKE_INPUTS for r in rows for m in (r.get('mechanics') or [])):
        warnings.append('Mechanics name a stroke input (%s) but no input kind is set: add "input": "cut|draw|..." to '
                        'level_plan.json or pass --input, so the stroke touch cases and wrong solutions are planned.'
                        % ', '.join(STROKE_INPUTS))
    return dict({'total_levels': total, 'tested_with_real_touch': tested, 'tested_count': len(tested),
            'skipped_count': total - len(tested), 'scope': scope,
            'baseline_levels': baseline if scope == 'full' else [], 'intro_levels': sorted(set(intros)),
            'selection_reasons': {str(n): sorted(reasons[n]) for n in tested},
            'mechanic_first_levels': first, 'missing_intro': [
                {'level': n, 'mechanics': values} for n, values in missing.items()],
            'warnings': warnings,
            'rule': ('1-15 all; 16-30 every 2nd; 31-40 every 3rd; 41-50 every 4th; +1 per further 10; last level and every tagged intro always'
                     if scope == 'full' else 'Only explicit changed/related/regression levels and their mechanic first-use representatives; no unrelated baseline replay'),
            'boundary': 'A sampling checklist, not evidence that any level was played or passed. Changed scope is local regression only, not full release acceptance.'},
                **stroke)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--total', type=int, help='number of levels; inferred from --level-plan when omitted')
    ap.add_argument('--level-plan', '--plan', dest='level_plan', type=Path, help='actual level_plan.json with intro tags')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--scope', choices=['full', 'changed'], default='full')
    ap.add_argument('--changed-levels', default='', help='changed levels, e.g. 18,25-26')
    ap.add_argument('--related-levels', default='', help='levels selected from actual shared dependencies')
    ap.add_argument('--regression-levels', default='', help='relevant previously failing levels')
    ap.add_argument('--input', choices=STROKE_INPUTS + ('tap', 'drag', 'other'),
                    help='main input; cut/slice/draw/line/swipe/stroke adds the T7 stroke cases (default: level_plan "input")')
    a = ap.parse_args()
    if a.total is not None and a.total < 1:
        ap.error('--total must be at least 1')
    rows, total = None, a.total
    if a.level_plan:
        try:
            count, rows = read_level_plan(a.level_plan)
            if a.input is None:
                a.input = json.loads(a.level_plan.read_text(encoding='utf-8-sig')).get('input')
        except (OSError, ValueError) as exc:
            ap.error(str(exc))
        if total is not None and total != count:
            ap.error('--total does not match level_plan.total_levels')
        total = count
    if total is None:
        ap.error('supply --level-plan (recommended) or --total')
    try:
        report = build_report(total, rows, scope=a.scope,
                              changed_levels=parse_levels(a.changed_levels),
                              related_levels=parse_levels(a.related_levels),
                              regression_levels=parse_levels(a.regression_levels),
                              input_kind=a.input)
    except ValueError as exc:
        ap.error(str(exc))
    if a.level_plan:
        report['level_plan'] = str(a.level_plan.resolve())
    for warning in report['warnings']:
        print('WARNING: ' + warning, file=sys.stderr)
    if a.out:
        if a.out.exists():
            raise SystemExit('output exists: ' + str(a.out))
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
