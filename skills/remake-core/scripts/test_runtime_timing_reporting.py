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
        self.proof = json.loads((CHECK/'runtime-reporting-compat.json').read_text())
        self.current = MODULE.read_bytes()
        previous = self.current.decode()
        for edit in reversed(self.proof['edits']):
            self.assertEqual(previous.count(edit['after']), 1)
            previous = previous.replace(edit['after'], edit['before'], 1)
        self.old = previous.encode()
        self.paths = [MODULE, HERE/'check_ledger.py']

    def test_exact_reverse_edits_reconstruct_formal_old_bytes(self):
        self.assertEqual(hashlib.sha256(self.old).hexdigest(), self.proof['old_runtime_sha256'])
        self.assertEqual(hashlib.sha256(self.current).hexdigest(), self.proof['new_runtime_sha256'])
        self.assertEqual(hashlib.sha256(HELPER.read_bytes()).hexdigest(), self.proof['helper_sha256'])

    def test_exact_reporting_update_preserves_original_fingerprint(self):
        real = Path.read_bytes
        def old_read(path): return self.old if path.resolve() == MODULE.resolve() else real(path)
        with patch.object(Path, 'read_bytes', old_read):
            expected = ledger.tool_fingerprint(self.paths)
        self.assertEqual(timing.rule_fingerprint(ledger, self.paths), expected)

    def test_any_unapproved_logic_edit_invalidates(self):
        approved = timing.rule_fingerprint(ledger, self.paths)
        changed = self.current.replace(b"passed=not problems", b"passed=True", 1)
        self.assertNotEqual(changed, self.current)
        real = Path.read_bytes
        def new_read(path): return changed if path.resolve() == MODULE.resolve() else real(path)
        with patch.object(Path, 'read_bytes', new_read):
            self.assertNotEqual(timing.rule_fingerprint(ledger, self.paths), approved)

    def test_reporting_helper_edit_is_not_implicitly_equivalent(self):
        approved = timing.rule_fingerprint(ledger, self.paths)
        real = Path.read_bytes
        def new_read(path): return real(path)+b'\n# another version\n' if path.resolve() == HELPER.resolve() else real(path)
        with patch.object(Path, 'read_bytes', new_read):
            self.assertNotEqual(timing.rule_fingerprint(ledger, self.paths), approved)

    def test_other_checker_change_is_still_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            other = Path(temp)/'judge.py';other.write_text('threshold=3')
            old = timing.rule_fingerprint(ledger, self.paths+[other])
            other.write_text('threshold=4')
            self.assertNotEqual(timing.rule_fingerprint(ledger, self.paths+[other]), old)

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
