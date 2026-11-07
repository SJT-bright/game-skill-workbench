"""Spine authoring and packed Cocos 2.4/3.x review entry points."""
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import audit_image_review_record as review
import audit_new_english_images as inventory


ATLAS_UUID = '11111111-1111-1111-1111-111111111111'
SKELETON_UUID = '22222222-2222-2222-2222-222222222222'
TEXTURE_UUID = '33333333-3333-3333-3333-333333333333'
ATLAS = 'subpackages/spine/native/11/' + ATLAS_UUID + '.abc.atlas'
TEXTURE = 'subpackages/texture/native/33/' + TEXTURE_UUID + '.ghi.png'
CONFIG = 'subpackages/spine/config.json'
OWNER = 'subpackages/texture/config.json'
SKELETON = 'subpackages/spine/import/pa/pack.def.json'
ATLAS_TEXT = 'page.png\nsize: 6,4\nregion\n  rotate: true\n  xy: 0,1\n  size: 3,2\n'


def encoded(value):
    return json.dumps(value).encode()


def fixture():
    image = Image.new('RGBA', (6, 4), 'white')
    image.paste('red', (0, 1, 2, 4))
    with BytesIO() as stream:
        image.save(stream, 'PNG')
        texture = stream.getvalue()
    defaults = {'importBase': 'import', 'nativeBase': 'native'}
    return {
        CONFIG: encoded(dict(defaults, name='spine', types=['cc.Asset', 'sp.SkeletonData', 'cc.Texture2D'],
                             paths={'0': ['effect/anim', 0], '1': ['effect/anim', 1], '2': ['effect/page', 2]},
                             uuids=[ATLAS_UUID, SKELETON_UUID, TEXTURE_UUID], packs={'pack': [1]},
                             deps=['texture'], redirect=[2, 0], versions={'native': [0, 'abc'], 'import': ['pack', 'def']})),
        OWNER: encoded(dict(defaults, name='texture', types=['cc.Texture2D'], paths={'0': ['page', 0]},
                            uuids=[TEXTURE_UUID], packs={'pack': [0]}, deps=[], redirect=[],
                            versions={'native': [0, 'ghi'], 'import': []})),
        SKELETON: encoded([1, [TEXTURE_UUID], [], [['sp.SkeletonData', ['_atlasText', 'textureNames', 'textures'], 1, 3]],
                           [[0, 0, 1, 2, 3]], [[[[0, ATLAS_TEXT, ['page.png'], [0]]], 0, 0, [0], [-1], [0]]]]),
        'subpackages/texture/import/pa/pack.json': encoded({'type': 'cc.Texture2D', 'data': '0,0,0,0'}),
        ATLAS: ATLAS_TEXT.encode(),
        TEXTURE: texture,
    }


def setUpModule():
    if inventory._chinese_audit() is None:
        raise unittest.SkipTest('English skill is required')


class SpineReview(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.record = self.root / 'review.json'
        self.files = fixture()

    def write(self, marker=None, **kwargs):
        with patch.dict(os.environ, {'CHINESE_AUDIT_FAKE_OCR': json.dumps(marker or {})}):
            record = review.write(self.files, ocr='fake', **kwargs)
        self.record.write_text(json.dumps(record))
        return record

    def test_compiled_page_and_rotated_slice_are_read(self):
        clean = self.write()
        self.assertEqual(clean['images'][0]['slices'], 1)
        self.assertTrue(review.check(self.files, self.record)['passed'])
        marker = inventory._chinese_audit().pixels_sha256(Image.new('RGBA', (3, 2), 'red'))
        record = self.write({marker: '测试中文'})
        self.assertEqual(record['images'][0]['chinese'], 'yes')
        self.assertEqual(record['images'][0]['slice_findings'][0]['slice'], 'region')
        self.assertFalse(review.check(self.files, self.record)['passed'])

    def test_debug_web_bundle_and_mixed_texture_pack(self):
        debug = {}
        for path, data in self.files.items():
            path = path.replace('subpackages/', 'assets/')
            if path.endswith('/config.json'):
                config = json.loads(data)
                ids = config['uuids']
                types = config.pop('types')
                config['debug'] = True
                config['paths'] = {ids[int(key)]: [row[0], types[row[1]]] for key, row in config['paths'].items()}
                config['redirect'][::2] = [ids[i] for i in config['redirect'][::2]]
                for refs in config['packs'].values():
                    refs[:] = [ids[i] for i in refs]
                for values in config['versions'].values():
                    values[::2] = [ids[key] if type(key) is int else key for key in values[::2]]
                data = encoded(config)
            elif path == 'assets/texture/import/pa/pack.json':
                data = encoded([1, [], [], ['cc.Texture2D'], [], [[['0,0,0,0', -1], [0], 0, [], [], []]]])
            debug[path] = data
        self.files = debug
        self.assertEqual(self.write()['images'][0]['slices'], 1)
        self.assertTrue(review.check(self.files, self.record)['passed'])

    def test_image_asset_is_followed_through_3x_texture_subasset(self):
        child_uuid = TEXTURE_UUID + '@6c48a'
        owner = json.loads(self.files[OWNER])
        owner['uuids'] = [child_uuid, TEXTURE_UUID]
        owner['types'].append('cc.ImageAsset')
        owner['paths']['1'] = ['image', 1]
        owner['packs']['imagepack'] = ['1']
        owner['versions']['native'] = ['1', 'ghi']
        self.files[OWNER] = encoded(owner)
        config = json.loads(self.files[CONFIG])
        config['uuids'][2] = child_uuid
        config['packs']['pack'] = ['1']
        config['redirect'] = ['2', '0']
        self.files[CONFIG] = encoded(config)
        pack = json.loads(self.files[SKELETON])
        pack[1][0] = child_uuid
        self.files[SKELETON] = encoded(pack)
        self.files['subpackages/texture/import/pa/pack.json'] = encoded({
            'type': 'cc.Texture2D', 'data': [['2,2,2,2,0,0', [TEXTURE_UUID]]]})
        self.files['subpackages/texture/import/im/imagepack.json'] = encoded({
            'type': 'cc.ImageAsset', 'data': [[1, 0, 0, ['cc.ImageAsset'], 0,
                                               [{'fmt': '0'}, -1], [0], 0, [], [], []]]})
        entry = self.write()['images'][0]
        self.assertEqual(entry['file'], TEXTURE)
        self.assertEqual(entry['slices'], 1)
        self.assertIn(child_uuid + ':' + TEXTURE_UUID, entry['atlas_context'][0])
        self.assertTrue(review.check(self.files, self.record)['passed'])

    def test_rotated_rect_cannot_overlap_another_slice_but_exact_alias_is_allowed(self):
        parse = inventory._chinese_audit().parse_spine_atlas
        alias = 'alias\n  rotate: true\n  xy: 0,1\n  size: 3,2\n'
        self.assertEqual(len(parse(ATLAS_TEXT + alias)[1]), 2)
        with self.assertRaisesRegex(ValueError, 'partially overlapping slices'):
            parse(ATLAS_TEXT + alias.replace('0,1', '1,1'))

    def test_unchanged_page_can_reuse_when_bundle_config_changes(self):
        record = self.write()
        self.files[CONFIG] = encoded(dict(json.loads(self.files[CONFIG]), unrelated='new'))
        with patch.object(inventory, 'scan_chinese', side_effect=AssertionError('repeated recognition')):
            self.assertIs(review.write(self.files, ocr='fake', previous=record), record)
        self.assertTrue(review.check(self.files, self.record)['passed'])

    def test_missing_texture_with_filename_decoy_and_missing_atlas_are_blocking(self):
        self.write()
        tex = self.files.pop(TEXTURE)
        self.files[str(Path(ATLAS).parent / 'page.png')] = tex
        with self.assertRaisesRegex(ValueError, 'missing runtime texture'):
            self.write()
        self.assertFalse(review.check(self.files, self.record)['passed'])
        self.files[TEXTURE] = tex
        del self.files[ATLAS]
        with self.assertRaisesRegex(ValueError, 'missing runtime Spine atlas'):
            self.write()
        self.assertFalse(review.check(self.files, self.record)['passed'])

    def test_sidecar_must_match_the_actual_inline_atlas(self):
        self.write()
        self.files[ATLAS] = ATLAS_TEXT.replace('0,1', '0,0').encode()
        with self.assertRaisesRegex(ValueError, 'text differs'):
            self.write()
        self.assertFalse(review.check(self.files, self.record)['passed'])

    def test_manual_ocr_verdict_cannot_override_missing_crop(self):
        atlas = 'sample.atlas'
        self.files = {atlas: ATLAS_TEXT.replace('0,1', '20,1').encode(),
                      'page.png': self.files[TEXTURE]}
        self.assertEqual(self.write()['images'][0]['status'], 'pending')
        digest = review.hashlib.sha256(self.files['page.png']).hexdigest()
        with self.assertRaisesRegex(ValueError, 'manual verdict cannot replace missing atlas slices'):
            self.write(verdicts={digest: 'no'}, by='reviewer')

    def test_authoring_reports_mismatched_importer_page_before_build(self):
        source = self.root / 'assets' / 'spine'
        source.mkdir(parents=True)
        (source / 'sample.atlas').write_text(ATLAS_TEXT)
        (source / 'page.png').write_bytes(self.files[TEXTURE])
        (source / 'page.png.meta').write_bytes(encoded({'uuid': TEXTURE_UUID}))
        meta = source / 'sample.json.meta'
        meta.write_bytes(encoded({'importer': 'spine', 'textures': [TEXTURE_UUID]}))
        first = inventory.scan_chinese(self.root, ocr='none')
        self.assertEqual(first['slices'], 1)
        self.assertEqual(first['spine_binding_problems'], [])
        (source / 'sample.atlas').write_text(ATLAS_TEXT.replace('page.png', 'alias/page.png'))
        alias = inventory.scan_chinese(self.root, ocr='none')
        self.assertEqual(alias['slices'], 1)
        self.assertEqual(alias['spine_binding_problems'], [])
        meta.write_bytes(encoded({'importer': 'spine', 'textures': [SKELETON_UUID]}))
        result = inventory.scan_chinese(self.root, ocr='none')
        self.assertEqual(result['slices'], 0)
        self.assertEqual(len(result['spine_binding_problems']), 1)


if __name__ == '__main__':
    unittest.main()
