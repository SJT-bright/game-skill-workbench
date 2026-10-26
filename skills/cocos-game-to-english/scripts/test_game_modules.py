#!/usr/bin/env python3
"""Self-tests for the built-in modules (user 2026-10-23, both boards): the skin module table (make_skin_table.py +
audit_acquisition_progression.py), the universal ad module (AdRewards.ts + modules_harness.mjs) and
audit_game_modules.py (decision, removed ranking / check-in, button audit, limited-skin route) and the 10-frame gift box,
which is an art-stage row of art_check.py since 2026-10-24. Good passes, broken fails."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
MODULE = HERE.parent / 'assets' / 'modules' / 'AdRewards.ts'
NODE = shutil.which('node')


def py(script, *args):
    r = subprocess.run([sys.executable, '-B', str(HERE / script)] + [str(a) for a in args], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def skin_table(tmp, *args, profile="legacy-2r"):
    out = Path(tmp) / 'unlock_table.json'
    code, text = py('make_skin_table.py', '--R', 50, *(args or ('--levels',)), *(['--price-profile', profile] if profile else []), '--out', out)
    assert code == 0, text
    return json.loads(out.read_text())


def unlock_audit(t):
    tmp = Path(tempfile.mkdtemp(prefix='skinmod-'))
    try:
        (tmp / 't.json').write_text(json.dumps(t))
        code, _ = py('audit_acquisition_progression.py', '--table', tmp / 't.json', '--report', tmp / 'r.json')
        return code, json.loads((tmp / 'r.json').read_text())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class SkinModuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='skins-')
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_generated_tables_pass(self):
        for args in (('--levels',), ('--endless',), ('--levels', '--no-backgrounds'), ('--endless', '--no-backgrounds')):
            t = skin_table(self.tmp, *args)
            code, r = unlock_audit(t)
            self.assertEqual(code, 0, (args, r['errors']))
        t = skin_table(self.tmp)
        skins = [x for x in t['items'] if x['group'] == 'skin']
        self.assertEqual((len(skins), sum(x['group'] == 'background' for x in t['items'])), (20, 10))
        self.assertTrue(skins[0]['limited'])                                   # the limited skin comes first (dimmed)
        prices = [x['coins'] for x in skins if x['unlock'] == 'coins']
        gaps = sorted({b - a for a, b in zip(prices, prices[1:])})
        self.assertEqual((prices[0], gaps), (100, [50, 200, 500, 1000]))       # user: +50, +200, +500, +1000

    def test_ordinary_level_profile(self):
        for args in (('--levels',), ('--endless',), ('--levels', '--normal-level-coins', '30', '--tier-levels', '8,12,16,20')):
            t = skin_table(self.tmp, *args, profile=None)
            self.assertEqual(t['price_profile'], 'ordinary-levels')
            self.assertEqual(unlock_audit(t)[0], 0)
            for row in t['items']:
                if row['unlock'] == 'coins':
                    self.assertEqual(row['coins'], t['normal_level_coins'] * t['price_level_targets'][row['rarity']])
            next(x for x in t['items'] if x['id'] == 'hero_02')['coins'] = 100
            self.assertIn('ordinary levels', ' '.join(unlock_audit(t)[1]['errors']))
        legacy = skin_table(self.tmp)
        legacy.pop('price_profile')
        self.assertEqual(unlock_audit(legacy)[0], 0)

    def test_broken_skin_tables_fail(self):
        def item(t, iid):
            return next(x for x in t['items'] if x['id'] == iid)
        cases = {
            'only 19 skins': (lambda t: t['items'].remove(item(t, 'hero_19')), 'exactly 20 items'),
            'ad-only skin': (lambda t: item(t, 'hero_03').update(unlock='ads', ads=2, coins=0), 'coins only'),
            'flat prices': (lambda t: item(t, 'hero_10').update(coins=item(t, 'hero_09')['coins'] + 50), 'the step for rare'),
            'cheap first skin': (lambda t: item(t, 'hero_02').update(coins=400), 'first item for sale costs 2R'),
            'bonus outside the band': (lambda t: item(t, 'hero_19').update(bonus={'type': 'coins', 'pct': 20}), 'outside 33-50'),
            'no bonus': (lambda t: item(t, 'bg_02').pop('bonus'), 'needs a coin bonus'),
            'limited skin not first': (lambda t: item(t, 'hero_limited').update(order=99), 'first in the list'),
            'two free skins': (lambda t: item(t, 'hero_02').update(unlock='free', coins=0, bonus=None), 'exactly one free'),
            'limited bonus not the top': (lambda t: item(t, 'hero_limited').update(bonus={'type': 'coins', 'pct': 45}), 'outside 51-60'),
            'league skin (removed)': (lambda t: t['items'].append({'id': 'lg1', 'group': 'skin', 'order': 50, 'rarity': 'rare',
                                                                   'unlock': 'league', 'ads': 0, 'coins': 0}), 'no ranking'),
            'check-in skin (removed)': (lambda t: t['items'].append({'id': 'ck1', 'group': 'skin', 'order': 51, 'rarity': 'rare',
                                                                     'unlock': 'checkin', 'ads': 0, 'coins': 0}), 'no 7-day check-in'),
            'skins without the module': (lambda t: t.pop('module'), 'make_skin_table.py'),
        }
        for name, (change, words) in cases.items():
            t = skin_table(self.tmp)
            change(t)
            code, r = unlock_audit(t)
            self.assertNotEqual(code, 0, name)
            if words:
                self.assertIn(words, ' '.join(r['errors']), name)
        t = skin_table(self.tmp, '--endless')
        next(x for x in t['items'] if x.get('limited')).update(ads=3)
        self.assertIn('5-10 ads', ' '.join(unlock_audit(t)[1]['errors']))

    def test_every_10_limited_skins(self):
        """User 2026-10-24: one limited skin per limited level is allowed too (19 + N skins, all limited ones first)."""
        for final, n in ((70, 7), (75, 7), (85, 8)):
            t = skin_table(self.tmp, '--levels', '--final-level', final, '--limited-mode', 'every_10')
            code, r = unlock_audit(t)
            self.assertEqual(code, 0, r['errors'])
            skins = sorted((x for x in t['items'] if x['group'] == 'skin'), key=lambda x: x['order'])
            self.assertEqual(len(skins), 19 + n)
            self.assertTrue(all(x.get('limited') for x in skins[:n]))
            self.assertEqual(t['limited_mode'], 'every_10')
        t = skin_table(self.tmp, '--levels', '--limited-mode', 'every_10')
        next(x for x in t['items'] if x['id'] == 'hero_limited_30').update(order=40)
        self.assertIn('first in the list', ' '.join(unlock_audit(t)[1]['errors']))
        t = skin_table(self.tmp, '--levels', '--limited-mode', 'every_10')
        next(x for x in t['items'] if x['id'] == 'hero_limited_30').update(unlock='coins', coins=5000, level=None)
        self.assertNotEqual(unlock_audit(t)[0], 0)
        self.assertNotEqual(py('make_skin_table.py', '--R', 50, '--levels', '--final-level', 60, '--out', Path(self.tmp) / 'x.json')[0], 0)


def frames(folder, n=10, same=False, size=256):
    from PIL import Image, ImageDraw
    folder.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        k = 0 if same else i
        d.rectangle([40, 90 - k * 3, 216, 220], fill=(230, 80, 90, 255))
        d.rectangle([30, 70 - k * 4, 226, 110 - k * 4], fill=(250, 200, 60, 255))
        im.save(folder / ('gift_%02d.png' % (i + 1)))


@unittest.skipUnless(NODE, 'Node.js is needed for the ad module simulation')
class GameModulesAuditTests(unittest.TestCase):
    def project(self, board='localize', change=None, mode='levels'):
        root = Path(tempfile.mkdtemp(prefix='modules-'))
        self.addCleanup(shutil.rmtree, root, True)
        cfg = root / 'assets/resources/config'
        cfg.mkdir(parents=True)
        (root / 'docs').mkdir()
        (root / 'docs/board.txt').write_text(board)
        shutil.copy(MODULE, root / 'assets/AdRewards.ts')
        code, text = py('make_skin_table.py', '--R', 50, '--' + mode, '--out', cfg / 'unlock_table.json')
        assert code == 0, text
        plan = {'schema': 'level_plan.v1', 'mode': mode, 'why': 'test'}
        if mode == 'levels':
            plan.update(total_levels=70, milestone_every=10, levels=[])
        (cfg / 'level_plan.json').write_text(json.dumps(plan))
        frames(root / 'assets/resources/ui/gift')
        dec = {'schema': 'game_modules.v1', 'asked': 'optimisation plan, user 2026-10-23: skins yes',
               'gameplay': 'match-3 on a shelf', 'currency': {'name': 'Pearls', 'icon': 'pearl'},
               'skins': {'suitable': True, 'why': 'a hamster hero and a room scene', 'user_choice': True, 'backgrounds': True},
               'gift_box': {'frames_dir': 'assets/resources/ui/gift'},
               'button_audit': [{'page': 'home', 'button': 'Play', 'works': True, 'keep': True, 'why': 'starts the level'},
                                {'page': 'home', 'button': 'More Games', 'works': True, 'keep': False, 'why': 'cross-promotion'},
                                {'page': 'home', 'button': 'Rank', 'works': False, 'keep': False, 'why': 'leaderboard, removed'}]}
        if change:
            change(root, dec)
        (root / 'docs/modules.json').write_text(json.dumps(dec))
        return root

    def audit(self, root, *extra):
        out = root / 'r.json'
        code, text = py('audit_game_modules.py', '--project', root, '--out', out, *extra)
        r = json.loads(out.read_text())
        return code, r, ' '.join(c['detail'] for c in r['checks'] if not c['passed'])

    def test_good_projects_pass(self):
        for board, mode in (('localize', 'levels'), ('remake', 'endless')):
            code, r, bad = self.audit(self.project(board, mode=mode))
            self.assertEqual(code, 0, (board, mode, bad))
            self.assertTrue(r['decision']['skins'])
            self.assertTrue(any(c['id'] == 'sim_gift_grows_with_skins' and c['passed'] for c in r['checks']))

        def no_skins(root, dec):
            dec['skins'] = {'suitable': False, 'why': 'a puzzle without a hero', 'user_choice': False, 'backgrounds': False}
            (root / 'assets/resources/config/unlock_table.json').write_text(json.dumps({'coins_per_ad': 50, 'items': []}))
        code, r, bad = self.audit(self.project('remake', no_skins))
        self.assertEqual(code, 0, bad)
        self.assertFalse(r['decision']['skins'])

    def test_gift_box_is_an_art_stage_row(self):
        """User 2026-10-24: the 10-frame gift box is checked by art_check.py (art stage), not by MOD-01 / the final audit."""
        sys.path.insert(0, str(HERE))
        from art_check import gift_box_row
        root = self.project()
        code, r, bad = self.audit(root)
        self.assertNotIn('gift_box_frames', [c['id'] for c in r['checks']])
        self.assertIs(gift_box_row(root)[1], True)
        (root / 'assets/resources/ui/gift/gift_10.png').unlink()
        title, ok, detail = gift_box_row(root)
        self.assertIs(ok, False)
        self.assertIn('10-frame animation', detail)
        self.assertEqual(self.audit(root)[0], 0)                               # MOD-01 no longer looks at the frames
        frames(root / 'assets/resources/ui/gift', same=True)
        self.assertIn('animate it', gift_box_row(root)[2])
        (root / 'docs/modules.json').unlink()
        self.assertIsNone(gift_box_row(root)[1])                               # no design yet: a hint, not blocking

    def test_design_check_runs_the_design_stage(self):
        """User 2026-10-24: design_check.py runs the design-stage audits at 英化 1.5 / 重塑 round 1."""
        root = self.project()
        out = root.parent / (root.name + '-design')
        self.addCleanup(shutil.rmtree, out, True)
        code, text = py('design_check.py', '--project', root, '--out', out)
        rep = json.loads((out / 'design-check.json').read_text())
        rows = {r['check']: r['status'] for r in rep['rows']}
        self.assertEqual(rep['tool'], 'design_check')
        self.assertEqual(rows['内置板块（MOD-01）'], '通过', text)
        self.assertEqual(rows['皮肤数值（ECON-01）'], '通过', text)
        self.assertEqual(rows['排名扩展（RANK-01）'], '通过', text)
        self.assertEqual(rows['可选扩展（FEAT-00）'], '通过', text)
        self.assertEqual(rows['关卡板块（LEVEL-01）'], '需处理', text)        # the fixture plan lists no levels
        self.assertEqual(code, 1)
        self.assertTrue((out / 'design-check.md').is_file())

    def test_every_10_limited_route(self):
        def every_10(root, dec):
            cfg = root / 'assets/resources/config'
            code, text = py('make_skin_table.py', '--R', 50, '--levels', '--limited-mode', 'every_10', '--out', cfg / 'unlock_table.json')
            assert code == 0, text
        code, r, bad = self.audit(self.project(change=every_10))
        self.assertEqual(code, 0, bad)
        self.assertIn('every_10', next(c['detail'] for c in r['checks'] if c['id'] == 'limited_skin_route'))

        def wrong_levels(root, dec):
            every_10(root, dec)
            f = root / 'assets/resources/config/unlock_table.json'
            t = json.loads(f.read_text())
            next(x for x in t['items'] if x['id'] == 'hero_limited_30')['level'] = 35
            f.write_text(json.dumps(t))
        code, r, bad = self.audit(self.project(change=wrong_levels))
        self.assertEqual(code, 1)
        self.assertIn('format every_10', bad)

    def test_missing_or_wrong_designs_fail(self):
        def nodec(root, dec):
            dec.clear()
        cases = {
            'no decision': (nodec, 'docs/modules.json needs'),
            'check-in still there': (lambda root, dec: (root / 'assets/DailyCheckin.ts').write_text('//'), 'no 7-day check-in'),
            'unrequested league code': (lambda root, dec: (root / 'assets/LeagueSim.ts').write_text('//'), 'no ranking'),
            'useless button kept': (lambda root, dec: dec['button_audit'][2].update(keep=True), 'does nothing real'),
            'share kept': (lambda root, dec: dec['button_audit'].append({'page': 'result', 'button': 'Share', 'works': True,
                                                                        'keep': True, 'why': 'posts a picture'}), 'removed feature'),
            'no button audit (英化)': (lambda root, dec: dec.pop('button_audit'), 'list every button'),
            'changed ad module': (lambda root, dec: (root / 'assets/AdRewards.ts').write_text(MODULE.read_text().replace(
                'RESULT_AD_MULTIPLIER = 2', 'RESULT_AD_MULTIPLIER = 3')), 'differs from the skill copy'),
            'skins chosen, no table': (lambda root, dec: (root / 'assets/resources/config/unlock_table.json').write_text(
                json.dumps({'coins_per_ad': 50, 'items': []})), 'make_skin_table.py'),
            'suitable but dropped by the AI': (lambda root, dec: dec.update(asked='AI decided') or dec['skins'].update(user_choice=False),
                                               'default is yes'),
            'limited skin on the wrong level': (lambda root, dec: (root / 'assets/resources/config/level_plan.json').write_text(json.dumps(
                {'schema': 'level_plan.v1', 'mode': 'levels', 'why': 't', 'total_levels': 80, 'milestone_every': 10, 'levels': []})),
                'last limited level 80'),
        }
        for name, (change, words) in cases.items():
            code, r, bad = self.audit(self.project('localize', change))
            self.assertEqual(code, 1, name)
            self.assertIn(words, bad, name)
        # the remake board needs no audit of original buttons
        code, r, bad = self.audit(self.project('remake', lambda root, dec: dec.pop('button_audit')))
        self.assertEqual(code, 0, bad)

    def test_legacy_league_decision_cannot_reenable_removed_ranking(self):
        def extensions(root, dec):
            (root / 'docs/league').mkdir()
            (root / 'docs/league/decision.json').write_text(json.dumps({'decision': 'keep_original'}))
            (root / 'docs/features.json').write_text(json.dumps({'daily_checkin': True}))
            for name in ('LeagueSim.ts', 'DailyCheckin.ts'):
                (root / 'assets' / name).write_text('// extension audited separately')
            dec['button_audit'].extend([{'page': 'home', 'button': name, 'works': True, 'keep': True,
                                        'why': 'user requested extension'} for name in ('League', 'Check-in')])
        code, report, bad = self.audit(self.project(change=extensions))
        self.assertEqual(code, 1, bad)
        self.assertIn('no ranking', bad)

    def test_core_record_produces_default_disabled_extension_reports(self):
        root = self.project()
        for script in ('audit_league.py', 'audit_optional_features.py'):
            out = root / (script + '.json')
            code, text = py(script, '--project', root, '--out', out)
            self.assertEqual(code, 0, text)
            report = json.loads(out.read_text())
            self.assertTrue(report['passed'])
        (root / 'assets/DailyCheckin.ts').write_text('// unrequested leftover')
        code, text = py('audit_optional_features.py', '--project', root, '--out', root / 'disabled.json')
        self.assertNotEqual(code, 0, text)

    def test_simulation_catches_a_broken_module(self):
        root = self.project()
        broken = root / 'broken.ts'
        broken.write_text(MODULE.read_text().replace('return round5(Math.max(R, GIFT_SHARE * p) + GIFT_PER_10_LEVELS',
                                                     'return round5(Math.max(R, 0 * p) + 0').replace('if (g.busy) return false;', ''))
        shutil.copy(broken, root / 'assets/AdRewards.ts')
        code, r, bad = self.audit(root, '--reference', broken)
        failed = {c['id'] for c in r['checks'] if not c['passed']}
        self.assertEqual(code, 1)
        self.assertTrue({'sim_gift_grows_with_levels', 'sim_gift_grows_with_skins', 'sim_ad_gate_single_fire'} <= failed, failed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
