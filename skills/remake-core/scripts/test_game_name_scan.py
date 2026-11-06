#!/usr/bin/env python3
"""生成时预防 R4O1 (Saul 2026-11-05: no game name in the game): tiktok_finalize_steps/game_name_scan.py.

Sample taken from the census: 园丁守花 GardenGuard prefabs carry a Label "GARDEN GUARD" (calibration 2026-11-05).
  1 names     glossary game_name, projectname, package.json name, folder names (CamelCase split, 新289_ prefix,
              _v3 suffix, a Chinese run); default names such as my-project are ignored
  2 block     a new remake game begun by init after 2026-11-05 with the name in a prefab Label -> block
  3 warn      the same game begun 2026-10-31 (in progress) -> warning; English (localize) -> warning
  4 legacy    legacy -> not checked
  5 copy      the English column of docs/copy/copy-table.csv is read; "Nim's Night Jars" matches NimsNightJars
  6 allow     glossary game_name_ok lets one text through; a short word ("Jar") never matches
  7 wired     game_name_scan is in SOURCE_STEPS and SYNC_SOURCE_STEPS
Run: python3 test_game_name_scan.py
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402

PREFAB = ('[{"__type__": "cc.Prefab"}, {"__type__": "cc.Node", "_name": "Title"},'
          ' {"__type__": "cc.Label", "_N$string": "GARDEN GUARD", "_string": "GARDEN GUARD"},'
          ' {"__type__": "cc.Label", "_string": "PLAY"}]')


def project(tmp, folder='新291_GardenGuard', prefab=PREFAB, created='2026-11-05T09:00:00-0800', by='init',
            board='remake'):
    root = Path(tmp) / folder / 'GardenGuard'
    (root / 'assets' / 'prefab').mkdir(parents=True)
    (root / 'assets' / 'prefab' / 'Home.prefab').write_text(prefab, encoding='utf-8')
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}', encoding='utf-8')
    P.write_marker(root, board, '2.0', reason=by)
    m = json.loads((root / P.MARKER).read_text(encoding='utf-8'))
    m['created'] = created
    (root / P.MARKER).write_text(json.dumps(m), encoding='utf-8')
    return root


def run(root, policy='new', board='remake'):
    from tiktok_finalize_steps import game_name_scan as G
    return G.apply(T.Ctx('source', root, policy=policy, board=board))


class GameNameScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_names(self):
        from tiktok_finalize_steps import game_name_scan as G
        root = project(self.tmp, folder='新289_NimsNightJars_v3')
        (root / 'docs' / 'copy').mkdir(parents=True)
        (root / 'docs/copy/glossary.json').write_text(json.dumps({'game_name': ['Nim\'s Night Jars', '尼姆夜罐子']}))
        (root / 'package.json').write_text('{"name": "my-project"}')
        (root / 'project.config.json').write_text('{"projectname": "Balloon Run"}')
        names = [n for n, _ in G.names_of(root)]
        self.assertEqual(names[:3], ["Nim's Night Jars", '尼姆夜罐子', 'Balloon Run'])
        self.assertIn('Garden Guard', names)
        self.assertNotIn('my-project', names)
        self.assertIn('珊瑚守卫', G._folder_names('珊瑚守卫-ReefGuard（自制）'))

    def test_new_game_after_rule_blocks(self):
        r = run(project(self.tmp))
        self.assertEqual([b['id'] for b in r['blocks']], ['K_game_name_text'])
        self.assertIn('GARDEN GUARD', r['blocks'][0]['message'])
        self.assertEqual(r['state'], 'conflict')

    def test_in_progress_and_english_warn(self):
        r = run(project(self.tmp, created='2026-10-31T19:12:14-0700'))
        self.assertEqual(r['blocks'], [])
        self.assertEqual([w['id'] for w in r['warnings']], ['K_W_game_name_text'])
        # R4Q2: an English game begun after the rule blocks now; one begun before it still warns
        r = run(project(tempfile.mkdtemp(dir=self.tmp), board='localize'), board='localize')
        self.assertEqual((len(r['blocks']), len(r['warnings'])), (1, 0))
        r = run(project(tempfile.mkdtemp(dir=self.tmp), board='localize', created='2026-11-04T23:59:00-0800'),
                board='localize')
        self.assertEqual((len(r['blocks']), len(r['warnings'])), (0, 1))
        r = run(project(tempfile.mkdtemp(dir=self.tmp), by='adopt'))
        self.assertEqual((len(r['blocks']), len(r['warnings'])), (0, 1))

    def test_legacy_not_checked(self):
        r = run(project(self.tmp), policy='legacy')
        self.assertEqual((r['blocks'], r['warnings']), ([], []))
        self.assertIn('not checked', r['info'][0])

    def test_copy_table_english_column(self):
        root = project(self.tmp, folder='新289_NimsNightJars', prefab='[{"__type__": "cc.Prefab"}]')
        (root / 'docs' / 'copy').mkdir(parents=True)
        (root / 'docs/copy/copy-table.csv').write_text('zh,en\n返回,Back\n尼姆夜罐子,Nim\'s Night Jars\n',
                                                     encoding='utf-8')
        r = run(root)
        self.assertEqual(len(r['blocks']), 1)
        self.assertIn('copy-table.csv line 3', r['blocks'][0]['message'])

    def test_allow_and_short_words(self):
        root = project(self.tmp, prefab=PREFAB.replace('GARDEN GUARD', 'Garden Guard Gus'))
        (root / 'docs' / 'copy').mkdir(parents=True)
        (root / 'docs/copy/glossary.json').write_text(json.dumps({'game_name_ok': ['Garden Guard Gus']}))
        self.assertEqual(run(root)['blocks'], [])
        root = project(tempfile.mkdtemp(dir=self.tmp), folder='新291_Jar', prefab=PREFAB.replace('GARDEN GUARD', 'Jar'))
        self.assertEqual([n for n, _ in __import__('tiktok_finalize_steps.game_name_scan',
                                                   fromlist=['x']).names_of(root)], ['Garden Guard'])

    def test_wired(self):
        self.assertIn('game_name_scan', T.SOURCE_STEPS)
        self.assertIn('game_name_scan', F.SYNC_SOURCE_STEPS)


if __name__ == '__main__':
    unittest.main()
