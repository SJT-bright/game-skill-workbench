"""Art patch v3 (2026-10-31), after comparing art patch v2 with v7.8 on 725 dumps and 13 atlases: clear-colour bands on
any page (泡泡六角龙 ~9% black bars, 方块冲冲 black block above the sky; v7.8 black_edge_band reads only revive / result
pages and near-black rows), flat-atlas frames take the default role by name (BalloonRun txt_ picture text was refused as
foreign_alpha_island), 'panel' frames are no longer skipped by name (PaperCutKid panel_reward ornament cut). Fails on the
v7.8 snapshot."""
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

import audit_page_richness as A
import audit_atlas_slices as S


def node(path, order, rect, opacity=1, **comps):
    return {'path': path, 'name': path.rsplit('/', 1)[-1], 'order': order, 'depth': path.count('/'),
            'rect': list(rect), 'opacity': opacity, 'comps': comps}


def kinds(problems):
    return [p.split(':', 1)[0] for p in problems]


class ClearBand(unittest.TestCase):
    def shot(self, root, bg_top):
        img = Image.new('RGB', (390, 844), (0, 0, 0))
        d = ImageDraw.Draw(img)
        for y in range(int(bg_top * 844), int((1 - bg_top) * 844)):
            d.line([0, y, 389, y], fill=(80 + (y * 7) % 120, 150, 210))
        img.save(root / 'p.png')

    def check(self, purpose, bg_top, with_bg=True):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.shot(root, bg_top)
            nodes = [node('Canvas/Btn', 3, [0.3, 0.6, 0.4, 0.08], button={'interactable': True})]
            if with_bg:
                nodes.insert(0, node('Canvas/Bg', 1, [0, bg_top, 1, 1 - 2 * bg_top], sprite={'frame': 'bg_city'}))
            d = {'kind': 'ui', 'purpose': purpose, 'nodes': nodes, 'screenshot': 'p.png', '_file': str(root / 'p-ui-dump-a.json')}
            return A.clear_band_problems(d, nodes, Image)

    def test_thick_bars_on_any_page(self):                  # 泡泡六角龙: ~9% bars, purpose "result" / home / game
        self.assertEqual(len(self.check('result', 0.09)), 2)
        self.assertEqual(len(self.check('home', 0.09)), 2)

    def test_no_2d_background_is_not_judged(self):          # 行星射击 3D scene: nothing to stop short of the edge
        self.assertEqual(self.check('gameplay', 0.09, with_bg=False), [])


class FlatAtlasRoles(unittest.TestCase):
    def make(self, root):
        (root / 'assets/ui').mkdir(parents=True)
        img = Image.new('RGBA', (400, 200), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for i, x in enumerate((10, 60, 110)):                     # three separate words in one picture-text frame
            d.rectangle([x, 20, x + 35, 60], fill=(250, 200, 200, 255))
        d.rectangle([220, 40, 380, 180], fill=(30, 150, 140, 255))  # a panel whose top ornament is cut by its rect
        d.ellipse([230, 10, 280, 60], fill=(30, 150, 140, 255))
        img.save(root / 'assets/ui/sheet.png')
        atlas = {'btn_play': {'image': 'ui/sheet', 'x': 220, 'y': 40, 'w': 161, 'h': 141},
                 'txt_three_words': {'image': 'ui/sheet', 'x': 0, 'y': 10, 'w': 160, 'h': 60},
                 'panel_reward': {'image': 'ui/sheet', 'x': 215, 'y': 30, 'w': 170, 'h': 155}}
        p = root / 'assets/ui/atlas.json'
        p.write_text(json.dumps(atlas))
        return p

    def test_unprefixed_text_is_scope_body_and_panels_are_checked(self):
        with tempfile.TemporaryDirectory() as t:
            r = S.audit(self.make(Path(t)))
            roles = {f['frame']: f['role'] for f in r['frames']}
            self.assertEqual(roles.get('txt_three_words'), 'scope_body')
            self.assertEqual(roles.get('btn_play'), 'single_body')
            got = {(i['frame'], i['kind']) for i in r['issues']}
            self.assertNotIn(('txt_three_words', 'foreign_alpha_island'), got)
            self.assertIn(('panel_reward', 'connected_body_cut_by_rect'), got)


if __name__ == '__main__':
    unittest.main()
