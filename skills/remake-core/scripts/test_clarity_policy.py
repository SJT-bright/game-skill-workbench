#!/usr/bin/env python3
"""Resolution policy boundaries only; synthetic fixtures, no browser/game build."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from clarity_policy import resolve_policy, measure, group_result

HERE = Path(__file__).resolve().parent


class ClarityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'assets').mkdir()
        (self.root / 'docs/art').mkdir(parents=True)
        (self.root / 'project.json').write_text(json.dumps({'engine': 'cocos-creator-js', 'version': '2.4.5'}))

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, **values):
        (self.root / 'docs/art/clarity-policy.json').write_text(json.dumps(dict(schema='clarity_policy.v1', **values)))

    def fixture(self, source=100, render=200, name='Icon'):
        (self.root / 'assets/icon.png.meta').write_text(json.dumps({'subMetas': {'icon': {'uuid': 'test-frame', 'rawWidth': source, 'rawHeight': source}}}))
        (self.root / 'assets/a.fire').write_text(json.dumps([
            {'__type__': 'cc.Sprite', '_type': 0, '_spriteFrame': {'__uuid__': 'test-frame'}, 'node': {'__id__': 1}},
            {'__type__': 'cc.Node', '_name': name, '_contentSize': {'width': render, 'height': render}, '_parent': None}
        ]))

    def run_static(self, *args):
        target = self.root / 'report.json'
        if target.exists():
            target.unlink()
        p = subprocess.run([sys.executable, '-B', str(HERE / 'audit_image_clarity.py'), '--project', str(self.root), '--out', str(target), *args], capture_output=True, text=True)
        return p, json.loads(target.read_text()) if target.exists() else None

    def test_default_advisory_never_blocks_ratio_alone(self):
        self.fixture()
        p, r = self.run_static()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(r['passed'])
        self.assertEqual(r['status'], 'advisory')
        f = r['findings'][0]
        self.assertEqual((f['source_render_ratio'], f['threshold'], f['severity']), (0.5, 1.0, 'advisory'))
        self.assertFalse(f['blocking'])
        self.assertFalse(f['auto_regenerate'])
        self.assertIsNone(group_result(r['clarity_policy'], ['low_res: actual ratio'], []))
        self.assertFalse(group_result(r['clarity_policy'], [], [], inputs_ready=False))

    def test_explicit_strict_blocks_and_preserves_metrics(self):
        self.fixture(source=150, render=100)
        p, r = self.run_static('--clarity-preset', 'strict')
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertFalse(r['passed'])
        self.assertEqual(r['findings'][0]['threshold'], 2.0)
        self.assertEqual(r['findings'][0]['source_render_ratio'], 1.5)
        self.assertEqual(json.loads(p.stdout)['below_threshold'], 1)
        self.assertFalse(group_result(r['clarity_policy'], ['low_res: actual ratio'], []))

    def test_background_default_and_strict_thresholds(self):
        self.fixture(source=125, render=100, name='Background')
        p, r = self.run_static()
        self.assertEqual(p.returncode, 0)
        self.assertEqual(r['items'][0]['threshold'], 1.0)
        self.assertEqual(r['findings'], [])
        p, r = self.run_static('--clarity-preset', 'strict')
        self.assertEqual(p.returncode, 1)
        self.assertEqual(r['findings'][0]['threshold'], 1.5)
        self.assertTrue(r['findings'][0]['background'])

    def test_project_custom_and_cli_precedence(self):
        self.config(preset='strict', min_ratio=1.25, background_min_ratio=1.1, severity='advisory')
        p = resolve_policy(self.root)
        self.assertEqual((p['min_ratio'], p['background_min_ratio'], p['severity']), (1.25, 1.1, 'advisory'))
        p = resolve_policy(self.root, cli_preset='strict')
        self.assertEqual((p['min_ratio'], p['background_min_ratio'], p['severity']), (2, 1.5, 'blocking'))
        p = resolve_policy(self.root, cli_preset='strict', cli_min_ratio=1.3, cli_severity='advisory')
        self.assertEqual((p['min_ratio'], p['background_min_ratio'], p['severity']), (1.3, 1.5, 'advisory'))
        self.assertEqual(p['sources']['min_ratio'], 'CLI field')
        self.fixture(source=100, render=100)
        process, report = self.run_static('--clarity-min-ratio', '0.8', '--clarity-severity', 'blocking')
        self.assertEqual(process.returncode, 0)
        self.assertEqual(report['findings'], [])

    def test_invalid_config_rejected_without_silent_default(self):
        invalid = [{'min_ratio': 0}, {'min_ratio': -1}, {'min_ratio': True}, {'min_ratio': float('nan')},
                   {'background_min_ratio': float('inf')}, {'preset': 'magic'}, {'severity': 'warn'}, {'typo_ratio': 2}]
        for data in invalid:
            with self.subTest(data=data):
                self.config(**data)
                with self.assertRaises(ValueError):
                    resolve_policy(self.root)
                p, report = self.run_static()
                self.assertEqual(p.returncode, 2)
                self.assertIsNone(report)
        (self.root / 'docs/art/clarity-policy.json').write_text('{broken')
        with self.assertRaises(ValueError):
            resolve_policy(self.root)
        with self.assertRaises(ValueError):
            resolve_policy(self.root, policy_path='missing.json')

    def test_invalid_cli_rejected_by_both_owners_before_work(self):
        self.fixture()
        p, _ = self.run_static('--clarity-min-ratio', 'nan')
        self.assertEqual(p.returncode, 2)
        p = subprocess.run([sys.executable, '-B', str(HERE / 'art_check.py'), '--project', str(self.root),
                            '--clarity-background-min-ratio', '-1'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn('finite positive', p.stderr)

    def test_valid_cli_does_not_relax_other_quality_gates(self):
        policy = resolve_policy(self.root)
        result = measure([80, 80], [100, 100], policy)
        self.assertFalse(result['blocking'])
        self.assertIn('missing glyphs', policy['boundary'])
        self.assertFalse(group_result(policy, [result], [], inputs_ready=False))
        for source, render in [([0, 100], [10, 10]), ([100, 100], [float('nan'), 10])]:
            with self.assertRaises(ValueError):
                measure(source, render, policy)


if __name__ == '__main__':
    unittest.main()
