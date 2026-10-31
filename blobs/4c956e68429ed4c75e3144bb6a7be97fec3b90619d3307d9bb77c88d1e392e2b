#!/usr/bin/env python3
"""Design-stage level checks. Localization compares real original/current data and never adds levels
(英化不补关, Saul 2026-10-28; replaces the 2026-10-24 rule "pad to 70"): production keeps exactly the original
records, count and order. Levels the user asked to add are a separate task, recorded as explicit_total in the plan.
New designs use the documented milestone/bonus template.
Original JSON preservation/count checks do not prove puzzle solvability or real input; use the
project's existing solver and affected runtime samples. No automatic full-game replay.
"""
import argparse
import json
from pathlib import Path
import re
import statistics
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_page_richness import load as load_dumps, text as node_text  # noqa: E402
from make_level_plan import bonus_places  # noqa: E402

PLAN_PATHS = ('assets/resources/config/level_plan.json', 'docs/levels/level_plan.json')
TABLE_PATHS = ('assets/resources/config/unlock_table.json', 'docs/economy/unlock_table.json')
EVERY = (10,)          # user 2026-10-23: every 10th level is a limited level
LEVELS = 70            # old 英化 minimum (user 2026-10-24); void since 英化不补关 (Saul 2026-10-28), kept for old imports
REMAKE_LEVELS = 60     # 重塑/new designs: 60 levels or more (Saul 2026-10-29; was 100 from 2026-10-27); check id stays levels_at_least_70
MIN_LEVELS = LEVELS
SKIN_MODES = ('final', 'every_10')   # user 2026-10-24: the two limited-skin formats
BUYABLE = ('ads', 'coins', 'ads_coins', 'ads_or_coins')
MAP_GROUPS = ('map', 'maps', 'world', 'worlds', 'chapter', 'chapters')


from product_contract import limited_levels, reward_errors, REWARD_POLICY


def _every_milestone(plan):
    """User-authorized per-milestone limited skins ( Customs Pigeon 2026-10-24: one limited skin at every 10th level).
    Recorded in level_plan.json as "limited_skin_policy": {mode, authorized_by, reason}; printed in the report."""
    o = plan.get('limited_skin_policy') if isinstance(plan, dict) else None
    return isinstance(o, dict) and o.get('mode') == 'every_milestone' \
        and len(str(o.get('authorized_by', '')).strip()) >= 6 and len(str(o.get('reason', '')).strip()) >= 30


def chapters(every, total):
    """(start, end) of each block of 10: a block ends on a limited level (the last one may be short)."""
    out, start = [], 1
    for end in sorted(set(limited_levels(every, total)) | {total}):
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


WAVE_POLICY = 'rising-mild-wave.v1'   # user 2026-10-27 (first option); plans without a policy keep the strict step-by-step rule
from difficulty_wave import POLICY as TIER_POLICY, POLICIES as TIER_POLICIES, problems as wave_problems  # noqa: E402
# wave-tiers.v2 is the default from v7.8 (Saul 2026-10-29); a plan that records wave-tiers.v1 keeps the v1 rules


def rise_problems(rows, policy=None, limited=()):
    """Strict (no policy): never down, no jump bigger than 3x the usual (median) step.
    rising-mild-wave.v1: same spike cap; a dip is allowed only on the 1st/2nd level after a limited level or on a
    level tagged intro (a new mechanic's first level), it may fall at most 3 usual steps, and every full block of 10 has a higher median."""
    out = []
    steps = [(a, b, b['difficulty'] - a['difficulty']) for a, b in zip(rows, rows[1:])]
    ups = sorted(d for _, _, d in steps if d > 0)
    usual = ups[len(ups) // 2] if ups else 0
    wave = policy == WAVE_POLICY
    recover = {m + k for m in limited for k in (1, 2)}
    for a, b, d in steps:
        if d < -1e-9:
            allowed = wave and (b['level'] in recover or 'intro' in (b.get('tags') or []))
            if not allowed:
                out.append('level %d is easier (%s) than level %d (%s)' % (b['level'], b['difficulty'], a['level'], a['difficulty'])
                           + ('; dips only right after a limited level or on a level tagged intro' if wave else ''))
            elif usual and -d > 3 * usual + 1e-6:
                out.append('level %d dips from %s to %s (usual step %s): a recovery dip is at most 3 usual steps'
                           % (b['level'], a['difficulty'], b['difficulty'], round(usual, 3)))
        elif usual and d > 3 * usual + 1e-6 and d > 0.15 * a['difficulty']:
            out.append('level %d jumps from %s to %s (usual step %s): no spikes, raise it gradually'
                       % (b['level'], a['difficulty'], b['difficulty'], round(usual, 3)))
    if wave and rows:
        blocks = {}
        for r in rows:
            blocks.setdefault((r['level'] - 1) // 10, []).append(r['difficulty'])
        keys = sorted(k for k, v in blocks.items() if len(v) >= 5)
        meds = [(k, sorted(blocks[k])[len(blocks[k]) // 2]) for k in keys]
        for (k0, m0), (k1, m1) in zip(meds, meds[1:]):
            if m1 <= m0 + 1e-9:
                out.append('levels %d-%d are not harder overall than levels %d-%d (median %s vs %s): keep the trend rising'
                           % (k1 * 10 + 1, k1 * 10 + 10, k0 * 10 + 1, k0 * 10 + 10, m1, m0))
    return out


def intro_levels(plan):
    return {r['level'] for r in plan.get('levels', []) if isinstance(r, dict) and 'intro' in (r.get('tags') or [])
            and type(r.get('level')) is int}


def check_base_mode(plan, mode, add):
    """Saul 2026-10-29: a remake follows its original game. Endless original -> endless remake (no map, no
    60+ levels); level original -> level remake. Only checked when the plan records base_game."""
    base = plan.get('base_game')
    if base is None:
        return
    if not isinstance(base, dict) or base.get('mode') not in ('levels', 'endless') \
            or not str(base.get('name', '')).strip() or len(str(base.get('evidence', '')).strip()) < 10:
        add('mode_matches_base', False, 'base_game needs {name, mode levels|endless, evidence (>=10 chars: what in the '
            'original source shows it, e.g. no level table/map, endless score loop)}')
        return
    if base['mode'] == mode:
        add('mode_matches_base', True, '%s, same as original %s (%s)' % (mode, base['name'], str(base['evidence'])[:120]))
        return
    ovr = plan.get('mode_override') if isinstance(plan.get('mode_override'), dict) else None
    if ovr and len(str(ovr.get('authorized_by', '')).strip()) >= 2 and len(str(ovr.get('reason', '')).strip()) >= 30:
        add('mode_matches_base', True, '%s but original %s is %s: OVERRIDE authorized by %s: %s'
            % (mode, base['name'], base['mode'], ovr['authorized_by'], str(ovr['reason'])[:180]))
    else:
        add('mode_matches_base', False, '%s but the original game %s is %s (Saul 2026-10-29: endless original stays '
            'endless, only a level original gets 60+ levels). Regenerate with make_level_plan.py --%s, or record '
            '"mode_override": {authorized_by, reason>=30 chars}' % (mode, base['name'], base['mode'],
                                                                   'endless' if base['mode'] == 'endless' else 'levels 60'))


RESKIN = 'reskin'
RESKIN_WHAT = ('levels', 'difficulty', 'gameplay_code')
BASE_ASSETS = Path('docs') / 'art' / 'base-assets.json'      # W90 (H8): where the base game was recorded
DATE = re.compile(r'^20\d\d-[01]\d-[0-3]\d$')


def is_reskin(plan):
    return isinstance(plan, dict) and plan.get('remake_mode') == RESKIN


def reskin_base(proj, plan):
    """-> (Path of the base folder or source ZIP, where it came from) or (None, why). The plan's reskin.base wins,
    otherwise docs/art/base-assets.json (art_records.py base / tiktok_finalize init --base)."""
    raw = (plan.get('reskin') or {}).get('base') if isinstance(plan.get('reskin'), dict) else None
    where = 'level_plan reskin.base'
    if not raw:
        try:
            raw = json.loads((Path(proj) / BASE_ASSETS).read_text(encoding='utf-8')).get('base')
            where = str(BASE_ASSETS)
        except (OSError, ValueError, AttributeError):
            raw = None
    if not raw or raw == 'none':
        return None, ('no base recorded: write reskin.base in the plan or record it with art_records.py base --project '
                      '<project> --from <base> (tiktok_finalize.py init --base)')
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (Path(proj) / path).resolve()
    if not path.exists():
        return None, 'base %s (from %s) is not on this machine' % (path, where)
    return path, where


def base_reader(base):
    """rel path inside the base project -> bytes or None. A source ZIP is read in place (its project folder is the
    shallowest one holding assets/; a ZIP of ZIPs one level deep)."""
    import io
    import zipfile
    if base.is_dir():
        def read_dir(rel):
            p = base / rel
            return p.read_bytes() if p.is_file() else None
        return read_dir
    from tiktok_finalize_steps.policy import project_base
    zf = zipfile.ZipFile(base)
    if project_base(zf.namelist()) is None:
        for info in zf.infolist():
            if info.filename.lower().endswith('.zip') and '__MACOSX' not in info.filename:
                try:
                    inner = zipfile.ZipFile(io.BytesIO(zf.read(info)))
                except zipfile.BadZipFile:
                    continue
                if project_base(inner.namelist()) is not None:
                    zf = inner
                    break
    prefix = project_base(zf.namelist())
    prefix = prefix + '/' if prefix else ''
    names = set(zf.namelist())

    def read_zip(rel):
        name = prefix + rel
        return zf.read(name) if name in names else None
    return read_zip


def _sha(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def audit_reskin(proj, plan, add):
    """Saul 2026-10-30 (总表 P18 / 22.6): a full reskin may copy the base game's levels, difficulty and gameplay code
    when the plan records remake_mode "reskin" and Saul's approval (who, date, his words). Every copied file must be
    byte-identical to the base (sha256); the 60-level minimum and the level template do not apply. Without the
    approval or with a changed file the reskin checks fail (a changed level is a new level: normal remake rules)."""
    rs = plan.get('reskin') if isinstance(plan.get('reskin'), dict) else {}
    ok_by = rs.get('approval') if isinstance(rs.get('approval'), dict) else {}
    approved = 'saul' in str(ok_by.get('by', '')).lower() and bool(DATE.match(str(ok_by.get('date', '')))) \
        and len(str(ok_by.get('quote', '')).strip()) >= 4
    add('reskin_approved', approved,
        'reskin approved by %s on %s: “%s”' % (ok_by.get('by'), ok_by.get('date'), str(ok_by.get('quote'))[:160])
        if approved else 'remake_mode "reskin" needs reskin.approval {by: "Saul", date: "YYYY-MM-DD", quote: his words} '
        '(Saul 2026-10-30: every reskin needs his OK); without it the game is a normal remake (60 levels, new levels)')
    base, where = reskin_base(proj, plan)
    add('reskin_base', base is not None, 'base %s (%s)' % (base, where) if base else where)
    rows = rs.get('copied') if isinstance(rs.get('copied'), list) else []
    kinds = {r.get('what') for r in rows if isinstance(r, dict)}
    need = {'gameplay_code'} | ({'levels'} if plan.get('mode') == 'levels' else set())
    bad_rows = [r for r in rows if not isinstance(r, dict) or r.get('what') not in RESKIN_WHAT
                or not str(r.get('base_path') or '').strip()]
    listed = bool(rows) and need <= kinds and not bad_rows
    add('reskin_copied_listed', listed,
        '%d copied files (%s)' % (len(rows), ', '.join(sorted(k for k in kinds if k))) if listed else
        'reskin.copied must list every copied file as {what: levels|difficulty|gameplay_code, base_path, project_path '
        '(default = base_path), sha256}; needs %s, found %s%s' % (sorted(need), sorted(k for k in kinds if k),
                                                                 ', %d bad rows' % len(bad_rows) if bad_rows else ''))
    diffs = ['base not readable'] if base is None else []
    if base is not None:
        try:
            read = base_reader(base)
        except Exception as exc:  # noqa: BLE001 - an unreadable base fails the check, never passes it
            read, diffs = None, ['base %s not readable: %r' % (base, exc)]
        for r in rows if read else []:
            if not isinstance(r, dict) or not r.get('base_path'):
                continue
            rel_b = str(r['base_path']).lstrip('/')
            rel_p = str(r.get('project_path') or rel_b).lstrip('/')
            mine, theirs = Path(proj) / rel_p, read(rel_b)
            if theirs is None:
                diffs.append('%s: not in the base' % rel_b)
            elif not mine.is_file():
                diffs.append('%s: not in the project' % rel_p)
            else:
                h = _sha(mine.read_bytes())
                if h != _sha(theirs):
                    diffs.append('%s differs from the base %s (a reskin copies it unchanged; changed levels are new '
                                 'levels: drop remake_mode reskin)' % (rel_p, rel_b))
                elif r.get('sha256') and str(r['sha256']).lower() != h:
                    diffs.append('%s: recorded sha256 %s is not the file (%s)' % (rel_p, str(r['sha256'])[:12], h[:12]))
    same = bool(rows) and not diffs
    add('reskin_same_bytes', same, '%d files byte-identical to the base' % len(rows) if same
        else '; '.join(diffs[:6]) or 'nothing listed in reskin.copied')
    exempt = approved and same and listed
    add('levels_at_least_70', exempt,
        'reskin: the base game\'s %s levels kept unchanged, no 60-level minimum (Saul 2026-10-30)'
        % plan.get('total_levels', '?') if exempt else
        'a reskin is exempt from the 60-level minimum only with Saul\'s approval and byte-identical copies')


def explicit_total(plan, total=None):
    """The level count the user authorized for this game, or None: "explicit_total": {count, authorized_by,
    reason >= 30 chars}; with total given, count must equal it."""
    ovr = plan.get('explicit_total') if isinstance(plan, dict) and isinstance(plan.get('explicit_total'), dict) else None
    if not ovr or type(ovr.get('count')) is not int or (total is not None and ovr['count'] != total):
        return None
    if len(str(ovr.get('authorized_by', '')).strip()) < 6 or len(str(ovr.get('reason', '')).strip()) < 30:
        return None
    return ovr


def localize_level_count(plan, rows, total):
    """英化不补关 (Saul 2026-10-28; replaces the 2026-10-24 rule "pad to 70"): the plan keeps the original count, and
    rows marked "new" are added levels, allowed only when the user asked for them (explicit_total)."""
    added = [r.get('level') for r in rows if isinstance(r, dict) and r.get('new')]
    if not added:
        return True, '%d levels: 英化 keeps the original level count (不补关, Saul 2026-10-28)' % total
    ovr = explicit_total(plan, total)
    if ovr:
        return True, ('%d levels, %d marked "new": OVERRIDE recorded in level_plan.json (authorized by %s): %s'
                      % (total, len(added), ovr.get('authorized_by'), str(ovr.get('reason'))[:180]))
    return False, ('%d levels marked "new" %s: 英化不补关 (Saul 2026-10-28; the 2026-10-24 rule "pad to 70" is void). Remove '
                   'the added levels, or record the levels the user asked for as "explicit_total": {count, authorized_by, '
                   'reason>=30 chars}' % (len(added), added[:8]))


def audit_plan(plan, items, add, board=None, proj=None):
    mode = plan.get('mode')
    if plan.get('schema') != 'level_plan.v1' or mode not in ('levels', 'endless') or not str(plan.get('why', '')).strip() \
            or 'TODO' in str(plan.get('why')):
        add('mode_recorded', False, 'level_plan.json needs schema level_plan.v1, mode levels|endless and why (how you decided)')
        return mode
    add('mode_recorded', True, '%s: %s' % (mode, plan['why']))
    check_base_mode(plan, mode, add)
    if is_reskin(plan) and board != 'localize':           # P18, Saul 2026-10-30: full reskin keeps the base's levels
        audit_reskin(proj or '.', plan, add)
        return mode
    if mode == 'endless':
        return mode
    total, every = plan.get('total_levels'), plan.get('milestone_every')
    rows = plan.get('levels') if isinstance(plan.get('levels'), list) else []
    if type(total) is not int or every not in EVERY or total < every:
        add('structure', False, 'total_levels (>= 10) and milestone_every 10 are required (user 2026-10-23: every 10th level is a '
            'limited level; found %r, %r)' % (total, every))
        return mode
    minimum = REMAKE_LEVELS
    if board == 'localize':     # 英化不补关 (Saul 2026-10-28): no minimum; added levels need the user's explicit_total
        ok, detail = localize_level_count(plan, rows, total)
    elif total >= minimum:
        ok, detail = True, '%d levels (%d or more: %s)' % (total, minimum, '重塑 Saul 2026-10-29')
    else:
        # User-authorized explicit level count (from-starter SKILL.md: 用户或项目明确关数优先).
        # The plan itself must record who authorized it and why; the override is printed in the report.
        ovr = plan.get('explicit_total') if isinstance(plan.get('explicit_total'), dict) else None
        if ovr and ovr.get('count') == total and len(str(ovr.get('authorized_by', '')).strip()) >= 6 \
                and len(str(ovr.get('reason', '')).strip()) >= 30:
            ok, detail = True, ('%d levels: OVERRIDE recorded in level_plan.json (authorized by %s): %s — skill default is %d; '
                                'kept because 用户或项目明确关数优先' % (total, ovr.get('authorized_by'), str(ovr.get('reason'))[:180], minimum))
        else:
            ok, detail = False, ('%d levels: this board needs %d levels or more (重塑 60, Saul 2026-10-29; 英化不补关), add at least %d '
                                 '(new levels in the starter gameplay, each one proven solvable). A user-authorized '
                                 'count must be recorded as "explicit_total": {count, authorized_by, reason>=30 chars}' % (total, minimum, minimum - total))
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
    reward_failures = reward_errors(plan)
    add('seeded_currency_rewards', not reward_failures, '; '.join(reward_failures[:8]) if reward_failures else 'seeded reward policy, bounds and stored values verified')
    climb = [by[n] for n in sorted(by) if by[n]['type'] != 'bonus']
    note = ''
    if board == 'localize':
        climb = [r for r in climb if r.get('new')]
        note = '（英化：原关卡顺序不改，只查新加的 %d 关）' % len(climb)
    limited = limited_levels(every, total)
    policy = plan.get('difficulty_policy')
    if policy in TIER_POLICIES:
        problems = wave_problems(climb, total, policy)
        ok_text = ('wave-tiers.v2: tutorial 1-2, level 3 already hard, every limited level a hard exam, irregular '
                   '25/45/15/15 wave from level 3' if policy == TIER_POLICY else
                   'wave-tiers.v1 (plan made before v7.8): tutorial 1-3, spike 4, recovery 5-9, exam 10, irregular '
                   '25/45/15/15 wave after it')
    else:
        problems = rise_problems(climb, policy, limited)
        ok_text = ('difficulty rises with mild recovery dips after limited levels, no spikes' if policy == WAVE_POLICY
                   else 'difficulty rises step by step, no spikes')
    add('difficulty_rises', not problems, (ok_text + note) if not problems else '; '.join(problems[:6]))
    wrong = [n for n in by if (by[n]['type'] == 'milestone') != (n in limited)]
    add('limited_every_%d' % every, not wrong, 'limited levels at %s' % limited if not wrong else
        'type "milestone" must be exactly levels %s (every %d; incomplete tail ends at %d without extra milestone); wrong: %s'
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
                if not (plan.get('reward_policy')==REWARD_POLICY and item.get('unlock')=='coins' and item.get('coins')==50*plan.get('coins_per_level',0) and item.get('ads')==0) and (str(item.get('unlock', '')).lower() != 'level' or str(item.get('condition', '')).lower() != 'clear' \
                        or item.get('level') != n or item.get('ads') or item.get('coins')):
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
        want = sorted(bonus_places(seed, total, every, plan.get('difficulty_policy'), intro_levels(plan)))
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
                if (plan.get('reward_policy') == REWARD_POLICY and by[n]['coins'] != 3 * plan.get('coins_per_level',0)) or (plan.get('reward_policy') not in (REWARD_POLICY,'seeded_band.v1') and not 2.9 * mid_c <= by[n]['coins'] <= 3.5 * mid_c):
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


def original_level_rows(data):
    if isinstance(data,dict) and 'levels'in data:data=data['levels']
    if isinstance(data,dict):
        if set(data)!={str(n)for n in range(1,len(data)+1)}:raise ValueError('original/production dictionary requires contiguous numeric level keys')
        data=[data[str(n)]for n in range(1,len(data)+1)]
    if not isinstance(data,list)or not data or any(not isinstance(r,(dict,list))or not r for r in data):raise ValueError('real nonempty level records required, not only a level count')
    return data

def audit_original_levels(original,current,add,explicit=None):
    """英化不补关 (Saul 2026-10-28; replaces "pad to 70"): production keeps exactly the original records, count and order.
    More maps only with the user's explicit_total (a separate task), and then they must be distinct actual maps."""
    original=original_level_rows(original);current=original_level_rows(current);count=len(original)
    target=explicit['count'] if explicit and type(explicit.get('count')) is int and explicit['count']>count else count
    why='英化不补关, Saul 2026-10-28' if target==count else 'explicit_total authorized by %s'%explicit.get('authorized_by')
    add('levels_at_least_70',len(current)==target,'original %d -> production %d; required %d (%s)'%(count,len(current),target,why))
    add('original_level_data_preserved',current[:count]==original,'original gameplay records and order must remain unchanged; currency uses a separate economic layer')
    if len(current)<=count:return
    def layout(row):
        if isinstance(row,dict):
            row={k:v for k,v in row.items()if k not in ('id','level','index','new','difficulty','coins','name','title','label','description')}
        return json.dumps(row,sort_keys=True)
    seen={layout(r)for r in original};unique=True
    for row in current[count:]:
        value=layout(row)
        if value in seen or value in ('{}','[]'):unique=False
        seen.add(value)
    add('new_actual_maps',len(current)==target and unique,'levels the user asked for (explicit_total): append exactly %d distinct actual maps; changing only IDs/count or repeating old maps cannot fill the gap. Project rules must independently replay all new solutions.'%(target-count))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--plan', type=Path)
    ap.add_argument('--original-levels',type=Path,help='read-only original gameplay JSON, from intake authority')
    ap.add_argument('--current-levels',type=Path,help='actual production gameplay JSON inside project')
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
        elif board=='localize':
            mode='levels'
            try:
                if plan.get('mode')=='endless':mode=audit_plan(plan,items,add,board)
                else:
                    if not a.original_levels or not a.current_levels:raise ValueError('localize requires --original-levels and --current-levels; do not regenerate original maps with make_level_plan.py')
                    original=a.original_levels.resolve();current=a.current_levels.resolve()
                    if not current.is_relative_to(proj):raise ValueError('current levels must be actual production data inside project')
                    audit_original_levels(json.loads(original.read_text()),json.loads(current.read_text()),add,explicit_total(plan))
                    import hashlib
                    checks.append({'id':'original_level_inputs','passed':True,'detail':'structural preservation/count only; new maps still require project-rule solution replay and affected samples','original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'current_sha256':hashlib.sha256(current.read_bytes()).hexdigest()})
            except (OSError,ValueError,TypeError)as exc:add('original_level_data_preserved',False,str(exc))
        else:mode = audit_plan(plan if isinstance(plan, dict) else {}, items, add, board, proj)
        if not maintenance and board!='localize' and mode in ('levels', 'endless') and not is_reskin(plan) \
                and all(c['passed'] for c in checks if c['id'] in ('mode_recorded', 'structure')):
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
