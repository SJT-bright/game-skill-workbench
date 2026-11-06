"""Sync / source step (read only, about 1 s): frame-rate dependent moves and nodes made every frame (生成时预防 P18 第 3 点).

The census found moves by a fixed step per frame (割草: 60 Hz and 120 Hz phones differ by 50%) and nodes made in
update (猫咪毛球: a new Sprite every frame, the node count kept growing; 方块迷阵 86 effects left behind). Both are
written in seconds, so they are caught here, right where the code is generated, before any trial.

Scans assets/**/*.js|*.ts (not assets/tiktok-platform/, not files with kit bytes, not files over 300 KB / minified).
For each update / lateUpdate method (class method, `update: function (dt)`, `update(dt: number)`):
  K_frame_dt       a statement that moves x / y / position relative to itself (`+=`, `-=`, `++`, `x = x + ...`,
                   setPosition(... .x / .y ...) / position.add(...)) without the frame time: neither the dt parameter
                   nor a variable computed from it. `this.node.x += 5` -> reported; `this.node.x += 300 * dt` and
                   `var step = speed * dt; this.node.x += step` -> not reported. update() without a parameter -> every
                   such move is reported.
  K_frame_new_node `new cc.Node(`, `new Node(`, `instantiate(` or `addComponent(` inside update / lateUpdate.
A line (or the line just above it) carrying `// tiktok-kit:frame-ok <why>` is skipped (a one-time init behind a flag);
the better fix is FxPool.js / RunSession.move.
New games (board remake, policy new): blocks. English (localize): info only (the English pack does not change the
original gameplay). Legacy games: warnings.
Called by tiktok_finalize `sync` (SYNC_SOURCE_STEPS; the wiring line is in the I3 handoff, not in this file).
生成时预防 R4F3 (#43): also in SOURCE_STEPS, so a new game's block goes into the source record and the writers refuse
the package by K5 (before, a sync block never reached the record and the package went out).
"""
import re
import time

from . import Result, sha256

STEP = 'frame_scan'
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', '.tiktok-kit', '__macosx', 'profiles'}
KIT_DIR = 'assets/tiktok-platform/'
MAX_BYTES = 300 * 1024
EXEMPT = 'tiktok-kit:frame-ok'
HEAD = re.compile(r'(?<![\w$.])(?:update|lateUpdate)\s*(?::\s*function\s*)?\(\s*([A-Za-z_$][\w$]*)?\s*(?::\s*[\w$.]+\s*)?\)'
                  r'\s*(?::\s*[\w$.<>]+\s*)?\{')
MOVE_COMPOUND = re.compile(r'([\w$.\[\]\'"]+)\.(x|y)\s*(?:\+=|-=)|\.(?:x|y)\s*(?:\+\+|--)|(?:\+\+|--)\s*[\w$.]+\.(?:x|y)\b')
MOVE_SELF = re.compile(r'([\w$.]+)\.(x|y)\s*=(?!=)\s*(.+)')
MOVE_SETPOS = re.compile(r'([\w$.]+)\.setPosition\s*\((.*)\)|([\w$.]+)\.position\s*=(?!=)\s*(.+)')
WRAP = re.compile(r'\bif\s*\(.*[<>]')       # `if (road.y < -h) road.y += 3 * h`: a wrap-around jump, not a move
NEW_NODE = re.compile(r'new\s+(?:cc\s*\.\s*)?Node\s*\(|(?<![\w$])(?:cc\s*\.\s*)?instantiate\s*\(|\.addComponent\s*\(')
ASSIGN = re.compile(r'^\s*(?:var|let|const)?\s*([\w$.]+)\s*(?::\s*[\w$.<>]+\s*)?(?:[+\-*/]?=)(?!=)\s*(.+)$')


def strip_code(text):
    """Comments and string contents blanked (same length, newlines kept) so braces and names can be read safely.
    Exemption comments are kept as a marker on their line."""
    out, i, n = [], 0, len(text)
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
            while j < n and text[j] != c:
                j += 2 if text[j] == '\\' else 1
            j = min(j + 1, n)
            out.append(c + re.sub(r'[^\n]', ' ', text[i + 1:j - 1]) + (c if j - 1 > i else ''))
            i = j
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def bodies(code):
    """[(param or None, body text, line of the body start)] of every update / lateUpdate method in stripped code."""
    out = []
    for m in HEAD.finditer(code):
        depth, j = 1, m.end()
        while j < len(code) and depth:
            depth += {'{': 1, '}': -1}.get(code[j], 0)
            j += 1
        out.append((m.group(1), code[m.end():j - 1], code.count('\n', 0, m.end()) + 1))
    return out


def _uses(text, names):
    return any(re.search(r'(?<![\w$])%s(?![\w$])' % re.escape(nm), text) for nm in names)


def _statements(body, start_line):
    lines = body.split('\n')
    for k, line in enumerate(lines):
        if EXEMPT in line or (k and lines[k - 1].strip() == EXEMPT):
            continue
        for part in line.split(';'):
            if part.strip():
                yield start_line + k, part.strip()


def scan_text(text, rel='?'):
    code = strip_code(text)
    raw_lines = text.split('\n')
    moves, made = [], []
    for param, body, line0 in bodies(code):
        timed = {param} if param else set()
        stmts = list(_statements(body, line0))
        for _ in range(3):                              # taint: variables computed from dt (fixpoint, 3 rounds)
            for _, st in stmts:
                a = ASSIGN.match(st)
                if a and timed and _uses(a.group(2), timed):
                    timed.add(a.group(1))
        for ln, st in stmts:
            src = raw_lines[ln - 1].strip() if 0 < ln <= len(raw_lines) else st
            if NEW_NODE.search(st):
                made.append({'file': rel, 'line': ln, 'code': src[:120]})
            moving = bool(MOVE_COMPOUND.search(st))
            if not moving:
                s = MOVE_SELF.search(st)
                if s:       # `x = x + 4` / `x = 4 - x` (a clamp or a min/max of x is not a move)
                    me = r'%s\.%s(?![\w$])' % (re.escape(s.group(1)), s.group(2))
                    moving = bool(re.search(me + r'\s*[+\-](?![=+\-])', s.group(3)) or
                                  re.search(r'[+\-]\s*' + me, s.group(3)))
            if not moving:
                p = MOVE_SETPOS.search(st)
                recv = p and (p.group(1) or p.group(3))
                arg = p and (p.group(2) or p.group(4) or '')
                # relative to ITS OWN place: node.setPosition(node.x + 3, ..) / node.position = node.position.add(..)
                moving = bool(arg and re.search(r'%s\s*\.\s*(x|y|position|getPosition)\b' % re.escape(recv), arg)
                              and re.search(r'[+\-]|\.add\(', arg))
            if moving and WRAP.search(st):
                moving = False
            if moving and not (timed and _uses(st, timed)):
                moves.append({'file': rel, 'line': ln, 'code': src[:120], 'dt': param or None})
    return moves, made


def scan(root, kit_hashes=()):
    started = time.time()
    moves, made, files = [], [], 0
    base = root / 'assets'
    for p in sorted(base.rglob('*')) if base.is_dir() else []:
        rel = p.relative_to(root).as_posix()
        if p.suffix not in ('.js', '.ts') or not p.is_file() or rel.startswith(KIT_DIR) \
                or SKIP_DIRS & {x.lower() for x in rel.split('/')[:-1]} or p.stat().st_size > MAX_BYTES:
            continue
        data = p.read_bytes()
        if sha256(data) in kit_hashes:
            continue
        text = data.decode('utf-8', 'replace')
        if text.count('\n') < len(text) / 2000:          # minified library
            continue
        files += 1
        a, b = scan_text(text, rel)
        moves += a
        made += b
    return {'files': files, 'moves': moves, 'made': made, 'seconds': round(time.time() - started, 3)}


def findings(found, policy='new', board=None):
    """-> [(level, finding)] level block | warn | info."""
    level = 'info' if board == 'localize' else ('warn' if policy == 'legacy' else 'block')
    out = []
    if found['moves']:
        shown = '; '.join('%s:%d %s' % (m['file'], m['line'], m['code']) for m in found['moves'][:8])
        out.append((level, {'id': 'K_frame_dt' if level == 'block' else 'K_W_frame_dt', 'level': level,
                            'message': '%d move(s) in update() by a fixed step per frame, not by the frame time (60 Hz '
                                       'and 120 Hz phones run them at different speeds): %s. Multiply by dt (speed per '
                                       'second * dt) or use RunSession.move' % (len(found['moves']), shown),
                            'evidence': found['moves'][:30]}))
    if found['made']:
        shown = '; '.join('%s:%d %s' % (m['file'], m['line'], m['code']) for m in found['made'][:8])
        out.append((level, {'id': 'K_frame_new_node' if level == 'block' else 'K_W_frame_new_node', 'level': level,
                            'message': '%d node(s) / component(s) made inside update() (one per frame: the node count '
                                       'grows, the game stutters): %s. Make them once in onLoad, or take them from '
                                       'FxPool.js' % (len(found['made']), shown), 'evidence': found['made'][:30]}))
    return out


def detect(ctx):
    found = scan(ctx.root)
    return 'conflict' if found['moves'] or found['made'] else 'kit_current'


def apply(ctx):
    r = Result(STEP)
    hashes = ctx.manifest.kit_hashes() if ctx.manifest else set()
    found = scan(ctx.root, hashes)
    for level, item in findings(found, ctx.policy, getattr(ctx, 'board', None)):
        if level == 'block':
            r.blocks.append(item)
        elif level == 'warn':
            r.warnings.append(item)
        else:
            r.info.append('%s: %s' % (item['id'], item['message']))
    r.state = 'conflict' if r.blocks else 'kit_current'
    r.info.append('%d script(s) scanned in %.2f s; %d per-frame move(s) without dt, %d node(s) made in update'
                  % (found['files'], found['seconds'], len(found['moves']), len(found['made'])))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    return []
