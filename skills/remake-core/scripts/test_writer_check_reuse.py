"""Real file/probe fixtures: unchanged reuse, changed dependency rejection, original evidence retained."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch

import audit_runtime_coverage as coverage_tool
import writer_check_reuse as reuse

HERE = Path(__file__).resolve().parent


class WriterReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.roots = {n: self.project/n for n in ('native', 'web', 'source')}
        for root in self.roots.values():
            root.mkdir()
            (root/'main.js').write_text('var state = 1;')
        self.coverage = self.project/'coverage.json'
        files, sites = coverage_tool.inventory(self.roots)
        self.coverage.write_text(json.dumps({'schema': 'runtime_coverage.v1', 'artifacts': files, 'sites': {}, 'domains': {}}))

    def command(self, kind):
        base = [sys.executable, str(HERE/('audit_runtime_coverage.py' if kind == 'runtime-coverage' else 'run_reward_storage_probe.py'))]
        if kind == 'runtime-coverage':
            base += ['--source', str(self.roots['source']), '--coverage', str(self.coverage)]
        return base+['--native', str(self.roots['native']), '--web', str(self.roots['web'])]

    def run_check(self, kind='runtime-coverage'):
        return reuse.run_command(self.project, kind, self.command(kind), **self.roots, coverage=self.coverage)

    def test_actual_coverage_executes_once_then_retains_exact_original_output(self):
        a = self.run_check()
        self.assertEqual(a.returncode, 0, a.stdout+a.stderr)
        self.assertFalse(a.check_reuse['reused'])
        original = subprocess.run
        with patch.object(reuse.subprocess, 'run', wraps=original) as command:
            b = self.run_check()
        self.assertEqual(command.call_count, 0)
        self.assertTrue(b.check_reuse['reused'])
        self.assertEqual(a.stdout, b.stdout)
        self.assertIn('original_executed_at', b.check_reuse)

    def test_changed_js_and_new_file_cannot_reuse(self):
        self.assertEqual(self.run_check().returncode, 0)
        (self.roots['native']/'new.js').write_text('localStorage.setItem("new", 1)')
        b = self.run_check()
        self.assertNotEqual(b.returncode, 0)
        self.assertFalse(b.check_reuse['reused'])

    def test_picture_only_change_does_not_repeat_storage_discovery(self):
        self.assertEqual(self.run_check().returncode, 0)
        (self.roots['native']/'button.png').write_bytes(b'not-used-by-storage-validator')
        self.assertTrue(self.run_check().check_reuse['reused'])

    def test_changed_external_observation_invalidates_coverage(self):
        proof = self.project/'evidence.txt';proof.write_text('controlled execution')
        for root in self.roots.values(): (root/'main.js').write_text('localStorage.getItem(KEY)')
        files, sites = coverage_tool.inventory(self.roots)
        doc = {'schema': 'runtime_coverage.v1', 'artifacts': files,
            'sites': {k: {'discovered': s, 'domain': 'ignored'} for k,s in sites.items()},
            'domains': {'ignored': {'kind': 'excluded', 'reason': 'This controlled fixture is not player state and retains its real supporting observation.',
                'evidence': {'path': 'evidence.txt', 'sha256': reuse.digest(proof.read_bytes())}}}}
        self.coverage.write_text(json.dumps(doc))
        self.assertEqual(self.run_check().returncode, 0)
        proof.write_text('different observation')
        self.assertNotEqual(self.run_check().returncode, 0)

    def test_changed_cache_payload_is_not_trusted(self):
        a = self.run_check();p = Path(a.check_reuse['record'])
        doc = json.loads(p.read_text());doc['execution']['stdout'] = '{"passed":true,"changed":true}'
        p.write_text(json.dumps(doc))
        b = self.run_check()
        self.assertFalse(b.check_reuse['reused'])
        self.assertNotIn('changed', b.stdout)

    def test_reward_absence_real_probe_reuses_but_new_ledger_invalidates(self):
        a = self.run_check('reward-storage')
        self.assertEqual(json.loads(a.stdout)['status'], 'not_applicable')
        self.assertTrue(self.run_check('reward-storage').check_reuse['reused'])
        (self.roots['native']/'ledger.js').write_text('GrowthLedger:[function')
        b = self.run_check('reward-storage')
        self.assertNotEqual(b.returncode, 0)
        self.assertFalse(b.check_reuse['reused'])

    def test_applicable_vm_probe_is_not_cached_without_clock_contract(self):
        fake = subprocess.CompletedProcess([], 0, '{"passed":true,"status":"passed","applicable":true}', '')
        with patch.object(reuse.subprocess, 'run', return_value=fake) as command:
            self.run_check('reward-storage');self.run_check('reward-storage')
        self.assertEqual(command.call_count, 2)

    def test_missing_evidence_and_failed_check_are_not_reused(self):
        self.coverage.write_text('{}')
        a = self.run_check();b = self.run_check()
        self.assertNotEqual(a.returncode, 0)
        self.assertNotEqual(b.returncode, 0)
        self.assertFalse(b.check_reuse['reused'])

    def test_input_mutation_during_check_refuses_result(self):
        def mutate(*a, **kw):
            (self.roots['native']/'main.js').write_text('var state = 2;')
            return subprocess.CompletedProcess(a[0], 0, '{"passed":true}', '')
        with patch.object(reuse.subprocess, 'run', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'inputs changed'):
                self.run_check()

    def test_concurrent_writer_requests_share_one_actual_execution(self):
        def slow(*a, **kw):
            time.sleep(0.15)
            return subprocess.CompletedProcess(a[0], 0, '{"passed":true}', '')
        with patch.object(reuse.subprocess, 'run', side_effect=slow) as command:
            with ThreadPoolExecutor(max_workers=2) as pool:
                rows = list(pool.map(lambda _:self.run_check(), range(2)))
        self.assertEqual(command.call_count, 1)
        self.assertEqual(sorted(r.check_reuse['reused'] for r in rows), [False, True])

    def test_native_reuse_rechecks_full_identity_and_returns_copy(self):
        memo = reuse.NativeAuditMemo();state = {'native': 'old', 'source': 'old'}
        def check(*args): return [], {'game.js': 8}, {'ok': ['original']}
        with patch.object(reuse, 'native_identity', side_effect=lambda *args: dict(state)):
            a = memo.run(None,None,None,None,check);a[2]['ok'].append('mutated caller')
            b = memo.run(None,None,None,None,check)
            self.assertTrue(b[2]['audit_reuse']['reused']);self.assertEqual(b[2]['ok'], ['original'])
            state['source'] = 'changed'
            c = memo.run(None,None,None,None,check)
            self.assertFalse(c[2]['audit_reuse']['reused'])

    def test_native_audio_documents_and_canonical_external_dependencies_are_bound(self):
        import tiktok_finalize
        context = {'project': str(self.project)}
        with patch.object(tiktok_finalize, 'check_source_record', return_value=[]) as validity, \
                patch.object(reuse, 'tools_state', return_value={}), \
                patch.object(reuse, 'environment', return_value={}):
            before = reuse.native_identity(self.roots['native'], 'localize', 'new', context)
            folder = self.project/'docs/audio';folder.mkdir(parents=True)
            (folder/'needs.csv').write_text('id,type\nlose,sfx\n')
            after = reuse.native_identity(self.roots['native'], 'localize', 'new', context)
            self.assertNotEqual(before, after)
            validity.return_value = [{'id': 'K5_source_finalized', 'message': 'external dependency changed'}]
            with self.assertRaisesRegex(ValueError, 'source preparation is not current'):
                reuse.native_identity(self.roots['native'], 'localize', 'new', context)

    def test_unknown_gate_never_reuses_native_result(self):
        import package_gates
        with patch.object(package_gates, 'GATE_MODULES', (*package_gates.GATE_MODULES, 'new_external_gate')):
            calls = []
            def check(*a): calls.append(1);return [], {}, {}
            memo = reuse.NativeAuditMemo()
            for _ in range(2): memo.run(self.roots['native'], 'localize', 'new', {}, check)
            self.assertEqual(len(calls), 2)

    def test_native_hook_mutation_runs_check_again(self):
        memo = reuse.NativeAuditMemo();state = {'native': 'old'}
        with patch.object(reuse, 'native_identity', side_effect=lambda *args: dict(state)):
            calls = []
            def check(*a): calls.append(1);return [], {}, {}
            memo.run(None,None,None,None,check)
            state['native'] = 'hook changed bytes'
            memo.run(None,None,None,None,check)
            self.assertEqual(len(calls), 2)

    def test_native_mutation_while_checking_is_not_a_pass(self):
        memo = reuse.NativeAuditMemo();states = iter([{'native':1}, {'native':2}])
        with patch.object(reuse, 'native_identity', side_effect=lambda *a:next(states)):
            with self.assertRaisesRegex(ValueError, 'inputs changed'):
                memo.run(None,None,None,None,lambda *a:([],{},{}))


if __name__ == '__main__': unittest.main()
