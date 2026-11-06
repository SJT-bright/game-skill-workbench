#!/usr/bin/env python3
"""R4N3 (补查2 第 15 组): raw_inputs.keep checks an original ZIP before it becomes the read-only baseline.

弹球传奇's original ZIP had its tail cut off (no central directory); it was kept and only found broken later, when the
old build's audio came out incomplete. keep() now reads the ZIP once (zipfile.testzip) and refuses a broken one.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_r4n3_raw_zip_integrity.py   (seconds, no browser)
"""
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import raw_inputs as R  # noqa: E402


def good_zip(path):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('弹球传奇/assets/Main.js', 'cc.log("原版");' * 200)
        z.writestr('弹球传奇/assets/audio/bgm.mp3', bytes(range(256)) * 400)
    return path


class RawZipIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4n3-zip-'))
        self.game = self.tmp / '弹球传奇'
        self.game.mkdir()

    def tearDown(self):
        R.unlock_for_test_cleanup(self.tmp)
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_tail_truncated_zip_is_refused(self):
        src = good_zip(self.tmp / '弹球传奇_中文原包.zip')
        data = src.read_bytes()
        src.write_bytes(data[:len(data) - 60])  # the central directory is gone, as in 弹球传奇
        with self.assertRaises(ValueError) as cm:
            R.keep(src, self.game)
        self.assertIn('截断', str(cm.exception))
        self.assertFalse((self.game / R.RAW_DIR).exists())  # not registered as the baseline
        self.assertEqual(R.main(['keep', '--source', str(src), '--game-folder', str(self.game)]), 2)

    def test_member_with_bad_crc_is_refused(self):
        src = good_zip(self.tmp / '原包.zip')
        data = bytearray(src.read_bytes())
        i = data.find(b'Main.js') + 40  # inside the first member's compressed data
        data[i] ^= 0xFF
        src.write_bytes(bytes(data))
        self.assertIsNotNone(R.zip_problem(src))
        with self.assertRaises(ValueError):
            R.keep(src, self.game)

    def test_whole_zip_and_folder_are_kept(self):
        src = good_zip(self.tmp / '原包.zip')
        self.assertIsNone(R.zip_problem(src))
        self.assertEqual(R.keep(src, self.game)['status'], 'kept')
        folder = self.tmp / '原文件夹'
        (folder / 'assets').mkdir(parents=True)
        (folder / 'assets' / 'a.js').write_text('x')
        self.assertIsNone(R.zip_problem(folder))
        self.assertEqual(R.keep(folder, self.game)['status'], 'kept')

    def test_non_zip_file_is_not_judged(self):
        f = self.tmp / 'notes.txt'
        f.write_text('hello')
        self.assertIsNone(R.zip_problem(f))


if __name__ == '__main__':
    unittest.main(verbosity=2)
