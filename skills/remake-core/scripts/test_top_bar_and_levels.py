#!/usr/bin/env python3
"""Self-tests for audit_top_bar.py (HUD-01) and make_level_plan.py / audit_level_plan.py (LEVEL-01), user 2026-10-22:
energy with a lightning, a currency that fits the game world (ocean -> pearls), all at the top and updated live; level
games have 70 levels or more (user 2026-10-24: at least 70 passes on both boards, more is fine), difficulty rising step by
step, a map with the total, the level module (user 2026-10-23): a limited level every 10 levels (a big pile of currency;
the limited skin either only on the last one - "final" - or one on every limited level - "every_10", user 2026-10-24),
one seeded random bonus level per block of 10 (very easy, 3x currency); no perfect-clear skins; endless games have no map."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NODE = shutil.which('node')
sys.path.insert(0, str(HERE))
from test_ui_layout_and_copy import mock_dump  # noqa: E402

BAR = {'schema': 'top_bar.v1', 'theme': 'ocean', 'resources': [
    {'kind': 'energy', 'name': 'Energy', 'icon': 'lightning', 'node': 'TopBar/Energy', 'count': 'TopBar/Energy/Count'},
    {'kind': 'currency', 'name': 'Pearls', 'icon': 'pearl', 'node': 'TopBar/Pearls', 'count': 'TopBar/Pearls/Count'},
    {'kind': 'progress', 'name': 'Level', 'icon': 'flag', 'node': 'TopBar/Level', 'count': 'TopBar/Level/Count'}]}
# a short test run: home -> map -> play -> win -> home -> map
RUN = [('good_home+bar', 'home', {'1,250': '1,250', '>12<': '12'}), ('good_map+bar', 'map', {}), ('play', 'other', {}),
       ('good_result', 'result_win', {}), ('good_home+bar', 'home', {'1,250': '1,310', '>12<': '13'}),
       ('good_map+bar', 'map', {'1,250': '1,310', '>12<': '13'})]


def py(script, *args):
    r = subprocess.run([sys.executable, '-B', str(HERE / script)] + [str(a) for a in args], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def picture(path):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (375, 812), (150, 210, 250))
    d = ImageDraw.Draw(im)
    for y in range(0, 812, 4):
        d.line([0, y, 375, y], fill=(150 - y // 12, 200 - y // 20, 250 - y // 30))
    im.save(path)


def plan(root, **kw):
    levels = kw.get('levels', 100)
    args = ['--levels', levels, '--coins', 40, '--currency', 'Pearls',
            '--seed', kw.get('seed', 7), '--out', root / 'assets/resources/config/level_plan.json']
    mode = kw.get('skin_mode', 'final')
    if kw.get('skins', True):
        args += ['--limited-skin', 'hero_limited', '--limited-skin-mode', mode]
    if kw.get('policy'):
        args += ['--policy', kw['policy']]
    for intro in kw.get('intros', ()):
        args += ['--intro', intro]
    code, out = py('make_level_plan.py', *args)
    assert code == 0, out
    p = json.loads((root / 'assets/resources/config/level_plan.json').read_text())
    p['why'] = '100 or more fixed levels cleared one by one'
    (root / 'assets/resources/config/level_plan.json').write_text(json.dumps(p))
    (root / 'docs/economy').mkdir(parents=True, exist_ok=True)
    table = root / 'docs/economy/unlock_table.json'
    code, out = py('make_skin_table.py', '--R', 40, '--levels', '--final-level', levels, '--limited-mode', mode, '--out', table)
    assert code == 0, out
    t = json.loads(table.read_text())
    if not kw.get('skins', True):
        t['items'] = [r for r in t['items'] if not r.get('limited')]
    t['items'] += [{'id': 'map_01', 'group': 'map', 'order': 1, 'rarity': 'common', 'unlock': 'free', 'ads': 0, 'coins': 0},
                   {'id': 'map_02', 'group': 'map', 'order': 2, 'rarity': 'rare', 'unlock': 'level', 'level': p['milestone_every'],
                    'condition': 'clear', 'ads': 0, 'coins': 0}]
    table.write_text(json.dumps(t))
    return p


class Fixture(unittest.TestCase):
    def project(self, run=RUN, bar=BAR, edit=None):
        root = Path(tempfile.mkdtemp(prefix='topbar-'))
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'assets').mkdir()
        folder = root / 'docs/test/run-iphone15'
        folder.mkdir(parents=True)
        plan(root)
        (root / 'docs/top-bar.json').write_text(json.dumps(bar))
        for i, (scene, purpose, swap) in enumerate(run):
            f = mock_dump(folder, 3, scene)
            d = json.loads(f.read_text())
            f.unlink()
            for n in d['nodes']:                      # the counts this page shows at this moment of the run
                if n['path'].endswith('TopBar/Pearls/Count') and '1,250' in swap:
                    n['comps']['label']['string'] = swap['1,250']
                if n['path'].endswith('TopBar/Level/Count') and '>12<' in swap:
                    n['comps']['label']['string'] = swap['>12<']
            d.update(purpose=purpose, screen='%s_%d' % (scene.split('+')[0], i))
            if edit:
                edit(i, d)
            name = '%03d-ui-dump-%s.json' % (i, d['screen'])
            d['screenshot'] = name.replace('-ui-dump-', '-ui-').replace('.json', '.png')
            (folder / name).write_text(json.dumps(d))
            picture(folder / d['screenshot'])
        return root

    def audit(self, root, script='audit_top_bar.py'):
        out = root / ('r-%s.json' % script)
        code, text = py(script, '--project', root, '--out', out)
        r = json.loads(out.read_text())
        return code, r, ' '.join(c['detail'] for c in r['checks'] if not c['passed'])


@unittest.skipUnless(NODE, 'node not installed')
class TopBarTests(Fixture):
    def test_good_bar_passes(self):
        code, r, bad = self.audit(self.project())
        self.assertEqual(code, 0, bad)
        ids = {c['id'] for c in r['checks']}
        for cid in ('themed_currency', 'energy_lightning', 'bar_on_home', 'bar_on_map', 'live_currency', 'live_progress'):
            self.assertIn(cid, ids)

    def test_plain_coin_for_an_ocean_game_fails_unless_explained(self):
        bar = json.loads(json.dumps(BAR))
        bar['resources'][1].update(name='Coins', icon='coin')
        run = [(s.replace('+bar', '+coinbar'), p, w) for s, p, w in RUN]
        code, r, bad = self.audit(self.project(run=run, bar=bar))
        self.assertEqual(code, 1)
        self.assertIn('Pearls', bad)
        bar['resources'][1]['why'] = 'the original game\'s own gold coins (英化 keeps them)'
        self.assertEqual(self.audit(self.project(run=run, bar=bar))[0], 0)

    def test_energy_needs_a_lightning(self):
        bar = json.loads(json.dumps(BAR))
        bar['resources'][0]['icon'] = 'heart'
        code, r, bad = self.audit(self.project(bar=bar))
        self.assertEqual(code, 1)
        self.assertIn('lightning', bad)

    def test_no_bar_on_home_fails(self):
        run = [(s.replace('good_home+bar', 'good_home'), p, w) for s, p, w in RUN]
        code, r, bad = self.audit(self.project(run=run))
        self.assertEqual(code, 1)
        self.assertIn('not found', bad)

    def test_count_not_updated_after_a_win_fails(self):
        run = [(s, p, {}) for s, p, w in RUN]
        code, r, bad = self.audit(self.project(run=run))
        self.assertEqual(code, 1)
        self.assertIn('did not go up', bad)

    def test_currency_bar_in_the_middle_fails(self):
        # user 2026-10-23 (Hazel's Shelf Scramble): "coin 0 / item 1" bar in the middle of the home page
        code, r, bad = self.audit(self.project(run=RUN + [('scattered_home+bar', 'home', {})]))
        self.assertEqual(code, 1)
        self.assertIn('never in the middle', bad)
        self.assertIn('CoinIcon', bad)
        good = {c['id']: c['passed'] for c in self.audit(self.project())[1]['checks']}
        self.assertTrue(good['currency_only_at_top'])            # result page "+50" coins and shop prices are content

    def test_bar_in_the_capsule_corner_or_low_fails(self):
        def move(i, d):
            for n in d['nodes']:
                if '/TopBar/Level' in n['path']:
                    n['screen'] = [0.80, 0.02, 0.18, 0.04]
                if '/TopBar/Energy' in n['path'] and d['purpose'] == 'home':
                    n['screen'] = [0.04, 0.30, 0.2, 0.04]
        code, r, bad = self.audit(self.project(edit=move))
        self.assertEqual(code, 1)
        self.assertIn('capsule', bad)
        self.assertIn('not at the top', bad)


@unittest.skipUnless(NODE, 'node not installed')
class LevelPlanTests(Fixture):
    def level_audit(self, root):
        return self.audit(root, 'audit_level_plan.py')

    def rewrite(self, root, fn):
        f = root / 'assets/resources/config/level_plan.json'
        p = json.loads(f.read_text())
        fn(p)
        f.write_text(json.dumps(p))

    def test_generated_plan_and_map_pass(self):
        code, r, bad = self.level_audit(self.project())
        self.assertEqual(code, 0, bad)
        self.assertEqual(r['mode'], 'levels')

    def test_generator_always_passes(self):
        root = Path(tempfile.mkdtemp(prefix='plan-'))
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'assets').mkdir()
        for seed in range(1, 40):
            for levels in (100, 107, 121, 200):
                mode = 'every_10' if seed % 3 == 0 else 'final'
                plan(root, levels=levels, seed=seed, skins=seed % 2 == 0, skin_mode=mode)
                for board in ('remake',):                     # user 2026-10-27: 重塑 >= 100
                    out = root / 'r.json'
                    py('audit_level_plan.py', '--project', root, '--out', out, '--board', board)
                    failed = [c for c in json.loads(out.read_text())['checks'] if not c['passed'] and c['id'] != 'map_page']
                    self.assertEqual(failed, [], (seed, levels, mode, board))

    def test_map_must_show_the_total(self):
        def drop(i, d):
            for n in d['nodes']:
                if n['path'].endswith('Progress'):
                    n['comps']['label']['string'] = 'Level 12'
        code, r, bad = self.level_audit(self.project(edit=drop))
        self.assertEqual(code, 1)
        self.assertIn('in total', bad)

    def test_level_game_without_a_map_fails(self):
        run = [x for x in RUN if x[1] != 'map']
        code, r, bad = self.level_audit(self.project(run=run))
        self.assertEqual(code, 1)
        self.assertIn('needs a map page', bad)

    def test_endless_game_has_no_map(self):
        root = self.project()
        (root / 'assets/resources/config/level_plan.json').write_text(json.dumps(
            {'schema': 'level_plan.v1', 'mode': 'endless', 'why': 'one run, the score keeps growing'}))
        code, r, bad = self.level_audit(root)
        self.assertEqual(code, 1)
        self.assertIn('endless games have no level map', bad)
        for f in (root / 'docs/test').rglob('*good_map*'):
            f.unlink()
        self.assertEqual(self.level_audit(root)[0], 0)

    def test_limited_level_mistakes_fail(self):
        root = self.project()

        def spoil(p):
            lv = {r['level']: r for r in p['levels']}
            lv[40]['reward'] = {'type': 'coins', 'amount': 50}           # less than the 5 levels before it
            lv[60]['reward'] = {'type': 'skin', 'id': 'hero_05'}          # only the last limited level gives a skin
            lv[100]['reward'] = {'type': 'coins', 'amount': 5000}         # ... and it gives the limited skin
            lv[33]['type'] = 'milestone'                                 # limited level in the wrong place
        self.rewrite(root, spoil)
        t = root / 'docs/economy/unlock_table.json'
        data = json.loads(t.read_text())
        data['items'].append({'id': 'skin_lv45', 'group': 'skin', 'order': 80, 'rarity': 'epic', 'unlock': 'level', 'level': 45,
                              'condition': 'clear', 'ads': 0, 'coins': 0})      # a level skin no limited level gives
        data['items'].append({'id': 'skin_p10', 'group': 'skin', 'order': 81, 'rarity': 'rare', 'unlock': 'level', 'level': 10,
                              'condition': 'perfect', 'ads': 0, 'coins': 0})      # user 2026-10-22: no perfect-clear skins
        t.write_text(json.dumps(data))
        code, r, bad = self.level_audit(root)
        self.assertEqual(code, 1)
        for words in ('below the sum', 'only the last limited level gives a skin', 'gives the limited skin hero_limited',
                      'exactly levels', 'must be the reward of its limited', 'no perfect-clear skins'):
            self.assertIn(words, bad)
        root = self.project()                                            # the finale skin must not be a shop skin
        self.rewrite(root, lambda p: p['levels'][99].update(reward={'type': 'skin', 'id': 'hero_05'}))
        self.assertIn('cannot be bought', self.level_audit(root)[2])

    def test_difficulty_rises_without_spikes(self):
        """Plans without difficulty_policy keep the old strict rule (step by step, no spikes)."""
        def strict(p):
            p.pop('difficulty_policy', None)
            for r in p['levels']:
                if r['type'] != 'bonus':
                    r['difficulty'] = round(1 + (r['level'] - 1) * 0.1, 2)
        def project():
            root = self.project()
            plan(root, policy='mild')                    # same bonus places as an old plan without a policy
            return root
        root = project()
        self.rewrite(root, strict)
        self.assertEqual(self.level_audit(root)[0], 0, self.level_audit(root)[2])
        self.rewrite(root, lambda p: p['levels'][39].update(difficulty=30))        # level 40 (limited) jumps
        self.assertIn('no spikes', self.level_audit(root)[2])
        root = project()
        self.rewrite(root, strict)
        self.rewrite(root, lambda p: p['levels'][23].update(difficulty=0.5))       # level 24 easier than 23
        bad = self.level_audit(root)[2]
        self.assertIn('easier', bad)
        # 英化: the original levels keep their order; only the added levels ("new": true) must rise
        (root / 'docs/board.txt').write_text('localize')
        self.rewrite(root, lambda p: [r.update(new=True) for r in p['levels'] if r['level'] > 50])
        self.assertNotIn('easier', self.level_audit(root)[2])

    def test_mild_wave_policy(self):
        """Earlier 2026-10-27 option (--policy mild): rising trend, small lift on limited levels, short dip after them."""
        def project():
            root = self.project()
            plan(root, policy='mild')
            return root
        root = project()
        p = json.loads((root / 'assets/resources/config/level_plan.json').read_text())
        self.assertEqual(p['difficulty_policy'], 'rising-mild-wave.v1')
        by = {r['level']: r for r in p['levels']}
        self.assertLess(by[11]['difficulty'], by[10]['difficulty'])             # recovery dip is generated
        self.assertEqual(self.level_audit(root)[0], 0)
        root = project()                                                   # a dip in mid-chapter is refused
        self.rewrite(root, lambda p: p['levels'][15].update(difficulty=p['levels'][14]['difficulty'] - 0.1))
        self.assertIn('dips only right after a limited level', self.level_audit(root)[2])
        root = project()                                                   # ... unless it is tagged intro
        self.rewrite(root, lambda p: p['levels'][15].update(difficulty=p['levels'][14]['difficulty'] - 0.1, tags=['intro']))
        self.assertEqual(self.level_audit(root)[0], 0)
        root = project()                                                   # a deep crash after a limited level
        self.rewrite(root, lambda p: p['levels'][10].update(difficulty=1.0))
        self.assertIn('at most 3 usual steps', self.level_audit(root)[2])
        root = project()                                                   # strict rule stays for old plans
        self.rewrite(root, lambda p: p.pop('difficulty_policy'))
        self.assertIn('easier', self.level_audit(root)[2])

    def test_finale_is_limited_and_last_chapter_short(self):
        p = json.loads((self.project() / 'assets/resources/config/level_plan.json').read_text())
        lim = [r['level'] for r in p['levels'] if r['type'] == 'milestone']
        self.assertEqual((p['total_levels'], lim), (100, list(range(10, 101, 10))))
        bonus = [r['level'] for r in p['levels'] if r['type'] == 'bonus']
        self.assertEqual([(b - 1) // 10 for b in bonus], list(range(10)))         # exactly one per block of 10
        self.assertGreater(len({(b - 1) % 10 for b in bonus}), 1)                 # not the same place every time
        self.assertTrue(any(91 <= r['level'] <= 100 and r['type'] == 'bonus' for r in p['levels']))
        self.assertNotIn(4, bonus)                                                # level 4 is the first spike

    def test_more_than_70_passes_on_both_boards(self):
        """重塑 100 or more passes (user 2026-10-27); a game with more levels is not cut."""
        root = self.project()
        plan(root, levels=110, seed=7)
        for board in ('remake',):
            (root / 'docs/board.txt').write_text(board)
            out = root / 'r.json'
            py('audit_level_plan.py', '--project', root, '--out', out)
            checks = {c['id']: c for c in json.loads(out.read_text())['checks']}
            self.assertTrue(checks['levels_at_least_70']['passed'], (board, checks['levels_at_least_70']))
            failed = [c for c in checks.values() if not c['passed'] and c['id'] not in ('map_shows_total',)]
            self.assertEqual(failed, [], board)

    def test_every_10_limited_skins(self):
        """User 2026-10-24: every limited level may give its own limited skin (format every_10)."""
        root = self.project()
        plan(root, levels=100, seed=11, skin_mode='every_10')
        out = root / 'r.json'
        py('audit_level_plan.py', '--project', root, '--out', out)
        r = json.loads(out.read_text())
        bad = [c for c in r['checks'] if not c['passed'] and c['id'] != 'map_shows_total']
        self.assertEqual(bad, [])
        self.assertIn('every_10', next(c['detail'] for c in r['checks'] if c['id'] == 'limited_skin_mode'))
        p = json.loads((root / 'assets/resources/config/level_plan.json').read_text())
        self.assertEqual([x['reward']['id'] for x in p['levels'] if x['type'] == 'milestone'],
                         ['hero_limited_%d' % n for n in range(10, 101, 10)])
        t = json.loads((root / 'docs/economy/unlock_table.json').read_text())
        lim = [x for x in t['items'] if x.get('limited')]
        self.assertEqual([x['award_level'] for x in lim], list(range(10, 101, 10)))
        self.assertTrue(all(x['unlock'] == 'coins' and x['coins'] == 50 * t['normal_level_coins'] and x['ads'] == 0 for x in lim))
        self.assertEqual([x['order'] for x in lim], list(range(1, 11)))                # all first in the list

        def coins_on_40(p):
            row = next(x for x in p['levels'] if x['level'] == 40)
            row['reward'] = {'type': 'coins', 'amount': 99999}
        self.rewrite(root, lambda p: (p.update(limited_skin_mode='every_10'), coins_on_40(p)))
        bad = self.level_audit(root)[2]
        self.assertIn('format "every_10": every limited level gives its own limited skin', bad)
        self.rewrite(root, lambda p: next(x for x in p['levels'] if x['level'] == 40).update(
            reward={'type': 'skin', 'id': 'hero_limited_30'}))
        self.assertIn('already the reward of level 30', self.level_audit(root)[2])
        self.rewrite(root, lambda p: p.update(limited_skin_mode='weekly'))
        self.assertIn('must be "final" or "every_10"', self.level_audit(root)[2])

    def test_fewer_than_70_levels_fails(self):
        root = self.project()

        def cut(p):
            p['levels'] = p['levels'][:40]
            p['total_levels'] = 40
        self.rewrite(root, cut)
        code, r, bad = self.level_audit(root)
        self.assertEqual(code, 1)
        self.assertIn('this board needs 100 levels or more', bad)
        self.assertIn('add at least 60', bad)
        self.assertNotEqual(py('make_level_plan.py', '--levels', 99, '--out', root / 'x.json')[0], 0)
        # 英化 keeps its own minimum of 70 (user 2026-10-27: only 重塑 moves to 100)
        from make_level_plan import make
        from audit_level_plan import audit_plan
        data = make(80, 50, None, 19, 'Coins')
        data['why'] = 'Localized game keeps its original eighty levels.'
        for board, expected in (('localize', True), ('remake', False)):
            checks = {}
            audit_plan(data, None, lambda name, passed, detail: checks.update({name: passed}), board)
            self.assertEqual(checks['levels_at_least_70'], expected, board)

    def test_wave_tiers_policy(self):
        """User 2026-10-27: wave-tiers.v1 - tutorial 1-3, spike 4, recovery 5-9, exam 10, tiered irregular wave after."""
        root = self.project()
        plan(root, intros=['23:wind', '51:ice'])
        p = json.loads((root / 'assets/resources/config/level_plan.json').read_text())
        self.assertEqual(p['difficulty_policy'], 'wave-tiers.v1')
        by = {r['level']: r for r in p['levels']}
        self.assertEqual([by[n]['tier'] for n in (1, 2, 3)], ['tutorial'] * 3)
        self.assertIn(by[4]['tier'], ('high', 'extreme'))
        rec = [by[n]['difficulty'] for n in range(5, 10) if by[n]['type'] != 'bonus']
        self.assertEqual(rec, sorted(rec, reverse=True))
        self.assertEqual((by[23]['tier'], by[23]['role']), ('low', 'intro'))
        self.assertEqual(self.level_audit(root)[0], 0, self.level_audit(root)[2])
        normal = [r for r in p['levels'] if r['level'] > 10 and r['type'] != 'bonus']
        tiers = [r['tier'] for r in normal]
        self.assertTrue(all(not (a in ('high', 'extreme') and b in ('high', 'extreme')) for a, b in zip(tiers, tiers[1:])))
        for spoil, words in [
                (lambda p: p['levels'][3].update(tier='low', difficulty=0.9), 'level 4 is the first spike'),
                (lambda p: next(r for r in p['levels'] if r['level'] == 23).update(tier='high', difficulty=9.0), 'introduces a mechanic'),
                (lambda p: [r.update(tier='extreme', difficulty=round(r['difficulty'] * 3, 2)) for r in p['levels']
                            if 31 <= r['level'] <= 34 and r['type'] == 'normal'], 'two high/extreme levels in a row')]:
            root = self.project()
            plan(root, intros=['23:wind', '51:ice'])
            self.rewrite(root, spoil)
            self.assertIn(words, self.level_audit(root)[2])

    def test_regular_or_bad_bonus_levels_fail(self):
        root = self.project()

        def regular(p):
            for r in p['levels']:
                if r['type'] == 'bonus':
                    r['type'] = 'normal'
                    r['coins'] = 40 + 5 * ((r['level'] - 1) // 10)
            for r in p['levels']:
                if r['level'] % 10 == 5:
                    r.update(type='bonus', coins=3 * r['coins'], difficulty=0.5)
        self.rewrite(root, regular)
        code, r, bad = self.level_audit(root)
        self.assertEqual(code, 1)
        self.assertIn('not the places drawn from seed', bad)

        def hard(p):
            for r in p['levels']:
                if r['type'] == 'bonus':
                    r['difficulty'] = 99
                    r['coins'] = 1
            p['levels'][1]['type'] = 'bonus'
        root = self.project()
        self.rewrite(root, hard)
        bad = self.level_audit(root)[2]
        for words in ('make it easy', 'needs 3x', 'not in levels 1-3', 'exactly one per block'):
            self.assertIn(words, bad)
        root = self.project()                                            # 2x is not enough any more (user 2026-10-23: 3x)
        self.rewrite(root, lambda p: [r.update(coins=r['coins'] * 2 // 3) for r in p['levels'] if r['type'] == 'bonus'])
        self.assertIn('needs 3x', self.level_audit(root)[2])


if __name__ == '__main__':
    unittest.main(verbosity=2)
