#!/usr/bin/env python3
"""which_package.py (音乐消消乐复盘 2026-11-05): a renamed copy is found by its bytes, two folders of one game are
reported as two lines, another game is not listed.  python3 test_which_package.py"""
import io
import json
import shutil
import sys
import tempfile
import unittest
import uuid
import zipfile
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import which_package as W  # noqa: E402


def source_zip(path, uuids, extra=''):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('Game/project.json', json.dumps({'engine': 'cocos-creator-js', 'version': '2.4.15'}))
        z.writestr('Game/package.json', '{}')
        for i, u in enumerate(uuids):
            name = 'Game/assets/scene/home.fire.meta' if i == 0 else 'Game/assets/img/p%d.png.meta' % i
            z.writestr(name, json.dumps({'ver': '1.0.0', 'uuid': u}))
        z.writestr('Game/assets/scripts/Main.js', 'cc.log(1);' + extra)


class WhichPackage(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.game = [str(uuid.UUID(int=1000 + i)) for i in range(40)]
        self.other = [str(uuid.UUID(int=9000 + i)) for i in range(40)]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, *argv):
        buf, out = io.StringIO(), self.tmp / 'r.json'
        with redirect_stdout(buf):
            code = W.main(list(argv) + ['--out', str(out)])
        return code, json.loads(out.read_text(encoding='utf-8')), buf.getvalue()

    def test_renamed_copy_and_two_lines(self):
        a = self.tmp / 'lineA' / 'deliver_v32' / 'MusicSlice_v32_upload.zip'
        source_zip(a, self.game, 'a')
        source_zip(self.tmp / 'lineB' / 'MusicSlice_v31.zip', self.game, 'b')
        source_zip(self.tmp / 'lineB' / 'Other_v3.zip', self.other)
        phone = self.tmp / 'wechat' / 'renamed(1).zip'
        phone.parent.mkdir()
        shutil.copy(a, phone)
        code, r, text = self.run_tool('--zip', str(phone), '--roots', str(self.tmp / 'lineA'), '--roots', str(self.tmp / 'lineB'))
        self.assertEqual(code, 0)
        self.assertEqual(r['exact'], [str(a)])
        paths = [x['path'] for x in r['same_game']]
        self.assertIn(str(self.tmp / 'lineB' / 'MusicSlice_v31.zip'), paths)
        self.assertNotIn(str(self.tmp / 'lineB' / 'Other_v3.zip'), paths)
        self.assertGreaterEqual(len(r['folders']), 2)
        self.assertIn('逐字节相同', text)
        self.assertIn('版本线', text)

    def test_unknown_package(self):
        source_zip(self.tmp / 'lineA' / 'MusicSlice_v31.zip', self.game)
        lone = self.tmp / 'phone.zip'
        source_zip(lone, self.other)
        code, r, text = self.run_tool('--zip', str(lone), '--roots', str(self.tmp / 'lineA'))
        self.assertEqual(code, 0)
        self.assertEqual(r['exact'], [])
        self.assertEqual(r['same_game'], [])
        self.assertIn('没有找到', text)

    def test_bad_input(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(W.main(['--zip', str(self.tmp / 'nope.zip'), '--roots', str(self.tmp)]), 2)


if __name__ == '__main__':
    unittest.main()
