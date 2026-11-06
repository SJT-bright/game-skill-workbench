#!/usr/bin/env python3
"""简化.11.14 R4D: original inputs survive a cleanup; the installed-Skill hash check reports direct edits.

  - T21:original_source_deleted (火柴人密室逃脱): a cleanup that removes every old version also removed the Chinese
    original ZIP. raw_inputs.keep() puts a read-only copy in _原始输入/; clean_old_versions.py skips it.
  - T21:installed_skill_direct_edit (39 times): installed_skill_check.py compares installed files with the release
    hashes (PROVENANCE.json / distribution-manifest.json) and says 「已装 Skill 被改过，请走补丁」. Hint only.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_r4d_raw_inputs_and_installed.py   (seconds, no browser)
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clean_old_versions as C  # noqa: E402
import installed_skill_check as I  # noqa: E402
import raw_inputs as R  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def game_folder(root):
    """A game folder as sessions leave it: the Chinese original, its unpacked copy, three English versions."""
    g = Path(root) / '火柴人密室逃脱'
    g.mkdir()
    with zipfile.ZipFile(g / '火柴人密室逃脱_中文原包.zip', 'w') as z:
        z.writestr('Game/assets/Main.js', 'cc.log("原版")')
    (g / '中文原版解压').mkdir()
    (g / '中文原版解压' / 'Main.js').write_text('cc.log("原版")')
    for v in ('v1', 'v2', 'v3'):
        (g / ('英化_' + v)).mkdir()
        (g / ('英化_' + v) / 'game.js').write_text(v)
    return g


def old_cleanup(g, keep):
    """The old way (火柴人密室逃脱): remove everything in the game folder except the newest version."""
    errors = []
    for p in list(Path(g).iterdir()):
        if p.name == keep:
            continue
        try:
            shutil.rmtree(p) if p.is_dir() else p.unlink()
        except OSError as error:
            errors.append(str(error))
    return errors


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4d-'))

    def tearDown(self):
        R.unlock_for_test_cleanup(self.tmp)
        shutil.rmtree(self.tmp, ignore_errors=True)


class RawInputs(Base):
    def test_old_way_deletes_the_original(self):
        g = game_folder(self.tmp)
        old_cleanup(g, '英化_v3')
        self.assertFalse((g / '火柴人密室逃脱_中文原包.zip').exists())     # the bug: nothing to compare with any more
        self.assertEqual(sorted(p.name for p in g.iterdir()), ['英化_v3'])

    @unittest.skipIf(os.name == 'nt' or (hasattr(os, 'geteuid') and os.geteuid() == 0), 'POSIX non-root read-only dirs')
    def test_kept_copy_survives_the_old_cleanup(self):
        g = game_folder(self.tmp)
        original = g / '火柴人密室逃脱_中文原包.zip'
        want = sha(original)
        r = R.keep(original, g)
        self.assertEqual(r['status'], 'kept')
        R.keep(g / '中文原版解压', g)
        errors = old_cleanup(g, '英化_v3')
        self.assertTrue(errors)                                       # rm -rf on _原始输入/ fails: read-only
        kept = g / R.RAW_DIR / original.name
        self.assertEqual(sha(kept), want)
        self.assertTrue((g / R.RAW_DIR / '中文原版解压' / 'Main.js').is_file())
        self.assertEqual(R.verify(g)['status'], 'ok')

    def test_keep_twice_is_one_copy(self):
        g = game_folder(self.tmp)
        R.keep(g / '火柴人密室逃脱_中文原包.zip', g)
        self.assertEqual(R.keep(g / '火柴人密室逃脱_中文原包.zip', g)['status'], 'already_kept')
        self.assertEqual(len(R.read_record(g / R.RAW_DIR)['entries']), 1)

    def test_clean_old_versions_skips_the_original(self):
        g = game_folder(self.tmp)
        R.keep(g / '火柴人密室逃脱_中文原包.zip', g)
        old = [g / '火柴人密室逃脱_中文原包.zip', g / R.RAW_DIR, g / '英化_v1', g / '英化_v2']
        p = C.plan(g, old)
        self.assertEqual(sorted(Path(x).name for x in p['remove']), ['英化_v1', '英化_v2'])
        whys = {Path(s['path']).name: s['why'] for s in p['skipped']}
        self.assertIn('原始输入', whys[R.RAW_DIR])
        self.assertIn('原始输入', whys['火柴人密室逃脱_中文原包.zip'])      # same bytes as the kept copy
        done, errors = C.apply(p)
        self.assertEqual(errors, [])
        self.assertTrue((g / C.OLD_DIR / '英化_v1').is_dir())             # moved, not deleted
        self.assertTrue((g / '火柴人密室逃脱_中文原包.zip').is_file())
        self.assertEqual(R.verify(g)['status'], 'ok')
        self.assertTrue(R.is_protected(g))                                # the game folder holds _原始输入/


def install(root, files, revision='2026-11-05.english-simple.11.14'):
    """An installed skill folder with its release PROVENANCE.json."""
    folder = Path(root) / 'remake-core'
    for rel, text in files.items():
        (folder / rel).parent.mkdir(parents=True, exist_ok=True)
        (folder / rel).write_text(text)
    prov = {'schema': I.PROV_SCHEMA, 'revision': revision, 'skill': 'remake-core',
            'files': [{'path': rel, 'sha256': sha(folder / rel), 'bytes': len(text.encode())} for rel, text in files.items()]}
    (folder / 'PROVENANCE.json').write_text(json.dumps(prov))
    return folder


class InstalledSkill(Base):
    FILES = {'SKILL.md': '# remake-core\n', 'scripts/art_check.py': 'print(1)\n'}

    def test_clean_install(self):
        install(self.tmp / 'skills', self.FILES)
        self.assertEqual(I.check(self.tmp / 'skills')['status'], 'clean')

    def test_direct_edit_is_reported(self):
        folder = install(self.tmp / 'skills', self.FILES)
        (folder / 'scripts' / 'art_check.py').write_text('print(2)  # 游戏会话直接改\n')
        (folder / 'scripts' / '__pycache__').mkdir()
        (folder / 'scripts' / '__pycache__' / 'x.pyc').write_bytes(b'\0')
        (folder / 'scripts' / 'reviewed_resource_profiles.json').write_text('{}')    # project QA registration
        r = I.check(self.tmp / 'skills')
        self.assertEqual(r['status'], 'modified')
        self.assertEqual(r['modified'], ['remake-core/scripts/art_check.py'])
        self.assertIn('已装 Skill 被改过，请走补丁', r['line'])
        self.assertEqual(r['added'], ['remake-core/scripts/reviewed_resource_profiles.json'])  # listed, not "changed"
        self.assertEqual(sha(folder / 'scripts' / 'art_check.py'),
                         hashlib.sha256('print(2)  # 游戏会话直接改\n'.encode()).hexdigest())  # hint only: not restored

    def test_missing_file_is_reported(self):
        folder = install(self.tmp / 'skills', self.FILES)
        (folder / 'SKILL.md').unlink()
        self.assertEqual(I.check(self.tmp / 'skills')['missing'], ['remake-core/SKILL.md'])

    def test_distribution_manifest_is_the_same_record(self):
        folder = install(self.tmp / 'skills', self.FILES)
        manifest = {'schema': I.MANIFEST_SCHEMA, 'revision': 'x', 'skills': ['remake-core'],
                    'files': {'remake-core/' + rel: {'sha256': sha(folder / rel), 'size': 1} for rel in self.FILES}}
        (self.tmp / 'distribution-manifest.json').write_text(json.dumps(manifest))
        self.assertEqual(I.check(self.tmp / 'skills', self.tmp / 'distribution-manifest.json')['status'], 'clean')
        (folder / 'SKILL.md').write_text('changed')
        self.assertEqual(I.check(self.tmp / 'skills', self.tmp / 'distribution-manifest.json')['modified'],
                         ['remake-core/SKILL.md'])

    def test_maintenance_tree_is_not_reported(self):
        root = self.tmp / '_内部' / 'maintenance' / 'tree'
        install(root, self.FILES)
        self.assertEqual(I.check(root)['status'], 'dev_tree')

    def test_cli_exit_is_always_0(self):
        folder = install(self.tmp / 'skills', self.FILES)
        (folder / 'SKILL.md').write_text('changed')
        self.assertEqual(I.main(['--root', str(self.tmp / 'skills')]), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
