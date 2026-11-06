#!/usr/bin/env python3
"""11.17 R4Q7 item 5a (补查3 第 5 节, SLS35 / SLS04-1): Creator would not start, its layout.json / window.json said
"Unexpected end of JSON input". check_machine.py now has the row「Cocos 编辑器配置能解析」: report only, nothing changed.
Run: python3 -B test_r4q7_editor_config.py
"""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import check_machine  # noqa: E402


class EditorConfig(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.home = Path(self.td.name)
        (self.home / '.CocosCreator' / 'editor').mkdir(parents=True)

    def tearDown(self):
        self.td.cleanup()

    def test_cut_short_layout_is_reported_and_left_alone(self):
        bad = self.home / '.CocosCreator' / 'editor' / 'layout.json'
        bad.write_text('{"version": 1, "panels": [', encoding='utf-8')
        (self.home / '.CocosCreator' / 'editor' / 'window.json').write_text('{}', encoding='utf-8')
        r = check_machine.editor_config_row(home=self.home)
        self.assertFalse(r['ok'], r)
        self.assertFalse(r['required'])
        self.assertIn('layout.json', r['detail'])
        self.assertNotIn('window.json', r['detail'])
        self.assertEqual(bad.read_text(encoding='utf-8'), '{"version": 1, "panels": [')   # only reported

    def test_good_or_missing_configs_pass(self):
        self.assertTrue(check_machine.editor_config_row(home=self.home)['ok'])
        (self.home / '.CocosCreator' / 'editor' / 'window.json').write_text('{"a": 1}', encoding='utf-8')
        self.assertTrue(check_machine.editor_config_row(home=self.home)['ok'])

    def test_collect_has_the_row(self):
        names = [r['name'] for r in check_machine.collect(quick=True)]
        self.assertIn('Cocos 编辑器配置能解析', names)


if __name__ == '__main__':
    unittest.main()
