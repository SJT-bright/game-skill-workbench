#!/usr/bin/env python3
"""v7.7.4 (总表 B17): the read-only commands no longer call a hand-made ZIP a pass.

verify_native_zip.py and upload_preflight.py, run by hand, refuse a ZIP without a matching writer receipt
(DriftRacer v2 went out after both said "pass", carrying an outdated ad service). --structure-only keeps the
structure answer. verify() itself, which the writers and check_package import, is unchanged.
Real packages (2026-10-30): DriftRacer v2 refused (verify exit 3, upload_preflight refuse); FoxDenDash v1 from
build_checked_zip passes; the same FoxDenDash bytes copied without the receipt are refused.
"""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'cocos-game-check' / 'package' / 'scripts'))

import upload_preflight as U  # noqa: E402
import verify_native_zip as V  # noqa: E402


def fake(entry):
    return {'entry': entry, 'entry_label': V.ENTRY_LABEL[entry],
            'entry_reason': 'matching receipt from build_checked_zip' if entry == 'official' else 'no writer receipt x',
            'status': 'local_structure_checks_passed', 'uncompressed_total_bytes': 10, 'main_bytes': 5,
            'file_sha256': {}}


class VerifyCommand(unittest.TestCase):
    def run_main(self, entry, *extra):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(V, 'verify', return_value=fake(entry)), \
                patch.object(sys, 'argv', ['verify_native_zip.py', 'game.zip', *extra]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = V.main()
        return code, out.getvalue(), err.getvalue()

    def test_unofficial_zip_is_refused(self):
        code, out, err = self.run_main('unofficial')
        self.assertEqual(code, 3)
        self.assertIn('unofficial_not_deliverable', out)
        self.assertIn('REFUSED', err)

    def test_structure_only_keeps_the_structure_answer(self):
        code, out, _ = self.run_main('unofficial', '--structure-only')
        self.assertEqual(code, 0)
        self.assertIn('local_structure_checks_passed', out)

    def test_official_zip_passes(self):
        self.assertEqual(self.run_main('official')[0], 0)


class UploadPreflight(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.zip = Path(tmp.name) / 'game.zip'
        self.zip.write_bytes(b'not read: verify is patched')

    def inspect(self, entry, structure_only=False):
        with patch.object(U, 'verify', return_value=fake(entry)):
            return U.inspect(self.zip, structure_only)

    def test_unofficial_zip_is_refused(self):
        r = self.inspect('unofficial')
        self.assertEqual(r['status'], 'refuse')
        self.assertIn('非官方入口', r['errors'][0])

    def test_official_zip_passes(self):
        self.assertEqual(self.inspect('official')['status'], 'pass')

    def test_structure_only_passes_without_receipt(self):
        r = self.inspect('unofficial', structure_only=True)
        self.assertEqual(r['status'], 'pass')
        self.assertIn('structure-only', r['mode'])


if __name__ == '__main__':
    unittest.main()
