"""Source step (read only, under 1 s): Cocos 3.x home entries placed by hand while HomeEntrySlots is installed
(生成时预防 Round 4 R4L1, R4G1 leftover; P06 3 / P14 2, element_overlap 64 games / 99 times).

R4G1 installs plugins-3x/HomeEntrySlots.plugin.js into new 3.x games so the profile-revisit and add-to-desktop entries
find a free place at runtime (TikTokKit.HomeEntrySlots.placeLater(cc, this, {root, entries})). A home script that
still writes the entries' coordinates itself (`profileBtn.setPosition(-220, -760)`, `shortcut.position = v3(0, -700)`)
and never calls place / placeLater keeps the overlap the census found. Reported here, where the code is written.

Scans assets/**/*.ts|*.js (not assets/tiktok-platform/, not kit bytes, not files over 300 KB / minified) when the
project is Cocos 3.x and assets/tiktok-platform/HomeEntrySlots.plugin.js is present:
  K_home_entry_coords  a position written with number literals (setPosition(n, ..), position = v3(n, ..) /
                       new Vec3(n, ..), .x = n / .y = n) on a node whose name or path names an entry (profile, revisit,
                       homepage, shortcut, desktop, sidebar, 主页, 回访, 桌面), and no project script calls
                       HomeEntrySlots.place( / placeLater(. Fix: build the two nodes anywhere, then
                       TikTokKit.HomeEntrySlots.placeLater(cc, this, {root: canvasNode, entries: [profile, shortcut]}).
A line (or the line just above it) carrying `// tiktok-kit:ui-ok <why>` is skipped.
New games (remake and English): warning K_W_home_entry_coords. Legacy games: report only (info). 2.4: n/a (2.4 uses
HomeGrowthEntries, which places the entries itself).
"""
import re
import time

from . import Result, sha256
from .ui_kit_scan import MAX_BYTES, _exempt, _skip, _words, tokenize

STEP = 'home_entry_scan'
PLUGIN = 'assets/tiktok-platform/HomeEntrySlots.plugin.js'
ENTRY_WORDS = {'profile', 'revisit', 'homepage', 'shortcut', 'shortcuts', 'desktop', 'sidebar'}
ENTRY_SUBSTR = ('addtodesktop', 'adddesktop', 'addshortcut', 'homepage', 'profileentry', '主页', '回访', '桌面')
CALLS_SLOTS = re.compile(r'\bHomeEntrySlots\s*\.\s*(?:place|placeLater)\s*\(')
NUM = r'\s*[-+]?\d+(?:\.\d+)?'
TARGET = r'((?:[\w$]+|\))(?:\s*!|\s*\??\.\s*[\w$]+|\s*\([^()]*\)|\s*\[[^\]]*\])*?)'
SET_POS = [re.compile(TARGET + r'\s*\.\s*setPosition\s*\(' + r'(?:\s*(?:new\s+)?(?:cc\s*\.\s*)?(?:v3|v2|Vec3|Vec2)\s*\()?' + NUM),
           re.compile(TARGET + r'\s*\.\s*position\s*=(?!=)\s*(?:new\s+)?(?:cc\s*\.\s*)?(?:v3|v2|Vec3|Vec2)\s*\(' + NUM),
           re.compile(TARGET + r'\s*\.\s*[xy]\s*=(?!=)' + NUM + r'\s*(?:;|$|,)')]


FACTORY = re.compile(r'(?i)\b[\w$]*(?:button|btn|entry|icon)[\w$]*\s*\(')
PURE_NUM = re.compile(r'^\s*[-+]?\d+(?:\.\d+)?\s*$')


def _args(code, start):
    """Top-level argument spans of the call whose '(' is at code[start - 1] -> [(a, b)], end."""
    depth, a, out, i = 0, start, [], start
    while i < len(code):
        c = code[i]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            if depth == 0:
                out.append((a, i))
                return out, i
            depth -= 1
        elif c == ',' and depth == 0:
            out.append((a, i))
            a = i + 1
        i += 1
    return out, i


def _factory_hits(text, code, strings):
    """Button factories given an entry name and number coordinates: this.button('profile', base, 'ProfileRevisit',
    165, -top + 128, 300, 96, cb) (CloverCourier EnglishUI.ts). Only identifier-like strings count as names, so a
    label such as 'ADD SHORTCUT' does not."""
    hits = []
    for m in FACTORY.finditer(code):
        spans, end = _args(code, m.end())
        names = [v for p, v in strings if m.end() <= p < end and re.fullmatch(r'[\w$.\-/]+', v or '')]
        nums = sum(1 for a, b in spans if PURE_NUM.match(code[a:b]))
        if nums >= 2 and any(_is_entry(v) for v in names):
            hits.append(text.count('\n', 0, m.start()) + 1)
    return hits


def _is_entry(text):
    low = text.lower()
    return bool(_words(text) & ENTRY_WORDS) or any(s in low for s in ENTRY_SUBSTR)


def scan_text(text, rel='?'):
    """-> ([hand-placed entry lines], calls_place)."""
    code, strings = tokenize(text)
    raw = text.split('\n')
    lines = code.split('\n')
    calls = bool(CALLS_SLOTS.search(code))
    out = []
    # string literals per line (node names / paths such as find('Canvas/ProfileBtn'))
    by_line = {}
    for pos, value in strings:
        by_line.setdefault(text.count('\n', 0, pos) + 1, []).append(value)
    for ln, line in enumerate(lines, 1):
        if _exempt(lines, ln):
            continue
        for pat in SET_POS:
            m = pat.search(line)
            if not m:
                continue
            target = raw[ln - 1][m.start(1):m.end(1)] if ln <= len(raw) else m.group(1)
            if _is_entry(target) or (_is_entry(' '.join(by_line.get(ln, []))) and '(' in m.group(1)):
                out.append({'file': rel, 'line': ln, 'code': raw[ln - 1].strip()[:120]})
                break
    seen = {x['line'] for x in out}
    for ln in _factory_hits(text, code, strings):
        if ln not in seen and not _exempt(lines, ln):
            seen.add(ln)
            out.append({'file': rel, 'line': ln, 'code': raw[ln - 1].strip()[:120]})
    out.sort(key=lambda x: x['line'])
    return out, calls


def scan(root, kit_hashes=()):
    started = time.time()
    found = {'files': 0, 'entries': [], 'calls': [], 'plugin': (root / PLUGIN).is_file()}
    base = root / 'assets'
    for p in sorted(base.rglob('*')) if base.is_dir() and found['plugin'] else []:
        rel = p.relative_to(root).as_posix()
        if not p.is_file() or p.suffix not in ('.js', '.ts') or _skip(rel) or p.stat().st_size > MAX_BYTES:
            continue
        data = p.read_bytes()
        if sha256(data) in kit_hashes:
            continue
        text = data.decode('utf-8', 'replace')
        if text.count('\n') < len(text) / 2000:
            continue
        found['files'] += 1
        hits, calls = scan_text(text, rel)
        found['entries'] += hits
        if calls:
            found['calls'].append(rel)
    found['seconds'] = round(time.time() - started, 3)
    return found


def findings(found, policy='new'):
    if not found['plugin'] or not found['entries'] or found['calls']:
        return []
    level = 'info' if policy == 'legacy' else 'warn'
    shown = '; '.join('%s:%d %s' % (x['file'], x['line'], x['code']) for x in found['entries'][:8])
    return [(level, {'id': 'K_W_home_entry_coords', 'level': level,
                     'message': '%d hand-written coordinate(s) for the home profile / add-to-desktop entries while '
                                'HomeEntrySlots is installed and never called: %s. Build the two nodes, then call '
                                'TikTokKit.HomeEntrySlots.placeLater(cc, this, {root: canvasNode, entries: [profile, '
                                'shortcut]}) so they find a free place at runtime' % (len(found['entries']), shown),
                     'evidence': found['entries'][:30]})]


def detect(ctx):
    if ctx.engine != 3:
        return 'n/a'
    return 'conflict' if findings(scan(ctx.root)) else 'kit_current'


def apply(ctx):
    r = Result(STEP)
    if ctx.engine != 3:
        r.state = 'n/a'
        return r.as_dict()
    hashes = ctx.manifest.kit_hashes() if ctx.manifest else set()
    found = scan(ctx.root, hashes)
    for level, item in findings(found, ctx.policy):
        if level == 'warn':
            r.warnings.append(item)
        else:
            r.info.append('%s (report only): %s' % (item['id'], item['message']))
    r.state = 'kit_current'
    r.info.append('%s; %d file(s) scanned in %.2f s; %d hand-placed entry line(s); place / placeLater called in %s'
                  % ('HomeEntrySlots installed' if found['plugin'] else 'HomeEntrySlots not installed',
                     found['files'], found['seconds'], len(found['entries']), ', '.join(found['calls']) or 'none'))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    return []
