#!/usr/bin/env python3
"""生成时预防 P01 / P14 / P10 (Round 3 I2): rewire the original's platform code at stage 2, not at packaging.

Called by tiktok_finalize.py (`inventory` adds the lists below, `rewire-ads` applies the automatic part).

plan(project) -> {'rewire_todo': [...], 'delete_list': [...], 'kit_copies': [...]}   (read only)
    rewire_todo  one row per call site the AI must handle, with kind, file, line, function, shape, auto, fix:
                 ad           a function that creates / shows a rewarded video (auto=True: rewire-ads does it)
                 growth       add-to-home / profile-revisit code: hard-coded reward in new MissionFlow({...})
                              (auto=True) or direct SDK calls (auto=False: use HomeGrowthEntries / MissionFlow)
                 save_best    a function that compares a best score and writes the save: use SaveStore.best
                 save_grant   a function that adds a reward and writes the save: use SaveStore.grant
    delete_list  share / cross-promotion / rank entries to delete at the start of stage 2
    kit_copies   kit module files at other paths or in older texts (sync puts the kit version back)

rewire(project, write=True) -> record
    ad      each recognised function keeps its name and parameters; its body becomes one call into the generated
            assets/tiktok-platform/AdBridge.js (same name, same parameters), which calls RewardedService.request().
            Shapes: callback (ok / fail callbacks, or one callback called with true / false), promise (resolve
            true / false, or resolve / reject), event (emits a success / fail event). A function that only creates
            the ad object for a rewired show function gets an inert ad object instead (AdBridge.inertAd), so the
            game code creates no rewarded ad. Anything else stays as it is and is listed in rewire_todo.
    growth  in new MissionFlow({...}) the hard-coded reward becomes AdBridge.growthAmount() (= growthReward())
            and rewardText becomes AdBridge.growthText(suffix); an unused reward constant is deleted.
    Changed files are copied to .tiktok-kit/rewire-backup/ first. Record: <project>/.tiktok-kit/rewire-ads.json.
Kit files are never rewritten here (sync owns them).
"""
import json
import re
import shutil
import time
from pathlib import Path

BRIDGE_PATH = 'assets/tiktok-platform/AdBridge.js'
KIT_DIR = 'assets/tiktok-platform/'
KIT_MODULES = ('RewardedService', 'PlatformConfig', 'TikTokMissionService', 'SaveStore', 'MissionFlow',
               'HomeGrowthEntries', 'GameUIKit', 'AdBridge')
SKIP = {'library', 'temp', 'build', 'local', 'node_modules', '.git', '.tiktok-kit', '__MACOSX'}
RECORD = Path('.tiktok-kit') / 'rewire-ads.json'
BACKUP = Path('.tiktok-kit') / 'rewire-backup'
DEFAULT_KEY = 'double_coins'

CREATE = re.compile(r'createRewardedVideoAd')
CREATE_CALLEE = re.compile(r'(?:[A-Za-z_$][\w$]*\s*(?:\.\s*[A-Za-z_$][\w$]*\s*|\[\s*["\'][\w$]+["\']\s*\]\s*)*'
                           r'\.\s*)?createRewardedVideoAd\s*(?=\()')
# Any reference (call or `if (tt.createRewardedVideoAd)` check) inside a create-only function: all become inertAd.
CREATE_REF = re.compile(r'(?:[A-Za-z_$][\w$]*\s*(?:\.\s*[A-Za-z_$][\w$]*\s*)*\.\s*)?createRewardedVideoAd\b')
GROWTH_CALL = re.compile(r'\.\s*(addShortcut|checkShortcut|startEntranceMission|getShortcutMissionReward|'
                         r'getEntranceMissionReward)\s*\(')
# Indexed calls through a name string: api[method](...) with method = "addShortcut" (埃及宝石 HexPlatform.Growth).
GROWTH_NAME = re.compile(r'(["\'])(addShortcut|checkShortcut|startEntranceMission|getShortcutMissionReward|'
                         r'getEntranceMissionReward)\1')
KEYWORDS = {'if', 'for', 'while', 'switch', 'catch', 'function', 'return', 'with', 'else', 'do', 'try', 'new',
            'typeof', 'delete', 'void', 'await', 'yield', 'super', 'constructor_'}
FAIL_NAME = re.compile(r'fail|err|cancel|close|reject|lose|no$', re.I)
START_NAME = re.compile(r'^(?:on)?(?:show|start|open|play|begin)\w*$', re.I)
OK_NAME = re.compile(r'^(?:on)?(?:succ\w*|ok|reward\w*|done|complete\w*|finish\w*|cb|callback|success)$', re.I)
FAIL_ONLY = re.compile(r'^(?:on)?(?:fail\w*|err\w*|cancel\w*|reject\w*)$', re.I)
PLACE_NAME = re.compile(r'^(?:type|adType|place|placement|placementKey|pos|scene|key|name|reason|kind|from|tag)$')
KEY_HINT = (('revive', 'revive'), ('relive', 'revive'), ('fuhuo', 'revive'), ('hint', 'hint'), ('tip', 'hint'),
            ('skin', 'skin'), ('double', 'double_coins'), ('gift', 'gift'))

try:                                                  # same API lists as the packaging audit (no drift)
    import audit_no_social_features as _social
    SHARE_API, RANK_API = _social.SHARE_API, _social.RANK_API
except Exception:  # noqa: BLE001
    SHARE_API = r'shareAppMessage|onShareAppMessage|showShareMenu|updateShareMenu|shareToStory'
    RANK_API = r'getFriendCloudStorage|getGroupCloudStorage|setUserCloudStorage|getOpenDataContext'
DELETE = (('share', re.compile(r'\b(?:%s)\s*\(' % SHARE_API)),
          ('cross_promo', re.compile(r'\b(?:navigateToMiniProgram|showMoreGamesModal|createMoreGamesButton|'
                                     r'navigateToMiniGame)\s*\(|\bmoreGames?(?:Btn|Button|Panel)?\b', re.I)),
          ('rank', re.compile(r'\b(?:%s)\s*\(|\b(?:rank|ranking|leaderboard)(?:Btn|Button|Panel|View|List|UI)\b'
                              % RANK_API, re.I)))
SAVE_WRITE = re.compile(r'setStorageSync\s*\(|\bsetStorage\s*\(|localStorage\s*\.\s*setItem\s*\(|'
                        r'\.\s*(?:save|saveData|saveAll|persist|flush|writeSave|setItem|update)\s*\(')
CURRENCY = re.compile(r'coin|gold|gem|diamond|money|cash|star|point|crystal|ruby', re.I)
BEST_WORD = re.compile(r'\b\w*(?:best|high|record|maxScore|topScore)\w*\b', re.I)
BEST_CMP = re.compile(r'[<>]=?(?!=)|Math\s*\.\s*max\s*\(')
GRANT_WORD = re.compile(r'\b\w*(?:coin|gold|gem|diamond|money|cash|reward|wallet|star)s?\w*\s*(?:\+=|=[^=;]*\+)',
                        re.I)


# ---------------------------------------------------------------- JS scanning (comments and strings masked)
def mask(text):
    """Same length as text; comment and string contents become spaces (quotes kept). Regex literals are not
    recognised (rare in game managers; a wrong guess only makes a site unrecognised, never rewritten wrongly)."""
    out, i, n = list(text), 0, len(text)
    while i < n:
        c = text[i]
        if c == '/' and i + 1 < n and text[i + 1] == '/':
            j = text.find('\n', i)
            j = n if j < 0 else j
            out[i:j] = ' ' * (j - i)
            i = j
        elif c == '/' and i + 1 < n and text[i + 1] == '*':
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out[i:j] = [ch if ch == '\n' else ' ' for ch in text[i:j]]
            i = j
        elif c in '"\'`':
            j = i + 1
            while j < n and text[j] != c:
                if text[j] == '\\':
                    j += 1
                elif text[j] == '\n' and c != '`':
                    break
                j += 1
            for k in range(i + 1, min(j, n)):
                if text[k] != '\n':
                    out[k] = ' '
            i = j + 1
        else:
            i += 1
    return ''.join(out)


def match_close(masked, start, open_='{', close='}'):
    """Index of the bracket closing masked[start] (== open_), or -1."""
    depth = 0
    for i in range(start, len(masked)):
        c = masked[i]
        if c == open_:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                return i
    return -1


HEADERS = (
    re.compile(r'\bfunction\s*\*?\s*([A-Za-z_$][\w$]*)\s*\('),                                     # function f(
    re.compile(r'([A-Za-z_$][\w$]*)\s*[:=]\s*(?:async\s+)?function\s*\*?\s*[\w$]*\s*\('),         # f: function(
    re.compile(r'([A-Za-z_$][\w$]*)\s*[:=]\s*(?:async\s*)?(?=\()'),                                # f = (a) => {
    re.compile(r'(?:^|[\s;{},])(?:(?:public|private|protected|static|async|override)\s+)*'
               r'([A-Za-z_$][\w$]*)\s*(?=\()'),                                                    # f(a) {
)


def functions(text, masked=None):
    """[{name, params, start, body_start, body_end, arrow}] for named functions (body between the braces)."""
    masked = masked if masked is not None else mask(text)
    seen, out = set(), []
    for kind, rx in enumerate(HEADERS):
        for m in rx.finditer(masked):
            name = m.group(1)
            if name in KEYWORDS:
                continue
            p_open = masked.find('(', m.end() - 1) if kind != 3 else m.end()
            if p_open < 0 or masked[p_open] != '(':
                continue
            p_close = match_close(masked, p_open, '(', ')')
            if p_close < 0:
                continue
            rest = masked[p_close + 1:p_close + 200]
            arrow = False
            if kind == 2:
                mm = re.match(r'\s*(?::\s*[^={;]+?)?\s*=>\s*\{', rest)
                arrow = True
            else:
                mm = re.match(r'\s*(?::\s*[^{;=]+?)?\s*\{', rest)
            if not mm:
                continue
            body_start = p_close + 1 + mm.end()          # just after '{'
            if body_start in seen:
                continue
            body_end = match_close(masked, body_start - 1)
            if body_end < 0:
                continue
            seen.add(body_start)
            out.append({'name': name, 'params': text[p_open + 1:p_close], 'start': m.start(1),
                        'body_start': body_start, 'body_end': body_end, 'arrow': arrow})
    out.sort(key=lambda f: f['body_start'])
    return out


def enclosing(funcs, pos):
    """Innermost named function whose body contains pos."""
    best = None
    for f in funcs:
        if f['body_start'] <= pos < f['body_end'] and (best is None or f['body_start'] > best['body_start']):
            best = f
    return best


def param_names(params):
    """'a, b: string, c = 1' -> ['a', 'b', 'c']; None when a parameter is destructured or a rest parameter."""
    names = []
    for raw in split_top(params):
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith(('...', '{', '[')):
            return None
        m = re.match(r'([A-Za-z_$][\w$]*)\s*\??\s*(?::|=|$)', raw)
        if not m:
            return None
        names.append(m.group(1))
    return names


def split_top(params):
    out, depth, cur = [], 0, ''
    masked = mask(params)
    for i, c in enumerate(masked):
        if c in '([{':                  # not < >: a TS type `(reason: string) => void` has a '>' of its own
            depth += 1
        elif c in ')]}':
            depth -= 1
        if c == ',' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += params[i]
    out.append(cur)
    return out


def line_of(text, pos):
    return text.count('\n', 0, pos) + 1


def game_files(project):
    """[(relpath, Path)] of game scripts (.js / .ts, not .d.ts) under assets/, kit folder and tool folders skipped."""
    project = Path(project)
    base = project / 'assets'
    out = []
    if not base.is_dir():
        return out
    for p in sorted(base.rglob('*')):
        rel = p.relative_to(project)
        if not p.is_file() or p.suffix not in ('.js', '.ts') or p.name.endswith('.d.ts') or SKIP & set(rel.parts):
            continue
        out.append((rel.as_posix(), p))
    return out


def is_kit_file(rel):
    stem = rel.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    return rel.startswith(KIT_DIR) or stem in KIT_MODULES


# ---------------------------------------------------------------- ad shapes
def _invoked(body_masked, name):
    """Calls of a parameter: p(...), p.call(...), p && p(...), p?.(...), or through an alias (this._cb = p)."""
    names = [name]
    for m in re.finditer(r'((?:this\s*\.\s*)?[A-Za-z_$][\w$]*)\s*=\s*%s\s*[;,\n)]' % re.escape(name), body_masked):
        names.append(re.sub(r'\s+', '', m.group(1)))
    calls = []
    for n in names:
        pat = re.escape(n).replace(r'\.', r'\s*\.\s*')
        for m in re.finditer(r'(?<![\w$.])%s\s*(?:\?\.\s*)?(?:\.\s*(?:call|apply)\s*)?\(' % pat, body_masked):
            calls.append(m.end())
    return calls


def _call_args(text, masked, open_after):
    """Argument text of the call whose '(' is just before open_after."""
    close = match_close(masked, open_after - 1, '(', ')')
    return text[open_after:close] if close > 0 else ''


def _bool_arg(arg):
    a = re.sub(r'\s+', '', arg)
    return a in ('true', 'false', '!0', '!1') or 'isEnded' in a


def classify_ad(text, masked, f):
    """-> (shape, detail) for a function that shows the ad. shape None = not recognised (detail says why)."""
    body = text[f['body_start']:f['body_end']]
    bm = masked[f['body_start']:f['body_end']]
    names = param_names(f['params'])
    if names is None:
        return None, 'destructured or rest parameters'
    if re.search(r'\breturn\s*\{[^}]*\bpromise\b', bm):
        return None, 'returns a handle object {promise, cancel}; call AdBridge.run() by hand'
    placement = next((n for n in names if PLACE_NAME.match(n) and not _invoked(bm, n)), None)
    detail = {'params': names, 'placement_param': placement}
    if re.search(r'\breturn\s+new\s+Promise\s*\(', bm):
        # Only when EVERY resolve() passes true / false (or nothing, with reject for the failure): a Promise of a
        # result object ({status: ...}, 麻将 RewardedCore) is read by its caller and cannot become a boolean.
        args = [re.sub(r'\s+', '', _call_args(body, bm, m.end())) for m in re.finditer(r'\bresolve\s*\(', bm)]
        if args and all(a in ('true', 'false', '!0', '!1') for a in args) and any(a in ('true', '!0') for a in args):
            return 'promise_bool', detail
        if args and all(a == '' for a in args) and re.search(r'\breject\s*\(', bm):
            return 'promise_reject', detail
        return None, 'Promise resolves something other than true / false (or nothing + reject); rewire by hand'
    called = [n for n in names if n != placement and _invoked(bm, n)]
    if called:
        # Strict on purpose: a wrong guess rewires the reward to the wrong callback, a missed one only stays in
        # rewire_todo. Checked on the 64 game projects of the learning library (说明.md).
        full = {n: [_call_args(body, bm, pos) for pos in _invoked(bm, n)] for n in called}
        args = {n: [re.sub(r'\s+', '', split_top(a)[0]) for a in full[n]] for n in called}     # first argument
        more = {n: any(len([x for x in split_top(a) if x.strip()]) > 1 for a in full[n]) for n in called}
        bools = [n for n in called if any(a in ('true', 'false', '!0', '!1') for a in args[n])
                 and all(_bool_arg(a) or re.match(r'^[A-Za-z_$][\w$.]*$', a) for a in args[n])]
        start = [n for n in called if START_NAME.search(n) and not FAIL_NAME.search(n) and n not in bools]
        if len(bools) == 1:
            others = [n for n in called if n not in bools and n not in start and not FAIL_NAME.search(n)]
            if others:
                return None, 'callback %s(true/false) plus other callbacks %s' % (bools[0], ', '.join(others))
            detail.update(ok=bools[0], bool=True, fail=None, extra=start, message=more[bools[0]])
            return 'callback', detail
        oks = [n for n in called if OK_NAME.match(n)]
        fails = [n for n in called if FAIL_ONLY.match(n)]
        others = [n for n in called if n not in oks and n not in fails and n not in start]
        if len(oks) != 1 or len(fails) > 1 or others or bools:
            return None, 'callbacks not clear (%s); rewire by hand' % ', '.join(called)
        if any(a for a in args[oks[0]]):
            return None, 'success callback %s gets arguments (%s); rewire by hand' % (
                oks[0], ', '.join(sorted(set(a for a in args[oks[0]] if a)))[:60])
        detail.update(ok=oks[0], bool=False, fail=fails[0] if fails else None, extra=start)
        return 'callback', detail
    emits = list(re.finditer(r'((?:this\s*\.\s*)?[\w$.]+\s*\.\s*(?:emit|dispatchEvent|dispatch|fire|trigger)\s*\('
                             r'\s*(["\'])([^"\']+)\2[^;\n]*\))', body))
    ok_stmt = next((m.group(1) for m in emits if not FAIL_NAME.search(m.group(3))), None)
    fail_stmt = next((m.group(1) for m in emits if FAIL_NAME.search(m.group(3))), None)
    if ok_stmt:
        local = set(re.findall(r'\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)', bm))
        used = set(re.findall(r'[A-Za-z_$][\w$]*', mask(ok_stmt + ' ' + (fail_stmt or ''))))
        if local & used:
            return None, 'event statement uses local variables: %s' % ', '.join(sorted(local & used))
        detail.update(ok_stmt=ok_stmt, fail_stmt=fail_stmt)
        return 'event', detail
    return None, 'no callback parameter, Promise or event found'


def _placement_key(f, detail):
    low = f['name'].lower()
    for hint, key in KEY_HINT:
        if hint in low:
            return key
    return DEFAULT_KEY


def bridge_entry(ident, f, shape, detail):
    """JS text of one bridge function (same parameters as the original)."""
    names = detail['params']
    key = _placement_key(f, detail)
    place = "key(%s, '%s')" % (detail['placement_param'], key) if detail.get('placement_param') else "'%s'" % key
    head = "B[%s] = function (%s) {\n  var self = this;\n" % (json.dumps(ident), ', '.join(names))
    if shape == 'promise_bool':
        body = ("  return new Promise(function (resolve) {\n    run(%s, function () { resolve(true); }, "
                "function () { resolve(false); }, true);\n  });\n" % place)
    elif shape == 'promise_reject':
        body = ("  return new Promise(function (resolve, reject) {\n    run(%s, function () { resolve(); }, "
                "function (r) { reject({errCode: -1, errMsg: r.message, status: r.status, result: r}); });\n"
                "  });\n" % place)
    elif shape == 'callback':
        ok = detail['ok']
        if detail['bool'] and detail.get('message'):    # cb(false, 'reason'): the game shows the reason itself
            okc, failc, toast = 'call(%s, [true])' % ok, 'call(%s, [false, r.message])' % ok, 'false'
        elif detail['bool']:
            okc, failc, toast = 'call(%s, [true])' % ok, 'call(%s, [false])' % ok, 'true'
        else:
            okc = 'call(%s, [])' % ok
            failc = 'call(%s, [r.message])' % detail['fail'] if detail.get('fail') else '/* no fail callback */'
            toast = 'false' if detail.get('fail') else 'true'
        body = "  run(%s, function () { %s; }, function (r) { %s; }, %s);\n" % (place, okc, failc, toast)
    else:  # event
        fail = detail.get('fail_stmt')
        body = ("  run(%s, function () { (function () { %s; }).call(self); }, function () { %s }, %s);\n"
                % (place, detail['ok_stmt'], '(function () { %s; }).call(self);' % fail if fail else '',
                   'false' if fail else 'true'))
    return head + body + '};\n'


def _body_call(ident, f, names):
    return "\n    return require('AdBridge')[%s].call(this%s);\n" % (
        json.dumps(ident), ''.join(', ' + n for n in names))


def scan_ads(rel, text, masked=None, funcs=None):
    """-> list of {file, line, function, shape, auto, why, edit} for one script. edit = (start, end, new text)."""
    masked = masked if masked is not None else mask(text)
    funcs = funcs if funcs is not None else functions(text, masked)
    sites = [m.start() for m in CREATE.finditer(masked)]
    if not sites:
        return []
    rows, done = [], set()
    for pos in sites:
        f = enclosing(funcs, pos)
        if f is None:
            rows.append({'kind': 'ad', 'file': rel, 'line': line_of(text, pos), 'function': None, 'shape': None,
                         'auto': False, 'why': 'not inside a named function'})
            continue
        bm = masked[f['body_start']:f['body_end']]
        targets = [f]
        init_only = not re.search(r'\.\s*show\s*\(', bm)
        if init_only:
            prop = re.search(r'([\w$]+)\s*=\s*[^;=]*createRewardedVideoAd', bm)
            prop = prop.group(1) if prop else None
            shows = [g for g in funcs if g is not f and prop and
                     re.search(r'\b%s\s*\.\s*show\s*\(' % re.escape(prop), masked[g['body_start']:g['body_end']])
                     and not any(h is not g and h['body_start'] < g['body_start'] and g['body_end'] < h['body_end']
                                 for h in [f])]
            if not shows:
                rows.append({'kind': 'ad', 'file': rel, 'line': line_of(text, pos), 'function': f['name'],
                             'shape': None, 'auto': False,
                             'why': 'creates the ad object but no function showing it was found'})
                continue
            targets = shows
        results = []
        for g in targets:
            shape, detail = classify_ad(text, masked, g)
            results.append((g, shape, detail))
        if any(s is None for _, s, _ in results):
            for g, s, d in results:
                if s is None:
                    rows.append({'kind': 'ad', 'file': rel, 'line': line_of(text, g['start']), 'function': g['name'],
                                 'shape': None, 'auto': False, 'why': d})
            continue
        for g, shape, detail in results:
            if g['body_start'] in done:
                continue
            done.add(g['body_start'])
            ident = '%s.%s' % (rel.rsplit('/', 1)[-1].rsplit('.', 1)[0], g['name'])
            rows.append({'kind': 'ad', 'file': rel, 'line': line_of(text, g['start']), 'function': g['name'],
                         'shape': shape, 'auto': True, 'why': None, 'ident': ident,
                         'bridge': bridge_entry(ident, g, shape, detail),
                         'edit': (g['body_start'], g['body_end'], _body_call(ident, g, detail['params']))})
        if init_only and ('inert', f['body_start']) not in done:
            done.add(('inert', f['body_start']))
            for m in CREATE_REF.finditer(masked, f['body_start'], f['body_end']):
                if masked[m.start():m.end()].strip():
                    rows.append({'kind': 'ad', 'file': rel, 'line': line_of(text, m.start()), 'function': f['name'],
                                 'shape': 'inert_init', 'auto': True, 'why': None,
                                 'edit': (m.start(), m.end(), "require('AdBridge').inertAd")})
    return rows


# ---------------------------------------------------------------- growth entries (P14)
def _prop_value(text, masked, obj_start, obj_end, prop):
    """(start, end) of the value of `prop:` at the top level of the object literal masked[obj_start:obj_end]."""
    depth = 0
    i = obj_start + 1
    while i < obj_end:
        c = masked[i]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif depth == 0:
            m = re.match(r'(?<![\w$])%s\s*:' % re.escape(prop), masked[i:obj_end])
            if m and (i == obj_start + 1 or not re.match(r'[\w$]', masked[i - 1])):
                v = i + m.end()
                d, j = 0, v
                while j < obj_end:
                    cj = masked[j]
                    if cj in '([{':
                        d += 1
                    elif cj in ')]}':
                        if d == 0:
                            break
                        d -= 1
                    elif cj == ',' and d == 0:
                        break
                    j += 1
                return v, j
        i += 1
    return None


def scan_growth(rel, text, masked=None, funcs=None):
    """-> rows: hard-coded rewards in new MissionFlow({...}) (auto) and direct growth SDK calls (todo)."""
    masked = masked if masked is not None else mask(text)
    funcs = funcs if funcs is not None else functions(text, masked)
    rows = []
    for m in re.finditer(r'\bnew\s+MissionFlow\s*\(\s*\{', masked):
        o_start = m.end() - 1
        o_end = match_close(masked, o_start)
        if o_end < 0:
            continue
        edits, consts, why = [], set(), None
        rv = _prop_value(text, masked, o_start, o_end, 'reward')
        reward_ok = rv is None or bool(re.search(r'growthReward|growthAmount', masked[rv[0]:rv[1]]))
        if not reward_ok:
            segm = masked[rv[0]:rv[1]]
            # one currency field += constant (or = (field || 0) + constant); items or several fields: by hand
            hits = list(re.finditer(r'([\w$.]+)\s*(?:\+=|=\s*\(?[^;=]*?\)?\s*\+)\s*([A-Z_][A-Z0-9_]*|\d+(?:\.\d+)?)\b',
                                    segm))
            if len(hits) != 1:
                why = 'reward function with %d amounts; make it pay growthReward() once (or omit reward)' % len(hits)
            elif not CURRENCY.search(hits[0].group(1).rsplit('.', 1)[-1]):
                why = 'reward goes to %s, not a currency; growth entries pay 5B currency' % hits[0].group(1)
            else:
                h = hits[0]
                if not h.group(2)[0].isdigit():
                    consts.add(h.group(2))
                edits.append((rv[0] + h.start(2), rv[0] + h.end(2), "require('AdBridge').growthAmount()"))
                reward_ok = True
        tv = _prop_value(text, masked, o_start, o_end, 'rewardText')
        if tv and reward_ok and not re.search(r'growthText|growthReward', masked[tv[0]:tv[1]]):
            seg = text[tv[0]:tv[1]]
            words = re.findall(r'["\']\s*\+?\s*\d*\s*([A-Za-z][A-Za-z ]*)["\']', seg)
            suffix = ' ' + (words[-1].strip() if words else 'Coins')
            for c in re.findall(r'\b([A-Z_][A-Z0-9_]*)\b', mask(seg)):
                consts.add(c)
            edits.append((tv[0], tv[1], " {shortcut: require('AdBridge').growthText(%s), profile: "
                          "require('AdBridge').growthText(%s)}" % (json.dumps(suffix), json.dumps(suffix))))
        if why:
            edits = []                                 # never half: reward and its text change together or not at all
        if edits or why:
            rows.append({'kind': 'growth', 'file': rel, 'line': line_of(text, m.start()), 'function':
                         (enclosing(funcs, m.start()) or {}).get('name'), 'shape': 'missionflow_options',
                         'auto': bool(edits), 'why': why, 'edits': edits, 'consts': sorted(consts),
                         'fix': 'reward amount only from PlatformConfig.growthReward()'})
    seen = set()
    hits = [(m.start(), m.group(1), 'calls') for m in GROWTH_CALL.finditer(masked)] + \
        [(m.start(), m.group(2), 'names') for m in GROWTH_NAME.finditer(text) if not masked[m.start()].isspace()]
    for pos, call, how in sorted(hits):
        f = enclosing(funcs, pos)
        if (f and f['body_start'], call) in seen:
            continue
        seen.add((f and f['body_start'], call))
        rows.append({'kind': 'growth', 'file': rel, 'line': line_of(text, pos), 'function': f and f['name'],
                     'shape': 'direct_sdk', 'auto': False, 'call': call,
                     'why': 'original %s %s itself' % (how, call),
                     'fix': 'delete this entry code; put HomeGrowthEntries.js on the home screen (or MissionFlow '
                            'open(kind, {navigate: true})); the amount is growthReward(), never a number here'})
    return rows


def _const_edits(text, masked, consts, edits):
    """Delete `var NAME = <number>;` lines of constants that no longer appear anywhere after the edits."""
    out = []
    taken = [(a, b) for a, b, _ in edits]
    for name in consts:
        uses = [m.start() for m in re.finditer(r'(?<![\w$.])%s(?![\w$])' % re.escape(name), masked)]
        decl = re.search(r'^[ \t]*(?:var|let|const)\s+%s\s*=\s*\d+(?:\.\d+)?\s*;[^\n]*\n' % re.escape(name),
                         text, re.M)
        if not decl:
            continue
        left = [u for u in uses if not (decl.start() <= u < decl.end()) and not any(a <= u < b for a, b in taken)]
        if not left:
            out.append((decl.start(), decl.end(), ''))
    return out


# ---------------------------------------------------------------- save sites (P10) and delete list (P14)
def scan_saves(rel, text, masked=None, funcs=None):
    masked = masked if masked is not None else mask(text)
    funcs = funcs if funcs is not None else functions(text, masked)
    rows = []
    for f in funcs:
        bm = masked[f['body_start']:f['body_end']]
        if not SAVE_WRITE.search(bm):
            continue
        inner = [g for g in funcs if g is not f and f['body_start'] < g['body_start'] < f['body_end']]
        if any(g['body_start'] <= f['body_start'] + m.start() < g['body_end'] for g in inner
               for m in SAVE_WRITE.finditer(bm)) and not any(
                not any(g['body_start'] <= f['body_start'] + m.start() < g['body_end'] for g in inner)
                for m in SAVE_WRITE.finditer(bm)):
            continue                                  # every write is in a nested function: reported there
        code = text[f['body_start']:f['body_end']]
        names_code = mask(code)
        if BEST_WORD.search(names_code) and BEST_CMP.search(names_code):
            rows.append({'kind': 'save_best', 'file': rel, 'line': line_of(text, f['start']), 'function': f['name'],
                         'auto': False, 'why': 'compares a best score and writes the save',
                         'fix': 'use SaveStore.best(key, value): writes only a larger value, also the first one'})
        if GRANT_WORD.search(names_code):
            rows.append({'kind': 'save_grant', 'file': rel, 'line': line_of(text, f['start']), 'function': f['name'],
                         'auto': False, 'why': 'adds a reward and writes the save',
                         'fix': 'use SaveStore.grant(delta, onDone): wallet + claimed flag in one write, the UI '
                                'changes only after it was read back'})
    return rows


def scan_delete(rel, text, masked=None, funcs=None):
    masked = masked if masked is not None else mask(text)
    funcs = funcs if funcs is not None else functions(text, masked)
    rows = []
    for kind, rx in DELETE:
        for m in rx.finditer(masked):
            f = enclosing(funcs, m.start())
            rows.append({'kind': kind, 'file': rel, 'line': line_of(text, m.start()), 'function': f and f['name'],
                         'text': text[m.start():m.end()].strip()[:60],
                         'fix': 'delete the entry and its button at the start of stage 2 (no share, cross-promo '
                                'or rank in TikTok games)'})
    return rows


V3_WHY = 'Cocos 3.x: rewire-ads writes Cocos 2.4 code only (require(\'AdBridge\'))'
V3_FIX = ('rewire by hand to globalThis.TikTokKit.RewardedService (ad) / TikTokKit.PlatformConfig.growthReward() '
          '(growth reward); the shape found is in `shape`')


def engine(project):
    """2 / 3 / None (same reading as tiktok_finalize)."""
    try:
        from tiktok_finalize_steps import policy
        return policy.engine_of_project(Path(project))
    except Exception:  # noqa: BLE001
        return None


def plan(project):
    """Read-only lists for inventory: rewire_todo, delete_list, kit_copies."""
    todo, delete, kit = [], [], []
    v3 = engine(project) == 3
    for rel, p in game_files(project):
        text = p.read_text(encoding='utf-8', errors='replace')
        if is_kit_file(rel):
            if not rel.startswith(KIT_DIR) or (CREATE.search(text) and 'getSDK' not in text):
                kit.append({'file': rel, 'fix': 'kit module name outside assets/tiktok-platform/ or own text: '
                                                'tiktok_finalize.py sync puts the kit file back'})
            continue
        masked = mask(text)
        funcs = functions(text, masked)
        for row in scan_ads(rel, text, masked, funcs) + scan_growth(rel, text, masked, funcs):
            row = {k: v for k, v in row.items() if k not in ('edit', 'edits', 'bridge', 'consts')}
            if v3 and row['auto']:
                row.update(auto=False, why=V3_WHY, fix=V3_FIX)
            row['fix'] = row.get('fix') or ('tiktok_finalize.py rewire-ads does it' if row['auto'] else
                                            'call RewardedService.request() through AdBridge.run(placementKey, onOk, '
                                            'onFail) by hand')
            todo.append(row)
        todo += scan_saves(rel, text, masked, funcs)
        delete += scan_delete(rel, text, masked, funcs)
    return {'rewire_todo': todo, 'delete_list': delete, 'kit_copies': kit}


# ---------------------------------------------------------------- AdBridge.js and the rewrite
BRIDGE_HEAD = r"""'use strict';
// AdBridge.js - GENERATED by `tiktok_finalize.py rewire-ads` (生成时预防 P01 / P14). Do not edit by hand:
// change the game code or the generator and run rewire-ads again.
// Every rewarded video of the original game goes through the platform kit RewardedService (15 s foreground
// request limit, no timer after playback starts, reward only for a finished video, no late reward, one live
// session). Each B['<File>.<function>'] below has the parameters of the original function it replaces.
var RewardedService = require('./RewardedService');
var config = require('./PlatformConfig');
var service = null;
var DEFAULT_KEY = '%(default)s';
var B = module.exports = {};

function svc() { return service || (service = new RewardedService()); }
function key(k, fallback) {
  var map = config.placementMap || {};
  if (typeof k === 'string' && map[k] !== undefined && map[k] !== null) return k;
  return map[fallback] !== undefined ? fallback : DEFAULT_KEY;
}
function call(fn, args) {
  if (typeof fn !== 'function') return;
  try { fn.apply(null, args); } catch (e) { try { console.error('[AdBridge]', e); } catch (_) {} }
}
function touchSDK() {
  var c = [typeof TTMinis !== 'undefined' && TTMinis && TTMinis.game, typeof tt !== 'undefined' && tt,
    typeof wx !== 'undefined' && wx];
  for (var i = 0; i < c.length; i++) if (c[i] && typeof c[i].onTouchStart === 'function') return c[i];
  return null;
}
// run(placementKey, onOk, onFail): exactly one of the two is called, once, never after a timeout or X.
// No callback 30 s after playback started: the next tap on the game counts as the X (RewardedService.exit()).
// showToast: true when the original function had no failure callback of its own (its own messages were in the body
// this bridge replaced), so a result without reward still shows RewardedService's message.
function toast(text) {
  if (!text) return;
  var c = [typeof TTMinis !== 'undefined' && TTMinis && TTMinis.game, typeof tt !== 'undefined' && tt,
    typeof wx !== 'undefined' && wx];
  for (var i = 0; i < c.length; i++) {
    if (c[i] && typeof c[i].showToast === 'function') {
      try { c[i].showToast({title: text, icon: 'none', duration: 2000}); } catch (_) {}
      return;
    }
  }
}
function run(placement, onOk, onFail, showToast) {
  var s = svc(), settled = false, sdk = null;
  function exitTap() { try { s.exit(); } catch (_) {} }
  function unarm() { if (sdk && typeof sdk.offTouchStart === 'function') { try { sdk.offTouchStart(exitTap); } catch (_) {} } sdk = null; }
  function settle(r) {
    if (settled) return;
    settled = true;
    unarm();
    r = r || {status: 'error', rewarded: false, message: 'The video could not open. Please try again.'};
    if (r.rewarded === true) { call(onOk, [r]); return; }
    if (showToast) toast(r.message);
    call(onFail, [r]);
  }
  var p;
  try {
    p = s.request({placementKey: placement, onExitAvailable: function () {
      sdk = touchSDK();
      if (sdk) { try { sdk.onTouchStart(exitTap); } catch (_) { sdk = null; } }
    }});
  } catch (e) { p = Promise.resolve({status: 'error', rewarded: false}); }
  p.then(settle, function () { settle({status: 'error', rewarded: false}); });
  return p;
}
// The original code that only created the ad object gets this inert one: show() fails at once, nothing plays,
// nothing is granted. The rewired show function above never uses it.
function inertAd() {
  function no() { return Promise.reject({errCode: -1, errMsg: 'AdBridge: rewarded ads go through RewardedService'}); }
  function noop() {}
  return {show: no, load: no, destroy: noop, onLoad: noop, offLoad: noop, onClose: noop, offClose: noop,
    onError: noop, offError: noop};
}
// P14: add-to-home / profile-revisit amount, only from PlatformConfig.growthReward() (5B, Saul 2026-10-29).
function growthAmount() { return config.growthReward(); }
function growthText(suffix) { try { return '+' + config.growthReward() + (suffix || ''); } catch (_) { return ''; } }
B.run = run;
B.key = key;
B.inertAd = inertAd;
B.growthAmount = growthAmount;
B.growthText = growthText;
B.useService = function (s) { service = s; };   // tests only
"""


def bridge_text(entries):
    return BRIDGE_HEAD % {'default': DEFAULT_KEY} + '\n' + '\n'.join(entries)


def existing_entries(text):
    """{'B["X.f"': entry text} of a generated AdBridge.js."""
    out = {}
    for m in re.finditer(r'^B\[(".*?")\] = function .*?^\};\n', text, re.M | re.S):
        out['B[' + m.group(1)] = m.group(0)
    return out


def _apply_edits(text, edits):
    seen, out = set(), text
    for a, b, new in sorted(set(edits), key=lambda e: e[0], reverse=True):
        if any(a < y and x < b for x, y in seen):
            continue                                       # overlapping edit: keep the first (outermost) one
        seen.add((a, b))
        out = out[:a] + new + out[b:]
    return out


def rewire(project, write=True):
    """rewire-ads: rewrite the recognised ad functions and MissionFlow rewards. -> record (see module doc)."""
    started = time.time()
    project = Path(project)
    entries, changed, rewired, todo = [], [], [], []
    v3 = engine(project) == 3
    for rel, p in game_files(project):
        if is_kit_file(rel) or v3:            # 3.x: nothing rewritten, plan() lists every site as by hand
            continue
        try:
            text = p.read_bytes().decode('utf-8')        # bytes: keep CRLF and the rest of the file exactly
        except UnicodeDecodeError:
            todo.append({'kind': 'ad', 'file': rel, 'line': 0, 'function': None, 'shape': None, 'auto': False,
                         'why': 'not UTF-8; not rewritten'})
            continue
        masked = mask(text)
        funcs = functions(text, masked)
        edits = []
        for row in scan_ads(rel, text, masked, funcs):
            if row['auto']:
                edits.append(row['edit'])
                if row.get('bridge'):
                    entries.append(row['bridge'])
                rewired.append({k: row[k] for k in ('kind', 'file', 'line', 'function', 'shape')})
            else:
                todo.append(row)
        for row in scan_growth(rel, text, masked, funcs):
            if row['auto']:
                edits += row['edits'] + _const_edits(text, masked, row['consts'], row['edits'])
                rewired.append({k: row[k] for k in ('kind', 'file', 'line', 'function', 'shape')})
        if not edits:
            continue
        new = _apply_edits(text, edits)
        if new != text:
            changed.append(rel)
            if write:
                backup = project / BACKUP / rel
                backup.parent.mkdir(parents=True, exist_ok=True)
                if not backup.exists():
                    shutil.copy2(p, backup)
                p.write_bytes(new.encode('utf-8'))
    bridge = project / BRIDGE_PATH
    old = existing_entries(bridge.read_text(encoding='utf-8')) if bridge.is_file() else {}
    for entry in entries:                       # a second run keeps the functions rewired by the first one
        old[entry.split(']', 1)[0]] = entry
    entries = list(old.values())
    if entries or any(r['kind'] == 'growth' for r in rewired):
        body = bridge_text(entries)
        if write and (not bridge.is_file() or bridge.read_text(encoding='utf-8') != body):
            bridge.parent.mkdir(parents=True, exist_ok=True)
            bridge.write_text(body, encoding='utf-8')
            changed.append(BRIDGE_PATH)
    after = plan(project) if write else None
    record = {'kind': 'rewire-ads', 'created': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'rewired': rewired,
              'changed': changed, 'bridge': BRIDGE_PATH if (project / BRIDGE_PATH).is_file() or entries else None,
              'rewire_todo': (after or {}).get('rewire_todo', [{k: v for k, v in r.items() if k != 'edit'}
                                                               for r in todo]),
              'delete_list': (after or {}).get('delete_list', []),
              'kit_copies': (after or {}).get('kit_copies', []),
              'next': 'run tiktok_finalize.py sync before the build (installs RewardedService.js / PlatformConfig.js '
                      'and moves same-name old kit copies away); handle every rewire_todo row by hand',
              'seconds': round(time.time() - started, 3)}
    if write:
        path = project / RECORD
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return record
