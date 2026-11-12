"""Offline real-ledger fixtures for missing-receipt baseline recovery."""
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import check_ledger as ledger
import regression_baseline as baseline
from verify_native_zip import make_receipt, receipt_path


class BaselineRecoveryTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix='regression-baseline-fixture-')
        self.addCleanup(folder.cleanup)
        self.project = Path(folder.name).resolve()
        self.old = {'game.js': b'offline fixture only', 'one.png': b'old one', 'two.png': b'old two'}
        self.current = dict(self.old, **{'one.png': b'changed one'})
        self.archive = self.project / 'old.zip'
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for name, data in self.old.items():
                archive.writestr(name, data)
        self.scope_path = self.project / 'docs/checks/check-inputs.json'
        self.scope_path.parent.mkdir(parents=True)
        self.config = {'schema': ledger.SCOPE_SCHEMA, 'checks': {
            'ads.one': {'basis': 'independent first fixture image consumer',
                        'inputs': {'package': ['one.png']}},
            'ads.two': {'basis': 'independent second fixture image consumer',
                        'inputs': {'package': ['two.png']}}}}
        self.write_scope()
        self.store = ledger.Ledger(self.project)
        self.addCleanup(self.store.close)
        self.old_roots = {'package': baseline.package_manifest(self.old)}
        self.current_roots = {'package': baseline.package_manifest(self.current)}

    def write_scope(self):
        self.scope_path.write_text(json.dumps(self.config))

    def record(self, cid, roots=None, *, passed=True):
        roots = self.old_roots if roots is None else roots
        row = self.store.prepare(cid, roots, {'fixture': True}, 'fixture-rule', domain='platform')
        self.assertEqual(row['action'], 'run')
        raw = self.project / (cid + '-observation.json')
        raw.write_text(json.dumps({'actual_observation': cid, 'passed': passed}))
        with redirect_stderr(io.StringIO()):
            self.store.execute(row, lambda: {'passed': passed, 'raw_files': [str(raw)]},
                               lambda result: result['passed'])
        return self.store.previous(cid)[0]

    def groups(self):
        return {'ads': [self.store.prepare(cid, self.current_roots, {'fixture': True}, 'fixture-rule',
                                           domain='platform') for cid in self.config['checks']], 'runtime': []}

    def seed(self):
        self.record('ads.one')
        self.record('ads.two')

    def identity(self, groups=None):
        return baseline.identity(self.archive, self.current, self.project,
                                 self.groups() if groups is None else groups)

    def test_missing_receipt_recovers_one_pending_and_another_real_reuse(self):
        self.seed()
        groups = self.groups()
        self.assertEqual([row['action'] for row in groups['ads']], ['run', 'reuse'])
        before_events = self.store.db.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        recovered = self.identity(groups)
        self.assertEqual(recovered['type'], 'evidence_recovery')
        self.assertFalse(recovered['old_official_pass_claimed'])
        self.assertEqual(recovered['receipt_status']['status'], 'missing')
        self.assertEqual(recovered['archive_manifest'], self.old_roots['package'])
        self.assertEqual(recovered['sources']['ads.one']['kind'], 'archive_observation')
        self.assertEqual(recovered['sources']['ads.two']['kind'], 'archive_observation')
        source = recovered['sources']['ads.one']
        original = self.store.previous('ads.one')[0]
        self.assertEqual(source['key'], ledger.sha(original['binding']))
        self.assertEqual(source['executed_at'], original['executed_at'])
        self.assertTrue(source['files'])
        self.assertFalse(receipt_path(self.archive).exists())
        self.assertEqual(before_events, self.store.db.execute('SELECT COUNT(*) FROM events').fetchone()[0])

    def test_mismatched_receipt_is_preserved_and_binds_recovery(self):
        self.seed()
        receipt = receipt_path(self.archive)
        original = b'{"tool":"make_tiktok_zip","zip_sha256":"other zip bytes"}'
        receipt.write_bytes(original)
        recovered = self.identity()
        self.assertEqual(recovered['receipt_status']['status'], 'mismatched')
        self.assertEqual(recovered['receipt_status']['sha256'], ledger.sha(original))
        self.assertEqual(receipt.read_bytes(), original)

    def test_normal_pending_completion_keeps_recovery_identity_stable(self):
        self.seed()
        before = self.identity()
        self.record('ads.one', self.current_roots)
        after = self.identity()
        self.assertEqual(before, after)

    def test_modified_original_raw_evidence_refuses_recovery(self):
        self.seed()
        original = self.store.previous('ads.one')[0]
        Path(original['files'][0]['path']).write_text('{"changed": true}')
        with self.assertRaisesRegex(ledger.NeedsScope, '原始证据缺失或字节变化'):
            self.identity()

    def test_all_pending_without_original_evidence_cannot_be_registered_as_new(self):
        self.config['baseline_recovery'] = {'new_checks': {
            cid: {'reason': 'new fixture unit', 'basis': 'fixture consumer'} for cid in self.config['checks']}}
        self.write_scope()
        with self.assertRaisesRegex(ledger.NeedsScope, '没有任何真实可沿用项'):
            self.identity()
        self.assertFalse(receipt_path(self.archive).exists())

    def test_current_observation_can_preserve_reuse_without_claiming_old_zip_passed(self):
        self.record('ads.two', self.current_roots)
        self.record('ads.one')
        result = self.identity()
        source = result['sources']['ads.two']
        self.assertEqual(source['kind'], 'current_observation')
        self.assertFalse(source['old_pass_claimed'])
        self.assertFalse(result['old_official_pass_claimed'])

    def test_missing_pending_source_is_a_precise_gap_not_permission_for_full_run(self):
        self.record('ads.two')
        with self.assertRaisesRegex(ledger.NeedsScope, 'ads.one.*待跑项缺少'):
            self.identity()

    def test_explicit_new_item_remains_stable_after_completion(self):
        self.record('ads.two')
        self.config['baseline_recovery'] = {'new_checks': {
            'ads.one': {'reason': 'new first fixture consumer', 'basis': 'first fixture reference'}}}
        self.write_scope()
        before = self.identity()
        self.assertEqual(before['sources']['ads.one']['kind'], 'new_check')
        self.record('ads.one', self.current_roots)
        self.assertEqual(before, self.identity())

    def test_failed_archive_source_cannot_be_relabelled_new(self):
        self.record('ads.one', passed=False)
        self.record('ads.two')
        self.config['baseline_recovery'] = {'new_checks': {
            'ads.one': {'reason': 'claim a new item', 'basis': 'same old check id'}}}
        self.write_scope()
        with self.assertRaisesRegex(ledger.NeedsScope, '原 ZIP 最新真实观察失败'):
            self.identity()

    def test_actual_failed_receipt_does_not_become_recoverable_missing_metadata(self):
        self.seed()
        receipt_path(self.archive).write_text(json.dumps({
            'tool': 'make_tiktok_zip', 'zip_sha256': baseline.digest(self.archive),
            'gate_result': {'passed': False, 'blocks': ['actual-block']}}))
        with self.assertRaisesRegex(ledger.NeedsScope, '真实失败'):
            self.identity()

    def test_official_identity_preserves_the_original_api(self):
        receipt = make_receipt('make_tiktok_zip', self.archive, baseline.digest(self.archive),
                               self.old_roots['package'], {'blocks': []}, 'localize',
                               finalize={'kind': 'finalize-native', 'policy': 'new', 'blocks': [],
                                         'files_after': self.old_roots['package']})
        receipt_file = receipt_path(self.archive)
        receipt_file.write_text(json.dumps(receipt))
        result = baseline.identity(self.archive, self.current)
        self.assertEqual(result, {'path': str(self.archive), 'sha256': baseline.digest(self.archive),
                                  'receipt': str(receipt_file), 'receipt_sha256': baseline.digest(receipt_file)})

    def test_exact_original_evidence_recheck_is_bounded_and_retains_provenance(self):
        self.current = dict(self.old)
        self.current_roots = self.old_roots
        self.seed()
        original = self.store.previous('ads.one')[0]
        raw = Path(original['files'][0]['path'])
        raw.unlink()
        self.config['evidence_rechecks'] = {'ads.one': {
            'prior_key': ledger.sha(original['binding']), 'reason': 'fixture file and backup are gone',
            'searched_locations': [str(raw), str(self.project / 'fixture-backup')]}}
        self.write_scope()
        result = self.identity()
        source = result['sources']['ads.one']
        self.assertEqual(source['key'], ledger.sha(original['binding']))
        self.assertFalse(source['files'][0]['observed_sha256'])
        self.assertEqual(source['evidence_recheck'], self.config['evidence_rechecks']['ads.one'])
        self.record('ads.one', self.current_roots)
        self.assertEqual(result, self.identity())


if __name__ == '__main__':
    unittest.main()
