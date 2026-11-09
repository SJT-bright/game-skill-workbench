#!/usr/bin/env python3
"""R4Q3 (补查3 第 3 组, 火箭三消 / 弹球传奇 11-05): an English game that keeps its original art is not blocked by the
大块深色与纯色底 row for pictures that are byte-identical to the Chinese original; new pictures still are; remake blocks
both. Two identical dark-blue plain pictures: one with the SHA the raw-input record holds, one re-saved (new SHA).

Run: PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B test_r4q3_keep_original_style.py   (needs Pillow; seconds)
"""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

import art_check  # noqa: E402
import art_receipt  # noqa: E402
from test_art_receipt_fixtures import write_fixture
import feature_policy  # noqa: E402
import raw_inputs  # noqa: E402

FAILED_SHOTS = {'checked': 2, 'failed': 1, 'over': [{'path': '/x/home-ui-1.png', 'problems': ['large dark area']}]}
NAVY = (22, 34, 70)


@unittest.skipIf(Image is None, 'needs Pillow')
class KeepOriginalStyle(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='r4q3-'))
        self.game = self.root / 'game'
        self.project = self.game / 'English'
        ui = self.project / 'assets' / 'ui'
        ui.mkdir(parents=True)
        (self.project / 'docs').mkdir()
        # the Chinese original: one dark navy plain background
        orig = self.root / 'src' / 'assets' / 'ui'
        orig.mkdir(parents=True)
        Image.new('RGB', (720, 1280), NAVY).save(str(orig / 'bg_home.png'))
        raw_inputs.keep(self.root / 'src', self.game)              # read-only _原始输入/ + its hashes
        shutil.copy2(orig / 'bg_home.png', ui / 'bg_home.png')     # kept as it is: same SHA
        self.board('localize')

    def tearDown(self):
        raw_inputs.unlock_for_test_cleanup(self.root)
        shutil.rmtree(self.root, ignore_errors=True)

    def board(self, name):
        (self.project / 'docs' / 'board.txt').write_text(name + '\n', encoding='utf-8')

    def add_new_navy(self):
        # same picture, re-saved: identical pixels, different bytes -> a NEW picture
        Image.new('RGB', (720, 1280), NAVY).save(str(self.project / 'assets' / 'ui' / 'popup_new.png'), compress_level=1)

    def row(self, board):
        r = art_check.dark_area_row(self.project, board, 1, FAILED_SHOTS)
        return r[0] if isinstance(r, tuple) else r

    def test_policy_row(self):
        self.assertEqual(feature_policy.applies('dark_flat_original', 'localize', self.project), 'not_applicable')
        self.assertEqual(feature_policy.applies('dark_flat_original', 'remake', self.project), 'block')
        (self.project / 'docs' / 'art-style.txt').write_text('remake\n', encoding='utf-8')
        self.assertEqual(feature_policy.applies('dark_flat_original', 'localize', self.project), 'block')

    def test_english_original_picture_not_applicable(self):
        row = self.row('localize')
        self.assertEqual(row['status'], '不适用', row)
        self.assertIn('原图保留', row['detail'])

    def test_english_new_picture_blocks(self):
        self.add_new_navy()
        row = self.row('localize')
        self.assertEqual(row['status'], '需处理', row)
        self.assertIn('popup_new.png', row['detail'])
        self.assertNotIn('bg_home.png', row['detail'].split('新做的图', 1)[-1])

    def test_remake_blocks_both(self):
        self.board('remake')
        self.add_new_navy()
        self.assertEqual(self.row('remake')['status'], '需处理')
        import original_style
        v = original_style.verdict(self.project, 'remake')
        self.assertEqual(v['state'], 'remake')

    def test_base_assets_record_also_counts(self):
        # a game started before R4D: only docs/art/base-assets.json (art_records.py base) knows the original
        raw_inputs.unlock_for_test_cleanup(self.game / raw_inputs.RAW_DIR)
        shutil.rmtree(self.game / raw_inputs.RAW_DIR)
        import original_style
        self.assertEqual(original_style.verdict(self.project, 'localize')['state'], 'no_original')
        sha = original_style._sha((self.project / 'assets/ui/bg_home.png').read_bytes())
        (self.project / 'docs' / 'art').mkdir(exist_ok=True)
        (self.project / 'docs/art/base-assets.json').write_text(json.dumps(
            {'kind': 'base-assets', 'images': {'assets/ui/bg_home.png': sha}}), encoding='utf-8')
        self.assertEqual(self.row('localize')['status'], '不适用')

    def receipt_for(self, rows, style):
        report = {'status': 'fail' if any(r['status'] == '需处理' for r in rows) else 'pass', 'rows': rows,
                  'passed': not any(r['status'] == '需处理' for r in rows), 'board': 'localize',
                  'original_style': style}
        return write_fixture(self.project, 'pass' if report['passed'] else 'fail', report)

    def test_receipt_reads_keep_record(self):
        # no original record at all, the only failing row is the dark one: with Saul's keep record the writer warns
        raw_inputs.unlock_for_test_cleanup(self.game / raw_inputs.RAW_DIR)
        shutil.rmtree(self.game / raw_inputs.RAW_DIR)
        row, style = art_check.dark_area_row(self.project, 'localize', 1, FAILED_SHOTS)
        self.assertEqual(row['status'], '需处理')
        self.receipt_for([row], style)
        import unittest.mock as m
        with m.patch.object(art_receipt, '_value_receipt_current', return_value=True):
            before = art_receipt.check_history(self.project, 'localize')
            self.assertEqual(before['level'], 'block')
            (self.project / 'docs' / 'art').mkdir(exist_ok=True)
            (self.project / 'docs/art/keep_original_style.json').write_text(json.dumps(
                {'schema': 'keep-original-style.v1', 'decided_by': 'Saul', 'date': '2026-11-05',
                 'why': '保留原画风'}, ensure_ascii=False), encoding='utf-8')
            after = art_receipt.check_history(self.project, 'localize')
        self.assertEqual(after['level'], 'warn', after['message'])
        self.assertIn('Saul', after['message'])

    def test_receipt_pass_names_kept_pictures(self):
        (self.project / 'docs' / 'art').mkdir(exist_ok=True)
        (self.project / 'docs/art/keep_original_style.json').write_text(json.dumps(
            {'decided_by': 'Saul', 'date': '2026-11-05'}), encoding='utf-8')
        row, style = art_check.dark_area_row(self.project, 'localize', 1, FAILED_SHOTS)
        rec = self.receipt_for([row], style)
        self.assertEqual(rec['status'], 'pass')
        self.assertEqual(rec['keep_original_style']['decided_by'], 'Saul')
        import unittest.mock as m
        with m.patch.object(art_receipt, '_value_receipt_current', return_value=True):
            got = art_receipt.check_history(self.project, 'localize')
        self.assertEqual(got['level'], 'ok', got['message'])
        self.assertIn('原图保留 1 张', got['message'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
