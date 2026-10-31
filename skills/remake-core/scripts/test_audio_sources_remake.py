#!/usr/bin/env python3
"""v7.8 (总表 H7) audit_audio_sources.py for board remake: a remake keeps no base-game / starter-pack sound, every sound
is found in the audio library's index.csv and needs no attribution, a library sound 2 or more OTHER games used is a
problem (1 other game a warning, one game in several folders counts once), a credits path that is not where the file
is gets reported. board localize keeps the v7.7.5 rules. Synthetic project and library in a temp folder; the library
is given by $GAME_AUDIO_LIB and the board by docs/board.txt, as preflight.py runs it.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_audio_sources_remake.py"""
import contextlib
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_audio_sources as A  # noqa: E402

GAMES = '/Users/someone/Downloads/！自制游戏'
INDEX_COLUMNS = ['path', 'source', 'pack', 'name', 'kind', 'license', 'attribution', 'url', 'file_sha256', 'audio_id']


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='w84_sources_'))
        self.lib = self.tmp / 'GameAudioLibrary'
        self.rows = []
        for i, (name, licence, attribution) in enumerate([('coin.ogg', 'CC0', 'no'), ('click.ogg', 'CC0 1.0', 'no'),
                                                          ('song.ogg', 'CC-BY 4.0', 'yes'),
                                                          ('pop.ogg', 'Mixkit Sound Effects Free License', 'no')]):
            path = self.lib / 'raw/kenney/pack_a' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'library sound %d' % i)
            self.rows.append({'path': str(path), 'source': 'kenney', 'pack': 'pack_a', 'name': path.stem, 'kind': 'sfx',
                              'license': licence, 'attribution': attribution, 'url': 'https://example.org/%s' % name,
                              'file_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                              'audio_id': 'pcm-sha256:%064d' % i})
        with (self.lib / 'index.csv').open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, INDEX_COLUMNS)
            w.writeheader()
            w.writerows(self.rows)
        (self.lib / 'usage').mkdir()
        # the game: under ！自制游戏 like a real one, working copy in a generic folder "game"
        self.project = self.tmp / '！自制游戏' / 'TestToyGame（自制）' / 'game'
        (self.project / 'assets/resources/audio').mkdir(parents=True)
        (self.project / 'docs/audio').mkdir(parents=True)
        (self.project / 'docs/board.txt').write_text('remake\n', encoding='utf-8')
        self.sound = self.project / 'assets/resources/audio/sfx_coin.mp3'
        self.sound.write_bytes(b'processed game sound')
        self.env = mock.patch.dict(os.environ, {'GAME_AUDIO_LIB': str(self.lib)})
        self.env.start()
        self.policy = mock.patch.object(A, 'decide_policy', return_value=('new', 'test: new game'), create=True)
        self.policy.start()

    def tearDown(self):
        self.policy.stop()
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def credits(self, header, *rows):
        with (self.project / 'docs/audio/credits.csv').open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, header)
            w.writeheader()
            w.writerows(rows)

    def credit_for(self, lib_row, outputs='assets/resources/audio/sfx_coin.mp3', licence=None):
        self.credits(['id', 'outputs', 'file', 'source', 'title', 'author', 'license', 'url', 'attribution'],
                     {'id': 'sfx_coin', 'outputs': outputs, 'file': lib_row['path'], 'source': 'kenney/pack_a',
                      'title': lib_row['name'], 'author': 'Kenney', 'license': licence or lib_row['license'],
                      'url': lib_row['url'], 'attribution': lib_row['attribution']})

    def used_by(self, project, *rows):
        name = hashlib.sha256(project.encode()).hexdigest()
        (self.lib / 'usage' / (name + '.json')).write_text(json.dumps(
            {'schema': 2, 'project': project, 'game': Path(project).name, 'paths': [r['path'] for r in rows],
             'asset_ids': [r['audio_id'] for r in rows]}), encoding='utf-8')

    def run_audit(self):
        out = self.tmp / ('report_%d.json' % len(list(self.tmp.glob('report_*.json'))))
        argv = ['audit_audio_sources.py', '--project', str(self.project), '--out', str(out)]
        with mock.patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
            code = A.main()
        return code, json.loads(out.read_text(encoding='utf-8'))


class RemakeRules(Fixture):
    def test_library_sound_unused_passes(self):
        self.credit_for(self.rows[0])
        code, report = self.run_audit()
        self.assertEqual((code, report['failed'], report['warnings']), (0, 0, []))
        self.assertEqual(report['checks'][0]['library_path'], self.rows[0]['path'])

    def test_kept_base_sound_refused_for_remake(self):
        (self.project / 'docs/audio/sources.md').write_text('- sfx_coin.mp3：原游戏自带，CC0\n', encoding='utf-8')
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn('base game', report['checks'][0]['problem'])
        (self.project / 'docs/audio/sources.md').write_text('- sfx_coin.mp3: starter pack (启动包提供)\n', encoding='utf-8')
        self.assertEqual(self.run_audit()[0], 1)

    def test_kept_base_sound_still_allowed_for_localize(self):
        (self.project / 'docs/board.txt').write_text('localize\n', encoding='utf-8')
        (self.project / 'docs/audio/sources.md').write_text('- sfx_coin.mp3：原游戏自带\n', encoding='utf-8')
        code, report = self.run_audit()
        self.assertEqual((code, report['failed']), (0, 0))
        # localize never reads the library: no index.csv is fine
        os.unlink(self.lib / 'index.csv')
        self.assertEqual(self.run_audit()[0], 0)

    def test_no_credits_refused(self):
        code, report = self.run_audit()                      # Pinecone fix1: no docs/audio at all
        self.assertEqual(code, 1)
        self.assertIn('no record', report['checks'][0]['problem'])

    def test_source_not_in_library_refused(self):
        self.credits(['id', 'outputs', 'file', 'source', 'title', 'author', 'license', 'url', 'attribution'],
                     {'id': 'sfx_coin', 'outputs': 'assets/resources/audio/sfx_coin.mp3', 'file': '/elsewhere/x.ogg',
                      'source': 'kenney', 'title': 'x', 'author': 'K', 'license': 'CC0', 'url': 'https://x.invalid/',
                      'attribution': 'no'})
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn('source not found', report['checks'][0]['problem'])

    def test_raw_copy_found_by_sha256(self):
        shutil.copyfile(self.rows[1]['path'], self.sound)
        (self.project / 'docs/audio/sources.md').write_text('- sfx_coin.mp3: Kenney, CC0\n', encoding='utf-8')
        code, report = self.run_audit()
        self.assertEqual(code, 0)
        self.assertEqual(report['checks'][0]['matched_by'], 'game file sha256')

    def test_attribution_needed_refused(self):
        self.credit_for(self.rows[2])                        # CC-BY 4.0, attribution yes
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn('attribution', report['checks'][0]['problem'])

    def test_used_by_two_other_games_refused(self):
        self.credit_for(self.rows[0])
        root = GAMES          # not under TMPDIR: usage under ~/.kiro/crew/scratch is skipped
        self.used_by(root + '/OtherGameAlpha/proj', self.rows[0])
        self.used_by(root + '/！交付游戏/2someone-OtherGameBravo（自制）/OtherGameBravo', self.rows[0])
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn('2 other games', report['checks'][0]['problem'])
        self.assertEqual(report['checks'][0]['used_by_other_games'], ['othergamealpha', 'othergamebravo'])

    def test_used_by_one_other_game_warns_and_own_folders_count_once(self):
        self.credit_for(self.rows[0])
        root = GAMES          # not under TMPDIR: usage under ~/.kiro/crew/scratch is skipped
        self.used_by(root + '/OtherGameAlpha/proj', self.rows[0])
        self.used_by(str(self.project), self.rows[0])                                       # this very project
        self.used_by(root + '/TestToyGame（自制）/音频/选音工程', self.rows[0])              # its audio work folder
        self.used_by(root + '/！交付游戏/TestToyGame（自制）/game', self.rows[0])            # after it moved
        code, report = self.run_audit()
        self.assertEqual((code, report['failed']), (0, 0))
        self.assertEqual(report['checks'][0]['used_by_other_games'], ['othergamealpha'])
        self.assertEqual(len([w for w in report['warnings'] if 'used by 1 other game' in w['warning']]), 1)

    def test_same_decoded_audio_counts_as_use(self):
        self.credit_for(self.rows[0])
        other = dict(self.rows[0], path='/some/other/copy.ogg')          # another file, same decoded audio
        root = GAMES          # not under TMPDIR: usage under ~/.kiro/crew/scratch is skipped
        self.used_by(root + '/OtherGameAlpha/proj', other)
        self.used_by(root + '/OtherGameCharlie/proj', other)
        self.assertEqual(self.run_audit()[0], 1)

    def test_selftest_and_scratch_usage_ignored(self):
        self.credit_for(self.rows[0])
        self.used_by('/Users/x/.kiro/crew/scratch/run-1/OtherGameAlpha', self.rows[0])
        self.used_by('/Users/x/maintenance/release-selftest/fixtures/OtherGameBravo', self.rows[0])
        self.assertEqual(self.run_audit()[1]['warnings'], [])

    def test_credits_path_not_where_the_file_is_warns(self):
        # file moved, credits not updated; plus an outputs entry with no file of that name anywhere
        self.credit_for(self.rows[0], outputs='assets/audio/sfx_coin.mp3;assets/audio/sfx_gone.mp3')
        code, report = self.run_audit()
        self.assertEqual(code, 0)
        by_path = {w['path']: w['warning'] for w in report['warnings']}
        self.assertIn('write the real path', by_path['assets/resources/audio/sfx_coin.mp3'])
        self.assertIn('not in the project', by_path['assets/audio/sfx_gone.mp3'])
        self.assertNotIn('assets/audio/sfx_coin.mp3', by_path)        # one warning per moved file, not two

    def test_legacy_game_gets_warnings(self):
        (self.project / 'docs/audio/sources.md').write_text('- sfx_coin.mp3：原游戏自带\n', encoding='utf-8')
        with mock.patch.object(A, 'decide_policy', return_value=('legacy', 'test: on the list')):
            code, report = self.run_audit()
        self.assertEqual((code, report['failed']), (0, 0))
        self.assertTrue(any('(legacy game)' in w['warning'] for w in report['warnings']))

    def test_no_library_index_refused(self):
        self.credit_for(self.rows[0])
        os.unlink(self.lib / 'index.csv')
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn('no index.csv', report['checks'][0]['problem'])


class CreditsHeaders(Fixture):
    """The 8 credits.csv headers found in the games (2026-10-30) all resolve to the library row."""

    def resolve(self, row):
        lib = A.Library(self.lib)
        return A.resolve_source(lib, row, 'no-such-sha', set())

    def test_every_header_resolves(self):
        r = self.rows[0]
        sha = r['file_sha256']
        cases = {
            'id,outputs,file,source,title,author,license,license_url,url,attribution,changes': {'file': r['path']},
            'id,outputs,file,source,title,author,license,url,attribution': {'file': r['path']},
            'id,outputs,file,...,original_sha256,runtime_sha256': {'file': 'raw/elsewhere.ogg', 'original_sha256': sha},
            'id,outputs,source,pack,name,author,url,license,attribution,original_path': {'original_path': r['path']},
            'id,outputs,source,pack,name (pack + name only)': {'pack': 'pack_a', 'name': 'coin'},
            'outputs,license,author,source_url,license_url': {'source_url': r['url']},
            'title,author,source,source_file,source_sha256,...': {'source_file': 'pack_a/coin.ogg'},
            'id,...,changes,library_path': {'library_path': r['path']},
            'id,event,source,title,...,source_sha256,outputs,sha256': {'source_sha256': sha},
            'title "pack / name"': {'title': 'pack_a / coin'},
        }
        for header, row in cases.items():
            found, how = self.resolve(row)
            self.assertIsNotNone(found, header)
            self.assertEqual(found['path'], r['path'], header)

    def test_file_name_narrowed_by_url(self):
        twin = self.lib / 'raw/other/pack_b/coin.ogg'
        twin.parent.mkdir(parents=True)
        twin.write_bytes(b'twin')
        with (self.lib / 'index.csv').open('a', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, INDEX_COLUMNS).writerow(dict(self.rows[0], path=str(twin), source='other', pack='pack_b',
                                                           url='https://example.org/twin', file_sha256='', audio_id=''))
        found, _ = self.resolve({'file': 'coin.ogg', 'url': 'https://example.org/twin'})
        self.assertEqual(found['path'], str(twin))


class GameKey(unittest.TestCase):
    def test_one_game_many_folders(self):
        root = '/Users/x/Downloads/！自制游戏'
        same = [root + '/新260_MeteorBlaster/proj', root + '/！交付游戏/新260-MeteorBlaster（自制）/MeteorBlaster',
                root + '/启动包工坊/projects/fusion-MeteorBlaster/work']
        self.assertEqual({A.game_key(p) for p in same}, {'meteorblaster'})
        self.assertNotEqual(A.game_key(root + '/1仁木-SimonsScrew（自制）/x'), A.game_key(root + '/1林子健-SorensRivet（自制）'))
        # a Latin person prefix is not the game: two games by "Liar" stay two games
        self.assertEqual(A.game_key(root + '/！交付游戏/1Liar-AdasAmber（自制）/p'), 'adasamber')
        self.assertEqual(A.game_key(root + '/！交付游戏/2Liar-Tavi194（自制）/p'), 'tavi194')
        self.assertEqual(A.game_key(root + '/！交付游戏/2子午-Pinecone（自制）/_work/x'), 'pinecone')
        self.assertEqual(A.game_key(root + '/1全民飞车漂移/DriftRacer3D-English'), '全民飞车漂移')
        self.assertEqual(A.game_key(root + '/新260-MeteorBlaster（自制）/x'), 'meteorblaster')
        self.assertNotEqual(A.game_key(root + '/新游戏_底子全民飞车漂移_待定名/p'), A.game_key(root + '/新游戏_底子我出枪贼快_待定名/p'))
        self.assertEqual(A.game_key(root + '/音乐消消乐/p'), A.game_key(root + '/！交付游戏/1莫慌-音乐消消乐/p'))


if __name__ == '__main__':
    unittest.main()
