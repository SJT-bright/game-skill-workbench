#!/usr/bin/env python3
"""简化.11.6 英化开工 unpack_source.py (Saul 2026-11-04, 91 SLS11): the working copy has no .git / .idea / __MACOSX and no
credential files; credential lines left in files are listed for cleaning; the original is not touched.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_unpack_source.py"""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / 'unpack_source.py'
SLS11 = Path('/Users/sijunting/Downloads/！自制游戏/！游戏学习库/游戏文件/23莫慌-SLS11/SLS11.zip')   # local sample only


def make_zip(extra=None):
    out = Path(tempfile.mkdtemp(prefix='unp-')) / 'src.zip'
    files = {'Game/assets/Main.ts': 'export {}', 'Game/project.json': '{}', 'Game/.git/HEAD': 'ref',
             'Game/.git/objects/aa/bb': 'blob', 'Game/.idea/workspace.xml': '<x/>', 'Game/app_desc.txt': '密码：Abc12345',
             '__MACOSX/Game/._Main.ts': 'junk', 'Game/.DS_Store': 'x',
             'Game/settings/project.json': '{"appSecret": ""}'}
    files.update(extra or {})
    with zipfile.ZipFile(out, 'w') as z:
        for k, v in files.items():
            z.writestr(k, v)
    return out


def run(source, out):
    r = subprocess.run([sys.executable, '-B', str(TOOL), '--source', str(source), '--out', str(out)],
                       capture_output=True, text=True)
    return r.returncode, json.loads(r.stdout)


def tree(root):
    return sorted(p.relative_to(root).as_posix() for p in Path(root).rglob('*') if p.is_file())


class Unpack(unittest.TestCase):
    def test_clean_working_copy_from_a_zip(self):
        src = make_zip()
        before = hashlib.sha256(src.read_bytes()).hexdigest()
        out = Path(tempfile.mkdtemp(prefix='unpo-')) / 'work'
        code, r = run(src, out)
        self.assertEqual(code, 0, r)
        files = tree(out)
        self.assertIn('assets/Main.ts', files, 'the single top folder is stripped')
        for bad in ('.git', '.idea', '__MACOSX', 'app_desc.txt', '.DS_Store'):
            self.assertFalse([f for f in files if bad in f], bad)
        self.assertEqual(r['left_out_vcs_ide'], ['Game/.git', 'Game/.idea', '__MACOSX'])
        self.assertEqual([x['path'] for x in r['left_out_credential_files']], ['Game/app_desc.txt'])
        self.assertTrue((out / 'docs/source-intake.json').is_file())
        self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(), before, 'the original ZIP is untouched')

    def test_credential_lines_are_listed_for_cleaning(self):
        code, r = run(make_zip({'Game/settings/project.json': '{"appSecret": "959b3ac0037d0f3c"}'}),
                      Path(tempfile.mkdtemp(prefix='unpo-')) / 'work')
        self.assertEqual(code, 1)
        self.assertEqual(r['status'], 'clean_before_delivery')
        self.assertEqual([x['path'] for x in r['credential_lines_to_clean']], ['settings/project.json'])

    def test_folder_source_and_existing_out(self):
        base = Path(tempfile.mkdtemp(prefix='unpf-'))
        with zipfile.ZipFile(make_zip()) as z:
            z.extractall(base)
        out = Path(tempfile.mkdtemp(prefix='unpo-')) / 'work'
        code, r = run(base / 'Game', out)
        self.assertEqual(code, 0, r)
        self.assertTrue((base / 'Game/.git/HEAD').is_file(), 'the original folder is untouched')
        self.assertFalse((out / '.git').exists())
        self.assertEqual(run(base / 'Game', out)[0], 2, 'an existing --out is never overwritten')

    @unittest.skipUnless(SLS11.is_file(), 'the 91 SLS11 sample is only on the maintainer machine')
    def test_the_real_sls11_zip(self):
        out = Path(tempfile.mkdtemp(prefix='unpo-')) / 'SLS11'
        code, r = run(SLS11, out)
        self.assertEqual(code, 0, r)
        self.assertIn('SLS11/.git', r['left_out_vcs_ide'])
        self.assertFalse((out / '.git').exists())
        self.assertTrue((out / 'assets').is_dir())
        sys.path.insert(0, str(HERE.parents[1] / 'remake-core' / 'scripts'))
        import source_hygiene
        self.assertTrue(source_hygiene.audit(out)['passed'])


if __name__ == '__main__':
    unittest.main()
