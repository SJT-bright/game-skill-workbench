#!/usr/bin/env python3
"""v7.8 (总表 B32 d): check tools that are not the released / installed ones are reported as 「改过的工具」 and get a
feedback draft (tool_identity.py; check_package.check() and its command, build_checked_zip, runtime_regression's command).
Bad: 企鹅雪道's shape (the ad-regression tools copied into the game's qa/ folder and edited), an installed file edited in
place, an added file. Good: the installed copy, a pristine release copy elsewhere, the maintenance tree (dev_tree).
Drafts: new file only, the same changes on one day once, a taken name gets _2. Run: python3 -B test_tool_identity.py
"""
import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import os
import unittest
from unittest.mock import patch

import tool_identity as T

FILES = {'package-check/scripts/check_package.py': 'print("check")\n',
         'package-check/scripts/ad_regression.py': 'print("ad")\n',
         'package-check/scripts/ad_regression/cases.mjs': 'const cam = cams[0];\nexport default cam;\n',
         'package-check/scripts/runtime_regression/lib.mjs': 'export const x = 1;\n'}
SHARED = {'scripts/verify_native_zip.py': 'print("verify")\n', 'scripts/package_gates/__init__.py': 'GATES = []\n'}


def write_skills(root, files=FILES, shared=SHARED, revision='2026-10-30.remake-v7.8'):
    for skill, table in (('cocos-game-check', files), ('remake-core', shared)):
        for rel, text in table.items():
            p = root / skill / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding='utf-8')
        (root / skill / 'PROVENANCE.json').write_text(json.dumps({'revision': revision, 'files': [
            {'path': rel, 'sha256': hashlib.sha256(text.encode()).hexdigest()} for rel, text in table.items()]}))
    return root / 'cocos-game-check' / 'package-check' / 'scripts'


class Identity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='tool identity ')
        self.root = Path(self.temp.name)
        self.installed = write_skills(self.root / 'install')
        self.roots = [self.root / 'install']

    def tearDown(self):
        self.temp.cleanup()

    def test_installed_and_pristine_copy_are_clean(self):
        ident = T.identity(self.installed, self.roots)
        self.assertEqual((ident['status'], ident['location'], ident['checked']), ('clean', 'installed', 6))
        copy = write_skills(self.root / 'unzipped release')
        self.assertEqual(T.identity(copy, self.roots)['status'], 'clean')
        self.assertEqual(T.identity(copy, self.roots)['location'], 'elsewhere')

    def test_penguin_shape_loose_edited_copy(self):
        qa = self.root / 'Game' / 'qa' / 'ad_regression_tool_fix'
        (qa / 'ad_regression').mkdir(parents=True)
        (qa / 'ad_regression.py').write_text(FILES['package-check/scripts/ad_regression.py'])
        (qa / 'ad_regression' / 'cases.mjs').write_text('const cam = canvasCamera(n);\nexport default cam;\n')
        (qa / 'ad_regression' / 'mine.mjs').write_text('// added\n')
        ident = T.identity(qa, self.roots)
        self.assertEqual((ident['status'], ident['location']), ('modified', 'elsewhere'))
        kinds = {m['rel']: m['kind'] for m in ident['modified']}
        self.assertEqual(kinds, {'package-check/scripts/ad_regression/cases.mjs': 'changed',
                                 'package-check/scripts/ad_regression/mine.mjs': 'added'})
        self.assertIn('用的不是安装目录里的工具', ident['summary'][0])

    def test_installed_file_edited_in_place(self):
        (self.installed / 'ad_regression' / 'cases.mjs').write_text('edited\n')
        ident = T.identity(self.installed, self.roots)
        self.assertEqual(ident['status'], 'modified')
        self.assertEqual([m['rel'] for m in ident['modified']], ['package-check/scripts/ad_regression/cases.mjs'])
        (self.root / 'install' / 'remake-core' / 'scripts' / 'package_gates' / '__init__.py').write_text('GATES = [1]\n')
        self.assertIn('scripts/package_gates/__init__.py', [m['rel'] for m in T.identity(self.installed, self.roots)['modified']])

    def test_dev_tree_and_nothing_to_compare(self):
        dev = write_skills(self.root / '_内部' / 'maintenance' / 'work')
        (dev / 'check_package.py').write_text('changed in the Skill work tree\n')
        self.assertEqual(T.identity(dev, self.roots)['status'], 'dev_tree')
        lone = self.root / 'lone'
        lone.mkdir()
        (lone / 'check_package.py').write_text('x\n')
        self.assertEqual(T.identity(lone, [])['status'], 'unknown')
        self.assertEqual(T.identity(T.HERE)['status'], 'dev_tree')     # this work tree itself

    def test_draft_written_once_never_overwritten(self):
        copy = write_skills(self.root / 'Game' / 'qa' / 'skill copy')
        (copy / 'ad_regression' / 'cases.mjs').write_text('const cam = canvasCamera(n);\nexport default cam;\n')
        ident = T.identity(copy, self.roots)
        out = self.root / '！Skill更新'
        day = datetime.date(2026, 10, 30)
        first = T.write_draft(ident, '企鹅雪道', out, day)
        self.assertEqual(first.name, '反馈草稿_改过的工具_企鹅雪道_20261030.md')
        text = first.read_text(encoding='utf-8')
        for want in ('cocos-game-check/package-check/scripts/ad_regression/cases.mjs', '```diff', '+const cam = canvasCamera(n);',
                     '-const cam = cams[0];', '指纹：'):
            self.assertIn(want, text)
        self.assertIsNone(T.write_draft(ident, '企鹅雪道', out, day))             # same changes, same day: once
        (copy / 'runtime_regression' / 'lib.mjs').write_text('export const x = 2;\n')
        second = T.write_draft(T.identity(copy, self.roots), '企鹅雪道', out, day)
        self.assertEqual(second.name, '反馈草稿_改过的工具_企鹅雪道_20261030_2.md')
        self.assertEqual(first.read_text(encoding='utf-8'), text)                 # the first one is untouched
        self.assertIsNone(T.write_draft(T.identity(write_skills(self.root / 'clean'), self.roots), 'x', out, day))

    def test_install_roots_env(self):
        with patch.dict('os.environ', {T.ENV_ROOTS: str(self.root / 'install')}):
            self.assertEqual(T.install_roots(), [(self.root / 'install').resolve()])


class Wiring(unittest.TestCase):
    """check_package.check() carries tool_identity and lists modified tools; its command and the writer write drafts."""

    def test_check_reports_modified_tools(self):
        import check_package
        from test_package_checks import fixture, runtime_patch, APP
        modified = {'status': 'modified', 'summary': ['cocos-game-check/package-check/scripts/ad_regression/cases.mjs 改过'],
                    'modified': [{'rel': 'x'}]}
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'Game.zip'
            check_package.write_archive(archive, fixture())
            with runtime_patch():
                plain = check_package.check(archive, APP)
                with patch('check_package.tools_in_use', return_value=modified):
                    changed = check_package.check(archive, APP)
        self.assertEqual(plain['tool_identity']['status'], 'dev_tree')              # the work tree: never reported
        self.assertNotIn('modified_tools', plain)
        self.assertEqual(changed['modified_tools'], modified['summary'])
        self.assertIn('改过的工具: ' + modified['summary'][0], changed['warnings'])
        with tempfile.TemporaryDirectory() as out, patch.dict('os.environ', {T.ENV_FEEDBACK: out}):
            self.assertIsNone(check_package.feedback_draft({'status': 'clean'}, 'Game'))
            ident = {'status': 'modified', 'here': '/x', 'location': 'elsewhere', 'release': None, 'summary': ['a'],
                     'modified': [{'file': '/x/a.mjs', 'skill': 'cocos-game-check', 'rel': 'package-check/scripts/a.mjs',
                                   'kind': 'added', 'sha256': '0' * 64, 'release_sha256': None, 'installed': []}]}
            path = check_package.feedback_draft(ident, 'Game')
            self.assertTrue(Path(path).is_file() and Path(path).parent == Path(out))
        source = Path(check_package.__file__).read_text(encoding='utf-8')
        self.assertIn("result['tool_identity'] = tools_in_use()", source)
        self.assertIn("result['modified_tools'] = result['tool_identity']['summary']", source)
        writer = (Path(check_package.__file__).parent / 'build_checked_zip.py').read_text(encoding='utf-8')
        self.assertIn("package_checks.feedback_draft(result.get('tool_identity')", writer)



class ThrowawayCopies(unittest.TestCase):
    """10-30 23:01: tests run on a selftest snapshot in ~/.kiro/crew/scratch wrote three drafts into ！Skill更新/."""

    def test_scratch_and_temp_copies_write_no_default_draft(self):
        ident = {'status': 'modified', 'here': '/Users/x' + T.THROWAWAY_MARKS[0] + 'w96/snap/remake-tree/cocos-game-check/'
                 'package-check/scripts', 'location': 'elsewhere', 'modified': [], 'release': None}
        with tempfile.TemporaryDirectory() as fake_feedback, patch.object(T, 'FEEDBACK_DIR', Path(fake_feedback)), \
                patch.dict('os.environ', {}, clear=False):
            os.environ.pop(T.ENV_FEEDBACK, None)
            self.assertTrue(T.throwaway(ident['here']))
            self.assertIsNone(T.write_draft(ident, 'pkg'))
            with tempfile.TemporaryDirectory() as tmp_copy:
                self.assertTrue(T.throwaway(tmp_copy))
                self.assertIsNone(T.write_draft(dict(ident, here=tmp_copy), 'pkg'))
            self.assertEqual(list(Path(fake_feedback).iterdir()), [])
            with tempfile.TemporaryDirectory() as out:                   # an explicit folder still gets one
                self.assertIsNotNone(T.write_draft(ident, 'pkg', out))

    def test_game_folder_copies_still_write_a_draft(self):
        self.assertFalse(T.throwaway('/Users/x/Downloads/game/qa/ad_regression_tool_fix'))

if __name__ == '__main__':
    unittest.main(verbosity=1)
