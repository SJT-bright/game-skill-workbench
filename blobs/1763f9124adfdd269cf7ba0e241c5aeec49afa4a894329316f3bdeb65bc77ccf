"""Offline fake observations exercise aggregate migration without a browser/game."""
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import check_ledger as CL
import runtime_unit_reuse as reuse


class UnitReuseTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.project = Path(folder.name)
        self.store = CL.Ledger(self.project)
        self.addCleanup(self.store.close)
        self.conditions = {'engine': '2.x', 'policy': 'new', 'capabilities': {'ads': True}}
        self.roots = {'package': {'skin.png': 'skin-v1', 'game.js': 'game-v1'},
                      'adapter': {'/entry': 'entry-v1', '/other': 'other-v1'}}
        self.scope = {'basis': 'the independent skin ad consumer',
                      'inputs': {'package': ['skin.png'], 'adapter': ['/entry']}}
        self.source_tool, self.target_tool = 'fixed-source-rule', 'fixed-target-rule'
        paired = patch.object(reuse, '_rule_pair', return_value=(self.source_tool, self.target_tool))
        self.rule_patch=paired
        paired.start()
        self.addCleanup(paired.stop)

    def source(self, suite='ad_outcome', *, aggregate_passed=False, failed_unit='bonus/home'):
        if suite == 'ad_outcome':
            cases = [{'id': unit + '/' + kind, 'passed': unit != failed_unit, 'detail': unit + ' ' + kind}
                     for unit in ('skin/home', 'bonus/home') for kind in ('cancel', 'complete')]
            report = {'suite': suite, 'policy': 'new',
                      'entries': [{'id': 'skin/home', 'from': 'ad_entries'},
                                  {'id': 'bonus/home', 'from': 'ad_entries'}],
                      'cases': [{'id': unit, 'cancel_result': 'pass' if unit != failed_unit else 'fail',
                                 'complete_result': 'pass' if unit != failed_unit else 'fail'}
                                for unit in ('skin/home', 'bonus/home')]}
        else:
            cases = [{'id': 'restart', 'passed': aggregate_passed, 'detail': 'kept after restart'}]
            report = {'suite': suite, 'policy': 'new', 'result': 'pass' if aggregate_passed else 'fail',
                      'storage': 'missing=false&numbool=01',
                      'kinds': {'steps': ['buy'], 'none': {}, 'missing': []},
                      'steps': [{'name': 'buy-skin', 'kind': 'buy', 'before': {'coins': 10},
                                 'after': {'coins': 5}, 'after_restart': {'coins': 5}}]}
        report_path = self.project / (suite + '-report.json')
        result_path = self.project / (suite + '-raw-result.json')
        screenshot = self.project / (suite + '.png')
        screenshot.write_bytes(b'offline fake screenshot')
        report_path.write_text(json.dumps(report))
        raw = {'suite': suite, 'passed': aggregate_passed, 'cases': cases,
               'evidence': {'report': str(report_path)}}
        result_path.write_text(json.dumps(raw))
        result = dict(raw, raw_files=[str(report_path), str(result_path), str(screenshot)],
                      browser=True, seconds=12.5, problems=[] if aggregate_passed else ['other independent entry failed'])
        old_plan = self.store.prepare('runtime.' + suite + '/@suite', self.roots,
                                      self.conditions, self.source_tool, domain='platform')
        with contextlib.redirect_stderr(io.StringIO()):
            self.store.execute(old_plan, lambda: result, lambda value: aggregate_passed)
        return self.store.previous(old_plan['check_id'])[0]

    def plan(self, suite='ad_outcome', unit='skin/home'):
        cid = 'runtime.' + suite + '/' + unit
        scope_file = self.project / 'docs/checks/check-inputs.json'
        scope_file.write_text(json.dumps({'schema': CL.SCOPE_SCHEMA, 'checks': {cid: self.scope}}))
        return self.store.prepare(cid, self.roots, self.conditions, self.target_tool, domain='platform')

    def migrate(self, plan, suite='ad_outcome', unit='skin/home'):
        return reuse.reuse_unit(self.store, plan, suite, unit, self.project / (suite + '.mjs'))

    def rewrite_source(self, source):
        with self.store.db:
            self.store.db.execute('UPDATE records SET data=? WHERE check_id=?',
                                  (CL.canonical(source), source['check_id']))

    def test_passing_ad_pair_from_failed_aggregate_preserves_real_source(self):
        source = self.source()
        plan = self.plan()
        rows_before = self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        migrated = self.migrate(plan)
        self.assertEqual(migrated['action'], 'reuse')
        self.assertEqual(plan['action'], 'run')
        record = migrated['record']
        self.assertFalse(record['source_passed'])
        self.assertEqual(record['source_record'], source)
        self.assertEqual(record['binding'], source['binding'])
        self.assertEqual(record['executed_at'], source['executed_at'])
        self.assertEqual(record['files'], source['files'])
        self.assertEqual(record['result']['cases'], source['result']['cases'][:2])
        self.assertEqual(record['source_key'], CL.sha(source['binding']))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0], rows_before)
        self.assertEqual(self.store.previous('runtime.ad_outcome/skin/home'), [])
        browser = Mock(side_effect=AssertionError('must not execute a suite'))
        with contextlib.redirect_stderr(io.StringIO()):
            result, proof = self.store.execute(migrated, browser, lambda value: value['passed'])
        self.assertTrue(result['passed'])
        self.assertTrue(proof['reused'])
        self.assertEqual(proof['original_at'], source['executed_at'])
        browser.assert_not_called()

    def test_failed_ad_pair_is_not_upgraded_to_pass(self):
        self.source()
        plan = self.plan(unit='bonus/home')
        self.assertIs(self.migrate(plan, unit='bonus/home'), plan)

    def test_relevant_input_change_remains_one_scoped_run(self):
        self.source()
        self.roots['package']['skin.png'] = 'changed-skin'
        plan = self.plan()
        self.assertIs(self.migrate(plan), plan)

    def test_unrelated_root_change_still_reuses_precise_projection(self):
        self.source()
        self.roots['package']['game.js'] = 'unrelated-module-change'
        self.roots['adapter']['/other'] = 'unrelated-adapter-change'
        self.assertEqual(self.migrate(self.plan())['action'], 'reuse')

    def test_changed_conditions_do_not_reuse(self):
        self.source()
        self.conditions = dict(self.conditions, policy='legacy')
        plan = self.plan()
        self.assertIs(self.migrate(plan), plan)

    def test_unknown_tool_pair_requires_diagnosis(self):
        source = self.source()
        source['binding']['tool_sha256'] = 'unreviewed arbitrary rules'
        self.rewrite_source(source)
        with self.assertRaisesRegex(CL.NeedsScope, '旧 aggregate 工具版本'):
            self.migrate(self.plan())

    def test_current_plan_must_match_actual_target_tool(self):
        self.source()
        plan = self.plan()
        plan['binding']['tool_sha256'] = 'fake-target'
        with self.assertRaisesRegex(CL.NeedsScope, '当前计划未绑定'):
            self.migrate(plan)

    def test_missing_or_tampered_raw_files_stop_without_browser(self):
        for mode in ('deleted', 'changed', 'unbound'):
            with self.subTest(mode=mode):
                source = self.source()
                path = Path(source['result']['evidence']['report'])
                if mode == 'deleted':
                    path.unlink()
                elif mode == 'changed':
                    path.write_text('{}')
                else:
                    source['files'] = [item for item in source['files'] if item['path'] != str(path)]
                    self.rewrite_source(source)
                with self.assertRaises(CL.NeedsScope):
                    self.migrate(self.plan())
                # Reset this subtest's immutable evidence before the next fake run.
                with self.store.db:
                    self.store.db.execute('DELETE FROM records')

    def test_new_unit_history_wins_over_old_aggregate(self):
        self.source()
        plan = self.plan()
        with contextlib.redirect_stderr(io.StringIO()):
            self.store.execute(plan, lambda: {'passed': False}, lambda value: False)
        later = self.plan()
        self.assertEqual(later['action'], 'blocked_failed')
        self.assertIs(self.migrate(later), later)
        later['action'] = 'run'
        self.assertIs(self.migrate(later), later)

    def test_fatal_or_batch_error_cannot_supply_passing_ad_unit(self):
        source = self.source()
        source['result']['batch_problems'] = ['invalid suite run']
        self.rewrite_source(source)
        with self.assertRaisesRegex(CL.NeedsScope, '全局运行'):
            self.migrate(self.plan())

    def test_save_step_requires_successful_aggregate_and_verified_readback(self):
        source = self.source('save_restart', aggregate_passed=True)
        plan = self.plan('save_restart', 'step/buy-skin')
        migrated = self.migrate(plan, 'save_restart', 'step/buy-skin')
        self.assertEqual(migrated['action'], 'reuse')
        self.assertEqual(migrated['record']['source_record'], source)
        self.assertEqual(migrated['record']['result']['cases'][0]['detail']['after_restart'], {'coins': 5})

    def test_failed_save_aggregate_cannot_supply_step_even_if_one_readback_looks_good(self):
        self.source('save_restart', aggregate_passed=False)
        plan = self.plan('save_restart', 'step/buy-skin')
        self.assertIs(self.migrate(plan, 'save_restart', 'step/buy-skin'), plan)

    def test_save_readback_validation_is_strict_about_json_types(self):
        report = {'result': 'pass', 'steps': [{'name': 'one', 'before': 4, 'after': 0, 'after_restart': False}]}
        result = {'cases': [{'id': 'restart', 'passed': True}]}
        self.assertIsNone(reuse._save_cases(report, result, 'step/one', True))
        report['steps'][0].update(before=False, after=0, after_restart=0)
        self.assertIsNotNone(reuse._save_cases(report, result, 'step/one', True))

    def test_save_kinds_needs_original_empty_missing_list(self):
        self.source('save_restart', aggregate_passed=True)
        plan = self.plan('save_restart', '@kinds')
        self.assertEqual(self.migrate(plan, 'save_restart', '@kinds')['action'], 'reuse')
        self.assertIsNone(reuse._save_cases({'result': 'pass', 'kinds': {'missing': ['buy']}},
                                          {'cases': [{'id': 'restart', 'passed': True}]}, '@kinds', True))

    def test_discovery_catalog_never_uses_failed_parent_as_global_pass(self):
        self.source(aggregate_passed=False)
        plan = self.plan(unit='@discovered')
        self.assertIs(self.migrate(plan, unit='@discovered'), plan)

    def test_derived_claim_is_checked_against_the_real_aggregate_record(self):
        source=self.source()
        plan=self.migrate(self.plan())
        records={source['check_id']:[(CL.sha(source['binding']),source)]}
        self.assertEqual(reuse.verify_derived_source(records,plan),plan['record'])
        forged=copy.deepcopy(plan)
        forged['record']['source_record']['executed_at']='invented'
        with self.assertRaisesRegex(CL.NeedsScope,'不在真实 ledger'):
            reuse.verify_derived_source(records,forged)

    def test_archive_legacy_unit_identity_is_stable_after_targeted_new_execution(self):
        import regression_baseline as baseline
        import zipfile
        old_files={'game.js':b'game','skin.png':b'skin'}
        self.roots['package']={name:CL.sha(raw) for name,raw in old_files.items()}
        source=self.source(aggregate_passed=True,failed_unit=None)
        archive=self.project/'previous.zip'
        with zipfile.ZipFile(archive,'w') as out:
            for name,raw in old_files.items():out.writestr(name,raw)
        current=dict(old_files,**{'game.js':b'new bonus module'})
        self.roots['package']={name:CL.sha(raw) for name,raw in current.items()}
        stable=self.migrate(self.plan())
        skin_scope=copy.deepcopy(self.scope)
        self.scope={'basis':'bonus game module consumer','inputs':{'package':['game.js'],'adapter':['/entry']}}
        changed=self.plan(unit='bonus/home')
        scope_path=self.project/'docs/checks/check-inputs.json'
        scope_path.write_text(json.dumps({'schema':CL.SCOPE_SCHEMA,'checks':{
            stable['check_id']:skin_scope,changed['check_id']:self.scope}}))
        groups={'runtime':[stable,changed]}
        with patch('verify_native_zip.receipt_status',return_value={
                'entry':'unregistered','receipt':str(self.project/'missing-receipt.json')}):
            before=baseline.identity(archive,current,self.project,groups)
            new_raw=self.project/'new-independent-observation.json'
            new_raw.write_text('{"offline_fixture":true}')
            with contextlib.redirect_stderr(io.StringIO()):
                self.store.execute(changed,lambda:{'passed':True,'evidence':str(new_raw)},lambda value:value['passed'])
            completed=self.plan(unit='bonus/home')
            # plan() refreshes this temp scope file; restore the full same scope identity.
            scope_path.write_text(json.dumps({'schema':CL.SCOPE_SCHEMA,'checks':{
                stable['check_id']:skin_scope,completed['check_id']:self.scope}}))
            after=baseline.identity(archive,current,self.project,{'runtime':[stable,completed]})
        self.assertEqual(before,after)
        self.assertEqual(before['sources'][changed['check_id']]['kind'],'legacy_unit_archive_observation')
        self.assertEqual(before['sources'][changed['check_id']]['key'],CL.sha(source['binding']))

    def test_precise_scope_can_recollect_only_the_explicit_missing_prior_evidence(self):
        cid='runtime.precise/item'
        old=self.store.prepare(cid,self.roots,self.conditions,self.target_tool,domain='platform')
        evidence=self.project/'old-evidence.json'
        evidence.write_text('{"original":true}')
        with contextlib.redirect_stderr(io.StringIO()):
            result,_=self.store.execute(old,lambda:{'passed':True,'evidence':str(evidence)},lambda value:value['passed'])
        frozen=Path(result['evidence']);frozen.unlink()
        request={'prior_key':old['key'],'reason':'Original and backup evidence unavailable',
                 'searched_locations':[str(frozen),str(self.project/'backup')]}
        scope_path=self.project/'docs/checks/check-inputs.json'
        scope_path.write_text(json.dumps({'schema':CL.SCOPE_SCHEMA,'checks':{cid:self.scope},
                                          'evidence_rechecks':{cid:request}}))
        pending=self.store.prepare(cid,self.roots,self.conditions,self.target_tool,domain='platform')
        self.assertEqual(pending['action'],'run')
        self.assertEqual(pending['evidence_recheck'],request)
        self.assertNotEqual(pending['key'],old['key'])
        evidence.write_text('{"new_actual_observation":true}')
        with contextlib.redirect_stderr(io.StringIO()):
            self.store.execute(pending,lambda:{'passed':True,'evidence':str(evidence)},lambda value:value['passed'])
        self.assertEqual(len(self.store.previous(cid)),2)
        self.assertEqual(self.store.prepare(cid,self.roots,self.conditions,self.target_tool)['action'],'reuse')

    def test_real_reviewed_tool_pair_reuses_without_mocking_the_rule_gate(self):
        import sys
        check=Path(__file__).resolve().parents[2]/'cocos-game-check/package-check/scripts'
        sys.path.insert(0,str(check))
        self.addCleanup(sys.path.remove,str(check))
        self.rule_patch.stop()
        script=check/'runtime_regression/suites/ad_outcome.mjs'
        self.source_tool,self.target_tool=reuse._rule_pair('ad_outcome',script,self.conditions)
        source=self.source()
        plan=self.plan()
        migrated=reuse.reuse_unit(self.store,plan,'ad_outcome','skin/home',script)
        self.assertEqual(migrated['action'],'reuse')
        records={source['check_id']:[(CL.sha(source['binding']),source)]}
        self.assertEqual(reuse.verify_derived_source(records,migrated),migrated['record'])

    def test_failed_legacy_unit_remains_a_known_observation_not_a_new_check(self):
        source=self.source()
        records={source['check_id']:[(CL.sha(source['binding']),source)]}
        plan=self.plan(unit='bonus/home')
        self.assertIsNone(reuse.legacy_comparison_source(records,plan,self.roots['package']))
        self.assertTrue(reuse.legacy_observation_exists(records,plan,self.roots['package']))

    def test_new_precise_scope_cannot_skip_latest_matching_failure_for_older_pass(self):
        cid='runtime.precise/item'
        first=self.store.prepare(cid,self.roots,self.conditions,self.target_tool)
        with contextlib.redirect_stderr(io.StringIO()):
            self.store.execute(first,lambda:{'passed':True},lambda value:value['passed'])
        scope_path=self.project/'docs/checks/check-inputs.json'
        scope_path.write_text(json.dumps({'schema':CL.SCOPE_SCHEMA,'checks':{cid:self.scope}}))
        failed=self.store.prepare(cid,self.roots,self.conditions,self.target_tool)
        failed['action']='run'  # An offline real failing observation, not a manufactured pass.
        with contextlib.redirect_stderr(io.StringIO()):
            self.store.execute(failed,lambda:{'passed':False},lambda value:value['passed'])
        newer_scope=dict(self.scope,basis='new precise declaration of exactly the same consumer')
        scope_path.write_text(json.dumps({'schema':CL.SCOPE_SCHEMA,'checks':{cid:newer_scope}}))
        target=self.store.prepare(cid,self.roots,self.conditions,self.target_tool)
        self.assertEqual(target['action'],'blocked_failed')
        self.assertFalse(target['record']['passed'])
        self.assertEqual(len(self.store.previous(cid)),2)
        with patch.dict('os.environ',{'CHECK_RETRY_REASON':'the diagnosed environment was restored'}):
            retry=self.store.prepare(cid,self.roots,self.conditions,self.target_tool)
        self.assertEqual(retry['action'],'run')
        self.assertFalse(retry['record']['passed'])


class ReviewedRuleTests(unittest.TestCase):
    def test_fixed_review_reconstructs_whole_new_scripts_and_keeps_original_assertions(self):
        suites = Path(__file__).resolve().parents[2] / 'cocos-game-check/package-check/scripts/runtime_regression/suites'
        for suite in ('ad_outcome', 'save_restart'):
            with self.subTest(suite=suite):
                old = reuse._reviewed_source(suite, suites / (suite + '.mjs'))
                self.assertEqual(reuse._digest(old), reuse.OLD_SHA[suite])

    def test_any_unreviewed_script_or_manifest_byte_refuses_equivalence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            suite = 'ad_outcome'
            script = root / (suite + '.mjs')
            suites = Path(__file__).resolve().parents[2] / 'cocos-game-check/package-check/scripts/runtime_regression/suites'
            script.write_bytes((suites / script.name).read_bytes() + b'\n// unreviewed change\n')
            with self.assertRaisesRegex(CL.NeedsScope, '固定的整文件审查对'):
                reuse._reviewed_source(suite, script)
            for file in reuse.FIXTURES.iterdir():
                (root / file.name).write_bytes(file.read_bytes())
            (root / 'unit-rule-review.json').write_text('{}')
            with patch.object(reuse, 'FIXTURES', root):
                with self.assertRaisesRegex(CL.NeedsScope, '审查清单已经变化'):
                    reuse._reviewed_source(suite, script)


if __name__ == '__main__':
    unittest.main()
