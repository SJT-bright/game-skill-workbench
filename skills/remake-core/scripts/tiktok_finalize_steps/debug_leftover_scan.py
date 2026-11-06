"""Source step (read only, well under 1 s): debug and other-studio leftovers (生成时预防 Round 4 R4Q5, 补查3 第 5 组).

What the census found (2 games, 5 times): 奔跑吧巨人 (GiantRush) turned the Profiler on from an old save with
debug=true, its FPS stats covered the bottom buttons, and the home page kept a tappable `level/btnDebug`;
方块收割者 (CubeHarvest) kept the original studio's "Galaxy Games" splash, which covered the home for 4 s at every
start. The kit startup parts now turn the stats off unconditionally (2.4 main.js v1.8, 3.x boot-guard-3x); this step
reports what the game's own files still carry, before every build:

  1. stats   game code that can turn the stats on: profiler.showStats(...), setDisplayStats(<anything but false>),
             showFPS / showStats set to true (scripts under assets/, kit folder tiktok-platform skipped).
  2. debug   an ACTIVE node (it and every parent active) in a scene or prefab whose name has the word debug / cheat /
             test / dbg (btnDebug, DebugPanel, cheat_add_gold, TestButton; "contest" or "latest" do not count).
  3. splash  in a scene: a node named splash / studio / company / publisher / 开屏 / 闪屏, a Label / RichText that
             names a studio ("Galaxy Games", "XX Studio", "presents", "powered by"), or a component script on a scene
             node of the LAUNCH scene (settings builder startScene) that hides its own node after a timer at start
             (setTimeout / scheduleOnce + fadeOut / opacity / active = false; 方块收割者 begin/bg.js).

Levels: new remake game begun by `init` at / after SINCE -> block (K_debug_leftover); other new remake games (in
progress, begun earlier or taken over) and English games -> warning (K_W_debug_leftover); legacy -> not checked.
A name or text that is meant to stay goes into docs/copy/glossary.json "debug_leftover_ok" (exact node name, text or
script file name). Called by tiktok_finalize `source` (SOURCE_STEPS) and `sync` (SYNC_SOURCE_STEPS).
"""
import datetime
import json
import re
import time

from . import Result

STEP = 'debug_leftover_scan'
GATE = 'K_debug_leftover'
SINCE = '2026-11-05T00:00:00-0800'
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', '.tiktok-kit', '__macosx', 'profiles',
             'tiktok-platform', 'build-templates', 'packages', 'extensions', 'settings', 'docs', 'tests', 'test'}
SCENES = ('.fire', '.scene')
PREFABS = ('.prefab',)
CODE = ('.js', '.ts')
MAX_BYTES = 8 * 1024 * 1024
STATS = [
    (re.compile(r'\bshowStats\s*\('), 'profiler.showStats()'),
    (re.compile(r'\bsetDisplayStats\s*\(\s*(?!false\s*\))[^)\s]'), 'setDisplayStats(not false)'),
    (re.compile(r'\b(?:showFPS|showStats|displayStats)\s*[:=]\s*true\b'), 'showFPS / showStats = true'),
]
DEBUG_WORDS = {'debug', 'cheat', 'cheats', 'test', 'tests', 'dbg'}
SPLASH_NAME_WORDS = {'splash', 'studio', 'studios', 'company', 'publisher', 'brand', 'presents'}
SPLASH_NAME_CJK = ('开屏', '闪屏', '启动页', '公司', '工作室')
SPLASH_TEXT = re.compile(r"\b[A-Z][\w'&]*\s+(?:Games|GAMES|Studios?|STUDIOS?|Interactive|Entertainment)\b|"
                         r"\b[Pp]resents\b|\b[Pp]owered\s+by\b|工作室|出品")   # a brand: capitalised name + Games / Studio
CREATOR_DEFAULT_NAMES = {'New Sprite(Splash)'}   # Creator's own white rectangle (internal sprite_splash), not a splash
SELF_HIDE = re.compile(r'(?:setTimeout|scheduleOnce|delayTime)')
HIDE_ACT = re.compile(r'(?:fadeOut|FadeOut|\.opacity\s*=|this\.node\.active\s*=\s*false|node\.destroy\(\))')
B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'


def words(name):
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', str(name))
    return {w.lower() for w in re.split(r'[^0-9A-Za-z]+', s) if w}


def compress_uuid(uuid):
    """Cocos scene files name a script component by its compressed uuid (5 hex + 18 base64 characters)."""
    h = uuid.replace('-', '')
    if len(h) != 32:
        return ''
    out = h[:5]
    for i in range(5, 32, 3):
        v = int(h[i:i + 3], 16)
        out += B64[v >> 6] + B64[v & 63]
    return out


def _skip(root, p):
    return any(part.lower() in SKIP_DIRS for part in p.relative_to(root).parts[:-1])


def _ok(root):
    try:
        g = json.loads((root / 'docs' / 'copy' / 'glossary.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return set()
    v = g.get('debug_leftover_ok') if isinstance(g, dict) else None
    return {str(x) for x in v} if isinstance(v, list) else set()


def _files(root, suffixes):
    base = root / 'assets'
    if not base.is_dir():
        return []
    return [p for p in sorted(base.rglob('*')) if p.suffix.lower() in suffixes and p.is_file()
            and not _skip(root, p) and p.stat().st_size <= MAX_BYTES]


def _load(p):
    try:
        d = json.loads(p.read_text(encoding='utf-8', errors='replace'))
    except (OSError, ValueError):
        return None
    return d if isinstance(d, list) else None


def _active(objs, i, seen=None):
    seen = seen or set()
    while isinstance(i, int) and 0 <= i < len(objs) and i not in seen:
        seen.add(i)
        o = objs[i]
        if not isinstance(o, dict) or o.get('_active') is False:
            return False
        par = o.get('_parent')
        i = par.get('__id__') if isinstance(par, dict) else None
    return True


def _path(objs, i):
    names, seen = [], set()
    while isinstance(i, int) and 0 <= i < len(objs) and i not in seen:
        seen.add(i)
        o = objs[i]
        if o.get('__type__') in ('cc.Scene', 'cc.Prefab'):
            break
        names.append(str(o.get('_name', '?')))
        par = o.get('_parent')
        i = par.get('__id__') if isinstance(par, dict) else None
    return '/'.join(reversed(names))


def _scripts(root):
    """-> {compressed uuid: (rel, source)} for the game's own component scripts."""
    out = {}
    for p in _files(root, CODE):
        meta = p.with_name(p.name + '.meta')
        try:
            uuid = json.loads(meta.read_text(encoding='utf-8')).get('uuid', '')
            src = p.read_text(encoding='utf-8', errors='replace')
        except (OSError, ValueError):
            continue
        c = compress_uuid(uuid)
        if c:
            out[c] = (p.relative_to(root).as_posix(), src)
    return out


def launch_scene(root):
    """-> project-relative path of the launch scene (2.4 settings/builder.json startScene; 3.x builder startScene /
    launchScene when present), or '' when the project does not say."""
    uuid = ''
    for cfg in ('settings/builder.json', 'settings/v2/packages/builder.json', 'settings/v2/packages/project.json'):
        try:
            d = json.loads((root / cfg).read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        m = re.search(r'"(?:startScene|launchScene)"\s*:\s*"([0-9a-f-]{36})"', json.dumps(d))
        if m:
            uuid = m.group(1)
            break
    if not uuid:
        return ''
    for p in _files(root, SCENES):
        try:
            if json.loads(p.with_name(p.name + '.meta').read_text(encoding='utf-8')).get('uuid') == uuid:
                return p.relative_to(root).as_posix()
        except (OSError, ValueError):
            continue
    return ''


def scan(root):
    t0 = time.time()
    ok = _ok(root)
    launch = launch_scene(root)
    hits = []
    for p in _files(root, CODE):
        rel = p.relative_to(root).as_posix()
        if p.name in ok:
            continue
        try:
            src = p.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for rx, what in STATS:
            for m in rx.finditer(src):
                line = src.count('\n', 0, m.start()) + 1
                text = src.splitlines()[line - 1].strip()[:100] if src.splitlines() else ''
                if text.startswith('//'):
                    continue
                hits.append({'kind': 'stats', 'file': rel, 'where': 'line %d' % line, 'text': text, 'what': what})
    scripts = None
    for p in _files(root, SCENES + PREFABS):
        objs = _load(p)
        if objs is None:
            continue
        rel = p.relative_to(root).as_posix()
        scene = p.suffix.lower() in SCENES
        for i, o in enumerate(objs):
            if not isinstance(o, dict):
                continue
            t = o.get('__type__')
            if t == 'cc.Node' and '_name' in o:
                name = str(o.get('_name'))
                if name in ok or not _active(objs, i):
                    continue
                w = words(name)
                if w & DEBUG_WORDS:
                    hits.append({'kind': 'debug', 'file': rel, 'where': _path(objs, i), 'text': name,
                                 'what': 'active debug / cheat / test node'})
                elif scene and name not in CREATOR_DEFAULT_NAMES and (w & SPLASH_NAME_WORDS or any(c in name for c in SPLASH_NAME_CJK)):
                    hits.append({'kind': 'splash', 'file': rel, 'where': _path(objs, i), 'text': name,
                                 'what': 'splash / studio node in a scene'})
            elif scene and t in ('cc.Label', 'cc.RichText'):
                s = str(o.get('_string') or o.get('_N$string') or '')
                node = o.get('node')
                ni = node.get('__id__') if isinstance(node, dict) else None
                if s and s not in ok and SPLASH_TEXT.search(s) and _active(objs, ni):
                    hits.append({'kind': 'splash', 'file': rel, 'where': _path(objs, ni), 'text': s[:80],
                                 'what': 'studio / publisher text in a scene'})
            elif scene and rel == launch and isinstance(t, str) and len(t) == 23 and not t.startswith('cc.'):
                if scripts is None:
                    scripts = _scripts(root)
                hit = scripts.get(t)
                node = o.get('node')
                ni = node.get('__id__') if isinstance(node, dict) else None
                if not hit or hit[0].rsplit('/', 1)[-1] in ok or not _active(objs, ni):
                    continue
                body = re.search(r'\b(?:start|onLoad)\s*(?::\s*function)?\s*\([^)]*\)\s*\{(.{0,1500})', hit[1], re.S)
                if body and SELF_HIDE.search(body.group(1)) and HIDE_ACT.search(body.group(1)):
                    hits.append({'kind': 'splash', 'file': rel, 'where': _path(objs, ni), 'text': hit[0],
                                 'what': 'scene node hides itself after a timer at start (startup splash)'})
    return {'hits': hits, 'launch_scene': launch, 'seconds': round(time.time() - t0, 3)}


def started_after_rule(root):
    from .policy import read_marker
    mark = read_marker(root) or {}
    if mark.get('by') != 'init':
        return False, 'not begun by init (marker by %s)' % (mark.get('by') or 'none')
    try:
        created = datetime.datetime.strptime(str(mark.get('created')), '%Y-%m-%dT%H:%M:%S%z')
        since = datetime.datetime.strptime(SINCE, '%Y-%m-%dT%H:%M:%S%z')
    except ValueError:
        return False, 'start time not readable'
    if created >= since:
        return True, 'begun %s, after R4Q5 (2026-11-05)' % mark.get('created')
    return False, 'begun %s, before R4Q5 (in progress: warning)' % mark.get('created')


def level_of(policy='new', board=None, after_rule=False):
    if policy == 'legacy':
        return 'skip'
    if board == 'localize' or not after_rule:
        return 'warn'
    return 'block'


def message(hits):
    shown = '; '.join('%s %s %s "%s"' % (h['kind'], h['file'], h['where'], h['text']) for h in hits[:8])
    return ('%d debug / other-studio leftover(s): %s. A TikTok game shows no FPS stats, no debug / cheat / test button '
            'and no other studio\'s splash: delete the node or set it inactive, remove the code that turns the stats on '
            '(the kit startup turns them off anyway), drop the splash so the home comes up at once. One that must stay '
            'goes into docs/copy/glossary.json "debug_leftover_ok"' % (len(hits), shown))


def detect(ctx):
    if ctx.policy == 'legacy':
        return 'kit_current'
    return 'conflict' if scan(ctx.root)['hits'] else 'kit_current'


def apply(ctx):
    r = Result(STEP)
    if ctx.policy == 'legacy':
        r.state = 'kit_current'
        r.info.append('legacy game: debug leftovers not checked')
        return r.as_dict()
    found = scan(ctx.root)
    after, why = started_after_rule(ctx.root)
    level = level_of(ctx.policy, getattr(ctx, 'board', None), after)
    if found['hits']:
        if level == 'block':
            r.block(GATE, message(found['hits']), found['hits'][:30])
        else:
            r.warn(GATE.replace('K_', 'K_W_', 1), message(found['hits']), found['hits'][:30])
    r.state = 'conflict' if r.blocks else 'kit_current'
    r.info.append('%d leftover(s) in %.2f s; level %s: %s' % (len(found['hits']), found['seconds'], level, why))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    return []
