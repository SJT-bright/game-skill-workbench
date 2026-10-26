#!/usr/bin/env python3
"""Isolated identity/cache/classification contracts; never reads a real audio library."""
from __future__ import annotations

import ast
import csv
import hashlib
import importlib.util
import math
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('index_under_test', HERE / 'build_index.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
BASE_SCORE_AST_SHA256 = '4092a81fbcd048f1422dc2671631f8e1da3cf0b8fe6798f1600a362731a94855'
METRICS = dict(duration=12.0, lufs=-20.0, peak_db=-3.0, lead_silence=0.0,
               clip=0, sample_rate=44100, channels=1, bitrate_kbps=705)


class IndexIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raw = self.root / 'raw'
        self.raw.mkdir()
        self.index = self.root / 'index.csv'
        self.credits = self.root / 'credits_master.csv'
        self.patches = [patch.object(b, 'RAW', self.raw), patch.object(b, 'INDEX', self.index),
                        patch.object(b, 'CREDITS_MASTER', self.credits), patch.object(b, 'THEME_PACKS', {})]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def asset(self, name='sound.wav', data=b'audio-a', pack='fixture'):
        path = self.raw / 'fixture-source' / pack / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def read(self):
        with self.index.open(newline='') as stream:
            return list(csv.DictReader(stream))

    def run_stub(self, **kwargs):
        with patch.object(b, 'analyze', return_value=dict(METRICS)) as analyze, \
             patch.object(b, 'decoded_audio_id', return_value='pcm-sha256:' + 'a' * 64) as pcm:
            result = b.build_index(workers=1, **kwargs)
            return result, analyze.call_count, pcm.call_count

    def test_original_score_ast_and_rejecting_controls(self):
        tree = ast.parse((HERE / 'build_index.py').read_text())
        score = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'score')
        digest = hashlib.sha256(ast.dump(score, include_attributes=False).encode()).hexdigest()
        self.assertEqual(digest, BASE_SCORE_AST_SHA256)
        normal = dict(METRICS, path='x.wav', tags='', license='CC0')
        self.assertEqual(b.score(normal), (100, ''))
        self.assertEqual(b.score(dict(normal, duration=0.01))[0], 0)
        self.assertEqual(b.score(dict(normal, license='unknown'))[0], 50)
        self.assertIn('削波', b.score(dict(normal, clip=20))[1])
        self.assertIn('风格偏暗', b.score(dict(normal, tags='dark'))[1])

    def test_byte_cache_reuses_analysis_and_pcm_but_refreshes_metadata(self):
        path = self.asset()
        b.THEME_PACKS['fixture'] = {'kind': 'sfx', 'themes': ['kitchen']}
        first, a1, p1 = self.run_stub()
        self.assertEqual((first['analyzed'], a1, p1), (1, 1, 1))
        with patch.object(b, 'analyze', side_effect=AssertionError('redundant analyze')), \
             patch.object(b, 'decoded_audio_id', side_effect=AssertionError('redundant PCM')):
            b.THEME_PACKS['fixture']['assets'] = {'sound.wav': {'title': 'Pan', 'family_id': 'pan-hit', 'themes': ['cooking'], 'tags': ['place']}}
            second = b.build_index(workers=1)
        row = self.read()[0]
        self.assertEqual((second['reused'], row['kind'], row['name'], row['family_id'], row['themes']), (1, 'sfx', 'Pan', 'pan-hit', 'cooking'))
        self.assertEqual(row['file_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertIn('place', row['tags'])
        self.assertNotIn('kitchen', row['tags'])

    def test_same_second_mtime_changed_bytes_invalidates_cache(self):
        path = self.asset(data=b'first')
        self.run_stub()
        timestamp = path.stat().st_mtime
        path.write_bytes(b'other')
        os.utime(path, (timestamp, timestamp))
        result, analysis, pcm = self.run_stub()
        self.assertEqual((result['analyzed'], analysis, pcm), (1, 1, 1))
        self.assertEqual(self.read()[0]['file_sha256'], hashlib.sha256(b'other').hexdigest())

    def test_manifest_kind_keeps_long_foley_and_ambience_out_of_music(self):
        for pack in ['wood_metal', 'metal_dark', 'music_metal', 'ambience', 'music']:
            self.asset('loop.wav', pack=pack)
        b.THEME_PACKS.update({
            'wood_metal': {'kind': 'sfx'}, 'metal_dark': {'kind': 'sfx'},
            'music_metal': {'kind': 'bgm'}, 'ambience': {'kind': 'ambience'}, 'music': {'kind': 'bgm'}})
        self.run_stub()
        rows = {r['pack']: r for r in self.read()}
        self.assertEqual(rows['wood_metal']['kind'], 'sfx')
        self.assertEqual(rows['ambience']['kind'], 'ambience')
        self.assertEqual(rows['music']['kind'], 'bgm')
        self.assertNotIn('dark', rows['wood_metal']['tags'])
        self.assertIn('dark', rows['metal_dark']['tags'])
        self.assertIn('dark', rows['music_metal']['tags'])
        for duration in [0.02, 1, 2.5, 3, 10]:
            self.assertEqual(b.declared_kind(duration, 'music', 'bgm'), b.kind_of(duration, 'music'))

    def test_legacy_csv_long_foley_and_jingle_preview_keep_declared_kind(self):
        self.assertEqual(b.LEGACY_PACK_KINDS["kenney_impact"], "sfx")
        self.assertEqual(b.LEGACY_PACK_KINDS["kenney_jingles"], "jingle")
        self.asset('foley-preview.wav', pack='kenney_impact')
        self.asset('preview.wav', pack='kenney_jingles')
        self.run_stub()
        rows = {row['pack']: row for row in self.read()}
        self.assertEqual(rows['kenney_impact']['kind'], 'sfx')
        self.assertEqual(rows['kenney_jingles']['kind'], 'jingle')
        # Explicit current manifest overrides the old declaration.
        b.THEME_PACKS['kenney_impact'] = {'kind': 'ambience'}
        self.run_stub()
        rows = {row['pack']: row for row in self.read()}
        self.assertEqual(rows['kenney_impact']['kind'], 'ambience')

    def test_decode_failure_does_not_forge_pcm_identity(self):
        path = self.asset(data=b'not audio')
        with patch.object(b, 'analyze', side_effect=ValueError('bad input')), \
             patch.object(b, 'decoded_audio_id', side_effect=ValueError('decode failed')):
            result = b.build_index(workers=1)
        row = self.read()[0]
        self.assertEqual(row['audio_id'], '')
        self.assertEqual(row['file_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(row['quality'], '0')
        self.assertEqual(result['analysis_failures'], 1)
        self.assertIn('decode failed', row['issues'])
        retry, a, p = self.run_stub()
        self.assertEqual((retry['analyzed'], a, p), (1, 1, 1))

    def test_index_and_credits_concurrent_updates_are_not_overwritten(self):
        self.asset()
        for target in [self.index, self.credits]:
            with self.subTest(target=target.name):
                self.index.unlink(missing_ok=True)
                self.credits.unlink(missing_ok=True)
                def change(_):
                    target.write_bytes(b'concurrent edit\n')
                    return dict(METRICS)
                with patch.object(b, 'analyze', side_effect=change), \
                     patch.object(b, 'decoded_audio_id', return_value='pcm-sha256:' + 'a' * 64):
                    with self.assertRaisesRegex(RuntimeError, 'changed during indexing'):
                        b.build_index(workers=1)
                self.assertEqual(target.read_bytes(), b'concurrent edit\n')
                self.assertEqual(list(self.root.glob('.index-*.csv')), [])

    def test_source_change_during_analysis_is_rejected(self):
        path = self.asset()
        def change(_):
            path.write_bytes(b'new audio bytes')
            return dict(METRICS)
        with patch.object(b, 'analyze', side_effect=change), \
             patch.object(b, 'decoded_audio_id', return_value='pcm-sha256:' + 'a' * 64):
            with self.assertRaisesRegex(RuntimeError, 'source changed'):
                b.build_index(workers=1)
        self.assertFalse(self.index.exists())

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg unavailable; no automatic install in tests')
    def test_lossless_formats_have_same_real_decoded_pcm_identity(self):
        wav = self.asset('tone.wav', data=b'')
        with wave.open(str(wav), 'wb') as stream:
            stream.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
            stream.writeframes(b''.join(struct.pack('<h', int(10000 * math.sin(2 * math.pi * 440 * i / 22050))) for i in range(11025)))
        flac = wav.with_suffix('.flac')
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', str(wav), str(flac)], check=True, capture_output=True)
        self.assertNotEqual(b.file_sha256(wav), b.file_sha256(flac))
        self.assertEqual(b.decoded_audio_id(wav), b.decoded_audio_id(flac))
        self.assertTrue(b.decoded_audio_id(wav).startswith('pcm-sha256:'))
        broken = self.asset('broken.wav', data=b'not audio')
        with self.assertRaisesRegex(ValueError, 'decode/hash failed'):
            b.decoded_audio_id(broken)


if __name__ == '__main__':
    unittest.main(verbosity=2)
