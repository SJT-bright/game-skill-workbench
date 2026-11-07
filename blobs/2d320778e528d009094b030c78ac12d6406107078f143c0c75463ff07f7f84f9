#!/usr/bin/env python3
"""English pack 10.2.10 (Saul 2026-10-31: the English Skill must work on other people's computers).

find_creator.py finds Creator on macOS and Windows layouts and in the Dashboard's own list, picks the exact version or
the nearest patch of the same minor version, and builds 2.x / 3.x commands. browser_env.py selects official Ego Lite
and refuses missing or unsupported routes before running any test. check_machine.py reports what is missing and how
to add it. fix_web_entry_3x.py writes only a missing 3.x entry page and refuses unknown templates.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_portable_tools.py
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import browser_env as BE  # noqa: E402
import find_creator as FC  # noqa: E402


def touch(path, text=''):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


class FindCreator(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)

    def project(self, version, major):
        p = self.root / ('proj%s' % version)
        if major == 2:
            touch(p / 'project.json', json.dumps({'engine': 'cocos-creator-js', 'version': version}))
            touch(p / 'settings' / 'project.json', '{}')
        else:
            touch(p / 'package.json', json.dumps({'name': 'x', 'creator': {'version': version}}))
        return p

    def test_project_versions(self):
        self.assertEqual(FC.project_version(self.project('2.4.15', 2)), ('2.4.15', 2))
        self.assertEqual(FC.project_version(self.project('3.7.1', 3)), ('3.7.1', 3))
        with self.assertRaises(ValueError):
            FC.project_version(self.root)

    def test_windows_dashboard_folders(self):
        drive = self.root / 'C'
        for v in ('2.4.5', '2.4.15'):
            touch(drive / 'CocosDashboard' / 'resources' / '.editors' / 'Creator' / v / 'CocosCreator.exe')
        touch(drive / 'ProgramData' / 'cocos' / 'editors' / 'Creator' / '3.8.8' / 'CocosCreator.exe')
        real_path = Path

        def fake_path(*a):
            if a and a[0] in ('C:\\', 'D:\\'):
                return real_path(drive) if a[0] == 'C:\\' else real_path(self.root / 'D')
            return real_path(*a)
        with mock.patch.object(FC, 'Path', side_effect=fake_path):
            editors = FC.installed_editors('win32', home=str(self.root / 'home'), env={'SystemDrive': 'C:'})
        self.assertEqual([e['version'] for e in editors], ['3.8.8', '2.4.15', '2.4.5'])
        self.assertTrue(all(e['exe'].endswith('CocosCreator.exe') for e in editors))

    def test_dashboard_record_and_env(self):
        home = self.root / 'home'
        exe = touch(self.root / 'Editors' / '3.6.2' / 'CocosCreator.exe')
        own = touch(self.root / 'Own' / '2.4.3' / 'CocosCreator.exe')
        touch(home / '.cocos' / 'profiles' / 'editor.json', json.dumps({'editor': {
            'Creator3D': [{'version': '3.6.2', 'file': str(exe.parent), 'state': 'success'},
                          {'version': '3.8.0', 'file': str(self.root / 'missing'), 'state': 'success'}],
            'Creator': [{'version': '2.4.9', 'file': str(exe.parent), 'state': 'downloading'}]}}))
        editors = FC.installed_editors('win32', home=str(home), env={'COCOS_CREATOR': str(own)})
        got = {e['version']: e['source'] for e in editors}
        self.assertEqual(set(got), {'3.6.2', '2.4.3'})
        self.assertIn('Dashboard', got['3.6.2'])
        self.assertEqual(got['2.4.3'], 'COCOS_CREATOR')

    def test_macos_app_layout(self):
        app = self.root / 'Creator' / '2.4.4' / 'CocosCreator.app'
        touch(app / 'Contents' / 'MacOS' / 'CocosCreator')
        import plistlib
        with open(touch(app / 'Contents' / 'Info.plist'), 'wb') as f:
            plistlib.dump({'CFBundleShortVersionString': '2.4.4'}, f)
        exe = FC.executable_of(app, 'darwin')
        self.assertTrue(str(exe).endswith('Contents/MacOS/CocosCreator'))
        self.assertEqual(FC.app_version(exe), '2.4.4')

    def test_choose_exact_substitute_missing(self):
        eds = [{'version': v, 'exe': '/x/' + v, 'source': 't'} for v in ('3.8.8', '2.4.15', '2.4.5', '2.4.3')]
        self.assertEqual(FC.choose('2.4.15', eds)['status'], 'exact')
        sub = FC.choose('2.4.4', eds)
        self.assertEqual((sub['status'], sub['editor']['version']), ('substitute', '2.4.5'))   # nearest, newer on a tie
        self.assertEqual(FC.choose('3.7.1', eds)['status'], 'missing')                         # never 3.8 for 3.7
        self.assertEqual(FC.choose('2.3.4', eds)['status'], 'missing')                         # never across minors

    def test_build_commands_per_major_and_report(self):
        ed = {'version': '2.4.5', 'exe': '/E/CocosCreator', 'source': 't'}
        a2 = FC.build_argv(ed, '/p', 2, 'web-mobile')
        a3 = FC.build_argv(ed, '/p', 3, 'bytedance-mini-game')
        t2 = FC.build_argv(ed, '/p', 2, 'bytedance-mini-game')     # 简化.11.15: 2.x calls the TikTok platform bytedance
        self.assertEqual((a2[1], a2[4]), ('--path', 'platform=web-mobile;debug=true'))
        self.assertEqual((a3[1], a3[4]), ('--project', 'platform=bytedance-mini-game;debug=false'))
        self.assertEqual((t2[1], t2[4]), ('--path', 'platform=bytedance;debug=false'))
        self.assertIn('"platform=web-mobile;debug=true"', FC.quote(['C:\\E\\CocosCreator.exe', '--build', 'platform=web-mobile;debug=true'], 'win32'))
        proj = self.project('2.4.4', 2)
        with mock.patch.object(FC, 'installed_editors', return_value=[ed]):
            r = FC.report(proj, platform='win32')
        self.assertEqual(r['status'], 'substitute')
        self.assertIn('--path', r['commands']['web-mobile']['argv'])
        text = FC.say(r)
        self.assertIn('没装 2.4.4', text)
        self.assertIn('engine.txt', text)
        with mock.patch.object(FC, 'installed_editors', return_value=[]):
            self.assertIn('Cocos Dashboard', FC.say(FC.report(proj, platform='win32')))

    def test_busy_parses_build_lines(self):
        ps = '  12 /A/CocosCreator.app/Contents/MacOS/CocosCreator --path /p --build platform=web-mobile\n  13 /bin/zsh\n'
        with mock.patch.object(FC.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, ps, '')):
            self.assertEqual([r['pid'] for r in FC.busy('darwin')], ['12'])
        with mock.patch.object(FC.subprocess, 'run', side_effect=OSError('denied')):
            self.assertIsNone(FC.busy('darwin'))


class BrowserEnv(unittest.TestCase):
    def test_ego_is_used_when_installed(self):
        with mock.patch.object(BE, 'find_ego', return_value='/u/bin/ego-browser'), \
                mock.patch.dict(os.environ, {'EGO_BROWSER': ''}):
            self.assertEqual(BE.plan('auto'), {'route': 'ego', 'ego_browser': '/u/bin/ego-browser'})
            self.assertEqual(BE.plan('ego'), BE.plan('auto'))

    def test_no_ego_does_not_fall_back(self):
        with mock.patch.object(BE, 'find_ego', return_value=None), \
                mock.patch.dict(os.environ, {'EGO_BROWSER': '', 'CDP_BROWSER': '/b/chrome'}), \
                mock.patch.object(BE.subprocess, 'run') as spawn:
            for mode in ('auto', 'ego'):
                plan = BE.plan(mode)
                self.assertIsNone(plan['route'])
                self.assertIn('ego-browser', plan['problem'])
                self.assertEqual(BE.main(['--browser', mode, '--', 'test-command']), BE.ENV_CODE)
            spawn.assert_not_called()

    def test_explicit_chrome_and_fake_ego_override_are_refused(self):
        with mock.patch.object(BE, 'find_ego', return_value='/u/bin/ego-browser'), \
                mock.patch.dict(os.environ, {'EGO_BROWSER': '/b/fake-ego'}), \
                mock.patch.object(BE.subprocess, 'run') as spawn:
            self.assertEqual(BE.main(['--browser', 'chrome', '--', 'test-command']), BE.ENV_CODE)
            self.assertIsNone(BE.plan()['route'])
            self.assertIn('EGO_BROWSER', BE.plan()['problem'])
            self.assertEqual(BE.main(['--', 'test-command']), BE.ENV_CODE)
            spawn.assert_not_called()

    def test_wrapped_environment_binds_the_official_ego_without_fallback(self):
        with tempfile.TemporaryDirectory() as td, \
                mock.patch.dict(os.environ, {BE.FALLBACK_BROWSER_ENV: '/b/chrome', BE.FALLBACK_NODE_ENV: '/n/node'}):
            chosen = {'route': 'ego', 'ego_browser': '/u/bin/ego-browser'}
            env = BE.environment_for(chosen, td, game='Portable Demo')
            self.assertEqual(env['EGO_BROWSER'], chosen['ego_browser'])
            self.assertEqual(env[BE.GAME_ENV], 'Portable Demo')
            self.assertEqual(env['PATH'], os.environ['PATH'])
            self.assertNotIn(BE.FALLBACK_BROWSER_ENV, env)
            self.assertNotIn(BE.FALLBACK_NODE_ENV, env)
            self.assertFalse(list(Path(td).glob('ego-browser*')))


class CheckMachine(unittest.TestCase):
    def collect(self, plan, editors, spec=True, ffmpeg='/x/ffmpeg', node=('/n/node', 22)):
        import check_machine as CM
        with mock.patch.object(CM.browser_env, 'plan', return_value=plan), \
                mock.patch.object(CM.browser_env, 'node_path', return_value=node), \
                mock.patch.object(CM.find_creator, 'installed_editors', return_value=editors), \
                mock.patch.object(CM.importlib.util, 'find_spec', return_value=object() if spec else None), \
                mock.patch.object(CM, 'ffmpeg_path', return_value=ffmpeg):
            rows = CM.collect(None, quick=True)
        return CM, rows

    def test_everything_present(self):
        CM, rows = self.collect({'route': 'ego', 'ego_browser': '/e/ego-browser'},
                                [{'version': '2.4.15', 'exe': '/c', 'source': 't'}])
        self.assertTrue(all(r['ok'] for r in rows if r['required']), rows)
        self.assertIn('可以开工', CM.say(rows))

    def test_missing_required_items_are_named_with_a_fix(self):
        CM, rows = self.collect({'route': None, 'problem': '找不到官方 Ego Lite'}, [], spec=False, ffmpeg=None, node=(None, None))
        missing = {r['name'] for r in rows if r['required'] and not r['ok']}
        self.assertEqual(missing, {'Pillow', '出包检查用的浏览器', 'Cocos Creator'})
        text = CM.say(rows)
        self.assertIn('缺（必须）', text)
        self.assertIn('缺（建议）  numpy', text)
        self.assertIn('缺（建议）  Node.js', text)
        self.assertIn('问一句能不能装', text)
        self.assertTrue(all(r['fix'] for r in rows if not r['ok']))

    def test_exit_codes(self):
        import check_machine as CM
        with mock.patch.object(CM, 'collect', return_value=[{'name': 'x', 'ok': False, 'required': True, 'detail': '',
                                                             'fix': 'f', 'affects': 'a'}]):
            self.assertEqual(CM.main(['--quick']), 1)
        with mock.patch.object(CM, 'collect', return_value=[{'name': 'x', 'ok': True, 'required': True, 'detail': '',
                                                             'fix': None, 'affects': None}]):
            self.assertEqual(CM.main(['--quick']), 0)


class FixWebEntry(unittest.TestCase):
    def setUp(self):
        import fix_web_entry_3x as FW
        self.FW = FW
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        root = Path(self.td.name)
        self.tpl = root / 'templates' / 'web-mobile'
        touch(self.tpl / 'index.ejs', '\ufeff<!DOCTYPE html><title>Cocos Creator | <%= projectName %></title>'
                                      '<link href="<%= cssUrl %>"/><body>\n  <%- include(cocosTemplate, {}) %>\n</body>')
        touch(self.tpl / 'index.js.ejs', FW.KNOWN_INDEX_JS_EJS + '\n')
        touch(self.tpl / 'style.css', 'body{margin:0}')
        self.exp = root / 'web-mobile'
        touch(self.exp / 'application.js', 'System.register([], function (_export) { _export("Application", 1); });')
        touch(self.exp / 'src' / 'system.bundle.js', '')
        touch(self.exp / 'src' / 'import-map.json', '{}')

    def test_writes_the_missing_entry_once(self):
        r = self.FW.fix(self.exp, self.tpl, 'Demo')
        self.assertEqual(r['written'], ['index.html', 'index.js', 'style.css'])
        html = (self.exp / 'index.html').read_text(encoding='utf-8')
        self.assertFalse(html.startswith('\ufeff'))
        self.assertIn('Cocos Creator | Demo', html)
        self.assertIn('src/system.bundle.js', html)
        self.assertNotIn('polyfills.bundle.js', html)            # not in this export, so no tag for it
        self.assertNotIn('<%', html)
        self.assertIn('System.register(["./application.js"]', (self.exp / 'index.js').read_text(encoding='utf-8'))
        self.assertEqual(self.FW.fix(self.exp, self.tpl, 'Demo')['written'], [])

    def test_refuses_unknown_templates_and_non_3x_exports(self):
        touch(self.tpl / 'index.ejs', '<html><%= projectName %><%= cssUrl %><%- include(cocosTemplate, {}) %><%= extra %></html>')
        with self.assertRaises(ValueError):
            self.FW.fix(self.exp, self.tpl, 'Demo')
        self.assertFalse((self.exp / 'index.html').exists())
        (self.exp / 'application.js').write_text('var x = 1;', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.FW.fix(self.exp, self.tpl, 'Demo')

    def test_editor_template_locations(self):
        mac = self.FW.template_dirs('/Applications/Cocos/Creator/3.7.1/CocosCreator.app/Contents/MacOS/CocosCreator')
        self.assertIn(Path('/Applications/Cocos/Creator/3.7.1/CocosCreator.app/Contents/Resources/resources/3d/engine/'
                           'templates/web-mobile'), mac)
        # forward slashes: the same Windows layout parses on every OS the test runs on
        win = self.FW.template_dirs('C:/CocosDashboard/resources/.editors/Creator/3.7.1/CocosCreator.exe')
        self.assertTrue(any(str(p).replace('\\', '/').endswith('3.7.1/resources/resources/3d/engine/templates/web-mobile')
                            for p in win), win)


if __name__ == '__main__':
    unittest.main(verbosity=2)
