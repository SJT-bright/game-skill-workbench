"""R4R3 (补读第 11 组, 弹球传奇 FREE GEMS / OK): a generated word picture with a soft blue halo is found and cleaned.

Fixtures: a clean word, the same word with a 6 px semi-transparent blue halo, and a word with a thick drawn outline and
a soft purple drop shadow (designed, must stay). The old flow (trim_visible.py without --word) keeps every pixel of
all three.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def word(halo=0, shadow=False, outline=4):
    im = Image.new('RGBA', (400, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x1, y1, x2, y2 = 100, 70, 300, 130
    if shadow:
        d.rectangle((x1 - outline, y1 - outline + 8, x2 + outline, y2 + outline + 8), fill=(90, 40, 140, 120))
    for i in range(halo, 0, -1):      # 6 px halo, alpha 150 near the outline -> 25 far out
        d.rectangle((x1 - outline - i, y1 - outline - i, x2 + outline + i, y2 + outline + i),
                    fill=(110, 120, 255, 25 + (halo - i) * 25))
    d.rectangle((x1 - outline - 1, y1 - outline - 1, x2 + outline + 1, y2 + outline + 1), fill=(20, 20, 80, 128))
    d.rectangle((x1 - outline, y1 - outline, x2 + outline, y2 + outline), fill=(20, 20, 80, 255))
    d.rectangle((x1, y1, x2, y2), fill=(250, 250, 255, 255))
    return im


def alpha_outside(im, box=(93, 63, 307, 137)):
    a = im.getchannel('A')
    full = sum(1 for v in a.getdata() if v)
    inner = sum(1 for v in a.crop(box).getdata() if v)
    return full - inner


class CleanGlow(unittest.TestCase):
    def test_old_flow_keeps_the_halo(self):
        from trim_visible import trim
        out, _ = trim(word(halo=6))
        self.assertGreater(alpha_outside(out, (93 - 94, 63 - 54, 307 - 94, 137 - 54)), 1000)

    def test_halo_found_and_cleaned_clean_and_outline_untouched(self):
        from clean_glow import clean, measure
        self.assertEqual(measure(word())['verdict'], 'clean')
        self.assertEqual(measure(word(outline=10))['verdict'], 'clean')
        self.assertEqual(measure(word(halo=6))['verdict'], 'glow')
        self.assertEqual(measure(word(shadow=True, outline=10))['verdict'], 'shadow')
        v, out, info = clean(word(halo=6), 'txt_free_gems.png')
        self.assertEqual(v, 'cleaned')
        self.assertEqual(info['after']['verdict'], 'clean')
        self.assertLess(alpha_outside(out), 20)
        self.assertEqual(out.crop((96, 66, 304, 134)).tobytes(), word(halo=6).crop((96, 66, 304, 134)).tobytes())
        for im in (word(), word(outline=10), word(shadow=True, outline=10)):
            self.assertIsNone(clean(im)[1])

    def test_cli_fixes_in_place_with_backup_and_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            word(halo=6).save(t / 'txt_ok.png')
            word().save(t / 'txt_clean.png')
            before = (t / 'txt_clean.png').read_bytes()
            r = subprocess.run([sys.executable, str(HERE / 'clean_glow.py'), str(t / 'txt_ok.png'),
                                str(t / 'txt_clean.png')], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((t / '_glow_backup' / 'txt_ok.png').is_file())
            self.assertEqual((t / 'txt_clean.png').read_bytes(), before)
            rec = json.loads((t / 'glow_clean.json').read_text())
            self.assertEqual([e['verdict'] for e in rec['entries']], ['cleaned', 'clean'])
            with Image.open(t / 'txt_ok.png') as im:
                self.assertLess(alpha_outside(im.convert('RGBA')), 20)

    def test_unremovable_glow_gives_regenerate_prompt(self):
        im = Image.new('RGBA', (300, 150), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((20, 20, 280, 130), fill=(120, 110, 255, 200))    # glow larger than the word itself
        d.rectangle((140, 70, 160, 80), fill=(255, 255, 255, 255))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'txt_free_gems.png'
            im.save(p)
            before = p.read_bytes()
            r = subprocess.run([sys.executable, str(HERE / 'clean_glow.py'), str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn('REGENERATE', r.stdout)
            self.assertIn('"FREE GEMS"', r.stdout)
            self.assertIn('300x150', r.stdout)
            self.assertEqual(p.read_bytes(), before)

    def test_trim_visible_word_flag_cleans_before_trim(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            word(halo=6).save(t / 'in.png')
            r = subprocess.run([sys.executable, str(HERE / 'trim_visible.py'), str(t / 'in.png'), '--out',
                                str(t / 'out.png'), '--word'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            rec = json.loads((t / 'out.png.trim.json').read_text())
            self.assertEqual(rec['glow']['verdict'], 'cleaned')
            self.assertEqual(rec['size'], [217, 77])       # outline + 2 px kept edge + 2 px margin (old flow: 227x87)


if __name__ == '__main__':
    unittest.main()
