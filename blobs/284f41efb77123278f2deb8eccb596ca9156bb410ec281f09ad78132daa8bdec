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
The browser half is proven on real packages (补丁_手机才出的五类问题_给v7.9/测试记录.md: 甜点消消乐 R47 refused / R48
passes resume_play and ad_outcome, SorensRivet r21 refused / r22 passes save_restart, Holly's Hay Hop v6 passes and
射击高手 v86 shows empty platform entries in image_stall).
Run: python3 -B test_phone_suites.py
"""
import functools
import http.server
import shutil
import subprocess
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
        self.assertIn('3.x', cat['image_stall']['uncovered'])
        ao = cat['ad_outcome']
        self.assertEqual((ao['applies'], ao['needs'], ao['needs_new']), (['adapter:ad_entries'], ['ad_entries'], ['ad_outcome']))
        self.assertNotIn('ad_outcome', rr.required_suites({'game.js': b'x'}, {}, cat))
        self.assertIn('ad_outcome', rr.required_suites({'game.js': b'x'}, {'ad_entries': []}, cat))
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
