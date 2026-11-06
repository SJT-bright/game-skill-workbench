#!/usr/bin/env python3
"""生成时预防 R4Q2 (广告skill 11-05, two notes on prompt_name_guard.py).
  1 common_word  project "Wheel": 'lucky wheel with 8 segments, no text' passes (old code: blocked);
                 'title logo reading "WHEEL"' and '"WHEEL" written on the rim' are reported
  2 multi_word   project "MergeShot2048" is still matched as a substring anywhere ("merge shot 2048 hero")
  3 refs         --refs list with ref/title_banner.png (or role "title logo") is reported; hero.png is not (old: no --refs)
Run: python3 test_prompt_name_guard_refs.py
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prompt_name_guard as G  # noqa: E402


class PromptNameGuardRefsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def project(self, name):
        p = self.tmp / name
        p.mkdir()
        return p

    def test_common_word_only_when_drawn_as_words(self):
        names = G.game_names(self.project('Wheel'))
        self.assertIn('Wheel', names)
        self.assertEqual(G.scan('lucky wheel with 8 segments, no text', names), [])
        self.assertEqual(G.scan('a wheel spinning on a wooden table', names), [])
        kinds = [h['kind'] for h in G.scan('title logo reading "WHEEL"', names)]
        self.assertIn('game_name_in_prompt', kinds)
        self.assertIn('game_name_in_prompt', [h['kind'] for h in G.scan('"WHEEL" written on the rim', names)])

    def test_multi_word_name_still_substring(self):
        names = G.game_names(self.project('MergeShot2048'))
        self.assertEqual([h['kind'] for h in G.scan('merge shot 2048 hero on a soft background', names)],
                         ['game_name_in_prompt'])

    def test_refs(self):
        refs = self.tmp / 'refs.json'
        refs.write_text(json.dumps(['ref/hero.png', 'ref/title_banner.png',
                                    {'path': 'ref/home_01.png', 'role': 'title logo of the original'}]))
        hits = G.scan_refs([refs])
        self.assertEqual(sorted(h['ref'] for h in hits), ['ref/home_01.png', 'ref/title_banner.png'])
        rc = G.main(['--project', str(self.project('Wheel')), '--refs', str(refs)])
        self.assertEqual(rc, 1)
        ok = self.tmp / 'ok.txt'
        ok.write_text('ref/hero.png\nlogos_dir/scene.png\n')
        self.assertEqual(G.main(['--project', str(self.tmp / 'Wheel'), '--refs', str(ok)]), 0)


if __name__ == '__main__':
    unittest.main()
