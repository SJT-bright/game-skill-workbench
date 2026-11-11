"""Reporting repair must preserve exact approved prior quality identities only."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
CHECK = HERE.parents[1]/'cocos-game-check/package-check/scripts'
sys.path.insert(0, str(CHECK))
import check_ledger as ledger
import runtime_timing as timing

MODULE = CHECK/'runtime_incremental.py'
HELPER = CHECK/'runtime_timing.py'


class RuntimeTimingTests(unittest.TestCase):
    def setUp(self):
        self.reporting = CHECK/'runtime-reporting-compat.json'
        self.scope_file = CHECK/'runtime-scope-compat.json'
        self.proof = json.loads(self.reporting.read_text())
        self.scope = json.loads(self.scope_file.read_text())
        self.current = MODULE.read_bytes()
        self.ledger_path = Path(ledger.__file__).resolve()
        self.paths = [MODULE, self.ledger_path]

    def test_scope_approval_preserves_the_historical_reporting_pair(self):
        # v2 chains onto the original reporting-only proof. The scope scheduler
        # and helper must not be re-signed as the old reporting byte pair.
        self.assertEqual(self.proof['schema'], 'runtime-reporting-compat.v1')
        self.assertEqual(self.scope['schema'], 'runtime-scope-compat.v2')
        self.assertEqual(self.scope['prior_runtime_sha256'], self.proof['new_runtime_sha256'])
        self.assertEqual(self.scope['prior_helper_sha256'], self.proof['helper_sha256'])
        self.assertEqual(self.scope['prior_compat_sha256'], hashlib.sha256(self.reporting.read_bytes()).hexdigest())
        self.assertNotEqual(hashlib.sha256(self.current).hexdigest(), self.proof['new_runtime_sha256'])
        self.assertNotEqual(hashlib.sha256(HELPER.read_bytes()).hexdigest(), self.proof['helper_sha256'])

    def test_exact_scope_triple_normalizes_runtime_and_ledger_identity(self):
        self.assertEqual(self.scope['scope'], 'scheduler-and-evidence-recovery-exact-byte-triple')
        self.assertEqual(hashlib.sha256(self.current).hexdigest(), self.scope['new_runtime_sha256'])
        self.assertEqual(hashlib.sha256(HELPER.read_bytes()).hexdigest(), self.scope['new_helper_sha256'])
        self.assertEqual(hashlib.sha256(self.ledger_path.read_bytes()).hexdigest(), self.scope['new_ledger_sha256'])
        expected = ledger.sha(sorted([(MODULE.name, self.proof['old_runtime_sha256']),
                                      (self.ledger_path.name, self.scope['prior_ledger_sha256'])]))
        with patch.object(ledger, 'tool_fingerprint', wraps=ledger.tool_fingerprint) as fallback:
            actual = timing.rule_fingerprint(ledger, self.paths)
        fallback.assert_not_called()
        self.assertEqual(actual, expected)
        self.assertNotEqual(actual, ledger.tool_fingerprint(self.paths))

    def test_any_unapproved_runtime_or_ledger_edit_uses_the_current_fingerprint(self):
        approved = timing.rule_fingerprint(ledger, self.paths)
        changes = [(MODULE, self.current.replace(b"passed=not problems", b"passed=True", 1)),
                   (self.ledger_path, self.ledger_path.read_bytes()+b'\n# unapproved ledger edit\n')]
        read_bytes, regular = Path.read_bytes, ledger.tool_fingerprint
        for changed_path, changed in changes:
            with self.subTest(file=changed_path.name):
                self.assertNotEqual(changed, read_bytes(changed_path))
                def new_read(path):
                    return changed if path.resolve() == changed_path.resolve() else read_bytes(path)
                with patch.object(Path, 'read_bytes', new_read), \
                        patch.object(ledger, 'tool_fingerprint', wraps=regular) as fallback:
                    actual = timing.rule_fingerprint(ledger, self.paths)
                    self.assertEqual(actual, regular(self.paths))
                fallback.assert_called_once_with(self.paths)
                self.assertNotEqual(actual, approved)

    def test_reporting_helper_edit_is_not_implicitly_equivalent(self):
        approved = timing.rule_fingerprint(ledger, self.paths)
        read_bytes, regular = Path.read_bytes, ledger.tool_fingerprint
        def new_read(path):
            return read_bytes(path)+b'\n# unapproved helper edit\n' if path.resolve() == HELPER.resolve() else read_bytes(path)
        with patch.object(Path, 'read_bytes', new_read), \
                patch.object(ledger, 'tool_fingerprint', wraps=regular) as fallback:
            actual = timing.rule_fingerprint(ledger, self.paths)
            self.assertEqual(actual, regular(self.paths))
        fallback.assert_called_once_with(self.paths)
        self.assertNotEqual(actual, approved)

    def test_other_checker_change_is_still_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            other = Path(temp)/'judge.py';other.write_text('threshold=3')
            old = timing.rule_fingerprint(ledger, self.paths+[other])
            other.write_text('threshold=4')
            changed = timing.rule_fingerprint(ledger, self.paths+[other])
            expected = ledger.sha(sorted([(MODULE.name, self.proof['old_runtime_sha256']),
                                          (self.ledger_path.name, self.scope['prior_ledger_sha256']),
                                          (other.name, ledger.sha(other.read_bytes()))]))
            self.assertEqual(changed, expected)
            self.assertNotEqual(changed, old)

    def test_suite_seconds_never_repeat_whole_batch_seconds(self):
        report = {'seconds': 100, '_timing_batch_id': 'batch-1', 'suites': [
            {'suite': 'startup', 'seconds': 3}, {'suite': 'layout', 'seconds': 7}]}
        self.assertEqual(timing.suite_seconds(report, 'startup', False), 3)
        self.assertEqual(timing.suite_seconds(report, 'layout', False), 7)
        self.assertEqual(timing.suite_seconds(report, 'startup', True), 0)
        self.assertIsNone(timing.suite_seconds(report, 'unmeasured', False))
        self.assertFalse(timing.suite_metadata(report, 'layout', False)['additive'])
        self.assertEqual(timing.suite_metadata(report, 'unmeasured', False)['scope'], 'shared_batch')


if __name__ == '__main__': unittest.main()
