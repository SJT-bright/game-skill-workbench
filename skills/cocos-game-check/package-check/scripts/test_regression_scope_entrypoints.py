"""Boundary tests with no real browser invocation."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_package as check
import package_gates
import regression_scope_gate as scope


class Entrypoints(unittest.TestCase):
    def test_writer_missing_plan_does_not_start_either_regression(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(scope.os.environ, {}, clear=True), \
                patch.object(check, 'rewarded_ad_gate') as ads, patch.object(check, 'runtime_gate') as runtime:
            report = check.writer_regressions({'game.js': b''}, folder, policy='new', project=Path(folder))
            self.assertEqual(report['status'], 'scope_required')
            self.assertTrue(report['blocked'])
            ads.assert_not_called()
            runtime.assert_not_called()

    def test_delivery_receipt_mismatch_has_no_live_fallback(self):
        def verify(*args, _verified_files, **kwargs):
            _verified_files['game.js'] = b''
            return {'entry': 'official', 'receipt': '/test/receipt.json', 'sha256': scope.sha(b'zip')}

        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'game.zip'
            archive.write_bytes(b'zip')
            with patch.object(check.verifier, 'verify', side_effect=verify), \
                    patch.object(package_gates, 'run', return_value={'blocks': [], 'policy': 'new'}), \
                    patch.object(check, 'packed_assets', return_value={'passed': True}), \
                    patch.object(check, 'reusable_regressions', return_value={'reused': False, 'why': 'different adapter'}), \
                    patch.object(check, 'rewarded_ad_gate') as ads, patch.object(check, 'runtime_gate') as runtime:
                with self.assertRaisesRegex(ValueError, 'delivery can only verify matching writer evidence'):
                    check.check(archive, policy='new', reuse_writer_regressions=True, project=folder)
                ads.assert_not_called()
                runtime.assert_not_called()

    def test_diagnostic_pass_cannot_form_a_writer_receipt(self):
        ad = {'passed': True, 'cases': [], 'complete': False, 'planned_not_run': ['cancel']}
        runtime = {'passed': True, 'suites': []}
        self.assertIsNone(check.regression_record(ad, runtime))


if __name__ == '__main__':
    unittest.main()
