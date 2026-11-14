#!/usr/bin/env python3
"""Maintenance-only compatibility for the opt-in custom-writer diagnostic.

Exercises a synthetic writer in temporary folders, never a real game/build/ZIP.
Canonical writer behavior remains covered by test_single_writer.py.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

DIAGNOSTIC = Path(__file__).with_name('test_writer_refusal.py')
WRITER = '''import json,sys
from pathlib import Path
review,out,mode=sys.argv[1:]
if mode!='broken':
 if not Path(review).exists():sys.exit(1)
 data=json.loads(Path(review).read_text())
 if data['binding']['source_sha256']=='0'*64:sys.exit(1)
 if any(x.get('status')=='fail' for x in data['checks'].values()):sys.exit(1)
 if not data['checks'].get('STORAGE-01',{}).get('auto_reports'):sys.exit(1)
# A diagnostic stub file, not an engine archive or deliverable.
Path(out).mkdir(exist_ok=True)
(Path(out)/'synthetic.zip').write_text('synthetic diagnostic output')
'''


class LegacyWriterCompatibility(unittest.TestCase):
    def exercise(self, mode):
        with tempfile.TemporaryDirectory(prefix='legacy-writer-contract-') as tmp:
            root = Path(tmp)
            review, writer = root/'review.json', root/'synthetic_writer.py'
            data = {'binding': {'source_sha256': 'a'*64},
                    'checks': {'STORAGE-01': {'status': 'pass', 'auto_reports': ['synthetic']}}}
            original = (json.dumps(data)+'\n').encode()
            review.write_bytes(original)
            writer.write_text(WRITER)
            report = root/'result.json'
            cmd = [sys.executable, '-B', str(DIAGNOSTIC), '--review', str(review),
                   '--zip-dir', str(root/'outputs'), '--out', str(report), '--',
                   sys.executable, '-B', str(writer), str(review), str(root/'outputs'), mode]
            run = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=30)
            self.assertTrue(report.is_file(), run.stderr)
            result = json.loads(report.read_text())
            self.assertEqual(review.read_bytes(), original, 'Legacy diagnostic must restore review bytes')
            self.assertEqual(hashlib.sha256(review.read_bytes()).hexdigest(), hashlib.sha256(original).hexdigest())
            return run, result

    def test_explicit_legacy_cli_preserves_five_paths_and_original_review(self):
        run, result = self.exercise('normal')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(result['passed'])
        self.assertEqual(result['checked'], 5)
        self.assertEqual([r['id'] for r in result['checks']],
                         ['missing_review','failed_check','stale_binding','missing_storage','normal'])

    def test_broken_custom_writer_is_detected_and_leaks_quarantined(self):
        run, result = self.exercise('broken')
        self.assertEqual(run.returncode, 1)
        self.assertFalse(result['passed'])
        self.assertEqual(result['failed'], 4)
        self.assertTrue(all(r['leaked_zips_quarantined'] for r in result['checks'][:-1]))

    def test_missing_inputs_remain_usage_error(self):
        run = subprocess.run([sys.executable,'-B',str(DIAGNOSTIC)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('--review', run.stderr)

    def test_legacy_help_remains_available(self):
        run = subprocess.run([sys.executable,'-B',str(DIAGNOSTIC),'--help'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0)
        self.assertIn('--zip-dir', run.stdout)


if __name__ == '__main__':
    unittest.main()
