#!/usr/bin/env python3
"""Historical evidence readback and retirement of aggregate receipts in current flows."""
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
from test_art_receipt_fixtures import write_fixture
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
        out = R.check_history(p)
        self.assertEqual((out['state'], out['level']), ('missing', 'block'))
        self.assertIn('重跑 art_check', out['message'])
        self.assertEqual(R.check_history(p, policy='legacy')['level'], 'warn')
        self.assertEqual(R.check_history(p, board='localize')['level'], 'block')
        self.assertIn('英化游戏，不出包、不起试玩', R.check_history(p, board='localize')['message'])

    def test_project_without_images_has_nothing_to_check(self):
        p = project24(self.d / 'p')
        self.assertEqual((R.check_history(p)['state'], R.check_history(p)['level']), ('no_images', 'ok'))

    def test_pass_receipt_matches_until_an_image_changes(self):
        p = project24(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        (p / 'assets' / 'b.png').write_bytes(b'two')
        rec = write_fixture(p, 'pass', {'status': 'pass', 'checked': 20, 'failed': 0})
        self.assertEqual(rec['images_count'], 2)
        self.assertEqual(R.check_history(p)['state'], 'match_pass')
        (p / 'assets' / 'a.png').write_bytes(b'one, redrawn')
        (p / 'assets' / 'c.png').write_bytes(b'new')
        (p / 'assets' / 'b.png').unlink()
        out = R.check_history(p)
        self.assertEqual((out['state'], out['level']), ('changed', 'block'))
        self.assertEqual((out['changed'], out['added'], out['removed']), (['assets/a.png'], ['assets/c.png'], ['assets/b.png']))
        self.assertIn('assets/a.png', out['message'])

    def test_fail_receipt_and_unreadable_receipt_block(self):
        p = project24(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        write_fixture(p, 'fail', {'status': 'fail', 'failed': 3})
        out = R.check_history(p)
        self.assertEqual((out['state'], out['level']), ('not_pass', 'block'))
        self.assertIn('失败 3 项', out['message'])
        R.receipt_path(p).write_text('{broken')
        self.assertEqual(R.check_history(p)['state'], 'unreadable')

    def test_3x_not_covered_passes_with_warning_but_not_on_24(self):
        p = project3x(self.d / 'p3')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        write_fixture(p, 'not_covered_3x', {'status': 'blocked_inputs'})
        out = R.check_history(p)
        self.assertEqual((out['state'], out['level'], out['gate']), ('match_3x', 'warn', R.GATE_3X))
        self.assertIn('3.x 未覆盖', out['message'])
        (p / 'assets' / 'a.png').write_bytes(b'changed')
        self.assertEqual(R.check_history(p)['level'], 'block')
        q = project24(self.d / 'p2')
        (q / 'assets' / 'a.png').write_bytes(b'one')
        write_fixture(q, 'not_covered_3x')
        self.assertEqual((R.check_history(q)['state'], R.check_history(q)['level']), ('not_pass', 'block'))


class ArtCheckWrites(Tmp):
    def run_art_check(self, p, **patches):
        out = self.d / ('out%d' % len(list(self.d.glob('out*'))))
        with mock.patch.object(sys, 'argv', ['art_check.py', '--project', str(p), '--out', str(out)]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.ExitStack() as stack:
            for target, value in patches.items():
                stack.enter_context(mock.patch.object(art_check, target, value))
            return art_check.main()

    def test_valid_prior_receipt_reuses_without_analysis_or_new_capture(self):
        p = project24(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        report=self.d/'original-art-report.json'
        report.write_text('{"passed":true,"status":"pass","failed":0}')
        write_fixture(p, 'pass', {'status': 'pass','passed':True}, report)
        before = R.receipt_path(p).read_bytes()
        self.assertEqual(self.run_art_check(p, run=mock.Mock(side_effect=AssertionError('no analysis'))), 0)
        self.assertEqual(R.receipt_path(p).read_bytes(), before)

    def test_changed_prior_art_requires_scope_without_analysis(self):
        p = project24(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        report=self.d/'original-art-report.json'
        report.write_text('{"passed":true,"status":"pass","failed":0}')
        write_fixture(p, 'pass', {'status': 'pass','passed':True}, report)
        before = R.receipt_path(p).read_bytes()
        (p / 'assets' / 'a.png').write_bytes(b'changed')
        self.assertEqual(self.run_art_check(p, run=mock.Mock(side_effect=AssertionError('no full analysis'))), 3)
        self.assertEqual(R.receipt_path(p).read_bytes(), before)

    def test_missing_inputs_on_3x_only_writes_check_details(self):
        p = project3x(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        self.assertEqual(self.run_art_check(p, run=mock.Mock(side_effect=AssertionError('no analysis'))), 1)
        self.assertFalse(R.receipt_path(p).exists())
        detail = json.loads((self.d/'out0/art-check.json').read_text())
        self.assertEqual(detail['status'], 'blocked_inputs')

    def test_analysis_that_fails_only_writes_check_details(self):
        p = project24(self.d / 'p')
        (p / 'assets' / 'a.png').write_bytes(b'one')
        ready = {'ready': True, 'errors': [], 'dump_files': [], 'shots': [], 'records': [{'kind': 'gameplay'}],
                 'observed': [], 'listed': [], 'viewports': []}
        import audit_no_social_features
        with mock.patch.object(audit_no_social_features, 'audit', return_value={'passed': True}):
            code = self.run_art_check(p, capture_inventory=mock.Mock(return_value=ready),
                                      run=mock.Mock(return_value=(1, '')))
        self.assertEqual(code, 1)
        self.assertFalse(R.receipt_path(p).exists())
        detail = json.loads((self.d/'out0/art-check.json').read_text())
        self.assertFalse(detail['passed'])


class Writers(W.KitInSync):
    def setUp(self):
        super().setUp()
        # Isolate historical receipt retirement and original-audio behavior.
        # The strict-six production contract has its own fail-closed tests.
        scope = mock.patch('ad_standard_scope.requirement', return_value={'required': False})
        scope.start()
        self.addCleanup(scope.stop)

    def art_project(self, name='p'):
        p = H.project24(self.d / name)
        (p / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').write_text(W.kit_config(), encoding='utf-8')
        (p / 'assets' / 'ui').mkdir(parents=True)
        (p / 'assets' / 'ui' / 'btn_play.png').write_bytes(b'art v1')
        rec = F.finalize_source(p, 'remake')
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        return p

    def test_writer_advances_without_an_art_receipt(self):
        p, b = self.art_project(), self.native()
        with mock.patch.object(R, 'read', side_effect=AssertionError('writers must not read an art receipt')):
            record, _, problems = M.finalize_for_writer(b, p, 'remake', APP)
        self.assertIsNotNone(record, problems)
        self.assertNotIn('art_receipt', M.finalize_report(record))
        self.assertFalse(R.receipt_path(p).exists())

    def test_english_writer_ignores_even_unreadable_historical_art_receipt(self):
        p, b = self.art_project(), self.native()
        F.finalize_source(p, 'localize')
        original = b'invalid historical art receipt'
        R.receipt_path(p).write_bytes(original)
        with mock.patch.object(R, 'read', side_effect=AssertionError('writers must not read an art receipt')), \
                mock.patch('art_records.base_audio_now', side_effect=AssertionError('H8 audio only applies to remake')):
            record, _, problems = M.finalize_for_writer(b, p, 'localize', APP)
        self.assertIsNotNone(record, problems)
        self.assertNotIn('art_receipt', record)
        self.assertEqual(R.receipt_path(p).read_bytes(), original)

    def test_remake_original_audio_gate_works_without_reading_an_art_receipt(self):
        p, b = self.art_project(), self.native()
        before = H.tree_sha(b)
        with mock.patch.object(R, 'read', side_effect=AssertionError('writers must not read an art receipt')), \
                mock.patch('art_records.base_audio_now', return_value=['assets/audio/original.mp3']):
            record, _, problems = M.finalize_for_writer(b, p, 'remake', APP)
        self.assertIsNone(record)
        self.assertIn('ART_base_audio', problems[0])
        self.assertIn('assets/audio/original.mp3', problems[0])
        self.assertEqual(H.tree_sha(b), before)


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

    def test_source_prepare_converts_images_without_reissuing_historical_receipt(self):
        p = self.project()
        write_fixture(p, 'pass')
        before = R.receipt_path(p).read_bytes()
        with mock.patch.object(R, 'image_fingerprints', side_effect=AssertionError('no aggregate scan')):
            rec = F.finalize_source(p, 'remake', steps=('images',))
        self.assertTrue((p / 'assets/ui/pic.jpg').is_file())
        self.assertNotIn('art_receipt', rec)
        self.assertEqual(R.receipt_path(p).read_bytes(), before)


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
        before = (p / F.SOURCE_RECORD).read_bytes()
        with mock.patch.object(F, '_run_steps', side_effect=AssertionError('final verification must not run source steps')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(F.main(['check-source', '--project', str(p)]), 0)
            (p / 'assets/ui/pop.prefab').write_text('[]')
            self.assertEqual(F.main(['check-source', '--project', str(p)]), 1)
        self.assertEqual((p / F.SOURCE_RECORD).read_bytes(), before)


class Preview(Tmp):
    def serve(self, *args):
        web = self.d / 'web'
        web.mkdir(exist_ok=True)
        (web / 'index.html').write_text('<html>game</html>')
        return subprocess.run([sys.executable, '-B', str(HERE / 'serve_preview.py'), '--directory', str(web),
                               '--no-browser', *args], capture_output=True, text=True, timeout=60)

    def test_keep_needs_a_project(self):
        r = self.serve('--keep')
        self.assertEqual(r.returncode, 1)  # the formal production entry refuses before the older parser guard
        self.assertIn('--project', r.stderr)



if __name__ == '__main__':
    unittest.main()
