import tempfile
from pathlib import Path
import unittest
import creator_migration as M


class BuildDiagnostic(unittest.TestCase):
    def probe(self, text, **kwargs):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / 'build.log'; log.write_text(text)
            return M.build_diagnostic(log, **kwargs)

    def test_initialization_does_not_prove_modal_or_cache_failure(self):
        row = self.probe('Initializing Cocos2d\nInitializing engine extends', timed_out=True)
        self.assertEqual(row['kind'], 'no_progress_unclassified')
        self.assertFalse(row['automatic_retry'])
        self.assertFalse(row['automatic_cache_reset'])

    def test_only_observed_error_selects_specific_repair(self):
        for text, kind in [('Cannot resolve module ResKeys', 'module_resolution'),
                           ('showMessageBoxSync at javascript importer', 'editor_modal_observed'),
                           ('GPU process exited', 'gpu_process_error')]:
            with self.subTest(text=text):
                row = self.probe(text, returncode=1)
                self.assertEqual(row['kind'], kind)
                self.assertEqual(row['returncode'], 1)
                self.assertIn(text, row['log_tail'])

    def test_unknown_failure_remains_unclassified(self):
        row = self.probe('unknown error', returncode=2)
        self.assertEqual(row['kind'], 'build_failed_unclassified')
        self.assertEqual(row['status'], 'diagnosis_required')


if __name__ == '__main__':
    unittest.main()
