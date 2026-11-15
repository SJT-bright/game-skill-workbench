"""P08 bind_art.py on a synthetic Cocos 2.4 project (a few seconds). Not a runtime or art acceptance.

Old way (a new frame dropped into the old 200x200 box, width/height untouched) -> --check reports it >10 % off.
New way (bind_art.py) -> node takes the picture's ratio inside the old box, trim matches how the node is sized,
too-small pictures and patched-over old words are refused, the old and new box are recorded.
"""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
from PIL import Image, ImageDraw
import bind_art as tool

FLAT = 'a23235d1-15db-4b95-8439-a2e005bfff91'


def node(name, parent, comps, children=(), w=200, h=200, scale=1.0):
    return {'__type__': 'cc.Node', '_name': name, '_parent': parent, '_children': [{'__id__': c} for c in children],
            '_components': [{'__id__': c} for c in comps], '_contentSize': {'__type__': 'cc.Size', 'width': w, 'height': h},
            '_trs': {'__type__': 'TypedArray', 'ctor': 'Float64Array', 'array': [0, 0, 0, 0, 0, 0, 1, scale, scale, 1]}}


def sprite(nid, uuid, trim=True, kind=0):
    return {'__type__': 'cc.Sprite', 'node': {'__id__': nid}, '_spriteFrame': {'__uuid__': uuid} if uuid else None,
            '_type': kind, '_sizeMode': 0, '_isTrimmedMode': trim}


class BindArt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'assets' / 'ui').mkdir(parents=True)
        self.old = self.png('old_btn', (200, 200), (0, 0, 200, 200))

    def tearDown(self):
        self.tmp.cleanup()

    def png(self, name, size, box, flat=False):
        """PNG with visible content in box (rest transparent) + a Cocos 2.4 .meta as the importer writes it."""
        im = Image.new('RGBA', size, (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        if flat:
            d.rectangle((box[0], box[1], box[2] - 1, box[3] - 1), fill=(230, 60, 60, 255))
        else:
            for y in range(box[1], box[3]):
                d.line((box[0], y, box[2] - 1, y), fill=(40 + y % 200, 120, 200, 255))
        p = self.root / 'assets' / 'ui' / (name + '.png')
        im.save(p)
        uuid = '%08x-0000-4000-8000-%012x' % (abs(hash(name)) % 2 ** 32, len(name))
        sub = {'ver': '1.0.6', 'uuid': uuid, 'trimType': 'auto', 'trimThreshold': 1, 'trimX': box[0], 'trimY': box[1],
               'width': box[2] - box[0], 'height': box[3] - box[1], 'rawWidth': size[0], 'rawHeight': size[1]}
        meta = {'ver': '2.3.7', 'uuid': uuid + '-tex', 'type': 'sprite', 'subMetas': {name: sub}}
        (self.root / 'assets' / 'ui' / (name + '.png.meta')).write_text(json.dumps(meta))
        return uuid

    def prefab(self, extra=None, trim=True, kind=0, scale=1.0):
        # 0 prefab, 1 root, 2 btn (old picture 200x200), 3 btn sprite
        data = [{'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
                node('Popup', None, [], [2], 720, 1280),
                node('btn', {'__id__': 1}, [3], scale=scale),
                sprite(2, self.old, trim, kind)]
        for fn in extra or []:
            fn(data)
        p = self.root / 'assets' / 'Popup.prefab'
        p.write_text(json.dumps(data, indent=2))
        return p

    def bind(self, image, **kw):
        m = self.root / 'bind.json'
        b = {'prefab': 'assets/Popup.prefab', 'node': 'Popup/btn', 'image': 'assets/ui/%s.png' % image}
        b.update(kw)
        m.write_text(json.dumps({'bindings': [b]}))
        return tool.run_bind(self.root, m, '', False)

    def btn(self):
        data = json.loads((self.root / 'assets' / 'Popup.prefab').read_text())
        return data[2]['_contentSize'], data[3]

    def test_old_way_new_frame_in_old_box_is_reported(self):
        uuid = self.png('tall', (80, 206), (0, 0, 80, 206))
        self.prefab([lambda d: d[3].update({'_spriteFrame': {'__uuid__': uuid}})])
        bad = tool.run_check(self.root, [])
        self.assertEqual(len(bad), 1)
        self.assertGreater(bad[0]['ratio_diff'], 0.10)
        p = subprocess.run([sys.executable, str(Path(tool.__file__)), '--project', str(self.root), '--check'],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn('squashed', p.stdout)

    def test_bind_contains_picture_ratio_in_old_box(self):
        self.png('tall', (80, 206), (0, 0, 80, 206))
        self.prefab()
        rec = self.bind('tall')[0]
        size, sp = self.btn()
        self.assertAlmostEqual(size['height'], 200, delta=0.1)
        self.assertAlmostEqual(size['width'], 77.7, delta=0.2)
        self.assertLess(abs((size['width'] / size['height']) / (80 / 206.0) - 1), 0.01)
        self.assertEqual(sp['_sizeMode'], 0)
        self.assertEqual(sp['_spriteFrame']['__uuid__'], rec['frame_uuid'])
        self.assertEqual(tool.run_check(self.root, []), [])
        log = json.loads((self.root / 'docs' / 'art' / 'bind_log.json').read_text())
        entry = log['bindings']['assets/Popup.prefab#Popup/btn']
        self.assertEqual(entry['old_size'], [200.0, 200.0])
        self.assertEqual(entry['new_size'], [size['width'], size['height']])

    def test_trimmed_picture_gets_matching_trim(self):
        # 300x300 PNG, visible 100x200 in the middle: the importer trims it; node sized to the rect needs trim on
        self.png('glow', (300, 300), (100, 50, 200, 250))
        self.prefab(trim=False)
        rec = self.bind('glow')[0]
        size, sp = self.btn()
        self.assertTrue(sp['_isTrimmedMode'])
        self.assertEqual([size['width'], size['height']], [100.0, 200.0])
        self.assertLess(rec['ratio_diff'], 0.01)
        # by original: node stands for the whole PNG, trim off, still the picture's own ratio when drawn
        self.prefab(trim=True)
        rec = self.bind('glow', by='original')[0]
        size, sp = self.btn()
        self.assertFalse(sp['_isTrimmedMode'])
        self.assertEqual([size['width'], size['height']], [200.0, 200.0])
        self.assertLess(rec['ratio_diff'], 0.01)
        # old way with the same file: trim on in a 200x200 node stretches the 1:2 visible part to 1:1
        self.assertGreater(abs(tool.drawn_ratio([200, 200], True, rec_geo(rec)) / 0.5 - 1), 0.10)

    def test_upscale_over_2x_refused(self):
        self.png('tiny', (40, 40), (0, 0, 40, 40))
        self.prefab()
        with self.assertRaisesRegex(tool.BindError, 'upscale'):
            self.bind('tiny')
        size, sp = self.btn()
        self.assertEqual(size['width'], 200)  # nothing written
        # the parent/own scale counts: 120 px picture in a 200 box at scale 1.5 = 2.5x
        self.png('mid', (120, 120), (0, 0, 120, 120))
        self.prefab(scale=1.5)
        with self.assertRaisesRegex(tool.BindError, 'upscale'):
            self.bind('mid')

    def test_patched_over_old_words_refused(self):
        self.png('new_btn', (200, 200), (0, 0, 200, 200))

        def patch(d):
            d[2]['_children'] = [{'__id__': 4}, {'__id__': 6}]
            d += [node('cover', {'__id__': 2}, [5], w=150, h=60), sprite(4, FLAT),
                  node('price', {'__id__': 2}, [7], w=150, h=60),
                  {'__type__': 'cc.Label', 'node': {'__id__': 6}, '_string': '50'}]
        self.prefab([patch])
        with self.assertRaisesRegex(tool.BindError, 'cover_old_text'):
            self.bind('new_btn')

    def test_label_node_and_sliced_sprite(self):
        self.png('new_btn', (200, 100), (0, 0, 200, 100))
        self.prefab([lambda d: (d.append({'__type__': 'cc.Label', 'node': {'__id__': 2}}),
                                d[2]['_components'].append({'__id__': 4}))])
        with self.assertRaisesRegex(tool.BindError, 'Label'):
            self.bind('new_btn')
        self.prefab(kind=1)
        rec = self.bind('new_btn')[0]
        self.assertIn('kept', rec)
        self.assertEqual(rec['new_size'], [200.0, 200.0])

    def test_gen_log_name_and_not_imported(self):
        self.png('tall', (80, 206), (0, 0, 80, 206))
        self.prefab()
        log = self.root / 'gen_log.json'
        log.write_text(json.dumps({'records': {'btn_tall': {'post': {
            'copied_to': str(self.root / 'assets' / 'ui' / 'tall.png')}}}}))
        m = self.root / 'bind.json'
        m.write_text(json.dumps({'bindings': [{'prefab': 'assets/Popup.prefab', 'node': 'Popup/btn', 'name': 'btn_tall'}]}))
        rec = tool.run_bind(self.root, m, log, False)[0]
        self.assertEqual(rec['image'], 'assets/ui/tall.png')
        Image.new('RGBA', (10, 10)).save(self.root / 'assets' / 'ui' / 'raw.png')
        with self.assertRaisesRegex(tool.BindError, 'not an imported sprite'):
            self.bind('raw')


def rec_geo(rec):
    return {'rect': rec['picture_rect'], 'raw': rec['picture_raw']}


if __name__ == '__main__':
    unittest.main()
