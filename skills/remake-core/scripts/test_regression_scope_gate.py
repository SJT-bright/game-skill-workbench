"""Offline tests for the mandatory package regression plan."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

import check_ledger as ledger
import regression_scope_gate as gate


class ScopeGateTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.project = Path(folder.name).resolve()
        (self.project / 'assets').mkdir()
        (self.project / 'project.json').write_text('{}')
        self.native = self.project / 'native'
        self.native.mkdir()
        self.adapter = self.project / 'adapter.json'
        self.adapter.write_text('{}')
        self.files = {'game.js': b'game', 'skin.png': b'new skin'}
        for name, data in self.files.items():
            (self.native / name).write_bytes(data)
        self.roots = {'package': ledger.manifest(self.native), 'adapter': ledger.json_manifest({})}
        self.plan_path = self.project / 'scope.json'
        self.scope_path = gate.scope_path(self.project)
        self.scope_path.parent.mkdir(parents=True)
        self.scope_path.write_text(json.dumps({'schema': ledger.SCOPE_SCHEMA, 'checks': {}}))
        self.environ = patch.dict(os.environ)
        self.environ.start()
        self.addCleanup(self.environ.stop)
        os.environ.pop(gate.ENV_PLAN, None)
        os.environ.pop('ENGLISH_CHECK_PROJECT', None)
        token = gate._active_plan.set(None)
        self.addCleanup(gate._active_plan.reset, token)

    def row(self, case, action='run', paths=('skin.png',)):
        return {'check_id': case, 'key': 'key-' + case, 'action': action, 'why': 'checked dependency',
                'scope': {'basis': 'actual skin consumer', 'inputs': {'package': list(paths)}}}

    def plan(self, rows, **changes):
        actions = {r['check_id']: {'key': r['key'], 'action': r['action'], 'reason': r['why']} for r in rows}
        doc = {
            'schema': gate.SCHEMA, 'mode': 'scoped', 'project': str(self.project),
            'scope_sha256': gate.scope_digest(self.project), 'baseline': {'path': 'original.zip'},
            'native_tree': ledger.sha(self.roots['package']), 'adapter_tree': ledger.sha(self.roots['adapter']),
            'actions': {'ads': actions},
        }
        doc.update(changes)
        self.write_plan(doc)
        return doc

    def write_plan(self, doc):
        self.plan_path.write_text(json.dumps(doc))
        os.environ[gate.ENV_PLAN] = str(self.plan_path)

    def activate_plan(self):
        gate._active_plan.set(gate.digest(self.plan_path))

    def authorize(self, rows, **options):
        return gate.authorize_batch(self.project, self.roots, rows, operation='ads', **options)

    def test_missing_plan_stops(self):
        with self.assertRaisesRegex(ledger.NeedsScope, 'scope_required.*执行计划'):
            self.authorize([self.row('ads.normal')])

    def test_stale_plan_cannot_follow_changed_candidate_or_scope(self):
        row = self.row('ads.normal')
        self.plan([row])
        self.activate_plan()
        self.roots['package']['skin.png'] = 'changed'
        with self.assertRaisesRegex(ledger.NeedsScope, 'Native'):
            self.authorize([row])
        self.scope_path.write_text('{"changed": true}')
        with self.assertRaisesRegex(ledger.NeedsScope, '依赖声明'):
            self.authorize([row])

    def test_altered_plan_cannot_rebind_active_execution(self):
        row = self.row('ads.normal')
        plan = self.plan([row])
        self.activate_plan()
        plan['authorization'] = 'added after the plan was bound'
        self.write_plan(plan)
        with self.assertRaisesRegex(ledger.NeedsScope, '更换|变化'):
            self.authorize([row])

    def test_full_run_cannot_omit_user_authorization(self):
        row = self.row('ads.normal', paths=('*',))
        self.plan([row], mode='full')
        self.activate_plan()
        with self.assertRaisesRegex(ledger.NeedsScope, '明确指令'):
            self.authorize([row])

    def test_wildcard_cannot_explain_scoped_run_even_mixed_with_exact_path(self):
        for paths in (('*',), ('**',), ('skin.png', '*'), ()):
            with self.subTest(paths=paths):
                row = self.row('ads.normal', paths=paths)
                self.plan([row])
                self.activate_plan()
                with self.assertRaisesRegex(ledger.NeedsScope, '整包或空范围'):
                    self.authorize([row])

    def test_unapproved_case_or_changed_execution_identity_stops(self):
        row = self.row('ads.normal')
        self.plan([row])
        self.activate_plan()
        with self.assertRaisesRegex(ledger.NeedsScope, '计划外检查'):
            self.authorize([row, self.row('ads.cancel')])
        with self.assertRaisesRegex(ledger.NeedsScope, '发生变化'):
            self.authorize([dict(row, key='different-rule-or-binding')])

    def test_reuse_cannot_be_promoted_to_run_after_plan(self):
        row = self.row('ads.normal', action='reuse')
        self.plan([row])
        self.activate_plan()
        with self.assertRaisesRegex(ledger.NeedsScope, '未获本次重跑'):
            self.authorize([dict(row, action='run')])

    def test_atomic_suite_without_granularity_evidence_stops(self):
        row = self.row('runtime.save_restart/@suite')
        self.plan([], actions={'runtime': {row['check_id']: row}})
        self.activate_plan()
        with self.assertRaisesRegex(ledger.NeedsScope, '先拆分到具体用例'):
            gate.authorize_batch(self.project, self.roots, [row], operation='runtime')

    def test_real_ledger_narrow_run_preserves_unaffected_evidence(self):
        paths = {'ads.normal': 'skin.png', 'ads.cancel': 'game.js'}
        scope = {cid: {'basis': 'independent consumer', 'inputs': {'package': [path]}}
                 for cid, path in paths.items()}
        self.scope_path.write_text(json.dumps({'schema': ledger.SCOPE_SCHEMA, 'checks': scope}))
        old = {'game.js': b'game', 'skin.png': b'old skin'}
        old_roots = {'package': gate.package_manifest(old), 'adapter': self.roots['adapter']}
        previous = self.project / 'original.zip'
        with zipfile.ZipFile(previous, 'w') as archive:
            for name, data in old.items():
                archive.writestr(name, data)
        store = ledger.Ledger(self.project)
        self.addCleanup(store.close)
        for cid in paths:
            initial = store.prepare(cid, old_roots, {}, 'tool', domain='platform')
            store.execute(initial, lambda: {'passed': True}, lambda result: result['passed'])
        plans = [store.prepare(cid, self.roots, {}, 'tool', domain='platform') for cid in paths]
        self.assertEqual([row['action'] for row in plans], ['run', 'reuse'])
        baseline = {'path': str(previous), 'sha256': gate.digest(previous)}
        groups = {'ads': plans, 'runtime': []}
        with patch.object(gate, 'baseline_identity', return_value=baseline), \
             patch.object(gate, '_observe', return_value=groups):
            result = gate.create_plan(self.project, self.files, self.adapter, board='localize',
                                      policy='new', prior=previous, mode='scoped',
                                      proposed={'ads.normal': 'the skin consumer changed'})
            self.write_plan(result)
            execution = gate.preflight(self.project, self.files, self.adapter, board='localize',
                                       policy='new', prior=previous)
        self.assertEqual(execution['allowed'], ['ads.normal'])
        self.assertEqual(self.authorize(plans), execution['plan_sha256'])
        run_batch = Mock(return_value={'ads.normal': {'passed': True}})
        _, evidence = store.execute_batch(plans, run_batch, lambda result: result['passed'])
        run_batch.assert_called_once_with(['ads.normal'])
        self.assertTrue(evidence['ads.cancel']['reused'])
        self.assertEqual(evidence['ads.cancel']['source_key'], ledger.sha(plans[1]['record']['binding']))

    def test_independently_changed_cases_are_not_rejected_by_their_count(self):
        previous=self.project/'previous.zip'
        with zipfile.ZipFile(previous,'w') as archive:
            archive.writestr('game.js',b'old game')
            archive.writestr('skin.png',b'old skin')
        baseline={'path':str(previous),'sha256':gate.digest(previous)}
        groups={'ads':[self.row('ads.normal',paths=('game.js',)),
                       self.row('ads.cancel',paths=('skin.png',))],'runtime':[]}
        proposed={'ads.normal':'game module changed','ads.cancel':'skin consumer changed'}
        gate._check_impact(self.project,groups,proposed,'scoped',baseline,self.files)

    def test_two_changed_cases_still_require_individual_approval(self):
        previous=self.project/'previous.zip'
        with zipfile.ZipFile(previous,'w') as archive:
            archive.writestr('game.js',b'old game')
            archive.writestr('skin.png',b'old skin')
        groups={'ads':[self.row('ads.normal',paths=('game.js',)),
                       self.row('ads.cancel',paths=('skin.png',))],'runtime':[]}
        with self.assertRaisesRegex(ledger.NeedsScope,'执行范围之外'):
            gate._check_impact(self.project,groups,{'ads.normal':'changed'},'scoped',
                               {'path':str(previous),'sha256':gate.digest(previous)},self.files)

    def test_reuse_only_rejects_any_actual_run(self):
        row = self.row('ads.normal')
        self.plan([row], mode='reuse-only')
        self.activate_plan()
        with self.assertRaisesRegex(ledger.NeedsScope, '纯沿用计划禁止启动浏览器'):
            self.authorize([row])

    def test_repair_reports_all_gaps_and_preserves_valid_evidence_without_execution(self):
        groups = {'ads': [self.row('ads.normal', action='reuse')], 'runtime': [
            self.row('runtime.ad_entries/skin/unowned', action='blocked_failed', paths=('*',)),
            self.row('runtime.save_restart/@suite', paths=('skin.png',)),
        ]}
        with patch.object(gate, '_observe', return_value=groups), \
             patch.object(gate, 'create_plan', side_effect=gate.ScopeRepairRequired('missing mapping')):
            report, plan = gate.repair_report(self.project, self.files, self.adapter, board='localize',
                                              policy='new', prior=None, mode='scoped', proposed={})
        self.assertIsNone(plan)
        self.assertEqual(report['status'], 'repair_required')
        self.assertFalse(report['task_terminal'])
        self.assertEqual(report['browser_launches'], 0)
        self.assertEqual(report['preserved'], ['ads.normal'])
        self.assertEqual({issue['kind'] for issue in report['issues']},
                         {'blocked_failed', 'dependency_or_execution_unit', 'plan_repair'})
        self.assertEqual(report['continuation']['action'], 'repair_and_replan')

    def test_repair_returns_executable_plan_only_after_the_original_gate_passes(self):
        groups = {'ads': [self.row('ads.normal', action='reuse')], 'runtime': []}
        verified = {'schema': gate.SCHEMA, 'actions': {'ads': {}, 'runtime': {}}}
        with patch.object(gate, '_observe', return_value=groups), \
             patch.object(gate, 'create_plan', side_effect=[gate.ScopeRepairRequired('prior receipt missing'), verified]) as create:
            failed, plan = gate.repair_report(self.project, self.files, self.adapter, board='localize',
                                              policy='new', prior=None, mode='scoped', proposed={})
            self.assertIsNone(plan)
            ready, plan = gate.repair_report(self.project, self.files, self.adapter, board='localize',
                                             policy='new', prior=None, mode='scoped', proposed={})
        self.assertEqual(create.call_count, 2)
        self.assertEqual(failed['status'], 'repair_required')
        self.assertEqual(ready['status'], 'plan_ready')
        self.assertIs(plan, verified)
        self.assertEqual(ready['issues'], [])
        self.assertEqual(ready['continuation']['action'], 'resume_authorized_step')

    def test_repairing_plan_cannot_bypass_wildcard_validation(self):
        groups = {'ads': [self.row('ads.normal', paths=('*',))], 'runtime': []}
        with patch.object(gate, '_observe', return_value=groups), \
             patch.object(gate, 'baseline_identity', return_value={'path': 'old.zip'}):
            report, plan = gate.repair_report(self.project, self.files, self.adapter, board='localize',
                                              policy='new', prior='old.zip', mode='scoped',
                                              proposed={'ads.normal': 'attempt to approve full wildcard'})
        self.assertIsNone(plan)
        self.assertEqual(report['status'], 'repair_required')
        self.assertTrue(any('整包' in issue['reason'] for issue in report['issues']))

    def test_lost_evidence_recollects_one_node_and_retains_the_original_record(self):
        cid = 'ads.normal'
        scope = {'basis': 'skin consumer', 'inputs': {'package': ['skin.png']}}
        self.scope_path.write_text(json.dumps({'schema': ledger.SCOPE_SCHEMA, 'checks': {cid: scope}}))
        store = ledger.Ledger(self.project)
        self.addCleanup(store.close)
        first = store.prepare(cid, self.roots, {}, 'tool', domain='platform')
        original = self.project/'original-evidence.json'
        original.write_text('{"actual_observation": true}')
        result, _ = store.execute(first, lambda: {'passed': True, 'evidence': str(original)},
                                  lambda value: value['passed'])
        frozen = Path(result['evidence'])
        frozen.unlink()
        self.assertEqual(store.prepare(cid, self.roots, {}, 'tool')['action'], 'evidence_missing')
        request = {'prior_key': first['key'], 'reason': 'Original capture and backup no longer exist',
                   'searched_locations': [str(frozen), str(self.project/'backup')]}
        self.scope_path.write_text(json.dumps({'schema': ledger.SCOPE_SCHEMA, 'checks': {cid: scope},
                                               'evidence_rechecks': {cid: request}}))
        retry = store.prepare(cid, self.roots, {}, 'tool', domain='platform')
        self.assertEqual(retry['action'], 'run')
        self.assertNotEqual(retry['key'], first['key'])
        self.assertEqual(retry['evidence_recheck'], request)
        original.write_text('{"new_actual_observation": true}')
        store.execute(retry, lambda: {'passed': True, 'evidence': str(original)}, lambda value: value['passed'])
        self.assertEqual(len(store.previous(cid)), 2)
        self.assertEqual(store.prepare(cid, self.roots, {}, 'tool')['action'], 'reuse')

    def test_bundle_digest_alone_does_not_identify_a_feature_change(self):
        path = 'assets/main/index.js'
        before = {'package': {path: 'old'}, 'adapter': {'/skin': 'same'}}
        self.assertTrue(gate._only_bundle_changed(before, {'package': {path: 'new'}, 'adapter': {'/skin': 'same'}}))
        self.assertFalse(gate._only_bundle_changed(before, {'package': {path: 'new'}, 'adapter': {'/skin': 'changed'}}))
        self.assertFalse(gate._only_bundle_changed(before, {'package': {path: 'new', 'skin.png': 'new'},
                                                           'adapter': {'/skin': 'same'}}))

    def import_runners(self):
        directory = Path(__file__).resolve().parents[2] / 'cocos-game-check/package-check/scripts'
        sys.path.insert(0, str(directory))
        self.addCleanup(sys.path.remove, str(directory))
        import ad_incremental
        import runtime_incremental
        return ad_incremental, runtime_incremental

    def fake_ad_runner(self):
        return SimpleNamespace(
            load_adapter=lambda path: {}, default_cases=lambda adapter: ['normal'], DOUBLE_CASES=(),
            tool_digest=lambda: 'ads-tool', _run_uncached=Mock(), RegressionRefused=ValueError,
            judge=lambda result, cases: (True, []),
        )

    def fake_runtime_runner(self):
        return SimpleNamespace(
            load_suites=lambda suites: {'toy': {}}, load_adapter=lambda path, catalog: {},
            package_files=lambda path: self.files, detect_engine=lambda files, adapter: '2.x',
            package_policy=lambda files, policy: ('new', 'test'), required_suites=lambda *args: ['toy'],
            load_capabilities=lambda caps: None, preflight=lambda *args, **kwargs: ({}, []),
            precheck=lambda *args: None, ordered=lambda names, catalog: names,
            BOARDS=('localize',), ENV_CAPABILITIES='TEST_NO_CAPS', RuntimeRefused=ValueError,
            _run_uncached=Mock(), not_run=lambda *args: [], _startup_measured=lambda *args: None,
            tool_digest=lambda *args: 'runtime-tool',
        )

    def test_plan_only_uses_actual_runners_without_running_any_browser(self):
        ad, runtime = self.import_runners()
        ar, rr = self.fake_ad_runner(), self.fake_runtime_runner()
        with patch.object(ledger.Ledger, 'execute_batch') as execute, patch.object(runtime, '_rule', return_value='runtime-tool'):
            ad_plans = ad.run(ar, self.native, self.adapter, plan_only=True)
            runtime_plans = runtime.run(rr, self.native, self.adapter, plan_only=True)
        execute.assert_not_called()
        ar._run_uncached.assert_not_called()
        rr._run_uncached.assert_not_called()
        self.assertEqual([(p['check_id'], p['action']) for p in ad_plans], [('ads.normal', 'run')])
        self.assertEqual([(p['check_id'], p['action']) for p in runtime_plans], [('runtime.toy/@suite', 'run')])

    def test_explicit_empty_ad_selection_never_falls_back_to_all(self):
        ad, _ = self.import_runners()
        ar = self.fake_ad_runner()
        self.plan([self.row('ads.normal')])
        self.activate_plan()
        result = ad.run(ar, self.native, self.adapter, cases=[])
        ar._run_uncached.assert_not_called()
        self.assertFalse(result['complete'])
        self.assertEqual(result['planned_not_run'], ['normal'])

    def test_explicit_empty_runtime_selection_never_falls_back_to_all(self):
        _, runtime = self.import_runners()
        rr = self.fake_runtime_runner()
        self.plan([], actions={'runtime': {}})
        self.activate_plan()
        with patch.object(runtime, '_rule', return_value='runtime-tool'):
            result = runtime.run(rr, self.native, self.adapter, suites=[])
        rr._run_uncached.assert_not_called()
        self.assertFalse(result['complete'])
        self.assertEqual(result['planned_not_run'], ['toy'])


if __name__ == '__main__':
    unittest.main()
