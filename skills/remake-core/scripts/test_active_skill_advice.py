"""Maintenance-only counterexamples and retained game-compatibility controls."""
import json
from pathlib import Path
import tempfile
import unittest

import active_skill_advice as advice
import audit_page_richness as richness


class ActiveAdvice(unittest.TestCase):
    def test_each_known_conflict_survives_no_precedence_banner(self):
        for rule in advice.load_policy()['rules']:
            with self.subTest(rule=rule['id']), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                control = rule['stale_control']
                target = root / control['path']
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('最新规则优先，下面保留旧版正文。\n' + control['text'] + '\n')
                hits = advice.scan(root)
                self.assertIn(rule['id'], {row['id'] for row in hits})
                self.assertTrue(all(row['line'] == 2 for row in hits))

    def test_clean_current_tree(self):
        root = Path(__file__).resolve().parents[2]
        self.assertEqual(advice.scan(root), [])

    def test_valid_legacy_and_strict_options_are_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = {
                'remake-core/references/fusion-policy.md':
                    '已交付旧合同的无关局部维护保留原奖励、皮肤适用性和存档。',
                'remake-art/references/ui-style-and-samples.md':
                    '显式 strict 时按用户选择的 2x 检查；默认 1:1 advisory。',
                'remake-core/references/single-writer.md':
                    '合法 root 为 subpackages/res 或 subpackages/res/，只规范计量前缀。',
                'remake-art/版本历史.md':
                    '历史：默认UI原图至少为最大设计显示尺寸2倍。',
                'remake-core/scripts/fixtures/old.py':
                    'old = "add a plate behind it"',
            }
            for relative, text in cases.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            self.assertEqual(advice.scan(root), [])

    def test_bad_registry_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'registry.json'
            for invalid in ({}, {'schema': 'active_skill_advice.v1', 'rules': []}):
                file.write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):
                    advice.load_policy(file)

    def test_flat_plate_still_detected_with_transparent_first_remedy(self):
        value = {'path': 'Canvas/HUD/Coins', 'rect': [.1, .1, .1, .05],
                 'comps': {'label': {'string': '100'}}}
        plate = {'path': 'Canvas/BluePlate', 'rect': [.09, .09, .13, .08],
                 'comps': {'graphics': {'fill_rgba': [20, 60, 100, 255]}}}
        findings = richness.flat_value_plate_problems([value, plate])
        self.assertEqual(len(findings), 1)
        self.assertIn('keep an already readable resource HUD transparent', findings[0])
        self.assertIn('fix glyphs/edges/spacing first', findings[0])
        self.assertNotIn('use a plate picture', findings[0])
        self.assertEqual(richness.flat_value_plate_problems([value]), [])


if __name__ == '__main__':
    unittest.main()
