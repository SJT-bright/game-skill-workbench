#!/usr/bin/env python3
"""Write a level plan skeleton (remake-levels/references/top-bar-and-level-map.md + remake-levels/references/level-rules.md, both boards).

Level games (通关型, the level module): new designs have 100 levels or more (user 2026-10-27; 英化 keeps the 70 rule);
difficulty follows wave-tiers.v1 (difficulty_wave.py: tutorial 1-3, spike 4, recovery 5-9, exam 10, then an irregular
low/medium/high/extreme wave 25/45/15/15; remake-levels/references/difficulty-curve.md); every 10th level is a limited level (限定关: 10, 20 ...; an incomplete final chapter adds no milestone;
= floor(total / 10) milestones) whose first clear gives a big reward - a pile of the game's currency (at least the sum of the 5
levels before it). Limited skin, two formats (user 2026-10-24, both allowed): "final" (default) = only the LAST limited
level gives the limited skin, the others coins; "every_10" = every limited level gives its own limited skin
(make_skin_table.py --limited-mode every_10 writes the matching skins, ids <skin>_<level>). In every block of 10 levels
exactly one bonus level (奖励关) at a place
drawn from the game's own random seed (so games differ): very easy, 3x the currency of a normal level (the x2 ad then
makes it 6x). Endless games: no levels, no map.

This generator is for NEW designs. Localization preserves the original actual maps when N>=70, or appends exactly
70-N new actual maps when N<70; do not use this skeleton to relabel/reorder original stages. Check original/current
production JSON with audit_level_plan.py --board localize --original-levels ... --current-levels ... instead.
Mark new mechanic introductions with tags ["intro"] and stable IDs; --intro LEVEL:MECHANIC records them.

Usage:
  python make_level_plan.py --levels 100 --coins 40 [--intro 23:wind] [--limited-skin hero_limited] [--limited-skin-mode final|every_10] [--seed N]
      [--currency Pearls] --out assets/resources/config/level_plan.json
  python make_level_plan.py --endless --why "one run, score keeps growing" --out assets/resources/config/level_plan.json
"""
import argparse
import json
import math
from pathlib import Path
import random


def ceil10(x):
    return int(math.ceil(x / 10.0) * 10)


EVERY = 10                 # user 2026-10-23: 1/10 of the levels are limited levels
BONUS_MULTIPLIER = 3       # bonus level = 3x a normal level (the ad doubles it again: 6x)
MILD_POLICY = 'rising-mild-wave.v1'   # earlier 2026-10-27 option, still accepted with --policy mild
MIN_LEVELS = 100   # user 2026-10-27: new designs (重塑) have 100 levels or more; 英化 keeps its own 70 rule


from product_contract import limited_levels, reward_rows, REWARD_POLICY, MILESTONE_POLICY
from difficulty_wave import POLICY as WAVE_POLICY, SPIKE, schedule, difficulty_of


def blocks(every, total):
    """(start, end) of each block: a block ends on a limited level."""
    out, start = [], 1
    for end in sorted(set(limited_levels(every, total)) | {total}):
        out.append((start, end))
        start = end + 1
    return out


def allowed_places(start, end):
    """Inside one block: never levels 1-3, never the first level after a limited level, never the limited level or the
    level before it."""
    return [n for n in range(max(start + 1, 4), end - 1)]


def bonus_places(seed, total, every=EVERY, policy=None, intros=()):
    """One bonus level in every block that has room (a short last block may have none), drawn from the seed; redrawn
    while every block uses the same place (that would look regular). audit_level_plan.py calls this too.
    With difficulty_policy wave-tiers.v1 the first-spike level 4 and the mechanic intro levels are never bonus levels."""
    rng = random.Random(seed)
    avoid = ({SPIKE} | set(intros)) if policy == WAVE_POLICY else set()
    places = lambda s, e: [n for n in allowed_places(s, e) if n not in avoid]
    spans = [b for b in blocks(every, total) if b[1] - b[0] + 1 == every and places(*b)]
    for _ in range(50):
        picks = [rng.choice(places(s, e)) for s, e in spans]
        offsets = {n - s for n, (s, e) in zip(picks, spans)}
        if len(picks) < 3 or len(offsets) > 1:
            return picks
    return picks


def wave_difficulty(n, limited):
    """rising-mild-wave.v1 base value: +0.1 per level and a limited level one step higher. The recovery dip after a
    limited level is applied by soften_after(), which also knows where the bonus levels are."""
    lin = 1 + (n - 1) * 0.1
    if n in limited:
        lin += 0.1
    return round(lin, 2)


def trend(n):
    return 1 + (n - 1) * 0.1


def next_normal(rows, i, reach=2):
    for j in range(i + 1, min(len(rows), i + 1 + reach)):
        if rows[j]['type'] == 'normal':
            return rows[j]
        if rows[j]['type'] != 'bonus':
            return None
    return None


def soften_after(plan):
    """After a limited level (not the last): the next level dips two steps under the trend, the next normal level one
    step under (skipping a bonus level), then the climb continues. No spikes, no extreme levels."""
    rows = plan['levels']
    limited = [r['level'] for r in rows if r['type'] == 'milestone']
    last = limited[-1] if limited else None
    for i, row in enumerate(rows):
        if row['type'] != 'milestone' or row['level'] == last or i + 1 >= len(rows):
            continue
        first = rows[i + 1]
        if first['type'] != 'normal':
            continue
        first['difficulty'] = round(min(first['difficulty'], trend(first['level']) - 0.2), 2)
        practice = next_normal(rows, i + 1)
        if practice:
            practice['difficulty'] = round(min(practice['difficulty'], trend(practice['level']) - 0.1), 2)


def soften_intros(plan):
    """A new mechanic's first level is easier (two steps under the trend) and the next normal level is the practice
    level (one step under); limited and bonus levels keep their own values."""
    rows = plan['levels']
    for i, row in enumerate(rows):
        if row['level'] == 1 or 'intro' not in row.get('tags', []) or row['type'] != 'normal':
            continue
        row['difficulty'] = round(min(row['difficulty'], trend(row['level']) - 0.2), 2)
        practice = next_normal(rows, i)
        if practice and 'intro' not in practice.get('tags', []):
            practice['difficulty'] = round(min(practice['difficulty'], trend(practice['level']) - 0.1), 2)


def make(levels, coins, limited_skin, seed, currency, every=EVERY, skin_mode='final', intros=None, policy=None):
    policy = policy or WAVE_POLICY
    intros = intros or {}
    plan = {'schema': 'level_plan.v1', 'mode': 'levels', 'why': 'TODO: why this is a level game (fixed levels to clear one by one)',
            'currency': currency, 'total_levels': levels, 'milestone_every': every, 'seed': seed,
            'bonus_multiplier': BONUS_MULTIPLIER, 'limited_skin_mode': skin_mode, 'levels': [],
            'reward_policy': REWARD_POLICY, 'milestone_policy': MILESTONE_POLICY, 'reward_seed': seed, 'coins_per_level': coins,
            'difficulty_policy': policy}
    bonus = set(bonus_places(seed, levels, every, policy, intros))
    limited = limited_levels(every, levels)
    tiers = schedule(levels, bonus, limited, set(intros), seed) if policy == WAVE_POLICY else {}
    rows = {}
    for n in range(1, levels + 1):
        block = sum(1 for m in limited if m < n)
        base = coins
        diff = difficulty_of(n, tiers[n][0]) if n in tiers else wave_difficulty(n, limited)
        if n in limited:
            need = int(math.ceil(sum(rows[k]['coins'] for k in range(max(1, n - 5), n)) / 10.0) * 10)
            row = {'level': n, 'type': 'milestone', 'difficulty': diff, 'coins': base, 'frame': 'TODO: ornate limited-level frame'}
            if limited_skin and skin_mode == 'every_10':
                row['reward'] = {'type': 'skin', 'id': '%s_%d' % (limited_skin, n)}
            elif limited_skin and n == limited[-1]:
                row['reward'] = {'type': 'skin', 'id': limited_skin}
            else:
                row['reward'] = {'type': 'coins', 'amount': need}
        elif n in bonus:
            start = max(m for m in [0] + limited if m < n) + 1
            row = {'level': n, 'type': 'bonus', 'difficulty': round(max(0.5, (1 + (start - 1) * 0.1) * 0.6), 2),
                   'coins': BONUS_MULTIPLIER * base, 'new': True,
                   'bonus': 'TODO: very easy and short, lots of ' + currency.lower() + ' (e.g. a treasure rush); node with the currency icon'}
        else:
            row = {'level': n, 'type': 'normal', 'difficulty': diff, 'coins': base}
        if n in tiers:
            row['tier'], row['role'] = tiers[n]
        if n in intros:
            row['tags'] = ['intro']
            row['mechanics'] = list(intros[n])
        rows[n] = row
        plan['levels'].append(row)
    if policy == WAVE_POLICY:
        for row in plan['levels']:                      # a bonus level is easier than every normal level of its block
            if row['type'] == 'bonus':
                start = max(m for m in [0] + limited if m < row['level']) + 1
                end = min([m for m in limited if m >= row['level']] or [levels])
                easiest = min(r['difficulty'] for r in plan['levels'][start - 1:end] if r['type'] != 'bonus')
                row['difficulty'] = round(max(0.3, easiest * 0.8), 2)
    else:
        soften_after(plan)
    rewards = reward_rows(levels, coins, seed, bonus, every)
    for row in plan['levels']:
        row.update(rewards[row['level']])
    for row in plan['levels']:
        if row['type'] == 'milestone' and row.get('reward', {}).get('type') == 'coins':
            row['reward']['amount'] = sum(plan['levels'][k-1]['coins'] for k in range(max(1, row['level']-5), row['level']))
    return plan


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--levels', type=int, default=MIN_LEVELS, help='100 or more for new designs (user 2026-10-27)')
    ap.add_argument('--policy', choices=['wave', 'mild'], default='wave', help='wave = wave-tiers.v1 (default, user 2026-10-27); mild = rising-mild-wave.v1')
    ap.add_argument('--coins', type=int, default=50, help='currency of a normal early level')
    ap.add_argument('--limited-skin', help='id of the limited skin (skin module, unlock "level"): final = the reward of the last '
                    'limited level; every_10 = the id prefix, level n gives <id>_<n>')
    ap.add_argument('--limited-skin-mode', choices=['final', 'every_10'], default='final',
                    help='final: only the last limited level gives the limited skin; every_10: every limited level gives one (user 2026-10-24)')
    ap.add_argument('--intro', action='append', default=[], metavar='LEVEL:MECHANIC',
                    help='first appearance of a gameplay mechanic; repeat for more mechanics, e.g. --intro 17:wind')
    ap.add_argument('--currency', default='Coins', help='the themed currency name, e.g. Pearls for an ocean game')
    ap.add_argument('--seed', type=int, help='random seed of the bonus places (default: a new random one, so every game differs)')
    ap.add_argument('--endless', action='store_true')
    ap.add_argument('--why', default='')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.endless and a.intro:
        ap.error('--intro requires a level game')
    if a.endless:
        plan = {'schema': 'level_plan.v1', 'mode': 'endless', 'why': a.why or 'TODO: why this is an endless game (no levels to clear)'}
    else:
        if a.levels < MIN_LEVELS:
            ap.error('--levels %d: a new level game has %d levels or more (user 2026-10-27); add %d levels first'
                     % (a.levels, MIN_LEVELS, MIN_LEVELS - a.levels))
        seed = a.seed if a.seed is not None else random.SystemRandom().randrange(1, 10 ** 6)
        intros = {}
        for value in a.intro:
            try:
                number, mechanic = value.split(':', 1)
                number = int(number)
                if not 1 <= number <= a.levels or not mechanic.strip():
                    raise ValueError()
            except ValueError:
                ap.error('--intro must be LEVEL:MECHANIC with a valid level and nonempty mechanic ID')
            intros.setdefault(number, []).append(mechanic)
        try:
            plan = make(a.levels, a.coins, a.limited_skin, seed, a.currency, skin_mode=a.limited_skin_mode, intros=intros,
                        policy=WAVE_POLICY if a.policy == 'wave' else MILD_POLICY)
        except ValueError as exc:
            ap.error(str(exc))
    for value in a.intro:
        try:
            number, mechanic = value.split(':', 1)
            number = int(number)
            if not 1 <= number <= a.levels or not mechanic.strip():
                raise ValueError()
        except ValueError:
            ap.error('--intro must be LEVEL:MECHANIC with a valid level and nonempty mechanic ID')
        row = plan['levels'][number - 1]
        row.setdefault('tags', [])
        if 'intro' not in row['tags']:
            row['tags'].append('intro')
        row.setdefault('mechanics', [])
        if mechanic not in row['mechanics']:
            row['mechanics'].append(mechanic)
    if plan['mode'] == 'levels' and plan.get('difficulty_policy') == MILD_POLICY:
        soften_intros(plan)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(plan, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if plan['mode'] == 'levels':
        kinds = {}
        for r in plan['levels']:
            kinds.setdefault(r['type'], []).append(r['level'])
        print(json.dumps({'out': str(a.out), 'seed': plan['seed'], 'limited': kinds.get('milestone', []), 'bonus': kinds.get('bonus', [])}))
    else:
        print(json.dumps({'out': str(a.out), 'mode': 'endless'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
