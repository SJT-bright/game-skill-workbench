#!/usr/bin/env python3
"""Write a level plan skeleton (references/top-bar-and-level-map.md + references/game-modules.md 五, both boards).

Level games (通关型, the level module): 70 levels or more (user 2026-10-24: at least 70; more is fine), difficulty rising
step by step (no spikes, limited levels too); every 10th level is a limited level (限定关: 10, 20 ... and the last level
= 1/10 of the levels) whose first clear gives a big reward - a pile of the game's currency (at least the sum of the 5
levels before it). Limited skin, two formats (user 2026-10-24, both allowed): "final" (default) = only the LAST limited
level gives the limited skin, the others coins; "every_10" = every limited level gives its own limited skin
(make_skin_table.py --limited-mode every_10 writes the matching skins, ids <skin>_<level>). In every block of 10 levels
exactly one bonus level (奖励关) at a place
drawn from the game's own random seed (so games differ): very easy, 3x the currency of a normal level (the x2 ad then
makes it 6x). Endless games: no levels, no map.

The skeleton is a starting point: replace difficulty/coins with the real numbers of your levels (英化: the original
levels' numbers; levels you add to reach 70 get "new": true; the bonus levels are new very easy levels put in at the
seeded places, the original levels keep their order; an original with 70 or more keeps all its levels: --levels
<its count>; 重塑 may make more than 70 too); keep the bonus places and the seed (audit_level_plan.py redraws them from
the seed), then run
audit_level_plan.py. Mark each new mechanic first appearance with tags: ["intro"] and stable mechanics IDs;
--intro LEVEL:MECHANIC can record known introductions while generating the skeleton.

Usage:
  python make_level_plan.py --levels 70 --coins 40 [--limited-skin hero_limited] [--limited-skin-mode final|every_10] [--seed N]
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


def limited_levels(every, total):
    """Every 10th level plus the last level (the finale): 10, 20 ... 70."""
    return sorted(set(range(every, total + 1, every)) | {total})


def blocks(every, total):
    """(start, end) of each block: a block ends on a limited level."""
    out, start = [], 1
    for end in limited_levels(every, total):
        out.append((start, end))
        start = end + 1
    return out


def allowed_places(start, end):
    """Inside one block: never levels 1-3, never the first level after a limited level, never the limited level or the
    level before it."""
    return [n for n in range(max(start + 1, 4), end - 1)]


def bonus_places(seed, total, every=EVERY):
    """One bonus level in every block that has room (a short last block may have none), drawn from the seed; redrawn
    while every block uses the same place (that would look regular). audit_level_plan.py calls this too."""
    rng = random.Random(seed)
    spans = [b for b in blocks(every, total) if b[1] - b[0] + 1 >= 6 and allowed_places(*b)]
    for _ in range(50):
        picks = [rng.choice(allowed_places(s, e)) for s, e in spans]
        offsets = {n - s for n, (s, e) in zip(picks, spans)}
        if len(picks) < 3 or len(offsets) > 1:
            return picks
    return picks


def make(levels, coins, limited_skin, seed, currency, every=EVERY, skin_mode='final'):
    plan = {'schema': 'level_plan.v1', 'mode': 'levels', 'why': 'TODO: why this is a level game (fixed levels to clear one by one)',
            'currency': currency, 'total_levels': levels, 'milestone_every': every, 'seed': seed,
            'bonus_multiplier': BONUS_MULTIPLIER, 'limited_skin_mode': skin_mode, 'levels': []}
    bonus = set(bonus_places(seed, levels, every))
    limited = limited_levels(every, levels)
    rows = {}
    for n in range(1, levels + 1):
        block = sum(1 for m in limited if m < n)
        base = coins + 5 * block
        diff = round(1 + (n - 1) * 0.1, 2)                     # rises a little every level, no spikes
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
        rows[n] = row
        plan['levels'].append(row)
    return plan


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--levels', type=int, default=70, help='70 or more (user 2026-10-24: at least 70)')
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
        if a.levels < 70:
            ap.error('--levels %d: a level game has 70 levels or more (user 2026-10-24); add %d levels first' % (a.levels, 70 - a.levels))
        seed = a.seed if a.seed is not None else random.SystemRandom().randrange(1, 10 ** 6)
        plan = make(a.levels, a.coins, a.limited_skin, seed, a.currency, skin_mode=a.limited_skin_mode)
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
