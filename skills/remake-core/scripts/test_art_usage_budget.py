"""Production-budget contracts and refusal controls, not screenshot acceptance."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import art_usage_budget as usage


class ImageBudget(unittest.TestCase):
    def setUp(self):
        self.budget = {'unit': 'css_px', 'density': 2,
                       'cases': [{'id': 'home-se', 'css_size': [18.5, 26.1]},
                                 {'id': 'result-se', 'css_size': [24, 33.9]}]}
        self.ids = ['home-se', 'result-se']

    def test_plan_before_image_exists(self):
        from art_usage_budget import plan_output
        data = {'unit': 'css_px', 'density': 2, 'cases': [
            {'id': 'home', 'css_size': [18.5, 26.1]}, {'id': 'result', 'css_size': [24, 33.9]}]}
        self.assertEqual(plan_output(data, ['home', 'result'])['minimum_output_size'], [48, 68])
        with self.assertRaises(ValueError):
            plan_output(None, ['home'])

    def test_missing_declaration_preserves_legacy(self):
        self.assertIsNone(usage.validate_budget(None, None))
        self.assertIsNone(usage.validate_output(None, None))
        self.assertIsNone(usage.validate_font_budget(None, None, None, None))

    def test_real_cross_page_size_is_required(self):
        data = usage.validate_budget(self.budget, self.ids)
        self.assertEqual(usage.validate_output(data, (48, 68))['minimum_output_size'], [48, 68])
        with self.assertRaises(ValueError):
            usage.validate_output(data, (46, 65))
        home = copy.deepcopy(self.budget)
        home['cases'] = home['cases'][:1]
        self.assertIsNotNone(usage.validate_output(usage.validate_budget(home, self.ids[:1]), (46, 65)))

    def test_cases_are_exact_not_subsets_or_duplicates(self):
        for ids in ([], ['home-se'], ['home-se', 'home-se'], ['home-se', 'result-se', 'unknown']):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                usage.validate_budget(self.budget, ids)
        bad = copy.deepcopy(self.budget)
        bad['cases'][1]['id'] = 'home-se'
        with self.assertRaises(ValueError):
            usage.validate_budget(bad, self.ids)

    def test_invalid_units_density_or_dimensions_refuse(self):
        for key, value in [('unit', 'design_px'), ('unit', 'physical_px'), ('density', 1.99),
                           ('density', float('nan')), ('density', float('inf')), ('density', True)]:
            bad = copy.deepcopy(self.budget)
            bad[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                usage.validate_budget(bad, self.ids)
        for value in (0, -1, True, float('nan'), float('inf'), '24', 10**1000):
            bad = copy.deepcopy(self.budget)
            bad['cases'][0]['css_size'][0] = value
            with self.subTest(value=repr(value)[:30]), self.assertRaises(ValueError):
                usage.validate_budget(bad, self.ids)

    def test_no_implicit_dpr_or_extra_scope(self):
        bad = dict(self.budget, dpr=3)
        with self.assertRaises(ValueError):
            usage.validate_budget(bad, self.ids)

    def test_final_reduction_is_rechecked_on_each_axis(self):
        for size in ((47, 68), (48, 67), (48, True), (48.0, 68), (0, 0)):
            with self.subTest(size=size), self.assertRaises(ValueError):
                usage.validate_output(self.budget, size)

    def test_real_wheel_design_size_is_not_css(self):
        data = {'unit': 'css_px', 'density': 2,
                'cases': [{'id': 'wheel-result', 'css_size': [136.5, 136.5]}]}
        result = usage.validate_output(usage.validate_budget(data, ['wheel-result']), (320, 320))
        self.assertEqual(result['minimum_output_size'], [273, 273])
        self.assertFalse(result['runtime_verified'])


class FontBudget(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / 'assets').mkdir()
        self.font = self.root / 'assets/digits.fnt'
        self.raw = ('info face="fixture" size=160\ncommon lineHeight=160\n'
                    'char id=52 x=0 y=0 width=110 height=128 xoffset=0 yoffset=12 xadvance=126\n'
                    'char id=77 x=120 y=0 width=127 height=128 xoffset=0 yoffset=12 xadvance=143\n')
        self.font.write_text(self.raw)
        self.data = {'unit': 'css_px', 'cases': [{'id': 'wallet', 'text': '4444M', 'font_size_css': 18,
                      'available_css': [74, 18], 'min_font_size_css': 16, 'spacing_css': 0, 'min_gap_css': 1.5}]}

    def tearDown(self):
        self.temp.cleanup()

    def run_budget(self, data=None):
        return usage.validate_font_budget(self.root, 'assets/digits.fnt', self.data if data is None else data, ['wallet'])

    def test_actual_metrics_and_no_asset_mutation(self):
        before = self.font.read_bytes()
        result = self.run_budget()
        self.assertAlmostEqual(result['cases'][0]['advance_width_css'], 72.7875)
        self.assertAlmostEqual(result['cases'][0]['minimum_actual_gap_css'], 1.8)
        self.assertEqual(before, self.font.read_bytes())
        self.assertEqual(result['scope'], 'source_budget_only')
        self.assertFalse(result['runtime_verified'])

    def test_official_gap_rule_rejects_historical_gap_six(self):
        self.font.write_text(self.raw.replace('xadvance=126', 'xadvance=116'))
        with self.assertRaisesRegex(ValueError, 'font_advance'):
            self.run_budget()

    def test_space_is_not_inferred_from_shrink_or_nominal_size(self):
        for change in ({'available_css': [60, 18]}, {'available_css': [74, 10]}, {'font_size_css': 15},
                       {'spacing_css': -1}, {'min_gap_css': 2.5}, {'text': '4444K'}, {'text': '4\nM'},
                       {'fontSize': 18}):
            bad = copy.deepcopy(self.data)
            bad['cases'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.run_budget(bad)

    def test_kerning_can_violate_gap_after_valid_advances(self):
        self.font.write_text(self.raw + 'kerning first=52 second=52 amount=-12\n')
        with self.assertRaisesRegex(ValueError, 'separation'):
            self.run_budget()

    def test_unknown_empty_and_nonfinite_metrics_refuse(self):
        for bad in (self.raw.replace('width=110', 'width=nan'),
                    self.raw.replace('width=110', 'width=0'),
                    self.raw.replace('width=110', 'width=110.5'),
                    self.raw.replace('xadvance=126', 'xadvance=inf'),
                    self.raw.replace('common lineHeight=160', 'common lineHeight=0'),
                    self.raw + 'common lineHeight=200\n'):
            self.font.write_text(bad)
            with self.subTest(raw=bad[:40]), self.assertRaises(ValueError):
                self.run_budget()

    def test_only_requested_font_is_checked(self):
        (self.root / 'assets/legacy.fnt').write_text(self.raw.replace('xadvance=126', 'xadvance=116'))
        self.assertIsNotNone(self.run_budget())

    def test_declared_font_source_stays_under_assets(self):
        outside = self.root / 'outside.fnt'
        outside.write_text(self.raw)
        with self.assertRaises(ValueError):
            usage.validate_font_budget(self.root, outside, self.data, ['wallet'])
        link = self.root / 'assets/alias.fnt'
        link.symlink_to(self.font)
        with self.assertRaises(ValueError):
            usage.validate_font_budget(self.root, link, self.data, ['wallet'])

    def test_cli_refuses_without_changing_font(self):
        budget = self.root / 'budget.json'
        budget.write_text(json.dumps(dict(self.data, unit='design_px')))
        before = self.font.read_bytes()
        run = subprocess.run([sys.executable, '-B', usage.__file__, '--budget', str(budget),
                              '--expected-cases', 'wallet', '--project', str(self.root), '--font', 'assets/digits.fnt'],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertFalse(json.loads(run.stdout)['passed'])
        self.assertEqual(self.font.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
