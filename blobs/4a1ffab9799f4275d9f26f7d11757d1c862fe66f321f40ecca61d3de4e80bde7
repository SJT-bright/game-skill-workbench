#!/usr/bin/env python3
"""Offline source-cache sync contracts using a generated isolated WAV/ZIP fixture.

AUDIO_TEST_STAGE optionally selects an already-verified real source cache.
Every import goes to a TemporaryDirectory; the real audio library is never written.
"""
from __future__ import annotations

import copy
import io
import struct
import wave
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sync_under_test', HERE / 'sync_theme_library.py')
sync_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_module)
import common


def cache_name(entry):
    return hashlib.sha256(entry['url'].encode()).hexdigest()[:20] + Path(unquote(urlparse(entry['url']).path)).suffix


class ThemeSyncCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('AUDIO_TEST_STAGE'):
            stage=Path(os.environ['AUDIO_TEST_STAGE'])
        else:
            # Test-only generated silence is never installed in the real library
            # or described as a downloaded commercial production sound.
            cls.stage_temp=tempfile.TemporaryDirectory(prefix='audio-cache-fixture-')
            cls.addClassCleanup(cls.stage_temp.cleanup)
            stage=Path(cls.stage_temp.name);(stage/'source-cache').mkdir()
            stream=io.BytesIO()
            with wave.open(stream,'wb') as audio:
                audio.setparams((1,2,8000,0,'NONE','not compressed'))
                audio.writeframes(struct.pack('<h',0)*1600)
            packed=io.BytesIO()
            with zipfile.ZipFile(packed,'w') as archive:
                archive.writestr('fixture.wav',stream.getvalue())
            entry={'url':'https://example.invalid/synthetic-test-only.zip','sha256':hashlib.sha256(packed.getvalue()).hexdigest()}
            pack={'key':'synthetic_cache','kind':'sfx','source':'synthetic_test_only','page':'https://example.invalid/test-only','author':'Generated validator fixture','license':'CC0','license_url':'https://creativecommons.org/publicdomain/zero/1.0/','files':[entry]}
            (stage/'source-cache'/cache_name(entry)).write_bytes(packed.getvalue())
            (stage/'new-packs.json').write_text(json.dumps([pack]))
        manifest = stage / 'new-packs.json'
        cache = stage / 'source-cache'
        if not manifest.is_file():
            raise unittest.SkipTest('Explicit AUDIO_TEST_STAGE does not contain the requested local manifest')
        choices = []
        for pack in json.loads(manifest.read_text()):
            if pack.get('kind') != 'sfx' or not pack.get('license', '').startswith('CC0') or len(pack.get('files', [])) != 1:
                continue
            entry = pack['files'][0]
            path = cache / cache_name(entry)
            if path.suffix == '.zip' and path.is_file() and sync_module.digest(path) == entry.get('sha256'):
                choices.append((path.stat().st_size, pack, path))
        if not choices:
            raise unittest.SkipTest('No verified, already-downloaded CC0 SFX ZIP in supplied cache')
        _, cls.original_pack, cls.original_zip = min(choices, key=lambda item: item[0])
        if not shutil.which('ffprobe'):
            raise unittest.SkipTest('ffprobe unavailable; tests never install dependencies')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.lib = self.root / 'GameAudioLibrary'
        self.raw = self.lib / 'raw'
        self.credits = self.lib / 'credits_master.csv'
        self.cache = self.root / 'cache'
        self.cache.mkdir()
        self.pack = copy.deepcopy(self.original_pack)
        self.pack['key'] = 'isolated_cache_contract'
        self.source = self.cache / cache_name(self.pack['files'][0])
        shutil.copy2(self.original_zip, self.source)
        self.patches = [patch.object(sync_module, 'LIB', self.lib), patch.object(sync_module, 'RAW', self.raw),
                        patch.object(common, 'LIB', self.lib), patch.object(common, 'RAW', self.raw),
                        patch.object(common, 'AUTH', self.lib / 'auth'), patch.object(common, 'CREDITS_MASTER', self.credits),
                        patch.dict(os.environ, {'GAME_AUDIO_LIB': str(self.lib)}),
                        patch.object(sync_module.requests, 'get', side_effect=AssertionError('network forbidden in offline contract'))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def run_sync(self):
        return sync_module.sync(self.pack, self.cache, offline=True)

    def target_files(self):
        return sorted(p for p in self.raw.rglob('*') if p.is_file()) if self.raw.exists() else []

    def test_verified_zip_imports_offline_and_consumes_asset_title_page(self):
        with zipfile.ZipFile(self.source) as archive:
            first = next(n for n in archive.namelist() if Path(n).suffix.lower() in common.AUDIO_EXT and not n.endswith('/'))
        self.pack.setdefault('assets', {}).setdefault(Path(first).as_posix(), {}).update(
            title='Verified material impact', page='https://opengameart.org/content/wood-and-metal-sound-effects-volume-2')
        result = self.run_sync()
        self.assertEqual(result['status'], 'downloaded')
        self.assertGreater(result['audio'], 0)
        rows = common.read_csv(self.credits)
        target = self.raw / self.pack['source'] / self.pack['key'] / first
        credit = next(r for r in rows if r['file'] == str(target))
        self.assertEqual(credit['title'], 'Verified material impact')
        self.assertEqual(credit['url'], self.pack['assets'][first]['page'])
        self.assertTrue(all(r['license'].startswith('CC0') for r in rows))
        self.assertTrue(target.is_file())
        self.assertFalse(sync_module.requests.get.called)

    def test_offline_corrupt_source_hash_rejects_before_raw_writes(self):
        self.source.write_bytes(b'corrupt source archive')
        with self.assertRaisesRegex(ValueError, 'Verified source cache missing'):
            self.run_sync()
        self.assertEqual(self.target_files(), [])
        self.assertFalse(sync_module.requests.get.called)

    def test_offline_missing_cache_never_uses_network(self):
        self.source.unlink()
        with self.assertRaisesRegex(ValueError, 'Verified source cache missing'):
            self.run_sync()
        self.assertEqual(self.target_files(), [])
        self.assertFalse(sync_module.requests.get.called)

    def test_online_checksum_mismatch_rejects_before_raw_writes(self):
        self.source.unlink()
        class ChangedSource:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def raise_for_status(self): pass
            def iter_content(self, _): yield b'changed original bytes'
        with patch.object(sync_module.requests, 'get', return_value=ChangedSource()):
            with self.assertRaisesRegex(ValueError, 'Source checksum changed'):
                sync_module.sync(self.pack, self.cache, offline=False)
        self.assertEqual(self.target_files(), [])
        self.assertFalse(self.credits.exists())

    def test_modified_local_audio_is_preserved_and_not_overwritten(self):
        self.run_sync()
        target = next(p for p in self.target_files() if p.suffix.lower() in common.AUDIO_EXT)
        target.write_bytes(b'local user changed this audio')
        with self.assertRaisesRegex(ValueError, 'Local modification preserved'):
            self.run_sync()
        self.assertEqual(target.read_bytes(), b'local user changed this audio')
        self.assertFalse(sync_module.requests.get.called)

    def test_repeated_receipt_repairs_deleted_credits_without_redownloading(self):
        self.run_sync()
        before = common.read_csv(self.credits)
        self.credits.unlink()
        result = self.run_sync()
        self.assertEqual(result['status'], 'reused')
        self.assertEqual(result['credits_repaired'], len(before))
        after = common.read_csv(self.credits)
        self.assertEqual({r['file'] for r in before}, {r['file'] for r in after})
        again = self.run_sync()
        self.assertEqual(again['credits_repaired'], 0)
        self.assertEqual(len(common.read_csv(self.credits)), len(before))
        self.assertFalse(sync_module.requests.get.called)


if __name__ == '__main__':
    unittest.main(verbosity=2)
