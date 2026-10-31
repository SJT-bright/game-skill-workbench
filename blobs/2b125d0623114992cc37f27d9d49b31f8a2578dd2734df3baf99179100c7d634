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


class RenamedZip(unittest.TestCase):
    """v7.7.5 (五款返工 #8): a ZIP renamed after writing (Saul renames before uploading) still finds its receipt,
    by the ZIP's sha256 in the same folder. Any other bytes still have no receipt."""
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def write(self, name, data):
        (self.dir / name).write_bytes(data)
        return self.dir / name

    def receipt(self, name, digest, tool='build_checked_zip'):
        import json
        (self.dir / name).write_text(json.dumps({'tool': tool, 'zip_sha256': digest}), encoding='utf-8')
        return self.dir / name

    def test_same_name_receipt_first_then_by_bytes(self):
        import hashlib
        z = self.write('上传TikTok用这个.zip', b'zip bytes')
        digest = hashlib.sha256(b'zip bytes').hexdigest()
        self.assertFalse(V.find_receipt(z, digest)[1])                          # nothing there yet
        r = self.receipt('Game_v3.zip.receipt.json', digest)
        self.assertEqual(V.find_receipt(z, digest), (r, True))
        own = self.receipt('上传TikTok用这个.zip.receipt.json', 'other')
        self.assertEqual(V.find_receipt(z, digest), (own, False))               # the same-name receipt wins

    def test_other_bytes_or_unofficial_tool_find_nothing(self):
        import hashlib
        z = self.write('changed.zip', b'changed bytes')
        self.receipt('Game_v3.zip.receipt.json', hashlib.sha256(b'zip bytes').hexdigest())
        self.receipt('Hand.zip.receipt.json', hashlib.sha256(b'changed bytes').hexdigest(), tool='zip -r')
        path, by_bytes = V.find_receipt(z, hashlib.sha256(b'changed bytes').hexdigest())
        self.assertFalse(by_bytes)
        self.assertEqual(path.name, 'changed.zip.receipt.json')
        self.assertEqual(V.receipt_status(z, 'x', {})['entry'], 'unofficial')

    def test_real_renamed_copy_of_driftracer_v31_is_official(self):
        import shutil
        src = Path('/Users/sijunting/Downloads/！自制游戏/1全民飞车漂移/交付/DriftRacer3D_TikTok_Test_v3.1_20261030.zip')
        if not (src.is_file() and V.receipt_path(src).is_file()):
            self.skipTest('DriftRacer v3.1 not on this machine')
        copy = self.dir / '上传TikTok用这个_飞车v3.1.zip'
        shutil.copyfile(src, copy)
        shutil.copyfile(V.receipt_path(src), self.dir / V.receipt_path(src).name)
        out = V.verify(copy)
        self.assertEqual(out['entry'], 'official', out.get('entry_reason'))
        self.assertIn('renamed', out['entry_reason'])


class CheckPackageCommand(unittest.TestCase):
    """v7.8 (总表 B17): check_package.py run by hand on a ZIP no official writer wrote says "只读预检，不可交付" and
    exits 3 (丛林荡藤 v6, 剪刀达人 v30 were called a pass). --structure-only keeps the old answer. check() itself is
    unchanged (both writers import it), so it is patched here and only main()'s verdict is tested."""
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(HERE.parent.parent / 'cocos-game-check' / 'package-check' / 'scripts'))
        import check_package
        cls.C = check_package

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.zip = Path(tmp.name) / 'game.zip'
        self.zip.write_bytes(b'not read: check is patched')

    def run_main(self, entry, *extra):
        result = {'status': 'pass', 'entry': entry, 'entry_reason': 'matching receipt from build_checked_zip'
                  if entry == 'official' else 'no writer receipt game.zip.receipt.json'}
        out, err = io.StringIO(), io.StringIO()
        with patch.object(self.C, 'check', return_value=result), \
                patch.object(sys, 'argv', ['check_package.py', '--input', str(self.zip), *extra]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = self.C.main()
        return code, out.getvalue(), err.getvalue()

    def test_unofficial_zip_is_read_only_not_deliverable(self):
        code, out, err = self.run_main('unofficial')
        self.assertEqual(code, 3)
        self.assertIn('unofficial_not_deliverable', out)
        self.assertIn('只读预检，不可交付', err)
        self.assertIn('REFUSED', err)

    def test_structure_only_keeps_the_old_answer(self):
        code, out, err = self.run_main('unofficial', '--structure-only')
        self.assertEqual(code, 0)
        self.assertIn('structure-only', out)
        self.assertIn('只读预检，不可交付', err)       # still says it is not a delivery approval

    def test_official_zip_passes(self):
        code, out, err = self.run_main('official')
        self.assertEqual(code, 0)
        self.assertIn('官方入口', err)
        self.assertNotIn('REFUSED', err)


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
