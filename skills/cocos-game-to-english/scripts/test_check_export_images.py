#!/usr/bin/env python3
"""check_export_images.py (English pack 10.2.7): an export from before the art change must be reported, a fresh export
must pass. Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_check_export_images.py
"""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_export_images as C  # noqa: E402

U1 = '11111111-2222-3333-4444-555555555555'
U2 = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'


def png(tag):
    return b'\x89PNG\r\n\x1a\n' + tag.encode('ascii') * 8


class ExportImages(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)

    def make(self, style='2.4'):
        root = Path(self.td.name)
        proj, exp = root / 'proj', root / 'web-mobile'
        (proj / 'assets' / 'ui').mkdir(parents=True)
        for name, uuid, tag in (('btn_play.png', U1, 'play-new'), ('title.png', U2, 'title-new')):
            (proj / 'assets' / 'ui' / name).write_bytes(png(tag))
            meta = ({'ver': '2.3.7', 'uuid': uuid, 'type': 'sprite', 'subMetas': {}} if style == '2.4' else
                    {'ver': '1.0.25', 'importer': 'image', 'uuid': uuid, 'userData': {'type': 'sprite-frame'}})
            (proj / 'assets' / 'ui' / (name + '.meta')).write_text(json.dumps(meta), encoding='utf-8')
        exp.mkdir()
        return proj, exp

    def put(self, exp, uuid, data, md5='ab12c', older_than=None, newer_than=None):
        p = exp / 'assets' / 'main' / 'native' / uuid[:2] / ('%s.%s.png' % (uuid, md5))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        ref = older_than or newer_than
        if ref is not None:
            t = ref.stat().st_mtime + (-60 if older_than is not None else 60)
            os.utime(p, (t, t))
        return p

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = C.main([str(a) for a in args])
        return code, out.getvalue()

    def test_fresh_export_passes_for_2x_and_3x_meta(self):
        for style in ('2.4', '3.x'):
            with self.subTest(style=style):
                self.td.cleanup()
                self.td = tempfile.TemporaryDirectory()
                proj, exp = self.make(style)
                self.put(exp, U1, png('play-new'))
                self.put(exp, U2, png('title-new'))
                (exp / 'splash.85cfd.png').write_bytes(png('engine'))
                r = C.check(proj, exp)
                self.assertTrue(r['passed'])
                self.assertEqual((r['exported'], r['matched'], r['current'], r['unmatched']), (3, 2, 2, 1))
                code, text = self.run_main('--project', proj, '--export', exp)
                self.assertEqual(code, 0, text)

    def test_export_from_before_the_art_change_is_reported(self):
        proj, exp = self.make()
        self.put(exp, U1, png('play-new'))
        self.put(exp, U2, png('title-old'), older_than=proj / 'assets' / 'ui' / 'title.png')
        r = C.check(proj, exp)
        self.assertFalse(r['passed'])
        self.assertEqual([row['project'] for row in r['old']], ['assets/ui/title.png'])
        self.assertIn('比工程里的旧', r['old'][0]['why'])
        code, text = self.run_main('--project', proj, '--export', exp)
        self.assertEqual(code, 1)
        self.assertIn('旧图：', text)
        self.assertIn('重新构建', text)
        self.put(exp, U2, png('title-new'))          # the fixed export: same file name, current bytes
        self.assertEqual(self.run_main('--project', proj, '--export', exp)[0], 0)

    def test_chinese_original_in_a_newer_export_is_reported(self):
        proj, exp = self.make()
        old = png('title-chinese')
        docs = proj / 'docs' / 'english'
        docs.mkdir(parents=True)
        (docs / 'pre-english-images.json').write_text(json.dumps({'source': 'x', 'images': {C.hashlib.sha256(old).hexdigest(): 'assets/ui/title.png'}}), encoding='utf-8')
        self.put(exp, U1, png('play-new'))
        self.put(exp, U2, old, newer_than=proj / 'assets' / 'ui' / 'title.png')
        r = C.check(proj, exp)
        self.assertFalse(r['passed'])
        self.assertIn('英化前的原图', r['old'][0]['why'])

    def test_newer_different_export_is_only_a_note(self):
        proj, exp = self.make()
        self.put(exp, U1, png('play-new'))
        self.put(exp, U2, png('title-compressed'), newer_than=proj / 'assets' / 'ui' / 'title.png')
        r = C.check(proj, exp)
        self.assertTrue(r['passed'])
        self.assertEqual(len(r['notes']), 1)
        self.assertIn('引擎压缩', r['notes'][0]['why'])

    def test_leftover_old_file_next_to_the_current_one_is_only_a_note(self):
        proj, exp = self.make()
        self.put(exp, U1, png('play-new'))
        self.put(exp, U2, png('title-new'), md5='new01')
        self.put(exp, U2, png('title-old'), md5='old99', older_than=proj / 'assets' / 'ui' / 'title.png')
        r = C.check(proj, exp)
        self.assertTrue(r['passed'])
        self.assertIn('旧文件', r['notes'][0]['why'])

    def test_bad_input_exits_2(self):
        proj, exp = self.make()
        self.assertEqual(self.run_main('--project', proj, '--export', exp / 'missing')[0], 2)
        self.assertEqual(self.run_main('--project', exp, '--export', exp)[0], 2)
        self.assertEqual(self.run_main('--project', proj, '--export', exp)[0], 2)   # export folder has no picture


if __name__ == '__main__':
    unittest.main(verbosity=2)
