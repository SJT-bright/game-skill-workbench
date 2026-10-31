"""Launch requests and real HTTP serving; never opens a real browser in these tests."""
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.request import urlopen
import preview_chrome as chrome

HERE = Path(__file__).resolve().parent


class ChromeRequest(unittest.TestCase):
    def test_google_window_request_preserves_existing_profile(self):
        with patch.object(chrome, 'find_chrome', return_value=Path('/vendor/Google Chrome')), patch.object(chrome.subprocess, 'Popen') as spawn:
            spawn.return_value.pid = 123
            receipt = chrome.browser_request('http://127.0.0.1:43210/', keep=True)
            argv = spawn.call_args.args[0]
            self.assertEqual(argv[0], '/vendor/Google Chrome')
            self.assertIn('--new-window', argv)
            self.assertEqual(argv[-1], 'http://127.0.0.1:43210/')
            self.assertFalse(any('user-data-dir' in arg or 'incognito' in arg or 'remote-debug' in arg for arg in argv))
            self.assertEqual(receipt['status'], 'launch_requested')
            self.assertIs(receipt['visible_window_verified'], False)

    def test_qa_and_suppressed_user_trial_do_not_spawn(self):
        with patch.object(chrome, 'open_chrome_window') as launch:
            for options in ({}, {'keep': True, 'no_browser': True}, {'explicit_open': True, 'no_browser': True}):
                self.assertEqual(chrome.browser_request('http://127.0.0.1:43210/', **options)['status'], 'not_requested')
            launch.assert_not_called()

    def test_missing_chrome_is_explicit_without_default_browser_fallback(self):
        with patch.object(chrome, 'find_chrome', side_effect=FileNotFoundError('Chrome missing')), patch.object(chrome.subprocess, 'Popen') as spawn:
            result = chrome.browser_request('http://127.0.0.1:43210/', keep=True)
            self.assertEqual(result['status'], 'launch_failed')
            self.assertIn('Chrome missing', result['error'])
            spawn.assert_not_called()

    def test_launch_failure_is_reported(self):
        with patch.object(chrome, 'find_chrome', return_value=Path('/vendor/Google Chrome')), patch.object(chrome.subprocess, 'Popen', side_effect=OSError('launch denied')):
            result = chrome.browser_request('http://127.0.0.1:43210/', keep=True)
            self.assertEqual(result['status'], 'launch_failed')
            self.assertIn('launch denied', result['error'])

    def test_remote_urls_are_not_launched(self):
        with patch.object(chrome.subprocess, 'Popen') as spawn:
            for url in ('https://example.com/', 'file:///tmp/game', 'http://127.0.0.1.example.com/', 'http://user@127.0.0.1/'):
                self.assertEqual(chrome.browser_request(url, keep=True)['status'], 'launch_failed')
            spawn.assert_not_called()

    def test_explicit_open_supports_landscape(self):
        with patch.object(chrome, 'find_chrome', return_value=Path('/vendor/Google Chrome')), patch.object(chrome.subprocess, 'Popen') as spawn:
            spawn.return_value.pid = 124
            result = chrome.browser_request('http://127.0.0.1:43210/', explicit_open=True, phone_size=(844, 390))
            self.assertEqual(result['status'], 'launch_requested')
            self.assertIn('--window-size=924,560', spawn.call_args.args[0])

    def test_windows_install_locations_are_supported_without_mac_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / 'Google/Chrome/Application/chrome.exe'
            executable.parent.mkdir(parents=True); executable.write_bytes(b'fixture')
            with patch.object(chrome.sys, 'platform', 'win32'), patch.dict(chrome.os.environ, {'LOCALAPPDATA': folder}, clear=True):
                self.assertEqual(chrome.find_chrome(), executable)


class PreviewProcess(unittest.TestCase):
    def check_process(self, flags, expected_status, expected_launches, *, missing=False):
        with tempfile.TemporaryDirectory(prefix='preview Chrome 中文 ') as folder:
            root = Path(folder)
            web = root / 'web'; web.mkdir()
            original = b'<!doctype html><title>fixture only</title><button>fixture</button>'
            (web / 'index.html').write_bytes(original)
            if '--keep' in flags:        # v7.8: a user trial checks the art receipt of --project (no image: nothing to check)
                (root / 'project' / 'assets').mkdir(parents=True)
                flags = [*flags, '--project', str(root / 'project')]
            runner = root / 'runner.py'
            runner.write_text('''import json,sys,types
from pathlib import Path
sys.path.insert(0,sys.argv[1])
record=Path(sys.argv[2]);missing=sys.argv[3]=='yes'
import preview_chrome as chrome
def fake_spawn(argv,**kwargs):
 with record.open('a') as stream:stream.write(json.dumps(argv)+'\\n')
 return types.SimpleNamespace(pid=123)
chrome.subprocess.Popen=fake_spawn
def find():
 if missing:raise FileNotFoundError('Chrome missing in controlled fixture')
 return Path('/vendor/Google Chrome')
chrome.find_chrome=find
sys.modules['browser_slots']=types.SimpleNamespace(sweep=lambda **kw:None,register=lambda *a,**kw:None)
import serve_preview
sys.argv=['serve_preview.py',*sys.argv[4:]]
serve_preview.main()
''', encoding='utf-8')
            log = root / 'server.log'; calls = root / 'calls.jsonl'
            with log.open('wb') as out:
                child = subprocess.Popen([sys.executable, '-B', str(runner), str(HERE), str(calls), 'yes' if missing else 'no', '--directory', str(web), *flags], stdout=out, stderr=out)
            port = None
            try:
                deadline = time.monotonic() + 6
                while time.monotonic() < deadline:
                    text = log.read_text()
                    if 'PREVIEW_BROWSER ' in text:
                        break
                    if child.poll() is not None:
                        self.fail(text)
                    time.sleep(.03)
                else:
                    self.fail(log.read_text())
                receipt = json.loads(next(line.removeprefix('PREVIEW_BROWSER ') for line in text.splitlines() if line.startswith('PREVIEW_BROWSER ')))
                self.assertEqual(receipt['status'], expected_status)
                url = receipt['url']; port = int(re.search(r':(\d+)/', url).group(1))
                for _ in range(2):
                    body = urlopen(url, timeout=3).read()
                    if '--raw' in flags:
                        self.assertEqual(body, original)
                    else:
                        self.assertIn(b'fixed-phone-v1', body)
                        self.assertIn(b'<iframe', body)
                self.assertEqual(len(calls.read_text().splitlines()) if calls.exists() else 0, expected_launches)
                self.assertEqual((web / 'index.html').read_bytes(), original)
            finally:
                child.terminate()
                child.wait(timeout=5)
                if port:
                    with socket.socket() as probe:
                        probe.settimeout(.5)
                        self.assertNotEqual(probe.connect_ex(('127.0.0.1', port)), 0)

    def test_user_keep_requests_once_and_serves_phone_shell(self):
        self.check_process(['--keep'], 'launch_requested', 1)

    def test_no_browser_preserves_server_without_launch(self):
        self.check_process(['--keep', '--no-browser'], 'not_requested', 0)

    def test_raw_internal_qa_stays_silent(self):
        self.check_process(['--raw'], 'not_requested', 0)

    def test_missing_browser_keeps_preview_available_and_reports_failure(self):
        self.check_process(['--keep'], 'launch_failed', 0, missing=True)


if __name__ == '__main__':
    unittest.main()
