#!/usr/bin/env python3
"""import_audio.py (生成时预防方案 P15): a library sound lands in the game together with its credits.csv row and usage
record; a 4.9 s fail sound is cut to <= 2 s with a fade-out, a 3 s win / reward / level-end sound is not (R4E);
refused files write nothing. The negative control is the
old way (copy the file by hand): the package gate audit_audio_sources.py fails it, and passes the same sound brought in
by import_audio.py. Library, sounds (WAV made here with the wave module) and project are in a temp folder; nothing of
the machine's own audio library is read. Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_import_audio.py"""
import contextlib
import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_audio_sources as A  # noqa: E402
import import_audio as I  # noqa: E402

INDEX_COLUMNS = ['path', 'source', 'pack', 'name', 'kind', 'license', 'attribution', 'author', 'url', 'file_sha256', 'audio_id']


def make_wav(path, seconds, rate=8000, freq=440.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(seconds * rate)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b''.join(struct.pack('<h', int(12000 * math.sin(2 * math.pi * freq * i / rate))) for i in range(n)))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class ImportAudio(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='p15_import_'))
        self.lib = self.tmp / 'Lib'
        self.rows = {}
        for i, (name, secs, lic) in enumerate([('click.wav', 0.2, 'CC0'), ('lose_long.wav', 4.9, 'CC0 1.0'),
                                               ('win_fanfare.wav', 3.0, 'Kenney CC0'), ('nc.wav', 0.3, 'CC BY-NC 4.0'),
                                               ('by.wav', 0.3, 'CC-BY 4.0'), ('pop.wav', 0.25, 'CC0'),
                                               ('reward_get.wav', 3.0, 'CC0'), ('level_end.wav', 3.2, 'CC0'),
                                               ('lose_reward.wav', 3.0, 'CC0')]):
            p = self.lib / 'raw/kenney/pack_a' / name
            make_wav(p, secs, freq=300 + 50 * i)
            self.rows[name] = {'path': str(p), 'source': 'kenney', 'pack': 'pack_a', 'name': p.stem, 'kind': 'sfx',
                               'license': lic, 'attribution': 'yes' if 'BY' in lic else 'no', 'author': 'Kenney',
                               'url': 'https://example.org/' + name, 'file_sha256': sha(p), 'audio_id': 'pcm:%d' % i}
        with (self.lib / 'index.csv').open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, INDEX_COLUMNS)
            w.writeheader()
            w.writerows(self.rows.values())
        (self.lib / 'usage').mkdir()
        self.project = self.tmp / '！自制游戏' / 'ToyBridge（自制）' / 'game'
        (self.project / 'assets/resources').mkdir(parents=True)
        (self.project / 'docs').mkdir()
        (self.project / 'docs/board.txt').write_text('remake\n', encoding='utf-8')
        self.env = mock.patch.dict(os.environ, {'GAME_AUDIO_LIB': str(self.lib)})
        self.env.start()
        self.policy = mock.patch.object(A, 'decide_policy', return_value=('new', 'test: new game'), create=True)
        self.policy.start()
        # the gate skips usage records of Skill self-test folders; when TMPDIR is one of them the fixture must still count
        self.skip = mock.patch.object(A, 'SKIP_USAGE', re.compile(r'(?!)'))
        self.skip.start()

    def tearDown(self):
        self.skip.stop()
        self.policy.stop()
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def imp(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = I.main(['--project', str(self.project)] + list(args))
        return code, json.loads(buf.getvalue().strip().splitlines()[-1])

    def credits(self):
        f = self.project / 'docs/audio/credits.csv'
        if not f.is_file():
            return []
        with f.open(newline='', encoding='utf-8-sig') as h:
            return list(csv.DictReader(h))

    def audit(self):
        out = self.tmp / ('report_%d.json' % len(list(self.tmp.glob('report_*.json'))))
        argv = ['audit_audio_sources.py', '--project', str(self.project), '--out', str(out)]
        with mock.patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
            code = A.main()
        return code, json.loads(out.read_text(encoding='utf-8'))

    def used_by(self, project, *names):
        key = hashlib.sha256(project.encode()).hexdigest()
        (self.lib / 'usage' / (key + '.json')).write_text(json.dumps(
            {'schema': 2, 'project': project, 'paths': [self.rows[n]['path'] for n in names],
             'asset_ids': [self.rows[n]['audio_id'] for n in names]}), encoding='utf-8')

    def test_import_writes_credits_with_matching_hash_and_usage(self):
        code, out = self.imp('--file', self.rows['click.wav']['path'], '--as', 'sfx_click.wav')
        self.assertEqual(code, 0, out)
        game_file = self.project / 'assets/resources/audio/sfx_click.wav'
        self.assertTrue(game_file.is_file())
        rows = [r for r in self.credits() if r['outputs'] == 'assets/resources/audio/sfx_click.wav']
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r['output_sha256'], sha(game_file))
        self.assertEqual(r['source_sha256'], self.rows['click.wav']['file_sha256'])
        self.assertEqual(r['library_path'], self.rows['click.wav']['path'])
        self.assertEqual((r['license'], r['attribution_required'], r['author']), ('CC0', 'no', 'Kenney'))
        self.assertEqual(sha(game_file), sha(self.rows['click.wav']['path']), 'a non-fail sound is copied byte for byte')
        usage = list((self.lib / 'usage').glob('*.json'))
        self.assertEqual(len(usage), 1)
        rec = json.loads(usage[0].read_text(encoding='utf-8'))
        self.assertIn(self.rows['click.wav']['path'], rec['paths'])
        self.assertIn('pcm:0', rec['asset_ids'])
        code, report = self.audit()
        self.assertEqual(code, 0, report)

    def test_negative_control_hand_copy_fails_the_gate(self):
        dest = self.project / 'assets/resources/audio/sfx_click.wav'
        dest.parent.mkdir(parents=True)
        shutil.copy(self.rows['click.wav']['path'], dest)          # the old way: copy, record later (or never)
        code, report = self.audit()
        self.assertEqual(code, 1, 'the gate must fail a sound copied in without a record')
        self.assertEqual(report['failed'], 1)

    def test_fail_sound_cut_to_two_seconds_with_fade(self):
        self.assertAlmostEqual(I.wav_seconds(Path(self.rows['lose_long.wav']['path'])), 4.9, places=2)
        code, out = self.imp('--file', self.rows['lose_long.wav']['path'], '--file', self.rows['lose_reward.wav']['path'])
        self.assertEqual(code, 0, out)
        for name in ('lose_long.wav', 'lose_reward.wav'):   # a fail word wins over a reward word
            f = self.project / 'assets/resources/audio' / name
            secs = I.wav_seconds(f)
            self.assertLessEqual(secs, 2.0 + 1e-6, name)
            self.assertGreater(secs, 1.9, name)
            with wave.open(str(f), 'rb') as w:
                frames = w.readframes(w.getnframes())
            tail = struct.unpack('<%dh' % 40, frames[-80:])
            self.assertLess(max(abs(x) for x in tail), 200, '%s does not fade out' % name)
            row = [r for r in self.credits() if r['outputs'].endswith(name)][0]
            self.assertEqual(row['output_sha256'], sha(f))
            self.assertIn('fail sound cut %s s -> 2.00 s' % ('4.90' if name == 'lose_long.wav' else '3.00'), row['notes'])
            self.assertEqual(row['type'], 'jingle')
        self.assertEqual(self.audit()[0], 0)

    def test_result_reward_end_sounds_are_not_cut(self):
        # R4E (Saul): only fail / lose sounds are cut to 2 s; win, reward and level-end sounds keep their length.
        names = ('win_fanfare.wav', 'reward_get.wav', 'level_end.wav')
        code, out = self.imp(*sum((['--file', self.rows[n]['path']] for n in names), []))
        self.assertEqual(code, 0, out)
        for name in names:
            f = self.project / 'assets/resources/audio' / name
            self.assertEqual(sha(f), sha(self.rows[name]['path']), '%s was changed (cut) on import' % name)
            self.assertGreaterEqual(I.wav_seconds(f), 2.9, name)
            row = [r for r in self.credits() if r['outputs'].endswith(name)][0]
            self.assertEqual(row['type'], 'jingle', name)
            self.assertNotIn('cut', row['notes'], name)
        code, out = self.imp('--file', self.rows['pop.wav']['path'], '--as', 'tap_pop.wav', '--result')
        self.assertEqual(code, 0, out)
        self.assertEqual(sha(self.project / 'assets/resources/audio/tap_pop.wav'), sha(self.rows['pop.wav']['path']))
        self.assertEqual(self.audit()[0], 0)

    def test_refused_licences_write_nothing(self):
        code, out = self.imp('--file', self.rows['click.wav']['path'], '--file', self.rows['nc.wav']['path'],
                             '--file', self.rows['by.wav']['path'])
        self.assertEqual(code, 1)
        self.assertEqual(len(out['problems']), 2, out)
        self.assertFalse((self.project / 'assets/resources/audio').exists(), 'a refused run copied files')
        self.assertEqual(self.credits(), [])
        self.assertEqual(list((self.lib / 'usage').glob('*.json')), [])

    def test_file_not_in_library_is_refused(self):
        stray = self.tmp / 'Downloads' / 'random.wav'
        make_wav(stray, 0.2)
        code, out = self.imp('--file', str(stray))
        self.assertEqual(code, 1)
        self.assertIn('not in', out['problems'][0])

    def test_reuse_warns_for_one_game_refuses_for_two(self):
        base = str(self.tmp / '！自制游戏')
        self.used_by(base + '/OtherAlpha（自制）/game', 'pop.wav')
        code, out = self.imp('--file', self.rows['pop.wav']['path'], '--no-usage')
        self.assertEqual(code, 0, out)
        self.assertEqual(len(out['warnings']), 1)
        self.assertEqual(list((self.lib / 'usage').glob('*.json')).__len__(), 1, '--no-usage wrote a record')
        self.used_by(base + '/OtherBravo（自制）/game', 'pop.wav')
        (self.project / 'assets/resources/audio/pop.wav').unlink()
        code, out = self.imp('--file', self.rows['pop.wav']['path'])
        self.assertEqual(code, 1, out)
        self.assertIn('2 other games', out['problems'][0])
        self.assertFalse((self.project / 'assets/resources/audio/pop.wav').exists())

    def test_reimport_keeps_other_rows_and_replaces_its_own(self):
        (self.project / 'docs/audio').mkdir(parents=True)
        with (self.project / 'docs/audio/credits.csv').open('w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['outputs', 'license', 'author', 'source_url'])
            w.writerow(['assets/resources/music/bgm.mp3', 'CC0', 'Someone', 'https://example.org/bgm'])
        self.imp('--file', self.rows['click.wav']['path'])
        self.imp('--file', self.rows['click.wav']['path'])
        rows = self.credits()
        self.assertEqual([r['outputs'] for r in rows], ['assets/resources/music/bgm.mp3', 'assets/resources/audio/click.wav'])
        self.assertEqual(rows[0]['source_url'], 'https://example.org/bgm')

    @unittest.skipUnless(I.pkg_audio.find_ffmpeg(), 'ffmpeg not on this machine')
    def test_ogg_fail_sound_cut_by_ffmpeg(self):
        ff = I.pkg_audio.find_ffmpeg()
        src = self.lib / 'raw/kenney/pack_a/gameover_long.ogg'
        import subprocess
        subprocess.run([ff, '-nostdin', '-loglevel', 'error', '-y', '-i', self.rows['lose_long.wav']['path'], str(src)], check=True)
        row = dict(self.rows['click.wav'], path=str(src), name='gameover_long', file_sha256=sha(src), audio_id='pcm:ogg')
        with (self.lib / 'index.csv').open('a', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, INDEX_COLUMNS).writerow(row)
        code, out = self.imp('--file', str(src))
        self.assertEqual(code, 0, out)
        secs = I.ffmpeg_seconds(ff, self.project / 'assets/resources/audio/gameover_long.ogg')
        self.assertLessEqual(secs, 2.05)

    def test_no_machine_paths_in_the_script(self):
        text = (HERE / 'import_audio.py').read_text(encoding='utf-8')
        for bad in ('/Users/', 'GameAudioLibrary"', "GameAudioLibrary'", '/opt/homebrew', 'C:\\\\'):
            self.assertNotIn(bad, text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
