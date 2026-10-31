#!/usr/bin/env python3
"""总表 H12: make_greybox_reference.py turns base art into numbered flat grey blocks; none of the base's colours
reach the picture sent to the image model. Needs Pillow (skipped without it). Run: python3 test_greybox_reference.py"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None

ALLOWED = {(176, 176, 176), (140, 140, 140), (204, 204, 204), (244, 244, 244), (32, 32, 32)}


def run(*args):
    r = subprocess.run([sys.executable, '-B', str(HERE / 'make_greybox_reference.py')] + [str(a) for a in args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


@unittest.skipIf(Image is None, 'Pillow missing')
class Greybox(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix='greybox_'))
        self.addCleanup(shutil.rmtree, self.d, True)

    def atlas(self):
        img = Image.new('RGBA', (400, 200), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dr.ellipse([10, 10, 150, 150], fill=(255, 40, 40, 255), outline=(255, 255, 255, 255), width=6)  # red + outline
        dr.rectangle([220, 30, 380, 120], fill=(30, 200, 90, 255))
        dr.rectangle([300, 170, 302, 172], fill=(0, 0, 255, 255))                                     # a speck
        p = self.d / 'atlas.png'
        img.save(p)
        return p

    def colours(self, path):
        im = Image.open(path).convert('RGB')
        return {c for _n, c in im.getcolors(1 << 20)}

    def test_atlas_pieces_become_numbered_grey_blocks(self):
        out = self.d / 'ref.png'
        code, _o, err = run('--image', self.atlas(), '--out', out)
        self.assertEqual(code, 0, err)
        legend = json.loads(Path(str(out) + '.json').read_text())
        self.assertEqual([i['n'] for i in legend['items']], [1, 2])          # the speck is ignored
        cols = self.colours(out)
        for base in ((255, 40, 40), (30, 200, 90), (255, 255, 255), (0, 0, 255)):
            self.assertNotIn(base, cols)
        main = {c for c in cols if all(abs(c[0] - c[k]) < 3 for k in (1, 2))}
        self.assertEqual(main, cols)                                         # only greys (number antialiasing too)

    def test_opaque_screenshot_is_refused(self):
        p = self.d / 'shot.png'
        Image.new('RGBA', (100, 100), (10, 120, 200, 255)).save(p)
        code, _o, err = run('--image', p, '--out', self.d / 'x.png')
        self.assertEqual(code, 2)
        self.assertIn('--dump', err)

    def test_folder_and_dump(self):
        folder = self.d / 'sprites'
        folder.mkdir()
        for i, colour in enumerate(((250, 0, 0, 255), (0, 250, 0, 255), (0, 0, 250, 255))):
            im = Image.new('RGBA', (60 + 10 * i, 40), (0, 0, 0, 0))
            ImageDraw.Draw(im).ellipse([0, 0, 59, 39], fill=colour)
            im.save(folder / ('s%d.png' % i))
        code, _o, err = run('--folder', folder, '--out', self.d / 'f.png')
        self.assertEqual(code, 0, err)
        self.assertEqual(len(json.loads(Path(str(self.d / 'f.png') + '.json').read_text())['items']), 3)
        self.assertFalse({(250, 0, 0), (0, 250, 0), (0, 0, 250)} & self.colours(self.d / 'f.png'))
        dump = self.d / 'home-ui-dump.json'
        dump.write_text(json.dumps({'tool': 'ui_dump', 'canvas_css': [0, 0, 390, 844], 'nodes': [
            {'path': 'Canvas/bg', 'rect': [0, 0, 1, 1], 'comps': {'sprite': {}}},
            {'path': 'Canvas/play', 'rect': [0.3, 0.7, 0.4, 0.08], 'comps': {'button': {}, 'sprite': {}}},
            {'path': 'Canvas/title', 'rect': [0.1, 0.1, 0.8, 0.1], 'comps': {'label': {'string': 'Hi'}}}]}))
        code, _o, err = run('--dump', dump, '--out', self.d / 'd.png')
        self.assertEqual(code, 0, err)
        names = [i['name'] for i in json.loads(Path(str(self.d / 'd.png') + '.json').read_text())['items']]
        self.assertEqual(names, ['Canvas/play (button)', 'Canvas/title (label)'])   # full-screen bg left out


if __name__ == '__main__':
    unittest.main(verbosity=1)
