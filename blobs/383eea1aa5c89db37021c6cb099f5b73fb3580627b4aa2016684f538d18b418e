#!/usr/bin/env python3
"""v7.8 (Saul 10-30): pictures already in a game when v7.8 is installed may be registered once as 「v7.8 前已有」.

Five games in progress (企鹅雪道, 丛林荡藤, 热气球, Meteor Blaster, Holly) had 45-305 shipped pictures without a generated
record. A game marked new on or before the v7.8 release day may run `art_records.py pre-v78` once; the pictures then count
as recorded but every check lists them. Base-identical files stay H8 findings; pictures added or edited afterwards need a
real record; a game marked new after v7.8, a game without a marker and a second run are refused.

    PYTHONDONTWRITEBYTECODE=1 python3 -B test_art_pre_v78.py
"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import art_records as AR  # noqa: E402


def png(path, seed):
    """A tiny but valid 8x8 PNG whose bytes differ per seed (stdlib only)."""
    import struct
    import zlib
    rows = b''.join(b'\x00' + bytes(((x * 31 + y * 7 + seed * 13) % 256 for x in range(8 * 3))) for y in range(8))
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 8, 8, 8, 2, 0, 0, 0)) + \
        chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def marker(root, created):
    (root / '.tiktok-kit').mkdir(parents=True, exist_ok=True)
    (root / '.tiktok-kit' / 'policy.json').write_text(json.dumps(
        {'policy': 'new', 'kit_version': '2.0', 'board': 'remake', 'created': created, 'by': 'init'}))


class PreV78(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix='art-pre-v78-'))
        self.base = self.d / 'base'
        png(self.base / 'assets' / 'resources' / 'old_logo.png', 99)
        self.p = self.d / 'game'
        (self.p / 'assets').mkdir(parents=True)
        (self.p / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
        png(self.p / 'assets' / 'resources' / 'ui' / 'btn_play.png', 1)        # resources: ships
        png(self.p / 'assets' / 'resources' / 'ui' / 'coin.png', 2)
        shutil.copy(self.base / 'assets' / 'resources' / 'old_logo.png', self.p / 'assets' / 'resources' / 'logo.png')
        AR.record_base(self.p, self.base)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def generated(self):
        return AR.check(self.p, 'remake')['generated']

    def test_registers_once_and_every_check_lists_it(self):
        marker(self.p, '2026-10-29T21:49:48-0700')
        before = self.generated()
        self.assertFalse(before['ok'])
        self.assertEqual(sorted(r['file'] for r in before['unrecorded']),
                         ['assets/resources/ui/btn_play.png', 'assets/resources/ui/coin.png'])
        added = AR.record_pre_v78(self.p, '装 v7.8 时工程里已有的图')
        self.assertEqual(sorted(x['file'] for x in added), ['assets/resources/ui/btn_play.png', 'assets/resources/ui/coin.png'])
        after = self.generated()
        self.assertTrue(after['ok'])
        self.assertEqual(after['pre_v78'], 2)
        self.assertIn('v7.8 前已有', after['message'])
        self.assertEqual(AR.summary(AR.check(self.p, 'remake'))['pre_v78'], 2)
        with self.assertRaisesRegex(ValueError, '只能登记一次'):
            AR.record_pre_v78(self.p, 'again')

    def test_base_identical_files_stay_an_h8_finding(self):
        marker(self.p, '2026-10-30T00:22:17-0700')
        added = AR.record_pre_v78(self.p, 'existing art')
        self.assertNotIn('assets/resources/logo.png', [x['file'] for x in added])
        base = AR.check(self.p, 'remake')['base']
        self.assertFalse(base['ok'])
        self.assertIn('assets/resources/logo.png', json.dumps(base, ensure_ascii=False))

    def test_pictures_added_or_edited_later_need_a_real_record(self):
        marker(self.p, '2026-10-30T00:22:17-0700')
        AR.record_pre_v78(self.p, 'existing art')
        png(self.p / 'assets' / 'resources' / 'ui' / 'new_digit.png', 3)            # drawn after v7.8
        png(self.p / 'assets' / 'resources' / 'ui' / 'coin.png', 4)                 # edited after registering
        g = self.generated()
        self.assertFalse(g['ok'])
        self.assertEqual([r['file'] for r in g['unrecorded']], ['assets/resources/ui/new_digit.png'])
        self.assertEqual([r['file'] for r in g['edited']], ['assets/resources/ui/coin.png'])
        AR.record_derived(self.p, [self.p / 'assets' / 'resources' / 'ui' / 'coin.png'])
        AR.record_generated(self.p, [self.p / 'assets' / 'resources' / 'ui' / 'new_digit.png'], 'codex image_gen',
                            prompt='gold digit 7, chunky cartoon numeral')
        g = self.generated()
        self.assertTrue(g['ok'])
        self.assertEqual(g['pre_v78'], 2)                    # btn_play + coin (its derive chain ends at pre-v7.8)

    def test_game_marked_after_v78_or_without_marker_is_refused(self):
        with self.assertRaisesRegex(ValueError, '新游戏标记'):
            AR.record_pre_v78(self.p, 'no marker')
        marker(self.p, '2026-11-05T10:00:00-0800')
        with self.assertRaisesRegex(ValueError, '晚于 v7.8'):
            AR.record_pre_v78(self.p, 'too late')
        self.assertFalse((self.p / AR.GENERATED_FILE).exists() and
                         any(x.get('pre_v78') for x in json.loads((self.p / AR.GENERATED_FILE).read_text())['images']))

    def test_cli(self):
        marker(self.p, '2026-10-29T21:49:48-0700')
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(AR.main(['pre-v78', '--project', str(self.p), '--why', 'existing art']), 0)
            self.assertEqual(AR.main(['pre-v78', '--project', str(self.p), '--why', 'again']), 1)
        self.assertIn('只能登记一次', err.getvalue())


if __name__ == '__main__':
    unittest.main()
