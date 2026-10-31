#!/usr/bin/env python3
"""v7.8 W91: full reskin (P18), sample-first reminder (22.6 q3), stroke touch cases (T7), trademark words (E8).
Synthetic projects in a temp folder; nothing outside it is written. Run: python3 test_w91_v78.py"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_level_plan as L  # noqa: E402


def tmp(case):
    d = Path(tempfile.mkdtemp(prefix='w91_'))
    case.addCleanup(shutil.rmtree, d, True)
    return d


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
    return path


def run(script, *args):
    r = subprocess.run([sys.executable, '-B', str(HERE / script)] + [str(a) for a in args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


class Reskin(unittest.TestCase):
    """P18 (Saul 2026-10-30): a reskin copies the base's levels and gameplay code byte for byte with his OK."""

    def setUp(self):
        root = tmp(self)
        self.base = root / 'base'
        self.proj = root / 'proj'
        for top in (self.base, self.proj):
            write(top / 'assets/scripts/LevelData.ts', 'export const LEVELS = [[1,2],[3,4]];\n')
            write(top / 'assets/scripts/Player.ts', 'speed = 300;\n')
        self.out = root / 'out'
        self.out.mkdir()

    def plan(self, **over):
        p = {'schema': 'level_plan.v1', 'mode': 'levels', 'remake_mode': 'reskin', 'why': 'full reskin of base',
             'total_levels': 20,
             'base_game': {'name': 'base', 'mode': 'levels', 'evidence': 'LevelData.ts has 20 levels'},
             'reskin': {'base': str(self.base),
                        'approval': {'by': 'Saul', 'date': '2026-10-30', 'quote': '照搬原游戏'},
                        'copied': [{'what': 'levels', 'base_path': 'assets/scripts/LevelData.ts'},
                                   {'what': 'gameplay_code', 'base_path': 'assets/scripts/Player.ts'}]}}
        p['reskin'].update(over)
        return write(self.out / ('plan%d.json' % len(list(self.out.iterdir()))), json.dumps(p))

    def audit(self, plan):
        rep = self.out / ('rep%d.json' % len(list(self.out.iterdir())))
        code, _o, err = run('audit_level_plan.py', '--project', self.proj, '--plan', plan, '--board', 'remake',
                            '--out', rep)
        self.assertTrue(rep.is_file(), err)
        return code, {c['id']: c for c in json.loads(rep.read_text())['checks']}

    def test_approved_identical_reskin_passes_without_60_levels(self):
        code, checks = self.audit(self.plan())
        self.assertEqual(code, 0, checks)
        self.assertTrue(checks['levels_at_least_70']['passed'])
        self.assertNotIn('map_page', checks)

    def test_changed_level_file_fails(self):
        write(self.proj / 'assets/scripts/LevelData.ts', 'export const LEVELS = [[1,2],[3,5]];\n')
        code, checks = self.audit(self.plan())
        self.assertEqual(code, 1)
        self.assertFalse(checks['reskin_same_bytes']['passed'])
        self.assertIn('LevelData.ts differs', checks['reskin_same_bytes']['detail'])
        self.assertFalse(checks['levels_at_least_70']['passed'])

    def test_no_saul_approval_is_not_a_reskin(self):
        for approval in ({}, {'by': 'Kiro', 'date': '2026-10-30', 'quote': '照搬原游戏'},
                         {'by': 'Saul', 'date': 'today', 'quote': '照搬原游戏'}):
            code, checks = self.audit(self.plan(approval=approval))
            self.assertEqual(code, 1, approval)
            self.assertFalse(checks['reskin_approved']['passed'])

    def test_base_from_base_assets_json_and_from_a_zip(self):
        import zipfile
        z = self.base.parent / 'base.zip'
        with zipfile.ZipFile(z, 'w') as out:
            for f in self.base.rglob('*'):
                if f.is_file():
                    out.write(f, 'Base/' + f.relative_to(self.base).as_posix())
            out.writestr('Base/project.json', '{}')
        write(self.proj / 'docs/art/base-assets.json', json.dumps({'kind': 'base-assets', 'base': str(z)}))
        plan = json.loads(self.plan().read_text())
        del plan['reskin']['base']
        code, checks = self.audit(write(self.out / 'zipplan.json', json.dumps(plan)))
        self.assertEqual(code, 0, checks)
        self.assertIn('base-assets.json', checks['reskin_base']['detail'])

    def test_gameplay_code_must_be_listed(self):
        code, checks = self.audit(self.plan(copied=[{'what': 'levels', 'base_path': 'assets/scripts/LevelData.ts'}]))
        self.assertEqual(code, 1)
        self.assertFalse(checks['reskin_copied_listed']['passed'])

    def test_make_level_plan_writes_a_reskin_plan(self):
        out = self.out / 'made.json'
        code, _o, err = run('make_level_plan.py', '--reskin', '--project', self.proj, '--reskin-base', self.base,
                            '--base-game', 'base', '--base-mode', 'levels', '--base-evidence', 'LevelData.ts has 20',
                            '--levels', '20', '--approved-by', 'Saul', '--approved-date', '2026-10-30',
                            '--approved-quote', '照搬原游戏', '--copy', 'levels:assets/scripts/LevelData.ts',
                            '--copy', 'gameplay_code:assets/scripts/Player.ts', '--out', out)
        self.assertEqual(code, 0, err)
        made = json.loads(out.read_text())
        self.assertEqual(made['remake_mode'], 'reskin')
        self.assertEqual(made['reskin']['copied'][0]['sha256'],
                         hashlib.sha256((self.proj / 'assets/scripts/LevelData.ts').read_bytes()).hexdigest())
        self.assertEqual(self.audit(out)[0], 0)
        code, _o, err = run('make_level_plan.py', '--reskin', '--project', self.proj, '--base-game', 'base',
                            '--base-mode', 'levels', '--base-evidence', 'LevelData.ts has 20',
                            '--copy', 'levels:assets/scripts/LevelData.ts', '--out', self.out / 'x.json')
        self.assertEqual(code, 2)
        self.assertIn('Saul', err)

    def test_plan_mode_is_still_levels_for_other_tools(self):
        write(self.proj / 'assets/resources/config/level_plan.json', self.plan().read_text())
        self.assertEqual(L.plan_mode(self.proj), 'levels')


class Samples(unittest.TestCase):
    """22.6 q3 (Saul 2026-10-30): sample first, only for self-made new games; a reminder, never a block."""

    def test_missing_partial_complete_skip_and_localize(self):
        import design_check as D
        proj = tmp(self)
        (proj / 'assets').mkdir()
        state, detail = D.samples_status(proj, 'remake')
        self.assertIsNone(state)
        self.assertIn('首页样图', detail)
        signed = {'verdict': 'ok', 'by': 'Saul', 'date': '2026-10-30'}
        data = {'schema': 'samples.v1', 'home_image': dict(signed, file='home.png'),
                'playtest_20s': dict(signed, file='play.mp4'),
                'bgm': dict(signed, options=['a.mp3', 'b.mp3', 'c.mp3'], chosen='b.mp3')}
        write(proj / D.SAMPLES, json.dumps(data))
        state, detail = D.samples_status(proj, 'remake')
        self.assertIsNone(state)
        self.assertIn('样关', detail)
        self.assertTrue(D.samples_status(proj, 'remake', reskin=True)[0])        # a reskin has no new levels
        data['sample_levels'] = dict(signed, levels=[3, 4, 5])
        write(proj / D.SAMPLES, json.dumps(data))
        self.assertTrue(D.samples_status(proj, 'remake')[0])
        write(proj / D.SAMPLES, json.dumps({'skip': {'why': 'started before v7.8, art already approved'}}))
        self.assertTrue(D.samples_status(proj, 'remake')[0])
        self.assertEqual(D.samples_status(proj, 'localize')[0], 'skip')


class StrokeCases(unittest.TestCase):
    """T7 (剪刀达人): stroke games get 3 fixed touch cases and design / wrong solutions per listed level."""

    def test_cut_game_gets_fixed_cases_and_wrong_solutions(self):
        import plan_level_tests as T
        rep = T.build_report(20, input_kind='cut')
        ids = [c['id'] for c in rep['stroke_touch_cases']]
        self.assertEqual(ids, ['release_outside', 'start_inside_8px', 'end_inside_8px'])
        cases = {(c['level'], c['case']): c['expect'] for c in rep['solution_cases']}
        for n in rep['tested_with_real_touch']:
            self.assertEqual(cases[(n, 'design_solution')], 'pass')
            self.assertEqual(cases[(n, 'wrong_offset')], 'fail')
            self.assertEqual(cases[(n, 'wrong_slant')], 'fail')
        self.assertNotIn('stroke_touch_cases', T.build_report(20, input_kind='tap'))

    def test_plan_input_field_and_mechanic_warning(self):
        d = tmp(self)
        rows = [{'level': n, 'type': 'normal', 'mechanics': ['cut'] if n == 1 else []} for n in range(1, 11)]
        plan = write(d / 'plan.json', json.dumps({'mode': 'levels', 'total_levels': 10, 'levels': rows, 'input': 'cut'}))
        code, out, _e = run('plan_level_tests.py', '--level-plan', plan)
        self.assertEqual(code, 0)
        self.assertIn('stroke_touch_cases', json.loads(out))
        plan2 = write(d / 'plan2.json', json.dumps({'mode': 'levels', 'total_levels': 10, 'levels': rows}))
        code, out, err = run('plan_level_tests.py', '--level-plan', plan2)
        self.assertIn('no input kind is set', err)


class Trademarks(unittest.TestCase):
    """E8: Codex's first English round of 全民飞车漂移 kept Ferrari 458."""

    def project(self, strings, glossary=None):
        proj = tmp(self)
        write(proj / 'assets/resources/i18n/en.json', json.dumps({'cars': strings}))
        if glossary:
            write(proj / 'docs/copy/glossary.json', json.dumps(glossary))
        return proj

    def audit(self, proj):
        out = proj.parent / (proj.name + '-copy.json')
        code, _o, err = run('audit_copy_quality.py', '--project', proj, '--out', out)
        self.assertTrue(out.is_file(), err)
        return code, json.loads(out.read_text())

    def test_brand_and_character_names_block_and_say_the_word(self):
        code, rep = self.audit(self.project(['Ferrari 458', 'Optimus Prime', 'Dodge Challenger', 'Taxi Cab']))
        self.assertEqual(code, 1)
        found = [c for c in rep['checks'] if c['kind'] == 'trademark']
        self.assertEqual({c['text'] for c in found}, {'Ferrari 458', 'Optimus Prime', 'Dodge Challenger'})
        self.assertTrue(any('「Ferrari」' in c['message'] for c in found))

    def test_plain_words_and_generic_names_pass(self):
        code, rep = self.audit(self.project(['Sports Car', 'Pony Car', 'Muscle Car', 'Dodge the rocks!',
                                             'Play Golf', 'Golden Mustang Ranch Bonus', 'Hatchback']))
        self.assertFalse([c for c in rep['checks'] if c['kind'] == 'trademark'])
        review = [r for r in rep['review'] if r['kind'] == 'trademark']
        self.assertEqual([r['text'] for r in review], ['Golden Mustang Ranch Bonus'])     # hint only

    def test_licensed_name_in_glossary_and_literals_are_review(self):
        proj = self.project(['Porsche 911'], {'trademark_ok': [{'term': 'Porsche', 'why': 'licensed by the client 2026'}]})
        write(proj / 'assets/scripts/Cars.ts', 'const NAMES = ["Lamborghini Mod", "Taxi"];\n')
        code, rep = self.audit(proj)
        self.assertEqual(code, 0, rep['checks'])
        self.assertEqual([r['text'] for r in rep['review'] if r['kind'] == 'trademark_literal'], ['Lamborghini Mod'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
