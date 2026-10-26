"""Dependency-byte evidence reuse across candidate directories, with real local runners."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from check_package import native_files, write_archive
from test_package_checks import fixture
from build_checked_zip import build
from prepare_delivery import prepare
import package_issue_gate as issues


class IssueRelocation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='issue relocation ')
        self.root = Path(self.temp.name)
        self.project = self.root/'project'; self.project.mkdir()
        issues.initialize(self.project)
        self.native = self.root/'original Native'; self.native.mkdir()
        self.negative = self.root/'fault Native'; self.negative.mkdir()
        self.normal = self.root/'normal Native'; self.normal.mkdir()
        for root, delta in [(self.native, 1), (self.negative, 2), (self.normal, 1)]:
            (root/'state.json').write_text(json.dumps({'delta': delta}))
        self.runner = self.root/'observed_runner.py'
        self.runner.write_text(
            "import argparse,json\nfrom pathlib import Path\n"
            "p=argparse.ArgumentParser();p.add_argument('--native');p.add_argument('--case');a=p.parse_args()\n"
            "print(json.dumps({'observed':json.loads((Path(a.native)/'state.json').read_text())}))\n")
        self.cases = [{'id':'reward_once','assertions':[{'path':['delta'],'op':'eq','value':1}]}]
        issues.register(self.project, self.native, 'reward-once', 'Do not pay twice',
                        ['state.json'], self.cases, self.runner)
        self.proof_ref = issues.retest(self.project, self.native, 'reward-once',
                                      self.negative, self.normal, self.root/'proof')

    def tearDown(self):
        self.temp.cleanup()

    def clone(self):
        moved = self.root/'next candidate'
        shutil.copytree(self.native, moved)
        return moved

    def update_raw(self, kind, change):
        # A new ledger reference is necessary to reach semantic checks rather
        # than merely fail the outer immutable-file hash.
        proof = issues.read_ref(self.proof_ref)
        raw_ref = proof['cases']['reward_once'][kind]
        raw = issues.read_ref(raw_ref)
        change(raw)
        path = Path(raw_ref['path']); path.write_text(json.dumps(raw))
        raw_ref['sha256'] = issues.sha(path)
        proof_path = self.root/'changed-proof.json'
        proof_path.write_text(json.dumps(proof))
        self.proof_ref = {'path': str(proof_path), 'sha256': issues.sha(proof_path)}
        issues.append(self.project, 'retested', {'id':'reward-once','proof':self.proof_ref})

    def test_identical_candidate_reuses_without_execution_or_new_receipt(self):
        moved = self.clone()
        _, ledger, head = issues.paths(self.project)
        before = {p: p.read_bytes() for p in (ledger, head, Path(self.proof_ref['path']))}
        with patch.object(issues.subprocess, 'run', side_effect=AssertionError('unexpected replay')):
            result = issues.audit(self.project, moved)
        row = result['checked_issues'][0]
        self.assertTrue(result['passed'])
        self.assertTrue(row['dependency_bytes_reused'])
        self.assertEqual(row['executed_native_root'], str(self.native.resolve()))
        self.assertEqual(row['current_native_root'], str(moved.resolve()))
        self.assertEqual(row['target_sha256'], {'state.json':issues.sha(moved/'state.json')})
        self.assertTrue(all(p.read_bytes() == raw for p, raw in before.items()))

    def test_same_root_still_validates(self):
        row = issues.audit(self.project, self.native)['checked_issues'][0]
        self.assertFalse(row['dependency_bytes_reused'])

    def test_cli_check_accepts_identical_new_candidate(self):
        result = subprocess.run([sys.executable, '-B', str(Path(issues.__file__).resolve()),
                                 'check', '--project', str(self.project), '--native', str(self.clone())],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)['result']['checked_issues'][0]['dependency_bytes_reused'])

    def test_related_bytes_change_refused(self):
        moved = self.clone(); (moved/'state.json').write_text('{"delta":2}')
        with self.assertRaisesRegex(ValueError, 'stale'):
            issues.audit(self.project, moved)

    def test_unrelated_candidate_change_reuses(self):
        moved = self.clone(); (moved/'unrelated.json').write_text('{"theme":"other"}')
        self.assertTrue(issues.audit(self.project, moved)['passed'])

    def test_missing_current_dependency_refused(self):
        moved = self.clone(); (moved/'state.json').unlink()
        with self.assertRaisesRegex(ValueError, 'target missing'):
            issues.audit(self.project, moved)

    def test_missing_original_execution_artifact_refused(self):
        moved = self.clone(); (self.native/'state.json').unlink()
        with self.assertRaisesRegex(ValueError, 'production artifact missing/changed'):
            issues.audit(self.project, moved)

    def test_changed_original_execution_artifact_refused(self):
        moved = self.clone(); (self.native/'state.json').write_text('{"delta":2}')
        with self.assertRaisesRegex(ValueError, 'production artifact missing/changed'):
            issues.audit(self.project, moved)

    def test_missing_original_root_refused(self):
        moved = self.clone(); shutil.rmtree(self.native)
        with self.assertRaisesRegex(ValueError, 'original executed Native/control roots missing'):
            issues.audit(self.project, moved)

    def test_fault_and_normal_originals_remain_required(self):
        moved = self.clone()
        for root in (self.negative, self.normal):
            with self.subTest(root=root.name):
                path = root/'state.json'; before = path.read_bytes(); path.unlink()
                try:
                    with self.assertRaisesRegex(ValueError, 'production artifact missing/changed'):
                        issues.audit(self.project, moved)
                finally:
                    path.write_bytes(before)

    def test_unchanged_bytes_at_unrelated_path_cannot_replace_original_artifact(self):
        moved = self.clone(); other = self.root/'same-bytes.json'
        other.write_bytes((self.native/'state.json').read_bytes())
        self.update_raw('current', lambda row:row['artifacts']['state.json'].update(path=str(other)))
        with self.assertRaisesRegex(ValueError, 'original executed Native target'):
            issues.audit(self.project, moved)

    def test_raw_root_cannot_be_relabelled_to_current_candidate(self):
        moved = self.clone()
        self.update_raw('current', lambda row:row.update(executed_native_root=str(moved.resolve())))
        with self.assertRaisesRegex(ValueError, 'raw executed Native identity mismatch'):
            issues.audit(self.project, moved)

    def test_pass_flag_cannot_cover_wrong_observation(self):
        moved = self.clone()
        self.update_raw('current', lambda row:row.update(passed=True, observed={'delta':2}))
        with self.assertRaisesRegex(ValueError, 'postconditions'):
            issues.audit(self.project, moved)

    def test_changed_runner_and_checker_refused(self):
        moved = self.clone()
        before = self.runner.read_bytes(); self.runner.write_bytes(before+b'# modified\n')
        with self.assertRaisesRegex(ValueError, 'runner changed'):
            issues.audit(self.project, moved)
        self.runner.write_bytes(before)
        proof = issues.read_ref(self.proof_ref); proof['checker_sha256'] = '0'*64
        path = self.root/'wrong-checker.json'; path.write_text(json.dumps(proof))
        issues.append(self.project,'retested',{'id':'reward-once','proof':{'path':str(path),'sha256':issues.sha(path)}})
        with self.assertRaisesRegex(ValueError, 'checker changed'):
            issues.audit(self.project, moved)

    def test_scope_revision_still_requires_real_retest(self):
        moved = self.clone(); previous_cases = copy.deepcopy(self.cases)
        revised = self.root/'revised_runner.py'; revised.write_text(self.runner.read_text()+'# revised\n')
        issues.revise_scope(self.project, moved, 'reward-once', ['state.json'], revised, 'Review migrated candidate')
        with self.assertRaisesRegex(ValueError, 'no passed retest'):
            issues.audit(self.project, moved)
        issues.retest(self.project, moved, 'reward-once', self.negative, self.normal, self.root/'new-proof')
        self.assertTrue(issues.audit(self.project, moved)['passed'])
        events,_ = issues.load(self.project)
        self.assertEqual(events[1]['payload']['message'], 'Do not pay twice')
        self.assertEqual(issues.issue_state(events)['reward-once']['contract']['cases'], previous_cases)


class RelocatedWriterDelivery(unittest.TestCase):
    setUp = IssueRelocation.setUp
    tearDown = IssueRelocation.tearDown
    clone = IssueRelocation.clone

    def package(self):
        (self.root/'other-temp').mkdir()
        data = fixture()
        config = json.loads(data['assets/main/config.json'])
        config.update(name='main', paths={'0':['runtime-fixture',0]}, types=['cc.JsonAsset'])
        data['assets/main/config.json'] = json.dumps(config).encode()
        for name, raw in data.items():
            p=self.native/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(raw)
        manifest = self.root/'resources.json'
        manifest.write_text('{"resources":[{"bundle":"main","path":"runtime-fixture","type":"cc.JsonAsset"}]}')
        return self.clone(), manifest

    def test_writer_and_delivery_accept_same_dependency_bytes(self):
        moved,manifest = self.package(); archive=self.root/'game.zip'
        with patch('build_checked_zip.audit_final_startup', return_value={'passed':True}):
            result=build(moved,'test-target',archive,project=self.project,resource_manifest=manifest)
        self.assertTrue(result['package_obligations']['reported_issues']['checked_issues'][0]['dependency_bytes_reused'])
        with patch('prepare_delivery.tempfile.gettempdir',return_value=str(self.root/'other-temp')), \
                patch('prepare_delivery.audit_final_startup',return_value={'passed':True}):
            receipt=prepare(archive,moved,'test-target',self.root/'delivery.json',
                            project=self.project,resource_manifest=manifest)
        self.assertTrue(receipt['expected_tree_exact'])

    def test_original_evidence_loss_blocks_writer_before_runtime(self):
        moved,manifest=self.package(); (self.native/'state.json').unlink(); out=self.root/'game.zip'
        with patch('build_checked_zip.audit_final_startup') as runtime:
            with self.assertRaisesRegex(ValueError,'production artifact missing/changed'):
                build(moved,'test-target',out,project=self.project,resource_manifest=manifest)
            runtime.assert_not_called()
        self.assertFalse(out.exists())

    def test_original_evidence_loss_blocks_delivery_record(self):
        moved,manifest=self.package(); archive=self.root/'game.zip';write_archive(archive,native_files(moved))
        (self.normal/'state.json').unlink();record=self.root/'delivery.json'
        with patch('prepare_delivery.tempfile.gettempdir',return_value=str(self.root/'other-temp')), \
                patch('prepare_delivery.audit_final_startup') as runtime:
            with self.assertRaisesRegex(ValueError,'production artifact missing/changed'):
                prepare(archive,moved,'test-target',record,project=self.project,resource_manifest=manifest)
            runtime.assert_not_called()
        self.assertFalse(record.exists())


if __name__ == '__main__':
    unittest.main()
