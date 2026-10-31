"""v7.8 W88: overlap blind spots (U11), home hero and HUD numbers (H11); W98: no popup-dim opacity limit (Saul 10-31).

    PYTHONDONTWRITEBYTECODE=1 python3 -B test_art_overlap_v78.py

Bad cases are shaped after the real dumps (Holly's Hay Hop v1/v2/v3 TikTok builds, 剪刀达人 v30 PlatformMission,
企鹅雪道 / 丛林荡藤 spin wheel); every bad case must be reported and the fixed one must pass.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import audit_page_richness as A  # noqa: E402

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    Image = None


def node(path, order, rect, opacity=1, **comps):
    return {'path': path, 'name': path.rsplit('/', 1)[-1], 'order': order, 'depth': path.count('/'),
            'rect': list(rect), 'opacity': opacity, 'comps': comps}


def kinds(problems):
    return [p.split(':', 1)[0] for p in problems]


class DimNotJudgedTests(unittest.TestCase):
    """Saul 10-31: no popup-dim opacity limit. Any full-screen input blocker hides the page below again (the
    pre-W88 rule), whatever its dim opacity (丛林荡藤 v4 spin wheel 80/255 is no longer reported)."""

    def setUp(self):
        self.under = node('Canvas/Home/BtnPlay', 1, [0.3, 0.6, 0.4, 0.08], button={'interactable': True})

    def shade(self, alpha):
        blocker = node('Canvas/Wheel', 5, [0, 0, 1, 1], block_input=True)
        dim = node('Canvas/Wheel/Dim', 6, [0, 0, 1, 1], opacity=alpha / 255.0, sprite={'frame': 'black'})
        return blocker, dim

    def test_no_opacity_limit_left(self):
        self.assertFalse(hasattr(A, 'DIM_OCCLUDE_OPACITY'))
        self.assertFalse(hasattr(A, 'shade_opacity'))
        from tiktok_finalize_steps import art_static
        self.assertFalse(hasattr(art_static, 'MIN_DIM_OPACITY'))

    def test_any_full_screen_blocker_occludes(self):
        for alpha in (0, 80, 180):
            blocker, dim = self.shade(alpha)
            masks = A.modal_masks([blocker, dim])
            self.assertEqual(masks, [blocker])
            self.assertTrue(A.fully_occluded(self.under, masks))
        g = node('Canvas/Mission', 5, [0, 0, 1, 1], block_input=True, graphics={'fillColor': [0, 0, 0, 112]})
        self.assertEqual(A.modal_masks([g]), [g])
        small = node('Canvas/Toast', 5, [0.1, 0.4, 0.8, 0.2], block_input=True)
        self.assertEqual(A.modal_masks([small]), [])

    def test_check_does_not_report_a_faint_dim(self):
        for alpha in (80, 180):
            blocker, dim = self.shade(alpha)
            panel = node('Canvas/Wheel/Panel', 7, [0.1, 0.2, 0.8, 0.5], sprite={'frame': 'panel'})
            d = {'kind': 'popup', 'purpose': 'other', 'nodes': [self.under, blocker, dim, panel],
                 '_file': '/nonexistent/x-ui-dump-a.json', 'page': {'width': 390, 'height': 844}}
            problems, _ = A.check(d)
            self.assertNotIn('faint_modal_dim', kinds(problems))
            self.assertFalse([p for p in problems if '/255' in p], problems)


class ControlOverFrameTests(unittest.TestCase):
    """U11 (a): a control drawn over another frame (Holly v1 in-game Settings over the leftover gameBox frame)."""

    def holly(self, with_box=True):
        nodes = [node('Canvas/gameLayer/gameView/info', 52, [0.273, 0.194, 0.453, 0.092])]
        if with_box:
            nodes += [node('Canvas/gameLayer/gameView/info/gameBox', 64, [0.059, 0.227, 0.157, 0.089]),
                      node('Canvas/gameLayer/gameView/info/gameBox/bg', 66, [0.059, 0.231, 0.157, 0.082],
                           sprite={'frame': 'gameIcon'})]
        nodes.append(node('Canvas/gameLayer/gameView/info/PauseSettings', 67, [0.059, 0.206, 0.123, 0.062],
                          sprite={'frame': 'sz'}, block_input=True))
        return nodes

    def test_holly_v1_settings_over_the_old_frame(self):
        out = A.control_picture_problems(self.holly(), [], [], 'gameplay')
        self.assertEqual(kinds(out), ['overlap_button_picture'], out)
        self.assertIn('gameBox/bg', out[0])

    def test_holly_v3_without_the_frame_passes(self):
        self.assertEqual(A.control_picture_problems(self.holly(False), [], [], 'gameplay'), [])

    def test_v775_only_compared_buttons_with_buttons(self):
        # the old overlap_buttons rule never saw this (no second button)
        nodes = self.holly()
        self.assertFalse([p for p in A.overlap_problems(nodes, [], []) if p.startswith('overlap_buttons')])

    def test_plate_badge_tag_and_cover_art_are_fine(self):
        btn = node('Canvas/Pop/BtnOk', 10, [0.3, 0.6, 0.4, 0.08], button={'interactable': True})
        panel = node('Canvas/Pop/Panel', 5, [0.1, 0.3, 0.8, 0.5], sprite={'frame': 'panel'})            # sits on it
        dot = node('Canvas/Pop/RedDot', 11, [0.66, 0.59, 0.03, 0.02], sprite={'frame': 'reddot_box'})    # badge
        tag = node('Canvas/Pop/UnlockTag', 12, [0.35, 0.665, 0.3, 0.035], sprite={'frame': 'btn_video'})  # hung below
        cover = node('Canvas/Pop/HeroCover', 9, [0.2, 0.4, 0.6, 0.25], sprite={'frame': 'cover-fruits'})  # not a frame
        self.assertEqual(A.control_picture_problems([panel, btn, dot, tag, cover], [btn], [], 'home'), [])

    def test_toast_over_a_button_is_reported(self):
        btn = node('Canvas/Revive/BtnRevive', 10, [0.1, 0.6, 0.8, 0.09], button={'interactable': True})
        toast = node('Canvas/Top/Toast/toast/bg', 30, [0.2, 0.58, 0.55, 0.08], sprite={'frame': 'rg_head'})
        self.assertEqual(kinds(A.control_picture_problems([btn, toast], [btn], [], 'popup')), ['overlap_button_picture'])

    def test_page_below_a_full_screen_blocker_is_not_compared(self):
        btn = node('Canvas/Home/Start', 3, [0.3, 0.6, 0.4, 0.08], button={'interactable': True})
        blocker = node('Canvas/Records/mask', 20, [0, 0, 1, 1], block_input=True, sprite={'frame': 'black'})
        card = node('Canvas/Records/allScore', 30, [0.3, 0.55, 0.4, 0.1], sprite={'frame': 'person_player_bg'})
        self.assertEqual(A.control_picture_problems([btn, blocker, card], [btn], [], 'popup', [blocker]), [])


class StackedTextTests(unittest.TestCase):
    """U11 (c): one text in two layers (剪刀达人 v26 status line; v27/v30 clear GeneratedLetters first)."""

    BASE = 'Main/viewLayer/HomeView/TikTokHomeEntries/PlatformMission/text'

    def letters(self, parent, order, y=0.6):
        group = node(parent + '/GeneratedLetters', order, [0.2, y, 0.6, 0.03], image_text={'string': 'CHECKING STATUS'})
        glyphs = [node(parent + '/GeneratedLetters/', order + 1 + i, [0.2 + 0.05 * i, y, 0.045, 0.03], sprite={'frame': c})
                  for i, c in enumerate('CHECKING')]
        return [group] + glyphs

    def test_v26_label_with_old_letters_on_top(self):
        label = node(self.BASE, 60, [0.167, 0.592, 0.667, 0.039], label={'string': 'Return task not completed yet.'})
        out = A.stacked_text_problems([label] + self.letters(self.BASE, 61))
        self.assertEqual(kinds(out), ['stacked_text_layers'], out)

    def test_two_letter_groups_on_one_text(self):
        host = node(self.BASE, 60, [0.167, 0.592, 0.667, 0.039], image_text={'string': 'CHECKING STATUS'})
        out = A.stacked_text_problems([host] + self.letters(self.BASE, 61) + self.letters(self.BASE, 80))
        self.assertEqual(kinds(out), ['stacked_text_layers'], out)

    def test_v27_one_layer_passes(self):
        label = node(self.BASE, 60, [0.167, 0.592, 0.667, 0.039], label={'string': 'Return task not completed yet.'})
        self.assertEqual(A.stacked_text_problems([label]), [])
        host = node(self.BASE, 60, [0.18, 0.289, 0.64, 0.039])          # label disabled while letters show
        self.assertEqual(A.stacked_text_problems([host] + self.letters(self.BASE, 61, 0.298)), [])

    def test_v775_exempted_the_parent_child_pair(self):
        label = node(self.BASE, 60, [0.167, 0.592, 0.667, 0.039], label={'string': 'Return task not completed yet.'})
        old = [p for p in A.overlap_problems([label] + self.letters(self.BASE, 61), [], [])
               if p.startswith(('overlap_text', 'overlap_text_picture'))]
        self.assertEqual(old, [])


@unittest.skipIf(Image is None, 'Pillow missing')
class BusyTextTests(unittest.TestCase):
    """U11 (b): plain text over a busy background (Holly v2 PROFILE over the fence; v3 plate)."""

    def page(self, tmp, busy, plate=False):
        im = Image.new('RGB', (390, 844), (236, 228, 205))
        draw = ImageDraw.Draw(im)
        if busy:          # painted farm scenery: grass, hay and fence posts in many shades behind the words
            import random
            rnd = random.Random(7)
            for _ in range(900):
                x, y = rnd.randrange(0, 390), rnd.randrange(630, 770)
                base = rnd.choice([(110, 70, 40), (120, 170, 60), (230, 190, 90), (70, 120, 50), (180, 210, 120)])
                shade = rnd.randrange(-50, 50)
                draw.rectangle((x, y, x + rnd.randrange(2, 7), y + rnd.randrange(2, 9)),
                               fill=tuple(max(0, min(255, c + shade)) for c in base))
        if plate:
            draw.rounded_rectangle((270, 682, 390, 718), 14, fill=(246, 236, 214))
        draw.text((295, 690), 'PROFILE', fill=(110, 70, 40))
        shot = Path(tmp) / '001-ui-home-390x844.png'
        im.save(shot)
        nodes = [node('Canvas/viewLayer/homeView/SkyBackdrop', 1, [0, 0, 1, 1], sprite={'frame': 'sky'}),
                 node('Canvas/viewLayer/homeView/profileMission', 10, [0.713, 0.756, 0.24, 0.092]),
                 node('Canvas/viewLayer/homeView/profileMission/Icon', 11, [0.779, 0.70, 0.109, 0.05], sprite={'frame': 'profile'}),
                 node('Canvas/viewLayer/homeView/profileMission/EntryCaption', 13, [0.733, 0.8175, 0.2, 0.025],
                      label={'string': 'Profile', 'font_kind': 'bitmap'})]
        if plate:
            nodes.insert(3, node('Canvas/viewLayer/homeView/profileMission/EntryCaptionPlate', 12,
                                 [0.69, 0.808, 0.31, 0.043], graphics={'fillColor': [246, 236, 214, 240]}))
        d = {'kind': 'home', 'purpose': 'home', 'nodes': nodes, '_file': str(Path(tmp) / '001-ui-dump-home-390x844.json'),
             'page': {'width': 390, 'height': 844}, 'canvas_css': [0, 0, 390, 844]}
        return d, nodes

    def test_busy_background_without_plate_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, nodes = self.page(tmp, busy=True)
            out = A.busy_text_problems(d, nodes, Image)
            self.assertEqual(kinds(out), ['busy_text_background'], out)

    def test_calm_background_or_plate_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, nodes = self.page(tmp, busy=False)
            self.assertEqual(A.busy_text_problems(d, nodes, Image), [])
        with tempfile.TemporaryDirectory() as tmp:
            d, nodes = self.page(tmp, busy=True, plate=True)
            self.assertEqual(A.busy_text_problems(d, nodes, Image), [])

    def test_check_runs_the_new_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, nodes = self.page(tmp, busy=True)
            self.assertIn('busy_text_background', kinds(A.check(d, Image)[0]))


class HeroAndHudTests(unittest.TestCase):
    """H11: 企鹅雪道美术 v3 home penguin half off screen; v4 score / currency digits ~1.3% of the screen high."""

    def setUp(self):
        A.HERO_GLOBS = []

    def home(self, hero_rect, unclipped=None, name='HeroPenguin'):
        hero = node('Canvas/Home/' + name, 5, hero_rect, sprite={'frame': 'penguin_idle'})
        if unclipped:
            hero['unclipped_rect'] = unclipped
        play = node('Canvas/Home/BtnPlay', 8, [0.2, 0.8, 0.6, 0.08], button={'interactable': True}, sprite={'frame': 'btn_play'})
        return {'purpose': 'home', 'kind': 'home'}, [hero, play]

    def test_v3_half_penguin_is_reported(self):
        d, nodes = self.home([0.3, 0.75, 0.4, 0.25], unclipped=[0.3, 0.75, 0.4, 0.5])     # bottom half below the screen
        self.assertEqual(kinds(A.hero_problems(d, nodes, nodes[1:])), ['home_hero_hidden'])

    def test_small_hero_is_reported_and_a_good_one_passes(self):
        d, nodes = self.home([0.4, 0.4, 0.15, 0.1])
        self.assertEqual(kinds(A.hero_problems(d, nodes, nodes[1:])), ['home_hero_small'])
        d, nodes = self.home([0.25, 0.35, 0.5, 0.3])
        self.assertEqual(A.hero_problems(d, nodes, nodes[1:]), [])

    def test_unknown_hero_is_reported_not_passed(self):
        d, nodes = self.home([0.4, 0.4, 0.01, 0.01], name='Spark')
        self.assertEqual(kinds(A.hero_problems(d, nodes, nodes[1:])), ['home_hero_unknown'])

    def test_hero_json_names_the_hero(self):
        A.HERO_GLOBS = ['penguin_*']
        d, nodes = self.home([0.25, 0.35, 0.5, 0.3], name='Thing')
        self.assertEqual(A.hero_problems(d, nodes, nodes[1:]), [])
        A.HERO_GLOBS = ['ingrid_*']
        self.assertEqual(kinds(A.hero_problems(d, nodes, nodes[1:])), ['home_hero_unknown'])

    def hud(self, font, box_h=40, rect_h=0.04):
        lab = node('Canvas/HUD/Score/Value', 5, [0.7, 0.05, 0.2, rect_h],
                   label={'string': '29', 'fontSize': font, 'actualFontSize': font, 'height': box_h})
        return {'kind': 'gameplay', 'purpose': 'other'}, [lab]

    def test_v4_small_score_is_reported(self):
        d, nodes = self.hud(16)        # 16/40 * 0.04 = 1.6% of the screen height (企鹅雪道 v4 ~1.8%)
        self.assertEqual(kinds(A.hud_digit_problems(d, nodes, [], None)), ['hud_digit_small'])

    def test_big_score_passes_and_field_numbers_are_not_hud(self):
        d, nodes = self.hud(40, rect_h=0.05)
        self.assertEqual(A.hud_digit_problems(d, nodes, [], None), [])
        tile = node('Canvas/Board/Tile/num', 6, [0.4, 0.5, 0.05, 0.02], label={'string': '8', 'fontSize': 20, 'height': 20})
        self.assertEqual(A.hud_digit_problems(d, nodes + [tile], [], None), [])

    def test_low_contrast_digits_are_reported(self):
        if Image is None:
            self.skipTest('Pillow missing')
        with tempfile.TemporaryDirectory() as tmp:
            im = Image.new('RGB', (390, 844), (200, 220, 235))
            ImageDraw.Draw(im).rectangle((296, 54, 324, 81), fill=(185, 205, 222))        # pale digits on pale sky
            im.save(Path(tmp) / '001-ui-run-390x844.png')
            d, nodes = self.hud(40, box_h=30, rect_h=0.05)
            d['_file'] = str(Path(tmp) / '001-ui-dump-run-390x844.json')
            nodes[0]['rect'] = [290 / 390, 50 / 844, 40 / 390, 35 / 844]
            self.assertIn('hud_digit_contrast', kinds(A.hud_digit_problems(d, nodes, [], Image)))


@unittest.skipIf(Image is None, 'Pillow missing')
class EdgeBandTests(unittest.TestCase):
    """H6 / AP 第五节: black bands at the top or bottom of revive / result pages."""

    def page(self, tmp, band):
        im = Image.new('RGB', (390, 844), (120, 170, 220))
        if band:
            ImageDraw.Draw(im).rectangle((0, 0, 390, 40), fill=(0, 0, 0))
        im.save(Path(tmp) / '001-ui-revive-390x844.png')
        return {'purpose': 'revive', '_file': str(Path(tmp) / '001-ui-dump-revive-390x844.json')}

    def test_band_reported_and_clean_page_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(kinds(A.edge_band_problems(self.page(tmp, True), Image)), ['black_edge_band'])
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(A.edge_band_problems(self.page(tmp, False), Image), [])


class HeroRowTests(unittest.TestCase):
    def test_h11_and_band_kinds_have_a_row(self):
        import art_check
        for k in ('home_hero_unknown', 'home_hero_hidden', 'home_hero_small', 'hud_digit_small', 'hud_digit_contrast',
                  'black_edge_band'):
            self.assertIn(k, art_check.HERO_HUD_KINDS)

    def test_new_kinds_are_in_the_overlap_row(self):
        import art_check
        for k in ('overlap_button_picture', 'busy_text_background', 'stacked_text_layers'):
            self.assertIn(k, art_check.OVERLAP_KINDS)
        self.assertNotIn('faint_modal_dim', art_check.OVERLAP_KINDS)     # Saul 10-31: dims are judged by eye


if __name__ == '__main__':
    unittest.main()
