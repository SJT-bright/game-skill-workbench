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


class ReviewRecord(unittest.TestCase):
    def run_check(self, files, entries):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'image-review.json'
            if entries is not None:
                p.write_text(json.dumps({'schema': 'image_review.v1', 'images': entries}))
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


class PackageEntryWiring(unittest.TestCase):
    """make_tiktok_zip.english_image_problems(): used by make_tiktok_zip.py and build_checked_zip.py (W4 REQUESTS 1)."""

    def setUp(self):
        from make_tiktok_zip import english_image_problems
        self.problems = english_image_problems
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        self.files = {'game.js': b'x', 'home.png': NEW, 'bg.png': BG}

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, review_entries, pre):
        docs = self.project / 'docs' / 'english'
        docs.mkdir(parents=True, exist_ok=True)
        (docs / 'image-review.json').write_text(json.dumps({'schema': 'image_review.v1', 'images': review_entries}))
        (docs / 'pre-english-images.json').write_text(json.dumps(pre))

    def entry(self, b):
        return {'sha256': sha(b), 'reviewer': 'main agent', 'status': 'done', 'chinese': 'no'}

    def test_remake_board_not_affected(self):
        self.assertEqual(self.problems(self.files, self.project, 'remake'), [])
        self.assertEqual(self.problems(self.files, None, None), [])

    def test_localize_missing_record_and_list_refuse(self):
        found = ' | '.join(self.problems(self.files, self.project, 'localize'))
        self.assertIn('image review', found)
        self.assertIn('pre-English image list missing', found)
        self.assertTrue(self.problems(self.files, None, 'localize'))

    def test_localize_complete_records_pass_and_big_new_image_refuses(self):
        self.write([self.entry(NEW), self.entry(BG)], [sha(BG)])
        self.assertEqual(self.problems(self.files, self.project, 'localize'), [])
        big = png(10, 10, newimg.MAX_BYTES)
        files = dict(self.files, **{'home.png': big})
        self.write([self.entry(big), self.entry(BG)], [sha(BG)])
        self.assertIn('> %d' % newimg.MAX_BYTES, ' '.join(self.problems(files, self.project, 'localize')))


if __name__ == '__main__':
    unittest.main()
