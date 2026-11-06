#!/usr/bin/env python3
"""生成时预防 R4Q2 (补查3 第 2 组; Saul 2026-11-05: no game name in the game): names drawn in pictures.

Census: 火箭三消 RocketMatch-English kept a home title picture "ROCKET BLOCKS", 方块收割者 CubeHarvest-English kept
logo.png "CUBE HARVESTER" (OCR read "CUBE HARVESTEER"); game_name_scan read only Label text and only warned English
games. Samples copy those receipts' shape (chinese-audit audit.json rows, review.py receipt.json + result.json).
  1 ocr_row    an English game begun 2026-11-05 by init, glossary game_name "Rocket Blocks", audit.json row of the
               home picture with ocr_text ["ROCKET", "BLOCKS"] -> block K_game_name_text (old code: no hit)
  2 stale      the same row after the picture was replaced (file bytes differ from file_sha256) -> no hit
  3 before     the same game begun 2026-11-04 -> warning only; legacy -> not checked
  4 review     a review.py receipt (image_sha256 of a project file, result.json observations "CUBE HARVESTEER")
               in a project folder CubeHarvest -> hit
Run: python3 test_game_name_in_pictures.py
"""
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 40


def project(tmp, folder='RocketMatch-English', created='2026-11-05T02:45:26-0800', name='Rocket Blocks'):
    root = Path(tmp) / folder
    (root / 'assets' / 'resources' / 'english').mkdir(parents=True)
    (root / 'assets' / 'prefab').mkdir(parents=True)
    (root / 'assets' / 'prefab' / 'Home.prefab').write_text('[{"__type__": "cc.Label", "_string": "PLAY"}]')
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    P.write_marker(root, 'localize', '2.0', reason='init')
    m = json.loads((root / P.MARKER).read_text(encoding='utf-8'))
    m['created'] = created
    (root / P.MARKER).write_text(json.dumps(m))
    if name:
        (root / 'docs' / 'copy').mkdir(parents=True)
        (root / 'docs/copy/glossary.json').write_text(json.dumps({'game_name': [name, '火箭三消']}))
    return root


def add_ocr_row(root, rel='assets/resources/english/home_title.png', text=('ROCKET', 'BLOCKS')):
    p = root / rel
    p.write_bytes(PNG)
    d = root / 'docs' / 'english' / 'chinese-audit'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'audit.json').write_text(json.dumps({'items': [
        {'kind': 'image', 'file': rel, 'file_sha256': hashlib.sha256(PNG).hexdigest(), 'ocr_text': list(text)},
        {'kind': 'text', 'file': 'assets/prefab/Home.prefab', 'text': 'PLAY'}]}))
    return p


def run(root, policy='new'):
    from tiktok_finalize_steps import game_name_scan as G
    return G.apply(T.Ctx('source', root, policy=policy, board='localize'))


class GameNameInPicturesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ocr_row_blocks_new_english_game(self):
        root = project(self.tmp)
        add_ocr_row(root)
        r = run(root)
        self.assertEqual([b['id'] for b in r['blocks']], ['K_game_name_text'])
        self.assertIn('home_title.png', r['blocks'][0]['message'])
        self.assertIn('chinese-audit OCR', r['blocks'][0]['message'])

    def test_stale_row_ignored(self):
        root = project(self.tmp)
        add_ocr_row(root).write_bytes(PNG + b'new art')
        r = run(root)
        self.assertEqual((r['blocks'], r['warnings']), ([], []))

    def test_before_rule_warns_legacy_skips(self):
        root = project(self.tmp, created='2026-11-04T20:00:00-0800')
        add_ocr_row(root)
        r = run(root)
        self.assertEqual((len(r['blocks']), len(r['warnings'])), (0, 1))
        self.assertEqual(run(root, policy='legacy')['warnings'], [])

    def test_review_receipt(self):
        root = project(self.tmp, folder='CubeHarvest-English', name=None)
        img = root / 'assets' / 'resources' / 'english' / 'logo.png'
        img.write_bytes(PNG)
        out = root / 'docs' / 'english' / 'grok' / 'logo-review'
        out.mkdir(parents=True)
        (out / 'receipt.json').write_text(json.dumps({'image_path': str(img), 'purpose': 'literal_transcription',
                                                      'image_sha256': hashlib.sha256(PNG).hexdigest()}))
        (out / 'result.json').write_text(json.dumps({'status': 'pass', 'observations': ['CUBE HARVESTEER'],
                                                     'issues': [], 'uncertainties': []}))
        r = run(root)
        self.assertEqual(len(r['blocks']), 1)
        self.assertIn('logo.png', r['blocks'][0]['message'])


if __name__ == '__main__':
    unittest.main()
