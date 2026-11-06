"""Source step (read only): the root background of the home, play and result pages is laid with ScreenFit.cover
(生成时预防 P07 第 3 点).

Backgrounds sized to the design (720 x 1280) leave bars on long or wide phones, and a Canvas with both fits squashes
the picture: the census counts screen_fit_wrong 28 times (another 33 squashed pictures, partly whole-screen). The kit
part parts/ScreenFit.js (K2 批, platform kit) lays a background over the real visible area keeping its ratio:
ScreenFit.cover(cc, bgNode, {watch: true}). This step checks every page has it.

Pages: every scene (.fire / .scene) and every prefab whose file name says home / main / menu / start / lobby / game /
play / battle / result / over / settle / win / lose / fail (not level / item prefabs). Root background of a page: a node at most two
levels under the Canvas (prefab: the root or its children) with a cc.Sprite covering 90% of the design width and
height (a popup panel is smaller); the ones named bg / background / 背景,
or (when none is named so) the first of them; full-screen
overlays named mask / fade / shade / dim / black / curtain / transition / splash are not backgrounds. It counts as laid with
cover when
  - a component on that node, or a component in the same file with a property pointing at the node (or at a component
    on it), runs a script that calls ScreenFit.cover( ; or
  - some project script calls ScreenFit.cover( and names the node in a string ('bg', 'Canvas/bg').
Findings: K_bg_cover (block) for new games (board remake, policy new); K_W_bg_cover (warning) for English (localize)
and legacy games. While the kit has no parts/ScreenFit.js (KIT_MANIFEST files) the finding is always the warning: a
part that does not exist yet cannot be required.
Called by tiktok_finalize `source` (SOURCE_STEPS; the wiring line is in the I3 handoff, not in this file).

简化.11.14 R4A (生成时预防 P07 第 2 点, 热气球 flash_frame): the loading page and the home must not show two different
game pictures. A loading page (scene / prefab whose file name says loading / boot / launch / splash / preload) whose
root background is a PROJECT picture (its sprite frame uuid is in a .meta under assets/; engine and official
built-in frames are not) different from the home's root background picture (home / main / menu / start / lobby
page) shows one picture and then the home swaps it, and re-lays it at another size: 热气球 v1 showed the loading
page's old picture, then a stretched portrait one, then shrank it to 750 wide. Finding K_bg_loading_swap (block for
new remake games, warning for English and legacy games, same rule as K_bg_cover). The loading page itself must
still be laid with ScreenFit.cover like every page. The kit main.js has no loading picture of its own (the TikTok
loading toast over an empty canvas), so this is checked in the project where the pictures are chosen.
"""
import json
import re

from . import Result
from .art_static import SCENE_SUFFIXES, Scene, _num, _skip, design_resolution, exemptions, project_files, split_exempt

STEP = 'bg_cover'
PAGE = re.compile(r'home|main|menu|start|lobby|game|play|battle|result|over|settle|win|lose|fail', re.I)
BG_NAME = re.compile(r'(^|[^a-z])(bg|background|back_?ground)([^a-z]|$)|背景', re.I)
COVER = re.compile(r'ScreenFit\s*\.\s*cover\s*\(')
OVERLAY = re.compile(r'mask|fade|shade|dim|black|curtain|transition|splash', re.I)   # full-screen overlays, not backgrounds
FULL = 0.9
SCREENFIT_KEY = 'parts/ScreenFit.js'
BASE64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'


def compress_uuid(uuid):
    """Cocos 2.4 / 3.x compressed script id (23 chars) used as a component __type__."""
    h = uuid.replace('-', '').lower()
    if len(h) != 32 or not re.fullmatch(r'[0-9a-f]{32}', h):
        return None
    out = h[:5]
    for i in range(5, 32, 3):
        v = int(h[i:i + 3], 16)
        out += BASE64[v >> 6] + BASE64[v & 63]
    return out


def _size(scene, node):
    s = node.get('_contentSize')
    if not isinstance(s, dict):
        for c in scene.comps(node):
            if c.get('__type__') == 'cc.UITransform':
                s = c.get('_contentSize')
    s = s if isinstance(s, dict) else {}
    sc = node.get('_scale') or node.get('_lscale') or {}
    k = (_num(sc.get('x'), 1.0), _num(sc.get('y'), 1.0)) if isinstance(sc, dict) else (1.0, 1.0)
    trs = node.get('_trs')
    if isinstance(trs, dict) and isinstance(trs.get('array'), list) and len(trs['array']) >= 9:
        k = (_num(trs['array'][7], 1.0), _num(trs['array'][8], 1.0))
    return abs(_num(s.get('width')) * k[0]), abs(_num(s.get('height')) * k[1])


def _kids(scene, node):
    return [c for c in (scene.obj(r) for r in node.get('_children') or []) if c and c.get('__type__') == 'cc.Node']


LOADING = re.compile(r'loading|boot|launch|splash|preload', re.I)   # R4A: loading page file names
HOME = re.compile(r'home|main|menu|start|lobby', re.I)
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:@[0-9a-z]+)?', re.I)


def _is_page(rel):
    name = rel.split('/')[-1]
    return rel.endswith(('.fire', '.scene')) or (rel.endswith('.prefab') and (PAGE.search(name) or LOADING.search(name)))


def page_kind(rel):
    """'loading' | 'home' | None from the file name (loading wins: 'MainLoading.fire' is a loading page)."""
    stem = rel.split('/')[-1].rsplit('.', 1)[0]
    if LOADING.search(stem):
        return 'loading'
    return 'home' if HOME.search(stem) else None


def picture(scene, node):
    """The sprite frame uuid a background node shows, or None."""
    sprite = scene.comp(node, 'cc.Sprite')
    frame = (sprite or {}).get('_spriteFrame')
    uid = frame.get('__uuid__') if isinstance(frame, dict) else None
    return uid if isinstance(uid, str) and uid else None


def project_uuids(files):
    """Every uuid written in a .meta under assets/ (textures and their sprite frames): the project's own pictures."""
    out = set()
    for rel, data in files.items():
        if rel.startswith('assets/') and rel.endswith('.meta'):
            out |= {u.lower() for u in UUID.findall(data.decode('utf-8', 'replace'))}
    return out


def backgrounds(scene, design):
    """Root background nodes of one page file -> [node dict]."""
    W, H = design
    roots = [scene.obj(c.get('node')) for c in scene.objs if isinstance(c, dict) and c.get('__type__') == 'cc.Canvas']
    roots = [n for n in roots if n]
    levels = []
    if roots:
        for r in roots:
            levels += _kids(scene, r)
            for k in _kids(scene, r):
                levels += _kids(scene, k)
    elif scene.rel.endswith('.prefab'):
        top = next((o for o in scene.objs if isinstance(o, dict) and o.get('__type__') == 'cc.Node'
                    and not scene.obj(o.get('_parent'))), None)
        if top:
            levels = [top] + _kids(scene, top)
    named, big = [], []
    for n in levels:
        name = str(n.get('_name') or '')
        if not scene.comp(n, 'cc.Sprite') or OVERLAY.search(name):
            continue
        w, h = _size(scene, n)
        if w < W * FULL or h < H * FULL:           # a popup panel's bg is smaller than the screen: not a page background
            continue
        (named if BG_NAME.search(name) else big).append(n)
    # named backgrounds when the page has them; else only the first full-screen sprite (drawn first = the back one)
    return named or big[:1]


def script_index(root):
    """{compressed uuid: script text} and [script text] of the project's .js / .ts files."""
    by_type, texts = {}, []
    base = root / 'assets'
    if not base.is_dir():
        return by_type, texts
    for p in base.rglob('*'):
        rel = p.relative_to(root).as_posix()
        if p.suffix not in ('.js', '.ts') or not p.is_file() or _skip(rel):
            continue
        text = p.read_text(encoding='utf-8', errors='replace')
        texts.append(text)
        meta = p.with_name(p.name + '.meta')
        try:
            uid = json.loads(meta.read_text(encoding='utf-8')).get('uuid') if meta.is_file() else None
        except ValueError:
            uid = None
        key = compress_uuid(uid) if isinstance(uid, str) else None
        if key:
            by_type[key] = text
            by_type[uid] = text
    return by_type, texts


def _refs(value, ids):
    if isinstance(value, dict):
        if value.get('__id__') in ids:
            return True
        return any(_refs(v, ids) for v in value.values())
    if isinstance(value, list):
        return any(_refs(v, ids) for v in value)
    return False


def covered(scene, node, by_type, texts):
    name = str(node.get('_name') or '')
    idx = next(i for i, o in enumerate(scene.objs) if o is node)
    ids = {idx} | {r.get('__id__') for r in node.get('_components') or [] if isinstance(r, dict)}
    own = {id(c) for c in scene.comps(node)}
    for c in scene.objs:
        if not isinstance(c, dict) or not COVER.search(by_type.get(str(c.get('__type__')), '')):
            continue
        if id(c) in own or _refs({k: v for k, v in c.items() if k != 'node'}, ids):
            return True
    lit = re.compile(r'[\'"`](?:[^\'"`]*/)?%s[\'"`]' % re.escape(name)) if name else None
    return bool(lit) and any(COVER.search(t) and lit.search(t) for t in texts)


def scan(root, files=None):
    files = files if files is not None else project_files(root)
    scenes, unreadable = [], []
    for rel in sorted(files):
        if rel.startswith('assets/') and rel.endswith(SCENE_SUFFIXES) and not _skip(rel):
            try:
                scenes.append(Scene(rel, json.loads(files[rel].decode('utf-8-sig'))))
            except (ValueError, UnicodeDecodeError):
                unreadable.append(rel)
    design = design_resolution(scenes)
    by_type, texts = script_index(root)
    own = project_uuids(files)
    missing, ok, pages = [], [], 0
    shown = {'loading': [], 'home': []}            # R4A: [(file, node path, picture uuid)] of project pictures
    for s in scenes:
        if not _is_page(s.rel):
            continue
        pages += 1
        kind = page_kind(s.rel)
        for n in backgrounds(s, design):
            item = {'file': s.rel, 'node': s.path(n)}
            (ok if covered(s, n, by_type, texts) else missing).append(item)
            pic = picture(s, n)
            if kind and pic and pic.lower() in own:
                shown[kind].append((s.rel, s.path(n), pic))
    missing, exempt = split_exempt(missing, exemptions(root))   # docs/art/static-exempt.json (same file as art_static)
    home_pics = {p.lower() for _, _, p in shown['home']}
    swaps = [{'file': f, 'node': n, 'picture': p, 'home': sorted({h[0] for h in shown['home']})}
             for f, n, p in shown['loading'] if home_pics and p.lower() not in home_pics]
    swaps, swap_exempt = split_exempt(swaps, exemptions(root))
    return {'design': list(design), 'pages': pages, 'missing': missing, 'covered': ok, 'exempt': exempt + swap_exempt,
            'unreadable': unreadable, 'loading_swap': swaps}


def loading_findings(found, policy='new', board=None):
    """R4A: K_bg_loading_swap - the loading page shows another project picture than the home."""
    swaps = found.get('loading_swap') or []
    if not swaps:
        return []
    hard = policy != 'legacy' and board != 'localize'
    shown = '; '.join('%s %s (%s)' % (s['file'], s['node'], s['picture']) for s in swaps[:6])
    return [{'id': 'K_bg_loading_swap' if hard else 'K_W_bg_loading_swap', 'level': 'block' if hard else 'warn',
             'message': 'the loading page background is a different game picture from the home background (%s; home: '
                        '%s): the player sees one picture, then the home swaps it and lays it again at another size '
                        '(热气球 flash). Give the loading page no game picture: use the official Cocos default loading '
                        '(cocos-game-check/startup/references/cocos-loading-screen.md, Saul 10-26), then run source '
                        'again'
                        % (shown, ', '.join(swaps[0]['home'])),
             'evidence': swaps[:30]}]


def findings(found, policy='new', board=None, kit_has_part=True):
    return cover_findings(found, policy, board, kit_has_part) + loading_findings(found, policy, board)


def cover_findings(found, policy='new', board=None, kit_has_part=True):
    if not found['missing']:
        return []
    hard = policy != 'legacy' and board != 'localize' and kit_has_part
    shown = '; '.join('%s %s' % (m['file'], m['node']) for m in found['missing'][:8])
    return [{'id': 'K_bg_cover' if hard else 'K_W_bg_cover', 'level': 'block' if hard else 'warn',
             'message': '%d page background(s) not laid with ScreenFit.cover (sized to the design they leave bars or '
                        'get squashed on long / wide phones): %s. Copy parts/ScreenFit.js to assets/tiktok-platform/ and '
                        'call ScreenFit.cover(cc, <bg node>, {watch: true}) in the page script (the loading page uses '
                        'the same picture and the same call), then run source again%s'
                        % (len(found['missing']), shown, '' if kit_has_part else
                           ' (this kit has no parts/ScreenFit.js yet: warning only)'),
             'evidence': found['missing'][:30]}]


def detect(ctx):
    found = scan(ctx.root)
    bad = found['missing'] or found.get('loading_swap')
    return 'conflict' if bad else ('kit_current' if found['pages'] else 'n/a')


def apply(ctx):
    r = Result(STEP)
    found = scan(ctx.root)
    kit_has = bool(ctx.manifest and isinstance((ctx.manifest.files or {}).get(SCREENFIT_KEY), dict))
    for item in findings(found, ctx.policy, getattr(ctx, 'board', None), kit_has):
        (r.blocks if item['level'] == 'block' else r.warnings).append(item)
    r.state = 'conflict' if r.blocks else ('kit_current' if found['pages'] else 'n/a')
    r.info.append('%d page file(s); %d background(s) with ScreenFit.cover, %d without%s; %d loading page picture(s) '
                  'differing from the home' % (found['pages'], len(found['covered']), len(found['missing']),
                                               '' if kit_has else '; kit has no parts/ScreenFit.js',
                                               len(found.get('loading_swap') or [])))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    return []
