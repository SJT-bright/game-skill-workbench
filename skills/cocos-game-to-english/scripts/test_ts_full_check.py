#!/usr/bin/env python3
"""ts_full_check.py never reads temp/ (R4O5, 补查2 第 5 节, SLS35: temp/declarations pointed at a Windows Cocos)."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ts_full_check  # noqa: E402

WIN = 'C:/ProgramData/cocos/editors/Creator/3.8.6/resources/resources/3d/engine/bin/.declarations/cc.d.ts'
GAME_TS = "import { _decorator, Component, Node } from 'cc';\nconst { ccclass } = _decorator;\n" \
          "@ccclass('Hud')\nexport class Hud extends Component {\n    start() { const n: Node = new Node('x'); n.active = true; }\n}\n"


def fake_project(root, ts=GAME_TS):
    """A 3.x project archived on Windows: tsconfig extends temp/, temp/declarations references the Windows engine."""
    p = Path(root) / 'game'
    (p / 'assets' / 'scripts').mkdir(parents=True)
    (p / 'assets' / 'scripts' / 'Hud.ts').write_text(ts, encoding='utf-8')
    (p / 'tsconfig.json').write_text('{\n  /* Base configuration. Do not edit this field. */\n'
                                     '  "extends": "./temp/tsconfig.cocos.json",\n'
                                     '  "compilerOptions": { "strict": false, },\n}\n', encoding='utf-8')
    (p / 'temp' / 'declarations').mkdir(parents=True)
    (p / 'temp' / 'declarations' / 'cc.d.ts').write_text('/// <reference path="%s"/>\ndeclare const cc: never;\n' % WIN)
    (p / 'temp' / 'tsconfig.cocos.json').write_text(json.dumps({'compilerOptions': {
        'target': 'ES2015', 'module': 'ES2015', 'strict': True, 'types': ['./temp/declarations/cc'],
        'paths': {'db://internal/*': ['C:/ProgramData/cocos/editors/Creator/3.8.6/resources/resources/3d/engine/editor/assets/*']},
        'experimentalDecorators': True, 'moduleResolution': 'node', 'noEmit': True}}))
    return p


class Config(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_generated_config_names_nothing_under_temp(self):
        project = fake_project(self.tmp)
        out = Path(self.tmp) / 'out'
        out.mkdir()
        cfg = ts_full_check.write_config(project, '/local/Creator/declarations', out)
        text = cfg.read_text(encoding='utf-8') + (out / 'cc-local-env.d.ts').read_text(encoding='utf-8')
        data = json.loads(cfg.read_text(encoding='utf-8'))
        self.assertNotIn('extends', data)
        self.assertNotIn('C:/ProgramData', text)
        self.assertNotIn('/temp/declarations', text)
        self.assertEqual(data['compilerOptions']['types'], [])
        self.assertIn('/local/Creator/declarations/cc.d.ts', text)
        self.assertIn((project / 'temp').resolve().as_posix(), data['exclude'])
        self.assertFalse(data['compilerOptions']['strict'])          # the project's own option is kept

    def test_comments_and_trailing_commas_are_read(self):
        project = fake_project(self.tmp)
        self.assertEqual(ts_full_check.project_options(project), {'strict': False})

    def test_stale_temp_reference_is_reported_not_used(self):
        project = fake_project(self.tmp)
        self.assertEqual(ts_full_check.stale_temp(project), [WIN])


@unittest.skipUnless(ts_full_check.local_toolchain() and shutil.which('node'), 'no local Cocos 3.x Creator / node')
class RealTsc(unittest.TestCase):
    """With the local Creator's tsc: the old way (tsc -p tsconfig.json) fails on the stale temp/, the tool passes."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.tools = ts_full_check.local_toolchain()

    def test_old_way_fails_on_the_windows_temp(self):
        project = fake_project(self.tmp)
        r = subprocess.run([shutil.which('node'), str(self.tools['tsc']), '-p', str(project / 'tsconfig.json'),
                            '--pretty', 'false'], capture_output=True, text=True, timeout=300)
        self.assertNotEqual(r.returncode, 0)
        self.assertRegex(r.stdout + r.stderr, r"Cannot find module 'cc'|TS6053|cannot find")

    def test_tool_passes_a_good_project_with_a_windows_temp(self):
        res = ts_full_check.run(fake_project(self.tmp))
        self.assertEqual(res['status'], 'passed', res.get('errors'))
        self.assertEqual(res['stale_temp_references'], [WIN])

    def test_tool_still_finds_a_real_type_error(self):
        res = ts_full_check.run(fake_project(self.tmp, GAME_TS.replace("new Node('x')", '42')))
        self.assertEqual(res['status'], 'failed')
        self.assertTrue(any('Hud.ts' in e for e in res['errors']), res['errors'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
