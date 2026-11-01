#!/usr/bin/env python3
"""Tests for audit_glyph_core (digit glyph-core size). Fonts and screenshots are drawn on the fly with PIL."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_glyph_core as g        # noqa: E402

W, H = 390, 844                     # CSS screen used by the runtime tests


def write_font(folder, name, cell, ink):
    """A 10-digit BMFont: cells cell x cell px (info size = lineHeight = cell); each digit is an ink-px-high bar."""
    page = Image.new('RGBA', (cell * 10, cell), (0, 0, 0, 0))
    d = ImageDraw.Draw(page)
    top = (cell - ink) // 2
    lines = ['info face="T" size=%d bold=0' % cell, 'common lineHeight=%d base=%d scaleW=%d scaleH=%d pages=1'
             % (cell, cell, cell * 10, cell), 'page id=0 file="%s.png"' % name, 'chars count=10']
    for i in range(10):
        d.rectangle([i * cell + cell // 4, top, i * cell + 3 * cell // 4, top + ink - 1], fill=(255, 255, 255, 255))
        lines.append('char id=%d x=%d y=0 width=%d height=%d xoffset=0 yoffset=0 xadvance=%d page=0'
                     % (48 + i, i * cell, cell, cell, cell))
    page.save(folder / (name + '.png'))
    (folder / (name + '.fnt')).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def label_node(path, value, font, size, box_h_css, top_css=20, kind='bitmap'):
    """A label whose node box is box_h_css CSS px high and whose font size equals the box height in design units."""
    r = [150 / W, top_css / H, 90 / W, box_h_css / H]
    return {'path': path, 'name': path.rsplit('/', 1)[-1], 'order': 5, 'depth': 3, 'opacity': 1, 'rect': r, 'screen': r,
            'comps': {'label': {'string': value, 'fontSize': size, 'actualFontSize': size, 'height': size,
                                'font': font, 'font_kind': kind}}}


def page(nodes, kind='home', purpose='home'):
    return {'kind': kind, 'purpose': purpose, 'canvas_css': [0, 0, W, H], 'nodes': nodes}


class StaticPadding(unittest.TestCase):
    def setUp(self):
        self.proj = Path(tempfile.mkdtemp())
        (self.proj / 'assets' / 'fonts').mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.proj)

    def test_wide_margin_font_reported(self):
        write_font(self.proj / 'assets' / 'fonts', 'padded', 96, 48)          # digits fill 50% of the em
        ratios = g.font_ink_ratios(self.proj, Image)
        self.assertAlmostEqual(ratios['padded']['ratio'], 0.5, places=2)
        probs = g.digit_glyph_padding_problems(ratios, self.proj)
        self.assertEqual(len(probs), 1)
        self.assertTrue(probs[0].startswith('digit_glyph_padding:'))

    def test_tight_font_passes(self):
        write_font(self.proj / 'assets' / 'fonts', 'tight', 96, 88)
        ratios = g.font_ink_ratios(self.proj, Image)
        self.assertGreater(ratios['tight']['ratio'], 0.9)
        self.assertEqual(g.digit_glyph_padding_problems(ratios, self.proj), [])

    def test_digit_strip_is_runtime_only(self):
        strip = Image.new('RGBA', (640, 96), (0, 0, 0, 0))
        ImageDraw.Draw(strip).rectangle([10, 24, 620, 71], fill=(255, 255, 255, 255))
        strip.save(self.proj / 'assets' / 'digits.png')
        ratios = g.font_ink_ratios(self.proj, Image)
        self.assertIn('digit3', ratios)                                      # frames cut from the strip
        self.assertEqual(g.digit_glyph_padding_problems(ratios, self.proj), [])


class RuntimeCore(unittest.TestCase):
    padded = {'padded': {'kind': 'fnt', 'file': 'padded.fnt', 'em': 96, 'ink': 48, 'ratio': 0.5}}
    tight = {'tight': {'kind': 'fnt', 'file': 'tight.fnt', 'em': 96, 'ink': 90, 'ratio': 0.94}}

    def test_big_size_small_core_reported(self):
        n = label_node('Canvas/topbar/coinCount', '120', 'padded', 30, 30)   # 30 CSS font, 15 CSS digits
        probs = g.glyph_core_problems(page([n]), [n], self.padded, None)
        self.assertEqual(len(probs), 1)
        self.assertTrue(probs[0].startswith('small_glyph_core:'), probs)

    def test_big_core_passes(self):
        n = label_node('Canvas/topbar/coinCount', '120', 'tight', 30, 30)    # 28 CSS digits
        self.assertEqual(g.glyph_core_problems(page([n]), [n], self.tight, None), [])

    def test_small_font_outside_hud_reported_as_value_font(self):
        n = label_node('Canvas/topbar/coinCount', '120', 'tight', 14, 14)    # 13 CSS digits, font size itself small
        probs = g.glyph_core_problems(page([n]), [n], self.tight, None)
        self.assertEqual([p.split(':')[0] for p in probs], ['small_value_font'])

    def test_small_font_in_english_game_is_only_a_hint(self):
        # Saul 2026-10-31 "small_value_font 先只拦重塑": the same finding, advisory in an English game
        n = label_node('Canvas/topbar/coinCount', '120', 'tight', 14, 14)
        probs = g.glyph_core_problems(page([n]), [n], self.tight, None, english=True)
        self.assertEqual([p.split(':')[0] for p in probs], ['small_value_font_hint'])
        self.assertIn('120', probs[0])
        big = label_node('Canvas/topbar/coinCount', '120', 'padded', 30, 30)   # small_glyph_core still blocks there
        self.assertEqual([p.split(':')[0] for p in g.glyph_core_problems(page([big]), [big], self.padded, None,
                                                                          english=True)], ['small_glyph_core'])

    def test_gameplay_hud_small_font_left_to_v78(self):
        n = label_node('Canvas/hud/score', '120', 'tight', 14, 14)
        self.assertEqual(g.glyph_core_problems(page([n], 'gameplay', 'gameplay'), [n], self.tight, None), [])

    def test_picture_digits_untrimmed_vs_trimmed(self):
        def digits(cell_h, box_css):
            out = []
            for i, ch in enumerate('25'):
                r = [(250 + i * 30) / W, 60 / H, 20 / W, box_css / H]
                out.append({'path': 'Canvas/page/hearts/art:digit%d' % i, 'name': 'd', 'order': 9 + i, 'depth': 3,
                            'opacity': 1, 'rect': r, 'screen': r,
                            'comps': {'sprite': {'frame': 'digit' + ch, 'frame_size': [64, cell_h]}}})
            return out
        strip = {'digit%d' % i: {'kind': 'digit_strip', 'file': 'digits.png', 'em': 96, 'ink': 50, 'ratio': 0.52,
                                 'cell_h': 96} for i in range(10)}
        before = digits(96, 25)            # Milo control: 25 CSS box, untrimmed cells -> 13 CSS of ink
        after = digits(50, 25)             # frames trimmed to the ink: the box is the digit
        self.assertTrue(g.glyph_core_problems(page(before), before, strip, None)[0].startswith('small_glyph_core:'))
        self.assertEqual(g.glyph_core_problems(page(after), after, strip, None), [])


class ScreenshotFallback(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.dir)

    def shot(self, ink_css):
        im = Image.new('RGB', (W, H), (90, 160, 220))
        d = ImageDraw.Draw(im)
        d.rectangle([150, 20, 240, 60], fill=(250, 240, 210))                     # cream value plate
        top = 40 - ink_css // 2
        for x in (160, 190, 215):                                                 # three dark "digits"
            d.rectangle([x, top, x + 14, top + ink_css - 1], fill=(30, 80, 110))
        im.save(self.dir / '001-ui-home.png')
        dump = self.dir / '001-ui-dump-home.json'
        return dump

    def run_shot(self, ink_css):
        dump = self.shot(ink_css)
        n = label_node('Canvas/topbar/coinCount', '120', 'unknown_font', 40, 40)  # font metrics not found
        d = page([n])
        d['_file'] = str(dump)
        return g.glyph_core_problems(d, [n], {}, Image)

    def test_measures_ink_on_screenshot(self):
        self.shot(15)
        im = Image.open(self.dir / '001-ui-home.png')
        h = g.shot_ink(im.convert('RGB'), [150 / W, 20 / H, 90 / W, 40 / H])
        self.assertAlmostEqual(h * H, 15, delta=1)

    def test_small_ink_is_advisory(self):
        probs = self.run_shot(15)
        self.assertEqual([p.split(':')[0] for p in probs], ['glyph_core_review'])

    def test_big_ink_passes(self):
        self.assertEqual(self.run_shot(26), [])

    def test_hidden_value_not_judged(self):
        self.assertEqual(self.run_shot(6), [])          # under 35% of the box: covered or not drawn


class Integration(unittest.TestCase):
    """audit_page_richness.check() and its setup list, and the art_check row, carry the glyph-core codes."""

    def setUp(self):
        self.proj = Path(tempfile.mkdtemp())
        (self.proj / 'assets' / 'fonts').mkdir(parents=True)
        write_font(self.proj / 'assets' / 'fonts', 'padded', 96, 48)
        self.out = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.proj)
        shutil.rmtree(self.out)

    def test_check_reports_small_core_and_keeps_screenshot_only_as_advice(self):
        import audit_page_richness as apr
        n = label_node('Canvas/topbar/coinCount', '120', 'padded', 30, 30)
        d = page([n])
        d['_file'] = str(self.out / '000-ui-dump-home.json')      # no screenshot: the font metrics decide
        problems, stats = apr.check(d, Image, self.proj)
        self.assertTrue(any(p.startswith('small_glyph_core:') for p in problems), problems)
        self.assertNotIn('glyph_core_review', stats)
        self.assertEqual([p.split(':')[0] for p in apr.glyph_padding_problems(self.proj)], ['digit_glyph_padding'])

    def test_art_check_row_lists_page_and_font_findings(self):
        import art_check
        self.assertTrue({'small_glyph_core', 'small_value_font', 'digit_glyph_padding'} <= art_check.HERO_HUD_KINDS)
        self.assertNotIn('small_value_font_hint', art_check.HERO_HUD_KINDS)       # a hint never fails the row

    def test_board_is_read_like_the_package_writers(self):
        def write(rel, text):
            f = self.proj / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding='utf-8')
        self.assertFalse(g.english_game(self.proj))                                  # nothing recorded: remake
        self.assertTrue(g.english_game(self.proj, 'localize'))                       # art_check --board
        write('docs/board.txt', 'localize\n')
        self.assertTrue(g.english_game(self.proj))
        write('.tiktok-kit/policy.json', json.dumps({'policy': 'new', 'board': 'remake'}))
        self.assertFalse(g.english_game(self.proj))                                  # the kickoff marker wins
        write('.tiktok-kit/finalize-source.json', json.dumps({'board': 'localize'}))
        self.assertTrue(g.english_game(self.proj))                                   # then the source record
        self.assertFalse(g.english_game(self.proj, 'remake'))
        write('docs/art-style.txt', 'original\n')
        self.assertTrue(g.english_game(self.proj, 'remake'))                         # kept original art
        self.assertFalse(g.english_game(None))

    def test_check_keeps_small_value_font_only_for_remake_games(self):
        import audit_page_richness as apr
        n = label_node('Canvas/topbar/coinCount', '120', 'padded', 14, 14)         # the font size itself is small
        english = Path(tempfile.mkdtemp())
        try:
            (english / 'assets' / 'fonts').mkdir(parents=True)
            write_font(english / 'assets' / 'fonts', 'padded', 96, 48)              # same font as the remake project
            (english / '.tiktok-kit').mkdir()
            (english / '.tiktok-kit' / 'policy.json').write_text(json.dumps({'policy': 'new', 'board': 'localize'}))
            results = {}
            for name, proj in (('remake', self.proj), ('english', english)):
                d = page([dict(n)])
                d['_file'] = str(self.out / ('%s-ui-dump-home.json' % name))
                results[name] = apr.check(d, Image, proj)
            problems, stats = results['remake']
            self.assertIn('small_value_font', [p.split(':')[0] for p in problems])
            self.assertNotIn('small_value_font_hints', stats)
            problems, stats = results['english']
            self.assertNotIn('small_value_font', [p.split(':')[0] for p in problems])
            self.assertEqual([h.split(':')[0] for h in stats['small_value_font_hints']], ['small_value_font_hint'])
        finally:
            shutil.rmtree(english)


if __name__ == '__main__':
    unittest.main()
