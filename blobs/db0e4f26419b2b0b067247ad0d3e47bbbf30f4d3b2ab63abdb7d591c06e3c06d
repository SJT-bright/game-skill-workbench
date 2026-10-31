#!/usr/bin/env python3
"""Wave difficulty with tiers (remake-levels/references/difficulty-curve.md). Two versions, told apart by the plan's
"difficulty_policy":

wave-tiers.v2 (default from v7.8, Saul 2026-10-29): levels 1-2 are tutorial levels, level 3 is already a hard level
(high, role "first-hard"), and from level 3 on no level is as easy as levels 1-2. There is no level-4 spike and no
5-9 recovery any more: levels 4+ are one irregular wave of low/medium/high/extreme in the ratio 25/45/15/15 (non-bonus
levels from level 3 on); every limited level (10, 20, ...) is a high chapter exam.

wave-tiers.v1 (user 2026-10-27, plans made before v7.8; still generated with --policy wave-v1 and still audited by its
own rules, so games already planned on it are not reworked): levels 1-3 tutorial, level 4 the first spike, levels 5-9
step down (recovery), level 10 the chapter exam, then the wave from level 11.

Both: a new mechanic's first level (tag "intro") is low, the next level is medium practice, the level before it is a
high exam; never two high/extreme in a row, never more than five medium or three low in a row; every chapter's median
is above the previous one. Difficulty = slowly rising baseline x tier factor. Shared by make_level_plan.py (writes it)
and audit_level_plan.py (checks it).
"""
import random

POLICY = 'wave-tiers.v2'          # default (Saul 2026-10-29: levels 1-2 teach, level 3 is already hard)
POLICY_V1 = 'wave-tiers.v1'       # older plans: tutorial 1-3, spike 4, recovery 5-9
POLICIES = (POLICY, POLICY_V1)
TIERS = ('tutorial', 'low', 'medium', 'high', 'extreme')
RANK = {t: i for i, t in enumerate(TIERS)}
FACTOR = {'low': 0.8, 'medium': 1.0, 'high': 1.3, 'extreme': 1.6}
RATIO = {'low': 0.25, 'medium': 0.45, 'high': 0.15, 'extreme': 0.15}
HARD = ('high', 'extreme')
# level -> (tier, role, difficulty)
OPENING_V1 = {1: ('tutorial', 'tutorial', 0.6), 2: ('tutorial', 'tutorial', 0.7), 3: ('tutorial', 'tutorial', 0.8),
              4: ('high', 'first-spike', 1.6), 5: ('medium', 'recovery', 1.25), 6: ('medium', 'recovery', 1.15),
              7: ('low', 'recovery', 1.05), 8: ('low', 'recovery', 1.0), 9: ('low', 'recovery', 0.95),
              10: ('high', 'chapter-exam', 1.55)}
OPENING = OPENING_V1               # old name, kept for callers of v1
OPENING_V2 = {1: ('tutorial', 'tutorial', 0.6), 2: ('tutorial', 'tutorial', 0.7)}
TUTORIAL_LAST = {POLICY: 2, POLICY_V1: 3}
FIRST_HARD = 3                     # v2: the first hard level
MAX_RUN = {'medium': 5, 'low': 3}
NO_BONUS = 4       # never a bonus level: v1 = the first spike, v2 = the level right after the first hard level
SPIKE = NO_BONUS   # old name (v1)


def baseline(n):
    return 1 + (n - 1) * 0.05


def value(n, tier):
    return round(baseline(n) * FACTOR[tier], 2)


def targets(count):
    """Integer tier counts for `count` levels by largest remainder."""
    raw = {t: RATIO[t] * count for t in RATIO}
    out = {t: int(raw[t]) for t in raw}
    for t in sorted(raw, key=lambda t: (raw[t] - out[t], RATIO[t]), reverse=True)[:count - sum(out.values())]:
        out[t] += 1
    return out


def run_ok(seq):
    """seq: list of tiers (None = still open). Checks hard-adjacency and run limits on the filled part."""
    prev, run = None, 0
    for t in seq:
        if t is None:
            prev, run = None, 0
            continue
        if prev in HARD and t in HARD:
            return False
        run = run + 1 if t == prev else 1
        if t in MAX_RUN and run > MAX_RUN[t]:
            return False
        prev = t
    return True


def values_rise(levels, values):
    blocks = {}
    for n, v in zip(levels, values):
        blocks.setdefault((n - 1) // 10, []).append(v)
    meds = [sorted(v)[len(v) // 2] for k, v in sorted(blocks.items()) if len(v) >= 5]
    return all(b > a for a, b in zip(meds, meds[1:]))


def medians_rise(levels, tiers, policy=POLICY_V1):
    return values_rise(levels, [difficulty_of(n, t, policy) for n, t in zip(levels, tiers)])


def opening(policy):
    """(fixed opening rows, last fixed level, last level whose mechanics the opening teaches)."""
    if policy == POLICY_V1:
        return OPENING_V1, 10, 10
    if policy == POLICY:
        return OPENING_V2, TUTORIAL_LAST[POLICY], FIRST_HARD
    raise ValueError('unknown difficulty_policy %r (use %s)' % (policy, ' or '.join(POLICIES)))


def schedule(total, bonus, limited, intros, seed, policy=POLICY):
    """Return {level: (tier, role)} for every non-bonus level 1..total. Raises ValueError when constraints clash."""
    head, cut, taught = opening(policy)
    levels = [n for n in range(1, total + 1) if n not in bonus]
    fixed = {n: (head[n][0], head[n][1]) for n in levels if n <= cut}
    later = [n for n in levels if n > cut]
    pos = {n: i for i, n in enumerate(later)}
    if policy == POLICY and FIRST_HARD in pos:
        fixed[FIRST_HARD] = ('high', 'first-hard')       # Saul 2026-10-29: level 3 is already hard
    for n in limited:
        if n > cut and n in pos:
            fixed[n] = ('high', 'chapter-exam' if n != total else 'finale')
    for n in sorted(intros):
        if n <= taught:
            continue                                     # opening mechanics are taught by the tutorial
        if n not in pos:
            raise ValueError('level %d cannot introduce a mechanic (bonus level)' % n)
        if n in fixed:
            raise ValueError('level %d is a limited level; introduce mechanics on a normal level' % n)
        fixed[n] = ('low', 'intro')
        i = pos[n]
        if i + 1 < len(later) and later[i + 1] not in fixed:
            fixed[later[i + 1]] = ('medium', 'practice')
        if i - 1 >= 0 and later[i - 1] not in fixed:
            before = later[i - 2] if i >= 2 else cut
            if fixed.get(before, (None,))[0] not in HARD:
                fixed[later[i - 1]] = ('high', 'pre-mechanic-exam')
    want = targets(len(later))
    for n in later:
        if n in fixed:
            want[fixed[n][0]] = max(0, want[fixed[n][0]] - 1)
    open_slots = [n for n in later if n not in fixed]
    if sum(want.values()) != len(open_slots):            # fixed nodes overshoot a tier; fill the gap with medium
        want['medium'] += len(open_slots) - sum(want.values())
        if want['medium'] < 0:
            raise ValueError('too many fixed exam/intro levels for the tier ratio')
    rng = random.Random(seed * 7919 + 17)
    hard_left = want['high'] + want['extreme']
    for _ in range(4000):
        tiers = {n: fixed[n][0] for n in later if n in fixed}
        # 1) hard levels first: never next to another hard level
        slots = open_slots[:]
        rng.shuffle(slots)
        picked = set()
        for n in slots:
            if len(picked) == hard_left:
                break
            i = pos[n]
            near = [later[j] for j in (i - 1, i + 1) if 0 <= j < len(later)]
            if any(m in picked or tiers.get(m) in HARD for m in near):
                continue
            picked.add(n)
        if len(picked) < hard_left:
            continue
        kinds = ['high'] * want['high'] + ['extreme'] * want['extreme']
        rng.shuffle(kinds)
        for n, t in zip(sorted(picked), kinds):
            tiers[n] = t
        # 2) low/medium in the gaps, keeping the run limits
        pool = {'low': want['low'], 'medium': want['medium']}
        ok = True
        for n in open_slots:
            if n in tiers:
                continue
            left = sum(pool.values())
            choices = sorted((t for t in pool if pool[t] > 0), key=lambda t: -pool[t] / max(1, left) * rng.random())
            for t in choices:
                tiers[n] = t
                if run_ok([tiers.get(m) for m in later[max(0, pos[n] - 6):pos[n] + 2]]):
                    pool[t] -= 1
                    break
                del tiers[n]
            else:
                ok = False
                break
        if not ok or not run_ok([tiers[n] for n in later]):
            continue
        if not medians_rise(levels, [head[n][0] if n <= cut else tiers[n] for n in levels], policy):
            continue
        out = {n: (head[n][0], head[n][1]) for n in levels if n <= cut}
        for n in later:
            out[n] = (tiers[n], fixed[n][1] if n in fixed else 'wave')
        return out
    raise ValueError('could not place tiers under the wave rules; move the intro levels apart')


def difficulty_of(n, tier, policy=POLICY):
    head, cut, _ = opening(policy)
    return head[n][2] if n <= cut else value(n, tier)


def problems(rows, total, policy=POLICY_V1):
    """Audit rows of a plan by its difficulty_policy (bonus rows excluded by the caller). The default is v1 because
    callers that do not pass a policy are older than v2."""
    if policy == POLICY:
        return problems_v2(rows, total)
    return problems_v1(rows, total)


def problems_v1(rows, total):
    """Audit rows of a plan with difficulty_policy wave-tiers.v1 (bonus rows excluded by the caller)."""
    out = []
    by = {r['level']: r for r in rows}
    for r in rows:
        if r.get('tier') not in TIERS:
            out.append('level %d needs tier tutorial|low|medium|high|extreme' % r['level'])
    if out:
        return out
    for n, r in by.items():
        if (r['tier'] == 'tutorial') != (n <= 3):
            out.append('level %d: only levels 1-3 are tutorial levels' % n)
    if 4 in by:
        four = by[4]
        if four['tier'] not in HARD or any(four['difficulty'] <= by[k]['difficulty'] for k in (3, 5, 6, 7, 8, 9) if k in by):
            out.append('level 4 is the first spike: high/extreme and harder than levels 3 and 5-9')
    rec = [by[k] for k in range(5, 10) if k in by]
    if any(r['tier'] in HARD for r in rec) or any(b['difficulty'] > a['difficulty'] + 1e-9 for a, b in zip(rec, rec[1:])):
        out.append('levels 5-9 are the recovery: low/medium and stepping down')
    if 10 in by and by[10]['tier'] not in HARD:
        out.append('level 10 is the chapter exam before new content: high/extreme')
    later = [by[n] for n in sorted(by) if n > 10]
    seq = [r['tier'] for r in later]
    prev = None
    run = 0
    for r in later:
        t = r['tier']
        if prev in HARD and t in HARD:
            out.append('levels %d: two high/extreme levels in a row; put a low/medium level between' % r['level'])
        run = run + 1 if t == prev else 1
        if t in MAX_RUN and run > MAX_RUN[t]:
            out.append('level %d: more than %d %s levels in a row' % (r['level'], MAX_RUN[t], t))
        prev = t
    for i, r in enumerate(later):
        if 'intro' in (r.get('tags') or []):
            if r['tier'] != 'low':
                out.append('level %d introduces a mechanic: make it low' % r['level'])
            if i + 1 < len(later) and later[i + 1]['tier'] != 'medium':
                out.append('level %d follows a mechanic intro: make it medium practice' % later[i + 1]['level'])
    for a, b in zip(later, later[1:]):
        ra, rb = RANK[a['tier']], RANK[b['tier']]
        if (rb > ra and b['difficulty'] <= a['difficulty']) or (rb < ra and b['difficulty'] >= a['difficulty']):
            out.append('level %d: difficulty %s does not match tier %s after level %d (%s, %s)'
                       % (b['level'], b['difficulty'], b['tier'], a['level'], a['difficulty'], a['tier']))
    if seq:
        want = targets(len(seq))
        slack = max(2, round(len(seq) * 0.05))
        got = {t: seq.count(t) for t in RATIO}
        off = {t: (got[t], want[t]) for t in RATIO if abs(got[t] - want[t]) > slack}
        if off:
            out.append('tier ratio after level 10 should be about 25/45/15/15 (got/want %s)' % off)
    levels = sorted(by)
    if not values_rise(levels, [by[n]['difficulty'] for n in levels]):
        out.append('a chapter is not harder overall than the one before it (median difficulty must rise chapter by chapter)')
    return out


def problems_v2(rows, total):
    """Audit rows of a plan with difficulty_policy wave-tiers.v2 (bonus rows excluded by the caller): levels 1-2
    tutorial, level 3 already hard, nothing from level 3 on as easy as levels 1-2, every limited level hard, then the
    same wave rules as v1 from level 3 on (no level-4 spike, no 5-9 recovery)."""
    out = []
    by = {r['level']: r for r in rows}
    for r in rows:
        if r.get('tier') not in TIERS:
            out.append('level %d needs tier tutorial|low|medium|high|extreme' % r['level'])
    if out:
        return out
    last = TUTORIAL_LAST[POLICY]
    for n, r in by.items():
        if (r['tier'] == 'tutorial') != (n <= last):
            out.append('level %d: only levels 1-2 are tutorial levels (Saul 2026-10-29: level 3 is already hard)' % n)
    if FIRST_HARD in by and by[FIRST_HARD]['tier'] not in HARD:
        out.append('level 3 is the first hard level (Saul 2026-10-29: levels 1-2 teach, level 3 is already hard): '
                   'make it high/extreme')
    teach = [by[n]['difficulty'] for n in range(1, last + 1) if n in by]
    if teach:
        floor = max(teach)
        easy = [n for n in sorted(by) if n > last and by[n]['difficulty'] <= floor]
        if easy:
            out.append('levels %s are as easy as the tutorial levels 1-2 (difficulty <= %s): from level 3 on no level '
                       'drops back to tutorial ease' % (easy[:8], floor))
    for n in sorted(by):
        if by[n].get('type') == 'milestone' and by[n]['tier'] not in HARD:
            out.append('level %d is a limited level (chapter exam): high/extreme' % n)
    later = [by[n] for n in sorted(by) if n > last]
    seq = [r['tier'] for r in later]
    prev = None
    run = 0
    for r in later:
        t = r['tier']
        if prev in HARD and t in HARD:
            out.append('levels %d: two high/extreme levels in a row; put a low/medium level between' % r['level'])
        run = run + 1 if t == prev else 1
        if t in MAX_RUN and run > MAX_RUN[t]:
            out.append('level %d: more than %d %s levels in a row' % (r['level'], MAX_RUN[t], t))
        prev = t
    for i, r in enumerate(later):
        if r['level'] > FIRST_HARD and 'intro' in (r.get('tags') or []):
            if r['tier'] != 'low':
                out.append('level %d introduces a mechanic: make it low' % r['level'])
            if i + 1 < len(later) and later[i + 1]['tier'] != 'medium':
                out.append('level %d follows a mechanic intro: make it medium practice' % later[i + 1]['level'])
    for a, b in zip(later, later[1:]):
        ra, rb = RANK[a['tier']], RANK[b['tier']]
        if (rb > ra and b['difficulty'] <= a['difficulty']) or (rb < ra and b['difficulty'] >= a['difficulty']):
            out.append('level %d: difficulty %s does not match tier %s after level %d (%s, %s)'
                       % (b['level'], b['difficulty'], b['tier'], a['level'], a['difficulty'], a['tier']))
    if seq:
        want = targets(len(seq))
        slack = max(2, round(len(seq) * 0.05))
        got = {t: seq.count(t) for t in RATIO}
        off = {t: (got[t], want[t]) for t in RATIO if abs(got[t] - want[t]) > slack}
        if off:
            out.append('tier ratio from level 3 on should be about 25/45/15/15 (got/want %s)' % off)
    levels = sorted(by)
    if not values_rise(levels, [by[n]['difficulty'] for n in levels]):
        out.append('a chapter is not harder overall than the one before it (median difficulty must rise chapter by chapter)')
    return out
