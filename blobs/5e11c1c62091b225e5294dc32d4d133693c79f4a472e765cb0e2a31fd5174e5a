"""Source step: squashed sprites and invisible play objects, read from the scenes before the build (v7.8, 总表 U7（补）).

Read only. Runs after `images` on <project>/assets/**/*.fire|*.scene|*.prefab and the sprite-frame sizes in the .meta
files (Cocos 2.4 and 3.x serialisation). Formal version of the 返工调查_20261030 prototype static_aspect.py: on
丛林荡藤 v4 it reports the 4 squashed pictures (btn_reward 1.55x, over ui/title 1.52x, btn_video_reward 1.24x,
suo/btn_video 1.11x); v6 is clean.

No popup-dim opacity limit (Saul 10-31 removed it, together with the 0.55x brightness idea): how dark a popup or page
is follows the game's style and is judged by eye (not too bright overall; no dull background without a designed
pattern, a black dim over an empty panel or a plain colour block is not acceptable). The earlier K_art_dim /
K_W_art_dim (opacity < 150) are gone.

  K_art_aspect  a squashed picture: a SIMPLE sprite (type 0) with size mode CUSTOM (0) whose drawn aspect ratio (node
                content size x scale) differs from its sprite frame's (trimmed size, or raw size when trimming is off)
                by more than 10%. Not reported: SLICED / TILED / FILLED / MESH sprites, other size modes, the bar
                sprite of a cc.ProgressBar (its size follows the progress at run time: Holly loadImg), and a
                picture that looks the same when stretched along that axis (every row, or every column, of the frame
                is one colour, e.g. the 7x8 rope gradient `line` of 丛林荡藤 that is drawn 100x5).
  K_art_hidden_body  (v7.8, 总表 H6 静态部分) a play object the player can hit but not see: a node with an enabled,
                non-sensor 2D collider (2.4 cc.Physics*Collider / cc.*Collider, 3.x cc.*Collider2D) whose own and
                descendant cc.Sprite components all are switched off or have no sprite frame (剪刀达人 v17/v18
                paperItem.prefab: collider on, `img` Sprite _enabled false, the board was invisible). Nodes without any
                Sprite (invisible walls, ground drawn by Graphics / TerrainGround) are not reported. New remake games
                block; legacy games and localized games (board localize) get K_W_art_hidden_body.
New remake games: blocks (the block lands in the source record, so both writers refuse the build: K5_source_finalized).
Legacy games and localized games (board localize; Saul 10-30: the English pack keeps the original art, matching the
art receipt's ART_receipt warn for localize): the same findings as warnings K_W_art_aspect / K_W_art_hidden_body. A scene or .meta that is not
readable JSON is the warning K_W_art_static_unreadable. <project>/docs/art/static-exempt.json {"nodes": [{"file": glob, "node": glob,
"why": "..."}]} exempts nodes that are never shown (base-game nodes code hides at run time); each one is listed in the
warning K_W_art_static_exempt, and an entry without a written why is ignored. Sprites whose frame is set only by code, prefab-instance overrides and
animations are not seen here; the art check's runtime dumps (audit_page_richness) still cover those.
"""
import json
from pathlib import Path

from . import Result, finding

STEP = 'art_static'
SCENE_SUFFIXES = ('.fire', '.scene', '.prefab')
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', '.tiktok-kit', '__macosx', 'profiles'}
SETTINGS_3X = 'settings/v2/packages/project.json'
MAX_STRETCH = 1.10               # same limit as audit_page_richness squashed_picture
DEFAULT_DESIGN = (640, 1136)
UNIFORM_TOLERANCE = 16           # per channel, premultiplied alpha
UNIFORM_SHARE = 0.97


def _num(value, default=0.0):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _skip(rel):
    return bool(SKIP_DIRS & {x.lower() for x in rel.split('/')[:-1]})


# ---------------------------------------------------------------- sprite frames from .meta

def _frame(name, sub, meta_rel):
    data = sub.get('userData') if isinstance(sub.get('userData'), dict) else sub      # 3.x keeps sizes in userData
    w, h = _num(data.get('width')), _num(data.get('height'))
    if not (sub.get('uuid') and w > 0 and h > 0):
        return None
    image = meta_rel[:-5] if meta_rel.lower().endswith(('.png.meta', '.jpg.meta', '.jpeg.meta', '.webp.meta')) else None
    return {'uuid': sub['uuid'], 'name': name, 'w': w, 'h': h,
            'raw_w': _num(data.get('rawWidth'), w) or w, 'raw_h': _num(data.get('rawHeight'), h) or h,
            'trim_x': int(_num(data.get('trimX'))), 'trim_y': int(_num(data.get('trimY'))),
            'rotated': bool(data.get('rotated')), 'image': image, 'meta': meta_rel}


def frames_from_metas(metas):
    """{sprite-frame uuid: frame} from {meta relpath: bytes} (2.4 subMetas, 3.x subMetas with userData)."""
    out, unreadable = {}, []
    for rel in sorted(metas):
        try:
            meta = json.loads(metas[rel].decode('utf-8-sig'))
        except (ValueError, UnicodeDecodeError):
            unreadable.append(rel)
            continue
        todo = [meta] if isinstance(meta, dict) else []
        while todo:
            node = todo.pop()
            for name, sub in (node.get('subMetas') or {}).items():
                if not isinstance(sub, dict):
                    continue
                f = _frame(name, sub, rel)
                if f:
                    out[f['uuid']] = f
                if sub.get('subMetas'):
                    todo.append(sub)
    return out, unreadable


# ---------------------------------------------------------------- scene objects

class Scene:
    def __init__(self, rel, objs):
        self.rel = rel
        self.objs = objs if isinstance(objs, list) else [objs]

    def obj(self, ref):
        if isinstance(ref, dict) and isinstance(ref.get('__id__'), int) and 0 <= ref['__id__'] < len(self.objs):
            o = self.objs[ref['__id__']]
            return o if isinstance(o, dict) else None
        return None

    def comps(self, node):
        return [c for c in (self.obj(r) for r in node.get('_components') or []) if c]

    def comp(self, node, kind):
        for c in self.comps(node):
            if c.get('__type__') == kind:
                return c
        return None

    def parent(self, node):
        return self.obj(node.get('_parent'))

    def path(self, node):
        names, seen = [], set()
        while node is not None and id(node) not in seen:
            seen.add(id(node))
            if node.get('__type__') in ('cc.Scene', 'cc.SceneAsset'):
                break
            names.append(str(node.get('_name') or '?'))
            node = self.parent(node)
        return '/'.join(reversed(names))

    def size(self, node):
        ui = self.comp(node, 'cc.UITransform')                                   # 3.x
        cs = (ui or {}).get('_contentSize') if ui else node.get('_contentSize')
        cs = cs if isinstance(cs, dict) else {}
        return _num(cs.get('width')), _num(cs.get('height'))

    @staticmethod
    def scale(node):
        trs = node.get('_trs')
        if isinstance(trs, dict) and isinstance(trs.get('array'), list) and len(trs['array']) >= 9:     # 2.4
            return abs(_num(trs['array'][7], 1)), abs(_num(trs['array'][8], 1))
        for key in ('_lscale', '_scale'):                                        # 3.x / old 2.x
            s = node.get(key)
            if isinstance(s, dict):
                return abs(_num(s.get('x'), 1)), abs(_num(s.get('y'), 1))
        return abs(_num(node.get('_scaleX'), 1)), abs(_num(node.get('_scaleY'), 1))


def design_resolution(scenes, settings_3x=None):
    """(width, height) of the design: a portrait cc.Canvas design resolution (2.4), else the 3.x project setting,
    else 640x1136."""
    found = []
    for scene in scenes:
        for o in scene.objs:
            if isinstance(o, dict) and o.get('__type__') == 'cc.Canvas':
                d = o.get('_designResolution')
                if isinstance(d, dict) and _num(d.get('width')) > 0 and _num(d.get('height')) > 0:
                    found.append((_num(d['width']), _num(d['height'])))
    if settings_3x:
        try:
            d = (json.loads(settings_3x.decode('utf-8-sig')).get('general') or {}).get('designResolution') or {}
            if _num(d.get('width')) > 0 and _num(d.get('height')) > 0:
                found.append((_num(d['width']), _num(d['height'])))
        except (ValueError, UnicodeDecodeError, AttributeError):
            pass
    portrait = [d for d in found if d[1] >= d[0]]
    return (portrait or found or [DEFAULT_DESIGN])[0]


def _frame_uuid(sprite):
    ref = sprite.get('_spriteFrame')
    return ref.get('__uuid__') if isinstance(ref, dict) else None


COLLIDERS = {'cc.PhysicsBoxCollider', 'cc.PhysicsCircleCollider', 'cc.PhysicsPolygonCollider', 'cc.PhysicsChainCollider',
             'cc.BoxCollider', 'cc.CircleCollider', 'cc.PolygonCollider',                       # 2.4 physics / collision
             'cc.BoxCollider2D', 'cc.CircleCollider2D', 'cc.PolygonCollider2D'}                  # 3.x 2D physics


def _children(scene, node):
    return [c for c in (scene.obj(r) for r in node.get('_children') or []) if c and c.get('__type__') == 'cc.Node']


def hidden_bodies(scene):
    """H6 (v7.8): play objects the player can hit but not see (剪刀达人 v17/v18: paperItem.prefab kept its
    PhysicsPolygonCollider while the cc.Sprite of its child `img` was switched off, the board was invisible).
    A node with an enabled, non-sensor 2D collider whose own and descendant cc.Sprite components exist but none is
    both enabled and given a sprite frame. Nodes with no Sprite at all (invisible walls, ground drawn by Graphics or
    a TerrainGround script) and nodes set inactive in the file are not reported."""
    out = []
    for node in scene.objs:
        if not isinstance(node, dict) or node.get('__type__') != 'cc.Node' or node.get('_active') is False:
            continue
        cols = [c for c in scene.comps(node) if c.get('__type__') in COLLIDERS and c.get('_enabled') is not False
                and not c.get('_sensor') and not c.get('sensor')]
        if not cols:
            continue
        sprites, todo, seen = [], [node], set()
        while todo:
            n = todo.pop()
            if id(n) in seen or len(seen) > 200:
                continue
            seen.add(id(n))
            if n is not node and n.get('_active') is False:
                continue
            sprites += [(n, c) for c in scene.comps(n) if c.get('__type__') == 'cc.Sprite']
            todo += _children(scene, n)
        if not sprites:
            continue
        shown = [s for n, s in sprites if s.get('_enabled') is not False and _frame_uuid(s)]
        if shown:
            continue
        why = '; '.join('%s Sprite %s' % (scene.path(n), 'switched off' if s.get('_enabled') is False else 'has no picture')
                        for n, s in sprites[:3])
        out.append({'file': scene.rel, 'node': scene.path(node), 'colliders': sorted({c['__type__'] for c in cols}),
                    'sprites': why})
    return out


def progress_bars(scene):
    """ids of the cc.Sprite objects a cc.ProgressBar drives: the bar's width/height is set from the progress at run time."""
    out = set()
    for o in scene.objs:
        if isinstance(o, dict) and o.get('__type__') == 'cc.ProgressBar':
            ref = o.get('_N$barSprite') or o.get('_barSprite')
            if isinstance(ref, dict) and isinstance(ref.get('__id__'), int):
                out.add(ref['__id__'])
    return out


def squashed(scene, frames):
    out = []
    bars = progress_bars(scene)
    for index, sprite in enumerate(scene.objs):
        if not isinstance(sprite, dict) or sprite.get('__type__') != 'cc.Sprite' or index in bars:
            continue
        if int(_num(sprite.get('_sizeMode'), 1)) != 0 or int(_num(sprite.get('_type'), 0)) != 0:
            continue
        frame = frames.get(_frame_uuid(sprite))
        node = scene.obj(sprite.get('node'))
        if not frame or not node:
            continue
        w, h = scene.size(node)
        sx, sy = scene.scale(node)
        trimmed = sprite.get('_isTrimmedMode') is not False
        fw, fh = (frame['w'], frame['h']) if trimmed else (frame['raw_w'], frame['raw_h'])
        if not (w > 0 and h > 0 and sx > 0 and sy > 0 and fw > 0 and fh > 0):
            continue
        k = (w * sx / (h * sy)) / (fw / fh)
        stretch = max(k, 1 / k)
        if stretch > MAX_STRETCH:
            out.append({'file': scene.rel, 'node': scene.path(node), 'frame': frame['name'], 'image': frame['image'],
                        'meta': frame['meta'], 'frame_size': [fw, fh], 'node_size': [w, h], 'scale': [sx, sy],
                        'stretch': round(stretch, 2), 'axis': 'x' if k > 1 else 'y', 'trimmed': trimmed,
                        '_frame': frame})
    return out


def uniform_along(pixels, width, height, axis):
    """True when the picture looks the same stretched along `axis`: (nearly) every row (axis x) or column (axis y) is
    one colour. pixels: row-major list of premultiplied (r, g, b, a)."""
    if width <= 0 or height <= 0:
        return False
    lines = range(height) if axis == 'x' else range(width)
    span = width if axis == 'x' else height
    ok = total = 0
    for i in lines:
        line = [pixels[i * width + j] if axis == 'x' else pixels[j * width + i] for j in range(span)]
        mid = sorted(line)[len(line) // 2]
        for p in line:
            total += 1
            ok += max(abs(p[c] - mid[c]) for c in range(4)) <= UNIFORM_TOLERANCE
    return total > 0 and ok / total >= UNIFORM_SHARE


def read_pixels(path, frame, trimmed, limit=96):
    """Premultiplied RGBA pixels of the frame rectangle, sampled down to at most limit x limit. None if unreadable."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as im:
            im = im.convert('RGBA')
            if trimmed and not frame.get('rotated'):
                box = (frame['trim_x'], frame['trim_y'], frame['trim_x'] + int(frame['w']), frame['trim_y'] + int(frame['h']))
                if box[2] <= im.width and box[3] <= im.height and box[2] > box[0] and box[3] > box[1]:
                    im = im.crop(box)
            if im.width > limit or im.height > limit:
                im = im.resize((min(im.width, limit), min(im.height, limit)), Image.NEAREST)
            data = [(r * a // 255, g * a // 255, b * a // 255, a) for r, g, b, a in im.getdata()]
            return data, im.width, im.height
    except (OSError, ValueError):
        return None


def scan(files, root=None):
    """files {project-relative posix path: bytes} (scenes, prefabs, .meta, 3.x project setting). root: the project,
    to read frame pixels for the stretchable test (None = no pixel test, nothing counts as stretchable).
    -> {'design', 'squashed', 'hidden_bodies', 'stretchable', 'exempt', 'unreadable', 'scenes', 'frames'}"""
    metas = {r: d for r, d in files.items() if r.endswith('.meta') and r.startswith('assets/') and not _skip(r)}
    frames, unreadable = frames_from_metas(metas)
    scenes = []
    for rel in sorted(files):
        if rel.startswith('assets/') and rel.endswith(SCENE_SUFFIXES) and not _skip(rel):
            try:
                scenes.append(Scene(rel, json.loads(files[rel].decode('utf-8-sig'))))
            except (ValueError, UnicodeDecodeError):
                unreadable.append(rel)
    design = design_resolution(scenes, files.get(SETTINGS_3X))
    bad_aspect, ok_stretch, hidden = [], [], []
    for scene in scenes:
        hidden += hidden_bodies(scene)
        for item in squashed(scene, frames):
            frame = item.pop('_frame')
            pixels = read_pixels(Path(root) / frame['image'], frame, item['trimmed']) \
                if root is not None and frame.get('image') else None
            if pixels and uniform_along(pixels[0], pixels[1], pixels[2], item['axis']):
                ok_stretch.append(item)
            else:
                bad_aspect.append(item)
    rules = exemptions(root)
    bad_aspect, exempt_aspect = split_exempt(bad_aspect, rules)
    hidden, exempt_hidden = split_exempt(hidden, rules)
    return {'design': list(design), 'squashed': bad_aspect, 'hidden_bodies': hidden,
            'stretchable': ok_stretch, 'exempt': exempt_aspect + exempt_hidden, 'unreadable': unreadable,
            'scenes': len(scenes), 'frames': len(frames)}


EXEMPT = 'docs/art/static-exempt.json'


def exemptions(root):
    """[(file glob, node glob, why)] from <project>/docs/art/static-exempt.json; entries without a written why are ignored.
    For nodes this step cannot see are never shown: base-game nodes that code hides at run time (企鹅雪道 EnglishUI
    sets every old Canvas child inactive). Deleting such nodes is the better fix."""
    if root is None:
        return []
    try:
        data = json.loads((Path(root) / EXEMPT).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return []
    out = []
    for row in (data.get('nodes') if isinstance(data, dict) else None) or []:
        if isinstance(row, dict) and row.get('node') and str(row.get('why') or '').strip():
            out.append((str(row.get('file') or '*'), str(row['node']), str(row['why']).strip()))
    return out


def split_exempt(items, rules):
    import fnmatch
    keep, exempt = [], []
    for item in items:
        why = next((w for f, n, w in rules if fnmatch.fnmatchcase(item['file'], f) and fnmatch.fnmatchcase(item['node'], n)), None)
        (exempt if why else keep).append(dict(item, why=why) if why else item)
    return keep, exempt


def project_files(root):
    root = Path(root)
    out = {}
    base = root / 'assets'
    if base.is_dir():
        for p in sorted(base.rglob('*')):
            rel = p.relative_to(root).as_posix()
            if p.is_file() and not p.is_symlink() and not _skip(rel) and (rel.endswith(SCENE_SUFFIXES) or rel.endswith('.meta')):
                out[rel] = p.read_bytes()
    s = root / SETTINGS_3X
    if s.is_file():
        out[SETTINGS_3X] = s.read_bytes()
    return out


def findings(found, policy='new', board=None):
    # Every art_static finding blocks only a new game that is not localized (Saul 10-30: new remake games block; legacy
    # games and localized games warn, like ART_receipt). policy None (no decision) counts as new.
    strict = policy != 'legacy' and board != 'localize'
    out = []
    if found.get('hidden_bodies'):
        hard = strict
        shown = '; '.join('%s %s (%s; %s)' % (h['file'], h['node'], '/'.join(h['colliders']), h['sprites'])
                          for h in found['hidden_bodies'][:6])
        out.append(finding('K_art_hidden_body' if hard else 'K_W_art_hidden_body', 'block' if hard else 'warn',
                           '%d play object(s) with a collider but no visible picture (剪刀达人 v17/v18: the board kept its '
                           'collider while its Sprite was switched off, players could cut what they could not see): %s. '
                           'Switch the Sprite back on and give it its picture (or delete the collider if the object is '
                           'meant to be invisible and write it in docs/art/static-exempt.json with a why), then run the '
                           'source phase again' % (len(found['hidden_bodies']), shown), found['hidden_bodies'][:30]))
    if found['squashed']:
        images = sorted({i['image'] or i['meta'] for i in found['squashed']})
        shown = '; '.join('%s %s: frame %s %gx%g drawn %gx%g -> %.2fx' % (
            i['file'], i['node'], i['frame'], i['frame_size'][0], i['frame_size'][1],
            i['node_size'][0] * i['scale'][0], i['node_size'][1] * i['scale'][1], i['stretch'])
            for i in found['squashed'][:8])
        out.append(finding('K_art_aspect' if strict else 'K_W_art_aspect', 'block' if strict else 'warn',
                           '%d SIMPLE/CUSTOM sprite(s) on %d picture(s) squashed or stretched more than 10%%: %s. '
                           'Size each node to its picture (width:height = frame width:height), or make a stretchable '
                           'picture SLICED, then run the source phase again'
                           % (len(found['squashed']), len(images), shown), found['squashed'][:40]))
    if found.get('exempt'):
        out.append(finding('K_W_art_static_exempt', 'warn', '%d sprite/collider finding(s) exempted by %s (reason written '
                           'there; deleting unused nodes is the better fix): %s' % (
                               len(found['exempt']), EXEMPT, '; '.join('%s %s (%s)' % (i['file'], i['node'], i['why'][:60])
                                                                       for i in found['exempt'][:6])),
                           found['exempt'][:40]))
    if found['unreadable']:
        out.append(finding('K_W_art_static_unreadable', 'warn', '%d scene/prefab/.meta file(s) not readable as JSON, '
                           'sprite ratios and colliders not checked there: %s'
                           % (len(found['unreadable']), ', '.join(found['unreadable'][:5])), found['unreadable'][:20]))
    return out


def verify(files, manifest=None, policy=None):
    """Read-only findings on {relpath: bytes} of a project (no pixel test: nothing counts as stretchable)."""
    return findings(scan(files), policy or 'new')


def _state(found):
    if found['squashed'] or found.get('hidden_bodies'):
        return 'conflict'
    return 'kit_current' if found['scenes'] else 'n/a'


def detect(ctx):
    return _state(scan(project_files(ctx.root), ctx.root))


def apply(ctx):
    r = Result(STEP)
    found = scan(project_files(ctx.root), ctx.root)
    for item in findings(found, ctx.policy, getattr(ctx, 'board', None)):
        (r.blocks if item['level'] == 'block' else r.warnings).append(item)
    r.state = ('conflict' if r.blocks else 'kit_current' if found['scenes'] else 'n/a') if ctx.policy != 'legacy' \
        else ('kit_current' if found['scenes'] else 'n/a')
    r.info.append('design %gx%g; %d scene/prefab file(s), %d sprite frame(s); %d squashed sprite(s); %d stretched but '
                  'stretchable (one colour along that axis); %d collider node(s) without a visible picture'
                  % (found['design'][0], found['design'][1], found['scenes'], found['frames'],
                     len(found['squashed']), len(found['stretchable']), len(found['hidden_bodies'])))
    if found['stretchable']:
        r.info.append('stretchable: ' + '; '.join('%s %s (%s %.2fx)' % (i['file'], i['node'], i['frame'], i['stretch'])
                                                  for i in found['stretchable'][:8]))
    return r.as_dict()
