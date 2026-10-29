#!/usr/bin/env python3
"""Regression for 'HelP the koi ... TaP ... Pond' (user 2026-10-28): generated letter atlases are refused."""
import json
from pathlib import Path
import tempfile
import unittest
from audit_bitmap_letter_fonts import audit


def fnt(chars):
    rows = ['info face="gen" size=48', 'common lineHeight=56 base=44 scaleW=512 scaleH=512 pages=1', 'page id=0 file="gen.png"']
    for i, (c, rect) in enumerate(chars.items()):
        x, y = rect if rect else (i * 30 % 480, i * 30 // 480 * 56)
        rows.append('char id=%d x=%d y=%d width=28 height=50 xoffset=0 yoffset=0 xadvance=32 page=0 chnl=15' % (ord(c), x, y))
    return '\n'.join(rows) + '\n'


class BitmapLetterFonts(unittest.TestCase):
    def project(self, font_chars, label_text):
        tmp = tempfile.TemporaryDirectory(prefix='bitmap fonts ')
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / 'assets/fonts').mkdir(parents=True)
        (root / 'assets/fonts/gen.fnt').write_text(fnt(font_chars))
        (root / 'assets/fonts/gen.fnt.meta').write_text(json.dumps({'uuid': 'font-1'}))
        scene = [{'__type__': 'cc.SceneAsset'}, {'__type__': 'cc.Label', '_N$string': label_text, '_N$file': {'__uuid__': 'font-1'}}]
        (root / 'assets/main.fire').write_text(json.dumps(scene))
        return root

    def kinds(self, report):
        return sorted({f['kind'] for f in report['findings']})

    def test_screenshot_defect_lowercase_p_drawn_as_capital(self):
        chars = {c: None for c in 'HelotkiachbmrwsnyTd .-'}
        chars['P'] = (400, 400)
        chars['p'] = (400, 400)  # the atlas reuses the capital P image
        report = audit(self.project(chars, 'Help the koi reach the bottom row. Tap a bottom-row koi to send it into the pond.'))
        self.assertFalse(report['passed'])
        self.assertIn('letter_case_alias', self.kinds(report))
        self.assertIn('sentence_in_bitmap', self.kinds(report))

    def test_missing_lowercase_glyph(self):
        chars = {c: None for c in 'TAPtaP'}
        report = audit(self.project(chars, 'Tap'))
        self.assertIn('missing_glyph', self.kinds(report))  # lowercase 'p' is absent
        self.assertIn('partial_letter_case', self.kinds(report))

    def test_digit_font_for_counters_passes(self):
        chars = {c: None for c in '0123456789+-:/%x'}
        report = audit(self.project(chars, '614'))
        self.assertTrue(report['passed'], report)

    def test_short_fixed_word_with_distinct_glyphs_is_not_a_sentence(self):
        chars = {c: None for c in 'LEVEL0123456789 '}
        report = audit(self.project(chars, 'LEVEL 13'))
        self.assertTrue(report['passed'], report)


if __name__ == '__main__':
    unittest.main(verbosity=2)
