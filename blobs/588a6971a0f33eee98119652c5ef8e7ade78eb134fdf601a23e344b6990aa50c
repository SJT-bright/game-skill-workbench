#!/usr/bin/env python3
"""Saul 2026-10-31 (香肠太难了 Redesign v2): dark button bodies, item icons on their own plate, dark pressed/disabled
states. Synthetic screenshots + dumps; the colours are the measured ones from the rejected and the fixed build."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    import numpy  # noqa: F401
    from PIL import Image, ImageDraw
except ImportError:                         # art_check.py reruns itself with a numpy python; so does this suite
    Image = None

import audit_button_colour as abc  # noqa: E402

W, H = 390, 844
SCENE = (226, 214, 190)          # light kitchen wall behind the buttons
TOMATO = (192, 79, 57)           # the rejected tile (L* 48)
RIM = (152, 83, 61)
ORANGE = (235, 133, 75)          # the original's PLAY / skin buttons (L* 66)
BRIGHT_RED = (231, 82, 57)       # an ordinary bright red close button (L* 55, V 0.91)
GOLD, GOLD_RIM = (240, 202, 99), (200, 140, 30)
NAVY = (43, 53, 85)


class Page:
    """A dump plus its screenshot, built node by node in draw order."""

    def __init__(self, kind='home', purpose='home'):
        self.img = Image.new('RGB', (W, H), SCENE)
        self.draw = ImageDraw.Draw(self.img)
        self.nodes, self.kind, self.purpose = [], kind, purpose
        self.add('Canvas', [0, 0, 1, 1], {}, depth=0)

    def add(self, name, rect, comps, depth=1, parent=None, opacity=1):
        nid = 'n%d' % len(self.nodes)
        anc = (parent['_audit_ancestors'] + [parent['id']]) if parent else ['n0'] if self.nodes else []
        path = (parent['path'] if parent else 'Canvas') + '/' + name if self.nodes else 'Canvas'
        n = {'path': path, 'id': nid, 'name': name, 'depth': depth, 'order': len(self.nodes), 'opacity': opacity,
             'rect': list(rect), 'screen': list(rect), 'comps': comps, 'ancestor_ids': anc, '_audit_ancestors': anc}
        self.nodes.append(n)
        return n

    def box(self, r):
        return (int(r[0] * W), int(r[1] * H), int((r[0] + r[2]) * W) - 1, int((r[1] + r[3]) * H) - 1)

    def button(self, name, rect, body, frame=None, rim=None, icon=(250, 245, 230), radius=14, kind='rounded'):
        b = self.add(name, rect, {'button': {'interactable': True}})
        pic = self.add('Art', rect, {'sprite': {'frame': frame or 'btn_' + name, 'frame_size': [160, 160]}}, 2, b)
        x0, y0, x1, y1 = self.box(rect)
        if rim:
            self.draw.rounded_rectangle((x0, y0, x1, y1), radius, fill=rim)
            self.draw.rounded_rectangle((x0 + 4, y0 + 4, x1 - 4, y1 - 6), radius - 3, fill=body)
        else:
            self.draw.rounded_rectangle((x0, y0, x1, y1), radius, fill=body)
        if icon:
            cx, cy, s = (x0 + x1) // 2, (y0 + y1) // 2, (x1 - x0) // 5
            self.draw.ellipse((cx - s, cy - s, cx + s, cy + s), fill=icon)
        return b, pic

    def dump(self):
        return {'tool': 'ui_dump', 'schema': 1, 'kind': self.kind, 'purpose': self.purpose,
                'canvas_css': [0, 0, W, H], 'page': {'width': W, 'height': H}, 'nodes': self.nodes}

    def problems(self, original=()):
        return abc.page_problems(self.dump(), self.nodes, self.img, original)


def coin(draw, box, rim=GOLD_RIM, face=GOLD):
    x0, y0, x1, y1 = box
    draw.ellipse(box, fill=rim)
    k = max(2, (x1 - x0) // 9)
    draw.ellipse((x0 + k, y0 + k, x1 - k, y1 - k), fill=face)


@unittest.skipIf(Image is None, 'needs numpy and Pillow')
class DarkButtons(unittest.TestCase):
    def test_rejected_tomato_tiles_are_dark_fixed_orange_is_not(self):
        p = Page()
        p.button('chooseSkin', [0.05, 0.40, 0.2, 0.093], TOMATO, 'icon_skins', rim=RIM)
        p.button('setNormal', [0.05, 0.05, 0.18, 0.083], TOMATO, 'icon_settings', rim=RIM)
        p.button('startGame', [0.2, 0.72, 0.6, 0.1], ORANGE, 'ksyx')
        p.button('close', [0.8, 0.05, 0.12, 0.055], BRIGHT_RED, 'btn_close')
        found, hints = p.problems()
        dark = [x for x in found if x.startswith('dark_button:')]
        self.assertEqual(len(dark), 2, found)
        self.assertTrue(all('icon_skins' in x or 'icon_settings' in x for x in dark))
        self.assertIn('砖红', dark[0])
        self.assertEqual(hints, [])

    def test_colour_rule(self):
        for rgb in (TOMATO, (154, 88, 60), (30, 58, 138), (46, 125, 50), (110, 70, 40), (90, 90, 90), (20, 20, 20),
                    (72, 133, 118), NAVY):
            self.assertTrue(abc.is_dark(rgb), rgb)
        for rgb in (ORANGE, BRIGHT_RED, (108, 173, 153), (198, 151, 90), (79, 124, 246), (227, 93, 110), (165, 107, 229),
                    (96, 144, 115), (110, 144, 92)):
            self.assertFalse(abc.is_dark(rgb), rgb)
        self.assertTrue(abc.near_dark((197, 85, 72)))        # the original's own close button: listed for the eye

    def test_gameplay_direction_keys_are_checked(self):
        p = Page('gameplay', 'gameplay')
        for i, name in enumerate(('leftBtn', 'rightBtn', 'jumpBtn')):
            p.button(name, [0.05 + i * 0.3, 0.85, 0.18, 0.083], TOMATO, 'icon_' + name, rim=RIM)
        found, _ = p.problems()
        self.assertEqual(len([x for x in found if x.startswith('dark_button:')]), 3, found)

    def test_scene_dimmed_behind_a_popup_and_half_transparent_buttons_are_not_reported(self):
        p = Page()
        p.button('shop', [0.1, 0.8, 0.2, 0.09], ORANGE, 'pf_game_shop')
        p.add('sprShopShadow', [0, 0, 1, 1], {'sprite': {'frame': 'default_sprite_splash', 'frame_size': [2, 2]}}, opacity=0.63)
        p.img = Image.blend(p.img, Image.new('RGB', (W, H), (0, 0, 0)), 0.63)
        p.draw = ImageDraw.Draw(p.img)
        b, pic = p.button('claim', [0.3, 0.5, 0.4, 0.08], ORANGE, 'btn_claim')
        found, _ = p.problems()
        self.assertEqual([x for x in found if x.startswith('dark_button:')], [])
        q = Page()
        b, pic = q.button('gift', [0.1, 0.3, 0.2, 0.09], NAVY, 'rg_ic_gift')
        pic['opacity'] = 0.4
        self.assertEqual(q.problems()[0], [])

    def test_english_original_buttons_are_kept(self):
        with tempfile.TemporaryDirectory() as t:
            proj = Path(t)
            (proj / 'docs/art').mkdir(parents=True)
            (proj / 'assets/ui').mkdir(parents=True)
            (proj / 'docs/board.txt').write_text('localize\n', encoding='utf-8')
            Image.new('RGBA', (8, 8), TOMATO + (255,)).save(proj / 'assets/ui/close.png')
            Image.new('RGBA', (8, 8), (191, 78, 57, 255)).save(proj / 'assets/ui/icon_new.png')
            for f in ('close', 'icon_new'):
                (proj / ('assets/ui/%s.png.meta' % f)).write_text(json.dumps(
                    {'subMetas': {f: {'uuid': 'u-' + f, 'trimX': 0, 'trimY': 0, 'width': 8, 'height': 8}}}), encoding='utf-8')
            p = Page()
            p.button('Close', [0.8, 0.05, 0.15, 0.07], TOMATO, 'close')
            p.button('Fresh', [0.1, 0.05, 0.15, 0.07], TOMATO, 'icon_new')
            missing = abc.OriginalArt(proj)
            found, _ = p.problems(missing)
            self.assertEqual(len(found), 2)
            self.assertTrue(all('base-assets.json' in x for x in found))     # says how to record the original
            digest = hashlib.sha256((proj / 'assets/ui/close.png').read_bytes()).hexdigest()
            (proj / 'docs/art/base-assets.json').write_text(json.dumps(
                {'base': '/orig', 'images': {'assets/ui/close.png': digest}, 'audio': {}}), encoding='utf-8')
            found, _ = p.problems(abc.OriginalArt(proj))
            self.assertEqual(len(found), 1, found)
            self.assertIn('icon_new', found[0])
            self.assertNotIn('base-assets.json', found[0])


@unittest.skipIf(Image is None, 'needs numpy and Pillow')
class IconPlates(unittest.TestCase):
    def test_coins_painted_on_a_tile_inside_the_icon_picture(self):
        p = Page()
        b = p.add('videoAddCoin', [0.05, 0.55, 0.22, 0.1], {'button': {'interactable': True}})
        r = [0.05, 0.55, 0.22, 0.1]
        p.add('SkinArtwork', r, {'sprite': {'frame': 'icon_coins', 'frame_size': [170, 170]}}, 2, b)
        x0, y0, x1, y1 = p.box(r)
        p.draw.rounded_rectangle((x0, y0, x1, y1), 22, fill=(214, 120, 96))      # a LIGHT tile: only icon_plate sees it
        coin(p.draw, (x0 + 18, y0 + 14, x1 - 18, y1 - 14))
        found, _ = p.problems()
        self.assertEqual([x.split(':')[0] for x in found], ['icon_plate'], found)

    def test_a_standalone_coin_with_a_rim_is_not_a_plate(self):
        p = Page()
        r = [0.4, 0.3, 0.12, 0.055]
        p.add('jb', r, {'sprite': {'frame': 'jb', 'frame_size': [64, 64]}})
        coin(p.draw, p.box(r))
        self.assertEqual(p.problems()[0], [])

    def test_coin_on_a_separate_disc_and_the_allowed_holders(self):
        p = Page('page', 'gifts')
        disc_r, coin_r = [0.40, 0.30, 0.2, 0.0924], [0.44, 0.318, 0.12, 0.0555]
        disc = p.add('Disc', disc_r, {'sprite': {'frame': 'disc', 'frame_size': [80, 80]}})
        p.draw.ellipse(p.box(disc_r), fill=NAVY)
        p.add('Coin', coin_r, {'sprite': {'frame': 'icon-coin', 'frame_size': [48, 48]}}, 2, disc)
        coin(p.draw, p.box(coin_r))
        # a resource capsule with its number and a BUY button with a price: both hold text, neither is a plate
        cap_r = [0.05, 0.03, 0.36, 0.05]
        cap = p.add('CoinBar', cap_r, {'sprite': {'frame': 'capsule', 'frame_size': [140, 40]}})
        p.draw.rounded_rectangle(p.box(cap_r), 18, fill=NAVY)
        p.add('Icon', [0.06, 0.035, 0.09, 0.04], {'sprite': {'frame': 'coin', 'frame_size': [40, 40]}}, 2, cap)
        coin(p.draw, p.box([0.06, 0.035, 0.09, 0.04]))
        p.add('Value', [0.17, 0.04, 0.2, 0.03], {'label': {'string': '120'}}, 2, cap)
        buy_r = [0.6, 0.6, 0.3, 0.12]
        buy = p.add('Buy', buy_r, {'button': {'interactable': True}, 'sprite': {'frame': 'btn_buy', 'frame_size': [120, 48]}})
        p.draw.rounded_rectangle(p.box(buy_r), 12, fill=ORANGE)
        p.add('Coin', [0.63, 0.63, 0.1, 0.05], {'sprite': {'frame': 'icon_coin', 'frame_size': [40, 40]}}, 2, buy)
        coin(p.draw, p.box([0.63, 0.63, 0.1, 0.05]))
        p.add('Price', [0.75, 0.64, 0.12, 0.03], {'label': {'string': 'BUY 100'}}, 2, buy)
        found, _ = p.problems()
        plates = [x for x in found if x.startswith('icon_plate:')]
        self.assertEqual(len(plates), 1, found)
        self.assertIn('Disc', plates[0])


@unittest.skipIf(Image is None, 'needs numpy and Pillow')
class ButtonStates(unittest.TestCase):
    def test_pressed_and_disabled_states_from_prefabs(self):
        with tempfile.TemporaryDirectory() as t:
            proj = Path(t)
            (proj / 'assets/ui').mkdir(parents=True)
            for name, colour in (('btn_ok', ORANGE + (255,)), ('btn_ok_down', (120, 40, 30, 255))):
                Image.new('RGBA', (32, 32), colour).save(proj / ('assets/ui/%s.png' % name))
                (proj / ('assets/ui/%s.png.meta' % name)).write_text(json.dumps(
                    {'subMetas': {name: {'uuid': 'f-' + name, 'trimX': 0, 'trimY': 0, 'width': 32, 'height': 32}}}),
                    encoding='utf-8')
            def prefab(transition, interactable=True, pressed=None, disabled=None):
                return [{'__type__': 'cc.Prefab'},
                        {'__type__': 'cc.Node', '_name': 'OkButton', '_color': {'r': 255, 'g': 255, 'b': 255}},
                        {'__type__': 'cc.Sprite', 'node': {'__id__': 1}, '_spriteFrame': {'__uuid__': 'f-btn_ok'}},
                        {'__type__': 'cc.Button', 'node': {'__id__': 1}, '_N$transition': transition,
                         '_N$interactable': interactable, '_N$target': {'__id__': 1},
                         '_N$pressedColor': {'__type__': 'cc.Color', 'r': pressed or 211, 'g': pressed or 211, 'b': pressed or 211},
                         '_N$disabledColor': {'__type__': 'cc.Color', 'r': disabled or 124, 'g': disabled or 124, 'b': disabled or 124},
                         '_N$pressedSprite': {'__uuid__': 'f-btn_ok_down'} if transition == 2 else None}]
            (proj / 'assets/ui/a.prefab').write_text(json.dumps(prefab(2)), encoding='utf-8')       # dark pressed picture
            (proj / 'assets/ui/b.prefab').write_text(json.dumps(prefab(1)), encoding='utf-8')       # default press tint
            (proj / 'assets/ui/c.prefab').write_text(json.dumps(prefab(1, interactable=False)), encoding='utf-8')
            found = abc.state_problems(proj)
            self.assertEqual(len(found), 2, found)
            self.assertTrue(any('a.prefab' in x and 'pressed' in x for x in found))
            self.assertTrue(any('c.prefab' in x and 'disabled' in x for x in found))


class Wiring(unittest.TestCase):
    def test_art_check_row_lists_every_kind(self):
        import art_check
        self.assertEqual(art_check.BUTTON_COLOUR_KINDS, set(abc.KINDS))

    @unittest.skipIf(Image is None, 'needs numpy and Pillow')
    def test_page_check_reports_it_once_per_button(self):
        import audit_page_richness as apr
        with tempfile.TemporaryDirectory() as t:
            p = Page('gameplay', 'gameplay')
            p.button('leftBtn', [0.05, 0.85, 0.18, 0.083], TOMATO, 'icon_left', rim=RIM)
            d = p.dump()
            for n in d['nodes']:
                n.pop('_audit_ancestors', None)
            f = Path(t) / 'gameplay-ui-dump-390x844.json'
            p.img.save(Path(t) / 'gameplay-ui-390x844.png')
            d['_file'] = str(f)
            problems, _ = apr.check(d, Image, None)
            self.assertEqual(len([x for x in problems if x.startswith('dark_button:')]), 1, problems)


if __name__ == '__main__':
    unittest.main()
