#!/usr/bin/env python3
"""11.17 R4Q7 item 4 (奔跑吧巨人 rollout 03-50-09 :4180): source 8 + export 7 passed chinese_audit check.
homePanel.prefab and EnglishPlatform.ts were edited for build 8 after export 7 was built; a fresh scan of source 8 with
export 7 gave `passed`. Now check reports export_not_this_source when assets/ files are newer than the export.
Run: python3 -B test_r4q7_export_not_this_source.py
"""
import os
import shutil
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import test_chinese_audit as T  # noqa: E402


class ExportNotThisSource(T.Base):
    def build(self):
        img = T.pattern(40, 20, 7)
        p = self.proj / 'assets' / 'res' / 'btn.png'
        img.save(str(p))
        self.meta(p, T.UUID_BTN)
        (self.proj / 'assets' / 'res' / 'homePanel.prefab').write_text('[{"__type__": "cc.Prefab", "_name": "home"}]',
                                                                        encoding='utf-8')
        self.export = self.root / 'web-mobile'
        (self.export / 'res').mkdir(parents=True)
        shutil.copy(str(p), str(self.export / 'res' / 'btn.png'))
        (self.export / 'main.js').write_text('// build 7', encoding='utf-8')
        old = time.time() - 600
        for f in self.export.rglob('*'):
            os.utime(str(f), (old, old))
        for f in (self.proj / 'assets').rglob('*'):
            os.utime(str(f), (old - 60, old - 60))

    def test_same_version_passes(self):
        self.build()
        self.scan('--export', self.export)
        code, result, text = self.check('--export', self.export)
        self.assertNotIn('export_not_this_source', self.codes(result))
        self.assertEqual(code, 0, text)

    def test_source_edited_after_export_blocks(self):
        self.build()
        prefab = self.proj / 'assets' / 'res' / 'homePanel.prefab'
        prefab.write_text('[{"__type__": "cc.Prefab", "_name": "home v8"}]', encoding='utf-8')   # build 8 edit
        self.scan('--export', self.export)                    # rescan source 8 + export 7, as the session did
        code, result, text = self.check('--export', self.export)
        self.assertEqual(code, 1, text)
        rows = [p for p in result['problems'] if p['code'] == 'export_not_this_source']
        self.assertEqual(len(rows), 1, result['problems'])
        self.assertIn('assets/res/homePanel.prefab', rows[0]['files'])
        self.assertIn('导出不是这版源码', rows[0]['message'])


if __name__ == '__main__':
    unittest.main()
