"""Source step (read only, under 1 s): hand-built popups, hard-coded mask colours and developer text in player strings
(生成时预防 Round 4 R4F3: #36 P05-5 / P09-3 and 补查第 4 组 T12:dev_text_residue).

The census counts button_covered 14 games, popup_close_dead 10, callback_missing 11 and too_dark 11, all in popups
written by hand (new cc.Node + BlockInputEvents + an own mask and fade) instead of parts/GameUIKit.js; and 9 times in
8 games a developer word reached the player (回家快跑: the ad-unavailable toast said "LOCAL PREVIEW"). Both are visible
in the code the moment it is generated, so they are reported here, where the code is written, before any trial.

Scans assets/**/*.js|*.ts (not assets/tiktok-platform/, not files with kit bytes, not files over 300 KB / minified)
and the cc.Label strings of scenes and prefabs (.fire / .scene / .prefab):
  K_ui_handmade_popup  a script that makes nodes (`new cc.Node(` / `new Node(`) and adds BlockInputEvents but never
                       uses GameUIKit (require('GameUIKit') / import ... GameUIKit / UI.popup). Fix: UI.popup(...),
                       or UI.adoptPopup({isOpen, setCovered}) for another kit's popup.
  K_ui_mask_hardcoded  a mask / dim / shade / overlay / curtain / modal node given a number opacity (not 0 or 255, the
                       fade ends) or a literal colour in the code (`mask.opacity = 160`, `this.dim.color =
                       cc.color(0,0,0)`, `cc.tween(mask).to(.2, {opacity: 150})`, `g.fillColor = cc.color(0,0,0,150)`
                       on a mask Graphics). Fix: let UI.popup lay the mask; its colour comes from
                       UI.setup({maskColor, maskOpacity}) (style.json line colour). The `maskColor:` / `maskOpacity:`
                       option keys of UI.setup / UI.popup are that route and are not reported. Brightness itself is
                       not measured (Saul 10-31: no brightness gate on masks); only where the value is written.
  K_dev_text           a player-facing string (`.string =`, toast / showToast / showModal / setLabel, `text:` /
                       `title:` / `content:` / `tip` keys, Label strings in scenes and prefabs) carrying a developer
                       word: PREVIEW, DEBUG, TODO, FIXME, TEST, "local preview", "debug", "placeholder", "lorem ipsum",
                       测试, 调试, 预览版, 占位, 待替换. Log, warn, error and throw lines are not player text.
                       Fix: player text comes from the game's text table; preview-only words stay in the
                       serve_preview shell, never in the game code.
  K_ui_label_order     (R4N4, 补查2 第 3 组) a Label made in code (`x = node.addComponent(cc.Label)`, `new cc.Label(`,
                       3.x `addComponent(Label)`) whose `.string` is set before its `.overflow` within 40 lines, or
                       (R4O5) with no overflow while its node is given a size or it wraps (`addComponent(Label).string =`
                       too); a short one-line value Label with no size and no wrap is not reported. SLS35: under Overflow.NONE the node
                       grew to the text, about 1.5 screens wide. Fix: UI.text(parent, {w, h, text, overflow}).
  K_tween_stop_all     (R4N4, 补查2 第 10 组) `Tween.stopAll(` / `cc.Tween.stopAll(` / `getActionManager().removeAllActions(`
                       / stopAllActions on a canvas / root / scene node. SLS35 Retry / Home also killed the popup's
                       closing tween. Fix: session.track(node) + newRun (RunSession 1.2), or stopAllByTarget.
                       Both R4N4 findings are warnings for new and English games, info for legacy games.
A line (or the line just above it) carrying `// tiktok-kit:ui-ok <why>` is skipped.
New games (board remake, policy new): K_dev_text blocks (the source record refuses and the writers refuse it by K5);
K_ui_handmade_popup and K_ui_mask_hardcoded are warnings (K_W_...) until calibrated clean (NEW_GAME_LEVEL), and block
a new game started with GameUIKit (GameUIKit.js / .ts installed and begun by init after 11.13, R4L1: ui_kit_era).
English (board localize): warnings (the English pack keeps the original popups). Legacy games: report only (info).
Called by tiktok_finalize `source` (SOURCE_STEPS) and, from R4J2, `sync` (SYNC_SOURCE_STEPS, before every build).
"""
import json
import re
import time

from . import Result, sha256

STEP = 'ui_kit_scan'
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', '.tiktok-kit', '__macosx', 'profiles'}
KIT_DIR = 'assets/tiktok-platform/'
MAX_BYTES = 300 * 1024
EXEMPT = 'tiktok-kit:ui-ok'
SCENE_SUFFIXES = ('.fire', '.scene', '.prefab')

NEW_NODE = re.compile(r'new\s+(?:cc\s*\.\s*)?Node\s*\(')
BLOCK_INPUT = re.compile(r'\bBlockInputEvents\b')
USES_KIT = re.compile(r'\bGameUIKit\b|\bUI\s*\.\s*(?:popup|adoptPopup|pausePage|revivePage|resultPage)\s*\(')
MASK_WORDS = {'mask', 'dim', 'dimmer', 'shade', 'shader_bg', 'overlay', 'curtain', 'modal', 'veil', 'blackbg',
              'black_bg', 'shadowbg', 'zhezhao'}
IDENT = re.compile(r'[A-Za-z_$][\w$]*')
OPTION_KEY = re.compile(r'\bmask(?:Color|Opacity|Alpha)\s*:')
SET_OPACITY = re.compile(r'([\w$.\[\]]+)\s*\.\s*opacity\s*=(?!=)\s*(\d+(?:\.\d+)?)\b')
TWEEN_OPACITY = re.compile(r'\bopacity\s*:\s*(\d+(?:\.\d+)?)\b')
SET_COLOR = re.compile(r'([\w$.\[\]]+)\s*\.\s*(?:color|fillColor)\s*=(?!=)\s*(?:new\s+)?(?:cc\s*\.\s*)?Color\b'
                       r'|([\w$.\[\]]+)\s*\.\s*(?:color|fillColor)\s*=(?!=)\s*(?:cc\s*\.\s*)?color\s*\(')
NOT_PLAYER = re.compile(r'\bconsole\s*\.|\bcc\s*\.\s*(?:log|warn|error|assert)\b|\bthrow\b|\bError\s*\(|'
                        r'\.(?:log|warn|error|debug|info)\s*\(|\brequire\s*\(|\bimport\b|\bfrom\b')
PLAYER = re.compile(r'\.\s*string\s*=(?!=)|\b(?:show)?[Tt]oast\s*\(|\bshowModal\s*\(|\bsetLabel\s*\(|'
                    r'\bsetString\s*\(|\b(?:text|title|content|tip|tips|desc|label|msg|message)\s*:')
DEV_CS = re.compile(r'(?<![A-Za-z])(?:PREVIEW|DEBUG|TODO|FIXME|TEST|XXX)(?![A-Za-z])')
DEV_CI = re.compile(r'(?i)\blocal\s+preview\b|\bdebug\b|\btodo\b|\bfixme\b|\bplaceholder\b|\blorem\s+ipsum\b|'
                    r'\btest\s+(?:build|mode|only|ad)\b|\bfor\s+testing\b')
DEV_ZH = re.compile(r'测试|调试|预览版|占位|待替换')


def _words(name):
    """`this.popupMask` -> {'this', 'popup', 'mask', 'popupmask'}; `dim_bg` -> {'dim', 'bg', 'dim_bg'}."""
    out = set()
    for part in re.split(r'[.\[\]\'"]+', name):
        if not part:
            continue
        out.add(part.lower())
        for w in re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+', part.replace('_', ' ').replace('$', ' ')):
            out.add(w.lower())
    return out


def _is_mask(name):
    return bool(_words(name) & MASK_WORDS)


def tokenize(text):
    """-> (code, strings). code: comments and string contents blanked (same length, newlines kept), an exemption
    comment kept as a marker; strings: [(offset, value)] of every string literal (template strings without ${})."""
    out, strings, i, n = [], [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith('//', i):
            j = text.find('\n', i)
            j = n if j < 0 else j
            out.append((EXEMPT if EXEMPT in text[i:j] else '').ljust(j - i))
            i = j
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r'[^\n]', ' ', text[i:j]))
            i = j
        elif c in '\'"`':
            j = i + 1
            while j < n and text[j] != c and (c == '`' or text[j] != '\n'):
                j += 2 if text[j] == '\\' else 1
            j = min(j + 1, n)
            strings.append((i, text[i + 1:j - 1]))
            out.append(c + re.sub(r'[^\n]', ' ', text[i + 1:j - 1]) + (c if j - 1 > i else ''))
            i = j
        else:
            out.append(c)
            i += 1
    return ''.join(out), strings


def _line_of(text, pos):
    return text.count('\n', 0, pos) + 1


def _exempt(code_lines, ln):
    return EXEMPT in code_lines[ln - 1] or (ln > 1 and code_lines[ln - 2].strip() == EXEMPT)


def _statement(code, pos):
    """The stripped statement around pos (from the last ; { } before it to the next ; or line end)."""
    start = max(code.rfind(ch, 0, pos) for ch in ';{}\n') + 1
    ends = [e for e in (code.find(';', pos), code.find('\n', pos)) if e >= 0]
    return code[start:min(ends) if ends else len(code)]


def dev_word(value):
    m = DEV_CS.search(value) or DEV_CI.search(value) or DEV_ZH.search(value)
    return m.group(0) if m else None


def scan_text(text, rel='?'):
    code, strings = tokenize(text)
    raw = text.split('\n')
    lines = code.split('\n')
    popups, masks, dev = [], [], []

    def src(ln):
        return raw[ln - 1].strip()[:120] if 0 < ln <= len(raw) else ''

    if NEW_NODE.search(code) and not USES_KIT.search(code + ''.join(v for _, v in strings if 'GameUIKit' in v)):
        for m in BLOCK_INPUT.finditer(code):
            ln = _line_of(code, m.start())
            before = code[max(code.rfind(';', 0, m.start()), code.rfind('}', 0, m.start())) + 1:m.start()]
            if re.match(r'\s*import\b', before):          # `import { ..., BlockInputEvents } from 'cc'` (3.x)
                continue
            if not _exempt(lines, ln):
                popups.append({'file': rel, 'line': ln, 'code': src(ln)})
    for ln, line in enumerate(lines, 1):
        if _exempt(lines, ln) or OPTION_KEY.search(line):
            continue
        hit = None
        for m in SET_OPACITY.finditer(line):
            if _is_mask(m.group(1)) and float(m.group(2)) not in (0.0, 255.0):
                hit = 'opacity %s' % m.group(2)
        for m in SET_COLOR.finditer(line):
            if _is_mask(m.group(1) or m.group(2)):
                hit = 'literal colour'
        if not hit and 'tween' in line:
            t = TWEEN_OPACITY.search(line)
            target = re.search(r'tween\s*\(\s*([\w$.\[\]]+)', line)
            if t and target and _is_mask(target.group(1)) and float(t.group(1)) not in (0.0, 255.0):
                hit = 'tween opacity %s' % t.group(1)
        if hit:
            masks.append({'file': rel, 'line': ln, 'code': src(ln), 'what': hit})
    for pos, value in strings:
        word = dev_word(value)
        if not word:
            continue
        ln = _line_of(text, pos)
        st = _statement(code, pos)
        if _exempt(lines, ln) or NOT_PLAYER.search(st) or not PLAYER.search(st):
            continue
        dev.append({'file': rel, 'line': ln, 'code': src(ln), 'word': word})
    return popups, masks, dev


# R4N4 (补查2 第 3 组, SLS35): a Label made in code gets its text before its overflow -> the node is sized to the text
NEW_LABEL = re.compile(r'(?:\b(?:var|let|const)\s+|\b)([\w$.]+)(?:\s*:\s*[\w$.]+)?\s*=(?!=)\s*(?:<[^>]*>\s*)?'
                       r'(?:[^=;\n]*?\.\s*)?(?:addComponent\s*\(\s*(?:cc\s*\.\s*)?Label\s*\)|new\s+(?:cc\s*\.\s*)?Label\s*\()')
CHAIN_LABEL = re.compile(r'addComponent\s*\(\s*(?:cc\s*\.\s*)?Label\s*\)\s*\.\s*string\s*=(?!=)')
LABEL_WINDOW = 40          # lines after the Label is made in which its .overflow must come before its .string
LABEL_BEFORE = 10          # R4O5: lines above it in which its node may already have been given a size
SIZE_TAIL = r'(?:setContentSize\s*\(|(?:width|height)\s*=(?!=))'
OWNER_BEFORE = re.compile(r'([\w$]+(?:\s*\.\s*[\w$]+)*)\s*\.\s*$')   # `node.` / `this.panel.` just before addComponent
# R4N4 (补查2 第 10 组, SLS35 Retry / Home): a global tween / action stop also kills the popup's closing tween
TWEEN_STOP_ALL = re.compile(r'(?<![\w$.])(?:cc\s*\.\s*)?Tween\s*\.\s*stopAll\s*\(|'
                            r'getActionManager\s*\(\s*\)\s*\.\s*removeAllActions\s*\(')
STOP_ALL_ACTIONS = re.compile(r'([\w$.\[\]()\'"]+?)\s*\.\s*stopAllActions\s*\(')
ROOT_WORDS = {'canvas', 'root', 'scene', 'getscene', 'rootnode'}


def _label_order(code, raw, lines, rel):
    out = []

    def src(ln):
        return raw[ln - 1].strip()[:120] if 0 < ln <= len(raw) else ''

    def window(start, end):
        """(text from LABEL_BEFORE lines above start, text up to LABEL_WINDOW lines after end)."""
        head = start
        for _ in range(LABEL_BEFORE):
            k = code.rfind('\n', 0, head)
            if k < 0:
                head = 0
                break
            head = k
        stop = end
        for _ in range(LABEL_WINDOW):
            k = code.find('\n', stop + 1)
            if k < 0:
                stop = len(code)
                break
            stop = k
        return code[head:start], code[end:stop]

    for m in CHAIN_LABEL.finditer(code):
        ln = _line_of(code, m.start())
        if _exempt(lines, ln):
            continue
        # R4O5: `owner.addComponent(Label).string = ...` is reported only when the owner node is given a size: a short
        # one-line value under Overflow.NONE is fine (R4N4 calibration: 32 of 37 new games, mostly these).
        owner = OWNER_BEFORE.search(code[max(0, m.start() - 200):m.start()])
        before, after = window(m.start(), m.end())
        if owner and _sized(owner.group(1), None, before + after):
            out.append({'file': rel, 'line': ln, 'code': src(ln), 'what': 'addComponent(Label).string =, sized node'})
    for m in NEW_LABEL.finditer(code):
        name = m.group(1)
        ln = _line_of(code, m.start())
        if _exempt(lines, ln):
            continue
        owner = OWNER_BEFORE.search(m.group(0).split('=', 1)[-1].split('addComponent', 1)[0])
        before, tail = window(m.start(), m.end())
        esc = re.escape(name)
        again = re.search(r'(?<![\w$.])' + esc + r'\s*=(?!=)\s*', tail)
        if again:
            tail = tail[:again.start()]          # the variable is given another Label: the window ends there
        st = re.search(r'(?<![\w$])' + esc + r'\s*\.\s*string\s*=(?!=)', tail)
        if not st:
            continue
        ov = re.search(r'(?<![\w$])' + esc + r'\s*\.\s*overflow\s*=(?!=)', tail)
        if ov and ov.start() < st.start():
            continue
        if not ov and not _sized(owner.group(1) if owner else None, name, before + tail):
            continue                             # R4O5: no overflow, no size, no wrap: a short one-line value Label
        out.append({'file': rel, 'line': ln, 'code': src(ln),
                    'what': '%s.string before %s.overflow' % (name, name) if ov else
                    '%s.string, sized or wrapped, no overflow' % name})
    return out


def _sized(owner, name, text):
    """R4O5: the Label's node is given a size (setContentSize / width / height, also through UITransform) or the Label
    wraps (enableWrapText = true) in `text`. owner: the node expression the Label was added to; name: the Label var."""
    pats = []
    if name:
        e = re.escape(name)
        pats.append(r'(?<![\w$])' + e + r'\s*\.\s*enableWrapText\s*=\s*true')
        pats.append(r'(?<![\w$])' + e + r'\s*\.\s*node\s*\.\s*' + SIZE_TAIL)
        pats.append(r'(?<![\w$])' + e + r'\s*\.\s*node\s*\.\s*getComponent\s*\(\s*(?:cc\s*\.\s*)?UITransform\s*\)\s*!?\s*\.\s*' + SIZE_TAIL)
    if owner:
        e = re.escape(owner)
        pats.append(r'(?<![\w$.])' + e + r'\s*\.\s*' + SIZE_TAIL)
        pats.append(r'(?<![\w$.])' + e + r'\s*\.\s*(?:getComponent|addComponent)\s*\(\s*(?:cc\s*\.\s*)?UITransform\s*\)\s*!?\s*\.\s*' + SIZE_TAIL)
    return any(re.search(p, text) for p in pats)


def _tween_stop_all(code, raw, lines, rel):
    out = []
    for ln, line in enumerate(lines, 1):
        if _exempt(lines, ln):
            continue
        hit = None
        m = TWEEN_STOP_ALL.search(line)
        if m:
            hit = re.sub(r'\s+', '', m.group(0)).rstrip('(')
        else:
            for s in STOP_ALL_ACTIONS.finditer(raw[ln - 1] if 'stopAllActions' in line and ln <= len(raw) else ''):
                recv = s.group(1)
                last = re.split(r'\.', recv.replace('(', '.').replace(')', '.').strip('.'))
                words = _words(recv) if recv else set()
                if words & ROOT_WORDS or (last and last[-1].lower() in ROOT_WORDS):
                    hit = recv + '.stopAllActions'
                    break
        if hit:
            out.append({'file': rel, 'line': ln, 'code': raw[ln - 1].strip()[:120] if ln <= len(raw) else '',
                        'what': hit})
    return out


def scan_order(text, rel='?'):
    """R4N4 -> (labels, tweens): Labels made in code whose .string comes before .overflow (or without overflow), and
    global tween / action stops (Tween.stopAll, cc.Tween.stopAll, getActionManager().removeAllActions, a root node's
    stopAllActions)."""
    code, _ = tokenize(text)
    raw = text.split('\n')
    lines = code.split('\n')
    return _label_order(code, raw, lines, rel), _tween_stop_all(code, raw, lines, rel)


def scan_scene(text, rel='?'):
    """Developer words in cc.Label strings of a scene / prefab (JSON list of objects)."""
    try:
        data = json.loads(text)
    except ValueError:
        return []
    out = []
    for k, obj in enumerate(data if isinstance(data, list) else []):
        if not isinstance(obj, dict) or obj.get('__type__') not in ('cc.Label', 'cc.RichText'):
            continue
        for key in ('_string', '_N$string', 'string'):
            value = obj.get(key)
            word = dev_word(value) if isinstance(value, str) else None
            if word:
                out.append({'file': rel, 'line': k, 'code': value[:120], 'word': word})
    return out


def _skip(rel):
    return rel.startswith(KIT_DIR) or bool(SKIP_DIRS & {x.lower() for x in rel.split('/')[:-1]})


def scan(root, kit_hashes=()):
    started = time.time()
    found = {'files': 0, 'popups': [], 'masks': [], 'dev': [], 'labels': [], 'tweens': []}
    base = root / 'assets'
    for p in sorted(base.rglob('*')) if base.is_dir() else []:
        rel = p.relative_to(root).as_posix()
        if not p.is_file() or _skip(rel) or p.stat().st_size > MAX_BYTES * (20 if p.suffix in SCENE_SUFFIXES else 1):
            continue
        if p.suffix in ('.js', '.ts'):
            data = p.read_bytes()
            if sha256(data) in kit_hashes:
                continue
            text = data.decode('utf-8', 'replace')
            if text.count('\n') < len(text) / 2000:          # minified library
                continue
            found['files'] += 1
            a, b, c = scan_text(text, rel)
            found['popups'] += a
            found['masks'] += b
            found['dev'] += c
            d, e = scan_order(text, rel)
            found['labels'] += d
            found['tweens'] += e
        elif p.suffix in SCENE_SUFFIXES:
            found['files'] += 1
            found['dev'] += scan_scene(p.read_bytes().decode('utf-8', 'replace'), rel)
    found['seconds'] = round(time.time() - started, 3)
    return found


# Level for new remake games, per finding. Calibration 2026-11-05 (read only): 8 of 9 remake games in progress and
# Marlows R6 build popups by hand (started before GameUIKit, 11.13), so the popup and mask findings start as warnings
# (K_W_...; team lead decision). Set them back to 'block' once finished games and newly started projects scan clean.
NEW_GAME_LEVEL = {'K_ui_handmade_popup': 'warn', 'K_ui_mask_hardcoded': 'warn', 'K_dev_text': 'block',
                  # R4N4: warnings for new games (calibration 2026-11-05 in 说明.md of the R4N4 patch)
                  'K_ui_label_order': 'warn', 'K_tween_stop_all': 'warn'}

# 生成时预防 R4L1: the two warnings above block a new game that was STARTED with GameUIKit, because that game had the
# kit from its first line of code and has no reason to build a popup by hand. "Started with" needs both:
#   1. the part is installed: assets/tiktok-platform/GameUIKit.js (2.4) or GameUIKit.ts (3.x), and
#   2. the start record says so: .tiktok-kit/policy.json written by `init` with "ui_kit_at_start": true (init from
#      R4L1 on), or written by `init` at or after UI_KIT_SINCE (英化 简化.11.13, the first pack with GameUIKit).
# The installed file alone is not enough: `sync` installs GameUIKit into every new game, also into the games begun
# before 11.13 (calibration 2026-11-05: 25 marked projects, all begun 10-29..10-31, none has the file yet), which
# would turn every one of them into a block at its next sync. Markers written by `adopt` or by `source` (auto) are
# existing games taken over, never "started with the kit".
UI_KIT_FILES = ('assets/tiktok-platform/GameUIKit.js', 'assets/tiktok-platform/GameUIKit.ts')
UI_KIT_SINCE = '2026-11-04T19:00:00-0800'
KIT_ERA_GATES = ('K_ui_handmade_popup', 'K_ui_mask_hardcoded')


def ui_kit_era(root):
    """-> (started_with_kit, why) for the project at root (read only)."""
    import datetime
    from .policy import read_marker
    have = [f for f in UI_KIT_FILES if (root / f).is_file()]
    if not have:
        return False, 'GameUIKit not installed in the project'
    mark = read_marker(root) or {}
    if mark.get('by') != 'init':
        return False, '%s installed, but the project was not started by init (marker by %s)' % (
            have[0], mark.get('by') or 'none')
    if mark.get('ui_kit_at_start') is True:
        return True, '%s installed and policy.json ui_kit_at_start' % have[0]
    try:
        created = datetime.datetime.strptime(str(mark.get('created')), '%Y-%m-%dT%H:%M:%S%z')
        since = datetime.datetime.strptime(UI_KIT_SINCE, '%Y-%m-%dT%H:%M:%S%z')
    except ValueError:
        return False, '%s installed, start time not readable' % have[0]
    if created >= since:
        return True, '%s installed and started %s (after GameUIKit came out)' % (have[0], mark.get('created'))
    return False, '%s installed, but started %s, before GameUIKit (11.13)' % (have[0], mark.get('created'))


def level_of(policy='new', board=None, gate=None, kit_era=False):
    if policy == 'legacy':
        return 'info'
    if board == 'localize':
        return 'warn'
    if kit_era and gate in KIT_ERA_GATES:
        return 'block'
    return NEW_GAME_LEVEL.get(gate, 'block')


def findings(found, policy='new', board=None, kit_era=False):
    """-> [(level, finding)] level block | warn | info. kit_era: the game was started with GameUIKit (R4L1)."""
    out = []

    def add(gate, items, text):
        if not items:
            return
        level = level_of(policy, board, gate, kit_era)
        shown = '; '.join('%s:%d %s' % (x['file'], x['line'], x['code']) for x in items[:8])
        gid = gate if level == 'block' else gate.replace('K_', 'K_W_', 1)
        out.append((level, {'id': gid, 'level': level, 'message': text % (len(items), shown),
                            'evidence': items[:30]}))

    add('K_ui_handmade_popup', found['popups'],
        '%d popup(s) built by hand (new cc.Node + BlockInputEvents, no GameUIKit): %s. Hand-built popups are where '
        'buttons get covered, X stops working and callbacks go missing; use UI.popup(canvas, {...}) from '
        'assets/tiktok-platform/GameUIKit (another kit\'s popup: UI.adoptPopup)')
    add('K_ui_mask_hardcoded', found['masks'],
        '%d mask colour / opacity value(s) written in panel code: %s. Let UI.popup lay the mask and set the colour '
        'once with UI.setup({maskColor, maskOpacity}) from style.json')
    add('K_dev_text', found['dev'],
        '%d player-facing string(s) with a developer word: %s. Player text comes from the game\'s text table; '
        'preview-only words stay in the serve_preview shell')
    add('K_ui_label_order', found.get('labels', []),
        '%d Label(s) made in code get their text before overflow / wrapping: %s. Under Overflow.NONE the engine sizes '
        'the node to the text (SLS35: rules text about 1.5 screens wide); make body text with UI.text(parent, {w, h, '
        'text, overflow}) from GameUIKit, or set the box, overflow and enableWrapText before .string')
    add('K_tween_stop_all', found.get('tweens', []),
        '%d global tween / action stop(s): %s. Retry / Home with a global stop also kills the popup\'s closing tween '
        '(SLS35); register the run\'s nodes with session.track(node) (RunSession: newRun stops only those) or stop '
        'by target (cc.Tween.stopAllByTarget(node))')
    return out


def detect(ctx):
    found = scan(ctx.root)
    return 'conflict' if found['popups'] or found['masks'] or found['dev'] or found['labels'] or found['tweens'] \
        else 'kit_current'


def apply(ctx):
    r = Result(STEP)
    hashes = ctx.manifest.kit_hashes() if ctx.manifest else set()
    found = scan(ctx.root, hashes)
    era, why = ui_kit_era(ctx.root)
    for level, item in findings(found, ctx.policy, getattr(ctx, 'board', None), era):
        if level == 'block':
            r.blocks.append(item)
        elif level == 'warn':
            r.warnings.append(item)
        else:
            r.info.append('%s (report only): %s' % (item['id'], item['message']))
    r.state = 'conflict' if r.blocks else 'kit_current'
    r.info.append('%d file(s) scanned in %.2f s; %d hand-built popup(s), %d hard-coded mask value(s), %d developer '
                  'string(s)' % (found['files'], found['seconds'], len(found['popups']), len(found['masks']),
                                 len(found['dev'])))
    r.info.append('R4N4: %d Label(s) given text before overflow, %d global tween / action stop(s)' % (
        len(found['labels']), len(found['tweens'])))
    r.info.append('hand-built popups / mask values %s: %s' % ('block (started with GameUIKit)' if era else
                                                             'warn only', why))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    return []
