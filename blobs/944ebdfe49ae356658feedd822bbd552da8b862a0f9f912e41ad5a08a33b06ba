"""R4O2 (补查2 第 7 组, 合成进化恐龙 NO THANKS / CLAIM): alpha=1 specks must not widen a crop."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def speck_word():
    """A 400x200 'word' at (150,80)-(249,119) plus alpha=1 and alpha=7 specks near every corner (as GPT output has)."""
    im = Image.new('RGBA', (400, 200), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle((150, 80, 249, 119), fill=(240, 240, 240, 255))
    im.putpixel((150, 79), (240, 240, 240, 40))           # soft anti-aliased edge, must survive
    for xy in ((3, 3), (396, 4), (5, 195), (390, 190)):
        im.putpixel(xy, (255, 255, 255, 1))
    im.putpixel((20, 100), (255, 255, 255, 7))
    return im


class TrimVisible(unittest.TestCase):
    def test_compose_foreground_ignores_low_alpha_specks(self):
        from compose_fixed_button import foreground
        im = speck_word()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'word.png'
            im.save(p)
            rec = {'file': 'word.png', 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
            fg = foreground(Path(tmp), rec)
        # visible 100x40 (+ the alpha-40 edge row) + 2 px each side; the old alpha>0 crop was 394x193
        self.assertEqual(fg.size, (104, 45), fg.size)

    def test_trim_box_and_margin(self):
        from trim_visible import trim, visible_box
        out, box = trim(speck_word())
        self.assertEqual(box, (148, 77, 252, 122))
        self.assertEqual(out.getpixel((2, 2))[3], 40)          # soft edge kept
        edge = Image.new('RGBA', (50, 20), (0, 0, 0, 0))
        ImageDraw.Draw(edge).rectangle((0, 0, 9, 9), fill='red')
        self.assertEqual(visible_box(edge), (0, 0, 12, 12))     # clamped at the picture border
        self.assertIsNone(visible_box(Image.new('RGBA', (8, 8), (9, 9, 9, 1))))

    def test_cli_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / 'a.png', Path(tmp) / 'b.png'
            speck_word().save(src)
            r = subprocess.run([sys.executable, str(HERE / 'trim_visible.py'), str(src), '--out', str(out)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            rec = json.loads(Path(str(out) + '.trim.json').read_text())
            self.assertEqual(rec['size'], [104, 45])
            with Image.open(out) as im:
                self.assertEqual(im.size, (104, 45))

    def test_cut_sheet_frame_already_uses_visible_alpha(self):
        from cut_sheet_frame import extract
        sheet = speck_word()
        _master, _cell, bounds = extract(sheet, 1, 1, 1, 1)
        self.assertEqual(bounds, (148, 77, 252, 122))


if __name__ == '__main__':
    unittest.main()
