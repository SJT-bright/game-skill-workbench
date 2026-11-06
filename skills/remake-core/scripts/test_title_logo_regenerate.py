#!/usr/bin/env python3
"""生成时预防 R4Q2 (补查3 第 2 组; Saul 2026-11-05: no game name in the game): audit_new_english_images --make-list
puts the original title logo on "regenerate" (hero / pattern / scene, no name), not only on the translate list.
Census: 火箭三消 / 方块收割者 / 弹球传奇 kept a worded title picture on the home page (ROCKET BLOCKS, CUBE HARVESTER,
BALL MASTER) because round 1 translated the Chinese logo into an English one.
  1 by_name    a worded picture named Ball_Logo.png -> regenerate with the no-name prompt, replace row marked
  2 by_scene   the widest worded picture (720x240) used by Home.fire -> regenerate; a 200x80 worded button on the same
               scene and a worded picture used only by Game.fire -> not listed
  3 make_list  make_list() carries the rows into chinese_scan.regenerate (old code: none)
Run: python3 test_title_logo_regenerate.py
"""
import json
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_new_english_images as A  # noqa: E402


def png(w, h):
    return b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\rIHDR' + struct.pack('>II', w, h) + b'\x08\x06\x00\x00\x00' + b'\x00' * 8


def project(tmp):
    root = Path(tmp) / 'RocketMatch'
    tex = root / 'assets' / 'tex'
    tex.mkdir(parents=True)
    pics = {'Ball_Logo.png': (600, 300, 'u-logo'), 'home_top.png': (720, 240, 'u-top'), 'btn_start.png': (200, 80, 'u-btn'),
            'game_banner_x.png': (100, 100, 'u-x'), 'level_tip.png': (800, 200, 'u-tip')}
    for name, (w, h, u) in pics.items():
        (tex / name).write_bytes(png(w, h))
        (tex / (name + '.meta')).write_text(json.dumps({'uuid': u, 'subMetas': {name[:-4]: {'uuid': u + '-sf'}}}))
    scenes = root / 'assets' / 'scene'
    scenes.mkdir()
    (scenes / 'Home.fire').write_text('[{"_spriteFrame": {"__uuid__": "u-top-sf"}}, {"_spriteFrame": {"__uuid__": "u-btn-sf"}}]')
    (scenes / 'Game.fire').write_text('[{"_spriteFrame": {"__uuid__": "u-tip-sf"}}]')
    return root


def scan_rows():
    return {'replace': [{'kind': 'image', 'file': 'assets/tex/%s' % n} for n in
                        ('Ball_Logo.png', 'home_top.png', 'btn_start.png', 'level_tip.png')],
            'manual_review': [], 'regenerate': []}


class TitleLogoRegenerateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_by_name_and_scene(self):
        root, scan = project(self.tmp), scan_rows()
        rows = A.title_logos(root, scan)
        self.assertEqual(sorted(r['file'] for r in rows), ['assets/tex/Ball_Logo.png', 'assets/tex/home_top.png'])
        self.assertTrue(all('no game name' in r['prompt'] for r in rows))
        marked = {r['file'] for r in scan['replace'] if r.get('regenerate_instead') == 'title_logo'}
        self.assertEqual(marked, {'assets/tex/Ball_Logo.png', 'assets/tex/home_top.png'})

    def test_make_list_carries_rows(self):
        root = project(self.tmp)
        old_scan, old_flat = A.scan_chinese, A.flat_panels
        A.scan_chinese = lambda project, ocr='auto': scan_rows()
        A.flat_panels = lambda project: []
        try:
            doc = A.make_list(root)
        finally:
            A.scan_chinese, A.flat_panels = old_scan, old_flat
        files = [r['file'] for r in doc['chinese_scan']['regenerate']]
        self.assertIn('assets/tex/home_top.png', files)
        self.assertIn('assets/tex/Ball_Logo.png', files)


if __name__ == '__main__':
    unittest.main()
