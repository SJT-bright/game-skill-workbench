#!/usr/bin/env python3
"""Write every economy number of a new game from B in one go (remake-economy economy-rules.md; 货币补丁 v3, W2).

Input: B (one ordinary level's base coins; may be fractional, e.g. 72.5) and the systems this game has.
Output, in --out-dir:
  economy_config.json   - whole numbers the game reads (schema economy_config.v1)
  economy_snapshot.json - the same numbers as economy_snapshot.v1 (meta.source = hand, every row origin = new), ready for
                          product_contract.py economy-audit --snapshot economy_snapshot.json

Every number comes from the rules table read at run time (default ../../remake-economy/references/economy_rules_table.json,
override with --rules); the upgrade line comes from product_contract.upgrade_costs(B). Nothing is written twice here.
Every k x B is rounded half up to a whole number, 'at most' amounts too (rules table B.rounding, lead 2026-11-01).
Numbers that have a range (item price 3B..5B, wheel coin cell 1B..3B, pack discount <= 10%, achievement tiers 3..7) take
the table's default and may be changed inside the range; anything outside the range is refused and no file is written.
A game with skins but no --skin-table gets one placeholder skin row (lowest ECON-TIER tier) so the main currency has a
sink; the real rows come from make_skin_table.py / ad-unlock (see unknowns in the snapshot). Skin prices and the ad-unlock table are not made here: the config lists the make_skin_table.py and
product_contract.py ad-unlock commands to run; the skin trial popup schedule (ECON-SKINTRIAL) is made here.

Usage:
  python3 make_economy_config.py --B 10 --systems items,item_pack,wheel,checkin,quests,chest,float_gift,bonus_level,
      ad_coin,shop_free,home_gift,shortcut,revisit,skins --item-ids hint,bomb --out-dir docs/economy
  python3 make_economy_config.py --B 72.5 --mode endless --no-items --no-gift-skins --systems checkin,home_gift,shortcut,revisit,skins ...
"""
import argparse
import json
import math
import sys
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import product_contract as pc  # noqa: E402
import economy_capabilities as caps  # noqa: E402  (P17, 2026-11-04)

SCHEMA = 'economy_config.v1'
TOOL = 'make_economy_config.py'
DEFAULT_RULES = HERE.parent.parent / 'remake-economy' / 'references' / 'economy_rules_table.json'
# CLI system name -> snapshot.systems key
SYSTEMS = {'items': 'items', 'item_pack': 'items', 'ad_item': 'ad_item', 'wheel': 'wheel', 'offline': 'offline',
           'upgrade': 'upgrade', 'checkin': 'checkin', 'quests': 'quests', 'energy': 'energy', 'chest': 'chest',
           'float_gift': 'float_gift', 'bonus_level': 'bonus_level', 'ad_coin': 'ad_coin', 'shop_free': 'shop_free',
           'home_gift': 'gift_home', 'shortcut': 'shortcut', 'revisit': 'revisit', 'skins': 'skins', 'skin_trial': 'skins',
           'timer_chest': 'timer_chest', 'online_gift': 'online_gift', 'key_chest': 'key_chest'}
# ad-boost board defaults the rules table only bounds (ad-boost v1.2.4 controllers): online-ladder tier shares run evenly from
# ECON-ONLINE per_tier_min_B to per_tier_max_B; key-chest nine cells (KeyChestController DEFAULT_CELLS_B, 15B, a cell <= 5B).
KEY_CHEST_CELLS_B = ('5', '3', '2', '1', '1', '1', '1', '0.5', '0.5')
MUST_HAVE = ('checkin', 'shortcut', 'revisit')  # remake games (economy-rules.md; Saul 2026-10-27 / 10-29)


class Refused(Exception):
    pass


def load_rules(path):
    table = json.loads(Path(path).read_text(encoding='utf-8'))
    if table.get('schema') != 'economy_rules.v1':
        raise Refused('%s is not economy_rules.v1' % path)
    return table, {r['id']: r.get('params', {}) for r in table['rules']}


class Money:
    """k x B as whole numbers, exact decimal arithmetic so the same input always gives the same bytes."""

    def __init__(self, B):
        self.B = Decimal(repr(B))

    @staticmethod
    def _d(k):
        return k if isinstance(k, Decimal) else Decimal(repr(k))

    def exact(self, k):  # k x B rounded half up (rules table B.rounding), 'at most' amounts too
        return int((self.B * self._d(k)).quantize(Decimal(1), rounding=ROUND_HALF_UP))

    def at_most(self, k):  # 'at most kB': same half-up rounding, never below 1
        return max(1, self.exact(k))


def x2_box(rules):
    p = rules['ECON-CLAIMX2']
    return {'checkbox': True, 'default_checked': p['default_checked'], 'multiplier': p['multiplier']}


def parse_list(text, conv=str):
    return [conv(x.strip()) for x in (text or '').split(',') if x.strip()]


def in_range(name, value, lo, hi):
    if not (lo - 1e-9 <= value <= hi + 1e-9):
        raise Refused('%s = %s is outside the rule range %s..%s' % (name, value, lo, hi))


def parse_systems(a):
    have, errors = set(), []
    for s in parse_list(a.systems):
        s = s.replace('-', '_')
        if s not in SYSTEMS:
            errors.append('unknown system %r; known: %s' % (s, ', '.join(SYSTEMS)))
        have.add(s)
    return have, errors


def capabilities(a, table):
    """P17 (2026-11-04): what the game HAS, written before any number (economy_capabilities.v1)."""
    have, _ = parse_systems(a)
    wallet = not a.no_wallet
    ev = {'wallet': '--no-wallet on the command line' if a.no_wallet else '--B %s / --currency %s' % (a.B, a.currency),
          'items': '--systems items/item_pack/ad_item' if have & {'items', 'item_pack', 'ad_item'} else
          ('--no-items' if a.no_items else 'no item system in --systems'),
          'skins': '--systems skins' if have & {'skins', 'skin_trial'} else 'no skins in --systems',
          'energy': '--systems energy' if 'energy' in have else 'no energy in --systems'}
    return caps.make(wallet, bool(have & {'items', 'item_pack', 'ad_item'}), bool(have & {'skins', 'skin_trial'}),
                     'energy' in have, kind=a.kind, wallet_currency=a.currency if wallet else None, evidence=ev,
                     rules_revision=table['revision'], written_by=TOOL)


# Systems that pay or price in the main coin: a game without a wallet cannot have them (they need B).
NO_WALLET_OK = {'items', 'ad_item', 'energy', 'shortcut', 'revisit'}


def build_no_wallet(a, table, rules, cap):
    """No out-of-round wallet: no B, so nothing is k x B. The B-based rewards get the rules-table replacements
    (ECON-NOCUR result x2, ECON-SHORTCUT / ECON-REVISIT no-coin params); see economy_capabilities.no_wallet_substitutes."""
    have, errors = parse_systems(a)
    if a.B is not None:
        errors.append('--no-wallet: there is no B (energy and score are not coins); drop --B')
    coin = sorted(have - NO_WALLET_OK)
    if coin:
        errors.append('--no-wallet: %s pay or price in coins and need a wallet (Saul 2026-11-04: with no coin and no energy, '
                      'add a coin and skins while localizing, then rerun with --B)' % ', '.join(coin))
    if errors:
        raise Refused('\n'.join(errors))
    sub = caps.no_wallet_substitutes(cap, rules)
    cfg = {'schema': SCHEMA, 'generated_by': TOOL, 'rules_revision': table['revision'], 'B': None, 'mode': a.mode,
           'currency': None, 'wallet': False, 'no_wallet': sub,
           'result_x2': dict(sub['result_x2'], note='no coin: never doubles the score (ECON-X2 v3.4 note)')}
    inflows, currencies = [], []
    if cap['energy']:
        currencies.append({'id': 'energy', 'label': 'Energy', 'role': 'energy', 'evidence': 'economy_config.json#/energy',
                           'origin': 'new'})
        p = rules['ECON-ENERGY']
        cfg['energy'] = {'ad_refill': p['ad_refill'], 'skip_if_no_room': p['skip_if_no_room']}
        inflows.append({'id': 'energy_ad', 'rule': 'ECON-ENERGY', 'origin': 'new', 'currency': 'energy', 'amount': p['ad_refill'],
                        'per': 'ad', 'needs_ad': True, 'x2': 'none', 'window': 'energy_ad',
                        'evidence': 'economy_config.json#/energy/ad_refill'})
    for s in ('shortcut', 'revisit'):
        if s not in have:
            continue
        cfg[s] = sub[s]
        if 'amount' in sub[s]:
            inflows.append({'id': s, 'rule': sub[s]['rule'], 'origin': 'new', 'currency': sub[s]['currency'],
                            'amount': sub[s]['amount'], 'per': 'once', 'needs_ad': False, 'x2': 'none',
                            'evidence': 'economy_config.json#/%s/amount' % s})
    if 'ad_item' in have:
        cfg['ad_item'] = {'per_ad': rules['ECON-ADITEM']['per_ad']}
    systems = {k: False for k in ('shop', 'skins', 'items', 'checkin', 'wheel', 'gift_home', 'shortcut', 'revisit', 'energy',
                                  'ad_coin', 'ad_item')}
    for s in have:
        systems[SYSTEMS[s]] = True
    systems['items'] = cap['items']
    systems['result_x2'] = cap['items']   # ECON-NOCUR: x2 only when there are items to pick up this round
    snap = {'schema': pc.ECON_SNAPSHOT_SCHEMA,
            'game': {'name': a.name, 'kind': a.kind, 'mode': a.mode, 'economy_policy': rules['ECON-TIER']['policy']},
            'meta': {'source': 'hand', 'tool': TOOL, 'generated_by': TOOL},
            'B': {'value': None, 'how': 'no_wallet', 'evidence': 'economy_capabilities.json#/wallet'},
            'currencies': currencies, 'inflows': inflows, 'sinks': [], 'systems': systems, 'configs': {},
            'unknowns': []}
    warnings = []
    if not cap['energy']:
        warnings.append('no coin and no energy: add a coin currency and skins to spend it on (English: while localizing), '
                        'then rerun with --B (Saul 2026-11-04; capabilities wallet_plan add_main_currency_and_skins)')
    return cfg, snap, warnings


def build(a, table, rules):
    errors = []
    if a.B is None:
        raise Refused('--B is required (a game without an out-of-round coin wallet: use --no-wallet instead)')
    if not pc._num(a.B) or a.B <= 0:
        raise Refused('B must be a positive number')
    have = set()
    for s in parse_list(a.systems):
        s = s.replace('-', '_')
        if s not in SYSTEMS:
            errors.append('unknown system %r; known: %s' % (s, ', '.join(SYSTEMS)))
        have.add(s)
    has_skins = bool(have & {'skins', 'skin_trial'})
    has_items = bool(have & {'items', 'item_pack', 'ad_item'})
    if a.no_items and has_items:
        errors.append('--no-items conflicts with items / item_pack / ad_item in --systems')
    if 'bonus_level' in have and a.mode != 'levels':
        errors.append('bonus_level needs --mode levels (an endless or idle game has no levels to add a bonus level to)')
    if 'offline' in have and a.mode != 'idle':
        errors.append('offline income only for games with per-second output (--mode idle; ECON-OFFLINE note)')
    window_rule = getattr(a, 'window_rule', 'block')   # R4N1: feature_policy econ_window_levels, set in main()
    if a.mode == 'levels' and a.total_levels < 1:
        errors.append('--total-levels must be at least 1')
    elif window_rule != 'not_applicable' and a.total_levels < rules['ECON-LEVEL10']['window_levels']:
        errors.append('--total-levels must be at least %d (%s)' % (rules['ECON-LEVEL10']['window_levels'],
                      getattr(a, 'window_why', 'new game')))
    if errors:
        raise Refused('\n'.join(errors))
    items = parse_list(a.item_ids) or ['booster'] if has_items else []
    if len(set(items)) != len(items):
        raise Refused('--item-ids has duplicates')
    m, B = Money(a.B), a.B
    box = x2_box(rules)
    cfg = {'schema': SCHEMA, 'generated_by': TOOL, 'rules_revision': table['revision'], 'B': a.B,
           'B_rounding': table['B']['rounding'],
           'mode': a.mode, 'currency': a.currency}
    inflows, sinks, configs, unknowns = [], [], {}, []
    systems = {k: False for k in ('shop', 'skins', 'items', 'checkin', 'wheel', 'gift_home', 'gift_window', 'offline', 'upgrade',
                                  'quests', 'energy', 'shortcut', 'revisit', 'chest', 'float_gift', 'bonus_level', 'shop_free',
                                  'ad_coin', 'ad_item', 'timer_chest', 'online_gift', 'key_chest')}
    for s in have:
        systems[SYSTEMS[s]] = True
    systems['result_x2'] = True
    systems['shop'] = bool(has_items or has_skins or 'shop_free' in have or 'upgrade' in have)
    cur = a.currency

    def row(id_, rule, amount, ptr, **kw):
        r = {'id': id_, 'rule': rule, 'origin': 'new', 'currency': kw.pop('currency', cur), 'amount': amount}
        r.update(kw)
        r['evidence'] = 'economy_config.json#/' + ptr
        inflows.append(r)

    # ordinary levels (ECON-LEVEL10) and result x2 (ECON-X2): every game
    lv = rules['ECON-LEVEL10']
    if a.mode == 'levels':
        k = Decimal(lv['sum_B']) / Decimal(lv['window_levels'])
        cum = [m.exact(k * i) for i in range(a.total_levels + 1)]
        per = [cum[i + 1] - cum[i] for i in range(a.total_levels)]
        cfg['level_reward'] = {'per_level': per, 'every_10_levels': m.exact(lv['sum_B'])}
        if a.total_levels < lv['window_levels']:   # R4N1: English game shorter than the window -> window = real levels
            cfg['level_reward']['window_levels'] = a.total_levels
        row('level_clear', 'ECON-LEVEL10', per[0], 'level_reward/per_level', amounts=per, per='level', needs_ad=False, x2='ad_button')
    x2 = rules['ECON-X2']
    cfg['result_x2'] = {'multiplier': x2['multiplier'], 'pay': x2['pay'],
                        'note': 'one round result: a WATCH AD x2 button and a free Claim line (ECON-X2), not a checkbox'}

    # items, packs, item ads (ECON-ITEM / ECON-PACK / ECON-ADITEM)
    if has_items:
        ip = rules['ECON-ITEM']
        prices = dict.fromkeys(items, a.item_price_B if a.item_price_B is not None else ip['default_B'])
        for spec in parse_list(a.item_prices_B):
            iid, _, v = spec.partition('=')
            if iid not in prices:
                raise Refused('--item-prices-B names %r, not in --item-ids' % iid)
            prices[iid] = float(v)
        cfg['items'] = []
        for n, iid in enumerate(items):
            in_range('price of %s (B)' % iid, prices[iid], ip['min_B'], ip['max_B'])
            price = m.exact(prices[iid])
            entry = {'id': iid, 'price': price}
            sinks.append({'id': iid + '_1', 'rule': 'ECON-ITEM', 'origin': 'new', 'kind': 'item', 'item': iid, 'currency': cur,
                          'price': price, 'pack_size': 1, 'evidence': 'economy_config.json#/items/%d/price' % n})
            if 'item_pack' in have:
                pk = rules['ECON-PACK']
                d = pk['max_discount'] if a.pack_discount is None else a.pack_discount
                in_range('--pack-discount', d, 0, pk['max_discount'])
                if a.pack_size < 2:
                    raise Refused('--pack-size must be at least 2')
                full = Decimal(price * a.pack_size)
                pprice = int((full * (1 - Decimal(repr(d)))).quantize(Decimal(1), rounding=ROUND_HALF_UP))
                while 1 - Decimal(pprice) / full > Decimal(repr(pk['max_discount'])):  # rounding must not pass the cap
                    pprice += 1
                entry['pack'] = {'size': a.pack_size, 'price': pprice}
                sinks.append({'id': '%s_%d' % (iid, a.pack_size), 'rule': 'ECON-PACK', 'origin': 'new', 'kind': 'item', 'item': iid,
                              'currency': cur, 'price': pprice, 'pack_size': a.pack_size,
                              'evidence': 'economy_config.json#/items/%d/pack' % n})
            if 'ad_item' in have:
                entry['ad_gives'] = rules['ECON-ADITEM']['per_ad']
                row(iid + '_ad', 'ECON-ADITEM', entry['ad_gives'], 'items/%d/ad_gives' % n, currency=iid, per='ad', needs_ad=True,
                    x2='none', window='ad_item')
            cfg['items'].append(entry)

    # home gift, add-to-desktop, home revisit (ECON-GIFT / ECON-SHORTCUT / ECON-REVISIT)
    if 'home_gift' in have:
        g = rules['ECON-GIFT']
        cfg['home_gift'] = {'amount': m.exact(g['reward_B']), 'cooldown_ms': g['cooldown_ms'], 'double_checkbox': g['claim_double_checkbox']}
        row('gift_home', 'ECON-GIFT', cfg['home_gift']['amount'], 'home_gift/amount', per='ad', needs_ad=True, x2='none',
            cooldown_ms=g['cooldown_ms'], window='home_gift')
    for s, rule in (('shortcut', 'ECON-SHORTCUT'), ('revisit', 'ECON-REVISIT')):
        if s in have:
            p = rules[rule]
            cfg[s] = {'amount': m.exact(p['reward_B']), 'times': p['times']}
            row(s, rule, cfg[s]['amount'], s + '/amount', per='once', needs_ad=False, x2='none')

    # watch-ad coins (ECON-ADCOIN), shop free claim (ECON-SHOPFREE): already ad rewards, never doubled
    if 'ad_coin' in have:
        p = rules['ECON-ADCOIN']
        cfg['ad_coin'] = {'amount': m.exact(p['reward_B']), 'per_day': p['per_day'], 'cooldown_sec': p['cooldown_sec']}
        row('ad_coin', 'ECON-ADCOIN', cfg['ad_coin']['amount'], 'ad_coin/amount', per='ad', needs_ad=True, x2='none',
            count_per_day=p['per_day'], window='ad_coin')
    if 'shop_free' in have:
        p = rules['ECON-SHOPFREE']
        slots = [{'id': 'free_' + iid, 'gives': iid, 'amount': p['item_per_claim'], 'per_day': p['per_slot_per_day']} for iid in items]
        slots.append({'id': 'free_coins', 'gives': cur, 'amount': m.exact(p['coins_B_per_claim']), 'per_day': p['per_slot_per_day']})
        cfg['shop_free'] = {'slots': slots, 'separate_from_ad_coin': p['separate_from_ad_coin']}
        for n, sl in enumerate(slots):
            row(sl['id'], 'ECON-SHOPFREE', sl['amount'], 'shop_free/slots/%d/amount' % n, currency=sl['gives'], per='ad',
                needs_ad=True, x2='none', count_per_day=sl['per_day'], window='shop_free')

    # seven-day check-in (ECON-CHECKIN), checkin_config.v1 shape so it can be saved as checkin-config.json as is
    if 'checkin' in have:
        p = rules['ECON-CHECKIN']
        coins_B = {int(d): k for d, k in p['coins_B_by_day'].items()}
        item_amount = {int(d): n for d, n in p['item_amount_by_day'].items()}
        gift_skin = has_skins and not a.no_gift_skins
        day_rows = {}
        for d in range(1, 8):
            rewards, coin_B = [], coins_B.get(d, 0)
            if str(d) in p['no_item_fallback_B']:
                if items:
                    rewards.append({'type': 'item', 'id': items[(d // 2 - 1) % len(items)], 'amount': item_amount[d]})
                else:
                    coin_B += p['no_item_fallback_B'][str(d)]
            if str(d) in p['skin_fallback_B']:
                if gift_skin:
                    rewards.append({'type': 'skin', 'id': 'TODO_common_or_rare_coin_skin_%d' % (d - 5),
                                    'fallback_coins': m.exact(p['skin_fallback_B'][str(d)])})
                else:
                    coin_B += p['skin_fallback_B'][str(d)]
            if d == 7 and items:
                rewards.append({'type': 'item', 'id': items[-1], 'amount': item_amount[d]})
            if coin_B:
                rewards.insert(0, {'type': 'coins', 'amount': m.exact(coin_B)})
            day_rows[d] = rewards
        cfg['checkin'] = {'schema': 'checkin_config.v1', 'title': 'Daily Reward', 'mode': 'cumulative', 'reset_hour': 0, 'R': a.B,
                          'double': box,
                          'days': [dict({'day': d}, **({'big': True} if d == 7 else {}), rewards=r) for d, r in day_rows.items()]}
        for d, r in day_rows.items():
            coins = sum(x['amount'] for x in r if x['type'] == 'coins')
            row('checkin_d%d' % d, 'ECON-CHECKIN', coins, 'checkin/days/%d/rewards' % (d - 1), day=d, per='claim', needs_ad=False,
                x2='checkbox_default_on', count_per_day=1, window='checkin')

    # wheel (ECON-WHEEL): 1 free + 2 ad a day, coin cells 1B..3B, cell <= 5B, one spin <= 2B on average
    if 'wheel' in have:
        p = rules['ECON-WHEEL']
        lo, hi = p['cell_coins_B_range']
        cells_B = parse_list(a.wheel_cells_B, float) if a.wheel_cells_B else list(p['default_cells_B'])
        weights = parse_list(a.wheel_weights, float) if a.wheel_weights else [1] * (len(cells_B) + min(2, len(items)))
        if len(weights) != len(cells_B) + min(2, len(items)):
            raise Refused('--wheel-weights needs %d numbers (coin cells, then up to 2 item cells)' % (len(cells_B) + min(2, len(items))))
        if any(w <= 0 for w in weights):
            raise Refused('--wheel-weights must be positive')
        for k in cells_B:
            in_range('wheel coin cell (B)', k, lo, min(hi, p['max_cell_B']))
        exp_B = sum(k * w for k, w in zip(cells_B, weights)) / sum(weights)
        if exp_B > p['expected_per_spin_B_max'] + 1e-9:
            raise Refused('one spin is worth %.2fB on average; at most %sB' % (exp_B, p['expected_per_spin_B_max']))
        cells = [{'type': 'coins', 'amount': m.exact(k), 'weight': w} for k, w in zip(cells_B, weights)]
        cells += [{'type': 'item', 'id': iid, 'amount': 1, 'weight': w} for iid, w in zip(items[:2], weights[len(cells_B):])]
        cfg['wheel'] = {'free_per_day': p['free_per_day'], 'ad_per_day': p['ad_per_day'], 'cells': cells, 'result_double': box}
        configs['wheel'] = {'free_per_day': p['free_per_day'], 'ad_per_day': p['ad_per_day'],
                            'cells': [{'amount': c['amount'] if c['type'] == 'coins' else 0, 'weight': c['weight']} for c in cells],
                            'result_double': {'enabled': True, 'default_checked': box['default_checked']}}
        for n, c in enumerate(cells):
            row('wheel_%d' % (n + 1), 'ECON-WHEEL', c['amount'], 'wheel/cells/%d' % n, currency=cur if c['type'] == 'coins' else c['id'],
                weight=c['weight'], per='spin', needs_ad=False, x2='checkbox_default_on', window='wheel_result',
                count_per_day=p['free_per_day'] + p['ad_per_day'])

    # every-5-levels chest (ECON-CHEST), floating gift (ECON-FLOAT), bonus level (ECON-BONUS)
    if 'chest' in have:
        p = rules['ECON-CHEST']
        free = m.at_most(p['free_max_B'])
        cfg['chest'] = {'every_levels': p['every_levels'], 'amount': free, 'double': box}
        row('chest', 'ECON-CHEST', free, 'chest/amount', per='claim', needs_ad=False, x2='checkbox_default_on',
            every_levels=p['every_levels'], window='chest')
    if 'float_gift' in have:
        p = rules['ECON-FLOAT']
        cfg['float_gift'] = {'amount': m.at_most(p['each_max_B']), 'per_round_max': p['per_round_max'], 'double': box}
        row('float_gift', 'ECON-FLOAT', cfg['float_gift']['amount'], 'float_gift/amount', per='claim', needs_ad=False,
            x2='checkbox_default_on', per_round_max=p['per_round_max'], window='float_gift')
    if 'bonus_level' in have:
        p = rules['ECON-BONUS']
        cfg['bonus_level'] = {'amount': m.exact(p['reward_B']), 'ad_total': m.exact(p['ad_reward_B']),
                              'note': 'watch-ad button brings the total to ad_total (pay the difference only)'}
        row('bonus_level', 'ECON-BONUS', cfg['bonus_level']['amount'], 'bonus_level/amount', per='level', needs_ad=False,
            x2='ad_button', window='bonus_level')
        row('bonus_level_ad', 'ECON-BONUS', cfg['bonus_level']['ad_total'], 'bonus_level/ad_total', per='level', needs_ad=True,
            x2='ad_button', window='bonus_level')

    # timer chest (ECON-TIMERCHEST), online-time gift (ECON-ONLINE), key chest (ECON-KEYCHEST): ad-boost boards, Saul 2026-11-01
    # 「默认数值就这样」. Every claim window is ECON-CLAIMX2 (default-ticked watch-ad x2).
    if 'timer_chest' in have:
        p = rules['ECON-TIMERCHEST']
        in_range('timer chest free open (B)', float(p['free_open_B']), 0, p['free_open_max_B'])
        if p['ad_cut_sec'] * p['ad_cuts_per_round'] >= p['wait_sec']:
            raise Refused('ECON-TIMERCHEST: ad_cut_sec x ad_cuts_per_round must be below wait_sec (no opening at once by ads)')
        timing = {k: p[k] for k in ('placement', 'wait_sec', 'ad_cut_sec', 'ad_cuts_per_round', 'rounds_per_day')}
        cfg['timer_chest'] = dict(timing, amount=m.exact(p['free_open_B']), double=box)
        row('timer_chest', 'ECON-TIMERCHEST', cfg['timer_chest']['amount'], 'timer_chest/amount', per='claim', needs_ad=False,
            x2='checkbox_default_on', count_per_day=p['rounds_per_day'], window='timer_chest')
        systems['timer_chest'] = timing
    if 'online_gift' in have:
        p = rules['ECON-ONLINE']
        tiers, lo, hi = p['tiers_min'], Decimal(repr(p['per_tier_min_B'])), Decimal(repr(p['per_tier_max_B']))
        step = (hi - lo) / (len(tiers) - 1) if len(tiers) > 1 else Decimal(0)
        # same as the online-ladder controller: floor(B x share), at least 1
        amounts = [max(1, int((m.B * (lo + step * i)).to_integral_value(rounding=ROUND_FLOOR))) for i in range(len(tiers))]
        if sum(amounts) > m.exact(p['day_total_max_B']):
            raise Refused('online-time gift tiers add up to %d, over %sB a day' % (sum(amounts), p['day_total_max_B']))
        cfg['online_gift'] = {'tiers': [{'minutes': t, 'amount': a_} for t, a_ in zip(tiers, amounts)],
                              'day_total_max': m.exact(p['day_total_max_B']), 'foreground_only': p['foreground_only'],
                              'reset': p['reset'], 'double': box}
        for n, (t, a_) in enumerate(zip(tiers, amounts)):
            row('online_%d' % t, 'ECON-ONLINE', a_, 'online_gift/tiers/%d/amount' % n, per='claim', needs_ad=False,
                x2='checkbox_default_on', count_per_day=1, tier_min=t, window='online_gift')
    if 'key_chest' in have:
        p = rules['ECON-KEYCHEST']
        cells = [Decimal(x) for x in KEY_CHEST_CELLS_B]
        if len(cells) != p['cells'] or max(cells) > Decimal(repr(p['cell_max_B'])) or sum(cells) != Decimal(repr(p['total_B'])):
            raise Refused('key chest default cells do not match ECON-KEYCHEST (%d cells, <= %sB, about %sB)'
                          % (p['cells'], p['cell_max_B'], p['total_B']))
        amounts = [m.at_most(c) for c in cells]  # KeyChestController cellCoins: round(min(cell, 5) x B), at least 1
        cfg['key_chest'] = {'cells': amounts, 'double': box, 'note': 'x2 on the summary window after leaving; cells opened with the ad +3 KEYS do not double'}
        for n, a_ in enumerate(amounts):
            row('key_cell_%d' % (n + 1), 'ECON-KEYCHEST', a_, 'key_chest/cells/%d' % n, per='open', needs_ad=False,
                x2='checkbox_default_on', window='key_chest')

    # offline income (ECON-OFFLINE), idle games only
    if 'offline' in have:
        p = rules['ECON-OFFLINE']
        configs['offline'] = {'min_away_sec': p['min_away_sec'], 'cap_sec': p['cap_sec'], 'ad_multiplier': p['ad_multiplier'],
                              'min_payout': p['min_payout']}
        cfg['offline'] = dict(configs['offline'], double=box,
                              note='amount = output per second x seconds away (capped); the game computes it')

    # upgrade lines (ECON-UPGRADE) from product_contract.upgrade_costs(B)
    if 'upgrade' in have:
        p = rules['ECON-UPGRADE']
        if a.mode == 'idle':
            cfg['upgrade'] = {'lines': [], 'note': 'idle/merge game: price = output per second x minutes, capped by offline (ECON-UPGRADE note); not generated'}
        else:
            if a.upgrade_lines < 1:
                raise Refused('--upgrade-lines must be at least 1')
            costs = pc.upgrade_costs(B, levels=p['levels'], first_B=p['first_B'], last_B=p['last_B'])
            cfg['upgrade'] = {'lines': [{'id': 'line_%d' % (i + 1), 'costs': costs} for i in range(a.upgrade_lines)]}
            configs['upgrade_lines'] = [list(costs) for _ in range(a.upgrade_lines)]
            for i in range(a.upgrade_lines):
                for lvl, c in enumerate(costs):
                    sinks.append({'id': 'line_%d_lv%d' % (i + 1, lvl + 1), 'rule': 'ECON-UPGRADE', 'origin': 'new', 'kind': 'upgrade',
                                  'currency': cur, 'price': c, 'line': 'line_%d' % (i + 1), 'level': lvl + 1,
                                  'evidence': 'economy_config.json#/upgrade/lines/%d/costs/%d' % (i, lvl)})

    # daily tasks and achievements (ECON-QUEST)
    if 'quests' in have:
        p = rules['ECON-QUEST']
        tlo, thi = p['achievement_tiers']
        in_range('--achievement-tiers', a.achievement_tiers, tlo, thi)
        if a.achievement_classes < 0:
            raise Refused('--achievement-classes must be 0 or more')
        lo_B, hi_B, n = Decimal(p['achievement_B_min']), Decimal(p['achievement_B_max']), a.achievement_tiers
        tiers = [m.exact(lo_B + (hi_B - lo_B) * i / (n - 1)) for i in range(n)]
        daily = [m.exact(p['daily_task_B'])] * p['daily_tasks']
        cfg['quests'] = {'daily': [{'id': 'daily_%d' % (i + 1), 'amount': x} for i, x in enumerate(daily)],
                         'achievements': [{'id': 'achievement_%d' % (c + 1), 'tiers': tiers} for c in range(a.achievement_classes)],
                         'achievement_gives_skin': p['achievement_gives_skin'], 'double': box}
        configs['quests'] = {'daily': daily, 'achievements': [list(tiers) for _ in range(a.achievement_classes)],
                             'achievement_gives_skin': p['achievement_gives_skin']}
        for i, x in enumerate(daily):
            row('daily_%d' % (i + 1), 'ECON-QUEST', x, 'quests/daily/%d/amount' % i, per='day', needs_ad=False,
                x2='checkbox_default_on', count_per_day=1, window='quest_claim')
        for c in range(a.achievement_classes):
            for t, x in enumerate(tiers):
                row('achievement_%d_t%d' % (c + 1, t + 1), 'ECON-QUEST', x, 'quests/achievements/%d/tiers/%d' % (c, t), per='once',
                    needs_ad=False, x2='checkbox_default_on', window='quest_claim')

    # energy (ECON-ENERGY): only when the original game has energy
    if 'energy' in have:
        p = rules['ECON-ENERGY']
        configs['energy'] = {'original_has_energy': True, 'ad_refill': p['ad_refill'], 'skip_if_no_room': p['skip_if_no_room']}
        cfg['energy'] = {'ad_refill': p['ad_refill'], 'skip_if_no_room': p['skip_if_no_room']}
        row('energy_ad', 'ECON-ENERGY', p['ad_refill'], 'energy/ad_refill', currency='energy', per='ad', needs_ad=True, x2='none',
            window='energy_ad')

    # skins: trial popup schedule here (ECON-SKINTRIAL); prices and ad-unlock by make_skin_table.py + ad-unlock (W1b)
    if has_skins:
        p = rules['ECON-SKINTRIAL']
        trial = {'present': True, 'no_popup_levels': list(p['no_popup_levels']), 'every_levels': p['every_levels'],
                 'endless_every_rounds': p['endless_every_rounds']}
        systems['skin_trial'] = dict(trial, evidence='economy_config.json#/skin_trial')
        cfg['skin_trial'] = dict(trial, schedule=p['schedule'] if a.mode == 'levels' else 'round %% %d == 0' % p['endless_every_rounds'],
                                 limited_not_trialed=p['limited_not_trialed'], skip_when_all_owned=p['skip_when_all_owned'],
                                 trial_view_counts_toward_unlock=p['trial_view_counts_toward_unlock'])
        b_arg = str(int(B)) if float(B).is_integer() else repr(B)
        mode_arg = '--levels --final-level %d --limited-mode final' % a.total_levels if a.mode == 'levels' else '--endless'
        cfg['skins'] = {
            'economy_policy': rules['ECON-TIER']['policy'], 'ad_unlock_policy': rules['ECON-ADUNLOCK']['policy'],
            'not_generated_here': 'prices and the ad-unlock table come from these two commands (run from the game project)',
            'commands': ['python3 <skills>/remake-core/scripts/make_skin_table.py --R %s --normal-level-coins %s %s '
                         '--out assets/resources/config/unlock_table.json' % (b_arg, b_arg, mode_arg),
                         'python3 <skills>/remake-core/scripts/product_contract.py ad-unlock --table assets/resources/config/unlock_table.json '
                         '--out assets/resources/config/ad_unlock_table.json'],
            'then': 'rerun make_economy_config.py with --skin-table / --ad-unlock-table so the snapshot carries the skin rows'}
        if not float(B).is_integer():
            cfg['skins']['warning'] = ('B = %s is fractional; make_skin_table.py --R / --normal-level-coins take whole numbers '
                                       'only (2026-11-01), so the first command fails until it accepts a fractional B' % b_arg)
        if a.skin_table:
            add_skin_sinks(a, sinks, cur)
        else:
            # No skin table yet: one placeholder row at the lowest ECON-TIER tier so the main currency has its sink
            # (ECON-DEAD). One row, not one per tier: a coin-only row per tier would break the 60% ad-unlock share, and
            # choosing which rows unlock by ads belongs to product_contract.py ad-unlock (W1b), not to this script.
            tiers = rules['ECON-TIER']['tiers_B']
            low = min(tiers, key=lambda r: tiers[r])
            sinks.append({'id': 'skin_placeholder', 'rule': 'ECON-TIER', 'origin': 'new', 'kind': 'skin', 'currency': cur,
                          'price': m.exact(tiers[low]), 'pack_size': 1, 'ad_unlock_views': 0, 'rarity': low,
                          'evidence': 'economy_config.json#/skins/commands',
                          'note': 'placeholder until make_skin_table.py writes the skin prices; rerun with --skin-table'})
            unknowns.append('skin prices and ad unlocks: not generated yet (make_skin_table.py + product_contract.py ad-unlock); '
                            'the snapshot carries one placeholder %s skin at %sB; rerun with --skin-table / --ad-unlock-table'
                            % (low, tiers[low]))

    currencies = [{'id': cur, 'label': a.currency_label, 'role': 'main', 'evidence': 'economy_config.json#/currency', 'origin': 'new'}]
    if 'energy' in have:
        currencies.append({'id': 'energy', 'label': 'Energy', 'role': 'energy', 'evidence': 'economy_config.json#/energy', 'origin': 'new'})
    snap = {'schema': pc.ECON_SNAPSHOT_SCHEMA,
            'game': {'name': a.name, 'kind': a.kind, 'mode': a.mode, 'economy_policy': rules['ECON-TIER']['policy']},
            'meta': {'source': 'hand', 'tool': TOOL, 'generated_by': TOOL},
            'B': {'value': B, 'how': 'config_normalLevelCoins', 'evidence': 'economy_config.json#/B'},
            'currencies': currencies, 'inflows': inflows, 'sinks': sinks, 'systems': systems, 'configs': configs, 'unknowns': unknowns}
    warnings = ['%s is missing: remake games must have it (economy-audit will report it)' % s for s in MUST_HAVE
                if s not in have and a.kind == 'remake']
    self_check(cfg, configs, sinks, B)
    return cfg, snap, warnings


def add_skin_sinks(a, sinks, cur):
    """Skin rows for the snapshot, copied from W1b's tables (never priced here)."""
    table = json.loads(Path(a.skin_table).read_text(encoding='utf-8'))
    views = {}
    if a.ad_unlock_table:
        views = {x['id']: x.get('ads_required', 0) for x in json.loads(Path(a.ad_unlock_table).read_text(encoding='utf-8')).get('items', [])}
    for n, it in enumerate(table.get('items', [])):
        if it.get('group') not in ('skin', 'background') or it.get('unlock') == 'free':
            continue
        sinks.append({'id': it['id'], 'rule': 'ECON-ADUNLOCK' if it['id'] in views else 'ECON-TIER', 'origin': 'new',
                      'kind': it['group'], 'currency': cur, 'price': it.get('coins', 0), 'pack_size': 1,
                      'ad_unlock_views': views.get(it['id'], 0), 'rarity': 'limited' if it.get('limited') else it.get('rarity'),
                      'evidence': '%s#/items/%d' % (Path(a.skin_table).name, n)})


def self_check(cfg, configs, sinks, B):
    """Refuse to write anything product_contract's own checks would reject."""
    errs = []
    for s in sinks:
        if s['rule'] == 'ECON-ITEM':
            errs += pc.item_price_errors(s['price'], B)
    unit = {s['item']: s['price'] for s in sinks if s['rule'] == 'ECON-ITEM'}
    for s in sinks:
        if s['rule'] == 'ECON-PACK':
            errs += pc.pack_discount_errors(unit[s['item']], s['price'], s['pack_size'])
    if 'wheel' in configs:
        errs += pc.wheel_config_errors(configs['wheel'], B)
    if 'offline' in configs:
        errs += pc.offline_errors(configs['offline'])
    for line in configs.get('upgrade_lines', []):
        errs += pc.upgrade_errors(line, B)
    if 'quests' in configs:
        q = configs['quests']
        errs += pc.quest_reward_errors(q['daily'], q['achievements'], B, q['achievement_gives_skin'])
    if 'energy' in configs:
        errs += pc.energy_errors(configs['energy'])
    if errs:
        raise Refused('generated numbers fail product_contract checks:\n' + '\n'.join(errs))


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--B', type=float, help='one ordinary level base coins; may be fractional (72.5); required unless --no-wallet')
    ap.add_argument('--no-wallet', action='store_true', help='P17: the game has no out-of-round coin wallet (energy/score are '
                    'not coins): no B; x2 / add-to-desktop / revisit get the rules-table replacements')
    ap.add_argument('--scan-project', type=Path, help='P17: game project to scan for reward numbers written in code '
                    '(coins += 30); found -> exit 1 (files are still written)')
    ap.add_argument('--systems', required=True, help='comma list: ' + ','.join(SYSTEMS))
    ap.add_argument('--out-dir', required=True, type=Path)
    ap.add_argument('--rules', type=Path, default=DEFAULT_RULES, help='economy_rules_table.json (default: %(default)s)')
    ap.add_argument('--mode', choices=['levels', 'endless', 'idle'], default='levels')
    ap.add_argument('--kind', choices=['remake', 'english'], default='remake')
    ap.add_argument('--name', default='new_game')
    ap.add_argument('--currency', default='coins', help='main currency id')
    ap.add_argument('--currency-label', default='Coins')
    ap.add_argument('--total-levels', type=int, default=60, help='levels games: per-level rewards for this many levels')
    ap.add_argument('--no-items', action='store_true', help='the game has no in-game items (check-in day 2/4 pay 1B)')
    ap.add_argument('--no-gift-skins', action='store_true', help='no skin can be given (check-in day 6 = 3B, day 7 = 6B + 5B)')
    ap.add_argument('--item-ids', help='comma list of item ids (default booster)')
    ap.add_argument('--item-price-B', type=float, help='price of every item in B, inside the ECON-ITEM range (default: its default_B)')
    ap.add_argument('--item-prices-B', help='per item, e.g. hint=3,bomb=5 (overrides --item-price-B)')
    ap.add_argument('--pack-size', type=int, default=3)
    ap.add_argument('--pack-discount', type=float, help='0..ECON-PACK max_discount (default the max)')
    ap.add_argument('--wheel-cells-B', help='coin cells in B, each inside ECON-WHEEL cell_coins_B_range (default: its default_cells_B)')
    ap.add_argument('--wheel-weights', help='weights of coin cells then up to 2 item cells (default all 1)')
    ap.add_argument('--upgrade-lines', type=int, default=1)
    ap.add_argument('--achievement-classes', type=int, default=3)
    ap.add_argument('--achievement-tiers', type=int, default=5, help='tiers per achievement class, inside ECON-QUEST achievement_tiers')
    ap.add_argument('--skin-table', help='unlock_table.json from make_skin_table.py (adds skin rows to the snapshot only)')
    ap.add_argument('--ad-unlock-table', help='ad_unlock_table.json from product_contract.py ad-unlock')
    ap.add_argument('--project', type=Path, help='R4N1: game folder; board from feature_policy.board_of, real level count '
                    'from docs/game_capabilities.json level_count')
    ap.add_argument('--board', choices=['localize', 'remake'], help='R4N1: override the recorded board (--kind english = localize)')
    a = ap.parse_args(argv)
    import feature_policy  # same folder (R4N1)
    board = (feature_policy.board_of(a.project, a.board)[0] if a.project else a.board) or (
        'localize' if a.kind == 'english' else None)
    a.window_rule, a.window_why = feature_policy.rule_verdict('econ_window_levels', board, a.project)
    if a.window_rule == 'not_applicable' and a.mode == 'levels':
        real, src = feature_policy.game_levels(a.project)
        if real is not None and '--total-levels' not in (argv if argv is not None else sys.argv[1:]):
            a.total_levels = real
        print('econ_window_levels 不适用: %s; --total-levels %d (%s); 经济窗口缩到真实关数'
              % (a.window_why, a.total_levels, src), file=sys.stderr)
    if pc._num(a.B) and float(a.B).is_integer():
        a.B = int(a.B)  # B = 10, not 10.0, in the files the game reads
    try:
        table, rules = load_rules(a.rules)
        try:
            cap = capabilities(a, table)        # P17: capabilities first, every number after
        except ValueError as exc:
            raise Refused('capability record: %s' % exc)
        cfg, snap, warnings = (build_no_wallet if a.no_wallet else build)(a, table, rules, *([cap] if a.no_wallet else []))
    except Refused as exc:
        print('refused, nothing written:\n%s' % exc, file=sys.stderr)
        return 2
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir / caps_file()).write_text(dumps(cap), encoding='utf-8')
    (a.out_dir / 'economy_config.json').write_text(dumps(cfg), encoding='utf-8')
    (a.out_dir / 'economy_snapshot.json').write_text(dumps(snap), encoding='utf-8')
    report = pc.economy_audit(json.loads(dumps(snap)), a.kind)
    hits = caps.scan_hardcoded(a.scan_project) if a.scan_project else []
    print(json.dumps({'out_dir': str(a.out_dir), 'files': [caps_file(), 'economy_config.json', 'economy_snapshot.json'],
                      'warnings': warnings, 'audit_ok': report['ok'], 'audit_counts': report['counts'],
                      'audit_errors': [r['id'] for r in report['results'] if r['status'] == 'error'],
                      **({'hardcoded_rewards': hits} if a.scan_project else {})}, ensure_ascii=False))
    return 1 if hits else 0


def caps_file():
    return 'economy_capabilities.json'


if __name__ == '__main__':
    raise SystemExit(main())
