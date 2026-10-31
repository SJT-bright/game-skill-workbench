#!/usr/bin/env python3
"""v7.8 (总表 B32 c): old script paths that sessions still call keep working through forwarding stubs.

cocos-game-check/core/scripts/<name>.py (v7.0 - v7.3; logs of 2026-10-29 still run
~/.kiro/crew/skills/cocos-game-check/core/scripts/audit_mobile_input.py, notes say .../core/scripts/serve_preview.py,
cocos-game-to-english/references/english-ui-rebuild.md names .../core/scripts/audit_english_coverage.py) now lives in
remake-core/scripts/<name>.py. Every stub is the same text, forwards to the script of its own name with the same
arguments and prints where it lives now. Run: python3 -B test_stable_paths.py
"""
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[2]
STUBS = SKILLS / 'cocos-game-check' / 'core' / 'scripts'
CALLED = ('serve_preview', 'verify_native_zip', 'make_tiktok_zip', 'check_known_issues', 'preflight', 'art_check',
          'logic_check', 'audit_english_coverage', 'audit_audio_sources', 'audit_startup_contract', 'audit_upload_startup',
          'audit_mobile_input', 'audit_page_readiness')


class Stubs(unittest.TestCase):
    def test_every_stub_is_the_same_text_and_has_a_target(self):
        files = sorted(STUBS.glob('*'))
        self.assertTrue(files)
        texts = {f.read_bytes() for f in files}
        self.assertEqual(len(texts), 1, 'all stubs must be byte-identical')
        for f in files:
            self.assertEqual(f.suffix, '.py', f.name)
            self.assertTrue((SKILLS / 'remake-core' / 'scripts' / f.name).is_file(), f.name)

    def test_the_names_sessions_call_are_there(self):
        for name in CALLED:
            self.assertTrue((STUBS / (name + '.py')).is_file(), name)

    def test_stub_runs_the_moved_script(self):
        for name, want in (('verify_native_zip', 'usage: verify_native_zip.py'), ('package_issue_gate', 'supersede')):
            r = subprocess.run([sys.executable, '-B', str(STUBS / (name + '.py')), '--help'], capture_output=True, text=True,
                               timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(want, r.stdout)
            self.assertIn('已搬到 %s' % (SKILLS / 'remake-core' / 'scripts' / (name + '.py')), r.stderr)

    def test_missing_target_says_so(self):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / 'cocos-game-check' / 'core' / 'scripts' / 'verify_native_zip.py'
            stub.parent.mkdir(parents=True)
            shutil.copy(STUBS / 'verify_native_zip.py', stub)
            r = subprocess.run([sys.executable, '-B', str(stub)], capture_output=True, text=True, timeout=60)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('moved to remake-core/scripts/verify_native_zip.py', r.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=1)
