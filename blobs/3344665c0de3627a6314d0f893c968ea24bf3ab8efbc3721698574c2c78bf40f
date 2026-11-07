"""生成时预防 J2b: serve_preview.py
P21 ⑤ 后半 - a link a person opens gets one Ego home screenshot first (black / one colour / still loading /
page error -> no link; no browser / timeout -> 未测, never "passed").
P13 ④ - the phone-frame game page turns a mouse drag on the canvas into touchstart / touchmove / touchend with the
fields the platform kit touch parts read.
No real browser: the fixture supplies a fake Ego CLI on its test PATH, writes a black or normal PNG, or hangs,
and the mouse -> touch part runs in a fake DOM under Node (preview_touch_fakedom.cjs). The 11.12+J2 serve_preview.py
(git HEAD~0 of the patch work tree, or _work/backup) is run the same way and must show the old problems."""
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zlib
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
PY = sys.executable
spec = importlib.util.spec_from_file_location('serve_preview_j2b', HERE / 'serve_preview.py')
SP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SP)
NODE = shutil.which('node') or shutil.which('nodejs')


def png(width, height, pixel):
    """pixel(x, y) -> (r, g, b); filter 0 rows."""
    raw = b''.join(b'\x00' + b''.join(bytes(pixel(x, y)) for x in range(width)) for y in range(height))
    chunk = lambda kind, body: struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


BLACK = png(39, 84, lambda x, y: (0, 0, 0))
WHITE = png(39, 84, lambda x, y: (255, 255, 255))
NORMAL = png(39, 84, lambda x, y: ((x * 6) % 256, (y * 3) % 256, 120 if y > 40 else 30))

FAKE_EGO = r'''#!%s
import json, os, re, sys, time, urllib.request
mode = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mode.txt')).read().strip()
assert sys.argv[1:3] == ['nodejs', '-e'], sys.argv[1:3]
script = sys.argv[3]
assert 'Page.captureScreenshot' in script
assert 'Emulation.setTouchEmulationEnabled' in script
assert 't.finish({keep:[]})' in script
literal = r'("(?:[^"\\]|\\.)*")'
def argument(command, end):
    return json.loads(re.search(re.escape(command) + literal + re.escape(end), script).group(1))
space = argument('taskSpace(', ')')
shot = argument('fs.writeFile(', ',')
url = argument('p.goto(', ')')
if mode == 'timeout':
    time.sleep(60)
probe = {'loading': {'errors': [], 'splash': True, 'engine': True, 'scene': None},
         'error': {'errors': ['uncaught: TypeError: Cannot read properties of undefined'], 'splash': False, 'engine': True, 'scene': 'Home'},
         'normal': {'errors': [], 'splash': False, 'engine': True, 'scene': 'Home'}}.get(mode)
if probe:
    base = url.split('/__preview/')[0].split('/index.html')[0].rstrip('/')
    page = urllib.request.urlopen(url).read()
    if b'/__local_home_probe.js' in page:
        urllib.request.urlopen(urllib.request.Request(base + '/__local_home_probe', data=json.dumps(probe).encode(), method='POST'))
if mode != 'noimage':
    name = {'black': 'black.png', 'white': 'white.png'}.get(mode, 'normal.png')
    open(shot, 'wb').write(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), name), 'rb').read())
if mode == 'cleanup_failure':
    sys.exit('fixture space cleanup failed')
if mode == 'wrong_receipt':
    space += '-old'
print(json.dumps({'browser_route': 'ego_taskspace', 'input_transport': 'ego_page_cdp', 'session_id': 7,
                  'space_name': space, 'screenshot': shot, 'space_finished': True}))
'''


class Tmp(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.d = Path(self._td.name)
        self.web = self.d / 'web-mobile'
        self.web.mkdir()
        (self.web / 'index.html').write_text('<html><head></head><body><canvas id="GameCanvas"></canvas>'
                                             '<script src="main.js"></script></body></html>', encoding='utf-8')
        (self.web / 'main.js').write_text('window.boot=1;', encoding='utf-8')
        fake = self.d / 'fake-ego-bin'
        fake.mkdir()
        (fake / 'black.png').write_bytes(BLACK)
        (fake / 'white.png').write_bytes(WHITE)
        (fake / 'normal.png').write_bytes(NORMAL)
        self.browser = fake / 'ego-browser'
        self.browser.write_text(FAKE_EGO % PY, encoding='utf-8')
        self.browser.chmod(0o755)
        self.mode('normal')

    def tearDown(self):
        self._td.cleanup()

    def mode(self, m):
        (self.browser.parent / 'mode.txt').write_text(m)

    def serve(self, module=SP, touch_bridge=True):
        kw = {'touch_bridge': touch_bridge} if module is SP else {}
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(module.Handler, directory=str(self.web), phone_size=(390, 844),
                                                                preview_token='t1', **kw))
        server.home_probe = None
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close()))
        return server, 'http://127.0.0.1:%d/' % server.server_port

    def gate(self, mode, timeout=20, export=None):
        self.mode(mode)
        server, url = self.serve()
        shot = url + '__preview/t1/index.html?__phone_game=1&__home_shot=1'
        with patch.object(SP, 'find_shot_browser', return_value=str(self.browser)):
            return SP.home_shot_gate(shot, export or self.web, (390, 844), self.d / 'home.png',
                                     probe=lambda: server.home_probe, timeout=timeout, wait=1)


class PngStats(unittest.TestCase):
    def test_black_white_normal(self):
        self.assertGreaterEqual(SP.png_stats(BLACK)['dark'], 0.99)
        self.assertGreaterEqual(SP.png_stats(WHITE)['dominant'], 0.999)
        s = SP.png_stats(NORMAL)
        self.assertLess(s['dark'], 0.5)
        self.assertLess(s['dominant'], 0.5)

    def test_all_png_filters(self):
        # Decode filtered PNG rows (Sub/Up/Average/Paeth) the same as unfiltered rows.
        width, height = 8, 6
        rows = [bytes((x * 30 + y * 7) % 256 for x in range(width * 3)) for y in range(height)]
        prev, raw = bytes(width * 3), b''
        for y, row in enumerate(rows):
            f = y % 5
            out = bytearray()
            for x in range(len(row)):
                a = row[x - 3] if x >= 3 else 0
                b, c = prev[x], prev[x - 3] if x >= 3 else 0
                p = a + b - c
                pr = a if abs(p - a) <= abs(p - b) and abs(p - a) <= abs(p - c) else b if abs(p - b) <= abs(p - c) else c
                out.append((row[x] - [0, a, b, (a + b) // 2, pr][f]) & 255)
            raw += bytes([f]) + bytes(out)
            prev = row
        chunk = lambda kind, body: struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
        filtered = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
                    + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
        plain = png(width, height, lambda x, y: tuple(rows[y][x * 3:x * 3 + 3]))
        self.assertEqual(SP.png_stats(filtered), SP.png_stats(plain))


class HomeShotGate(Tmp):
    def test_normal_home_passes(self):
        level, message, info = self.gate('normal')
        self.assertEqual(level, 'pass', message)
        self.assertEqual(info['probe']['scene'], 'Home')
        self.assertEqual(info['browser_route'], 'ego_taskspace')
        self.assertEqual(info['input_transport'], 'ego_page_cdp')
        self.assertTrue(info['space_name'].startswith('preview-home-'))
        self.assertIn(str(self.d / 'home.png'), message)

    def test_black_screen_is_refused(self):
        level, message, _ = self.gate('black')
        self.assertEqual(level, 'block')
        self.assertIn('全黑', message)

    def test_white_screen_is_refused(self):
        level, message, _ = self.gate('white')
        self.assertEqual(level, 'block')
        self.assertIn('一种颜色', message)

    def test_still_on_loading_page_is_refused(self):
        level, message, _ = self.gate('loading')
        self.assertEqual(level, 'block')
        self.assertIn('加载页', message)

    def test_page_error_is_refused(self):
        level, message, _ = self.gate('error')
        self.assertEqual(level, 'block')
        self.assertIn('页面报错', message)
        self.assertIn('TypeError', message)

    def test_timeout_keeps_browser_check_untested(self):
        t0 = time.time()
        level, message, info = self.gate('timeout', timeout=2)
        self.assertLess(time.time() - t0, 20)
        self.assertEqual(level, 'warn')
        self.assertIsNone(info['screenshot'])
        self.assertIn('保留未测', message)

    def test_browser_without_picture_does_not_reuse_an_old_file(self):
        (self.d / 'home.png').write_bytes(NORMAL)
        level, message, info = self.gate('noimage')
        self.assertEqual(level, 'warn')
        self.assertIsNone(info['screenshot'])
        self.assertIn('没截图', message)
        self.assertFalse((self.d / 'home.png').exists())

    def test_ego_cleanup_failure_is_not_a_screenshot_pass(self):
        level, message, info = self.gate('cleanup_failure')
        self.assertEqual(level, 'warn')
        self.assertIsNone(info['screenshot'])
        self.assertIn('保留未测', message)

    def test_image_without_matching_ego_space_receipt_is_untested(self):
        level, message, info = self.gate('wrong_receipt')
        self.assertEqual(level, 'warn')
        self.assertIsNone(info['screenshot'])
        self.assertIn('当前空间回执', message)
        self.assertNotIn('首页截图核对通过', message)

    def test_no_ego_does_not_try_another_browser(self):
        with patch.object(SP, 'find_shot_browser', return_value=None):
            def forbidden(*args, **kwargs):
                self.fail('started a browser without the official Ego CLI')
            level, message, info = SP.home_shot_gate('http://127.0.0.1:9/', self.web, (390, 844), self.d / 'x.png',
                                                    run=forbidden)
        self.assertEqual(level, 'warn')
        self.assertIsNone(info['screenshot'])
        self.assertIn('找不到官方 Ego CLI', message)

    def test_screenshot_lookup_ignores_desktop_browser_override(self):
        with patch.dict(os.environ, {'PATH': str(self.browser.parent), 'CDP_BROWSER': str(self.d / 'Chrome')}):
            self.assertEqual(SP.find_shot_browser(), str(self.browser))

    def test_cocos3_problem_only_warns(self):
        (self.web / 'index.html').write_text('<html><head></head><body><canvas id="GameCanvas"></canvas><script src="main.js">'
                                             '</script><script>System.import("./index.js")</script></body></html>')
        level, message, _ = self.gate('black')
        self.assertEqual(level, 'warn')
        self.assertIn('3.x', message)


class ProbeAndBridgeServing(Tmp):
    def test_probe_only_on_home_shot_page_and_bridge_only_in_phone_frame(self):
        _, url = self.serve()
        page = urlopen(url + '__preview/t1/index.html?__phone_game=1').read()
        self.assertIn(SP.TOUCH_BRIDGE_TAG, page)
        self.assertNotIn(SP.HOME_PROBE_TAG, page)
        shot = urlopen(url + '__preview/t1/index.html?__phone_game=1&__home_shot=1').read()
        self.assertIn(SP.HOME_PROBE_TAG, shot)
        self.assertIn(b'addEventListener', urlopen(url + '__local_touch_bridge.js').read())
        self.assertEqual((self.web / 'index.html').read_bytes().count(b'__local'), 0)   # export bytes never change
        _, raw = self.serve(touch_bridge=False)
        self.assertNotIn(SP.TOUCH_BRIDGE_TAG, urlopen(raw + '__preview/t1/index.html?__phone_game=1').read())

    def test_entry_readback_still_passes_with_bridge(self):
        _, url = self.serve()
        ok, rows, problem = SP.entry_readback(url, self.web)
        self.assertTrue(ok, problem)
        self.assertEqual(sorted(r['file'] for r in rows), ['index.html', 'main.js'])


def old_scripts(dest):
    """11.12 + J2 remake-core/scripts with the pre-J2b serve_preview.py (from git HEAD of the work tree or _work/backup)."""
    shutil.copytree(HERE, dest)
    old = None
    try:
        old = subprocess.run(['git', 'show', 'HEAD:remake-core/scripts/serve_preview.py'], cwd=str(HERE), capture_output=True,
                             timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        pass
    if not old or b'home_shot_gate' in old:
        backup = HERE.parents[2] / 'backup' / 'remake-core' / 'scripts' / 'serve_preview.py'
        old = backup.read_bytes() if backup.is_file() else None
    if not old or b'home_shot_gate' in old:
        return None
    (dest / 'serve_preview.py').write_bytes(old)
    return dest


class EndToEnd(Tmp):
    """serve_preview.py --idle-minutes 0 (a link a person opens) with the fake Ego CLI drawing a black screen."""

    def run_main(self, scripts, new=True):
        env = dict(os.environ, PATH=str(self.browser.parent) + os.pathsep + os.environ.get('PATH', ''),
                   GAME_SKILL_LOCK_DIR=str(self.d / 'locks'),
                   PYTHONDONTWRITEBYTECODE='1')
        extra = ['--home-shot-wait', '1', '--home-shot-timeout', '20'] if new else []
        p = subprocess.Popen([PY, '-B', str(scripts / 'serve_preview.py'), '--directory', str(self.web), '--no-browser',
                              '--idle-minutes', '0', *extra],
                             env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        lines = []
        reader = threading.Thread(target=lambda: [lines.append(x) for x in p.stdout], daemon=True)
        reader.start()
        deadline = time.time() + 40
        while time.time() < deadline and p.poll() is None and not re.search(r'本地试玩[^\n]*：http', ''.join(lines)):
            time.sleep(0.1)
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        reader.join(timeout=5)
        p.stdout.close()
        return p.returncode, ''.join(lines)

    def test_old_gives_link_on_black_screen_new_refuses(self):
        self.mode('black')
        old = old_scripts(self.d / 'old_scripts')
        if old is None:
            self.skipTest('pre-J2b serve_preview.py not found (only in the patch work tree)')
        code, out = self.run_main(old, new=False)
        self.assertRegex(out, r'本地试玩[^\n]*：http://127\.0\.0\.1:\d+/', '11.12+J2: black screen still gets a link')
        code, out = self.run_main(HERE)
        self.assertEqual(code, 1, out)
        self.assertIn('不给试玩链接：首页截图几乎全黑', out)
        self.assertNotRegex(out, r'本地试玩[^\n]*：http')

    def test_new_gives_link_on_normal_home(self):
        self.mode('normal')
        code, out = self.run_main(HERE)
        self.assertIn('首页截图核对通过', out)
        self.assertRegex(out, r'本地试玩[^\n]*：http://127\.0\.0\.1:\d+/')


@unittest.skipUnless(NODE, 'Node.js not found')
class MouseToTouch(unittest.TestCase):
    def fakedom(self, bridge):
        r = subprocess.run([NODE, str(HERE / 'preview_touch_fakedom.cjs'), bridge], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_old_phone_page_drag_gives_no_touchmove(self):
        out = self.fakedom('none')
        types = [e['type'] for e in out['events'] if e['on'] == 'canvas']
        self.assertNotIn('touchmove', types)          # BrothersRush: a touch-only game cannot be dragged
        self.assertFalse(out['touchCapable'])

    def test_bridge_turns_drag_into_touches_with_kit_fields(self):
        out = self.fakedom(str(HERE.parent / 'assets' / 'preview-touch-bridge.js'))
        canvas = [e for e in out['events'] if e['on'] == 'canvas']
        self.assertEqual([e['type'] for e in canvas],
                         ['touchstart', 'touchmove', 'touchmove', 'touchend', 'touchstart', 'touchend'])
        self.assertTrue(out['touchCapable'])           # engines enable touch input only on touch-capable pages
        first = canvas[:4]
        self.assertEqual({e['identifier'] for e in first}, {1})
        self.assertEqual(canvas[4]['identifier'], 2)   # a new press is a new finger
        for e in canvas:
            self.assertEqual((e['screenX'], e['screenY']), (e['clientX'], e['clientY']))   # game coords, not monitor
        self.assertEqual((canvas[2]['clientX'], canvas[2]['clientY']), (200, 210))
        self.assertEqual([e['touches'] for e in first], [1, 1, 1, 0])
        self.assertNotIn('mousedown', [e['type'] for e in canvas])    # the engine does not get the press twice
        self.assertEqual([e['type'] for e in out['events'] if e['on'] == 'overlay'], ['mousedown', 'mouseup'])
        self.assertEqual(out['kitRead'][1], [1, 150, 200])            # tiktok-touch-3x normalizePoint reads them as-is


if __name__ == '__main__':
    unittest.main()
