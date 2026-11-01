"""Network / bundle-name / cross-promotion gates (v7.5, W1a).

H12_bundle_name     (block) game JS loads a bundle/subpackage by name that the package does not have
                    (MusicSlice v29b loadSubpackage('general'), GooglyEyeRecall). Ported from the completed-game
                    gate tiktok_upload_gate.py (known_bundles / missing_bundle_refs), calibrated 0 false blocks.
H13_analytics_domain (block) game JS carries a Chinese analytics SDK report host (Tencent MTA pas.qq.com /
                    mta.qq.com, Umeng, CNZZ, Baidu Tongji, TalkingData, Aldwx, GrowingIO, Zhuge): TikTok only
                    reaches domains registered in the developer console, so these never work there.
H14_cross_promo     (block) game JS calls navigateToMiniProgram / showMoreGamesModal or carries another mini
                    game's App ID (tt/wx + 16 hex). An emptied component that keeps only its field names has
                    none of these strings and passes (MergeShot2048 v83/v84).
Engine and platform-adapter files are never scanned (see package_gates.PackageView.game_js).

v7.9 (phone-only failures, task A; block for a new game, warn for a legacy game):
H15_package_read_via_request  game JS reads a package file through cc.assetManager.downloader.downloadFile (2.4/3.x
                    mini-game: XMLHttpRequest = tt.request, https only) outside a browser-only branch, or opens
                    an XMLHttpRequest / tt.request on a literal non-https path. Pinecone check_build_2415: the boot
                    loader read 5 package files this way, the phone stayed on "Loading failed"; fix1 moves the call
                    into if(cc.sys.isBrowser){...} and uses the engine pipeline on the phone.
H16_font_path_as_family  the callback result of downloader._downloaders['.ttf'|'.otf'|'.woff'] (a FILE PATH on the
                    mini-game) is stored as cc.Font _nativeAsset / fontFamily: every label falls back to ~10 px
                    system text on the phone (Pinecone check_build_2415; fix1 loads the font through cc.resources).
H17_resource_path_missing  a literal path given to cc.resources.load/loadDir, cc.loader.loadRes/loadResDir, or
                    <bundle>.load/loadDir (bundle known from a literal getBundle/loadBundle name in the same file)
                    that no bundle config of the package lists. Paths built with + or variables are skipped
                    (Junos 'art'+x subpackage, object-pool aliases): those stay runtime-suite work.
"""
import json
import posixpath
import re

from . import finding

LOAD_NAME = re.compile(r'''\b(?:loadBundle|loadSubpackage|loadSubPackage|preDownloadSubpackage)\s*\(\s*'''
                       r'''(?:\{\s*name\s*:\s*)?(['"])([A-Za-z0-9_\-]{1,64})\1''')
BUILTIN_BUNDLES = {'internal', 'main', 'resources', 'start-scene'}
SETTINGS = re.compile(r'(^|/)src/settings[^/]*\.(js|json)$')

ANALYTICS = re.compile(
    r'(?<![A-Za-z0-9.\-])((?:[A-Za-z0-9\-]+\.)*(?:pas\.qq\.com|mta\.qq\.com|pingma\.qq\.com|umeng\.com|umengcloud\.com|'
    r'cnzz\.com|hm\.baidu\.com|talkingdata\.com|talkingdata\.net|tenddata\.com|aldwx\.com|growingio\.com|'
    r'zhugeio\.com))(?![A-Za-z0-9\-])', re.I)
CROSS_PROMO = re.compile(r'\b(navigateToMiniProgram|showMoreGamesModal)\b')
FOREIGN_APP_ID = re.compile(r'''(['"])((?:tt|wx)[0-9a-f]{16})\1''')


def known_bundles(view):
    names = set(BUILTIN_BUNDLES)
    for sub in view.game_json.get('subpackages') or view.game_json.get('subPackages') or []:
        if not isinstance(sub, dict):
            continue
        for key in ('name', 'root'):
            value = str(sub.get(key) or '').strip().strip('/')
            if value:
                names.add(value)
                names.add(value.split('/')[-1])
    for name in view.files:
        parts = name.split('/')
        if len(parts) > 2 and parts[0] in ('assets', 'subpackages', 'remote'):
            names.add(parts[1])
        if len(parts) > 3 and parts[0] == 'subpackages' and parts[2] == 'assets':
            names.add(parts[3])
    for name in view.files:
        if not SETTINGS.search(name):
            continue
        text = view.text(name)
        names.update(re.findall(r'["\']?([A-Za-z0-9_\-]{1,64})["\']?\s*:\s*["\'][0-9a-f]{5}["\']', text))
        for block in re.findall(r'(?:subpackages|remoteBundles|projectBundles|preloadBundles)["\']?\s*:\s*\[([^\]]*)\]', text):
            names.update(re.findall(r'["\']([^"\']{1,64})["\']', block))
    return names


def _scanned(view):
    """Game JavaScript only; 'adapter' in the file name is also skipped (same rule as the calibrated gate)."""
    return [n for n in view.game_js() if 'adapter' not in posixpath.basename(n).lower()]


def missing_bundle_refs(view):
    known = known_bundles(view)
    found = {}
    for name in _scanned(view):
        for match in LOAD_NAME.finditer(view.text(name)):
            bundle = match.group(2)
            if bundle not in known:
                found.setdefault(bundle, name)
    return found


def _context(text, match, width=60):
    start, end = max(0, match.start() - width), min(len(text), match.end() + width)
    return text[start:end].replace('\n', ' ')


def analytics_hits(view):
    hits = []
    for name in _scanned(view):
        text = view.text(name)
        for match in ANALYTICS.finditer(text):
            if match.group(1).lower().startswith(('doc.', 'docs.', 'developer.')):
                continue          # documentation links (e.g. doc.aldwx.com in a .d.ts), not a report host
            hits.append({'file': name, 'host': match.group(1).lower(), 'context': _context(text, match)})
    return hits


def cross_promo_hits(view):
    try:
        own = str(json_appid(view) or '')
    except (ValueError, UnicodeDecodeError):
        own = ''
    hits = []
    for name in _scanned(view):
        text = view.text(name)
        for match in CROSS_PROMO.finditer(text):
            hits.append({'file': name, 'match': match.group(1), 'context': _context(text, match)})
        for match in FOREIGN_APP_ID.finditer(text):
            if match.group(2) != own:
                hits.append({'file': name, 'match': match.group(2), 'context': _context(text, match)})
    return hits


def json_appid(view):
    raw = view.files.get('project.config.json')
    if not raw:
        return None
    data = json.loads(raw.decode('utf-8-sig'))
    return data.get('appid') if isinstance(data, dict) else None


# ---------------------------------------------------------------- v7.9 H15 / H16 / H17 (package-local files)

REGEX_PREV = set('(,=:[!&|?{};+-*%<>~^') | {''}


def _pairs(text):
    """{open: close} and {close: open} for braces and parens, skipping strings, comments and regex literals
    (minified-code heuristic). Computed once per file and only when a candidate call is present."""
    opens, close_of, open_of = [], {}, {}
    i, n, prev = 0, len(text), ''
    while i < n:
        c = text[i]
        if c in '"\'`':
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == '\\' else 1
            i, prev = j + 1, 'a'
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '/':
            j = text.find('\n', i)
            i = n if j < 0 else j
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '*':
            j = text.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == '/' and prev in REGEX_PREV:
            j, klass = i + 1, False
            while j < n and text[j] != '\n':
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == '[':
                    klass = True
                elif text[j] == ']':
                    klass = False
                elif text[j] == '/' and not klass:
                    break
                j += 1
            i, prev = j + 1, 'a'
            continue
        if c in '{(':
            opens.append(i)
        elif c in '})' and opens:
            o = opens.pop()
            close_of[o], open_of[i] = i, o
        if not c.isspace():
            prev = c
        i += 1
    return close_of, open_of


class _Code:
    def __init__(self, text):
        self.text = text
        self._p = None

    def pairs(self):
        if self._p is None:
            self._p = _pairs(self.text)
        return self._p

    def enclosing(self, pos):
        """'{' positions of the blocks around pos, innermost first."""
        close_of, _ = self.pairs()
        return sorted((o for o, c in close_of.items() if self.text[o] == '{' and o < pos < c), reverse=True)

    def if_condition(self, brace):
        """Condition text of `if(COND){` for the block opening at brace, else None."""
        text = self.text
        j = brace - 1
        while j >= 0 and text[j].isspace():
            j -= 1
        if j < 0 or text[j] != ')':
            return None
        _, open_of = self.pairs()
        o = open_of.get(j)
        if o is None or not re.search(r'(?<![\w$])if\s*$', text[max(0, o - 8):o]):
            return None
        return text[o + 1:j]

    def else_of(self, brace):
        """For `...}else{` return the condition of the matching if, else None."""
        text = self.text
        head = text[max(0, brace - 12):brace]
        if not re.search(r'(?<![\w$])else\s*$', head):
            return None
        j = brace - 1
        while text[j].isspace():
            j -= 1
        j -= 4                          # before 'else'
        while j >= 0 and text[j].isspace():
            j -= 1
        if j < 0 or text[j] != '}':
            return None
        _, open_of = self.pairs()
        o = open_of.get(j)
        return None if o is None else self.if_condition(o)


BROWSER_TOKEN = re.compile(r'((?:[\w$]+\.)*)isBrowser\b')
# s=!0===cc.sys.isBrowser / s=cc.sys.isBrowser (JaspersKelp keeps the test in a local and branches on it later)
BROWSER_ALIAS = re.compile(r'(?<![\w$.])([\w$]+)\s*=\s*(?:!0\s*===?\s*)?(?:[\w$]+\.)*isBrowser(?:\s*===?\s*!0)?'
                           r'\s*(?=[,;)}])')
# a platform API that is missing (only true off the phone): !r, "function"!=typeof r.x, "undefined"==typeof tt
API_MISSING = re.compile(r'''\s*\(?\s*(?:!\s*[\w$.]+|(["'])function\1\s*!==?\s*typeof\s+[\w$.]+|'''
                         r'''typeof\s+[\w$.]+\s*!==?\s*(["'])function\2|(["'])undefined\3\s*===?\s*typeof\s+[\w$.]+|'''
                         r'''typeof\s+[\w$.]+\s*===?\s*(["'])undefined\4)\s*\)?\s*''')
# a platform API that is present (true on the phone): cc.sys.isNative, fs&&fs.getFileSystemManager, typeof tt!="undefined"
API_PRESENT = re.compile(r'''\s*\(?\s*(?:(?:[\w$]+\.)*isNative|(?:[\w$]+\s*&&\s*)?[\w$]+(?:\.[\w$]+)*\.'''
                         r'''(?:getFileSystemManager|readFile)|(["'])function\1\s*===?\s*typeof\s+[\w$.]+\.'''
                         r'''(?:getFileSystemManager|readFile)|typeof\s+(?:tt|wx|TTMinis)\s*!==?\s*(["'])undefined\2)'''
                         r'''\s*\)?\s*''')


def _split_top(cond, op):
    parts, depth, last, i = [], 0, 0, 0
    while i < len(cond):
        c = cond[i]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif depth == 0 and cond.startswith(op, i):
            parts.append(cond[last:i])
            last = i + len(op)
            i += len(op)
            continue
        i += 1
    parts.append(cond[last:])
    return parts


def _browser_sense(cond, aliases=()):
    """'pos' when cond only holds in a browser (cc.sys.isBrowser [&& ...], or isBrowser || <platform API missing>),
    'neg' for !isBrowser [|| ...]."""
    token = BROWSER_TOKEN if not aliases else re.compile(
        r'((?:[\w$]+\.)*)isBrowser\b|((?<![\w$.]))(?:%s)(?![\w$])' % '|'.join(re.escape(a) for a in aliases))
    senses = set()
    for m in token.finditer(cond):
        before = cond[:m.start()].rstrip()
        after = cond[m.end():m.end() + 8]
        neg = before.endswith('!') or re.match(r'\s*(?:===?\s*(?:!1|false)|!==?\s*(?:!0|true))', after)
        senses.add('neg' if neg else 'pos')
    if senses == {'pos'}:
        if '||' not in cond:
            return 'pos'
        terms = _split_top(cond, '||')
        if all(token.search(t) or API_MISSING.fullmatch(t) for t in terms):
            return 'pos'                # cc.sys.isBrowser || !tt || "function"!=typeof tt.getFileSystemManager
        return None
    if senses == {'neg'} and '&&' not in cond:
        return 'neg'
    if senses <= {'neg'}:               # if(cc.sys.isNative || fs && fs.getFileSystemManager){phone}else{browser}
        terms = _split_top(cond, '||')
        if all(API_PRESENT.fullmatch(t) or (token.search(t) and '&&' not in t) for t in terms):
            return 'neg'
    return None


def _aliases(code, before):
    """Locals holding cc.sys.isBrowser assigned in the 3000 characters before the branch."""
    window = code.text[max(0, before - 3000):before]
    return tuple(sorted({m.group(1) for m in BROWSER_ALIAS.finditer(window)}))


def _browser_only(code, pos):
    """True when the call at pos sits in a branch that runs only in a web browser (never on the phone)."""
    text = code.text
    cut = max(text.rfind(';', 0, pos), text.rfind('{', 0, pos), text.rfind('}', 0, pos))
    segment = text[cut + 1:pos]
    for m in BROWSER_TOKEN.finditer(segment):           # cc.sys.isBrowser ? x.downloadFile(...) / && / if(...)x
        if not segment[:m.start()].rstrip().endswith('!') and re.match(r'\s*(?:\?|&&|\))', segment[m.end():]):
            tail = segment[m.end():]
            if not (tail.lstrip().startswith('?') and ':' in tail):
                return True
    for brace in code.enclosing(pos):
        aliases = _aliases(code, brace)
        cond = code.if_condition(brace)
        if cond is not None and _browser_sense(cond, aliases) == 'pos':
            return True
        cond = code.else_of(brace)
        if cond is not None and _browser_sense(cond, aliases) == 'neg':
            return True
    return False


DOWNLOAD_FILE = re.compile(r'\bdownloader\s*\.\s*downloadFile\s*\(')
XHR_OPEN = re.compile(r'''\.open\(\s*(["'])(?:GET|POST|HEAD|get|post)\1\s*,\s*''')
TT_REQUEST = re.compile(r'''\b(?:tt|wx|swan|qq)\s*\.\s*request\s*\(\s*\{''')
REMOTE = re.compile(r'''^\s*(["'`])(?:https?:)?//''')
LOCAL_URL_HINT = re.compile(r'nativeUrl|getUrlWithUuid|url\.raw|transformUrl|nativeBase|importBase')


def _argument(text, start):
    """The expression from start up to the first top-level ',' or ')' (short, for evidence and literal tests)."""
    depth, i, quote = 0, start, None
    while i < len(text) and i - start < 400:
        c = text[i]
        if quote:
            if c == '\\':
                i += 1
            elif c == quote:
                quote = None
        elif c in '"\'`':
            quote = c
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            if depth == 0:
                break
            depth -= 1
        elif c == ',' and depth == 0:
            break
        i += 1
    return text[start:i].strip()


def _local_literal(expr):
    m = re.fullmatch(r'''(["'])([^"'\\]+)\1''', expr)
    if not m:
        return False
    value = m.group(2)
    return not re.match(r'(?:[a-z][a-z0-9+.\-]*:|//)', value, re.I)


def package_read_hits(view):
    hits = []
    for name in _scanned(view):
        text = view.text(name)
        code = None
        candidates = []
        for m in DOWNLOAD_FILE.finditer(text):
            arg = _argument(text, m.end())
            if not REMOTE.match(arg):
                candidates.append((m, 'downloader.downloadFile', arg))
        if 'XMLHttpRequest' in text:
            for m in XHR_OPEN.finditer(text):
                arg = _argument(text, m.end())
                if _local_literal(arg) or (not REMOTE.match(arg) and LOCAL_URL_HINT.search(arg)):
                    candidates.append((m, 'XMLHttpRequest.open', arg))
        for m in TT_REQUEST.finditer(text):
            u = re.match(r'''\s*url\s*:\s*''', text[m.end():m.end() + 20])
            if u:
                arg = _argument(text, m.end() + u.end())
                if _local_literal(arg) or (not REMOTE.match(arg) and LOCAL_URL_HINT.search(arg)):
                    candidates.append((m, 'tt.request', arg))
        for m, kind, arg in candidates:
            code = code or _Code(text)
            if _browser_only(code, m.start()):
                continue
            hits.append({'file': name, 'call': kind, 'url': arg[:80], 'context': _context(text, m)})
    return hits


FONT_LOADER = re.compile(r'''([\w$]+)\s*=\s*(?:[\w$]+\.)*_downloaders\s*\[\s*(["'])\.(?:ttf|otf|woff2?)\2\s*\]''')
FONT_DIRECT = re.compile(r'''_downloaders\s*\[\s*(["'])\.(?:ttf|otf|woff2?)\1\s*\]\s*\(''')
CALLBACK = re.compile(r'''\s*(?:function\s*\(\s*[\w$]+\s*,\s*([\w$]+)\s*\)|\(\s*[\w$]+\s*,\s*([\w$]+)\s*\)\s*=>)\s*\{''')


def _callback_result_as_family(code, call_open):
    """call_open = index of '(' of loader(url, options, callback): does the callback store its result as the
    font family (x._nativeAsset = result / x.fontFamily = result)?"""
    text = code.text
    close_of, _ = code.pairs()
    end = close_of.get(call_open)
    if end is None:
        return None
    inner = text[call_open + 1:end]
    for m in re.finditer(r',', inner):
        cb = CALLBACK.match(inner, m.end())
        if not cb:
            continue
        result = cb.group(1) or cb.group(2)
        body = inner[cb.end():]
        store = re.search(r'\.\s*(_nativeAsset|fontFamily)\s*=\s*' + re.escape(result) + r'(?![\w$])', body)
        if store:
            at = call_open + 1 + cb.end() + store.start()
            return text[max(0, at - 80):at + 40].replace('\n', ' ')
    return None


def font_path_hits(view):
    hits = []
    for name in _scanned(view):
        text = view.text(name)
        if '_downloaders' not in text:
            continue
        code = _Code(text)
        for m in FONT_LOADER.finditer(text):
            var = m.group(1)
            for call in re.finditer(r'(?<![\w$.])' + re.escape(var) + r'\s*\(', text[m.end():m.end() + 1500]):
                fragment = _callback_result_as_family(code, m.end() + call.end() - 1)
                if fragment:
                    hits.append({'file': name, 'loader': m.group(0)[:60], 'context': fragment})
                    break
        for m in FONT_DIRECT.finditer(text):
            fragment = _callback_result_as_family(code, m.end() - 1)
            if fragment:
                hits.append({'file': name, 'loader': m.group(0)[:60], 'context': fragment})
    return hits


BUNDLE_CONFIG = re.compile(r'(?:^|/)(?:assets|subpackages|remote)/([^/]+)/config(?:\.[0-9a-f]{5,})?\.json$')
ASSET_EXT = re.compile(r'\.(?:png|jpe?g|webp|json|prefab|fire|scene|mp3|ogg|wav|m4a|plist|atlas|fnt|ttf|txt|anim|'
                       r'mtl|effect|bin|skel)$', re.I)
SUB_ASSET = re.compile(r'/(?:spriteFrame|texture)$')
LITERAL_ARG = r'''\s*(?P<q>["'])(?P<path>[^"'\\\n]{1,200})(?P=q)\s*[,)]'''
RES_CALL = re.compile(r'(?<![\w$])(?:cc\s*\.\s*resources\s*\.\s*(load|loadDir)|cc\s*\.\s*loader\s*\.\s*(loadRes|loadResDir))'
                      r'\s*\(' + LITERAL_ARG)
GET_BUNDLE_CALL = re.compile(r'''\bgetBundle\s*\(\s*(["'])([\w\-]{1,64})\1\s*\)\s*\.\s*(load|loadDir)\s*\(''' + LITERAL_ARG)
LOAD_BUNDLE_CB = re.compile(r'''\bloadBundle\s*\(\s*(["'])([\w\-]{1,64})\1\s*,\s*(?:\{[^{}]*\}\s*,\s*)?'''
                            r'''(?:function\s*\(\s*[\w$]+\s*,\s*([\w$]+)\s*\)|\(\s*[\w$]+\s*,\s*([\w$]+)\s*\)\s*=>)\s*\{''')


def bundle_paths(view):
    """{bundle: set(asset paths)} from every bundle config in the package; None for an unreadable config."""
    out = {}
    for name in view.files:
        m = BUNDLE_CONFIG.search(name)
        if not m:
            continue
        try:
            data = json.loads(view.files[name].decode('utf-8-sig'))
        except (ValueError, UnicodeDecodeError):
            out[m.group(1)] = None
            continue
        if not isinstance(data, dict) or not isinstance(data.get('paths'), dict):
            out[m.group(1)] = None
            continue
        paths = out.setdefault(m.group(1), set())
        if paths is None:
            continue
        for value in data['paths'].values():
            if isinstance(value, list) and value and isinstance(value[0], str):
                paths.add(value[0])
        for scene in (data.get('scenes') or {}):
            if isinstance(scene, str):
                base = scene.split('/')[-1]
                paths.add(base.rsplit('.', 1)[0])
        name_in = data.get('name')
        if isinstance(name_in, str) and name_in and name_in != m.group(1):
            out.setdefault(name_in, paths)
    return out


def _path_present(paths, path, directory):
    path = path.strip().strip('/')
    if directory:
        return path == '' or path in paths or any(p.startswith(path + '/') for p in paths)
    candidates = {path, ASSET_EXT.sub('', path)}
    for p in list(candidates):
        candidates.add(SUB_ASSET.sub('', p))
        candidates.add(p + '/spriteFrame')
        candidates.add(p + '/texture')
    return bool(candidates & paths)


def missing_resource_hits(view):
    configs = bundle_paths(view)
    if not configs:
        return []
    hits = []

    def test(name, text, match, bundle, method, path):
        paths = configs.get(bundle)
        if not paths:                       # bundle not shipped (H12's business) or config unreadable: skip
            return
        if not _path_present(paths, path, method.endswith('Dir')):
            hits.append({'file': name, 'bundle': bundle, 'path': path, 'call': method,
                         'context': _context(text, match)})

    for name in _scanned(view):
        text = view.text(name)
        if 'resources' in text or 'loadRes' in text:
            for m in RES_CALL.finditer(text):
                test(name, text, m, 'resources', m.group(1) or m.group(2), m.group('path'))
        if 'Bundle' not in text:
            continue
        for m in GET_BUNDLE_CALL.finditer(text):
            test(name, text, m, m.group(2), m.group(3), m.group('path'))
        code = None
        for m in LOAD_BUNDLE_CB.finditer(text):
            code = code or _Code(text)
            close_of, _ = code.pairs()
            end = close_of.get(m.end() - 1)
            if end is None:
                continue
            var = m.group(3) or m.group(4)
            body_call = re.compile(r'(?<![\w$.])' + re.escape(var) + r'\s*\.\s*(load|loadDir)\s*\(' + LITERAL_ARG)
            for call in body_call.finditer(text, m.end(), end):
                test(name, text, call, m.group(2), call.group(1), call.group('path'))
    return hits


def _level(view):
    get = getattr(view, 'get_policy', None)
    policy = get()[0] if get else (getattr(view, 'policy', None) or 'new')
    return ('block' if policy != 'legacy' else 'warn'), policy


def local_file_findings(view):
    out = []
    reads, fonts, missing = package_read_hits(view), font_path_hits(view), missing_resource_hits(view)
    if not (reads or fonts or missing):
        return out
    level, policy = _level(view)
    if reads:
        out.append(finding('H15_package_read_via_request', level,
                           'game JS reads a package file through %s outside a browser-only branch (%s): on the TikTok '
                           'mini game this is XMLHttpRequest/tt.request, which only reaches https URLs, so the phone '
                           'stops at loading - load package files with cc.resources/bundle.load (or '
                           'downloader._downloaders[ext]) and keep downloadFile inside if(cc.sys.isBrowser)'
                           % ('/'.join(sorted({h['call'] for h in reads})), reads[0]['file']), reads[:6]))
    if fonts:
        out.append(finding('H16_font_path_as_family', level,
                           'game JS stores the result of downloader._downloaders[".ttf"] as the font family (%s): '
                           'on the mini game that result is the font FILE PATH, so every label falls back to tiny '
                           'system text - load the font with cc.resources.load(path, cc.Font)' % fonts[0]['file'],
                           fonts[:6]))
    if missing:
        out.append(finding('H17_resource_path_missing', level,
                           'code loads resource paths no bundle config of the package lists: ' +
                           '; '.join('%s:%s (%s)' % (h['bundle'], h['path'], h['file']) for h in missing[:6]) +
                           ' - fix the path or ship the asset in that bundle', missing[:6]))
    return out


def check(view):
    out = []
    absent = missing_bundle_refs(view)
    if absent:
        out.append(finding('H12_bundle_name', 'block',
                           'code loads a bundle/subpackage the package does not have: ' +
                           '; '.join('%s (%s)' % kv for kv in list(absent.items())[:6]) +
                           ' - remove the call (other-channel code) or ship that bundle as a declared subpackage',
                           [{'bundle': b, 'file': f} for b, f in absent.items()]))
    hits = analytics_hits(view)
    if hits:
        hosts = sorted({h['host'] for h in hits})
        out.append(finding('H13_analytics_domain', 'block',
                           'Chinese analytics SDK report host in game JS: %s (%s) - TikTok only reaches registered '
                           'domains; remove the analytics module' % (', '.join(hosts), hits[0]['file']), hits[:10]))
    promo = cross_promo_hits(view)
    if promo:
        kinds = sorted({h['match'] for h in promo})
        out.append(finding('H14_cross_promo', 'block',
                           'cross-promotion / jump to other mini games in game JS: %s (%s) - empty the behaviour '
                           '(keep same-name fields if a prefab lists the component) so no call or foreign App ID '
                           'remains' % (', '.join(kinds[:6]), promo[0]['file']), promo[:10]))
    out += local_file_findings(view)
    return out
