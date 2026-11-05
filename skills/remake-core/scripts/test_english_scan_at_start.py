#!/usr/bin/env python3
"""P16 (生成时预防, 2026-11-04): Chinese in pictures, atlas slices and animation frames is found at the START of English work.

  audit_new_english_images.py --make-list   cuts every slice of a cocos .plist atlas and reads each with OCR; only the
                                            slice with Chinese goes onto art-replace-round1.json "replace"
  no recognizer                             nothing is called clean, every picture and slice is listed for manual review
  audit_image_review_record.py write        the only way to get an image-review.json that the package check accepts;
                                            a hand-filled or hand-edited record is refused

OCR is the chinese_audit fake recognizer (CHINESE_AUDIT_FAKE_OCR), so this runs on any computer with Pillow.
Old way: OLD_SCRIPTS=<dir with the 11.12 audit_new_english_images.py / audit_image_review_record.py> runs the same
cases against the old scripts (expected: the frame/record cases fail).
Run: python3 test_english_scan_at_start.py
"""
import contextlib
import importlib.util
import io
import json
import os
import plistlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SRC = Path(os.environ.get('OLD_SCRIPTS') or HERE)
sys.path.insert(0, str(HERE.parent.parent / 'cocos-game-to-english' / 'scripts'))
try:
    import chinese_audit as C  # noqa: E402
except ImportError:  # 简化.11.14: the remake pack shares remake-core but has no English entry
    C = None


def setUpModule():
    if C is None:
        raise unittest.SkipTest('cocos-game-to-english/scripts/chinese_audit.py is not in this tree (remake pack layout)')

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


def load(name):
    spec = importlib.util.spec_from_file_location(name + '_under_test', SRC / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ani = load('audit_new_english_images')
review = load('audit_image_review_record')


def frame(color):
    return Image.new('RGBA', (20, 10), color)


def psha(img):
    return C.pixels_sha256(img)


@unittest.skipIf(Image is None, 'needs Pillow')
class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / 'game'
        res = self.project / 'assets' / 'resources' / 'anim'
        res.mkdir(parents=True)
        # a 3-frame animation atlas (cocos plist, format 2): wave_0 / wave_1 / wave_2; only wave_1 has Chinese
        self.frames = [frame((200, 0, 0, 255)), frame((0, 200, 0, 255)), frame((0, 0, 200, 255))]
        page = Image.new('RGBA', (60, 10), (0, 0, 0, 0))
        meta = {}
        for i, f in enumerate(self.frames):
            page.paste(f, (20 * i, 0))
            meta['wave_%d.png' % i] = {'frame': '{{%d,0},{20,10}}' % (20 * i), 'offset': '{0,0}', 'rotated': False,
                                       'sourceColorRect': '{{0,0},{20,10}}', 'sourceSize': '{20,10}'}
        page.save(str(res / 'wave.png'))
        (res / 'wave.plist').write_bytes(plistlib.dumps({'frames': meta, 'metadata': {
            'format': 2, 'textureFileName': 'wave.png', 'size': '{60,10}'}}))
        bg = Image.new('RGBA', (8, 8), (90, 90, 90, 255))
        bg.save(str(self.project / 'assets' / 'resources' / 'bg.png'))
        self.bg = bg
        # the page itself reads "WAVE" (English) so only the slice can carry the Chinese
        self.fake = {psha(self.frames[1]): '高波来袭！', psha(self.frames[0]): 'WAVE', psha(self.frames[2]): 'GO',
                     psha(page): 'WAVE GO'}

    def tearDown(self):
        self.tmp.cleanup()

    def env(self):
        return mock.patch.dict(os.environ, {C.ENV_FAKE: json.dumps(self.fake)})


class MakeList(Base):
    def run_make_list(self, ocr='fake'):
        out = self.root / 'docs' / 'pre-english-images.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        base_args = ['--make-list', str(self.project), '--out', str(out)]
        for args in (base_args + ['--ocr', ocr], base_args):   # the 11.12 script has no --ocr: run it the old way
            with self.env(), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                    mock.patch.object(sys, 'argv', ['x'] + args):
                try:
                    code = ani.main(args) if ani.main.__code__.co_argcount else ani.main()
                except SystemExit as exc:
                    code = exc.code
            if code != 2:
                break
        self.assertEqual(code, 0, 'make-list did not run')
        doc = json.loads(out.read_text(encoding='utf-8'))
        rp = out.parent / 'art-replace-round1.json'
        return doc, (json.loads(rp.read_text(encoding='utf-8')) if rp.is_file() else None)

    def test_only_the_chinese_frame_is_listed(self):
        doc, repl = self.run_make_list()
        self.assertIsNotNone(repl, 'no first-round art replacement list written')
        self.assertEqual(len(doc['images']), 2)                     # old part of the list unchanged
        self.assertEqual(repl['status'], 'ok')
        self.assertEqual(repl['slices'], 3)
        got = [(r['kind'], r.get('slice')) for r in repl['replace']]
        self.assertEqual(got, [('slice', 'wave_1.png')], repl['replace'])
        self.assertEqual(repl['replace'][0]['pixels_sha256'], psha(self.frames[1]))
        self.assertEqual(repl['manual_review'], [])
        self.assertEqual(doc['chinese_scan']['replace'], repl['replace'])

    def test_no_recognizer_lists_everything_for_manual_review(self):
        doc, repl = self.run_make_list('none')
        self.assertIsNotNone(repl)
        self.assertEqual(repl['status'], 'no_recognizer')
        self.assertEqual(repl['clean'], 0)
        self.assertEqual(repl['replace'], [])
        self.assertEqual(len(repl['manual_review']), 2 + 3)         # 2 whole pictures + 3 slices


class ReviewRecordWriter(Base):
    def pkg(self, chinese_frame=True):
        files = {}
        for p in (self.project / 'assets').rglob('*'):
            if p.is_file():
                files[p.relative_to(self.project / 'assets').as_posix()] = p.read_bytes()
        if not chinese_frame:
            self.fake[psha(self.frames[1])] = 'BIG WAVE!'
        return files

    def check(self, files, record):
        p = self.root / 'image-review.json'
        p.write_text(json.dumps(record, ensure_ascii=False), encoding='utf-8')
        return review.check(files, p)

    def test_hand_filled_record_refused(self):
        files = self.pkg(chinese_frame=False)
        import hashlib
        hand = {'schema': 'image_review.v1', 'images': [
            {'sha256': hashlib.sha256(b).hexdigest(), 'file': n, 'reviewer': 'main agent', 'status': 'done',
             'chinese': 'no', 'atlas': True, 'slices_reviewed': True} for n, b in files.items() if n.endswith('.png')]}
        r = self.check(files, hand)
        self.assertFalse(r['passed'], 'a hand-written "done / no / true" record passed')

    def test_written_record_finds_chinese_frame_and_passes_when_clean(self):
        self.assertTrue(hasattr(review, 'write'), 'no script writer for image-review.json')
        files = self.pkg()
        with self.env():
            rec = review.write(files, 'fake')
        page = [e for e in rec['images'] if e['file'].endswith('wave.png')][0]
        self.assertEqual((page['chinese'], page['atlas'], page['slices']), ('yes', True, 3))
        self.assertFalse(self.check(files, rec)['passed'])           # Chinese frame still in the package
        files = self.pkg(chinese_frame=False)
        with self.env():
            rec = review.write(files, 'fake')
        r = self.check(files, rec)
        self.assertTrue(r['passed'], r['problems'])
        rec['images'][0]['chinese'] = 'no' if rec['images'][0]['chinese'] == 'yes' else 'yes'
        self.assertFalse(self.check(files, rec)['passed'], 'hand edit of a written record passed')

    def test_no_recognizer_leaves_pending_until_a_person_decides(self):
        self.assertTrue(hasattr(review, 'write'), 'no script writer for image-review.json')
        files = self.pkg(chinese_frame=False)
        rec = review.write(files, 'none')
        self.assertTrue(all(e['status'] == 'pending' for e in rec['images']))
        self.assertFalse(self.check(files, rec)['passed'])
        verdicts = {e['sha256']: 'no' for e in rec['images']}
        with self.assertRaises(ValueError):
            review.write(files, 'none', verdicts)                     # a verdict needs a name
        rec = review.write(files, 'none', verdicts, by='main agent, looked at every slice')
        r = self.check(files, rec)
        self.assertTrue(r['passed'], r['problems'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
