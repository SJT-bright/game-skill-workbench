#!/usr/bin/env python3
"""生成时预防 R4R2 (补查3 第 1 组补充; 弹球传奇 11-05: 54 runtime whole words, 48 missing): audit_new_english_images
--make-list also lists the whole-word pictures scripts fetch at run time, so the missing ones are drawn in round 1.
  1 literal   caption('equipped') and no txt_equipped.png -> missing txt_equipped; 'EnglishUI/txt_shop' present -> wired
  2 label     caption(this.stateLabel) + this.stateLabel.string = "EQUIP" -> txt_equip; ballName.string = list['name']
              -> every short config `name` (English -> txt_<slug>, Chinese -> untranslated_names)
  3 make_list make_list() carries it as chinese_scan.runtime_words (old code: no such key)
Run: python3 test_runtime_word_images.py
"""
import json
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_new_english_images as A  # noqa: E402


def png(w=8, h=8):
    return b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\rIHDR' + struct.pack('>II', w, h) + b'\x08\x06\x00\x00\x00' + b'\x00' * 8


SHOP = """var EnglishValue = require('EnglishValue');
cc.Class({ onLoad() {
    EnglishValue.caption(this.isUsedOwnLabel);
    EnglishValue.caption(this.ballName);
    var tip = EnglishValue.caption('equipped');
    cc.loader.loadRes('EnglishUI/txt_shop', cc.SpriteFrame, function () {});
  },
  updateItem(list) {
    this.ballName.string = list['name'];
    if (list.used) this.isUsedOwnLabel.string = "EQUIP";
  }
});
"""


def project(tmp):
    root = Path(tmp) / 'BallMaster'
    (root / 'assets/scripts').mkdir(parents=True)
    (root / 'assets/scripts/ShopBallItem.js').write_text(SHOP, encoding='utf-8')
    (root / 'assets/resources/EnglishUI').mkdir(parents=True)
    (root / 'assets/resources/EnglishUI/txt_shop.png').write_bytes(png())
    (root / 'assets/resources/EnglishUI/txt_fire_ball.png').write_bytes(png())
    (root / 'assets/resources/config').mkdir(parents=True)
    (root / 'assets/resources/config/balls.json').write_text(json.dumps(
        {'balls': [{'id': 1, 'name': 'Fire Ball'}, {'id': 2, 'name': 'Ice Ball'}, {'id': 3, 'name': '雷电球'}]}),
        encoding='utf-8')
    return root


class RuntimeWordImages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_literal_label_and_config_words(self):
        r = A.runtime_word_images(project(self.tmp))
        self.assertEqual(sorted(m['key'] for m in r['missing']), ['txt_equip', 'txt_equipped', 'txt_ice_ball'])
        self.assertEqual(r['wired'], 2)                                  # txt_shop, txt_fire_ball
        self.assertEqual([u['text'] for u in r['untranslated_names']], ['雷电球'])

    def test_make_list_carries_runtime_words(self):
        root = project(self.tmp)
        old_scan, old_flat = A.scan_chinese, A.flat_panels
        A.scan_chinese = lambda project, ocr='auto': {'replace': [], 'manual_review': [], 'regenerate': []}
        A.flat_panels = lambda project: []
        try:
            doc = A.make_list(root)
        finally:
            A.scan_chinese, A.flat_panels = old_scan, old_flat
        words = doc['chinese_scan'].get('runtime_words')
        self.assertIsNotNone(words, 'OLD WAY BUG: --make-list only looked at prefabs and scenes')
        self.assertIn('txt_equipped.png', [m['file'] for m in words['missing']])


if __name__ == '__main__':
    unittest.main()
