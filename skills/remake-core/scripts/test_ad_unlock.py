"""Rule 36 ad-unlock table (economy-rules.md #看广告解锁): separate table, coin table unchanged.

rule36-c.v1 (new tables, Saul 2026-11-01, ECON-ADUNLOCK): 60 % of each group, every tier of 2+ mixed, cheapest stays
coins, views = ceil(price / 2B) on a normal-5-80.v1 coin table. rule36-b.v1 (frozen normal-10-50.v1 tables): about half,
10B->1 ... 50B->9 -- the old tests below run unchanged against frozen tables, so frozen tables stay checked."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from product_contract import (ad_unlock_errors, ad_unlock_table, ad_unlock_eligible, budget_errors, ad_unlock_views, ad_unlock_share_ok,
                              AD_UNLOCK_SCHEMA, AD_UNLOCK_POLICY, AD_UNLOCK_POLICY_LEGACY,
                              AD_UNLOCK_VIEWS, AD_UNLOCK_VIEWS_BY_LEVEL, AD_UNLOCK_VIEWS_LEGACY, AD_UNLOCK_VIEWS_BY_LEVEL_LEGACY,
                              AD_UNLOCK_PROGRESS, AD_UNLOCK_GROUPS, PRICE_LEVEL_TARGETS, PRICE_LEVEL_TARGETS_LEGACY,
                              SKIN_POLICY, SKIN_POLICY_LEGACY, ECONOMY_POLICY, skin_tiers_B)
from make_skin_table import make as skin_table

HERE = Path(__file__).resolve().parent
LEGACY = SKIN_POLICY_LEGACY


def build_ad_table(table, groups=AD_UNLOCK_GROUPS, policy=AD_UNLOCK_POLICY_LEGACY):
    return ad_unlock_table(table, groups, policy)


def rules_table():
    """remake-economy/references/economy_rules_table.json when this tree has it (the contract), else None."""
    path = HERE.parents[1] / 'remake-economy/references/economy_rules_table.json'
    if not path.is_file():
        return None
    return {r['id']: r for r in json.loads(path.read_text(encoding='utf-8'))['rules']}


class AdUnlockTests(unittest.TestCase):
    """rule36-b.v1 on frozen normal-10-50.v1 tables (unchanged v7.8 behaviour)."""
    def setUp(self):
        self.table = skin_table(50, 'levels', 100, True, 'hero', economy_policy=LEGACY)
        self.ad = build_ad_table(self.table)

    def test_views_follow_price_levels(self):
        self.assertEqual(AD_UNLOCK_VIEWS_BY_LEVEL_LEGACY, {10: 1, 20: 3, 30: 5, 40: 7, 50: 9})
        self.assertEqual(set(AD_UNLOCK_VIEWS_LEGACY), set(PRICE_LEVEL_TARGETS_LEGACY))
        for rarity, level in PRICE_LEVEL_TARGETS_LEGACY.items():
            coin_ads = level // 5  # 5B coin ads needed to earn the same price
            self.assertEqual(AD_UNLOCK_VIEWS_LEGACY[rarity], coin_ads - 1, 'ad unlock needs one view fewer than coin ads')
            self.assertGreater(level / AD_UNLOCK_VIEWS_LEGACY[rarity], 5, 'per-view coin equivalent exceeds the 5B coin ad')

    def test_valid_table_passes_and_coin_table_unchanged(self):
        self.assertEqual(self.table['economy_policy'], LEGACY)
        self.assertEqual(self.ad['policy'], AD_UNLOCK_POLICY_LEGACY)
        self.assertEqual(budget_errors(self.table), [])
        self.assertEqual(ad_unlock_errors(self.ad, self.table), [])
        for group in AD_UNLOCK_GROUPS:
            n = len(ad_unlock_eligible(self.table, group)); k = sum(r['group'] == group for r in self.ad['items'])
            self.assertTrue(n // 2 <= k <= (n + 1) // 2)
        self.assertTrue(all(r['ads'] == 0 for r in self.table['items']))
        self.assertFalse(any(r['rarity'] == 'limited' for r in self.ad['items']))

    def test_no_backgrounds_and_endless(self):
        for t in (skin_table(40, 'levels', 70, False, 'cat', limited_mode='every_10', economy_policy=LEGACY),
                  skin_table(30, 'endless', 100, True, 'hero', economy_policy=LEGACY)):
            self.assertEqual(ad_unlock_errors(build_ad_table(t), t), [])

    def test_selection_spreads_over_tiers(self):
        rows = [r for r in self.ad['items'] if r['group'] == 'skin']
        self.assertEqual([sum(r['rarity'] == k for r in rows) for k in ('common', 'rare', 'epic', 'legendary')], [3, 3, 2, 1])
        self.assertEqual(len([r for r in self.ad['items'] if r['group'] == 'background']), 4)
        cheapest = min(ad_unlock_eligible(self.table, 'skin'), key=lambda x: (x['coins'], x['order']))
        self.assertNotIn(cheapest['id'], {r['id'] for r in rows})

    def test_wrong_views_rejected(self):
        bad = copy.deepcopy(self.ad); bad['items'][0]['ads_required'] += 1
        self.assertTrue(any('views/price' in e for e in ad_unlock_errors(bad, self.table)))
        bad = copy.deepcopy(self.ad); bad['views_by_price_level']['10'] = 2
        self.assertTrue(ad_unlock_errors(bad, self.table))

    def test_limited_free_unknown_rejected(self):
        for target in ('hero_limited', 'hero_01', 'ghost_99'):
            bad = copy.deepcopy(self.ad); row = dict(bad['items'][0], id=target)
            if target == 'hero_limited':
                row.update(rarity='limited', coin_price_reference=2500, price_level=50, ads_required=9)
            bad['items'][0] = row
            self.assertTrue(any(target in e for e in ad_unlock_errors(bad, self.table)), target)

    def test_more_or_less_than_half_rejected(self):
        listed = {r['id'] for r in self.ad['items']}
        extra = [r for r in ad_unlock_eligible(self.table, 'skin') if r['id'] not in listed][:2]
        more = copy.deepcopy(self.ad); B = self.table['normal_level_coins']
        for r in extra:
            more['items'].append({'id': r['id'], 'group': 'skin', 'rarity': r['rarity'], 'coin_price_reference': r['coins'],
                                  'price_level': r['coins'] // B, 'ads_required': AD_UNLOCK_VIEWS_BY_LEVEL_LEGACY[r['coins'] // B]})
        self.assertTrue(any('about half' in e for e in ad_unlock_errors(more, self.table)))
        less = copy.deepcopy(self.ad)
        drop = [r['id'] for r in less['items'] if r['group'] == 'skin'][:2]
        less['items'] = [r for r in less['items'] if r['id'] not in drop]
        self.assertTrue(any('about half' in e for e in ad_unlock_errors(less, self.table)))

    def test_duplicate_extra_key_schema_and_b(self):
        bad = copy.deepcopy(self.ad); bad['items'].append(dict(bad['items'][0]))
        self.assertTrue(ad_unlock_errors(bad, self.table))
        bad = copy.deepcopy(self.ad); bad['items'][0]['coins'] = 0
        self.assertTrue(ad_unlock_errors(bad, self.table))
        bad = copy.deepcopy(self.ad); bad['policy'] = 'rule36.v0'
        self.assertTrue(ad_unlock_errors(bad, self.table))
        bad = copy.deepcopy(self.ad); bad['normal_level_coins'] = 60
        self.assertTrue(ad_unlock_errors(bad, self.table))
        bad = copy.deepcopy(self.ad); bad['progress'] = dict(bad['progress'], cancel_error_timeout='counts')
        self.assertTrue(ad_unlock_errors(bad, self.table))

    def test_coin_item_carrying_ads_still_rejected_by_budget(self):
        table = copy.deepcopy(self.table)
        row = next(r for r in table['items'] if r['id'] == self.ad['items'][0]['id'])
        row['ads'] = 3
        self.assertTrue(budget_errors(table))
        self.assertTrue(ad_unlock_errors(self.ad, table))
        table = copy.deepcopy(self.table)
        row = next(r for r in table['items'] if r['id'] == self.ad['items'][0]['id'])
        row.update(unlock='ads', coins=0, ads=3)
        self.assertTrue(budget_errors(table))

    def test_map_group_allowed_for_ordinary_games(self):
        table = copy.deepcopy(self.table); B = table['normal_level_coins']
        for i, (rarity, lv) in enumerate([('common', 10), ('rare', 20), ('epic', 30), ('legendary', 40)]):
            table['items'].append({'id': 'map_%02d' % (i + 2), 'group': 'map', 'order': i + 2, 'rarity': rarity, 'unlock': 'coins',
                                   'ads': 0, 'coins': B * lv})
        ad = build_ad_table(table, AD_UNLOCK_GROUPS + ('map',))
        self.assertEqual(budget_errors(table), [])
        self.assertEqual(ad_unlock_errors(ad, table), [])
        maps = [r for r in ad['items'] if r['group'] == 'map']
        self.assertEqual(len(maps), 2)
        others = [r for r in ad['items'] if r['group'] != 'map']
        ad['items'] = others  # maps are opt-in: a game may keep every map a coin purchase
        self.assertEqual(ad_unlock_errors(ad, table), [])
        ad['items'] = others + maps[:1]  # once listed, about half applies to the map group too
        self.assertTrue(any(e.startswith('map:') for e in ad_unlock_errors(ad, table)))

    def test_frozen_tables_stay_checked_not_skipped(self):
        """A frozen table is checked by its own numbers: its old bad cases still fail (not 'not checked')."""
        bad = copy.deepcopy(self.table); bad['items'][-1]['coins'] += 1
        self.assertTrue(budget_errors(bad))
        bad = copy.deepcopy(self.table); bad['price_level_targets'] = dict(PRICE_LEVEL_TARGETS)
        self.assertTrue(any('differs from normal-10-50.v1' in e for e in budget_errors(bad)))
        # a frozen table is not judged by the new numbers, and a new ad table cannot bind it
        self.assertTrue(ad_unlock_errors(dict(self.ad, policy=AD_UNLOCK_POLICY), self.table))
        with self.assertRaises(ValueError):
            ad_unlock_table(self.table)  # default rule36-c.v1 refuses a normal-10-50.v1 coin table


class AdUnlockRule36CTests(unittest.TestCase):
    """rule36-c.v1 on normal-5-80.v1 tables (Saul 2026-11-01)."""
    def setUp(self):
        self.table = skin_table(50, 'levels', 60, True, 'hero')
        self.ad = ad_unlock_table(self.table)

    def test_contract_constants_follow_rules_table(self):
        self.assertEqual((ECONOMY_POLICY, AD_UNLOCK_POLICY), ('normal-5-80.v1', 'rule36-c.v1'))
        self.assertEqual(PRICE_LEVEL_TARGETS, {'common': 5, 'rare': 10, 'epic': 20, 'legendary': 40, 'limited': 80})
        self.assertEqual(skin_tiers_B(SKIN_POLICY_LEGACY), {'common': 10, 'rare': 20, 'epic': 30, 'legendary': 40, 'limited': 50})
        self.assertEqual(AD_UNLOCK_VIEWS_BY_LEVEL, {5: 3, 10: 5, 20: 10, 40: 20})
        self.assertEqual(AD_UNLOCK_VIEWS, {'common': 3, 'rare': 5, 'epic': 10, 'legendary': 20})
        rules = rules_table()
        if rules is None:
            self.skipTest('economy_rules_table.json not in this tree')
        tier, adu = rules['ECON-TIER']['params'], rules['ECON-ADUNLOCK']['params']
        self.assertEqual((tier['policy'], tier['tiers_B']), (SKIN_POLICY, PRICE_LEVEL_TARGETS))
        self.assertEqual((tier['legacy']['policy'], tier['legacy']['tiers_B']), (SKIN_POLICY_LEGACY, PRICE_LEVEL_TARGETS_LEGACY))
        self.assertEqual((adu['policy'], adu['share'], adu['B_per_view']), (AD_UNLOCK_POLICY, 0.6, 2))
        self.assertEqual(adu['views_by_tier_B'], {str(k): v for k, v in AD_UNLOCK_VIEWS_BY_LEVEL.items()})
        self.assertEqual(adu['legacy']['policy'], AD_UNLOCK_POLICY_LEGACY)
        self.assertEqual(adu['legacy']['views_by_tier_B'], {str(k): v for k, v in AD_UNLOCK_VIEWS_BY_LEVEL_LEGACY.items()})
        for b, v in adu['views_by_tier_B'].items():
            self.assertEqual(ad_unlock_views(int(b) * 50, 50), v)

    def test_views_are_price_over_2B_rounded_up(self):
        for level, want in [(5, 3), (10, 5), (20, 10), (40, 20), (80, 40), (1, 1), (3, 2)]:
            self.assertEqual(ad_unlock_views(level * 50, 50), want)
        self.assertEqual(ad_unlock_views(363, 72.5), 3)  # 5 x 72.5 = 362.5 written as 363 is still 5B
        self.assertEqual(ad_unlock_views(725, 72.5), 5)
        self.assertEqual(ad_unlock_views(726, 72.5), 6)  # 10 x 72.5 is whole: 726 is above 10B
        self.assertEqual([ad_unlock_views(p * 50, 50, AD_UNLOCK_POLICY_LEGACY) for p in (10, 20, 30, 40, 50, 5)], [1, 3, 5, 7, 9, None])

    def test_share_band_is_60_percent(self):
        for n, lo, hi in [(18, 10, 11), (9, 5, 6), (27, 16, 17), (5, 3, 3), (1, 0, 1), (0, 0, 0)]:
            ok = [k for k in range(n + 2) if ad_unlock_share_ok(n, k)]
            self.assertEqual((ok[0], ok[-1]), (lo, hi), n)
        self.assertTrue(ad_unlock_share_ok(18, 9, AD_UNLOCK_POLICY_LEGACY))
        self.assertFalse(ad_unlock_share_ok(18, 9))

    def test_default_tables_pass_and_pick_is_deterministic(self):
        self.assertEqual(self.table['economy_policy'], SKIN_POLICY)
        self.assertEqual(budget_errors(self.table), [])
        self.assertEqual(ad_unlock_errors(self.ad, self.table), [])
        self.assertEqual(json.dumps(self.ad), json.dumps(ad_unlock_table(copy.deepcopy(self.table))))
        shuffled = copy.deepcopy(self.table); shuffled['items'].reverse()
        self.assertEqual(json.dumps(ad_unlock_table(shuffled)['items']), json.dumps(self.ad['items']))
        for t in (skin_table(40, 'levels', 70, False, 'cat', limited_mode='every_10'), skin_table(30, 'endless', 100, True, 'hero')):
            self.assertEqual(ad_unlock_errors(ad_unlock_table(t), t), [])

    def test_default_allocation(self):
        """20 protagonist skins (18 priced) and 10 backgrounds (9 priced): 11/18 and 5/9 by ads."""
        per = {}
        for r in self.ad['items']:
            per.setdefault(r['group'], {}).setdefault(r['rarity'], 0)
            per[r['group']][r['rarity']] += 1
        self.assertEqual(per['skin'], {'common': 4, 'rare': 4, 'epic': 2, 'legendary': 1})
        self.assertEqual(per['background'], {'common': 2, 'rare': 2, 'epic': 1})
        self.assertEqual([r['id'] for r in self.ad['items'] if r['group'] == 'skin'],
                         ['hero_03', 'hero_05', 'hero_07', 'hero_08', 'hero_10', 'hero_11', 'hero_13', 'hero_14', 'hero_16', 'hero_17', 'hero_19'])
        self.assertEqual([r['id'] for r in self.ad['items'] if r['group'] == 'background'], ['bg_03', 'bg_04', 'bg_06', 'bg_07', 'bg_09'])
        self.assertEqual({r['price_level']: r['ads_required'] for r in self.ad['items']}, {5: 3, 10: 5, 20: 10, 40: 20})
        for group in AD_UNLOCK_GROUPS:
            rows = sorted(ad_unlock_eligible(self.table, group), key=lambda x: (x['coins'], x['order'], x['id']))
            self.assertNotIn(rows[0]['id'], {r['id'] for r in self.ad['items']}, 'cheapest stays coins')
        self.assertFalse(any(r['rarity'] == 'limited' for r in self.ad['items']))
        self.assertTrue(all(r['ads'] == 0 for r in self.table['items']), 'coin table stays coin-only')

    def test_wrong_views_and_header_rejected(self):
        bad = copy.deepcopy(self.ad); bad['items'][0]['ads_required'] += 1
        self.assertTrue(any('views/price' in e for e in ad_unlock_errors(bad, self.table)))
        old = copy.deepcopy(self.ad)  # old rule36-b numbers on a new table
        for r in old['items']:
            r['ads_required'] = {5: 1, 10: 1, 20: 3, 40: 7}[r['price_level']]
        self.assertTrue(ad_unlock_errors(old, self.table))
        bad = copy.deepcopy(self.ad); bad['views_by_price_level']['5'] = 1
        self.assertTrue(any('views_by_price_level' in e for e in ad_unlock_errors(bad, self.table)))

    def test_half_is_not_60_percent(self):
        half = ad_unlock_table(skin_table(50, 'levels', 60, True, 'hero', economy_policy=LEGACY), policy=AD_UNLOCK_POLICY_LEGACY)
        ids = {r['id'] for r in half['items']}
        bad = copy.deepcopy(self.ad); B = self.table['normal_level_coins']
        bad['items'] = [dict(id=r['id'], group=r['group'], rarity=r['rarity'], coin_price_reference=r['coins'], price_level=r['coins'] // B,
                             ads_required=AD_UNLOCK_VIEWS_BY_LEVEL[r['coins'] // B]) for r in self.table['items'] if r['id'] in ids]
        self.assertTrue(any('requires 60%' in e for e in ad_unlock_errors(bad, self.table)))
        less = copy.deepcopy(self.ad); less['items'] = [r for r in less['items'] if r['id'] != 'hero_13']
        self.assertEqual(ad_unlock_errors(less, self.table), [])  # 10 of 18 is inside floor(10.8)..ceil(10.8)
        less['items'] = [r for r in less['items'] if r['id'] != 'hero_07']
        self.assertTrue(any('skin: 9 of 18' in e and '(10..11)' in e for e in ad_unlock_errors(less, self.table)))

    def test_cheapest_must_stay_coins_and_tiers_mixed(self):
        B = self.table['normal_level_coins']
        def row(i):
            src = next(r for r in self.table['items'] if r['id'] == i)
            return dict(id=i, group=src['group'], rarity=src['rarity'], coin_price_reference=src['coins'], price_level=src['coins'] // B,
                        ads_required=AD_UNLOCK_VIEWS_BY_LEVEL[src['coins'] // B])
        swap = copy.deepcopy(self.ad)  # hero_02 (cheapest) instead of hero_03: same count, same tier
        swap['items'] = [row('hero_02') if r['id'] == 'hero_03' else r for r in swap['items']]
        self.assertTrue(any('cheapest item hero_02' in e for e in ad_unlock_errors(swap, self.table)))
        legend = copy.deepcopy(self.ad)  # both legendary skins by ads, one rare back to coins: count still 11
        legend['items'] = [r for r in legend['items'] if r['id'] != 'hero_14'] + [row('hero_18')]
        self.assertTrue(any('skin legendary: 2 of 2' in e for e in ad_unlock_errors(legend, self.table)))

    def test_limited_free_unknown_rejected(self):
        for target in ('hero_limited', 'hero_01', 'ghost_99'):
            bad = copy.deepcopy(self.ad); row = dict(bad['items'][0], id=target)
            if target == 'hero_limited':
                row.update(rarity='limited', coin_price_reference=4000, price_level=80, ads_required=40)
            bad['items'][0] = row
            self.assertTrue(any(target in e for e in ad_unlock_errors(bad, self.table)), target)

    def test_new_coin_table_checked_by_new_prices(self):
        bad = copy.deepcopy(self.table); bad['items'][-1]['coins'] += 1
        self.assertTrue(budget_errors(bad))
        old = skin_table(50, 'levels', 60, True, 'hero', economy_policy=LEGACY)
        relabel = dict(old, economy_policy=SKIN_POLICY)  # old 10..50 prices claiming the new policy
        self.assertTrue(any('5/10/20/40/80' in e for e in budget_errors(relabel)))
        self.assertTrue(ad_unlock_errors(dict(self.ad, economy_policy=LEGACY), self.table))
        self.assertTrue(ad_unlock_errors(self.ad, dict(self.table, economy_policy=LEGACY)))


class FractionalBTests(unittest.TestCase):
    """B = 72.5 (Saul 2026-10-31: B need not be whole; prices are k*B rounded half up, rules table B.rounding)."""
    def test_fractional_b_table_prices_views_and_checks(self):
        t = skin_table(72.5, 'levels', 60, True, 'hero')
        self.assertEqual(t['normal_level_coins'], 72.5)
        self.assertEqual(t['coins_per_ad'], 363)  # 5B = 362.5 -> 363
        prices = sorted({r['coins'] for r in t['items'] if r['coins']})
        self.assertEqual(prices, [363, 725, 1450, 2900, 5800])  # 5/10/20/40/80B rounded half up
        self.assertEqual(budget_errors(t), [])
        ad = ad_unlock_table(t)
        self.assertEqual(ad_unlock_errors(ad, t), [])
        self.assertEqual({r['price_level']: r['ads_required'] for r in ad['items']}, {5: 3, 10: 5, 20: 10, 40: 20})
        bad = copy.deepcopy(t); next(r for r in bad['items'] if r['coins'] == 725)['coins'] = 727  # 2 away from 10B
        self.assertTrue(budget_errors(bad))
        bad = copy.deepcopy(t); next(r for r in bad['items'] if r['coins'] == 363)['coins'] = 362  # still within 5B rounding
        self.assertEqual(budget_errors(bad), [])

    def test_whole_b_output_unchanged(self):
        self.assertEqual(json.dumps(skin_table(50, 'levels', 60, True, 'hero')), json.dumps(skin_table(50.0 if False else 50, 'levels', 60, True, 'hero')))
        t = skin_table(50, 'levels', 60, True, 'hero')
        self.assertIs(type(t['coins_per_ad']), int)
        self.assertTrue(all(type(r['coins']) is int for r in t['items']))

    def test_cli_accepts_fractional_b(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 't.json'
            r = subprocess.run([sys.executable, str(HERE / 'make_skin_table.py'), '--R', '72.5', '--levels', '--out', str(out)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(out.read_text())['normal_level_coins'], 72.5)
            r = subprocess.run([sys.executable, str(HERE / 'make_skin_table.py'), '--R', '50', '--levels', '--out', str(out)],
                               capture_output=True, text=True)
            self.assertEqual(json.loads(out.read_text())['normal_level_coins'], 50)
            self.assertIn('"normal_level_coins": 50,', out.read_text())


class AdUnlockCliTests(unittest.TestCase):
    def run_cli(self, table, *extra):
        with tempfile.TemporaryDirectory() as td:
            src, out = Path(td) / 'unlock.json', Path(td) / 'ad.json'
            src.write_text(json.dumps(table))
            r = subprocess.run([sys.executable, str(HERE / 'product_contract.py'), 'ad-unlock', '--table', str(src), '--out', str(out), *extra],
                               capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            return r, (json.loads(out.read_text()) if out.exists() else None)

    def test_default_policy_is_new_and_legacy_is_explicit(self):
        new = skin_table(50, 'levels', 60, True, 'hero')
        r, ad = self.run_cli(new)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((ad['policy'], ad['economy_policy']), (AD_UNLOCK_POLICY, SKIN_POLICY))
        old = skin_table(50, 'levels', 60, True, 'hero', economy_policy=LEGACY)
        r, ad = self.run_cli(old)
        self.assertEqual((r.returncode, ad), (1, None))
        self.assertIn('--policy rule36-b.v1', r.stderr)
        r, ad = self.run_cli(old, '--policy', AD_UNLOCK_POLICY_LEGACY)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(ad, ad_unlock_table(old, policy=AD_UNLOCK_POLICY_LEGACY))
        r, ad = self.run_cli(new, '--policy', AD_UNLOCK_POLICY_LEGACY)
        self.assertEqual((r.returncode, ad), (1, None))


if __name__ == '__main__':
    unittest.main()
