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
runtime_regression.py trial_smoke: tap one rewarded-ad entry. Ordinary links need a visible response. Simulated links
need a visible ad panel, an enabled completion button, and a subsequent game response; --adapter gives the taps). Smoke failed: no link, exit 1. Smoke could not run (no Ego, no ad entry found):
the reason is printed and the link is given. Exports that never call createRewardedVideoAd skip it.
生成时预防 P21 ⑤: a link a person opens (--keep, --open or --idle-minutes 0) is read back over HTTP before it is printed:
the entry page and its <script src> files must be byte-identical to the export folder given now (with --snapshot: the
export, not the copy). Different (old cache, old copy, export changed meanwhile) -> no link, exit 1.
生成时预防 P21 ⑤ 后半: after the read-back, a headless Chrome/Edge (browser_env.find_browser) screenshots the game page;
black / one-colour picture, still on the loading page, or a page error -> no link, exit 1. No browser, timeout or a
browser error -> the link is given with 没截图 (never counted as passed). The picture path is printed: look at it.
生成时预防 P13 ④: the game page inside the phone frame gets assets/preview-touch-bridge.js (response only): a mouse
press / drag / release on the canvas becomes touchstart / touchmove / touchend with identifier, clientX/Y, screenX/Y.
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
from urllib.parse import parse_qs, urlsplit, urlunsplit

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


def trial_smoke_gate(url, directory, adapter=None, smoke=None, *, ad_simulator=False):
    """v7.8 (总表 B21 / B30 F): before a user trial link is printed, tap one rewarded-ad entry on the link exactly as
    Saul opens it (runtime_regression.trial_smoke, suite trial_link). An injected preview must also complete its ad. Returns (level, message): 'block' = do not give the link out, 'warn' = the smoke
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
    evidence = summary.get('evidence') or {}
    if not summary.get('passed'):
        return 'block', '不给试玩链接：没有通过本次入口响应检查'
    if evidence.get('simulatorCompleted') is True:
        response = '项目读数' if evidence.get('responseKind') == 'project_readback' else '画面文字'
        return 'pass', '试玩链接冒烟通过：已点开模拟广告并选择看完，%s随后有变化' % response
    if ad_simulator:
        return 'block', '不给模拟试玩链接：未证实独立模拟面板已打开并完成'
    return 'pass', '试玩链接冒烟通过：点击广告入口后游戏给出了可见响应'


SCRIPT_SRC = re.compile(r'<script\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', re.I)
SHELL_ENTRY = re.compile(r"new URL\('([^']+)'")


def entry_readback(url, export_dir, *, html_injected=False, fetch=None):
    """生成时预防 P21 ⑤ (MabelsMeadow / Meadow Match: the link still loaded an old build; 普查 stale_preview 10 次):
    read the link back over HTTP exactly as a browser opens it (phone shell -> game entry page -> its <script src>
    files) and compare every entry file byte for byte with the CURRENT export folder. Returns (ok, rows, problem).
    html_injected: the server adds preview-only scripts to HTML (--ad-simulator), so the entry page itself is not
    compared, only its scripts. Scripts the engine loads later are not read here."""
    import hashlib
    from urllib.parse import urljoin
    from urllib.request import Request, urlopen

    def get(u):
        if fetch is not None:
            return fetch(u)
        with urlopen(Request(u, headers={'Cache-Control': 'no-cache'}), timeout=10) as r:
            return r.read()

    sha = lambda b: hashlib.sha256(b).hexdigest()
    export_dir = Path(export_dir)
    try:
        top = get(url)
        m = SHELL_ENTRY.search(top.decode('utf-8', 'replace')) if b'game-preview-mode' in top else None
        entry_url = urljoin(url, m.group(1)) + '?__phone_game=1' if m else url
        mount = urlsplit(urljoin(url, m.group(1))).path.rsplit('/', 1)[0] + '/' if m else '/'
        page = get(entry_url)
    except Exception as error:  # noqa: BLE001
        return False, [], '读不回试玩链接（%s）' % error
    rows = []

    def compare(rel, served):
        local = export_dir / rel
        try:
            want = local.read_bytes()
        except OSError:
            rows.append({'file': rel, 'served_sha256': sha(served), 'export_sha256': None, 'same': False})
            return
        rows.append({'file': rel, 'served_sha256': sha(served), 'export_sha256': sha(want), 'same': served == want})

    if not html_injected:
        compare('index.html', page.replace(TOUCH_BRIDGE_TAG, b'', 1))   # P13 ④: the preview-only touch bridge tag
    for src in SCRIPT_SRC.findall(page.decode('utf-8', 'replace')):
        full = urljoin(entry_url, src)
        parts = urlsplit(full)
        if parts.netloc != urlsplit(url).netloc or parts.path.startswith('/__local'):
            continue
        rel = parts.path[len(mount):] if parts.path.startswith(mount) else parts.path.lstrip('/')
        try:
            compare(rel, get(urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ''))))
        except Exception as error:  # noqa: BLE001
            rows.append({'file': rel, 'served_sha256': None, 'export_sha256': None, 'same': False, 'error': str(error)})
    bad = [r['file'] for r in rows if not r['same']]
    if not rows:
        return False, rows, '链接里读不到入口页和入口脚本'
    if bad:
        return False, rows, '链接给出的 %s 和现在的导出不一样（旧缓存、旧副本，或导出在起服务以后又变了）' % '、'.join(bad)
    return True, rows, None


TOUCH_BRIDGE_TAG = b'<script src="/__local_touch_bridge.js"></script>'
HOME_PROBE_TAG = b'<script src="/__local_home_probe.js"></script>'
# 生成时预防 P21 ⑤ (后半): preview-only probe in the headless home screenshot page (query __home_shot=1). It reports
# uncaught errors, unhandled rejections, console.error, the Cocos splash and whether a scene runs back to this server.
HOME_PROBE_JS = br"""(function(w){if(w.__homeProbe)return;var s={errors:[],t0:Date.now()};w.__homeProbe=s;
function add(m){if(s.errors.length<8)s.errors.push(String(m).slice(0,300))}
var ce=console.error;console.error=function(){try{add('console.error: '+[].map.call(arguments,function(a){return a&&a.stack||String(a)}).join(' '))}catch(e){}return ce.apply(this,arguments)};
w.addEventListener('error',function(e){if(e&&e.target&&e.target!==w&&(e.target.src||e.target.href))add('load failed: '+(e.target.src||e.target.href));else add('uncaught: '+(e&&(e.message||e.error)||'error'))},true);
w.addEventListener('unhandledrejection',function(e){var r=e&&e.reason;add('unhandled rejection: '+(r&&r.message||r))});
function state(){var sp=document.getElementById('splash'),shown=false;try{shown=!!(sp&&getComputedStyle(sp).display!=='none'&&getComputedStyle(sp).visibility!=='hidden'&&sp.offsetWidth>0)}catch(e){}
var c=w.cc,scene=null;try{var sc=c&&c.director&&c.director.getScene&&c.director.getScene();scene=sc?String(sc.name||sc._name||'?'):null}catch(e){}
return {errors:s.errors,splash:shown,engine:!!(c&&c.director),scene:scene,ms:Date.now()-s.t0}}
function send(){try{var x=new XMLHttpRequest();x.open('POST','/__local_home_probe',false);x.setRequestHeader('Content-Type','application/json');x.send(JSON.stringify(state()))}catch(e){}}
w.addEventListener('load',send);setInterval(send,500);})(window);"""


def png_stats(data):
    """Black / one-colour verdict input for a headless screenshot (8-bit RGB/RGBA/grey PNG, as Chrome writes them):
    {'width','height','dark','dominant'} with dark = share of pixels darker than luminance 16 and dominant = share of
    the most common colour (rounded to 8 levels per channel). Every 4th pixel of every 2nd row is counted."""
    import struct
    import zlib
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('不是 PNG')
    pos, idat, head = 8, [], None
    while pos < len(data):
        length, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b'IHDR':
            head = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            idat.append(body)
        elif kind == b'IEND':
            break
        pos += 12 + length
    width, height, depth, colour, _, _, interlace = head
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(colour)
    if depth != 8 or channels is None or interlace:
        raise ValueError('PNG 格式不支持（%s 位，颜色类型 %s，隔行 %s）' % (depth, colour, interlace))
    raw, stride = zlib.decompress(b''.join(idat)), width * channels
    prev, rows, i = bytearray(stride), [], 0
    for _ in range(height):
        f, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        if f == 1:
            for x in range(channels, stride):
                line[x] = (line[x] + line[x - channels]) & 255
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif f == 3:
            for x in range(stride):
                line[x] = (line[x] + ((line[x - channels] if x >= channels else 0) + prev[x]) // 2) & 255
        elif f == 4:
            for x in range(stride):
                a = line[x - channels] if x >= channels else 0
                b, c = prev[x], prev[x - channels] if x >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    counts, dark, total = {}, 0, 0
    for y in range(0, height, 2):
        line = rows[y]
        for x in range(0, width, 4):
            px = line[x * channels:x * channels + channels]
            r, g, b = (px[0], px[0], px[0]) if channels < 3 else (px[0], px[1], px[2])
            total += 1
            if 0.299 * r + 0.587 * g + 0.114 * b < 16:
                dark += 1
            key = (r >> 5, g >> 5, b >> 5)
            counts[key] = counts.get(key, 0) + 1
    return {'width': width, 'height': height, 'dark': dark / max(1, total),
            'dominant': max(counts.values()) / max(1, total) if counts else 1.0}


def find_shot_browser():
    """The headless browser for the home screenshot: browser_env.find_browser (Chrome, Edge, Chromium; CDP_BROWSER /
    CHROME_PATH first) from cocos-game-to-english, else preview_chrome.find_chrome. None when there is none."""
    english = Path(__file__).resolve().parents[2] / 'cocos-game-to-english' / 'scripts'
    try:
        if english.is_dir() and str(english) not in sys.path:
            sys.path.append(str(english))
        import browser_env
        found = browser_env.find_browser()
        if found:
            return found
    except Exception:  # noqa: BLE001
        pass
    for key in ('CDP_BROWSER', 'CHROME_PATH'):
        if os.environ.get(key) and os.path.isfile(os.environ[key]):
            return os.environ[key]
    try:
        from preview_chrome import find_chrome
        return str(find_chrome())
    except (OSError, ImportError):
        return None


def home_shot_gate(shot_url, export_dir, phone_size, out_png, *, probe=None, browser=None, timeout=90, wait=12,
                   run=None):
    """生成时预防 P21 ⑤ (后半; 普查「进不去游戏」96 款 203 次, 试玩链接打不开 14 次): before a link a person opens is
    printed, an actual Ego Page takes one screenshot of the game page (the same page the phone frame shows).
    Returns (level, message, info). 'block' (no link): the picture is black or one flat colour, the page is still on
    the loading page (Cocos splash shown or no scene running), or the page reported an error. 'warn': no screenshot
    (no browser on this computer, browser failed or timed out, export without scripts) - the message says 没截图, it
    is never reported as passed. probe: callable returning the page probe report (dict) or None."""
    import subprocess
    import tempfile
    info = {'screenshot': None, 'browser': None}
    try:
        entry = (Path(export_dir) / 'index.html').read_bytes()
    except OSError:
        entry = b''
    if not re.search(br'<script\b', entry, re.I):
        return 'warn', '首页截图没截：导出的 index.html 里没有脚本，不像能跑的 Cocos 导出（没截图，不算通过）', info
    # EGO_ONLY_TEST_POLICY: the link's automatic check is a test; Chrome is the user's window only.
    import shutil
    import secrets
    ego = shutil.which('ego-browser')
    if not ego:
        return 'warn', '首页截图未执行：找不到官方 Ego CLI；不能用 Chrome 补测，未核对不算通过', info
    info['browser'] = ego
    info['browser_route'] = 'ego_taskspace'
    out_png = Path(out_png).resolve()
    try: out_png.unlink()
    except OSError: pass
    width, height = phone_size
    name = 'preview-home-%s-%s' % (os.getpid(), secrets.token_hex(4))
    info['space_name'] = name
    script = """const fs=await import('node:fs/promises');
const t=await taskSpace(%s),p=t.page('p1');
let finished=false;
try {
 await p.cdp('Network.enable',{});await p.cdp('Network.setCacheDisabled',{cacheDisabled:true});
 async function size(){await p.cdp('Emulation.setDeviceMetricsOverride',{width:%d,height:%d,deviceScaleFactor:1,mobile:true});await p.cdp('Emulation.setVisibleSize',{width:%d,height:%d});await p.cdp('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:5});}
 await size();await p.goto(%s);await size();
 const until=Date.now()+%d;while(Date.now()<until)await new Promise(r=>setTimeout(r,250));
 const image=await p.cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await fs.writeFile(%s,Buffer.from(image.data,'base64'));
 console.log(JSON.stringify({browser_route:'ego_taskspace',session_id:t.spaceId,space_name:%s,screenshot:%s}));
 await t.finish({keep:[]});finished=true;
}catch(e){console.error(String(e));throw e;}
""" % (json.dumps(name),width,height,width,height,json.dumps(shot_url),int(wait*1000),json.dumps(str(out_png)),json.dumps(name),json.dumps(str(out_png)))
    try:
        done=(run or subprocess.run)([ego,'nodejs','-e',script],stdin=subprocess.DEVNULL,capture_output=True,timeout=timeout)
        tail=(done.stderr or b'')[-300:].decode('utf-8','replace').strip()
    except subprocess.TimeoutExpired:
        return 'warn', '首页 Ego 截图超时；保留未测，不回退 Chrome', info
    except OSError as error:
        return 'warn', '首页 Ego 截图未执行：%s；不回退 Chrome' % error, info
    if done.returncode:
        return 'warn', '首页 Ego 截图或空间收尾未完成（%s）；保留未测，不回退 Chrome' % tail, info
    if not out_png.is_file():
        return 'warn', '首页截图没截成：浏览器退出码 %s，没写出图（%s）。没截图，不算通过' % (done.returncode, tail or '无输出'), info
    info['screenshot'] = str(out_png)
    try:
        stats = png_stats(out_png.read_bytes())
    except Exception as error:  # noqa: BLE001
        return 'warn', '首页截图读不了（%s）：%s。没核对，不算通过' % (error, out_png), info
    info['stats'] = stats
    report = probe() if probe else None
    info['probe'] = report
    problems = []
    if stats['dark'] >= 0.98:
        problems.append('首页截图几乎全黑（%.0f%% 像素是黑的）' % (stats['dark'] * 100))
    elif stats['dominant'] >= 0.995:
        problems.append('首页截图只有一种颜色（白屏或空画面）')
    if report:
        if report.get('errors'):
            problems.append('页面报错：' + '；'.join(report['errors'][:3]))
        if report.get('splash'):
            problems.append('%g 秒后还停在加载页（Cocos 启动页还在显示）' % wait)
        elif report.get('engine') and not report.get('scene'):
            problems.append('%g 秒后还停在加载页（引擎起来了，但还没有场景在跑）' % wait)
    if problems and b'System.import' in entry:
        # Cocos 3.x: one real 3.x export (BubbleAxolotl-English) was black with no scene in headless Chrome, not yet
        # checked on a 3.x export known to start, so 3.x only warns (like the other "3.x 未覆盖" checks)
        return 'warn', ('首页截图有问题（3.x 导出，还没校准，只警告）：%s。截图：%s，给链接前自己打开看，没看到首页不要给'
                        % ('；'.join(problems), out_png)), info
    if problems:
        return 'block', '不给试玩链接：%s。截图：%s' % ('；'.join(problems), out_png), info
    seen = '，场景 %s' % report['scene'] if report and report.get('scene') else ('，页面探针没回报' if not report else '')
    return 'pass', '首页截图核对通过（不是黑屏、不是纯色、没停在加载页、没报错%s）。截图：%s，给链接前自己看一眼' % (seen, out_png), info


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
    def __init__(self, *args, phone_size=None, preview_token=None, ad_simulator=False, ad_simulator_setup=None,
                 touch_bridge=False, **kwargs):
        self.phone_size = phone_size
        self.touch_bridge = touch_bridge      # P13 ④: mouse -> touch in the fixed-phone game page (user links)
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
        if request.path == '/__local_touch_bridge.js':
            if not self.touch_bridge:
                self.send_error(404)
                return
            self.send_bytes((Path(__file__).resolve().parent.parent / 'assets' / 'preview-touch-bridge.js').read_bytes(), 'application/javascript; charset=utf-8')
            return
        if request.path == '/__local_home_probe.js':
            self.send_bytes(HOME_PROBE_JS, 'application/javascript; charset=utf-8')
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
        query = parse_qs(request.query)
        script = b''
        if query.get('__home_shot') == ['1']:
            script += HOME_PROBE_TAG                # P21 ⑤: only the headless home screenshot page
        if self.touch_bridge and self.phone_size and query.get('__phone_game') == ['1']:
            script += TOUCH_BRIDGE_TAG              # P13 ④: only the game page inside the phone frame
        if self.ad_simulator:
            script += b'<script src="/__local_ad_simulator.js"></script>'
            if self.ad_simulator_setup:
                script += b'<script src="/__local_ad_simulator_setup.js"></script>'
        if script:
            path = Path(self.translate_path(self.path))
            # Apply to nested HTML exports as well. Only HTTP response bytes change.
            if path.suffix.lower() in ('.html', '.htm') and path.is_file():
                content = path.read_bytes()
                match = re.search(br'<head\b[^>]*>', content, re.I)
                pos = match.end() if match else 0
                content = content[:pos] + script + content[pos:]
                self.send_bytes(content, 'text/html; charset=utf-8')
                return
        super().do_GET()

    def do_POST(self):
        """P21 ⑤: the home screenshot probe reports here (latest report kept on the server object)."""
        if urlsplit(self.path).path != '/__local_home_probe':
            self.send_error(404)
            return
        try:
            body = self.rfile.read(min(int(self.headers.get('Content-Length') or 0), 65536))
            self.server.home_probe = json.loads(body.decode('utf-8'))
        except (ValueError, OSError):
            pass
        self.send_bytes(b'ok', 'text/plain')

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


def start_check_server(handler):
    """生成时预防 #40: a second loopback server with the same handler on a new port, for automated pages only (home
    screenshot, trial smoke). A browser keys localStorage by origin (scheme, host, port), so what the game saves there
    never shows up when a person opens the printed link. Returns (server, url)."""
    check = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=check.serve_forever, daemon=True).start()
    return check, f'http://127.0.0.1:{check.server_port}/'


def stop_check_server(check):
    try:
        check.shutdown()
        check.server_close()
    except Exception:  # noqa: BLE001
        pass


def _can_write(folder):
    """R4N3: True when a file can be created in `folder` (made if missing)."""
    probe = Path(folder) / ('.write-probe-%d-%s' % (os.getpid(), secrets.token_hex(3)))
    try:
        Path(folder).mkdir(parents=True, exist_ok=True)
        probe.write_bytes(b'')
        probe.unlink()
        return True
    except OSError:
        return False


def _project_of(export_dir, project=None):
    if project:
        return Path(project).resolve()
    for p in Path(export_dir).resolve().parents:
        if (p / 'assets').is_dir() and ((p / 'project.json').is_file() or (p / 'package.json').is_file()):
            return p
    return Path(export_dir).resolve().parent


def make_snapshot(directory, project=None, slots=None):
    """R4N3 (补查2 第 1 组 1c, 蛋壳特工队 `~/.game-skill-locks/web-snapshots` Operation not permitted): the private copy
    goes to the shared snapshot folder when it can be written, else to <project>/.tiktok-kit/snapshots/.
    -> (copy, where, own): where = 'shared' | 'project'; own = True when this script deletes the copy itself."""
    import shutil
    import uuid
    if slots is None:
        import browser_slots as slots
    src = Path(directory).resolve()
    if not (src / 'index.html').is_file():
        raise SystemExit('index.html not found in ' + str(src) + ' (give the finished web export folder)')
    if _can_write(slots.SNAPSHOTS):
        try:
            return slots.snapshot(src), 'shared', False
        except OSError:
            pass
    base = _project_of(src, project) / '.tiktok-kit' / 'snapshots'
    if not _can_write(base):
        raise SystemExit('快照目录都写不进：共享目录 %s 和工程里的 %s。换一个能写的工程副本再试，或去掉 --snapshot。'
                         % (slots.SNAPSHOTS, base))
    dest = base / (time.strftime('%m%d-%H%M%S') + '-' + src.name + '-' + uuid.uuid4().hex[:6])
    shutil.copytree(src, dest)
    return dest, 'project', True


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
    parser.add_argument('--home-shot-wait', type=float, default=12, help='headless home screenshot: seconds of page time '
                        'before the picture is taken (default 12)')
    parser.add_argument('--home-shot-timeout', type=float, default=90, help='headless home screenshot: give up after this '
                        'many seconds (default 90; then the link says 没截图)')
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
    current_export = directory                          # what the link must show (P21 ⑤), also with --snapshot
    if args.snapshot:
        if browser_slots is None:
            raise SystemExit('--snapshot needs browser_slots.py next to this script')
        directory, snap_where, snap_own = make_snapshot(directory, args.project, browser_slots)  # R4N3
        print('快照目录：%s（%s）' % (directory, '共享目录' if snap_where == 'shared' else
                                    '共享目录写不进，改用工程里的 .tiktok-kit/snapshots/'), flush=True)
    token = None if args.raw else secrets.token_hex(8)
    handler = partial(Handler, directory=str(directory), phone_size=None if args.raw else phone_size, preview_token=token,
                      ad_simulator=args.ad_simulator, ad_simulator_setup=args.ad_simulator_setup,
                      touch_bridge=not args.raw)
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
    for_person = args.keep or args.open or args.idle_minutes == 0
    if for_person:
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        # 生成时预防 P21 ⑤: a link a person opens is read back first; it must serve the current export's entry files
        ok, rows, problem = entry_readback(url, current_export, html_injected=args.ad_simulator)
        if not ok:
            print('不给试玩链接：%s。重新导出完、确认导出目录对了，再起一个新的预览服务。' % problem, file=sys.stderr, flush=True)
            server.shutdown()
            server.server_close()
            if slot:
                browser_slots.release(slot)
            raise SystemExit(1)
        print('试玩链接读回核对：入口 %d 个文件和现在的导出一字不差（%s）。' % (len(rows), '、'.join(r['file'] for r in rows)),
              flush=True)
        # 生成时预防 #40 (普查 trial_link_dead 14、stale_preview 10): the screenshot and the trial smoke play the game
        # and the game writes its save (localStorage) for the origin it runs on. They run on a second port of their
        # own (another origin, its own localStorage), so the link a person opens starts from a fresh save.
        check_server, check_url = start_check_server(handler)
        # 生成时预防 P21 ⑤ (后半): one headless screenshot of the game page before the link is printed
        import tempfile
        shot_url = check_url + ('__preview/%s/' % token if token else '') + 'index.html?__phone_game=1&__home_shot=1'
        check_server.home_probe = None
        level, message, _ = home_shot_gate(
            shot_url, current_export, phone_size,
            Path(tempfile.gettempdir()) / ('serve_preview_home_%d.png' % server.server_port),
            probe=lambda: getattr(check_server, 'home_probe', None), timeout=args.home_shot_timeout, wait=args.home_shot_wait)
        print(message, file=sys.stderr if level == 'block' else sys.stdout, flush=True)
        if level == 'block':
            stop_check_server(check_server)
            server.shutdown()
            server.server_close()
            if slot:
                browser_slots.release(slot)
            raise SystemExit(1)
    if args.keep:
        # v7.8 (总表 B21 / B30 F): the trial-link smoke runs on the same pages before the link is printed; a failure keeps
        # the link from the user (the ad window behind the game looked like a frozen game in 全民飞车漂移 v1-v3).
        # #40: on the check port, so the reward it earns is not in the save the user opens.
        level, message = trial_smoke_gate(check_url, directory, args.adapter, ad_simulator=args.ad_simulator)
        print(message, file=sys.stderr if level == 'block' else sys.stdout, flush=True)
        if level == 'block':
            stop_check_server(check_server)
            server.shutdown()
            server.server_close()
            if slot:
                browser_slots.release(slot)
            raise SystemExit(1)
    if for_person:
        stop_check_server(check_server)
        print('自动截图和冒烟用的是单独的检查端口，试玩链接 %s 没被自动打开过，存档是新的。' % url, flush=True)
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
        if args.snapshot and snap_own:                    # R4N3: a copy in the project's .tiktok-kit/snapshots/
            import shutil
            shutil.rmtree(directory, ignore_errors=True)


if __name__ == '__main__':
    main()
