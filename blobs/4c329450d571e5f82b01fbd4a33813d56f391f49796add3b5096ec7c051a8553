#!/usr/bin/env python3
"""audio_inventory.py (生成时预防 R4O6, 补查2 第 12 组): the English inventory lists the original game's own sound
entries so they are switched to AudioService at stage 1. Fixtures are cut from 弹球传奇 BallAudioManager.js (2.4,
cc.audioEngine) and 奔跑吧巨人 audioManager.ts (3.x, AudioSource, music / sound keys), plus a one-key switch, a
platform audio object, animation play() calls and comments that must not count, and the kit's own AudioService.
Run: python3 -B test_audio_inventory.py   (well under a second)"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

BALL = """cc.Class({
    playAudio(audioSource, loop, volume, callback) {
        var id = cc.audioEngine.play(audioSource, loop, volume);
        // cc.audioEngine.playEffect(old, false);
        this._anim.play();
    },
    init() {
        this.bgMusicVolume = Number(cc.sys.localStorage.getItem('ballmaster.audio.music.level') || 0.5);
        this.effectMusicVolume = Number(cc.sys.localStorage.getItem('ballmaster.audio.effects.level') || 0.5);
    },
    setMusicVolume(value) { if (id !== undefined) cc.audioEngine.setVolume(id, value); }
});
"""
GIANT = """export class AudioManager {
    getAudioSetting(isMusic: boolean) {
        return isMusic ? StorageManager.instance.getGlobalData('music') : StorageManager.instance.getGlobalData('sound');
    }
    playSound(name: string) { clip.setVolume(this.soundVolume); clip.playOneShot(); }
    playMusic() { audio.clip.play(); }
    /* audio.clip.play(); old */
    openMusic() { StorageManager.instance.setGlobalData('music', 'true'); }
}
"""
DINO = """export class SoundMgr {
    get on() { return sys.localStorage.getItem('Audio') !== '0'; }
    bgm() { this.source.play(); }
    tip() { const ctx = tt.createInnerAudioContext(); ctx.src = 'a.mp3'; ctx.play(); }
}
"""
KIT_AUDIO = "AudioService.prototype.playMusic=function(){cc.audioEngine.playMusic(c,!0)};"
ANIM_ONLY = "cc.Class({ start() { this.getComponent(cc.Animation).play('idle'); this.anim.play(); } });\n"


def project(files):
    root = Path(tempfile.mkdtemp(prefix='audioinv_'))
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    return root


class AudioInventory(unittest.TestCase):
    def setUp(self):
        import audio_inventory
        self.A = audio_inventory
        self.root = project({'assets/script/BallAudioManager.js': BALL, 'assets/script/audioManager.ts': GIANT,
                             'assets/script/SoundMgr.ts': DINO, 'assets/tiktok-platform/AudioService.js': KIT_AUDIO,
                             'assets/script/Hero.js': ANIM_ONLY})
        self.addCleanup(shutil.rmtree, self.root, True)

    def rows(self, kind=None, file=None):
        return [(r['api'], r['line']) for r in self.A.plan(self.root)['audio_todo']
                if (kind is None or r['kind'] == kind) and (file is None or r['file'].endswith(file))]

    def test_ball_master_engine_audio(self):
        self.assertEqual(self.rows('audio_play', 'BallAudioManager.js'), [('cc.audioEngine.play', 3)])
        sw = self.rows('audio_switch', 'BallAudioManager.js')
        self.assertIn(('storage key ballmaster.audio.music.level', 8), sw)
        self.assertIn(('storage key ballmaster.audio.effects.level', 9), sw)
        self.assertIn(('setMusicVolume', 11), sw)

    def test_giant_rush_audio_source_and_keys(self):
        self.assertEqual(self.rows('audio_play', 'audioManager.ts'), [('AudioSource.playOneShot', 5), ('AudioSource.play', 6)])
        sw = self.rows('audio_switch', 'audioManager.ts')
        self.assertIn(('storage key music', 3), sw)
        self.assertIn(('storage key sound', 3), sw)
        self.assertIn(('storage key music', 8), sw)

    def test_one_switch_and_platform_audio(self):
        self.assertEqual(self.rows('audio_platform_api', 'SoundMgr.ts'), [('tt.createInnerAudioContext', 4)])
        self.assertIn(('AudioSource.play', 3), self.rows('audio_play', 'SoundMgr.ts'))
        self.assertNotIn('one_switch_suspect', self.A.plan(self.root)['audio_summary'])  # music and sound keys exist
        one = project({'assets/script/SoundMgr.ts': DINO})
        self.addCleanup(shutil.rmtree, one, True)
        summary = self.A.plan(one)['audio_summary']
        self.assertEqual(summary['switch_keys'], ['Audio'])
        self.assertIn('one_switch_suspect', summary)

    def test_skips_kit_animation_and_comments(self):
        files = {r['file'] for r in self.A.plan(self.root)['audio_todo']}
        self.assertNotIn('assets/tiktok-platform/AudioService.js', files)
        self.assertNotIn('assets/script/Hero.js', files)
        self.assertNotIn(('cc.audioEngine.playEffect', 4), self.rows(file='BallAudioManager.js'))
        self.assertNotIn(('AudioSource.play', 7), self.rows(file='audioManager.ts'))
        for r in self.A.plan(self.root)['audio_todo']:
            self.assertIn('AudioService', r['fix'])

    def test_read_only(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.A.plan(self.root)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_finalize_inventory_carries_audio_todo(self):
        import tiktok_finalize
        inv = tiktok_finalize.inventory(self.root)
        self.assertIn('rewire_todo', inv)
        self.assertEqual(len(inv['audio_todo']), len(self.A.plan(self.root)['audio_todo']))
        self.assertGreater(inv['audio_summary']['play'], 0)
        json.dumps(inv)


if __name__ == '__main__':
    unittest.main()
