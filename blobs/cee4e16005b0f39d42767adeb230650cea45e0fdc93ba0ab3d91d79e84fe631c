#!/usr/bin/env python3
"""简化.11.14 R4D 英化开工 unpack_source.py: the Chinese original goes into a read-only _原始输入/ before anything
else (火柴人密室逃脱 deleted it while cleaning old versions), and the intake record carries the installed-Skill hint.
R4D_OLD_TREE=<untouched base tree> also runs the old unpack_source.py to show the original was not kept before.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_r4d_raw_input_intake.py   (seconds)"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
TOOL = HERE / 'unpack_source.py'
sys.path.insert(0, str(HERE.parents[1] / 'remake-core' / 'scripts'))
import raw_inputs as R  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(tool, source, out):
    r = subprocess.run([sys.executable, '-B', str(tool), '--source', str(source), '--out', str(out)],
                       capture_output=True, text=True)
    return r.returncode, json.loads(r.stdout)


class Intake(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4d-intake-'))
        self.game = self.tmp / '火柴人密室逃脱'
        self.game.mkdir()
        self.src = self.game / '中文原包.zip'
        with zipfile.ZipFile(self.src, 'w') as z:
            z.writestr('Game/assets/Main.js', 'cc.log(1)')
            z.writestr('Game/project.json', '{}')

    def tearDown(self):
        R.unlock_for_test_cleanup(self.tmp)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_original_kept_read_only(self):
        code, rec = run(TOOL, self.src, self.game / '英化工程')
        self.assertEqual(code, 0, rec)
        kept = self.game / R.RAW_DIR / '中文原包.zip'
        self.assertEqual(sha(kept), sha(self.src))
        self.assertFalse(os.access(kept, os.W_OK) and os.name != 'nt' and os.geteuid() != 0)
        self.assertEqual(rec['raw_input']['status'], 'kept')
        self.assertIn('clean_old_versions.py', rec['raw_input']['rule'])
        self.assertIn('installed_skills', rec)                 # the start-of-work hash hint is recorded
        intake = json.loads((self.game / '英化工程' / 'docs' / 'source-intake.json').read_text(encoding='utf-8'))
        self.assertEqual(intake['raw_input']['copy'], str(kept.resolve()))
        # the session deletes the original and every old version: the kept copy is still there
        self.src.unlink()
        shutil.rmtree(self.game / '英化工程')
        self.assertEqual(R.verify(self.game)['status'], 'ok')

    def test_second_unpack_reuses_the_copy(self):
        run(TOOL, self.src, self.game / 'w1')
        code, rec = run(TOOL, self.src, self.game / 'w2')
        self.assertEqual(rec['raw_input']['status'], 'already_kept')

    @unittest.skipUnless(os.environ.get('R4D_OLD_TREE'), 'set R4D_OLD_TREE to the untouched base tree')
    def test_old_unpack_keeps_nothing(self):
        old = Path(os.environ['R4D_OLD_TREE']) / 'cocos-game-to-english' / 'scripts' / 'unpack_source.py'
        code, rec = run(old, self.src, self.game / '英化工程')
        self.assertEqual(code, 0, rec)
        self.assertFalse((self.game / R.RAW_DIR).exists())
        self.assertNotIn('raw_input', rec)
        self.assertNotIn('installed_skills', rec)
        self.src.unlink()                                      # cleaning old versions: the original is gone for good
        self.assertEqual(R.verify(self.game)['status'], 'none')


if __name__ == '__main__':
    unittest.main(verbosity=2)
