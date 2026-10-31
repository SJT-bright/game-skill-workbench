#!/usr/bin/env python3
"""v7.8 H8 (no base-game image / model texture / sound left in a remake) and H10 (generated-art record), plus the two
small fixes of the same round: art_check re-runs itself with a numpy Python, and HUD digits on repeated play pieces
(Meteor Blaster block/boxtext) are not HUD numbers.

Bad must be caught, fixed must pass:
  H8  a remake without docs/art/base-assets.json fails; base-identical image / FBX-embedded texture / sound fails until
      replaced or kept with a why; English (board localize, art-style original) is not checked; tiny fill pixels and
      platform-kit files never count; the package writers re-check the sounds (ART_base_audio).
  H10 a picture not in docs/art/generated.json fails (企鹅雪道美术 v3: PIL + Fredoka buttons); recorded, derived and
      allowed pictures pass; tiktok_finalize source records its own WebP conversion.
"""
import contextlib
import io
import json
import os
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import art_records as AR  # noqa: E402
import art_receipt as R  # noqa: E402
import art_check  # noqa: E402
import tiktok_finalize as F  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402


def png(path, seed=1, size=(16, 16)):
    from PIL import Image
    im = Image.new('RGBA', size)
    for x in range(size[0]):
        for y in range(size[1]):
            im.putpixel((x, y), ((x * 37 + seed * 11) % 255, (y * 53 + seed) % 255, (x * y + seed * 7) % 255, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    path.write_bytes(buf.getvalue())
    return path


def pil_button(path, word='PLAY'):
    """What 企鹅雪道美术 v3 did: a button and its word drawn offline with PIL (not generated)."""
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (240, 90), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, 236, 86), radius=30, fill=(80, 170, 240, 255), outline=(20, 60, 120, 255), width=4)
    d.text((90, 35), word, fill=(255, 255, 255, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return path


def fbx_with_texture(path, texture):
    """A binary FBX holding `texture` as a raw 'R' property (how Video/Content stores an embedded image)."""
    body = b'Kaydara FBX Binary  \x00\x1a\x00' + struct.pack('<I', 7400) + b'\x00' * 40
    body += b'Content' + b'R' + struct.pack('<I', len(texture)) + texture + b'\x00' * 16
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def project(root, board='remake', engine=2):
    (root / 'assets').mkdir(parents=True, exist_ok=True)
    if engine == 3:
        (root / 'package.json').write_text('{"creator": {"version": "3.8.8"}}')
    else:
        (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    P.write_marker(root, board, '2.0')
    return root


class Tmp(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix='art-records-'))
        self.addCleanup(lambda: __import__('shutil').rmtree(self.d, True))

    def base_game(self, name='base'):
        """A base game: 2 pictures, 1 tiny fill pixel, 1 FBX with an embedded texture, 1 sound."""
        b = self.d / name
        png(b / 'assets' / 'ui' / 'btn_play.png', 1)
        png(b / 'assets' / 'ui' / 'coin.png', 2)
        png(b / 'assets' / 'ui' / 'dot.png', 3, size=(2, 2))
        self.tex = png(self.d / 'tex.png', 9).read_bytes()
        fbx_with_texture(b / 'assets' / 'model' / 'Fishbone.fbx', self.tex)
        (b / 'assets' / 'audio').mkdir(parents=True, exist_ok=True)
        (b / 'assets' / 'audio' / 'bgm.mp3').write_bytes(b'ID3' + b'base-music' * 50)
        return b


class H8Base(Tmp):
    def test_record_from_folder_and_zip_reads_images_sounds_and_fbx_textures(self):
        b = self.base_game()
        p = project(self.d / 'p')
        data = AR.record_base(p, b)
        self.assertEqual(data['counts'], {'images': 2, 'audio': 1, 'embedded': 1})
        self.assertEqual(data['tiny_skipped'], 1)
        z = self.d / 'base.zip'
        with zipfile.ZipFile(z, 'w') as zf:
            for f in b.rglob('*'):
                if f.is_file():
                    zf.write(f, 'Game/' + f.relative_to(b).as_posix())
            zf.writestr('__MACOSX/Game/assets/ui/._btn_play.png', b'junk')
        data = AR.record_base(p, z)
        self.assertEqual((data['counts'], data['base_type']), ({'images': 2, 'audio': 1, 'embedded': 1}, 'zip'))
        self.assertTrue(data['base_sha256'])

    def test_remake_without_a_base_record_fails_and_names_the_command(self):
        p = project(self.d / 'p')
        png(p / 'assets' / 'a.png', 5)
        r = AR.check_base(p)
        self.assertEqual((r['state'], r['ok']), ('no_record', False))
        self.assertIn('art_records.py base', r['message'])
        AR.record_none(p, 'made from scratch')
        self.assertEqual((AR.check_base(p)['state'], AR.check_base(p)['ok']), ('none', True))
        with self.assertRaises(ValueError):
            AR.record_none(p, '  ')

    def test_base_identical_image_texture_and_sound_fail_until_replaced_or_kept(self):
        b = self.base_game()
        p = project(self.d / 'p')
        AR.record_base(p, b)
        (p / 'assets' / 'ui').mkdir(parents=True)
        (p / 'assets' / 'ui' / 'play.png').write_bytes((b / 'assets/ui/btn_play.png').read_bytes())   # renamed copy
        (p / 'assets' / 'ui' / 'dot.png').write_bytes((b / 'assets/ui/dot.png').read_bytes())          # 2x2 fill: ok
        fbx_with_texture(p / 'assets' / 'model' / 'Fish.fbx', self.tex)                               # re-exported
        (p / 'assets' / 'sfx').mkdir()
        (p / 'assets' / 'sfx' / 'music.mp3').write_bytes((b / 'assets/audio/bgm.mp3').read_bytes())
        png(p / 'assets' / 'ui' / 'new.png', 40)
        r = AR.check_base(p)
        self.assertFalse(r['ok'])
        self.assertEqual(sorted((x['kind'], x['file']) for x in r['unlisted']),
                         [('audio', 'assets/sfx/music.mp3'), ('embedded', 'assets/model/Fish.fbx#embedded-0'),
                          ('image', 'assets/ui/play.png')])
        self.assertIn('base-keep.json', r['message'])
        # a keep entry without a why does not count
        (p / 'docs/art/base-keep.json').write_text(json.dumps({'keep': [{'file': 'assets/ui/play.png'}]}))
        self.assertEqual(len(AR.check_base(p)['unlisted']), 3)
        AR.record_reason(p, 'keep', ['assets/ui/play.png', 'assets/model/Fish.fbx'], 'hidden at runtime by Game.ts')
        png(p / 'assets' / 'sfx' / 'x.png', 77)
        (p / 'assets' / 'sfx' / 'music.mp3').write_bytes(b'ID3' + b'library sound' * 50)
        r = AR.check_base(p)
        self.assertTrue(r['ok'], r['message'])
        self.assertEqual(len(r['kept']), 2)
        self.assertIn('留着的', r['message'])

    def test_english_games_are_not_checked(self):
        b = self.base_game()
        for board, style in (('localize', ''), ('remake', 'original')):
            p = project(self.d / ('p' + board + style), board)
            if style:
                (p / 'docs').mkdir(exist_ok=True)
                (p / 'docs' / 'art-style.txt').write_text(style)
            (p / 'assets' / 'a.png').write_bytes((b / 'assets/ui/btn_play.png').read_bytes())
            r = AR.check_base(p, board if board == 'localize' else None)
            self.assertEqual((r['state'], r['ok']), ('not_applicable', None))

    def test_platform_kit_files_are_not_base_art(self):
        b = self.base_game()
        kit = sorted(AR.KIT_DIR.rglob('*.webp'))[0].read_bytes()
        (b / 'assets' / 'probe.webp').write_bytes(kit)
        p = project(self.d / 'p')
        AR.record_base(p, b)
        (p / 'assets' / 'probe.webp').write_bytes(kit)
        self.assertTrue(AR.check_base(p)['ok'])

    def test_init_records_the_base(self):
        b = self.base_game()
        p = self.d / 'p'
        (p / 'assets').mkdir(parents=True)
        (p / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(F.main(['init', '--project', str(p), '--board', 'remake', '--base', str(b)]), 0)
        self.assertIn('底子已记下', out.getvalue())
        self.assertEqual(AR.read_base(p)[0]['counts']['images'], 2)
        q = self.d / 'q'
        (q / 'assets').mkdir(parents=True)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(F.main(['init', '--project', str(q), '--board', 'remake']), 0)
        self.assertIn('还没记底子', out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(F.main(['init', '--project', str(q), '--board', 'remake', '--no-base-why', 'scratch']), 0)
        self.assertEqual(AR.read_base(q)[0]['base'], 'none')

    def test_cli_check_exit_codes(self):
        p = project(self.d / 'p')
        png(p / 'assets' / 'a.png', 5)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(AR.main(['check', '--project', str(p)]), 1)
            self.assertEqual(AR.main(['base', '--project', str(p), '--none', '--why', 'scratch']), 0)
            self.assertEqual(AR.main(['generated', '--project', str(p), '--prompt', 'a red gem', '--tool', 'image_gen',
                                      str(p / 'assets' / 'a.png')]), 0)
            self.assertEqual(AR.main(['check', '--project', str(p)]), 0)


class H8Writer(Tmp):
    """Sounds are not in the image receipt: the writers' receipt check compares them with the base."""

    def test_base_sound_refuses_a_new_remake_and_warns_a_legacy_one(self):
        b = self.base_game()
        p = project(self.d / 'p')
        AR.record_base(p, b)
        png(p / 'assets' / 'a.png', 30)
        R.write(p, 'pass', {'status': 'pass'})
        self.assertEqual(R.check(p, policy='new')['level'], 'ok')
        (p / 'assets' / 'bgm.mp3').write_bytes((b / 'assets/audio/bgm.mp3').read_bytes())
        out = R.check(p, policy='new')
        self.assertEqual((out['level'], out['gate']), ('block', R.GATE_BASE_AUDIO))
        self.assertIn('assets/bgm.mp3', out['message'])
        self.assertIn('底子原声', R.table_row(out)['result'])
        self.assertEqual(R.check(p, policy='legacy')['level'], 'warn')
        self.assertEqual(R.check(p, board='localize', policy='new')['level'], 'ok')
        AR.record_reason(p, 'keep', ['assets/bgm.mp3'], 'Saul asked to keep the theme')
        self.assertEqual(R.check(p, policy='new')['level'], 'ok')


class H10Generated(Tmp):
    def scratch_project(self, board='remake'):
        p = project(self.d / 'p', board)
        AR.record_none(p, 'made from scratch')
        return p

    def test_pil_drawn_button_is_not_a_generated_picture(self):
        p = self.scratch_project()
        pil_button(p / 'assets' / 'ui' / 'btn_play.png')
        r = AR.check_generated(p)
        self.assertEqual((r['ok'], [x['file'] for x in r['unrecorded']]), (False, ['assets/ui/btn_play.png']))
        self.assertIn('不是生成的图', r['message'])

    def test_recorded_final_file_raw_and_derive_chain_pass(self):
        p = self.scratch_project()
        raw = png(self.d / 'raw.png', 50, size=(64, 64))
        final = png(p / 'assets' / 'ui' / 'btn_play.png', 51)
        added = AR.record_generated(p, [final], 'codex image_gen', prompt='glossy PLAY button', raw=raw)
        self.assertEqual([bool(x.get('from_sha256')) for x in added], [False, True])
        self.assertTrue(AR.check_generated(p)['ok'])
        png(final, 52)                                     # cropped again by hand
        r = AR.check_generated(p)
        self.assertEqual((r['ok'], len(r['edited'])), (False, 1))
        self.assertIn('derive', r['message'])
        AR.record_derived(p, [final], how='cropped')
        self.assertTrue(AR.check_generated(p)['ok'])
        stray = png(p / 'assets' / 'ui' / 'other.png', 60)
        with self.assertRaises(ValueError):
            AR.record_derived(p, [stray])               # never recorded: derive cannot launder it

    def test_entries_without_prompt_or_source_do_not_count(self):
        p = self.scratch_project()
        f = png(p / 'assets' / 'a.png', 5)
        (p / 'docs/art/generated.json').write_text(json.dumps({'images': [
            {'sha256': AR.sha(f.read_bytes()), 'file': 'assets/a.png', 'tool': 'pil'}]}))
        r = AR.check_generated(p)
        self.assertFalse(r['ok'])
        self.assertIn('找不到提示词或来源', r['message'])
        with self.assertRaises(ValueError):
            AR.record_generated(p, [f], 'pil')
        AR.record_generated(p, [f], 'kenney', source='https://kenney.nl/assets/ui-pack', license_='CC0')
        self.assertTrue(AR.check_generated(p)['ok'])

    def test_allow_list_needs_a_why_and_base_images_are_left_to_h8(self):
        b = self.base_game()
        p = project(self.d / 'p')
        AR.record_base(p, b)
        (p / 'assets' / 'keep.png').write_bytes((b / 'assets/ui/coin.png').read_bytes())
        plate = png(p / 'assets' / 'ui' / 'plate9.png', 70)
        r = AR.check_generated(p)
        self.assertEqual([x['file'] for x in r['unrecorded']], ['assets/ui/plate9.png'])     # not keep.png (H8's)
        (p / 'docs/art/script-drawn-allow.json').write_text(json.dumps({'allow': [{'file': 'assets/ui/plate9.png'}]}))
        self.assertFalse(AR.check_generated(p)['ok'])
        AR.record_reason(p, 'allow', [str(plate)], 'plain nine-slice plate drawn by code')
        r = AR.check_generated(p)
        self.assertTrue(r['ok'])
        self.assertEqual(len(r['allowed']), 1)

    def test_english_game_only_warns_and_needs_the_original_recorded(self):
        b = self.base_game()
        p = project(self.d / 'p', 'localize')
        (p / 'assets' / 'orig.png').write_bytes((b / 'assets/ui/coin.png').read_bytes())
        pil_button(p / 'assets' / 'btn_play_en.png')
        self.assertEqual(AR.check_generated(p, 'localize')['state'], 'not_applicable')
        AR.record_base(p, b)
        r = AR.check_generated(p, 'localize')
        self.assertEqual((r['ok'], [x['file'] for x in r['unrecorded']]), (None, ['assets/btn_play_en.png']))
        self.assertIn('英化游戏只提示', r['message'])

    def test_finalize_source_records_its_own_conversion(self):
        b = self.base_game()
        p = project(self.d / 'p')
        AR.record_base(p, b)
        gen = png(p / 'assets' / 'ui' / 'hero.png', 80)
        AR.record_generated(p, [gen], 'codex image_gen', prompt='hero')
        old = p / 'assets' / 'ui' / 'coin.webp'
        old.write_bytes((b / 'assets/ui/coin.png').read_bytes())
        AR.record_reason(p, 'keep', ['assets/ui/coin.webp'], 'kept on purpose')
        before = AR.snapshot(p)

        def convert(ctx, names):
            png(gen, 81)                                         # shrunk
            old.rename(old.with_suffix('.png'))                  # WebP -> PNG, new bytes
            png(old.with_suffix('.png'), 82)
            return []
        with mock.patch.object(F, '_run_steps', side_effect=convert), \
                mock.patch.object(F, '_art_records_before', return_value=before):
            record = F.finalize_source(p, 'remake', steps=())
        self.assertEqual(record['art_records']['generated'], 1)
        self.assertEqual(record['art_records']['base'], 1)
        self.assertEqual(record['art_records']['keep'], 1)
        self.assertTrue(AR.check_generated(p)['ok'], AR.check_generated(p)['message'])
        r = AR.check_base(p)
        self.assertEqual([x['file'] for x in r['kept']], ['assets/ui/coin.png'])   # still known as base, still kept

    def test_carry_never_raises(self):
        p = self.scratch_project()
        (p / 'docs/art/generated.json').write_text('{broken')
        png(p / 'assets' / 'a.png', 1)
        out = AR.carry(p, {'assets/a.png': 'x'})        # unreadable record: nothing carried, nothing raised
        self.assertEqual(out['generated'], 0)
        with mock.patch.object(AR, 'snapshot', side_effect=OSError('disk')):
            self.assertIn('error', AR.carry(p, {'assets/a.png': 'x'}))


class ArtCheckRows(Tmp):
    def run_art_check(self, p, **patches):
        out = self.d / ('out%d' % len(list(self.d.glob('out*'))))
        with mock.patch.object(sys, 'argv', ['art_check.py', '--project', str(p), '--out', str(out)]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.ExitStack() as stack:
            for target, value in patches.items():
                stack.enter_context(mock.patch.object(art_check, target, value))
            code = art_check.main()
        return code, json.loads((out / 'art-check.json').read_text())

    def test_missing_capture_still_reports_h8_h10_and_3x_receipt_fails(self):
        p = project(self.d / 'p', engine=3)
        pil_button(p / 'assets' / 'btn.png')
        code, rep = self.run_art_check(p, run=mock.Mock(side_effect=AssertionError('no analysis')))
        self.assertEqual(code, 1)
        rows = {x['check']: x['status'] for x in rep['rows']}
        self.assertEqual((rows[art_check.H8_TITLE], rows[art_check.H10_TITLE]), ('需处理', '需处理'))
        rec = json.loads(R.receipt_path(p).read_text())
        self.assertEqual(rec['status'], 'fail')
        self.assertEqual(rec['base_generated']['generated_ok'], False)
        out = R.check(p, policy='new')
        self.assertEqual(out['level'], 'block')
        self.assertIn('没有底子记录', out['message'])
        # fixed: base recorded, picture recorded as generated -> the 3.x receipt is "not covered" again (W83)
        AR.record_none(p, 'scratch')
        AR.record_generated(p, [p / 'assets' / 'btn.png'], 'codex image_gen', prompt='PLAY button')
        self.run_art_check(p, run=mock.Mock(side_effect=AssertionError('no analysis')))
        self.assertEqual(json.loads(R.receipt_path(p).read_text())['status'], 'not_covered_3x')

    def test_missing_capture_keeps_a_24_receipt(self):
        p = project(self.d / 'p')
        pil_button(p / 'assets' / 'btn.png')
        R.write(p, 'pass', {'status': 'pass'})
        before = R.receipt_path(p).read_bytes()
        self.run_art_check(p, run=mock.Mock(side_effect=AssertionError('no analysis')))
        self.assertEqual(R.receipt_path(p).read_bytes(), before)

    def test_full_analysis_rows_make_the_receipt_fail(self):
        p = project(self.d / 'p')
        pil_button(p / 'assets' / 'btn.png')
        ready = {'ready': True, 'errors': [], 'dump_files': [], 'shots': [], 'records': [{'kind': 'gameplay'}],
                 'observed': [], 'listed': [], 'viewports': []}
        import audit_no_social_features
        with mock.patch.object(audit_no_social_features, 'audit', return_value={'passed': True}):
            code, rep = self.run_art_check(p, capture_inventory=mock.Mock(return_value=ready),
                                           run=mock.Mock(return_value=(0, '')))
        rows = {x['check']: x for x in rep['rows']}
        self.assertEqual(rows[art_check.H8_TITLE]['status'], '需处理')
        self.assertEqual(rows[art_check.H10_TITLE]['status'], '需处理')
        self.assertEqual(rep['base_generated']['not_generated'], 1)


class NumpyPython(unittest.TestCase):
    def test_no_reexec_when_numpy_is_here(self):
        with mock.patch('importlib.util.find_spec', return_value=object()):
            self.assertIsNone(art_check.numpy_python())

    def test_reexec_with_a_python_that_has_numpy(self):
        ran = mock.Mock(return_value=mock.Mock(returncode=0))
        with mock.patch('importlib.util.find_spec', return_value=None), mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(art_check.subprocess, 'run', ran), mock.patch('os.path.exists', return_value=True), \
                mock.patch('os.path.realpath', side_effect=lambda x: x):
            os.environ.pop('ART_CHECK_REEXEC', None)
            self.assertEqual(art_check.numpy_python(), '/usr/bin/python3')
            os.environ['ART_CHECK_REEXEC'] = '1'
            self.assertIsNone(art_check.numpy_python())
            os.environ.pop('ART_CHECK_REEXEC', None)
        none = mock.Mock(return_value=mock.Mock(returncode=1))
        with mock.patch('importlib.util.find_spec', return_value=None), mock.patch.object(art_check.subprocess, 'run', none):
            self.assertIsNone(art_check.numpy_python())


class HudDigitsOnPieces(unittest.TestCase):
    """W88 false positive: Meteor Blaster's block numbers (Canvas/gameBox/blockList/block/boxtext) in the top band."""

    def nodes(self, extra=()):
        def node(path, rect, comps):
            return {'path': path, 'name': path.rsplit('/', 1)[-1], 'rect': rect, 'screen': rect, 'opacity': 1,
                    'comps': comps}
        out = []
        for i in range(4):
            x = 0.2 * i
            out.append(node('Canvas/gameBox/blockList/block', [x, 0.05, 0.2, 0.078], {'sprite': {'frame': 'rock'}}))
            out.append(node('Canvas/gameBox/blockList/block/boxtext', [x + 0.08, 0.06, 0.036, 0.02],
                            {'label': {'string': str(i + 1), 'fontSize': 20, 'height': 20}}))
        out.append(node('Canvas/ui/Score', [0.4, 0.02, 0.2, 0.015], {'label': {'string': '120', 'fontSize': 20, 'height': 20}}))
        for i in range(3):
            out.append(node('Canvas/LiveSkillsHUD/Skill', [0.2 * i, 0.93, 0.1, 0.05], {'sprite': {'frame': 'skill'}}))
            out.append(node('Canvas/LiveSkillsHUD/Skill/Value', [0.2 * i, 0.95, 0.03, 0.015],
                            {'label': {'string': str(i), 'fontSize': 20, 'height': 20}}))
        return out + list(extra)

    def test_piece_numbers_skipped_real_hud_still_reported(self):
        import audit_page_richness as A
        problems = A.hud_digit_problems({'kind': 'gameplay'}, self.nodes(), [], None)
        paths = sorted({p.split('(')[1].split(')')[0] for p in problems})
        self.assertEqual(paths, ['Canvas/LiveSkillsHUD/Skill/Value', 'Canvas/ui/Score'])


class EnglishImagesList(Tmp):
    def test_base_assets_record_is_a_pre_english_list(self):
        import audit_new_english_images as E
        b = self.base_game()
        p = project(self.d / 'p', 'localize')
        AR.record_base(p, b)
        pre = E.load_pre(p / AR.BASE_FILE)
        self.assertIn(AR.sha((b / 'assets/ui/coin.png').read_bytes()), pre)
        self.assertIn(AR.sha(self.tex), pre)


if __name__ == '__main__':
    unittest.main()
