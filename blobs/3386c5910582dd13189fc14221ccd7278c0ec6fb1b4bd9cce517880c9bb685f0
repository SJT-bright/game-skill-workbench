#!/usr/bin/env python3
"""生成时预防 R4F1 (#11, P02-3): the build commands find_creator.py prints start with `tiktok_finalize.py sync`.

Before, only SKILL.md said "run sync before every build"; the printed command was the bare Creator build, so a build ran
on platform-kit files that had drifted (普查 startup_stuck 34 款 / touch_coord_missing 28 款). Cases:
  1 posix      web-mobile and TikTok text: `<python> .../tiktok_finalize.py sync --project P --board localize && <Creator>`,
               steps = [sync argv, build argv], argv stays the bare build (old callers keep working)
  2 marker     a project whose .tiktok-kit/policy.json says board remake gets --board remake; --board overrides
  3 windows    PowerShell text runs the build only when sync exited 0 ($LASTEXITCODE)
  4 runs       the printed sync argv really runs on a 2.4 fixture project (exit 0, .tiktok-kit/sync.json written)
  5 missing    no remake-core next to the pack: no sync in the commands and a hint says so
Run: python3 test_r4f1_build_sync.py
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import find_creator as FC  # noqa: E402

ED = {'version': '2.4.15', 'exe': '/E/CocosCreator', 'source': 't'}


def touch(path, text=''):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


class BuildSync(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.proj = Path(td.name) / 'proj'
        touch(self.proj / 'project.json', json.dumps({'engine': 'cocos-creator-js', 'version': '2.4.15'}))
        touch(self.proj / 'settings' / 'project.json', '{}')
        touch(self.proj / 'assets' / 'scenes' / 'Main.fire.meta',
              '{"ver": "1.2.9", "uuid": "1b2c3d4e-0000-4000-8000-00000000abcd", "importer": "scene"}')

    def report(self, **kw):
        with mock.patch.object(FC, 'installed_editors', return_value=[ED]):
            return FC.report(self.proj, sandbox_probe=False, **kw)

    def test_1_posix_build_text_starts_with_sync(self):
        r = self.report(platform='darwin')
        for name in ('web-mobile', 'bytedance-mini-game'):
            cmd = r['commands'][name]
            sync, build = cmd['text'].split(' && ')[:2]     # R4J4: the TikTok text also ends with && sync --native
            self.assertRegex(sync, r"tiktok_finalize\.py'? sync --project ")
            self.assertTrue(sync.endswith('--board localize'), sync)
            self.assertTrue(build.startswith('/E/CocosCreator --path'), build)
            self.assertEqual(cmd['steps'][0][2:4], ['sync', '--project'])
            self.assertEqual(cmd['steps'][1], cmd['argv'])
            self.assertEqual(cmd['argv'][0], '/E/CocosCreator')
        self.assertIn('每条构建命令前面都带 tiktok_finalize.py sync', FC.say(r))

    def test_2_board_from_marker_or_flag(self):
        touch(self.proj / '.tiktok-kit' / 'policy.json', json.dumps({'policy': 'new', 'board': 'remake'}))
        self.assertEqual(self.report(platform='darwin')['commands']['web-mobile']['sync_argv'][-1], 'remake')
        self.assertEqual(self.report(platform='darwin', board='localize')['sync']['board'], 'localize')

    def test_3_windows_runs_build_only_after_sync(self):
        text = self.report(platform='win32')['commands']['bytedance-mini-game']['text']
        self.assertRegex(text, r'^& .*tiktok_finalize\.py.* sync .*; if \(\$LASTEXITCODE -eq 0\) \{ & .*CocosCreator')

    def test_4_printed_sync_really_runs(self):
        argv = self.report(platform='darwin')['commands']['web-mobile']['steps'][0]
        out = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertTrue((self.proj / '.tiktok-kit' / 'sync.json').is_file())

    def test_5_no_remake_core(self):
        r = self.report(platform='darwin', finalize=self.proj / 'nothing.py')
        self.assertNotIn('sync', r['commands']['web-mobile']['text'])
        self.assertTrue(any('tiktok_finalize.py' in h for h in r['hints']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
