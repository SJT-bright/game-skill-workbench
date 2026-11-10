#!/usr/bin/env python3
"""11.17.14 lightweight art-check record: first full pass is kept, no fingerprints, failing last run blocks.
Run: python3 -B test_art_check_record.py"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import art_check_record as R  # noqa: E402

PASS = {'rows': [{'check': '深色粗字（永久禁止）', 'status': '通过'}], 'failed': 0}
FAIL = {'rows': [{'check': '深色粗字（永久禁止）', 'status': '需处理'}], 'failed': 1}


class Record(unittest.TestCase):
    def project(self, tmp):
        root = Path(tmp) / 'Game'
        (root / 'assets').mkdir(parents=True)
        (root / 'project.json').write_text('{"engine":"cocos-creator-js","version":"2.4.15"}')
        return root

    def test_missing_record_blocks_first_trial_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(tmp)
            self.assertEqual(R.check(root)['level'], 'block')
            self.assertEqual(R.check(root, earlier_trial=True)['level'], 'warn')

    def test_first_full_pass_survives_later_runs_and_holds_no_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(tmp)
            R.write(root, 'pass', PASS, None, 'localize')
            first = R.read(root)['first_full_pass']
            R.write(root, 'pass', PASS, None, 'localize', scoped=['maintenance'])
            data = R.read(root)
            self.assertEqual(data['first_full_pass'], first)
            self.assertNotIn('images', json.dumps(data))
            (root / 'assets' / 'new.png').write_bytes(b'changed')
            self.assertEqual(R.check(root)['level'], 'ok')

    def test_failing_latest_run_blocks_until_fixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(tmp)
            R.write(root, 'pass', PASS, None, 'localize')
            R.write(root, 'fail', FAIL, None, 'localize', scoped=['english_visual_scope'])
            result = R.check(root)
            self.assertEqual(result['level'], 'block')
            self.assertIn('深色粗字', result['message'])
            R.write(root, 'pass', PASS, None, 'localize', scoped=['english_visual_scope'])
            self.assertEqual(R.check(root)['level'], 'ok')

    def test_scoped_pass_alone_is_not_a_first_full_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(tmp)
            R.write(root, 'pass', PASS, None, 'localize', scoped=['maintenance'])
            self.assertEqual(R.check(root)['level'], 'block')
            self.assertEqual(R.check(root, earlier_trial=True)['level'], 'ok')

    def test_old_passing_receipt_counts_without_fingerprint_compare(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(tmp)
            (root / R.LEGACY_RECEIPT).parent.mkdir(parents=True)
            (root / R.LEGACY_RECEIPT).write_text(json.dumps({'status': 'pass', 'images': {'a.png': 'old'}}))
            self.assertEqual(R.check(root)['level'], 'ok')

    def test_3x_not_covered_is_a_warning_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.project(tmp)
            R.write(root, 'not_covered_3x', {'rows': []}, None, 'localize')
            self.assertEqual(R.check(root)['level'], 'warn')


if __name__ == '__main__':
    unittest.main()
