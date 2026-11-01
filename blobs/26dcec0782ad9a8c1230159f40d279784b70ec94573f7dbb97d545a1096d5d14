#!/usr/bin/env python3
"""Tests for make_economy_config.py (货币补丁 v3, W2). Run: /usr/bin/python3 test_make_economy_config.py

Every number in the generated economy_config.json is checked here against the rules table directly (not against the
script), for B = 10, 72.5 and 3; out-of-range inputs must be refused with nothing written; the same input must give the
same bytes; the generated snapshot must pass product_contract.py economy-audit.
"""
import copy
import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import product_contract as pc  # noqa: E402

SCRIPT = HERE / 'make_economy_config.py'
RULES_PATH = HERE.parent.parent / 'remake-economy' / 'references' / 'economy_rules_table.json'
TABLE = json.loads(RULES_PATH.read_text(encoding='utf-8'))
R = {r['id']: r.get('params', {}) for r in TABLE['rules']}
ALL = 'items,item_pack,ad_item,wheel,upgrade,checkin,quests,energy,chest,float_gift,bonus_level,ad_coin,shop_free,home_gift,shortcut,revisit,skins'
CASES = {  # name -> arguments
    'B10': ['--B', '10', '--systems', ALL, '--item-ids', 'hint,bomb'],
    'B72.5': ['--B', '72.5', '--systems', ALL, '--item-ids', 'hint,bomb', '--item-prices-B', 'hint=3,bomb=5',
              '--wheel-cells-B', '1,3,2,1', '--achievement-tiers', '7'],
    'B3': ['--B', '3', '--mode', 'endless', '--no-items', '--no-gift-skins',
           '--systems', 'wheel,upgrade,checkin,quests,chest,float_gift,ad_coin,shop_free,home_gift,shortcut,revisit,skins'],
    'B10_idle': ['--B', '10', '--mode', 'idle', '--systems', 'offline,upgrade,checkin,home_gift,shortcut,revisit,items',
                 '--item-ids', 'hint'],
}


def run(args, out):
    p = subprocess.run([sys.executable, str(SCRIPT)] + args + ['--out-dir', str(out)], capture_output=True, text=True)
    return p


def eq(amount, k, B):
    """amount is the game's whole number for k x B (fractional -> less than 1 away, whole -> exact)."""
    w = k * B
    return type(amount) is int and (abs(amount - w) < 1 if abs(w - round(w)) > 1e-9 else amount == round(w))


def at_most(amount, k, B):
    return type(amount) is int and 1 <= amount <= math.ceil(k * B - 1e-9)


def check_config(c, B, mode, has_items, gift_skins):
    """Every number of an economy_config.v1 against the rules table; returns a list of problems."""
    bad = []

    def need(ok, msg):
        if not ok:
            bad.append(msg)

    box = {'checkbox': True, 'default_checked': R['ECON-CLAIMX2']['default_checked'], 'multiplier': R['ECON-CLAIMX2']['multiplier']}
    need(c['rules_revision'] == TABLE['revision'], 'rules revision')
    need(c['B'] == B, 'B kept as given')
    if mode == 'levels':
        per = c['level_reward']['per_level']
        need(all(type(x) is int for x in per), 'level rewards whole')
        for i in range(0, len(per) - 9, 10):
            need(eq(sum(per[i:i + 10]), R['ECON-LEVEL10']['sum_B'], B), 'levels %d-%d sum' % (i + 1, i + 10))
    need(c['result_x2'] == {'multiplier': R['ECON-X2']['multiplier'], 'pay': R['ECON-X2']['pay'], 'note': c['result_x2']['note']}, 'result x2')
    for it in c.get('items', []):
        need(at_most(it['price'], R['ECON-ITEM']['max_B'], B) and it['price'] >= math.floor(R['ECON-ITEM']['min_B'] * B), 'item %s price' % it['id'])
        if 'pack' in it:
            disc = 1 - it['pack']['price'] / (it['price'] * it['pack']['size'])
            need(0 <= disc <= R['ECON-PACK']['max_discount'] + 1e-9, 'pack %s discount %.3f' % (it['id'], disc))
        if 'ad_gives' in it:
            need(it['ad_gives'] == R['ECON-ADITEM']['per_ad'], 'ad item')
    if 'home_gift' in c:
        g = c['home_gift']
        need(eq(g['amount'], R['ECON-GIFT']['reward_B'], B) and g['cooldown_ms'] == R['ECON-GIFT']['cooldown_ms']
             and g['double_checkbox'] is False, 'home gift')
    for s, rule in (('shortcut', 'ECON-SHORTCUT'), ('revisit', 'ECON-REVISIT')):
        if s in c:
            need(eq(c[s]['amount'], R[rule]['reward_B'], B) and c[s]['times'] == R[rule]['times'], s)
    if 'ad_coin' in c:
        p = R['ECON-ADCOIN']
        need(eq(c['ad_coin']['amount'], p['reward_B'], B) and c['ad_coin']['per_day'] == p['per_day'], 'ad coin')
    if 'shop_free' in c:
        p = R['ECON-SHOPFREE']
        for sl in c['shop_free']['slots']:
            ok = eq(sl['amount'], p['coins_B_per_claim'], B) if sl['gives'] == c['currency'] else sl['amount'] == p['item_per_claim']
            need(ok and sl['per_day'] == p['per_slot_per_day'], 'shop free %s' % sl['id'])
    if 'checkin' in c:
        p, ck = R['ECON-CHECKIN'], c['checkin']
        need(ck['R'] == B and ck['double'] == box and [d['day'] for d in ck['days']] == list(range(1, 8)), 'check-in frame')
        for d in ck['days']:
            day = d['day']
            coins = sum(x['amount'] for x in d['rewards'] if x['type'] == 'coins')
            allowed = p['allowed_day_coins_B'][str(day)]
            need(any(coins == 0 if k == 0 else eq(coins, k, B) for k in allowed), 'check-in day %d coins %s' % (day, coins))
            forced = p['coins_B_by_day'].get(str(day), 0)
            if not has_items and str(day) in p['no_item_fallback_B']:
                forced += p['no_item_fallback_B'][str(day)]
            if not gift_skins and str(day) in p['skin_fallback_B']:
                forced += p['skin_fallback_B'][str(day)]
            need(coins == 0 if forced == 0 else eq(coins, forced, B), 'check-in day %d coins %s, %sB expected' % (day, coins, forced))
            for x in d['rewards']:
                if x['type'] == 'skin':
                    need(gift_skins and eq(x['fallback_coins'], p['skin_fallback_B'][str(day)], B), 'check-in day %d skin fallback' % day)
                if x['type'] == 'item':
                    need(has_items and x['amount'] == p['item_amount_by_day'].get(str(day)), 'check-in day %d item amount' % day)
            need(has_items == any(x['type'] == 'item' for x in d['rewards']) or str(day) not in p['item_amount_by_day'],
                 'check-in day %d item present only with items' % day)
    if 'wheel' in c:
        p, w = R['ECON-WHEEL'], c['wheel']
        lo, hi = p['cell_coins_B_range']
        coins = [x for x in w['cells'] if x['type'] == 'coins']
        need(w['free_per_day'] == p['free_per_day'] and w['ad_per_day'] == p['ad_per_day'] and w['result_double'] == box, 'wheel frame')
        need(all(type(x['amount']) is int and math.floor(lo * B) <= x['amount'] <= math.ceil(min(hi, p['max_cell_B']) * B) for x in coins),
             'wheel coin cells')
        exp = sum(x['amount'] * x['weight'] for x in coins) / sum(x['weight'] for x in w['cells'])
        need(exp <= math.ceil(p['expected_per_spin_B_max'] * B), 'wheel expected %.2f' % exp)
    if 'chest' in c:
        p = R['ECON-CHEST']
        need(at_most(c['chest']['amount'], p['free_max_B'], B) and at_most(2 * c['chest']['amount'], p['double_max_B'], B)
             and c['chest']['every_levels'] == p['every_levels'] and c['chest']['double'] == box, 'chest')
    if 'float_gift' in c:
        p = R['ECON-FLOAT']
        need(at_most(c['float_gift']['amount'], p['each_max_B'], B) and c['float_gift']['per_round_max'] == p['per_round_max']
             and c['float_gift']['double'] == box, 'floating gift')
    if 'bonus_level' in c:
        p = R['ECON-BONUS']
        need(eq(c['bonus_level']['amount'], p['reward_B'], B) and eq(c['bonus_level']['ad_total'], p['ad_reward_B'], B), 'bonus level')
    if 'offline' in c:
        p = R['ECON-OFFLINE']
        need(all(c['offline'][k] == p[k] for k in ('min_away_sec', 'cap_sec', 'ad_multiplier', 'min_payout')) and c['offline']['double'] == box, 'offline')
    if 'upgrade' in c:
        p = R['ECON-UPGRADE']
        for line in c['upgrade']['lines']:
            need(line['costs'] == pc.upgrade_costs(B, p['levels'], p['first_B'], p['last_B']), 'upgrade line = upgrade_costs(B)')
            need(abs(sum(line['costs']) / B - p['total_B']) <= p['total_B'] * p['tolerance'], 'upgrade total')
    if 'quests' in c:
        p, q = R['ECON-QUEST'], c['quests']
        need(len(q['daily']) == p['daily_tasks'] and all(eq(x['amount'], p['daily_task_B'], B) for x in q['daily']), 'daily tasks')
        for a in q['achievements']:
            t = a['tiers']
            need(p['achievement_tiers'][0] <= len(t) <= p['achievement_tiers'][1] and eq(t[0], p['achievement_B_min'], B) and eq(t[-1], p['achievement_B_max'], B)
                 and t == sorted(t) and all(type(x) is int for x in t), 'achievement %s' % a['id'])
        need(q['achievement_gives_skin'] is p['achievement_gives_skin'] and q['double'] == box, 'quest frame')
    if 'energy' in c:
        need(c['energy']['ad_refill'] == R['ECON-ENERGY']['ad_refill'] and c['energy']['skip_if_no_room'] is True, 'energy')
    if 'skin_trial' in c:
        p, t = R['ECON-SKINTRIAL'], c['skin_trial']
        need(t['present'] is True and t['no_popup_levels'] == p['no_popup_levels'] and t['every_levels'] == p['every_levels']
             and t['endless_every_rounds'] == p['endless_every_rounds'], 'skin trial')
        need(c['skins']['economy_policy'] == R['ECON-TIER']['policy'] and c['skins']['ad_unlock_policy'] == R['ECON-ADUNLOCK']['policy']
             and any('make_skin_table.py' in x for x in c['skins']['commands']) and any(' ad-unlock ' in x for x in c['skins']['commands']),
             'skin commands')
    return bad


class MakeEconomyConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='w2_econ_'))
        cls.out = {}
        for name, args in CASES.items():
            p = run(args, cls.tmp / name)
            assert p.returncode == 0, (name, p.stderr)
            cls.out[name] = (json.loads((cls.tmp / name / 'economy_config.json').read_text(encoding='utf-8')),
                             json.loads((cls.tmp / name / 'economy_snapshot.json').read_text(encoding='utf-8')))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_number_follows_the_rules(self):
        for name, B, mode, items, gift in (('B10', 10, 'levels', True, True), ('B72.5', 72.5, 'levels', True, True),
                                           ('B3', 3, 'endless', False, False), ('B10_idle', 10, 'idle', True, False)):  # idle: no skins
            with self.subTest(name):
                self.assertEqual(check_config(self.out[name][0], B, mode, items, gift), [])

    def test_defaults_are_the_table_defaults(self):
        """Round 2 (lead 2026-11-01): item price, wheel cells, check-in item amounts and rounding come from the table."""
        c = self.out['B10'][0]
        self.assertEqual([it['price'] for it in c['items']], [R['ECON-ITEM']['default_B'] * 10] * 2)
        self.assertEqual([x['amount'] for x in c['wheel']['cells'] if x['type'] == 'coins'],
                         [k * 10 for k in R['ECON-WHEEL']['default_cells_B']])
        got = {d['day']: x['amount'] for d in c['checkin']['days'] for x in d['rewards'] if x['type'] == 'item'}
        self.assertEqual(got, {int(k): v for k, v in R['ECON-CHECKIN']['item_amount_by_day'].items()})
        self.assertIn('0.5', TABLE['B']['rounding'])
        self.assertEqual(c['B_rounding'], TABLE['B']['rounding'])
        # 'at most' amounts round half up as well: 0.5B x 72.5 = 36.25 -> 36, 0.5B x 3 = 1.5 -> 2, 2B x 72.5 = 145
        self.assertEqual(self.out['B72.5'][0]['float_gift']['amount'], 36)
        self.assertEqual(self.out['B3'][0]['float_gift']['amount'], 2)
        self.assertEqual(self.out['B72.5'][0]['chest']['amount'], 145)

    def test_skins_without_table_get_a_placeholder_sink(self):
        """Round 2: skins but no --skin-table used to leave coins without a sink (ECON-DEAD error)."""
        args = ['--B', '10', '--systems', 'checkin,skins,skin_trial,home_gift,shortcut,revisit', '--no-items', '--no-gift-skins']
        p = run(args, self.tmp / 'placeholder')
        self.assertEqual(p.returncode, 0, p.stderr)
        s = json.loads((self.tmp / 'placeholder' / 'economy_snapshot.json').read_text(encoding='utf-8'))
        tiers = R['ECON-TIER']['tiers_B']
        low = min(tiers, key=lambda r: tiers[r])
        ph = [x for x in s['sinks'] if x['id'] == 'skin_placeholder']
        self.assertEqual(len(ph), 1)
        self.assertEqual((ph[0]['kind'], ph[0]['rarity'], ph[0]['price'], ph[0]['origin'], ph[0]['ad_unlock_views']),
                         ('skin', low, tiers[low] * 10, 'new', 0))
        self.assertTrue(any('make_skin_table' in u for u in s['unknowns']))
        rep = pc.economy_audit(copy.deepcopy(s), 'remake')
        status = {r['id']: r['status'] for r in rep['results']}
        self.assertEqual([(r['id'], r['details']) for r in rep['results'] if r['status'] == 'error'], [])
        self.assertEqual((status['ECON-DEAD'], status['ECON-TIER'], status['ECON-ADUNLOCK']), ('pass', 'pass', 'pass'))
        # without the placeholder (the round-1 output) the same snapshot fails ECON-DEAD
        s['sinks'] = [x for x in s['sinks'] if x['id'] != 'skin_placeholder']
        rep = pc.economy_audit(s, 'remake')
        self.assertEqual({r['id']: r['status'] for r in rep['results']}['ECON-DEAD'], 'error')

    def test_systems_present(self):
        c = self.out['B10'][0]
        for k in ('level_reward', 'items', 'home_gift', 'shortcut', 'revisit', 'ad_coin', 'shop_free', 'checkin', 'wheel', 'chest',
                  'float_gift', 'bonus_level', 'upgrade', 'quests', 'energy', 'skin_trial', 'skins'):
            self.assertIn(k, c)
        self.assertIn('offline', self.out['B10_idle'][0])
        self.assertEqual(self.out['B10_idle'][0]['upgrade']['lines'], [])  # idle: price by output per second

    def test_checker_catches_tampering(self):
        """坏的被拦: the checker above is not a rubber stamp."""
        c = self.out['B72.5'][0]
        for path, value in ((('home_gift', 'amount'), 400), (('chest', 'amount'), 146), (('float_gift', 'amount'), 38),
                            (('bonus_level', 'ad_total'), 437), (('wheel', 'result_double', 'default_checked'), False),
                            (('checkin', 'days', 6, 'rewards', 0, 'amount'), 800), (('ad_coin', 'per_day'), 50),
                            (('skin_trial', 'every_levels'), 4)):
            bad = copy.deepcopy(c)
            node = bad
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.subTest(path):
                self.assertNotEqual(check_config(bad, 72.5, 'levels', True, True), [])

    def test_out_of_range_refused_nothing_written(self):
        base = ['--B', '10', '--systems', 'items,item_pack,wheel,quests,bonus_level,checkin', '--item-ids', 'hint']
        for extra in (['--item-price-B', '2.5'], ['--item-price-B', '6'], ['--item-prices-B', 'hint=5.5'],
                      ['--wheel-cells-B', '1,4'], ['--wheel-cells-B', '0.5,1'], ['--wheel-cells-B', '3,3,3'],
                      ['--pack-discount', '0.2'], ['--pack-size', '1'], ['--achievement-tiers', '8'], ['--achievement-tiers', '2'],
                      ['--mode', 'endless'], ['--systems', 'checkin,bogus'], ['--no-items'], ['--B', '0'], ['--B', '-3'],
                      ['--systems', 'offline'], ['--wheel-weights', '1,1']):
            with self.subTest(extra):
                out = self.tmp / ('refused_%d' % abs(hash(tuple(extra))))
                p = run(base + extra, out)
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertIn('refused, nothing written', p.stderr)
                self.assertFalse(out.exists())

    def test_same_input_same_bytes(self):
        for name, args in CASES.items():
            with self.subTest(name):
                p = run(args, self.tmp / (name + '_again'))
                self.assertEqual(p.returncode, 0)
                for f in ('economy_config.json', 'economy_snapshot.json'):
                    self.assertEqual((self.tmp / name / f).read_bytes(), (self.tmp / (name + '_again') / f).read_bytes())

    def test_rules_read_at_run_time(self):
        """A changed table changes the output: no number is kept in the script."""
        t = copy.deepcopy(TABLE)
        for r in t['rules']:
            if r['id'] == 'ECON-GIFT':
                r['params']['reward_B'] = 6
            if r['id'] == 'ECON-SKINTRIAL':
                r['params']['every_levels'] = 4
            if r['id'] == 'ECON-ITEM':
                r['params']['default_B'] = 4
            if r['id'] == 'ECON-WHEEL':
                r['params']['default_cells_B'] = [1, 1, 2]
            if r['id'] == 'ECON-CHECKIN':
                r['params']['item_amount_by_day'] = {'2': 5, '4': 6, '7': 7}
            if r['id'] == 'ECON-QUEST':
                r['params']['achievement_tiers'] = [3, 4]
        rules = self.tmp / 'rules_changed.json'
        rules.write_text(json.dumps(t, ensure_ascii=False), encoding='utf-8')
        p = run(['--B', '10', '--systems', 'home_gift,skins,items,wheel,checkin', '--item-ids', 'hint', '--rules', str(rules)],
                self.tmp / 'changed')
        self.assertEqual(p.returncode, 0, p.stderr)
        c = json.loads((self.tmp / 'changed' / 'economy_config.json').read_text(encoding='utf-8'))
        self.assertEqual(c['home_gift']['amount'], 60)
        self.assertEqual(c['skin_trial']['every_levels'], 4)
        self.assertEqual(c['items'][0]['price'], 40)
        self.assertEqual([x['amount'] for x in c['wheel']['cells'] if x['type'] == 'coins'], [10, 10, 20])
        self.assertEqual({d['day']: x['amount'] for d in c['checkin']['days'] for x in d['rewards'] if x['type'] == 'item'},
                         {2: 5, 4: 6, 7: 7})
        # the tier range is read from the table too: 5 tiers (the default) is outside [3, 4] -> refused
        p = run(['--B', '10', '--systems', 'quests', '--rules', str(rules)], self.tmp / 'changed_q')
        self.assertEqual(p.returncode, 2)
        self.assertFalse((self.tmp / 'changed_q').exists())

    def test_snapshot_shape(self):
        for name, (c, s) in self.out.items():
            with self.subTest(name):
                self.assertEqual(s['schema'], 'economy_snapshot.v1')
                self.assertEqual(s['meta']['source'], 'hand')
                self.assertEqual({x['origin'] for x in s['inflows'] + s['sinks']}, {'new'})
                self.assertEqual(s['game']['economy_policy'], R['ECON-TIER']['policy'])
                claim = R['ECON-CLAIMX2']
                for x in s['inflows']:
                    w = x.get('window')
                    if w in claim['windows']:
                        self.assertIn(x['x2'], claim['accepted_marks'].get(w, claim['accepted_marks']['default']), x['id'])
                    if w in claim['excluded']:
                        self.assertEqual(x['x2'], 'none', x['id'])

    def test_snapshot_passes_economy_audit(self):
        """Uses the product_contract.py next to this file (patch version at the time). Rules the audit does not know yet are
        listed, not failed; the lead re-runs this on the final v3."""
        for name, (c, s) in self.out.items():
            with self.subTest(name):
                rep = pc.economy_audit(copy.deepcopy(s), 'remake')
                self.assertEqual(rep.get('schema_warnings', []), [], 'snapshot uses field names the audit does not know')
                self.assertEqual([(r['id'], r['details']) for r in rep['results'] if r['status'] == 'error'], [])
                self.assertTrue(rep['ok'])
                missing = sorted({'ECON-SKINTRIAL', 'ECON-CHEST', 'ECON-FLOAT', 'ECON-BONUS', 'ECON-SHOPFREE'}
                                 - {r['id'] for r in rep['results']})
                if missing:
                    print('\n  [%s] audit has no rows yet for %s (W1a still adding them; lead re-checks on v3)' % (name, missing))

    def test_audit_blocks_a_tampered_snapshot(self):
        """坏的被拦 on the audit side: one wrong row in the generated snapshot makes economy-audit fail."""
        s = self.out['B10'][1]
        for rule, field, value in (('ECON-CHECKIN', 'amount', 15), ('ECON-GIFT', 'amount', 40), ('ECON-WHEEL', 'x2', 'none'),
                                   ('ECON-QUEST', 'amount', 30)):
            bad = copy.deepcopy(s)
            next(x for x in bad['inflows'] if x['rule'] == rule)[field] = value
            bad['configs'].pop('wheel' if rule == 'ECON-WHEEL' else 'quests' if rule == 'ECON-QUEST' else '_', None)
            with self.subTest(rule):
                rep = pc.economy_audit(bad, 'remake')
                self.assertFalse(rep['ok'], rule)

    def test_three_ad_boost_boards(self):
        """Rules table v3.2 (货币skill 会话 11-01): --systems timer_chest,online_gift,key_chest. Every B passes economy-audit
        with the three rules and the claim double checked (pass, not skip), and the numbers are the table's."""
        boards = ',timer_chest,online_gift,key_chest'
        for name, args in (('B10', CASES['B10']), ('B72.5', CASES['B72.5']), ('B3', CASES['B3'])):
            args = list(args)
            args[args.index('--systems') + 1] += boards
            out = self.tmp / ('boards_' + name)
            p = run(args, out)
            with self.subTest(name):
                self.assertEqual(p.returncode, 0, p.stderr)
                c = json.loads((out / 'economy_config.json').read_text(encoding='utf-8'))
                s = json.loads((out / 'economy_snapshot.json').read_text(encoding='utf-8'))
                B = s['B']['value']
                rep = pc.economy_audit(copy.deepcopy(s), 'remake')
                self.assertEqual(rep.get('schema_warnings', []), [])
                self.assertEqual([(r['id'], r['details']) for r in rep['results'] if r['status'] == 'error'], [])
                status = {r['id']: r['status'] for r in rep['results']}
                for rule in ('ECON-TIMERCHEST', 'ECON-ONLINE', 'ECON-KEYCHEST', 'ECON-CLAIMX2'):
                    self.assertEqual(status[rule], 'pass', rule)
                tc, t = c['timer_chest'], R['ECON-TIMERCHEST']
                self.assertTrue(eq(tc['amount'], t['free_open_B'], B))
                self.assertEqual({k: tc[k] for k in ('wait_sec', 'ad_cut_sec', 'ad_cuts_per_round', 'rounds_per_day')},
                                 {k: t[k] for k in ('wait_sec', 'ad_cut_sec', 'ad_cuts_per_round', 'rounds_per_day')})
                self.assertEqual(s['systems']['timer_chest']['wait_sec'], t['wait_sec'])
                o = R['ECON-ONLINE']
                tiers = c['online_gift']['tiers']
                self.assertEqual([x['minutes'] for x in tiers], o['tiers_min'])
                self.assertLessEqual(sum(x['amount'] for x in tiers), math.ceil(o['day_total_max_B'] * B))
                self.assertEqual(len(c['key_chest']['cells']), R['ECON-KEYCHEST']['cells'])
                windows = {x['window'] for x in s['inflows'] if x['rule'] in ('ECON-TIMERCHEST', 'ECON-ONLINE', 'ECON-KEYCHEST')}
                self.assertEqual(windows, {'timer_chest', 'online_gift', 'key_chest'})
                self.assertTrue(all(x['x2'] == 'checkbox_default_on' for x in s['inflows']
                                    if x['rule'] in ('ECON-TIMERCHEST', 'ECON-ONLINE', 'ECON-KEYCHEST')))

    def test_three_boards_refused_when_numbers_break_the_rules(self):
        """A key-chest cell of 6B, or cells that do not add up to 15B, in the generator's defaults; a timer chest whose ads
        open it at once and online tiers over 10B a day in the rules table: refused, nothing written."""
        import make_economy_config as mec
        from unittest import mock
        base = ['--B', '10', '--systems', 'checkin,shortcut,revisit,key_chest']
        for cells in (('6',) + mec.KEY_CHEST_CELLS_B[1:], mec.KEY_CHEST_CELLS_B[:-1] + ('1',)):
            out = self.tmp / ('key_refused_%s' % '_'.join(cells))
            with self.subTest(cells), mock.patch.object(mec, 'KEY_CHEST_CELLS_B', cells), \
                    mock.patch('sys.stderr', new_callable=__import__('io').StringIO) as err:
                self.assertEqual(mec.main(base + ['--out-dir', str(out)]), 2)
                self.assertIn('key chest default cells do not match ECON-KEYCHEST', err.getvalue())
                self.assertFalse(out.exists())
        self.assertEqual(mec.main(base + ['--out-dir', str(self.tmp / 'key_ok')]), 0)      # the shipped defaults pass
        for rule, key, value, words in (('ECON-TIMERCHEST', 'ad_cuts_per_round', 4, 'below wait_sec'),
                                        ('ECON-ONLINE', 'per_tier_max_B', 4, 'over 10B a day')):
            table = copy.deepcopy(TABLE)
            next(r for r in table['rules'] if r['id'] == rule)['params'][key] = value
            rules = self.tmp / ('rules_%s.json' % rule)
            rules.write_text(json.dumps(table, ensure_ascii=False), encoding='utf-8')
            out = self.tmp / ('refused_' + rule)
            p = run(['--B', '10', '--systems', 'checkin,shortcut,revisit,timer_chest,online_gift', '--rules', str(rules)], out)
            with self.subTest(rule):
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertIn('refused, nothing written', p.stderr)
                self.assertIn(words, p.stderr)
                self.assertFalse(out.exists())

    def test_skin_tables_merge(self):
        """Skin rows come from W1b's make_skin_table.py + ad-unlock, never priced here."""
        d = self.tmp / 'skins'
        d.mkdir()
        p1 = subprocess.run([sys.executable, str(HERE / 'make_skin_table.py'), '--R', '10', '--levels', '--final-level', '60',
                             '--out', str(d / 'unlock_table.json')], capture_output=True, text=True)
        p2 = subprocess.run([sys.executable, str(HERE / 'product_contract.py'), 'ad-unlock', '--table', str(d / 'unlock_table.json'),
                             '--out', str(d / 'ad_unlock_table.json')], capture_output=True, text=True)
        self.assertEqual((p1.returncode, p2.returncode), (0, 0), p1.stderr + p2.stderr)
        table = json.loads((d / 'unlock_table.json').read_text(encoding='utf-8'))
        p = run(CASES['B10'] + ['--skin-table', str(d / 'unlock_table.json'), '--ad-unlock-table', str(d / 'ad_unlock_table.json')], d / 'out')
        self.assertEqual(p.returncode, 0, p.stderr)
        s = json.loads((d / 'out' / 'economy_snapshot.json').read_text(encoding='utf-8'))
        skins = [x for x in s['sinks'] if x['kind'] in ('skin', 'background')]
        self.assertEqual(len(skins), sum(1 for it in table['items'] if it.get('unlock') != 'free'))
        self.assertFalse(any(x['id'] == 'skin_placeholder' for x in s['sinks']))  # real rows replace the placeholder
        self.assertFalse(any('make_skin_table' in u for u in s['unknowns']))
        if table.get('economy_policy') != R['ECON-TIER']['policy']:
            self.skipTest('make_skin_table.py still writes %s (W1b not merged); ECON-TIER/ADUNLOCK on merged rows checked by lead on v3'
                          % table.get('economy_policy'))
        rep = pc.economy_audit(s, 'remake')
        self.assertEqual([(r['id'], r['details']) for r in rep['results'] if r['status'] == 'error'], [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
