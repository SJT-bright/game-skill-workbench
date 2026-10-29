"""Rule 36 ad-unlock table (economy-rules.md #看广告解锁): separate table, coin table unchanged."""
import copy
import unittest
from product_contract import (ad_unlock_errors, ad_unlock_table, ad_unlock_eligible, budget_errors, AD_UNLOCK_SCHEMA, AD_UNLOCK_POLICY,
                              AD_UNLOCK_VIEWS, AD_UNLOCK_VIEWS_BY_LEVEL, AD_UNLOCK_PROGRESS, AD_UNLOCK_GROUPS,
                              PRICE_LEVEL_TARGETS, ECONOMY_POLICY)
from make_skin_table import make as skin_table


def build_ad_table(table, groups=AD_UNLOCK_GROUPS):
    return ad_unlock_table(table, groups)


class AdUnlockTests(unittest.TestCase):
    def setUp(self):
        self.table = skin_table(50, 'levels', 100, True, 'hero')
        self.ad = build_ad_table(self.table)

    def test_views_follow_price_levels(self):
        self.assertEqual(AD_UNLOCK_VIEWS_BY_LEVEL, {10: 1, 20: 3, 30: 5, 40: 7, 50: 9})
        self.assertEqual(set(AD_UNLOCK_VIEWS), set(PRICE_LEVEL_TARGETS))
        for rarity, level in PRICE_LEVEL_TARGETS.items():
            coin_ads = level // 5  # 5B coin ads needed to earn the same price
            self.assertEqual(AD_UNLOCK_VIEWS[rarity], coin_ads - 1, 'ad unlock needs one view fewer than coin ads')
            self.assertGreater(level / AD_UNLOCK_VIEWS[rarity], 5, 'per-view coin equivalent exceeds the 5B coin ad')

    def test_valid_table_passes_and_coin_table_unchanged(self):
        self.assertEqual(budget_errors(self.table), [])
        self.assertEqual(ad_unlock_errors(self.ad, self.table), [])
        for group in AD_UNLOCK_GROUPS:
            n = len(ad_unlock_eligible(self.table, group)); k = sum(r['group'] == group for r in self.ad['items'])
            self.assertTrue(n // 2 <= k <= (n + 1) // 2)
        self.assertTrue(all(r['ads'] == 0 for r in self.table['items']))
        self.assertFalse(any(r['rarity'] == 'limited' for r in self.ad['items']))

    def test_no_backgrounds_and_endless(self):
        for t in (skin_table(40, 'levels', 70, False, 'cat', limited_mode='every_10'), skin_table(30, 'endless', 100, True, 'hero')):
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
                                  'price_level': r['coins'] // B, 'ads_required': AD_UNLOCK_VIEWS_BY_LEVEL[r['coins'] // B]})
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


if __name__ == '__main__':
    unittest.main()
