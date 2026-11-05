"""P08 on Cocos 3.x + P12 import type, bind_art.py on synthetic projects (well under a second).
Not a runtime or art acceptance.

3.x fixtures follow the census cases on Creator 3.8.8 games (all_occurrences.jsonl squashed_image):
  * 05:501 潜水员下潜: an 80x206 skin picture put into a 200x200 node (cc.UITransform) -> squashed;
  * 04:181 蛋壳特工队: a new HEAL word picture with a wider trim box stretched over the old node -> flattened.
Old way (frame swapped and size untouched, or width/height typed by eye) -> --check reports it >10 % off.
New way (bind_art.py) -> the UITransform takes the picture's ratio inside the old box, trim matches.
Import type: a picture imported as a plain texture (3.x userData.type "texture", 2.4 "raw") is switched to a
sprite in the same run; other types are refused; a 3.x picture is not bound into a 2.4 file.
The 2.4 cases stay in test_bind_art.py.
"""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
from PIL import Image, ImageDraw
import bind_art as tool

SPLASH_3X = '7d8f9b89-4fd1-4c9f-a3ab-38ec7cded7ca@f9941'


def n3(name, parent, comps, children=(), scale=1.0):
    return {'__type__': 'cc.Node', '_name': name, '_objFlags': 0, '_parent': parent,
            '_children': [{'__id__': c} for c in children], '_active': True,
            '_components': [{'__id__': c} for c in comps], '_prefab': None,
            '_lpos': {'__type__': 'cc.Vec3', 'x': 0, 'y': 0, 'z': 0},
            '_lrot': {'__type__': 'cc.Quat', 'x': 0, 'y': 0, 'z': 0, 'w': 1},
            '_lscale': {'__type__': 'cc.Vec3', 'x': scale, 'y': scale, 'z': 1}, '_layer': 33554432}


def ut(nid, w, h):
    return {'__type__': 'cc.UITransform', '_name': '', 'node': {'__id__': nid}, '_enabled': True,
            '_contentSize': {'__type__': 'cc.Size', 'width': w, 'height': h},
            '_anchorPoint': {'__type__': 'cc.Vec2', 'x': 0.5, 'y': 0.5}}


def sp3(nid, uuid, trim=True, kind=0, size_mode=0):
    # as Creator 3.8.8 writes it (DeepDive start_menu.scene)
    return {'__type__': 'cc.Sprite', '_name': '', 'node': {'__id__': nid}, '_enabled': True,
            '_spriteFrame': {'__uuid__': uuid, '__expectedType__': 'cc.SpriteFrame'} if uuid else None,
            '_type': kind, '_fillType': 0, '_sizeMode': size_mode, '_isTrimmedMode': trim, '_atlas': None}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'assets' / 'ui').mkdir(parents=True)
        (self.root / 'package.json').write_text(json.dumps({'creator': {'version': '3.8.8'}}))
        self.old = self.png3('old_skin', (200, 200), (0, 0, 200, 200))

    def tearDown(self):
        self.tmp.cleanup()

    def draw(self, name, size, box):
        im = Image.new('RGBA', size, (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for y in range(box[1], box[3]):
            d.line((box[0], y, box[2] - 1, y), fill=(40 + y % 200, 120, 200, 255))
        p = self.root / 'assets' / 'ui' / (name + '.png')
        im.save(p)
        return p

    def png3(self, name, size, box, typ='sprite-frame'):
        """PNG + a Cocos 3.x image .meta as Creator 3.8.8 writes it (texture 6c48a, sprite-frame f9941)."""
        p = self.draw(name, size, box)
        uuid = '%08x-0000-4000-8000-%012x' % (abs(hash(name)) % 2 ** 32, len(name))
        subs = {'6c48a': {'importer': 'texture', 'uuid': uuid + '@6c48a', 'displayName': name, 'id': '6c48a',
                          'name': 'texture', 'userData': {'imageUuidOrDatabaseUri': uuid, 'isUuid': True},
                          'ver': '1.0.22', 'imported': True, 'files': ['.json'], 'subMetas': {}}}
        if typ == 'sprite-frame':
            subs['f9941'] = {'importer': 'sprite-frame', 'uuid': uuid + '@f9941', 'displayName': name, 'id': 'f9941',
                             'name': 'spriteFrame', 'ver': '1.0.12', 'imported': True, 'files': ['.json'], 'subMetas': {},
                             'userData': {'trimType': 'auto', 'trimThreshold': 1, 'rotated': False,
                                          'trimX': box[0], 'trimY': box[1], 'width': box[2] - box[0],
                                          'height': box[3] - box[1], 'rawWidth': size[0], 'rawHeight': size[1],
                                          'imageUuidOrDatabaseUri': uuid + '@6c48a', 'isUuid': True}}
        meta = {'ver': '1.0.27', 'importer': 'image', 'imported': True, 'uuid': uuid, 'files': ['.json', '.png'],
                'subMetas': subs, 'userData': {'type': typ, 'hasAlpha': True, 'redirect': uuid + '@6c48a'}}
        (p.parent / (p.name + '.meta')).write_text(json.dumps(meta))
        return uuid + '@f9941' if typ == 'sprite-frame' else uuid

    def png24(self, name, size, box, typ='sprite'):
        p = self.draw(name, size, box)
        uuid = '%08x-1111-4000-8000-%012x' % (abs(hash(name)) % 2 ** 32, len(name))
        subs = {}
        if typ == 'sprite':
            subs[name] = {'ver': '1.0.6', 'uuid': uuid + '-f', 'trimType': 'auto', 'trimThreshold': 1,
                          'trimX': box[0], 'trimY': box[1], 'width': box[2] - box[0], 'height': box[3] - box[1],
                          'rawWidth': size[0], 'rawHeight': size[1]}
        (p.parent / (p.name + '.meta')).write_text(json.dumps({'ver': '2.3.7', 'uuid': uuid, 'type': typ,
                                                               'subMetas': subs}))
        return uuid

    def meta(self, name):
        return json.loads((self.root / 'assets' / 'ui' / (name + '.png.meta')).read_text())

    # 0 prefab, 1 root, 2 root UITransform, 3 skin node, 4 its UITransform, 5 its Sprite
    def prefab(self, w=200, h=200, trim=True, kind=0, scale=1.0, extra=None, name='Popup.prefab', node='skin'):
        data = [{'__type__': 'cc.Prefab', '_name': 'Popup', 'data': {'__id__': 1}},
                n3('Popup', None, [2], [3]), ut(1, 720, 1280),
                n3(node, {'__id__': 1}, [4, 5], scale=scale), ut(3, w, h), sp3(3, self.old, trim, kind)]
        for fn in extra or []:
            fn(data)
        p = self.root / 'assets' / name
        p.write_text(json.dumps(data, indent=2))
        return p

    def scene(self, frame, w=200, h=200):
        """潜水员 skin preview in a 3.x scene: SceneAsset -> Scene -> Canvas -> skin_preview."""
        data = [{'__type__': 'cc.SceneAsset', '_name': 'start_menu', 'scene': {'__id__': 1}},
                {'__type__': 'cc.Scene', '_name': 'start_menu', '_parent': None, '_children': [{'__id__': 2}],
                 '_components': [], '_prefab': None},
                n3('Canvas', {'__id__': 1}, [3], [4]), ut(2, 720, 1280),
                n3('skin_preview', {'__id__': 2}, [5, 6]), ut(4, w, h), sp3(4, frame)]
        p = self.root / 'assets' / 'start_menu.scene'
        p.write_text(json.dumps(data, indent=2))
        return p

    def bind(self, image, prefab='assets/Popup.prefab', node='Popup/skin', dry=False, **kw):
        m = self.root / 'bind.json'
        b = {'prefab': prefab, 'node': node, 'image': 'assets/ui/%s.png' % image}
        b.update(kw)
        m.write_text(json.dumps({'bindings': [b]}))
        return tool.run_bind(self.root, m, '', dry)

    def doc(self, name='Popup.prefab'):
        return json.loads((self.root / 'assets' / name).read_text())


class Cocos3Ratio(Base):
    def test_diver_old_way_frame_swapped_in_scene_is_reported(self):
        tall = self.png3('diver_skin', (80, 206), (0, 0, 80, 206))
        self.scene(tall)
        bad = tool.run_check(self.root, [])
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]['file'], 'assets/start_menu.scene')
        self.assertEqual(bad[0]['node'], 'Canvas/skin_preview')
        self.assertGreater(bad[0]['ratio_diff'], 0.10)
        p = subprocess.run([sys.executable, str(Path(tool.__file__)), '--project', str(self.root), '--check'],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn('squashed', p.stdout)

    def test_old_way_width_height_typed_by_eye_is_reported(self):
        tall = self.png3('diver_skin', (80, 206), (0, 0, 80, 206))
        self.scene(tall, w=120, h=200)   # "about right" by eye: 0.6 instead of 0.388
        bad = tool.run_check(self.root, [])
        self.assertEqual(len(bad), 1)
        self.assertGreater(bad[0]['ratio_diff'], 0.10)

    def test_diver_bind_scene_contains_ratio(self):
        self.png3('diver_skin', (80, 206), (0, 0, 80, 206))
        self.scene(self.old)
        rec = self.bind('diver_skin', prefab='assets/start_menu.scene', node='Canvas/skin_preview')[0]
        d = self.doc('start_menu.scene')
        size, sp = d[5]['_contentSize'], d[6]
        self.assertNotIn('_contentSize', d[4])          # 3.x: size stays on the UITransform
        self.assertAlmostEqual(size['height'], 200, delta=0.1)
        self.assertAlmostEqual(size['width'], 77.7, delta=0.2)
        self.assertLess(abs((size['width'] / size['height']) / (80 / 206.0) - 1), 0.01)
        self.assertEqual(sp['_spriteFrame'], {'__uuid__': rec['frame_uuid'], '__expectedType__': 'cc.SpriteFrame'})
        self.assertTrue(rec['frame_uuid'].endswith('@f9941'))
        self.assertEqual(sp['_sizeMode'], 0)
        self.assertEqual(rec['engine'], '3.x')
        self.assertEqual(tool.run_check(self.root, []), [])
        log = json.loads((self.root / 'docs' / 'art' / 'bind_log.json').read_text())
        self.assertEqual(log['bindings']['assets/start_menu.scene#Canvas/skin_preview']['old_size'], [200.0, 200.0])

    def test_heal_word_with_wider_trim_box(self):
        # 400x200 PNG, the word HEAL visible 360x90: old way stretches the 4:1 word over the old 300x100 box
        heal = self.png3('heal', (400, 200), (20, 55, 380, 145))
        self.prefab(w=300, h=100, node='HEAL', extra=[lambda d: d[5].update(
            {'_spriteFrame': {'__uuid__': heal, '__expectedType__': 'cc.SpriteFrame'}})])
        bad = tool.run_check(self.root, [])
        self.assertEqual(len(bad), 1)
        self.assertGreater(bad[0]['ratio_diff'], 0.10)
        rec = self.bind('heal', node='Popup/HEAL')[0]
        d = self.doc()
        self.assertEqual([d[4]['_contentSize']['width'], d[4]['_contentSize']['height']], [300.0, 75.0])
        self.assertTrue(d[5]['_isTrimmedMode'])
        self.assertLess(rec['ratio_diff'], 0.01)
        self.assertEqual(tool.run_check(self.root, []), [])
        # by original: the node stands for the whole 2:1 PNG, trim off, drawn word still 4:1
        self.prefab(w=300, h=100, node='HEAL')
        rec = self.bind('heal', node='Popup/HEAL', by='original')[0]
        d = self.doc()
        self.assertFalse(d[5]['_isTrimmedMode'])
        self.assertEqual([d[4]['_contentSize']['width'], d[4]['_contentSize']['height']], [200.0, 100.0])
        self.assertLess(rec['ratio_diff'], 0.01)

    def test_upscale_with_lscale_refused_and_nothing_written(self):
        self.png3('mid', (120, 120), (0, 0, 120, 120))
        p = self.prefab(scale=1.5)
        before = p.read_bytes()
        with self.assertRaisesRegex(tool.BindError, 'upscale'):
            self.bind('mid')
        self.assertEqual(p.read_bytes(), before)

    def test_sliced_label_transform_and_nested_prefab(self):
        self.png3('panel', (200, 100), (0, 0, 200, 100))
        self.prefab(kind=1)
        rec = self.bind('panel')[0]
        self.assertIn('kept', rec)
        self.assertEqual(rec['new_size'], [200.0, 200.0])
        self.prefab(extra=[lambda d: (d.append({'__type__': 'cc.Label', 'node': {'__id__': 3}, '_string': 'PLAY'}),
                                      d[3]['_components'].append({'__id__': 6}))])
        with self.assertRaisesRegex(tool.BindError, 'Label'):
            self.bind('panel')
        self.prefab(extra=[lambda d: d[3].update({'_components': [{'__id__': 5}]})])
        with self.assertRaisesRegex(tool.BindError, 'UITransform'):
            self.bind('panel')
        self.prefab(extra=[lambda d: d.append({'__type__': 'cc.PrefabInstance', 'propertyOverrides': []})])
        with self.assertRaisesRegex(tool.BindError, 'nested prefab'):
            self.bind('panel', node='Popup/btn_in_nested')

    def test_cover_old_text_with_3x_builtin_splash(self):
        self.png3('new_btn', (200, 200), (0, 0, 200, 200))

        def patch(d):
            d[3]['_children'] = [{'__id__': 6}, {'__id__': 9}]
            d += [n3('cover', {'__id__': 3}, [7, 8]), ut(6, 150, 60), sp3(6, SPLASH_3X),
                  n3('price', {'__id__': 3}, [10, 11]), ut(9, 150, 60),
                  {'__type__': 'cc.Label', 'node': {'__id__': 9}, '_string': '50'}]
        self.prefab(extra=[patch])
        with self.assertRaisesRegex(tool.BindError, 'cover_old_text'):
            self.bind('new_btn')


class ImportType(Base):
    def test_3x_texture_meta_switched_to_sprite_frame(self):
        tex = self.png3('btn_claim', (300, 120), (10, 10, 290, 110), typ='texture')
        self.prefab(w=300, h=120)
        before = (self.root / 'assets' / 'ui' / 'btn_claim.png.meta').read_bytes()
        self.bind('btn_claim', dry=True)
        self.assertEqual((self.root / 'assets' / 'ui' / 'btn_claim.png.meta').read_bytes(), before)
        rec = self.bind('btn_claim')[0]
        m = self.meta('btn_claim')
        self.assertEqual(m['userData']['type'], 'sprite-frame')
        sub = m['subMetas']['f9941']
        self.assertEqual(sub['importer'], 'sprite-frame')
        self.assertEqual(sub['uuid'], tex + '@f9941')
        self.assertEqual(sub['userData']['imageUuidOrDatabaseUri'], tex + '@6c48a')
        self.assertEqual([sub['userData'][k] for k in ('trimX', 'trimY', 'width', 'height', 'rawWidth', 'rawHeight')],
                         [10, 10, 280, 100, 300, 120])
        self.assertIn('6c48a', m['subMetas'])         # the texture uuid stays for code that loads the texture
        self.assertEqual(rec['frame_uuid'], tex + '@f9941')
        self.assertIn('texture -> sprite-frame', rec['meta_fixed'])
        self.assertEqual(self.doc()[5]['_spriteFrame']['__uuid__'], tex + '@f9941')
        self.assertEqual(tool.run_check(self.root, []), [])

    def test_3x_other_type_refused(self):
        self.png3('bump', (128, 128), (0, 0, 128, 128), typ='normal map')
        p = self.prefab()
        before = p.read_bytes()
        with self.assertRaisesRegex(tool.BindError, 'normal map'):
            self.bind('bump')
        self.assertEqual(p.read_bytes(), before)
        self.assertEqual(self.meta('bump')['userData']['type'], 'normal map')

    def test_24_raw_meta_switched_to_sprite(self):
        (self.root / 'package.json').unlink()
        self.old = self.png24('old_btn', (200, 200), (0, 0, 200, 200))
        tex = self.png24('btn_play', (240, 120), (0, 0, 240, 120), typ='raw')
        data = [{'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
                {'__type__': 'cc.Node', '_name': 'Home', '_parent': None, '_children': [{'__id__': 2}],
                 '_components': [], '_contentSize': {'__type__': 'cc.Size', 'width': 720, 'height': 1280}},
                {'__type__': 'cc.Node', '_name': 'btn', '_parent': {'__id__': 1}, '_children': [],
                 '_components': [{'__id__': 3}], '_contentSize': {'__type__': 'cc.Size', 'width': 200, 'height': 200}},
                {'__type__': 'cc.Sprite', 'node': {'__id__': 2}, '_spriteFrame': {'__uuid__': self.old + '-f'},
                 '_type': 0, '_sizeMode': 0, '_isTrimmedMode': True}]
        (self.root / 'assets' / 'Home.prefab').write_text(json.dumps(data))
        dry = self.bind('btn_play', prefab='assets/Home.prefab', node='Home/btn', dry=True)[0]
        rec = self.bind('btn_play', prefab='assets/Home.prefab', node='Home/btn')[0]
        self.assertEqual(dry['frame_uuid'], rec['frame_uuid'])   # same uuid every run
        m = self.meta('btn_play')
        self.assertEqual(m['type'], 'sprite')
        sub = m['subMetas']['btn_play']
        self.assertEqual(sub['uuid'], rec['frame_uuid'])
        self.assertEqual(sub['rawTextureUuid'], tex)
        self.assertEqual(self.doc('Home.prefab')[3]['_spriteFrame'], {'__uuid__': rec['frame_uuid']})
        self.assertEqual(self.doc('Home.prefab')[2]['_contentSize']['height'], 100.0)
        self.assertIn('raw -> sprite', rec['meta_fixed'])

    def test_3x_picture_not_bound_into_24_file(self):
        self.png3('btn_ok', (200, 100), (0, 0, 200, 100))
        data = [{'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
                {'__type__': 'cc.Node', '_name': 'Home', '_parent': None, '_children': [{'__id__': 2}],
                 '_components': [], '_contentSize': {'__type__': 'cc.Size', 'width': 720, 'height': 1280}},
                {'__type__': 'cc.Node', '_name': 'btn', '_parent': {'__id__': 1}, '_children': [],
                 '_components': [{'__id__': 3}], '_contentSize': {'__type__': 'cc.Size', 'width': 200, 'height': 200}},
                {'__type__': 'cc.Sprite', 'node': {'__id__': 2}, '_spriteFrame': None, '_type': 0, '_sizeMode': 0,
                 '_isTrimmedMode': True}]
        (self.root / 'assets' / 'Home.prefab').write_text(json.dumps(data))
        with self.assertRaisesRegex(tool.BindError, '3.x but Home.prefab is a Cocos 2.4 file|Cocos 3.x but'):
            self.bind('btn_ok', prefab='assets/Home.prefab', node='Home/btn')

    def test_batch_with_meta_fix_is_all_or_nothing(self):
        self.png3('btn_claim', (300, 120), (0, 0, 300, 120), typ='texture')
        self.png3('tiny', (40, 40), (0, 0, 40, 40))
        p = self.prefab(extra=[lambda d: (d[1]['_children'].append({'__id__': 6}),
                                          d.extend([n3('icon', {'__id__': 1}, [7, 8]), ut(6, 200, 200),
                                                    sp3(6, self.old)]))])
        before_p = p.read_bytes()
        meta_p = self.root / 'assets' / 'ui' / 'btn_claim.png.meta'
        before_m = meta_p.read_bytes()
        m = self.root / 'bind.json'
        m.write_text(json.dumps({'bindings': [
            {'prefab': 'assets/Popup.prefab', 'node': 'Popup/skin', 'image': 'assets/ui/btn_claim.png'},
            {'prefab': 'assets/Popup.prefab', 'node': 'Popup/icon', 'image': 'assets/ui/tiny.png'}]}))
        p2 = subprocess.run([sys.executable, str(Path(tool.__file__)), '--project', str(self.root), '--map', str(m)],
                            capture_output=True, text=True)
        self.assertEqual(p2.returncode, 1, p2.stdout)
        self.assertIn('nothing written', p2.stdout)
        self.assertEqual(p.read_bytes(), before_p)
        self.assertEqual(meta_p.read_bytes(), before_m)


BTN_UUID = 'b7000000-0000-4000-8000-0000000000b7'
PANEL_UUID = 'a7000000-0000-4000-8000-0000000000a7'


class NestedPrefab3x(Base):
    """R4C / census squashed_image (3.x games): a button prefab placed in a scene as a nested instance. The scene
    stores only the instance root and cc.PrefabInstance.propertyOverrides; the old bind_art said "node not found"
    and the picture got swapped by hand (frame override, size untouched) -> squashed in the scene only."""

    def add(self, data, obj):
        data.append(obj)
        return len(data) - 1

    def button_prefab(self, inner=None):
        """Button.prefab: Btn (UITransform 300x300) / icon (UITransform 200x200, Sprite old)."""
        d = [{'__type__': 'cc.Prefab', '_name': 'Button', 'data': {'__id__': 1}}]
        root = self.add(d, n3('Btn', None, []))
        icon = self.add(d, n3('icon', {'__id__': root}, []))
        d[root]['_children'] = [{'__id__': icon}]
        for nid, fid in ((root, 'rootF'), (icon, 'iconF')):
            pi = self.add(d, {'__type__': 'cc.PrefabInfo', 'root': {'__id__': root}, 'asset': {'__id__': 0},
                              'fileId': fid, 'instance': None})
            d[nid]['_prefab'] = {'__id__': pi}
        for nid, comp, fid in ((root, ut(root, 300, 300), 'rootUT'), (icon, ut(icon, 200, 200), 'iconUT'),
                               (icon, sp3(icon, self.old), 'iconSP')):
            cp = self.add(d, {'__type__': 'cc.CompPrefabInfo', 'fileId': fid})
            comp['__prefab'] = {'__id__': cp}
            d[nid]['_components'].append({'__id__': self.add(d, comp)})
        p = self.root / 'assets' / 'Button.prefab'
        p.write_text(json.dumps(d, indent=2))
        (self.root / 'assets' / 'Button.prefab.meta').write_text(json.dumps(
            {'ver': '1.1.50', 'importer': 'prefab', 'imported': True, 'uuid': BTN_UUID, 'files': ['.json'],
             'subMetas': {}, 'userData': {'syncNodeName': 'Btn'}}))
        return p

    def instance(self, d, parent, asset, name, inst_fid, root_fid='rootF', overrides=()):
        """A nested instance as Creator 3.8 writes it: a bare cc.Node + PrefabInfo + PrefabInstance + overrides."""
        node = self.add(d, {'__type__': 'cc.Node', '_objFlags': 0, '_parent': {'__id__': parent},
                            '_prefab': None, '__editorExtras__': {}})
        d[parent].setdefault('_children', []).append({'__id__': node})
        inst = self.add(d, {'__type__': 'cc.PrefabInstance', 'fileId': inst_fid, 'prefabRootNode': None,
                            'mountedChildren': [], 'mountedComponents': [], 'propertyOverrides': [],
                            'removedComponents': []})
        pi = self.add(d, {'__type__': 'cc.PrefabInfo', 'root': {'__id__': node},
                          'asset': {'__uuid__': asset, '__expectedType__': 'cc.Prefab'}, 'fileId': root_fid,
                          'instance': {'__id__': inst}, 'targetOverrides': None})
        d[node]['_prefab'] = {'__id__': pi}
        for lid, path, v in [([root_fid], ['_name'], name)] + list(overrides):
            o = self.add(d, {'__type__': 'CCPropertyOverrideInfo', 'targetInfo': None, 'propertyPath': path,
                             'value': v})
            d[o]['targetInfo'] = {'__id__': self.add(d, {'__type__': 'cc.TargetInfo', 'localID': lid})}
            d[inst]['propertyOverrides'].append({'__id__': o})
        return node, inst

    def home_scene(self, overrides=(), panel=False):
        d = [{'__type__': 'cc.SceneAsset', '_name': 'home', 'scene': {'__id__': 1}},
             {'__type__': 'cc.Scene', '_name': 'home', '_parent': None, '_children': [], '_components': [],
              '_prefab': None}]
        canvas = self.add(d, n3('Canvas', {'__id__': 1}, []))
        d[1]['_children'].append({'__id__': canvas})
        d[canvas]['_components'].append({'__id__': self.add(d, ut(canvas, 720, 1280))})
        if panel:
            self.instance(d, canvas, PANEL_UUID, 'Panel', 'outerInst', root_fid='panelRootF', overrides=overrides)
        else:
            self.instance(d, canvas, BTN_UUID, 'PlayBtn', 'instF', overrides=overrides)
        p = self.root / 'assets' / 'home.scene'
        p.write_text(json.dumps(d, indent=2))
        return p

    def panel_prefab(self):
        """Panel.prefab holds a nested Button instance (instance fileId innerInst) named PlayBtn."""
        d = [{'__type__': 'cc.Prefab', '_name': 'Panel', 'data': {'__id__': 1}}]
        root = self.add(d, n3('Panel', None, []))
        pi = self.add(d, {'__type__': 'cc.PrefabInfo', 'root': {'__id__': root}, 'asset': {'__id__': 0},
                          'fileId': 'panelRootF', 'instance': None})
        d[root]['_prefab'] = {'__id__': pi}
        self.instance(d, root, BTN_UUID, 'PlayBtn', 'innerInst')
        (self.root / 'assets' / 'Panel.prefab').write_text(json.dumps(d, indent=2))
        (self.root / 'assets' / 'Panel.prefab.meta').write_text(json.dumps(
            {'ver': '1.1.50', 'importer': 'prefab', 'uuid': PANEL_UUID, 'subMetas': {}, 'userData': {}}))

    def overrides(self, d):
        out = {}
        for o in d:
            if o.get('__type__') == 'CCPropertyOverrideInfo':
                out.setdefault((tuple(d[o['targetInfo']['__id__']]['localID']), tuple(o['propertyPath'])), []).append(
                    o['value'])
        return out

    def test_old_way_frame_override_only_is_reported_in_scene(self):
        tall = self.png3('diver_skin', (80, 206), (0, 0, 80, 206))
        btn = self.button_prefab()
        self.home_scene(overrides=[(['iconSP'], ['_spriteFrame'],
                                    {'__uuid__': tall, '__expectedType__': 'cc.SpriteFrame'})])
        bad = tool.run_check(self.root, [])
        self.assertEqual([(b['file'], b['node']) for b in bad], [('assets/home.scene', 'Canvas/PlayBtn/icon')])
        self.assertGreater(bad[0]['ratio_diff'], 0.10)
        self.assertEqual(tool.run_check(self.root, [btn]), [])   # the button prefab itself is fine

    def test_bind_writes_property_overrides_not_the_nested_prefab(self):
        self.png3('diver_skin', (80, 206), (0, 0, 80, 206))
        btn = self.button_prefab()
        before = btn.read_bytes()
        self.home_scene()
        rec = self.bind('diver_skin', prefab='assets/home.scene', node='Canvas/PlayBtn/icon')[0]
        self.assertEqual(btn.read_bytes(), before)               # nested .prefab untouched
        ov = self.overrides(self.doc('home.scene'))
        size = ov[(('iconUT',), ('_contentSize',))][0]
        self.assertAlmostEqual(size['height'], 200, delta=0.1)
        self.assertAlmostEqual(size['width'], 77.7, delta=0.2)
        self.assertEqual(ov[(('iconSP',), ('_spriteFrame',))][0],
                         {'__uuid__': rec['frame_uuid'], '__expectedType__': 'cc.SpriteFrame'})
        self.assertEqual(rec['nested']['prefab'], 'assets/Button.prefab')
        self.assertEqual(rec['prefab'], 'assets/home.scene')
        self.assertEqual(tool.run_check(self.root, []), [])
        # bind again with another picture: the same overrides are replaced, not duplicated
        self.png3('wide', (300, 100), (0, 0, 300, 100))
        self.bind('wide', prefab='assets/home.scene', node='Canvas/PlayBtn/icon')
        ov = self.overrides(self.doc('home.scene'))
        self.assertEqual(len(ov[(('iconUT',), ('_contentSize',))]), 1)
        self.assertEqual(len(ov[(('iconSP',), ('_spriteFrame',))]), 1)
        self.assertEqual(tool.run_check(self.root, []), [])

    def test_existing_size_override_is_the_old_box(self):
        self.png3('diver_skin', (80, 206), (0, 0, 80, 206))
        self.button_prefab()
        self.home_scene(overrides=[(['iconUT'], ['_contentSize'], {'__type__': 'cc.Size', 'width': 100, 'height': 100})])
        rec = self.bind('diver_skin', prefab='assets/home.scene', node='Canvas/PlayBtn/icon')[0]
        self.assertEqual(rec['old_size'], [100.0, 100.0])
        self.assertAlmostEqual(rec['new_size'][1], 100.0, delta=0.1)

    def test_instance_root_scale_override_counts_for_upscale(self):
        self.png3('mid', (120, 120), (0, 0, 120, 120))
        self.button_prefab()
        p = self.home_scene(overrides=[(['rootF'], ['_lscale'], {'__type__': 'cc.Vec3', 'x': 1.5, 'y': 1.5, 'z': 1})])
        before = p.read_bytes()
        with self.assertRaisesRegex(tool.BindError, 'upscale'):
            self.bind('mid', prefab='assets/home.scene', node='Canvas/PlayBtn/icon')
        self.assertEqual(p.read_bytes(), before)

    def test_two_levels_local_id_path(self):
        self.png3('diver_skin', (80, 206), (0, 0, 80, 206))
        self.button_prefab()
        self.panel_prefab()
        self.home_scene(panel=True)
        self.bind('diver_skin', prefab='assets/home.scene', node='Canvas/Panel/PlayBtn/icon')
        ov = self.overrides(self.doc('home.scene'))
        self.assertIn((('innerInst', 'iconUT'), ('_contentSize',)), ov)
        self.assertIn((('innerInst', 'iconSP'), ('_spriteFrame',)), ov)
        self.assertEqual(tool.run_check(self.root, []), [])

    def test_missing_nested_asset_named(self):
        self.png3('diver_skin', (80, 206), (0, 0, 80, 206))
        self.home_scene()   # Button.prefab not in the project
        with self.assertRaisesRegex(tool.BindError, 'nested prefab'):
            self.bind('diver_skin', prefab='assets/home.scene', node='Canvas/PlayBtn/icon')


if __name__ == '__main__':
    unittest.main()
