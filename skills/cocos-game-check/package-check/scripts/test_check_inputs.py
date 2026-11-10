#!/usr/bin/env python3
"""P19 (问题普查 20261104: check_inputs_missing 20, checker_input_rejected 29, empty lists skipped): the check inputs are
made from docs/logic/pages.json while the game is made, an empty or missing input is 「未执行」, and report statuses come
from one file. Each case runs in well under a second, no browser:

  pages_*      a fixture pages.json (3 pages, 1 rewarded-ad entry) -> page_registry.py make -> screens.json read by
               art_check.capture_inventory, the adapter read by ad_regression.load_adapter and
               runtime_regression.load_adapter (pause_button and ad_entries filled from the registry)
  empty_*      runtime_regression.run: ad_entries [] (割草) and resume_play.pause_button "" (美人鱼) stop before the
               browser as not_run (exit 2), a new rewarded game with no ad_entries list is not_run instead of a
               silent skip; a legacy game only warns
  writer_*     check_package: no adapter file is status not_run (was failed), not a reusable record
  status_*     grok-image-review: the prompt names the allowed statuses (火锅大逃亡 receipt: model wrote "ok"), the
               receiver reads the same list; check-status.json is the one list
"""
import json
import inspect
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (HERE, ROOT / 'remake-core' / 'scripts', ROOT / 'grok-image-review' / 'scripts'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import check_guard  # noqa: E402
import runtime_regression as rr  # noqa: E402
import ad_regression  # noqa: E402

PAGES = {
    'schema': 'pages.v1',
    'game': 'fixture',
    'required_viewports': [{'name': 'iphone14', 'width': 390, 'height': 844},
                           {'name': 'iphone-se', 'width': 375, 'height': 667}],
    'adapter_js': {'request': "window.__qaAds.show(function(r){if(r&&r.isEnded)grant();});",
                   'ready': 'return !!window.__qaAds;'},
    'pages': [
        {'id': 'home', 'name': '首页', 'kind': 'home', 'node': 'Canvas/Home', 'seen_at_runtime': True,
         'buttons': [{'id': 'play', 'node': 'Canvas/Home/btn_play', 'label': 'PLAY', 'to': 'level'}]},
        {'id': 'level', 'name': '关卡', 'kind': 'gameplay', 'node': 'Canvas/Level', 'seen_at_runtime': True,
         'pause': 'Canvas/Level/HUD/btn_pause',
         'buttons': [{'id': 'win', 'node': 'Canvas/Level/debug_win', 'to': 'result'}]},
        {'id': 'result', 'name': '结算', 'kind': 'popup', 'node': 'Canvas/Result', 'seen_at_runtime': True,
         'close': 'Canvas/Result/btn_close',
         'ad_entries': [{'id': 'result_x2', 'role': 'double', 'button': 'Canvas/Result/btn_x2',
                         'states': [{'name': 'after_win', 'why': 'win a level, then the button',
                                     'actions': [{'tap': 'Canvas/Home/btn_play'}, {'wait_node': 'Canvas/Result/btn_x2'}]}]}]},
    ],
    'no_ad_roles': {'revive': 'no fail state in this fixture'},
}


def project_with(pages):
    tmp = Path(tempfile.mkdtemp(prefix='p19-'))
    (tmp / 'assets').mkdir()
    (tmp / 'docs' / 'logic').mkdir(parents=True)
    if pages is not None:
        (tmp / 'docs' / 'logic' / 'pages.json').write_text(json.dumps(pages, ensure_ascii=False), encoding='utf-8')
    return tmp


class PagesRegistry(unittest.TestCase):
    def make(self, pages=PAGES):
        import page_registry
        proj = project_with(pages)
        outputs, report = page_registry.build(proj)
        if report.get('passed'):
            page_registry.write(proj, outputs)
        return proj, report

    def test_pages_screens_read_by_art_check(self):
        import art_check
        proj, report = self.make()
        self.assertTrue(report['passed'], report)
        inv = art_check.capture_inventory(proj, proj / 'docs' / 'test')
        self.assertEqual([r['id'] for r in inv['listed']], ['home', 'level', 'result'])
        self.assertEqual(len(inv['viewports']), 2)
        bad = [e for e in inv['errors'] if '无有效docs/art/screens.json' in e or '页面清单' in e or '页面项' in e
               or '视口' in e or '至少需要两种' in e]
        self.assertEqual(bad, [], inv['errors'])

    def test_pages_adapter_read_by_both_regressions(self):
        proj, _ = self.make()
        path = proj / 'qa' / 'ad-regression.json'
        ad = ad_regression.load_adapter(path)
        self.assertIn('grant()', ad['request'])
        rt = rr.load_adapter(path)
        self.assertEqual(rt['resume_play']['pause_button'], 'Canvas/Level/HUD/btn_pause')
        self.assertEqual([e['id'] for e in rt['ad_entries']], ['result_x2'])
        self.assertEqual(rt['ad_outcome']['none']['revive'][:19], 'capability record: ')
        caps = json.loads((proj / 'docs' / 'game_capabilities.json').read_text(encoding='utf-8'))
        self.assertEqual(caps['pause_button'], 'Canvas/Level/HUD/btn_pause')
        flows = json.loads((proj / 'docs' / 'logic' / 'flows.json').read_text(encoding='utf-8'))
        self.assertEqual(len(flows['flows']), 20)       # F01-F20 template for a new file
        self.assertIn('P:result:close', [f['id'] for f in flows['page_flows']])

    def test_pages_hand_edit_is_reported(self):
        import page_registry
        proj, _ = self.make()
        self.assertTrue(page_registry.check(proj)['passed'])
        screens = proj / 'docs' / 'art' / 'screens.json'
        screens.write_text(screens.read_text(encoding='utf-8').replace('结算', '结算页'), encoding='utf-8')
        self.assertFalse(page_registry.check(proj)['passed'])

    def test_pages_missing_or_empty_is_not_run(self):
        import page_registry
        for pages in (None, dict(PAGES, pages=[])):
            proj = project_with(pages)
            self.assertEqual(page_registry.main(['make', '--project', str(proj)]), check_guard.NOT_RUN_EXIT)
            self.assertFalse((proj / 'docs' / 'art' / 'screens.json').exists())

    def test_pages_popup_without_close_and_level_without_pause_refused(self):
        import page_registry
        bad = json.loads(json.dumps(PAGES))
        del bad['pages'][2]['close']
        del bad['pages'][1]['pause']
        errs = page_registry.validate(bad)
        self.assertTrue(any('close key' in e for e in errs), errs)
        self.assertTrue(any('pause' in e for e in errs), errs)


def package(rewarded=True):
    tmp = Path(tempfile.mkdtemp(prefix='p19-pkg-'))
    (tmp / 'game.js').write_text("require('./main');" + (" tt.createRewardedVideoAd({});" if rewarded else ''),
                                 encoding='utf-8')
    (tmp / 'main.js').write_text('//', encoding='utf-8')
    return tmp


def adapter_file(doc):
    f = Path(tempfile.mkdtemp(prefix='p19-ad-')) / 'ad-regression.json'
    f.write_text(json.dumps(doc), encoding='utf-8')
    return f


class EmptyInputs(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.saved = rr.touch_problem, rr.find_browser, rr.run_suite
        rr.touch_problem = lambda files: None
        rr.find_browser = lambda: '/bin/true'

        def fake_suite(name, *a, **k):
            self.calls.append(name)
            selected = inspect.signature(self.saved[2]).bind(name, *a, **k).arguments.get('selection') or ['x']
            return {'suite': name, 'passed': True, 'problems': [], 'cases': [{'id': ident, 'passed': True} for ident in selected],
                    'warnings': [], 'evidence': None, 'seconds': 0.0, 'browser': True}
        rr.run_suite = fake_suite

    def tearDown(self):
        rr.touch_problem, rr.find_browser, rr.run_suite = self.saved

    def run_rr(self, adapter, suites, policy='new'):
        adapter = dict({'home': 'return true;', 'play': 'Canvas/Home/btn_play'}, **adapter)   # what startup needs
        return rr.run(package(), adapter_file(adapter), suites, policy=policy, capabilities='')

    def assert_not_run(self, adapter, suites, word):
        with self.assertRaises(rr.RuntimeRefused) as ctx:
            self.run_rr(adapter, suites)
        summary = getattr(ctx.exception, 'summary', {})
        self.assertEqual(summary.get('status'), 'not_run', (str(ctx.exception), summary))
        self.assertIn(word, ' '.join(summary.get('missing', [])))
        self.assertEqual(self.calls, [], 'a suite ran (browser) although an input was empty')

    def test_empty_ad_entries_list_is_not_run(self):
        # 割草: the ad-entry list was there and empty
        self.assert_not_run({'request': 'grant();', 'ad_entries': []}, ['ad_entries'], 'ad_entries')

    def test_empty_pause_button_is_not_run(self):
        # 美人鱼: resume_play written, pause key left empty
        self.assert_not_run({'request': 'grant();', 'resume_play': {'pause_button': ''}}, ['startup'], 'pause_button')

    def test_new_rewarded_game_without_entry_list_is_not_run_not_skipped(self):
        # full run (the writers' way: no --suites) over a one-suite catalog; old: passed, the ad entries never looked at
        suites = Path(tempfile.mkdtemp(prefix='p19-suites-'))
        (suites / 'only.json').write_text(json.dumps({'name': 'only', 'applies': ['tiktok'], 'needs': []}), encoding='utf-8')
        (suites / 'only.mjs').write_text('// fake', encoding='utf-8')
        with self.assertRaises(rr.RuntimeRefused) as ctx:
            rr.run(package(), adapter_file({'request': 'grant();'}), None, suites_dir=suites, policy='new',
                   capabilities='')
        summary = getattr(ctx.exception, 'summary', {})
        self.assertEqual(summary.get('status'), 'not_run', (str(ctx.exception), summary))
        self.assertIn('ad_entries', ' '.join(summary.get('missing', [])))
        self.assertEqual(self.calls, [])

    def test_legacy_game_warns_and_runs(self):
        summary = self.run_rr({'request': 'grant();', 'ad_entries': []}, ['startup'], policy='legacy')
        self.assertTrue(summary['passed'])
        self.assertTrue(any('legacy game: warning' in w for w in summary['warnings']), summary['warnings'])

    def test_cli_exit_2_and_verdict(self):
        f = adapter_file({'request': 'grant();', 'ad_entries': []})
        # tool_identity writes a "modified tools" draft when run from a work tree: keep it in a temp folder
        os.environ['COCOS_SKILL_FEEDBACK_DIR'] = tempfile.mkdtemp(prefix='p19-feedback-')
        try:
            code = rr.main(['run', '--package', str(package()), '--adapter', str(f), '--suites', 'ad_entries',
                            '--policy', 'new'])
        finally:
            os.environ.pop('COCOS_SKILL_FEEDBACK_DIR', None)
        self.assertEqual(code, 2)


class WriterInputs(unittest.TestCase):
    def test_writer_no_adapter_is_not_run(self):
        import check_package
        files = {'game.js': b'tt.createRewardedVideoAd({})'}
        old = os.environ.pop(ad_regression.ENV_ADAPTER, None)
        try:
            out = check_package.writer_regressions(files, package(), adapter=None, policy='new')
        finally:
            if old is not None:
                os.environ[ad_regression.ENV_ADAPTER] = old
        self.assertTrue(out['blocked'])
        self.assertEqual(out['rewarded_ad_regression']['status'], 'not_run', out['rewarded_ad_regression'])
        self.assertEqual(out['runtime_regression']['status'], 'not_run', out['runtime_regression'])
        self.assertIsNone(check_package.regression_record(out['rewarded_ad_regression'], out['runtime_regression']))

    def test_unknown_status_is_not_reused(self):
        import check_package
        good = {'status': 'passed', 'passed': True, 'tool_sha256': 'a', 'adapter_sha256': 'b'}
        self.assertIsNotNone(check_package.regression_record(good, dict(good, required=[])))
        self.assertIsNone(check_package.regression_record(dict(good, status='ok'), good))


class StatusSchema(unittest.TestCase):
    def test_status_prompt_names_receiver_values(self):
        import review
        rule = review.status_rule()
        for v in check_guard.status_values('image_review'):
            self.assertIn(v, rule)
        self.assertEqual(tuple(review.FALLBACK_STATUSES), check_guard.status_values('image_review'))
        ok = review.parse_report('{"status":"pass","observations":["PLAY"],"issues":[],"uncertainties":[]}')
        self.assertEqual(ok['status'], 'pass')
        with self.assertRaises(ValueError) as ctx:     # 火锅大逃亡 evidence/art/play-ocr: the model wrote "ok"
            review.parse_report('{"status":"ok","observations":["PLAY"],"issues":[],"uncertainties":[]}')
        self.assertIn('allowed: pass, issue, uncertain', str(ctx.exception))

    def test_status_one_list(self):
        self.assertIn(check_guard.not_run('t', 'r')['status'], check_guard.status_values())
        self.assertIn('not_run', check_guard.status_values())
        self.assertNotIn('not_run', check_guard.status_passing())

    def test_every_check_package_status_is_listed(self):
        """R4H 批 (Round4 #21): every status word check_package.py writes is in check-status.json (it used to list only
        the regression-record and check_guard words: requires_runtime_evidence, unofficial_not_deliverable, refuse and
        error were nowhere). The new kinds never widen the check values a receiver accepts."""
        import re
        src = (HERE / 'check_package.py').read_text(encoding='utf-8')
        words = set(re.findall(r"""(?:'status':\s*|status=)'([a-z_]+)'""", src))
        listed = set()
        doc = json.loads(check_guard.STATUS_FILE.read_text(encoding='utf-8'))
        for kind, sec in doc.items():
            if isinstance(sec, dict) and 'values' in sec:
                listed |= set(sec['values'])
        self.assertTrue({'requires_runtime_evidence', 'unofficial_not_deliverable', 'refuse', 'error'} <= words, words)
        self.assertEqual(sorted(words - listed), [], 'status words not in check-status.json')
        for k in ('package_cli', 'runtime_requirement', 'tool_identity'):
            self.assertTrue(set(check_guard.status_values(k)).isdisjoint(check_guard.status_passing()), k)
        self.assertEqual(check_guard.status_values(), ('passed', 'failed', 'not_run', 'not_applicable',
                                                       'environment_incomplete'))


class CapabilitiesMerge(unittest.TestCase):
    """R4H 批 (Round4 #21): game_capabilities.py write and page_registry.py make write the same docs/game_capabilities.json.
    Old: the later writer replaced the file, silently dropping what only the first one knew."""

    def caps(self, proj):
        return json.loads((proj / 'docs' / 'game_capabilities.json').read_text(encoding='utf-8'))

    def test_make_after_write_keeps_and_says(self):
        import contextlib, io
        import game_capabilities as g
        import page_registry
        pages = json.loads(json.dumps(PAGES))
        pages.pop('no_ad_roles')
        proj = project_with(pages)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(g.main(['write', '--project', str(proj), '--pause-button', 'Canvas/Level/HUD/btn_pause',
                                     '--no-ad-entries', 'not decided yet', '--no-ad-role', 'revive=no fail state',
                                     '--evidence', 'pause=Level.js:40']), 0)
        outputs, report = page_registry.build(proj)
        self.assertTrue(report['passed'], report)
        page_registry.write(proj, outputs)
        doc = self.caps(proj)
        self.assertEqual(doc.get('no_ad_roles'), {'revive': 'no fail state'}, 'OLD WAY BUG: make dropped no_ad_roles')
        self.assertEqual(doc['evidence'].get('pause'), 'Level.js:40')
        self.assertEqual(doc['ad_entries'][0]['role'], 'double')               # pages.json is the source for ad entries
        self.assertIn('game_capabilities.py write', doc['written_by'])
        self.assertIn('page_registry.py make', doc['written_by'])
        self.assertEqual(g.validate(doc), [])
        said = ' '.join(report.get('capabilities_merged') or [])
        self.assertIn('no_ad_roles', said)
        self.assertIn('ad_entries', said)
        self.assertEqual(page_registry.check(proj)['status'], 'passed')

    def test_write_after_make_keeps_and_says(self):
        import contextlib, io
        import game_capabilities as g
        import page_registry
        proj = project_with(PAGES)
        outputs, report = page_registry.build(proj)
        page_registry.write(proj, outputs)
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(g.main(['write', '--project', str(proj), '--pause-button', 'Canvas/Level/HUD/btn_settings',
                                     '--ad-entry', 'double=Canvas/Result/btn_x2']), 0)
        doc = self.caps(proj)
        self.assertEqual(doc['pause_button'], 'Canvas/Level/HUD/btn_settings')
        self.assertEqual(doc.get('no_ad_roles'), {'revive': 'no fail state in this fixture'},
                         'OLD WAY BUG: write dropped what make wrote')
        self.assertIn('pause_button', err.getvalue())
        self.assertIn('no_ad_roles', err.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=2)
