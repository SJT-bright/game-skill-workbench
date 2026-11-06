#!/usr/bin/env python3
"""生成时预防 R4R1 (Saul 2026-11-05 09:4x: 「发现问题直接处理啊，直接修改图片」): fix_game_name.py fixes what
game_name_scan finds instead of only blocking.

Sample = the shape of 弹球传奇 BallMaster-English (begun 2026-11-05, glossary "Ball Master"): a 2.4 prefab with a
Label "BALL MASTER" next to PLAY, copy-table cells "Ball Master" and "Welcome to Ball Master! Tap to play.", and a logo
picture whose chinese-audit OCR row reads BALL MASTER.
  1 texts       Label emptied and switched off (node kept, PLAY untouched), cell emptied, sentence -> "the game",
                backups + record written; picture list has size, page, a clean prompt and no title references
  2 images      a same-size picture with the same name replaces the logo (.meta kept) -> scan clean, exit 0;
                a wrong-size one is left with the reason, exit 1
  3 dry run     reports, writes nothing
  4 legacy      not touched
  5 neutral     sentence rewrites (capitals, sentence start, "the <name>", possessive)
Run: python3 test_fix_game_name.py   (old code: no fix_game_name.py -> import error)
"""
import contextlib
import hashlib
import io
import json
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fix_game_name as F  # noqa: E402
from tiktok_finalize_steps import game_name_scan as G  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402


def png(w, h, seed=0):
    raw = b''.join(b'\x00' + bytes([(seed + x) % 256, 80, 120, 255]) * w for x in range(h))
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


PREFAB = [
    {"__type__": "cc.Prefab", "_name": "", "data": {"__id__": 1}},
    {"__type__": "cc.Node", "_name": "Home", "_children": [{"__id__": 2}, {"__id__": 4}, {"__id__": 6}],
     "_components": []},
    {"__type__": "cc.Node", "_name": "TitleText", "_components": [{"__id__": 3}],
     "_contentSize": {"__type__": "cc.Size", "width": 520, "height": 90}},
    {"__type__": "cc.Label", "_name": "", "node": {"__id__": 2}, "_enabled": True,
     "_N$string": "BALL MASTER", "_string": "BALL MASTER", "_fontSize": 64},
    {"__type__": "cc.Node", "_name": "PlayText", "_components": [{"__id__": 5}]},
    {"__type__": "cc.Label", "_name": "", "node": {"__id__": 4}, "_enabled": True,
     "_N$string": "PLAY", "_string": "PLAY"},
    {"__type__": "cc.Node", "_name": "Logo", "_components": [{"__id__": 7}]},
    {"__type__": "cc.Sprite", "node": {"__id__": 6}, "_spriteFrame": {"__uuid__": "logo-frame-uuid"}},
    {"__type__": "cc.Sprite", "node": {"__id__": 6}, "_spriteFrame": {"__uuid__": "hero-frame-uuid"}},
]


def project(tmp, created='2026-11-05T03:00:00-0800'):
    root = Path(tmp) / 'BallMaster-English'
    eng = root / 'assets' / 'resources' / 'english'
    eng.mkdir(parents=True)
    (root / 'assets' / 'prefab').mkdir(parents=True)
    (root / 'assets/prefab/Home.prefab').write_text(json.dumps(PREFAB, indent=2) + '\n', encoding='utf-8')
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    for name, (w, h), frame, seed in (('Ball_Logo.png', (200, 80), 'logo', 1), ('hero.png', (128, 128), 'hero', 2),
                                      ('title_bg.png', (300, 120), 'tbg', 3)):
        (eng / name).write_bytes(png(w, h, seed))
        (eng / (name + '.meta')).write_text(json.dumps({'uuid': frame + '-uuid', 'subMetas': {
            name[:-4]: {'uuid': frame + '-frame-uuid'}}}))
    P.write_marker(root, 'localize', '2.0', reason='init')
    m = json.loads((root / P.MARKER).read_text(encoding='utf-8'))
    m['created'] = created
    (root / P.MARKER).write_text(json.dumps(m))
    (root / 'docs' / 'copy').mkdir(parents=True)
    (root / 'docs/copy/glossary.json').write_text(json.dumps({'game_name': ['Ball Master', '弹球传奇'],
                                                             'hero': 'a round blue ball hero with a smile'}))
    (root / 'docs/copy/copy-table.csv').write_text(
        'id,zh,en\ntitle,弹球传奇,Ball Master\nwelcome,欢迎,Welcome to Ball Master! Tap to play.\nplay,开始,PLAY\n',
        encoding='utf-8')
    audit = root / 'docs' / 'english' / 'chinese-audit'
    audit.mkdir(parents=True)
    logo = eng / 'Ball_Logo.png'
    (audit / 'audit.json').write_text(json.dumps({'items': [
        {'kind': 'image', 'file': 'assets/resources/english/Ball_Logo.png',
         'file_sha256': hashlib.sha256(logo.read_bytes()).hexdigest(), 'ocr_text': ['BALL', 'MASTER']}]}))
    return root


def cli(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = F.main([str(a) for a in args])
    return code, json.loads(buf.getvalue())


class FixGameNameTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_texts_fixed_and_picture_list(self):
        root = project(self.tmp)
        self.assertEqual(len(G.scan(root)['hits']), 5)   # _N$string and _string both read
        code, out = cli('--project', root)
        self.assertEqual(code, 1)                      # the logo picture is still there
        pre = json.loads((root / 'assets/prefab/Home.prefab').read_text(encoding='utf-8'))
        self.assertEqual((pre[3]['_string'], pre[3]['_N$string'], pre[3]['_enabled']), ('', '', False))
        self.assertEqual(pre[2]['_contentSize']['width'], 520)          # node and layout untouched
        self.assertEqual((pre[5]['_string'], pre[5]['_enabled']), ('PLAY', True))
        table = (root / 'docs/copy/copy-table.csv').read_text(encoding='utf-8')
        self.assertIn('title,弹球传奇,\n', table)
        self.assertIn('Welcome to the game! Tap to play.', table)
        self.assertIn('play,开始,PLAY', table)
        bk = root / F.FIX_DIR / 'backup'
        self.assertIn('BALL MASTER', (bk / 'assets/prefab/Home.prefab.orig').read_text(encoding='utf-8'))
        self.assertIn('Ball Master', (bk / 'docs/copy/copy-table.csv.orig').read_text(encoding='utf-8'))
        rec = json.loads((root / F.FIX_DIR / 'record.json').read_text(encoding='utf-8'))
        self.assertEqual(len(rec['runs'][0]['changes']), 3)
        self.assertEqual([h['file'] for h in out['remaining_hits']], ['assets/resources/english/Ball_Logo.png'])
        lst = json.loads((root / F.IMAGE_LIST).read_text(encoding='utf-8'))
        it, = lst['images']
        self.assertEqual((it['path'], it['width'], it['height'], it['alpha']),
                         ('assets/resources/english/Ball_Logo.png', 200, 80, True))
        self.assertEqual(it['used_on'], ['assets/prefab/Home.prefab'])
        self.assertNotIn('ball master', it['prompt'].lower())
        self.assertIn('round blue ball hero', it['prompt'])
        self.assertIn('no text', it['prompt'])
        self.assertEqual(it['prompt_check'], 'clean')
        self.assertIn('assets/resources/english/hero.png', it['references'])
        self.assertFalse([r for r in it['references'] if 'title' in r or 'Logo' in r])
        self.assertIn('fix_game_name.py', G.message(out['remaining_hits']))

    def test_apply_images(self):
        root = project(self.tmp)
        cli('--project', root)
        meta = (root / 'assets/resources/english/Ball_Logo.png.meta').read_text()
        bad = Path(self.tmp) / 'bad'
        bad.mkdir()
        (bad / 'Ball_Logo.png').write_bytes(png(210, 80, 9))
        code, out = cli('--project', root, '--apply-images', bad)
        self.assertEqual(code, 1)
        self.assertIn('size 210x80, needs 200x80', out['skipped'][0]['why'])
        good = Path(self.tmp) / 'new'
        good.mkdir()
        (good / 'Ball_Logo.png').write_bytes(png(200, 80, 50))
        code, out = cli('--project', root, '--apply-images', good)
        self.assertEqual(code, 0, out)
        self.assertTrue(out['clean'])
        self.assertEqual((root / 'assets/resources/english/Ball_Logo.png').read_bytes(), png(200, 80, 50))
        self.assertEqual((root / 'assets/resources/english/Ball_Logo.png.meta').read_text(), meta)
        self.assertEqual((root / F.FIX_DIR / 'backup/assets/resources/english/Ball_Logo.png.orig').read_bytes(),
                         png(200, 80, 1))
        self.assertEqual(G.scan(root)['hits'], [])

    def test_dry_run_writes_nothing(self):
        root = project(self.tmp)
        before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
        code, out = cli('--project', root, '--dry-run')
        self.assertEqual(code, 1)
        self.assertEqual(len(out['text_changes']), 3)
        self.assertEqual(len(out['image_list']['images']), 1)
        after = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_legacy_not_touched(self):
        root = project(self.tmp)
        real, F._policy = F._policy, lambda r: 'legacy'
        self.addCleanup(setattr, F, '_policy', real)
        before = (root / 'assets/prefab/Home.prefab').read_bytes()
        code, out = cli('--project', root)
        self.assertEqual(code, 0)
        self.assertIn('legacy', out['skipped'])
        self.assertEqual((root / 'assets/prefab/Home.prefab').read_bytes(), before)

    def test_neutral_rewrites(self):
        pats = [F.name_pattern('Ball Master')]
        self.assertEqual(F.neutral('Ball Master is fun', pats), 'The game is fun')
        self.assertEqual(F.neutral('WELCOME TO BALL MASTER', pats), 'WELCOME TO THE GAME')
        self.assertEqual(F.neutral('Thanks for playing the Ball Master!', pats), 'Thanks for playing the game!')
        self.assertEqual(F.neutral("Ball Master's best score", pats), "The game's best score")
        self.assertTrue(F.whole_name('BALL MASTER 2!', pats))
        self.assertFalse(F.whole_name('Play Ball Master now', pats))
        self.assertTrue(F.whole_name('Dino Merge Evolution', [F.name_pattern('Dino Merge')]))   # DinoMerge copy table
        self.assertFalse(F.whole_name('Play Ball Master', pats))


if __name__ == '__main__':
    unittest.main()
