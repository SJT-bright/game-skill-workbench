"""Startup gates (v7.5): progress, first frame, splash, local-file load guard, pre-home bytes.

G3_progress (block, Mabel's Meadow problem 2.1): a normal subpackage of at least 4,000,000 bytes, a 5-60 s
    no-progress timer in a root startup file, and no onFileProgress / onProgressUpdate in the root startup files.
    A download that is slow but alive then looks dead to the watchdog. Packages using the platform kit's own
    main.js subscribe to progress and pass.
G5_3x_presubpackage (block, LunasJade problem 1.1): Cocos 3.x game.js waits for loadSubpackage before
    application.start(), or settings preloadBundles names a normal subpackage over 2 MB and no root startup file
    takes the loading page over (overrideSettings('assets', 'preloadBundles', ...)). Either way the first frame
    waits for the whole subpackage download. The awaited form blocks on every board; the preloadBundles form blocks
    on board 'remake' and warns elsewhere (completed 3.x games kuaidi and huaxue preload 20-28 MB and completed).
G6_3x_splash (block on board 'remake', warn elsewhere; LunasJade problem 3): Cocos 3.x settings
    splashScreen.totalTime > 0 and no root startup file sets it to 0. The engine splash waits for img.onload, which
    the TikTok image object is not documented to fire. Completed 3.x games (kuaidi, tiaoyueniao, mishi, huaxue)
    ship totalTime 2000, so outside the remake board it is a warning.
G7_file_load_guard (block, MergeShot2048 v82 item 1): a custom downloader/parser guard in package code fails a
    local file after less than 20 s with no second attempt (maxRetryCount 0, late answers dropped). On a real
    iPhone package files can answer late; v81 lost its home-page buttons this way.
W8_prehome_bytes (warn, MusicSlice problem 6.3): main package plus subpackages loaded before the home page exceed
    15 MB. pre_home_bytes(view) returns the numbers for reports. v7.8 (S8 补): this is the static estimate (load
    names read from the startup code); the runtime suite layout_state measures the same thing in the host
    (subpackages requested before EVENT_BEFORE_SCENE_LOADING of the home scene) and refuses a new game over 10 MiB or
    with sound in it. W8 stays a warning so the two never disagree on a refusal; check_package reports both
    (pre_home_bytes and pre_home_bytes.measured).
G9_doc_hidden_clock / G9_dom_retry (block, Finger Mahjong v57): game code times foreground with document.hidden /
    visibilityState and has no onHide / EVENT_HIDE nearby, or draws a Retry with DOM elements and never calls
    showModal. TikTok keeps document.hidden false and draws no DOM; v57 locked its home page this way. The runtime
    half is the startup suite's lifecycle cases (clock jump, background, hung image, then a real PLAY tap).
"""
import json
import re

from . import finding

BIG_SUBPACKAGE = 4000000
PRESUB_3X_LIMIT = 2 * 1024 * 1024
PREHOME_WARN = 15 * 1000 * 1000
FILE_GUARD_MIN_MS = 20000

STALL = re.compile(r'Date\.now\(\)\s*-\s*[\w.$\[\]]+\s*>=?\s*(\d{4,6})|(\d{4,6})\s*<=?\s*Date\.now\(\)\s*-|'
                   r'setTimeout\([^)]{0,200}?,\s*(\d{4,6})\s*\)')
PROGRESS = re.compile(r'onFileProgress|onProgressUpdate')
GUARD_REGISTER = re.compile(r'(?:downloader|parser|_downloaders)\b[\w.\[\]\'"]*\.register\s*\(|'
                            r'\b(?:downloader|parser)\.register\s*\(')
RETRY_ZERO = re.compile(r'maxRetryCount\s*[:=]\s*0\b')
RETRY_MORE = re.compile(r'\battempts?\b|parallelAfter|\bretr(?:y|ies)\w*\s*[(<]|re-?issue|'
                        r'maxRetryCount\s*[:=]\s*[1-9]|retryCount\s*[:=]\s*[1-9]', re.I)
GUARD_NUMBERS = (
    re.compile(r'(?:>=?|<=?)\s*(\d{4,6})\b'),
    re.compile(r'\b(?:budget|timeout\w*|giveUp|limit\w*|deadline\w*|\w*Ms)\s*[:=]\s*([^,;)}]{0,60})', re.I),
)
OVERRIDE_PRELOAD = re.compile(r'overrideSettings\s*\(\s*["\']assets["\']\s*,\s*["\']preloadBundles["\']')
OVERRIDE_SPLASH = re.compile(r'overrideSettings\s*\(\s*["\']splashScreen["\']\s*,\s*["\']totalTime["\']\s*,\s*0\s*\)')
LOAD_NAME = re.compile(r'loadSubpackage\s*\(\s*\{[^}]{0,300}?\bname\s*:\s*["\']([^"\']+)["\']|'
                       r'loadSubpackage\s*\(\s*["\']([^"\']+)["\']|loadBundle\s*\(\s*["\']([^"\']+)["\']')


def _remake_level(view):
    # Completed 3.x games (kuaidi, tiaoyueniao, mishi, huaxue) ship splash 2000 and preload a 20-28 MB resources
    # bundle and still completed on TikTok, so these two stay warnings outside the remake board.
    return 'block' if view.board == 'remake' else 'warn'


def _root_js(view):
    return [n for n in view.game_js() if '/' not in n]


def _subpackage_bytes(view):
    sizes = {}
    for sub in view.subpackages:
        sizes[sub['root']] = sum(len(v) for k, v in view.files.items() if k.startswith(sub['root']))
    return sizes


def _settings_3x(view):
    for name in ('src/settings.json',):
        if name in view.files:
            try:
                data = json.loads(view.files[name].decode('utf-8-sig'))
                return data if isinstance(data, dict) else {}
            except (ValueError, UnicodeDecodeError):
                return {}
    return {}


def _sub_by_name(view, name):
    for sub in view.subpackages:
        if sub['name'] == name or sub['root'].rstrip('/').split('/')[-1] == name:
            return sub
    return None


def check_progress(view):
    sizes = _subpackage_bytes(view)
    big = [(s['root'], sizes[s['root']]) for s in view.subpackages
           if not s['independent'] and sizes[s['root']] >= BIG_SUBPACKAGE]
    if not big:
        return []
    roots = _root_js(view)
    stall = []
    for name in roots:
        for match in STALL.finditer(view.text(name)):
            ms = int(next(g for g in match.groups() if g))
            if 5000 <= ms <= 60000:
                stall.append((name, ms))
    has_progress = any(PROGRESS.search(view.text(n)) for n in roots)
    if stall and not has_progress:
        return [finding('G3_progress', 'block',
                        'subpackage %s (%d bytes) loads under a %d ms no-progress timer in %s, but no root startup '
                        'file subscribes to onFileProgress/onProgressUpdate, so a slow download is judged dead'
                        % (big[0][0], big[0][1], stall[0][1], stall[0][0]),
                        {'big_subpackages': big, 'stall_timers': stall[:6]})]
    return []


def _chain_before_start(text):
    """Text of game.js from the engine import up to application.start()."""
    end = text.find('application.start')
    if end < 0:
        return ''
    begin = text.rfind("System.import('cc')", 0, end)
    if begin < 0:
        begin = text.rfind('System.import("cc")', 0, end)
    return text[max(begin, 0):end]


def _module_function_loads(view, module_file, fn):
    if module_file not in view.files:
        return False
    text = view.text(module_file)
    match = re.search(r'exports\.%s\s*=\s*function' % re.escape(fn), text)
    if not match:
        return False
    nxt = text.find('exports.', match.end())
    body = text[match.end(): nxt if nxt > 0 else len(text)]
    return 'loadSubpackage' in body or 'loadBundle' in body


def check_3x(view):
    if view.engine_major != 3:
        return []
    out = []
    roots = _root_js(view)
    roots_text = '\n'.join(view.text(n) for n in roots)
    sizes = _subpackage_bytes(view)
    # G5a: game.js waits for a subpackage before application.start()
    if 'game.js' in view.files:
        text = view.text('game.js')
        chain = _chain_before_start(text)
        waits = []
        if re.search(r'loadSubpackage|loadBundle', chain):
            waits.append('game.js')
        requires = dict(re.findall(r'(?:var|let|const)\s+(\w+)\s*=\s*require\(\s*["\']\./([\w.-]+?)(?:\.js)?["\']\s*\)', text))
        # Only calls the chain waits for: `.then(() => x.y(`, `.then(function () { return x.y(`, `await x.y(`.
        # A delegate registration such as onPostBaseInitDelegate.add(() => boot.configure(cc)) does not block.
        awaited = re.findall(r'(?:\.then\(\s*(?:\(\s*\)|\w+)\s*=>\s*\{?\s*(?:return\s+)?|'
                             r'\.then\(\s*function\s*\(\s*\w*\s*\)\s*\{\s*return\s+|\bawait\s+)(\w+)\.(\w+)\s*\(', chain)
        for obj, fn in awaited:
            module = requires.get(obj)
            if module and _module_function_loads(view, module + '.js', fn):
                waits.append('%s.%s() in %s.js' % (obj, fn, module))
        if waits:
            out.append(finding('G5_3x_presubpackage', 'block',
                               'game.js waits for loadSubpackage (%s) before application.start(): the first frame '
                               'waits for the whole subpackage download' % ', '.join(waits), {'waits': waits}))
    # G5b: preloadBundles names a big normal subpackage, no loading-page takeover
    settings = _settings_3x(view)
    preload = ((settings.get('assets') or {}).get('preloadBundles') or [])
    if not OVERRIDE_PRELOAD.search(roots_text):
        heavy = []
        for entry in preload:
            name = entry.get('bundle') if isinstance(entry, dict) else entry
            sub = _sub_by_name(view, name) if isinstance(name, str) else None
            if sub and not sub['independent'] and sizes.get(sub['root'], 0) > PRESUB_3X_LIMIT:
                heavy.append((name, sizes[sub['root']]))
        if heavy:
            out.append(finding('G5_3x_presubpackage', _remake_level(view),
                               'settings preloadBundles makes the engine download subpackage %s (%d bytes) before the '
                               'first frame and no loading page takes it over' % heavy[0], {'preload': heavy}))
    # G6: engine splash waits for img.onload
    splash = settings.get('splashScreen') or {}
    total = splash.get('totalTime') if isinstance(splash, dict) else None
    if isinstance(total, (int, float)) and total > 0 and not OVERRIDE_SPLASH.search(roots_text):
        out.append(finding('G6_3x_splash', _remake_level(view),
                           'settings splashScreen.totalTime is %s: the 3.x engine splash waits for img.onload; set it '
                           'to 0 and show the Cocos logo on the loading page' % total, {'totalTime': total}))
    return out


def _strip_comments(text):
    # Comments such as "retries are owned by bounded()" must not count as a retry.
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    return re.sub(r'(^|[\s;{}])//[^\n]*', r'\1', text)


def _guard_timeouts(text):
    numbers = []
    for match in GUARD_NUMBERS[0].finditer(text):
        numbers.append(int(match.group(1)))
    for match in GUARD_NUMBERS[1].finditer(text):
        numbers += [int(x) for x in re.findall(r'\b(\d{4,6})\b', match.group(1))]
    return [n for n in numbers if 1000 <= n <= 120000]


def check_file_guard(view):
    out = []
    for name in view.game_js():
        text = view.text(name)
        if not GUARD_REGISTER.search(text) or not re.search(r'_downloaders|downloadDomImage|assetManager', text):
            continue
        # Only the guard region: from the first register call, at most 20 kB.
        start = GUARD_REGISTER.search(text).start()
        region = _strip_comments(text[max(0, start - 4000): start + 20000])
        timeouts = _guard_timeouts(region)
        if not timeouts:
            continue
        fatal = max(timeouts)
        retries = bool(RETRY_MORE.search(RETRY_ZERO.sub('', region)))
        if fatal < FILE_GUARD_MIN_MS and not retries:
            # v7.5: warning, not block - the same static pattern ships in device-tested Mosslight v20 (cross-game
            # summary conflict C10); the hard check belongs in the runtime startup suite (image hang cases).
            out.append(finding('G7_file_load_guard', 'warn',
                               '%s fails a package file after at most %d ms with no second attempt%s; local files can '
                               'answer late on a real phone. Re-issue after 10 s, first answer wins, fail only after '
                               '30 s of foreground time' % (name, fatal,
                                                             ' (maxRetryCount 0)' if RETRY_ZERO.search(region) else ''),
                               {'file': name, 'timeouts_ms': sorted(set(timeouts))}))
    return out


def pre_home_bytes(view):
    """Main package bytes plus the subpackages the startup loads before the home page."""
    main = sum(len(view.files[n]) for n in view.main_files())
    names = set()
    for n in _root_js(view):
        for groups in LOAD_NAME.findall(view.text(n)):
            names.update(g for g in groups if g)
    if view.engine_major == 3:
        preload = ((_settings_3x(view).get('assets') or {}).get('preloadBundles') or [])
        names.update(e.get('bundle') for e in preload if isinstance(e, dict) and isinstance(e.get('bundle'), str))
    else:
        names.update(('resources', 'main', 'internal'))   # Cocos 2.4 main.js loads these before the launch scene
    sizes = _subpackage_bytes(view)
    subs = {}
    for name in sorted(names):
        sub = _sub_by_name(view, name)
        if sub:
            subs[sub['root']] = sizes[sub['root']]
    return {'main_bytes': main, 'subpackages': subs, 'total_bytes': main + sum(subs.values())}


def check_prehome(view):
    info = pre_home_bytes(view)
    if info['total_bytes'] > PREHOME_WARN:
        return [finding('W8_prehome_bytes', 'warn',
                        'about %.1f MB must download before the home page (main %.1f MB + %s); over 15 MB keeps '
                        'players on the TikTok spinner on a slow network. Static estimate from the startup code; the '
                        'measured number (runtime suite layout_state, 10 MiB and no sound, v7.8 S8) is the one that '
                        'refuses'
                        % (info['total_bytes'] / 1e6, info['main_bytes'] / 1e6,
                           ', '.join('%s %.1f MB' % (k, v / 1e6) for k, v in info['subpackages'].items()) or 'no subpackage'),
                        info)]
    return []


def check(view):
    return check_progress(view) + check_3x(view) + check_file_guard(view) + check_prehome(view) + check_lifecycle(view)


# G9 (Finger Mahjong v57, 10-30): TikTok keeps document.hidden false, never fires visibilitychange and draws no
# DOM. v57's own loading watchdog timed "foreground" with document.hidden (lock-screen time became a stall) and
# showed its Retry as a DOM <div>, invisible on the phone, while the home buttons waited for it forever.
DOC_STATE = re.compile(r'document\.(?:hidden|visibilityState)\b')
HIDE_HOOK = re.compile(r'EVENT_HIDE|\bonHide\b|\boffHide\b|game\.on\(\s*[\'"]hide')
CLOCK = re.compile(r'Date\.now\(\)|performance\.now\(\)')
# A clock that adds at most 1 s per tick cannot turn a frozen thread into a stall (BalloonRun v55 frame guard).
TICK_CAP = re.compile(r'Math\.min\(\s*(?:1|1e3|1000)\s*,|Math\.min\([^;]{0,80}?,\s*(?:1|1e3|1000)\s*\)')
DOM_APPEND = re.compile(r'document\.(?:body|documentElement)\.appendChild\s*\(')
DOM_MAKE = re.compile(r'createElement\(\s*[\'"](?:div|button|p|span|a)[\'"]')
RETRY_WORD = re.compile(r'Retry|RETRY|Try again|TRY AGAIN|Reload|RELOAD|重试|重新加载')
NATIVE_DIALOG = re.compile(r'showModal\s*\(|showModal\s*:|\.showModal\b')
DEAD_IF = re.compile(r'if\s*\(\s*(?:false|!1|0)\s*\)\s*\{')


def _in_dead_branch(code, pos):
    """True when pos sits inside an `if (false) {` / `if(!1){` block that opens at most 3000 chars before it."""
    start = max(0, pos - 3000)
    last = None
    for last in DEAD_IF.finditer(code, start, pos):
        pass
    if not last:
        return False
    span = code[last.end():pos]
    return span.count('{') - span.count('}') >= 0


def check_lifecycle(view):
    out = []
    for name in view.game_js():
        text = view.text(name)
        if 'document.' not in text:
            continue
        code = _strip_comments(text)
        for m in DOC_STATE.finditer(code):
            near = code[max(0, m.start() - 600): m.end() + 600]
            module = code[max(0, m.start() - 3000): m.end() + 3000]
            if not CLOCK.search(near) or HIDE_HOOK.search(module) or TICK_CAP.search(near):
                continue
            # Calibration (10-30, 157 packages): a hook elsewhere in a bundled file may feed this clock
            # (Tangos v77 setBackground, PorcelainKiln restore-boot), so that case only warns.
            level = 'warn' if HIDE_HOOK.search(code) else 'block'
            line = code.count('\n', 0, m.start()) + 1
            out.append(finding('G9_doc_hidden_clock', level,
                               '%s line %d times foreground with %s and no onHide / cc.game EVENT_HIDE nearby. '
                               'TikTok keeps it false, so lock-screen and background time count as a stall. Use '
                               'tt.onHide/onShow or cc.game hide/show, and count at most 1 s per tick'
                               % (name, line, m.group(0)),
                               {'file': name, 'line': line, 'code': code[max(0, m.start() - 120): m.end() + 120]}))
            break
        for m in DOM_APPEND.finditer(code):
            around = code[max(0, m.start() - 3000): m.end() + 600]
            if _in_dead_branch(code, m.start()):
                continue      # TrashPanda v0.2 main.js: the web panel sits in `if (false) {`, the native one runs
            if DOM_MAKE.search(around) and RETRY_WORD.search(around) and \
                    not NATIVE_DIALOG.search(code[max(0, m.start() - 6000): m.end() + 6000]):
                line = code.count('\n', 0, m.start()) + 1
                out.append(finding('G9_dom_retry', 'block',
                                   '%s line %d draws a Retry with DOM elements; TikTok draws no DOM, so the player '
                                   'sees nothing. Show it with tt.showModal or on the canvas' % (name, line),
                                   {'file': name, 'line': line}))
                break
    return out
