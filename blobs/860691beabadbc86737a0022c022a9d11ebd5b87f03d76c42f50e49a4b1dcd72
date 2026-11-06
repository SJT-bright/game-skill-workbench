#!/usr/bin/env python3
"""Write the skin module table (remake-skins/references/skin-rules.md, both boards; user 2026-10-23).

20 protagonist skins (group "skin"): the limited skin first in the list (shown dimmed as a silhouette until owned),
the starting skin (free), then 18 skins for coins: 7 common, 6 rare, 3 epic, 2 legendary.
10 scene backgrounds (group "background", only when the game has a scene to dress): the starting one (free), then
9 for coins: 3 common, 3 rare, 2 epic, 1 legendary.
Default prices (--economy-policy normal-5-80.v1, Saul 2026-11-01): ordinary-levels = 5/10/20/40/80 ordinary base
rewards (common/rare/epic/legendary/limited: the lowest rarity 5B, every rarity above doubles), including purchasable
limited. --economy-policy normal-10-50.v1 rebuilds a frozen old table at 10/20/30/40/50 (byte-identical to v7.8).
60 % of the priced skins/backgrounds then unlock by ads: product_contract.py ad-unlock (rule36-c.v1).
Use --normal-level-coins when ordinary base income differs from R (ad reward unit).
Explicit legacy-2r preserves the old 2R first price and +1/4/10/20 R curve.
Every skin has a coin bonus that rises with rarity (skins 5-10 / 11-20 / 21-32 / 33-50 %, limited 51-60 %;
backgrounds about half). The limited skin, two formats (user 2026-10-24, both allowed; level games):
  --limited-mode final (default): ONE limited skin, won on the last limited level (--final-level, 70 or more);
  --limited-mode every_10: one limited skin per limited level (10, 20 ... --final-level), all first in the list
    (then 19 + N skins: N limited + the free one + 18 for coins).
Current economy: limited skins cost the top tier (80B; 50B on normal-10-50.v1) in levels and endless games; optional milestone awards grant the same item once. Legacy-2r retains its former limited routes.

Fill in "previewFrame" (R4O2: each skin's own preview picture; templates bind only this, never a slot/frame picture or a
Sprite colour tint; check_skin_preview.py), "name" and "art" (what the skin changes: common = one accessory, rare = colours + accessory, epic = full outfit,
legendary = full costume + effect, limited = the most detailed: themed costume, accessories, aura, own idle animation),
keep the numbers, then run audit_acquisition_progression.py.

Usage:
  python make_skin_table.py --R 50 --levels [--final-level 70] [--limited-mode final|every_10] [--no-backgrounds] [--hero cat]
      --out assets/resources/config/unlock_table.json
  python make_skin_table.py --R 50 --endless --out assets/resources/config/unlock_table.json
"""
import argparse
import json
import math
import sys
from pathlib import Path

STEPS = {'common': 1, 'rare': 4, 'epic': 10, 'legendary': 20}
FIRST = 2  # legacy-2r only
PRICE_PROFILES = ('ordinary-levels', 'legacy-2r')
from product_contract import PRICE_LEVEL_TARGETS, SKIN_POLICY, SKIN_POLICY_LEGACY, ECONOMY_POLICIES, skin_tiers_B
DEFAULT_TIER_LEVELS = dict(PRICE_LEVEL_TARGETS)

def tier_levels(value=None, policy=None):
    """Tier targets in ordinary levels; value None -> the policy's tiers (default normal-5-80.v1: 5/10/20/40/80)."""
    if value is None:return skin_tiers_B(policy or SKIN_POLICY)
    if isinstance(value,str):
        parts=value.split(',');value=dict(zip(('common','rare','epic','legendary','limited'),map(float,parts))) if len(parts) in (4,5) else {}
    if not isinstance(value,dict) or set(value) not in (set(STEPS),set(DEFAULT_TIER_LEVELS)):
        raise ValueError('tier-levels needs common,rare,epic,legendary[,limited]')
    result={k:float(v) for k,v in value.items()}
    if 'limited' not in result:result['limited']=max(50.,result['legendary']+10.) if policy==SKIN_POLICY_LEGACY else 2.*result['legendary']
    values=[result[k] for k in DEFAULT_TIER_LEVELS]
    if any(not math.isfinite(v) or v<=0 for v in values) or any(a>=b for a,b in zip(values,values[1:])):raise ValueError('tier-levels must be positive and strictly increasing')
    return result
SKIN_TIERS = [('common', 7), ('rare', 6), ('epic', 3), ('legendary', 2)]
BG_TIERS = [('common', 3), ('rare', 3), ('epic', 2), ('legendary', 1)]
SKIN_BONUS = {'common': [5, 6, 7, 8, 8, 9, 10], 'rare': [12, 13, 15, 16, 18, 20], 'epic': [24, 27, 30], 'legendary': [38, 45]}
BG_BONUS = {'common': [2, 3, 5], 'rare': [6, 8, 10], 'epic': [12, 15], 'legendary': [20]}
LIMITED_BONUS = 55
# R4O2 (补查2 第 7 组, SLS35): each skin shows its OWN preview picture; the store/trial template binds only this field
PREVIEW_TODO = 'TODO: own preview picture of %s (e.g. skins/<id>_preview.png); never a slot/frame/tile background, never a tint'
LIMITED_ADS = 6
ART = {'common': 'TODO: one accessory (hat, glasses, scarf)', 'rare': 'TODO: new colours + an accessory',
       'epic': 'TODO: a full outfit', 'legendary': 'TODO: a full costume with a glow/effect',
       'limited': 'TODO: the most detailed of all: full themed costume, accessories, aura, its own idle animation'}


def curve(R, tiers, price_profile='ordinary-levels', normal_level_coins=None, targets=None):
    if price_profile not in PRICE_PROFILES:
        raise ValueError('unknown price_profile: ' + str(price_profile))
    targets = tier_levels(targets)
    base = R if normal_level_coins is None else normal_level_coins
    if not math.isfinite(base) or base <= 0:
        raise ValueError('normal-level-coins must be positive')
    rows, price = [], None
    for rarity, count in tiers:
        for _ in range(count):
            price = (max(1, math.floor(base * targets[rarity] + 0.5)) if price_profile == 'ordinary-levels'
                     else FIRST * R if price is None else price + STEPS[rarity] * R)
            rows.append((rarity, int(price)))
    return rows


from product_contract import limited_levels, GIFT_COOLDOWN_MS, b_coins


def b_number(text):
    """--R / --normal-level-coins: a positive number; whole values stay int (same table bytes as before), others like 72.5
    are kept as a fractional B (Saul 2026-10-31: B need not be whole; prices are k*B rounded half up)."""
    value = float(text)
    if not math.isfinite(value):
        raise argparse.ArgumentTypeError('B must be a finite number')
    return int(value) if value == int(value) else value


def make(R, mode, final_level, backgrounds, hero, limited_mode='final', price_profile='ordinary-levels', normal_level_coins=None, targets=None,
         economy_policy=SKIN_POLICY):
    """economy_policy: normal-5-80.v1 (new tables) or normal-10-50.v1 (rebuild a frozen old table, same bytes as v7.8)."""
    if economy_policy not in ECONOMY_POLICIES:raise ValueError('economy policy must be one of '+', '.join(ECONOMY_POLICIES))
    items = []
    policy = economy_policy if price_profile=='ordinary-levels' else SKIN_POLICY_LEGACY  # legacy-2r keeps its saved metadata
    targets = tier_levels(targets, policy)
    want = skin_tiers_B(policy)
    if price_profile=='ordinary-levels' and targets!=want:raise ValueError('%s requires %s ordinary levels; existing custom tables retain their saved contract' % (policy, ','.join(str(v) for v in want.values())))
    normal_level_coins = R if normal_level_coins is None else normal_level_coins
    # R4N1: an English game keeps its original level count (SLS35: 6); with fewer than 10 levels the limited skin goes
    # on the last level (the remake CLI path still refuses fewer than 60 levels before getting here)
    chapter = 10 if final_level >= 10 else max(1, final_level)
    skins = curve(R, SKIN_TIERS, price_profile, normal_level_coins, targets)
    top = max(p for _, p in skins)

    def limited_skin(sid, order):
        return {'id': sid, 'group': 'skin', 'order': order, 'rarity': 'limited', 'limited': True,
                'name': 'TODO', 'art': ART['limited'], 'bonus': {'type': 'coins', 'pct': LIMITED_BONUS}}
    if mode == 'levels' and limited_mode == 'every_10':
        for i, n in enumerate(limited_levels(chapter, final_level)):
            row = limited_skin('%s_limited_%d' % (hero, n), i + 1)
            row.update(unlock='level', level=n, condition='clear', ads=0, coins=0)
            items.append(row)
    else:
        row = limited_skin(hero + '_limited', 1)
        if mode == 'levels':
            row.update(unlock='level', level=limited_levels(chapter, final_level)[-1], condition='clear', ads=0, coins=0)
        else:
            row.update(unlock='ads_coins', ads=LIMITED_ADS, coins=int(math.ceil(1.5 * top / 100.0) * 100))
        items.append(row)
    if price_profile=='ordinary-levels':
        for row in items:
            if 'level' in row:row['award_level']=row['level']
            row.pop('level',None);row.pop('condition',None)
            row.update(unlock='coins',coins=b_coins(targets['limited'],normal_level_coins),ads=0)  # k*B rounded half up (B may be 72.5)
    first = len(items)
    items.append({'id': hero + '_01', 'group': 'skin', 'order': first + 1, 'rarity': 'common', 'unlock': 'free', 'ads': 0, 'coins': 0,
                  'name': 'TODO (the starting look)', 'art': 'the original protagonist'})
    seen = {}
    for i, (rarity, price) in enumerate(skins):
        k = seen.get(rarity, 0)
        seen[rarity] = k + 1
        items.append({'id': '%s_%02d' % (hero, i + 2), 'group': 'skin', 'order': first + i + 2, 'rarity': rarity, 'unlock': 'coins',
                      'ads': 0, 'coins': price, 'bonus': {'type': 'coins', 'pct': SKIN_BONUS[rarity][k]}, 'name': 'TODO', 'art': ART[rarity]})
    if backgrounds:
        items.append({'id': 'bg_01', 'group': 'background', 'order': 1, 'rarity': 'common', 'unlock': 'free', 'ads': 0, 'coins': 0,
                      'name': 'TODO (the original scene)', 'art': 'the original background'})
        seen = {}
        for i, (rarity, price) in enumerate(curve(R, BG_TIERS, price_profile, normal_level_coins, targets)):
            k = seen.get(rarity, 0)
            seen[rarity] = k + 1
            items.append({'id': 'bg_%02d' % (i + 2), 'group': 'background', 'order': i + 2, 'rarity': rarity, 'unlock': 'coins',
                          'ads': 0, 'coins': price, 'bonus': {'type': 'coins', 'pct': BG_BONUS[rarity][k]}, 'name': 'TODO',
                          'art': 'TODO: the scene in a new theme (calm, few details: remake-art/references/page-richness.md)'})
    if economy_policy == SKIN_POLICY and price_profile == 'ordinary-levels':   # R4O2; frozen tables keep their bytes
        for row in items:
            row['previewFrame'] = PREVIEW_TODO % row['id']
    coin_ad = 5*normal_level_coins if type(normal_level_coins) is int else b_coins(5, normal_level_coins)  # 5B, whole coins
    t = {'module': 'skin.v1', 'coins_per_ad': (coin_ad if price_profile=='ordinary-levels' else R), 'coins_per_level': normal_level_coins, 'normal_level_coins': normal_level_coins,
         'price_profile': price_profile, 'price_level_targets': targets, 'price_steps': [1, 4, 10, 20], 'mode': mode, 'items': items}
    if mode == 'levels':
        t['limited_mode'] = limited_mode
    if price_profile=='ordinary-levels':t.update(economy_policy=policy,gift_multiplier=5,gift_cooldown_ms=GIFT_COOLDOWN_MS)
    return t


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--R', type=b_number, required=True, help='ordinary base B for new pricing (may be fractional, e.g. 72.5); legacy-2r ad unit for old contracts')
    ap.add_argument('--price-profile', choices=PRICE_PROFILES, default='ordinary-levels')
    ap.add_argument('--normal-level-coins', type=b_number, help='ordinary level base income, excluding ads/bonuses (default R; may be fractional)')
    ap.add_argument('--economy-policy', choices=ECONOMY_POLICIES, default=SKIN_POLICY,
                    help='normal-5-80.v1 (default, new tables: 5/10/20/40/80B); normal-10-50.v1 only to rebuild a frozen old table')
    ap.add_argument('--tier-levels', help='ordinary-level targets: common,rare,epic,legendary,limited (default: the policy tiers)')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--levels', action='store_true', help='level game: top-tier limited purchase (80B; 50B frozen), optional last-milestone award')
    g.add_argument('--endless', action='store_true', help='endless game: limited purchase is the top tier (80B; 50B frozen); legacy-2r retains the old route')
    ap.add_argument('--final-level', type=int, default=60, help='total levels, including any incomplete tail (重塑 60 or more, 英化 70 or more)')
    ap.add_argument('--limited-mode', choices=['final', 'every_10'], default='final',
                    help='final: one limited skin on the last limited level; every_10: one per limited level (user 2026-10-24)')
    ap.add_argument('--no-backgrounds', action='store_true', help='the game has no scene to dress (no background skins)')
    ap.add_argument('--hero', default='hero', help='id prefix of the protagonist skins')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--project', type=Path, help='R4N1: game folder; board from feature_policy.board_of, real level count '
                    'from docs/game_capabilities.json level_count (English games keep the original level count)')
    ap.add_argument('--board', choices=['localize', 'remake'], help='R4N1: override the recorded board')
    a = ap.parse_args(argv)
    if a.R <= 0:
        ap.error('--R must be > 0')
    import feature_policy  # same folder
    board = feature_policy.board_of(a.project, a.board)[0] if a.project else a.board
    rule, why = feature_policy.rule_verdict('skin_min_levels', board, a.project)
    if a.levels and rule == 'not_applicable':
        real, src = feature_policy.game_levels(a.project)
        if real is not None and '--final-level' not in (argv if argv is not None else sys.argv[1:]):
            a.final_level = real
        print('skin_min_levels 不适用: %s; --final-level %d (%s)' % (why, a.final_level, src), file=sys.stderr)
        if a.final_level < 1:
            ap.error('--final-level must be >= 1')
    elif a.levels and a.final_level < 60:
        ap.error('--final-level %d: a level game has 60 levels or more (英化 70, 重塑 60; Saul 2026-10-29). %s; an English '
                 'game keeping its original levels: --project <game> with board localize' % (a.final_level, why))
    try:
        policy = a.economy_policy if a.price_profile == 'ordinary-levels' else SKIN_POLICY_LEGACY  # legacy-2r keeps its old metadata
        tiers = a.tier_levels if a.tier_levels is not None else ','.join(str(v) for v in skin_tiers_B(policy).values())
        t = make(a.R, 'levels' if a.levels else 'endless', a.final_level, not a.no_backgrounds, a.hero, a.limited_mode,
                 a.price_profile, a.normal_level_coins, tier_levels(tiers, policy), a.economy_policy)
    except ValueError as exc:
        ap.error(str(exc))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(t, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    prices = [r['coins'] for r in t['items'] if r['group'] == 'skin' and r['unlock'] == 'coins']
    print(json.dumps({'out': str(a.out), 'skins': sum(r['group'] == 'skin' for r in t['items']),
                      'backgrounds': sum(r['group'] == 'background' for r in t['items']), 'skin_prices': prices}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
