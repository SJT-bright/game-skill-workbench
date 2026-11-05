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


def _is_page(rel):
    return rel.endswith(('.fire', '.scene')) or (rel.endswith('.prefab') and PAGE.search(rel.split('/')[-1]))


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
    missing, ok, pages = [], [], 0
    for s in scenes:
        if not _is_page(s.rel):
            continue
        pages += 1
        for n in backgrounds(s, design):
            item = {'file': s.rel, 'node': s.path(n)}
            (ok if covered(s, n, by_type, texts) else missing).append(item)
    missing, exempt = split_exempt(missing, exemptions(root))   # docs/art/static-exempt.json (same file as art_static)
    return {'design': list(design), 'pages': pages, 'missing': missing, 'covered': ok, 'exempt': exempt,
            'unreadable': unreadable}


def findings(found, policy='new', board=None, kit_has_part=True):
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
    return 'conflict' if found['missing'] else ('kit_current' if found['pages'] else 'n/a')


def apply(ctx):
    r = Result(STEP)
    found = scan(ctx.root)
    kit_has = bool(ctx.manifest and isinstance((ctx.manifest.files or {}).get(SCREENFIT_KEY), dict))
    for item in findings(found, ctx.policy, getattr(ctx, 'board', None), kit_has):
        (r.blocks if item['level'] == 'block' else r.warnings).append(item)
    r.state = 'conflict' if r.blocks else ('kit_current' if found['pages'] else 'n/a')
    r.info.append('%d page file(s); %d background(s) with ScreenFit.cover, %d without%s'
                  % (found['pages'], len(found['covered']), len(found['missing']),
                     '' if kit_has else '; kit has no parts/ScreenFit.js'))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    return []
