"""Per-case behavior tests. Synthetic observations never represent a game pass."""
import copy
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import check_ledger as C
import logic_check as L
import logic_regressions as R
from logic_case_ledger import CaseRecords
import test_logic_regressions as fixtures


class IncrementalCases(unittest.TestCase):
    # Reuse fixture builders only; do not inherit or rediscover the 33 original tests.
    doc = fixtures.RegressionTests.doc
    errors = fixtures.RegressionTests.errors
    run_cli = fixtures.RegressionTests.run_cli
    write_doc = fixtures.RegressionTests.write_doc

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='logic-case-ledger-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'assets').mkdir()
        (self.root / 'assets/main.js').write_text('const synthetic = true;\n')
        (self.root / 'assets/audio.js').write_text('const audioGain = 1;\n')
        self.evidence = self.root / 'synthetic.txt'
        self.evidence.write_text('Synthetic validator fixture; no browser or real game was run.\n')
        self.document = self.doc()
        for row in self.document['regressions']:
            row['observed_at'] = '2026-11-07T12:00:00Z'
        checks = {}
        for ident, *_ in [*R.CASES, *L.FLOWS]:
            checks['logic.' + ident] = {
                'inputs': {'source': ['audio.js'] if ident == 'R09' else ['main.js']},
                'basis': 'Independent exact-path fixture; only R09 consumes the synthetic audio setting.',
            }
        self.scope = self.root / 'docs/checks/check-inputs.json'
        self.scope.parent.mkdir(parents=True)
        self.scope.write_text(json.dumps({'schema': 'check-inputs.v1', 'checks': checks}))

    def rows(self):
        path = self.root / 'docs/checks/incremental/ledger.sqlite3'
        if not path.exists():
            return []
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
            return [json.loads(row[0]) for row in db.execute('SELECT data FROM records ORDER BY rowid')]

    def validate(self):
        return R.validate(self.document, self.root, R.source_digest(self.root))

    def change_audio(self):
        (self.root / 'assets/audio.js').write_text('const audioGain = .5;\n')

    def bind_current(self):
        self.document['regression_binding'] = {'source_sha256': R.source_digest(self.root)}

    def report(self):
        self.write_doc(self.document)
        result = self.run_cli('--mode', 'build')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((self.root / 'docs/logic/logic-check.json').read_text())

    def test_audio_edit_only_invalidates_audio_observation(self):
        rows, errors = self.validate()
        self.assertEqual(errors, [])
        original = self.rows()
        rows, errors = self.validate()
        self.assertEqual(errors, [])
        self.assertEqual({r['incremental']['action'] for r in rows}, {'reuse'})
        self.assertEqual(self.rows(), original)
        self.change_audio()
        self.assertEqual([r['id'] for r in self.errors(self.document)], ['R09'])
        self.bind_current()
        self.assertEqual([r['id'] for r in self.errors(self.document)], ['R09'])
        rec = next(r for r in self.document['regressions'] if r['id'] == 'R09')
        ev = self.root / 'audio-new.txt'
        ev.write_text('New synthetic audio observations; validator fixture only.')
        rec['evidence'] = [{'path': ev.name, 'sha256': hashlib.sha256(ev.read_bytes()).hexdigest()}]
        rec['observed_at'] = '2026-11-08T12:00:00Z'
        rows, errors = self.validate()
        self.assertEqual(errors, [])
        self.assertEqual({r['id'] for r in rows if r['incremental']['action'] != 'reuse'}, {'R09'})
        self.assertEqual(self.rows()[:9], original)

    def test_unowned_source_needs_mapping_not_full_run(self):
        self.assertEqual(self.errors(self.document), [])
        (self.root / 'assets/new.js').write_text('new module')
        errors = self.errors(self.document)
        self.assertEqual({r['id'] for r in errors}, {r[0] for r in R.CASES})
        self.assertTrue(all('source:new.js' in r['problem'] for r in errors))

    def test_copying_or_removing_old_refs_is_not_new_raw_evidence(self):
        rec = self.document['regressions'][-1]
        second = self.root / 'old-second.txt'
        second.write_text('A second original synthetic observation, before any input changed.')
        rec['evidence'].append({'path': second.name, 'sha256': hashlib.sha256(second.read_bytes()).hexdigest()})
        original_refs = copy.deepcopy(rec['evidence'])
        self.assertEqual(self.errors(self.document), [])
        original_rows = self.rows()
        self.change_audio()
        self.bind_current()
        for changed_refs in (original_refs + [original_refs[0]], original_refs[:1]):
            with self.subTest(refs=changed_refs):
                rec['evidence'] = copy.deepcopy(changed_refs)
                errors = self.errors(self.document)
                self.assertEqual([r['id'] for r in errors], ['R09'])
                self.assertIn('没有新的原始观察证据', errors[0]['problem'])
                self.assertEqual(self.rows(), original_rows)

    def test_current_report_uses_project_and_never_writes_or_executes(self):
        report = self.report()
        db = self.root / 'docs/checks/incremental/ledger.sqlite3'
        original_bytes = db.read_bytes()
        with patch.object(C.Ledger, 'execute', side_effect=AssertionError('read-only gate executed a node')):
            self.assertTrue(R.current_report(report, self.root))
            self.assertFalse(R.current_report(report, self.root / 'docs/logic'))
            self.change_audio()
            self.assertFalse(R.current_report(report, self.root))
        self.assertEqual(db.read_bytes(), original_bytes)
        self.assertFalse((self.root / 'docs/logic/docs/checks/incremental').exists())

    def test_older_historical_capture_cannot_certify_a_third_source(self):
        rec = self.document['regressions'][-1]
        first_refs = copy.deepcopy(rec['evidence'])
        self.assertEqual(self.errors(self.document), [])
        self.change_audio()
        self.bind_current()
        fresh = self.root / 'second-audio.txt'
        fresh.write_text('Second synthetic raw observation, bound to the second source.')
        rec['evidence'] = [{'path': fresh.name, 'sha256': hashlib.sha256(fresh.read_bytes()).hexdigest()}]
        self.assertEqual(self.errors(self.document), [])
        (self.root / 'assets/audio.js').write_text('const audioGain = .25;\n')
        self.bind_current()
        rec['evidence'] = first_refs
        self.assertEqual([r['id'] for r in self.errors(self.document)], ['R09'])

    def test_pass_cannot_become_na_without_an_applicability_review(self):
        self.assertEqual(self.errors(self.document), [])
        rec = self.document['regressions'][-1]
        rec.clear()
        rec.update(id='R09', status='n/a', note='Changed only the status; no new applicability review.')
        errors = self.errors(self.document)
        self.assertEqual([r['id'] for r in errors], ['R09'])
        self.assertIn('适用性', errors[0]['problem'])

    def test_current_report_missing_ledger_does_not_cold_register(self):
        report = self.report()
        home = self.root / 'docs/checks/incremental'
        home.rename(home.with_name('retained-original-ledger'))
        self.change_audio()
        self.assertNotEqual(report['current_source_sha256'], R.source_digest(self.root))
        self.assertFalse(R.current_report(report, self.root))
        self.assertFalse(home.exists())

    def test_current_report_missing_case_does_not_recreate_record(self):
        report = self.report()
        db = self.root / 'docs/checks/incremental/ledger.sqlite3'
        with closing(sqlite3.connect(db)) as connection, connection:
            connection.execute("DELETE FROM records WHERE check_id='logic.R09'")
        original_bytes = db.read_bytes()
        self.assertFalse(R.current_report(report, self.root))
        self.assertEqual(db.read_bytes(), original_bytes)

    def test_current_report_rejects_unbound_project_and_missing_flow_record(self):
        report = self.report()
        unbound = copy.deepcopy(report)
        unbound.pop('project_root')
        self.assertFalse(R.current_report(unbound, self.root))
        with closing(sqlite3.connect(self.root / 'docs/checks/incremental/ledger.sqlite3')) as db, db:
            db.execute("DELETE FROM records WHERE check_id='logic.F01'")
        self.assertFalse(R.current_report(report, self.root))

    def test_flow_directory_empty_and_partial_missing_evidence_block_cli(self):
        empty = self.root / 'empty.txt'
        empty.touch()
        for refs in ('assets', 'empty.txt', 'synthetic.txt;missing.txt'):
            with self.subTest(evidence=refs):
                self.document['flows'][0].update(status='pass', evidence=refs)
                self.write_doc(self.document)
                result = self.run_cli('--mode', 'build')
                report = json.loads((self.root / 'docs/logic/logic-check.json').read_text())
                self.assertEqual(result.returncode, 1)
                self.assertFalse(report['passed'])
                self.assertEqual([r['id'] for r in report['flows'] if r.get('problem')], ['F01'])
                self.assertFalse(any(r['check_id'] == 'logic.F01' for r in self.rows()))

    def test_case_api_rejects_empty_or_directory_raw_evidence(self):
        records = CaseRecords(self.root)
        self.addCleanup(records.close)
        for evidence in ([], [{'path': 'assets', 'sha256': '0' * 64}]):
            with self.subTest(evidence=evidence), self.assertRaises(C.NeedsScope):
                records.resolve('R09', {'id': 'R09', 'status': 'pass', 'evidence': evidence}, True, [])
        self.assertEqual(self.rows(), [])

    def test_na_source_change_only_requires_that_case_applicability(self):
        rec = self.document['regressions'][-1]
        rec.clear()
        rec.update(id='R09', status='n/a', note='Synthetic source only declares a setting and has no actual audio output.')
        self.assertEqual(self.errors(self.document), [])
        original_rows = self.rows()
        self.change_audio()
        self.assertEqual([r['id'] for r in self.errors(self.document)], ['R09'])
        self.bind_current()
        errors = self.errors(self.document)
        self.assertEqual([r['id'] for r in errors], ['R09'])
        self.assertIn('适用性', errors[0]['problem'])
        rec['applicability_review'] = {
            'source_sha256': R.source_digest(self.root), 'observed_at': '2026-11-08T12:00:00Z',
            'reason': 'Reviewed changed synthetic constant; no audio loader or output consumer has been added.',
        }
        rows, errors = self.validate()
        self.assertEqual(errors, [])
        self.assertEqual({r['id'] for r in rows if r['incremental']['action'] != 'reuse'}, {'R09'})
        self.assertEqual(self.rows()[:9], original_rows)
        (self.root / 'assets/audio.js').write_text('const audioGain = .25;\n')
        self.bind_current()
        rec['applicability_review']['source_sha256'] = R.source_digest(self.root)
        self.assertEqual([r['id'] for r in self.errors(self.document)], ['R09'])

    def test_flow_na_is_bound_to_its_own_inputs(self):
        scope = json.loads(self.scope.read_text())
        scope['checks']['logic.F01']['inputs']['source'] = ['audio.js']
        self.scope.write_text(json.dumps(scope))
        rows, errors = L.validate_flows(self.document, self.root, R.source_digest(self.root))
        self.assertEqual(errors, [])
        self.change_audio()
        self.bind_current()
        rows, errors = L.validate_flows(self.document, self.root, R.source_digest(self.root))
        self.assertEqual([r['id'] for r in errors], ['F01'])
        self.assertEqual({r['incremental']['action'] for r in rows[1:]}, {'reuse'})

    def test_frozen_evidence_tamper_blocks_only_that_case(self):
        self.assertEqual(self.errors(self.document), [])
        row = next(r for r in self.rows() if r['check_id'] == 'logic.R09')
        Path(row['files'][0]['path']).write_text('Changed frozen evidence bytes.')
        self.assertEqual([r['id'] for r in self.errors(self.document)], ['R09'])


if __name__ == '__main__':
    unittest.main()
