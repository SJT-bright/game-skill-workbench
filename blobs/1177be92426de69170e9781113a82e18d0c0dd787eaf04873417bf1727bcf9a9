#!/usr/bin/env python3
"""Check a collection/skin unlock table against references/rarity-unlock-design.md (user rules 2026-10-20).

Table: a JSON array of items, or {"coins_per_ad": R, "coins_per_level": N, "items": [...]}.
Item: {"id", "group", "order", "rarity", "unlock", "ads", "coins"} plus "level"/"condition" for unlock=level.
unlock: free | ads | coins | ads_coins | ads_or_coins | level
  (league and checkin are gone: no ranking, no 7-day check-in - user 2026-10-23, both boards)

SKIN MODULE (user 2026-10-23, both boards, references/game-modules.md 四): a table with "module": "skin.v1"
(make_skin_table.py writes it) has its groups "skin" (protagonist) and "background" checked by these rules instead:
  - skin: 20 = the limited skin first ("limited": true, rarity "limited", shown dimmed until owned) + the free
    starting skin + 18 for coins (7 common, 6 rare, 3 epic, 2 legendary). Two limited formats (user 2026-10-24, both
    allowed): "final" = one limited skin, won on the last limited level (endless: bought, see below); "every_10" = one
    limited skin per limited level (10, 20 ... last), all of them first in the list, unlock "level" (then 19 + N skins);
    background (when the game has a scene):
    exactly 10 = the free starting one + 9 for coins (3 common, 3 rare, 2 epic, 1 legendary)
  - only coins (no ad-only / ads+coins / either-or skins): ads feed the coins (x2 at every level end, gift box, bonus levels)
  - prices: the first for sale = 2R, every next one = the one before + 1R / 4R / 10R / 20R by its rarity (+-10%)
  - every non-free item has a coin bonus that rises with rarity, bands are errors here: skin 5-10 / 11-20 / 21-32 / 33-50,
    limited 51-60 (above every legendary); background 2-5 / 6-10 / 11-16 / 17-25
  - the limited skin: unlock "level" (condition clear; audit_level_plan.py checks it is the reward of its limited level) or, for
    endless games, "ads_coins" with 5-10 ads and coins >= 1.5x the dearest skin
  A table without the module that has a "skin"/"background" group fails: use make_skin_table.py.
Optional "bonus" (skin bonus, user 2026-10-22): {"type": "coins"|"score", "pct": N} or {"type": "moves"|"time", "amount": N}
  - when one item of a group has a bonus, every non-free item of that group has one, all of the same type
  - pct 1..--max-bonus (default 50); purchasable items: bonus never goes down along display order and every
    higher rarity is above every lower one (like prices); bands are warnings: common 5-10, rare 11-20, epic 21-32, legendary 33-50
  - moves/time bonuses change the game itself: warning, levels must stay solvable with the starting skin
Rules:
  - numbers match the unlock type; at most 8 ads (--max-ads)
  - free items only before paid items; level items need level > 0 and condition clear (user 2026-10-22: no "perfect
    clear gives a skin"; a level skin is the limited-skin reward of a limited level, see audit_level_plan.py)
  - purchasable items: rarity never goes down along display order; >=3 tiers when >=4 items, >=2 when >=2
  - all four purchasable types (ads, coins, ads_coins, ads_or_coins) when a group has >=4 purchasable items
  - per type: higher rarity min > lower rarity max (ads and coins separately); no decrease inside a tier
  - with R (coins_per_ad): value in ad units must fall in the rarity band (tier i -> 2i+1..2i+2, e.g.
    common 1-2, rare 3-4, epic 5-6, legendary 7-8); ads_or_coins coins = ads x R (+-10%)
  - map-style groups (only free + level items): levels increase with display order
R (coins_per_ad) is required when purchasable items exist.
Warnings: cheapest coin item needs more than 5 levels of coins_per_level income.

Legacy mode "alternative" keeps the old check (coin price and ad count as alternative routes, both > 0).

Usage:
  python audit_acquisition_progression.py --table unlock_table.json [--coins-per-ad R] [--coins-per-level N]
      [--rarity-order common,rare,epic,legendary] [--max-ads 8] [--binding review.json] --report result.json
Exit codes: 0 pass, 2 fail or bad input. Configuration only; runtime, ads and saving are checked elsewhere.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
from feature_policy import enabled

UNLOCKS = {'free', 'ads', 'coins', 'ads_coins', 'ads_or_coins', 'level'}
REMOVED = {'league': 'no ranking / Weekly League', 'checkin': 'no 7-day check-in'}   # user 2026-10-23
SKIN_GROUPS = ('skin', 'background')
MODULE_COUNTS = {'skin': {'common': 7, 'rare': 6, 'epic': 3, 'legendary': 2}, 'background': {'common': 3, 'rare': 3, 'epic': 2, 'legendary': 1}}
MODULE_TOTAL = {'skin': 20, 'background': 10}
PRICE_STEPS = {'common': 1, 'rare': 4, 'epic': 10, 'legendary': 20}
MODULE_BANDS = {'skin': {'common': (5, 10), 'rare': (11, 20), 'epic': (21, 32), 'legendary': (33, 50), 'limited': (51, 60)},
                'background': {'common': (2, 5), 'rare': (6, 10), 'epic': (11, 16), 'legendary': (17, 25)}}
BUYABLE = ('ads', 'coins', 'ads_coins', 'ads_or_coins')
LABEL = {'ads': 'ads-only', 'coins': 'coins-only', 'ads_coins': 'ads+coins', 'ads_or_coins': 'ads-or-coins'}
METRICS = {'ads': ('ads',), 'coins': ('coins',), 'ads_coins': ('ads', 'coins'), 'ads_or_coins': ('ads', 'coins')}


def value_in_ads(r, rate):
    if r['unlock'] == 'coins':
        return r['coins'] / rate
    if r['unlock'] == 'ads_coins':
        return r['ads'] + r['coins'] / rate
    return r['ads']


BONUS_TYPES = {'coins': 'pct', 'score': 'pct', 'moves': 'amount', 'time': 'amount'}
BONUS_BANDS = [(5, 10), (11, 20), (21, 32), (33, 50)]


def bonus_value(raw, item, max_bonus):
    if raw in (None, {}, 0):
        return None
    if not isinstance(raw, dict) or raw.get('type') not in BONUS_TYPES:
        raise ValueError(f'{item}: bonus must be {{"type": coins|score, "pct": N}} or {{"type": moves|time, "amount": N}}')
    key = BONUS_TYPES[raw['type']]
    v = raw.get(key)
    if type(v) is not int or v < 1 or (key == 'pct' and v > max_bonus):
        raise ValueError(f'{item}: bonus {key} must be a whole number 1..{max_bonus if key == "pct" else "N"}')
    return raw['type'], v


def audit_bonus(groups, errors, warnings):
    for group, entries in sorted(groups.items()):
        have = [r for r in entries if r.get('bonus')]
        if not have:
            continue
        missing = [r['item'] for r in entries if not r.get('bonus') and r['unlock'] != 'free']
        if missing:
            errors.append(f'Group {group}: skin bonus on some items but not on {", ".join(missing[:6])} (every non-free skin has one)')
        types = {r['bonus'][0] for r in have}
        if len(types) > 1:
            errors.append(f'Group {group}: one bonus type per group, found {", ".join(sorted(types))}')
        if types & {'moves', 'time'}:
            warnings.append(f'Group {group}: {"/".join(sorted(types & {"moves", "time"}))} bonuses change the game: levels must stay '
                            'solvable with the starting skin (design and solve levels without any bonus)')
        buy = sorted([r for r in have if r['unlock'] in BUYABLE], key=lambda r: r['order'])
        for a, b in zip(buy, buy[1:]):
            if b['bonus'][1] < a['bonus'][1]:
                errors.append(f'Group {group}: bonus goes down from {a["item"]} (+{a["bonus"][1]}) to {b["item"]} (+{b["bonus"][1]})')
        by_tier = {}
        for r in buy:
            by_tier.setdefault(r['rank'], []).append(r['bonus'][1])
        ranks = sorted(by_tier)
        for lo, hi in zip(ranks, ranks[1:]):
            if min(by_tier[hi]) <= max(by_tier[lo]):
                errors.append(f'Group {group}: bonus must rise with rarity (tier {hi} min +{min(by_tier[hi])} is not above tier {lo} max +{max(by_tier[lo])})')
        if types <= {'coins', 'score'}:
            for r in buy:
                lo_b, hi_b = BONUS_BANDS[min(r['rank'], 3)]
                if not lo_b <= r['bonus'][1] <= hi_b:
                    warnings.append(f'Group {group}: {r["item"]} {r["rarity"]} bonus +{r["bonus"][1]}% (usual band {lo_b}-{hi_b}%)')


def audit_module_group(group, entries, R, errors):
    """The skin module (references/game-modules.md 四): fixed counts, coins only, the 2R + 1/4/10/20 R price curve,
    bonus bands, the limited skin first."""
    entries = sorted(entries, key=lambda r: r['order'])
    if len({r['order'] for r in entries}) != len(entries):
        errors.append(f'Group {group}: duplicate display order')
    limited = [r for r in entries if r.get('limited')]
    total = MODULE_TOTAL[group]
    every_10 = group == 'skin' and len(limited) > 1 and all(r['unlock'] == 'level' for r in limited)
    if every_10:
        total = MODULE_TOTAL[group] - 1 + len(limited)   # user 2026-10-24: one limited skin per limited level
    if len(entries) != total:
        errors.append(f'Group {group}: the skin module has exactly {total} items, found {len(entries)} (make_skin_table.py)')
    free = [r for r in entries if r['unlock'] == 'free']
    buy = [r for r in entries if not r.get('limited') and r['unlock'] != 'free']
    if group == 'skin':
        if not limited or (len(limited) > 1 and not every_10):
            errors.append(f'Group skin: one limited skin ("final": the last limited level / endless: bought) or one per limited '
                          f'level ("every_10": all unlock "level"), found {len(limited)} (make_skin_table.py --limited-mode)')
        elif entries[:len(limited)] != limited:
            errors.append(f'Group skin: the limited skin(s) {", ".join(r["item"] for r in limited[:4])} come first in the list '
                          '(shown dimmed as a silhouette until owned)')
    elif limited:
        errors.append(f'Group background: no limited item (the limited one is a protagonist skin)')
    if len(free) != 1 or (free and free[0]['rarity'] != 'common'):
        errors.append(f'Group {group}: exactly one free starting item (common), found {len(free)}')
    wrong = [r['item'] for r in buy if r['unlock'] != 'coins']
    if wrong:
        errors.append(f'Group {group}: skins are bought with coins only ({", ".join(wrong[:5])}): ads feed the coins '
                      '(x2 at every level end, the home gift box, bonus levels), see references/game-modules.md')
    counts = {}
    for r in buy:
        counts[r['rarity']] = counts.get(r['rarity'], 0) + 1
    if counts != MODULE_COUNTS[group]:
        errors.append(f'Group {group}: rarities for sale must be {MODULE_COUNTS[group]}, found {counts}')
    for a, b in zip(buy, buy[1:]):
        if b['rank'] < a['rank']:
            errors.append(f'Group {group}: rarity goes down from {a["item"]} ({a["rarity"]}) to {b["item"]} ({b["rarity"]})')
    prices = [r for r in buy if r['unlock'] == 'coins']
    if R and prices:
        if abs(prices[0]['coins'] - 2 * R) > 0.1 * 2 * R:
            errors.append(f'Group {group}: the first item for sale costs 2R = {2 * R:g}, found {prices[0]["coins"]}')
        for a, b in zip(prices, prices[1:]):
            want = PRICE_STEPS.get(b['rarity'], 1) * R
            gap = b['coins'] - a['coins']
            if abs(gap - want) > max(5, 0.1 * want):
                errors.append(f'Group {group}: {b["item"]} ({b["rarity"]}) costs {b["coins"]}, {gap:g} more than {a["item"]}; '
                              f'the step for {b["rarity"]} is {PRICE_STEPS.get(b["rarity"], 1)}R = {want:g} (curve 1R/4R/10R/20R)')
    bands = MODULE_BANDS[group]
    for r in buy + limited:
        b = r.get('bonus')
        lo, hi = bands.get(r['rarity'], (1, 60))
        if not b or b[0] != 'coins':
            errors.append(f'Group {group}: {r["item"]} needs a coin bonus {{"type": "coins", "pct": {lo}-{hi}}}')
        elif not lo <= b[1] <= hi:
            errors.append(f'Group {group}: {r["item"]} {r["rarity"]} bonus +{b[1]}% is outside {lo}-{hi}%')
    for a, b in zip(buy, buy[1:]):
        if a.get('bonus') and b.get('bonus') and b['bonus'][1] < a['bonus'][1]:
            errors.append(f'Group {group}: bonus goes down from {a["item"]} (+{a["bonus"][1]}) to {b["item"]} (+{b["bonus"][1]})')
    for r in limited:
        top = max([x['coins'] for x in prices] or [0])
        if r['unlock'] == 'level':
            if r.get('condition') != 'clear':
                errors.append(f'Group skin: limited skin {r["item"]} is won by clearing its limited level (condition clear)')
        elif r['unlock'] == 'ads_coins':
            if not 5 <= r['ads'] <= 10 or r['coins'] < 1.5 * top:
                errors.append(f'Group skin: endless limited skin {r["item"]} costs >= 1.5x the dearest skin ({1.5 * top:g}) plus 5-10 ads, '
                              f'found {r["coins"]} coins and {r["ads"]} ads')
        else:
            errors.append(f'Group skin: limited skin {r["item"]} unlock must be "level" (level games: its limited level) or '
                          f'"ads_coins" (endless: many coins + >= 5 ads), found {r["unlock"]}')
        legend = [x['bonus'][1] for x in buy if x['rarity'] == 'legendary' and x.get('bonus')]
        if r.get('bonus') and legend and r['bonus'][1] <= max(legend):
            errors.append(f'Group skin: the limited skin bonus +{r["bonus"][1]}% must be above every legendary (+{max(legend)}%)')


def audit_rarity(rows, f, tiers, coins_per_level=None, coins_per_ad=None, max_ads=8, max_bonus=50, module=None, optional=None):
    optional = optional or {}
    errors, warnings, groups, seen = [], [], {}, set()
    if not isinstance(rows, list) or not rows:
        return {'status': 'fail', 'errors': ['Table must be a nonempty array of items'], 'warnings': [], 'groups': []}
    rank = {name.lower(): i for i, name in enumerate(tiers)}
    if module == 'skin.v1':
        rank['limited'] = len(tiers)
    elif module is not None:
        errors.append(f'unknown module {module!r} (the skin module is "skin.v1", make_skin_table.py)')
    for index, row in enumerate(rows):
        try:
            if not isinstance(row, dict):
                raise ValueError('object required')
            item, group = str(row[f['id']]), str(row[f['group']])
            order, ads, coins = row[f['order']], row[f['ads']], row[f['coins']]
            rarity, unlock = str(row[f['rarity']]).lower(), str(row[f['unlock']]).lower()
            if any(type(v) is not int for v in (order, ads, coins)) or min(ads, coins) < 0:
                raise ValueError('order, ads and coins must be non-negative integers')
            if item in seen:
                raise ValueError(f'duplicate item {item}')
            seen.add(item)
            if rarity not in rank:
                raise ValueError(f'unknown rarity {rarity!r} (expected one of {", ".join(tiers)})')
            if unlock in REMOVED and not optional.get(unlock):
                raise ValueError(f'{item}: unlock {unlock!r} is gone ({REMOVED[unlock]}, user 2026-10-23, both boards)')
            if rarity == 'limited' and not (module == 'skin.v1' and group == 'skin' and row.get('limited') is True):
                raise ValueError(f'{item}: rarity "limited" only for the limited protagonist skin(s) of the skin module ("limited": true)')
            in_module = module == 'skin.v1' and group in SKIN_GROUPS
            if unlock not in UNLOCKS and not (unlock in REMOVED and optional.get(unlock)):
                raise ValueError(f'unknown unlock {unlock!r} ({"/".join(sorted(UNLOCKS))})')
            ok = {'free': ads == 0 and coins == 0, 'level': ads == 0 and coins == 0, 'league': ads == 0 and coins == 0, 'checkin': ads == 0 and coins == 0,
                  'ads': ads > 0 and coins == 0, 'coins': coins > 0 and ads == 0,
                  'ads_coins': ads > 0 and coins > 0, 'ads_or_coins': ads > 0 and coins > 0}[unlock]
            if not ok:
                raise ValueError(f'{item}: numbers do not match unlock type {unlock} (ads={ads}, coins={coins})')
            if ads > (10 if in_module and row.get('limited') is True else max_ads):
                raise ValueError(f'{item}: {ads} ads is above the maximum of {max_ads}')
            entry = {'item': item, 'order': order, 'rarity': rarity, 'rank': rank[rarity],
                     'unlock': unlock, 'ads': ads, 'coins': coins}
            if row.get('limited') is True:
                entry['limited'] = True
            b = bonus_value(row.get('bonus'), item, 60 if in_module else max_bonus)
            if b:
                entry['bonus'] = b
            if unlock == 'level':
                level, cond = row.get('level'), str(row.get('condition', '')).lower()
                if cond == 'perfect':
                    raise ValueError(f'{item}: no "perfect clear gives a skin" (user 2026-10-22); skins are won on limited '
                                     'levels (condition clear, level_plan.json)')
                if type(level) is not int or level <= 0 or cond != 'clear':
                    raise ValueError(f'{item}: level items need "level" > 0 and "condition" clear')
                entry.update(level=level, condition=cond)
            groups.setdefault(group, []).append(entry)
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f'Row {index}: {exc}')
    league = [r for es in groups.values() for r in es if r['unlock'] == 'league']
    if league and len(league) != 10:
        errors.append(f'{len(league)} league items: the Weekly League gives exactly 10 league-only skins (references/ranking-league.md)')
    any_buyable = False
    result = []
    if module == 'skin.v1':
        for group in SKIN_GROUPS:
            if group in groups:
                audit_module_group(group, groups[group], coins_per_ad, errors)
                any_buyable = True
                entries = sorted(groups[group], key=lambda r: r['order'])
                result.append({'group': group, 'module': 'skin.v1', 'items': [{k: v for k, v in r.items() if k != 'rank'} for r in entries]})
        if 'skin' not in groups:
            errors.append('module skin.v1 without a "skin" group (20 protagonist skins)')
    else:
        for group in SKIN_GROUPS:
            if group in groups and not any(optional.values()):
                errors.append(f'Group {group}: skins and backgrounds use the skin module (user 2026-10-23): write the table with '
                              'make_skin_table.py ("module": "skin.v1": 20 skins + 10 backgrounds, the 1R/4R/10R/20R price curve)')
    groups = {g: es for g, es in groups.items() if not (module == 'skin.v1' and g in SKIN_GROUPS)}
    audit_bonus(groups, errors, warnings)
    for group, entries in sorted(groups.items()):
        entries.sort(key=lambda r: r['order'])
        if len({r['order'] for r in entries}) != len(entries):
            errors.append(f'Group {group}: duplicate display order')
        buy = [r for r in entries if r['unlock'] in BUYABLE]
        levels = [r for r in entries if r['unlock'] == 'level']
        first_paid = min((r['order'] for r in buy + levels), default=None)
        for r in entries:
            if r['unlock'] == 'free' and first_paid is not None and r['order'] > first_paid:
                errors.append(f'Group {group}: free item {r["item"]} comes after paid items; free is only for starting items')
        if not buy:   # map-style group: only free + level items
            for a, b in zip(levels, levels[1:]):
                if b['level'] <= a['level']:
                    errors.append(f'Group {group}: unlock levels must increase with display order ({a["item"]} -> {b["item"]})')
            result.append({'group': group, 'items': [{k: v for k, v in r.items() if k != 'rank'} for r in entries]})
            continue
        any_buyable = True
        for a, b in zip(buy, buy[1:]):
            if b['rank'] < a['rank']:
                errors.append(f'Group {group}: rarity goes down from {a["item"]} ({a["rarity"]}) to {b["item"]} ({b["rarity"]})')
        used = {r['rank'] for r in buy}
        need = 3 if len(buy) >= 4 else 2 if len(buy) >= 2 else 1
        if len(used) < need:
            errors.append(f'Group {group}: {len(buy)} purchasable items need at least {need} rarity tiers, found {len(used)}')
        if len(buy) >= 4:
            missing = [u for u in BUYABLE if not any(r['unlock'] == u for r in buy)]
            if missing:
                errors.append(f'Group {group}: missing unlock types {", ".join(missing)} (need ads, coins, ads_coins and ads_or_coins)')
        for unlock in BUYABLE:
            same = [r for r in buy if r['unlock'] == unlock]
            by_tier = {}
            for r in same:
                by_tier.setdefault(r['rank'], []).append(r)
            ranks = sorted(by_tier)
            for metric in METRICS[unlock]:
                for lo, hi in zip(ranks, ranks[1:]):
                    lo_max = max(by_tier[lo], key=lambda r: r[metric])
                    hi_min = min(by_tier[hi], key=lambda r: r[metric])
                    if hi_min[metric] <= lo_max[metric]:
                        errors.append(f'Group {group}: {LABEL[unlock]} {metric} must rise with rarity: {hi_min["item"]} ({hi_min["rarity"]}, {hi_min[metric]}) '
                                      f'is not above {lo_max["item"]} ({lo_max["rarity"]}, {lo_max[metric]})')
                for tier_rows in by_tier.values():
                    for a, b in zip(tier_rows, tier_rows[1:]):
                        if b[metric] < a[metric]:
                            errors.append(f'Group {group}: {LABEL[unlock]} {metric} decreases inside {a["rarity"]} from {a["item"]} to {b["item"]}')
        if coins_per_ad:
            for r in buy:
                lo, hi = 2 * r['rank'] + 1, 2 * r['rank'] + 2
                v = value_in_ads(r, coins_per_ad)
                r['value_in_ads'] = round(v, 2)
                if not (lo * 0.9 <= v <= hi * 1.1):
                    errors.append(f'Group {group}: {r["item"]} ({r["rarity"]}, {LABEL[r["unlock"]]}) is worth {v:.1f} ads; '
                                  f'{r["rarity"]} should be {lo}-{hi} ads (1 ad = {coins_per_ad} coins)')
                if r['unlock'] == 'ads_or_coins' and abs(r['coins'] - r['ads'] * coins_per_ad) > 0.1 * r['ads'] * coins_per_ad:
                    errors.append(f'Group {group}: {r["item"]} ads-or-coins price should be ads x R = {r["ads"] * coins_per_ad}, found {r["coins"]}')
        if coins_per_level:
            priced = [r for r in buy if r['coins']]
            for r in priced:
                r['levels_of_income'] = math.ceil(r['coins'] / coins_per_level)
            if priced:
                cheapest = min(priced, key=lambda r: r['coins'])
                if cheapest['levels_of_income'] > 5:
                    warnings.append(f'Group {group}: cheapest coin item {cheapest["item"]} needs {cheapest["levels_of_income"]} levels of income (aim for <= 5)')
        result.append({'group': group, 'items': [{k: v for k, v in r.items() if k != 'rank'} for r in entries]})
    if any_buyable and not coins_per_ad:
        errors.append('coins_per_ad missing: set R = coins from a medium-difficulty level in the table or with --coins-per-ad')
    return {'status': 'fail' if errors else 'pass', 'errors': errors, 'warnings': warnings, 'groups': result}


def audit_alternative(rows, fields, bases, ratio=None):
    """Legacy: coin price and ad count are alternative routes; both > 0 and strictly increasing."""
    errors, groups, seen = [], {}, set()
    if not isinstance(rows, list) or not rows:
        return {'status': 'fail', 'errors': ['Table must be a nonempty array'], 'warnings': [], 'groups': []}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f'Row {index}: object required')
            continue
        try:
            item = str(row[fields['id']])
            category = str(row[fields['group']])
            order, coin, ads = (row[fields[k]] for k in ('order', 'coins', 'ads'))
            if any(type(v) is not int for v in (order, coin, ads)):
                raise ValueError('order, coin and ads must be integers')
            if item in seen:
                raise ValueError(f'duplicate item {item}')
            seen.add(item)
            if order < 0 or coin < 0 or ads < 0:
                raise ValueError('negative order/cost/count')
            if item in bases:
                if coin or ads:
                    raise ValueError('explicit starting item must have zero cost/count')
            elif coin <= 0 or ads <= 0:
                raise ValueError('new item has a free acquisition route')
            elif ratio is not None and Fraction(coin, ads) != ratio:
                raise ValueError(f'coin/ad ratio differs from {ratio}')
            groups.setdefault(category, []).append({'item': item, 'order': order, 'coin': coin, 'ads': ads, 'starting': item in bases})
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f'Row {index}: {exc}')
    for item in sorted(bases - seen):
        errors.append(f'Explicit starting item missing: {item}')
    result = []
    for group, entries in sorted(groups.items()):
        entries.sort(key=lambda r: r['order'])
        if len({r['order'] for r in entries}) != len(entries):
            errors.append(f'Group {group}: duplicate display order')
        new = [r for r in entries if not r['starting']]
        for previous, current in zip(new, new[1:]):
            if current['coin'] <= previous['coin'] or current['ads'] <= previous['ads']:
                errors.append(f'Group {group}: difficulty does not strictly increase from {previous["item"]} to {current["item"]}')
        result.append({'group': group, 'items': entries})
    return {'status': 'fail' if errors else 'pass', 'errors': errors, 'warnings': [], 'groups': result}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--table', type=Path)
    p.add_argument('--project', type=Path)
    p.add_argument('--maintenance-scope', type=Path)
    p.add_argument('--mode', choices=['rarity', 'alternative'], default='rarity')
    for name, default in [('id', 'id'), ('group', 'group'), ('order', 'order'), ('rarity', 'rarity'),
                          ('unlock', 'unlock'), ('coins', 'coins'), ('ads', 'ads')]:
        p.add_argument(f'--{name}-field', default=default)
    p.add_argument('--rarity-order', default='common,rare,epic,legendary')
    p.add_argument('--coins-per-level', type=int)
    p.add_argument('--coins-per-ad', type=Fraction, help='R = coins from a medium-difficulty level (rarity mode); coin/ad ratio (alternative mode)')
    p.add_argument('--max-ads', type=int, default=8)
    p.add_argument('--max-bonus', type=int, default=50, help='max skin bonus percent (default 50)')
    p.add_argument('--starting-items', nargs='*', default=[], help='alternative mode only')
    p.add_argument('--binding', type=Path, help='known-issue review JSON whose "binding" is copied into the report')
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    if a.maintenance_scope:
        from maintenance_scope import audit_scope, collection_catalog, sha
        binding = json.loads(a.binding.read_text()).get('binding') if a.binding else None
        scope, errors = audit_scope(a.maintenance_scope, a.project or Path('.'), binding)
        if scope and 'collection' not in scope.get('existing_features',[]):errors.append('actual preserved collection inventory required; this is not a no-economy waiver')
        catalog = collection_catalog(scope['economy_catalog'], a.maintenance_scope.parent, binding) if scope and not errors else None
        items = sum(len(g['items']) for g in catalog['current']['groups']) if catalog else 0
        result = {'tool':'audit_acquisition_progression','implementation':'production_js','project':str((a.project or Path('.')).resolve()),
                  'maintenance_scope':str(a.maintenance_scope.resolve()),'maintenance_scope_sha256':sha(a.maintenance_scope),'binding':binding,
                  'checked':items,'failed':len(errors),'passed':not errors and items>0,'status':'fail' if errors or not items else 'pass',
                  'errors':errors,'warnings':[],'boundary':'Preserved actual collection, exact original prices, production source/Web/Native purchase/merge/equip/effect/storage runtime; current mobile GUI remains separately mandatory.'}
        a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'checked':items,'errors':errors}));return 0 if result['passed'] else 2
    if not a.table:p.error('--table is required unless explicit --maintenance-scope and --project are supplied')
    try:
        raw = a.table.read_bytes()
        data = json.loads(raw.decode('utf-8-sig'))
        rows = data.get('items') if isinstance(data, dict) else data
        meta = data if isinstance(data, dict) else {}
        coins_per_ad = a.coins_per_ad or meta.get('coins_per_ad') or meta.get('coinsPerAd')
        coins_per_level = a.coins_per_level or meta.get('coins_per_level') or meta.get('coinsPerLevel')
        fields = {k: getattr(a, k + '_field') for k in ('id', 'group', 'order', 'rarity', 'unlock', 'coins', 'ads')}
        if a.mode == 'rarity':
            tiers = [t.strip() for t in a.rarity_order.split(',') if t.strip()]
            if len(tiers) < 2:
                raise ValueError('rarity-order needs at least two tiers')
            result = audit_rarity(rows, fields, tiers, coins_per_level, float(coins_per_ad) if coins_per_ad else None, a.max_ads, a.max_bonus,
                                  meta.get('module'), enabled(next((p for p in a.table.resolve().parents if (p / 'docs').is_dir()), a.table.parent)))
        else:
            if a.coins_per_ad is not None and a.coins_per_ad <= 0:
                raise ValueError('coins-per-ad must be positive')
            result = audit_alternative(rows, fields, set(a.starting_items), Fraction(coins_per_ad) if coins_per_ad else None)
        result.update(table=str(a.table.resolve()), table_sha256=hashlib.sha256(raw).hexdigest())
        if a.binding:
            binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
            if not isinstance(binding, dict):
                raise ValueError(f'no binding object in {a.binding}')
            result['binding'] = binding
    except (OSError, ValueError, TypeError) as exc:
        result = {'status': 'fail', 'errors': [str(exc)], 'warnings': [], 'groups': []}
    items = sum(len(g['items']) for g in result.get('groups', []))
    result.update(tool='audit_acquisition_progression', mode=a.mode, checked=items,
                  failed=len(result['errors']), passed=result['status'] == 'pass',
                  boundary='Configuration only; no runtime, GUI, storage, device or real-ad acceptance implied.')
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'checked': items, 'errors': result['errors'][:10],
                      'warnings': result['warnings'][:5], 'report': str(a.report)}, ensure_ascii=False))
    return 0 if result['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
