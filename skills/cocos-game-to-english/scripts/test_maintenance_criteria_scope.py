#!/usr/bin/env python3
"""Synthetic, fail-closed tests for source-maintenance criterion filtering."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import maintenance_criteria_scope as m

BINDING = {'source_sha256': 's', 'native_tree_sha256': 'n', 'web_tree_sha256': 'w', 'build_tag': 'r18'}


def ref(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class CriteriaDerivationTests(unittest.TestCase):
    def setUp(self):
        self.refs = {k: {'path': f'/evidence/{k}.json', 'sha256': k} for k in (*m.REQUIRED_DOCS, 'maintenance_scope')}
        self.scope = {'new_modules_requested': False, 'existing_features': ['daily_checkin', 'collection', 'hero_trial']}
        self.features = {'daily_checkin': True, 'skin_bonus': False}
        self.level = {'mode': 'endless'}
        self.league = {'decision': 'none'}

    def derive(self, **changes):
        vals = dict(features=self.features, level=self.level, league=self.league, scope=self.scope,
                    refs=self.refs, route_labels='', binding=BINDING)
        vals.update(changes)
        return m.derive_criteria(**vals)

    def test_narrow_templates_scoped_out_but_existing_contracts_remain(self):
        report = self.derive()
        req = set(report['required_criteria'])
        out = set(report['scoped_out_criteria'])
        self.assertIn('FEAT-02.original_seven_day_signin', req)
        self.assertIn('MOD-02.original_reward_behavior_and_no_stall', req)
        self.assertIn('AD-01.existing_ad_entry_inventory', req)
        self.assertIn('AD-02.existing_ad_completion_once', req)
        self.assertIn('CORE-01.original_match_and_round_flow', req)
        self.assertIn('UI-01.player_visible_english_and_no_share', req)
        self.assertIn('STORAGE-01.current_native_storage_contract', req)
        self.assertIn('LOAD-01.current_loading_and_recovery', req)
        self.assertIn('RANK-02.original_in_match_rank_behavior', req)
        self.assertIn('MOD-01.add_skin_v1_module', out)
        self.assertIn('MOD-01.add_fixed_70_level_map', out)
        self.assertIn('MOD-01.add_home_gift_box_module', out)
        self.assertIn('RANK-01.add_weekly_league_system', out)
        self.assertIn('FEAT-00.replace_original_signin_with_DailyCheckin_ts', out)
        self.assertFalse(any(x.startswith('AD-') or 'existing_reward' in x for x in out))

    def test_enabled_features_and_routes_restore_applicability(self):
        features = {'daily_checkin': True, 'skin_bonus': True}
        scope = {'new_modules_requested': True, 'existing_features': ['daily_checkin', 'skin_bonus', 'collection']}
        level = {'mode': 'levels'}
        league = {'decision': 'add'}
        report = self.derive(features=features, scope=scope, level=level, league=league)
        req, out = set(report['required_criteria']), set(report['scoped_out_criteria'])
        self.assertIn('ECON-01.authorized_skin_bonus_progression', req)
        self.assertIn('LEVEL-01.authorized_fixed_level_plan', req)
        self.assertIn('RANK-02.authorized_weekly_league_behavior', req)
        self.assertIn('MOD-01.authorized_new_reward_modules', req)
        self.assertNotIn('MOD-01.add_skin_v1_module', out)
        self.assertNotIn('MOD-01.add_fixed_70_level_map', out)
        self.assertNotIn('RANK-02.add_weekly_league_behavior', out)
        self.assertNotIn('MOD-01.add_home_gift_box_module', out)

    def test_existing_map_or_league_contradiction_blocks_exclusion(self):
        with self.assertRaisesRegex(ValueError, 'league decision none conflicts'):
            self.derive(scope={'new_modules_requested': False, 'existing_features': ['daily_checkin', 'weekly_league']})

    def test_applicable_template_feature_without_real_gate_domain_blocks(self):
        report = self.derive(level={'mode': 'levels'})
        with self.assertRaisesRegex(ValueError, 'no enforced source-maintenance check domain'):
            m.validate_supported_criteria(report)

    def test_preservation_matrix_uses_only_enforced_check_domains(self):
        m.validate_supported_criteria(self.derive())


class EvidenceGateTests(unittest.TestCase):
    def test_missing_and_stale_refs_block_before_scope_evaluation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel, value in [(m.REQUIRED_DOCS['features'], {'schema':'optional_features.v1','skin_bonus':False,'daily_checkin':True,'asked':'preserve'}),
                               (m.REQUIRED_DOCS['level_plan'], {'schema':'level_plan.v1','mode':'endless'}),
                               (m.REQUIRED_DOCS['league_decision'], {'schema':'league_decision.v1','decision':'none'})]:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps(value))
            record = {'schema': m.SCHEMA, 'binding': BINDING, 'inputs': {k:ref(root/v) for k,v in m.REQUIRED_DOCS.items()}}
            with self.assertRaisesRegex(ValueError, 'evidence reference must be object'):
                m.evaluate(record, root, BINDING, root)
            record['inputs']['features'] = {'path': str(root/m.REQUIRED_DOCS['features']), 'sha256':'0'*64}
            record['inputs']['level_plan'] = ref(root/m.REQUIRED_DOCS['level_plan'])
            record['inputs']['league_decision'] = ref(root/m.REQUIRED_DOCS['league_decision'])
            with self.assertRaisesRegex(ValueError, 'missing/changed'):
                m.evaluate(record, root, BINDING, root)

    def test_missing_decision_file_and_stale_binding_block(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            record = {'schema':m.SCHEMA, 'binding':{'source_sha256':'old'}, 'inputs':{}}
            with self.assertRaisesRegex(ValueError, 'missing or stale'):
                m.evaluate(record, root, BINDING, root)
            record['binding'] = BINDING
            with self.assertRaisesRegex(ValueError, 'required current decision document missing'):
                m.evaluate(record, root, BINDING, root)

    def test_criteria_matrix_cannot_hide_required_failure(self):
        # Required check domain contract is separately immutable in the caller.
        from pathlib import Path as P
        source = (P(__file__).parent/'audit_source_maintenance.py').read_text()
        self.assertIn("required = {'LOAD-01','LOAD-03','STORAGE-01','BUSINESS','PAGES','NORMAL','AUDIO','VISUAL','COVERAGE','SCOPE','ENGLISH'}", source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
