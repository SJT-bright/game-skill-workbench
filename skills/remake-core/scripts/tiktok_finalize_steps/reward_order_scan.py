"""Source step (read only, well under 1 s): the game's own reward code that pays in the wrong order (生成时预防 Round 4
R4Q4, 问题普查补查3 第 4 组: 奔跑吧巨人, 合成进化恐龙, 10 条).

Census (10_补查3_20261105/occurrences.jsonl): 奔跑吧巨人 saved the chest x2 and the shop diamonds at the END of the
animation, so a closed page or a failed save after the button was already hidden lost the reward (T07
save_after_animation); upgrade, skin, shoe and chest-key rewards changed shared memory first and had no rollback when
the save failed (T07 ad_save_not_atomic / save_rollback_missing); the result x2 showed ceil(base*2) and paid
2*ceil(base), one coin apart (T13 reward_display_mismatch); 合成进化恐龙 had put the battle coins into the wallet during
the battle and the result Claim paid the same coins again (T13 duplicate_reward). The fixed order is: claim id ->
save and read back -> refresh the UI -> play the animation (SaveStore grant / ShopTx do the first two in one call).

Scans assets/**/*.ts|*.js (not assets/tiktok-platform/, not kit bytes, not files over 300 KB / minified / bundles):
  K_W_reward_in_anim_callback  a save / grant / addCoins-style call inside an animation-end callback
        (tween .call( , cc.callFunc( , scheduleOnce( , setCompleteListener( , .on('finished' | 'complete' ...),
        onComplete: ). Fix: grant first, play the animation only after ok; the callback only refreshes the UI.
  K_W_reward_no_rollback  a wallet / item field changed in memory (+= / -= / = x + n) and saved within 12 lines with
        no failure handling, or with a failure branch (catch / if (!ok) / fail:) that does not set the field back.
        Fix: store.grant({id, add: {...}}) (nothing is in memory until the save is ok), or keep `before` and restore it
        in the failure branch.
  K_W_x2_rounding_mismatch  the project rounds the doubled value in two orders: Math.ceil|floor|round(<base> * 2)
        somewhere and 2 * Math.ceil|floor|round(<base>) (or round(<base>) * 2) elsewhere. Fix: compute ONE base
        integer, show and pay 2 * it.
  K_W_reward_prepaid_twice  a run total that collects what the wallet already got (`wallet += x` and `runGain += x`
        within 3 lines) is added to the wallet again outside an ad / x2 branch. Fix: the result Claim only records
        the claim; the x2 adds one more share once (claim id run:<id>:x2).
A line (or the line just above it) carrying `// tiktok-kit:reward-ok <why>` is skipped.
Policy: English and new games: warning (the game's own code; it is a to-do, not a block). Legacy games: report only.
"""
import re
import time

from . import Result, sha256

STEP = 'reward_order_scan'
MAX_BYTES = 300 * 1024
LONG_LINE = 600
SKIP_PARTS = ('assets/tiktok-platform/', '/library/', '/temp/', '/build/', 'node_modules/')
EXEMPT = 'tiktok-kit:reward-ok'
VALUE = (r'(?:coins?|golds?|gems?|diamonds?|money|cash|keys?|energy|stamina|hearts?|lives|tickets?|items?|props?|'
         r'skins?|shoes?|fragments?|shards?|tokens?)')
VALUE_WORD = re.compile(r'(?i)' + VALUE + r'(?:_?(?:num|count|amount|total|value))?$')
FIELD = r'((?:this\s*\.\s*)?[\w$]+(?:\s*\.\s*[\w$]+|\s*\[[^\]\n]*\])*)'
MUTATE = re.compile(FIELD + r'\s*(?:\+=|-=|\+\+|--|=(?![=>])\s*([^;\n]+))')
SAVE = re.compile(r'(?i)(?<![\w$])(?:[\w$]+\s*\.\s*)*(?:save[\w$]*|writeSave|persist|setItem|setStorageSync|setStorage|'
                  r'setGlobalData|setConfigData[\w$]*)\s*\(')
PAY = re.compile(r'(?i)(?:\.\s*grant|\b(?:add|give|grant|gain|update)[\w$]*(?:Coins?|Golds?|Gems?|Diamonds?|Money|Keys?|'
                 r'Rewards?|PlayerInfo)|\b(?:save|saveData|saveGame|saveAll|writeSave|setItem|setStorageSync|'
                 r'setGlobalData|setConfigData))\s*\(')
ANIM_CALL = re.compile(r'\.\s*call\s*\(|\bcc\s*\.\s*callFunc\s*\(|\bcallFunc\s*\(|\bscheduleOnce\s*\(|'
                       r'\bsetCompleteListener\s*\(|\.\s*(?:on|once)\s*\(\s*[\'"](?:finished|complete|animationend|'
                       r'lastframe)[\'"]\s*,|'
                       r'\b(?:show|play|start|run)?[\w$]*(?:[Ff]ly|[Rr]aise|[Aa]nim|[Tt]ween|[Ee]ffect)[\w$]*\s*\((?=[^;]*?(?:=>|function\b))')
SCHEDULED = re.compile(r'\b(?:schedule|scheduleOnce)\s*\(\s*this\s*\.\s*([\w$]+)')
ANIM_PROP = re.compile(r'\bonComplete\s*:')
FAIL = re.compile(r'\bcatch\b|\bif\s*\(\s*!|===?\s*false|\.ok\b|\bfail\s*:|\berr(?:or)?\b')
ROUND = r'Math\s*\.\s*(ceil|floor|round)\s*\('
MULT = r'(?:2|(?:this\s*\.\s*)?[\w$]*(?i:mult|double)[\w$]*)'
ROUND_OF_X2 = re.compile(ROUND + r'([^;\n]*?)\*\s*' + MULT + r'\s*\)')
X2_OF_ROUND = re.compile(r'\b' + MULT + r'\s*\*\s*' + ROUND + r'|' + ROUND + r'[^()\n]*(?:\([^()\n]*\)[^()\n]*)*\)\s*\*\s*'
                         + MULT + r'\b')
AD_WORDS = re.compile(r'(?i)x2|double|multipl|\bmult\b|rewarded|watchad|showad|showvideo|adsuccess|onadcomplete|adreward')


PLUS_EQ = re.compile(FIELD + r'\s*\+=\s*([^;\n]+)')


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


def _exempt(raw, ln):
    return any(EXEMPT in raw[k] for k in (ln - 1, ln - 2) if 0 <= k < len(raw))


def _last(field):
    parts = [p for p in re.split(r'[.\[\]\s\'"]+', field) if p]
    return parts[-1] if parts else ''


def value_field(field):
    name = _last(field).lstrip('_$')
    if VALUE_WORD.match(name):
        return True
    return any(VALUE_WORD.match(name[m.end():]) for m in re.finditer(r'_(?=[A-Za-z])|(?<=[a-z0-9])(?=[A-Z])', name))


def wallet_field(field):
    """The wallet itself (GD.coin, data.gold, this.diamonds): the last name IS a value word, not runCoins / levelGold."""
    return VALUE_WORD.match(_last(field).lstrip('_$')) is not None


def _balanced(code, start):
    """Text from code[start] up to the ')' that closes the call whose '(' ends at code[start - 1]."""
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


def _line_of(starts, pos):
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


VALUE_ANY = re.compile(r'(?i)' + VALUE)


def _reward_body(body, p):
    """A plain storage write (setItem / save) counts only when the callback touches a wallet / item value."""
    if re.match(r'(?i)\.\s*grant|(?:add|give|grant|gain|update)', p.group(0).lstrip('. ')):
        return True
    return VALUE_ANY.search(body) is not None


def anim_payments(code, raw, rel):
    hits, starts = [], [0]
    for line in code.split('\n'):
        starts.append(starts[-1] + len(line) + 1)
    for m in list(ANIM_CALL.finditer(code)) + list(ANIM_PROP.finditer(code)):
        if m.re is ANIM_PROP:
            j = code.find('{', m.end())
            body = _balanced(code, j + 1) if 0 <= j < m.end() + 40 else ''
        else:
            body = _balanced(code, m.end())
        p = PAY.search(body)
        if not p or not _reward_body(body, p):
            continue
        pos = (code.find('{', m.end()) + 1 if m.re is ANIM_PROP else m.end()) + p.start()
        ln = _line_of(starts, pos)
        if _exempt(raw, ln) or _exempt(raw, _line_of(starts, m.start())):
            continue
        hits.append({'file': rel, 'line': ln, 'code': raw[ln - 1].strip()[:120],
                     'why': 'paid / saved inside the animation callback opened on line %d' % _line_of(starts, m.start())})
    for m in SCHEDULED.finditer(code):       # this.schedule(this._numRaise, dt): a count-up that pays when it ends
        d = re.search(r'(?<![\w$.])' + re.escape(m.group(1)) + r'\s*(?:=\s*(?:function\s*)?)?\([^()]*\)\s*(?::\s*[\w$<>]+\s*)?(?:=>\s*)?\{',
                      code)
        if not d:
            continue
        body = _balanced(code, d.end())
        p = PAY.search(body)
        if not p or not _reward_body(body, p):
            continue
        ln = _line_of(starts, d.end() + p.start())
        if not _exempt(raw, ln):
            hits.append({'file': rel, 'line': ln, 'code': raw[ln - 1].strip()[:120],
                         'why': 'paid at the end of %s, scheduled on line %d (a count-up animation)'
                                % (m.group(1), _line_of(starts, m.start()))})
    seen, out = set(), []
    for h in hits:
        if h['line'] not in seen:
            seen.add(h['line'])
            out.append(h)
    return out


def _mutations(line):
    out = []
    if not VALUE_ANY.search(line):
        return out
    for m in MUTATE.finditer(line):
        field = m.group(1).replace(' ', '')
        if not value_field(field):
            continue
        rhs = (m.group(2) or '').replace(' ', '')
        if m.group(2) is None or (rhs.startswith(field) and rhs[len(field):len(field) + 1] in '+-'):
            out.append(field)
    return out


def no_rollback(code, raw, rel):
    hits = []
    lines = code.split('\n')
    for ln, line in enumerate(lines, 1):
        if not VALUE_ANY.search(line) or _exempt(raw, ln) or re.search(r'\.\s*grant\s*\(', line):
            continue
        for field in _mutations(line):
            if re.match(r'(?:draft|d|next|copy|tmp)\b', field) or \
                    re.search(r'\.\s*(?:grant|update|commit)\s*\(|\bapply\s*[:(]', '\n'.join(lines[max(0, ln - 4):ln])):
                continue           # a draft inside grant / update / ShopTx apply: SaveStore saves it or drops it whole
            k_save = next((k for k in range(ln, min(len(lines), ln + 12)) if SAVE.search(lines[k])), None)
            if k_save is None or _exempt(raw, k_save + 1):
                continue
            after = '\n'.join(lines[k_save:k_save + 8])
            fail = FAIL.search(after)
            name = re.escape(field)
            restored = re.search(r'(?<![\w$.])' + name + r'\s*(?:=(?!=)|\+=|-=)', after)
            if fail and restored:
                continue
            hits.append({'file': rel, 'line': ln, 'field': field, 'code': raw[ln - 1].strip()[:120],
                         'save_line': k_save + 1,
                         'why': ('failure branch does not set %s back' % field) if fail else
                                ('save result on line %d not checked, %s already changed' % (k_save + 1, field))})
            break
    return hits


def rounding(code, raw, rel):
    out = {'round_of_x2': [], 'x2_of_round': []}
    for ln, line in enumerate(code.split('\n'), 1):
        if _exempt(raw, ln):
            continue
        if 'random' in line.lower():
            continue
        if ROUND_OF_X2.search(line):
            out['round_of_x2'].append({'file': rel, 'line': ln, 'code': raw[ln - 1].strip()[:120]})
        if X2_OF_ROUND.search(line):
            out['x2_of_round'].append({'file': rel, 'line': ln, 'code': raw[ln - 1].strip()[:120]})
    return out


def prepaid(code, raw, rel):
    """(collectors, payouts): run totals that collect what the wallet already got; wallet += <total> lines."""
    lines = code.split('\n')
    adds = []           # (line, field, rhs)
    for ln, line in enumerate(lines, 1):
        if '+=' not in line:
            continue
        for m in PLUS_EQ.finditer(line):
            adds.append((ln, m.group(1).replace(' ', ''), m.group(2).strip().rstrip(')').replace(' ', '')))
    collectors = set()
    for ln, f, rhs in adds:
        if not wallet_field(f):
            continue
        for ln2, f2, rhs2 in adds:
            if f2 != f and abs(ln2 - ln) <= 3 and rhs2 == rhs and not wallet_field(f2):
                collectors.add(_last(f2))
    payouts = []
    for ln, f, rhs in adds:
        if wallet_field(f) and _exempt(raw, ln) is False:
            payouts.append({'file': rel, 'line': ln, 'field': f, 'rhs': rhs, 'code': raw[ln - 1].strip()[:120],
                            'ad': bool(AD_WORDS.search('\n'.join(lines[max(0, ln - 9):ln])))})
    return collectors, payouts


def scan_text(text, rel='?'):
    empty = {'anim': [], 'rollback': [], 'round_of_x2': [], 'x2_of_round': [], 'collectors': set(), 'payouts': []}
    if 'cc._RF.push(' in text or not (VALUE_ANY.search(text) or 'Math.' in text):
        return empty                      # a bundle, or nothing about coins / items / rounding: skip the slow parse
    code = '\n'.join('' if len(l) > LONG_LINE else l for l in strip_comments(text).split('\n'))
    raw = text.split('\n')
    rnd = rounding(code, raw, rel)
    collectors, payouts = prepaid(code, raw, rel)
    return {'anim': anim_payments(code, raw, rel), 'rollback': no_rollback(code, raw, rel),
            'round_of_x2': rnd['round_of_x2'], 'x2_of_round': rnd['x2_of_round'],
            'collectors': collectors, 'payouts': payouts}


def _skip(rel):
    low = '/' + rel.lower()
    return any(p in low for p in SKIP_PARTS) or rel.endswith('.d.ts') or rel.endswith('.min.js')


def combine(per_file):
    """Project-wide result from scan_text() outputs (x2 rounding and prepaid totals look across files)."""
    found = {'anim': [], 'rollback': [], 'round_of_x2': [], 'x2_of_round': [], 'twice': []}
    collectors, payouts = set(), []
    for r in per_file:
        for k in ('anim', 'rollback', 'round_of_x2', 'x2_of_round'):
            found[k] += r[k]
        collectors |= r['collectors']
        payouts += r['payouts']
    for p in payouts:
        if not p['ad'] and _last(p['rhs']) in collectors and re.fullmatch(r'(?:this\.)?[\w$.]+', p['rhs']):
            found['twice'].append(p)
    return found


def scan(root, kit_hashes=()):
    started = time.time()
    per_file, files = [], 0
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
        files += 1
        per_file.append(scan_text(text, rel))
    found = combine(per_file)
    found['files'] = files
    found['seconds'] = round(time.time() - started, 3)
    return found


def _shown(items):
    return '; '.join('%s:%d %s' % (x['file'], x['line'], x['code']) for x in items[:6])


def findings(found, policy='new'):
    level = 'info' if policy == 'legacy' else 'warn'
    out = []
    if found['anim']:
        out.append((level, {'id': 'K_W_reward_in_anim_callback', 'level': level,
                            'message': '%d reward(s) paid or saved inside an animation-end callback: %s. Pay first '
                                       '(grant / ShopTx: claim id -> save and read back), refresh the UI, then play the '
                                       'animation; the callback only shows' % (len(found['anim']), _shown(found['anim'])),
                            'evidence': found['anim'][:30]}))
    if found['rollback']:
        out.append((level, {'id': 'K_W_reward_no_rollback', 'level': level,
                            'message': '%d wallet / item change(s) made in memory before the save, with no rollback on '
                                       'a failed save: %s. Use store.grant({id, add: {...}}) (nothing changes until the '
                                       'save is ok) or keep the old value and restore it in the failure branch'
                                       % (len(found['rollback']), _shown(found['rollback'])),
                            'evidence': found['rollback'][:30]}))
    if found['round_of_x2'] and found['x2_of_round']:
        both = found['round_of_x2'][:3] + found['x2_of_round'][:3]
        out.append((level, {'id': 'K_W_x2_rounding_mismatch', 'level': level,
                            'message': 'the doubled reward is rounded in two orders (round(base*2) and 2*round(base)): '
                                       '%s. The label and the grant can differ by 1; compute one base integer and use '
                                       '2 * it for both' % _shown(both),
                            'evidence': both}))
    if found['twice']:
        out.append((level, {'id': 'K_W_reward_prepaid_twice', 'level': level,
                            'message': '%d payout(s) add a run total whose parts the wallet already got: %s. The result '
                                       'Claim only records the claim; an x2 adds one more share once (claim id '
                                       'run:<id>:x2)' % (len(found['twice']), _shown(found['twice'])),
                            'evidence': found['twice'][:30]}))
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
    r.info.append('%d file(s) in %.2f s: %d animation-callback payment(s), %d no-rollback change(s), x2 rounding %d/%d, '
                  '%d prepaid-twice payout(s)' % (found['files'], found['seconds'], len(found['anim']),
                                                   len(found['rollback']), len(found['round_of_x2']),
                                                   len(found['x2_of_round']), len(found['twice'])))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    return []
