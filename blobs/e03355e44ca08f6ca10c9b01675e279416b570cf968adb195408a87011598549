#!/usr/bin/env python3
"""v7.8 U7（补）: art-check receipt in both package writers and serve_preview --keep, static ratio source step.

Synthetic fixtures only (never a game pass); the real-project evidence is in the W83 RESULT. Each rule has a bad case
that is refused and a good case that passes:
  receipt   art_receipt.check: no receipt / fail receipt / changed, added or removed image -> refused for a new remake
            game, warning for legacy and English games; pass receipt with the same images -> ok; 3.x not_covered_3x
            -> passes with the "3.x 未覆盖" warning; a project without images has nothing to check
  art_check writes the receipt after its analysis (pass / fail); missing inputs keep a 2.4 receipt; 3.x -> not_covered_3x
  writers   make_tiktok_zip.finalize_for_writer (both writers) refuses before the build folder changes; the result is
            a row of the finalize table; make_tiktok_zip.py and build_checked_zip.build refuse with 重跑 art_check
  carry     tiktok_finalize source moves a matching receipt to the PNG/JPG its images step wrote; a receipt that no longer
            matched before the source phase is not carried
  static    art_static: squashed SIMPLE/CUSTOM sprite blocked for new games, warned for legacy; SLICED, TRIMMED, right
            ratio, one-colour stretch, ProgressBar bar and exempted node pass; any popup dim opacity (80, 30, 180) is
            not judged (Saul 10-31); 3.x serialisation; the block lands in the source record (K5)
  preview   serve_preview --keep needs --project and gets no server without a matching receipt
Run: python3 test_art_receipt.py
"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
CHECK = HERE.parents[1] / 'cocos-game-check' / 'package-check' / 'scripts'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(CHECK))
import art_receipt as R  # noqa: E402
import art_check  # noqa: E402
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import art_static as A  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402
import make_tiktok_zip as M  # noqa: E402
import test_tiktok_finalize as H  # noqa: E402
import test_writer_finalize as W  # noqa: E402

APP = H.APP


def png(path, size=(8, 8), colour=(200, 40, 40, 255), rows=False):
    from PIL import Image
    im = Image.new('RGBA', size, colour)
    if not rows:                                   # a picture with detail in both directions
        for x in range(size[0]):
            for y in range(size[1]):
                im.putpixel((x, y), ((x * 37) % 255, (y * 53) % 255, (x * y) % 255, 255))
    else:                                          # every row one colour (stretchable sideways)
        for y in range(size[1]):
            for x in range(size[0]):
                im.putpixel((x, y), (20 * y % 255, 90, 40, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return path


def project24(root, marker=True, board='remake'):
    (root / 'assets').mkdir(parents=True, exist_ok=True)
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    if marker:
        P.write_marker(root, board, '2.0')
    return root


def project3x(root):
    (root / 'assets').mkdir(parents=True, exist_ok=True)
    (root / 'package.json').write_text('{"creator": {"version": "3.8.8"}}')
    P.write_marker(root, 'remake', '2.0')
    return root


class Tmp(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix='art-receipt-'))
        self.addCleanup(lambda: __import__('shutil').rmtree(self.d, True))


class Receipt(Tmp):
    def test_fingerprints_cover_images_atlas_and_models_only_under_assets(self):
        p = project24(self.d / 'p')
        for rel in ('assets/a.png', 'assets/ui/b.jpg', 'assets/c.webp', 'assets/atlas/d.plist', 'assets/m/e.fbx',
                    'assets/m/f.glb', 'assets/m/g.gltf', 'assets/a.png.meta', 'assets/s.js', 'library/x.png',
                    'assets/temp/y.png', '.tiktok-kit/originals/assets/z.png'):
            (p / rel).parent.mkdir(parents=True, exist_ok=True)
            (p / rel).write_bytes(rel.encode())
        self.assertEqual(sorted(R.image_fingerprints(p)), ['assets/a.png', 'assets/atlas/d.plist', 'assets/c.webp',
                                                           'assets/m/e.fbx', 'assets/m/f.glb', 'assets/m/g.gltf',
                                                           'assets/ui/b.jpg'])

    def test_missing_receipt_blocks_a_new_remake_game_and_warns_otherwise(self):
        p = project24(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        out = R.check(p)
        self.assertEqual((out['state'], out['level']), ('missing', 'block'))
        self.assertIn('重跑 art_check', out['message'])
        self.assertEqual(R.check(p, policy='legacy')['level'], 'warn')
        self.assertEqual(R.check(p, board='localize')['level'], 'warn')
        self.assertIn('英化游戏只警告', R.check(p, board='localize')['message'])

    def test_project_without_images_has_nothing_to_check(self):
        p = project24(self.d / 'p')
        self.assertEqual((R.check(p)['state'], R.check(p)['level']), ('no_images', 'ok'))

    def test_pass_receipt_matches_until_an_image_changes(self):
        p = project24(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        (p / 'assets' / 'b.png').write_bytes(b'two')
        rec = R.write(p, 'pass', {'status': 'pass', 'checked': 20, 'failed': 0})
        self.assertEqual(rec['images_count'], 2)
        self.assertEqual(R.check(p)['state'], 'match_pass')
        (p / 'assets' / 'a.png').write_bytes(b'one, redrawn')
        (p / 'assets' / 'c.png').write_bytes(b'new')
        (p / 'assets' / 'b.png').unlink()
        out = R.check(p)
        self.assertEqual((out['state'], out['level']), ('changed', 'block'))
        self.assertEqual((out['changed'], out['added'], out['removed']), (['assets/a.png'], ['assets/c.png'], ['assets/b.png']))
        self.assertIn('assets/a.png', out['message'])

    def test_fail_receipt_and_unreadable_receipt_block(self):
        p = project24(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        R.write(p, 'fail', {'status': 'fail', 'failed': 3})
        out = R.check(p)
        self.assertEqual((out['state'], out['level']), ('not_pass', 'block'))
        self.assertIn('失败 3 项', out['message'])
        R.receipt_path(p).write_text('{broken')
        self.assertEqual(R.check(p)['state'], 'unreadable')

    def test_3x_not_covered_passes_with_warning_but_not_on_24(self):
        p = project3x(self.d / 'p3')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        R.not_covered_3x(p, {'status': 'blocked_inputs'}, None)
        out = R.check(p)
        self.assertEqual((out['state'], out['level'], out['gate']), ('match_3x', 'warn', R.GATE_3X))
        self.assertIn('3.x 未覆盖', out['message'])
        (p / 'assets' / 'a.png').write_bytes(b'changed')
        self.assertEqual(R.check(p)['level'], 'block')
        q = project24(self.d / 'p2')
        (q / 'assets' / 'a.png').write_bytes(b'one')
        R.not_covered_3x(q, {}, None)
        self.assertEqual((R.check(q)['state'], R.check(q)['level']), ('not_pass', 'block'))


class ArtCheckWrites(Tmp):
    def run_art_check(self, p, **patches):
        out = self.d / ('out%d' % len(list(self.d.glob('out*'))))
        with mock.patch.object(sys, 'argv', ['art_check.py', '--project', str(p), '--out', str(out)]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.ExitStack() as stack:
            for target, value in patches.items():
                stack.enter_context(mock.patch.object(art_check, target, value))
            return art_check.main()

    def test_missing_inputs_keep_the_24_receipt(self):
        p = project24(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        R.write(p, 'pass', {'status': 'pass'})
        before = R.receipt_path(p).read_bytes()
        self.assertEqual(self.run_art_check(p, run=mock.Mock(side_effect=AssertionError('no analysis'))), 1)
        self.assertEqual(R.receipt_path(p).read_bytes(), before)

    def test_missing_inputs_on_3x_write_not_covered(self):
        p = project3x(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        self.assertEqual(self.run_art_check(p, run=mock.Mock(side_effect=AssertionError('no analysis'))), 1)
        rec = json.loads(R.receipt_path(p).read_text())
        self.assertEqual((rec['status'], rec['passed'], rec['images_count']), ('not_covered_3x', False, 1))

    def test_analysis_that_fails_writes_a_fail_receipt(self):
        p = project24(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        ready = {'ready': True, 'errors': [], 'dump_files': [], 'shots': [], 'records': [{'kind': 'gameplay'}],
                 'observed': [], 'listed': [], 'viewports': []}
        import audit_no_social_features
        with mock.patch.object(audit_no_social_features, 'audit', return_value={'passed': True}):
            code = self.run_art_check(p, capture_inventory=mock.Mock(return_value=ready),
                                      run=mock.Mock(return_value=(1, '')))
        self.assertEqual(code, 1)
        rec = json.loads(R.receipt_path(p).read_text())
        self.assertEqual(rec['status'], 'fail')
        self.assertTrue(rec['art_check']['report_sha256'])
        self.assertEqual(R.check(p)['level'], 'block')

    def test_passing_report_writes_a_pass_receipt(self):
        p = project24(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        report = self.d / 'art-check.json'
        report.write_text('{"passed": true}')
        rec = R.after_art_check(p, {'passed': True, 'status': 'pass', 'checked': 25, 'failed': 0}, report)
        self.assertEqual((rec['status'], rec['art_check']['checked']), ('pass', 25))
        self.assertEqual(R.check(p)['state'], 'match_pass')


class Writers(W.KitInSync):
    def art_project(self, name='p'):
        p = H.project24(self.d / name)
        (p / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').write_text(W.kit_config(), encoding='utf-8')
        (p / 'assets' / 'ui').mkdir(parents=True)
        (p / 'assets' / 'ui' / 'btn_play.png').write_bytes(b'art v1')
        rec = F.finalize_source(p, 'remake')
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        return p

    def test_no_receipt_refused_before_the_build_changes(self):
        p, b = self.art_project(), self.native()
        before = H.tree_sha(b)
        record, _, problems = M.finalize_for_writer(b, p, 'remake', APP)
        self.assertIsNone(record)
        self.assertTrue(any(x.startswith('ART_receipt:') and '重跑 art_check' in x for x in problems), problems)
        self.assertEqual(H.tree_sha(b), before)

    def test_matching_receipt_passes_and_is_a_table_row(self):
        p, b = self.art_project(), self.native()
        R.write(p, 'pass', {'status': 'pass'})
        record, _, problems = M.finalize_for_writer(b, p, 'remake', APP)
        self.assertFalse(any('ART_receipt' in x for x in problems), problems)
        self.assertEqual(record['art_receipt']['state'], 'match_pass')
        self.assertIn('art_receipt', F.table_markdown(record))
        self.assertIn('art_receipt', M.finalize_report(record))

    def test_image_changed_after_the_art_check_refused_even_with_a_fresh_source_record(self):
        p, b = self.art_project(), self.native()
        R.write(p, 'pass', {'status': 'pass'})
        (p / 'assets' / 'ui' / 'btn_play.png').write_bytes(b'art v2, nobody looked')
        F.finalize_source(p, 'remake')                       # K5 current again; the art check was not re-run
        _, _, problems = M.finalize_for_writer(b, p, 'remake', APP)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn('assets/ui/btn_play.png', problems[0])

    def test_english_game_only_warns(self):
        p, b = self.art_project(), self.native()
        _, _, problems = M.finalize_for_writer(b, p, 'localize', APP)
        self.assertFalse(any('ART_receipt' in x for x in problems), problems)

    def test_both_writer_entries_refuse(self):
        p, b = self.art_project(), self.native()
        import build_checked_zip as B
        with self.assertRaisesRegex(ValueError, 'ART_receipt'):
            B.build(b, APP, self.d / 'out.zip', resource_manifest=self.d / 'r.json', project=p, board='remake')
        review = self.d / 'review.json'
        review.write_text('{}')
        code, err = W.run_make_zip(['--native', b, '--app-id', APP, '--out', self.d / 'out.zip', '--project', p,
                                    '--web', b, '--build-tag', 't', '--review', review, '--board', 'remake'])
        self.assertEqual(code, 1)
        self.assertIn('重跑 art_check', err)
        self.assertFalse((self.d / 'out.zip').exists())


class Carry(Tmp):
    def project(self):
        p = H.project24(self.d / 'p')
        (p / 'assets' / 'ui').mkdir(parents=True)
        png(self.d / 'src.png')
        from PIL import Image
        with Image.open(self.d / 'src.png') as im:
            im.save(p / 'assets' / 'ui' / 'pic.webp', 'WEBP', lossless=True)
        (p / 'assets' / 'ui' / 'pic.webp.meta').write_text(json.dumps({
            'ver': '2.3.7', 'uuid': 'aaaaaaaa-0000-4000-8000-000000000001', 'importer': 'texture', 'type': 'sprite',
            'width': 8, 'height': 8, 'platformSettings': {}, 'subMetas': {}}))
        return p

    def test_matching_receipt_follows_the_webp_to_png_conversion(self):
        p = self.project()
        R.write(p, 'pass', {'status': 'pass'})
        rec = F.finalize_source(p, 'remake', steps=('images',))
        self.assertTrue((p / 'assets' / 'ui' / 'pic.jpg').is_file())            # opaque WebP -> JPG
        self.assertEqual(rec['art_receipt'], {'before': 'match_pass', 'carried': True, 'after': 'match_pass'})
        receipt = json.loads(R.receipt_path(p).read_text())
        self.assertEqual((receipt['carried'][0]['added'], receipt['carried'][0]['removed']),
                         (['assets/ui/pic.jpg'], ['assets/ui/pic.webp']))
        self.assertEqual(receipt['status'], 'pass')

    def test_receipt_that_no_longer_matched_is_not_carried(self):
        p = self.project()
        R.write(p, 'pass', {'status': 'pass'})
        (p / 'assets' / 'ui' / 'other.png').write_bytes(b'added after the art check')
        rec = F.finalize_source(p, 'remake', steps=('images',))
        self.assertEqual(rec['art_receipt']['carried'], False)
        self.assertEqual(R.check(p)['state'], 'changed')


SPRITE_UUID = 'bbbbbbbb-0000-4000-8000-000000000001'
LINE_UUID = 'bbbbbbbb-0000-4000-8000-000000000002'


def prefab24(nodes):
    """nodes: list of dicts {name, size, opacity, sprite: {...} | None, block, widget, parent (index into nodes)}."""
    objs = [{'__type__': 'cc.Prefab', 'data': {'__id__': 1}}]
    ids = []
    for n in nodes:
        ids.append(len(objs))
        objs.append({'__type__': 'cc.Node', '_name': n['name'], '_components': [], '_opacity': n.get('opacity', 255),
                     '_color': {'__type__': 'cc.Color', 'r': 0, 'g': 0, 'b': 0, 'a': 255},
                     '_contentSize': {'__type__': 'cc.Size', 'width': n['size'][0], 'height': n['size'][1]},
                     '_trs': {'__type__': 'TypedArray', 'ctor': 'Float64Array', 'array': [0, 0, 0, 0, 0, 0, 1, 1, 1, 1]},
                     '_parent': None})
    for n, i in zip(nodes, ids):
        node = objs[i]
        if n.get('parent') is not None:
            node['_parent'] = {'__id__': ids[n['parent']]}
        if n.get('sprite') is not None:
            s = {'__type__': 'cc.Sprite', 'node': {'__id__': i}, '_enabled': True, '_sizeMode': 0, '_type': 0,
                 '_isTrimmedMode': True, '_spriteFrame': {'__uuid__': SPRITE_UUID}}
            s.update(n['sprite'])
            node['_components'].append({'__id__': len(objs)})
            objs.append(s)
        if n.get('block'):
            node['_components'].append({'__id__': len(objs)})
            objs.append({'__type__': 'cc.BlockInputEvents', 'node': {'__id__': i}})
        if n.get('widget'):
            node['_components'].append({'__id__': len(objs)})
            objs.append({'__type__': 'cc.Widget', 'node': {'__id__': i}, '_alignFlags': 45, '_left': 0, '_right': 0,
                         '_top': 0, '_bottom': 0})
        if n.get('bar_of') is not None:                    # a cc.ProgressBar driving node n['bar_of']'s sprite
            target = objs[ids[n['bar_of']]]['_components'][0]['__id__']
            node['_components'].append({'__id__': len(objs)})
            objs.append({'__type__': 'cc.ProgressBar', 'node': {'__id__': i}, '_N$barSprite': {'__id__': target}})
    return objs


def meta(uuid, w, h, name='btn'):
    return json.dumps({'ver': '2.3.7', 'uuid': uuid[:-1] + 'f', 'importer': 'texture', 'width': w, 'height': h,
                       'subMetas': {name: {'uuid': uuid, 'width': w, 'height': h, 'rawWidth': w, 'rawHeight': h,
                                           'trimX': 0, 'trimY': 0}}}).encode()


def canvas_scene():
    return json.dumps([{'__type__': 'cc.SceneAsset'}, {'__type__': 'cc.Canvas',
                                                      '_designResolution': {'width': 750, 'height': 1334}}]).encode()


class Static(Tmp):
    def files(self, nodes, frame=(255, 296)):
        return {'assets/main.fire': canvas_scene(), 'assets/ui/pop.prefab': json.dumps(prefab24(nodes)).encode(),
                'assets/ui/btn.png.meta': meta(SPRITE_UUID, *frame)}

    def ids(self, files, policy='new', root=None):
        return [(f['id'], f['level']) for f in A.findings(A.scan(files, root), policy)]

    def test_faint_full_screen_dim_is_not_judged(self):
        """Saul 10-31: no dim-opacity limit; an 80/255 popup dim (丛林荡藤 v4 spin wheel) is not blocked or warned."""
        self.assertFalse(hasattr(A, 'MIN_DIM_OPACITY'))
        dim = {'name': 'mask', 'size': (750, 1334), 'opacity': 80, 'sprite': {'_type': 1}, 'block': True}
        for policy in ('new', 'legacy'):
            for op in (80, 30, 180):
                self.assertEqual(self.ids(self.files([dict(dim, opacity=op)]), policy), [], (policy, op))
        root = {'name': 'popup', 'size': (750, 1334), 'block': True}
        child = {'name': 'mask', 'size': (100, 100), 'opacity': 100, 'sprite': {'_type': 1}, 'widget': True, 'parent': 0}
        self.assertEqual(self.ids(self.files([root, child])), [])
        self.assertNotIn('faint', A.scan(self.files([dim])))

    def test_squashed_custom_simple_sprite_blocks_other_modes_pass(self):
        btn = {'name': 'btn_reward', 'size': (120, 90), 'sprite': {}}                     # 255x296 -> 1.55x
        found = A.scan(self.files([btn]))
        self.assertEqual([(i['node'], i['stretch']) for i in found['squashed']], [('btn_reward', 1.55)])
        self.assertEqual(self.ids(self.files([btn])), [('K_art_aspect', 'block')])
        self.assertEqual(self.ids(self.files([btn]), 'legacy'), [('K_W_art_aspect', 'warn')])
        for ok in ({'_type': 1}, {'_type': 2}, {'_sizeMode': 1}):
            self.assertEqual(self.ids(self.files([dict(btn, sprite=ok)])), [], ok)
        self.assertEqual(self.ids(self.files([dict(btn, size=(128, 148))])), [])         # right ratio
        self.assertEqual(self.ids(self.files([dict(btn, size=(120, 132))])), [])         # within 10 %

    def test_one_colour_rows_may_stretch_detail_may_not(self):
        p = self.d / 'p'
        png(p / 'assets' / 'ui' / 'btn.png', (7, 8), rows=True)
        files = self.files([{'name': 'line', 'size': (100, 5), 'sprite': {}}], frame=(7, 8))
        self.assertEqual(self.ids(files, root=p), [])                                   # 丛林荡藤 rope `line`
        self.assertEqual(self.ids(files), [('K_art_aspect', 'block')])                  # no pixels: not assumed
        png(p / 'assets' / 'ui' / 'btn.png', (7, 8))
        self.assertEqual(self.ids(files, root=p), [('K_art_aspect', 'block')])

    def test_progress_bar_sprite_and_exempted_node_pass(self):
        bar = {'name': 'fill', 'size': (474, 28), 'sprite': {}}
        self.assertEqual(self.ids(self.files([bar])), [('K_art_aspect', 'block')])
        self.assertEqual(self.ids(self.files([bar, {'name': 'progress', 'size': (480, 30), 'bar_of': 0}])), [])
        p = self.d / 'p'
        (p / 'docs' / 'art').mkdir(parents=True)
        rule = {'file': 'assets/ui/*.prefab', 'node': 'fill', 'why': 'base-game node, EnglishUI hides it at start'}
        (p / A.EXEMPT).write_text(json.dumps({'nodes': [rule]}))
        self.assertEqual(self.ids(self.files([bar]), root=p), [('K_W_art_static_exempt', 'warn')])
        (p / A.EXEMPT).write_text(json.dumps({'nodes': [dict(rule, why=' ')]}))
        self.assertEqual(self.ids(self.files([bar]), root=p), [('K_art_aspect', 'block')])

    def test_cocos3_serialisation(self):
        objs = [{'__type__': 'cc.Prefab'},
                {'__type__': 'cc.Node', '_name': 'mask', '_parent': None, '_lscale': {'x': 1, 'y': 1, 'z': 1},
                 '_components': [{'__id__': 2}, {'__id__': 3}, {'__id__': 4}, {'__id__': 5}]},
                {'__type__': 'cc.UITransform', '_contentSize': {'width': 750, 'height': 1334}},
                {'__type__': 'cc.Sprite', 'node': {'__id__': 1}, '_sizeMode': 0, '_type': 0,
                 '_color': {'r': 0, 'g': 0, 'b': 0, 'a': 255}, '_spriteFrame': {'__uuid__': 'cccc@f9941'}},
                {'__type__': 'cc.UIOpacity', '_opacity': 90},
                {'__type__': 'cc.BlockInputEvents'}]
        settings = json.dumps({'general': {'designResolution': {'width': 750, 'height': 1334}}}).encode()
        meta3 = json.dumps({'ver': '1.0.26', 'importer': 'image', 'uuid': 'cccc', 'subMetas': {'f9941': {
            'importer': 'sprite-frame', 'uuid': 'cccc@f9941', 'userData': {'width': 8, 'height': 8, 'rawWidth': 8,
                                                                           'rawHeight': 8}}}}).encode()
        files = {'assets/pop.prefab': json.dumps(objs).encode(), A.SETTINGS_3X: settings, 'assets/m.png.meta': meta3}
        self.assertEqual(self.ids(files), [('K_art_aspect', 'block')])           # UIOpacity 90: no dim finding
        objs[2]['_contentSize'] = {'width': 750, 'height': 750}
        files['assets/pop.prefab'] = json.dumps(objs).encode()
        self.assertEqual(self.ids(files), [])

    def test_source_phase_records_the_block_and_k5_refuses(self):
        self.assertIn('art_static', T.SOURCE_STEPS)
        self.assertIn('art_static', F.SOURCE_STEPS)
        p = H.project24(self.d / 'p')
        for rel, data in self.files([{'name': 'btn_reward', 'size': (120, 90), 'sprite': {}}]).items():
            (p / rel).parent.mkdir(parents=True, exist_ok=True)
            (p / rel).write_bytes(data)
        rec = F.finalize_source(p, 'remake', steps=('art_static',))
        self.assertEqual([b['id'] for b in rec['blocks']], ['K_art_aspect'])
        self.assertTrue(any('source phase refused' in f['message'] and 'K_art_aspect' in f['message']
                            for f in F.check_source_record(p)))
        (p / 'assets' / 'ui' / 'pop.prefab').write_text(json.dumps(prefab24([{'name': 'btn_reward', 'size': (128, 148),
                                                                              'sprite': {}}])))
        self.assertEqual(F.finalize_source(p, 'remake', steps=('art_static',))['blocks'], [])


class Preview(Tmp):
    def serve(self, *args):
        web = self.d / 'web'
        web.mkdir(exist_ok=True)
        (web / 'index.html').write_text('<html>game</html>')
        return subprocess.run([sys.executable, '-B', str(HERE / 'serve_preview.py'), '--directory', str(web),
                               '--no-browser', *args], capture_output=True, text=True, timeout=60)

    def test_keep_needs_a_project(self):
        r = self.serve('--keep')
        self.assertEqual(r.returncode, 2)
        self.assertIn('--project', r.stderr)

    def test_keep_refused_without_matching_receipt(self):
        p = project24(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        r = self.serve('--keep', '--project', str(p))
        self.assertEqual(r.returncode, 1)
        self.assertIn('不起试玩服务', r.stderr)
        self.assertIn('重跑 art_check', r.stderr)


if __name__ == '__main__':
    unittest.main()
