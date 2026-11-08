"""Delivery source identity and read-only logic records; synthetic fixtures, no game runs."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

CORE = Path(__file__).resolve().parents[3] / 'remake-core/scripts'
sys.path.insert(0, str(CORE))
import check_ledger as C
import logic_check as L
import logic_regressions as R
import test_logic_regressions as fixtures
import prepare_delivery as P


class DeliveryLogicRecords(unittest.TestCase):
    doc = fixtures.RegressionTests.doc

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='delivery-logic-records-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'Source'
        (self.root / 'assets').mkdir(parents=True)
        (self.root / 'assets/main.js').write_text('const synthetic = true;\n')
        (self.root / 'assets/unrelated.json').write_text('{"unrelated":1}')
        self.evidence = self.root / 'synthetic.txt'
        self.evidence.write_text('Synthetic observation only; no real game or browser.')
        doc = self.doc()
        checks = {'logic.' + ident: {'inputs': {'source': ['main.js']}, 'basis': 'Synthetic case only consumes main.js.'}
                  for ident, *_ in [*R.CASES, *L.FLOWS]}
        checks['fixture.external'] = {'inputs': {'source': ['unrelated.json']},
                                     'basis': 'Synthetic unrelated data belongs to an external fixture, not these logic cases.'}
        scope = self.root / 'docs/checks/check-inputs.json'
        scope.parent.mkdir(parents=True)
        scope.write_text(json.dumps({'schema': 'check-inputs.v1', 'checks': checks}))
        flows = self.root / 'docs/logic/flows.json'
        flows.parent.mkdir(parents=True)
        flows.write_text(json.dumps(doc))
        with patch.object(sys, 'argv', ['logic_check.py', '--project', str(self.root)]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(L.main(), 0)
        self.report = self.root / 'docs/logic/logic-check.json'

    def source_zip(self, name='Source.zip', *, stale=False):
        archive = Path(self.tmp.name) / name
        with zipfile.ZipFile(archive, 'w') as z:
            for path in (self.root / 'assets').rglob('*'):
                if path.is_file():
                    data = b'const stale = true;' if stale and path.name == 'main.js' else path.read_bytes()
                    z.writestr('Source/' + path.relative_to(self.root).as_posix(), data)
        return archive

    def test_old_aggregate_hash_reuses_current_cases_for_matching_source_zip(self):
        old = json.loads(self.report.read_text())['current_source_sha256']
        (self.root / 'assets/unrelated.json').write_text('{"unrelated":2}')
        self.assertNotEqual(old, R.source_digest(self.root))
        db = self.root / 'docs/checks/incremental/ledger.sqlite3'
        original = db.read_bytes()
        with patch.object(C.Ledger, 'execute', side_effect=AssertionError('delivery must not execute a node')):
            result = P.logic_source_binding(self.report, self.source_zip(), self.root)
        self.assertEqual(result['validation'], 'existing_case_records')
        self.assertEqual(result['current_source_sha256'], R.source_digest(self.root))
        self.assertEqual(result['report_source_sha256'], old)
        self.assertFalse(result['browser_executed'])
        self.assertEqual(db.read_bytes(), original)

    def test_delivered_source_must_match_actual_project(self):
        with self.assertRaisesRegex(ValueError, 'delivered source differs from the current project'):
            P.logic_source_binding(self.report, self.source_zip(stale=True), self.root)

    def test_prepare_calls_readonly_binding_for_the_actual_delivered_source(self):
        (self.root / 'assets/unrelated.json').write_text('{"unrelated":2}')
        files = {'game.js': b'boot();', 'game.json': b'{}', 'project.config.json': b'{"appid":"123"}'}
        archive = Path(self.tmp.name) / 'Game.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            for name, data in files.items():
                z.writestr(name, data)
        native = Path(self.tmp.name) / 'Native'
        native.mkdir()
        contract = Path(self.tmp.name) / 'startup.json'
        contract.write_text(json.dumps({'binding': {'web_tree_sha256': 'synthetic-web-tree'}}))
        record = Path(self.tmp.name) / 'delivery.json'
        verified = {'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                    'file_sha256': {n: hashlib.sha256(d).hexdigest() for n, d in files.items()},
                    'entry': 'official', 'runtime_execution': 'synthetic verifier boundary'}
        with patch.object(P.tempfile, 'gettempdir', return_value='/nonexistent-temp'), \
                patch.object(P, 'writer_board', return_value='localize'), \
                patch.object(P, 'check', return_value=verified), patch.object(P, 'native_files', return_value=files), \
                patch.object(P.package_obligations, 'verify', return_value={}), \
                patch.object(P.package_obligations, 'publication_guard', return_value=contextlib.nullcontext()), \
                patch.object(P, 'audit_final_startup', return_value={'startup_contract_sha256': hashlib.sha256(contract.read_bytes()).hexdigest()}), \
                patch.object(P, 'verify_preview', return_value={'synthetic': True}), \
                patch.object(C.Ledger, 'execute', side_effect=AssertionError('delivery executed a node')):
            result = P.prepare(archive, native, '123', record, project=self.root, startup_contract=contract,
                               logic_report=self.report, source=self.source_zip(), preview_url='http://127.0.0.1/synthetic')
        self.assertEqual(result['logic_source_binding']['validation'], 'existing_case_records')
        self.assertEqual(result['logic_source_binding']['current_source_sha256'], R.source_digest(self.root))
        self.assertTrue(record.is_file())

    def test_related_source_change_refuses_without_new_execution(self):
        (self.root / 'assets/main.js').write_text('const changed = true;')
        with patch.object(C.Ledger, 'execute', side_effect=AssertionError('unexpected execution')):
            with self.assertRaisesRegex(ValueError, 'per-case records cannot be reused'):
                P.logic_source_binding(self.report, self.source_zip(), self.root)

    def test_modern_missing_ledger_cannot_downgrade_to_legacy(self):
        home = self.root / 'docs/checks/incremental'
        home.rename(home.with_name('retained-ledger'))
        with self.assertRaisesRegex(ValueError, 'per-case records cannot be reused'):
            P.logic_source_binding(self.report, self.root, self.root)
        self.assertFalse(home.exists())

    def test_legacy_exact_hash_compatibility_never_creates_ledger(self):
        root = Path(self.tmp.name) / 'Legacy'
        (root / 'assets').mkdir(parents=True)
        (root / 'assets/main.js').write_text('const legacy = true;')
        report = root / 'old-report.json'
        report.write_text(json.dumps({'current_source_sha256': R.source_digest(root)}))
        result = P.logic_source_binding(report, root, root)
        self.assertEqual(result['validation'], 'legacy_exact_source')
        self.assertFalse((root / 'docs/checks/incremental').exists())
        (root / 'assets/main.js').write_text('const legacy = false;')
        with self.assertRaisesRegex(ValueError, 'differs from the delivered source'):
            P.logic_source_binding(report, root, root)
        self.assertFalse((root / 'docs/checks/incremental').exists())


if __name__ == '__main__':
    unittest.main()
