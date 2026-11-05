"""Source step: the top bar keeps out from under the TikTok capsule by default (生成时预防 P06 第 4 点).

CapsuleLayout.js used to be opt-in, so most top bars never called it: the census (问题普查_20261104) counts element
overlap first (99 times in 64 games) and 16 top bars / coin counters under the capsule. This step makes it the default:

  new games (board remake, policy new, Cocos 2.4): copies parts/CapsuleLayout.js and parts/CapsuleAuto.js to
      assets/tiktok-platform/ (kit bytes, checked against KIT_MANIFEST). CapsuleAuto runs by itself after every scene
      launch and moves only the top-bar nodes that really overlap the capsule (see the part's header). Nothing to call.
  English games (board localize) and legacy games: nothing written. K_W_capsule_auto lists the top-bar nodes found in
      the scenes and prefabs (name contains top / hud / coin, or a node in the top 15% of the design right under the
      Canvas or a page root), so the session can check them on the phone sizes / put them under the capsule itself.
  Cocos 3.x: not installed yet (CapsuleAuto is 2.4 only); the same list as info.

Scanned: every scene and the prefabs whose file name says home / main / menu / start / lobby / game / play / battle /
hud / top / bar / ui (level and item prefabs are not pages). Static top-bar rule (the runtime part uses the same names; it moves only what overlaps the capsule): name
/top|hud|coin/i with its top edge in the top 30%, or local top edge in the
top 15% of the design for a child of the Canvas / of a page root; a node taller than 25% of the design height is a
page root or background, not a bar. A game file named CapsuleLayout.js / CapsuleAuto.js somewhere else in assets/ with
other bytes would make a second module of the same name in Cocos 2.4: the step then writes nothing and warns
(K_W_capsule_auto_conflict).
Called by tiktok_finalize `source` (SOURCE_STEPS; the wiring line is in the I3 handoff, not in this file).
"""
import json
import re

from . import Result, sha256
from .art_static import SCENE_SUFFIXES, Scene, _num, _skip, design_resolution, project_files

STEP = 'capsule_auto'
NAME = re.compile(r'top|hud|coin', re.I)
PAGE = re.compile(r'home|main|menu|start|lobby|game|play|battle|hud|top|bar|ui', re.I)   # page prefabs (scenes always)
TOP_SHARE = 0.15
BAR_SHARE = 0.25
NAME_SHARE = 0.30               # a named node lower than the top 30% (a coin panel mid-screen) is not a top bar
MAX_DEPTH = 4
DEST_DIR = 'assets/tiktok-platform/'
PARTS = ('parts/CapsuleLayout.js', 'parts/CapsuleAuto.js')


def _size(scene, node):
    s = node.get('_contentSize')
    if not isinstance(s, dict):
        for c in scene.comps(node):
            if c.get('__type__') == 'cc.UITransform':
                s = c.get('_contentSize')
                break
    s = s if isinstance(s, dict) else {}
    return _num(s.get('width')), _num(s.get('height'))


def _pos(node):
    p = node.get('_lpos') or node.get('_position') or {}                  # 3.x _lpos; old 2.x _position
    p = p if isinstance(p, dict) else {}
    trs = node.get('_trs')                                                  # 2.4: TypedArray [x, y, z, ...]
    if isinstance(trs, dict) and isinstance(trs.get('array'), list) and len(trs['array']) >= 2:
        return _num(trs['array'][0]), _num(trs['array'][1])
    return _num(p.get('x')), _num(p.get('y'))


def _anchor_y(scene, node):
    a = node.get('_anchorPoint')
    if not isinstance(a, dict):
        for c in scene.comps(node):
            if c.get('__type__') == 'cc.UITransform':
                a = c.get('_anchorPoint')
                break
    return _num((a or {}).get('y'), 0.5) if isinstance(a, dict) else 0.5


def _kids(scene, node):
    return [c for c in (scene.obj(r) for r in node.get('_children') or []) if c and c.get('__type__') == 'cc.Node']


def _roots(scene):
    """Canvas nodes of a scene; the root node of a prefab (it is placed under a Canvas at run time)."""
    out = [scene.obj(c.get('node')) for c in scene.objs if isinstance(c, dict) and c.get('__type__') == 'cc.Canvas']
    out = [n for n in out if n]
    if not out and scene.rel.endswith('.prefab'):
        for o in scene.objs:
            if isinstance(o, dict) and o.get('__type__') == 'cc.Node' and not scene.obj(o.get('_parent')):
                out.append(o)
                break
    return out


def top_bars(scene, design):
    """[{file, node, why}] top-bar candidates of one scene / prefab (static rule of the module docstring)."""
    W, H = design
    line = H / 2 - H * TOP_SHARE                     # Canvas-centred local y of the top-15% line
    out = []

    def walk(node, depth, page_level, oy):
        for n in _kids(scene, node):
            if n.get('_active') is False:
                continue
            w, h = _size(scene, n)
            x, y = _pos(n)
            top = oy + y + h * (1 - _anchor_y(scene, n))
            bar = h <= H * BAR_SHARE
            by_name = bar and top > H / 2 - H * NAME_SHARE and bool(NAME.search(str(n.get('_name') or '')))
            by_place = bar and page_level and top > line
            if by_name or by_place:
                out.append({'file': scene.rel, 'node': scene.path(n), 'why': 'name' if by_name else 'top 15%',
                            'top': round(top, 1)})
            elif depth < MAX_DEPTH:
                walk(n, depth + 1, depth == 0, oy + y)

    for root in _roots(scene):
        walk(root, 0, True, 0.0)
    return out


def scan(files):
    scenes, unreadable = [], []
    for rel in sorted(files):
        page = rel.endswith(('.fire', '.scene')) or PAGE.search(rel.split('/')[-1])   # not level / item prefabs
        if rel.startswith('assets/') and rel.endswith(SCENE_SUFFIXES) and not _skip(rel) and page:
            try:
                scenes.append(Scene(rel, json.loads(files[rel].decode('utf-8-sig'))))
            except (ValueError, UnicodeDecodeError):
                unreadable.append(rel)
    design = design_resolution(scenes)
    bars = []
    for s in scenes:
        bars += top_bars(s, design)
    return {'design': list(design), 'bars': bars, 'scenes': len(scenes), 'unreadable': unreadable}


def _kit(ctx, key):
    """(dest, bytes) of a kit part, refused (KitError text) unless its bytes equal KIT_MANIFEST files[key].sha256."""
    spec = (ctx.manifest.files or {}).get(key) if ctx.manifest else None
    if not isinstance(spec, dict) or not spec.get('sha256'):
        raise ValueError('%s not registered in KIT_MANIFEST files' % key)
    src = ctx.manifest.kit_dir / key
    data = src.read_bytes() if src.is_file() else None
    if data is None or sha256(data) != spec['sha256']:
        raise ValueError('kit file %s missing or differs from KIT_MANIFEST' % key)
    return spec.get('project_path') or DEST_DIR + key.split('/')[-1], data, spec


def _elsewhere(root, dest):
    name = dest.split('/')[-1]
    base = root / 'assets'
    if not base.is_dir():
        return []
    return [p for p in base.rglob(name) if p.is_file() and p.relative_to(root).as_posix() != dest
            and not _skip(p.relative_to(root).as_posix())]


def _shown(bars, k=8):
    return '; '.join('%s %s (%s)' % (b['file'], b['node'], b['why']) for b in bars[:k])


def detect(ctx):
    if ctx.engine != 2 or ctx.policy == 'legacy' or ctx.board == 'localize':
        return 'n/a'
    states = []
    for key in PARTS:
        try:
            dest, data, _ = _kit(ctx, key)
        except ValueError:
            return 'conflict'
        have = ctx.read(dest)
        states.append('absent' if have is None else 'kit_current' if have == data else 'own')
    return 'kit_current' if set(states) == {'kit_current'} else ('absent' if 'own' not in states else 'kit_old')


def apply(ctx):
    r = Result(STEP)
    found = scan(project_files(ctx.root))
    bars = found['bars']
    r.info.append('design %gx%g; %d scene/prefab file(s); %d top-bar node(s): %s'
                  % (found['design'][0], found['design'][1], found['scenes'], len(bars), _shown(bars) or '-'))
    strict = ctx.policy != 'legacy' and ctx.board != 'localize'
    if not strict or ctx.engine != 2:
        r.state = 'n/a'
        if bars and ctx.engine == 2:
            r.warn('K_W_capsule_auto', '%d top-bar node(s) not kept out from under the TikTok capsule by the kit (%s: '
                   'CapsuleAuto is installed for new games only): %s. Check them on both phone sizes; move the ones '
                   'under the capsule with CapsuleLayout.placeBelow (assets/tiktok-platform/CapsuleLayout.js)'
                   % (len(bars), 'English game' if ctx.board == 'localize' else 'legacy game', _shown(bars)), bars[:30])
        elif bars:
            r.info.append('Cocos 3.x: CapsuleAuto not installed (2.4 only); use CapsuleLayout.placeBelow on these')
        return r.as_dict()
    try:
        parts = [_kit(ctx, key) for key in PARTS]
    except ValueError as error:
        r.state = 'conflict'
        r.block('K_kit_unusable', str(error))
        return r.as_dict()
    clash = [(dest, p) for dest, data, _ in parts for p in _elsewhere(ctx.root, dest) if p.read_bytes() != data]
    if clash:
        r.state = 'conflict'
        r.warn('K_W_capsule_auto_conflict', 'not installed: the game has its own %s (a second module of the same name '
               'breaks the Cocos 2.4 build). Delete the game copy (the kit one is the same part, newer) and run source '
               'again' % ', '.join(p.relative_to(ctx.root).as_posix() for _, p in clash))
        return r.as_dict()
    states = []
    for dest, data, spec in parts:
        if _elsewhere(ctx.root, dest):                    # the game already carries these exact kit bytes elsewhere
            states.append('kit_current')
            continue
        have = ctx.read(dest)
        if have == data:
            states.append('kit_current')
            continue
        old = have is not None and sha256(have) in set(spec.get('previous_sha256') or [])
        if have is not None:
            r.info.append('moved %s to %s' % (dest, ctx.move_away(dest)))
        ctx.write(dest, data)
        r.change(dest, have, data, '%s %s' % (dest.split('/')[-1], 'added' if have is None else
                                               'restored (%s)' % ('kit_old' if old else 'own')))
        states.append('absent')
    r.state = 'kit_current' if set(states) == {'kit_current'} else 'absent'
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    """Read only (package_gates may reuse it): no findings; the runtime part and layout_state judge the bar itself."""
    return []
