"""Shared product data rules, independent of project paths and renderer state."""
import random
import statistics
import math

REVISION = '2026-10-27.economy-v4'
REWARD_POLICY = 'normal_budget.v2'
# Purchase price of each rarity in ordinary base rewards B (ECON-TIER). New tables use normal-5-80.v1 (Saul 2026-11-01:
# the lowest rarity costs 5B and every rarity above doubles; the fifth tier 80B is Kiro's default). Frozen old tables keep
# normal-10-50.v1 and are still checked against it. Unsuffixed names are the current policy, *_LEGACY the frozen one.
SKIN_POLICY = 'normal-5-80.v1'
SKIN_POLICY_LEGACY = 'normal-10-50.v1'
RARITIES = ('common', 'rare', 'epic', 'legendary', 'limited')
SKIN_TIERS_B = {SKIN_POLICY: dict(zip(RARITIES, (5, 10, 20, 40, 80))), SKIN_POLICY_LEGACY: dict(zip(RARITIES, (10, 20, 30, 40, 50)))}
ECONOMY_POLICY = SKIN_POLICY
ECONOMY_POLICY_LEGACY = SKIN_POLICY_LEGACY
ECONOMY_POLICIES = (SKIN_POLICY, SKIN_POLICY_LEGACY)


def skin_tiers_B(policy=SKIN_POLICY):
    """{'common': 5, 'rare': 10, ...}: price of each rarity in B under policy (normal-5-80.v1, or frozen normal-10-50.v1)."""
    if not isinstance(policy, str) or policy not in SKIN_TIERS_B:
        raise ValueError('unknown economy policy %r (%s)' % (policy, ' / '.join(ECONOMY_POLICIES)))
    return dict(SKIN_TIERS_B[policy])


PRICE_LEVEL_TARGETS = skin_tiers_B(SKIN_POLICY)
PRICE_LEVEL_TARGETS_LEGACY = skin_tiers_B(SKIN_POLICY_LEGACY)


def b_coins(k, B):
    """The whole-coin amount the game writes for k*B: k*B rounded half up (rules table B.rounding, Saul 2026-10-31:
    B may be fractional, e.g. 72.5 -> 5B = 362.5 -> 363). A whole k*B is returned unchanged."""
    return int(math.floor(k * B + 0.5))


def _positive_B(B):
    """B (ordinary base reward) may be a whole or a fractional positive number, never a bool."""
    return type(B) in (int, float) and math.isfinite(B) and B > 0
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
    """Economic contract of the table's own policy (normal-5-80.v1, or a frozen normal-10-50.v1 table checked by its old
    numbers); saved pre-policy tables retain their explicit legacy scope."""
    policy=table.get('economy_policy')
    if not isinstance(policy,str) or policy not in SKIN_TIERS_B:return []
    targets=skin_tiers_B(policy)
    base=table.get('normal_level_coins');errors=[]
    if type(base)is int:
        if base<=0:return ['normal_level_coins must be a positive integer']
        ok=lambda v,k:v==k*base  # whole B: exact, unchanged from v7.8
    elif _positive_B(base):
        ok=lambda v,k:_b_amount_ok(v,k,base)  # fractional B: k*B written as a whole number (less than 1 away)
    else:return ['normal_level_coins must be a positive integer']
    for key,want in [('price_level_targets',targets),('coins_per_level',base),('coins_per_ad',None),('gift_multiplier',5),('gift_cooldown_ms',GIFT_COOLDOWN_MS)]:
        if (not ok(table.get(key),5)) if key=='coins_per_ad' else table.get(key)!=want:errors.append(key+' differs from '+policy)
    for row in table.get('items',[]):
        if row.get('group') in ('map','maps','world','worlds','chapter','chapters') or row.get('unlock')=='free':continue
        rarity=row.get('rarity')
        if rarity not in targets or row.get('unlock')!='coins' or row.get('ads')!=0 or not ok(row.get('coins'),targets[rarity]):
            errors.append(str(row.get('id'))+': coin purchase must cost exactly '+'/'.join(str(v) for v in targets.values())+' ordinary rewards')
    return errors


# Rule 36: part of the priced, non-free, non-limited cosmetics of each group unlock by completed rewarded videos
# instead of coins. Kept in a SEPARATE table (ad_unlock_table.json); unlock_table.json stays coin-only (ads=0) so
# budget_errors above is unchanged. Mirrors the workshop receiver (workshop_intake._check_ad_unlock_table) and
# generator (kit/scripts/economy_v71.py). Two policies, chosen by the ad table's own "policy":
#   rule36-c.v1 (ECON-ADUNLOCK, Saul 2026-11-01, new tables): 60 % per group (floor(0.6n) <= k <= ceil(0.6n)), every
#     rarity tier of 2+ items has both ad and coin items, the cheapest item stays coins, 1 view = 2B so
#     views = ceil(price / 2B): 5B->3, 10B->5, 20B->10, 40B->20. Binds a normal-5-80.v1 coin table.
#   rule36-b.v1 (Saul 2026-10-28, frozen tables only): about half, 10B->1 ... 50B->9. Binds normal-10-50.v1.
AD_UNLOCK_SCHEMA = 'workshop-ad-unlock.v1'
AD_UNLOCK_POLICY = 'rule36-c.v1'
AD_UNLOCK_POLICY_LEGACY = 'rule36-b.v1'
AD_UNLOCK_POLICIES = (AD_UNLOCK_POLICY, AD_UNLOCK_POLICY_LEGACY)
AD_UNLOCK_ECONOMY = {AD_UNLOCK_POLICY: SKIN_POLICY, AD_UNLOCK_POLICY_LEGACY: SKIN_POLICY_LEGACY}  # each binds one price policy
AD_UNLOCK_SHARE = (3, 5)  # rule36-c.v1: 60 % as a fraction
AD_UNLOCK_B_PER_VIEW = 2  # rule36-c.v1: one completed video stands for 2B
AD_UNLOCK_PATH = 'assets/resources/config/ad_unlock_table.json'
AD_UNLOCK_VIEWS = {k: -(-v // AD_UNLOCK_B_PER_VIEW) for k, v in PRICE_LEVEL_TARGETS.items() if k != 'limited'}  # 3/5/10/20
AD_UNLOCK_VIEWS_BY_LEVEL = {PRICE_LEVEL_TARGETS[k]: v for k, v in AD_UNLOCK_VIEWS.items()}  # 5B->3, 10B->5, 20B->10, 40B->20
AD_UNLOCK_VIEWS_LEGACY = dict(zip(RARITIES, (1, 3, 5, 7, 9)))  # rule36-b.v1 common..limited -> views
AD_UNLOCK_VIEWS_BY_LEVEL_LEGACY = {PRICE_LEVEL_TARGETS_LEGACY[k]: v for k, v in AD_UNLOCK_VIEWS_LEGACY.items()}  # 10B->1 ... 50B->9
AD_UNLOCK_PROGRESS = {'persist': 'per_item_completed_views_in_game_save', 'counts': 'verified_completed_rewarded_video_only',
                      'cancel_error_timeout': 'no_progress', 'cap': 'ads_required', 'coin_purchase': 'not_offered_for_listed_items'}
AD_UNLOCK_KEYS = {'id', 'group', 'rarity', 'coin_price_reference', 'price_level', 'ads_required'}
AD_UNLOCK_GROUPS = ('skin', 'background')  # workshop packs list skins/backgrounds only; maps/permanent items allowed for ordinary games


def ad_unlock_eligible(table, group):
    """Priced, non-free, non-limited coin-table rows of one group (the receiver's _ad_eligible)."""
    return [x for x in table.get('items', []) if isinstance(x, dict) and x.get('group') == group and x.get('unlock') == 'coins'
            and not x.get('limited') and type(x.get('coins')) is int and x['coins'] > 0]


def ad_unlock_views(price, B, policy=AD_UNLOCK_POLICY):
    """Completed videos that unlock an item priced `price` (main currency) when one ordinary base reward is B; None when
    the price has no view count under the policy. rule36-c.v1: ceil(price / 2B) (5B->3, 10B->5, 20B->10, 40B->20); with a
    fractional B a price within the whole-number rounding of kB counts as exactly kB (_b_amount_ok). rule36-b.v1 (frozen):
    only the five tiers 10B->1, 20B->3, 30B->5, 40B->7, 50B->9."""
    if policy not in AD_UNLOCK_POLICIES:
        raise ValueError('unknown ad unlock policy %r (%s)' % (policy, ' / '.join(AD_UNLOCK_POLICIES)))
    if not _num(price) or not _num(B) or B <= 0 or price <= 0:
        return None
    if policy == AD_UNLOCK_POLICY_LEGACY:
        return AD_UNLOCK_VIEWS_BY_LEVEL_LEGACY.get(_b_level(price, AD_UNLOCK_VIEWS_BY_LEVEL_LEGACY, B))
    k = round(price / B)
    level = k if k > 0 and _b_amount_ok(price, k, B) else price / B
    return max(1, math.ceil(level / AD_UNLOCK_B_PER_VIEW - 1e-9))


def ad_unlock_share_ok(n, k, policy=AD_UNLOCK_POLICY):
    """Is k ad unlocks out of n priced items of one group the policy's share? rule36-c.v1: floor(0.6n) <= k <= ceil(0.6n);
    rule36-b.v1 (frozen): n//2 <= k <= (n+1)//2."""
    if policy == AD_UNLOCK_POLICY_LEGACY:
        return n // 2 <= k <= (n + 1) // 2
    if policy != AD_UNLOCK_POLICY:
        raise ValueError('unknown ad unlock policy %r (%s)' % (policy, ' / '.join(AD_UNLOCK_POLICIES)))
    a, b = AD_UNLOCK_SHARE
    return (a * n) // b <= k <= -(-a * n // b)


def _ad_unlock_pick(rows):
    """rule36-c.v1 choice inside one group; rows sorted by price, order, id. k = 60 % of n rounded half up. Each rarity
    tier (in price order) gets its largest-remainder share of k, at least one ad and one coin item when it has 2+, and the
    cheapest tier keeps at least one coin item (its first one); ties go to the dearer tier. Inside a tier the ad items
    are spread evenly (first item coins). Returns the chosen rows in input order; the same rows always give the same pick."""
    from fractions import Fraction
    tiers = {}
    for row in rows:
        tiers.setdefault(row['rarity'], []).append(row)
    tiers = list(tiers.values())
    n, (a, b) = len(rows), AD_UNLOCK_SHARE
    sizes = [len(t) for t in tiers]
    lo = [1 if c >= 2 else 0 for c in sizes]
    hi = [c - 1 if c >= 2 or i == 0 else c for i, c in enumerate(sizes)]
    quota = [Fraction(a * c, b) for c in sizes]
    k = min(max((2 * a * n + b) // (2 * b), sum(lo)), sum(hi))
    if not ad_unlock_share_ok(n, k):
        raise ValueError('cannot choose 60%% ad unlocks with every tier mixed (tier sizes %r)' % sizes)
    got = [min(max(int(q), l), h) for q, l, h in zip(quota, lo, hi)]
    while sum(got) < k:
        got[max((j for j in range(len(sizes)) if got[j] < hi[j]), key=lambda j: (quota[j] - got[j], j))] += 1
    while sum(got) > k:
        got[min((j for j in range(len(sizes)) if got[j] > lo[j]), key=lambda j: (quota[j] - got[j], j))] -= 1
    chosen = set()
    for tier, g in zip(tiers, got):
        c = len(tier)
        chosen.update(id(row) for i, row in enumerate(tier) if (i + 1) * g // c > i * g // c)
    return [row for row in rows if id(row) in chosen]


def ad_unlock_errors(ad_table, unlock_table):
    """Errors of a rule-36 ad-unlock table against its bound coin table; [] means valid. The ad table's own policy
    decides the contract: rule36-c.v1 (new) or rule36-b.v1 (frozen tables keep their old numbers and stay checked)."""
    policy = ad_table.get('policy') if isinstance(ad_table, dict) else None
    if policy == AD_UNLOCK_POLICY_LEGACY:
        return _ad_unlock_errors_b(ad_table, unlock_table)
    if policy == AD_UNLOCK_POLICY and ad_table.get('schema') == AD_UNLOCK_SCHEMA:
        return _ad_unlock_errors_c(ad_table, unlock_table)
    return ['ad unlock table schema/policy must be %s/%s (or %s for a frozen normal-10-50.v1 table)'
            % (AD_UNLOCK_SCHEMA, AD_UNLOCK_POLICY, AD_UNLOCK_POLICY_LEGACY)]


def _ad_unlock_errors_c(ad, table):
    """rule36-c.v1: 60 % per group, both kinds in every tier of 2+, cheapest stays coins, views = ceil(price / 2B)."""
    if not isinstance(table, dict):
        return ['coin unlock table missing']
    errors = []
    B = table.get('normal_level_coins')
    if not _positive_B(B):  # rule36-c.v1 accepts a fractional B (prices are k*B rounded half up)
        return ['coin table normal_level_coins (B) must be a positive number']
    if table.get('economy_policy') != SKIN_POLICY or ad.get('economy_policy') != SKIN_POLICY or ad.get('normal_level_coins') != B:
        errors.append('ad unlock table must bind the same %s B as the coin table (rule36-c.v1)' % SKIN_POLICY)
    if ad.get('views_by_price_level') != {str(k): v for k, v in AD_UNLOCK_VIEWS_BY_LEVEL.items()}:
        errors.append('views_by_price_level must be 5B->3, 10B->5, 20B->10, 40B->20 (1 view = 2B, rounded up)')
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
        level = _b_level(src['coins'], AD_UNLOCK_VIEWS_BY_LEVEL, B)  # whole B: exact multiple; fractional B: within rounding
        if (level is None or row['price_level'] != level
                or row['coin_price_reference'] != src['coins'] or type(row['ads_required']) is not int
                or row['ads_required'] != AD_UNLOCK_VIEWS_BY_LEVEL[level]):
            errors.append('ad unlock item %s views/price differ from rule36-c.v1 (1 view = 2B: 5B->3, 10B->5, 20B->10, 40B->20)' % row['id'])
    listed = {row.get('id') for row in rows if isinstance(row, dict)}
    for group in groups:
        eligible = sorted(ad_unlock_eligible(table, group), key=lambda x: (x['coins'], x.get('order', 0), x['id']))
        n = len(eligible)
        k = sum(1 for row in rows if isinstance(row, dict) and row.get('group') == group)
        if not n:
            continue
        if not ad_unlock_share_ok(n, k):
            a, b = AD_UNLOCK_SHARE
            errors.append('%s: %d of %d priced items are ad unlocks; rule36-c.v1 requires 60%% (%d..%d)'
                          % (group, k, n, a * n // b, -(-a * n // b)))
        if eligible[0]['id'] in listed:
            errors.append('%s: the cheapest item %s must stay a coin purchase (rule36-c.v1)' % (group, eligible[0]['id']))
        for rarity in dict.fromkeys(x['rarity'] for x in eligible):
            tier = [x for x in eligible if x['rarity'] == rarity]
            ads = sum(1 for x in tier if x['id'] in listed)
            if len(tier) >= 2 and ads in (0, len(tier)):
                errors.append('%s %s: %d of %d are ad unlocks; a tier of 2 or more needs both ad and coin items (rule36-c.v1)'
                              % (group, rarity, ads, len(tier)))
    return errors


def _ad_unlock_errors_b(ad, table):
    """rule36-b.v1 (frozen normal-10-50.v1 tables), unchanged from v7.8. Each item needs one view fewer than earning
    its price with 5B coin ads (10B: 1 vs 2 ... 50B: 9 vs 10)."""
    if not isinstance(ad, dict) or ad.get('schema') != AD_UNLOCK_SCHEMA or ad.get('policy') != AD_UNLOCK_POLICY_LEGACY:
        return ['ad unlock table schema/policy must be %s/%s' % (AD_UNLOCK_SCHEMA, AD_UNLOCK_POLICY_LEGACY)]
    if not isinstance(table, dict):
        return ['coin unlock table missing']
    errors = []
    B = table.get('normal_level_coins')
    if type(B) is not int or B <= 0:
        return ['coin table normal_level_coins (B) must be a positive integer']
    if (table.get('economy_policy') != SKIN_POLICY_LEGACY or ad.get('economy_policy') != SKIN_POLICY_LEGACY
            or ad.get('normal_level_coins') != B):
        errors.append('ad unlock table must bind the same normal-10-50.v1 B as the coin table')
    if ad.get('views_by_price_level') != {str(k): v for k, v in AD_UNLOCK_VIEWS_BY_LEVEL_LEGACY.items()}:
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
        if (src['coins'] != B * level or level not in AD_UNLOCK_VIEWS_BY_LEVEL_LEGACY or row['price_level'] != level
                or row['coin_price_reference'] != src['coins'] or type(row['ads_required']) is not int
                or row['ads_required'] != AD_UNLOCK_VIEWS_BY_LEVEL_LEGACY[level]):
            errors.append('ad unlock item %s views/price differ from rule 36 (10B->1 ... 50B->9)' % row['id'])
    for group in groups:
        n = len(ad_unlock_eligible(table, group))
        k = sum(1 for row in rows if isinstance(row, dict) and row.get('group') == group)
        if n and not (n // 2 <= k <= (n + 1) // 2):
            errors.append('%s: %d of %d priced items are ad unlocks; rule 36 requires about half' % (group, k, n))
    return errors


def ad_unlock_table(unlock_table, groups=AD_UNLOCK_GROUPS, policy=AD_UNLOCK_POLICY):
    """Generate ad_unlock_table.json from the coin table (same selection and bytes as the workshop generator).
    rule36-c.v1 (default, needs a normal-5-80.v1 coin table): per group, 60 % of the priced non-free non-limited rows
    sorted by price, then order, then id, chosen by _ad_unlock_pick (every tier of 2+ mixed, cheapest stays coins).
    rule36-b.v1 (frozen normal-10-50.v1 tables): every second item (positions 2, 4, 6 ...), byte-identical to v7.8.
    Add 'map' or another permanent-item group to groups only for ordinary (non-workshop) games."""
    if policy not in AD_UNLOCK_POLICIES:
        raise ValueError('unknown ad unlock policy %r (%s)' % (policy, ' / '.join(AD_UNLOCK_POLICIES)))
    legacy = policy == AD_UNLOCK_POLICY_LEGACY
    views = AD_UNLOCK_VIEWS_BY_LEVEL_LEGACY if legacy else AD_UNLOCK_VIEWS_BY_LEVEL
    B = unlock_table.get('normal_level_coins')
    if not (type(B) is int and B > 0 if legacy else _positive_B(B)):  # rule36-c.v1 accepts a fractional B
        raise ValueError('ad unlock table needs the bound coin table normal_level_coins (B)')
    if not legacy and unlock_table.get('economy_policy') != SKIN_POLICY:
        raise ValueError('coin table economy_policy is %r; rule36-c.v1 needs a %s table (a frozen %s table keeps --policy %s)'
                         % (unlock_table.get('economy_policy'), SKIN_POLICY, SKIN_POLICY_LEGACY, AD_UNLOCK_POLICY_LEGACY))
    items = []
    for group in groups:
        rows = sorted(ad_unlock_eligible(unlock_table, group), key=lambda x: (x['coins'], x.get('order', 0), x['id']))
        for row in (rows[1::2] if legacy else _ad_unlock_pick(rows)):
            if legacy:
                level = row['coins'] // B
                level = level if row['coins'] == B * level else None
            else:
                level = _b_level(row['coins'], views, B)  # whole B: exact multiple; fractional B: k*B rounded
            if level not in views:
                raise ValueError('item %s is not priced at %s B' % (row['id'], '/'.join(str(v) for v in views)))
            items.append({'id': row['id'], 'group': group, 'rarity': row['rarity'], 'coin_price_reference': row['coins'],
                          'price_level': level, 'ads_required': views[level]})
    return {'schema': AD_UNLOCK_SCHEMA, 'policy': policy, 'economy_policy': AD_UNLOCK_ECONOMY[policy],
            'normal_level_coins': B, 'views_by_price_level': {str(k): v for k, v in views.items()},
            'selection': ('per group: odd positions of priced non-free non-limited items sorted by price then order' if legacy else
                          'per group: 60% (rounded half up) of priced non-free non-limited items sorted by price then order; '
                          'every rarity of 2+ has ad and coin items, the cheapest stays coins, ads spread evenly in each rarity'),
            'progress': dict(AD_UNLOCK_PROGRESS), 'items': items}


# ---------------------------------------------------------------------------------------------------------------
# Extended economy rules (Saul 2026-10-31, remake-economy economy-rules.md 第五节起). Values mirror
# remake-economy/references/economy_rules_table.json (economy_rules.v1); test_economy_extended.py checks they agree.
# Everything above this line is unchanged; these are additions only. Amounts are in B unless the name says otherwise.
ECON_RULES_SCHEMA = 'economy_rules.v1'
ECON_RULES_REVISION = '2026-11-01.v3.2'   # v3.1: Saul 11-01 decided ADCOIN / SHOPFREE / TIMERCHEST numbers; + ONLINE, KEYCHEST
#                                           v3.2: CLAIMX2 windows + online_gift, key_chest; excluded + key_chest_ad_keys
ECON_SEVERITY_BY_KIND = {'remake': 'error', 'english': 'suggest', 'finished': 'label'}
ECON_UNDECIDED_MAX = 'suggest'   # a number Saul has not decided yet (params decided_by_saul=false) never blocks a package
ECON_ORIGINS, ECON_ORIGIN_DEFAULT = ('original', 'ad-boost', 'new'), 'original'
ECON_ENGLISH_DEFAULT = ('ECON-B', 'ECON-X2', 'ECON-NOCUR', 'ECON-SHORTCUT', 'ECON-REVISIT', 'ECON-CLAIMX2')
LEVEL_WINDOW, LEVEL_WINDOW_SUM_B = 10, 10
GIFT_REWARD_B = AD_COIN_REWARD_B = SHORTCUT_REWARD_B = REVISIT_REWARD_B = 5
AD_COIN_PER_DAY, AD_COIN_COOLDOWN_SEC = 3, 0
AD_COIN_DECIDED = {'reward_B': True, 'per_day': True, 'cooldown_sec': True}         # Saul 2026-11-01: 3 a day, no cooldown
SHOP_FREE_ITEM_PER_CLAIM, SHOP_FREE_COINS_B_PER_CLAIM, SHOP_FREE_PER_SLOT_PER_DAY = 1, 5, 3
SHOP_FREE_DECIDED = {'item_per_claim': True, 'coins_B_per_claim': True, 'per_slot_per_day': True}   # Saul 2026-11-01
CHECKIN_COINS_B_BY_DAY = {1: 1, 3: 2, 5: 3, 7: 6}
CHECKIN_NO_ITEM_FALLBACK_B = {2: 1, 4: 1}
CHECKIN_SKIN_FALLBACK_B = {6: 3, 7: 5}
CHECKIN_ALLOWED_DAY_COINS_B = {1: (1,), 2: (0, 1), 3: (2,), 4: (0, 1), 5: (3,), 6: (0, 3), 7: (6, 11)}
CHECKIN_ROUND_COINS_B = 12
CLAIM_DOUBLE_WINDOWS = ('checkin', 'wheel_result', 'gift_window', 'chest', 'float_gift', 'quest_claim', 'offline', 'bonus_level',
                        'timer_chest', 'online_gift', 'key_chest')   # key_chest: the summary window after leaving the board
CLAIM_DOUBLE_ACCEPTED_MARKS = {'default': ('checkbox_default_on',), 'offline': ('checkbox_default_on', 'ad_button'),
                               'bonus_level': ('checkbox_default_on', 'ad_button')}
# key_chest_ad_keys: cells opened with the +3 KEYS a watched ad gives are never doubled (rules table v3.2)
CLAIM_DOUBLE_EXCLUDED = ('home_gift', 'skin', 'revive', 'ad_coin', 'ad_item', 'energy_ad', 'shop_free', 'key_chest_ad_keys')
# English games (lead 2026-11-01): these windows of the original game, and any window we added (origin ad-boost/new), must
# have the default-on double (error); the original game's other windows (quests, offline, chest, bonus level) only suggest.
CLAIM_DOUBLE_ENGLISH_REQUIRED_WINDOWS = ('checkin', 'wheel_result', 'gift_window')
CHECKIN_ITEM_AMOUNT_BY_DAY = {2: 2, 4: 3, 7: 3}   # items given on days 2/4/7 when the game has items (generator default)
CLAIM_DOUBLE_MULTIPLIER = 2
CHEST_EVERY_LEVELS, CHEST_FREE_MAX_B, CHEST_DOUBLE_MAX_B = 5, 2, 4
# Timer chest on the level-map page (Saul 2026-11-01, decided in rules table v3.1): wait 20 minutes for a free open, one ad
# cuts 5 minutes, at most 2 cuts a round, 4 rounds a day; a free open gives 3B and never more than 5B.
TIMER_CHEST_PLACEMENT, TIMER_CHEST_FREE_OPEN_B, TIMER_CHEST_FREE_OPEN_MAX_B = 'level_map', 3, 5
TIMER_CHEST_WAIT_SEC, TIMER_CHEST_AD_CUT_SEC, TIMER_CHEST_AD_CUTS_PER_ROUND, TIMER_CHEST_ROUNDS_PER_DAY = 1200, 300, 2, 4
TIMER_CHEST_DECIDED = {'placement': True, 'free_open_B': True, 'free_open_max_B': True, 'wait_sec': True, 'ad_cut_sec': True,
                       'ad_cuts_per_round': True, 'rounds_per_day': True}
# Online-time gift (Saul 2026-11-01, ad-boost online-ladder): playing in the foreground 5/10/15/20/30 minutes in a day pays
# each tier once, 1B..3B a tier, at most 10B a day, reset at midnight.
ONLINE_TIERS_MIN, ONLINE_TIER_MIN_B, ONLINE_TIER_MAX_B, ONLINE_DAY_TOTAL_MAX_B = (5, 10, 15, 20, 30), 1, 3, 10
ONLINE_DECIDED = {'tiers_min': True, 'per_tier_max_B': True, 'day_total_max_B': True}
# Key chest (Saul 2026-11-01, ad-boost key-chest): nine cells about 15B in total, a cell at most 5B (the total is reported).
KEY_CHEST_CELLS, KEY_CHEST_TOTAL_B, KEY_CHEST_CELL_MAX_B = 9, 15, 5
KEY_CHEST_DECIDED = {'total_B': True, 'cell_max_B': True}
# One unlock method per skin (Saul 2026-11-01: 「皮肤的解锁条件只能有一种，不可以既让金币购买又让看广告获取」): an ad item's
# unlock_mode, when written, is one of these; an item never has both a coin row and an ad row.
AD_UNLOCK_ONLY_MODES = ('ads', 'ad', 'video')
FLOAT_EACH_MAX_B, FLOAT_PER_ROUND_MAX = 0.5, 5
BONUS_REWARD_B, BONUS_AD_REWARD_B = 3, 6
SKIN_TRIAL_NO_POPUP_LEVELS, SKIN_TRIAL_EVERY_LEVELS, SKIN_TRIAL_ENDLESS_EVERY_ROUNDS = (1, 2), 3, 3
SKIN_TRIAL_ENDLESS_NO_POPUP_ROUNDS = (1, 2)
# What a trial gives (Saul 2026-11-01): levels games one level; endless games the skin for 30 minutes after an ad, not
# one round. A trial is never doubled. snapshot systems.skin_trial.trial: one_level | ad_minutes (one_round = wrong).
SKIN_TRIAL_LEVEL_TRIAL, SKIN_TRIAL_ENDLESS_TRIAL, SKIN_TRIAL_ENDLESS_MINUTES = 'one_level', 'ad_minutes', 30
SKIN_TRIAL_CLAIM_DOUBLE = False
ITEM_PRICE_MIN_B, ITEM_PRICE_MAX_B = 3, 5
ITEM_PRICE_DEFAULT_B = 3                     # generator default for a single item (ECON-ITEM default_B)
PACK_MAX_DISCOUNT = 0.10
AD_ITEM_PER_VIEW = 1
WHEEL_FREE_PER_DAY, WHEEL_AD_PER_DAY = 1, 2
WHEEL_MAX_CELL_B, WHEEL_EXPECTED_MAX_B = 5, 2
WHEEL_CELL_COINS_B_RANGE = (1, 3)            # coin cells of an ad-boost wheel
WHEEL_DEFAULT_CELLS_B = (1, 2, 1, 3, 1, 2)   # generator default: six coin cells, 1.67B a spin
OFFLINE_MIN_AWAY_SEC, OFFLINE_CAP_SEC, OFFLINE_AD_MULTIPLIER, OFFLINE_MIN_PAYOUT = 300, 7200, 2, 1
UPGRADE_LEVELS, UPGRADE_FIRST_B, UPGRADE_LAST_B, UPGRADE_TOTAL_B, UPGRADE_TOLERANCE = 10, 3, 25, 108, 0.15
QUEST_DAILY_TASK_B, QUEST_DAILY_TASKS = 1, 3
QUEST_ACHIEVEMENT_B_MIN, QUEST_ACHIEVEMENT_B_MAX = 1, 5
QUEST_ACHIEVEMENT_TIERS = (3, 7)             # ECON-QUEST achievement_tiers: 3..7 tiers a class
ENERGY_AD_REFILL = 3
ENERGY_NO_UNLIMITED = True   # Saul 2026-11-01: no 'unlimited energy for N minutes' reward (amount 'unlimited' / unlimited_minutes)
SECOND_PER_AD = 5
SECOND_KEPT_EXCHANGE_MAX_DISCOUNT = 0.10   # kept second currency (English / older games): big exchange pack vs smallest
SECOND_KEPT_AD_NEEDS_DAILY_CAP = True      # kept second currency: watch-ad second currency needs count_per_day

# Claim window of an inflow when inflow.window is not written (ECON-CLAIMX2 reads windows, not rules).
ECON_RULE_WINDOW = {'ECON-CHECKIN': 'checkin', 'ECON-WHEEL': 'wheel_result', 'ECON-CLAIMX2': 'gift_window', 'ECON-CHEST': 'chest',
                    'ECON-FLOAT': 'float_gift', 'ECON-QUEST': 'quest_claim', 'ECON-OFFLINE': 'offline', 'ECON-BONUS': 'bonus_level',
                    'ECON-GIFT': 'home_gift', 'ECON-ADCOIN': 'ad_coin', 'ECON-SHOPFREE': 'shop_free', 'ECON-ADITEM': 'ad_item',
                    'ECON-ENERGY': 'energy_ad', 'ECON-X2': 'result', 'ECON-TIMERCHEST': 'timer_chest',
                    'ECON-ONLINE': 'online_gift', 'ECON-KEYCHEST': 'key_chest'}
ECON_WINDOWS = CLAIM_DOUBLE_WINDOWS + CLAIM_DOUBLE_EXCLUDED + ('result',)   # 'result' = one round's result (ECON-X2)
ECON_WINDOW_SYSTEM = {'checkin': 'checkin', 'wheel_result': 'wheel', 'gift_window': 'gift_window', 'chest': 'chest',
                      'float_gift': 'float_gift', 'quest_claim': 'quests', 'offline': 'offline', 'bonus_level': 'bonus_level',
                      'timer_chest': 'timer_chest', 'online_gift': 'online_gift', 'key_chest': 'key_chest'}
# snapshot.systems key a rule belongs to (systems_origin {<system>: 'ad-boost'|'new'} -> that rule is judged as remake).
ECON_RULE_SYSTEM = {'ECON-TIER': 'skins', 'ECON-ADUNLOCK': 'skins', 'ECON-SKINTRIAL': 'skin_trial', 'ECON-X2': 'result_x2',
                    'ECON-GIFT': 'gift_home', 'ECON-ADCOIN': 'ad_coin', 'ECON-SHOPFREE': 'shop_free', 'ECON-SHORTCUT': 'shortcut',
                    'ECON-REVISIT': 'revisit', 'ECON-CHECKIN': 'checkin', 'ECON-CHEST': 'chest', 'ECON-FLOAT': 'float_gift',
                    'ECON-BONUS': 'bonus_level', 'ECON-ITEM': 'items', 'ECON-PACK': 'items', 'ECON-ADITEM': 'ad_item',
                    'ECON-WHEEL': 'wheel', 'ECON-OFFLINE': 'offline', 'ECON-UPGRADE': 'upgrade', 'ECON-QUEST': 'quests',
                    'ECON-ENERGY': 'energy', 'ECON-TIMERCHEST': 'timer_chest', 'ECON-ONLINE': 'online_gift',
                    'ECON-KEYCHEST': 'key_chest'}
# ad-boost module names also accepted as systems_origin keys ('-' and '_' both fine).
ECON_SYSTEM_ALIASES = {'coin_ad': ('ad_coin',), 'quest_x2': ('quests',), 'gift': ('gift_window', 'chest', 'float_gift'),
                       'skin_ad': ('skins', 'skin_trial'), 'hint': ('ad_item',), 'booster_refill': ('ad_item',),
                       'online_ladder': ('online_gift',)}
# Field names economy_snapshot.v1 knows; anything else (keys starting with '_' aside) -> report schema_warnings.
ECON_SNAPSHOT_FIELDS = {
    'top': ('schema', 'game', 'meta', 'B', 'currencies', 'inflows', 'sinks', 'systems', 'systems_origin', 'configs', 'unknowns'),
    'game': ('name', 'no', 'engine', 'kind', 'mode', 'project', 'platform_kit', 'economy_policy'),
    'meta': ('source', 'tool', 'version', 'generated_at', 'generated_by', 'notes'),
    'B': ('value', 'how', 'evidence', 'note'),
    'currency': ('id', 'label', 'role', 'evidence', 'origin', 'note'),
    'inflow': ('id', 'rule', 'window', 'origin', 'currency', 'amount', 'amounts', 'day', 'by_day', 'day_evidence', 'rows_total',
               'per', 'needs_ad', 'x2', 'x2_evidence', 'count_per_day', 'per_round_max', 'every_levels', 'weight', 'cooldown_ms',
               'cooldown_sec', 'item', 'placement', 'unlimited_minutes', 'wait_sec', 'ad_cut_sec', 'ad_cuts_per_round',
               'rounds_per_day', 'tier_min', 'evidence', 'note'),
    'sink': ('id', 'rule', 'origin', 'kind', 'currency', 'price', 'gives', 'gives_currency', 'pack_size', 'item', 'ad_unlock_views',
             'unlock_mode', 'rarity', 'group', 'unlock', 'source', 'line', 'level', 'evidence', 'note'),
    'systems': ('shop', 'skins', 'items', 'checkin', 'wheel', 'gift_home', 'gift_window', 'offline', 'upgrade', 'quests', 'energy',
                'shortcut', 'revisit', 'revive', 'result_x2', 'skin_trial', 'chest', 'float_gift', 'bonus_level', 'shop_free',
                'ad_coin', 'ad_item', 'timer_chest', 'online_gift', 'key_chest'),
    'skin_trial': ('present', 'no_popup_levels', 'every_levels', 'endless_every_rounds', 'endless_no_popup_rounds', 'trial',
                   'trial_minutes', 'claim_double', 'evidence', 'note'),
    'configs': ('wheel', 'offline', 'upgrade_lines', 'quests', 'energy'),
}
ECON_META_SOURCES = ('auto_scan', 'hand')
ECON_AUTO_SCAN_SKIP_NOTE = 'auto scan did not find this system; it may have been missed, confirm by hand (自动扫描没找到，可能漏读，要人确认)'


def _num(x):
    return type(x) in (int, float) and x == x and x not in (float('inf'), float('-inf'))


def _b_fraction(w):
    return abs(w - round(w)) > 1e-9


def _b_amount_ok(amount, k, B):
    """Is amount the game's number for k*B? B may be fractional (Saul 2026-10-31, e.g. B = 72.5): when k*B is
    fractional (5 x 72.5 = 362.5) the game writes a whole number, so anything less than 1 away passes (362, 363);
    when k*B is whole (10 x 72.5 = 725) it must match exactly. Same rule as the learning library's isB_k / eq."""
    if not _num(amount) or not _num(B) or B <= 0:
        return False
    w = k * B
    return abs(amount - w) < 1 if _b_fraction(w) else abs(amount - w) < 1e-6


def _b_low(k, B):
    """Lowest whole amount that still counts as 'at least kB' (k*B rounded down when fractional)."""
    w = k * B
    return math.floor(w) if _b_fraction(w) else w


def _b_high(k, B):
    """Highest whole amount that still counts as 'at most kB' (k*B rounded up when fractional)."""
    w = k * B
    return math.ceil(w) if _b_fraction(w) else w


def _b_level(price, levels, B):
    """Which of levels (multiples of B) price stands for under _b_amount_ok, or None."""
    return next((k for k in sorted(levels) if _b_amount_ok(price, k, B)), None)


def item_price_errors(price, B):
    """One consumable in-game item (pack of 1) costs 3B..5B of the main currency (ECON-ITEM)."""
    if not _num(price) or not _num(B) or B <= 0:
        return ['item price and B must be positive numbers']
    if price < _b_low(ITEM_PRICE_MIN_B, B) or price > _b_high(ITEM_PRICE_MAX_B, B):
        return ['item price %s is %.2fB; a single item must cost %dB..%dB' % (price, price / B, ITEM_PRICE_MIN_B, ITEM_PRICE_MAX_B)]
    return []


def pack_discount_errors(unit_price, pack_price, pack_size):
    """A multi-item pack may be at most 10% cheaper than buying the items one by one (ECON-PACK)."""
    if not _num(unit_price) or unit_price <= 0 or not _num(pack_price) or pack_price < 0 or type(pack_size) is not int or pack_size < 2:
        return ['pack needs a positive unit price, a pack price and pack_size >= 2']
    discount = 1 - pack_price / (unit_price * pack_size)
    if discount > PACK_MAX_DISCOUNT + 1e-9:
        return ['pack of %d at %s is %.0f%% off %s each; at most %d%% allowed'
                % (pack_size, pack_price, discount * 100, unit_price, round(PACK_MAX_DISCOUNT * 100))]
    return []


def ad_item_errors(per_view):
    """One completed rewarded video gives exactly one item (ECON-ADITEM)."""
    return [] if per_view == AD_ITEM_PER_VIEW else ['an item ad must give %d item per completed view, not %r' % (AD_ITEM_PER_VIEW, per_view)]


def wheel_expected(cells):
    """Expected main-currency amount of one spin; cells = [{'amount': n, 'weight': w}], missing weight = 1, non-coin = 0."""
    pairs = []
    for c in cells:
        w, a = c.get('weight', 1), c.get('amount', 0)
        pairs.append((w if _num(w) and w > 0 else 0, a if _num(a) and a > 0 else 0))
    total = sum(w for w, _ in pairs)
    return sum(w * a for w, a in pairs) / total if total > 0 else 0.0


def wheel_config_errors(cfg, B):
    """cfg = {free_per_day, ad_per_day, cells:[{amount, weight}], result_double:{enabled, default_checked}} (ECON-WHEEL)."""
    if not isinstance(cfg, dict) or not _num(B) or B <= 0:
        return ['wheel config and positive B required']
    errors = []
    if cfg.get('free_per_day') != WHEEL_FREE_PER_DAY or cfg.get('ad_per_day') != WHEEL_AD_PER_DAY:
        errors.append('wheel must give %d free + %d ad spins per day, not %r + %r'
                      % (WHEEL_FREE_PER_DAY, WHEEL_AD_PER_DAY, cfg.get('free_per_day'), cfg.get('ad_per_day')))
    cells = [c for c in cfg.get('cells') or [] if isinstance(c, dict)]
    if not cells:
        errors.append('wheel cells missing')
    else:
        top = max((c.get('amount') or 0) for c in cells)
        if top > _b_high(WHEEL_MAX_CELL_B, B):
            errors.append('largest wheel cell %s is %.2fB; at most %dB' % (top, top / B, WHEEL_MAX_CELL_B))
        exp = wheel_expected(cells)
        if exp > _b_high(WHEEL_EXPECTED_MAX_B, B) + 1e-9:
            errors.append('one spin is worth %.2fB on average; at most %dB' % (exp / B, WHEEL_EXPECTED_MAX_B))
    rd = cfg.get('result_double') or {}
    if not (rd.get('enabled') and rd.get('default_checked')):
        errors.append('wheel result needs the watch-ad double checkbox, checked by default')
    return errors


def offline_errors(cfg):
    """cfg = {min_away_sec, cap_sec, ad_multiplier, min_payout} (ECON-OFFLINE)."""
    if not isinstance(cfg, dict):
        return ['offline config required']
    want = {'min_away_sec': OFFLINE_MIN_AWAY_SEC, 'cap_sec': OFFLINE_CAP_SEC, 'ad_multiplier': OFFLINE_AD_MULTIPLIER}
    errors = ['offline %s must be %s, not %r' % (k, v, cfg.get(k)) for k, v in want.items() if cfg.get(k) != v]
    if not _num(cfg.get('min_payout')) or cfg['min_payout'] < OFFLINE_MIN_PAYOUT:
        errors.append('offline popup must not show below %d (min_payout %r)' % (OFFLINE_MIN_PAYOUT, cfg.get('min_payout')))
    return errors


def upgrade_costs(B, levels=UPGRADE_LEVELS, first_B=UPGRADE_FIRST_B, last_B=UPGRADE_LAST_B):
    """costs[k] = round_half_up(first_B*B * r^k), r = (last/first)^(1/(levels-1)); B=10 -> 30,38,...,250 (total 1078).
    B may be fractional (72.5 -> whole costs, each rounded half up)."""
    if not _num(B) or isinstance(B, bool) or B <= 0 or type(levels) is not int or levels < 2:
        raise ValueError('positive B and at least 2 levels required')
    r = (last_B / first_B) ** (1 / (levels - 1))
    return [int(math.floor(first_B * B * r ** k + 0.5)) for k in range(levels)]


def upgrade_errors(costs, B):
    """One upgrade line: 10 levels, first ~3B, last ~25B, total ~108B (each within 15%), never cheaper later (ECON-UPGRADE)."""
    if not isinstance(costs, (list, tuple)) or not costs or not all(_num(c) and c > 0 for c in costs) or not _num(B) or B <= 0:
        return ['upgrade line needs positive costs and B']
    errors, tol = [], UPGRADE_TOLERANCE
    if len(costs) != UPGRADE_LEVELS:
        errors.append('upgrade line has %d levels; %d expected' % (len(costs), UPGRADE_LEVELS))
    if any(b < a for a, b in zip(costs, costs[1:])):
        errors.append('upgrade costs must not go down')
    for label, got, want in (('first', costs[0], UPGRADE_FIRST_B), ('last', costs[-1], UPGRADE_LAST_B), ('total', sum(costs), UPGRADE_TOTAL_B)):
        if abs(got / B - want) > want * tol + 1e-9:
            errors.append('upgrade %s cost is %.1fB; about %dB (±%d%%) expected' % (label, got / B, want, round(tol * 100)))
    return errors


def quest_reward_errors(daily, achievements, B, achievement_gives_skin=False):
    """daily = [amount per daily task]; achievements = [[tier amounts of one class], ...] (ECON-QUEST).
    Daily tasks ~1B each (0.5B..1.5B), together less than one 5B home gift; achievement classes 3..7 tiers,
    1B..5B, not decreasing; achievements never give skins."""
    if not _num(B) or B <= 0:
        return ['positive B required']
    errors = []
    for i, x in enumerate(daily or []):
        if not _num(x) or not (0.5 * B <= x <= 1.5 * B):
            errors.append('daily task %d reward %r is not about %dB' % (i + 1, x, QUEST_DAILY_TASK_B))
    if daily and sum(x for x in daily if _num(x)) >= GIFT_REWARD_B * B:
        errors.append('daily tasks together give %.1fB; must stay below one %dB home gift' % (sum(daily) / B, GIFT_REWARD_B))
    for c, tiers in enumerate(achievements or []):
        if not isinstance(tiers, (list, tuple)) or not (QUEST_ACHIEVEMENT_TIERS[0] <= len(tiers) <= QUEST_ACHIEVEMENT_TIERS[1]):
            errors.append('achievement class %d needs %d..%d tiers' % (c + 1, *QUEST_ACHIEVEMENT_TIERS))
            continue
        if any(not _num(x) or x < _b_low(QUEST_ACHIEVEMENT_B_MIN, B) or x > _b_high(QUEST_ACHIEVEMENT_B_MAX, B) for x in tiers):
            errors.append('achievement class %d rewards must be %dB..%dB' % (c + 1, QUEST_ACHIEVEMENT_B_MIN, QUEST_ACHIEVEMENT_B_MAX))
        elif any(b < a for a, b in zip(tiers, tiers[1:])):
            errors.append('achievement class %d rewards must not go down' % (c + 1))
    if achievement_gives_skin:
        errors.append('achievements must not give skins')
    return errors


def energy_errors(cfg):
    """cfg = {original_has_energy, ad_refill, skip_if_no_room} (ECON-ENERGY; behaviour lives in remake-ads)."""
    if not isinstance(cfg, dict):
        return ['energy config required']
    errors = []
    if cfg.get('original_has_energy') is False:
        errors.append('energy only when the original game has energy')
    if cfg.get('ad_refill') != ENERGY_AD_REFILL:
        errors.append('energy ad must give +%d, not %r' % (ENERGY_AD_REFILL, cfg.get('ad_refill')))
    if cfg.get('skip_if_no_room') is not True:
        errors.append('energy ad must not play when +%d does not fit' % ENERGY_AD_REFILL)
    return errors


def second_currency_ad_views(price):
    """Former second-currency price -> completed ad views: every 5 = 1 view, rounded up, at least 1 (ECON-SECOND)."""
    if not _num(price) or price < 0:
        raise ValueError('second-currency price must be a non-negative number')
    return max(1, math.ceil(price / SECOND_PER_AD))


def _fmt_B(x, B):
    return '%s (%.2fB)' % (x, x / B) if _num(x) and _num(B) and B > 0 else repr(x)


def checkin_bad_days(day_coins, B, has_items=None, has_skins=None, skip_days=()):
    """{day: problem} for a seven-day check-in (ECON-CHECKIN). day_coins = {day: main-currency coins that day, every row of
    the same day added up}; a day with no coin row counts as 0. Allowed per day (B multiples): 1:1, 2:0|1, 3:2, 4:0|1, 5:3,
    6:0|3, 7:6|11 (0 on day 2/4 = an item that day, 1B when the game has no items; 0 on day 6 = a skin, 3B when no skin can be
    given; day 7 = 6B + skin, or 6B + 5B = 11B without one). has_items / has_skins False (the game has none) makes the
    fallback compulsory. skip_days: days whose amount could not be read (reported as unknown by the caller)."""
    if not _num(B) or B <= 0:
        return {0: 'positive B required'}
    bad = {}
    for d, allowed in sorted(CHECKIN_ALLOWED_DAY_COINS_B.items()):
        if d in skip_days:
            continue
        got = day_coins.get(d, 0)
        if not _num(got):
            bad[d] = 'check-in day %d amount %r is not a number' % (d, got)
        elif not any((abs(got) < 1e-9) if k == 0 else _b_amount_ok(got, k, B) for k in allowed):
            bad[d] = 'check-in day %d gives %s; %s expected' % (d, _fmt_B(got, B), ' or '.join('%dB' % k for k in allowed))
    forced = []
    if has_items is False:
        forced += [(d, CHECKIN_COINS_B_BY_DAY.get(d, 0) + k, 'the game has no items') for d, k in CHECKIN_NO_ITEM_FALLBACK_B.items()]
    if has_skins is False:
        forced += [(d, CHECKIN_COINS_B_BY_DAY.get(d, 0) + k, 'no skin can be given') for d, k in CHECKIN_SKIN_FALLBACK_B.items()]
    for d, want, why in forced:
        if d not in bad and d not in skip_days and not _b_amount_ok(day_coins.get(d, 0), want, B):
            bad[d] = 'check-in day %d gives %s; %s, so %dB' % (d, _fmt_B(day_coins.get(d, 0), B), why, want)
    return bad


def checkin_coin_errors(day_coins, B, has_items=None, has_skins=None, skip_days=()):
    """Problems of a seven-day check-in as a list (see checkin_bad_days)."""
    return [m for _, m in sorted(checkin_bad_days(day_coins, B, has_items, has_skins, skip_days).items())]


def daily_cap_errors(count_per_day, cap, label):
    """A claim that may be repeated needs a daily cap of 1..cap (ECON-ADCOIN per_day, ECON-SHOPFREE per_slot_per_day)."""
    if count_per_day is None:
        return ['%s: no daily cap found (count_per_day); at most %d a day' % (label, cap)]
    if type(count_per_day) is not int or not (1 <= count_per_day <= cap):
        return ['%s: %r a day; at most %d a day' % (label, count_per_day, cap)]
    return []


def chest_errors(amount, B, needs_ad=False, every_levels=None):
    """Every-5-levels chest (ECON-CHEST): the free claim gives at most 2B; the ticked watch-ad claim (needs_ad, or 2 x the free
    amount through the default double checkbox) at most 4B; every_levels, when known, is 5."""
    if not _num(amount) or amount < 0 or not _num(B) or B <= 0:
        return ['chest amount and positive B required']
    cap = CHEST_DOUBLE_MAX_B if needs_ad else CHEST_FREE_MAX_B
    errors = []
    if amount > _b_high(cap, B):
        errors.append('%s chest gives %s; at most %dB' % ('watch-ad' if needs_ad else 'free', _fmt_B(amount, B), cap))
    if every_levels is not None and every_levels != CHEST_EVERY_LEVELS:
        errors.append('chest every %r levels; every %d expected' % (every_levels, CHEST_EVERY_LEVELS))
    return errors


def float_gift_errors(amount, B, per_round_max):
    """Floating in-game gift (ECON-FLOAT): each at most 0.5B, at most 5 a round."""
    if not _num(B) or B <= 0:
        return ['positive B required']
    errors = []
    if not _num(amount) or amount < 0 or amount > _b_high(FLOAT_EACH_MAX_B, B):
        errors.append('floating gift gives %s; at most %sB each' % (_fmt_B(amount, B), FLOAT_EACH_MAX_B))
    if type(per_round_max) is not int or not (1 <= per_round_max <= FLOAT_PER_ROUND_MAX):
        errors.append('floating gifts %r a round; at most %d' % (per_round_max, FLOAT_PER_ROUND_MAX))
    return errors


def bonus_level_errors(amount, B, needs_ad=False):
    """Bonus level (ECON-BONUS): 3B; after the ad it comes to 6B in total (needs_ad row = the total after the ad)."""
    want = BONUS_AD_REWARD_B if needs_ad else BONUS_REWARD_B
    if not _b_amount_ok(amount, want, B):
        return ['%s bonus level gives %s; %dB expected' % ('watch-ad' if needs_ad else 'free', _fmt_B(amount, B), want)]
    return []


def skin_trial_errors(cfg, mode='levels'):
    """cfg = systems.skin_trial {present, no_popup_levels, every_levels, endless_every_rounds} (ECON-SKINTRIAL).
    Levels games: not in levels 1-2, then every 3 levels (before level 3, 6, 9 ...); endless games: every 3 rounds;
    'both' checks both; idle games only need the popup."""
    if not isinstance(cfg, dict) or cfg.get('present') is not True:
        return ['skins need the watch-ad skin trial popup (Saul 2026-11-01: every 3 levels, not in levels 1-2)']
    errors = []
    if mode not in ('endless', 'idle'):
        npl = cfg.get('no_popup_levels')
        if not isinstance(npl, (list, tuple)) or sorted(set(npl)) != list(SKIN_TRIAL_NO_POPUP_LEVELS):
            errors.append('skin trial must stay away from levels %s exactly, not %r'
                          % ('/'.join(map(str, SKIN_TRIAL_NO_POPUP_LEVELS)), npl))
        if cfg.get('every_levels') != SKIN_TRIAL_EVERY_LEVELS:
            errors.append('skin trial every %r levels; every %d expected' % (cfg.get('every_levels'), SKIN_TRIAL_EVERY_LEVELS))
    if mode in ('endless', 'both') and cfg.get('endless_every_rounds') != SKIN_TRIAL_ENDLESS_EVERY_ROUNDS:
        errors.append('skin trial every %r endless rounds; every %d expected'
                      % (cfg.get('endless_every_rounds'), SKIN_TRIAL_ENDLESS_EVERY_ROUNDS))
    if mode in ('endless', 'both') and cfg.get('endless_no_popup_rounds') is not None:
        npr = cfg['endless_no_popup_rounds']
        if not isinstance(npr, (list, tuple)) or sorted(set(npr)) != list(SKIN_TRIAL_ENDLESS_NO_POPUP_ROUNDS):
            errors.append('skin trial must stay away from endless rounds %s exactly, not %r'
                          % ('/'.join(map(str, SKIN_TRIAL_ENDLESS_NO_POPUP_ROUNDS)), npr))
    # what the trial gives (Saul 2026-11-01): levels -> one level; endless -> the skin for 30 minutes after an ad, not one round
    trial = cfg.get('trial')
    allowed = {'levels': (SKIN_TRIAL_LEVEL_TRIAL,), 'endless': (SKIN_TRIAL_ENDLESS_TRIAL,),
               'both': (SKIN_TRIAL_LEVEL_TRIAL, SKIN_TRIAL_ENDLESS_TRIAL)}.get(mode, (SKIN_TRIAL_LEVEL_TRIAL, SKIN_TRIAL_ENDLESS_TRIAL))
    if trial is not None and trial not in allowed:
        errors.append('skin trial gives %r; %s expected%s' % (trial, ' or '.join(allowed), ' (endless: 30 minutes after an ad, not one round)'
                                                               if SKIN_TRIAL_ENDLESS_TRIAL in allowed else ''))
    if mode in ('endless', 'both', 'idle') and cfg.get('trial_minutes') is not None \
            and cfg['trial_minutes'] != SKIN_TRIAL_ENDLESS_MINUTES:
        errors.append('endless skin trial lasts %r minutes; %d expected' % (cfg['trial_minutes'], SKIN_TRIAL_ENDLESS_MINUTES))
    if cfg.get('claim_double') not in (None, False, 'none') and SKIN_TRIAL_CLAIM_DOUBLE is False:
        errors.append('a skin trial is never doubled (claim_double %r)' % cfg['claim_double'])
    return errors


def exchange_discount_errors(packs):
    """Kept second currency (ECON-SECOND): exchange packs of one currency pair, packs = [{'id', 'price', 'gives'}].
    Per unit received, no pack may be more than 10% cheaper than the smallest pack."""
    errors = ['%s: exchange needs a positive price and gives' % p.get('id') for p in packs
              if not (_num(p.get('price')) and p['price'] > 0 and _num(p.get('gives')) and p['gives'] > 0)]
    ok = [p for p in packs if _num(p.get('price')) and p['price'] > 0 and _num(p.get('gives')) and p['gives'] > 0]
    if len(ok) < 2:
        return errors
    small = min(ok, key=lambda p: (p['gives'], p['price']))
    unit = small['price'] / small['gives']
    for p in ok:
        off = 1 - (p['price'] / p['gives']) / unit
        if p is not small and off > SECOND_KEPT_EXCHANGE_MAX_DISCOUNT + 1e-9:
            errors.append('%s: %s for %s is %.0f%% better than the smallest pack (%s for %s); at most %d%%'
                          % (p.get('id'), p['price'], p['gives'], off * 100, small['price'], small['gives'],
                             round(SECOND_KEPT_EXCHANGE_MAX_DISCOUNT * 100)))
    return errors


def _close(word, choices):
    import difflib
    m = difflib.get_close_matches(str(word), list(choices), n=1, cutoff=0.6)
    return ' (did you mean %s?)' % m[0] if m else ''


def _econ_schema_warnings(snap):
    """Unknown field names / values in an economy_snapshot.v1 ('inflows[3].amout: unknown field (did you mean amount?)').
    Warnings only: they never change ok or the exit code; a misspelt field is otherwise read as missing."""
    F, out = ECON_SNAPSHOT_FIELDS, []

    def keys(obj, kind, path):
        if isinstance(obj, dict):
            out.extend('%s%s: unknown field%s' % (path, k, _close(k, F[kind])) for k in obj
                       if not str(k).startswith('_') and k not in F[kind])

    def value(v, allowed, path):
        if v is not None and v not in allowed:
            out.append('%s: unknown value %r%s' % (path, v, _close(v, allowed)))

    keys(snap, 'top', '')
    for name in ('game', 'meta', 'B', 'systems'):
        keys(snap.get(name), name, name + '.')
    configs = snap.get('configs')
    keys(configs, 'configs', 'configs.')
    systems = snap.get('systems') if isinstance(snap.get('systems'), dict) else {}
    keys(systems.get('skin_trial'), 'skin_trial', 'systems.skin_trial.')
    meta = snap.get('meta') if isinstance(snap.get('meta'), dict) else {}
    value(meta.get('source'), ECON_META_SOURCES, 'meta.source')
    for name, kind in (('currencies', 'currency'), ('inflows', 'inflow'), ('sinks', 'sink')):
        for i, row in enumerate(snap.get(name) or []):
            if isinstance(row, dict):
                keys(row, kind, '%s[%d].' % (name, i))
                value(row.get('origin'), ECON_ORIGINS, '%s[%d].origin' % (name, i))
                if kind == 'inflow':
                    value(row.get('window'), ECON_WINDOWS, '%s[%d].window' % (name, i))
    so = snap.get('systems_origin')
    if isinstance(so, dict):
        for k, v in so.items():
            n = str(k).replace('-', '_')
            if n not in F['systems'] and n not in ECON_SYSTEM_ALIASES:
                out.append('systems_origin.%s: unknown system%s' % (k, _close(n, F['systems'] + tuple(ECON_SYSTEM_ALIASES))))
            value(v, ECON_ORIGINS, 'systems_origin.%s' % k)
    elif so is not None:
        out.append('systems_origin: must be an object {system: "ad-boost"|"new"}')
    return out


def _econ_systems_origin(raw):
    """systems_origin with ad-boost module names expanded: {'coin-ad': 'ad-boost'} -> {'ad_coin': 'ad-boost'}."""
    out = {}
    for k, v in (raw.items() if isinstance(raw, dict) else ()):
        n = str(k).replace('-', '_')
        for s in ECON_SYSTEM_ALIASES.get(n, (n,)):
            out[s] = v
    return out


ECON_AUDIT_SCHEMA = 'economy_audit.v1'
ECON_SNAPSHOT_SCHEMA = 'economy_snapshot.v1'
ECON_RULE_TITLES = {  # same order as economy_rules_table.json; report rows come out in this order
    'ECON-B': 'B can be determined', 'ECON-LEVEL10': 'ten ordinary levels pay 10B',
    'ECON-TIER': 'skin coin price by rarity 5/10/20/40/80B', 'ECON-ADUNLOCK': '60% ad unlocks, views = ceil(price / 2B), one unlock method',
    'ECON-SKINTRIAL': 'skins -> watch-ad skin trial, not levels 1-2, then every 3 levels / 3 rounds; endless 30 min, no x2',
    'ECON-X2': 'result watch-ad x2', 'ECON-NOCUR': 'no-currency game doubles picked-up items',
    'ECON-GIFT': 'home gift 5B, 30 min, no checkbox', 'ECON-ADCOIN': 'watch-ad coins 5B, at most 3 a day',
    'ECON-SHOPFREE': 'shop free claim 1 item or 5B, at most 3 a slot a day, no x2',
    'ECON-SHORTCUT': 'add-to-desktop 5B once', 'ECON-REVISIT': 'home revisit 5B once',
    'ECON-CHECKIN': 'seven-day check-in 1B/2B/3B/6B, fallbacks 1B/3B/+5B, same-day rows added',
    'ECON-CLAIMX2': 'every claim window: double checkbox checked by default',
    'ECON-CHEST': 'every-5-levels chest: free <= 2B, watch-ad <= 4B',
    'ECON-TIMERCHEST': 'timer chest on the level map: free open 3B (<= 5B), 20 min, ad -5 min x2, 4 rounds, claim double',
    'ECON-ONLINE': 'online-time gift 5/10/15/20/30 min, 1B..3B a tier, <= 10B a day',
    'ECON-KEYCHEST': 'key chest nine cells about 15B, a cell <= 5B',
    'ECON-FLOAT': 'floating gift <= 0.5B, at most 5 a round',
    'ECON-BONUS': 'bonus level 3B, ad to 6B',
    'ECON-ITEM': 'single item 3B..5B', 'ECON-PACK': 'pack discount <= 10%', 'ECON-ADITEM': 'one item per ad',
    'ECON-WHEEL': 'wheel 1 free + 2 ad, cell <= 5B, spin <= 2B', 'ECON-OFFLINE': 'offline 5 min .. 2 h, ad x2',
    'ECON-UPGRADE': 'upgrade line 10 levels 3B..25B, ~108B', 'ECON-QUEST': 'daily ~1B, achievements 1B..5B, no skins',
    'ECON-ENERGY': 'energy only if original, ad +3, no unlimited energy',
    'ECON-SECOND': 'no second currency from levels; 5 = 1 ad; kept: exchange <= 10% off, ad capped per day',
    'ECON-DEAD': 'every currency can be spent', 'ECON-PACING': 'shop pacing numbers (report only)'}


def _econ_status(rule, kind):
    """Severity of a broken rule for this kind of game: remake error, english suggest (english_default rules error), finished label."""
    if kind == 'english':
        return 'error' if rule in ECON_ENGLISH_DEFAULT else 'suggest'
    return ECON_SEVERITY_BY_KIND.get(kind, 'suggest')


def _econ_cap_undecided(status):
    """A miss of a number Saul has not decided (decided_by_saul=false) is at most ECON_UNDECIDED_MAX."""
    return ECON_UNDECIDED_MAX if status == 'error' else status


def _econ_added_by(rule, offenders, systems_origin):
    """'ad-boost' / 'new' when the rows behind a miss (or the rule's whole system) were added by us, else None."""
    o = systems_origin.get(ECON_RULE_SYSTEM.get(rule))
    if o in ECON_ORIGINS[1:]:
        return o
    return next((x.get('origin') for x in offenders or () if x.get('origin') in ECON_ORIGINS[1:]), None)


def economy_audit(snapshot, kind=None):
    """Check an economy_snapshot.v1 against ECON-xx. Returns economy_audit.v1 with one row per rule:
    status pass | error | suggest | label (broken; severity by kind) | skip (not applicable) | unknown (snapshot lacks data)
    | info (ECON-PACING numbers). Optional snapshot extensions read when present: inflow.day / inflow.by_day (check-in day;
    rows of the same day are added up), inflow.weight (wheel cell), inflow.cooldown_ms, inflow.window (claim window, else
    from the rule: ECON_RULE_WINDOW), inflow.count_per_day, inflow.per_round_max, inflow.every_levels, inflow/sink.origin
    (original | ad-boost | new), snapshot.systems_origin {<system>: 'ad-boost'|'new'}, systems.skin_trial, sink.item (pack ->
    single item id), sink.line / sink.level (upgrade), sink kind 'exchange' (price -> gives [gives_currency]), meta.source
    (auto_scan | hand), and snapshot.configs.{wheel, offline, upgrade_lines, quests, energy} shaped like the *_errors() inputs.
    English games: a miss whose rows have origin ad-boost/new (or whose system is in systems_origin) is judged as remake.
    v3.1 (Saul 2026-11-01): inflow.cooldown_sec (watch-ad coins: no cooldown), sink.unlock_mode / sink.item (one unlock
    method per skin), windows online_gift / key_chest (ECON-ONLINE / ECON-KEYCHEST). With meta.source = auto_scan an
    unread count_per_day is unknown, not a miss. v3.2: online_gift / key_chest are ECON-CLAIMX2 windows too
    (key_chest_ad_keys is excluded); timer chest wait_sec / ad_cut_sec / ad_cuts_per_round / rounds_per_day on a row or in
    a systems.timer_chest object; inflow.tier_min (online-time tier minutes) is read but not judged.
    Misses of numbers Saul has not decided (decided_by_saul=false) are at most suggest. Unknown field names go to
    schema_warnings; with meta.source = auto_scan, 'system not found' skips go to confirm_by_hand."""
    snap = snapshot if isinstance(snapshot, dict) else {}
    game = snap.get('game') if isinstance(snap.get('game'), dict) else {}
    kind = kind or game.get('kind') or 'unknown'
    b = snap.get('B') if isinstance(snap.get('B'), dict) else {}
    B = b.get('value') if _num(b.get('value')) and b.get('value') > 0 else None
    currencies = [c for c in snap.get('currencies') or [] if isinstance(c, dict)]
    roles = {c.get('id'): c.get('role') for c in currencies}
    main_ids = {c.get('id') for c in currencies if c.get('role') == 'main'}
    inflows = [x for x in snap.get('inflows') or [] if isinstance(x, dict)]
    sinks = [x for x in snap.get('sinks') or [] if isinstance(x, dict)]
    systems = snap.get('systems') if isinstance(snap.get('systems'), dict) else {}
    configs = snap.get('configs') if isinstance(snap.get('configs'), dict) else {}
    meta = snap.get('meta') if isinstance(snap.get('meta'), dict) else {}
    auto_scan = meta.get('source') == 'auto_scan'
    sys_origin = _econ_systems_origin(snap.get('systems_origin'))
    warnings = _econ_schema_warnings(snap)
    rows = []

    def add(rule, broken=None, ok=None, skip=None, unknown=None, info=None, soft=None, offenders=None, found=False, weak=None):
        """broken: misses (severity by kind); soft: misses of numbers Saul has not decided (at most suggest);
        weak: misses an English game only gets a suggestion for (original-game windows outside the required ones; for
        other kinds they count as broken); offenders: the rows behind broken (None = every row of this rule);
        found=True: the skip is a positive finding (endless game, has a currency ...), not 'system not found'."""
        extra = {}
        if weak and kind != 'english':
            broken, weak = list(broken or []) + list(weak), None
        if weak and not broken:
            status, details = ('suggest', list(weak) + list(soft or []))
            extra['english_optional'] = True
        elif broken:
            status, details = _econ_status(rule, kind), list(broken) + list(weak or []) + list(soft or [])
            added = _econ_added_by(rule, [x for x in inflows + sinks if x.get('rule') == rule] if offenders is None else offenders,
                                   sys_origin)
            if kind == 'english' and added and status != 'error':
                status, extra['judged_as'] = 'error', 'remake'
                details.append('judged as remake: added by %s (origin), not part of the original game' % added)
        elif soft:
            status, details = _econ_cap_undecided(_econ_status(rule, kind)), list(soft)
            extra['capped_by'] = 'decided_by_saul=false'
        elif unknown:
            status, details = 'unknown', unknown
        elif skip:
            status, details = 'skip', list(skip)
            if auto_scan and not found:
                details.append(ECON_AUTO_SCAN_SKIP_NOTE)
                extra['confirm_by_hand'] = True
        elif info is not None:
            status, details = 'info', info
        else:
            status, details = 'pass', ok or []
        rows.append(dict({'id': rule, 'title': ECON_RULE_TITLES[rule], 'status': status, 'english_default': rule in ECON_ENGLISH_DEFAULT,
                          'details': details}, **extra))

    def by_rule(rule):
        return [x for x in inflows if x.get('rule') == rule]

    def window_of(x):
        if x.get('window'):
            return x['window']
        if str(x.get('id', '')).startswith('gift_window'):
            return 'gift_window'
        return ECON_RULE_WINDOW.get(x.get('rule'))

    def in_window(w):
        return [x for x in inflows if window_of(x) == w]

    def is_main(cur):
        return cur in main_ids if main_ids else cur in roles

    def doubled(x):
        return x.get('x2') not in (None, '', 'none')

    def each(rows_, check):
        """(messages, offending rows) of check(row) -> [messages] over rows_."""
        msgs, offs = [], []
        for x in rows_:
            m = check(x)
            if m:
                msgs += m
                offs.append(x)
        return msgs, offs

    def in_B(x):
        return '%s (%.2fB)' % (x, x / B) if B else str(x)

    # ECON-B
    if B is None or b.get('how') in (None, 'unknown'):
        add('ECON-B', broken=['B is unknown; find normalLevelCoins, the median of the first 10 ordinary levels, or cheapest item / 10'])
    else:
        add('ECON-B', ok=['B = %s via %s' % (B, b.get('how'))])
    if B is None:  # every other numeric rule needs B
        for rule in ECON_RULE_TITLES:
            if rule != 'ECON-B':
                add(rule, unknown=['B unknown'])
        return _econ_report(snap, kind, B, rows, warnings)

    # ECON-LEVEL10
    lv = [x for x in by_rule('ECON-LEVEL10') or [x for x in inflows if x.get('id') == 'level_clear'] if x.get('per') == 'level']
    if game.get('mode') == 'endless' and not lv:
        add('ECON-LEVEL10', skip=['endless game: no ordinary levels'], found=True)
    elif not lv:
        add('ECON-LEVEL10', unknown=['no per-level inflow in snapshot'])
    else:
        amounts = lv[0].get('amounts') if isinstance(lv[0].get('amounts'), list) else None
        if amounts and len(amounts) >= LEVEL_WINDOW:  # every full group of ten (1-10, 11-20, ...), not only the first
            windows = [(i + 1, i + LEVEL_WINDOW, sum(x or 0 for x in amounts[i:i + LEVEL_WINDOW]))
                       for i in range(0, len(amounts) - LEVEL_WINDOW + 1, LEVEL_WINDOW)]
        else:
            windows = [(1, LEVEL_WINDOW, (lv[0].get('amount') or 0) * LEVEL_WINDOW)]
        bad = ['levels %d-%d pay %s; %dB expected' % (a, z, in_B(got), LEVEL_WINDOW_SUM_B)
               for a, z, got in windows if not _b_amount_ok(got, LEVEL_WINDOW_SUM_B, B)]
        if bad:
            add('ECON-LEVEL10', broken=bad)
        else:
            add('ECON-LEVEL10', ok=['%d group(s) of ten ordinary levels each pay %s' % (len(windows), in_B(windows[0][2]))])

    # ECON-TIER / ECON-ADUNLOCK (permanent cosmetics bought with the main currency). game.economy_policy picks the
    # contract: normal-5-80.v1 (default; ad unlocks rule36-c.v1) or a frozen normal-10-50.v1 table (rule36-b.v1), whose
    # misses are reported as info only. Prices are compared with _b_level, so a fractional B works.
    cosmetics = [s for s in sinks if s.get('kind') in ('skin', 'background') and (not main_ids or s.get('currency') in main_ids)]
    priced = [s for s in cosmetics if s.get('rarity') != 'limited' and ((s.get('price') or 0) > 0 or (s.get('ad_unlock_views') or 0) > 0)]
    tier_policy = game.get('economy_policy') or SKIN_POLICY
    if not isinstance(tier_policy, str) or tier_policy not in ECONOMY_POLICIES:
        why = ['game.economy_policy %r is neither %s (new) nor %s (frozen old table)' % (tier_policy, SKIN_POLICY, SKIN_POLICY_LEGACY)]
        add('ECON-TIER', unknown=why)
        add('ECON-ADUNLOCK', unknown=why)
    else:
        tier_legacy = tier_policy == SKIN_POLICY_LEGACY
        ad_policy = AD_UNLOCK_POLICY_LEGACY if tier_legacy else AD_UNLOCK_POLICY
        tiers = skin_tiers_B(tier_policy)
        tier_text = '/'.join(str(v) for v in tiers.values()) + 'B'

        def verdict(rule, bad, skip):
            if bad and tier_legacy:
                add(rule, info=['frozen %s table, reported only: %s' % (tier_policy, m) for m in bad])
            else:
                add(rule, broken=bad, skip=skip)

        def cost(s):  # coin price, or the rarity's tier price for an ad-only row
            return s.get('price') or (tiers.get(s.get('rarity')) or 0) * B

        tier_bad = []
        for s in cosmetics:
            price = s.get('price') or 0
            if price <= 0:
                continue
            level = _b_level(price, tiers.values(), B)
            want = tiers.get(s.get('rarity'))
            if level is None or (want is not None and level != want):
                tier_bad.append('%s costs %s; tiers are %s by rarity (%s)' % (s.get('id'), in_B(price), tier_text, tier_policy))
        verdict('ECON-TIER', tier_bad, None if cosmetics else ['no coin-priced skins/backgrounds'])
        ad_bad = []
        for s in priced:
            views = s.get('ad_unlock_views') or 0
            if views:
                want = ad_unlock_views(cost(s), B, ad_policy)
                if want != views:
                    ad_bad.append('%s needs %s views; %s expected for %s (%s: %s)' % (
                        s.get('id'), views, want, in_B(cost(s)), ad_policy,
                        '10B->1 ... 50B->9' if tier_legacy else '1 view = 2B, rounded up'))
        for group in sorted({s.get('kind') for s in priced}):
            g = [s for s in priced if s.get('kind') == group]
            n, k = len(g), sum(1 for s in g if (s.get('ad_unlock_views') or 0) > 0)
            if not ad_unlock_share_ok(n, k, ad_policy):
                a_, b_ = AD_UNLOCK_SHARE
                ad_bad.append('%s: %d of %d priced items unlock by ads; %s expected' % (
                    group, k, n, 'about half' if tier_legacy else '60%% (%d..%d)' % (a_ * n // b_, -(-a_ * n // b_))))
            if tier_legacy:
                continue
            cheapest = min(cost(s) for s in g)
            if all((s.get('ad_unlock_views') or 0) > 0 for s in g if cost(s) == cheapest):
                ad_bad.append('%s: the cheapest item (%s) must stay a coin purchase' % (group, in_B(cheapest)))
            for rarity in sorted({s.get('rarity') for s in g}, key=str):
                t = [s for s in g if s.get('rarity') == rarity]
                ads = sum(1 for s in t if (s.get('ad_unlock_views') or 0) > 0)
                if len(t) >= 2 and ads in (0, len(t)):
                    ad_bad.append('%s %s: %d of %d unlock by ads; a rarity of 2 or more needs both ad and coin items'
                                  % (group, rarity, ads, len(t)))
        # One unlock method per skin (Saul 2026-11-01): an ad row's unlock_mode, when written, is ads only, and one item
        # (sink.item) never has both a coin row and an ad row. The ad row's price only sets the number of views.
        perm, by_item = [s for s in sinks if s.get('kind') in ('skin', 'background')], {}
        for s in perm:
            mode = s.get('unlock_mode')
            if (s.get('ad_unlock_views') or 0) > 0 and mode and str(mode).lower() not in AD_UNLOCK_ONLY_MODES:
                ad_bad.append('%s: unlock_mode %s; an ad item is not also sold for coins, one unlock method per skin' % (s.get('id'), mode))
            if s.get('item'):
                by_item.setdefault(s['item'], []).append(s)
        for item, xs in sorted(by_item.items(), key=lambda kv: str(kv[0])):
            coin_ids = [str(s.get('id')) for s in xs if not (s.get('ad_unlock_views') or 0) and (s.get('price') or 0) > 0]
            ad_ids = [str(s.get('id')) for s in xs if (s.get('ad_unlock_views') or 0) > 0]
            if coin_ids and ad_ids:
                ad_bad.append('%s: sold for coins (%s) and unlocked by ads (%s); one unlock method per skin'
                              % (item, ', '.join(coin_ids), ', '.join(ad_ids)))
        verdict('ECON-ADUNLOCK', ad_bad, None if priced else ['no priced skins/backgrounds'])

    # ECON-SKINTRIAL (Saul 2026-11-01: with skins, a watch-ad skin trial popup every 3 levels, none in levels 1-2)
    has_skins = bool(systems.get('skins')) or any(s.get('kind') == 'skin' for s in sinks)
    trial = systems.get('skin_trial')
    if not has_skins:
        add('ECON-SKINTRIAL', skip=['no skins'])
    elif trial is None:
        add('ECON-SKINTRIAL', unknown=['systems.skin_trial not reported; a game with skins needs the watch-ad skin trial popup'])
    elif trial is True:
        add('ECON-SKINTRIAL', unknown=['skin trial present, schedule not reported (no_popup_levels, every_levels, endless_every_rounds)'])
    else:
        add('ECON-SKINTRIAL', broken=skin_trial_errors(trial, game.get('mode')), offenders=[],
            ok=['skin trial: levels %s free, then every %s levels' % (trial.get('no_popup_levels'), trial.get('every_levels'))])

    # ECON-X2 / ECON-NOCUR
    if systems.get('result_x2') is True:
        add('ECON-X2', ok=['result watch-ad x2 present'])
    elif systems.get('result_x2') is False:
        add('ECON-X2', broken=['no result watch-ad x2'])
    else:
        add('ECON-X2', unknown=['systems.result_x2 not reported'])
    if currencies:
        add('ECON-NOCUR', skip=['game has a currency'], found=True)
    else:
        add('ECON-NOCUR', broken=None if systems.get('result_x2') else ['no-currency game still needs x2 of picked-up items'])

    # ECON-GIFT
    gift = by_rule('ECON-GIFT')
    if not systems.get('gift_home') and not gift:
        add('ECON-GIFT', skip=['no home gift'])
    elif not gift:
        add('ECON-GIFT', unknown=['home gift amount not found'])
    else:
        bad, offs = each(gift, lambda g: (['home gift gives %s; %dB expected' % (in_B(g.get('amount') or 0), GIFT_REWARD_B)]
                                          if not _b_amount_ok(g.get('amount') or 0, GIFT_REWARD_B, B) else [])
                         + (['home gift cooldown %s ms; %d ms expected' % (g['cooldown_ms'], GIFT_COOLDOWN_MS)]
                            if 'cooldown_ms' in g and g['cooldown_ms'] != GIFT_COOLDOWN_MS else [])
                         + (['home gift must not get a double checkbox (Saul 2026-10-31)']
                            if str(g.get('x2', 'none')).startswith('checkbox') else []))
        add('ECON-GIFT', broken=bad, offenders=offs)

    def capped_daily(x, cap):
        """(misses, unread) of a repeatable claim's daily cap; an auto scan that did not read count_per_day -> unread."""
        if x.get('count_per_day') is None and auto_scan:
            return [], ['%s: count_per_day not read; at most %d a day (confirm by hand)' % (x.get('id'), cap)]
        return daily_cap_errors(x.get('count_per_day'), cap, str(x.get('id'))), []

    # ECON-ADCOIN (Saul 2026-11-01 decided all three: 5B a view, at most 3 a day, no cooldown)
    adcoin = in_window('ad_coin')
    if not adcoin and not systems.get('ad_coin'):
        add('ECON-ADCOIN', skip=['no stand-alone watch-ad coins'])
    elif not adcoin:
        add('ECON-ADCOIN', unknown=['watch-ad coins amount not found'])
    else:
        unk = [u for x in adcoin for u in capped_daily(x, AD_COIN_PER_DAY)[1]]
        bad, offs = each(adcoin, lambda x: (['%s gives %s; %dB expected' % (x.get('id'), in_B(x.get('amount') or 0), AD_COIN_REWARD_B)]
                                            if not _b_amount_ok(x.get('amount') or 0, AD_COIN_REWARD_B, B) else [])
                         + (['%s: watch-ad coins are not doubled (x2 %s)' % (x.get('id'), x.get('x2'))] if doubled(x) else [])
                         + capped_daily(x, AD_COIN_PER_DAY)[0]
                         + (['%s: cooldown %s s; watch-ad coins have no cooldown (Saul 2026-11-01)' % (x.get('id'), x['cooldown_sec'])]
                            if _num(x.get('cooldown_sec')) and x['cooldown_sec'] != AD_COIN_COOLDOWN_SEC else []))
        add('ECON-ADCOIN', broken=bad, offenders=offs, unknown=unk,
            ok=['watch-ad coins %s, %s a day' % (in_B(adcoin[0].get('amount') or 0), adcoin[0].get('count_per_day'))])

    # ECON-SHOPFREE (Saul 2026-11-01 decided: 1 item or 5B a claim, at most 3 a slot a day; never doubled)
    sf = in_window('shop_free')
    if not sf and not systems.get('shop_free'):
        add('ECON-SHOPFREE', skip=['no shop free claim'])
    elif not sf:
        add('ECON-SHOPFREE', unknown=['shop free claim amounts not found'])
    else:
        def sf_check(x):
            amt, m = x.get('amount'), []
            if is_main(x.get('currency')):
                if not _b_amount_ok(amt or 0, SHOP_FREE_COINS_B_PER_CLAIM, B):
                    m.append('%s gives %s; %dB a claim expected' % (x.get('id'), in_B(amt or 0), SHOP_FREE_COINS_B_PER_CLAIM))
            elif amt != SHOP_FREE_ITEM_PER_CLAIM:
                m.append('%s gives %r %s; %d item a claim expected' % (x.get('id'), amt, x.get('currency'), SHOP_FREE_ITEM_PER_CLAIM))
            if doubled(x):
                m.append('%s: a shop free claim is already a watch-ad reward, no x2 (x2 %s)' % (x.get('id'), x.get('x2')))
            return m + capped_daily(x, SHOP_FREE_PER_SLOT_PER_DAY)[0]
        bad, offs = each(sf, sf_check)
        add('ECON-SHOPFREE', broken=bad, offenders=offs,
            unknown=[u for x in sf for u in capped_daily(x, SHOP_FREE_PER_SLOT_PER_DAY)[1]])

    # ECON-SHORTCUT / ECON-REVISIT
    for rule, key, label in (('ECON-SHORTCUT', 'shortcut', 'add-to-desktop'), ('ECON-REVISIT', 'revisit', 'home revisit')):
        rows_ = by_rule(rule)
        if systems.get(key) is False and not rows_:
            add(rule, broken=['no %s entry (all games, Saul 2026-10-29)' % label])
        elif not rows_:
            add(rule, unknown=['%s reward not found' % label])
        else:
            def sc_check(x, label=label):
                m = []
                if not _b_amount_ok(x.get('amount') or 0, SHORTCUT_REWARD_B, B):
                    m.append('%s gives %s; %dB expected' % (label, in_B(x.get('amount') or 0), SHORTCUT_REWARD_B))
                if x.get('per') not in (None, 'once'):
                    m.append('%s must pay once, not per %s' % (label, x.get('per')))
                if main_ids and x.get('currency') not in main_ids:
                    m.append('%s must pay the main currency, not %s' % (label, x.get('currency')))
                return m
            bad, offs = each(rows_, sc_check)
            add(rule, broken=bad, offenders=offs)

    # ECON-CHECKIN (rows of the same day are added up; by_day {"1": n, ...} rows count too; fallbacks per the rules table)
    ck = in_window('checkin')
    if not systems.get('checkin') and not ck:
        add('ECON-CHECKIN', broken=['remake games must have the seven-day check-in'] if kind == 'remake' else None,
            skip=None if kind == 'remake' else ['no check-in'])
    else:
        day_coins, day_rows, unread = {}, {}, set()
        for x in ck:
            if x.get('currency') is not None and not is_main(x.get('currency')):
                continue  # the skin / item part of a day
            if isinstance(x.get('by_day'), dict):
                pairs = [(int(k), v) for k, v in x['by_day'].items() if str(k).isdigit()]
            elif type(x.get('day')) is int:
                pairs = [(x['day'], x.get('amount'))]
            else:
                continue
            for d, v in pairs:
                day_rows.setdefault(d, []).append(x)
                if _num(v):
                    day_coins[d] = day_coins.get(d, 0) + v
                else:
                    unread.add(d)
        unread -= set(day_coins)
        if not day_coins:
            add('ECON-CHECKIN', unknown=['check-in day amounts not found'])
        else:
            no_items = systems.get('items') is False and not any(s.get('kind') == 'item' for s in sinks)
            no_skins = systems.get('skins') is False and not has_skins
            bad_days = checkin_bad_days(day_coins, B, False if no_items else None, False if no_skins else None, unread)
            add('ECON-CHECKIN', broken=[m for _, m in sorted(bad_days.items())],
                offenders=[x for d in bad_days for x in day_rows.get(d, ck)],
                unknown=['check-in day %d amount not read' % d for d in sorted(unread)],
                ok=['check-in days %s' % ', '.join('%d:%s' % (d, in_B(v)) for d, v in sorted(day_coins.items()))])

    # ECON-CLAIMX2: every claim window in the rules table (excluded ones are not looked at); window = inflow.window or the rule's
    w_cfg = {}
    if isinstance(configs.get('wheel'), dict) and isinstance(configs['wheel'].get('result_double'), dict):
        rd = configs['wheel']['result_double']
        w_cfg['wheel_result'] = ('checkbox_default_on' if rd.get('default_checked') else 'checkbox_default_off') if rd.get('enabled') else 'none'
    if isinstance(configs.get('quests'), dict) and 'claim_double' in configs['quests']:
        cd = configs['quests']['claim_double']
        w_cfg['quest_claim'] = (cd if isinstance(cd, str) else ('checkbox_default_on' if cd.get('default_checked') else 'checkbox_default_off')
                                if isinstance(cd, dict) and cd.get('enabled') else 'none')
    if isinstance(configs.get('offline'), dict):
        oc = configs['offline']
        if oc.get('x2') or oc.get('ad_multiplier') == CLAIM_DOUBLE_MULTIPLIER:
            w_cfg['offline'] = oc.get('x2') or 'ad_button'
    cbad, cweak, cunk, coffs, present = [], [], [], [], []
    for w in CLAIM_DOUBLE_WINDOWS:
        wr = in_window(w)
        if not systems.get(ECON_WINDOW_SYSTEM[w]) and not wr and w not in w_cfg:
            continue
        present.append(w)
        accepted = CLAIM_DOUBLE_ACCEPTED_MARKS.get(w, CLAIM_DOUBLE_ACCEPTED_MARKS['default'])
        marks = {}
        for x in wr:
            m = x.get('x2') or None
            if (m in (None, 'none')) and x.get('needs_ad') and 'ad_button' in accepted:
                m = 'ad_button'  # the watch-ad row is the ad button of this window
            if m:
                marks.setdefault(m, []).append(x)
        if w in w_cfg:
            marks.setdefault(w_cfg[w], [])
        wrong = sorted(m for m in marks if m not in accepted)
        if not marks:
            cunk.append('%s: double option not found' % w)
        elif wrong:
            msg = '%s: double must be %s, found %s' % (w, ' or '.join(accepted), ', '.join(sorted(marks)))
            offs = [x for m in wrong for x in marks[m]]
            added = sys_origin.get(ECON_WINDOW_SYSTEM[w]) in ECON_ORIGINS[1:] or any(x.get('origin') in ECON_ORIGINS[1:] for x in offs)
            if w in CLAIM_DOUBLE_ENGLISH_REQUIRED_WINDOWS or added:
                cbad.append(msg + ('' if w in CLAIM_DOUBLE_ENGLISH_REQUIRED_WINDOWS else ' (added by us: required)'))
            else:   # English: the original game's own quest / offline / chest / bonus window -> only a suggestion
                cweak.append(msg + ' (original window: English games only suggest)')
            coffs += offs
    if not present:
        add('ECON-CLAIMX2', skip=['no claim window (check-in, wheel, gift window, chest, floating gift, quests, offline, bonus level, '
                                  'timer chest, online-time gift, key chest)'])
    else:
        add('ECON-CLAIMX2', broken=cbad, weak=cweak, unknown=cunk, offenders=coffs, ok=['double checkbox on: %s' % ', '.join(present)])

    # ECON-CHEST / ECON-FLOAT / ECON-BONUS (ad-boost gift-pack and bonus-level amounts; main-currency rows are checked)
    for rule, w, label in (('ECON-CHEST', 'chest', 'every-5-levels chest'), ('ECON-FLOAT', 'float_gift', 'floating gift'),
                           ('ECON-BONUS', 'bonus_level', 'bonus level')):
        wr = in_window(w)
        coin = [x for x in wr if x.get('currency') is None or is_main(x.get('currency'))]
        if not wr and not systems.get(ECON_WINDOW_SYSTEM[w]):
            add(rule, skip=['no %s' % label])
            continue
        if not wr:
            add(rule, unknown=['%s amounts not found' % label])
            continue
        unk = ['%s: amount not read' % x.get('id') for x in coin if not _num(x.get('amount'))]
        coin = [x for x in coin if _num(x.get('amount'))]
        if rule == 'ECON-CHEST':
            bad, offs = each(coin, lambda x: chest_errors(x['amount'], B, bool(x.get('needs_ad')), x.get('every_levels')))
        elif rule == 'ECON-BONUS':
            bad, offs = each(coin, lambda x: bonus_level_errors(x['amount'], B, bool(x.get('needs_ad'))))
        else:  # amount per coin row; per_round_max on any row that writes it (item gifts too)
            def cap_of(x):
                return x['per_round_max'] if x.get('per_round_max') is not None else FLOAT_PER_ROUND_MAX
            bad, offs = each(wr, lambda x: float_gift_errors(x['amount'] if x in coin else 0, B, cap_of(x)))
            if all(x.get('per_round_max') is None for x in wr):
                unk.append('floating gifts per round not reported (per_round_max); at most %d' % FLOAT_PER_ROUND_MAX)
        add(rule, broken=bad, offenders=offs, unknown=unk,
            ok=['%s: %s' % (label, ', '.join(in_B(x['amount']) for x in coin) or 'no main-currency amounts')])

    # ECON-TIMERCHEST (Saul 2026-11-01 decided: on the level-map page, not home; a free open gives 3B and at most 5B); the
    # claim double is ECON-CLAIMX2 timer_chest.
    tc = in_window('timer_chest')
    if not tc and not systems.get('timer_chest'):
        add('ECON-TIMERCHEST', skip=['no timer chest'])
    elif not tc:
        add('ECON-TIMERCHEST', unknown=['timer chest amounts not found'])
    else:
        coin = [x for x in tc if not x.get('needs_ad') and (x.get('currency') is None or is_main(x.get('currency')))]
        bad, offs = each(tc, lambda x: (['%s: timer chest belongs on the %s page, not %s' % (x.get('id'), TIMER_CHEST_PLACEMENT, x['placement'])]
                                        if x.get('placement') not in (None, TIMER_CHEST_PLACEMENT) else [])
                         + (['%s: free timer chest gives %s; at most %dB' % (x.get('id'), in_B(x['amount']), TIMER_CHEST_FREE_OPEN_MAX_B)]
                            if x in coin and _num(x.get('amount')) and x['amount'] > _b_high(TIMER_CHEST_FREE_OPEN_MAX_B, B) else []))
        # v3.2 (same as the learning library's economy_plan.js): wait times written in systems.timer_chest (an object) or on
        # a timer-chest row must be the decided numbers, and the ads together must cut less than the wait (no ad-only open).
        tsys = systems['timer_chest'] if isinstance(systems.get('timer_chest'), dict) else {}
        decided = {'wait_sec': TIMER_CHEST_WAIT_SEC, 'ad_cut_sec': TIMER_CHEST_AD_CUT_SEC,
                   'ad_cuts_per_round': TIMER_CHEST_AD_CUTS_PER_ROUND, 'rounds_per_day': TIMER_CHEST_ROUNDS_PER_DAY}
        tm = {k: o[k] for o in [tsys] + tc for k in decided if _num(o.get(k))}   # rows win over systems.timer_chest
        tbad = ['timer chest %s is %s; %s decided (Saul 2026-11-01)' % (k, tm[k], v) for k, v in decided.items() if k in tm and tm[k] != v]
        if tsys.get('placement') not in (None, TIMER_CHEST_PLACEMENT):
            tbad.append('timer chest belongs on the %s page, not %s (systems.timer_chest)' % (TIMER_CHEST_PLACEMENT, tsys['placement']))
        if any(k in tm for k in ('wait_sec', 'ad_cut_sec', 'ad_cuts_per_round')):
            wait, cut, cuts = (tm.get(k, decided[k]) for k in ('wait_sec', 'ad_cut_sec', 'ad_cuts_per_round'))
            if cut * cuts >= wait:
                tbad.append('timer chest ads cut %s x %s = %s s, not less than the %s s wait: watching ads would open it directly'
                            % (cut, cuts, cut * cuts, wait))
        if tbad:
            bad, offs = bad + tbad, tc
        add('ECON-TIMERCHEST', broken=bad, offenders=offs,
            unknown=['%s: amount not read' % x.get('id') for x in coin if not _num(x.get('amount'))],
            ok=['timer chest: %s; wait times %s' % (', '.join(in_B(x['amount']) for x in coin if _num(x.get('amount'))) or 'no main-currency amounts',
                                                    'as decided' if tm else 'not written (confirm by hand)')])

    # ECON-ONLINE / ECON-KEYCHEST (Saul 2026-11-01 「默认数值就这样」; ad-boost online-ladder / key-chest; main-currency
    # rows): an online-time tier pays 1B..3B and a day's tiers add up to at most 10B; a key-chest cell gives at most 5B and
    # a board of nine coin cells adds up to about 15B (each cell's rounding allowed: off by less than the number of cells).
    for rule, w, label in (('ECON-ONLINE', 'online_gift', 'online-time gift'), ('ECON-KEYCHEST', 'key_chest', 'key chest')):
        wr = in_window(w)
        if not wr and not systems.get(w):
            add(rule, skip=['no %s' % label])
            continue
        if not wr:
            add(rule, unknown=['%s amounts not found' % label])
            continue
        coin = [x for x in wr if x.get('currency') is None or is_main(x.get('currency'))]
        unk = ['%s: amount not read' % x.get('id') for x in coin if not _num(x.get('amount'))]
        coin = [x for x in coin if _num(x.get('amount'))]
        total = sum(x['amount'] for x in coin)
        if rule == 'ECON-ONLINE':
            bad, offs = each(coin, lambda x: ['%s: an online-time tier gives %s; %dB..%dB a tier' % (
                x.get('id'), in_B(x['amount']), ONLINE_TIER_MIN_B, ONLINE_TIER_MAX_B)]
                if not _b_low(ONLINE_TIER_MIN_B, B) <= x['amount'] <= _b_high(ONLINE_TIER_MAX_B, B) else [])
            if total > _b_high(ONLINE_DAY_TOTAL_MAX_B, B):
                bad.append('online-time tiers add up to %s a day; at most %dB' % (in_B(total), ONLINE_DAY_TOTAL_MAX_B))
                offs = coin
        else:
            bad, offs = each(coin, lambda x: ['%s: a key-chest cell gives %s; at most %dB' % (x.get('id'), in_B(x['amount']), KEY_CHEST_CELL_MAX_B)]
                             if x['amount'] > _b_high(KEY_CHEST_CELL_MAX_B, B) else [])
            if len(coin) == len(wr) == KEY_CHEST_CELLS and abs(total - KEY_CHEST_TOTAL_B * B) >= KEY_CHEST_CELLS:
                bad.append('the %d key-chest cells add up to %s; about %dB' % (KEY_CHEST_CELLS, in_B(total), KEY_CHEST_TOTAL_B))
                offs = coin
        add(rule, broken=bad, offenders=offs, unknown=unk,
            ok=['%s: %s (total %s)' % (label, ', '.join(in_B(x['amount']) for x in coin) or 'no main-currency amounts', in_B(total))])

    # ECON-ITEM / ECON-PACK / ECON-ADITEM
    items = [s for s in sinks if s.get('kind') == 'item' and (not main_ids or s.get('currency') in main_ids) and (s.get('price') or 0) > 0]
    singles = [s for s in items if (s.get('pack_size') or 1) == 1]
    add('ECON-ITEM', skip=None if singles else ['no coin-priced single items'],
        broken=[('%s: ' % s.get('id')) + e for s in singles for e in item_price_errors(s.get('price'), B)])
    packs = [s for s in items if (s.get('pack_size') or 1) > 1]
    unit = {s.get('item', s.get('id')): s.get('price') for s in singles}
    pbad, punk = [], []
    for s in packs:
        u = unit.get(s.get('item'))
        if u is None:
            punk.append('%s: single price of its item not found (set sink.item)' % s.get('id'))
        else:
            pbad += [('%s: ' % s.get('id')) + e for e in pack_discount_errors(u, s.get('price'), s.get('pack_size'))]
    add('ECON-PACK', skip=None if packs else ['no item packs'], broken=pbad, unknown=punk)
    aditem = [x for x in inflows if x.get('rule') == 'ECON-ADITEM']
    add('ECON-ADITEM', skip=None if aditem else ['no item ads'],
        broken=[('%s: ' % x.get('id')) + e for x in aditem for e in ad_item_errors(x.get('amount'))])

    # ECON-WHEEL
    wcfg = configs.get('wheel')
    wrows = by_rule('ECON-WHEEL')
    if not systems.get('wheel') and not wrows and not wcfg:
        add('ECON-WHEEL', skip=['no wheel'])
    else:
        if not isinstance(wcfg, dict) and wrows:
            free = [x.get('count_per_day') for x in wrows if not x.get('needs_ad') and x.get('count_per_day') is not None]
            paid = [x.get('count_per_day') for x in wrows if x.get('needs_ad') and x.get('count_per_day') is not None]
            marks = {x.get('x2') for x in wrows}
            wcfg = {'free_per_day': max(free) if free else None, 'ad_per_day': max(paid) if paid else None,
                    'cells': [{'amount': x.get('amount') or 0, 'weight': x.get('weight', 1)} for x in wrows],
                    'result_double': {'enabled': marks == {'checkbox_default_on'}, 'default_checked': marks == {'checkbox_default_on'}}}
        if isinstance(wcfg, dict):
            add('ECON-WHEEL', broken=wheel_config_errors(wcfg, B))
        else:
            add('ECON-WHEEL', unknown=['wheel numbers not found'])

    # ECON-OFFLINE
    ocfg = configs.get('offline')
    if not systems.get('offline') and not ocfg:
        add('ECON-OFFLINE', skip=['no offline income'])
    else:
        add('ECON-OFFLINE', broken=offline_errors(ocfg) if isinstance(ocfg, dict) else None,
            unknown=None if isinstance(ocfg, dict) else ['offline numbers not found'])

    # ECON-UPGRADE
    lines = configs.get('upgrade_lines')
    if not isinstance(lines, list):
        ups = [s for s in sinks if s.get('kind') == 'upgrade' and (not main_ids or s.get('currency') in main_ids)]
        grouped = {}
        for s in ups:
            grouped.setdefault(s.get('line', 'line'), []).append(s)
        lines = [[s.get('price') or 0 for s in sorted(g, key=lambda s: s.get('level', 0))] for _, g in sorted(grouped.items())]
    if not systems.get('upgrade') and not lines:
        add('ECON-UPGRADE', skip=['no upgrade line'])
    elif game.get('mode') == 'idle':
        add('ECON-UPGRADE', skip=['idle/merge game: price = output per second x minutes, capped by offline limit'], found=True)
    elif not lines:
        add('ECON-UPGRADE', unknown=['upgrade prices not found'])
    else:
        add('ECON-UPGRADE', broken=['line %d: %s' % (i + 1, e) for i, line in enumerate(lines) for e in upgrade_errors(line, B)])

    # ECON-QUEST
    qcfg = configs.get('quests')
    qrows = by_rule('ECON-QUEST')
    if not systems.get('quests') and not qrows and not qcfg:
        add('ECON-QUEST', skip=['no quests or achievements'])
    else:
        if not isinstance(qcfg, dict):
            qcfg = {'daily': [x.get('amount') or 0 for x in qrows if x.get('per') == 'day' and x.get('currency') != 'skin'],
                    'achievements': [[x.get('amount') or 0 for x in qrows if x.get('per') == 'once' and x.get('currency') != 'skin']]
                    if any(x.get('per') == 'once' for x in qrows) else [],
                    'achievement_gives_skin': any(x.get('currency') == 'skin' for x in qrows)}
        if not qcfg.get('daily') and not qcfg.get('achievements') and not qcfg.get('achievement_gives_skin'):
            add('ECON-QUEST', unknown=['quest rewards not found'])
        else:
            add('ECON-QUEST', broken=quest_reward_errors(qcfg.get('daily'), qcfg.get('achievements'), B, qcfg.get('achievement_gives_skin')))

    # ECON-ENERGY (+3 a view; Saul 2026-11-01: no unlimited energy, e.g. amount 'unlimited' or unlimited_minutes)
    ecfg = configs.get('energy')
    energy_ids = {c for c, r in roles.items() if r == 'energy'}

    def unlimited(x):
        a = x.get('amount')
        return (isinstance(a, str) and any(w in a.lower() for w in ('unlimited', 'infinite'))) or x.get('unlimited_minutes') is not None

    unl = [x for x in inflows if (x.get('currency') in energy_ids or x.get('rule') == 'ECON-ENERGY' or window_of(x) == 'energy_ad')
           and unlimited(x)] if ENERGY_NO_UNLIMITED else []
    ubad = ['%s: unlimited energy is not allowed (Saul 2026-11-01); an energy ad gives +%d' % (x.get('id'), ENERGY_AD_REFILL) for x in unl]
    if isinstance(ecfg, dict) and ecfg.get('unlimited_minutes') is not None and ENERGY_NO_UNLIMITED:
        ubad.append('configs.energy.unlimited_minutes %r: unlimited energy is not allowed (Saul 2026-11-01)' % ecfg['unlimited_minutes'])
    if not systems.get('energy') and not ecfg and not ubad:
        add('ECON-ENERGY', skip=['no energy'])
    elif not isinstance(ecfg, dict):
        refill = [x.get('amount') for x in by_rule('ECON-ENERGY') if x not in unl]
        add('ECON-ENERGY', broken=ubad + ['energy ad gives %r; +%d expected' % (r, ENERGY_AD_REFILL) for r in refill if r != ENERGY_AD_REFILL],
            offenders=unl or None, unknown=None if refill else ['energy ad amount not found'])
    else:
        add('ECON-ENERGY', broken=ubad + energy_errors(ecfg), offenders=unl or None)

    # ECON-SECOND
    second = {c for c, r in roles.items() if r == 'second'}
    sbad, soffs = [], []
    for x in inflows:
        if x.get('currency') in second and x.get('per') == 'level':
            sbad.append('%s: levels pay second currency %s' % (x.get('id'), x.get('currency')))
            soffs.append(x)
    for s in sinks:
        if s.get('currency') in second and (s.get('price') or 0) > 0 and kind == 'remake' and s.get('kind') != 'exchange':
            want = second_currency_ad_views(s['price'])
            if s.get('ad_unlock_views') != want:
                sbad.append('%s: costs %s %s; new games unlock it with %d ads (5 = 1 ad)' % (s.get('id'), s['price'], s.get('currency'), want))
                soffs.append(s)
    # kept second currency (English / older games): exchange packs at most 10% better than the smallest; watch-ad second
    # currency needs a daily cap. Checked for every kind; a new game should not have them in the first place.
    pairs = {}
    for s in sinks:
        if s.get('kind') == 'exchange' and (s.get('currency') in second or s.get('gives_currency') in second):
            pairs.setdefault((s.get('currency'), s.get('gives_currency')), []).append(s)
    for (_, _), packs in sorted(pairs.items(), key=lambda kv: str(kv[0])):
        errs = exchange_discount_errors(packs)
        sbad += errs
        soffs += packs if errs else []
    if SECOND_KEPT_AD_NEEDS_DAILY_CAP:
        b2, o2 = each([x for x in inflows if x.get('currency') in second and (x.get('needs_ad') or x.get('per') == 'ad')],
                      lambda x: [] if type(x.get('count_per_day')) is int and x['count_per_day'] >= 1 else
                      ['%s: watch-ad %s needs a daily cap (count_per_day), found %r' % (x.get('id'), x.get('currency'), x.get('count_per_day'))])
        sbad, soffs = sbad + b2, soffs + o2
    add('ECON-SECOND', skip=None if second else ['one currency only'], broken=sbad, offenders=soffs)

    # ECON-DEAD
    spend = {s.get('currency') for s in sinks}
    dead = [c for c, r in roles.items() if r in ('main', 'second', 'ticket') and c not in spend]
    add('ECON-DEAD', skip=None if roles else ['no currency'], broken=['currency %s has nowhere to spend' % c for c in dead])

    # ECON-PACING (numbers only, never blocking)
    shop = [s for s in sinks if s.get('kind') in ('skin', 'background', 'upgrade', 'other') and (not main_ids or s.get('currency') in main_ids)
            and (s.get('price') or 0) > 0 and not (s.get('ad_unlock_views') or 0)]
    if not shop:
        add('ECON-PACING', skip=['nothing to buy with the main currency'])
    else:
        total = sum(s['price'] for s in shop)
        tiers = {}
        for s in shop:
            tiers.setdefault(s.get('rarity') or s.get('kind'), []).append(s['price'])
        add('ECON-PACING', info={'cheapest_levels': round(min(s['price'] for s in shop) / B, 1),
                                 'one_per_tier_levels': {k: round(min(v) / B, 1) for k, v in sorted(tiers.items())},
                                 'buy_all_levels_no_x2': round(total / B, 1), 'buy_all_levels_every_x2': round(total / (2 * B), 1),
                                 'items': len(shop)})
    return _econ_report(snap, kind, B, rows, warnings)


def _econ_report(snap, kind, B, rows, warnings=None):
    """economy_audit.v1. Rows in ECON_RULE_TITLES order. schema_warnings (unknown field names) never change ok;
    confirm_by_hand lists rules skipped only because an auto scan (meta.source = auto_scan) did not find the system."""
    order = {r: i for i, r in enumerate(ECON_RULE_TITLES)}
    rows = sorted(rows, key=lambda r: order.get(r['id'], len(order)))
    count = {}
    for r in rows:
        count[r['status']] = count.get(r['status'], 0) + 1
    game = snap.get('game') if isinstance(snap.get('game'), dict) else {}
    meta = snap.get('meta') if isinstance(snap.get('meta'), dict) else {}
    errors = [] if snap.get('schema') == ECON_SNAPSHOT_SCHEMA else ['snapshot schema must be %s' % ECON_SNAPSHOT_SCHEMA]
    return {'schema': ECON_AUDIT_SCHEMA, 'rules_revision': ECON_RULES_REVISION, 'game': game.get('name'), 'kind': kind, 'B': B,
            'source': meta.get('source', 'hand'), 'schema_errors': errors, 'schema_warnings': list(warnings or []),
            'confirm_by_hand': [r['id'] for r in rows if r.get('confirm_by_hand')],
            'counts': dict(sorted(count.items())), 'ok': not errors and count.get('error', 0) == 0, 'results': rows}


def _economy_audit_main(argv):
    import argparse, json, sys
    ap = argparse.ArgumentParser(prog='product_contract.py economy-audit',
                                 description='Check economy_snapshot.v1 against ECON-xx (remake-economy economy-rules.md).')
    ap.add_argument('--snapshot', required=True, help='economy_snapshot.json')
    ap.add_argument('--kind', choices=['remake', 'english', 'finished', 'unknown'], help='override snapshot game.kind')
    ap.add_argument('--out', help='write the report here as well as stdout')
    a = ap.parse_args(argv)
    with open(a.snapshot, encoding='utf-8') as f:
        report = economy_audit(json.load(f), a.kind)
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(text)
    sys.stdout.write(text)
    return 0 if report['ok'] else 1


def _main(argv=None):
    import argparse, json, sys
    _args = sys.argv[1:] if argv is None else list(argv)
    if _args[:1] == ['economy-audit']:
        return _economy_audit_main(_args[1:])
    ap = argparse.ArgumentParser(description='Write ad_unlock_table.json (remake-economy economy-rules.md #看广告解锁).')
    ap.add_argument('command', choices=['ad-unlock'])
    ap.add_argument('--table', required=True, help='unlock_table.json written by make_skin_table.py')
    ap.add_argument('--out', required=True, help='assets/resources/config/ad_unlock_table.json')
    ap.add_argument('--groups', default=','.join(AD_UNLOCK_GROUPS), help='default skin,background; add map only for ordinary games')
    ap.add_argument('--policy', choices=AD_UNLOCK_POLICIES, default=AD_UNLOCK_POLICY,
                    help='rule36-c.v1 (default, Saul 2026-11-01): 60%%, views = ceil(price / 2B), needs a normal-5-80.v1 table; '
                         'rule36-b.v1: frozen normal-10-50.v1 tables, output byte-identical to v7.8')
    a = ap.parse_args(argv)
    with open(a.table, encoding='utf-8') as f:
        table = json.load(f)
    if budget_errors(table):
        print('\n'.join(budget_errors(table)), file=sys.stderr); return 1
    try:
        ad = ad_unlock_table(table, tuple(g for g in a.groups.split(',') if g), a.policy)
    except ValueError as exc:
        if a.policy == AD_UNLOCK_POLICY_LEGACY:
            raise
        print(str(exc), file=sys.stderr); return 1
    errors = ad_unlock_errors(ad, table)
    if errors:
        print('\n'.join(errors), file=sys.stderr); return 1
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write(json.dumps(ad, ensure_ascii=True, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'out': a.out, 'ad_unlock_items': len(ad['items'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(_main())
