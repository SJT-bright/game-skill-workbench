#!/usr/bin/env python3
"""生成时预防 #40 (普查 trial_link_dead 14、stale_preview 10): the home screenshot and the trial smoke play the game
before the link is printed, and the game saves to localStorage of the origin it runs on. They must run on another
port than the printed link (another origin = another localStorage), so the person opening the link gets a fresh save.

No browser: main() runs in-process with the screenshot, smoke, read-back and window launch replaced by recorders.
Old serve_preview.py: the screenshot and smoke URLs carry the user link's port -> fails. New: other port, same pages.
Run: python3 -B test_preview_fresh_save.py   (SERVE_PREVIEW_DIR=<other scripts dir> runs it against another copy)
"""
import io
import os
import shutil
import sys
import tempfile
import types
import unittest
import urllib.request
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(os.environ.get('SERVE_PREVIEW_DIR') or Path(__file__).resolve().parent)
sys.path.insert(0, str(HERE))
import serve_preview  # noqa: E402


def fetch(url):
    with urllib.request.urlopen(url, timeout=5) as answer:
        return answer.read()


class FreshSaveOnUserLink(unittest.TestCase):
    def run_main(self, keep):
        seen = {'shot': None, 'smoke': None, 'same_page': None}
        export = Path(tempfile.mkdtemp(prefix='fresh_save_'))
        (export / 'index.html').write_text('<html><head></head><body><script src="main.js"></script></body></html>')
        (export / 'main.js').write_text('localStorage.setItem("coins","999")')
        project = Path(tempfile.mkdtemp(prefix='fresh_save_proj_'))
        self.addCleanup(shutil.rmtree, export, True)
        self.addCleanup(shutil.rmtree, project, True)

        def shot(shot_url, *a, **k):
            seen['shot'] = shot_url
            seen['same_page'] = fetch(shot_url.split('?')[0].rsplit('/', 1)[0] + '/main.js')
            return 'pass', 'shot ok', {}

        def smoke(url, *a, **k):
            seen['smoke'] = url
            raw = project / 'synthetic-smoke.json'
            raw.write_text('{"passed":true,"fixture":"origin-isolation-only"}')
            return 'pass', 'smoke ok', {'raw_files':[str(raw)],'summary':{'passed':True}}

        def launch(url, **k):
            seen['user'] = url
            seen['user_page'] = fetch(url + 'main.js')
            raise KeyboardInterrupt          # leave serve_forever like Control+C

        saved = {name: getattr(serve_preview, name) for name in
                 ('home_shot_gate', 'trial_smoke_gate', 'entry_readback', 'browser_request')}
        mods = {name: sys.modules.get(name) for name in ('browser_slots', 'art_receipt')}
        argv = sys.argv
        try:
            serve_preview.home_shot_gate = shot
            serve_preview.trial_smoke_gate = smoke
            serve_preview.entry_readback = lambda *a, **k: (True, [{'file': 'index.html'}], None)
            serve_preview.browser_request = launch
            sys.modules['browser_slots'] = None   # no window sweep on this computer
            sys.modules['art_receipt'] = types.SimpleNamespace(check=lambda p: {'level': 'pass', 'message': 'ok'})
            sys.argv = ['serve_preview.py', '--directory', str(export), '--no-browser',
                        '--project', str(project)] + (['--keep'] if keep else ['--open'])
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                serve_preview.main()
        finally:
            for name, value in saved.items():
                setattr(serve_preview, name, value)
            for name, value in mods.items():
                if value is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = value
            sys.argv = argv
        return seen, out.getvalue()

    def test_screenshot_and_smoke_not_on_user_origin(self):
        seen, _ = self.run_main(keep=True)
        user_port = urlsplit(seen['user']).port
        self.assertNotEqual(urlsplit(seen['shot']).port, user_port, 'home screenshot ran on the user link origin')
        self.assertNotEqual(urlsplit(seen['smoke']).port, user_port, 'trial smoke ran on the user link origin')
        self.assertEqual(seen['same_page'], seen['user_page'], 'check port must serve the same game files')

    def test_open_without_keep(self):
        seen, out = self.run_main(keep=False)
        self.assertNotEqual(urlsplit(seen['shot']).port, urlsplit(seen['user']).port)
        self.assertIsNone(seen['smoke'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
