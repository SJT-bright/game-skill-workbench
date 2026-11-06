#!/usr/bin/env python3
"""11.17 R4Q7 items 2 and 3 (合成进化恐龙, rollout 02-23-05 :638).

Item 3: pages.json adapter_js was changed and make run again, but qa/ad-regression.json kept the old hand-written
request (page_registry used setdefault) and said nothing. Now make warns adapter_body_drift, and --force-body takes the
pages.json body.
Item 2: the adapter request still clicked with node.emit('click'), which a GameUIKit button() / wrapExisting() button
never hears (it listens to TOUCH_END and takes the old click events off). In a project with GameUIKit, make refuses it
under policy new and warns under legacy.
OLD_SCRIPTS=<base-tree remake-core/scripts> runs this file against the old scripts.
  python3 -B test_r4q7_page_registry_adapter.py
"""
import importlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(os.environ.get('OLD_SCRIPTS') or Path(__file__).resolve().parent)
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
pr = importlib.import_module('page_registry')

PAGES = {'schema': 'pages.v1',
         'no_ad_roles': {'revive': 'no fail state'},
         'adapter_js': {'request': "window.__qa.tapX2(); // new body"},
         'pages': [{'id': 'home', 'name': 'Home', 'kind': 'home', 'node': 'Canvas/Home'},
                   {'id': 'ad-boost:wheel', 'name': 'Wheel', 'kind': 'popup', 'close': 'Canvas/Wheel/btn_close'},
                   {'id': 'level', 'name': 'Level', 'kind': 'gameplay', 'pause': 'Canvas/Level/HUD/btn_pause'}]}
OLD_REQUEST = "cc.find('Canvas/Result/btn_x2').emit('click');"


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / 'docs' / 'logic').mkdir(parents=True)
        (self.dir / 'qa').mkdir()
        (self.dir / 'docs' / 'logic' / 'pages.json').write_text(json.dumps(PAGES), encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def old_adapter(self, request):
        (self.dir / 'qa' / 'ad-regression.json').write_text(json.dumps({'request': request}), encoding='utf-8')

    def request_of(self, outputs):
        return json.loads(outputs['qa/ad-regression.json'])['request']


class BodyDrift(Base):
    def test_drift_is_reported(self):
        self.old_adapter("window.__qa.tapX2Old();")
        outputs, report = pr.build(self.dir)
        self.assertTrue(report.get('passed'), report)
        self.assertEqual(report.get('adapter_body_drift'), ['request'])
        self.assertEqual(self.request_of(outputs), "window.__qa.tapX2Old();")   # default keeps the hand-written body
        self.assertTrue(any('--force-body' in w for w in report.get('warnings', [])))

    def test_force_body_takes_pages_json(self):
        self.old_adapter("window.__qa.tapX2Old();")
        outputs, report = pr.build(self.dir, force_body=True)
        self.assertTrue(report.get('passed'), report)
        self.assertEqual(self.request_of(outputs), PAGES['adapter_js']['request'])
        self.assertNotIn('adapter_body_drift', report)
        self.assertEqual(pr.main(['make', '--project', str(self.dir), '--force-body']), 0)

    def test_no_drift_no_warning(self):
        outputs, report = pr.build(self.dir)
        self.assertTrue(report.get('passed'), report)
        self.assertNotIn('adapter_body_drift', report)


class EmitClick(Base):
    def with_uikit(self):
        (self.dir / 'assets' / 'scripts' / 'kit').mkdir(parents=True)
        (self.dir / 'assets' / 'scripts' / 'kit' / 'GameUIKit.js').write_text('// kit', encoding='utf-8')

    def test_emit_click_refused_when_gameuikit(self):
        self.with_uikit()
        self.old_adapter(OLD_REQUEST)
        outputs, report = pr.build(self.dir)
        self.assertFalse(report.get('passed'), report)
        self.assertTrue(any('TOUCH_END' in p for p in report.get('problems', [])), report)
        self.assertEqual(outputs, {})

    def test_emit_click_only_warns_for_legacy(self):
        self.with_uikit()
        self.old_adapter(OLD_REQUEST)
        _outputs, report = pr.build(self.dir, policy='legacy')
        self.assertTrue(any('TOUCH_END' in w for w in report.get('warnings', [])), report)

    def test_emit_click_without_gameuikit_untouched(self):
        self.old_adapter(OLD_REQUEST)
        _outputs, report = pr.build(self.dir)
        self.assertTrue(report.get('passed'), report)

    def test_r4l4_ad_boost_page_id_still_valid(self):
        self.assertEqual(pr.validate(PAGES), [])


if __name__ == '__main__':
    unittest.main()
