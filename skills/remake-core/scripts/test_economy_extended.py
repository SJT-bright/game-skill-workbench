"""Extended economy rules (remake-economy economy-rules.md 第五节起, Saul 2026-10-31 / 2026-11-01) and the economy-audit command.

Constants must agree with remake-economy/references/economy_rules_table.json (revision 2026-11-04.v3.4, 36 rules); the
ad-unlock path is tested in test_ad_unlock.py. Samples live in remake-core/examples/economy-snapshot/.
ECON-TIER / ECON-ADUNLOCK belong to W1b (skin_tiers_B / ad_unlock_views); while those names are missing the two rules are
left out of the comparisons here (W1B_READY)."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

import product_contract as pc

HERE = Path(__file__).resolve().parent
SAMPLES = HERE.parent / 'examples' / 'economy-snapshot'
TABLE = HERE.parent.parent / 'remake-economy' / 'references' / 'economy_rules_table.json'
B = 10
W1B_READY = all(hasattr(pc, n) for n in ('SKIN_POLICY', 'SKIN_POLICY_LEGACY', 'skin_tiers_B', 'AD_UNLOCK_POLICY_LEGACY',
                                         'ad_unlock_views', 'ad_unlock_share_ok'))
W1B_RULES = set() if W1B_READY else {'ECON-TIER', 'ECON-ADUNLOCK'}


def load(name):
    return json.loads((SAMPLES / name).read_text(encoding='utf-8'))


def status(report, rule):
    return next(r['status'] for r in report['results'] if r['id'] == rule)


def row(report, rule):
    return next(r for r in report['results'] if r['id'] == rule)


def with_status(report, *statuses):
    return {x['id'] for x in report['results'] if x['status'] in statuses} - W1B_RULES


def inflow(s, i):
    return next(x for x in s['inflows'] if x['id'] == i)


def sink(s, i):
    return next(x for x in s['sinks'] if x['id'] == i)


@unittest.skipUnless(TABLE.is_file(), 'remake-economy/references/economy_rules_table.json not in this tree '
                     '(English pack before remake-economy is shared)')
class RulesTableAgreesWithConstants(unittest.TestCase):
    def setUp(self):
        self.t = json.loads(TABLE.read_text(encoding='utf-8'))
        self.r = {x['id']: x for x in self.t['rules']}

    def p(self, rule):
        return self.r[rule]['params']

    def test_header_and_rule_ids(self):
        self.assertEqual(self.t['schema'], pc.ECON_RULES_SCHEMA)
        self.assertEqual(self.t['revision'], pc.ECON_RULES_REVISION)
        self.assertEqual(pc.ECON_RULES_REVISION, '2026-11-04.v3.4')
        sev = {k: v for k, v in self.t['severity_by_kind'].items() if not k.startswith('_')}
        self.assertEqual(sev.pop('undecided_max'), pc.ECON_UNDECIDED_MAX)   # v3: undecided numbers at most suggest
        self.assertEqual(sev, pc.ECON_SEVERITY_BY_KIND)
        self.assertEqual((tuple(self.t['origin']['values']), self.t['origin']['default']), (pc.ECON_ORIGINS, pc.ECON_ORIGIN_DEFAULT))
        self.assertEqual(len(self.r), 36)   # round 2: + TIMERCHEST; v3.1: + ONLINE, KEYCHEST; v3.4: + 5
        self.assertEqual(list(self.r), list(pc.ECON_RULE_TITLES))            # same rules, same order
        self.assertEqual({k for k, v in self.r.items() if v['english_default']}, set(pc.ECON_ENGLISH_DEFAULT))

    @unittest.skipUnless(W1B_READY, 'W1b names (skin_tiers_B, ad_unlock_views ...) not in product_contract.py yet')
    def test_tier_and_ad_unlock_policies(self):
        t, a = self.p('ECON-TIER'), self.p('ECON-ADUNLOCK')
        self.assertEqual((t['policy'], t['legacy']['policy']), (pc.SKIN_POLICY, pc.SKIN_POLICY_LEGACY))
        self.assertEqual(t['tiers_B'], pc.skin_tiers_B(pc.SKIN_POLICY))
        self.assertEqual(t['legacy']['tiers_B'], pc.skin_tiers_B(pc.SKIN_POLICY_LEGACY))
        self.assertEqual((a['policy'], a['legacy']['policy']), (pc.AD_UNLOCK_POLICY, pc.AD_UNLOCK_POLICY_LEGACY))
        self.assertEqual({int(k): v for k, v in a['views_by_tier_B'].items()},
                         {k: pc.ad_unlock_views(k * B, B) for k in map(int, a['views_by_tier_B'])})

    def test_existing_rules(self):
        self.assertEqual(self.p('ECON-LEVEL10'), {'window_levels': pc.LEVEL_WINDOW, 'sum_B': pc.LEVEL_WINDOW_SUM_B})
        self.assertEqual(self.p('ECON-X2')['multiplier'], 2)
        g = self.p('ECON-GIFT')
        self.assertEqual((g['reward_B'], g['cooldown_ms'], g['claim_double_checkbox']), (pc.GIFT_REWARD_B, pc.GIFT_COOLDOWN_MS, False))
        self.assertEqual(pc.GIFT_REWARD_B, pc.GIFT_MULTIPLIER)
        self.assertEqual(self.p('ECON-ADCOIN')['reward_B'], pc.AD_COIN_REWARD_B)
        self.assertEqual(pc.AD_COIN_REWARD_B, pc.AD_CURRENCY_MULTIPLIER)
        for rule, value in (('ECON-SHORTCUT', pc.SHORTCUT_REWARD_B), ('ECON-REVISIT', pc.REVISIT_REWARD_B)):
            self.assertEqual((self.p(rule)['reward_B'], self.p(rule)['times']), (value, 1))
        c = self.p('ECON-CHECKIN')
        self.assertEqual({int(k): v for k, v in c['coins_B_by_day'].items()}, pc.CHECKIN_COINS_B_BY_DAY)
        self.assertEqual({int(k): v for k, v in c['no_item_fallback_B'].items()}, pc.CHECKIN_NO_ITEM_FALLBACK_B)
        self.assertEqual({int(k): v for k, v in c['skin_fallback_B'].items()}, pc.CHECKIN_SKIN_FALLBACK_B)
        self.assertEqual({int(k): tuple(v) for k, v in c['allowed_day_coins_B'].items()}, pc.CHECKIN_ALLOWED_DAY_COINS_B)
        self.assertEqual((c['same_day_rows'], c['round_coins_B']), ('sum', pc.CHECKIN_ROUND_COINS_B))
        self.assertEqual({int(k): v for k, v in c['item_amount_by_day'].items()}, pc.CHECKIN_ITEM_AMOUNT_BY_DAY)
        self.assertTrue(isinstance(self.t['B'].get('rounding'), str) and self.t['B']['rounding'])   # text only, no constant
        d = self.p('ECON-CLAIMX2')
        self.assertEqual((tuple(d['windows']), d['default_checked'], d['multiplier'], d['home_gift']),
                         (pc.CLAIM_DOUBLE_WINDOWS, True, pc.CLAIM_DOUBLE_MULTIPLIER, False))
        self.assertEqual({k: tuple(v) for k, v in d['accepted_marks'].items()}, pc.CLAIM_DOUBLE_ACCEPTED_MARKS)
        self.assertEqual(tuple(d['excluded']), pc.CLAIM_DOUBLE_EXCLUDED)
        self.assertEqual(tuple(d['english_required_windows']), pc.CLAIM_DOUBLE_ENGLISH_REQUIRED_WINDOWS)
        self.assertTrue(set(pc.CLAIM_DOUBLE_ENGLISH_REQUIRED_WINDOWS) <= set(pc.CLAIM_DOUBLE_WINDOWS))

    def test_new_rules(self):
        # round 2: the table gained default_B (ITEM), default_cells_B (WHEEL), achievement_tiers (QUEST)
        self.assertEqual(self.p('ECON-ITEM'), {'min_B': pc.ITEM_PRICE_MIN_B, 'max_B': pc.ITEM_PRICE_MAX_B,
                                               'default_B': pc.ITEM_PRICE_DEFAULT_B})
        self.assertTrue(pc.ITEM_PRICE_MIN_B <= pc.ITEM_PRICE_DEFAULT_B <= pc.ITEM_PRICE_MAX_B)
        self.assertEqual(self.p('ECON-PACK')['max_discount'], pc.PACK_MAX_DISCOUNT)
        self.assertEqual(self.p('ECON-ADITEM')['per_ad'], pc.AD_ITEM_PER_VIEW)
        w = self.p('ECON-WHEEL')
        self.assertEqual((w['free_per_day'], w['ad_per_day'], w['max_cell_B'], w['expected_per_spin_B_max'], w['result_double']),
                         (pc.WHEEL_FREE_PER_DAY, pc.WHEEL_AD_PER_DAY, pc.WHEEL_MAX_CELL_B, pc.WHEEL_EXPECTED_MAX_B, True))
        self.assertEqual((tuple(w['cell_coins_B_range']), tuple(w['default_cells_B'])),
                         (pc.WHEEL_CELL_COINS_B_RANGE, pc.WHEEL_DEFAULT_CELLS_B))
        cells = [{'amount': k * B} for k in pc.WHEEL_DEFAULT_CELLS_B]        # the default wheel passes ECON-WHEEL
        self.assertEqual(pc.wheel_config_errors({'free_per_day': 1, 'ad_per_day': 2, 'cells': cells,
                                                 'result_double': {'enabled': True, 'default_checked': True}}, B), [])
        o = self.p('ECON-OFFLINE')
        self.assertEqual((o['min_away_sec'], o['cap_sec'], o['ad_multiplier'], o['min_payout']),
                         (pc.OFFLINE_MIN_AWAY_SEC, pc.OFFLINE_CAP_SEC, pc.OFFLINE_AD_MULTIPLIER, pc.OFFLINE_MIN_PAYOUT))
        u = self.p('ECON-UPGRADE')
        self.assertEqual((u['levels'], u['first_B'], u['last_B'], u['total_B'], u['tolerance']),
                         (pc.UPGRADE_LEVELS, pc.UPGRADE_FIRST_B, pc.UPGRADE_LAST_B, pc.UPGRADE_TOTAL_B, pc.UPGRADE_TOLERANCE))
        q = self.p('ECON-QUEST')
        self.assertEqual((q['daily_task_B'], q['daily_tasks'], q['achievement_B_min'], q['achievement_B_max'], q['achievement_gives_skin']),
                         (pc.QUEST_DAILY_TASK_B, pc.QUEST_DAILY_TASKS, pc.QUEST_ACHIEVEMENT_B_MIN, pc.QUEST_ACHIEVEMENT_B_MAX, False))
        self.assertEqual(tuple(q['achievement_tiers']), pc.QUEST_ACHIEVEMENT_TIERS)
        e = self.p('ECON-ENERGY')
        self.assertEqual((e['ad_refill'], e['skip_if_no_room'], e['only_if_original_has_energy']), (pc.ENERGY_AD_REFILL, True, True))
        s = self.p('ECON-SECOND')
        self.assertEqual((s['levels_drop_second_currency'], s['second_per_ad']), (False, pc.SECOND_PER_AD))
        self.assertEqual((s['kept']['exchange_max_discount'], s['kept']['ad_second_needs_daily_cap']),
                         (pc.SECOND_KEPT_EXCHANGE_MAX_DISCOUNT, pc.SECOND_KEPT_AD_NEEDS_DAILY_CAP))
        self.assertTrue(self.p('ECON-PACING')['report_only'])

    def test_v3_rules(self):
        a = self.p('ECON-ADCOIN')
        self.assertEqual((a['per_day'], a['cooldown_sec'], a['decided_by_saul']), (pc.AD_COIN_PER_DAY, pc.AD_COIN_COOLDOWN_SEC, pc.AD_COIN_DECIDED))
        f = self.p('ECON-SHOPFREE')
        self.assertEqual((f['item_per_claim'], f['coins_B_per_claim'], f['per_slot_per_day'], f['decided_by_saul']),
                         (pc.SHOP_FREE_ITEM_PER_CLAIM, pc.SHOP_FREE_COINS_B_PER_CLAIM, pc.SHOP_FREE_PER_SLOT_PER_DAY, pc.SHOP_FREE_DECIDED))
        c = self.p('ECON-CHEST')
        self.assertEqual((c['every_levels'], c['free_max_B'], c['double_max_B']),
                         (pc.CHEST_EVERY_LEVELS, pc.CHEST_FREE_MAX_B, pc.CHEST_DOUBLE_MAX_B))
        fl = self.p('ECON-FLOAT')
        self.assertEqual((fl['each_max_B'], fl['per_round_max']), (pc.FLOAT_EACH_MAX_B, pc.FLOAT_PER_ROUND_MAX))
        b = self.p('ECON-BONUS')
        self.assertEqual((b['reward_B'], b['ad_reward_B']), (pc.BONUS_REWARD_B, pc.BONUS_AD_REWARD_B))
        t = self.p('ECON-SKINTRIAL')
        self.assertEqual((tuple(t['no_popup_levels']), t['every_levels'], t['endless_every_rounds'], t['required_if_skins']),
                         (pc.SKIN_TRIAL_NO_POPUP_LEVELS, pc.SKIN_TRIAL_EVERY_LEVELS, pc.SKIN_TRIAL_ENDLESS_EVERY_ROUNDS, True))
        self.assertEqual((tuple(t['endless_no_popup_rounds']), t['level_trial'], t['endless_trial'], t['endless_trial_minutes'],
                          t['claim_double']),
                         (pc.SKIN_TRIAL_ENDLESS_NO_POPUP_ROUNDS, pc.SKIN_TRIAL_LEVEL_TRIAL, pc.SKIN_TRIAL_ENDLESS_TRIAL,
                          pc.SKIN_TRIAL_ENDLESS_MINUTES, pc.SKIN_TRIAL_CLAIM_DOUBLE))
        tc = self.p('ECON-TIMERCHEST')
        self.assertEqual((tc['placement'], tc['not_on_home'], tc['free_open_B'], tc['free_open_max_B'], tc['wait_sec'],
                          tc['ad_cut_sec'], tc['ad_cuts_per_round'], tc['rounds_per_day'], tc['decided_by_saul']),
                         (pc.TIMER_CHEST_PLACEMENT, True, pc.TIMER_CHEST_FREE_OPEN_B, pc.TIMER_CHEST_FREE_OPEN_MAX_B,
                          pc.TIMER_CHEST_WAIT_SEC, pc.TIMER_CHEST_AD_CUT_SEC, pc.TIMER_CHEST_AD_CUTS_PER_ROUND,
                          pc.TIMER_CHEST_ROUNDS_PER_DAY, pc.TIMER_CHEST_DECIDED))
        self.assertLess(pc.TIMER_CHEST_AD_CUT_SEC * pc.TIMER_CHEST_AD_CUTS_PER_ROUND, pc.TIMER_CHEST_WAIT_SEC)   # ads never open it
        self.assertEqual(tc['double'], 'ECON-CLAIMX2 timer_chest')
        self.assertIn('timer_chest', pc.CLAIM_DOUBLE_WINDOWS)
        self.assertEqual(self.p('ECON-ENERGY')['no_unlimited_energy'], pc.ENERGY_NO_UNLIMITED)
        # every window the table names is a window the audit knows
        d = self.p('ECON-CLAIMX2')
        self.assertTrue(set(d['windows']) | set(d['excluded']) <= set(pc.ECON_WINDOWS))
        self.assertEqual(set(pc.ECON_WINDOW_SYSTEM), set(d['windows']))

    def test_v31_rules(self):
        # Saul 2026-11-01 「默认数值就这样」: every number of ADCOIN / SHOPFREE / TIMERCHEST / ONLINE / KEYCHEST is decided
        # (v3.4 added the coin jar's numbers to ECON-ONLINE, not decided by Saul: test_v34_numbers)
        for rule in ('ECON-ADCOIN', 'ECON-SHOPFREE', 'ECON-TIMERCHEST', 'ECON-KEYCHEST'):
            self.assertTrue(all(self.p(rule)['decided_by_saul'].values()), rule)
        o = self.p('ECON-ONLINE')
        v31 = {k: v for k, v in o['decided_by_saul'].items() if not k.startswith('jar_')}
        self.assertEqual((tuple(o['tiers_min']), o['per_tier_min_B'], o['per_tier_max_B'], o['day_total_max_B'], v31),
                         (pc.ONLINE_TIERS_MIN, pc.ONLINE_TIER_MIN_B, pc.ONLINE_TIER_MAX_B, pc.ONLINE_DAY_TOTAL_MAX_B, pc.ONLINE_DECIDED))
        k = self.p('ECON-KEYCHEST')
        self.assertEqual((k['cells'], k['total_B'], k['cell_max_B'], k['decided_by_saul']),
                         (pc.KEY_CHEST_CELLS, pc.KEY_CHEST_TOTAL_B, pc.KEY_CHEST_CELL_MAX_B, pc.KEY_CHEST_DECIDED))
        self.assertEqual((pc.ECON_RULE_SYSTEM['ECON-ONLINE'], pc.ECON_RULE_SYSTEM['ECON-KEYCHEST']), ('online_gift', 'key_chest'))
        self.assertIn('只有一种解锁方式', self.r['ECON-ADUNLOCK']['title'])
        # v3.2: the online-time gift and the key chest's summary window are claim windows; +3 KEYS ad cells are not doubled
        self.assertEqual((o['double'], k['double']), ('ECON-CLAIMX2 online_gift', 'ECON-CLAIMX2 key_chest'))
        self.assertTrue({'online_gift', 'key_chest'} <= set(pc.CLAIM_DOUBLE_WINDOWS))
        self.assertIn('key_chest_ad_keys', pc.CLAIM_DOUBLE_EXCLUDED)
        self.assertEqual(len(pc.ECON_WINDOWS), len(set(pc.ECON_WINDOWS)))   # no window listed twice

    def test_v33_no_coin_platform_rewards(self):
        # Saul 2026-11-04: without coins, add-to-desktop / home revisit pay +3 energy; no energy either -> add a coin and skins
        for rule in ('ECON-SHORTCUT', 'ECON-REVISIT'):
            p = self.p(rule)
            self.assertEqual(p['no_coin_with_energy'], {'currency': 'energy', 'amount': pc.NO_COIN_PLATFORM_ENERGY}, rule)
            self.assertEqual(p['no_coin_no_energy'], pc.NO_COIN_NO_ENERGY, rule)
            self.assertEqual(set(p['decided_by_saul']), {'no_coin_with_energy', 'no_coin_no_energy'}, rule)
            self.assertTrue(all(p['decided_by_saul'].values()), rule)
            self.assertEqual((p['reward_B'], p['currency']), (pc.SHORTCUT_REWARD_B, 'main'), rule)   # coin games unchanged

    def test_v34_numbers(self):
        # rules table v3.4 (2026-11-04, ad-boost round six): the constants are the table's numbers and Saul decided none of
        # them (decided_by_saul false: a miss is at most a suggestion), as test_economy_plan.js「v3.4 新编号都在规则表里」
        bp = self.p('ECON-BATTLEPASS')
        self.assertEqual({k: bp[k] for k in pc.BATTLE_PASS_PERIOD}, pc.BATTLE_PASS_PERIOD)
        self.assertEqual((tuple(bp['points_per_endless_round']), bp['free_cell_B'], tuple(bp['ad_cells_B']),
                          bp['season_max_B_without_x2']),
                         (pc.BATTLE_PASS_ENDLESS_POINTS, pc.BATTLE_PASS_FREE_CELL_B, pc.BATTLE_PASS_AD_CELLS_B,
                          pc.BATTLE_PASS_SEASON_MAX_B))
        self.assertEqual(len(pc.BATTLE_PASS_AD_CELLS_B), pc.BATTLE_PASS_PERIOD['tiers'])
        rp, ru = self.p('ECON-REVIVEPAY'), self.p('ECON-RUNPAY')
        self.assertEqual((rp['price_B'], rp['per_round_with_ad_revive']), (pc.REVIVE_PAY_PRICE_B, pc.REVIVE_PAY_PER_ROUND))
        self.assertEqual((ru['normal_round_B'], ru['round_max_B'], ru['min_coins_if_score']),
                         (pc.RUN_PAY_NORMAL_B, pc.RUN_PAY_MAX_B, pc.RUN_PAY_MIN_COINS))
        self.assertEqual({k: v for k, v in self.p('ECON-MIDRUN').items() if k != 'decided_by_saul'}, pc.MID_RUN)
        self.assertEqual(self.p('ECON-NOODDS'), {})
        self.assertEqual(self.p('ECON-WHEEL')['no_replacement'], pc.WHEEL_NO_REPLACEMENT)
        self.assertEqual(self.p('ECON-CHEST')['score_chest'], pc.SCORE_CHEST)
        o = self.p('ECON-ONLINE')
        self.assertEqual((o['jar_fill_B_per_min'], o['jar_cap_B']), (pc.ONLINE_JAR_FILL_B_PER_MIN, pc.ONLINE_JAR_CAP_B))
        self.assertEqual(self.p('ECON-UPGRADE')['lose_free_upgrade_per_round'], pc.UPGRADE_LOSE_FREE_PER_ROUND)
        self.assertEqual(tuple(self.p('ECON-ADUNLOCK')['gate_every_levels']), pc.AD_UNLOCK_GATE_EVERY_LEVELS)
        undecided = {'ECON-BATTLEPASS': None, 'ECON-REVIVEPAY': None, 'ECON-RUNPAY': None, 'ECON-MIDRUN': None,
                     'ECON-UPGRADE': ('lose_free_upgrade_per_round',), 'ECON-WHEEL': ('no_replacement',),
                     'ECON-CHEST': ('score_chest',), 'ECON-ONLINE': ('jar_fill_B_per_min', 'jar_cap_B', 'jar_claims_per_day'),
                     'ECON-ADUNLOCK': ('gate_every_levels',)}
        for rule, keys in undecided.items():
            p = self.p(rule)
            for k in keys or [k for k in p if k != 'decided_by_saul']:
                self.assertIs(p['decided_by_saul'][k], False, '%s.%s' % (rule, k))
        for rule in ('ECON-BATTLEPASS', 'ECON-REVIVEPAY', 'ECON-RUNPAY', 'ECON-MIDRUN', 'ECON-NOODDS'):
            self.assertFalse(self.r[rule]['english_default'], rule)
        d = self.p('ECON-CLAIMX2')
        self.assertTrue({'battle_pass', 'score_chest', 'online_jar'} <= set(d['windows']))
        self.assertTrue({'battle_pass_ad', 'mid_boost', 'lose_upgrade'} <= set(d['excluded']))
        self.assertEqual(tuple(d['english_required_windows']), ('checkin', 'wheel_result', 'gift_window'))
        self.assertEqual([pc.ECON_RULE_SYSTEM[k] for k in ('ECON-BATTLEPASS', 'ECON-REVIVEPAY', 'ECON-RUNPAY', 'ECON-MIDRUN')],
                         ['battle_pass', 'revive_pay', 'run_pay', 'mid_boost'])


class NewRulePureFunctions(unittest.TestCase):
    def test_item_price(self):
        for price in (30, 40, 50):
            self.assertEqual(pc.item_price_errors(price, B), [])
        for price in (10, 29, 51, 0):
            self.assertTrue(pc.item_price_errors(price, B), price)

    def test_pack_discount(self):
        self.assertEqual(pc.pack_discount_errors(30, 81, 3), [])   # exactly 10% off
        self.assertEqual(pc.pack_discount_errors(30, 90, 3), [])   # no discount
        self.assertTrue(pc.pack_discount_errors(30, 80, 3))        # 11% off
        self.assertEqual(pc.pack_discount_errors(300, 3000, 11), [])  # 66 甜点消消乐: 11 for 3000 vs 3300 = 9.1% off
        self.assertTrue(pc.pack_discount_errors(30, 50, 1))        # not a pack

    def test_ad_item(self):
        self.assertEqual(pc.ad_item_errors(1), [])
        self.assertTrue(pc.ad_item_errors(2))

    def test_wheel(self):
        good = {'free_per_day': 1, 'ad_per_day': 2, 'cells': [{'amount': 10}, {'amount': 20}, {'amount': 30}, {'amount': 0}, {'amount': 0},
                {'amount': 0}], 'result_double': {'enabled': True, 'default_checked': True}}
        self.assertEqual(pc.wheel_config_errors(good, B), [])
        self.assertAlmostEqual(pc.wheel_expected(good['cells']), 10.0)
        for change in ({'ad_per_day': 5}, {'free_per_day': 0}, {'cells': [{'amount': 60}, {'amount': 0, 'weight': 9}]},
                       {'cells': [{'amount': 30}, {'amount': 20}]}, {'result_double': {'enabled': True, 'default_checked': False}},
                       {'result_double': None}, {'cells': []}):
            self.assertTrue(pc.wheel_config_errors(dict(good, **change), B), change)

    def test_offline(self):
        good = {'min_away_sec': 300, 'cap_sec': 7200, 'ad_multiplier': 2, 'min_payout': 1}
        self.assertEqual(pc.offline_errors(good), [])
        for change in ({'cap_sec': 43200}, {'min_away_sec': 60}, {'ad_multiplier': 3}, {'min_payout': 0}):
            self.assertTrue(pc.offline_errors(dict(good, **change)), change)

    def test_upgrade(self):
        self.assertEqual(pc.upgrade_costs(10), [30, 38, 48, 61, 77, 97, 123, 156, 198, 250])
        self.assertEqual(sum(pc.upgrade_costs(10)), 1078)
        for b in (1, 5, 10, 37, 50, 100):
            self.assertEqual(pc.upgrade_errors(pc.upgrade_costs(b), b), [], b)
        self.assertTrue(pc.upgrade_errors([500 * (k + 1) for k in range(10)], B))   # 17 极限滑雪-like, far too dear
        self.assertTrue(pc.upgrade_errors(pc.upgrade_costs(10)[:5], B))            # 5 levels
        self.assertTrue(pc.upgrade_errors(list(reversed(pc.upgrade_costs(10))), B))

    def test_quests(self):
        self.assertEqual(pc.quest_reward_errors([10, 10, 10], [[10, 20, 30, 40, 50]], B), [])
        self.assertTrue(pc.quest_reward_errors([300, 10, 10], [], B))             # 33 球球乐 300+ coins
        self.assertTrue(pc.quest_reward_errors([10] * 5, [], B))                  # 5B a day = a home gift
        self.assertTrue(pc.quest_reward_errors([], [[10, 20]], B))                # 2 tiers
        self.assertTrue(pc.quest_reward_errors([], [[10, 20, 3000]], B))          # 62 射击高手 3000
        self.assertTrue(pc.quest_reward_errors([], [[50, 40, 30]], B))            # goes down
        self.assertTrue(pc.quest_reward_errors([], [], B, achievement_gives_skin=True))

    def test_energy(self):
        good = {'original_has_energy': True, 'ad_refill': 3, 'skip_if_no_room': True}
        self.assertEqual(pc.energy_errors(good), [])
        for change in ({'original_has_energy': False}, {'ad_refill': 5}, {'skip_if_no_room': False}):
            self.assertTrue(pc.energy_errors(dict(good, **change)), change)

    def test_second_currency_ad_views(self):
        self.assertEqual([pc.second_currency_ad_views(x) for x in (0, 1, 5, 6, 20, 21)], [1, 1, 1, 2, 4, 5])
        with self.assertRaises(ValueError):
            pc.second_currency_ad_views(-1)


class V3PureFunctions(unittest.TestCase):
    """Patch v3 helpers: each has a passing value and at least one blocked value."""

    def test_checkin_days(self):
        full = {1: 10, 3: 20, 5: 30, 7: 60}
        self.assertEqual(pc.checkin_coin_errors(full, B), [])
        fallback = {**full, 2: 10, 4: 10, 6: 30, 7: 110}
        self.assertEqual(pc.checkin_coin_errors(fallback, B), [])   # every fallback taken
        for d, v in ((1, 20), (2, 20), (3, 10), (6, 10), (7, 100), (7, 50)):
            self.assertIn(d, pc.checkin_bad_days({**full, d: v}, B), (d, v))
        self.assertIn(1, pc.checkin_bad_days({3: 20, 5: 30, 7: 60}, B))            # a missing day 1 is 0
        # the game has no items / no skins: the fallback becomes compulsory
        self.assertEqual(set(pc.checkin_bad_days(full, B, has_items=False)), {2, 4})
        self.assertEqual(set(pc.checkin_bad_days(full, B, has_skins=False)), {6, 7})
        self.assertEqual(pc.checkin_bad_days(fallback, B, False, False), {})
        self.assertEqual(pc.checkin_bad_days({1: 10, 3: 20, 5: 30}, B, skip_days={7}), {})   # unread day 7 not judged
        # fractional B (72.5): 6B = 435 exact; 6B + 5B written as 435 + 363 = 798 is within 1 of 797.5
        self.assertEqual(pc.checkin_coin_errors({1: 73, 3: 145, 5: 218, 7: 798}, 72.5), [])
        self.assertTrue(pc.checkin_coin_errors({1: 73, 3: 145, 5: 218, 7: 436}, 72.5))

    def test_daily_cap(self):
        for n in (1, 2, 3):
            self.assertEqual(pc.daily_cap_errors(n, 3, 'x'), [])
        for n in (None, 0, 4, 50, 3.0, '3'):
            self.assertTrue(pc.daily_cap_errors(n, 3, 'x'), n)

    def test_chest(self):
        self.assertEqual(pc.chest_errors(20, B), [])
        self.assertEqual(pc.chest_errors(40, B, needs_ad=True, every_levels=5), [])
        self.assertTrue(pc.chest_errors(21, B))
        self.assertTrue(pc.chest_errors(41, B, needs_ad=True))
        self.assertTrue(pc.chest_errors(20, B, every_levels=10))
        self.assertEqual(pc.chest_errors(145, 72.5), [])     # 2B = 145
        self.assertTrue(pc.chest_errors(146, 72.5))

    def test_float_gift(self):
        self.assertEqual(pc.float_gift_errors(5, B, 5), [])
        self.assertEqual(pc.float_gift_errors(37, 72.5, 1), [])   # 0.5B = 36.25 -> up to 37
        for amt, cap in ((6, 5), (5, 6), (5, 0), (5, None), (38, 5)):
            self.assertTrue(pc.float_gift_errors(amt, 72.5 if amt > 10 else B, cap), (amt, cap))

    def test_bonus_level(self):
        self.assertEqual(pc.bonus_level_errors(30, B), [])
        self.assertEqual(pc.bonus_level_errors(60, B, needs_ad=True), [])
        self.assertTrue(pc.bonus_level_errors(50, B))
        self.assertTrue(pc.bonus_level_errors(30, B, needs_ad=True))

    def test_skin_trial(self):
        good = {'present': True, 'no_popup_levels': [1, 2], 'every_levels': 3, 'endless_every_rounds': 3}
        self.assertEqual(pc.skin_trial_errors(good, 'levels'), [])
        self.assertEqual(pc.skin_trial_errors(good, 'both'), [])
        self.assertEqual(pc.skin_trial_errors({'present': True, 'endless_every_rounds': 3}, 'endless'), [])
        self.assertEqual(pc.skin_trial_errors({'present': True}, 'idle'), [])
        for cfg, mode in ((None, 'levels'), (False, 'levels'), (dict(good, present=False), 'levels'),
                          (dict(good, no_popup_levels=[1]), 'levels'), (dict(good, no_popup_levels=[1, 2, 3]), 'levels'),
                          (dict(good, every_levels=5), 'levels'), (dict(good, endless_every_rounds=5), 'endless'),
                          (dict(good, endless_every_rounds=None), 'both')):
            self.assertTrue(pc.skin_trial_errors(cfg, mode), (cfg, mode))

    def test_exchange_discount(self):
        packs = [{'id': 'p1', 'price': 10, 'gives': 100}, {'id': 'p5', 'price': 45, 'gives': 500}]   # 10% better: ok
        self.assertEqual(pc.exchange_discount_errors(packs), [])
        self.assertEqual(pc.exchange_discount_errors(packs[:1]), [])
        bad = packs + [{'id': 'p10', 'price': 80, 'gives': 1000}]                                    # 20% better
        self.assertEqual(len(pc.exchange_discount_errors(bad)), 1)
        self.assertTrue(pc.exchange_discount_errors([{'id': 'x', 'price': 0, 'gives': 10}]))


class EconomyAudit(unittest.TestCase):
    def test_good_snapshot_passes(self):
        for kind in (None, 'english', 'finished'):
            r = pc.economy_audit(load('good.json'), kind)
            self.assertEqual(with_status(r, 'error', 'suggest', 'label', 'unknown'), set(), kind)
            self.assertTrue(r['ok'] or W1B_RULES, kind)
            self.assertEqual(r['schema'], pc.ECON_AUDIT_SCHEMA)
            self.assertEqual([x['id'] for x in r['results']], list(pc.ECON_RULE_TITLES))   # every rule, table order
            self.assertEqual((r['schema_warnings'], r['confirm_by_hand']), ([], []))
        self.assertEqual(status(pc.economy_audit(load('good.json')), 'ECON-PACING'), 'info')
        self.assertEqual(len(pc.ECON_RULE_TITLES), 36)

    def test_bad_snapshot_blocked_for_remake(self):
        # v3: bad.json = good.json + 5 faults (was: 3 faults on its own older base). Added ④ ad-boost check-in day 7 = 5B
        # and ⑤ 50 watch-ad coins a day. v3.1: Saul decided 3 a day, so ⑤ is an error too (was a capped suggest).
        r = pc.economy_audit(load('bad.json'))
        self.assertFalse(r['ok'])
        self.assertEqual(with_status(r, 'error'), {'ECON-SHORTCUT', 'ECON-ITEM', 'ECON-SECOND', 'ECON-CHECKIN', 'ECON-ADCOIN'})
        self.assertEqual(with_status(r, 'suggest'), set())
        self.assertNotIn('capped_by', row(r, 'ECON-ADCOIN'))

    def test_bad_snapshot_english_shortcut_and_added_checkin_are_errors(self):
        # v3: was {'ECON-SHORTCUT'} only; the check-in in bad.json is now added by ad-boost (systems_origin), so its
        # wrong day 7 is judged as remake (error) in an English game too.
        r = pc.economy_audit(load('bad.json'), 'english')
        self.assertFalse(r['ok'])
        self.assertEqual(with_status(r, 'error'), {'ECON-SHORTCUT', 'ECON-CHECKIN'})
        self.assertEqual(row(r, 'ECON-CHECKIN')['judged_as'], 'remake')
        for rule in ('ECON-ITEM', 'ECON-SECOND', 'ECON-ADCOIN'):
            self.assertEqual(status(r, rule), 'suggest', rule)

    def test_finished_game_only_labels(self):
        r = pc.economy_audit(load('bad.json'), 'finished')
        self.assertTrue(r['ok'])
        self.assertEqual(with_status(r, 'label'), {'ECON-SHORTCUT', 'ECON-ITEM', 'ECON-SECOND', 'ECON-CHECKIN', 'ECON-ADCOIN'})

    def test_each_single_fault_caught(self):
        def broken(edit):
            s = load('good.json'); edit(s); return with_status(pc.economy_audit(s), 'error')
        cases = {
            'ECON-B': lambda s: s['B'].update(value=None, how='unknown'),
            'ECON-LEVEL10': lambda s: inflow(s, 'level_clear').update(amount=15),
            'ECON-TIER': lambda s: sink(s, 'skin_r1').update(price=250),
            # v3: was ad_unlock_views=5, which is now the right count for a 10B skin (ceil(100 / 2B) = 5)
            'ECON-ADUNLOCK': lambda s: sink(s, 'skin_r2').update(ad_unlock_views=9),
            'ECON-SKINTRIAL': lambda s: s['systems']['skin_trial'].update(every_levels=5),
            'ECON-X2': lambda s: s['systems'].update(result_x2=False),
            'ECON-GIFT': lambda s: inflow(s, 'gift_home').update(x2='checkbox_default_on'),
            'ECON-ADCOIN': lambda s: inflow(s, 'ad_coins').update(amount=250),
            'ECON-SHOPFREE': lambda s: inflow(s, 'shop_free_coins').update(amount=60),
            'ECON-REVISIT': lambda s: inflow(s, 'revisit').update(amount=150),
            'ECON-CHECKIN': lambda s: inflow(s, 'checkin_d7').update(amount=100),
            'ECON-CLAIMX2': lambda s: inflow(s, 'checkin_d1').update(x2='checkbox_default_off'),
            'ECON-CHEST': lambda s: inflow(s, 'chest_5').update(amount=30),
            'ECON-FLOAT': lambda s: inflow(s, 'float_gift').update(per_round_max=8),
            'ECON-BONUS': lambda s: inflow(s, 'bonus_level').update(amount=50),
            'ECON-PACK': lambda s: sink(s, 'hint_3').update(price=60),
            'ECON-ADITEM': lambda s: inflow(s, 'hint_ad').update(amount=2),
            'ECON-WHEEL': lambda s: inflow(s, 'wheel_big').update(amount=80),
            'ECON-OFFLINE': lambda s: s['configs']['offline'].update(cap_sec=28800),
            'ECON-UPGRADE': lambda s: s['configs'].update(upgrade_lines=[[500, 1000, 2000]]),
            'ECON-QUEST': lambda s: s['configs']['quests'].update(achievement_gives_skin=True),
            'ECON-ENERGY': lambda s: s['configs']['energy'].update(ad_refill=5),
            'ECON-DEAD': lambda s: (s['currencies'].append({'id': 'pearls', 'role': 'second', 'label': 'Pearls', 'evidence': 'x:1'})),
        }
        for rule, edit in cases.items():
            if rule in W1B_RULES:
                continue
            self.assertIn(rule, broken(edit), rule)
        self.assertEqual(broken(lambda s: None), set())

    def test_snapshot_lacking_data_is_unknown_not_guessed(self):
        s = load('good.json')
        s['inflows'] = [x for x in s['inflows'] if x['rule'] != 'ECON-SHORTCUT']
        r = pc.economy_audit(s)
        self.assertEqual(status(r, 'ECON-SHORTCUT'), 'unknown')
        s['systems']['shortcut'] = False
        self.assertEqual(status(pc.economy_audit(s, 'english'), 'ECON-SHORTCUT'), 'error')
        r = pc.economy_audit({'schema': 'economy_snapshot.v1', 'B': {'value': None, 'how': 'unknown'}}, 'remake')
        self.assertEqual(status(r, 'ECON-B'), 'error')
        self.assertTrue(all(x['status'] == 'unknown' for x in r['results'] if x['id'] != 'ECON-B'))
        self.assertEqual(len(r['results']), 36)

    def test_idle_game_skips_fixed_upgrade_line(self):
        s = load('good.json'); s['game']['mode'] = 'idle'; s['configs']['upgrade_lines'] = [[10, 100, 1000]]
        self.assertEqual(status(pc.economy_audit(s), 'ECON-UPGRADE'), 'skip')

    def test_wrong_schema_fails(self):
        s = load('good.json'); s['schema'] = 'economy_snapshot.v0'
        r = pc.economy_audit(s)
        self.assertFalse(r['ok']); self.assertTrue(r['schema_errors'])

    def test_cli_exit_codes(self):
        script = str(HERE / 'product_contract.py')
        def run(*args):
            return subprocess.run([sys.executable, script, 'economy-audit', *args], capture_output=True, text=True)
        good = run('--snapshot', str(SAMPLES / 'good.json'))
        self.assertEqual(good.returncode, 0 if W1B_READY else good.returncode, good.stderr)
        self.assertEqual(json.loads(good.stdout)['schema'], pc.ECON_AUDIT_SCHEMA)
        self.assertEqual(run('--snapshot', str(SAMPLES / 'bad.json')).returncode, 1)
        english = run('--snapshot', str(SAMPLES / 'bad.json'), '--kind', 'english')
        self.assertEqual(english.returncode, 1)
        self.assertEqual(with_status(json.loads(english.stdout), 'error'), {'ECON-SHORTCUT', 'ECON-CHECKIN'})   # v3, see above


class CheckinV3(unittest.TestCase):
    """Saul 2026-10-31: no item -> 1B on days 2/4, no skin -> 3B on day 6 and 6B + 5B on day 7; rows of one day add up."""

    def snap(self, **days):
        s = load('good.json')
        s['inflows'] = [x for x in s['inflows'] if x['rule'] != 'ECON-CHECKIN']
        for d, amounts in days.items():
            for i, a in enumerate(amounts if isinstance(amounts, list) else [amounts]):
                s['inflows'].append({'id': 'ck_%s_%d' % (d, i), 'rule': 'ECON-CHECKIN', 'day': int(d[1:]), 'currency': 'coins',
                                     'amount': a, 'per': 'claim', 'needs_ad': False, 'x2': 'checkbox_default_on', 'count_per_day': 1})
        return s

    def st(self, s, kind=None):
        return status(pc.economy_audit(s, kind), 'ECON-CHECKIN')

    def test_day7_six_plus_five_in_two_rows_passes(self):
        # before v3 the second row of day 7 replaced the first (50 -> error) and 11B was not accepted at all
        self.assertEqual(self.st(self.snap(d1=10, d3=20, d5=30, d7=[60, 50])), 'pass')
        self.assertEqual(self.st(self.snap(d1=10, d3=20, d5=30, d6=30, d7=110)), 'pass')

    def test_wrong_sums_blocked(self):
        self.assertEqual(self.st(self.snap(d1=10, d3=20, d5=30, d7=[60, 40])), 'error')     # 10B
        self.assertEqual(self.st(self.snap(d1=10, d3=20, d5=30, d7=[30, 30, 30])), 'error')  # 9B
        self.assertEqual(self.st(self.snap(d1=[5, 5], d3=20, d5=30, d7=60)), 'pass')         # 1B in two rows

    def test_fallback_compulsory_without_items_or_skins(self):
        s = self.snap(d1=10, d3=20, d5=30, d7=60)
        s['systems'].update(skins=False)
        s['sinks'] = [x for x in s['sinks'] if x['kind'] != 'skin']
        self.assertEqual(self.st(s), 'error')                                             # day 6 0 and day 7 6B, no skin
        s2 = self.snap(d1=10, d3=20, d5=30, d6=30, d7=[60, 50])
        s2['systems'].update(skins=False); s2['sinks'] = s['sinks']
        self.assertEqual(self.st(s2), 'pass')
        s3 = self.snap(d1=10, d3=20, d5=30, d7=60)
        s3['systems'].update(items=False); s3['sinks'] = [x for x in s3['sinks'] if x['kind'] != 'item']
        self.assertEqual(self.st(s3), 'error')                                            # days 2/4 give nothing
        s3['inflows'] += [dict(inflow(s3, 'ck_d1_0'), id='ck2', day=2), dict(inflow(s3, 'ck_d1_0'), id='ck4', day=4)]
        self.assertEqual(self.st(s3), 'pass')

    def test_by_day_rows_read(self):
        s = self.snap()
        s['inflows'].append({'id': 'checkin', 'rule': 'ECON-CHECKIN', 'currency': 'coins', 'amount': None, 'per': 'day',
                             'by_day': {'1': 10, '2': 10, '3': 20, '4': 10, '5': 30, '6': 30, '7': 110}, 'x2': 'checkbox_default_on'})
        self.assertEqual(self.st(s), 'pass')
        s['inflows'][-1]['by_day']['7'] = 70
        self.assertEqual(self.st(s), 'error')
        s['inflows'][-1]['by_day']['7'] = None
        r = pc.economy_audit(s)
        self.assertEqual(status(r, 'ECON-CHECKIN'), 'unknown')
        self.assertIn('day 7', row(r, 'ECON-CHECKIN')['details'][0])

    def test_fractional_b_sum(self):
        s = self.snap(d1=73, d3=145, d5=218, d7=[435, 363])
        s['B']['value'] = 72.5
        r = pc.economy_audit(s)
        self.assertEqual(status(r, 'ECON-CHECKIN'), 'pass', row(r, 'ECON-CHECKIN'))


class OriginV3(unittest.TestCase):
    """English games: a miss on a row (or system) we added (origin ad-boost / new) is judged as remake."""

    def wheel_bad(self, origin=None, sys_origin=None):
        s = load('good.json')
        if origin:
            for x in s['inflows']:
                if x['rule'] == 'ECON-WHEEL':
                    x['origin'] = origin
        if sys_origin:
            s['systems_origin'] = sys_origin
        inflow(s, 'wheel_big').update(amount=80)
        return pc.economy_audit(s, 'english')

    def test_rows_added_by_us_are_errors(self):
        self.assertEqual(status(self.wheel_bad(), 'ECON-WHEEL'), 'suggest')
        for origin in ('ad-boost', 'new'):
            r = self.wheel_bad(origin)
            self.assertEqual(status(r, 'ECON-WHEEL'), 'error', origin)
            self.assertEqual(row(r, 'ECON-WHEEL')['judged_as'], 'remake')
            self.assertFalse(r['ok'])
        self.assertEqual(status(self.wheel_bad('original'), 'ECON-WHEEL'), 'suggest')

    def test_systems_origin_and_aliases(self):
        self.assertEqual(status(self.wheel_bad(sys_origin={'wheel': 'ad-boost'}), 'ECON-WHEEL'), 'error')
        s = load('good.json'); inflow(s, 'ad_coins').update(amount=30); s['systems_origin'] = {'coin-ad': 'ad-boost'}
        self.assertEqual(status(pc.economy_audit(s, 'english'), 'ECON-ADCOIN'), 'error')
        s['systems_origin'] = {}
        self.assertEqual(status(pc.economy_audit(s, 'english'), 'ECON-ADCOIN'), 'suggest')

    def test_only_offending_rows_count(self):
        # an ad-boost row that is right does not drag an original row's miss up to error
        s = load('good.json')
        inflow(s, 'wheel_free')['origin'] = 'ad-boost'
        inflow(s, 'gift_home').update(amount=30, origin='original')
        s['systems_origin'] = {}
        r = pc.economy_audit(s, 'english')
        self.assertEqual(status(r, 'ECON-GIFT'), 'suggest')
        inflow(s, 'gift_home')['origin'] = 'new'
        self.assertEqual(status(pc.economy_audit(s, 'english'), 'ECON-GIFT'), 'error')

    def test_remake_and_finished_unchanged(self):
        s = load('good.json'); inflow(s, 'wheel_big').update(amount=80, origin='ad-boost')
        self.assertEqual(status(pc.economy_audit(s, 'remake'), 'ECON-WHEEL'), 'error')
        self.assertEqual(status(pc.economy_audit(s, 'finished'), 'ECON-WHEEL'), 'label')


class DecidedCapsV31(unittest.TestCase):
    """v3.1 (Saul 2026-11-01 「默认数值就这样」): ADCOIN 3 a day with no cooldown and SHOPFREE 3 a slot a day are decided, so
    a miss is an error for remake games (v3 capped them at suggest). An auto scan that did not read count_per_day: unknown."""

    def test_ad_coin_daily_cap(self):
        s = load('good.json')
        for n in (50, None, 0):
            inflow(s, 'ad_coins')['count_per_day'] = n
            r = pc.economy_audit(s, 'remake')
            self.assertEqual(status(r, 'ECON-ADCOIN'), 'error', n)
            self.assertFalse(r['ok'], n)
            self.assertNotIn('capped_by', row(r, 'ECON-ADCOIN'))
            self.assertEqual(status(pc.economy_audit(s, 'english'), 'ECON-ADCOIN'), 'suggest', n)   # the original game's own
            self.assertEqual(status(pc.economy_audit(s, 'finished'), 'ECON-ADCOIN'), 'label', n)
        inflow(s, 'ad_coins').update(count_per_day=50, amount=250)       # both messages kept
        r = pc.economy_audit(s)
        self.assertEqual(status(r, 'ECON-ADCOIN'), 'error')
        self.assertEqual(len(row(r, 'ECON-ADCOIN')['details']), 2)

    def test_ad_coin_no_cooldown(self):
        s = load('good.json'); inflow(s, 'ad_coins')['cooldown_sec'] = 600
        r = pc.economy_audit(s)
        self.assertEqual(status(r, 'ECON-ADCOIN'), 'error')
        self.assertTrue(any('cooldown' in d for d in row(r, 'ECON-ADCOIN')['details']))
        self.assertEqual(r['schema_warnings'], [])
        inflow(s, 'ad_coins')['cooldown_sec'] = 0
        self.assertEqual(status(pc.economy_audit(s), 'ECON-ADCOIN'), 'pass')

    def test_auto_scan_unread_cap_is_unknown(self):
        s = load('good.json'); s.setdefault('meta', {})['source'] = 'auto_scan'
        inflow(s, 'ad_coins')['count_per_day'] = None
        inflow(s, 'shop_free_hint')['count_per_day'] = None
        r = pc.economy_audit(s)
        self.assertEqual((status(r, 'ECON-ADCOIN'), status(r, 'ECON-SHOPFREE')), ('unknown', 'unknown'))
        inflow(s, 'ad_coins')['count_per_day'] = 4                         # read and wrong: still an error
        self.assertEqual(status(pc.economy_audit(s), 'ECON-ADCOIN'), 'error')

    def test_ad_coin_not_doubled(self):
        s = load('good.json'); inflow(s, 'ad_coins')['x2'] = 'checkbox_default_on'
        self.assertEqual(status(pc.economy_audit(s), 'ECON-ADCOIN'), 'error')

    def test_shop_free(self):
        s = load('good.json')
        inflow(s, 'shop_free_hint')['count_per_day'] = 5
        self.assertEqual(status(pc.economy_audit(s), 'ECON-SHOPFREE'), 'error')
        self.assertEqual(status(pc.economy_audit(s, 'english'), 'ECON-SHOPFREE'), 'error')   # added by ad-boost (origin)
        inflow(s, 'shop_free_hint').update(count_per_day=3, amount=2)                  # 1 item a claim is decided
        self.assertEqual(status(pc.economy_audit(s), 'ECON-SHOPFREE'), 'error')
        inflow(s, 'shop_free_hint').update(amount=1, x2='checkbox_default_on')         # already an ad reward: no x2
        self.assertEqual(status(pc.economy_audit(s), 'ECON-SHOPFREE'), 'error')
        s2 = load('good.json'); s2['inflows'] = [x for x in s2['inflows'] if x['rule'] != 'ECON-SHOPFREE']
        self.assertEqual(status(pc.economy_audit(s2), 'ECON-SHOPFREE'), 'unknown')   # systems.shop_free true, no rows
        s2['systems']['shop_free'] = False
        self.assertEqual(status(pc.economy_audit(s2), 'ECON-SHOPFREE'), 'skip')


class SkinTrialV3(unittest.TestCase):
    def st(self, s, kind=None):
        return status(pc.economy_audit(s, kind), 'ECON-SKINTRIAL')

    def test_required_with_skins(self):
        s = load('good.json')
        self.assertEqual(self.st(s), 'pass')
        del s['systems']['skin_trial']
        self.assertEqual(self.st(s), 'unknown')
        s['systems']['skin_trial'] = {'present': False}
        self.assertEqual(self.st(s), 'error')
        self.assertEqual(self.st(s, 'english'), 'suggest')
        s['systems_origin'] = {'skin-ad': 'ad-boost'}
        self.assertEqual(self.st(s, 'english'), 'error')

    def test_schedule(self):
        for change in ({'no_popup_levels': [1]}, {'no_popup_levels': []}, {'every_levels': 2}, {'every_levels': None}):
            s = load('good.json'); s['systems']['skin_trial'].update(change)
            self.assertEqual(self.st(s), 'error', change)
        s = load('good.json'); s['game']['mode'] = 'endless'; s['systems']['skin_trial'] = {'present': True, 'endless_every_rounds': 3}
        self.assertEqual(self.st(s), 'pass')
        s['systems']['skin_trial']['endless_every_rounds'] = 5
        self.assertEqual(self.st(s), 'error')

    def test_no_skins_skip(self):
        s = load('good.json'); s['systems']['skins'] = False; s['sinks'] = [x for x in s['sinks'] if x['kind'] != 'skin']
        del s['systems']['skin_trial']
        self.assertEqual(self.st(s), 'skip')


class ClaimWindowsV3(unittest.TestCase):
    """Saul 2026-11-01: every claim window that can be doubled has the default-checked double checkbox."""

    def errs(self, s):
        return with_status(pc.economy_audit(s), 'error')

    def test_each_window(self):
        cases = {
            'chest': lambda s: inflow(s, 'chest_5').update(x2='none'),
            'float_gift': lambda s: inflow(s, 'float_gift').update(x2='checkbox_default_off'),
            'quest_claim': lambda s: inflow(s, 'daily_2').update(x2='none'),
            'bonus_level': lambda s: inflow(s, 'bonus_level').update(x2='none'),
            'wheel_result': lambda s: inflow(s, 'wheel_ad').update(x2='ad_button'),   # ad_button only for offline / bonus level
            'offline': lambda s: s['configs']['offline'].update(x2='checkbox_default_off'),
            'gift_window': lambda s: (s['systems'].update(gift_window=True),
                                      s['inflows'].append({'id': 'gift_window_1', 'currency': 'coins', 'amount': 20, 'x2': 'none'})),
        }
        for w, edit in cases.items():
            s = load('good.json'); edit(s)
            r = pc.economy_audit(s)
            self.assertIn('ECON-CLAIMX2', self.errs(s), w)
            self.assertTrue(any(d.startswith(w) for d in row(r, 'ECON-CLAIMX2')['details']), (w, row(r, 'ECON-CLAIMX2')))

    def test_accepted_marks_and_window_inference(self):
        s = load('good.json')
        inflow(s, 'bonus_level')['x2'] = 'checkbox_default_on'          # both marks accepted on a bonus level
        s['inflows'].append({'id': 'bonus_ad', 'rule': 'ECON-BONUS', 'currency': 'coins', 'amount': 60, 'needs_ad': True, 'x2': 'none'})
        self.assertNotIn('ECON-CLAIMX2', self.errs(s))                     # the needs_ad row is the ad button
        for x in s['inflows']:
            x.pop('window', None)                                          # window from the rule
        self.assertEqual(self.errs(s) - W1B_RULES, set())
        inflow(s, 'chest_5')['x2'] = 'none'
        self.assertIn('ECON-CLAIMX2', self.errs(s))

    def test_excluded_windows_not_checked(self):
        s = load('good.json')
        inflow(s, 'energy_ad')['x2'] = 'checkbox_default_on'               # excluded: not a CLAIMX2 matter
        inflow(s, 'hint_ad')['x2'] = 'checkbox_default_off'
        self.assertNotIn('ECON-CLAIMX2', self.errs(s))
        s2 = load('good.json')
        inflow(s2, 'daily_1')['window'] = 'ad_coin'                         # explicit window wins over the rule
        inflow(s2, 'daily_1')['x2'] = 'none'
        self.assertNotIn('ECON-CLAIMX2', self.errs(s2))

    def test_quest_claim_from_config(self):
        s = load('good.json')
        s['inflows'] = [x for x in s['inflows'] if x['rule'] != 'ECON-QUEST']
        self.assertNotIn('ECON-CLAIMX2', self.errs(s))
        s['configs']['quests']['claim_double'] = {'enabled': True, 'default_checked': False}
        self.assertIn('ECON-CLAIMX2', self.errs(s))
        del s['configs']['quests']['claim_double']
        self.assertEqual(status(pc.economy_audit(s), 'ECON-CLAIMX2'), 'unknown')   # quests on, double not found


class EnglishClaimWindowsV3(unittest.TestCase):
    """Lead 2026-11-01 (round 2): English games - the original check-in / wheel result / gift window and every window we
    added need the default-on double (error); the original game's other windows only get a suggestion. Remake: all error."""

    def original(self):
        s = load('good.json')
        s['systems_origin'] = {}
        for x in s['inflows']:
            x.pop('origin', None)
        return s

    def claim(self, s, kind='english'):
        return row(pc.economy_audit(s, kind), 'ECON-CLAIMX2')

    def test_original_other_windows_only_suggest(self):
        edits = {'quest_claim': lambda s: inflow(s, 'daily_1').update(x2='none'),
                 'offline': lambda s: s['configs']['offline'].update(x2='checkbox_default_off'),
                 'chest': lambda s: inflow(s, 'chest_5').update(x2='none'),
                 'bonus_level': lambda s: inflow(s, 'bonus_level').update(x2='none'),
                 'float_gift': lambda s: inflow(s, 'float_gift').update(x2='checkbox_default_off')}
        for w, edit in edits.items():
            s = self.original(); edit(s)
            r = self.claim(s)
            self.assertEqual((r['status'], r.get('english_optional')), ('suggest', True), w)
            self.assertTrue(pc.economy_audit(s, 'english')['ok'] or W1B_RULES, w)
            self.assertEqual(self.claim(s, 'remake')['status'], 'error', w)       # remake unchanged
            self.assertEqual(self.claim(s, 'finished')['status'], 'label', w)

    def test_original_required_windows_are_errors(self):
        edits = {'checkin': lambda s: inflow(s, 'checkin_d1').update(x2='checkbox_default_off'),
                 'wheel_result': lambda s: inflow(s, 'wheel_free').update(x2='none'),
                 'gift_window': lambda s: (s['systems'].update(gift_window=True),
                                           s['inflows'].append({'id': 'gift_window_1', 'currency': 'coins', 'amount': 20, 'x2': 'none'}))}
        for w, edit in edits.items():
            s = self.original(); edit(s)
            self.assertEqual(self.claim(s)['status'], 'error', w)
            self.assertFalse(pc.economy_audit(s, 'english')['ok'], w)

    def test_windows_added_by_us_are_errors(self):
        s = self.original(); inflow(s, 'chest_5').update(x2='none', origin='ad-boost')
        self.assertEqual(self.claim(s)['status'], 'error')
        s = self.original(); inflow(s, 'daily_1').update(x2='none', origin='new')
        self.assertEqual(self.claim(s)['status'], 'error')
        s = self.original(); inflow(s, 'daily_1')['x2'] = 'none'; s['systems_origin'] = {'quest-x2': 'ad-boost'}
        self.assertEqual(self.claim(s)['status'], 'error')
        s = self.original(); s['configs']['offline']['x2'] = 'checkbox_default_off'; s['systems_origin'] = {'offline': 'new'}
        self.assertEqual(self.claim(s)['status'], 'error')
        s = load('good.json'); inflow(s, 'bonus_level')['x2'] = 'none'          # good.json: bonus level added by ad-boost
        self.assertEqual(self.claim(s)['status'], 'error')

    def test_mixed_keeps_both_messages(self):
        s = self.original()
        inflow(s, 'daily_1')['x2'] = 'none'
        inflow(s, 'checkin_d1')['x2'] = 'checkbox_default_off'
        r = self.claim(s)
        self.assertEqual(r['status'], 'error')
        self.assertTrue(any(d.startswith('checkin') for d in r['details']) and any(d.startswith('quest_claim') for d in r['details']), r)


class Saul1101RoundTwo(unittest.TestCase):
    """Saul 2026-11-01 (round 2): timer chest on the level map, endless skin trial = 30 minutes after an ad and never
    doubled, no unlimited energy."""

    def st(self, s, rule, kind=None):
        return status(pc.economy_audit(s, kind), rule)

    def test_timer_chest(self):
        s = load('good.json')
        self.assertEqual(self.st(s, 'ECON-TIMERCHEST'), 'pass')
        inflow(s, 'timer_chest')['amount'] = 60                         # 6B > 5B, decided in v3.1 (was a capped suggest)
        for kind, want in (('remake', 'error'), ('english', 'error'), ('finished', 'label')):   # english: added by ad-boost
            r = pc.economy_audit(s, kind)
            self.assertEqual(status(r, 'ECON-TIMERCHEST'), want, kind)
            self.assertEqual(r['ok'], kind == 'finished', kind)
        self.assertNotIn('capped_by', row(pc.economy_audit(s), 'ECON-TIMERCHEST'))
        self.assertFalse(any('placeholder' in d for d in row(pc.economy_audit(s), 'ECON-TIMERCHEST')['details']))
        s = load('good.json'); inflow(s, 'timer_chest')['placement'] = 'home'   # placement is decided: not on home
        self.assertEqual(self.st(s, 'ECON-TIMERCHEST'), 'error')
        s = load('good.json'); inflow(s, 'timer_chest')['x2'] = 'none'           # claim double -> ECON-CLAIMX2
        self.assertEqual(self.st(s, 'ECON-CLAIMX2'), 'error')
        self.assertEqual(self.st(s, 'ECON-CLAIMX2', 'english'), 'error')     # added by ad-boost (systems_origin timer-chest)
        s['systems_origin'] = {}; inflow(s, 'timer_chest').pop('origin')
        self.assertEqual(self.st(s, 'ECON-CLAIMX2', 'english'), 'suggest')   # an original game's own timer chest: suggest
        s = load('good.json'); s['inflows'] = [x for x in s['inflows'] if x['id'] != 'timer_chest']
        self.assertEqual(self.st(s, 'ECON-TIMERCHEST'), 'unknown')          # systems.timer_chest true, no rows
        s['systems']['timer_chest'] = False
        self.assertEqual(self.st(s, 'ECON-TIMERCHEST'), 'skip')
        s = load('good.json'); inflow(s, 'timer_chest')['amount'] = 363; s['B']['value'] = 72.5   # 5B = 362.5 -> up to 363
        self.assertEqual(self.st(s, 'ECON-TIMERCHEST'), 'pass')

    def test_timer_chest_wait_times(self):
        # v3.2 (same as economy_plan.js「v3.2 倒计时宝箱等待时间」): written wait times must be the decided 1200 / 300 / 2 / 4,
        # and the ads must cut less than the wait
        def tc(sys_=None, **row_):
            s = load('good.json')
            if sys_ is not None:
                s['systems']['timer_chest'] = dict({'placement': 'level_map'}, **sys_)
            inflow(s, 'timer_chest').update(row_)
            return s
        r = pc.economy_audit(tc({'wait_sec': 1200, 'ad_cut_sec': 300, 'ad_cuts_per_round': 2, 'rounds_per_day': 4}))
        self.assertEqual(status(r, 'ECON-TIMERCHEST'), 'pass')
        self.assertTrue(any('as decided' in d for d in row(r, 'ECON-TIMERCHEST')['details']))
        r = pc.economy_audit(tc({'wait_sec': 600, 'ad_cut_sec': 300, 'ad_cuts_per_round': 2, 'rounds_per_day': 4}))
        d = row(r, 'ECON-TIMERCHEST')['details']
        self.assertEqual(status(r, 'ECON-TIMERCHEST'), 'error')
        self.assertTrue(any('wait_sec is 600' in x for x in d) and any('open it directly' in x for x in d), d)
        r = pc.economy_audit(tc({'ad_cuts_per_round': 4}))
        self.assertTrue(any('300 x 4 = 1200' in x for x in row(r, 'ECON-TIMERCHEST')['details']), row(r, 'ECON-TIMERCHEST'))
        r = pc.economy_audit(tc({}))                                          # not written: pass, confirm by hand
        self.assertEqual(status(r, 'ECON-TIMERCHEST'), 'pass')
        self.assertTrue(any('not written' in x for x in row(r, 'ECON-TIMERCHEST')['details']))
        r = pc.economy_audit(tc(None, wait_sec=900))                          # written on the row
        self.assertEqual((status(r, 'ECON-TIMERCHEST'), r['schema_warnings']), ('error', []))
        self.assertEqual(self.st(tc(None, wait_sec=900), 'ECON-TIMERCHEST', 'english'), 'error')   # added by ad-boost
        self.assertEqual(self.st(tc({'placement': 'home'}), 'ECON-TIMERCHEST'), 'error')

    def endless(self, **trial):
        s = load('good.json'); s['game']['mode'] = 'endless'
        s['systems']['skin_trial'] = dict({'present': True, 'endless_every_rounds': 3, 'endless_no_popup_rounds': [1, 2],
                                           'trial': 'ad_minutes', 'trial_minutes': 30, 'claim_double': False}, **trial)
        return s

    def test_endless_skin_trial_30_minutes(self):
        self.assertEqual(self.st(self.endless(), 'ECON-SKINTRIAL'), 'pass')
        self.assertEqual(self.st(self.endless(trial_minutes=None), 'ECON-SKINTRIAL'), 'pass')   # not written: not judged
        for change in ({'trial_minutes': 15}, {'trial': 'one_round'}, {'trial': 'one_level'}, {'endless_no_popup_rounds': [1]},
                       {'claim_double': True}, {'claim_double': 'checkbox_default_on'}):
            self.assertEqual(self.st(self.endless(**change), 'ECON-SKINTRIAL'), 'error', change)

    def test_level_trial_one_level_never_doubled(self):
        s = load('good.json')
        for change in ({'trial': 'ad_minutes'}, {'trial': 'one_round'}, {'claim_double': True}):
            s2 = copy.deepcopy(s); s2['systems']['skin_trial'].update(change)
            self.assertEqual(self.st(s2, 'ECON-SKINTRIAL'), 'error', change)
        s['game']['mode'] = 'both'; s['systems']['skin_trial'].update(trial='ad_minutes', trial_minutes=30)
        self.assertEqual(self.st(s, 'ECON-SKINTRIAL'), 'pass')

    def test_no_unlimited_energy(self):
        self.assertEqual(self.st(load('good.json'), 'ECON-ENERGY'), 'pass')
        for row_ in ({'id': 'unl', 'currency': 'energy', 'amount': 'unlimited', 'per': 'ad', 'needs_ad': True},
                     {'id': 'unl', 'rule': 'ECON-ENERGY', 'amount': 0, 'unlimited_minutes': 15, 'needs_ad': True},
                     {'id': 'unl', 'window': 'energy_ad', 'currency': 'energy', 'amount': 'Infinite 15 min'}):
            s = load('good.json'); s['inflows'].append(dict(row_))
            r = pc.economy_audit(s)
            self.assertEqual(status(r, 'ECON-ENERGY'), 'error', row_)
            self.assertTrue(any('unlimited' in d for d in row(r, 'ECON-ENERGY')['details']), row_)
            self.assertEqual(r['schema_warnings'], [])
        s = load('good.json'); s['configs']['energy']['unlimited_minutes'] = 15
        self.assertEqual(self.st(s, 'ECON-ENERGY'), 'error')
        s = load('good.json'); del s['configs']['energy']; s['systems']['energy'] = False   # no energy system, still caught
        s['inflows'].append({'id': 'unl', 'currency': 'energy', 'amount': 'unlimited'})
        self.assertEqual(self.st(s, 'ECON-ENERGY'), 'error')
        s = load('good.json'); s['inflows'].append({'id': 'unl', 'currency': 'energy', 'amount': 'unlimited', 'origin': 'ad-boost'})
        self.assertEqual(self.st(s, 'ECON-ENERGY', 'english'), 'error')     # added by us in an English game


class Saul1101V31(unittest.TestCase):
    """Rules table v3.1 (Saul 2026-11-01): online-time gift 1B..3B a tier and <= 10B a day; key chest cells <= 5B and a
    nine-cell board about 15B; 「皮肤的解锁条件只能有一种，不可以既让金币购买又让看广告获取」."""

    def st(self, s, rule, kind=None):
        return status(pc.economy_audit(s, kind), rule)

    def online(self, amounts, **extra):
        s = load('good.json'); s['systems']['online_gift'] = True
        s['inflows'] += [dict({'id': 'online_%d' % m, 'rule': 'ECON-ONLINE', 'currency': 'coins', 'amount': a, 'per': 'day',
                               'x2': 'checkbox_default_on', 'origin': 'ad-boost'}, **extra) for m, a in zip(pc.ONLINE_TIERS_MIN, amounts)]
        return s

    def key_chest(self, amounts, x2='checkbox_default_on'):
        s = load('good.json'); s['systems']['key_chest'] = True
        s['inflows'] += [{'id': 'key_cell_%d' % i, 'rule': 'ECON-KEYCHEST', 'currency': 'coins', 'amount': a, 'x2': x2,
                          'origin': 'ad-boost'} for i, a in enumerate(amounts)]
        return s

    def test_claim_double_online_and_key_chest(self):
        # v3.2: ECON-CLAIMX2 checks the online-time gift and the key chest's summary window (default-on double)
        cells = [50, 30, 20, 10, 10, 10, 10, 5, 5]
        for s in (self.online([10, 10, 20, 30, 30]), self.key_chest(cells)):
            self.assertEqual(self.st(s, 'ECON-CLAIMX2'), 'pass')
        for s, w in ((self.online([10, 10, 20, 30, 30], x2='none'), 'online_gift'), (self.key_chest(cells, 'none'), 'key_chest')):
            r = pc.economy_audit(s)
            self.assertEqual(status(r, 'ECON-CLAIMX2'), 'error', w)
            self.assertTrue(any(d.startswith(w) for d in row(r, 'ECON-CLAIMX2')['details']), (w, row(r, 'ECON-CLAIMX2')))
            self.assertEqual(status(pc.economy_audit(s, 'english'), 'ECON-CLAIMX2'), 'error', w)   # added by ad-boost
        s = self.key_chest(cells)                                   # a cell opened with the +3 KEYS of an ad: never doubled
        s['inflows'].append({'id': 'key_ad_open', 'rule': 'ECON-CLAIMX2', 'window': 'key_chest_ad_keys', 'currency': 'coins',
                             'amount': 10, 'needs_ad': True, 'x2': 'none', 'origin': 'ad-boost'})
        r = pc.economy_audit(s)
        self.assertEqual((status(r, 'ECON-CLAIMX2'), status(r, 'ECON-KEYCHEST'), r['schema_warnings']), ('pass', 'pass', []))

    def test_online_gift(self):
        self.assertEqual(self.st(load('good.json'), 'ECON-ONLINE'), 'skip')
        r = pc.economy_audit(self.online([10, 10, 20, 30, 30]))               # 1/1/2/3/3B = 10B a day
        self.assertEqual(status(r, 'ECON-ONLINE'), 'pass')
        self.assertEqual(r['schema_warnings'], [])
        for amounts in ([10, 20, 30, 30, 30], [5, 10, 10, 10, 10], [40, 10, 10, 10, 10]):   # 12B a day, a 0.5B tier, a 4B tier
            self.assertEqual(self.st(self.online(amounts), 'ECON-ONLINE'), 'error', amounts)
        self.assertEqual(self.st(self.online([40, 10, 10, 10, 10]), 'ECON-ONLINE', 'english'), 'error')     # added by ad-boost
        self.assertEqual(self.st(self.online([40, 10, 10, 10, 10], origin='original'), 'ECON-ONLINE', 'english'), 'suggest')
        s = self.online([72, 72, 145, 217, 217]); s['B']['value'] = 72.5       # rounded down, 723 <= 10B = 725
        self.assertEqual(self.st(s, 'ECON-ONLINE'), 'pass')
        s = self.online([10, 10, 20, 30, 30], window='online_gift')
        for x in s['inflows']:
            if x['id'].startswith('online_'):
                del x['rule']
        r = pc.economy_audit(s)
        self.assertEqual((status(r, 'ECON-ONLINE'), r['schema_warnings']), ('pass', []))   # read by window as well
        s = load('good.json'); s['systems']['online_gift'] = True
        self.assertEqual(self.st(s, 'ECON-ONLINE'), 'unknown')

    def test_key_chest(self):
        cells = [50, 30, 20, 10, 10, 10, 10, 5, 5]                              # ad-boost default 5/3/2/1/1/1/1/0.5/0.5B = 15B
        self.assertEqual(self.st(load('good.json'), 'ECON-KEYCHEST'), 'skip')
        self.assertEqual(self.st(self.key_chest(cells), 'ECON-KEYCHEST'), 'pass')
        self.assertEqual(self.st(self.key_chest([60] + cells[1:]), 'ECON-KEYCHEST'), 'error')        # a 6B cell
        self.assertEqual(self.st(self.key_chest([50] * 9), 'ECON-KEYCHEST'), 'error')                # 45B board
        self.assertEqual(self.st(self.key_chest(cells[:7] + [30, 30]), 'ECON-KEYCHEST'), 'error')    # 20B board
        self.assertEqual(self.st(self.key_chest(cells[:8] + [10]), 'ECON-KEYCHEST'), 'pass')         # 15.5B: rounding of a cell
        self.assertEqual(self.st(self.key_chest(cells[:8]), 'ECON-KEYCHEST'), 'pass')                # not 9 coin cells: total not judged
        s = self.key_chest([363, 218, 145, 73, 72, 72, 73, 36, 37]); s['B']['value'] = 72.5        # 1089 vs 15B = 1087.5
        self.assertEqual(self.st(s, 'ECON-KEYCHEST'), 'pass')
        s = load('good.json'); s['systems']['key_chest'] = True
        self.assertEqual(self.st(s, 'ECON-KEYCHEST'), 'unknown')

    @unittest.skipUnless(W1B_READY, 'W1b names not in product_contract.py yet')
    def test_one_unlock_method_per_skin(self):
        s = load('good.json')
        self.assertEqual(self.st(s, 'ECON-ADUNLOCK'), 'pass')
        for mode, want in (('ads', 'pass'), ('Ad', 'pass'), ('video', 'pass'), ('coins_or_ads', 'error'), ('coin+ad', 'error')):
            sink(s, 'skin_c2')['unlock_mode'] = mode
            r = pc.economy_audit(s)
            self.assertEqual(status(r, 'ECON-ADUNLOCK'), want, mode)
            self.assertEqual(r['schema_warnings'], [], mode)
        s = load('good.json')
        sink(s, 'skin_c1')['item'] = sink(s, 'skin_c2')['item'] = 'cat'       # one skin with a coin row and an ad row
        r = pc.economy_audit(s)
        self.assertEqual(status(r, 'ECON-ADUNLOCK'), 'error')
        self.assertTrue(any('cat' in d and 'skin_c1' in d and 'skin_c2' in d for d in row(r, 'ECON-ADUNLOCK')['details']))
        sink(s, 'skin_c2')['item'] = 'dog'
        self.assertEqual(self.st(s, 'ECON-ADUNLOCK'), 'pass')


class GiftPackAndBonusV3(unittest.TestCase):
    def st(self, s, rule):
        return status(pc.economy_audit(s), rule)

    def test_chest(self):
        s = load('good.json'); inflow(s, 'chest_5')['every_levels'] = 10
        self.assertEqual(self.st(s, 'ECON-CHEST'), 'error')
        s = load('good.json'); s['inflows'].append(dict(inflow(s, 'chest_5'), id='chest_ad', needs_ad=True, amount=40))
        self.assertEqual(self.st(s, 'ECON-CHEST'), 'pass')
        inflow(s, 'chest_ad')['amount'] = 50
        self.assertEqual(self.st(s, 'ECON-CHEST'), 'error')
        s = load('good.json'); s['inflows'] = [x for x in s['inflows'] if x['rule'] != 'ECON-CHEST']
        self.assertEqual(self.st(s, 'ECON-CHEST'), 'unknown')
        s['systems']['chest'] = False
        self.assertEqual(self.st(s, 'ECON-CHEST'), 'skip')

    def test_float(self):
        s = load('good.json'); inflow(s, 'float_gift')['amount'] = 6
        self.assertEqual(self.st(s, 'ECON-FLOAT'), 'error')
        s = load('good.json'); del inflow(s, 'float_gift')['per_round_max']
        self.assertEqual(self.st(s, 'ECON-FLOAT'), 'unknown')
        s = load('good.json'); s['inflows'].append({'id': 'float_hint', 'rule': 'ECON-FLOAT', 'currency': 'hint', 'amount': 1,
                                                    'x2': 'checkbox_default_on', 'per_round_max': 9})
        self.assertEqual(self.st(s, 'ECON-FLOAT'), 'error')                 # item gifts: per round still capped

    def test_bonus(self):
        s = load('good.json'); s['inflows'].append({'id': 'bonus_ad', 'rule': 'ECON-BONUS', 'currency': 'coins', 'amount': 50,
                                                    'needs_ad': True, 'x2': 'none'})
        self.assertEqual(self.st(s, 'ECON-BONUS'), 'error')                 # ad total must be 6B
        inflow(s, 'bonus_ad')['amount'] = 60
        self.assertEqual(self.st(s, 'ECON-BONUS'), 'pass')


class SecondCurrencyKeptV3(unittest.TestCase):
    def snap(self, kind='english'):
        s = load('good.json')
        s['game']['kind'] = kind
        s['currencies'].append({'id': 'gems', 'label': 'Gems', 'role': 'second', 'evidence': 'Wallet.js:6'})
        s['sinks'] += [{'id': 'ex_1', 'kind': 'exchange', 'currency': 'gems', 'price': 10, 'gives': 100, 'gives_currency': 'coins'},
                       {'id': 'ex_5', 'kind': 'exchange', 'currency': 'gems', 'price': 45, 'gives': 500, 'gives_currency': 'coins'}]
        s['inflows'].append({'id': 'ad_gems', 'currency': 'gems', 'amount': 5, 'per': 'ad', 'needs_ad': True, 'x2': 'none',
                             'count_per_day': 3})
        return s

    def test_kept_second_currency_ok(self):
        for kind in ('english', 'remake'):
            self.assertEqual(status(pc.economy_audit(self.snap(kind)), 'ECON-SECOND'), 'pass', kind)

    def test_exchange_discount_over_10_percent(self):
        s = self.snap(); s['sinks'].append({'id': 'ex_10', 'kind': 'exchange', 'currency': 'gems', 'price': 80, 'gives': 1000,
                                            'gives_currency': 'coins'})
        self.assertEqual(status(pc.economy_audit(s), 'ECON-SECOND'), 'suggest')
        self.assertEqual(status(pc.economy_audit(s, 'remake'), 'ECON-SECOND'), 'error')
        s['sinks'][-1]['origin'] = 'new'
        self.assertEqual(status(pc.economy_audit(s), 'ECON-SECOND'), 'error')

    def test_ad_second_needs_daily_cap(self):
        s = self.snap(); inflow(s, 'ad_gems')['count_per_day'] = None
        r = pc.economy_audit(s)
        self.assertEqual(status(r, 'ECON-SECOND'), 'suggest')
        self.assertIn('daily cap', ' '.join(row(r, 'ECON-SECOND')['details']))
        self.assertEqual(status(pc.economy_audit(s, 'remake'), 'ECON-SECOND'), 'error')


class SchemaWarningsAndAutoScanV3(unittest.TestCase):
    def test_misspelt_field_warned_not_failed(self):
        s = load('good.json')
        x = inflow(s, 'shortcut'); x['amout'] = x.pop('amount')
        s['systems']['chst'] = True
        s['meta']['sorce'] = 'hand'
        inflow(s, 'chest_5')['window'] = 'chests'
        r = pc.economy_audit(s)
        w = r['schema_warnings']
        i = s['inflows'].index(x)
        self.assertIn('inflows[%d].amout: unknown field (did you mean amount?)' % i, w)
        self.assertIn('systems.chst: unknown field (did you mean chest?)', w)
        self.assertIn('meta.sorce: unknown field (did you mean source?)', w)
        self.assertTrue(any(m.startswith('inflows[') and "unknown value 'chests' (did you mean chest?)" in m for m in w), w)
        self.assertEqual(status(r, 'ECON-SHORTCUT'), 'error')     # the misspelt amount reads as missing: still caught
        self.assertEqual(pc.economy_audit(load('good.json'))['schema_warnings'], [])

    def test_warnings_do_not_change_exit_code(self):
        import tempfile, os
        s = load('good.json'); s['inflows'][0]['amont'] = 1; s['_note'] = 'underscore keys are free'
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 's.json')
            Path(p).write_text(json.dumps(s), encoding='utf-8')
            out = subprocess.run([sys.executable, str(HERE / 'product_contract.py'), 'economy-audit', '--snapshot', p],
                                 capture_output=True, text=True)
        r = json.loads(out.stdout)
        self.assertEqual(r['schema_warnings'], ['inflows[0].amont: unknown field (did you mean amount?)'])
        if W1B_READY:
            self.assertEqual(out.returncode, 0)

    def test_systems_origin_warnings(self):
        s = load('good.json'); s['systems_origin'] = {'chekin': 'ad-boost', 'wheel': 'adboost'}
        w = pc.economy_audit(s)['schema_warnings']
        self.assertTrue(any(m.startswith('systems_origin.chekin: unknown system (did you mean checkin?)') for m in w), w)
        self.assertTrue(any(m.startswith("systems_origin.wheel: unknown value 'adboost'") for m in w), w)

    def test_auto_scan_skips_need_confirmation(self):
        s = load('good.json')
        s['meta'] = {'source': 'auto_scan'}
        s['systems'].update(wheel=False, chest=False)
        s['inflows'] = [x for x in s['inflows'] if x['rule'] not in ('ECON-WHEEL', 'ECON-CHEST')]
        r = pc.economy_audit(s)
        self.assertEqual(r['source'], 'auto_scan')
        self.assertIn('ECON-WHEEL', r['confirm_by_hand'])
        self.assertIn('ECON-CHEST', r['confirm_by_hand'])
        self.assertNotIn('ECON-NOCUR', r['confirm_by_hand'])          # 'has a currency' is a finding, not a miss
        self.assertIn(pc.ECON_AUTO_SCAN_SKIP_NOTE, row(r, 'ECON-WHEEL')['details'])
        self.assertEqual(status(r, 'ECON-WHEEL'), 'skip')
        s['meta']['source'] = 'hand'
        r = pc.economy_audit(s)
        self.assertEqual(r['confirm_by_hand'], [])
        self.assertNotIn(pc.ECON_AUTO_SCAN_SKIP_NOTE, row(r, 'ECON-WHEEL')['details'])


def no_coin_snapshot(kind='english', energy='power', amount=3, energy_system=False, items=False, result_x2=False):
    """good.json turned into a game without coins (rules table v3.3): B unknown, the currencies list holds only an energy
    currency (or nothing), add-to-desktop / home revisit pay `amount` of `energy` (a score when there is no energy)."""
    s = load('good.json')
    s['game']['kind'] = kind
    s['B'] = {'value': None, 'how': 'unknown', 'evidence': ''}
    s['currencies'] = [{'id': energy, 'label': energy, 'role': 'energy', 'evidence': 'x:1'}] if energy else []
    s['systems'].update(energy=bool(energy_system), items=items, result_x2=result_x2)
    for i in ('shortcut', 'revisit'):
        inflow(s, i).update(currency=energy or 'score', amount=amount)
    return s


class NoCoinV33(unittest.TestCase):
    """Rules table v3.3 (Saul 2026-11-04 「游戏里有体力的，各发 +3 体力；没有体力的，英化时加一种金币，再加皮肤给它当花处」), judged as
    the learning library's economy_plan.js platformNoCoin() and its test 「没有金币的游戏（Saul 2026-11-04）」."""
    RULES = ('ECON-SHORTCUT', 'ECON-REVISIT')

    def test_energy_only_pays_three_energy(self):
        r = pc.economy_audit(no_coin_snapshot())          # no B needed
        for rule in self.RULES:
            self.assertEqual(status(r, rule), 'pass', row(r, rule))
        self.assertTrue(r['ok'])

    def test_energy_only_paying_five_is_an_error_in_english_games(self):
        r = pc.economy_audit(no_coin_snapshot(amount=5))  # 5B worked out as 5 energy: wrong
        for rule in self.RULES:
            self.assertEqual(status(r, rule), 'error', rule)
            self.assertIn('+3 energy', ' '.join(row(r, rule)['details']))
        self.assertFalse(r['ok'])

    def test_energy_in_systems_only_accepts_an_energy_named_reward(self):
        s = no_coin_snapshot(energy=None, energy_system=True)
        for i in ('shortcut', 'revisit'):
            inflow(s, i).update(currency='Tili', amount=3)
        r = pc.economy_audit(s)
        for rule in self.RULES:
            self.assertEqual(status(r, rule), 'pass', row(r, rule))
        inflow(s, 'shortcut').update(currency='gems')
        self.assertEqual(status(pc.economy_audit(s), 'ECON-SHORTCUT'), 'error')

    def test_no_coin_no_energy_asks_for_a_coin_and_skins(self):
        r = pc.economy_audit(no_coin_snapshot(energy=None, amount=50))   # a score as the reward
        for rule in self.RULES:
            self.assertEqual(status(r, rule), 'error', rule)
            self.assertIn('add a coin currency and skins', ' '.join(row(r, rule)['details']))
        r = pc.economy_audit(no_coin_snapshot(energy=None, amount=50, kind='remake'))
        self.assertEqual(status(r, 'ECON-SHORTCUT'), 'error')

    def test_no_coin_skips_b_and_x2_and_nocur_without_items(self):
        r = pc.economy_audit(no_coin_snapshot())
        self.assertEqual((status(r, 'ECON-B'), status(r, 'ECON-X2'), status(r, 'ECON-NOCUR')), ('skip', 'skip', 'skip'))
        s = no_coin_snapshot(); s['meta'] = {'source': 'auto_scan'}
        r = pc.economy_audit(s)
        for rule in ('ECON-B', 'ECON-X2', 'ECON-NOCUR'):         # findings, not 'system not found'
            self.assertNotIn(rule, r['confirm_by_hand'])
        s['systems'].pop('items')                                  # items not reported: still skip, but confirm by hand
        r = pc.economy_audit(s)
        self.assertEqual(status(r, 'ECON-NOCUR'), 'skip')
        self.assertIn('ECON-NOCUR', r['confirm_by_hand'])

    def test_no_coin_with_items_needs_the_result_double(self):
        self.assertEqual(status(pc.economy_audit(no_coin_snapshot(items=True)), 'ECON-NOCUR'), 'error')
        self.assertEqual(status(pc.economy_audit(no_coin_snapshot(items=True, result_x2=True)), 'ECON-NOCUR'), 'pass')
        self.assertEqual(status(pc.economy_audit(no_coin_snapshot(items=True, result_x2=True)), 'ECON-X2'), 'skip')

    def test_other_rules_unknown_without_b(self):
        r = pc.economy_audit(no_coin_snapshot())
        judged = {'ECON-B', 'ECON-X2', 'ECON-NOCUR', 'ECON-SHORTCUT', 'ECON-REVISIT'}
        self.assertEqual(len(r['results']), len(pc.ECON_RULE_TITLES))
        for x in r['results']:
            if x['id'] not in judged:
                self.assertEqual((x['status'], x['details']), ('unknown', ['no coin currency, so no B: not checked']), x['id'])

    def test_no_coin_with_b_written_uses_the_energy_rule_too(self):
        s = no_coin_snapshot(); s['B'] = {'value': 10, 'how': 'config_normalLevelCoins', 'evidence': 'x:1'}
        r = pc.economy_audit(s)
        for rule in self.RULES:
            self.assertEqual(status(r, rule), 'pass', row(r, rule))
        self.assertEqual(status(r, 'ECON-X2'), 'skip')
        inflow(s, 'revisit').update(per='day')
        self.assertEqual(status(pc.economy_audit(s), 'ECON-REVISIT'), 'error')

    def test_finished_games_only_label(self):
        r = pc.economy_audit(no_coin_snapshot(energy=None, amount=50, kind='finished'))
        self.assertTrue(r['ok'])
        self.assertEqual(status(r, 'ECON-SHORTCUT'), 'label')

    def test_coin_games_and_snapshots_without_a_currency_list_unchanged(self):
        self.assertEqual(status(pc.economy_audit(load('good.json')), 'ECON-SHORTCUT'), 'pass')
        s = load('good.json'); inflow(s, 'shortcut').update(amount=40)
        self.assertEqual(status(pc.economy_audit(s), 'ECON-SHORTCUT'), 'error')
        s = load('good.json'); inflow(s, 'shortcut').update(currency='energy', amount=3)   # has coins: 5B coins, not energy
        self.assertEqual(status(pc.economy_audit(s), 'ECON-SHORTCUT'), 'error')
        r = pc.economy_audit({'schema': 'economy_snapshot.v1', 'B': {'value': None, 'how': 'unknown'}}, 'remake')
        self.assertEqual(status(r, 'ECON-B'), 'error')             # no currencies list: not assumed to have no coins


# The v3.4 rows of the learning library's template (配置模板/economy.config.json, enabled:false there), as snapshot rows.
V34_ROWS = {
    'battle_pass_free': ('inflows', {'id': 'battle_pass_free', 'rule': 'ECON-BATTLEPASS', 'window': 'battle_pass', 'currency': 'coins',
                                     'amounts': [10] * 10, 'per': 'season', 'needs_ad': False, 'x2': 'checkbox_default_on',
                                     'days_per_season': 7, 'tiers': 10, 'points_per_tier': 30, 'points_per_level': 10}),
    'battle_pass_ad': ('inflows', {'id': 'battle_pass_ad', 'rule': 'ECON-BATTLEPASS', 'window': 'battle_pass_ad', 'currency': 'coins',
                                   'amounts': [5, 5, 5, 5, 10, 10, 10, 15, 15, 20], 'per': 'season', 'needs_ad': True, 'x2': 'none'}),
    'score_chest_1': ('inflows', {'id': 'score_chest_1', 'rule': 'ECON-CHEST', 'window': 'score_chest', 'tier': 1, 'currency': 'coins',
                                  'amount': 20, 'per': 'claim', 'needs_ad': False, 'x2': 'checkbox_default_on'}),
    'online_jar': ('inflows', {'id': 'online_jar', 'rule': 'ECON-ONLINE', 'window': 'online_jar', 'currency': 'coins', 'amount': None,
                               'jar_fill_per_min': 3, 'jar_cap': 30, 'day_fill_max': 100, 'per': 'claim', 'needs_ad': False,
                               'x2': 'checkbox_default_on'}),
    'mid_boost': ('inflows', {'id': 'mid_boost', 'rule': 'ECON-MIDRUN', 'window': 'mid_boost', 'per': 'attempt', 'needs_ad': True,
                              'x2': 'none', 'extra_steps': 5, 'per_attempt': 1, 'bought_steps_pay': False}),
    'lose_upgrade': ('inflows', {'id': 'lose_upgrade', 'rule': 'ECON-UPGRADE', 'window': 'lose_upgrade', 'per': 'round', 'needs_ad': True,
                                 'x2': 'none', 'upgrade_levels': 1, 'per_round_max': 1}),
    'run_pay': ('inflows', {'id': 'run_pay', 'rule': 'ECON-RUNPAY', 'currency': 'coins', 'amount': 10, 'amount_max': 30, 'amount_min': 1,
                            'per': 'round', 'needs_ad': False, 'x2': 'ad_button'}),
    'revive_pay': ('sinks', {'id': 'revive_pay', 'rule': 'ECON-REVIVEPAY', 'kind': 'revive', 'currency': 'coins', 'price': 30,
                             'per_round_max': 1}),
}
V34_ALL = ('battle_pass_free', 'battle_pass_ad', 'score_chest_1', 'online_jar', 'mid_boost', 'lose_upgrade', 'revive_pay')
BATTLE_PASS = ('battle_pass_free', 'battle_pass_ad')


def v34_snapshot(ids=(), kind=None):
    """good.json plus the v3.4 template rows named in ids."""
    s = load('good.json')
    for i in ids:
        where, x = V34_ROWS[i]
        s[where].append(copy.deepcopy(x))
    if kind:
        s['game']['kind'] = kind
    return s


class V34NewBoards(unittest.TestCase):
    """Rules table v3.4 (2026-11-04, ad-boost round six), judged as the learning library's economy_plan.js and its tests
    「v3.4 ...」. Saul decided none of the new numbers: a miss is a capped suggestion even in a remake game; a wrong x2, a
    hidden ad-revive button or an ad that buys odds is reported by kind as usual. economy_plan.js writes a broken and a soft
    finding as two rows; the audit keeps one row per rule, listing both under the reported severity. A boost row whose
    numbers were not read is unknown here (economy_plan.js: skip with confirm)."""

    def audit(self, s, rule, kind=None):
        return row(pc.economy_audit(s, kind), rule)

    def soft(self, s, rule, kind=None):
        """Assert the rule's row is a capped suggestion that blocks nothing; return its details joined."""
        r = pc.economy_audit(s, kind)
        x = row(r, rule)
        self.assertEqual((x['status'], x.get('capped_by')), ('suggest', 'decided_by_saul=false'), x)
        self.assertIn(pc.ECON_V34_UNDECIDED_NOTE, x['details'])
        self.assertTrue(r['ok'] or W1B_RULES, with_status(r, 'error'))
        return ' | '.join(x['details'])

    def test_all_new_boards_clean(self):
        r = pc.economy_audit(v34_snapshot(V34_ALL))
        self.assertEqual(with_status(r, 'error', 'suggest', 'label', 'unknown'), set())
        self.assertEqual(r['schema_warnings'], [])
        self.assertTrue(r['ok'] or W1B_RULES)
        for rule in ('ECON-BATTLEPASS', 'ECON-REVIVEPAY', 'ECON-MIDRUN', 'ECON-CHEST', 'ECON-ONLINE', 'ECON-UPGRADE', 'ECON-CLAIMX2'):
            self.assertEqual(status(r, rule), 'pass', rule)
        self.assertIn('battle_pass, score_chest, online_jar', row(r, 'ECON-CLAIMX2')['details'][0])
        r = pc.economy_audit(load('good.json'))
        for rule in ('ECON-BATTLEPASS', 'ECON-REVIVEPAY', 'ECON-RUNPAY', 'ECON-MIDRUN', 'ECON-NOODDS'):
            self.assertEqual(status(r, rule), 'skip', rule)
        for key, rule in (('battle_pass', 'ECON-BATTLEPASS'), ('revive_pay', 'ECON-REVIVEPAY'), ('run_pay', 'ECON-RUNPAY'),
                          ('mid_boost', 'ECON-MIDRUN')):
            s = load('good.json'); s['systems'][key] = True                  # reported present, no numbers: not guessed
            self.assertEqual(status(pc.economy_audit(s), rule), 'unknown', rule)

    def test_battle_pass(self):
        s = v34_snapshot(BATTLE_PASS); inflow(s, 'battle_pass_free')['amounts'] = [20] * 10
        d = self.soft(s, 'ECON-BATTLEPASS')
        self.assertIn('battle_pass_free tier 1 gives 20; 1B = 10 expected', d)
        self.assertIn('a battle-pass season adds up to 300 (30.00B) without x2; at most 20B', d)
        s = v34_snapshot(BATTLE_PASS); inflow(s, 'battle_pass_ad')['amounts'] = [10] * 10
        self.assertIn('battle_pass_ad tier 1 gives 10; 0.5B = 5 expected', self.soft(s, 'ECON-BATTLEPASS'))
        s = v34_snapshot(BATTLE_PASS); inflow(s, 'battle_pass_free').update(tiers=8, points_per_endless_round=30)
        d = self.soft(s, 'ECON-BATTLEPASS')
        self.assertIn('battle pass tiers = 8; 10 expected', d)
        self.assertIn('30 points for an endless round; 10..20 expected', d)
        s = v34_snapshot(BATTLE_PASS); inflow(s, 'battle_pass_ad')['x2'] = 'checkbox_default_on'     # an ad cell is never doubled
        x = self.audit(s, 'ECON-BATTLEPASS')
        self.assertEqual(x['status'], 'error')
        self.assertIn('never doubled', x['details'][0])
        s = v34_snapshot(BATTLE_PASS); inflow(s, 'battle_pass_free')['x2'] = 'none'                 # the free cells' claim window
        x = self.audit(s, 'ECON-CLAIMX2')
        self.assertEqual(x['status'], 'error')
        self.assertTrue(any(m.startswith('battle_pass:') for m in x['details']), x)
        # no window written: the needs_ad row is the ad cell (economy_plan.js windowOf), so its x2 none is right
        s = v34_snapshot(BATTLE_PASS)
        for i in BATTLE_PASS:
            del inflow(s, i)['window']
        r = pc.economy_audit(s)
        self.assertEqual((status(r, 'ECON-BATTLEPASS'), status(r, 'ECON-CLAIMX2'), r['schema_warnings']), ('pass', 'pass', []))
        inflow(s, 'battle_pass_ad')['x2'] = 'checkbox_default_on'
        self.assertEqual(status(pc.economy_audit(s), 'ECON-BATTLEPASS'), 'error')

    def test_battle_pass_points_are_not_a_currency(self):
        s = v34_snapshot(BATTLE_PASS)
        s['currencies'].insert(0, {'id': 'bp_points', 'label': 'Points', 'role': 'points', 'evidence': 'x:1'})
        r = pc.economy_audit(s)
        self.assertEqual((status(r, 'ECON-DEAD'), status(r, 'ECON-BATTLEPASS')), ('pass', 'pass'))   # never spent: not dead
        # no main role written: the coins are the main currency, not the points (economy_plan.js: first non-points)
        s['currencies'][1]['role'] = 'second'
        inflow(s, 'battle_pass_free')['amounts'] = [20] * 10
        s['inflows'].append({'id': 'battle_pass_points', 'rule': 'ECON-BATTLEPASS', 'currency': 'bp_points', 'amount': 999})
        d = ' | '.join(self.audit(s, 'ECON-BATTLEPASS')['details'])
        self.assertIn('battle_pass_free tier 1 gives 20', d)
        self.assertNotIn('999', d)
        s = no_coin_snapshot()                                           # energy and points only: still no coins (v3.3)
        s['currencies'].append({'id': 'bp_points', 'label': 'Points', 'role': 'points', 'evidence': 'x:1'})
        r = pc.economy_audit(s)
        self.assertEqual((status(r, 'ECON-B'), status(r, 'ECON-SHORTCUT')), ('skip', 'pass'))

    def test_revive_pay(self):
        self.assertEqual(status(pc.economy_audit(v34_snapshot(['revive_pay'])), 'ECON-REVIVEPAY'), 'pass')
        s = v34_snapshot(['revive_pay']); sink(s, 'revive_pay').update(price=50, per_round_max=2)
        d = self.soft(s, 'ECON-REVIVEPAY')
        self.assertIn('a revive costs 50 (5.00B); 3B = 30 expected', d)
        self.assertIn('2 revives a round; together with the ad revive at most 1', d)
        s = v34_snapshot(['revive_pay']); sink(s, 'revive_pay')['hides_ad_revive'] = True
        x = self.audit(s, 'ECON-REVIVEPAY')
        self.assertEqual(x['status'], 'error')
        self.assertIn('hides the watch-ad revive button', x['details'][0])
        s = v34_snapshot(['revive_pay']); s['systems']['revive'] = False
        x = self.audit(s, 'ECON-REVIVEPAY')
        self.assertEqual(x['status'], 'error')
        self.assertIn('the ad revive button must be offered too', x['details'][0])

    def test_revive_is_a_place_to_spend_not_a_shop_item(self):
        s = v34_snapshot(['revive_pay'])
        s['currencies'].append({'id': 'gems', 'label': 'Gems', 'role': 'second', 'evidence': 'x:1'})   # gems only revive
        s['sinks'].append({'id': 'revive_gems', 'kind': 'revive', 'currency': 'gems', 'price': 5, 'per_round_max': 1})
        r = pc.economy_audit(s)
        self.assertEqual(status(r, 'ECON-DEAD'), 'pass', row(r, 'ECON-DEAD'))
        s['sinks'] = [x for x in s['sinks'] if x['id'] != 'revive_gems']
        self.assertEqual(status(pc.economy_audit(s), 'ECON-DEAD'), 'error')
        s = v34_snapshot(['revive_pay']); sink(s, 'revive_pay')['price'] = 20        # cheaper than any skin: not counted
        self.assertEqual(row(pc.economy_audit(s), 'ECON-PACING')['details'], row(pc.economy_audit(load('good.json')), 'ECON-PACING')['details'])

    def run_game(self, **change):
        """An endless game whose round pays nothing itself: the result turns the score into coins (ECON-RUNPAY)."""
        s = v34_snapshot(['run_pay'])
        s['game']['mode'] = 'endless'
        s['inflows'] = [x for x in s['inflows'] if x['id'] != 'level_clear']
        s['systems']['result_x2'] = False
        s['systems']['skin_trial'].update(trial='ad_minutes', trial_minutes=30)
        inflow(s, 'run_pay').update(change)
        return s

    def test_run_pay(self):
        r = pc.economy_audit(self.run_game())
        self.assertEqual((status(r, 'ECON-RUNPAY'), status(r, 'ECON-X2')), ('pass', 'pass'))   # its x2 is the result double
        self.assertTrue(r['ok'] or W1B_RULES)
        d = self.soft(self.run_game(amount=20, amount_max=50, amount_min=0), 'ECON-RUNPAY')
        for want in ('a normal round gives 20 (2.00B); 1B = 10 expected', 'up to 50 (5.00B); at most 3B before x2',
                     'at least 0 coins; at least 1'):
            self.assertIn(want, d)
        r = pc.economy_audit(self.run_game(x2='none'))
        self.assertEqual((status(r, 'ECON-RUNPAY'), status(r, 'ECON-X2')), ('pass', 'error'))

    def test_mid_run(self):
        self.assertEqual(status(pc.economy_audit(v34_snapshot(['mid_boost'])), 'ECON-MIDRUN'), 'pass')
        s = v34_snapshot(['mid_boost'])
        inflow(s, 'mid_boost').update(extra_steps=10, extra_sec=30, per_attempt=3, bought_steps_pay=True, refresh_free_per_round=5,
                                      refresh_ad_per_level=2, pick_all_ticket_every_levels=1)
        d = self.soft(s, 'ECON-MIDRUN')
        for want in ('+10 steps; +5 steps expected', '+30 s; +15 s expected', '3 times an attempt; at most 1',
                     'bought steps / time count in the round reward', '5 free refreshes a round; at most 2',
                     '2 ad refreshes a level; at most 1', 'a pick-all ticket every 1 levels; one every 3 levels'):
            self.assertIn(want, d)
        s = v34_snapshot(['mid_boost']); inflow(s, 'mid_boost')['x2'] = 'checkbox_default_on'
        r = pc.economy_audit(s)
        self.assertEqual((status(r, 'ECON-MIDRUN'), status(r, 'ECON-CLAIMX2')), ('error', 'pass'))   # mid_boost: excluded window
        self.assertIn('no x2', row(r, 'ECON-MIDRUN')['details'][0])
        s = load('good.json'); s['inflows'].append({'id': 'extra_steps_ad', 'needs_ad': True})   # found by id, numbers not read
        r = pc.economy_audit(s)
        self.assertEqual((status(r, 'ECON-MIDRUN'), r['schema_warnings']), ('unknown', []))

    def test_no_odds(self):
        s = load('good.json')
        s['inflows'].append({'id': 'claw_luck_ad', 'currency': 'coins', 'amount': 0, 'needs_ad': True, 'ad_buys_odds': True})
        r = pc.economy_audit(s)
        self.assertEqual((status(r, 'ECON-NOODDS'), r['schema_warnings']), ('error', []))
        self.assertIn('claw_luck_ad', row(r, 'ECON-NOODDS')['details'][0])
        self.assertEqual(status(pc.economy_audit(s, 'english'), 'ECON-NOODDS'), 'suggest')    # the original game's own
        inflow(s, 'claw_luck_ad')['origin'] = 'ad-boost'
        self.assertEqual(status(pc.economy_audit(s, 'english'), 'ECON-NOODDS'), 'error')      # added by us
        self.assertEqual(status(pc.economy_audit(load('good.json')), 'ECON-NOODDS'), 'skip')

    def test_lose_upgrade(self):
        self.assertEqual(status(pc.economy_audit(v34_snapshot(['lose_upgrade'])), 'ECON-UPGRADE'), 'pass')
        s = v34_snapshot(['lose_upgrade'])
        inflow(s, 'lose_upgrade').update(amount=50, currency='coins', per_round_max=2, upgrade_levels=2)
        d = self.soft(s, 'ECON-UPGRADE')
        for want in ('gives 50 coins; a free upgrade after a loss gives no coins', '2 a round; at most 1',
                     'upgrades 2 levels; +1 level expected'):
            self.assertIn(want, d)
        s['configs']['upgrade_lines'] = [[500, 1000, 2000]]          # a decided miss too: one row, error, both listed
        x = self.audit(s, 'ECON-UPGRADE')
        self.assertEqual(x['status'], 'error')
        self.assertTrue(any(m.startswith('line 1:') for m in x['details']) and any('gives no coins' in m for m in x['details']), x)
        s = v34_snapshot(['lose_upgrade']); inflow(s, 'lose_upgrade')['x2'] = 'checkbox_default_on'
        r = pc.economy_audit(s)
        self.assertEqual((status(r, 'ECON-UPGRADE'), status(r, 'ECON-CLAIMX2')), ('error', 'pass'))
        s = v34_snapshot(['lose_upgrade']); del s['configs']['upgrade_lines']; s['systems']['upgrade'] = False
        self.assertEqual(status(pc.economy_audit(s), 'ECON-UPGRADE'), 'pass')    # the free upgrade alone, no upgrade line

    def nr_wheel(self, **grand):
        """good.json's wheel replaced by an ad-boost no-replacement wheel, one row as in the learning library's template."""
        s = load('good.json')
        s['inflows'] = [x for x in s['inflows'] if x['rule'] != 'ECON-WHEEL']
        cells = [{'amount': a, 'weight': 1} for a in (50, 10, 10, 10, 20, 20, 20, 20, 20)]
        cells.append(dict({'grand': True, 'item': 'skin_lim', 'owned_fallback': 50, 'weight': 1}, **grand))
        s['inflows'].append({'id': 'wheel', 'rule': 'ECON-WHEEL', 'window': 'wheel_result', 'currency': 'coins', 'amount': None,
                             'per': 'spin', 'needs_ad': False, 'x2': 'checkbox_default_on', 'free_per_day': 1, 'ad_per_day': 2,
                             'count_per_day': 3, 'no_replacement': True, 'cells': cells, 'origin': 'ad-boost'})
        return s

    def test_no_replacement_wheel(self):
        r = pc.economy_audit(self.nr_wheel())
        self.assertEqual((status(r, 'ECON-WHEEL'), status(r, 'ECON-CLAIMX2'), r['schema_warnings']), ('pass', 'pass', []))
        self.assertIn('no-replacement wheel', row(r, 'ECON-WHEEL')['details'][0])
        s = self.nr_wheel()
        inflow(s, 'wheel')['cells'][1]['amount'] = 30
        inflow(s, 'wheel')['cells'][2]['amount'] = 30                 # 22B a round, 2.2B a spin
        d = self.soft(s, 'ECON-WHEEL')
        self.assertIn('add up to 220 (22.00B); at most 18B a round', d)
        self.assertNotIn('one spin is worth', d)                       # averaged over the round, not per spin
        d = self.soft(self.nr_wheel(item='skin_r2', owned_fallback=60), 'ECON-WHEEL')
        for want in ('skin_r2 is in the ad-unlock table', 'skin_r2 must count as limited', 'gives 60 (6.00B) instead; at most 5B'):
            self.assertIn(want, d)
        x = self.audit(self.nr_wheel(x2='checkbox_default_on'), 'ECON-WHEEL')
        self.assertEqual(x['status'], 'error')
        self.assertIn('grand-prize cell is not doubled', x['details'][0])
        s = self.nr_wheel(); inflow(s, 'wheel')['cells'].pop()
        self.assertIn('has 9 cells; 10 expected', self.soft(s, 'ECON-WHEEL'))
        s = self.nr_wheel(); inflow(s, 'wheel')['cells'][1]['amount'] = 60     # one cell is still at most 5B
        x = self.audit(s, 'ECON-WHEEL')
        self.assertEqual(x['status'], 'error')
        self.assertIn('largest wheel cell 60', x['details'][0])
        s = self.nr_wheel(); inflow(s, 'wheel')['free_per_day'] = 2              # the daily spins are read off the row
        self.assertEqual(status(pc.economy_audit(s), 'ECON-WHEEL'), 'error')

    def test_score_chest(self):
        r = pc.economy_audit(v34_snapshot(['score_chest_1']))
        self.assertEqual((status(r, 'ECON-CHEST'), status(r, 'ECON-CLAIMX2')), ('pass', 'pass'))
        s = v34_snapshot(['score_chest_1'])
        inflow(s, 'score_chest_1').update(amount=30, reclaim_by_ad=True)
        for t in (2, 3, 4):                      # no window: told apart from the every-5-levels chest by id
            s['inflows'].append({'id': 'score_chest_%d' % t, 'rule': 'ECON-CHEST', 'tier': t, 'currency': 'coins', 'amount': 20,
                                 'x2': 'checkbox_default_on'})
        d = self.soft(s, 'ECON-CHEST')
        for want in ('4 tiers; at most 3', 'free 30 (3.00B); a score-chest tier gives at most 2B', 'with the ad 60 (6.00B)',
                     'claimed again with an ad; each tier is claimed once'):
            self.assertIn(want, d)
        s = v34_snapshot(['score_chest_1']); inflow(s, 'score_chest_1')['x2'] = 'none'
        x = self.audit(s, 'ECON-CLAIMX2')
        self.assertEqual(x['status'], 'error')
        self.assertTrue(any(m.startswith('score_chest:') for m in x['details']), x)
        s = v34_snapshot(['score_chest_1'])
        s['inflows'] = [x for x in s['inflows'] if x['id'] != 'chest_5']; s['systems']['chest'] = False
        self.assertEqual(status(pc.economy_audit(s), 'ECON-CHEST'), 'pass')         # a score chest alone
        s = v34_snapshot(['score_chest_1']); inflow(s, 'chest_5')['amount'] = 30; inflow(s, 'score_chest_1')['amount'] = 30
        x = self.audit(s, 'ECON-CHEST')          # a decided chest miss and an undecided score-chest miss: one row, error
        self.assertEqual(x['status'], 'error')
        self.assertTrue('free chest gives 30 (3.00B); at most 2B' in x['details'] and any(m.startswith('score_chest_1') for m in x['details']), x)

    def test_coin_jar(self):
        r = pc.economy_audit(v34_snapshot(['online_jar']))
        self.assertEqual((status(r, 'ECON-ONLINE'), status(r, 'ECON-CLAIMX2')), ('pass', 'pass'))
        s = v34_snapshot(['online_jar']); inflow(s, 'online_jar').update(jar_fill_per_min=5, jar_cap=50)
        del inflow(s, 'online_jar')['day_fill_max']
        d = self.soft(s, 'ECON-ONLINE')
        for want in ('fills 5 (0.50B) a minute; at most 0.25B', 'a full jar holds 50 (5.00B); at most 3B', 'day_fill_max not written'):
            self.assertIn(want, d)
        s = v34_snapshot(['online_jar']); inflow(s, 'online_jar')['day_fill_max'] = 30; s['systems']['online_gift'] = True
        s['inflows'] += [{'id': 'online_gift_%d' % (i + 1), 'rule': 'ECON-ONLINE', 'currency': 'coins', 'amount': a,
                          'x2': 'checkbox_default_on'} for i, a in enumerate((10, 20, 20, 20, 20))]   # cards 9B + jar 3B a day
        self.assertIn('add up to 120 (12.00B); at most 10B', self.soft(s, 'ECON-ONLINE'))
        s = v34_snapshot(['online_jar']); inflow(s, 'online_jar')['x2'] = 'none'
        x = self.audit(s, 'ECON-CLAIMX2')
        self.assertEqual(x['status'], 'error')
        self.assertTrue(any(m.startswith('online_jar:') for m in x['details']), x)
        s = v34_snapshot(['online_jar'])
        s['inflows'].append({'id': 'online_jar_ad', 'window': 'online_jar', 'currency': 'coins', 'needs_ad': True,
                             'x2': 'checkbox_default_on', 'day_fill_max': 0})
        self.assertEqual(status(pc.economy_audit(s), 'ECON-ONLINE'), 'error')        # the watch-ad jar row is the ad itself

    @unittest.skipUnless(W1B_READY, 'W1b names not in product_contract.py yet')
    def test_ad_unlock_level_gates(self):
        def gates(**g):
            s = load('good.json')
            for i, level in g.items():
                sink(s, i)['gate_level'] = level
            return s
        x = self.audit(gates(skin_c2=3, skin_r2=7), 'ECON-ADUNLOCK')
        self.assertEqual(x['status'], 'pass')
        self.assertIn('one every 3..5 levels', x['details'][0])
        d = self.soft(gates(skin_c2=10, skin_r2=3), 'ECON-ADUNLOCK')
        self.assertIn('7 levels apart; one every 3..5 levels', d)
        self.assertIn('skin_c2 (50) is cheaper than skin_r2 (100) but opens later', d)
        x = self.audit(gates(skin_c2=3), 'ECON-ADUNLOCK')
        self.assertEqual(x['status'], 'pass')
        self.assertIn('without a gate: confirm by hand', x['details'][0])
        self.assertEqual(self.audit(load('good.json'), 'ECON-ADUNLOCK')['details'], [])   # no gate written: nothing added
        s = gates(skin_c2=10, skin_r2=3); sink(s, 'skin_r2')['ad_unlock_views'] = 9        # a decided miss too: error
        x = self.audit(s, 'ECON-ADUNLOCK')
        self.assertEqual(x['status'], 'error')
        self.assertTrue(any('levels apart' in m for m in x['details']) and any('9 views' in m for m in x['details']), x)

    def test_english_and_added_by_ad_boost(self):
        s = v34_snapshot(BATTLE_PASS, 'english'); inflow(s, 'battle_pass_free')['amounts'][0] = 50
        self.assertIn('tier 1 gives 50', self.soft(s, 'ECON-BATTLEPASS'))   # the original game's own: suggest
        s['systems_origin']['battle_pass'] = 'ad-boost'
        self.soft(s, 'ECON-BATTLEPASS')                                       # added by ad-boost: still at most suggest
        inflow(s, 'battle_pass_ad')['x2'] = 'checkbox_default_on'
        x = self.audit(s, 'ECON-BATTLEPASS')                                  # its doubled ad cell is judged as remake
        self.assertEqual((x['status'], x.get('judged_as')), ('error', 'remake'))
        self.assertTrue(any('never doubled' in m for m in x['details']) and any('tier 1 gives 50' in m for m in x['details']), x)
        del s['systems_origin']['battle_pass']
        self.assertEqual(status(pc.economy_audit(s), 'ECON-BATTLEPASS'), 'suggest')       # the original game's ad cell
        self.assertEqual(status(pc.economy_audit(s, 'finished'), 'ECON-BATTLEPASS'), 'label')

    def test_b_unknown_still_judges_mid_run_and_odds(self):
        s = v34_snapshot(['mid_boost', 'battle_pass_free']); s['B'] = {'value': None, 'how': 'unknown'}
        inflow(s, 'mid_boost')['x2'] = 'checkbox_default_on'
        s['inflows'].append({'id': 'claw_luck_ad', 'currency': 'coins', 'amount': 0, 'needs_ad': True, 'ad_buys_odds': True})
        r = pc.economy_audit(s)
        self.assertEqual([status(r, k) for k in ('ECON-B', 'ECON-MIDRUN', 'ECON-NOODDS', 'ECON-BATTLEPASS')],
                         ['error', 'error', 'error', 'unknown'])
        self.assertEqual([x['id'] for x in r['results']], list(pc.ECON_RULE_TITLES))

    def test_auto_scan_unread_numbers_are_confirmed_not_guessed(self):
        def snap(source):
            s = v34_snapshot(['run_pay', 'revive_pay', 'lose_upgrade', 'online_jar'])
            s['meta']['source'] = source
            for i, k in (('run_pay', 'amount_max'), ('lose_upgrade', 'per_round_max'), ('online_jar', 'day_fill_max')):
                del inflow(s, i)[k]
            del sink(s, 'revive_pay')['per_round_max']
            return s
        rules = ('ECON-RUNPAY', 'ECON-REVIVEPAY', 'ECON-UPGRADE', 'ECON-ONLINE')
        r = pc.economy_audit(snap('auto_scan'))
        for rule in rules:
            self.assertEqual(status(r, rule), 'pass', rule)
            self.assertIn('confirm by hand', row(r, rule)['details'][-1], rule)
        r = pc.economy_audit(snap('hand'))                    # written by hand: a missing number is a capped suggestion
        self.assertEqual([status(r, rule) for rule in rules], ['suggest'] * 4)


def fractional_b_snapshot(newB=72.5):
    """good.json (B = 10) rewritten the way a correct game with a fractional B writes it: every k*B rounded half up."""
    s = load('good.json')
    f = newB / 10
    r = lambda x: int(pc.math.floor(x * f + 0.5))
    s['B']['value'] = newB
    for x in s['inflows']:
        if x['currency'] == 'coins':
            x['amount'] = r(x['amount'])
    level = next(x for x in s['inflows'] if x['id'] == 'level_clear')
    level['amounts'] = [73, 72] * 10            # 72.5 a level: each group of ten sums to exactly 725
    for x in s['sinks']:
        if x['currency'] == 'coins':
            x['price'] = r(x['price'])
    hint = next(x for x in s['sinks'] if x['id'] == 'hint_1')['price']
    next(x for x in s['sinks'] if x['id'] == 'hint_3')['price'] = int(pc.math.ceil(0.9 * 3 * hint))
    s['configs']['upgrade_lines'] = [pc.upgrade_costs(newB)]
    q = s['configs']['quests']
    q['daily'] = [r(x) for x in q['daily']]
    q['achievements'] = [[r(x) for x in tiers] for tiers in q['achievements']]
    return s


class FractionalB(unittest.TestCase):
    """Saul 2026-10-31: B need not be whole (球球乐消除 B = 72.5). k*B fractional -> within 1; k*B whole -> exact."""

    def errors(self, s, kind=None):
        return {x['id']: x['details'] for x in pc.economy_audit(s, kind)['results'] if x['status'] == 'error' and x['id'] not in W1B_RULES}

    def test_amount_rule(self):
        self.assertTrue(pc._b_amount_ok(362, 5, 72.5) and pc._b_amount_ok(363, 5, 72.5))
        self.assertFalse(pc._b_amount_ok(361, 5, 72.5) or pc._b_amount_ok(364, 5, 72.5))
        self.assertTrue(pc._b_amount_ok(725, 10, 72.5))
        self.assertFalse(pc._b_amount_ok(724, 10, 72.5) or pc._b_amount_ok(726, 10, 72.5))
        self.assertTrue(pc._b_amount_ok(50, 5, 10))
        self.assertFalse(pc._b_amount_ok(49, 5, 10) or pc._b_amount_ok(51, 5, 10))   # whole B unchanged: exact
        self.assertEqual((pc._b_low(3, 72.5), pc._b_high(5, 72.5)), (217, 363))
        self.assertEqual((pc._b_low(3, 10), pc._b_high(5, 10)), (30, 50))

    def test_rounded_game_passes(self):
        s = fractional_b_snapshot()
        for kind in (None, 'english'):
            self.assertEqual(self.errors(s, kind), {}, kind)
        r = pc.economy_audit(s)
        self.assertTrue(r['ok'] or W1B_RULES)
        self.assertEqual(r['B'], 72.5)

    def test_more_than_rounding_still_caught(self):
        def bad(edit):
            s = fractional_b_snapshot(); edit(s); return set(self.errors(s))
        cases = {
            'ECON-GIFT': lambda s: inflow(s, 'gift_home').update(amount=361),
            'ECON-ADCOIN': lambda s: inflow(s, 'ad_coins').update(amount=364),
            'ECON-SHORTCUT': lambda s: inflow(s, 'shortcut').update(amount=350),
            'ECON-CHECKIN': lambda s: inflow(s, 'checkin_d7').update(amount=436),   # 6B = 435 is whole: exact
            'ECON-LEVEL10': lambda s: inflow(s, 'level_clear').update(amounts=[73] * 20),
            'ECON-TIER': lambda s: sink(s, 'skin_c1').update(price=730),
            'ECON-ITEM': lambda s: sink(s, 'hint_1').update(price=216),
            'ECON-WHEEL': lambda s: inflow(s, 'wheel_big').update(amount=364),
            'ECON-CHEST': lambda s: inflow(s, 'chest_5').update(amount=146),         # 2B = 145 is whole: at most 145
            'ECON-FLOAT': lambda s: inflow(s, 'float_gift').update(amount=38),       # 0.5B = 36.25: at most 37
            'ECON-BONUS': lambda s: inflow(s, 'bonus_level').update(amount=216),     # 3B = 217.5: 217 or 218
            'ECON-SHOPFREE': lambda s: inflow(s, 'shop_free_coins').update(amount=361),
        }
        for rule, edit in cases.items():
            if rule in W1B_RULES:
                continue
            self.assertIn(rule, bad(edit), rule)

    def test_every_group_of_ten_levels_checked(self):
        s = load('good.json')
        level = next(x for x in s['inflows'] if x['id'] == 'level_clear')
        level['amounts'] = [10] * 10 + [15] * 10
        details = self.errors(s).get('ECON-LEVEL10')
        self.assertTrue(details and 'levels 11-20' in details[0], details)
        level['amounts'] = [10] * 25                  # a partial last group is not judged
        self.assertNotIn('ECON-LEVEL10', self.errors(s))

    def test_upgrade_costs_accepts_fractional_b(self):
        costs = pc.upgrade_costs(72.5)
        self.assertEqual(len(costs), 10)
        self.assertTrue(all(type(c) is int for c in costs))
        self.assertEqual(costs[0], 218)
        self.assertEqual(pc.upgrade_errors(costs, 72.5), [])
        self.assertEqual(pc.upgrade_costs(10), [30, 38, 48, 61, 77, 97, 123, 156, 198, 250])
        for b in (0, -1, None, True, float('nan')):
            with self.assertRaises(ValueError):
                pc.upgrade_costs(b)


if __name__ == '__main__':
    unittest.main()
