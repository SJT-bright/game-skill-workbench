"""Offline integration of real ledger, scope gate and continuation callbacks."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import check_ledger as ledger
import delivery_continuation as continuation
import regression_scope_gate as gate
import verify_native_zip as verifier


class RepairWorkflow(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.project = Path(folder.name).resolve()
        self.scope_path = self.project / 'docs/checks/check-inputs.json'
        self.scope_path.parent.mkdir(parents=True)
        self.adapter = self.project / 'adapter.json'
        self.adapter.write_text('{}')
        self.old = {'game.js': b'bootstrap', 'skin.png': b'old skin'}
        self.current = dict(self.old, **{'skin.png': b'new skin'})
        self.prior = self.project / 'previous.zip'
        with zipfile.ZipFile(self.prior, 'w') as archive:
            for name, raw in self.old.items():
                archive.writestr(name, raw)
        self.scope = {
            'ads.skin': {'basis': 'skin consumer', 'inputs': {'package': ['skin.png']}},
            'ads.other': {'basis': 'unchanged bootstrap consumer', 'inputs': {'package': ['game.js']}},
        }
        self.write_scope(self.scope)
        self.store = ledger.Ledger(self.project)
        self.addCleanup(self.store.close)
        self.raw = self.project / 'observation.json'
        self.raw.write_text('{"observed": "fixture"}')
        for cid in self.scope:
            row = self.store.prepare(cid, self.roots(self.old), {}, 'observer-v1', domain='platform')
            self.store.execute(row, lambda: {'passed': True, 'raw': str(self.raw)},
                               lambda result: result['passed'])
        self.execution_calls = []
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop(gate.ENV_PLAN, None)
        active = gate._active_plan.set(None)
        self.addCleanup(gate._active_plan.reset, active)
        observed = patch.object(gate, '_observe', side_effect=self.observe_groups)
        observed.start()
        self.addCleanup(observed.stop)

    def write_scope(self, scopes):
        self.scope_path.write_text(json.dumps({'schema': ledger.SCOPE_SCHEMA, 'checks': scopes}))

    def roots(self, files):
        return {'package': gate.package_manifest(files), 'adapter': ledger.json_manifest({})}

    def observe_groups(self, project, files, adapter, board, policy, prior_files=None):
        return {'ads': [self.store.prepare(cid, self.roots(files), {}, 'observer-v1', domain='platform')
                        for cid in self.scope], 'runtime': []}

    def test_missing_receipt_and_missing_plan_recover_one_changed_item(self):
        original_events = self.store.db.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        with gate.execution_scope():
            audit = gate.ensure_plan(self.project, self.current, self.adapter,
                                     board='localize', policy='new', prior=self.prior)
            plan_path = Path(os.environ[gate.ENV_PLAN])
            plan = json.loads(plan_path.read_bytes())
            self.assertEqual(audit['allowed'], ['ads.skin'])
            self.assertEqual(plan['baseline']['type'], 'evidence_recovery')
            self.assertFalse(plan['baseline']['old_official_pass_claimed'])
            self.assertEqual(plan['actions']['ads']['ads.other']['action'], 'reuse')
            self.assertFalse(verifier.receipt_path(self.prior).exists())
            self.assertEqual(original_events, self.store.db.execute('SELECT COUNT(*) FROM events').fetchone()[0])

    def test_wildcard_is_repaired_then_original_gate_resumes_only_the_skin(self):
        broad = {cid: {'basis': value['basis'], 'inputs': {'package': ['*']}}
                 for cid, value in self.scope.items()}
        self.write_scope(broad)
        task = continuation.continuation_task(stage='writer', original_failure={'error': 'whole package wildcard'},
                                              approved_run_ids=['ads.skin'])

        def repair(_):
            self.write_scope(self.scope)

        def resume(plan):
            with gate.execution_scope():
                gate.preflight(self.project, self.current, self.adapter, board='localize',
                               policy='new', prior=self.prior)
                rows = self.observe_groups(self.project, self.current, self.adapter, 'localize', 'new')['ads']
                gate.authorize_batch(self.project, self.roots(self.current), rows, operation='ads')
                def execute(ids):
                    self.execution_calls.append(ids)
                    return {cid: {'passed': True, 'raw': str(self.raw)} for cid in ids}
                result, detail = self.store.execute_batch(rows, execute, lambda value: value['passed'])
                self.assertTrue(detail['ads.other']['reused'])
            return {'status': 'fixture_delivery_complete', 'passed': all(value['passed'] for value in result.values())}

        report = gate.resume_scoped_step(
            task, project=self.project, read_files=lambda: dict(self.current),
            adapter=self.adapter, board='localize', policy='new', prior=self.prior,
            proposed={'ads.skin': 'skin.png actually changed'},
            repair_action='map_actual_consumer', actions={'map_actual_consumer': repair},
            observe=lambda: {'scope': self.scope_path.read_text()}, resume=resume)
        self.assertEqual(report['status'], 'resumed', report)
        self.assertEqual(self.execution_calls, [['ads.skin']])
        self.assertEqual(report['resume_calls'], 1)
        self.assertEqual(report['resume_result'], {'status': 'fixture_delivery_complete', 'passed': True})
        self.assertFalse(report['task_terminal'])

    def test_real_gate_repair_cannot_expand_original_authorized_ids(self):
        self.scope['ads.still_valid'] = {'basis': 'independent adapter observer',
                                        'inputs': {'adapter': ['*']}}
        self.write_scope(self.scope)
        row = self.store.prepare('ads.still_valid', self.roots(self.old), {}, 'observer-v1', domain='platform')
        self.store.execute(row, lambda: {'passed': True, 'raw': str(self.raw)}, lambda value: value['passed'])
        self.current['game.js'] = b'changed independent bootstrap'
        broad = {cid: {'basis': value['basis'], 'inputs': {'package': ['*']}}
                 for cid, value in self.scope.items()}
        self.write_scope(broad)
        task = continuation.continuation_task(
            stage='writer', original_failure='wildcard', approved_run_ids=['ads.skin'])
        called = []
        report = gate.resume_scoped_step(
            task, project=self.project, read_files=lambda: dict(self.current),
            adapter=self.adapter, board='localize', policy='new', prior=self.prior,
            proposed={'ads.skin': 'skin changed', 'ads.other': 'bootstrap changed'},
            repair_action='repair', actions={'repair': lambda _: self.write_scope(self.scope)},
            observe=lambda: {'scope': self.scope_path.read_text()}, resume=lambda plan: called.append(plan))
        self.assertEqual(report['status'], 'repair_required', report)
        self.assertIn('扩大原授权', report['why'])
        self.assertEqual(called, [])
        self.assertNotIn(gate.ENV_PLAN, os.environ)
        self.assertFalse(report['task_terminal'])

    def test_candidate_is_reread_before_resuming_original_step(self):
        broad = {cid: {'basis': value['basis'], 'inputs': {'package': ['*']}}
                 for cid, value in self.scope.items()}
        self.write_scope(broad)
        task = continuation.continuation_task(
            stage='writer', original_failure='wildcard', approved_run_ids=['ads.skin'])
        reads, called = [], []
        def read_files():
            reads.append(True)
            return dict(self.current, **({'skin.png': b'changed after planning'} if len(reads) == 3 else {}))
        report = gate.resume_scoped_step(
            task, project=self.project, read_files=read_files, adapter=self.adapter,
            board='localize', policy='new', prior=self.prior,
            proposed={'ads.skin': 'skin actually changed'}, repair_action='repair',
            actions={'repair': lambda _: self.write_scope(self.scope)},
            observe=lambda: {'scope': self.scope_path.read_text()}, resume=lambda plan: called.append(plan))
        self.assertEqual(report['status'], 'repair_required', report)
        self.assertIn('实际 Native', report['why'])
        self.assertEqual(called, [])


class ReceiptRecovery(unittest.TestCase):
    def test_precise_scope_plan_is_checked_before_the_legacy_receipt_path(self):
        scripts = Path(__file__).resolve().parents[2] / 'cocos-game-check/package-check/scripts'
        sys.path.insert(0, str(scripts))
        self.addCleanup(sys.path.remove, str(scripts))
        import check_package
        import rework_scope
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ):
            root = Path(folder)
            adapter = root / 'adapter.json'
            adapter.write_text('{}')
            os.environ[gate.ENV_PLAN] = str(root / 'precise.plan.json')
            os.environ['ENGLISH_CHECK_PROJECT'] = str(root)
            with patch.object(gate, 'preflight', return_value={'mode': 'scoped'}) as preflight, \
                 patch.object(rework_scope, 'plan', side_effect=AssertionError('legacy receipt route must not run')):
                self.assertIsNone(check_package.rework_plan(root / 'previous.zip', {'game.js': b'fixture'},
                                                            str(adapter), 'new', 'localize'))
            preflight.assert_called_once()

    def test_invalid_same_name_does_not_hide_a_valid_same_byte_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / 'renamed.zip'
            archive.write_bytes(b'fixture ZIP identity')
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            manifest = {'game.js': hashlib.sha256(b'fixture').hexdigest()}
            def receipt(tree, passed=True):
                return {'tool': 'build_checked_zip', 'zip_sha256': digest, 'native_tree_sha256': tree,
                        'gate_result': {'passed': passed, 'blocks': []},
                        'finalize': {'kind': 'finalize-native', 'policy': 'new',
                                     'kit_version': 'fixture', 'files_after': {}}}
            preferred = verifier.receipt_path(archive)
            preferred.write_text(json.dumps(receipt('wrong tree')))
            invalid = root / 'a-invalid.zip.receipt.json'
            invalid.write_text(json.dumps(receipt(verifier.tree_digest(manifest), False)))
            valid = root / 'b-original.zip.receipt.json'
            valid.write_text(json.dumps(receipt(verifier.tree_digest(manifest))))
            before = {path: path.read_bytes() for path in (preferred, invalid, valid)}
            status = verifier.receipt_status(archive, digest, manifest)
            self.assertEqual(status['entry'], 'official', status)
            self.assertEqual(status['receipt'], str(valid))
            self.assertEqual(before, {path: path.read_bytes() for path in before})


if __name__ == '__main__':
    unittest.main()
