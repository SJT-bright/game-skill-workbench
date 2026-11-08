"""Creator 3.x typed JSON preflight; no real engine/browser is launched."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import find_creator as F


class TypedConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name).resolve() / 'a project'
        self.p.mkdir(); (self.p / 'package.json').write_text('{"creator":{"version":"3.6.2"}}')
        (self.p / 'assets/scenes').mkdir(parents=True)
        self.scenes = []
        for name in ('Home', 'Play'):
            scene = self.p / 'assets/scenes' / (name + '.scene'); scene.write_text('[]')
            scene.with_suffix('.scene.meta').write_text(json.dumps({'uuid': name}))
            self.scenes.append({'uuid': name, 'url': 'db://assets/scenes/' + name + '.scene', 'inBundle': False})
        self.options = {'platform': 'bytedance-mini-game', 'debug': False, 'startScene': 'Home',
                        'scenes': self.scenes, 'buildPath': 'project://out', 'outputName': 'custom',
                        'packages': {'bytedance-mini-game': {'appid': 'own-app', 'orientation': 'portrait'}}}
        self.saved = self.p / 'profiles/v2/packages/builder.json'; self.saved.parent.mkdir(parents=True)
        self.save()

    def save(self):
        self.saved.write_text(json.dumps({'common': {'platform': 'web-desktop', 'outputName': 'wrong'},
               'BuildTaskManager': {'taskMap': {'8': {'options': self.options}}}}))

    def test_json_false_and_project_settings_preserved(self):
        before = self.saved.read_bytes()
        out = F.write_build_config_3x(self.p, 'bytedance-mini-game')
        cfg = json.loads(out.read_text())
        self.assertIs(cfg['debug'], False); self.assertIs(cfg['sourceMaps'], False)
        for key in ('scenes', 'startScene', 'packages', 'buildPath', 'outputName'):
            self.assertEqual(cfg[key], self.options[key])
        self.assertEqual(before, self.saved.read_bytes())
        stamp = out.stat().st_mtime_ns
        F.write_build_config_3x(self.p, 'bytedance-mini-game')
        self.assertEqual(stamp, out.stat().st_mtime_ns)

    def test_newest_target_task_not_other_platform(self):
        data = json.loads(self.saved.read_text())
        data['BuildTaskManager']['taskMap']['9'] = {'options':dict(self.options, startScene='Play')}
        data['BuildTaskManager']['taskMap']['99'] = {'options':dict(self.options, platform='web-mobile', startScene='Home')}
        self.saved.write_text(json.dumps(data))
        self.assertEqual(F.build_config_3x(self.p, 'bytedance-mini-game')['startScene'], 'Play')

    def test_current_platform_profile_overrides_old_task_adaptation(self):
        profile=self.saved.with_name('bytedance-mini-game.json')
        profile.write_text(json.dumps({'common':{'platform':'bytedance-mini-game','outputName':'latest'},
                       'options':{'bytedance-mini-game':{'appid':'current-app','orientation':'landscape'}}}))
        cfg=F.build_config_3x(self.p,'bytedance-mini-game')
        self.assertEqual(cfg['outputName'],'latest')
        self.assertEqual(cfg['packages']['bytedance-mini-game']['appid'],'current-app')
        self.assertEqual(cfg['scenes'],self.scenes)

    def test_bad_boolean_scene_uuid_or_start_refused(self):
        original = copy.deepcopy(self.options)
        for key, value in [('debug','false'), ('debug',0), ('sourceMaps','false'), ('startScene','other'), ('scenes',[]), ('buildPath','db://bad'), ('outputName','../outside')]:
            with self.subTest(key=key,value=value):
                self.options=copy.deepcopy(original);self.options[key]=value;self.save()
                with self.assertRaises(ValueError):F.write_build_config_3x(self.p,'bytedance-mini-game')
                self.assertFalse(F.config_path_3x(self.p,'bytedance-mini-game').exists())
        self.options=original;self.options['scenes'][0]['uuid']='wrong';self.save()
        with self.assertRaisesRegex(ValueError,'UUID'):F.build_config_3x(self.p,'bytedance-mini-game')

    def test_malformed_json_refused(self):
        for text in ('[]','{bad'):
            self.saved.write_text(text)
            with self.assertRaises(ValueError):F.write_build_config_3x(self.p,'bytedance-mini-game')

    def test_no_guess_when_several_scenes_without_start(self):
        self.saved.unlink()
        with self.assertRaisesRegex(ValueError,'startScene'):F.build_config_3x(self.p,'bytedance-mini-game')

    def test_discovery_read_only_and_steps_include_preparation(self):
        editor={'version':'3.6.2','exe':'/fake/Creator'}
        with mock.patch.object(F,'installed_editors',return_value=[editor]):
            r=F.report(self.p,platform='darwin',sandbox_probe=False)
        self.assertFalse((self.p/'docs').exists())
        cmd=r['commands']['bytedance-mini-game']
        self.assertEqual(len(cmd['steps']),4)
        self.assertEqual(cmd['steps'][1],cmd['prepare_argv'])
        self.assertNotIn('debug=false',cmd['argv'][4])
        self.assertEqual(cmd['native_dir'],str(self.p/'out/custom'))
        self.assertIn('configPath=',cmd['argv'][4])

    def test_stale_generated_config_not_used_to_predict_new_output(self):
        path=F.write_build_config_3x(self.p,'bytedance-mini-game')
        self.options['outputName']='next';self.save()
        argv=F.build_argv({'exe':'Creator'},self.p,3,'bytedance-mini-game')
        self.assertEqual(F.native_dir(argv,self.p,3),(self.p/'out/next',None))
        self.assertEqual(json.loads(path.read_text())['outputName'],'custom')

    @unittest.skipIf(sys.platform=='win32','POSIX execution')
    def test_bad_preparation_stops_fake_build(self):
        marker=self.p/'started'
        fake=self.p/'fake.py';fake.write_text('from pathlib import Path;Path('+repr(str(marker))+').touch()')
        self.options['debug']='false';self.save()
        command=F.configured_chain(None,F.config_prepare_argv(self.p,'bytedance-mini-game'),[sys.executable,str(fake)],None,'darwin',3)
        p=subprocess.run(['/bin/sh','-c',command],capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertFalse(marker.exists())

    def test_external_config_bad_output_types_are_explicitly_refused(self):
        path=self.p/'external.json'
        for key,value in [('buildPath',1),('outputName',[]),('outputName','../bad')]:
            path.write_text(json.dumps(dict({'platform':'bytedance-mini-game'},**{key:value})))
            folder,why=F.native_dir(['Creator','--build','platform=bytedance-mini-game;configPath='+str(path)],self.p,3)
            self.assertIsNone(folder);self.assertTrue(why)

    def test_2x_command_unchanged(self):
        argv=F.build_argv({'exe':'Creator'},self.p,2,'bytedance-mini-game')
        self.assertEqual(argv[1],'--path');self.assertEqual(argv[4],'platform=bytedance;debug=false')
        with self.assertRaisesRegex(ValueError,'3.x'):
            (self.p/'package.json').unlink();(self.p/'project.json').write_text('{"version":"2.4.15"}')
            F.write_build_config_3x(self.p,'bytedance-mini-game')

if __name__=='__main__':unittest.main()
