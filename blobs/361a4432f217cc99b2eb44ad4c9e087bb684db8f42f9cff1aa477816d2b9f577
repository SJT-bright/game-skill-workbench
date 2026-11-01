#!/usr/bin/env python3
"""chinese_audit.py (English pack, 2026-11-01): the twelve cases of the Garden Guardians report (section 9), text
scanning, and one real macOS Vision case. Logic tests use the fake recognizer, so every computer gives the same result.
Run: python3 -B test_chinese_audit.py
"""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import chinese_audit as C  # noqa: E402

from PIL import Image, ImageDraw  # noqa: E402

UUID_PAGE = '11111111-2222-3333-4444-555555555555'
UUID_BTN = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'


def pattern(w, h, seed):
    """An asymmetric picture (so a wrong rotation gives other pixels), different for every seed."""
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w // 3, h - 1], fill=(200, (seed * 37) % 256, 40, 255))
    d.rectangle([w // 2, 0, w - 1, h // 4], fill=((seed * 91) % 256, 30, 220, 255))
    d.point((w - 1, h - 1), fill=(seed % 256, 255, 0, 255))
    return img


def psha(img):
    return C.pixels_sha256(img)


class Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory(prefix='chinese-audit-test-')
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.proj = self.root / 'proj'
        (self.proj / 'assets' / 'res').mkdir(parents=True)
        (self.proj / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}', encoding='utf-8')
        self.out = self.proj / 'docs' / 'english' / 'chinese-audit'
        self.fake = {}

    # ---- fixtures
    def spine_page(self, wave_seed=1, wave_xy=(110, 10), rotate_wave=False):
        """highwave-like page: 'black' and 'wave' regions on a 300x100 page."""
        page = Image.new('RGBA', (300, 100), (0, 0, 0, 0))
        black = pattern(100, 80, 50)
        wave = pattern(60, 30, wave_seed)
        page.paste(black, (2, 2))
        stored = wave.transpose(Image.ROTATE_90) if rotate_wave else wave     # Spine stores turned CCW
        page.paste(stored, wave_xy)
        p = self.proj / 'assets' / 'res' / 'highwave.png'
        page.save(str(p))
        self.meta(p, UUID_PAGE)
        self.write_atlas(wave_xy, rotate_wave)
        return {'page': psha(page), 'black': psha(black), 'wave': psha(wave)}

    def write_atlas(self, wave_xy=(110, 10), rotate_wave=False):
        (self.proj / 'assets' / 'res' / 'highwave.atlas').write_text(
            '\nhighwave.png\nsize: 300,100\nformat: RGBA8888\nfilter: Linear,Linear\nrepeat: none\n'
            'black\n  rotate: false\n  xy: 2, 2\n  size: 100, 80\n  orig: 104, 80\n  offset: 2, 0\n  index: -1\n'
            'wave\n  rotate: %s\n  xy: %d, %d\n  size: 60, 30\n  orig: 60, 30\n  offset: 0, 0\n  index: -1\n'
            % ('true' if rotate_wave else 'false', wave_xy[0], wave_xy[1]), encoding='utf-8')

    def meta(self, p, uuid):
        Path(str(p) + '.meta').write_text(json.dumps({'ver': '2.3.7', 'uuid': uuid, 'type': 'sprite'}), encoding='utf-8')

    def run_cli(self, *args):
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {C.ENV_FAKE: json.dumps(self.fake)}), contextlib.redirect_stdout(buf):
            code = C.main([str(a) for a in args])
        return code, buf.getvalue()

    def scan(self, *extra, ocr='fake'):
        code, text = self.run_cli('scan', '--project', self.proj, '--ocr', ocr, *extra)
        self.assertEqual(code, 0, text)
        return json.loads((self.out / 'audit.json').read_text(encoding='utf-8'))

    def check(self, *extra):
        code, text = self.run_cli('check', '--project', self.proj, *extra)
        result = json.loads((self.out / 'check-result.json').read_text(encoding='utf-8'))
        return code, result, text

    def review(self, *args):
        return self.run_cli('review', '--project', self.proj, *args)

    def item(self, audit, **match):
        for i in audit['items']:
            if all(i.get(k) == v for k, v in match.items()):
                return i
        self.fail('no item %s' % match)

    def codes(self, result):
        return [p['code'] for p in result['problems']]


class ReportCases(Base):
    def test_01_spine_slice_with_chinese_is_found_and_blocks(self):
        s = self.spine_page()
        self.fake = {s['wave']: '高波来袭！'}        # the whole page reads as nothing, only the slice has text
        audit = self.scan()
        wave = self.item(audit, kind='slice', slice='wave')
        page = self.item(audit, kind='image', file='assets/res/highwave.png')
        self.assertEqual(page['scan'], 'auto_covered')
        self.assertEqual(wave['scan'], 'needs_review')
        self.assertIn('高波来袭', wave['reasons'][0])
        self.assertTrue((self.out / wave['slice_file']).is_file())
        code, result, text = self.check()
        self.assertEqual(code, 1, text)
        rows = [p for p in result['problems'] if p.get('id') == wave['id']]
        self.assertEqual(rows[0]['code'], 'needs_review')
        self.assertEqual(rows[0]['slice'], 'wave')
        self.assertFalse(result['passed'])

    def test_02_hand_written_old_record_does_not_pass(self):
        self.spine_page()
        old = self.proj / 'docs' / 'english'
        old.mkdir(parents=True)
        (old / 'image-review.json').write_text(json.dumps({'schema': 'image_review.v1', 'images': [
            {'file': 'assets/res/highwave.png', 'status': 'done', 'chinese': 'no', 'atlas': True,
             'slices_reviewed': True, 'reviewer': 'someone'}]}), encoding='utf-8')
        code, result, text = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(result['problems'][0]['code'], 'no_audit')
        self.assertIn('image-review.json', result['problems'][0]['message'])
        missing = {p.get('slice') or p.get('file') for p in result['problems'] if p['code'] == 'needs_review'}
        self.assertEqual(missing, {'assets/res/highwave.png', 'black', 'wave'})
        # a hand-made audit.json with passed: true and no receipts is refused too
        self.scan()
        shutil.rmtree(str(self.out / 'ocr'))
        audit = json.loads((self.out / 'audit.json').read_text(encoding='utf-8'))
        audit['passed'] = True
        (self.out / 'audit.json').write_text(json.dumps(audit), encoding='utf-8')
        code, result, _ = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(self.codes(result).count('receipt_missing'), 3)

    def test_03_atlas_coordinates_or_rotation_change_voids_slice_evidence(self):
        self.spine_page()
        self.scan()
        self.assertEqual(self.check()[0], 0)
        png = (self.proj / 'assets' / 'res' / 'highwave.png').read_bytes()
        for xy, rot in (((111, 10), False), ((110, 10), True)):
            with self.subTest(xy=xy, rotate=rot):
                self.write_atlas(xy, rot)
                code, result, _ = self.check()
                self.assertEqual(code, 1)
                self.assertIn('files_changed', self.codes(result))
                self.assertTrue(any(p['code'] == 'not_scanned_now' and p.get('slice') == 'wave' for p in result['problems']))
                self.assertEqual((self.proj / 'assets' / 'res' / 'highwave.png').read_bytes(), png)
        self.scan()
        self.assertEqual(self.check()[0], 0)

    def test_04_new_picture_with_review_evidence_of_the_old_one_is_refused(self):
        s1 = self.spine_page(wave_seed=1)
        new_wave = pattern(60, 30, 2)
        self.fake = {s1['wave']: '近≤', psha(new_wave): '近≤'}
        audit = self.scan()
        wave = self.item(audit, kind='slice', slice='wave')
        old_slice = self.out / wave['slice_file']
        code, text = self.review('--id', wave['id'], '--verdict', 'false_positive', '--by', 'tester',
                                 '--evidence', old_slice, '--reason', 'particle')
        self.assertEqual(code, 0, text)
        self.assertEqual(self.check()[0], 0)
        self.spine_page(wave_seed=2)                    # the picture is replaced
        code, text = self.review('--id', wave['id'], '--verdict', 'false_positive', '--by', 'tester',
                                 '--evidence', old_slice)
        self.assertEqual(code, 1, text)                 # before a new scan the item is not current
        audit = self.scan()
        code, result, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn('review_for_old_version', self.codes(result))
        code, text = self.review('--id', wave['id'], '--verdict', 'false_positive', '--by', 'tester',
                                 '--evidence', old_slice)
        self.assertEqual(code, 1, text)
        self.assertIn('另一版的切片', text)
        new_slice = self.out / self.item(audit, kind='slice', slice='wave')['slice_file']
        code, text = self.review('--id', wave['id'], '--verdict', 'false_positive', '--by', 'tester',
                                 '--evidence', new_slice)
        self.assertEqual(code, 0, text)
        self.assertEqual(self.check()[0], 0)

    def test_05_failed_recognition_or_uncovered_slice_stays_open(self):
        s = self.spine_page()
        self.fake = {s['wave']: 'fail'}
        audit = self.scan()
        wave = self.item(audit, kind='slice', slice='wave')
        self.assertEqual(wave['scan'], 'needs_review')
        code, result, _ = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any(p.get('id') == wave['id'] and '识字失败' in p['message'] for p in result['problems']))
        # someone edits audit.json to call the failed receipt "no text"
        doc = json.loads((self.out / 'audit.json').read_text(encoding='utf-8'))
        for i in doc['items']:
            if i['id'] == wave['id']:
                i['scan'] = 'auto_covered'
        (self.out / 'audit.json').write_text(json.dumps(doc), encoding='utf-8')
        self.assertIn('audit_disagrees', self.codes(self.check()[1]))
        # a slice outside the page cannot be cut: it is a finding, never a pass
        self.write_atlas((280, 10))
        self.fake = {}
        audit = self.scan()
        wave = self.item(audit, kind='slice', slice='wave')
        self.assertIn('超出纹理页', wave['error'])
        code, result, _ = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any(p.get('id') == wave['id'] for p in result['problems']))

    def test_06_multi_page_rotated_trimmed_atlases_are_cut_completely(self):
        res = self.proj / 'assets' / 'res'
        a, b, c, d = pattern(40, 20, 11), pattern(30, 50, 12), pattern(24, 16, 13), pattern(36, 18, 14)
        p1 = Image.new('RGBA', (128, 64), (0, 0, 0, 0))
        p1.paste(a, (0, 0))
        p1.paste(b.transpose(Image.ROTATE_90), (60, 0))      # rotate: 90 -> stored turned CCW, area 50x30
        p1.save(str(res / 'multi.png'))
        p2 = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        p2.paste(c, (4, 4))
        p2.save(str(res / 'multi2.png'))
        (res / 'multi.atlas').write_text(
            'multi.png\nsize:128,64\nfilter:Linear,Linear\npma:true\n'
            'a\nbounds:0,0,40,20\noffsets:2,1,44,22\n'
            'b\nbounds:60,0,30,50\nrotate:90\n'
            '\nmulti2.png\nsize:64,64\nfilter:Linear,Linear\n'
            'c\nbounds:4,4,24,16\n', encoding='utf-8')
        sheet = Image.new('RGBA', (100, 60), (0, 0, 0, 0))
        sheet.paste(d.transpose(Image.ROTATE_270), (10, 5))   # TexturePacker: stored turned CW, area 18x36
        sheet.paste(a, (50, 30))
        sheet.save(str(res / 'ui.png'))
        frames = {'d.png': {'textureRect': '{{10,5},{36,18}}', 'textureRotated': True, 'spriteOffset': '{0,0}',
                            'spriteSize': '{36,18}', 'spriteSourceSize': '{40,20}'},
                  'a2.png': {'frame': '{{50,30},{40,20}}', 'rotated': False, 'offset': '{1,0}',
                             'sourceColorRect': '{{1,0},{40,20}}', 'sourceSize': '{42,20}'}}
        import plistlib
        (res / 'ui.plist').write_bytes(plistlib.dumps({'frames': frames, 'metadata': {
            'format': 3, 'textureFileName': 'ui.png', 'realTextureFileName': 'ui.png', 'size': '{100,60}'}}))
        self.fake = {psha(b): '高波来袭', psha(d): '开始游戏'}
        audit = self.scan()
        slices = {(i['atlas_file'].rsplit('/', 1)[-1], i['slice']): i for i in audit['items'] if i['kind'] == 'slice'}
        self.assertEqual(set(slices), {('multi.atlas', 'a'), ('multi.atlas', 'b'), ('multi.atlas', 'c'),
                                       ('ui.plist', 'd.png'), ('ui.plist', 'a2.png')})
        for key, want in ((('multi.atlas', 'a'), a), (('multi.atlas', 'b'), b), (('multi.atlas', 'c'), c),
                          (('ui.plist', 'd.png'), d), (('ui.plist', 'a2.png'), a)):
            self.assertEqual(slices[key]['pixels_sha256'], psha(want), key)
            self.assertTrue((self.out / slices[key]['slice_file']).is_file())
        self.assertEqual(slices[('multi.atlas', 'c')]['file'], 'assets/res/multi2.png')
        self.assertEqual(slices[('multi.atlas', 'a')]['region']['orig'], [44, 22])
        self.assertEqual(slices[('multi.atlas', 'b')]['scan'], 'needs_review')
        self.assertEqual(slices[('ui.plist', 'd.png')]['scan'], 'needs_review')
        receipt = json.loads((self.out / ('ocr/%s.json' % slices[('multi.atlas', 'b')]['ocr_key'])).read_text(encoding='utf-8'))
        self.assertEqual(receipt['prepared']['variants'], ['upright', 'turned_180'])   # both directions read
        self.assertGreaterEqual(min(receipt['prepared']['size']), C.MIN_OCR_SIDE)        # small slice enlarged
        self.assertGreater(receipt['prepared']['scale'], 1)

    def test_07_effect_misread_as_text_passes_with_slice_evidence_and_is_not_touched(self):
        s = self.spine_page()
        before = (self.proj / 'assets' / 'res' / 'highwave.png').read_bytes()
        self.fake = {s['black']: '近≤'}
        audit = self.scan()
        black = self.item(audit, kind='slice', slice='black')
        self.assertEqual(self.check()[0], 1)
        code, text = self.review('--id', black['id'], '--verdict', 'false_positive', '--by', 'main agent',
                                 '--evidence', self.out / black['slice_file'], '--reason', '白色受击粒子，不是字')
        self.assertEqual(code, 0, text)
        code, result, text = self.check()
        self.assertEqual(code, 0, text)
        self.assertTrue(result['passed'])
        self.assertEqual((self.proj / 'assets' / 'res' / 'highwave.png').read_bytes(), before)

    def _export(self, data):
        exp = self.root / 'web-mobile'
        p = exp / 'assets' / 'resources' / 'native' / UUID_BTN[:2] / (UUID_BTN + '.ab12c.png')
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        (exp / 'index.html').write_text('<html></html>', encoding='utf-8')
        return exp, p

    def _button(self, seed):
        img = pattern(80, 40, seed)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return img, buf.getvalue()

    def test_08_export_still_has_the_old_chinese_picture(self):
        old_img, old_bytes = self._button(21)
        new_img, new_bytes = self._button(22)
        btn = self.proj / 'assets' / 'res' / 'btn.png'
        btn.write_bytes(new_bytes)                         # source already fixed
        self.meta(btn, UUID_BTN)
        docs = self.proj / 'docs' / 'english'
        docs.mkdir(parents=True)
        (docs / 'pre-english-images.json').write_text(json.dumps(
            {'images': {C.sha_bytes(old_bytes): 'assets/res/btn.png'}}), encoding='utf-8')
        exp, ep = self._export(old_bytes)
        os.utime(str(ep), (btn.stat().st_mtime - 60,) * 2)
        self.fake = {psha(old_img): '开始游戏'}
        self.scan('--export', exp)
        code, result, text = self.check('--export', exp)
        self.assertEqual(code, 1, text)
        self.assertIn('export_old_image', self.codes(result))
        self.assertTrue(any(p['code'] == 'needs_review' and p['kind'] == 'export_image' for p in result['problems']))
        self.assertEqual(self.check()[0], 0)                # without --export only the (fixed) source is checked
        ep.write_bytes(new_bytes)                           # rebuild
        self.assertIn('export_changed', self.codes(self.check('--export', exp)[1]))
        self.scan('--export', exp)
        code, result, text = self.check('--export', exp)
        self.assertEqual(code, 0, text)

    def test_09_corrected_conclusion_replaces_the_old_one_and_conflicts_block(self):
        img, data = self._button(31)
        btn = self.proj / 'assets' / 'res' / 'btn.png'
        btn.write_bytes(data)
        self.meta(btn, UUID_BTN)
        exp, _ = self._export(data)
        self.fake = {psha(img): '回'}
        audit = self.scan('--export', exp)
        it = self.item(audit, kind='image', file='assets/res/btn.png')
        ev = self.root / 'look.png'
        img.save(str(ev))
        self.assertEqual(self.review('--id', it['id'], '--verdict', 'false_positive', '--by', 'a', '--evidence', ev)[0], 0)
        self.assertEqual(self.check('--export', exp)[0], 0)         # export picture uses the source conclusion
        self.assertEqual(self.review('--id', it['id'], '--verdict', 'chinese', '--by', 'b', '--evidence', ev)[0], 0)
        code, result, _ = self.check('--export', exp)
        self.assertEqual(code, 1)
        self.assertIn('review_conflict', self.codes(result))
        code, text = self.review('--id', it['id'], '--verdict', 'chinese', '--by', 'b', '--evidence', ev,
                                 '--supersedes', 'R0001', '--reason', '看清了是「回」字')
        self.assertEqual(code, 0, text)
        code, result, _ = self.check('--export', exp)
        self.assertEqual(code, 1)
        cs = self.codes(result)
        self.assertNotIn('review_conflict', cs)
        self.assertIn('confirmed_chinese', cs)
        self.assertIn('export_source_not_ok', cs)                     # the export no longer rides on R0001
        self.assertIn('pre_english_chinese_here', cs)                 # those bytes are confirmed Chinese

    def test_10_unchanged_project_reuses_receipts_and_still_checks_snapshot(self):
        self.spine_page()
        img, data = self._button(41)
        btn = self.proj / 'assets' / 'res' / 'btn.png'
        btn.write_bytes(data)
        self.meta(btn, UUID_BTN)
        exp, _ = self._export(data)
        first = self.scan('--export', exp)
        self.assertGreater(first['stats']['ocr_calls'], 0)
        second = self.scan('--export', exp)
        self.assertEqual(second['stats']['ocr_calls'], 0)
        self.assertEqual(second['stats']['ocr_reused'], first['stats']['ocr_calls'])
        snap = self.root / 'snapshot'
        shutil.copytree(str(exp), str(snap))
        code, result, text = self.check('--export', exp, '--snapshot', snap)
        self.assertEqual(code, 0, text)
        self.assertEqual(result['snapshot']['sha256'], result['export']['manifest_sha256'])
        (snap / 'index.html').write_text('<html>other build</html>', encoding='utf-8')
        code, result, _ = self.check('--export', exp, '--snapshot', snap)
        self.assertEqual(code, 1)
        self.assertIn('snapshot_mismatch', self.codes(result))

    def test_11_no_recognizer_means_everything_waits_for_review(self):
        self.spine_page()
        audit = self.scan(ocr='none')
        pics = [i for i in audit['items'] if i['kind'] in ('image', 'slice')]
        self.assertEqual({i['scan'] for i in pics}, {'not_scanned'})
        code, result, _ = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(self.codes(result).count('needs_review'), len(pics))
        code, text = self.review('--id', pics[0]['id'], '--verdict', 'no_text', '--by', 'x')
        self.assertEqual(code, 1, text)                              # no evidence: refused
        for i in pics:
            ev = self.out / i['slice_file'] if i['kind'] == 'slice' else self.proj / i['file']
            self.assertEqual(self.review('--id', i['id'], '--verdict', 'no_text', '--by', 'x', '--evidence', ev)[0], 0)
        self.assertEqual(self.check()[0], 0)

    def test_12_isolated_render_is_listed_apart_from_natural_play(self):
        s = self.spine_page()
        self.fake = {s['wave']: 'INC0MlNG 高'}
        audit = self.scan()
        wave = self.item(audit, kind='slice', slice='wave')
        shot = self.root / 'warning-render.png'
        pattern(200, 100, 99).save(str(shot))
        code, text = self.review('--id', wave['id'], '--verdict', 'english_only', '--by', 'main agent',
                                 '--evidence', shot, '--evidence-kind', 'isolated_render',
                                 '--reason', '真引擎隔离渲染 0.33 秒画面是 INCOMING!')
        self.assertEqual(code, 0, text)
        code, result, text = self.check()
        self.assertEqual(code, 0, text)
        self.assertEqual([r['item_id'] for r in result['evidence_kinds']['isolated_render']], [wave['id']])
        self.assertEqual(result['evidence_kinds']['natural_play'], [])
        self.assertIn('隔离渲染', text)
        copied = list((self.out / 'evidence').glob('*-warning-render.png'))
        self.assertEqual(len(copied), 1)                              # outside evidence is copied and bound by sha
        copied[0].write_bytes(b'changed')
        code, result, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn('review_evidence_bad', self.codes(result))


class TextScan(Base):
    def test_text_kinds(self):
        res = self.proj / 'assets' / 'res'
        (res / 'Game.ts').write_text(
            '// 游戏主逻辑\n/* 注释：不显示 */\nconsole.log("调试信息");\ncc.warn("警告", 1);\n'
            'const title = "开始游戏";\nconst esc = "\\u9ad8\\u6ce2";\nconst re = /[一-龥]/;\nlet n = 10 / 2;\n'
            'const tpl = `第${n}关`;\nshow(cc.log ? "确定" : "");\n', encoding='utf-8')
        (res / 'Home.prefab').write_text(json.dumps([
            {'__type__': 'cc.Node', '_name': '开始按钮'},
            {'__type__': 'cc.Label', '_string': '开始', '_N$string': '开始'},
            {'__type__': 'cc.EditBox', '_N$placeholder': '请输入'},
            {'__type__': 'Shop', 'tip': '金币不足'}], ensure_ascii=True), encoding='utf-8')
        (res / 'wave.json').write_text(json.dumps({'skeleton': {'spine': '3.8.99', 'images': 'C:/新建文件夹',
                                                               'audio': 'D:/音效'}, 'bones': [{'name': '根'}]},
                                                  ensure_ascii=False), encoding='utf-8')
        (res / 'config.json').write_text(json.dumps({'levels': [{'title': '第一关'}]}, ensure_ascii=False), encoding='utf-8')
        (res / 'font.fnt').write_text('info face="x"\npage id=0 file="font.png"\nchars count=2\n'
                                      'char id=48 x=0 y=0 width=8 height=8\nchar id=39640 x=8 y=0 width=8 height=8\n',
                                      encoding='utf-8')
        Image.new('RGBA', (16, 8)).save(str(res / 'font.png'))
        audit = self.scan()
        texts = [i for i in audit['items'] if i['kind'] == 'text']
        got = {(t['file'].rsplit('/', 1)[-1], t['category'], t['decoded'], t['scan']) for t in texts}
        want_needs = {('Game.ts', 'script_string', '开始游戏'), ('Game.ts', 'script_string', '高波'),
                      ('Game.ts', 'script_string', '第${n}关'), ('Game.ts', 'script_string', '确定'),
                      ('Home.prefab', 'label', '开始'), ('Home.prefab', 'label', '请输入'),
                      ('Home.prefab', 'serial_field', '金币不足'), ('config.json', 'config_value', '第一关'),
                      ('font.fnt', 'bmfont_glyph', '高')}
        want_auto = {('Game.ts', 'script_comment', '游戏主逻辑'), ('Game.ts', 'script_comment', '注释：不显示'),
                     ('Game.ts', 'console_log', '调试信息'), ('Game.ts', 'console_log', '警告'),
                     ('Home.prefab', 'node_name', '开始按钮'), ('wave.json', 'spine_editor_path', 'C:/新建文件夹'),
                     ('wave.json', 'spine_editor_path', 'D:/音效'), ('wave.json', 'spine_internal', '根')}
        for f, cat, val in want_needs:
            self.assertIn((f, cat, val, 'needs_review'), got)
        for f, cat, val in want_auto:
            self.assertIn((f, cat, val, 'auto_pass'), got)
        esc = [t for t in texts if t['decoded'] == '高波'][0]
        self.assertTrue(esc['decoded_escapes'])
        self.assertEqual(esc['line'], 6)
        self.assertEqual(len([t for t in texts if t['decoded'] == '开始' and t['category'] == 'label']), 2)
        self.assertEqual(len({t['id'] for t in texts}), len(texts))
        regex = [t for t in texts if '一-龥' in t['decoded']]
        self.assertEqual([(t['category'], t['scan']) for t in regex], [('script_regex', 'auto_pass')])
        # a text finding needs a conclusion before check passes; a reason is enough for text
        code, result, _ = self.check()
        self.assertEqual(code, 1)
        for t in texts:
            if t['scan'] == 'needs_review':
                self.assertEqual(self.review('--id', t['id'], '--verdict', 'not_displayed', '--by', 'x',
                                             '--reason', 'test')[0], 0)
        self.assertEqual(self.check()[0], 0)

    def test_full_width_mark_in_english_is_not_chinese_but_han_is(self):
        rec = lambda *t: {'status': 'ok', 'results': [{'text': x, 'confidence': 1.0} for x in t]}
        self.assertEqual(C.classify(rec('INCOMING！'))[0], 'auto_covered')
        self.assertEqual(C.classify(rec('高波来袭！'))[0], 'needs_review')
        self.assertEqual(C.classify(rec('？'))[0], 'needs_review')
        self.assertEqual(C.classify({'status': 'ok', 'results': [{'text': '∞', 'confidence': 0.3}]})[0], 'needs_review')
        self.assertEqual(C.classify({'status': 'ok', 'results': [{'text': 'GO', 'confidence': 0.3}]})[0], 'auto_covered')
        self.assertEqual(C.classify({'status': 'failed', 'error': 'x'})[0], 'needs_review')
        self.assertEqual(C.classify(None)[0], 'needs_review')

    def test_bad_input_and_out_inside_assets(self):
        self.assertEqual(self.run_cli('check', '--project', self.root / 'nope')[0], 2)
        self.assertEqual(self.run_cli('scan', '--project', self.proj, '--ocr', 'fake',
                                      '--out', self.proj / 'assets' / 'x')[0], 2)
        self.assertFalse((self.proj / 'assets' / 'x').exists())
        self.assertEqual(self.run_cli('frobnicate')[0], 2)
        self.spine_page()
        self.scan()
        self.assertEqual(self.review('--id', 'img-nope', '--verdict', 'no_text', '--by', 'x', '--reason', 'r')[0], 2)


def _cjk_font():
    for p in ('/System/Library/Fonts/PingFang.ttc', '/System/Library/Fonts/Hiragino Sans GB.ttc',
              '/System/Library/Fonts/STHeiti Medium.ttc', '/System/Library/Fonts/STHeiti Light.ttc'):
        if Path(p).is_file():
            return p
    return None


@unittest.skipUnless(sys.platform == 'darwin', 'Vision 只在 macOS 上')
@unittest.skipUnless(shutil.which('swiftc') or shutil.which('swift'), '没有 swift')
@unittest.skipUnless(_cjk_font(), '没有中文字体')
class RealExportFindings(Base):
    """简化.11 integration on a real English export (SausageRun English v1): @property tooltips were 8 "maybe shown"
    script strings, and 857 level-config "name" values each needed a conclusion of their own."""

    def test_property_tooltips_are_editor_only_but_other_strings_wait(self):
        (self.proj / 'assets' / 'res' / 'joy.ts').write_text(
            "@property({ type: cc.Node, tooltip: '摇杆背景节点' })\njoyBk = null;\n"
            "@property({ displayName : \"最大半径\" })\nmaxR = 100;\n"
            "start() { this.label.string = '开始游戏'; }\n", encoding='utf-8')
        audit = self.scan()
        texts = {i['decoded']: i for i in audit['items'] if i['kind'] == 'text'}
        self.assertEqual(texts['摇杆背景节点']['category'], 'editor_label')
        self.assertEqual(texts['摇杆背景节点']['scan'], 'auto_pass')
        self.assertEqual(texts['最大半径']['scan'], 'auto_pass')
        self.assertEqual(texts['开始游戏']['scan'], 'needs_review')

    def test_review_a_batch_of_text_items_by_file_and_field(self):
        cfg = self.proj / 'assets' / 'res' / 'configs'
        cfg.mkdir()
        for n in (1, 2):
            (cfg / ('%d.json' % n)).write_text(json.dumps([{'name': '起点', 'x': 1}, {'name': '金币', 'tip': '小心'}],
                                                          ensure_ascii=False), encoding='utf-8')
        audit = self.scan()
        names = [i['id'] for i in audit['items'] if i['kind'] == 'text' and (i.get('field') or '').endswith('/name')]
        self.assertEqual(len(names), 4)
        code, text = self.review('--field', '/name$', '--verdict', 'not_displayed', '--by', 't', '--reason', 'x')
        self.assertEqual(code, 2, text)                                      # --field needs --file
        code, text = self.review('--file', 'assets/nothing/*.json', '--verdict', 'not_displayed', '--by', 't',
                                 '--reason', 'x')
        self.assertEqual(code, 1, text)                                      # selects nothing: refused
        code, text = self.review('--file', 'assets/res/configs/*.json', '--field', '/name$', '--verdict', 'not_displayed',
                                 '--by', 'main agent')                       # text needs evidence or a reason
        self.assertEqual(code, 1, text)
        code, text = self.review('--file', 'assets/res/configs/*.json', '--field', '/name$', '--verdict', 'not_displayed',
                                 '--by', 'main agent', '--reason', '关卡数据里的物件类型名，只用来匹配，不显示')
        self.assertEqual(code, 0, text)
        self.assertIn('选中 4 项', text)
        code, result, text = self.check()
        open_ids = {p.get('id') for p in result['problems'] if p['code'] == 'needs_review'}
        self.assertFalse(open_ids & set(names))
        tips = [i['id'] for i in audit['items'] if i['kind'] == 'text' and (i.get('field') or '').endswith('/tip')]
        self.assertTrue(set(tips) <= open_ids)                               # the other field still waits
        self.assertEqual(code, 1)


class RealVision(Base):
    def test_vision_reads_chinese_in_a_rotated_spine_slice(self):
        from PIL import ImageFont
        rec = C.VisionRecognizer()
        if not rec.available():
            self.skipTest('Vision 跑不起来：%s' % rec.note)
        font = ImageFont.truetype(_cjk_font(), 48)
        word = Image.new('RGBA', (300, 70), (0, 0, 0, 0))
        ImageDraw.Draw(word).text((8, 4), '高波来袭', font=font, fill=(255, 255, 255, 255))
        page = Image.new('RGBA', (200, 400), (0, 0, 0, 0))
        page.paste(word.transpose(Image.ROTATE_90), (20, 30))
        res = self.proj / 'assets' / 'res'
        page.save(str(res / 'warn.png'))
        (res / 'warn.atlas').write_text('warn.png\nsize: 200,400\nformat: RGBA8888\nfilter: Linear,Linear\n'
                                        'repeat: none\nwave\n  rotate: true\n  xy: 20, 30\n  size: 300, 70\n'
                                        '  orig: 300, 70\n  offset: 0, 0\n  index: -1\n', encoding='utf-8')
        audit = self.scan(ocr='vision')
        wave = self.item(audit, kind='slice', slice='wave')
        self.assertEqual(wave['scan'], 'needs_review', wave)
        self.assertTrue(any('高' in t or '袭' in t for t in wave['ocr_text']), wave['ocr_text'])
        self.assertEqual(self.check()[0], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
