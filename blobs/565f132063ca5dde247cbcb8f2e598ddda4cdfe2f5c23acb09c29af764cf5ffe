"""Merged default/explicit extension behavior: same policy across source, module, and UI audits."""
import json
from pathlib import Path
import tempfile
import unittest
from audit_platform_markers import audit
from feature_policy import enabled, removed, economy_disabled
from audit_ui_coverage import share_entries, REMOVED_WORDS

class FusionPolicyTests(unittest.TestCase):
    def test_explicit_records_change_only_the_requested_extension(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'assets').mkdir()
            source = root / 'assets/main.ts'
            source.write_text('setImRankData(); createRewardedVideoAd();')
            self.assertIn('setImRankData', audit(root, features=('iaa',))['share_calls_in_source'])
            (root / 'docs/league').mkdir(parents=True)
            (root / 'docs/league/decision.json').write_text(json.dumps({'decision': 'add'}))
            flags = enabled(root)
            self.assertFalse(flags['league'])
            self.assertTrue(removed('Weekly League', flags))
            # 2026-10-27 (user): the 7-day check-in is a required module, so feature_policy.enabled() has it on unless
            # docs/features.json says daily_checkin false (audit_optional_features.py checkin_required rejects that for
            # remake games). This test still expected the pre-10-27 default (off) and failed from then on
            # (release-selftest known_failures.json: "原因没查", found 2026-11-01).
            self.assertTrue(flags['checkin'])
            self.assertFalse(removed('Daily Check-in', flags))
            self.assertIn('setImRankData', audit(root, features=('iaa',))['share_calls_in_source'])
            source.write_text('setImRankData(); shareAppMessage(); navigateToMiniProgram();')
            hits = audit(root, features=('iaa',))['share_calls_in_source']
            self.assertIn('shareAppMessage', hits)
            self.assertIn('navigateToMiniProgram', hits)
            (root / 'docs/features.json').write_text(json.dumps({'daily_checkin': False}))
            self.assertTrue(removed('Daily Check-in', enabled(root)))
            (root / 'docs/features.json').write_text(json.dumps({'daily_checkin': True}))
            self.assertFalse(removed('Daily Check-in', enabled(root)))
            self.assertTrue(removed('More Games', enabled(root)))
            self.assertTrue(removed('Share', enabled(root)))

    def test_no_skin_game_does_not_require_an_empty_collection_system(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / 'docs').mkdir()
            report = {'passed': True, 'decision': {'skins': False}}
            self.assertFalse(economy_disabled(root, report))
            (root / 'docs/modules.json').write_text(json.dumps({'schema': 'game_modules.v1', 'asked': 'user declined skins',
                                                              'skins': {'suitable': False, 'user_choice': False}}))
            self.assertTrue(economy_disabled(root, report))
            (root / 'docs/economy').mkdir()
            table = root / 'docs/economy/unlock_table.json'
            table.write_text(json.dumps({'items': [{'id': 'tool', 'group': 'tools'}]}))
            self.assertFalse(economy_disabled(root, report))
            table.write_text(json.dumps({'items': []}))
            self.assertTrue(economy_disabled(root, report))
            self.assertFalse(economy_disabled(root, {'passed': True, 'decision': {'skins': True}}))

    def test_layout_entries_include_nested_removed_features(self):
        layout = {'buttons': [{'name': 'Play'}], 'boxes': [{'contents': [{'name': 'BtnCheckIn'}]}]}
        self.assertEqual(share_entries(layout, REMOVED_WORDS), ['BtnCheckIn'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
