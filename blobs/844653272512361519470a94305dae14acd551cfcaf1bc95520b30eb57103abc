#!/usr/bin/env python3
"""Canonical writer consumes exact original per-case evidence, never starts CI.

The fixture catalogue has one explicitly synthetic runtime unit. Production input
validation, ledger binding/freezing, scope authorization, result judges and full
coverage validation are real. The only manufactured observations are labelled
fixture records created at a separate explicit producer step below. No browser.
"""
import ast
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
CHECK = HERE.parents[1] / 'cocos-game-check/package-check/scripts'
sys.path[:0] = [str(HERE), str(CHECK)]
import make_tiktok_zip as M
import build_checked_zip as B
import check_package as C
import check_ledger as L
import regression_scope_gate as S
import runtime_regression as RR
import runtime_incremental as RI
import ad_regression as AR
import ad_incremental as AI
from test_check_inputs import PAGES
import page_registry


class WriterRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='writer-ledger-fixture-', dir='/private/tmp')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        (self.project / 'assets').mkdir(parents=True)
        (self.project / 'project.json').write_text('{"version":"2.4.15"}')
        pages = self.project / 'docs/logic/pages.json'
        pages.parent.mkdir(parents=True)
        pages.write_text(json.dumps(PAGES))
        outputs, report = page_registry.build(self.project)
        self.assertTrue(report['passed'], report)
        page_registry.write(self.project, outputs)
        self.adapter = self.project / 'qa/ad-regression.json'
        adapter_data = json.loads(self.adapter.read_text())
        adapter_data['play'] = 'return {x:1,y:1};'  # synthetic unit input, never executed
        self.adapter.write_text(json.dumps(adapter_data))
        self.native = self.project / 'native'; self.native.mkdir()
        (self.native / 'game.js').write_text("require('./main');")
        (self.native / 'main.js').write_text('// explicitly synthetic package input')
        self.suites = self.root / 'suites'; self.suites.mkdir()
        (self.suites / 'network.json').write_text(json.dumps({'name':'network','applies':['tiktok'],
            'needs':['play','ad_entries','ad_outcome','resume_play'],'host':'none','engines':['2.x'],'owner':'synthetic factory contract'}))
        (self.suites / 'network.mjs').write_text('// synthetic unit; never executed')
        def start(patcher):
            value = patcher.start()
            self.addCleanup(patcher.stop)
            return value
        start(mock.patch.object(RR, 'SUITES_DIR', self.suites))
        start(mock.patch.dict(os.environ, {RR.ENV_ADAPTER:'', RR.ENV_CAPABILITIES:'', S.ENV_PLAN:'',
                                          'ENGLISH_CHECK_PROJECT':str(self.project)}))
        self.ad_execution = start(mock.patch.object(AR, '_run_uncached', side_effect=AssertionError('writer opened ad CI')))
        self.raw_runtime = RR._run_uncached
        self.runtime_execution = start(mock.patch.object(RR, '_run_uncached', side_effect=AssertionError('writer opened runtime CI')))
        self.browser = start(mock.patch.object(RR, 'find_browser', side_effect=AssertionError('writer looked for browser')))

    def files(self):
        return C.native_files(self.native)

    def seed(self, *, policy='new', rewarded=False, fail_id=None):
        """An explicit fixture producer, before writer invocation, with real immutable records."""
        if rewarded:
            (self.native / 'game.js').write_text("require('./main');tt.createRewardedVideoAd({});")
        plans = RI.run(RR, self.native, self.adapter, policy=policy, board='remake', plan_only=True)
        ad_plans = AI.run(AR, self.native, self.adapter, plan_only=True) if rewarded else []
        ledger = L.Ledger(self.project)
        try:
            for plan in plans + ad_plans:
                cid = plan['check_id']; good = cid != fail_id
                raw = self.root / (cid.replace('/', '_') + '.json')
                raw.write_text(json.dumps({'fixture_only':True,'check_id':cid,'passed':good}))
                if cid.startswith('ads.'):
                    row = {'case':cid[4:],'ok':good,'problems':[] if good else ['timeout paid twice']}
                    value = {'row':row,'fatal':None,'raw_files':[str(raw)],'warnings':[]}
                    judge = lambda item: AR.judge({'cases':[item['row']]}, [item['row']['case']])[0]
                else:
                    value = {'suite':'network','unit':'@suite','passed':good,
                             'cases':[{'id':'synthetic_postcondition','passed':good}],
                             'problems':[] if good else ['PLAY did nothing'], 'warnings':['fixture warning'],
                             'raw_files':[str(raw)],'evidence':{'report':str(raw)},'browser':False}
                    judge = lambda item: item['passed'] is True
                ledger.execute(plan, lambda value=value:value, judge)
        finally:
            ledger.close()
        return plans + ad_plans

    def consume(self, policy='new', adapter='default'):
        with S.execution_scope():
            result = M.writer_regressions(self.native, self.adapter if adapter == 'default' else adapter,
                                          policy, 'remake', project=self.project)
        self.ad_execution.assert_not_called(); self.runtime_execution.assert_not_called(); self.browser.assert_not_called()
        return result

    def test_new_game_without_adapter_refused_no_execution(self):
        result = self.consume(adapter=None)
        self.assertTrue(result['blocked']); self.assertIn('适配', str(result['problems']))

    def test_new_game_missing_suite_refused_before_browser(self):
        result = self.consume()
        self.assertTrue(result['blocked']); self.assertIn('runtime.network/@suite', str(result['problems']))

    def test_new_game_failed_suite_refused(self):
        self.seed(fail_id='runtime.network/@suite')
        result = self.consume()
        self.assertTrue(result['blocked']); self.assertIn('runtime.network/@suite', str(result['problems']))

    def test_passing_regressions_are_read_from_exact_original_records(self):
        plans = self.seed()
        result = self.consume()
        self.assertFalse(result['blocked'], result)
        runtime = result['runtime_regression']
        self.assertTrue(runtime['passed']); self.assertTrue(runtime['complete'])
        self.assertEqual(runtime['executed_units'], 0); self.assertEqual(runtime['reused_units'], len(plans))
        self.assertIn('fixture warning', result['warnings'])
        self.assertIsNone(C.regression_coverage_problem(result['rewarded_ad_regression'], runtime,
                                                       self.files(), self.adapter, 'new'))
        self.assertIsNotNone(C.regression_record(result['rewarded_ad_regression'], runtime))

    def test_new_game_rewarded_ad_failure_refused(self):
        fail_id = 'ads.' + AR.CASES[-1]
        self.seed(rewarded=True, fail_id=fail_id)
        result = self.consume()
        self.assertTrue(result['blocked']); self.assertIn(fail_id, str(result['problems']))

    def test_rewarded_case_matrix_is_complete_and_reused(self):
        self.seed(rewarded=True)
        result = self.consume()
        self.assertFalse(result['blocked'], result)
        ad = result['rewarded_ad_regression']
        self.assertEqual(sorted(row['case'] for row in ad['cases']), sorted(AR.default_cases(AR.load_adapter(self.adapter))))
        self.assertEqual(ad['executed_units'], 0); self.assertTrue(ad['complete'])

    def test_env_adapter_is_used_like_legacy_build_api(self):
        self.seed()
        with mock.patch.dict(os.environ, {RR.ENV_ADAPTER:str(self.adapter)}):
            result = self.consume(adapter=None)
        self.assertFalse(result['blocked'], result)

    def test_legacy_game_missing_or_failed_evidence_is_not_downgraded(self):
        missing = self.consume('legacy')
        self.assertTrue(missing['blocked'])
        self.seed(policy='legacy', fail_id='runtime.network/@suite')
        failed = self.consume('legacy')
        self.assertTrue(failed['blocked']); self.assertIn('runtime.network/@suite', str(failed['problems']))

    def test_native_or_adapter_mutation_does_not_trigger_full_rerun(self):
        self.seed()
        (self.native / 'added.js').write_text('// actual new package dependency')
        self.assertTrue(self.consume()['blocked'])
        (self.native / 'added.js').unlink()
        data = json.loads(self.adapter.read_text()); data['home'] = 'return false;'
        self.adapter.write_text(json.dumps(data))
        self.assertTrue(self.consume()['blocked'])

    def test_lost_frozen_raw_evidence_blocks_only_its_node(self):
        self.seed()
        ledger = L.Ledger(self.project)
        try:
            row = ledger.previous('runtime.network/@suite')[0]
            Path(row['files'][0]['path']).unlink()
        finally: ledger.close()
        result = self.consume()
        self.assertTrue(result['blocked']); self.assertIn('runtime.network/@suite', str(result['problems']))

    def test_explicit_producer_without_browser_still_refuses_before_suite(self):
        # Environment diagnostics live at the explicit producer, never writer replay.
        with mock.patch.object(RR, 'touch_problem', return_value=None), \
                mock.patch.object(RR, 'find_browser', side_effect=RR.EnvironmentIncomplete('Ego CLI unavailable')), \
                mock.patch.object(RR, 'run_suite', side_effect=AssertionError('no browser suite')) as suite:
            with self.assertRaisesRegex(RR.EnvironmentIncomplete, 'Ego CLI unavailable'):
                self.raw_runtime(self.native, self.adapter, ['network'], policy='new')
            suite.assert_not_called()

    def test_empty_input_remains_not_run_before_any_execution(self):
        data = json.loads(self.adapter.read_text()); data['ad_entries'] = []
        self.adapter.write_text(json.dumps(data))
        result = self.consume()
        self.assertTrue(result['blocked']); self.assertIn('ad_entries', str(result['problems']).lower())


class Interface(unittest.TestCase):
    def test_both_legacy_names_delegate_to_one_engine(self):
        self.assertIn('make_tiktok_zip.write_package(', inspect.getsource(B.build))
        source = inspect.getsource(M.write_package)
        calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)]
        regression = next(node for node in calls if isinstance(node.func, ast.Name) and node.func.id == 'writer_regressions')
        receipt = next(node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == 'make_receipt')
        self.assertLess(regression.lineno, receipt.lineno)
        self.assertIn('reuse_only=True', source)
        self.assertIn('cases=[]', inspect.getsource(M.writer_regressions))
        self.assertIn('suites=[]', inspect.getsource(M.writer_regressions))


if __name__ == '__main__':
    unittest.main(verbosity=2)
