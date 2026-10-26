#!/usr/bin/env python3
"""Self-tests for the optional features (user 2026-10-22): skin bonuses (audit_acquisition_progression.py) and the
7-day check-in (DailyCheckin.ts + checkin_harness.mjs + audit_optional_features.py). Good passes, broken fails."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / 'assets' / 'checkin'
NODE = shutil.which('node')
BONUS = {'skin_01': None, 'skin_02': 6, 'skin_03': 8, 'skin_04': 14, 'skin_05': 18, 'skin_06': 25, 'skin_07': 40, 'skin_lv10': 22}


def table(bonus=True, checkin=True, change=None):
    items = [{'id': 'skin_01', 'group': 'skin', 'order': 1, 'rarity': 'common', 'unlock': 'free', 'ads': 0, 'coins': 0},
             {'id': 'skin_02', 'group': 'skin', 'order': 2, 'rarity': 'common', 'unlock': 'ads', 'ads': 1, 'coins': 0},
             {'id': 'skin_03', 'group': 'skin', 'order': 3, 'rarity': 'common', 'unlock': 'coins', 'ads': 0, 'coins': 100},
             {'id': 'skin_04', 'group': 'skin', 'order': 4, 'rarity': 'rare', 'unlock': 'ads_or_coins', 'ads': 3, 'coins': 150},
             {'id': 'skin_05', 'group': 'skin', 'order': 5, 'rarity': 'rare', 'unlock': 'coins', 'ads': 0, 'coins': 200},
             {'id': 'skin_06', 'group': 'skin', 'order': 6, 'rarity': 'epic', 'unlock': 'ads_coins', 'ads': 3, 'coins': 120},
             {'id': 'skin_07', 'group': 'skin', 'order': 7, 'rarity': 'legendary', 'unlock': 'ads_or_coins', 'ads': 8, 'coins': 400}]
    if checkin:
        items += [{'id': 'checkin_skin_01', 'group': 'skin', 'order': 9, 'rarity': 'rare', 'unlock': 'checkin', 'ads': 0, 'coins': 0},
                  {'id': 'checkin_skin_02', 'group': 'skin', 'order': 10, 'rarity': 'epic', 'unlock': 'checkin', 'ads': 0, 'coins': 0}]
    for r in items:
        pct = BONUS.get(r['id'], 15 if r['unlock'] == 'checkin' else None)
        if bonus and pct:
            r['bonus'] = {'type': 'coins', 'pct': pct}
    t = {'coins_per_ad': 50, 'coins_per_level': 50, 'items': items}
    if change:
        change(t)
    return t


def unlock_audit(t):
    tmp = Path(tempfile.mkdtemp(prefix='bonus-'))
    try:
        (tmp / 'docs').mkdir()
        (tmp / 'docs/features.json').write_text(json.dumps({'daily_checkin': True}))
        (tmp / 't.json').write_text(json.dumps(t))
        r = subprocess.run([sys.executable, '-B', str(HERE / 'audit_acquisition_progression.py'), '--table', str(tmp / 't.json'),
                            '--report', str(tmp / 'r.json')], capture_output=True, text=True)
        return r.returncode, json.loads((tmp / 'r.json').read_text())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class SkinBonusTests(unittest.TestCase):
    def test_good_bonus_table_passes(self):
        code, r = unlock_audit(table())
        self.assertEqual(code, 0, r['errors'])

    def item(self, t, iid):
        return next(x for x in t['items'] if x['id'] == iid)

    def test_broken_bonus_tables_fail(self):
        cases = {
            'goes down': lambda t: self.item(t, 'skin_05').update(bonus={'type': 'coins', 'pct': 9}),
            'missing on one skin': lambda t: self.item(t, 'skin_04').pop('bonus'),
            'above the cap': lambda t: self.item(t, 'skin_07').update(bonus={'type': 'coins', 'pct': 80}),
            'mixed types': lambda t: self.item(t, 'skin_06').update(bonus={'type': 'moves', 'amount': 2}),
            'not rising with rarity': lambda t: self.item(t, 'skin_04').update(bonus={'type': 'coins', 'pct': 8}),
        }
        for name, change in cases.items():
            code, r = unlock_audit(table(change=change))
            self.assertEqual(code, 2, name)

    def test_moves_bonus_warns(self):
        def moves(t):
            for i, x in enumerate(t['items']):
                if x.get('bonus'):
                    x['bonus'] = {'type': 'moves', 'amount': 1 + i}
        code, r = unlock_audit(table(change=moves))
        self.assertEqual(code, 0, r['errors'])
        self.assertTrue(any('solvable' in w for w in r['warnings']))


@unittest.skipUnless(NODE, 'node not installed')
class CheckinTests(unittest.TestCase):
    def project(self, features=None, files=True, t=None, cfg_change=None):
        root = Path(tempfile.mkdtemp(prefix='checkin-test-'))
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'assets/scripts').mkdir(parents=True)
        (root / 'assets/resources/config').mkdir(parents=True)
        (root / 'docs').mkdir()
        if features is not False:
            (root / 'docs/features.json').write_text(json.dumps(features or {
                'schema': 'optional_features.v1', 'asked': 'optimisation plan, user replied 2026-10-22', 'skin_bonus': True, 'daily_checkin': True}))
        if files:
            shutil.copy(ASSETS / 'DailyCheckin.ts', root / 'assets/scripts/DailyCheckin.ts')
            cfg = json.loads((ASSETS / 'checkin-config.json').read_text())
            if cfg_change:
                cfg_change(cfg)
            (root / 'assets/resources/config/checkin-config.json').write_text(json.dumps(cfg))
        (root / 'assets/resources/config/unlock_table.json').write_text(json.dumps(t or table()))
        return root

    def audit(self, root):
        out = root.parent / (root.name + '-r.json')
        self.addCleanup(lambda: out.unlink(missing_ok=True))
        r = subprocess.run([sys.executable, '-B', str(HERE / 'audit_optional_features.py'), '--project', str(root), '--out', str(out)],
                           capture_output=True, text=True)
        rep = json.loads(out.read_text())
        return r.returncode, {c['id']: c['passed'] for c in rep['checks']}

    def test_good_project_passes(self):
        code, c = self.audit(self.project())
        self.assertEqual(code, 0, c)
        self.assertGreaterEqual(len(c), 8)

    def test_no_decision_fails(self):
        code, c = self.audit(self.project(features=False))
        self.assertEqual((code, c['decision_recorded']), (1, False))

    def test_answer_no_means_no_files_and_no_bonus(self):
        no = {'schema': 'optional_features.v1', 'asked': 'user said no', 'skin_bonus': False, 'daily_checkin': False}
        code, c = self.audit(self.project(features=no, files=False, t=table(bonus=False, checkin=False)))
        self.assertEqual(code, 0, c)
        code, c = self.audit(self.project(features=no))
        self.assertFalse(c['no_skin_bonus'])
        self.assertFalse(c['no_checkin'])

    def test_broken_projects_fail(self):
        root = self.project()
        f = root / 'assets/scripts/DailyCheckin.ts'
        f.write_text(f.read_text() + '\n// edited\n')
        self.assertFalse(self.audit(root)[1]['module_unchanged'])
        small = lambda cfg: cfg['days'][6]['rewards'][0].update(amount=150)
        self.assertFalse(self.audit(self.project(cfg_change=small))[1]['sim_config_valid'])
        self.assertFalse(self.audit(self.project(t=table(checkin=False)))[1]['checkin_skins_in_table'])
        self.assertFalse(self.audit(self.project(cfg_change=lambda cfg: cfg.update(R=80)))[1]['same_R'])
        self.assertFalse(self.audit(self.project(t=table(bonus=False)))[1]['skin_bonus_in_table'])

    def harness(self, text):
        tmp = Path(tempfile.mkdtemp(prefix='ck-h-'))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / 'C.mjs').write_text(text)
        r = subprocess.run([NODE, str(HERE / 'checkin_harness.mjs'), str(tmp / 'C.mjs'), str(ASSETS / 'checkin-config.json')],
                           capture_output=True, text=True, env=dict(os.environ, TZ='UTC'))
        return {c['id']: c['passed'] for c in json.loads(r.stdout)['checks']}

    def test_broken_module_is_caught(self):
        src = (ASSETS / 'DailyCheckin.ts').read_text()
        mutants = {
            'once_per_day_in_order': src.replace('return st.last_day === null || localDay(cfg, nowMs) > st.last_day;', 'return true;'),
            'owned_skin_pays_coins': src.replace("if (r.type === 'skin' && have.indexOf(r.id) >= 0)", 'if (false)'),
            'clock_missed_days_reload': src.replace("const d = new Date(nowMs - (cfg.reset_hour || 0) * 3600000);", 'const d = new Date(nowMs);'),
        }
        for check, text in mutants.items():
            self.assertNotEqual(text, src, check)
        self.assertFalse(self.harness(mutants['once_per_day_in_order'])['once_per_day_in_order'])
        self.assertFalse(self.harness(mutants['owned_skin_pays_coins'])['owned_skin_pays_coins'])
        self.assertTrue(all(self.harness(src).values()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
