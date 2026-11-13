"""Real SQLite/evidence tests with a small synthetic catalogue; no game acceptance."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json
import tempfile
import unittest

import check_known_issues as gate
import check_ledger as ledger
import known_issue_checkpoints as checkpoints


class CheckpointReuse(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='known-checkpoint-control-')
        self.root = Path(self.temp.name)
        self.project = self.root / 'Source'
        self.native = self.root / 'Native'
        self.web = self.root / 'Web'
        for directory in (self.project / 'assets', self.native, self.web):
            directory.mkdir(parents=True)
        for name in ('font', 'flow', 'routes'):
            (self.project / ('assets/' + name + '.js')).write_text('// synthetic ' + name)
        (self.project / 'assets/icon.png').write_bytes(b'synthetic image bytes, not an image')
        (self.native / 'game.js').write_text('// synthetic Native, no game execution')
        (self.web / 'index.html').write_text('<p>synthetic metadata only</p>')
        self.catalog = self.root / 'catalog.json'
        self.catalog.write_text(json.dumps({'revision': 'synthetic-checkpoint-v1', 'reward_states': [],
            'reward_policy_kinds': ['repeatable'], 'items': [
                {'id': 'UI-04', 'title': 'Synthetic text resource', 'phase': 'pre_scan'},
                {'id': 'FLOW-01', 'title': 'Synthetic flow observation', 'phase': 'pre_scan'}]}))
        self.catalog_patch = patch.object(gate, 'CATALOG', self.catalog)
        self.catalog_patch.start()
        self.args = SimpleNamespace(project=self.project, native=self.native, web=self.web,
            build_tag='synthetic-1', review=self.root / 'review.json', markdown=None,
            inventory=None, board='localize', art_style='original', stage='pre_scan', executor_exit=False)
        gate.init(self.args)
        self.review = gate.load(self.args.review)
        self.review['inventory_complete'] = True
        self.review['inventory_evidence'] = [self.ref('inventory')]
        for cid in ('UI-04', 'FLOW-01'):
            self.review['checks'][cid] = {'status': 'pass', 'layer': 'source',
                'observed': 'Synthetic schema observation for ' + cid + ', no real game',
                'evidence': [self.ref(cid)]}
        scope = {'schema': ledger.SCOPE_SCHEMA, 'checks': {}}
        for cid, filename in [('known.UI-04', 'font.js'), ('known.FLOW-01', 'flow.js'),
                              ('known.inventory', 'routes.js'), ('art.synthetic', 'icon.png')]:
            scope['checks'][cid] = {'inputs': {'source': ['assets/' + filename]},
                                   'basis': 'Synthetic independent source owner: ' + filename}
        self.save(self.project / 'docs/checks/check-inputs.json', scope)
        self.flush()

    def tearDown(self):
        self.catalog_patch.stop()
        self.temp.cleanup()

    def save(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2))

    def flush(self):
        self.save(self.args.review, self.review)

    def ref(self, name):
        path = self.root / (name + '.txt')
        path.write_text('Synthetic original evidence only: ' + name)
        return {'path': str(path), 'sha256': gate.sha(path.read_bytes()),
                'role': 'current_artifact', 'binding': gate.binding(self.args)}

    def test_unchanged_rows_are_not_revalidated_and_keep_original_times(self):
        original = gate.check_row
        with patch.object(gate, 'check_row', wraps=original) as observe:
            first = gate.audit(self.args)
            self.assertEqual(first['status'], 'passed', first)
            self.assertEqual(observe.call_count, 2)
            second = gate.audit(self.args)
            self.assertEqual(second['status'], 'passed', second)
            self.assertEqual(observe.call_count, 2)
            self.assertTrue(all(r['action'] == 'reused' and r['recorded_at'] for r in second['checks']))
            self.assertTrue(all(r['original_at'] is None for r in second['checks']))

    def test_unrelated_image_change_reuses_text_flow_and_inventory(self):
        self.assertEqual(gate.audit(self.args)['status'], 'passed')
        (self.project / 'assets/icon.png').write_bytes(b'changed synthetic image only')
        old = gate._audit_uncached(self.args)
        self.assertEqual(old['status'], 'blocked')
        self.assertTrue(any('Source/Native/Web/build tag' in e for e in old['errors']))
        with patch.object(gate, 'check_row', side_effect=AssertionError('old observation rerun')):
            current = gate.audit(self.args)
        self.assertEqual(current['status'], 'passed', current)
        self.assertTrue(all(r['action'] == 'reused' for r in current['checks']))

    def test_changed_text_needs_its_own_new_proof_only(self):
        self.assertEqual(gate.audit(self.args)['status'], 'passed')
        (self.project / 'assets/font.js').write_text('// changed synthetic font consumer')
        failed = gate.audit(self.args)
        self.assertEqual(failed['status'], 'blocked')
        self.assertTrue(any(e.startswith('UI-04:') for e in failed['errors']), failed)
        self.assertFalse(any(e.startswith('FLOW-01:') for e in failed['errors']), failed)
        self.review['binding'] = gate.binding(self.args)
        self.review['checks']['UI-04']['evidence'] = [self.ref('UI-04-repaired')]
        self.review['checks']['UI-04']['observed'] += ' new actual synthetic input'
        self.flush()
        with patch.object(gate, 'check_row', wraps=gate.check_row) as observe:
            repaired = gate.audit(self.args)
        self.assertEqual(repaired['status'], 'passed', repaired)
        self.assertEqual(observe.call_count, 1)
        after = gate.audit(self.args)
        self.assertEqual(after['status'], 'passed', after)
        self.assertTrue(all(r['action'] == 'reused' for r in after['checks']))

    def test_executor_and_build_tag_do_not_create_observations(self):
        self.assertEqual(gate.audit(self.args)['status'], 'passed')
        self.review['test_executor'] = 'claude'
        self.flush()
        self.args.build_tag = 'synthetic-2'
        with patch.object(gate, 'check_row', side_effect=AssertionError('executor replay')):
            result = gate.audit(self.args)
        self.assertEqual(result['status'], 'passed', result)
        self.assertTrue(all(r['action'] == 'reused' for r in result['checks']))

    def test_changed_referenced_evidence_is_not_a_cached_pass(self):
        self.assertEqual(gate.audit(self.args)['status'], 'passed')
        (self.root / 'UI-04.txt').write_text('different bytes')
        result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked')
        self.assertTrue(any('known.UI-04: Referenced evidence bytes changed' in e for e in result['errors']))

    def test_lost_frozen_evidence_does_not_rerun_a_whole_review(self):
        self.assertEqual(gate.audit(self.args)['status'], 'passed')
        store = ledger.Ledger(self.project)
        try:
            record = store.previous('known.UI-04')[0]
            Path(record['files'][0]['path']).unlink()
        finally:
            store.close()
        with patch.object(gate, '_audit_uncached', side_effect=AssertionError('automatic review fallback')):
            result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['repair_scope'], ['known.UI-04'])
        self.assertFalse(result['replay_authorized'])

    def test_unknown_new_source_requires_dependency_ownership(self):
        self.assertEqual(gate.audit(self.args)['status'], 'passed')
        (self.project / 'assets/unknown.js').write_text('// new unknown consumer')
        with patch.object(gate, '_audit_uncached', side_effect=AssertionError('global fallback')):
            result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked')
        self.assertFalse(result['replay_authorized'])

    def test_forged_global_binding_does_not_relabel_old_observations(self):
        self.assertEqual(gate.audit(self.args)['status'], 'passed')
        self.review['binding']['source_sha256'] = 'f' * 64
        self.flush()
        result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked')
        self.assertTrue(any('Source/Native/Web/build tag' in e for e in result['errors']))

    def test_no_review_is_reported_as_unmapped_not_complete(self):
        out = checkpoints.consume_for_writer(self.project, self.native, self.web)
        self.assertEqual(out['status'], 'not_recorded')
        self.assertFalse(out['passed'])
        with self.assertRaisesRegex(ValueError, 'explicitly supplied review is missing'):
            checkpoints.consume_for_writer(self.project, self.native, self.web,
                                           review=self.root / 'not-here.json')

    def test_manifest_reads_are_bounded_per_batch_not_per_row(self):
        with patch.object(checkpoints, 'source_roots', wraps=checkpoints.source_roots) as snapshots:
            result = gate.audit(self.args)
        self.assertEqual(result['status'], 'passed', result)
        self.assertEqual(snapshots.call_count, 3)

    def test_input_changes_during_freeze_invalidate_only_new_checkpoints(self):
        freeze = ledger.Ledger._freeze
        moved = []
        def change(store, value, folder, files):
            result = freeze(store, value, folder, files)
            if not moved:
                moved.append(True)
                (self.native / 'game.js').write_text('// changed during checkpoint commit')
            return result
        with patch.object(ledger.Ledger, '_freeze', change):
            result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked', result)
        store = ledger.Ledger(self.project)
        try:
            self.assertFalse(any(r['passed'] for cid in ('known.UI-04', 'known.FLOW-01', 'known.inventory')
                                 for r in store.previous(cid)))
        finally:
            store.close()

    def test_consumer_does_not_invoke_registered_project_hooks(self):
        with patch('project_qa.review_policy', return_value={'audit': 'synthetic-executable-hook'}), \
             patch('project_qa.invoke', side_effect=AssertionError('consumer executed project producer')):
            result = checkpoints.consume_for_writer(self.project, self.native, self.web,
                                                     review=self.args.review)
        self.assertEqual(result['status'], 'project_supplement')
        self.assertFalse(result['passed'])

    def test_load_report_consumer_explicitly_forbids_browser_replay(self):
        import audit_startup_contract
        binding = gate.binding(self.args)
        report = self.root / 'startup.json'
        self.save(report, {'tool': 'audit_startup_contract', 'passed': True, 'failed': 0,
                           'checked': 1, 'binding': binding})
        row = {'auto_reports': [{'path': str(report), 'sha256': gate.sha(report.read_bytes())}]}
        seen = []
        def validate(data, bound, **kwargs):
            replay = kwargs.get('replay_runner')
            self.assertIsNotNone(replay)
            replay({}, self.native, bound, self.project)
            return []
        def observe(*args, **kwargs):
            seen.append(kwargs)
            return {'action': 'reused'}
        with patch.object(audit_startup_contract, 'validate_runtime_report', validate), \
             patch('regression_scope_gate.startup_replay', observe), \
             patch('native_startup_ledger.replay', side_effect=AssertionError('default replay invoked')):
            errors = []
            gate.auto_reports({'id': 'LOAD-01', 'auto_check': ['audit_startup_contract']},
                              row, self.root, errors, binding, project=self.project)
        self.assertEqual(errors, [])
        self.assertEqual(len(seen), 1)
        self.assertTrue(seen[0]['reuse_only'])
        self.assertEqual(seen[0]['plan_project'], self.project.resolve())

    def test_missing_original_inventory_is_read_from_valid_frozen_evidence(self):
        self.assertEqual(gate.audit(self.args)['status'], 'passed')
        (self.root / 'inventory.txt').unlink()
        (self.root / self.review['inventory_snapshot']['path']).unlink()
        with patch.object(gate, 'check_row', side_effect=AssertionError('missing original caused replay')):
            result = gate.audit(self.args)
        self.assertEqual(result['status'], 'passed', result)
        self.assertTrue(all(r['action'] == 'reused' for r in result['checks']))

    def test_legacy_spot_flows_do_not_force_three_new_runs_after_art_change(self):
        self.review['gpt_spot_check']['flows'] = [{
            'check_id': 'FLOW-01', 'observed': 'Historical synthetic flow, not a new game run',
            'evidence': deepcopy(self.review['checks']['FLOW-01']['evidence'])}]
        self.flush()
        self.assertEqual(gate.audit(self.args)['status'], 'passed')
        (self.project / 'assets/icon.png').write_bytes(b'art changed after old spot review')
        with patch.object(gate, 'check_row', side_effect=AssertionError('legacy spot replay')):
            result = gate.audit(self.args)
        self.assertEqual(result['status'], 'passed', result)
        self.review['gpt_spot_check']['flows'][0]['passed'] = False
        self.flush()
        self.assertEqual(gate.audit(self.args)['status'], 'blocked')

    def test_same_failed_input_does_not_repeat_validation_before_repair(self):
        self.assertEqual(gate.audit(self.args)['status'], 'passed')
        (self.project / 'assets/font.js').write_text('// changed input lacks new proof')
        first = gate.audit(self.args)
        self.assertEqual(first['status'], 'blocked')
        with patch.object(gate, '_audit_uncached', side_effect=AssertionError('same failure repeated')):
            second = gate.audit(self.args)
        self.assertEqual(second['status'], 'blocked')
        self.assertEqual(second['repair_scope'], ['known.UI-04'])
        self.assertTrue(any('该输入已失败' in e for e in second['errors']))

    def records(self, cid):
        store = ledger.Ledger(self.project)
        try:
            return store.previous(cid)
        finally:
            store.close()

    def test_first_partial_failure_commits_other_passes_and_repairs_only_failed_node(self):
        self.review['checks']['UI-04']['status'] = 'fail'
        self.flush()
        with patch.object(gate, 'check_row', wraps=gate.check_row) as observe:
            first = gate.audit(self.args)
        self.assertEqual(first['status'], 'blocked', first)
        self.assertEqual([call.args[3] for call in observe.call_args_list], ['UI-04', 'FLOW-01'])
        self.assertEqual(first['global_validation_errors'], [])
        self.assertEqual(first['per_node_validation']['known.FLOW-01']['status'], 'passed')
        self.assertFalse(self.records('known.UI-04')[0]['passed'])
        saved = self.records('known.FLOW-01')[0]
        self.assertTrue(saved['passed'])
        self.assertTrue(self.records('known.inventory')[0]['passed'])
        with patch.object(gate, '_audit_uncached', side_effect=AssertionError('same failed row replayed')):
            unchanged = gate.audit(self.args)
        self.assertEqual(unchanged['repair_scope'], ['known.UI-04'])
        self.review['checks']['UI-04']['status'] = 'pass'
        self.review['checks']['UI-04']['observed'] += ' repaired synthetic metadata'
        self.flush()
        with patch.object(gate, 'check_row', wraps=gate.check_row) as observe:
            repaired = gate.audit(self.args)
        self.assertEqual(repaired['status'], 'passed', repaired)
        self.assertEqual([call.args[3] for call in observe.call_args_list], ['UI-04'])
        self.assertEqual(self.records('known.FLOW-01')[0]['executed_at'], saved['executed_at'])
        self.assertEqual(self.records('known.FLOW-01')[0]['binding'], saved['binding'])
        actions = {row['id']: row['action'] for row in repaired['checks']}
        self.assertEqual(actions['known.FLOW-01'], 'reused')
        self.assertEqual(actions['known.inventory'], 'reused')

    def test_opaque_node_failure_uses_explicit_owner_not_error_prefix(self):
        original = gate.check_row
        def validate(row, base, errors, label, binding):
            original(row, base, errors, label, binding)
            if label == 'UI-04':
                errors.append('opaque reason without any check ID')
        with patch.object(gate, 'check_row', validate):
            result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked', result)
        self.assertEqual(result['per_node_validation']['known.UI-04']['errors'],
                         ['opaque reason without any check ID'])
        self.assertFalse(self.records('known.UI-04')[0]['passed'])
        self.assertTrue(self.records('known.FLOW-01')[0]['passed'])

    def test_global_error_with_node_like_prefix_cannot_commit_any_pass(self):
        with patch.object(gate, 'spot_check', return_value=['UI-04: global unresolved discrepancy']):
            result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked', result)
        self.assertEqual(result['per_node_validation']['known.UI-04']['status'], 'passed')
        self.assertEqual(result['global_validation_errors'], ['UI-04: global unresolved discrepancy'])
        for cid in ('known.UI-04', 'known.FLOW-01', 'known.inventory'):
            self.assertEqual(self.records(cid), [])
        self.assertTrue(all(row['action'] == 'not_committed' for row in result['checks']))

    def test_unattributed_validator_error_is_not_a_local_pass(self):
        original = gate._audit_uncached
        def validate(args):
            result = original(args)
            result['errors'] = list(result['errors']) + ['unattributed error from an unknown validator']
            result['status'] = 'blocked'
            return result
        with patch.object(gate, '_audit_uncached', validate):
            result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked', result)
        for cid in ('known.UI-04', 'known.FLOW-01', 'known.inventory'):
            self.assertEqual(self.records(cid), [])

    def test_global_binding_failure_blocks_partial_commits(self):
        self.review['checks']['UI-04']['status'] = 'fail'
        self.review['binding']['source_sha256'] = 'f' * 64
        self.flush()
        result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked', result)
        self.assertTrue(result['global_validation_errors'])
        self.assertEqual(result['per_node_validation']['known.FLOW-01']['status'], 'passed')
        for cid in ('known.UI-04', 'known.FLOW-01', 'known.inventory'):
            self.assertEqual(self.records(cid), [])

    def test_unrecognized_node_ownership_cannot_authorize_other_commits(self):
        original = gate._audit_uncached
        def validate(args):
            result = original(args)
            error = 'error assigned to a node with no current definition'
            result['errors'] = list(result['errors']) + [error]
            result['status'] = 'blocked'
            result['per_node_validation']['known.unknown'] = {'status': 'failed', 'errors': [error]}
            return result
        with patch.object(gate, '_audit_uncached', validate):
            result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked', result)
        for cid in ('known.UI-04', 'known.FLOW-01', 'known.inventory'):
            self.assertEqual(self.records(cid), [])

    def test_catalog_and_row_structure_failures_do_not_commit_passes(self):
        original = deepcopy(self.review)
        for broken in ('catalog', 'unknown_row'):
            with self.subTest(broken=broken):
                self.review = deepcopy(original)
                if broken == 'catalog':
                    self.review['catalog_sha256'] = 'f' * 64
                else:
                    self.review['checks']['UNKNOWN-01'] = deepcopy(self.review['checks']['UI-04'])
                self.flush()
                result = gate.audit(self.args)
                self.assertEqual(result['status'], 'blocked', result)
                self.assertTrue(result['global_validation_errors'])
                for cid in ('known.UI-04', 'known.FLOW-01', 'known.inventory'):
                    self.assertEqual(self.records(cid), [])

    def test_cross_row_copied_observation_blocks_all_new_commits(self):
        self.review['checks']['UI-04']['observed'] = self.review['checks']['FLOW-01']['observed']
        self.flush()
        result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked', result)
        self.assertTrue(any('Same observed text copied' in error for error in result['global_validation_errors']))
        for cid in ('known.UI-04', 'known.FLOW-01', 'known.inventory'):
            self.assertEqual(self.records(cid), [])

    def test_inventory_snapshot_identity_is_a_global_commit_boundary(self):
        snapshot = self.root / self.review['inventory_snapshot']['path']
        record = gate.load(snapshot)
        record['binding']['native_tree_sha256'] = 'f' * 64
        self.save(snapshot, record)
        self.review['inventory_snapshot']['sha256'] = gate.sha(snapshot.read_bytes())
        self.flush()
        result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked', result)
        self.assertTrue(any('Inventory snapshot belongs to another build' in error
                            for error in result['global_validation_errors']))
        for cid in ('known.UI-04', 'known.FLOW-01', 'known.inventory'):
            self.assertEqual(self.records(cid), [])

    def test_partial_commit_source_movement_invalidates_new_passes(self):
        self.review['checks']['UI-04']['status'] = 'fail'
        self.flush()
        freeze = ledger.Ledger._freeze
        moved = []
        def change(store, value, folder, files):
            result = freeze(store, value, folder, files)
            if not moved:
                moved.append(True)
                (self.native / 'game.js').write_text('// source moved during partial checkpoint commit')
            return result
        with patch.object(ledger.Ledger, '_freeze', change):
            result = gate.audit(self.args)
        self.assertEqual(result['status'], 'blocked', result)
        self.assertFalse(any(row['passed'] for cid in ('known.UI-04', 'known.FLOW-01', 'known.inventory')
                             for row in self.records(cid)))


if __name__ == '__main__':
    unittest.main()
