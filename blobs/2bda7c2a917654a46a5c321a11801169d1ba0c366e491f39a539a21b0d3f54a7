#!/usr/bin/env python3
"""R4J2 (lead decision 11-05): ad_entries of two writers are joined by (role, button), and merge-dumps only warns for
unlisted ad-boost board pages.

Old way: R4H merge() replaced the whole ad_entries field with the later writer's list, so the board entries ad-boost
record_ad_entries.py wrote (spin, booster_refill ...) were gone after the next `page_registry.py make` or `write`.
And an AdBoostKit popup recorded as "ad-boost:<board>" but not yet in pages.json failed merge-dumps outright.
OLD_SCRIPTS=<base-tree remake-core/scripts> runs this file against the old scripts.
  python3 -B test_r4j2_entries_union.py
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
sys.path.insert(0, str(HERE))
gc = importlib.import_module('game_capabilities')

AD_BOOST_RECORD = {'schema': 'game_capabilities.v1', 'pause_button': 'Canvas/Level/HUD/btn_pause',
                   'ad_entries': [{'id': 'result_x2', 'role': 'double', 'button': 'Canvas/Result/btn_x2'},
                                  {'role': 'spin', 'button': 'Canvas/Home/AdBoostWheel/btn_spin'},
                                  {'role': 'booster_refill', 'button': 'Canvas/Level/AdBoostRefill/btn_ad'}],
                   'evidence': {}, 'written_by': 'ad-boost record_ad_entries.py (game_capabilities.make)'}
PAGES = {'schema': 'pages.v1',
         'required_viewports': [{'name': 'iphone14', 'width': 390, 'height': 844},
                                {'name': 'iphone-se', 'width': 375, 'height': 667}],
         'no_ad_roles': {'revive': 'no fail state'},
         'pages': [{'id': 'home', 'name': 'Home', 'kind': 'home', 'node': 'Canvas/Home',
                    'buttons': [{'id': 'play', 'node': 'Canvas/Home/btn_play', 'label': 'PLAY', 'to': 'level'}]},
                   {'id': 'level', 'name': 'Level', 'kind': 'gameplay', 'pause': 'Canvas/Level/HUD/btn_pause'},
                   {'id': 'result', 'name': 'Result', 'kind': 'popup', 'close': 'Canvas/Result/btn_close',
                    'ad_entries': [{'id': 'result_x2', 'role': 'double', 'button': 'Canvas/Result/btn_x2',
                                    'states': [{'name': 'after_win', 'actions': [{'wait_node': 'Canvas/Result/btn_x2'}]}]}]}]}


def roles_buttons(doc):
    return sorted((e['role'], e['button']) for e in doc['ad_entries'])


class Union(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / 'docs' / 'logic').mkdir(parents=True)
        self.rec = self.dir / 'docs' / 'game_capabilities.json'
        self.rec.write_text(json.dumps(AD_BOOST_RECORD), encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_merge_into_keeps_board_entries(self):
        new = gc.make('Canvas/Level/HUD/btn_pause', [{'id': 'result_x2', 'role': 'double', 'button': 'Canvas/Result/btn_x2',
                                                      'states': [{'name': 'after_win'}]}], written_by='page_registry.py make')
        doc, _notes = gc.merge_into(self.dir, new)
        self.assertIn(('spin', 'Canvas/Home/AdBoostWheel/btn_spin'), roles_buttons(doc))
        self.assertIn(('booster_refill', 'Canvas/Level/AdBoostRefill/btn_ad'), roles_buttons(doc))
        x2 = [e for e in doc['ad_entries'] if e['role'] == 'double']
        self.assertEqual(len(x2), 1)                                    # same (role, button): the later one replaces it
        self.assertEqual(x2[0]['states'][0]['name'], 'after_win')

    def test_write_cli_keeps_board_entries(self):
        p = subprocess.run([sys.executable, '-B', str(HERE / 'game_capabilities.py'), 'write', '--project', str(self.dir),
                            '--pause-button', 'Canvas/Level/HUD/btn_pause', '--ad-entry', 'revive=Canvas/Revive/btn_ad'],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = roles_buttons(json.loads(self.rec.read_text(encoding='utf-8')))
        self.assertEqual(len(got), 4, got)
        self.assertIn(('spin', 'Canvas/Home/AdBoostWheel/btn_spin'), got)

    def test_page_registry_make_keeps_board_entries(self):
        (self.dir / 'docs' / 'logic' / 'pages.json').write_text(json.dumps(PAGES), encoding='utf-8')
        pr = importlib.import_module('page_registry')
        outputs, report = pr.build(self.dir)
        self.assertTrue(report.get('passed'), report)
        doc = json.loads(outputs[gc.RECORD.as_posix()])
        self.assertIn(('spin', 'Canvas/Home/AdBoostWheel/btn_spin'), roles_buttons(doc))
        self.assertIn(('booster_refill', 'Canvas/Level/AdBoostRefill/btn_ad'), roles_buttons(doc))
        self.assertEqual([e['states'][0]['name'] for e in doc['ad_entries'] if e['role'] == 'double'], ['after_win'])


class MergeDumpsAdBoost(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / 'docs' / 'logic').mkdir(parents=True)
        (self.dir / 'docs' / 'test').mkdir(parents=True)
        (self.dir / 'docs' / 'logic' / 'pages.json').write_text(json.dumps(PAGES), encoding='utf-8')
        self.pr = importlib.import_module('page_registry')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def dump(self, ids):
        (self.dir / 'docs' / 'test' / 'iphone14-ui-dump-1.json').write_text(
            json.dumps({'pages': [{'id': i} for i in ids]}), encoding='utf-8')
        return self.pr.merge_dumps(self.dir, self.dir / 'docs' / 'test')

    def test_ad_boost_page_warns(self):
        r = self.dump(['home', 'ad-boost:wheel'])
        self.assertEqual(r['status'], 'passed', r)
        self.assertTrue(any('record_ad_entries.py' in w for w in r.get('warnings') or []), r)
        self.assertEqual(r['seen'], ['home'])

    def test_other_unlisted_page_still_fails(self):
        r = self.dump(['home', 'ad-boost:wheel', 'shop'])
        self.assertEqual(r['status'], 'failed', r)
        self.assertEqual(len(r['problems']), 1, r)
        self.assertIn('shop', r['problems'][0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
