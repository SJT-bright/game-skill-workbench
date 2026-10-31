#!/usr/bin/env python3
"""Synthetic bad/good fixtures for package_gates/tiktok_compat.py (SimonsScrew TikTok research 2026-10-28).
Each rule: the bad package is refused (or warned), the fixed package passes. No game ZIP needed.
Run: python3 -B test_package_gates_compat.py"""
import json
import struct
import sys
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_gates as gates  # noqa: E402
from package_gates import tiktok_compat as compat  # noqa: E402


def png(width, height):
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    chunk = b'IHDR' + ihdr
    return compat.PNG_SIG + struct.pack('>I', len(ihdr)) + chunk + struct.pack('>I', zlib.crc32(chunk))


def jpeg(width, height, progressive=False):
    app0 = b'\xff\xe0' + struct.pack('>H', 16) + b'JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    sof = b'\xff' + (b'\xc2' if progressive else b'\xc0') + struct.pack('>HBHHB', 11, 8, height, width, 1) + b'\x01\x11\x00'
    return b'\xff\xd8' + app0 + sof + b'\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00' + b'\x00' * 8 + b'\xff\xd9'


def pkg(game=None, extra=None, game_js=''):
    files = {
        'game.json': json.dumps(game if game is not None else {'subpackages': []}).encode(),
        'project.config.json': b'{}',
        'cocos/cocos2d-js-min.js': b'/* engine */ cc.macro.CLEANUP_IMAGE_CACHE=!1;',
        'adapter-min.js': b'/* adapter */',
        'game.js': game_js.encode(),
        'assets/main/native/ab/ab12.png': png(512, 512),
    }
    files.update(extra or {})
    return files


def ids(files, policy='new', level=None):
    view = gates.PackageView(files, policy=policy)
    return sorted(f['id'] for f in compat.check(view) if level is None or f['level'] == level)


class ImageSize(unittest.TestCase):
    def test_png(self):
        self.assertEqual(compat.image_size(png(2170, 1300)), (2170, 1300))

    def test_jpeg_baseline_and_progressive(self):
        self.assertEqual(compat.image_size(jpeg(4097, 300)), (4097, 300))
        self.assertEqual(compat.image_size(jpeg(640, 5000, progressive=True)), (640, 5000))

    def test_garbage(self):
        self.assertIsNone(compat.image_size(b'not an image'))


class EnginePlugin(unittest.TestCase):
    DOUYIN = {'subpackages': [], 'plugins': {'cocos': {'provider': 'tt9186e73b0ebd04c2', 'version': '', 'path': 'cocos'}}}

    def test_douyin_separate_engine_refused_both_policies(self):
        self.assertEqual(ids(pkg(self.DOUYIN), 'new', 'block'), ['T1_engine_plugin'])
        self.assertEqual(ids(pkg(self.DOUYIN), 'legacy', 'block'), ['T1_engine_plugin'])

    def test_plugin_without_version_refused(self):
        game = {'subpackages': [], 'plugins': {'physics': {'provider': 'abc', 'path': 'p'}}}
        self.assertEqual(ids(pkg(game), 'new', 'block'), ['T1_engine_plugin'])

    def test_other_plugin_only_warned(self):
        game = {'subpackages': [], 'plugins': {'physics': {'provider': 'tiktok-physics', 'version': '1.0.0'}}}
        self.assertEqual(ids(pkg(game), 'new', 'block'), [])
        self.assertEqual(ids(pkg(game), 'new', 'warn'), ['T1_engine_plugin'])

    def test_no_plugins_passes(self):
        self.assertEqual(ids(pkg()), [])


class SubpackagesKey(unittest.TestCase):
    def test_camel_case_refused(self):
        game = {'subPackages': [{'name': 'late', 'root': 'subpackages/late/'}]}
        self.assertEqual(ids(pkg(game), 'legacy', 'block'), ['T2_subpackages_key'])

    def test_both_keys_refused(self):
        game = {'subpackages': [], 'SubPackages': []}
        self.assertEqual(ids(pkg(game), 'new', 'block'), ['T2_subpackages_key'])

    def test_lowercase_passes(self):
        self.assertEqual(ids(pkg({'subpackages': [{'name': 'late', 'root': 'subpackages/late/'}]})), [])


class OggAudio(unittest.TestCase):
    BAD = {'assets/main/native/cd/cd34.ogg': b'OggS\x00'}

    def test_new_refused_legacy_warned(self):
        self.assertEqual(ids(pkg(extra=self.BAD), 'new', 'block'), ['T3_ogg_audio'])
        self.assertEqual(ids(pkg(extra=self.BAD), 'legacy', 'block'), [])
        self.assertEqual(ids(pkg(extra=self.BAD), 'legacy', 'warn'), ['T3_ogg_audio'])

    def test_mp3_passes(self):
        self.assertEqual(ids(pkg(extra={'assets/main/native/cd/cd34.mp3': b'ID3\x03'})), [])


class TextureSize(unittest.TestCase):
    def test_over_4096_refused_for_new(self):
        bad = {'subpackages/late/native/ef/ef56.png': png(4500, 1024)}
        self.assertEqual(ids(pkg(extra=bad), 'new', 'block'), ['T4_texture_over_4096'])
        self.assertEqual(ids(pkg(extra=bad), 'legacy', 'block'), [])
        self.assertEqual(ids(pkg(extra={'a/b.jpg': jpeg(300, 4200)}), 'new', 'block'), ['T4_texture_over_4096'])

    def test_simonsscrew_sizes_only_warned(self):
        files = pkg(extra={'s/a.png': png(2079, 900), 's/b.png': png(2170, 1200), 's/c.jpg': jpeg(2115, 1000)})
        self.assertEqual(ids(files, 'new', 'block'), [])
        self.assertEqual(ids(files, 'new', 'warn'), ['W_texture_over_2048'])

    def test_2048_exactly_passes(self):
        self.assertEqual(ids(pkg(extra={'s/atlas.png': png(2048, 2048)})), [])

    def test_unreadable_png_warned(self):
        self.assertEqual(ids(pkg(extra={'s/x.png': b'\x00' * 30}), 'new', 'warn'), ['W_texture_unreadable'])


class PathChars(unittest.TestCase):
    def test_space_hash_question_percent_refused(self):
        for bad in ('assets/main/native/my image.png', 'assets/a#1.json', 'assets/a?.json', 'assets/a%20b.json'):
            data = png(64, 64) if bad.endswith('.png') else b'{}'
            self.assertEqual(ids(pkg(extra={bad: data}), 'new', 'block'), ['T5_path_chars'], bad)

    def test_normal_names_pass(self):
        self.assertEqual(ids(pkg(extra={'assets/main/import/0a/0a1b2c3d-4e5f.json': b'{}',
                                        'subpackages/late-art/game.js': b''})), [])


class ImageCache(unittest.TestCase):
    def test_game_code_turning_cache_off_warned(self):
        files = pkg(game_js='cc.macro.CLEANUP_IMAGE_CACHE = false;')
        self.assertEqual(ids(files, 'new', 'block'), [])
        self.assertEqual(ids(files, 'new', 'warn'), ['W_image_cache_off'])

    def test_engine_default_and_true_pass(self):
        self.assertEqual(ids(pkg(game_js='cc.macro.CLEANUP_IMAGE_CACHE = true;')), [])


class Wiring(unittest.TestCase):
    def test_registered_and_run_by_every_entry(self):
        self.assertIn('tiktok_compat', gates.GATE_MODULES)
        result = gates.run(pkg(extra={'a/b.ogg': b'OggS'}), policy='new', modules=('tiktok_compat',))
        self.assertEqual([f['id'] for f in result['blocks']], ['T3_ogg_audio'])
        self.assertEqual(result['gates'], ['tiktok_compat'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
