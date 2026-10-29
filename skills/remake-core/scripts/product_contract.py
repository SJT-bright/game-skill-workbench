"""Shared product data rules, independent of project paths and renderer state."""
import random
import statistics
import math

REVISION = '2026-10-27.economy-v4'
REWARD_POLICY = 'normal_budget.v2'
ECONOMY_POLICY = 'normal-10-50.v1'
PRICE_LEVEL_TARGETS = dict(zip(('common','rare','epic','legendary','limited'), (10,20,30,40,50)))
GIFT_COOLDOWN_MS = 30 * 60 * 1000
GIFT_MULTIPLIER = AD_CURRENCY_MULTIPLIER = 5
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


def legacy_reward_rows(total, base_coins, seed, bonus_levels, every=10):
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


def reward_rows(total, base_coins, seed, bonus_levels, every=10):
    """Stored bounded rolls; each ten ordinary wins sum exactly 10B, without chapter inflation."""
    if type(total) is not int or total < 1 or type(base_coins) is not int or base_coins < 1 or type(seed) is not int:
        raise ValueError('positive total/base_coins and integer reward_seed required')
    bonus=set(bonus_levels);rng=random.Random('normal-budget-v2:'+str(seed));band=base_coins//10
    normal=[n for n in range(1,total+1) if n not in bonus];rows={}
    for start in range(0,len(normal),10):
        group=normal[start:start+10];rolls=[]
        for _ in range(len(group)//2):
            value=rng.randint(1,band) if band else 0
            rolls.extend((value,-value))
        if len(group)%2:rolls.append(0)
        rng.shuffle(rolls)
        for n,roll in zip(group,rolls):
            rows[n]={'coins_base':base_coins,'coins_band':band,'coins_roll':roll,'coins':base_coins+roll}
    for n in bonus:
        rows[n]={'coins':3*base_coins,'normal_level_coins':base_coins}
    return rows


def reward_errors(plan):
    """Validate deterministic policy, arithmetic, bounds, and immutable seed."""
    errors = []
    if plan.get('reward_policy') not in (REWARD_POLICY,'seeded_band.v1'):
        return ['reward_policy must be '+REWARD_POLICY+' for a newly generated plan']
    try:
        rows = plan['levels'];total = plan['total_levels'];seed = plan['reward_seed'];base = plan['coins_per_level']
        factory = legacy_reward_rows if plan['reward_policy']=='seeded_band.v1' else reward_rows
        expected = factory(total, base, seed, [r['level'] for r in rows if r['type']=='bonus'])
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


def budget_errors(table):
    """Current economic contract only; saved pre-policy tables retain their explicit legacy scope."""
    if table.get('economy_policy')!=ECONOMY_POLICY:return []
    base=table.get('normal_level_coins');errors=[]
    if type(base)is not int or base<=0:return ['normal_level_coins must be a positive integer']
    for key,want in [('price_level_targets',PRICE_LEVEL_TARGETS),('coins_per_level',base),('coins_per_ad',5*base),('gift_multiplier',5),('gift_cooldown_ms',GIFT_COOLDOWN_MS)]:
        if table.get(key)!=want:errors.append(key+' differs from normal-10-50.v1')
    for row in table.get('items',[]):
        if row.get('group') in ('map','maps','world','worlds','chapter','chapters') or row.get('unlock')=='free':continue
        rarity=row.get('rarity')
        if rarity not in PRICE_LEVEL_TARGETS or row.get('unlock')!='coins' or row.get('ads')!=0 or row.get('coins')!=base*PRICE_LEVEL_TARGETS[rarity]:
            errors.append(str(row.get('id'))+': coin purchase must cost exactly 10/20/30/40/50 ordinary rewards')
    return errors


# Rule 36 (Saul 2026-10-28): about half of the priced, non-free, non-limited cosmetics of each group unlock by
# completed rewarded videos instead of coins. Kept in a SEPARATE table (ad_unlock_table.json); unlock_table.json
# stays coin-only (ads=0) so budget_errors above is unchanged. Mirrors the workshop receiver
# (workshop_intake._check_ad_unlock_table) and generator (kit/scripts/economy_v71.py).
AD_UNLOCK_SCHEMA = 'workshop-ad-unlock.v1'
AD_UNLOCK_POLICY = 'rule36-b.v1'
AD_UNLOCK_PATH = 'assets/resources/config/ad_unlock_table.json'
AD_UNLOCK_VIEWS = dict(zip(PRICE_LEVEL_TARGETS, (1, 3, 5, 7, 9)))  # common..limited -> views
AD_UNLOCK_VIEWS_BY_LEVEL = {PRICE_LEVEL_TARGETS[k]: v for k, v in AD_UNLOCK_VIEWS.items()}  # 10B->1 ... 50B->9
AD_UNLOCK_PROGRESS = {'persist': 'per_item_completed_views_in_game_save', 'counts': 'verified_completed_rewarded_video_only',
                      'cancel_error_timeout': 'no_progress', 'cap': 'ads_required', 'coin_purchase': 'not_offered_for_listed_items'}
AD_UNLOCK_KEYS = {'id', 'group', 'rarity', 'coin_price_reference', 'price_level', 'ads_required'}
AD_UNLOCK_GROUPS = ('skin', 'background')  # workshop packs list skins/backgrounds only; maps/permanent items allowed for ordinary games


def ad_unlock_eligible(table, group):
    """Priced, non-free, non-limited coin-table rows of one group (the receiver's _ad_eligible)."""
    return [x for x in table.get('items', []) if isinstance(x, dict) and x.get('group') == group and x.get('unlock') == 'coins'
            and not x.get('limited') and type(x.get('coins')) is int and x['coins'] > 0]


def ad_unlock_errors(ad_table, unlock_table):
    """Errors of a rule-36 ad-unlock table against its bound coin table; [] means valid.
    Each item needs one view fewer than earning its price with 5B coin ads (10B: 1 vs 2 ... 50B: 9 vs 10)."""
    ad, table = ad_table, unlock_table
    if not isinstance(ad, dict) or ad.get('schema') != AD_UNLOCK_SCHEMA or ad.get('policy') != AD_UNLOCK_POLICY:
        return ['ad unlock table schema/policy must be %s/%s' % (AD_UNLOCK_SCHEMA, AD_UNLOCK_POLICY)]
    if not isinstance(table, dict):
        return ['coin unlock table missing']
    errors = []
    B = table.get('normal_level_coins')
    if type(B) is not int or B <= 0:
        return ['coin table normal_level_coins (B) must be a positive integer']
    if table.get('economy_policy') != ECONOMY_POLICY or ad.get('economy_policy') != ECONOMY_POLICY or ad.get('normal_level_coins') != B:
        errors.append('ad unlock table must bind the same normal-10-50.v1 B as the coin table')
    if ad.get('views_by_price_level') != {str(k): v for k, v in AD_UNLOCK_VIEWS_BY_LEVEL.items()}:
        errors.append('views_by_price_level must be 10B->1, 20B->3, 30B->5, 40B->7, 50B->9')
    if ad.get('progress') != AD_UNLOCK_PROGRESS:
        errors.append('ad unlock progress policy must persist completed views only and offer no coin purchase')
    rows = ad.get('items')
    if not isinstance(rows, list) or not rows:
        return errors + ['ad unlock table must list items']
    by_id = {x.get('id'): x for x in table.get('items', []) if isinstance(x, dict)}
    seen, groups = set(), list(AD_UNLOCK_GROUPS)
    for row in rows:
        if not isinstance(row, dict) or set(row) != AD_UNLOCK_KEYS or row.get('id') in seen:
            errors.append('ad unlock row malformed or duplicated: %r' % (row.get('id') if isinstance(row, dict) else row))
            continue
        seen.add(row['id'])
        if row['group'] not in groups:
            groups.append(row['group'])
        src = by_id.get(row['id'])
        if src is None:
            errors.append('ad unlock item %s is not in the coin table' % row['id'])
            continue
        if (src.get('unlock') != 'coins' or src.get('ads') != 0 or src.get('limited') or type(src.get('coins')) is not int
                or src['coins'] <= 0 or src.get('group') != row['group'] or src.get('rarity') != row['rarity']):
            errors.append('ad unlock item %s must be a priced, non-free, non-limited coin-table item of the same group/rarity' % row['id'])
            continue
        level = src['coins'] // B
        if (src['coins'] != B * level or level not in AD_UNLOCK_VIEWS_BY_LEVEL or row['price_level'] != level
                or row['coin_price_reference'] != src['coins'] or type(row['ads_required']) is not int
                or row['ads_required'] != AD_UNLOCK_VIEWS_BY_LEVEL[level]):
            errors.append('ad unlock item %s views/price differ from rule 36 (10B->1 ... 50B->9)' % row['id'])
    for group in groups:
        n = len(ad_unlock_eligible(table, group))
        k = sum(1 for row in rows if isinstance(row, dict) and row.get('group') == group)
        if n and not (n // 2 <= k <= (n + 1) // 2):
            errors.append('%s: %d of %d priced items are ad unlocks; rule 36 requires about half' % (group, k, n))
    return errors


def ad_unlock_table(unlock_table, groups=AD_UNLOCK_GROUPS):
    """Generate ad_unlock_table.json from the coin table (same selection and bytes as the workshop generator):
    per group, every second item (positions 2, 4, 6 ...) of the priced non-free non-limited rows sorted by price,
    then order, then id. Add 'map' or another permanent-item group to groups only for ordinary (non-workshop) games."""
    B = unlock_table.get('normal_level_coins')
    if type(B) is not int or B <= 0:
        raise ValueError('ad unlock table needs the bound coin table normal_level_coins (B)')
    items = []
    for group in groups:
        rows = sorted(ad_unlock_eligible(unlock_table, group), key=lambda x: (x['coins'], x.get('order', 0), x['id']))
        for i, row in enumerate(rows):
            if i % 2 == 1:
                level = row['coins'] // B
                if row['coins'] != B * level or level not in AD_UNLOCK_VIEWS_BY_LEVEL:
                    raise ValueError('item %s is not priced at 10/20/30/40/50 B' % row['id'])
                items.append({'id': row['id'], 'group': group, 'rarity': row['rarity'], 'coin_price_reference': row['coins'],
                              'price_level': level, 'ads_required': AD_UNLOCK_VIEWS_BY_LEVEL[level]})
    return {'schema': AD_UNLOCK_SCHEMA, 'policy': AD_UNLOCK_POLICY, 'economy_policy': ECONOMY_POLICY,
            'normal_level_coins': B, 'views_by_price_level': {str(k): v for k, v in AD_UNLOCK_VIEWS_BY_LEVEL.items()},
            'selection': 'per group: odd positions of priced non-free non-limited items sorted by price then order',
            'progress': dict(AD_UNLOCK_PROGRESS), 'items': items}


def _main(argv=None):
    import argparse, json, sys
    ap = argparse.ArgumentParser(description='Write ad_unlock_table.json (remake-economy economy-rules.md #看广告解锁).')
    ap.add_argument('command', choices=['ad-unlock'])
    ap.add_argument('--table', required=True, help='unlock_table.json written by make_skin_table.py')
    ap.add_argument('--out', required=True, help='assets/resources/config/ad_unlock_table.json')
    ap.add_argument('--groups', default=','.join(AD_UNLOCK_GROUPS), help='default skin,background; add map only for ordinary games')
    a = ap.parse_args(argv)
    with open(a.table, encoding='utf-8') as f:
        table = json.load(f)
    if budget_errors(table):
        print('\n'.join(budget_errors(table)), file=sys.stderr); return 1
    ad = ad_unlock_table(table, tuple(g for g in a.groups.split(',') if g))
    errors = ad_unlock_errors(ad, table)
    if errors:
        print('\n'.join(errors), file=sys.stderr); return 1
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write(json.dumps(ad, ensure_ascii=True, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'out': a.out, 'ad_unlock_items': len(ad['items'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(_main())
