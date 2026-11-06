#!/usr/bin/env python3
"""R4J2 批: `game_capabilities.py write --merge` and the one home gift box role word.

The ad-boost recorder (record_ad_entries.py) had to call make() itself because the `write` command line
  - dropped the states of an entry already in the record (page_registry.py make writes them),
  - kept only the last of two buttons with the same role (`--ad-entry spin=A --ad-entry spin=B` -> B),
  - refused when the record had no pause key (--pause-button / --no-pause-button required).
And the home gift box role was home_gift in the code but home_reward in runtime-regression.md.
OLD_SCRIPTS=<base-tree remake-core/scripts> runs this file against the old script: every test fails there.
  python3 -B test_capabilities_write_merge.py
"""
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(os.environ.get('OLD_SCRIPTS') or Path(__file__).resolve().parent)
TOOL = HERE / 'game_capabilities.py'
sys.path.insert(0, str(HERE))

# what page_registry.py make writes for a level game (entry with states, no pause key recorded yet)
OLD_RECORD = {'schema': 'game_capabilities.v1',
              'ad_entries': [{'id': 'x2', 'role': 'double', 'button': 'Canvas/Result/btn_x2',
                              'states': [{'name': 'win_level', 'why': 'result page', 'actions': [{'tap': 'Canvas/Win'}]}]},
                             {'id': 'revive', 'role': 'revive', 'button': 'Canvas/Revive/btn_ad',
                              'states': [{'name': 'after_fail', 'why': 'fail by itself'}]}],
              'no_ad_roles': {'spin': 'no wheel yet'},
              'evidence': {'pages': 'docs/page_registry.json'},
              'written_by': 'page_registry.py make'}


class WriteMerge(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / 'docs').mkdir()
        self.rec = self.dir / 'docs' / 'game_capabilities.json'
        self.rec.write_text(json.dumps(OLD_RECORD), encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_write(self, *extra):
        return subprocess.run([sys.executable, '-B', str(TOOL), 'write', '--project', str(self.dir)] + list(extra),
                              capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)

    def doc(self):
        return json.loads(self.rec.read_text(encoding='utf-8'))

    def test_states_kept_when_adding_an_entry(self):
        p = self.run_write('--merge', '--ad-entry', 'spin=Canvas/Home/btn_spin')
        self.assertEqual(p.returncode, 0, p.stderr)
        by = {(e['role'], e['button']): e for e in self.doc()['ad_entries']}
        self.assertEqual(by[('double', 'Canvas/Result/btn_x2')]['states'][0]['name'], 'win_level')
        self.assertEqual(by[('revive', 'Canvas/Revive/btn_ad')]['id'], 'revive')
        self.assertIn(('spin', 'Canvas/Home/btn_spin'), by)
        self.assertNotIn('spin', self.doc().get('no_ad_roles') or {})   # the role has an entry now

    def test_second_button_of_a_role_kept(self):
        p = self.run_write('--merge', '--ad-entry', 'spin=Canvas/Home/btn_spin',
                           '--ad-entry', 'spin=Canvas/Wheel/btn_again')
        self.assertEqual(p.returncode, 0, p.stderr)
        spins = [e['button'] for e in self.doc()['ad_entries'] if e['role'] == 'spin']
        self.assertEqual(spins, ['Canvas/Home/btn_spin', 'Canvas/Wheel/btn_again'])

    def test_no_pause_key_in_record_is_not_a_refusal(self):
        p = self.run_write('--merge', '--ad-entry', 'checkin=Canvas/Checkin/btn_x2')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn('pause_button', self.doc())      # still unrecorded, never guessed

    def test_pause_key_recorded_stays(self):
        d = dict(OLD_RECORD, pause_button='Canvas/Level/btn_pause')
        self.rec.write_text(json.dumps(d), encoding='utf-8')
        p = self.run_write('--merge', '--ad-entry', 'spin=Canvas/Home/btn_spin')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.doc()['pause_button'], 'Canvas/Level/btn_pause')

    def test_entry_json_carries_states(self):
        e = {'id': 'spin', 'role': 'spin', 'button': 'Canvas/Home/btn_spin',
             'states': [{'name': 'home', 'why': 'home page', 'actions': []}]}
        p = self.run_write('--merge', '--ad-entry-json', json.dumps(e))
        self.assertEqual(p.returncode, 0, p.stderr)
        got = [x for x in self.doc()['ad_entries'] if x['role'] == 'spin']
        self.assertEqual(got[0]['states'][0]['name'], 'home')
        self.assertEqual(len(self.doc()['ad_entries']), 3)

    def test_without_merge_still_needs_both_fields(self):
        p = self.run_write('--ad-entry', 'spin=Canvas/Home/btn_spin')
        self.assertEqual(p.returncode, 2)
        self.assertEqual(self.doc()['ad_entries'], OLD_RECORD['ad_entries'])   # nothing written

    def test_same_role_twice_without_merge_keeps_both(self):
        p = self.run_write('--no-pause-button', 'endless, no pause key', '--ad-entry', 'spin=A', '--ad-entry', 'spin=B')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual([e['button'] for e in self.doc()['ad_entries'] if e['role'] == 'spin'], ['A', 'B'])


class HomeGiftRole(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / 'docs').mkdir()
        self.gc = importlib.import_module('game_capabilities')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_home_reward_record_reads_as_home_gift(self):
        rec = {'schema': 'game_capabilities.v1', 'ad_entries': [{'role': 'home_reward', 'button': 'Canvas/Home/gift'}],
               'written_by': 'hand'}
        (self.dir / 'docs' / 'game_capabilities.json').write_text(json.dumps(rec), encoding='utf-8')
        caps = self.gc.load(self.dir)
        self.assertEqual(self.gc.verdict(caps, 'ad_role:home_gift')[0], 'yes')
        self.assertEqual(self.gc.verdict(caps, 'ad_role:home_reward')[0], 'yes')   # the old word still asks right

    def test_write_uses_home_gift(self):
        doc = self.gc.make('P', [{'role': 'home_reward', 'button': 'Canvas/Home/gift'}], {'home_reward': 'x'})
        self.assertEqual(doc['ad_entries'][0]['role'], 'home_gift')
        self.assertEqual(list(doc['no_ad_roles']), ['home_gift'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
