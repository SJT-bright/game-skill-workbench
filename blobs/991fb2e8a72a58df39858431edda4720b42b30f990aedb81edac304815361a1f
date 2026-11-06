"""Source step (read only, well under 1 s): save reads that turn a real 0 / false into the default, ad rewards whose
receipt is written apart from the grant, and level caps that differ from the real level count (生成时预防 Round 4
R4N6, 问题普查补查2 第 6 组 + 第 9 组关卡上限).

Census (09_补查2_20261105/occurrences.jsonl): 合成进化恐龙 GD.init moved old coins with `d.coin || 100`, so a saved 0
or false came back as 100 (T07 save_zero_defaulted); 奔跑吧巨人 paid the result x2 and wrote its receipt (run, x2,
amount) in a second save, so a failed save lost the receipt and the next claim paid x1 (T07
ad_receipt_lost_on_save_failure); 弹球传奇 had `_MapMax: 1000` with level files only up to 500 (T15
level_count_mismatch). SaveStore already keeps 0 / false and writes a grant in one update; these are the game's own
reads, written when the code is written, so they are reported here and at every sync.

Scans assets/**/*.ts|*.js (not assets/tiktok-platform/, not kit bytes, not files over 300 KB / minified):
  K_W_save_read_falsy_default  `<save read> || <default>` or `if (!<save read>) <save read> = <default>` where the
        default is a non-zero number, true or a non-empty text, and the read is getItem( / getStorageSync( /
        JSON.parse( or a field of a variable filled from one of them (or named data / save / saveData / gd / ...).
        A saved 0 / false / '' then comes back as the default. Fix: `x === undefined ? <default> : x` (or
        SaveStore + make_save_schema.py defaults).
  K_W_ad_receipt_split  an ad reward (x2 / double / multiplier / rewarded) paid with .grant({...}) that has no id,
        or a grant / wallet change followed within 12 lines by a separate save write of the receipt (receipt / runId
        / multiplier / adDone / claimed...). Fix: ONE grant({id: 'run:' + runId + ':x2', add: {coins: amount},
        apply: function (d) { d.lastReceipt = {...}; }}); a failed save is retried with the same id, never paid x1.
  K_W_level_cap_mismatch  a level cap constant (_MapMax / MAX_LEVEL / maxLevel / levelCount / totalLevels ...: a
        number >= 10) that differs from the level count on record: docs/levels/level_resources.json (written by
        make_level_plan.py --record-level-files) or level_plan.json total_levels. No record: nothing reported.
A line (or the line just above it) carrying `// tiktok-kit:save-ok <why>` is skipped.
Policy: new remake and English games: warning (the game's own code; English keeps the original logic, so it is a
to-do for the AI, not a block). Legacy games: report only (info).
"""
import json
import re
import time

from . import Result, sha256

STEP = 'save_read_scan'
MAX_BYTES = 300 * 1024
SKIP_PARTS = ('assets/tiktok-platform/', '/library/', '/temp/', '/build/', 'node_modules/')
EXEMPT = 'tiktok-kit:save-ok'
STORAGE_READ = re.compile(r'\b(?:getItem|getStorageSync|getStorage)\s*\(|\bJSON\s*\.\s*parse\s*\(')
SAVE_NAMES = {'data', 'save', 'saved', 'savedata', 'store', 'record', 'gd', 'userdata', 'localdata', 'storage',
              'archive'}
LONG_LINE = 600            # a longer line is bundled / minified engine output (delivery/ build copies), not game code
# default literal that hides a saved 0 / false / '': a non-zero number, true, a non-empty text
TRUTHY = r'''(?:-?(?:[1-9]\d*(?:\.\d+)?|0\.\d*[1-9]\d*)|true|'[^'\n]+'|"[^"\n]+")'''
OPERAND = r'''((?:[\w$]+(?:\s*\??\.\s*[\w$]+|\s*\[[^\]\n]*\]|\s*\([^()\n]*\))*))'''
OR_DEFAULT = re.compile(OPERAND + r'\s*\|\|\s*(' + TRUTHY + r')(?![\w.$])')
IF_NOT = re.compile(r'\bif\s*\(\s*!\s*' + OPERAND + r'\s*\)\s*\{?\s*([\w$.\[\]\'"]+)\s*=(?!=)\s*(' + TRUTHY + r')')
ASSIGN_FROM_READ = re.compile(r'(?:\b(?:var|let|const)\s+)?((?:this\s*\.\s*)?[\w$]+)\s*(?::\s*[\w$<>\[\]]+\s*)?=(?![=>])'
                              r'([^;\n]*)')
AD_WORDS = re.compile(r'(?i)x2|double|multiplier|\bmult\b|rewarded|watchad|showad|adsuccess|onadcomplete|adreward')
RECEIPT_WORDS = re.compile(r'(?i)receipt|runid|run_id|multiplier|\bmult\b|addone|adwatched|adcomplete|claimedrun|'
                           r'doubleclaimed|x2done|rewardtoken|pendingreward|\bclaimed\b')
GRANT_CALL = re.compile(r'\.\s*grant\s*\(')
WALLET_WRITE = re.compile(r'(?i)\b(?:coins?|gold|gems?|money|diamonds?|cash)\s*(?:\+=|=(?!=)[^;\n]*\+)')
SAVE_WRITE = re.compile(r'\.\s*(?:update|setItem|setStorageSync|setStorage|save|saveData|write)\s*\(')
CAP_NAME = re.compile(r'(?i)^_?(?:max_?(?:level|map|stage|chapter)s?|(?:level|map|stage)s?_?(?:max|count|limit)|'
                      r'total_?(?:level|map|stage)s|num_?(?:level|map|stage)s)$')   # not level_total (FogPier: tiles per level)
CAP_DEF = re.compile(r'(?:\b(?:var|let|const|static|readonly|private|public)\s+)*([\w$]+)\s*(?::\s*number\s*)?[:=](?![=>])'
                     r'\s*(\d{2,6})\s*(?:[,;)}\n]|//|$)')
PLAN_PATHS = ('assets/resources/config/level_plan.json', 'docs/levels/level_plan.json')
RESOURCES = 'docs/levels/level_resources.json'


def strip_comments(text):
    """Code with // and /* */ comments blanked (strings kept; line numbers kept)."""
    out, i, n, quote = [], 0, len(text), None
    while i < n:
        c = text[i]
        if quote:
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == quote or c == '\n':
                quote = None
            i += 1
            continue
        if c in '\'"`':
            quote = c
            out.append(c)
        elif text.startswith('//', i):
            j = text.find('\n', i)
            j = n if j < 0 else j
            out.append(' ' * (j - i))
            i = j
            continue
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(''.join(ch if ch == '\n' else ' ' for ch in text[i:j]))
            i = j
            continue
        else:
            out.append(c)
        i += 1
    return ''.join(out)


def _exempt(raw_lines, ln):
    return any(EXEMPT in raw_lines[k] for k in (ln - 1, ln - 2) if 0 <= k < len(raw_lines))


def _root(expr):
    m = re.match(r'\s*(?:this\s*\.\s*)?([\w$]+)', expr)
    return m.group(1).lower() if m else ''


def _tainted(code):
    """Variables filled from a storage read in this file (var d = JSON.parse(raw); this.save = ls.getItem(k))."""
    out = set()
    for m in ASSIGN_FROM_READ.finditer(code):
        if STORAGE_READ.search(m.group(2)):
            out.add(re.sub(r'^this\s*\.\s*', '', m.group(1)).lower())
    return out


def _is_save_read(expr, tainted):
    if STORAGE_READ.search(expr):
        return True
    root = _root(expr)
    if not re.search(r'[.\[]', expr):         # a bare variable: only when it was filled from a storage read
        return root in tainted
    first = re.sub(r'^this\s*\.\s*', '', expr.strip())
    root = re.match(r'[\w$]*', first).group(0).lower()
    return root in tainted or root in SAVE_NAMES


def falsy_defaults(code, raw, rel):
    hits = []
    if not STORAGE_READ.search(code) and not re.search(r'(?i)\b(?:save|savedata|gd|userdata)\b', code):
        return hits
    tainted = _tainted(code)
    for ln, line in enumerate(code.split('\n'), 1):
        if _exempt(raw, ln):
            continue
        for m in OR_DEFAULT.finditer(line):
            if _is_save_read(m.group(1), tainted):
                hits.append({'file': rel, 'line': ln, 'code': raw[ln - 1].strip()[:120],
                             'fix': '%s === undefined ? %s : %s' % (m.group(1).strip(), m.group(2), m.group(1).strip())})
                break
        else:
            m = IF_NOT.search(line)
            if m and m.group(1).replace(' ', '') == m.group(2).replace(' ', '') and _is_save_read(m.group(1), tainted):
                hits.append({'file': rel, 'line': ln, 'code': raw[ln - 1].strip()[:120],
                             'fix': 'if (%s === undefined) %s = %s' % (m.group(1).strip(), m.group(2), m.group(3))})
    return hits


def _call_args(code, start):
    """Text of the call whose '(' ends at code[start - 1] (balanced), or the rest of the line."""
    depth, i = 0, start
    while i < len(code):
        c = code[i]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            if depth == 0:
                return code[start:i]
            depth -= 1
        i += 1
    return code[start:]


def receipt_splits(code, raw, rel):
    hits = []
    lines = code.split('\n')
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line) + 1)
    for ln, line in enumerate(lines, 1):
        if _exempt(raw, ln):
            continue
        near = '\n'.join(lines[max(0, ln - 7):ln + 6])
        g = GRANT_CALL.search(line)
        if g:
            args = _call_args(code, starts[ln - 1] + g.end())
            if args.lstrip().startswith('{') and not re.search(r'(?:^|[{,\s])[\'"]?id[\'"]?\s*:', args) \
                    and AD_WORDS.search(near):     # SaveStore-style grant({...}); a game's own grant(type, receipt) is not it
                hits.append({'file': rel, 'line': ln, 'code': raw[ln - 1].strip()[:120],
                             'why': 'ad reward grant without a claim id'})
                continue
        if g or WALLET_WRITE.search(line):
            for k in range(ln, min(len(lines), ln + 12)):
                later = lines[k]
                s = SAVE_WRITE.search(later)
                if not s or _exempt(raw, k + 1):
                    continue
                args = _call_args(code, starts[k] + s.end()) + later[s.end():]
                body = args if not g else args
                if RECEIPT_WORDS.search(body[:400]) and (g or AD_WORDS.search(near)):
                    hits.append({'file': rel, 'line': k + 1, 'code': raw[k].strip()[:120],
                                 'why': 'receipt written apart from the reward (line %d)' % ln})
                    break
    seen, out = set(), []
    for h in hits:
        if h['line'] not in seen:
            seen.add(h['line'])
            out.append(h)
    return out


def level_caps(code, raw, rel):
    out = []
    for ln, line in enumerate(code.split('\n'), 1):
        if _exempt(raw, ln):
            continue
        for m in CAP_DEF.finditer(line):
            if CAP_NAME.match(m.group(1)) and int(m.group(2)) >= 10:
                out.append({'file': rel, 'line': ln, 'name': m.group(1), 'value': int(m.group(2)),
                            'code': raw[ln - 1].strip()[:120]})
    return out


def level_record(root):
    """(count, where) of the real level count on record, or (None, None)."""
    path = root / RESOURCES
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data.get('count'), int):
                return data['count'], RESOURCES
        except (OSError, ValueError, AttributeError):
            pass
    for rel in PLAN_PATHS:
        p = root / rel
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            if isinstance(data, dict) and isinstance(data.get('total_levels'), int):
                return data['total_levels'], rel + ' total_levels'
    return None, None


def scan_text(text, rel='?'):
    if 'cc._RF.push(' in text:              # a compiled Cocos bundle (build output copied under assets/)
        return {'falsy': [], 'receipt': [], 'caps': []}
    code = '\n'.join('' if len(l) > LONG_LINE else l for l in strip_comments(text).split('\n'))
    raw = text.split('\n')
    return {'falsy': falsy_defaults(code, raw, rel), 'receipt': receipt_splits(code, raw, rel),
            'caps': level_caps(code, raw, rel)}


def _skip(rel):
    low = '/' + rel.lower()
    return any(p in low for p in SKIP_PARTS) or rel.endswith('.d.ts') or rel.endswith('.min.js')


def scan(root, kit_hashes=()):
    started = time.time()
    found = {'files': 0, 'falsy': [], 'receipt': [], 'caps': []}
    base = root / 'assets'
    for p in sorted(base.rglob('*')) if base.is_dir() else []:
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
        for k, v in scan_text(text, rel).items():
            found[k] += v
    found['level_count'], found['level_where'] = level_record(root)
    found['seconds'] = round(time.time() - started, 3)
    return found


def _shown(items):
    return '; '.join('%s:%d %s' % (x['file'], x['line'], x['code']) for x in items[:6])


def findings(found, policy='new'):
    level = 'info' if policy == 'legacy' else 'warn'
    out = []
    if found['falsy']:
        out.append((level, {'id': 'K_W_save_read_falsy_default', 'level': level,
                            'message': '%d save read(s) turn a saved 0 / false / empty text into the default: %s. '
                                       'Write `x === undefined ? <default> : x` (first: %s)'
                                       % (len(found['falsy']), _shown(found['falsy']), found['falsy'][0]['fix']),
                            'evidence': found['falsy'][:30]}))
    if found['receipt']:
        out.append((level, {'id': 'K_W_ad_receipt_split', 'level': level,
                            'message': '%d ad reward(s) whose receipt is not in the same grant: %s. Pay it with ONE '
                                       "grant({id: 'run:' + runId + ':x2', add: {...}, apply: function (d) {/* receipt "
                                       '*/}}); on a failed save retry the same grant, never pay x1'
                                       % (len(found['receipt']), _shown(found['receipt'])),
                            'evidence': found['receipt'][:30]}))
    count = found.get('level_count')
    bad = [c for c in found['caps'] if count is not None and c['value'] != count]
    if bad:
        out.append((level, {'id': 'K_W_level_cap_mismatch', 'level': level,
                            'message': 'level cap constant(s) differ from the %d level(s) on record (%s): %s. Take the '
                                       'cap from the level table / level_resources.json, not a separate number'
                                       % (count, found['level_where'], '; '.join(
                                           '%s:%d %s = %d' % (c['file'], c['line'], c['name'], c['value']) for c in bad[:6])),
                            'evidence': bad[:30]}))
    return out


def detect(ctx):
    return 'conflict' if findings(scan(ctx.root)) else 'kit_current'


def apply(ctx):
    r = Result(STEP)
    hashes = ctx.manifest.kit_hashes() if ctx.manifest else set()
    found = scan(ctx.root, hashes)
    for level, item in findings(found, ctx.policy):
        if level == 'warn':
            r.warnings.append(item)
        else:
            r.info.append('%s (report only): %s' % (item['id'], item['message']))
    r.state = 'kit_current'
    r.info.append('%d file(s) in %.2f s: %d falsy-default read(s), %d split receipt(s), %d level cap(s) (record: %s)'
                  % (found['files'], found['seconds'], len(found['falsy']), len(found['receipt']), len(found['caps']),
                     '%s = %s' % (found['level_where'], found['level_count']) if found['level_where'] else 'none'))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    return []
