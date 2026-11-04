#!/usr/bin/env python3
"""简化.11.3 sound wiring gate package_gates/sound.py (CubeDigits 11-02 audio requirements, step 1).

Fault cases from the requirement list (section 8), each refused for its own reason:
  1  only sliders and saved values, no play wiring          -> S2_sound_no_play_call
  2  audio not in the package / engine audio module off     -> S1_sound_no_audio_files, S3_sound_engine_no_audio
  12 only volume / playing set, no real play call           -> S2_sound_no_play_call
  17 an applicable package tried as a formal package        -> package_gates.run blocks (every writer calls it)
plus: normal package passes, aliased engine play passes, a game without sound controls is not judged, legacy only
warns, board localize is no exemption, an engine moved into a subpackage is still found, a silent-design record that
contradicts sound controls is refused, engine and kit text never count as game controls.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_package_gates_sound.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_gates as gates  # noqa: E402
from package_gates import sound  # noqa: E402

SETTINGS_3X = (b'e.prototype.buildSettings=function(n){this.volume(n,"bgm","Music",135),'
               b'this.volume(n,"sfx","Sound Effects",-35)};this.store=new t.SaveStore({volumes:{sfx:1,bgm:1}});'
               b'e.applyAudioVolumes=function(){this.sounds.forEach(function(s){s.volume=1})};')
PLAY_3X = b'var s=this.node.addComponent(o.AudioSource);s.clip=c;s.loop=!0;s.play();s.playOneShot(k,.5);'
SETTINGS_24 = b'cc.sys.localStorage.setItem("musicVolume",this.musicVolume);this.sfxVolume=.8;'
PLAY_24 = b'cc.audioEngine.playMusic(this.bgm,!0);cc.audioEngine.playEffect(this.click,!1);'
ALIAS_24 = b'this._engine=cc.audioEngine;var s=this._engine.play(e,t,i);'


def pkg(engine=3, code=b'', audio=1, engine_audio=True, extra=None):
    files = {'game.json': json.dumps({'deviceOrientation': 'portrait'}).encode(), 'game.js': b'require("./main")',
             'project.config.json': b'{}'}
    if engine == 3:
        files['cocos-js/cc.js'] = b'/* engine */' + (b' class AudioSource{} cc.AudioSource' if engine_audio else b'')
        files['web-adapter.js'] = b'/* adapter: audio volume muted */'
    else:
        files['cocos2d-js-min.js'] = b'/* engine */' + (b' cc.audioEngine={play:function(){}}' if engine_audio else b'')
        files['adapter-min.js'] = b'/* adapter */'
    files['assets/main/index.js'] = code
    for i in range(audio):
        files['subpackages/audio/native/0%d/0a1b2c3d-0000-4000-8000-00000000000%d.mp3' % (i, i)] = b'ID3 fake'
    files.update(extra or {})
    return files


def ids(files, policy='new', board='remake', context=None):
    view = gates.PackageView(files, board=board, policy=policy, context=context)
    return {f['id']: f['level'] for f in sound.check(view)}


class Faults(unittest.TestCase):
    def test_case1_and_12_sliders_saved_but_nothing_plays(self):
        self.assertEqual(ids(pkg(3, SETTINGS_3X)), {'S2_sound_no_play_call': 'block'})
        self.assertEqual(ids(pkg(2, SETTINGS_24 + b'this.bgm.volume=.5;this.playing=true;')),
                         {'S2_sound_no_play_call': 'block'})

    def test_case2_no_audio_file_in_package(self):
        self.assertEqual(ids(pkg(3, SETTINGS_3X + PLAY_3X, audio=0)), {'S1_sound_no_audio_files': 'block'})
        self.assertEqual(ids(pkg(2, SETTINGS_24 + PLAY_24, audio=0)), {'S1_sound_no_audio_files': 'block'})

    def test_case2_engine_audio_module_switched_off(self):
        self.assertEqual(ids(pkg(3, SETTINGS_3X + PLAY_3X, engine_audio=False)), {'S3_sound_engine_no_audio': 'block'})
        self.assertEqual(ids(pkg(2, SETTINGS_24 + PLAY_24, engine_audio=False)), {'S3_sound_engine_no_audio': 'block'})

    def test_cubedigits_shape_two_reasons(self):
        self.assertEqual(ids(pkg(3, SETTINGS_3X, audio=0, engine_audio=False)),
                         {'S1_sound_no_audio_files': 'block', 'S3_sound_engine_no_audio': 'block'})

    def test_case17_every_writer_entry_refuses(self):
        result = gates.run(pkg(3, SETTINGS_3X, audio=0, engine_audio=False), None, 'localize', policy='new')
        self.assertIn('sound', result['gates'])
        self.assertTrue({'S1_sound_no_audio_files', 'S3_sound_engine_no_audio'} <= {f['id'] for f in result['blocks']})

    def test_silent_record_contradicted(self):
        with tempfile.TemporaryDirectory() as project:
            Path(project, 'docs/audio').mkdir(parents=True)
            Path(project, 'docs/audio/silent_design.md').write_text('silent by design', encoding='utf-8')
            got = ids(pkg(3, SETTINGS_3X + PLAY_3X), context={'writer': True, 'project': project})
            self.assertEqual(got, {'S4_sound_silent_record_contradicted': 'block'})


class Controls(unittest.TestCase):
    def test_normal_package_passes(self):
        self.assertEqual(ids(pkg(3, SETTINGS_3X + PLAY_3X)), {})
        self.assertEqual(ids(pkg(2, SETTINGS_24 + PLAY_24)), {})

    def test_play_through_a_variable_counts(self):
        self.assertEqual(ids(pkg(2, SETTINGS_24 + ALIAS_24)), {})

    def test_scene_audio_source_counts(self):
        scene = {'subpackages/resources/import/ab/abc.json': b'[{"__type__":"cc.AudioSource","_playOnAwake":true}]'}
        self.assertEqual(ids(pkg(3, SETTINGS_3X, extra=scene)), {})

    def test_scene_label_is_a_control(self):
        scene = {'assets/main/import/ab/abc.json': b'[{"__type__":"cc.Label","_string":"Music"}]'}
        self.assertEqual(ids(pkg(3, b'var x=1;', audio=0, extra=scene)), {'S1_sound_no_audio_files': 'block'})

    def test_no_sound_controls_is_not_judged(self):
        self.assertEqual(ids(pkg(3, b'var score=0;', audio=0, engine_audio=False)), {})

    def test_legacy_warns_and_localize_is_no_exemption(self):
        bad = pkg(3, SETTINGS_3X, audio=0)
        self.assertEqual(ids(bad, policy='legacy'), {'S1_sound_no_audio_files': 'warn'})
        self.assertEqual(ids(bad, board='localize'), {'S1_sound_no_audio_files': 'block'})

    def test_engine_and_kit_text_never_count(self):
        files = pkg(3, b'var score=0;', audio=0, extra={
            'subpackages/renderer/cc.js': b'AudioState musicVolume "Music" audioEngine',
            'src/assets/tiktok-platform/RewardedService.plugin.js': b'"sound"',
            'storage-guard.js': b'soundOn', 'tiktok-touch-3x.js': b'"Music"'})
        self.assertEqual(sound.inspect(gates.PackageView(files))['controls'], [])

    def test_engine_in_a_subpackage_is_found(self):
        files = pkg(3, SETTINGS_3X + PLAY_3X, engine_audio=False,
                    extra={'subpackages/renderer/cc.js': b'cc.AudioSource=class AudioSource{}'})
        self.assertEqual(ids(files), {})


if __name__ == '__main__':
    unittest.main()
