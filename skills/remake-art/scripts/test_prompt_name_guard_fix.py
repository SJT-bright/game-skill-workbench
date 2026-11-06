#!/usr/bin/env python3
"""生成时预防 R4R1 (Saul 2026-11-05 09:4x: 发现问题直接处理): prompt_name_guard --fix rewrites the prompt.

  1 json      prompts.json with 'title logo reading "BALL MASTER"' and "Ball Master game name banner" ->
              prompts.fixed.json: no name, no title / logo request, "no text"; ids and paths untouched; exit 0
  2 text      --text with a one-word name ("WHEEL logo") and a plain wheel prompt that must stay as it is
  3 refs      a reference list with title_logo.png -> .fixed list without it, exit 0
  4 unfixable a single title picture given as --refs -> exit 1
Run: python3 test_prompt_name_guard_fix.py   (old code: --fix is an unknown option -> exit 2)
"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prompt_name_guard as G  # noqa: E402


def cli(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = G.main([str(a) for a in args])
        except SystemExit as e:
            return e.code, None
    return code, json.loads(buf.getvalue())


class PromptFixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_json_prompts_rewritten(self):
        root = self.tmp / 'BallMaster-English'
        (root / 'docs' / 'art').mkdir(parents=True)
        f = root / 'docs/art/prompts.json'
        f.write_text(json.dumps({'home_title': {
            'prompt': 'Cartoon title logo reading "BALL MASTER" with a bouncing ball, glossy',
            'out': 'assets/resources/english/Ball_Logo.png'},
            'banner': {'prompt': 'Ball Master game name banner for the loading page'},
            'play': {'prompt': 'PLAY button word picture, glossy orange'}}))
        code, out = cli('--project', root, '--file', f)
        self.assertEqual(code, 1)
        code, out = cli('--project', root, '--file', f, '--fix')
        self.assertEqual(code, 0, out)
        fixed = json.loads((root / 'docs/art/prompts.fixed.json').read_text(encoding='utf-8'))
        p1, p2 = fixed['home_title']['prompt'], fixed['banner']['prompt']
        for p in (p1, p2):
            self.assertNotIn('ball master', p.lower())
            self.assertNotIn('logo', p.lower())
            self.assertIn('no text', p)
            self.assertIn('main character', p)
        self.assertIn('bouncing ball', p1)
        self.assertEqual(fixed['home_title']['out'], 'assets/resources/english/Ball_Logo.png')
        self.assertEqual(fixed['play']['prompt'], 'PLAY button word picture, glossy orange')
        self.assertTrue(json.loads(f.read_text())['home_title']['prompt'].startswith('Cartoon title logo'))

    def test_text_single_word_name(self):
        root = self.tmp / 'Wheel'
        root.mkdir()
        code, out = cli('--project', root, '--fix', '--text', 'WHEEL logo, golden letters, festive',
                        '--text', 'lucky wheel with 8 segments, no text')
        self.assertEqual(code, 0, out)
        t1, t2 = out['fixed_texts']
        self.assertNotIn('WHEEL', t1)
        self.assertIn('no text', t1)
        self.assertEqual(t2, 'lucky wheel with 8 segments, no text')

    def test_refs_list_dropped(self):
        root = self.tmp / 'Game'
        root.mkdir()
        lst = self.tmp / 'refs.txt'
        lst.write_text('assets/hero.png\nassets/title_logo.png\nassets/bg.png\n')
        code, out = cli('--project', root, '--refs', lst, '--fix')
        self.assertEqual(code, 0, out)
        self.assertEqual((self.tmp / 'refs.fixed.txt').read_text(), 'assets/hero.png\nassets/bg.png\n')

    def test_single_title_ref_cannot_be_fixed(self):
        root = self.tmp / 'Game'
        root.mkdir()
        code, out = cli('--project', root, '--refs', self.tmp / 'title.png', '--fix')
        self.assertEqual(code, 1)


if __name__ == '__main__':
    unittest.main()
