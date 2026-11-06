#!/usr/bin/env python3
"""R4I1（Round4 #4，普查 checker_crash 28/37、checker_false_block 62/98）：检查脚本自己的三条。
1. --help 不崩：preview_touch_fakedom.cjs 把 --help 当文件打开、remake-art/check_card_layout.py 把 --help 当 JSON 读。
2. 报告开头写引擎版本和实际检查项数：audit_copy_quality.py、audit_image_clarity.py 在空 Cocos 3.8.8 工程上
   输出 engine、checked=0、status=not_run（退出 2）。
3. 检查默认只读：跑完以后工程文件夹一字不差。
发版自检 C10（release-selftest/drivers/checker_selfcheck.py）对全部入口脚本做同样的事；这里只钉住这次修的四个。"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE.parent.parent / 'remake-art' / 'scripts'


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)


def digest(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob('*')):
        h.update(p.relative_to(root).as_posix().encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


class Help(unittest.TestCase):
    def test_help_prints_usage(self):
        cases = [[sys.executable, str(ART / 'check_card_layout.py'), '--help']]
        if shutil.which('node'):
            cases.append(['node', str(HERE / 'preview_touch_fakedom.cjs'), '--help'])
        with tempfile.TemporaryDirectory() as cwd:
            for cmd in cases:
                p = run(cmd, cwd)
                text = p.stdout + p.stderr
                self.assertEqual(p.returncode, 0, (cmd[1], text[-300:]))
                self.assertIn('usage', text.lower(), cmd[1])
                self.assertNotIn('Traceback', text)
                self.assertNotIn('ENOENT', text)


class ZeroItems(unittest.TestCase):
    def test_empty_3x_project_is_not_run_with_engine_and_untouched(self):
        with tempfile.TemporaryDirectory() as t:
            proj = Path(t, 'Empty3x')
            (proj / 'assets').mkdir(parents=True)
            (proj / 'package.json').write_text('{"creator": {"version": "3.8.8"}}\n', encoding='utf-8')
            before = digest(proj)
            for name in ('audit_copy_quality.py', 'audit_image_clarity.py'):
                p = run([sys.executable, '-B', str(HERE / name), '--project', str(proj)], t)
                data = json.loads(p.stdout)
                self.assertEqual(p.returncode, 2, (name, p.stdout[-300:], p.stderr[-300:]))
                self.assertEqual(data.get('status'), 'not_run', name)
                self.assertEqual(data.get('checked'), 0, name)
                self.assertEqual((data.get('engine') or {}).get('version'), '3.8.8', name)
                self.assertEqual(list(data)[:2], ['engine', 'checked'], name)     # the head of the report
            self.assertEqual(digest(proj), before)


if __name__ == '__main__':
    unittest.main()
