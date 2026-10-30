#!/usr/bin/env python3
"""v7.5 logic_check.py additions (Germ2048 item 10): L-DAILY-DATE fail, L-SAVE-PARSE hint, --stage final.
Run: python3 -B test_logic_check_v75.py"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import logic_check  # noqa: E402


def project(root, files):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    return root


def rules(root):
    found, _ = logic_check.scan(root)
    return {(f['rule'], f['severity']) for f in found}


class LogicV75(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_daily_getdate_only_fails(self):
        p = project(self.root / 'a', {'assets/Daily.ts': 'if (data.lastplayday !== new Date().getDate()) { giveDailyReward(); }\n'})
        self.assertIn(('L-DAILY-DATE', 'fail'), rules(p))

    def test_daily_full_date_passes(self):
        p = project(self.root / 'b', {'assets/Daily.ts': 'const d = new Date(); const key = d.getFullYear() + "-" + d.getMonth() + '
                                                          '"-" + d.getDate(); if (data.dailyKey !== key) giveDailyReward();\n'})
        self.assertNotIn(('L-DAILY-DATE', 'fail'), rules(p))

    def test_daily_with_date_key_helper_passes(self):
        p = project(self.root / 'c', {'assets/Daily.ts': 'const today = Store.todayKey(); if (old.lastplayday === new Date().getDate()) '
                                                          '{ migrate(today); }\n'})
        self.assertNotIn(('L-DAILY-DATE', 'fail'), rules(p))

    def test_save_parse_without_try_is_hint(self):
        p = project(self.root / 'd', {'assets/Save.ts': 'let raw = cc.sys.localStorage.getItem("save"); this.data = JSON.parse(raw);\n'})
        got = rules(p)
        self.assertIn(('L-SAVE-PARSE', 'hint'), got)
        self.assertNotIn(('L-SAVE-PARSE', 'fail'), got)

    def test_save_parse_inside_try_and_deep_copy_not_listed(self):
        p = project(self.root / 'e', {'assets/Save.ts': 'try { this.data = JSON.parse(cc.sys.localStorage.getItem("save")); } catch (e) '
                                                         '{ this.data = {}; }\nconst c = JSON.parse(JSON.stringify(this.data));\n'})
        self.assertFalse({r for r in rules(p) if r[0] == 'L-SAVE-PARSE'})

    def test_final_stage_missing_regressions_fail_in_review(self):
        p = project(self.root / 'f', {'assets/Game.ts': 'export const x = 1;\n'})
        out = self.root / 'out'
        base = [sys.executable, '-B', str(HERE / 'logic_check.py'), '--project', str(p), '--mode', 'review']
        r = subprocess.run(base + ['--out', str(out / 'code.json')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads((out / 'code.json').read_text())['status'], 'review')
        r = subprocess.run(base + ['--stage', 'final', '--out', str(out / 'final.json')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        rep = json.loads((out / 'final.json').read_text())
        self.assertEqual(rep['status'], 'fail')
        self.assertIn('R01', rep['final_stage_regression_failures'])
        self.assertFalse((p / 'docs').exists(), 'with --out nothing is written into the project')


if __name__ == '__main__':
    unittest.main()
