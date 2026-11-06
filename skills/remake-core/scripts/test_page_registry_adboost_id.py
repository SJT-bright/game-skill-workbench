#!/usr/bin/env python3
"""R4L4 (lead, 11-05): pages.json can list the ad-boost board pages as "ad-boost:<board>".

Old way: the page id rule ^[A-Za-z][A-Za-z0-9_.-]{0,60}$ refused the colon, so the id the lead fixed for AdBoostKit
pages ("ad-boost:wheel", R4J2) could never be written into pages.json: validate() failed, make exited 1, and the
merge-dumps warning for those pages could never go away (广告skill found it while making ad-boost v1.2.20).
OLD_SCRIPTS=<base-tree remake-core/scripts> runs this file against the old scripts.
  python3 -B test_page_registry_adboost_id.py
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
pr = importlib.import_module('page_registry')

PAGES = {'schema': 'pages.v1',
         'required_viewports': [{'name': 'iphone14', 'width': 390, 'height': 844},
                                {'name': 'iphone-se', 'width': 375, 'height': 667}],
         'no_ad_roles': {'revive': 'no fail state'},
         'pages': [{'id': 'home', 'name': 'Home', 'kind': 'home', 'node': 'Canvas/Home',
                    'buttons': [{'id': 'play', 'node': 'Canvas/Home/btn_play', 'label': 'PLAY', 'to': 'level'}]},
                   {'id': 'level', 'name': 'Level', 'kind': 'gameplay', 'pause': 'Canvas/Level/HUD/btn_pause'},
                   {'id': 'ad-boost:wheel', 'name': 'Wheel', 'kind': 'popup', 'close': 'Canvas/AdBoostWheel/btn_close'}]}


def with_id(pid):
    doc = json.loads(json.dumps(PAGES))
    doc['pages'][2]['id'] = pid
    return doc


class AdBoostPageId(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / 'docs' / 'logic').mkdir(parents=True)
        (self.dir / 'docs' / 'test').mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, doc):
        (self.dir / 'docs' / 'logic' / 'pages.json').write_text(json.dumps(doc), encoding='utf-8')

    def test_validate_accepts_ad_boost_board_page(self):
        self.assertEqual([e for e in pr.validate(PAGES) if 'id must be' in e], [])

    def test_other_colons_still_refused(self):
        for bad in ('shop:big', 'ad-boost:', 'ad-boost:1wheel', 'x:ad-boost:wheel', 'ad-boost:wheel:2'):
            self.assertTrue(any('id must be' in e for e in pr.validate(with_id(bad))), bad)

    def test_plain_ids_unchanged(self):
        for ok in ('result', 'shop.big', 'level_2', 'pause-menu'):
            self.assertEqual([e for e in pr.validate(with_id(ok)) if 'id must be' in e], [], ok)

    def test_make_cli_passes_and_check_passes(self):
        self.write(PAGES)
        run = lambda *a: subprocess.run([sys.executable, '-B', str(HERE / 'page_registry.py'), *a, '--project', str(self.dir)],
                                        capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
        made = run('make')
        self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
        checked = run('check')
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_listed_board_page_counts_as_seen_without_warning(self):
        self.write(PAGES)
        (self.dir / 'docs' / 'test' / 'iphone14-ui-dump-1.json').write_text(
            json.dumps({'pages': [{'id': 'home'}, {'id': 'ad-boost:wheel'}]}), encoding='utf-8')
        r = pr.merge_dumps(self.dir, self.dir / 'docs' / 'test')
        self.assertEqual(r['status'], 'passed', r)
        self.assertIn('ad-boost:wheel', r['seen'])
        self.assertFalse(r.get('warnings'), r)


if __name__ == '__main__':
    unittest.main(verbosity=2)
