"""Subreport bindings preserve original files; never invent inherited approvals."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from art_check import analysis_report_refs


class AnalysisRefs(unittest.TestCase):
    def test_fresh_reports_bind_actual_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / 'page_richness.json'
            f.write_text('{"passed":false}')
            result = analysis_report_refs(root)
            self.assertEqual(result['page_richness.json']['sha256'], hashlib.sha256(f.read_bytes()).hexdigest())
            self.assertEqual(result['page_richness.json']['path'], str(f.resolve()))
            self.assertNotIn('visual-slots-result.json', result)

    def test_inheritance_retains_original_path_and_requires_old_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / 'old'; old.mkdir()
            new = root / 'new'; new.mkdir()
            (old / 'page_richness.json').write_text('{}')
            previous = {'analysis_reports': analysis_report_refs(old)}
            self.assertEqual(analysis_report_refs(new, previous), previous['analysis_reports'])
            self.assertEqual(analysis_report_refs(new, {}), {})
            self.assertFalse((new / 'page_richness.json').exists())
            (old / 'page_richness.json').write_text('{"changed":true}')
            with self.assertRaises(ValueError):
                analysis_report_refs(new, previous)

    def test_unbound_or_relative_inherited_artifact_is_not_resealed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                analysis_report_refs(Path(tmp), {'analysis_reports': {'page_richness.json': {'sha256': '0'*64}}})
            with self.assertRaises(ValueError):
                analysis_report_refs(Path(tmp), {'analysis_reports': {'page_richness.json': {'path': 'old.json', 'sha256': '0'*64}}})


if __name__ == '__main__':
    unittest.main()
