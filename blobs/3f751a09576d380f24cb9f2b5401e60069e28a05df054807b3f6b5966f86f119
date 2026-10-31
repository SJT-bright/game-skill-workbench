#!/usr/bin/env python3
"""v7.8 W90b (总表 H8 / H10 补): only files that go into the package are findings.

H8 says 「运行时可见的图和声音」. W90 compared every file under assets/; 热气球 BreezyBalloon and 丛林荡藤 also hold base
files the game never uses, and blocking those would send games back for work that changes nothing in the package.
Bad must be caught, fixed must pass:
  blocked  a base-identical picture referenced from a scene (by its sprite-frame subMetas uuid, 2.4; by uuid@sub, 3.x),
           through a prefab / font / atlas, in a resources folder, in an asset bundle, named by path in a script,
           without a .meta (cannot be told), or present in the given build;
  hint     a base-identical picture or sound the project never uses: listed as 「工程里没用到，建议删掉」, ok stays True;
  H10      an unrecorded picture counts only when it ships; the writers' sound re-check (base_audio_now) too.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import art_records as AR  # noqa: E402
import art_check  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402

N = [0]


def uid(n):
    return '%08x-1111-4222-8333-%012x' % (n, n)


def png_bytes(seed):
    """A 16x16 PNG with seeded pixels (no Pillow needed: zlib + struct)."""
    import struct
    import zlib
    raw = b''.join(b'\x00' + bytes(((x * 37 + seed * 11) % 255, (y * 53 + seed) % 255, (x * y + seed * 7) % 255, 255)
                                    [i % 4] for x in range(16) for i in range(4)) for y in range(16))

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 16, 16, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data) if isinstance(data, bytes) else path.write_text(data)
    return path


def meta24(path, n, sub=None):
    """Cocos 2.4 image .meta: texture uuid + one sprite-frame subMeta with its own uuid."""
    sub = sub if sub is not None else n + 5000
    write(Path(str(path) + '.meta'), json.dumps({
        'ver': '2.3.7', 'uuid': uid(n), 'importer': 'texture', 'type': 'sprite',
        'subMetas': {path.stem: {'ver': '1.0.6', 'uuid': uid(sub), 'importer': 'sprite-frame',
                                 'rawTextureUuid': uid(n), 'subMetas': {}}}}))


def meta3x(path, n):
    """Cocos 3.x image .meta: uuid, texture uuid@6c48a, sprite frame uuid@f9941."""
    u = uid(n)
    write(Path(str(path) + '.meta'), json.dumps({
        'ver': '1.0.27', 'importer': 'image', 'uuid': u,
        'subMetas': {'6c48a': {'importer': 'texture', 'uuid': u + '@6c48a', 'subMetas': {}},
                     'f9941': {'importer': 'sprite-frame', 'uuid': u + '@f9941', 'subMetas': {}}},
        'userData': {'type': 'sprite-frame', 'redirect': u + '@f9941'}}))


def folder_meta(path, n, bundle=False, engine=2):
    data = {'ver': '1.1.3', 'uuid': uid(n), 'importer': 'folder', 'subMetas': {}}
    if bundle and engine == 2:
        data['isBundle'] = True
    if bundle and engine == 3:
        data['userData'] = {'isBundle': True}
    write(Path(str(path) + '.meta'), json.dumps(data))


def scene(path, n, refs):
    write(path, json.dumps([{'__type__': 'cc.SceneAsset', '_name': path.stem}] +
                           [{'__type__': 'cc.Sprite', '_spriteFrame': {'__uuid__': r}} for r in refs]))
    write(Path(str(path) + '.meta'), json.dumps({'ver': '1.2.9', 'uuid': uid(n), 'subMetas': {}}))


class Fixture(unittest.TestCase):
    """A remake whose base holds pictures b1..b9 and a sound; the project keeps them in different places."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix='art-shipped-'))
        self.base = self.d / 'base'
        self.pics = {k: png_bytes(k) for k in range(1, 12)}
        for k, data in [(k, v) for k, v in self.pics.items() if k <= 9]:      # 10, 11: new pictures
            write(self.base / 'assets' / 'img' / ('b%d.png' % k), data)
        self.sound = b'ID3\x03\x00base-bgm' + bytes(range(256)) * 4
        write(self.base / 'assets' / 'audio' / 'bgm.mp3', self.sound)

    def project(self, engine=2, board='remake'):
        root = self.d / ('p%d' % len(list(self.d.glob('p*'))))
        (root / 'assets').mkdir(parents=True)
        if engine == 3:
            write(root / 'package.json', '{"creator": {"version": "3.8.8"}}')
        else:
            write(root / 'project.json', '{"engine": "cocos-creator-js", "version": "2.4.15"}')
        P.write_marker(root, board, '2.0')
        return root

    def pic(self, root, rel, k, engine=2, meta=True):
        path = write(root / rel, self.pics[k])
        if meta:
            (meta3x if engine == 3 else meta24)(path, 100 + k)
        return path

    def record(self, root):
        AR.record_base(root, self.base)

    def files(self, rows):
        return sorted(r['file'] for r in rows)


class ShippedTests(Fixture):
    def test_scene_reference_blocks_unreferenced_is_only_a_hint(self):
        root = self.project()
        self.pic(root, 'assets/ui/used.png', 1)
        self.pic(root, 'assets/legacy-art/unused.png', 2)
        scene(root / 'assets/scene/Main.fire', 900, [uid(5101)])         # the sprite-frame subMeta uuid of used.png
        self.record(root)
        b = AR.check_base(root)
        self.assertFalse(b['ok'])
        self.assertEqual(self.files(b['unlisted']), ['assets/ui/used.png'])
        self.assertEqual(b['unlisted'][0]['shipped'], ['referenced'])
        self.assertEqual(self.files(b['unused']), ['assets/legacy-art/unused.png'])
        self.assertIn('建议删掉', b['message'])
        self.assertIn('assets/legacy-art/unused.png', b['message'])

    def test_only_unused_base_files_pass_with_a_hint(self):
        root = self.project()
        self.pic(root, 'assets/legacy-art/a.png', 2)
        self.pic(root, 'assets/legacy-art/b.png', 3)
        write(root / 'assets/audio/old-bgm.mp3', self.sound)
        write(root / 'assets/audio/old-bgm.mp3.meta', json.dumps({'uuid': uid(777), 'subMetas': {}}))
        scene(root / 'assets/scene/Main.fire', 900, [])
        self.record(root)
        b = AR.check_base(root)
        self.assertTrue(b['ok'], b['message'])
        self.assertEqual(len(b['unused']), 3)
        self.assertIn('另有 3 个', b['message'])
        self.assertEqual(AR.base_audio_now(root), [])              # the writers' sound check: unused bgm not counted
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(AR.main(['check', '--project', str(root)]), 0)
        self.assertIn('建议删掉', out.getvalue())

    def test_resources_folder_blocks(self):
        root = self.project()
        self.pic(root, 'assets/resources/images/bg.png', 4)
        self.pic(root, 'assets/game/sub/resources/x.png', 5)               # any folder named resources
        self.record(root)
        b = AR.check_base(root)
        self.assertEqual(self.files(b['unlisted']), ['assets/game/sub/resources/x.png', 'assets/resources/images/bg.png'])
        self.assertTrue(all(r['shipped'] == ['resources'] for r in b['unlisted']))
        self.assertIn('只是因为放在 resources 或资源包文件夹里', b['message'])

    def test_bundle_folder_blocks_2x_and_3x(self):
        for engine in (2, 3):
            root = self.project(engine)
            folder_meta(root / 'assets' / 'legacy-art', 50, bundle=True, engine=engine)
            folder_meta(root / 'assets' / 'plain', 51, engine=engine)
            self.pic(root, 'assets/legacy-art/images/btn.png', 6, engine)
            self.pic(root, 'assets/plain/btn.png', 7, engine)
            self.record(root)
            b = AR.check_base(root)
            self.assertEqual(self.files(b['unlisted']), ['assets/legacy-art/images/btn.png'], engine)
            self.assertEqual(self.files(b['unused']), ['assets/plain/btn.png'], engine)

    def test_submeta_reference_3x_blocks(self):
        root = self.project(3)
        self.pic(root, 'assets/ui/frame.png', 1, 3)
        self.pic(root, 'assets/ui/tex.png', 2, 3)
        self.pic(root, 'assets/ui/none.png', 3, 3)
        scene(root / 'assets/home.scene', 901, [uid(101) + '@f9941', uid(102) + '@6c48a'])
        self.record(root)
        b = AR.check_base(root)
        self.assertEqual(self.files(b['unlisted']), ['assets/ui/frame.png', 'assets/ui/tex.png'])
        self.assertEqual(self.files(b['unused']), ['assets/ui/none.png'])

    def test_transitive_prefab_font_and_atlas(self):
        root = self.project()
        self.pic(root, 'assets/prefab/icon.png', 1)
        self.pic(root, 'assets/font/digits.png', 2)
        self.pic(root, 'assets/atlas/sheet.png', 3)
        self.pic(root, 'assets/atlas/orphan.png', 4)
        write(root / 'assets/prefab/Panel.prefab', json.dumps([{'_spriteFrame': {'__uuid__': uid(5101)}},
                                                               {'_font': {'__uuid__': uid(300)}},
                                                               {'_spriteFrame': {'__uuid__': uid(401)}}]))
        write(root / 'assets/prefab/Panel.prefab.meta', json.dumps({'uuid': uid(200), 'subMetas': {}}))
        write(root / 'assets/font/digits.fnt', 'info face="d"\npage id=0 file="digits.png"\n')
        write(root / 'assets/font/digits.fnt.meta', json.dumps({'uuid': uid(300), 'textureUuid': uid(102), 'subMetas': {}}))
        write(root / 'assets/atlas/sheet.plist', '<plist/>')
        write(root / 'assets/atlas/sheet.plist.meta', json.dumps({'uuid': uid(400), 'rawTextureUuid': uid(103),
                                                                  'subMetas': {'a.png': {'uuid': uid(401)}}}))
        scene(root / 'assets/scene/Main.fire', 900, [uid(200)])             # scene -> prefab -> sprite / font / atlas
        self.record(root)
        b = AR.check_base(root)
        self.assertEqual(self.files(b['unlisted']), ['assets/atlas/sheet.png', 'assets/font/digits.png',
                                                     'assets/prefab/icon.png'])
        self.assertEqual(self.files(b['unused']), ['assets/atlas/orphan.png'])

    def test_excluded_scene_does_not_ship_its_pictures(self):
        root = self.project()
        self.pic(root, 'assets/old/from-old-scene.png', 1)
        scene(root / 'assets/old/OldMenu.fire', 950, [uid(5101)])
        write(root / 'settings/builder.json', json.dumps({'startScene': uid(951), 'excludeScenes': [uid(950)]}))
        self.record(root)
        b = AR.check_base(root)
        self.assertTrue(b['ok'], b['message'])
        self.assertEqual(self.files(b['unused']), ['assets/old/from-old-scene.png'])
        write(root / 'settings/builder.json', json.dumps({'excludeScenes': []}))
        self.assertFalse(AR.check_base(root)['ok'])

    def test_unknown_is_shipped_no_meta_and_path_in_code(self):
        root = self.project()
        self.pic(root, 'assets/loose/no-meta.png', 1, meta=False)
        self.pic(root, 'assets/legacy-art/images/coded.png', 2)
        self.pic(root, 'assets/legacy-art/images/named.png', 3)
        self.pic(root, 'assets/legacy-art/images/quiet.png', 4)
        write(root / 'assets/scripts/Game.ts', "const a = 'images/coded';\nconst b = \"named.png\";\nconst c = 'quiet';\n")
        write(root / 'assets/scripts/Game.ts.meta', json.dumps({'uuid': uid(990), 'subMetas': {}}))
        self.record(root)
        b = AR.check_base(root)
        rows = {r['file']: r['shipped'] for r in b['unlisted']}
        self.assertEqual(rows.get('assets/loose/no-meta.png'), ['no_meta'])
        self.assertEqual(rows.get('assets/legacy-art/images/coded.png'), ['script'])
        self.assertEqual(rows.get('assets/legacy-art/images/named.png'), ['script'])
        self.assertEqual(self.files(b['unused']), ['assets/legacy-art/images/quiet.png'])  # a bare word is not a path

    def test_uuid_in_script_ships(self):
        root = self.project()
        self.pic(root, 'assets/legacy-art/by-uuid.png', 1)
        write(root / 'assets/scripts/Load.ts', "assetManager.loadAny({uuid: '%s'})\n" % uid(101))
        self.record(root)
        self.assertEqual(self.files(AR.check_base(root)['unlisted']), ['assets/legacy-art/by-uuid.png'])

    def test_build_folder_or_zip_counts(self):
        root = self.project()
        self.pic(root, 'assets/legacy-art/in-build.png', 1)
        self.pic(root, 'assets/legacy-art/not-in-build.png', 2)
        self.record(root)
        zp = self.d / 'pkg.zip'
        with zipfile.ZipFile(zp, 'w') as z:
            z.writestr('subpackages/legacy/native/%s/%s.png' % (uid(101)[:2], uid(101)), b'recompressed bytes')
        b = AR.check(root, build=zp)['base']
        self.assertEqual(self.files(b['unlisted']), ['assets/legacy-art/in-build.png'])
        self.assertEqual(b['unlisted'][0]['shipped'], ['build'])
        self.assertEqual(self.files(b['unused']), ['assets/legacy-art/not-in-build.png'])
        folder = self.d / 'build'
        write(folder / 'res' / 'raw-assets' / 'x.png', self.pics[2])         # same bytes, other name
        self.assertEqual(self.files(AR.check(root, build=folder)['base']['unlisted']),
                         ['assets/legacy-art/not-in-build.png'])

    def test_embedded_model_texture_follows_its_model(self):
        import struct
        root = self.project(3)
        tex = self.pics[8]
        body = b'Kaydara FBX Binary  \x00\x1a\x00' + struct.pack('<I', 7400) + b'\x00' * 40
        body += b'Content' + b'R' + struct.pack('<I', len(tex)) + tex + b'\x00' * 16
        write(self.base / 'assets' / 'model' / 'Fish.fbx', body)
        for name, n in (('Used.fbx', 60), ('Spare.fbx', 61)):
            write(root / 'assets/model' / name, body)
            write(root / 'assets/model' / (name + '.meta'), json.dumps(
                {'uuid': uid(n), 'subMetas': {'c256d': {'uuid': uid(n) + '@c256d', 'importer': 'gltf-embeded-image'}}}))
        write(root / 'assets/prefab/Fish.prefab', json.dumps([{'_mesh': {'__uuid__': uid(60) + '@8e3a1'}}]))
        write(root / 'assets/prefab/Fish.prefab.meta', json.dumps({'uuid': uid(62), 'subMetas': {}}))
        scene(root / 'assets/game.scene', 902, [uid(62)])
        self.record(root)
        b = AR.check_base(root)
        self.assertEqual([r['file'] for r in b['unlisted']], ['assets/model/Used.fbx#embedded-0'])
        self.assertEqual([r['file'] for r in b['unused']], ['assets/model/Spare.fbx#embedded-0'])

    def test_audio_writer_check_only_shipped_sounds(self):
        root = self.project()
        write(root / 'assets/resources/audio/bgm.mp3', self.sound)
        write(root / 'assets/resources/audio/bgm.mp3.meta', json.dumps({'uuid': uid(700), 'subMetas': {}}))
        write(root / 'assets/old/bgm.mp3', self.sound)
        write(root / 'assets/old/bgm.mp3.meta', json.dumps({'uuid': uid(701), 'subMetas': {}}))
        self.record(root)
        self.assertEqual(AR.base_audio_now(root), ['assets/resources/audio/bgm.mp3'])

    def test_broken_shipped_counts_everything(self):
        root = self.project()
        self.pic(root, 'assets/legacy-art/unused.png', 2)
        self.record(root)
        real = AR.shipped
        AR.shipped = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('boom'))
        try:
            b = AR.check_base(root)
        finally:
            AR.shipped = real
        self.assertFalse(b['ok'])
        self.assertIn('全部按会进包算', b['message'])


class GeneratedShippedTests(Fixture):
    def test_unrecorded_picture_counts_only_when_shipped(self):
        root = self.project()
        AR.record_none(root, 'made from scratch')
        self.pic(root, 'assets/ui/drawn-used.png', 1)
        self.pic(root, 'assets/ui/drawn-unused.png', 2)
        scene(root / 'assets/scene/Main.fire', 900, [uid(5101)])
        g = AR.check_generated(root)
        self.assertFalse(g['ok'])
        self.assertEqual([r['file'] for r in g['unrecorded']], ['assets/ui/drawn-used.png'])
        self.assertEqual(g['unused'], ['assets/ui/drawn-unused.png'])
        self.assertIn('建议删掉', g['message'])
        AR.record_generated(root, [root / 'assets/ui/drawn-used.png'], 'codex image_gen', prompt='a play button')
        g = AR.check_generated(root)
        self.assertTrue(g['ok'], g['message'])
        s = AR.summary(AR.check(root))
        self.assertEqual((s['not_generated'], s['generated_unused']), (0, 1))

    def test_art_check_rows_pass_with_only_unused_and_name_the_hint(self):
        root = self.project()
        self.pic(root, 'assets/legacy-art/old.png', 3)
        self.pic(root, 'assets/legacy-art/drawn.png', 10)
        self.record(root)
        rows, summ = art_check.base_generated_rows(root, 'remake')
        self.assertEqual([r[1] for r in rows], [True, True], rows)
        self.assertIn('建议删掉', rows[0][2])
        self.assertIn('建议删掉', rows[1][2])
        self.assertEqual((summ['base_unused'], summ['generated_unused']), (1, 1))


if __name__ == '__main__':
    unittest.main()
