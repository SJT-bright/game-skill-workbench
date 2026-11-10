#!/usr/bin/env python3
"""11.17.16 startup check "log says home, screen still loading" (runtime_regression/screen.mjs).
Synthetic PNGs with every PNG row filter; the SLS36 v61 shape (an almost one-colour loading picture that never
leaves the screen) must fail, a real home must pass. Needs node. Run: python3 -B test_screen_change.py"""
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib

HERE = Path(__file__).resolve().parent
SCREEN = HERE / 'runtime_regression' / 'screen.mjs'
SUITES = HERE / 'runtime_regression' / 'suites'


def png(pixels, w, h, ch=3):
    """Encode rows with filters 0..4 in turn, so the decoder's unfilter paths are all exercised."""
    def paeth(a, b, c):
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        return a if pa <= pb and pa <= pc else b if pb <= pc else c
    stride, raw, prev = w * ch, bytearray(), bytearray(w * ch)
    for y in range(h):
        row = bytearray(pixels[y * stride:(y + 1) * stride])
        f = y % 5
        out = bytearray()
        for x in range(stride):
            a = row[x - ch] if x >= ch else 0
            b = prev[x]
            c = prev[x - ch] if x >= ch else 0
            pred = (0, a, b, (a + b) >> 1, paeth(a, b, c))[f]
            out.append((row[x] - pred) & 255)
        raw += bytes([f]) + out
        prev = row

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 6 if ch == 4 else 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(bytes(raw))) + chunk(b'IEND', b'')


def frame(w, h, fill, boxes=()):
    px = bytearray(fill * (w * h))
    for (x0, y0, x1, y1, colour) in boxes:
        for y in range(y0, y1):
            for x in range(x0, x1):
                i = (y * w + x) * 3
                px[i:i + 3] = bytes(colour)
    return bytes(px)


W, H = 120, 240
LOADING = frame(W, H, b'\x20\x60\xc0', [(40, 90, 80, 120, (255, 255, 255)), (20, 200, 70, 206, (255, 200, 0))])
LOADING_LATER = frame(W, H, b'\x20\x60\xc0', [(40, 90, 80, 120, (255, 255, 255)), (20, 200, 78, 206, (255, 200, 0))])
HOME = frame(W, H, b'\x60\xa0\x40', [(10, 20, 110, 60, (250, 230, 120)), (30, 150, 90, 190, (200, 60, 40)),
                                    (20, 205, 50, 230, (40, 40, 40)), (70, 205, 100, 230, (40, 40, 40))])
DARK_HOME = frame(W, H, b'\x00\x00\x00', [(30, 40, 90, 60, (230, 230, 230)), (35, 150, 85, 175, (90, 200, 90))])


@unittest.skipUnless(shutil.which('node'), 'node is required')
class ScreenChange(unittest.TestCase):
    def share(self, a, b, ch=3):
        with tempfile.TemporaryDirectory() as tmp:
            pa, pb = Path(tmp) / 'a.png', Path(tmp) / 'b.png'
            pa.write_bytes(png(a, W, H, ch))
            pb.write_bytes(png(b, W, H, ch))
            code = ("import fs from 'node:fs'; const S = await import(%s); "
                    "const a = fs.readFileSync(%s), b = fs.readFileSync(%s); "
                    "const d = S.decodePng(a); console.log(JSON.stringify({share: S.changedShare(a, b), min: S.MIN_CHANGED, "
                    "px: d && Array.from(d.data.subarray(0, 6))}));"
                    % (json.dumps(SCREEN.as_uri()), json.dumps(str(pa)), json.dumps(str(pb))))
            r = subprocess.run(['node', '--input-type=module', '-e', code], capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            return json.loads(r.stdout)

    def test_decoder_reads_every_filter(self):
        out = self.share(LOADING, LOADING)
        self.assertEqual(out['px'], [0x20, 0x60, 0xc0, 0x20, 0x60, 0xc0])
        self.assertEqual(out['share'], 0)

    def test_sls36_shape_stuck_on_loading_fails(self):
        out = self.share(LOADING, LOADING_LATER)          # the progress bar moved a little; the picture is the same
        self.assertLess(out['share'], out['min'])

    def test_real_home_passes(self):
        self.assertGreater(self.share(LOADING, HOME)['share'], 0.5)

    def test_dark_minimal_home_after_black_start_passes(self):
        black = frame(W, H, b'\x00\x00\x00')
        self.assertGreater(self.share(black, DARK_HOME)['share'], 0.02)

    def test_rgba_screenshots(self):
        rgba = lambda px: b''.join(px[i:i + 3] + b'\xff' for i in range(0, len(px), 3))
        out = self.share(rgba(LOADING), rgba(HOME), ch=4)
        self.assertGreater(out['share'], 0.5)

    def test_both_startup_suites_judge_the_screen(self):
        for name in ('startup.mjs', 'startup3x.mjs'):
            text = (SUITES / name).read_text(encoding='utf-8')
            self.assertIn("../screen.mjs", text, name)
            self.assertIn('sw.loading(page', text, name)
            self.assertIn('sw.judge(page', text, name)


if __name__ == '__main__':
    unittest.main()
