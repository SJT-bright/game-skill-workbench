"""Production-budget contracts and refusal controls, not screenshot acceptance."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import art_usage_budget as usage
from clarity_policy import resolve_policy


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

    def test_legacy_reserve_is_advisory_but_explicit_strict_applies(self):
        data = usage.validate_budget(self.budget, self.ids)
        self.assertEqual(usage.validate_output(data, (48, 68))['minimum_output_size'], [48, 68])
        advisory = usage.validate_output(data, (46, 65))
        self.assertTrue(advisory['advisories'])
        self.assertFalse(advisory['blocking'])
        with self.assertRaises(ValueError):
            usage.validate_output(data, (46, 65), policy=resolve_policy(cli_preset='strict'))
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
        for key, value in [('unit', 'design_px'), ('unit', 'physical_px'), ('density', 0), ('density', -1),
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
                usage.validate_output(self.budget, size, policy=resolve_policy(cli_preset='strict'))

    def test_real_wheel_design_size_is_not_css(self):
        data = {'unit': 'css_px', 'density': 2,
                'cases': [{'id': 'wheel-result', 'css_size': [136.5, 136.5]}]}
        result = usage.validate_output(usage.validate_budget(data, ['wheel-result']), (320, 320))
        self.assertEqual(result['minimum_output_size'], [273, 273])
        self.assertFalse(result['runtime_verified'])

    def test_old_two_x_declaration_stays_identical_and_never_forces_redrawing_by_default(self):
        original = json.loads(json.dumps(self.budget))
        canonical = usage.validate_budget(self.budget, self.ids)
        self.assertEqual(canonical, original)
        result = usage.validate_output(canonical, (24, 34))
        self.assertFalse(result['blocking'])
        self.assertEqual(len(result['advisories']), 2)
        self.assertEqual(self.budget, original)
        lower = dict(self.budget, density=1.25)
        self.assertEqual(usage.validate_budget(lower, self.ids)['density'], 1.25)

    def test_strict_uses_current_policy_not_historical_generation_reserve(self):
        legacy = {'unit': 'css_px', 'density': 4, 'cases': [{'id': 'icon', 'css_size': [100, 100]}]}
        result = usage.validate_output(legacy, (250, 250), policy=resolve_policy(cli_preset='strict'))
        self.assertEqual(result['cases'][0]['threshold'], 2)
        self.assertTrue(result['cases'][0]['below_generation_reserve'])
        self.assertEqual(result['advisories'][0]['severity'], 'advisory')
        with self.assertRaises(ValueError):
            usage.validate_output(legacy, (190, 190), policy=resolve_policy(cli_preset='strict'))

    def test_direct_project_policy_and_cli_can_be_explicitly_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'docs/art').mkdir(parents=True)
            (root/'docs/art/clarity-policy.json').write_text(json.dumps({'preset':'strict','min_ratio':1.25}))
            data = {'unit':'css_px','density':2,'cases':[{'id':'icon','css_size':[100,100]}]}
            with self.assertRaises(ValueError):usage.validate_output(data,(120,120),project=root)
            self.assertFalse(usage.validate_output(data,(130,130),project=root)['blocking'])
            budget=root/'budget.json';budget.write_text(json.dumps(data))
            cmd=[sys.executable,'-B',usage.__file__,'--budget',str(budget),'--expected-cases','icon','--size','120','120','--project',str(root)]
            self.assertEqual(subprocess.run(cmd,capture_output=True,text=True).returncode,1)
            advisory=subprocess.run(cmd+['--clarity-preset','default'],capture_output=True,text=True)
            self.assertEqual(advisory.returncode,0,advisory.stderr)
            self.assertTrue(json.loads(advisory.stdout)['measurements']['advisories'])


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


class IndividualFirstRequest(unittest.TestCase):
    def test_first_request_includes_safe_edges_and_content_aspect(self):
        r = usage.plan_individual('coin', 'transparent reward coin icon', [150, 120])
        self.assertEqual(r['generation_mode'], 'individual')
        self.assertEqual(r['recommended_content_source_px'], [300, 240])
        self.assertEqual(r['recommended_source_px'], [316, 256])
        self.assertEqual(r['content_aspect_ratio'], 1.25)
        self.assertFalse(r['blocking'])
        self.assertFalse(r['auto_generate'])
        self.assertFalse(r['auto_retry'])
        self.assertFalse(r['reserve_is_acceptance_threshold'])
        bg = usage.plan_individual('sky', 'full-screen painted sky', [390, 844], background=True, safe_edge_px=0)
        self.assertEqual(bg['reserve_ratio'], 1.5)
        self.assertEqual(bg['recommended_source_px'], [585, 1266])
        tuned = usage.plan_individual('sky', 'full-screen painted sky', [390, 844], reserve_ratio=1, safe_edge_px=0)
        self.assertEqual(tuned['recommended_source_px'], [390, 844])

    def test_generator_limits_are_one_upfront_decision_not_failure_or_retry(self):
        r = usage.plan_individual('energy', 'isolated energy icon', [145, 150], generator_sizes=[[256, 256]])
        self.assertTrue(r['needs_size_decision_before_request'])
        self.assertEqual([x['choice'] for x in r['generator_limit_advisories']], ['larger_generator_tier', 'smaller_display'])
        self.assertEqual(r['generator_limit_advisories'][1]['max_css_size'], [116, 120])
        self.assertFalse(r['blocking'])
        fitted = usage.plan_individual('energy', 'isolated energy icon', [145, 150], generator_sizes=[[1024, 1024], [512, 512]])
        self.assertEqual(fitted['selected_generator_size'], [512, 512])
        self.assertFalse(fitted['needs_size_decision_before_request'])

    def test_actual_source_and_supplied_render_are_recorded_without_visual_pass(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / 'coin.png'
            Image.new('RGBA', (100, 80)).save(image)
            before = image.read_bytes()
            r = usage.plan_individual('coin', 'coin preview', [150, 120], source_image=image, render_css=[50, 40])
            measurement = r['source_render_measurement']
            self.assertEqual(measurement['source_px'], [100, 80])
            self.assertEqual(measurement['source_render_ratio'], 2)
            self.assertEqual(measurement['severity'], 'advisory')
            self.assertIsNone(measurement['visual_passed'])
            self.assertEqual(before, image.read_bytes())

    def test_cli_limit_advice_succeeds_and_bad_input_is_rejected(self):
        base = [sys.executable, '-B', usage.__file__, '--plan-individual', '--asset-id', 'coin', '--purpose', 'coin icon', '--max-css', '150', '120']
        r = subprocess.run(base + ['--generator-size', '100', '100'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout)['advisory'])
        for flags in (['--reserve-ratio', 'nan'], ['--safe-edge-px', '-1'], ['--generator-size', '0', '100']):
            r = subprocess.run(base + flags, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stderr)
            self.assertFalse(json.loads(r.stdout)['passed'])


if __name__ == '__main__':
    unittest.main()
