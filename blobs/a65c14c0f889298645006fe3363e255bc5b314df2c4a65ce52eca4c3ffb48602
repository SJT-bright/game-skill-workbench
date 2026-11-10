#!/usr/bin/env python3
"""生成时预防 R4J4 (P02-3, after R4F1): the TikTok build command find_creator.py prints ends with
`tiktok_finalize.py sync --project P --board B --native <build folder>`, run only when the build succeeded.

Before, the printed TikTok command stopped after the Creator build, so English builds were packaged without the startup
parts, touch fix, storage layer, host-shim and guards (普查 startup_stuck 34/42 款, touch_coord_missing 28/34 款). The
build folder is worked out from the build argv, not written in: 2.4 <buildPath, default build>/bytedance, 3.x
<buildPath, default project://build>/<outputName, default bytedance-mini-game>. Creator is never started: a fake
Creator script stands in for it. Cases:
  1 cocos 2.4    TikTok steps = [sync, build, sync --native P/build/bytedance]; text `sync && build && sync --native`;
                 web-mobile keeps its two steps
  2 cocos 3.x    --native P/build/bytedance-mini-game; build_ok_exit [0, 36]; PowerShell runs it when
                 $LASTEXITCODE is 0 or 36
  3 folder       buildPath / outputName / project:// / absolute / 2.4 Build-panel buildPath are followed; configPath or
                 an odd buildPath gives no --native step and a hint to run it by hand
  4 2.4 runs     the printed POSIX text, run by /bin/sh with a fake Creator that writes a 2.4 build folder: the real
                 sync --native puts the kit touch-coordinates.js, storage-guard.js and main.js into P/build/bytedance
  5 exit codes   3.x: build exit 36 -> sync --native runs, 34 -> it does not; 2.4: exit 1 -> it does not
Run: python3 test_r4j4_native_sync.py
"""
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import find_creator as FC  # noqa: E402

MANIFEST = HERE.parents[1] / 'remake-core' / 'assets' / 'platform-kit' / 'KIT_MANIFEST.json'
GAME24 = """"use strict";
require('adapter-min.js');
__globalAdapter.init();
require('cocos/cocos2d-js-min.js');
__globalAdapter.adaptEngine();
require('./ccRequire');
require('./src/settings');
require('./main');
window.boot();
"""
# stands in for CocosCreator: writes a minimal 2.4 bytedance build under <project>/build/bytedance, exits FAKE_EXIT
FAKE_CREATOR = r'''#!%s
import os, sys
from pathlib import Path
a = sys.argv
p = Path(a[a.index('--path') + 1] if '--path' in a else a[a.index('--project') + 1])
if os.environ.get('FAKE_WRITE') == '1':
    b = p / 'build' / 'bytedance'
    (b / 'cocos').mkdir(parents=True, exist_ok=True)
    (b / 'src').mkdir(exist_ok=True)
    (b / 'cocos' / 'cocos2d-js-min.js').write_text('var ENGINE_VERSION = "2.4.15"; window.cc = {};\n')
    (b / 'adapter-min.js').write_text('/* adapter */\n')
    (b / 'game.js').write_text(os.environ['FAKE_GAME'])
    (b / 'main.js').write_text('window.boot = function () { /* editor main */ };\n')
    (b / 'ccRequire.js').write_text('/* ccRequire */\n')
    (b / 'src' / 'settings.js').write_text('window._CCSettings = {};\n')
    (b / 'game.json').write_text('{"deviceOrientation": "portrait"}\n')
    (b / 'project.config.json').write_text('{"appid": "1"}\n')
sys.exit(int(os.environ.get('FAKE_EXIT', '0')))
'''
FAKE_FINALIZE = r'''#!%s
import sys
with open(sys.argv[0] + '.log', 'a') as f:
    f.write(' '.join(sys.argv[1:]) + '\n')
'''


def touch(path, text=''):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class NativeSync(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp = Path(td.name)
        self.p2 = self.tmp / 'proj24'
        touch(self.p2 / 'project.json', json.dumps({'engine': 'cocos-creator-js', 'version': '2.4.15'}))
        touch(self.p2 / 'settings' / 'project.json', '{}')
        touch(self.p2 / 'assets' / 'scenes' / 'Main.fire.meta',
              '{"ver": "1.2.9", "uuid": "1b2c3d4e-0000-4000-8000-00000000abcd", "importer": "scene"}')
        self.p3 = self.tmp / 'proj3x'
        touch(self.p3 / 'package.json', json.dumps({'creator': {'version': '3.8.8'}}))
        touch(self.p3 / 'assets' / 'Main.scene', '[]')
        touch(self.p3 / 'assets' / 'Main.scene.meta', '{"uuid":"main-scene"}')
        self.creator = touch(self.tmp / 'FakeCreator', FAKE_CREATOR % sys.executable)
        os.chmod(self.creator, 0o755)

    def report(self, project, version, **kw):
        ed = {'version': version, 'exe': str(self.creator), 'source': 't'}
        with mock.patch.object(FC, 'installed_editors', return_value=[ed]):
            return FC.report(project, sandbox_probe=False, **kw)

    def test_1_cocos24_tiktok_ends_with_sync_native(self):
        r = self.report(self.p2, '2.4.15', platform='darwin')
        tt = r['commands']['bytedance-mini-game']
        want = str(self.p2.resolve() / 'build' / 'bytedance')
        self.assertEqual(len(tt['steps']), 3, tt['steps'])
        self.assertEqual(tt['steps'][1], tt['argv'])
        self.assertEqual(tt['steps'][2], tt['sync_argv'] + ['--native', want])
        self.assertEqual(tt['native_dir'], want)
        parts = tt['text'].split(' && ')
        self.assertEqual(len(parts), 3, tt['text'])
        self.assertEqual(shlex.split(parts[2])[-2:], ['--native', want])
        self.assertEqual(len(r['commands']['web-mobile']['steps']), 2, 'web-mobile has no --native step')
        self.assertNotIn('--native', r['commands']['web-mobile']['text'])
        self.assertIn('sync --native', FC.say(r))

    def test_2_cocos3x_folder_and_exit_36(self):
        r = self.report(self.p3, '3.8.8', platform='darwin')
        tt = r['commands']['bytedance-mini-game']
        want = str(self.p3.resolve() / 'build' / 'bytedance-mini-game')
        self.assertEqual(tt['steps'][-1][-2:], ['--native', want])
        self.assertEqual(tt['steps'][1], tt['prepare_argv'])
        self.assertEqual(tt['build_ok_exit'], [0, 36])
        self.assertEqual(shlex.split(tt['text'].rsplit(' && ', 1)[1])[-2:], ['--native', want])
        win = self.report(self.p3, '3.8.8', platform='win32')['commands']['bytedance-mini-game']['text']
        self.assertRegex(win, r'; if \(\$LASTEXITCODE -eq 0 -or \$LASTEXITCODE -eq 36\) \{ & .*tiktok_finalize\.py'
                              r'.* sync .*--native .*bytedance-mini-game"? \} \} \}$')
        win24 = self.report(self.p2, '2.4.15', platform='win32')['commands']['bytedance-mini-game']['text']
        self.assertRegex(win24, r'; if \(\$LASTEXITCODE -eq 0\) \{ & .*--native .*bytedance"? \} \}$')

    def test_3_folder_follows_build_arguments(self):
        p2, p3 = self.p2.resolve(), self.p3.resolve()
        nd = FC.native_dir
        self.assertEqual(nd(['C', '--path', str(p2), '--build', 'platform=bytedance;debug=false;buildPath=out'], p2, 2),
                         (p2 / 'out' / 'bytedance', None))
        self.assertEqual(nd(['C', '--project', str(p3), '--build',
                             'platform=bytedance-mini-game;buildPath=project://dist;outputName=tt'], p3, 3),
                         (p3 / 'dist' / 'tt', None))
        absolute = self.tmp / 'abs'
        self.assertEqual(nd(['C', '--build', 'platform=bytedance-mini-game;buildPath=%s' % absolute], p3, 3)[0],
                         absolute / 'bytedance-mini-game')
        self.assertEqual(nd(['C', '--build', 'platform=bytedance;outputName=x'], p2, 2)[0], p2 / 'build' / 'bytedance',
                         '2.4 has no outputName')
        touch(self.p2 / 'local' / 'builder.json', json.dumps({'buildPath': 'release'}))
        self.assertEqual(nd(['C', '--build', 'platform=bytedance'], p2, 2)[0], p2 / 'release' / 'bytedance',
                         '2.4 without buildPath uses the Build panel one')
        for opts in ('platform=bytedance-mini-game;configPath=/x/b.json', 'platform=bytedance-mini-game;buildPath=db://x',
                     'platform=web-mobile'):
            folder, why = nd(['C', '--build', opts], p3, 3)
            self.assertIsNone(folder, opts)
            self.assertTrue(why, opts)
        touch(self.p2 / 'local' / 'builder.json', json.dumps({'buildPath': 7}))
        with mock.patch.object(FC, 'native_dir', return_value=(None, '测试')):
            r = self.report(self.p2, '2.4.15', platform='darwin')
        tt = r['commands']['bytedance-mini-game']
        self.assertNotIn('--native', tt['text'])
        self.assertEqual(len(tt['steps']), 2)
        self.assertTrue(any('sync --native' in h and '手跑' in h for h in r['hints']), r['hints'])
        self.assertIsNone(FC.native_dir(['C', '--build', 'platform=bytedance'], p2, 2)[0], 'odd saved buildPath')

    @unittest.skipIf(sys.platform == 'win32', 'POSIX shell text')
    def test_4_cocos24_printed_text_really_installs_parts(self):
        r = self.report(self.p2, '2.4.15', platform='darwin')
        text = r['commands']['bytedance-mini-game']['text']
        env = dict(os.environ, FAKE_WRITE='1', FAKE_EXIT='0', FAKE_GAME=GAME24)
        out = subprocess.run(['/bin/sh', '-c', text], capture_output=True, text=True, timeout=120, env=env)
        self.assertEqual(out.returncode, 0, out.stdout[-2000:] + out.stderr[-2000:])
        b = self.p2 / 'build' / 'bytedance'
        man = json.loads(MANIFEST.read_text(encoding='utf-8'))['parts']
        self.assertEqual(sha(b / 'touch-coordinates.js'), man['touch24']['file']['sha256'])
        self.assertEqual(sha(b / 'storage-guard.js'), man['storage24']['file']['sha256'])
        self.assertEqual(sha(b / 'main.js'), man['startup24']['file']['sha256'])
        rec = json.loads((self.p2 / '.tiktok-kit' / 'sync.json').read_text(encoding='utf-8'))
        self.assertEqual(Path(rec['native']).resolve(), b.resolve())

    @unittest.skipIf(sys.platform == 'win32', 'POSIX shell text')
    def test_5_native_step_only_after_a_good_build(self):
        fin = touch(self.tmp / 'fake_finalize.py', FAKE_FINALIZE % sys.executable)
        log = Path(str(fin) + '.log')
        for project, version, code, ran in ((self.p3, '3.8.8', 36, True), (self.p3, '3.8.8', 0, True),
                                            (self.p3, '3.8.8', 34, False), (self.p2, '2.4.15', 1, False),
                                            (self.p2, '2.4.15', 0, True)):
            if log.exists():
                log.unlink()
            text = self.report(project, version, platform='darwin', finalize=fin)['commands']['bytedance-mini-game']['text']
            subprocess.run(['/bin/sh', '-c', text], capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, FAKE_WRITE='0', FAKE_EXIT=str(code)))
            lines = log.read_text().splitlines()
            self.assertEqual(lines[0].split()[:1], ['sync'])
            self.assertEqual(any('--native' in l for l in lines), ran, (version, code, lines))


if __name__ == '__main__':
    unittest.main(verbosity=2)
