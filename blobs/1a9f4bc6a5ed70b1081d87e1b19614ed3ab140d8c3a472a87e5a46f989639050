#!/usr/bin/env python3
"""Level map, bonus levels and limited levels (LEVEL-01, both boards; user 2026-10-22, the level module 2026-10-23,
70-or-more and the two limited-skin formats 2026-10-24). A design-stage check (references/check-stages.md): run it with
design_check.py at 英化 1.5 / 重塑 round 1, not in the final audit.
references/top-bar-and-level-map.md, references/game-modules.md 五

The plan: assets/resources/config/level_plan.json (the game reads it), or docs/levels/level_plan.json with a note
where the original keeps its levels. make_level_plan.py writes a skeleton.
  {"schema": "level_plan.v1", "mode": "levels"|"endless", "why": "...", "currency": "Pearls",
   "total_levels": 70, "milestone_every": 10, "seed": N (the bonus places are drawn from it),
   "limited_skin_mode": "final"|"every_10" (optional; read from the rewards when missing),
   "levels": [{"level": 1, "type": "normal"|"bonus"|"milestone", "difficulty": 1.0, "coins": 40, "new": true (英化: added level),
               "reward": {"type": "coins", "amount": N} | {"type": "skin", "id": "..."} (milestone)}]}
endless: no levels, no map page (purpose "map" must not appear in the test dumps).
levels:
  - 70 levels or more (user 2026-10-24, both boards: at least 70 passes, more is fine, nothing is cut): 英化 with fewer
    than 70 adds new levels in the original gameplay up to at least 70 (marked "new": true); an original with 70 or
    more keeps all its levels; 重塑 makes 70 or more
  - every level 1..total_levels listed once, difficulty > 0, coins >= 0
  - difficulty rises step by step (bonus levels left out): never goes down, no jump bigger than 3x the usual step
    (limited levels included: no spike). 英化: only the added levels are checked (the original order is kept)
  - a limited level (type milestone) exactly at every 10th level and on the last level (user 2026-10-23: 1/10 of the
    levels; 10, 20 ... last), nowhere else; coin rewards >= the sum of the 5 levels before it. Limited skin, two formats
    (user 2026-10-24, both pass): "final" = only the LAST limited level gives the limited skin of the skin module (when
    the game has skins), the other limited levels give coins; "every_10" = every limited level gives its own limited
    skin. A limited skin is unlock "level", condition "clear", that level, no ads, no coins (cannot be bought)
  - bonus levels: exactly one in every block of 10 (0-1 in a short last block) at the places make_level_plan.py draws
    from the plan's "seed" (every game differs; never levels 1-3, never on or next to a limited level); very easy
    (not harder than the easiest normal level of its block) and 3x the block's median normal coins (2.9-3.5x; the x2
    ad makes it 6x). 英化: bonus levels are new easy levels ("new": true) put in at those places
  - unlock_table: no "perfect clear gives a skin" items (user 2026-10-22); every level skin is the reward of its
    limited level; a map item (group map, condition clear) unlocks on a limited level (the chapter end)
  - dumps (docs/test, chrome_touch dump_ui): at least one map page, and a map page shows the total number of levels
Usage:
  python audit_level_plan.py --project <game> [--plan level_plan.json] [--dumps <folder> ...] [--board localize|remake]
      [--binding review.json] --out report.json
Exit codes: 0 pass, 1 fail, 2 bad input. Markers and the reward popup are checked in the browser (LEVEL-02).
"""
import argparse
import json
from pathlib import Path
import re
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_page_richness import load as load_dumps, text as node_text  # noqa: E402
from make_level_plan import bonus_places  # noqa: E402

PLAN_PATHS = ('assets/resources/config/level_plan.json', 'docs/levels/level_plan.json')
TABLE_PATHS = ('assets/resources/config/unlock_table.json', 'docs/economy/unlock_table.json')
EVERY = (10,)          # user 2026-10-23: every 10th level is a limited level
LEVELS = 70            # user 2026-10-24: every level game has 70 levels or more (both boards; was "exactly 70")
MIN_LEVELS = LEVELS
SKIN_MODES = ('final', 'every_10')   # user 2026-10-24: the two limited-skin formats
BUYABLE = ('ads', 'coins', 'ads_coins', 'ads_or_coins')
MAP_GROUPS = ('map', 'maps', 'world', 'worlds', 'chapter', 'chapters')


def limited_levels(every, total):
    """Limited levels: every 10th level plus the last level (the finale): 10, 20 ... 70."""
    return sorted(set(range(every, total + 1, every)) | {total})


def _every_milestone(plan):
    """User-authorized per-milestone limited skins ( Customs Pigeon 2026-10-24: one limited skin at every 10th level).
    Recorded in level_plan.json as "limited_skin_policy": {mode, authorized_by, reason}; printed in the report."""
    o = plan.get('limited_skin_policy') if isinstance(plan, dict) else None
    return isinstance(o, dict) and o.get('mode') == 'every_milestone' \
        and len(str(o.get('authorized_by', '')).strip()) >= 6 and len(str(o.get('reason', '')).strip()) >= 30


def chapters(every, total):
    """(start, end) of each block of 10: a block ends on a limited level (the last one may be short)."""
    out, start = [], 1
    for end in limited_levels(every, total):
        out.append((start, end))
        start = end + 1
    return out


def find_plan(proj):
    for rel in PLAN_PATHS:
        p = Path(proj) / rel
        if p.is_file():
            return p
    return None


def plan_mode(proj):
    """'levels', 'endless' or None: used by the other audits (map page required / top bar pages)."""
    p = find_plan(proj)
    try:
        return json.loads(p.read_text(encoding='utf-8-sig')).get('mode') if p else None
    except (OSError, ValueError, AttributeError):
        return None


def table_items(proj):
    for rel in TABLE_PATHS:
        p = Path(proj) / rel
        if p.is_file():
            data = json.loads(p.read_text(encoding='utf-8-sig'))
            rows = data.get('items') if isinstance(data, dict) else data
            return [r for r in rows or [] if isinstance(r, dict)]
    return None


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def rise_problems(rows):
    """Difficulty goes up one step at a time: never down, no jump bigger than 3x the usual (median) step."""
    out = []
    steps = [(a, b, b['difficulty'] - a['difficulty']) for a, b in zip(rows, rows[1:])]
    ups = sorted(d for _, _, d in steps if d > 0)
    usual = ups[len(ups) // 2] if ups else 0
    for a, b, d in steps:
        if d < -1e-9:
            out.append('level %d is easier (%s) than level %d (%s)' % (b['level'], b['difficulty'], a['level'], a['difficulty']))
        elif usual and d > 3 * usual + 1e-9 and d > 0.15 * a['difficulty']:
            out.append('level %d jumps from %s to %s (usual step %s): no spikes, raise it gradually'
                       % (b['level'], a['difficulty'], b['difficulty'], round(usual, 3)))
    return out


def audit_plan(plan, items, add, board=None):
    mode = plan.get('mode')
    if plan.get('schema') != 'level_plan.v1' or mode not in ('levels', 'endless') or not str(plan.get('why', '')).strip() \
            or 'TODO' in str(plan.get('why')):
        add('mode_recorded', False, 'level_plan.json needs schema level_plan.v1, mode levels|endless and why (how you decided)')
        return mode
    add('mode_recorded', True, '%s: %s' % (mode, plan['why']))
    if mode == 'endless':
        return mode
    total, every = plan.get('total_levels'), plan.get('milestone_every')
    rows = plan.get('levels') if isinstance(plan.get('levels'), list) else []
    if type(total) is not int or every not in EVERY or total < every:
        add('structure', False, 'total_levels (>= 10) and milestone_every 10 are required (user 2026-10-23: every 10th level is a '
            'limited level; found %r, %r)' % (total, every))
        return mode
    if total >= LEVELS:
        ok, detail = True, '%d levels (70 or more, user 2026-10-24)' % total
    elif total < LEVELS:
        # User-authorized explicit level count (from-starter SKILL.md: 用户或项目明确关数优先).
        # The plan itself must record who authorized it and why; the override is printed in the report.
        ovr = plan.get('explicit_total') if isinstance(plan.get('explicit_total'), dict) else None
        if ovr and ovr.get('count') == total and len(str(ovr.get('authorized_by', '')).strip()) >= 6 \
                and len(str(ovr.get('reason', '')).strip()) >= 30:
            ok, detail = True, ('%d levels: OVERRIDE recorded in level_plan.json (authorized by %s): %s — skill default is %d; '
                                'kept because 用户或项目明确关数优先' % (total, ovr.get('authorized_by'), str(ovr.get('reason'))[:180], LEVELS))
        else:
            ok, detail = False, ('%d levels: every level game has %d levels or more (user 2026-10-24), add at least %d (英化 too: new '
                                 'levels in the original gameplay, marked "new": true, each one proven solvable). A user-authorized '
                                 'count must be recorded as "explicit_total": {count, authorized_by, reason>=30 chars}' % (total, LEVELS, LEVELS - total))
    else:
        ok, detail = False, ('%d levels: every level game has 70 levels or more (user 2026-10-24), add at least %d (英化 too: '
                             'new levels in the original gameplay, marked "new": true, each one proven solvable)' % (total, LEVELS - total))
    add('levels_at_least_70', ok, detail)
    by = {}
    bad = []
    for r in rows:
        n = r.get('level') if isinstance(r, dict) else None
        if type(n) is not int or n in by or not 1 <= n <= total or r.get('type') not in ('normal', 'bonus', 'milestone') \
                or not num(r.get('difficulty')) or r['difficulty'] <= 0 or type(r.get('coins')) is not int or r['coins'] < 0:
            bad.append(n if type(n) is int else repr(r)[:40])
            continue
        by[n] = r
    missing = [n for n in range(1, total + 1) if n not in by]
    add('every_level_listed', not bad and not missing,
        'levels 1-%d listed with type, difficulty and coins' % total if not bad and not missing else
        'fix level rows: bad %s, missing %s' % (bad[:8], missing[:8]))
    if bad or missing:
        return mode
    climb = [by[n] for n in sorted(by) if by[n]['type'] != 'bonus']
    note = ''
    if board == 'localize':
        climb = [r for r in climb if r.get('new')]
        note = '（英化：原关卡顺序不改，只查新加的 %d 关）' % len(climb)
    problems = rise_problems(climb)
    add('difficulty_rises', not problems, ('difficulty rises step by step, no spikes' + note) if not problems else '; '.join(problems[:6]))
    limited = limited_levels(every, total)
    wrong = [n for n in by if (by[n]['type'] == 'milestone') != (n in limited)]
    add('limited_every_%d' % every, not wrong, 'limited levels at %s' % limited if not wrong else
        'type "milestone" must be exactly levels %s (every %d and the last level %d); wrong: %s'
        % (limited, every, total, sorted(wrong)[:8]))
    item_by_id = {str(r.get('id')): r for r in items or []}
    limited_skins = [r for r in items or [] if r.get('limited') is True and str(r.get('group', '')).lower() == 'skin']
    skin_levels = [n for n in limited if (by[n].get('reward') or {}).get('type') == 'skin']
    skin_mode = plan.get('limited_skin_mode')
    if skin_mode is None:
        skin_mode = 'every_10' if len(skin_levels) > 1 else 'final'
    add('limited_skin_mode', skin_mode in SKIN_MODES,
        ('limited skin format "%s" (%s)' % (skin_mode, 'only the last limited level gives the limited skin' if skin_mode == 'final'
                                              else 'every limited level gives its own limited skin'))
        if skin_mode in SKIN_MODES else 'limited_skin_mode must be "final" or "every_10" (user 2026-10-24), found %r' % skin_mode)
    seen_skins = {}
    for n in limited:
        r = by[n]
        need = sum(by[k]['coins'] for k in range(max(1, n - 5), n))
        problems = []
        reward = r.get('reward') if isinstance(r.get('reward'), dict) else {}
        if skin_mode == 'final' and not _every_milestone(plan) and n == limited[-1] and limited_skins and not (
                reward.get('type') == 'skin' and str(reward.get('id')) == str(limited_skins[0].get('id'))):
            problems.append('format "final": the last limited level gives the limited skin %s of the skin module' % limited_skins[0].get('id'))
        if skin_mode == 'every_10' and reward.get('type') != 'skin':
            problems.append('format "every_10": every limited level gives its own limited skin (make_skin_table.py --limited-mode '
                            'every_10), or use format "final"')
        if reward.get('type') == 'coins':
            if type(reward.get('amount')) is not int or reward['amount'] < need:
                problems.append('coin reward %s is below the sum of the 5 levels before it (%d)' % (reward.get('amount'), need))
        elif reward.get('type') == 'skin' and skin_mode == 'final' and not _every_milestone(plan) and n != limited[-1]:
            problems.append('format "final": only the last limited level gives a skin; level %d gives a big pile of coins '
                            '(or set "limited_skin_mode": "every_10": every limited level gives one)' % n)
        elif reward.get('type') == 'skin':
            sid = str(reward.get('id'))
            item = item_by_id.get(sid)
            if sid in seen_skins:
                problems.append('skin %s is already the reward of level %d: one skin per limited level' % (sid, seen_skins[sid]))
            seen_skins.setdefault(sid, n)
            if items is None:
                problems.append('skin %s: unlock_table.json not found' % reward.get('id'))
            elif not item:
                problems.append('skin %s is not in unlock_table.json' % reward.get('id'))
            elif _every_milestone(plan):
                if not item.get('limited'):
                    problems.append('every-milestone skin %s must be marked limited in unlock_table.json' % reward.get('id'))
            else:
                if str(item.get('unlock', '')).lower() != 'level' or str(item.get('condition', '')).lower() != 'clear' \
                        or item.get('level') != n or item.get('ads') or item.get('coins'):
                    problems.append('limited skin %s must be unlock "level", condition "clear", level %d, ads 0, coins 0 '
                                    '(only won here, cannot be bought)' % (reward.get('id'), n))
                if str(item.get('rarity', '')).lower() not in ('limited', 'rare', 'epic', 'legendary'):
                    problems.append('limited skin %s is %r: worth as much as a good shop skin (rare, epic or legendary)'
                                    % (reward.get('id'), item.get('rarity')))
        else:
            problems.append('reward must be {"type": "coins", "amount": N} or {"type": "skin", "id": "..."}')
        add('limited_level_%d' % n, not problems, 'reward %s' % reward if not problems else 'level %d: %s' % (n, '; '.join(problems)))
    rewards = {str((by[n].get('reward') or {}).get('id')): n for n in limited if (by[n].get('reward') or {}).get('type') == 'skin'}
    bonus = sorted(n for n in by if by[n]['type'] == 'bonus')
    problems = []
    seed = plan.get('seed')
    if type(seed) is not int:
        problems.append('the plan needs its "seed" (make_level_plan.py): the bonus places are drawn from it')
    else:
        want = sorted(bonus_places(seed, total, every))
        if bonus != want:
            problems.append('bonus levels %s are not the places drawn from seed %d (%s): one per block of 10, keep the '
                            'generator\'s places or draw new ones with another --seed' % (bonus, seed, want))
    for n in bonus:
        if n <= 3:
            problems.append('bonus level %d: not in levels 1-3' % n)
        if {n - 1, n + 1} & set(limited):
            problems.append('bonus level %d is next to a limited level' % n)
    for start, end in chapters(every, total):
        inside = [n for n in bonus if start <= n <= end]
        full = end - start + 1 >= 10
        if len(inside) > 1 or (full and not inside):
            problems.append('levels %d-%d have %d bonus levels (exactly one per block of 10)' % (start, end, len(inside)))
        block = [by[k] for k in range(start, end + 1) if by[k]['type'] == 'normal']
        if block:
            easiest = min(c['difficulty'] for c in block)
            mid_c = statistics.median(c['coins'] for c in block)
            for n in inside:
                if by[n]['difficulty'] > easiest:
                    problems.append('bonus level %d is not very easy (%s; the easiest normal level of its block is %s): make it easy'
                                    % (n, by[n]['difficulty'], easiest))
                if not 2.9 * mid_c <= by[n]['coins'] <= 3.5 * mid_c:
                    problems.append('bonus level %d gives %d, needs 3x the block median (%d; the x2 ad then makes it 6x)'
                                    % (n, by[n]['coins'], 3 * mid_c))
    bp = plan.get('bonus_levels_policy') if isinstance(plan.get('bonus_levels_policy'), dict) else None
    bonus_authorized = bool(bonus) is False and bp is not None and bp.get('mode') == 'milestones_only' \
        and len(str(bp.get('authorized_by', '')).strip()) >= 6 and len(str(bp.get('reason', '')).strip()) >= 30
    if bonus_authorized:
        add('bonus_levels', True, 'OVERRIDE milestones_only (authorized by %s): no separate easy bonus levels; the authorized design '
            'keeps only the milestone stages, whose rewards are the milestone skins/gifts (%s)' % (bp.get('authorized_by'), str(bp.get('reason'))[:140]))
    else:
        add('bonus_levels', not problems, 'bonus levels %s' % bonus if not problems else '; '.join(problems[:12]))
    if items is not None:
        clash = []
        for it in items:
            unlock, cond = str(it.get('unlock', '')).lower(), str(it.get('condition', '')).lower()
            group, lv = str(it.get('group', '')).lower(), it.get('level')
            if unlock != 'level':
                continue
            if cond == 'perfect':
                clash.append('%s: no perfect-clear skins (user 2026-10-22); skins are won on limited levels' % it.get('id'))
            elif group not in MAP_GROUPS and str(it.get('id')) not in rewards:
                clash.append('%s: a level skin must be the reward of its limited level in level_plan.json (level %s)' % (it.get('id'), lv))
            elif type(lv) is int and lv not in limited:
                clash.append('%s: a new map unlocks on a limited level (chapter end %s), not level %d' % (it.get('id'), limited[:4], lv))
        add('unlock_table_levels', not clash, 'unlock_table level items fit the plan' if not clash else '; '.join(clash[:6]))
    return mode


def audit_dumps(dumps, mode, total, add):
    maps = [d for d in dumps if d.get('purpose') == 'map']
    if mode == 'endless':
        add('endless_no_map', not maps, 'endless game: no map page' if not maps else
            'endless game but %d map dumps: endless games have no level map (start from the home page)' % len(maps))
        return
    if not maps:
        add('map_page', False, 'a level game needs a map page: read it with chrome_touch dump_ui and "purpose": "map"')
        return
    pat = re.compile(r'(?<![\d,])%d(?![\d,])' % total)
    shown = [node_text(n) for d in maps for n in d.get('nodes', []) if pat.search(node_text(n)) and n.get('opacity', 1) > 0.05]
    add('map_shows_total', bool(shown), 'map shows the total: "%s"' % shown[0] if shown else
        'the map must show how many levels there are in total (e.g. "12 / %d" or "%d Levels"); no text with %d found'
        % (total, total, total))


def preserved_levels(proj, plan, binding, add):
    """Validate original levels instead of adding unauthorised map/economy mechanics."""
    from maintenance_scope import audit_scope, checked_ref, source_inventory
    try:
        scope_path=proj/'docs/maintenance-scope.json'
        scope, errors=audit_scope(scope_path,proj,binding)
        if errors:raise ValueError('; '.join(errors))
        base=proj/'docs/levels'
        original=checked_ref(plan['original_data'],base)
        current=checked_ref(plan['current_data'],base)
        if not current.is_relative_to(proj/'assets') or current.read_bytes()!=original.read_bytes():raise ValueError('original/current level data must be byte-identical')
        rows=json.loads(current.read_text());total=len(rows)
        if set(rows)!={str(i) for i in range(1,total+1)} or total<70 or plan.get('total_levels')!=total:raise ValueError('all original numeric level records, >=70, required')
        result_path=checked_ref(plan['runtime_result'],base);runtime=json.loads(result_path.read_text())
        if runtime.get('execution_binding')!=binding:raise ValueError('level runtime belongs to another build')
        observed=runtime.get('results',[])
        if {x.get('level') for x in observed}!=set(range(1,total+1)) or len(observed)!=total:raise ValueError('every original level must load in the current runtime')
        if any(not x.get('loaded') or not x.get('backgroundCorrect') or x.get('error') or x.get('errors') for x in observed):raise ValueError('unloaded level, wrong background or runtime error')
        samples=[x for x in observed if x.get('sampled')]
        if len(samples)<43 or any(not x.get('trustedEvents') or not any(t.get('trusted') is True for t in x['trustedEvents']) for x in samples):raise ValueError('>=43 real-touch level samples and original trusted event traces required')
        source_inventory(scope['source_inventory'],scope_path.parent,proj,binding)
        add('preserved_level_data',True,'%d original records unchanged; every board/background loaded, %d real-touch samples'%(total,len(samples)))
        add('preserved_routes',True,'Current source and two-ratio GUI verify original direct play/progress routes; no unrequested map or bonus economy injected')
        return True
    except (ValueError,OSError,KeyError,TypeError) as exc:
        add('preserved_level_data',False,str(exc));return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--plan', type=Path)
    ap.add_argument('--dumps', type=Path, nargs='*', help='folders with chrome_touch dump_ui files (default <project>/docs/test)')
    ap.add_argument('--board', choices=['localize', 'remake'], help='default: docs/board.txt')
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    proj = a.project.resolve()
    board = a.board
    if not board and (proj / 'docs/board.txt').is_file():
        board = (proj / 'docs/board.txt').read_text(encoding='utf-8').strip().lower() or None
    if not (proj / 'assets').is_dir():
        ap.error('%s is not a Cocos project (no assets folder)' % proj)
    checks = []

    def add(cid, ok, detail):
        checks.append({'id': cid, 'passed': bool(ok), 'detail': detail})

    plan_path = a.plan or find_plan(proj)
    mode = None
    if not plan_path or not plan_path.is_file():
        add('mode_recorded', False, 'level plan missing: write %s (make_level_plan.py; endless games too, with mode "endless")' % PLAN_PATHS[0])
    else:
        try:
            plan = json.loads(plan_path.read_text(encoding='utf-8-sig'))
            items = table_items(proj)
        except (OSError, ValueError) as exc:
            ap.error('cannot read the plan or unlock_table.json: %s' % exc)
        maintenance = plan.get('schema') == 'preserved_level_plan.v1'
        if maintenance:
            binding=json.loads(a.binding.read_text()).get('binding') if a.binding else None
            preserved_levels(proj,plan,binding,add);mode='levels'
        else:mode = audit_plan(plan if isinstance(plan, dict) else {}, items, add, board)
        if not maintenance and mode in ('levels', 'endless') and all(c['passed'] for c in checks if c['id'] in ('mode_recorded', 'structure')):
            folders = [f for f in (a.dumps or [proj / 'docs/test']) if Path(f).is_dir()]
            audit_dumps(load_dumps(folders), mode, plan.get('total_levels'), add)
    failed = [c for c in checks if not c['passed']]
    report = {'tool': 'audit_level_plan', 'schema': 1, 'mode': mode, 'plan': str(plan_path) if plan_path else None,
              'checks': checks, 'checked': len(checks), 'failed': len(failed), 'passed': not failed and bool(checks),
              'status': 'pass' if not failed and checks else 'fail',
              'boundary': 'Plan numbers, unlock table and map-page text from dump_ui. The map markers, bonus level '
                          'and reward popup are checked in the browser (LEVEL-02).'}
    if a.binding:
        try:
            b = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
        except (OSError, ValueError) as exc:
            ap.error('binding: %s' % exc)
        if not isinstance(b, dict):
            ap.error('no binding object in %s' % a.binding)
        report['binding'] = b
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'mode': mode, 'checked': len(checks), 'failed': len(failed),
                      'found': [{'id': c['id'], 'detail': c['detail'][:200]} for c in failed][:8], 'report': str(a.out)}, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
