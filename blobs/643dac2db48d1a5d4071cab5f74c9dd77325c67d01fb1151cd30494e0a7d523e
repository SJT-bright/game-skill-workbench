#!/usr/bin/env python3
"""audit_text_fit.py -- the six 蛋壳特工队 screenshots Saul sent on 2026-11-04, rebuilt as small dumps, plus the
layouts that must stay quiet. Run: python3 -m unittest test_text_fit"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_text_fit as T  # noqa: E402

W, H = 400.0, 800.0
FNT = '\n'.join(['info face="Digits" size=100', 'common lineHeight=100', 'page id=0 file="num.png"'] +
                ['char id=%d x=0 y=0 width=80 height=100 xoffset=0 yoffset=0 xadvance=%d page=0 chnl=15' % (48 + i, a)
                 for i, a in enumerate([106, 118, 121, 115, 133, 117, 117, 110, 119, 117])])


def node(path, order, x, y, w, h, **comps):
    return {'path': path, 'name': path.rsplit('/', 1)[-1], 'order': order, 'opacity': 1,
            'rect': [x / W, y / H, w / W, h / H], 'comps': comps}


def label(text, w_units, h_units, overflow=0, size=20, font='', kind='system', **kw):
    d = {'string': text, 'fontSize': size, 'actualFontSize': size, 'width': w_units, 'height': h_units,
         'overflow': overflow, 'font': font, 'font_kind': kind, 'color': [255, 255, 255]}
    d.update(kw)
    return d


def sprite(frame):
    return {'frame': frame, 'sliced': False, 'tiled': False}


class TextFitCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='textfit_'))
        (self.root / 'assets/font').mkdir(parents=True)
        (self.root / 'assets/font/num.fnt').write_text(FNT, encoding='utf-8')
        (self.root / 'dumps').mkdir()
        self.n = 0

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def dump(self, nodes, kind='popup', **extra):
        self.n += 1
        d = {'tool': 'ui_dump', 'schema': 1, 'screen': 'case%d' % self.n, 'kind': kind, 'canvas_css': [0, 0, W, H],
             'viewport': {'width': int(W), 'height': int(H)}, 'nodes': nodes}
        d.update(extra)
        (self.root / 'dumps' / ('%03d-ui-dump-case%d.json' % (self.n, self.n))).write_text(json.dumps(d), encoding='utf-8')

    def run_audit(self, **kw):
        return T.audit(self.root, [self.root / 'dumps'], **kw)

    def kinds(self, result):
        return sorted({f['kind'] for f in result['findings']})

    def png(self, rel, size, draw):
        from PIL import Image, ImageDraw
        p = self.root / 'assets' / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        im = Image.new('RGBA', size, (0, 0, 0, 0))
        draw(ImageDraw.Draw(im))
        im.save(p)
        return p


class SixScreenshots(TextFitCase):
    def test_mail_10000_runs_off_the_coin_card(self):
        # 邮件奖励: card 66 wide, SHRINK box 72 wide hanging 14 to the left, the 5 digits fill the box
        self.dump([node('Canvas/LetterLayer/ui/award/propItem/bg', 10, 123, 425, 66, 66, sprite=sprite('propbg1')),
                   node('Canvas/LetterLayer/ui/award/propItem/num', 12, 109, 470, 72, 18,
                        label=label('10000', 165, 40, overflow=2, size=32, font='num', kind='bitmap', spacingX=-2))])
        r = self.run_audit()
        self.assertIn('text_outside_plate', self.kinds(r), r['findings'])
        f = next(f for f in r['findings'] if f['kind'] == 'text_outside_plate')
        self.assertIn('左边', f['message'])

    def test_short_value_on_the_same_card_is_fine(self):
        self.dump([node('Canvas/LetterLayer/ui/award/propItem/bg', 10, 205, 425, 66, 66, sprite=sprite('propbg1')),
                   node('Canvas/LetterLayer/ui/award/propItem/num', 12, 191, 470, 72, 18,
                        label=label('200', 165, 40, overflow=2, size=32, font='num', kind='bitmap'))])
        self.assertEqual(self.run_audit()['findings'], [])

    def test_get_free_letters_under_the_video_icon_and_past_the_button(self):
        # 免费获得 → Get Free: yellow button 120 wide, video icon at its left, the text box centred on the button
        self.dump([node('Canvas/PatrolFastLayer/ui/btns/btnGet', 20, 40, 600, 120, 50, button={'interactable': True},
                        sprite=sprite('ui_btn_yellow')),
                   node('Canvas/PatrolFastLayer/ui/btns/btnGet/ui_video', 21, 46, 612, 26, 24, sprite=sprite('ui_video')),
                   node('Canvas/PatrolFastLayer/ui/btns/btnGet/Label', 22, 56, 610, 126, 30,
                        label=label('Get Free', 126, 30, overflow=0, size=26))])
        k = self.kinds(self.run_audit())
        self.assertIn('text_on_icon', k)
        self.assertIn('text_outside_plate', k)

    def test_quick_patrol_sentence_runs_off_the_panel_and_the_screen(self):
        self.dump([node('Canvas/PatrolFastLayer/ui/bg', 30, 20, 300, 360, 240, sprite=sprite('panel')),
                   node('Canvas/PatrolFastLayer/ui/bg/Label', 31, -10, 360, 430, 24,
                        label=label('Claim 300 minutes of Patrol rewards now', 430, 24, overflow=0, size=20))])
        k = self.kinds(self.run_audit())
        self.assertIn('text_outside_plate', k)
        self.assertIn('text_off_screen', k)

    def test_vip_watch_on_the_badge_once_the_row_is_laid_out(self):
        self.dump([node('Canvas/VipLayer/ui/top/bg', 40, 25, 300, 342, 82, sprite=sprite('bg2')),
                   node('Canvas/VipLayer/ui/top/rank', 41, 32, 309, 71, 62, sprite=sprite('rank')),
                   node('Canvas/VipLayer/ui/top/bar/info/text', 45, 55, 317, 56, 24, label=label('Watch', 103, 44, size=30)),
                   node('Canvas/VipLayer/ui/top/bar/info/val', 46, 116, 314, 28, 31, label=label('1', 51, 56, overflow=2, size=40,
                                                                                               font='num', kind='bitmap')),
                   node('Canvas/VipLayer/ui/top/bar/info/text', 47, 149, 317, 137, 24, label=label('times to reach', 251, 44, size=30))],
                  settle={'labels': 3, 'layouts': 1, 'moved': 3})
        r = self.run_audit()
        hit = [f for f in r['findings'] if f['kind'] == 'text_on_icon']
        self.assertTrue(hit and hit[0]['text'] == 'Watch' and hit[0]['picture'].endswith('/rank'), r['findings'])

    def test_vip_row_dumped_before_the_layout_ran(self):
        nodes = [node('Canvas/VipLayer/ui/top/bg', 40, 25, 300, 342, 82, sprite=sprite('bg2'))]
        for i, (word, w) in enumerate([('Watch', 56), ('times to reach', 137), ('VIP2', 60)]):
            nodes.append(node('Canvas/VipLayer/ui/top/bar/info/t%d' % i, 45 + i, 120 + 15 * i, 317, w, 24,
                              label=label(word, w * 1.83, 44, size=30)))
        self.dump(nodes)                                   # no "settle": an old ui_dump.js
        self.assertIn('unsettled_dump', self.kinds(self.run_audit()))

    def test_legendary_rewards_caption_past_the_painted_gold_bar(self):
        def poster(dr):
            dr.rectangle([0, 0, 399, 199], fill=(40, 80, 200, 255))
            dr.rectangle([120, 60, 280, 84], fill=(250, 190, 40, 255))          # the bar the caption must fit in
        self.png('shop/page1.png', (400, 200), poster)
        self.dump([node('Canvas/ShopLayer/content/page2', 30, 0, 100, 400, 200,
                        sprite={'frame': 'page1', 'frame_size': [400, 200], 'sliced': False, 'tiled': False}),
                   node('Canvas/ShopLayer/content/page2/Caption', 31, 130, 164, 220, 16,
                        label=label('DRAWS TO GUARANTEE', 220, 16, overflow=0, size=14))])
        r = self.run_audit()
        band = [f for f in r['findings'] if f['kind'] == 'text_off_band']
        self.assertTrue(band, r['findings'])
        self.assertIn('右边', band[0]['message'])

    def test_caption_inside_the_bar_is_fine(self):
        def poster(dr):
            dr.rectangle([0, 0, 399, 199], fill=(40, 80, 200, 255))
            dr.rectangle([60, 60, 340, 84], fill=(250, 190, 40, 255))
        self.png('shop/page1.png', (400, 200), poster)
        self.dump([node('Canvas/ShopLayer/content/page2', 30, 0, 100, 400, 200,
                        sprite={'frame': 'page1', 'frame_size': [400, 200], 'sliced': False, 'tiled': False}),
                   node('Canvas/ShopLayer/content/page2/Caption', 31, 100, 164, 200, 16,
                        label=label('DRAWS TO GUARANTEE', 200, 16, overflow=0, size=14))])
        self.assertEqual(self.run_audit()['findings'], [])

    def test_watch_ad_to_claim_card_under_the_hero(self):
        # RewardSkinLayer: itembg1 is a whole "WATCH AD TO CLAIM" word picture used as the card under each hero
        self.png('activityRes/itembg1.png', (259, 102), lambda dr: dr.rectangle([0, 0, 258, 101], fill=(255, 255, 255, 255)))
        audit = {'items': [{'kind': 'image', 'file': 'assets/activityRes/itembg1.png', 'ocr_text': ['WATCH AD', 'TO CLAIM']}]}
        (self.root / 'docs/english/chinese-audit').mkdir(parents=True)
        (self.root / 'docs/english/chinese-audit/audit.json').write_text(json.dumps(audit), encoding='utf-8')
        self.dump([node('Canvas/RewardSkinLayer/ui/item/bg', 10, 40, 300, 120, 48,
                        sprite={'frame': 'itembg1', 'frame_size': [259, 102], 'sliced': False, 'tiled': False}),
                   node('Canvas/RewardSkinLayer/ui/item/head', 11, 75, 280, 50, 70, sprite=sprite('hero1'))])
        r = self.run_audit()
        self.assertIn('words_covered', self.kinds(r), r['findings'])


class StaysQuiet(TextFitCase):
    def test_icon_with_a_gap_and_text_inside(self):
        self.dump([node('Canvas/Pop/btn', 20, 40, 600, 160, 50, button={'interactable': True}, sprite=sprite('btn')),
                   node('Canvas/Pop/btn/icon', 21, 50, 612, 26, 24, sprite=sprite('video')),
                   node('Canvas/Pop/btn/Label', 22, 84, 610, 100, 30, label=label('Get Free', 100, 30, size=26))])
        self.assertEqual(self.run_audit()['findings'], [])

    def test_page_under_a_popup_is_left_to_its_own_dump(self):
        self.dump([node('Canvas/Home/btnPlay', 5, 100, 700, 60, 40, button={'interactable': True}, sprite=sprite('play')),
                   node('Canvas/Home/btnPlay/Label', 6, 80, 705, 140, 30, label=label('PLAY NOW PLEASE', 140, 30)),
                   node('Canvas/Pop/bg', 20, 0, 0, 400, 800, sprite=sprite('dim')),
                   node('Canvas/Pop/panel', 21, 50, 200, 300, 300, sprite=sprite('panel')),
                   node('Canvas/Pop/panel/title', 22, 100, 220, 200, 30, label=label('Settings', 200, 30))])
        self.assertEqual(self.run_audit()['findings'], [])

    def test_count_on_the_rim_of_an_item_icon(self):
        self.png('icon/exp.png', (100, 100), lambda dr: dr.rectangle([0, 0, 99, 99], fill=(60, 200, 90, 255)))
        audit = {'items': [{'kind': 'image', 'file': 'assets/icon/exp.png', 'ocr_text': ['EXP']}]}
        (self.root / 'docs/english/chinese-audit').mkdir(parents=True)
        (self.root / 'docs/english/chinese-audit/audit.json').write_text(json.dumps(audit), encoding='utf-8')
        self.dump([node('Canvas/Pop/item/card', 10, 100, 300, 70, 70, sprite=sprite('card')),
                   node('Canvas/Pop/item/icon', 11, 105, 305, 60, 60,
                        sprite={'frame': 'exp', 'frame_size': [100, 100], 'sliced': False, 'tiled': False}),
                   node('Canvas/Pop/item/num', 12, 105, 352, 60, 14, label=label('76', 60, 14, overflow=2, size=12,
                                                                                font='num', kind='bitmap'))])
        self.assertNotIn('text_over_words', self.kinds(self.run_audit()))

    def test_scrolled_away_page_and_masked_rows(self):
        self.dump([node('Canvas/Shop/view/content/page3', 10, 500, 100, 300, 200, sprite=sprite('page')),
                   node('Canvas/Shop/view/content/page3/name', 11, 560, 150, 120, 20, label=label('COMMON', 120, 20)),
                   dict(node('Canvas/Shop/list/row/name', 12, 10, 50, 100, 20, label=label('Long item name', 100, 20)),
                        unclipped_rect=[10 / W, 40 / H, 100 / W, 30 / H])])
        self.assertEqual(self.run_audit()['findings'], [])

    def test_world_numbers_in_a_level_are_not_ui(self):
        self.dump([node('CanvasMap/map/monsterLayer/m1/monster/body', 10, 0, 500, 40, 40, sprite=sprite('monster')),
                   node('CanvasMap/map/numLayer/num', 30, -10, 510, 40, 20, label=label('46', 54, 27, overflow=2,
                                                                                       font='num', kind='bitmap'))],
                  kind='gameplay')
        self.assertEqual(self.run_audit()['findings'], [])


class BudgetAndLongest(TextFitCase):
    def test_plan_says_how_wide_the_button_must_be(self):
        self.dump([node('Canvas/Pop/btn', 20, 40, 600, 120, 50, button={'interactable': True}, sprite=sprite('btn')),
                   node('Canvas/Pop/btn/icon', 21, 46, 612, 26, 24, sprite=sprite('video')),
                   node('Canvas/Pop/btn/Label', 22, 76, 610, 80, 30, label=label('Get Free', 80, 30, size=26))])
        r = self.run_audit()
        row = next(b for b in r['budget'] if b['text'] == 'Get Free')
        self.assertGreater(row['need_plate_px'], row['text_px'] + row['icons_px'])
        self.assertIn('底板至少要', T.plan_markdown(r))

    def test_declared_longest_value_does_not_fit(self):
        (self.root / 'docs/art').mkdir(parents=True)
        (self.root / 'docs/art/longest-text.json').write_text(json.dumps(
            {'labels': [{'path': '*/propItem/num', 'text': '999999', 'why': '邮件奖励最多 6 位'}]}), encoding='utf-8')
        self.dump([node('Canvas/Letter/award/propItem/bg', 10, 120, 425, 70, 70, sprite=sprite('card')),
                   node('Canvas/Letter/award/propItem/num', 12, 125, 470, 60, 16,
                        label=label('200', 132, 35, overflow=2, size=24, font='num', kind='bitmap'))])
        self.assertIn('longest_does_not_fit', self.kinds(self.run_audit()))


class NumpyRuntime(TextFitCase):
    """简化.11.10: under Homebrew's python3 (no numpy) the gold-bar case found nothing and the audit passed."""

    def quiet_page(self):
        self.dump([node('Canvas/Pop/bg', 10, 40, 300, 320, 200, sprite=sprite('panel')),
                   node('Canvas/Pop/bg/Label', 11, 100, 380, 120, 30, label=label('Hello', 120, 30, size=24))])

    def test_without_any_numpy_python_the_audit_does_not_pass(self):
        saved = list(T._NUMPY_PYTHON)
        T._NUMPY_PYTHON[:] = ['']                       # as on a computer where no Python has numpy
        try:
            self.quiet_page()
            r = self.run_audit()
        finally:
            T._NUMPY_PYTHON[:] = saved
        self.assertFalse(r['passed'])
        self.assertIn('pixel_checks_unavailable', self.kinds(r))

    def test_the_audit_runs_with_numpy_here_or_in_another_python(self):
        self.assertNotEqual(T.numpy_python(), '', 'no Python with numpy on this computer')
        self.quiet_page()
        self.assertEqual(self.run_audit()['findings'], [])


class Fonts(unittest.TestCase):
    def test_fnt_advances(self):
        cfg = T.parse_fnt(FNT)
        self.assertAlmostEqual(T.bm_width(cfg, '10', 50, 0), (118 + 106) * 0.5)
        self.assertAlmostEqual(T.bm_width(cfg, '10', 50, -2), (118 + 106) * 0.5 - 2)


if __name__ == '__main__':
    unittest.main()
