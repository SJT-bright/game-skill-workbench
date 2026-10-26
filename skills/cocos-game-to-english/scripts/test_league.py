#!/usr/bin/env python3
"""Self-tests for the Weekly League (audit_league.py + league_harness.mjs + LeagueSim.ts).

Each rule is calibrated: a good project passes, and a version broken on purpose fails on the right check.
Needs Node.js (the league module is JavaScript); skipped without it.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / 'assets' / 'league'
NODE = shutil.which('node')


def unlock_table():
    items = [{'id': 'skin_01', 'group': 'skin', 'order': 1, 'rarity': 'common', 'unlock': 'free', 'ads': 0, 'coins': 0},
             {'id': 'skin_02', 'group': 'skin', 'order': 2, 'rarity': 'common', 'unlock': 'ads', 'ads': 1, 'coins': 0},
             {'id': 'skin_03', 'group': 'skin', 'order': 3, 'rarity': 'rare', 'unlock': 'coins', 'ads': 0, 'coins': 150},
             {'id': 'skin_04', 'group': 'skin', 'order': 4, 'rarity': 'epic', 'unlock': 'ads_coins', 'ads': 3, 'coins': 120},
             {'id': 'skin_05', 'group': 'skin', 'order': 5, 'rarity': 'legendary', 'unlock': 'ads_or_coins', 'ads': 8, 'coins': 400}]
    for i in range(1, 11):
        items.append({'id': 'league_skin_%02d' % i, 'group': 'skin', 'order': 20 + i, 'rarity': 'rare' if i < 4 else 'epic' if i < 8 else 'legendary',
                      'unlock': 'league', 'ads': 0, 'coins': 0})
    return {'coins_per_ad': 50, 'coins_per_level': 50, 'items': items}


DECISION = {'schema': 'league_decision.v1', 'decision': 'add', 'game_type': 'level_progression', 'metric': 'levels',
            'answers': {'win_lose_or_score': True, 'ever_growing_number': True, 'enough_content': True, 'comparable': True},
            'evidence': {'win_lose_or_score': 'GAME_DESIGN.md: clear the board to win, 3 stars', 'ever_growing_number': 'levels cleared',
                         'enough_content': '120 levels in levels/', 'comparable': 'same levels for everyone'}}


class LeagueTests(unittest.TestCase):
    def make(self, board='remake', decision=None, ui_text='League rivals are computer players.', league=True):
        root = Path(tempfile.mkdtemp(prefix='league-test-'))
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'assets/scripts').mkdir(parents=True)
        (root / 'assets/resources/config').mkdir(parents=True)
        (root / 'docs/league').mkdir(parents=True)
        (root / 'docs/board.txt').write_text(board)
        (root / 'docs/league/decision.json').write_text(json.dumps(decision or DECISION))
        if league:
            shutil.copy(ASSETS / 'LeagueSim.ts', root / 'assets/scripts/LeagueSim.ts')
            shutil.copy(ASSETS / 'league-config.json', root / 'assets/resources/config/league-config.json')
        (root / 'assets/resources/config/unlock_table.json').write_text(json.dumps(unlock_table()))
        (root / 'assets/scripts/LeagueUi.ts').write_text('this.title.string = "Weekly League";\nthis.rules.string = %s;\n' % json.dumps(ui_text))
        return root

    def audit(self, root, *extra):
        out = root.parent / (root.name + '-report.json')
        self.addCleanup(lambda: out.unlink(missing_ok=True))
        r = subprocess.run([sys.executable, '-B', str(HERE / 'audit_league.py'), '--project', str(root), '--out', str(out), *extra],
                           capture_output=True, text=True)
        rep = json.loads(out.read_text()) if out.exists() else None
        return r.returncode, rep, {c['id']: c for c in (rep or {}).get('checks', [])}

    def harness(self, module_text=None, cfg=None):
        tmp = Path(tempfile.mkdtemp(prefix='league-h-'))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / 'L.mjs').write_text(module_text or (ASSETS / 'LeagueSim.ts').read_text())
        c = json.loads((ASSETS / 'league-config.json').read_text())
        c.update(cfg or {})
        (tmp / 'c.json').write_text(json.dumps(c))
        r = subprocess.run([NODE, str(HERE / 'league_harness.mjs'), str(tmp / 'L.mjs'), str(tmp / 'c.json')],
                           capture_output=True, text=True, env=dict(os.environ, TZ='UTC'))
        return {c['id']: c['passed'] for c in json.loads(r.stdout)['checks']}

    @unittest.skipUnless(NODE, 'node not installed')
    def test_good_remake_project_passes(self):
        code, rep, c = self.audit(self.make())
        self.assertEqual(code, 0, json.dumps([x for x in rep['checks'] if not x['passed']], ensure_ascii=False))
        self.assertEqual(rep['decision'], 'add')
        self.assertGreaterEqual(rep['checked'], 15)

    @unittest.skipUnless(NODE, 'node not installed')
    def test_broken_module_is_caught_by_the_simulation(self):
        src = (ASSETS / 'LeagueSim.ts').read_text()
        mutants = {
            'drop_rate': src.replace('< cfg.drop.chance) {', '< cfg.drop.chance * 2) {'),
            'never_first': src.replace('return cfg.best_rank + (st.start_rank - cfg.best_rank)', 'return 1 + (st.start_rank - 1)')
                              .replace('after = Math.max(after, cfg.best_rank);', ''),
            'rivals_follow': src.replace('const anchor = Math.max(P, cfg.gain.win);', 'const anchor = cfg.gain.win * 50;'),
            'rise_each_round': src.replace('if (after >= before && before > cfg.min_step_above_rank) after = before - 1;', ''),
            'deterministic_after_reload': src.replace("rand(st.seed, 'drop', st.week, st.rounds)", 'Math.random()'),
            'weekly_rewards': src.replace('if (!skin) coins += cfg.skin_fallback_coins;', ''),
        }
        for check, text in mutants.items():
            self.assertNotEqual(text, src, check)
            self.assertFalse(self.harness(text)[check], check + ' should fail on the broken module')
        self.assertTrue(all(self.harness().values()))

    @unittest.skipUnless(NODE, 'node not installed')
    def test_rise_check_bites(self):
        # a config without the minimum step and a flat curve leaves rounds with no rise while far from the top
        self.assertFalse(self.harness((ASSETS / 'LeagueSim.ts').read_text().replace(
            'if (after >= before && before > cfg.min_step_above_rank) after = before - 1;', ''),
            {'curve': {'half_points': 5000, 'power': 0.8}})['rise_each_round'])

    @unittest.skipUnless(NODE, 'node not installed')
    def test_config_rules(self):
        self.assertFalse(self.harness(cfg={'drop': {'chance': 0.08, 'min_pct': 0.004, 'max_pct': 0.015, 'min': 1, 'max': 150, 'grace_rounds': 3}})['config_valid'])
        self.assertFalse(self.harness(cfg={'best_rank': 1})['config_valid'])
        self.assertFalse(self.harness(cfg={'league_skins': ['a', 'b']})['config_valid'])
        self.assertFalse(self.harness(cfg={'calibration': {'casual': {'rounds_per_week': 10, 'rank_at_least': 9000},
                                                            'regular': {'rounds_per_week': 40, 'rank_between': [1, 5]},
                                                            'heavy': {'rounds_per_week': 120, 'rank_at_most': 2}}})['calibration'])

    @unittest.skipUnless(NODE, 'node not installed')
    def test_edited_module_rejected(self):
        root = self.make()
        f = root / 'assets/scripts/LeagueSim.ts'
        f.write_text(f.read_text().replace('chance', 'chance ') + '\n')
        code, rep, c = self.audit(root)
        self.assertEqual(code, 1)
        self.assertFalse(c['module_unchanged']['passed'])

    @unittest.skipUnless(NODE, 'node not installed')
    def test_real_player_claims_and_missing_rules_line(self):
        code, rep, c = self.audit(self.make(ui_text='Compete with real players nationwide!'))
        self.assertEqual(code, 1)
        self.assertFalse(c['no_real_player_claims']['passed'])
        self.assertFalse(c['rules_say_computer_rivals']['passed'])

    @unittest.skipUnless(NODE, 'node not installed')
    def test_league_skins_must_be_ten_in_table(self):
        root = self.make()
        t = unlock_table()
        t['items'] = t['items'][:-1]
        (root / 'assets/resources/config/unlock_table.json').write_text(json.dumps(t))
        code, rep, c = self.audit(root)
        self.assertFalse(c['league_skins_in_table']['passed'])
        r = subprocess.run([sys.executable, '-B', str(HERE / 'audit_acquisition_progression.py'), '--table',
                            str(root / 'assets/resources/config/unlock_table.json'), '--report', str(root / 'u.json')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn('exactly 10', r.stdout)

    def test_full_table_passes_unlock_audit(self):
        root = Path(tempfile.mkdtemp(prefix='league-u-'))
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'docs/league').mkdir(parents=True)
        (root / 'docs/league/decision.json').write_text(json.dumps({'decision': 'add'}))
        (root / 't.json').write_text(json.dumps(unlock_table()))
        r = subprocess.run([sys.executable, '-B', str(HERE / 'audit_acquisition_progression.py'), '--table', str(root / 't.json'),
                            '--report', str(root / 'u.json')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_decision_must_match_answers(self):
        d = json.loads(json.dumps(DECISION))
        d['answers']['enough_content'] = False
        d['evidence']['enough_content'] = 'only 12 levels'
        code, rep, c = self.audit(self.make(decision=d))
        self.assertFalse(c['decision_matches_answers']['passed'])                    # add although content is too short
        d['decision'] = 'skip'
        code, rep, c = self.audit(self.make(decision=d, league=False))
        self.assertEqual(code, 0, rep)
        d2 = json.loads(json.dumps(DECISION))
        d2['decision'] = 'skip'
        code, rep, c = self.audit(self.make(decision=d2, league=False))
        self.assertEqual(code, 0, rep)  # suitable does not override a disabled decision
        code, rep, c = self.audit(self.make(decision={'schema': 'league_decision.v1', 'decision': 'add'}))
        self.assertFalse(c['decision_recorded']['passed'])

    def test_localize_never_adds_a_league(self):
        none = {'schema': 'league_decision.v1', 'decision': 'none'}
        code, rep, c = self.audit(self.make(board='localize', decision=none, league=False))
        self.assertEqual(code, 0, rep)
        code, rep, c = self.audit(self.make(board='localize', decision=none))
        self.assertEqual(code, 1)
        self.assertFalse(c['default_disabled']['passed'])
        code, rep, c = self.audit(self.make(board='localize', decision=DECISION, league=False))
        self.assertEqual(code, 1, rep)  # explicit add still requires the actual module/config and evidence
        keep = {'schema': 'league_decision.v1', 'decision': 'keep_original', 'notes': 'RankPanel.ts from the original, unchanged'}
        self.assertEqual(self.audit(self.make(board='localize', decision=keep, league=False))[0], 0)

    def test_missing_decision_fails(self):
        root = self.make()
        (root / 'docs/league/decision.json').unlink()
        code, rep, c = self.audit(root)
        self.assertEqual(code, 1)
        self.assertFalse(c['decision_recorded']['passed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
