#!/usr/bin/env python3
"""v7.7 wave 3 W-F1b: source-stage and record fixes. Each item has a bad case that fails on the wave-2 code.

  1 hard-coded .webp   images.py: a new game whose conversion / compression switch-off changes anything is blocked
                       (IMG0_source_images, file and line) when assets/ .json/.ts/.js data says ".webp" (Marlows R6
                       manifest "imageExt": ".webp": 19 images failed to load); legacy and the exception only warn;
                       game data is never rewritten. Real package: Marlows R6 source copy (skipped when absent).
  2 recorded options   finalize-source.json records `options`; K5 refuses a writer whose --keep-webp-exception
                       differs from the source record (W-D1 request 3).
  3 parts table        a kit_current part whose step inserted a load line reads 已装（插加载行）(W-D4 request 4).
  4 3.x WebP           keep_webp_exception is refused on Cocos 3.x (DECISIONS 13:25), before anything changes.
Run: python3 test_finalize_source_fixes.py
"""
import json
import shutil
import sys
import unittest
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
CHECK = HERE.parents[1] / 'cocos-game-check' / 'package-check' / 'scripts'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(CHECK))
from PIL import Image  # noqa: E402

import package_gates as G  # noqa: E402
from package_gates import kit_parts  # noqa: E402
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import images  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402
import test_tiktok_finalize as H  # noqa: E402
import test_writer_finalize as WF  # noqa: E402
import make_tiktok_zip as M  # noqa: E402

APP = H.APP
MARLOWS = H.J / '4周燎原-Marlows（自制）' / 'MarlowsMarbleCut_PortionV2_R6_Source_20261029.zip'
EXC = {'keep_webp_exception': 'still 45 MB after max_side'}


def uid(n):
    return '%08x-1111-4222-8333-%012x' % (n, n)


def meta24(name, n, w, h, webp_compress=False):
    stem = name.rsplit('.', 1)[0]
    m = {'ver': '2.3.5', 'uuid': uid(n), 'type': 'sprite', 'width': w, 'height': h, 'platformSettings': {},
         'subMetas': {stem: {'ver': '1.0.4', 'uuid': uid(n + 1000), 'rawTextureUuid': uid(n), 'trimX': 0, 'trimY': 0,
                             'offsetX': 0, 'offsetY': 0, 'width': w, 'height': h, 'rawWidth': w, 'rawHeight': h,
                             'borderTop': 0, 'borderBottom': 0, 'borderLeft': 0, 'borderRight': 0, 'subMetas': {}}}}
    if webp_compress:
        m['platformSettings'] = {'bytedance': {'formats': [{'name': 'webp', 'quality': 80}]}}
    return m


def put(project, rel, meta, fmt):
    p = project / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGBA', (32, 32), (10, 200, 30, 255)).save(p, fmt, **({'lossless': True} if fmt == 'WEBP' else {}))
    p.with_name(p.name + '.meta').write_text(json.dumps(meta, indent=2))
    return p


def art24(root, data=None, webp=True, compress=False):
    """2.4 project: one WebP (or PNG) image loaded by code from resources/, and a data file naming its extension."""
    proj = root
    (proj / 'assets').mkdir(parents=True, exist_ok=True)
    (proj / 'project.json').write_text(json.dumps({'engine': 'cocos2d-html5', 'version': '2.4.15'}))
    if webp:
        put(proj, 'assets/resources/art/hero.webp', meta24('hero.webp', 1, 32, 32), 'WEBP')
    else:
        put(proj, 'assets/resources/art/hero.png', meta24('hero.png', 1, 32, 32, webp_compress=compress), 'PNG')
    if data is not None:
        (proj / 'assets' / 'resources' / 'art' / 'manifest.json').write_text(data)
    return proj


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(Path(root).rglob('*')) if p.is_file()}


def img0(result):
    return [b for b in result['blocks'] if b['id'] == 'IMG0_source_images' and 'hard-coded .webp' in b['message']]


class HardCodedWebp(unittest.TestCase):
    def setUp(self):
        self.d = H.tmpdir(self)

    def test_bad_imageExt_webp_blocked_with_file_and_line_and_nothing_changed(self):
        p = art24(self.d / 'p', '{\n  "name": "art",\n  "imageExt": ".webp"\n}\n')
        before = tree(p)
        r = images.apply({'project': p, 'policy': 'new'})
        hits = img0(r)
        self.assertEqual(len(hits), 1, r['blocks'])
        self.assertIn('assets/resources/art/manifest.json', hits[0]['message'])
        self.assertIn('line 3', hits[0]['message'])
        self.assertIn('".png" or ".jpg"', hits[0]['message'])
        self.assertEqual(tree(p), before)                     # refused before touching anything, data not rewritten

    def test_good_imageExt_png_passes_and_converts(self):
        p = art24(self.d / 'p', '{"imageExt": ".png"}\n')
        r = images.apply({'project': p, 'policy': 'new'})
        self.assertEqual(r['blocks'], [])
        art = p / 'assets/resources/art'
        self.assertTrue((art / 'hero.png').is_file() or (art / 'hero.jpg').is_file())
        self.assertFalse((art / 'hero.webp').exists())

    def test_compress_off_alone_also_triggers(self):
        p = art24(self.d / 'p', '{"imageExt": ".webp"}', webp=False, compress=True)
        self.assertTrue(img0(images.apply({'project': p, 'policy': 'new'})))

    def test_ts_and_js_literals_and_json_paths_blocked(self):
        p = art24(self.d / 'p', '{"frames": {"hero": "art/hero.webp"}, "cdn": "https://x.example/a.webp"}')
        (p / 'assets' / 'scripts').mkdir()
        (p / 'assets' / 'scripts' / 'Art.ts').write_text("const EXT = '.webp';\n")
        (p / 'assets' / 'scripts' / 'Art.js').write_text('var e = `.webp`;\n')
        msgs = ' '.join(b['message'] for b in img0(images.apply({'project': p, 'policy': 'new'})))
        for rel in ('assets/scripts/Art.ts', 'assets/scripts/Art.js', 'assets/resources/art/manifest.json'):
            self.assertIn(rel, msgs)
        self.assertIn('art/hero.webp', msgs)
        self.assertNotIn('x.example', msgs)                   # a remote URL is not a build file

    def test_format_list_meta_and_kit_files_not_reported(self):
        p = art24(self.d / 'p', None)
        (p / 'assets' / 'scripts').mkdir()
        (p / 'assets' / 'scripts' / 'Guard.ts').write_text(
            "var types=['.png','.jpg','.jpeg','.bmp','.gif','.ico','.tiff','.image','.webp'];\n")  # AssetLoadGuard
        (p / 'assets' / 'scripts' / 'Guard.ts.meta').write_text('{"note": ".webp"}')
        (p / 'assets' / 'tiktok-platform').mkdir()
        (p / 'assets' / 'tiktok-platform' / 'Probe.js').write_text("var x = '.webp';\n")
        r = images.apply({'project': p, 'policy': 'new'})
        self.assertEqual(r['blocks'], [])

    def test_nothing_converted_means_no_scan(self):
        p = art24(self.d / 'p', '{"imageExt": ".webp"}', webp=False)    # PNG art, no WebP compression
        self.assertEqual(images.apply({'project': p, 'policy': 'new'})['blocks'], [])

    def test_legacy_warns_and_changes_nothing(self):
        p = art24(self.d / 'p', '{"imageExt": ".webp"}')
        before = tree(p)
        r = images.apply({'project': p, 'policy': 'legacy'})
        self.assertEqual(r['blocks'], [])
        self.assertTrue(any('hard-coded .webp' in w['message'] and w['id'] == 'IMG0_source_images'
                            for w in r['warnings']), r['warnings'])
        self.assertEqual(tree(p), before)

    def test_exception_2x_warns(self):
        p = art24(self.d / 'p', '{"imageExt": ".webp"}', webp=False, compress=True)
        r = images.apply({'project': p, 'policy': 'new', 'options': EXC})
        self.assertEqual(img0(r), [])
        self.assertTrue(any('hard-coded .webp' in w['message'] for w in r['warnings']), r['warnings'])


@unittest.skipUnless(MARLOWS.is_file(), 'Marlows R6 source zip not on this machine')
class MarlowsR6(unittest.TestCase):
    """Real package (W-D4 request 2): the init new-game marker, the real policy (no --policy), the real source stage."""

    def copy(self, image_ext):
        d = H.tmpdir(self)
        with zipfile.ZipFile(MARLOWS) as z:
            z.extractall(d)
        p = d / 'MarlowsMarbleCut_Source' / 'game'
        if image_ext:
            m = p / 'assets' / 'resources' / 'art' / 'manifest.json'
            text = m.read_text(encoding='utf-8')
            self.assertIn('"imageExt": ".webp"', text)
            m.write_text(text.replace('"imageExt": ".webp"', '"imageExt": "%s"' % image_ext), encoding='utf-8')
        P.write_marker(p, 'remake', T.load_manifest().version, reason='init')
        return p

    def test_source_copy_with_marker_blocked(self):
        p = self.copy(None)
        rec = F.finalize_source(p, 'remake', app_id=APP)
        self.assertEqual(rec['policy'], 'new')
        hits = [b for b in rec['blocks'] if b['id'] == 'IMG0_source_images']
        self.assertEqual(len(hits), 1, rec['blocks'])
        self.assertIn('assets/resources/art/manifest.json', hits[0]['message'])
        self.assertIn('line 1993', hits[0]['message'])
        self.assertTrue((p / 'assets/resources/art/manifest.json').read_text().count('"imageExt": ".webp"'))
        self.assertTrue(F.check_source_record(p))                 # K5 refuses the writer

    def test_imageExt_png_passes(self):
        p = self.copy('.png')
        rec = F.finalize_source(p, 'remake', app_id=APP)
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        self.assertEqual(rec['policy'], 'new')
        self.assertEqual(F.check_source_record(p), [])


class RecordedOptions(WF.KitInSync):
    def src(self, options):
        p = H.project24(self.d / 'p')
        (p / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').write_text(WF.kit_config(), encoding='utf-8')
        rec = F.finalize_source(p, 'remake', options=options)
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        return p, rec

    @staticmethod
    def differs(findings):
        return [f for f in findings if f['id'] == 'K5_source_finalized' and 'keep-webp-exception differs' in f['message']]

    def test_record_keeps_options(self):
        _, rec = self.src(EXC)
        self.assertEqual(rec['options'], {'keep_webp_exception': EXC['keep_webp_exception']})
        self.assertEqual(F.read_source_record(self.d / 'p')['options'], rec['options'])

    def test_same_option_both_sides_passes(self):
        p, _ = self.src(EXC)
        self.assertEqual(F.check_source_record(p, options=dict(EXC)), [])
        q = H.project24(self.d / 'q')
        (q / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').write_text(WF.kit_config(), encoding='utf-8')
        F.finalize_source(q, 'remake')
        self.assertEqual(F.check_source_record(q, options={}), [])

    def test_source_without_writer_with_refused(self):
        p, _ = self.src(None)
        self.assertTrue(self.differs(F.check_source_record(p, options=dict(EXC))))

    def test_source_with_writer_without_refused(self):
        p, _ = self.src(EXC)
        self.assertTrue(self.differs(F.check_source_record(p, options={})))

    def test_different_reason_refused(self):
        p, _ = self.src(EXC)
        self.assertTrue(self.differs(F.check_source_record(p, options={'keep_webp_exception': 'other reason'})))

    def test_writer_refuses_differing_options_before_touching_the_build(self):
        # W-F1b request 1 (applied by the parent): the writers' early K5 gets this run's options, so a writer
        # whose --keep-webp-exception differs from the source record refuses before finalize_native edits b.
        p, _ = self.src(EXC)
        b = self.native()

        def snap():
            return {str(f.relative_to(b)): f.read_bytes() for f in sorted(b.rglob('*')) if f.is_file()}

        before = snap()
        record, context, problems = M.finalize_for_writer(b, p, 'remake', APP, {})   # writer without the option
        self.assertIsNone(record)
        self.assertIsNone(context)
        self.assertTrue(any('K5_source_finalized' in s and 'keep-webp-exception differs' in s for s in problems),
                        problems)
        self.assertEqual(snap(), before)

    def test_kit_parts_gate_compares_the_writer_options(self):
        # The gate keeps its own comparison as a second line: a context whose options differ from the record.
        p, _ = self.src(EXC)
        b = self.native()
        record, context, problems = M.finalize_for_writer(b, p, 'remake', APP, dict(EXC))   # same option
        self.assertIsNotNone(record, problems)
        context = dict(context, finalize_options={})
        out = G.run(F._native_files(b), b, 'remake', policy=record['policy'], context=context)
        self.assertTrue(self.differs(out['blocks']), out['blocks'])

    def test_preflight_without_options_not_compared(self):
        p, _ = self.src(EXC)
        self.assertEqual(F.check_source_record(p), [])


class PartsTable(unittest.TestCase):
    def table(self, state, changed):
        rec = {'policy': 'new', 'steps': [{'step': 'touch', 'state': state, 'changed': changed, 'blocks': [],
                                           'warnings': []}]}
        return F.summary_table(rec)[0]['result']

    def test_kit_current_with_load_line_inserted(self):
        self.assertEqual(self.table('kit_current', [{'file': 'game.js', 'what': 'touch3x load line'}]), '已装（插加载行）')

    def test_kit_current_unchanged_stays_already_there(self):
        self.assertEqual(self.table('kit_current', []), '原本就有')

    def test_kit_current_other_change(self):
        self.assertEqual(self.table('kit_current', [{'file': 'x', 'what': 'something'}]), '已装（本次有改动）')

    def test_real_3x_build_with_kit_file_copied_from_build_templates(self):
        m = H.manifest()
        b = H.build3x(H.tmpdir(self) / 'b')
        (b / 'tiktok-touch-3x.js').write_bytes(H.kit_bytes(m, 'touch3x'))   # Creator copied it from build-templates
        rec = F.finalize_native(b, None, 'remake', APP, policy='new', manifest=m, steps=('touch',))
        row = rec['table'][0]
        self.assertEqual(rec['steps'][0]['state'], 'kit_current')
        self.assertEqual((row['result'], row['changed']), ('已装（插加载行）', 1), rec['steps'])


class NoWebpException3x(unittest.TestCase):
    def setUp(self):
        self.d = H.tmpdir(self)

    def project3(self):
        p = self.d / 'p3'
        (p / 'assets' / 'art').mkdir(parents=True)
        (p / 'package.json').write_text(json.dumps({'creator': {'version': '3.8.8'}}))
        Image.new('RGBA', (8, 8)).save(p / 'assets/art/a.webp', 'WEBP', lossless=True)
        (p / 'assets/art/a.webp.meta').write_text(json.dumps({'ver': '1.0.27', 'importer': 'image', 'uuid': uid(5),
                                                              'files': ['.json', '.webp'], 'subMetas': {},
                                                              'userData': {'type': 'texture', 'hasAlpha': True}}))
        return p

    def test_images_step_refuses_on_3x(self):
        p = self.project3()
        before = tree(p)
        r = images.apply({'project': p, 'policy': 'new', 'options': EXC})
        self.assertTrue(any('not available for Cocos 3.x' in b['message'] and 'v7.8' in b['message']
                            and '30 MB' in b['message'] for b in r['blocks']), r)
        self.assertEqual(tree(p), before)

    def test_finalize_source_refuses_before_any_step(self):
        p = self.project3()
        before = tree(p)
        rec = F.finalize_source(p, 'remake', policy='new', options=EXC)
        self.assertEqual([b['id'] for b in rec['blocks']], ['K_webp_exception_3x'])
        self.assertEqual(rec['steps'], [])
        self.assertEqual({k: v for k, v in tree(p).items() if not k.startswith('.tiktok-kit/')}, before)

    def test_finalize_native_refuses_before_any_step(self):
        b = H.build3x(self.d / 'b')
        before = tree(b)
        rec = F.finalize_native(b, None, 'remake', APP, policy='new', options=EXC)
        self.assertIn('K_webp_exception_3x', [x['id'] for x in rec['blocks']])
        self.assertEqual(tree(b), before)

    def test_kit_parts_refuses_3x_writer_with_exception(self):
        b = H.build3x(self.d / 'b')
        out = G.run(F._native_files(b), b, 'remake', policy='new',
                    context={'writer': True, 'finalize_record': None, 'project': None, 'finalize_options': EXC})
        self.assertIn('K_webp_exception_3x', {f['id'] for f in out['blocks']})

    def test_2x_exception_still_allowed(self):
        self.assertEqual(F.webp_exception_3x(2, EXC), [])
        self.assertTrue(F.webp_exception_3x(3, EXC))
        self.assertEqual(F.webp_exception_3x(3, {}), [])
        p = art24(self.d / 'p24', None)
        r = images.apply({'project': p, 'policy': 'new', 'options': EXC})
        self.assertEqual(r['blocks'], [])
        self.assertTrue((p / 'assets/resources/art/hero.webp').is_file())


if __name__ == '__main__':
    unittest.main(verbosity=1)
