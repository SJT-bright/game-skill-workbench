#!/usr/bin/env python3
"""v7.9 (手机才出的五类问题): wiring of the suites resume_play, ad_outcome, save_restart, image_stall and the runner fixes
that came with them, without a browser (fake ego-browser of test_runtime_regression.py).

- the four sidecars load, apply to every TikTok package (ad_outcome only with ad_entries) and their adapter blocks are
  known adapter keys;
- any lower-case na_field name works: {"n/a": reason} passes without a browser, a missing block refuses a new game and
  warns on a legacy one, a malformed n/a refuses;
- the host server must serve THIS package: a port where another server answers is skipped (_start_host);
- every suite page runs without the HTTP cache (lib.mjs open(), ad_regression/cases.mjs);
- both hosts have adhide=1 (a rewarded video sends the game to the background), the 3.x host __simHide / __simShow.
v7.9 手机检查补全 (Saul 11-04「全部补上，老游戏先不管」):
- a sidecar's "after" orders the run and hands the suite the evidence of those suites (CFG.prior) and the package facts
  (CFG.facts.rewarded_ads); ad_outcome applies to every package with rewarded ads and runs after button_sweep and
  resume_play;
- the finger that never lifts is a real mouse press without release (2.x) / the 3.x host's holdTouch; both hosts log
  lifecycle and ad-result rows the same way, switch the ad result at run time (__setAdPolicy), stall / fail pictures
  (imghang / imgfail) and read storage like a phone (missing / numbool);
- the suites look for what the adapter left out (pause control, in-level ad, ad entries), legacy games do not.
Browser half: 补丁_手机检查补全_基于简化11.7/测试记录.md. Before that, the browser half is proven on real packages (补丁_手机才出的五类问题_给v7.9/测试记录.md: 甜点消消乐 R47 refused / R48
passes resume_play and ad_outcome, SorensRivet r21 refused / r22 passes save_restart, Holly's Hay Hop v6 passes and
射击高手 v86 shows empty platform entries in image_stall).
Run: python3 -B test_phone_suites.py
"""
import functools
import http.server
import shutil
import stat
import subprocess
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
import urllib.request

import runtime_regression as rr
from test_runtime_regression import Base, SIDECAR

HERE = Path(__file__).resolve().parent
RT = HERE / 'runtime_regression'
NEW = ('resume_play', 'ad_outcome', 'save_restart', 'image_stall')


class Sidecars(unittest.TestCase):
    def test_load_and_required(self):
        cat = rr.load_suites()
        for name in ('resume_play', 'save_restart', 'image_stall'):
            self.assertEqual((cat[name]['applies'], cat[name]['na_field']), (['tiktok'], name))
            self.assertIn(name, rr.required_suites({'game.js': b'x'}, {}, cat))
        self.assertEqual(cat['resume_play']['needs_new'], ['resume_play'])
        self.assertEqual(cat['save_restart']['needs_new'], ['save_restart'])
        self.assertEqual(cat['image_stall']['needs_new'], [])          # optional block: the entries are found on screen
        self.assertEqual(cat['image_stall']['uncovered'], {})          # v7.9 手机检查补全: 3.x runs (legacy 3.x warns in the suite)
        # v7.9 手机检查补全: every package with rewarded ads, entries from ad_entries / resume_play.ad / button_sweep
        ao = cat['ad_outcome']
        self.assertEqual((ao['applies'], ao['needs'], ao['needs_new'], ao['na_field'], ao['after']),
                         (['rewarded_ads', 'adapter:ad_entries'], [], [], 'ad_outcome', ['button_sweep', 'resume_play']))
        self.assertNotIn('ad_outcome', rr.required_suites({'game.js': b'x'}, {}, cat))
        self.assertIn('ad_outcome', rr.required_suites({'game.js': b'x'}, {'ad_entries': []}, cat))
        self.assertIn('ad_outcome', rr.required_suites({'game.js': b'x', 'main.js': b'tt.createRewardedVideoAd({})'}, {}, cat))
        self.assertEqual(cat['resume_play']['after'], ['button_sweep'])
        keys = rr.adapter_keys(cat)
        for name in NEW:
            self.assertIn(name, keys)

    def test_scripts_parse(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        for path in [RT / 'phone.mjs'] + [RT / 'suites' / (n + '.mjs') for n in NEW]:
            r = subprocess.run([node, '--check', str(path)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, (path.name, r.stderr[-400:]))

    def test_no_game_names_in_suites(self):
        """甜点消消乐 / 射击高手 / SorensRivet node names belong in adapters, never in the suites."""
        for name in NEW:
            code = '\n'.join(l for l in (RT / 'suites' / (name + '.mjs')).read_text(encoding='utf-8').splitlines()
                             if not l.lstrip().startswith('//'))
            for word in ('GameView', 'pauseParent', 'downMenu', 'homeDisplay', 'diamondCounter', 'ResourcePanel', 'Canvas/Screen'):
                self.assertNotIn(word, code, (name, word))


FAKE_PRIOR = '''
import json, sys
from urllib.parse import unquote, urlparse
code = sys.argv[sys.argv.index('-e') + 1]
entry = unquote(urlparse(json.loads(code[len('await import('):-1])).path)
cfg = json.loads(open(entry, encoding='utf-8').read().split('\\n', 1)[0][len('globalThis.CFG = '):-1])
ev = {'suite': cfg['suite'], 'prior': cfg.get('prior'), 'facts': cfg.get('facts')}
open(cfg['resultFile'], 'w').write(json.dumps({'suite': cfg['suite'], 'passed': True, 'cases': [{'id': 'ok', 'passed': True, 'detail': None}],
                                               'warnings': [], 'evidence': ev, 'fatal': None}))
'''


class AfterPrior(Base):
    """v7.9 手机检查补全: a sidecar's "after" runs it after those suites and hands it their evidence (CFG.prior), plus
    what the package bytes say (CFG.facts): resume_play / ad_outcome use the ad entries and popups button_sweep found."""
    def fake_prior(self):
        browser = self.root / 'ego-browser'
        browser.write_text('#!%s\n%s' % (sys.executable, FAKE_PRIOR))
        browser.chmod(browser.stat().st_mode | stat.S_IEXEC)
        (self.suites / 'fake.json').unlink()
        (self.suites / 'fake.mjs').unlink()
        base = {'about': 'x', 'applies': ['tiktok'], 'needs': [], 'engines': ['2.x', '3.x'], 'timeout_s': 60}
        self.sidecar('aa_late', {**base, 'name': 'aa_late', 'after': ['zz_first']})
        self.sidecar('zz_first', {**base, 'name': 'zz_first'})

    def test_order_and_prior(self):
        self.fake_prior()
        summary = self.run_fake({'home': 'return true'}, suites=['aa_late', 'zz_first'])
        self.assertEqual([r['suite'] for r in summary['suites']], ['zz_first', 'aa_late'])
        first, late = summary['suites'][0]['evidence'], summary['suites'][1]['evidence']
        self.assertEqual(first['prior'], {})
        self.assertEqual(late['prior']['zz_first']['suite'], 'zz_first')
        self.assertEqual(late['facts'], {'rewarded_ads': False})
        (self.package / 'main.js').write_text('tt.createRewardedVideoAd({adUnitId: "x"})')
        self.assertEqual(self.run_fake({'home': 'return true'}, suites=['aa_late'])['suites'][0]['evidence'],
                         {'suite': 'aa_late', 'prior': {}, 'facts': {'rewarded_ads': True}})

    def test_ordered_keeps_the_order_and_survives_a_cycle(self):
        self.assertEqual(rr.ordered(['a', 'b'], {'a': {'after': ['b']}, 'b': {}}), ['b', 'a'])
        self.assertEqual(rr.ordered(['c', 'a', 'b'], {'a': {'after': ['b']}, 'b': {'after': ['a']}, 'c': {}}), ['c', 'a', 'b'])
        self.assertEqual(rr.ordered(['a', 'x'], {'a': {'after': ['zz']}, 'x': {}}), ['a', 'x'])   # not in the run: ignored
        cat = rr.load_suites()
        names = rr.ordered(sorted(cat), cat)
        self.assertLess(names.index('button_sweep'), names.index('resume_play'))
        self.assertLess(names.index('resume_play'), names.index('ad_outcome'))

    def test_after_must_name_other_suites(self):
        self.sidecar('fake', {**SIDECAR, 'after': ['fake']})
        with self.assertRaisesRegex(rr.RuntimeRefused, '"after" must be a list of other suite names'):
            rr.load_suites(self.suites)


class AdRoles(Base):
    """v7.9 手机问题源头约束: a new game lists its result-page x2 (role double) and revive (role revive) in ad_entries;
    refused before any browser opens. Legacy games, ad_outcome {"n/a"} and ad_outcome.none.<role> pass."""
    ENTRY = {'id': 'x', 'button': 'Canvas/b', 'states': [{'name': 's'}]}

    def test_rule(self):
        self.assertEqual(len(rr.ad_roles_problems({})), 1)
        self.assertIn('role "double"', rr.ad_roles_problems({})[0])
        self.assertIn('role "revive"', rr.ad_roles_problems({})[0])
        both = {'ad_entries': [dict(self.ENTRY, role='double'), dict(self.ENTRY, id='y', role='revive')]}
        self.assertEqual(rr.ad_roles_problems(both), [])
        one = {'ad_entries': [dict(self.ENTRY, role='revive')]}
        self.assertIn('ad_outcome.none.double', rr.ad_roles_problems(one)[0])
        self.assertEqual(rr.ad_roles_problems(dict(one, ad_outcome={'none': {'double': 'no level end: an endless runner'}})), [])
        self.assertEqual(rr.ad_roles_problems({'ad_outcome': {'n/a': 'no rewarded ad a player can start'}}), [])
        self.assertIn('ad_outcome.none must map', rr.ad_roles_problems(dict(one, ad_outcome={'none': {'double': ' '}}))[0])
        self.assertIn('ad_outcome.none must map', rr.ad_roles_problems(dict(one, ad_outcome={'none': {'shop': 'x'}}))[0])

    def test_refused_before_the_browser_for_a_new_game_only(self):
        (self.suites / 'fake.json').unlink()
        (self.suites / 'fake.mjs').unlink()
        self.sidecar('ad_outcome', {**SIDECAR, 'name': 'ad_outcome', 'needs': [], 'na_field': 'ad_outcome',
                                    'fields': ['fake_mode', 'ad_entries']})
        with self.assertRaisesRegex(rr.RuntimeRefused, 'before the browser.*ad_outcome: adapter.ad_entries lists no'):
            self.run_fake({'home': 'return true'}, policy='new')
        self.assertTrue(self.run_fake({'home': 'return true'}, policy='legacy')['passed'])
        good = {'home': 'return true', 'ad_entries': [dict(self.ENTRY, role='double'), dict(self.ENTRY, id='y', role='revive')]}
        self.assertTrue(self.run_fake(good, policy='new')['passed'])


class PhoneParts(unittest.TestCase):
    """v7.9 手机检查补全: the pieces the browser half stands on, as text (the browser half: 测试记录.md)."""
    def test_finger_that_never_lifts(self):
        p = (RT / 'phone.mjs').read_text(encoding='utf-8')
        body = p[p.index('export async function fingerHold'):p.index('// The pause popup the game may show')]
        self.assertIn("type: 'mousePressed'", body)          # 2.x host: a real press, the host's touch id 0
        self.assertNotIn('mouseReleased', body)               # ... that never lifts
        self.assertIn('window.__H.holdTouch', p)              # 3.x host hook
        h3 = (RT / 'host3x' / 'host.js').read_text(encoding='utf-8')
        self.assertIn('X.holdTouch = (x, y, id) =>', h3)

    def test_hosts_speak_the_same_way(self):
        h2 = (HERE / 'ad_regression' / 'host.js').read_text(encoding='utf-8')
        h3 = (RT / 'host3x' / 'host.js').read_text(encoding='utf-8')
        self.assertIn("matches('imgfail', v)", h2)
        for s in ("hit('imghang')", "hit('imgfail')", 'window.__setAdPolicy = (p) =>', "else if (k === 'lifecycle') beacon('lifecycle', s);",
                  "beacon('ad-result', { unit, result: mode === 'complete' ? 'complete' : 'cancel' })", "const m = Q.get('missing');",
                  "nb === 'all' || r === 0 || r === 1"):
            self.assertIn(s, h3)
        self.assertIn('window.__setAdPolicy = function (p)', h2)

    def test_suites_find_what_the_adapter_left_out(self):
        rp = (RT / 'suites' / 'resume_play.mjs').read_text(encoding='utf-8')
        for s in ('P.findPause(page)', 'P.priorAdEntries()', "{ warnSkip: 'no pause_button given", 'const LEGACY = POLICY === \'legacy\''):
            self.assertIn(s, rp)
        ao = (RT / 'suites' / 'ad_outcome.mjs').read_text(encoding='utf-8')
        for s in ("from: 'button_sweep'", "id: 'resume_play.ad'", "await adTap(page, en, 'cancel')", "await adTap(page, en, 'complete')",
                  "if (POLICY === 'legacy') return { list: A.ad_outcome ? list : list.filter(e => e.role === 'revive')"):
            self.assertIn(s, ao)
        sr = (RT / 'suites' / 'save_restart.mjs').read_text(encoding='utf-8')
        self.assertIn("const KINDS = ['level', 'buy', 'claim', 'other'];", sr)
        bs = (RT / 'suites' / 'button_sweep.mjs').read_text(encoding='utf-8')
        self.assertIn('all: p.buttons.map((n) => ({ path: n.path, sig: (n.sig ||', bs)
        im = (RT / 'suites' / 'image_stall.mjs').read_text(encoding='utf-8')
        self.assertIn('e.shared = e.files.filter', im)


class AnyNaField(Base):
    def rp(self):
        self.sidecar('rp', {**SIDECAR, 'name': 'rp', 'needs': [], 'needs_new': ['resume_play'], 'na_field': 'resume_play',
                            'fields': ['fake_mode']})
        (self.suites / 'fake.json').unlink()
        (self.suites / 'fake.mjs').unlink()

    def test_na_passes_without_the_browser(self):
        self.rp()
        summary = self.run_fake({'home': 'return true', 'resume_play': {'n/a': 'no level: a idle clicker with one screen'}})
        row = summary['suites'][0]
        self.assertTrue(summary['passed'])
        self.assertEqual((row['cases'][0]['id'], row['browser']), ('n_a', False))

    def test_missing_refuses_new_warns_legacy_and_bad_na_refuses(self):
        self.rp()
        with self.assertRaisesRegex(rr.RuntimeRefused, 'rp/adapter: adapter has no "resume_play"'):
            self.run_fake({'home': 'return true'}, policy='new')
        summary = self.run_fake({'home': 'return true'}, policy='legacy')
        self.assertTrue(summary['passed'])
        self.assertTrue(any('legacy game: warning' in w for w in summary['warnings']), summary['warnings'])
        for bad, why in (({'n/a': ' '}, 'needs the reason'), ({'n/a': 'x', 'start': []}, 'no other keys'), ([], 'must be an object')):
            with self.assertRaisesRegex(rr.RuntimeRefused, why):
                self.run_fake({'home': 'return true', 'resume_play': bad}, policy='new')

    def test_complete_block_runs_the_suite(self):
        self.rp()
        summary = self.run_fake({'home': 'return true', 'resume_play': {'start': [{'tap': 'Canvas/play'}], 'probe': {'tap': 'x'}, 'state_js': 'return 1'}})
        self.assertTrue(summary['passed'])
        self.assertTrue(summary['suites'][0]['cases'][0]['passed'])

    def test_na_field_name_must_be_a_field_name(self):
        self.sidecar('fake', {**SIDECAR, 'na_field': 'Bad Name'})
        with self.assertRaisesRegex(rr.RuntimeRefused, 'na_field'):
            rr.load_suites(self.suites)
        self.assertEqual(rr.field_shape('popin'), rr.popin_problems)
        self.assertEqual(rr.field_shape('save_restart')({'steps': []}), [])


class StartHost(Base):
    def test_a_port_serving_another_package_is_skipped(self):
        other = self.root / 'other'
        other.mkdir()
        (other / 'game.js').write_text('OTHER GAME')
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(other)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        busy = server.server_address[1]
        real = rr._free_port
        ports = iter([busy])
        try:
            with patch.object(rr, '_free_port', side_effect=lambda: next(ports, None) or real()):
                port, proc = rr._start_host(rr.HOST2, self.package, self.root / 'log.jsonl')
            try:
                self.assertNotEqual(port, busy)
                self.assertEqual(urllib.request.urlopen('http://127.0.0.1:%d/game.js' % port, timeout=5).read(), b'GAME')
            finally:
                proc.terminate()
                proc.wait(timeout=5)
        finally:
            server.shutdown()
            server.server_close()


class PageAndHost(unittest.TestCase):
    def test_suite_pages_run_without_the_http_cache(self):
        for path in (RT / 'lib.mjs', HERE / 'ad_regression' / 'cases.mjs'):
            self.assertIn("Network.setCacheDisabled', { cacheDisabled: true }", path.read_text(encoding='utf-8'), path.name)

    def test_hosts_send_the_game_to_the_background_during_an_ad(self):
        h2 = (HERE / 'ad_regression' / 'host.js').read_text(encoding='utf-8')
        self.assertIn("Q.get('adhide') === '1'", h2)
        self.assertIn("function playing() { if (adHide && !rec.finished) { rec.hid = true; setHidden(true); } }", h2)
        h3 = (RT / 'host3x' / 'host.js').read_text(encoding='utf-8')
        self.assertIn("Q.get('adhide') === '1'", h3)
        self.assertIn('window.__simHide = X.hide; window.__simShow = X.show;', h3)


if __name__ == '__main__':
    unittest.main()
