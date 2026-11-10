#!/usr/bin/env python3
"""Tests for audit_image_review_record.py and audit_new_english_images.py (v7.5, MusicSlice items 6-7).
Run: python3 -B test_english_image_gates.py"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_image_review_record as review  # noqa: E402
import audit_new_english_images as newimg  # noqa: E402


def png(w, h, pad=0):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(b'\0' * 10)) + chunk(b'tEXt', b'x' * pad) + chunk(b'IEND', b''))


def sha(b):
    return hashlib.sha256(b).hexdigest()


OLD, NEW, BG = png(10, 10, 1), png(10, 10, 2), png(20, 20)


def sealed(entries):
    """P16 (2026-11-04): only a record written by audit_image_review_record.py write counts; tests seal theirs the same way."""
    return {'schema': 'image_review.v1', 'images': entries,
            'generated_by': {'tool': review.WRITER, 'entries_sha256': review.entries_seal(entries)}}


class ReviewRecord(unittest.TestCase):
    def run_check(self, files, entries):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'image-review.json'
            if entries is not None:
                p.write_text(json.dumps(sealed(entries)))
            return review.check(files, p)

    def entry(self, b, chinese='no', **kw):
        return dict({'sha256': sha(b), 'reviewer': 'main agent', 'status': 'done', 'chinese': chinese}, **kw)

    def test_missing_record_refused(self):
        self.assertFalse(self.run_check({'a.png': BG}, None)['passed'])

    def test_unreplaced_chinese_refused_and_replaced_passes(self):
        r = self.run_check({'home.png': OLD, 'bg.png': BG}, [self.entry(OLD, 'yes'), self.entry(BG)])
        self.assertFalse(r['passed'])
        self.assertIn('still in the package', r['problems'][0])
        r = self.run_check({'home.png': NEW, 'bg.png': BG}, [self.entry(OLD, 'yes', replaced_with=sha(NEW)), self.entry(NEW), self.entry(BG)])
        self.assertTrue(r['passed'], r['problems'])

    def test_unlisted_pending_and_atlas(self):
        self.assertFalse(self.run_check({'a.png': BG, 'b.png': NEW}, [self.entry(BG)])['passed'])
        self.assertFalse(self.run_check({'a.png': BG}, [self.entry(BG, status='pending')])['passed'])
        files = {'atlas.png': BG, 'atlas.plist': b'<plist/>'}
        self.assertFalse(self.run_check(files, [self.entry(BG)])['passed'])
        self.assertTrue(self.run_check(files, [self.entry(BG, slices_reviewed=True)])['passed'])

    def test_duplicates_counted_once(self):
        r = self.run_check([('a.png', BG), ('copy/a.png', BG)], [self.entry(BG)])
        self.assertTrue(r['passed'])
        self.assertEqual(r['distinct_images'], 1)


class NewImages(unittest.TestCase):
    def test_only_new_images_judged(self):
        big_old = png(4000, 4000, 900_000)
        big_new = png(100, 100, 900_000)
        r = newimg.check({'old.png': big_old, 'new.png': big_new}, [sha(big_old)])
        self.assertFalse(r['passed'])
        self.assertEqual(len(r['problems']), 1)
        self.assertIn('new.png', r['problems'][0])

    def test_display_ratio(self):
        img = png(1983, 793)
        self.assertFalse(newimg.check({'retry.png': img}, [], {'retry.png': (390, 156)})['passed'])
        self.assertTrue(newimg.check({'retry.png': img}, [], {'retry.png': (800, 320)})['passed'])
        self.assertTrue(newimg.check({'retry.png': img}, [])['passed'], 'no display size known: bytes rule only')

    def test_pixels_reader(self):
        self.assertEqual(newimg.pixels(png(33, 44)), (33, 44))


class WriterNewImageGate(unittest.TestCase):
    """11.17.14: both writers check the bytes about to be zipped; no art re-run, no image review, no recording."""

    def gate(self, files, board='localize', pre=None):
        import make_tiktok_zip
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            if pre is not None:
                target = project / make_tiktok_zip.PRE_ENGLISH_LIST
                target.parent.mkdir(parents=True)
                target.write_text(json.dumps({'images': {s: 'x.png' for s in pre}}), encoding='utf-8')
            return make_tiktok_zip.english_new_image_problems(files, project, board)

    def test_oversized_new_image_refused_original_kept(self):
        big = png(10, 10, newimg.MAX_BYTES + 10)
        self.assertTrue(any('800' in p or 'bytes' in p or 'KB' in p for p in
                            self.gate({'assets/new.png': big}, pre=[sha(OLD)])))
        self.assertEqual(self.gate({'assets/old.png': big}, pre=[sha(big)]), [])
        self.assertEqual(self.gate({'assets/new.png': NEW}, pre=[sha(OLD)]), [])

    def test_missing_pre_english_list_refused_with_the_command(self):
        problems = self.gate({'assets/new.png': NEW})
        self.assertTrue(problems and '--make-list' in problems[0])

    def test_remake_board_not_judged(self):
        self.assertEqual(self.gate({'assets/new.png': png(10, 10, newimg.MAX_BYTES + 10)}, board='remake'), [])


if __name__ == '__main__':
    unittest.main()
