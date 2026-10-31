#!/usr/bin/env python3
"""Serve an actual Cocos Web export on loopback; stops by itself after --idle-minutes without requests.

Never shared, never waited for (user 2026-10-23): every test line starts its own server on a new free port
(--port 0, the default) instead of waiting for another line's server. --snapshot first copies the export to a
private folder, so a build of the same game running at the same time cannot change the files under the test.
The server registers itself in browser_slots.py (old free ones are closed first) and frees its slot on exit.
Default URL is a centered fixed-size phone iframe (390x844); larger desktop windows never enlarge it.
--raw is internal automated QA only; it cannot be combined with --keep. Source/export bytes are never rewritten.
User trial: --keep automatically requests a separate Google Chrome window for the fixed-phone URL.
--no-browser suppresses the request; internal QA does not open windows by default.
The launch receipt is not visible-window or gameplay verification.
v7.8 (U7 补): --keep needs --project (the game's Cocos project) and checks its art receipt (art_receipt.py, written by
art_check.py; never a new art run): a new remake game without a passing receipt whose image fingerprints match gets no
trial server; legacy / English games and "3.x 未覆盖" print a warning. Internal QA without --keep is unchanged.
v7.8 (总表 B21 / B30 F): --keep runs the trial-link smoke on the link before printing it (cocos-game-check
runtime_regression.py trial_smoke: tap one rewarded-ad entry, the simulated ad window must be on top, 看完 must change
the game; --adapter gives the taps). Smoke failed: no link, exit 1. Smoke could not run (no Ego, no ad entry found):
the reason is printed and the link is given. Exports that never call createRewardedVideoAd skip it.
Phone shape (B7): the default page is a fixed portrait phone (390x844, only scaled down); --raw is the full-window page
for internal checks.
"""
import argparse
import os
import re
import secrets
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time
import json
from preview_chrome import browser_request
from urllib.parse import parse_qs, urlsplit

LAST = [time.time()]
CHECK_SCRIPTS = Path(__file__).resolve().parents[2] / 'cocos-game-check' / 'package-check' / 'scripts'


def uses_rewarded_ads(directory):
    """True when any JavaScript file of the export calls createRewardedVideoAd (then the trial link must show an ad)."""
    for path in Path(directory).rglob('*.js'):
        try:
            if path.is_file() and b'createRewardedVideoAd' in path.read_bytes():
                return True
        except OSError:
            continue
    return False


def trial_smoke_gate(url, directory, adapter=None, smoke=None):
    """v7.8 (总表 B21 / B30 F): before a user trial link is printed, tap one rewarded-ad entry on the link exactly as
    Saul opens it (runtime_regression.trial_smoke, suite trial_link): the simulated ad window must be on top of the
    game and 看完 must change the game. Returns (level, message): 'block' = do not give the link out, 'warn' = the smoke
    did not run (reason printed), 'pass'. smoke: the trial_smoke function (tests)."""
    if not uses_rewarded_ads(directory):
        return 'pass', '试玩链接冒烟：这个导出不调用 createRewardedVideoAd，不涉及看广告，没跑'
    if smoke is None:
        try:
            if str(CHECK_SCRIPTS) not in sys.path:
                sys.path.insert(0, str(CHECK_SCRIPTS))
            import runtime_regression
        except Exception as error:  # noqa: BLE001
            return 'warn', '试玩链接冒烟没跑：找不到 cocos-game-check 的 runtime_regression.py（%s）' % error
        smoke, refused = runtime_regression.trial_smoke, runtime_regression.RuntimeRefused
    else:
        refused = getattr(smoke, 'refused', Exception)
    try:
        summary = smoke(url, adapter)
    except refused as error:
        if getattr(error, 'summary', None):
            return 'block', '不给试玩链接：试玩链接冒烟不通过：%s' % error
        return 'warn', '试玩链接冒烟没跑：%s' % error
    if summary.get('not_run'):
        return 'warn', '试玩链接冒烟没跑：%s（可用 --adapter 给出 trial.taps）' % summary['not_run']
    return 'pass', '试玩链接冒烟通过：点看广告后模拟广告窗在最上层，点「看完」后游戏有变化'


def phone_preview_html(width=390, height=844, entry="index.html"):
    """Keep the game iframe's CSS viewport fixed; only scale its outer presentation."""
    return ("""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="game-preview-mode" content="fixed-phone-v1"><title>手机试玩</title>
<style>html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#20242c}
body{display:grid;place-items:center}#phone-shell{position:relative;overflow:hidden;border-radius:12px;outline:1px solid #515762;box-shadow:0 12px 48px #0008;background:#fff}
#phone-game{position:absolute;left:0;top:0;border:0;display:block;transform-origin:top left;background:#fff}</style>
</head><body><main id="phone-shell" aria-label="手机尺寸游戏试玩"><iframe id="phone-game" title="游戏试玩" allow="autoplay; gamepad; fullscreen 'none'"></iframe></main>
<script>(()=>{const width=__WIDTH__,height=__HEIGHT__,shell=document.getElementById('phone-shell'),frame=document.getElementById('phone-game');
frame.style.width=width+'px';frame.style.height=height+'px';
const game=new URL('__PREVIEW_ENTRY__',location.href);game.search=location.search;game.searchParams.set('__phone_game','1');frame.src=game.pathname+game.search+location.hash;
function fit(){const scale=Math.min(1,Math.max(1,innerWidth-32)/width,Math.max(1,innerHeight-32)/height);shell.style.width=width*scale+'px';shell.style.height=height*scale+'px';frame.style.transform='scale('+scale+')';window.__phonePreview={policy:'fixed-phone-v1',width,height,scale};}
addEventListener('resize',fit);fit();})();</script></body></html>""".replace('__WIDTH__',str(width)).replace('__HEIGHT__',str(height)).replace('__PREVIEW_ENTRY__',entry)).encode('utf-8')


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, phone_size=None, preview_token=None, ad_simulator=False, ad_simulator_setup=None, **kwargs):
        self.phone_size = phone_size
        self.ad_simulator = ad_simulator
        self.ad_simulator_setup = ad_simulator_setup
        self.preview_mount = "/__preview/" + preview_token + "/" if preview_token else ""
        super().__init__(*args, **kwargs)

    def do_GET(self):
        LAST[0] = time.time()
        request = urlsplit(self.path)
        if request.path == '/__local_ad_simulator.js':
            if not self.ad_simulator:
                self.send_error(404)
                return
            self.send_bytes((Path(__file__).resolve().parent.parent / 'assets' / 'ad-simulator.js').read_bytes(), 'application/javascript; charset=utf-8')
            return
        if request.path == '/__local_ad_simulator_setup.js':
            if not self.ad_simulator or not self.ad_simulator_setup:
                self.send_error(404)
                return
            self.send_bytes(self.ad_simulator_setup.read_bytes(), 'application/javascript; charset=utf-8')
            return
        if (self.phone_size and request.path in ('/', '/index.html')
                and parse_qs(request.query).get('__phone_game') != ['1']):
            content = phone_preview_html(*self.phone_size, entry=self.preview_mount + "index.html" if self.preview_mount else "index.html")
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Permissions-Policy', 'fullscreen=()')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        if self.preview_mount and request.path.startswith(self.preview_mount):
            # A unique directory versions scripts AND engine-discovered bundle/resource URLs.
            # It keeps the same origin/localStorage while isolating old WebView caches.
            self.path = "/" + request.path[len(self.preview_mount):]
            if request.query:
                self.path += "?" + request.query
        if 'If-Modified-Since' in self.headers: del self.headers['If-Modified-Since']
        if 'If-None-Match' in self.headers: del self.headers['If-None-Match']
        if self.ad_simulator:
            path = Path(self.translate_path(self.path))
            # Apply to nested HTML exports as well. Only HTTP response bytes change.
            if path.suffix.lower() in ('.html', '.htm') and path.is_file():
                content = path.read_bytes()
                script = b'<script src="/__local_ad_simulator.js"></script>'
                if self.ad_simulator_setup:
                    script += b'<script src="/__local_ad_simulator_setup.js"></script>'
                match = re.search(br'<head\b[^>]*>', content, re.I)
                pos = match.end() if match else 0
                content = content[:pos] + script + content[pos:]
                self.send_bytes(content, 'text/html; charset=utf-8')
                return
        super().do_GET()

    def send_bytes(self, content, content_type):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, max-age=0')
        self.send_header('Pragma', 'no-cache')
        super().end_headers()

    def log_message(self, *args):   # quiet: no line per request
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--no-browser', action='store_true', help='do not open a browser, including user-trial --keep')
    parser.add_argument('--open', action='store_true', help='request a separate Google Chrome window, including without --keep')
    parser.add_argument('--idle-minutes', type=float, default=20, help='stop after this many minutes without requests (0 = never)')
    parser.add_argument('--snapshot', action='store_true', help='serve a private copy of the export (a running build cannot change it)')
    parser.add_argument('--name', default='', help='label shown in browser_slots.py list, e.g. "测试线 音量复核"')
    parser.add_argument('--project', help='the Cocos project: required with --keep (art receipt check), else a label')
    parser.add_argument('--keep', action='store_true', help='user trial: automatically open a separate Chrome window; keep the local preview service')
    parser.add_argument('--orientation', choices=['portrait', 'landscape'], default='portrait', help='user preview phone orientation (default portrait 390x844)')
    parser.add_argument('--phone-width', type=int, help='fixed inner CSS viewport width; use with --phone-height')
    parser.add_argument('--phone-height', type=int, help='fixed inner CSS viewport height; use with --phone-width')
    parser.add_argument('--raw', action='store_true', help='internal automated QA only: expose top-level original canvas; never hand this URL to a user')
    parser.add_argument('--ad-simulator', action='store_true', help='inject manual rewarded-ad simulation into local HTML responses only; no source or Native changes')
    parser.add_argument('--ad-simulator-setup', type=Path, help='optional game-specific preview-only entry labels and real-state reader')
    parser.add_argument('--adapter', type=Path, help='--keep trial-link smoke: the runtime adapter JSON; its "trial" field '
                        '(taps, reward_js) names the way to a rewarded ad (default: an ad-like home button)')
    args = parser.parse_args()
    if args.ad_simulator_setup:
        if not args.ad_simulator or not args.ad_simulator_setup.is_file():
            parser.error('--ad-simulator-setup requires --ad-simulator and an existing JavaScript file')
        args.ad_simulator_setup = args.ad_simulator_setup.resolve()
    if (args.phone_width is None) != (args.phone_height is None):
        parser.error('--phone-width and --phone-height must be supplied together')
    phone_size = (args.phone_width, args.phone_height) if args.phone_width is not None else ((844, 390) if args.orientation == 'landscape' else (390, 844))
    if any(value < 200 or value > 1600 for value in phone_size):
        parser.error('phone viewport dimensions must be between 200 and 1600 CSS pixels')
    if args.raw and args.keep:
        parser.error('--raw is internal QA only and cannot be combined with user-trial --keep')
    directory = args.directory.resolve()
    if not (directory / 'index.html').is_file():
        raise SystemExit('找不到 index.html，请指定实际 Cocos Web 导出目录。')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if args.keep:
        # v7.8 U7（补）: a user trial needs the art receipt, like the package writers (checked only, never a new art run)
        if not args.project:
            parser.error('用户试玩 --keep 需要 --project <这款游戏的 Cocos 工程>：起服务前要核对美术回执 .tiktok-kit/art-receipt.json')
        import art_receipt
        art = art_receipt.check(Path(args.project))
        if art['level'] == 'block':
            print('不起试玩服务：' + art['message'], file=sys.stderr, flush=True)
            raise SystemExit(1)
        print('美术回执：' + art['message'] + ('（警告）' if art['level'] == 'warn' else ''), flush=True)
    try:
        import browser_slots
        browser_slots.sweep(close=True)                     # close free old test windows / servers first
    except Exception:
        browser_slots = None
    if args.snapshot:
        if browser_slots is None:
            raise SystemExit('--snapshot needs browser_slots.py next to this script')
        directory = browser_slots.snapshot(directory)
    handler = partial(Handler, directory=str(directory), phone_size=None if args.raw else phone_size, preview_token=None if args.raw else secrets.token_hex(8), ad_simulator=args.ad_simulator, ad_simulator_setup=args.ad_simulator_setup)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
    url = f'http://127.0.0.1:{server.server_port}/'
    slot = None
    if browser_slots is not None:
        try:
            slot = browser_slots.register('preview', args.name or directory.name, os.getpid(), args.project,
                                          port=server.server_port, url=url, directory=directory if args.snapshot else None,
                                          keep=args.keep or args.idle_minutes == 0)
        except Exception:
            slot = None
    serving = None
    if args.keep:
        # v7.8 (总表 B21 / B30 F): the trial-link smoke runs on this very link before it is printed; a failure keeps the
        # link from the user (the ad window behind the game looked like a frozen game in 全民飞车漂移 v1-v3)
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        level, message = trial_smoke_gate(url, directory, args.adapter)
        print(message, file=sys.stderr if level == 'block' else sys.stdout, flush=True)
        if level == 'block':
            server.shutdown()
            server.server_close()
            if slot:
                browser_slots.release(slot)
            raise SystemExit(1)
    lifetime = '用户试玩保留中；不因空闲时间自动关闭。' if args.keep or args.idle_minutes == 0 else f'{args.idle_minutes:g} 分钟没人访问会自动关闭。'
    entry_kind = '内部QA入口（禁止交给用户试玩）' if args.raw else f'手机尺寸本地试玩（内部 {phone_size[0]}×{phone_size[1]}，只缩小不放大）'
    print(f'{entry_kind}：{url}\n（用户试玩会自动请求独立 Google Chrome 窗口；同时在回复中保留此本地链接。须读回实际窗口，不能把启动请求当作已显示。）\n保持窗口打开；按 Control+C 结束。{lifetime}'
          + (f'\n（独立副本：{directory}）' if args.snapshot else ''), flush=True)
    if slot:
        def beat():
            seen = 0
            while True:
                time.sleep(15)
                if LAST[0] != seen:
                    seen = LAST[0]
                    try:
                        browser_slots.heartbeat(slot, heartbeat_ts=LAST[0])
                    except Exception:
                        pass
        threading.Thread(target=beat, daemon=True).start()
    if args.idle_minutes > 0 and not args.keep:
        def watch():
            while True:
                time.sleep(15)
                if time.time() - LAST[0] > args.idle_minutes * 60:
                    print('长时间没人访问，预览服务已自动关闭。', flush=True)
                    server.shutdown()
                    return
        threading.Thread(target=watch, daemon=True).start()
    import signal
    def stop(signum, frame):
        raise KeyboardInterrupt                         # SIGTERM from a sweep: still free our slot below
    for sig in (getattr(signal, 'SIGTERM', None), getattr(signal, 'SIGBREAK', None)):
        if sig is not None:
            try:
                signal.signal(sig, stop)
            except (OSError, ValueError):
                pass
    try:
        launch = browser_request(url, keep=args.keep, explicit_open=args.open,
                                 no_browser=args.no_browser, phone_size=phone_size)
        print('PREVIEW_BROWSER ' + json.dumps(launch, ensure_ascii=False), flush=True)
        if serving is None:
            server.serve_forever()
        else:
            while serving.is_alive():
                serving.join(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        if serving is not None and serving.is_alive():
            server.shutdown()
        server.server_close()
        if slot:
            browser_slots.release(slot)                   # also deletes the private snapshot copy


if __name__ == '__main__':
    main()
