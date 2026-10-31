#!/usr/bin/env python3
"""v7.8 (总表 H7, 22.1) audio package gate package_gates/audio.py: loudness (sound effect -16 LUFS, music -20 LUFS,
+-4 LU) and fail-sound length (2 s rule, blocks above 2.5 s) of the audio really in the package, harsh-sound warning,
and ffmpeg missing never passes silently (B18). Bad fixtures are refused for a new game and warned for a legacy game
or a localize package; fixed ones pass. Fixtures are made with ffmpeg (sine tones / white noise brought to an exact
loudness), named the way a Cocos build names them (native/xx/<uuid>.mp3 + bundle config.json).
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_package_gates_audio.py"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_gates as gates  # noqa: E402
from package_gates import audio  # noqa: E402

FFMPEG = audio.find_ffmpeg()
TMP = tempfile.TemporaryDirectory(prefix='w84_audio_gate_')
_MADE = {}


def tone(seconds, lufs, source='sine', freq=440, ext='.mp3'):
    """bytes of an audio file of `seconds` measuring `lufs` integrated loudness (within ~0.5 LU)."""
    key = (seconds, lufs, source, freq, ext)
    if key in _MADE:
        return _MADE[key]
    src = ('sine=frequency=%d:sample_rate=44100:duration=%s' % (freq, seconds) if source == 'sine' else
           'anoisesrc=color=white:sample_rate=44100:amplitude=0.3:duration=%s' % seconds)
    out = Path(TMP.name) / ('%d%s' % (len(_MADE), ext))

    def render(gain_db):
        if out.exists():
            out.unlink()
        subprocess.run([FFMPEG, '-nostdin', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i', src,
                        '-af', 'volume=%.2fdB' % gain_db, '-ac', '1', str(out)], check=True)
        return out.read_bytes()

    data = render(0.0)
    if seconds >= 0.5:
        audio._CACHE.clear()
        measured = audio.measure(FFMPEG, data, ext)['lufs']
        data = render(lufs - measured)
    audio._CACHE.clear()
    _MADE[key] = data
    return data


UUIDS = ['0a1b2c3d-0000-4000-8000-%012d' % i for i in range(20)]


def pkg(sounds, engine=2):
    """sounds: [(asset path, bytes)] -> package files named by uuid, with a bundle config.json naming them."""
    files = {'game.json': json.dumps({'deviceOrientation': 'portrait'}).encode(), 'game.js': b'',
             'project.config.json': b'{}'}
    if engine == 2:
        files['cocos/cocos2d-js-min.js'] = b'/* engine */'
        base, config = 'assets/main/', 'assets/main/config.json'
    else:
        files['cocos-js/cc.js'] = b'/* engine */'
        files['web-adapter.js'] = b'/* adapter */'
        base, config = 'subpackages/bundle/', 'subpackages/bundle/config.json'
    uuids, paths = [], {}
    for index, (name, data) in enumerate(sounds):
        uuid = UUIDS[index]
        uuids.append(uuid)
        paths[str(index)] = [name, 'cc.AudioClip']
        files['%snative/%s/%s.mp3' % (base, uuid[:2], uuid)] = data
    files[config] = json.dumps({'uuids': uuids, 'paths': paths}).encode()
    return files


def found(files, policy='new', board='remake', context=None):
    view = gates.PackageView(files, board=board, policy=policy, context=context)
    out = {}
    for item in audio.check(view):
        out[item['id']] = item['level']
    return out


@unittest.skipUnless(FFMPEG, 'ffmpeg is not installed (the A0 test below still runs)')
class Measured(unittest.TestCase):
    def test_long_fail_sound_refused_new_warned_legacy_and_localize(self):
        bad = pkg([('audio/bgm/jingle_lose', tone(6.0, -16))])          # Pinecone fix2: 6.0 s jingle_lose
        self.assertEqual(found(bad), {'A2_fail_sound_length': 'block'})
        self.assertEqual(found(bad, policy='legacy'), {'A2_fail_sound_length': 'warn'})
        self.assertEqual(found(bad, board='localize'), {'A2_fail_sound_length': 'warn'})
        good = pkg([('audio/bgm/jingle_lose', tone(1.8, -16))])         # 企鹅雪道: cut to 1.8 s
        self.assertEqual(found(good), {})

    def test_fail_names(self):
        for name in ('sfx/GameOver', 'sfx_game_over', 'CatDeath', 'player_die', 'lose', 'pfs_fail', 'defeated'):
            self.assertTrue(audio.is_fail_name(name), name)
        for name in ('sfx_dice', 'closeButton', 'lower', 'sfx_level_start', 'diet', 'bgm_menu', 'jingle_win'):
            self.assertFalse(audio.is_fail_name(name), name)

    def test_time_up_sounds_are_fail_sounds(self):
        # Saul 10-30: a time-up sound ends the round, so it follows the fail-sound rule (2 s with a fade-out)
        for name in ('timeout', 'audio/sfx/timeout', 'sfx_time_out', 'TimeUp', 'times_up', 'jingle_timesup'):
            self.assertTrue(audio.is_fail_name(name), name)
        for name in ('sfx_timer_tick', 'time_bonus', 'sfx_out', 'checkout', 'ui_tap'):
            self.assertFalse(audio.is_fail_name(name), name)
        bad = pkg([('audio/sfx/timeout', tone(3.0, -20))])               # Holly timeout.mp3: 3 s
        self.assertEqual(found(bad), {'A2_fail_sound_length': 'block'})
        self.assertEqual(found(pkg([('audio/sfx/timeout', tone(1.8, -20))])), {})   # a jingle may sit at -20

    def test_3x_bundle_names_too(self):
        bad = pkg([('audio/sfx/game_over', tone(4.0, -16))], engine=3)
        self.assertEqual(found(bad), {'A2_fail_sound_length': 'block'})

    def test_sound_effect_loudness(self):
        self.assertEqual(found(pkg([('audio/sfx/sfx_coin', tone(1.0, -30))])), {'A1_audio_loudness': 'block'})
        self.assertEqual(found(pkg([('audio/sfx/sfx_coin', tone(1.0, -6))])), {'A1_audio_loudness': 'block'})
        self.assertEqual(found(pkg([('audio/sfx/sfx_coin', tone(1.0, -30))]), policy='legacy'),
                         {'A1_audio_loudness': 'warn'})
        self.assertEqual(found(pkg([('audio/sfx/sfx_coin', tone(1.0, -16))])), {})
        self.assertEqual(found(pkg([('audio/sfx/sfx_coin', tone(1.0, -18.5))])), {})       # inside +-4 LU

    def test_short_sounds_not_measured_for_loudness(self):
        self.assertEqual(found(pkg([('audio/sfx/sfx_tick', tone(0.3, -40))])), {})

    def test_music_loudness_by_name_and_by_length(self):
        self.assertEqual(found(pkg([('audio/bgm/bgm_game', tone(20.0, -20))])), {})
        self.assertEqual(found(pkg([('audio/bgm/bgm_game', tone(20.0, -10))])), {'A1_audio_loudness': 'block'})
        self.assertEqual(found(pkg([('audio/forest_ambience', tone(20.0, -20))])), {})      # > 15 s -> music
        # 10 s, name says nothing: a sound effect, so -20 LUFS is 4 LU off (inside), -22 is 6 LU off (outside)
        self.assertEqual(found(pkg([('audio/menu_tune', tone(10.0, -22))])), {'A1_audio_loudness': 'block'})
        self.assertEqual(found(pkg([('audio/bgm_menu_tune', tone(10.0, -22))])), {})        # name says music

    def test_starter_pack_names_music_fail_and_music_win(self):
        # starter packs ship audio/assets/bgm/music_fail.mp3 and music_win.mp3: tunes at the -16 LUFS jingle level
        self.assertEqual(found(pkg([('audio/bgm/music_fail', tone(6.0, -16))])), {'A2_fail_sound_length': 'block'})
        self.assertEqual(found(pkg([('audio/bgm/music_win', tone(3.0, -16))])), {})
        self.assertEqual(found(pkg([('audio/bgm/music_win', tone(1.2, -20.4))])), {})      # 6子午-Cosmos: -20.4
        self.assertEqual(found(pkg([('audio/bgm/music_fail', tone(0.9, -22))])), {})        # 巴扎黑-Lulus: -22.1
        self.assertEqual(found(pkg([('audio/bgm/music_win', tone(1.2, -28))])), {'A1_audio_loudness': 'block'})
        self.assertEqual(found(pkg([('audio/jingle_lose', tone(1.2, -9))])), {'A1_audio_loudness': 'block'})

    def test_writer_project_needs_csv_decides_music(self):
        project = Path(TMP.name) / 'project'
        (project / 'assets/resources/audio').mkdir(parents=True, exist_ok=True)
        (project / 'docs/audio').mkdir(parents=True, exist_ok=True)
        (project / 'assets/resources/audio/menu_tune.mp3').write_bytes(b'x')
        (project / 'assets/resources/audio/menu_tune.mp3.meta').write_text(json.dumps({'uuid': UUIDS[0]}))
        (project / 'docs/audio/needs.csv').write_text('id,type\nmenu_tune,bgm\n')
        (project / 'docs/audio/credits.csv').write_text('id,outputs,license\nmenu_tune,'
                                                        'assets/resources/audio/menu_tune.mp3,CC0\n')
        files = pkg([('audio/menu_tune', tone(10.0, -22))])
        self.assertEqual(found(files), {'A1_audio_loudness': 'block'})
        self.assertEqual(found(files, context={'writer': True, 'project': str(project)}), {})

    def test_harsh_sound_only_warns(self):
        files = pkg([('audio/sfx/sfx_hiss', tone(1.0, -16, source='noise'))])
        self.assertEqual(found(files), {'W_audio_harsh': 'warn'})

    def test_short_clicks_are_not_reported_as_harsh(self):
        # Saul 10-30: button clicks of 0.3 s or less are bright by nature (13 of 18 packages warned before)
        self.assertEqual(found(pkg([('audio/sfx/sfx_click', tone(0.25, -16, source='noise'))])), {})
        self.assertEqual(found(pkg([('audio/sfx/sfx_click', tone(0.6, -16, source='noise'))])),
                         {'W_audio_harsh': 'warn'})

    def test_undecodable_file_warns(self):
        self.assertEqual(found(pkg([('audio/sfx/sfx_coin', b'ID3 not really audio')])), {'W_audio_unmeasured': 'warn'})

    def test_long_sound_without_a_name_warns(self):
        files = pkg([('x', tone(4.0, -16))])
        files = {k: v for k, v in files.items() if not k.endswith('config.json')}
        self.assertEqual(found(files), {'W_audio_unnamed': 'warn'})

    def test_every_package_entry_runs_it(self):
        bad = pkg([('audio/bgm/jingle_lose', tone(6.0, -16))])
        result = gates.run(bad, None, 'remake', policy='new')
        self.assertIn('audio', result['gates'])
        self.assertIn('A2_fail_sound_length', [f['id'] for f in result['blocks']])
        good = pkg([('audio/bgm/jingle_lose', tone(1.8, -16))])
        result = gates.run(good, None, 'remake', policy='new')
        self.assertFalse([f for f in result['blocks'] if f['id'].startswith(('A0', 'A1', 'A2'))])


class Wiring(unittest.TestCase):
    def test_listed_last_in_gate_modules(self):
        self.assertEqual(gates.GATE_MODULES[-1], 'audio')

    def test_no_ffmpeg_never_passes_silently(self):
        files = pkg([('audio/sfx/sfx_coin', b'not measured')])
        with mock.patch.object(audio, 'find_ffmpeg', return_value=None):
            self.assertEqual(found(files), {'A0_ffmpeg_missing': 'block'})
            self.assertEqual(found(files, policy='legacy'), {'A0_ffmpeg_missing': 'warn'})
            self.assertIn('install ffmpeg', [f['message'] for f in audio.check(gates.PackageView(files, policy='new'))]
                          [0].lower())

    def test_package_without_audio_is_quiet(self):
        with mock.patch.object(audio, 'find_ffmpeg', return_value=None):
            self.assertEqual(found(pkg([])), {})


if __name__ == '__main__':
    unittest.main()
