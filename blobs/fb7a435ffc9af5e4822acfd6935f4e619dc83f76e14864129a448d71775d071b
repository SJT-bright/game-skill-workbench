"""v7.8 W88: colliders without a visible picture (H6 static part) and the wider atlas slice scope (H9（补）).

    PYTHONDONTWRITEBYTECODE=1 python3 -B test_art_static_v78.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from tiktok_finalize_steps import art_static as S  # noqa: E402


def paper_prefab(sprite_enabled=True, frame=True, collider='cc.PhysicsPolygonCollider', sensor=False, sprite=True):
    """剪刀达人 paperItem.prefab shape: root with RigidBody + collider, child `img` with the Sprite."""
    objs = [{'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
            {'__type__': 'cc.Node', '_name': 'paperItem', '_active': True, '_children': [{'__id__': 2}],
             '_components': [{'__id__': 5}, {'__id__': 6}], '_contentSize': {'width': 200, 'height': 40}},
            {'__type__': 'cc.Node', '_name': 'img', '_active': True, '_parent': {'__id__': 1}, '_children': [],
             '_components': [{'__id__': 3}] if sprite else [], '_contentSize': {'width': 200, 'height': 40}},
            {'__type__': 'cc.Sprite', '_enabled': sprite_enabled, 'node': {'__id__': 2}, '_sizeMode': 1,
             '_spriteFrame': {'__uuid__': 'f-1'} if frame else None},
            {'__type__': 'cc.PrefabInfo'},
            {'__type__': 'cc.RigidBody', '_enabled': True},
            {'__type__': collider, '_enabled': True, '_sensor': sensor}]
    objs[1]['_parent'] = None
    return json.dumps(objs).encode()


class HiddenBodyTests(unittest.TestCase):
    def scan(self, **kw):
        return S.scan({'assets/prefab/paperItem.prefab': paper_prefab(**kw)})

    def test_v17_sprite_switched_off_is_found(self):
        found = self.scan(sprite_enabled=False)
        self.assertEqual([h['node'] for h in found['hidden_bodies']], ['paperItem'])
        self.assertIn('switched off', found['hidden_bodies'][0]['sprites'])

    def test_missing_picture_is_found(self):
        self.assertEqual(len(self.scan(frame=False)['hidden_bodies']), 1)

    def test_v18_1_fixed_board_passes(self):
        self.assertEqual(self.scan()['hidden_bodies'], [])

    def test_sensor_and_sprite_less_walls_are_fine(self):
        self.assertEqual(self.scan(sprite_enabled=False, sensor=True)['hidden_bodies'], [])
        self.assertEqual(self.scan(sprite=False)['hidden_bodies'], [])

    def test_3x_collider_names(self):
        self.assertEqual(len(self.scan(sprite_enabled=False, collider='cc.BoxCollider2D')['hidden_bodies']), 1)

    def test_policy_and_board(self):
        found = self.scan(sprite_enabled=False)
        ids = lambda **kw: [(f['id'], f['level']) for f in S.findings(found, **kw)]
        self.assertIn(('K_art_hidden_body', 'block'), ids(policy='new', board='remake'))
        self.assertIn(('K_W_art_hidden_body', 'warn'), ids(policy='new', board='localize'))
        self.assertIn(('K_W_art_hidden_body', 'warn'), ids(policy='legacy', board='remake'))

    def test_aspect_only_warns_a_localized_game(self):
        """Saul 10-30 (v7.8): every art_static finding blocks only a new remake game; a localized game keeps its
        original art and gets warnings, like ART_receipt. Saul 10-31: no dim finding at all."""
        found = {'hidden_bodies': [], 'exempt': [], 'unreadable': [],
                 'squashed': [{'file': 'assets/ui/pop.prefab', 'node': 'btn', 'frame': 'btn', 'image': 'btn.png',
                               'meta': 'btn.png.meta', 'frame_size': [255, 296], 'node_size': [120, 90],
                               'scale': [1, 1], 'stretch': 1.55}]}
        ids = lambda **kw: [(f['id'], f['level']) for f in S.findings(found, **kw)]
        self.assertEqual(ids(policy='new', board='remake'), [('K_art_aspect', 'block')])
        self.assertEqual(ids(policy='new', board=None), [('K_art_aspect', 'block')])
        self.assertEqual(ids(policy='new', board='localize'), [('K_W_art_aspect', 'warn')])
        self.assertEqual(ids(policy='legacy', board='remake'), [('K_W_art_aspect', 'warn')])

    def test_exemption_with_a_why(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'assets/prefab').mkdir(parents=True)
            (root / 'assets/prefab/paperItem.prefab').write_bytes(paper_prefab(sprite_enabled=False))
            (root / 'docs/art').mkdir(parents=True)
            (root / 'docs/art/static-exempt.json').write_text(json.dumps(
                {'nodes': [{'file': '*paperItem.prefab', 'node': 'paperItem', 'why': 'code draws the board at run time'}]}))
            found = S.scan(S.project_files(root), root)
            self.assertEqual(found['hidden_bodies'], [])
            self.assertEqual(len(found['exempt']), 1)


class AtlasScopeTests(unittest.TestCase):
    """Ingrid's Snowball Stack r3: caption_* / closet / snowball carried a neighbour's sliver; tilesets must pass."""

    def setUp(self):
        from PIL import Image, ImageDraw
        self.tmp = tempfile.TemporaryDirectory()
        p = Path(self.tmp.name)
        im = Image.new('RGBA', (400, 120))
        d = ImageDraw.Draw(im)
        d.ellipse((10, 20, 90, 100), fill='white')                 # snowball (game piece) with a sliver on its top edge
        d.rectangle((40, 4, 70, 7), fill='black')
        d.ellipse((110, 20, 190, 100), fill='white')               # clean snowball
        d.rectangle((210, 10, 290, 110), fill='#88cc66')           # opaque ground tiles, joined
        d.rectangle((290, 10, 370, 110), fill='#88cc66')
        d.text((120, 104), 'AB', fill='white')                     # detached letters inside a text slice: allowed
        im.save(p / 'sheet.png')
        self.manifest = p / 'frames.json'
        self.frames = {'snowball': {'texture': 'sheet', 'rect': [8, 4, 86, 98]},
                       'snowball_ok': {'texture': 'sheet', 'rect': [108, 12, 86, 92]},
                       'caption_ab': {'texture': 'sheet', 'rect': [112, 100, 30, 18]},
                       'grass_a': {'texture': 'sheet', 'rect': [210, 10, 80, 100]},
                       'piece_b': {'texture': 'sheet', 'rect': [290, 10, 80, 100]}}

    def tearDown(self):
        self.tmp.cleanup()

    def run_audit(self, frames):
        from audit_atlas_slices import audit
        self.manifest.write_text(json.dumps({'textures': {'sheet': {}}, 'frames': frames}))
        return audit(self.manifest)

    def test_unprefixed_piece_sliver_is_reported(self):
        r = self.run_audit(self.frames)
        bad = {(i['frame'], i['kind']) for i in r['issues']}
        self.assertEqual(bad, {('snowball', 'edge_fragment')}, r['issues'])

    def test_clean_pieces_text_and_tiles_pass(self):
        frames = {k: v for k, v in self.frames.items() if k != 'snowball'}
        r = self.run_audit(frames)
        self.assertTrue(r['passed'], r['issues'])
        reasons = {x['frame']: x['reason'] for x in r['skipped']}
        self.assertIn('grass_a', reasons)          # tile name
        self.assertIn('piece_b', reasons)          # opaque to all four edges

    def test_cut_body_of_an_unprefixed_slice_is_reported(self):
        frames = {'snowball_ok': {'texture': 'sheet', 'rect': [108, 12, 60, 92]}}
        self.assertIn('connected_body_cut_by_rect', {i['kind'] for i in self.run_audit(frames)['issues']})

    def test_tileset_role_skips(self):
        frames = {'piece_x': {'texture': 'sheet', 'rect': [200, 10, 60, 100], 'slice_role': 'tileset'}}
        r = self.run_audit(frames)
        self.assertTrue(r['passed'])
        self.assertEqual(r['skipped'][0]['reason'], 'slice_role tileset')


if __name__ == '__main__':
    unittest.main()
