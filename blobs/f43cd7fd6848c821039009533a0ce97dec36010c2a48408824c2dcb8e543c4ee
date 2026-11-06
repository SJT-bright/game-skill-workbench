#!/usr/bin/env python3
"""生成时预防 R4Q5 (补查3 第 5 组 奔跑吧巨人): platform-kit/tools/check_kit_project.py foreign_config_findings.

  1 shared   the kit template's shared test app (Saul 2026-10-29) with an own gameId -> clean
  2 copied   appId and ad unit of another game on this machine (--peers) -> errors, its gameId -> warning (old: nothing)
  3 unknown  ids that are neither shared nor recorded nor seen elsewhere -> warning; recorded in
             docs/platform/platform_ids.json -> clean
Run: python3 test_platform_ids_foreign.py
"""
import importlib.util
import shutil
import tempfile
import unittest
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / 'assets' / 'platform-kit' / 'tools' / 'check_kit_project.py'
TEMPLATE = (HERE.parent / 'assets' / 'platform-kit' / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').read_text(
    encoding='utf-8')
spec = importlib.util.spec_from_file_location('check_kit_project', TOOL)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def config(game, app=None, ad=None):
    t = TEMPLATE.replace("gameId: 'change-me'", "gameId: '%s'" % game)
    if app:
        t = t.replace("appId: '7683427172773644296'", "appId: '%s'" % app)
    if ad:
        t = t.replace("ad7683064432721709074", ad)
    return t


def game(root, name, text):
    d = Path(root) / name / 'assets' / 'tiktok-platform'
    d.mkdir(parents=True)
    (d / 'PlatformConfig.js').write_text(text, encoding='utf-8')
    return d.parents[1]


class ForeignIds(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='r4q5ids-')
        self.peers = Path(self.tmp) / 'games'
        game(self.peers, 'SnakeVSBlock', config('snakevsblock', app='7600000000000000001', ad='ad7600000000000000009'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_shared_test_app_clean(self):
        proj = game(self.tmp, 'GiantRush', config('giantrush'))
        self.assertEqual(C.foreign_config_findings(proj, config('giantrush'), [self.peers]), ([], []))

    def test_2_copied_from_other_game(self):
        text = config('snakevsblock', app='7600000000000000001', ad='ad7600000000000000009')
        proj = game(self.tmp, 'GiantRush', text)
        errors, warnings = C.foreign_config_findings(proj, text, [self.peers])
        self.assertEqual(len(errors), 2, errors)      # appId, ad unit
        self.assertTrue(any('save key' in w for w in warnings))

    def test_3_unknown_warns_recorded_clean(self):
        text = config('giantrush', app='7611111111111111111')
        proj = game(self.tmp, 'GiantRush', text)
        errors, warnings = C.foreign_config_findings(proj, text, [self.peers])
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        (proj / 'docs' / 'platform').mkdir(parents=True)
        (proj / 'docs' / 'platform' / 'platform_ids.json').write_text(
            json.dumps({'appId': '7611111111111111111', 'source': 'TikTok console 2026-11-05'}), encoding='utf-8')
        self.assertEqual(C.foreign_config_findings(proj, text, [self.peers]), ([], []))


if __name__ == '__main__':
    unittest.main()
