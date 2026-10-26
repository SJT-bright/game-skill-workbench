"""Behavior coverage: intro levels override sampling gaps; missing marks stay visible."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import plan_level_tests as sampling

HERE = Path(__file__).resolve().parent


class IntroSamplingTests(unittest.TestCase):
    def rows(self, total=70):
        return [{'level': n} for n in range(1, total + 1)]

    def test_intro_in_sampling_gap_is_always_included_once(self):
        rows = self.rows()
        rows[16].update(tags=['intro'], mechanics=['wind'])
        rows[17].update(mechanics=['wind'])
        rows[22].update(tags=['intro'], mechanics=['ice', 'key'])
        rows[69].update(tags=['intro'], mechanics=['boss'])
        result = sampling.build_report(70, rows)
        self.assertNotIn(17, sampling.plan(70))
        self.assertEqual(result['tested_with_real_touch'], sorted(set(sampling.plan(70)) | {17, 23}))
        self.assertEqual(result['intro_levels'], [17, 23, 70])
        self.assertEqual(result['missing_intro'], [])
        self.assertEqual(result['warnings'], [])
        self.assertEqual(result['tested_count'] + result['skipped_count'], 70)

    def test_unordered_rows_find_first_mechanic_and_warn_even_if_already_sampled(self):
        rows = self.rows()
        rows[0].update(mechanics=['move'])
        rows[16].update(mechanics=['wind'])
        rows[17].update(mechanics=['wind'])
        rows[22].update(tags=['intro'], mechanics=['ice'])
        result = sampling.build_report(70, list(reversed(rows)))
        self.assertEqual(result['missing_intro'], [
            {'level': 1, 'mechanics': ['move']}, {'level': 17, 'mechanics': ['wind']}])
        self.assertTrue(any('Level 17' in message for message in result['warnings']))
        self.assertNotIn(17, result['intro_levels'])

    def test_total_only_and_unannotated_table_warn(self):
        self.assertTrue(sampling.build_report(70)['warnings'])
        result = sampling.build_report(70, self.rows())
        self.assertTrue(any('No "intro"' in message for message in result['warnings']))
        self.assertTrue(any('No mechanics' in message for message in result['warnings']))
        self.assertEqual(result['tested_with_real_touch'], sampling.plan(70))

    def test_full_sample_stays_stable_and_includes_changed_and_failed_levels(self):
        self.assertEqual(len(sampling.plan(70)), 35)
        self.assertEqual(len(sampling.plan(100)), 40)
        self.assertEqual(len(sampling.plan(200)), 51)
        result = sampling.build_report(70, self.rows(), changed_levels=[17], regression_levels=[23])
        self.assertEqual(result['tested_with_real_touch'], sorted(set(sampling.plan(70)) | {17, 23}))
        self.assertIn('known_failure', result['selection_reasons']['23'])

    def test_changed_scope_does_not_restart_the_full_sample(self):
        rows = self.rows()
        for row in rows:
            row['mechanics'] = ['move']
        rows[0]['tags'] = ['intro']
        rows[16].update(tags=['intro'], mechanics=['move', 'wind'])
        rows[17]['mechanics'] = ['move', 'wind']
        rows[49].update(tags=['intro'], mechanics=['move', 'ice'])
        result = sampling.build_report(70, rows, scope='changed', changed_levels=[18],
                                      related_levels=[19], regression_levels=[69])
        self.assertEqual(result['tested_with_real_touch'], [1, 17, 18, 19, 69])
        self.assertEqual(result['baseline_levels'], [])
        self.assertNotIn(50, result['tested_with_real_touch'])
        self.assertNotIn(70, result['tested_with_real_touch'])
        self.assertEqual(result['selection_reasons']['17'], ['affected_mechanic_intro'])

    def test_invalid_incremental_selection_is_rejected(self):
        for value in ['0', '3-2', '1,,4', '1-a', '-2', '1-100001']:
            with self.assertRaises(ValueError, msg=value):
                sampling.parse_levels(value)
        self.assertEqual(sampling.parse_levels('18,25-26,18'), [18, 25, 26])
        for kwargs in [{'scope': 'changed'}, {'changed_levels': [71]},
                       {'related_levels': [False]}, {'scope': 'unknown'}]:
            with self.assertRaises(ValueError, msg=str(kwargs)):
                sampling.build_report(70, self.rows(), **kwargs)

    def test_all_intro_sample_warns_without_dropping_real_mechanics(self):
        rows = [{'level': n, 'tags': ['intro'], 'mechanics': ['mechanic_%d' % n]}
                for n in range(1, 71)]
        result = sampling.build_report(70, rows)
        self.assertEqual(result['tested_count'], 70)
        self.assertTrue(any('covers every level' in message for message in result['warnings']))

    def test_changed_scope_cli_is_local_only_and_checks_bounds(self):
        command = [sys.executable, '-B', str(HERE / 'plan_level_tests.py'), '--total', '70',
                   '--scope', 'changed', '--changed-levels', '18,25-26', '--regression-levels', '69']
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['tested_with_real_touch'], [18, 25, 26, 69])
        self.assertEqual(report['scope'], 'changed')
        bad = subprocess.run(command + ['--related-levels', '71'], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)

    def test_generator_to_cli_and_bad_input(self):
        with tempfile.TemporaryDirectory(prefix='intro sample ') as tmp:
            root = Path(tmp)
            source, target = root / 'level plan.json', root / 'touch plan.json'
            generated = subprocess.run([sys.executable, '-B', str(HERE / 'make_level_plan.py'),
                '--levels', '70', '--seed', '19', '--intro', '1:move', '--intro', '17:wind',
                '--intro', '17:ice', '--out', str(source)], capture_output=True, text=True)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            def run(*extra):
                return subprocess.run([sys.executable, '-B', str(HERE / 'plan_level_tests.py'),
                    '--level-plan', str(source), *extra], capture_output=True, text=True)
            result = run('--out', str(target))
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(target.read_text())
            self.assertIn(17, report['tested_with_real_touch'])
            self.assertEqual(report['intro_levels'], [1, 17])
            self.assertFalse(report['warnings'])
            self.assertNotEqual(run('--out', str(target)).returncode, 0)  # protect existing evidence
            self.assertEqual(run('--total', '71').returncode, 2)
            data = json.loads(source.read_text())
            for mutation in ('duplicate', 'missing', 'bad_tags', 'bad_mechanics', 'endless'):
                bad = json.loads(json.dumps(data))
                if mutation == 'duplicate': bad['levels'][1]['level'] = 1
                elif mutation == 'missing': bad['levels'].pop()
                elif mutation == 'bad_tags': bad['levels'][0]['tags'] = 'intro'
                elif mutation == 'bad_mechanics': bad['levels'][0]['mechanics'] = [False]
                else: bad['mode'] = 'endless'
                source.write_text(json.dumps(bad))
                self.assertEqual(run().returncode, 2, mutation)

    def test_current_project_explicit_count_survives_v8_template(self):
        from make_level_plan import make
        from audit_level_plan import audit_plan
        data = make(40, 50, None, 19, 'Coins')
        data['why'] = 'Existing project keeps the explicitly approved original forty levels.'
        def count_check():
            checks = {}
            audit_plan(data, None, lambda name, passed, detail: checks.update({name: passed}), 'localize')
            return checks['levels_at_least_70']
        self.assertFalse(count_check())
        data['explicit_total'] = {'count': 40, 'authorized_by': 'current project contract',
            'reason': 'The current project explicitly preserves its original forty levels and all progression values.'}
        self.assertTrue(count_check())

    def test_missing_intro_warning_reaches_stderr_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'levels.json'
            rows = self.rows()
            rows[16]['mechanics'] = ['wind']
            source.write_text(json.dumps({'mode': 'levels', 'total_levels': 70, 'levels': rows}))
            result = subprocess.run([sys.executable, '-B', str(HERE / 'plan_level_tests.py'),
                '--plan', str(source)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn('WARNING:', result.stderr)
            self.assertIn('Level 17', result.stderr)
            self.assertEqual(json.loads(result.stdout)['missing_intro'], [{'level': 17, 'mechanics': ['wind']}])


if __name__ == '__main__':
    unittest.main()
