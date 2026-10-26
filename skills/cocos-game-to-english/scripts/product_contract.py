"""Shared product data rules, independent of project paths and renderer state."""
import random
import statistics
import math

REVISION = '2026-10-26.contracts-v3'
REWARD_POLICY = 'seeded_band.v1'
MILESTONE_POLICY = 'multiples_only.v1'


def limited_levels(every, total):
    if type(every) is not int or every <= 0 or type(total) is not int or total < every:
        raise ValueError('positive chapter size and at least one complete chapter required')
    return list(range(every, total + 1, every))


def limited_skin_count(total, mode):
    if mode not in ('final', 'every_10'):
        raise ValueError('limited skin mode must be final or every_10')
    return 1 if mode == 'final' else len(limited_levels(10, total))


def skin_counts(total=70, mode='final'):
    limited = limited_skin_count(total, mode)
    return {'limited': limited, 'free': 1, 'common': 7, 'rare': 6,
            'epic': 3, 'legendary': 2, 'total': 19 + limited}


def reward_rows(total, base_coins, seed, bonus_levels, every=10):
    """Seeded normal/milestone rolls, then bonus median; no retry-time RNG."""
    if type(total) is not int or total < 1 or type(base_coins) is not int or base_coins < 1 or type(seed) is not int:
        raise ValueError('positive total/base_coins and integer reward_seed required')
    bonus = set(bonus_levels)
    rng = random.Random('reward-v1:'+str(seed))
    rows = {}
    for n in range(1, total + 1):
        base = base_coins + 5*((n-1)//every)
        band = max(1, round(base*.10))
        roll = rng.randint(-band, band)
        rows[n] = {'coins_base': base, 'coins_band': band, 'coins_roll': roll,
                   'coins': base+roll}
    for start in range(1, total+1, every):
        normal = [n for n in range(start, min(start+every, total+1)) if n not in bonus]
        if len(normal) >= 2 and len({rows[n]['coins'] for n in normal}) == 1:
            row = rows[normal[-1]]
            row['coins_roll'] = -row['coins_band'] if row['coins_roll'] != -row['coins_band'] else row['coins_band']
            row['coins'] = row['coins_base']+row['coins_roll']
    # With the chapter base increments, >=70 levels admit at least five values.
    normal = [n for n in rows if n not in bonus]
    if total >= 70 and len({rows[n]['coins'] for n in normal}) < 5:
        used = {rows[n]['coins'] for n in normal}
        for n in normal:
            row = rows[n]
            choices = [x for x in range(-row['coins_band'], row['coins_band']+1) if row['coins_base']+x not in used]
            if choices:
                row['coins_roll'] = choices[0];row['coins'] = row['coins_base']+choices[0];used.add(row['coins'])
            if len(used) >= 5:
                break
    for n in sorted(bonus):
        start = ((n-1)//every)*every+1
        values = [rows[k]['coins'] for k in range(start, min(start+every, total+1)) if k not in bonus and k % every != 0]
        median = math.ceil(statistics.median(values))
        rows[n] = {'coins': 3*int(median), 'chapter_median': int(median)}
    return rows


def reward_errors(plan):
    """Validate deterministic policy, arithmetic, bounds, and immutable seed."""
    errors = []
    if plan.get('reward_policy') != REWARD_POLICY:
        return ['reward_policy must be '+REWARD_POLICY+' for a newly generated plan']
    try:
        rows = plan['levels'];total = plan['total_levels'];seed = plan['reward_seed'];base = plan['coins_per_level']
        expected = reward_rows(total, base, seed, [r['level'] for r in rows if r['type']=='bonus'])
        if plan.get('milestone_policy') != MILESTONE_POLICY:
            errors.append('milestone_policy must be '+MILESTONE_POLICY)
        for row in rows:
            n = row['level']
            for key, value in expected[n].items():
                if type(row.get(key)) is not int or row[key] != value:
                    errors.append('level %s %s differs from seeded reward contract' % (n, key))
        if type(seed) is not int:
            errors.append('reward_seed must be an integer')
    except (KeyError, TypeError, ValueError) as exc:
        errors.append('incomplete reward contract: '+str(exc))
    return errors
