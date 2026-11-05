#!/usr/bin/env python3
"""Bind new pictures to Cocos Creator 2.4 / 3.x prefab/scene nodes so they keep their own ratio (P08).

Do not hand-edit node width/height after swapping a picture: this script does it.

  python3 bind_art.py --project <Cocos project> --map bind.json [--gen-log <gen_log.json>] [--dry-run]
  python3 bind_art.py --project <Cocos project> --check [<prefab, .fire or .scene> ...]     read-only, about 1 s

Cocos 2.4 (.prefab/.fire): size is the node's _contentSize, scale _trs/_scale. Cocos 3.x (.prefab/.scene): size is
the cc.UITransform component's _contentSize, scale _lscale; the sprite frame is the "<uuid>@f9941" sub-asset.
The rules below are the same for both.

bind.json: {"bindings": [{"prefab": "assets/prefabs/Result.prefab", "node": "Result/panel/btn_claim",
                          "image": "assets/resources/ui/btn_claim.png"}, ...]}
  "node"   names from the prefab root (scene: from the first node under the scene), joined by "/".
           3.x nested prefab instance: name the node through the instance ("Canvas/PlayBtn/icon", the instance
           named as in the scene). The binding is written as cc.PrefabInstance.propertyOverrides in this file
           (UITransform _contentSize, Sprite _spriteFrame/_sizeMode/_isTrimmedMode; localID = [component fileId],
           deeper levels [nested PrefabInstance fileId, ..., component fileId]); the nested .prefab is not changed.
           --check also reads the overrides, so a frame swapped only in the scene's overrides is reported.
  "image"  a PNG inside the project that Cocos has imported (it has a .meta). Instead of "image", "name"
           takes the picture from --gen-log (ad-boost postprocess.py: post.copied_to, else post.final).
  "by"     "rect" (default): the visible part fills the node; "original": the node stands for the whole PNG
           including its transparent border (glow/alignment kept on purpose).

Import type (P12): a bound picture must be imported as a sprite (2.4 .meta "type": "sprite" with a sprite-frame
sub-meta; 3.x .meta userData.type "sprite-frame" with the "f9941" sprite-frame sub-asset). A picture imported as
a plain texture (2.4 "raw"/"texture", 3.x "texture") is switched to sprite in the same run (the texture uuid stays,
so code that loads it as a texture keeps working); any other type is an error that names the type.

What a binding does (Cocos 2.4/3.x Sprite.trim, as in ad-boost AdBoostKit 1.2.0 trimFor):
  * node size = the picture's ratio contained in the node's old box (never stretched, never larger than the box);
  * by rect -> trim on; by original -> trim off; sizeMode CUSTOM; the sprite frame is set to the picture;
  * SLICED / TILED / FILLED sprites keep their size (stretching is their job), only the frame is set.
Errors (nothing is written for the whole run):
  * upscale: the node would show the picture more than 2x its pixels (with the node and parent scales)
    -> regenerate bigger (display size x 2, backgrounds x 1.5);
  * cover_old_text: under the bound node there is a flat colour block (built-in single-colour frame, a flat
    PNG or cc.Graphics) and a cc.Label -> old words covered by a patch and new words typed on top;
    regenerate the whole picture with the new word instead (rule T02);
  * no Sprite on the node, a Label on the same node (2.4 and 3.x draw one render component per node), node not
    found / ambiguous, picture not imported, picture imported as a type that is not a sprite or a texture,
    a 3.x picture bound into a 2.4 file (or the other way round), a 3.x node without cc.UITransform.
Every binding is recorded with the old box and the new size in <project>/docs/art/bind_log.json.
--check lists every SIMPLE sprite whose drawn picture is more than 10 % off its own ratio (the old way: a new
frame dropped into the old box); exit 1 when there is one.
"""
import argparse
import json
import math
import os
import pathlib
import sys
import uuid as uuidlib

MAX_UPSCALE = 2.0
RATIO_TOL = 0.10
# Cocos built-in single-colour frames (default_sprite_splash, default_sprite): 2.4, then 3.x (Creator 3.8.8
# editor/assets/default_ui, sprite-frame sub-asset f9941)
BUILTIN_FLAT = {'a23235d1-15db-4b95-8439-a2e005bfff91', '8cdb44ac-a3f6-449f-b354-7cd48cf84061',
                '7d8f9b89-4fd1-4c9f-a3ab-38ec7cded7ca@f9941', '57520716-48c8-4a19-8acf-41c9f8777fb0@f9941'}
SIMPLE, SLICED = 0, 1
CUSTOM = 0
V3_FRAME_ID, V3_TEX_ID = 'f9941', '6c48a'   # fixed sub-asset ids of a 3.x image: spriteFrame, texture
TEXTURE_TYPES_24 = ('raw', 'texture')
TEXTURE_TYPES_3X = ('texture',)


class BindError(Exception):
    pass


def read_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def write_json(p, data):
    p = pathlib.Path(p)
    tmp = p.with_name(p.name + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, p)


# ---------------------------------------------------------------- project pictures
def meta_is_3x(m):
    """3.x image metas have a top-level "importer" ("image") and sub-assets with their own importer."""
    return isinstance(m, dict) and 'importer' in m


def frame_subs(m):
    """(frame uuid, trim fields) for each sprite frame a .meta declares. 2.4: every sub-meta of a "sprite" meta
    (the trim fields sit on the sub-meta); 3.x: the "sprite-frame" sub-assets (trim fields in its userData)."""
    out = []
    for sub in (m.get('subMetas') or {}).values():
        if not isinstance(sub, dict) or not sub.get('uuid'):
            continue
        if meta_is_3x(m):
            if sub.get('importer') == 'sprite-frame':
                out.append((sub['uuid'], sub.get('userData') or {}))
        else:
            out.append((sub['uuid'], sub))
    return out


def index_frames(project):
    """frame uuid -> {png, meta entry}; png path (relative) -> (frame uuid, entry)."""
    by_uuid, by_png = {}, {}
    assets = pathlib.Path(project) / 'assets'
    for meta in assets.rglob('*.png.meta'):
        try:
            m = read_json(meta)
        except (ValueError, OSError):
            continue
        png = meta.with_suffix('')
        rel = png.relative_to(project).as_posix()
        for u, sub in frame_subs(m):
            by_uuid[u] = {'png': png, 'rel': rel, 'meta': sub, 'v3': meta_is_3x(m)}
            by_png.setdefault(rel, (u, sub))
    return by_uuid, by_png


def _trim_fields(png):
    """Auto-trim fields as the Cocos importer writes them (threshold 1), measured on the PNG."""
    from PIL import Image
    with Image.open(png) as src:
        im = src.convert('RGBA')
    W, H = im.size
    box = im.getchannel('A').point(lambda v: 255 if v > 1 else 0).getbbox() or (0, 0, W, H)
    w, h = box[2] - box[0], box[3] - box[1]
    return {'trimType': 'auto', 'trimThreshold': 1, 'rotated': False,
            'offsetX': box[0] + w / 2.0 - W / 2.0, 'offsetY': -(box[1] + h / 2.0 - H / 2.0),
            'trimX': box[0], 'trimY': box[1], 'width': w, 'height': h, 'rawWidth': W, 'rawHeight': H,
            'borderTop': 0, 'borderBottom': 0, 'borderLeft': 0, 'borderRight': 0}


def sprite_frame_of(project, rel, by_png):
    """P12: the bound picture must be imported as a sprite. Returns (frame uuid, trim fields, is_3x, fix) where
    fix is None or {'meta': path, 'data': new meta, 'from': old type} to be written with the rest of the batch."""
    meta_path = pathlib.Path(project) / (rel + '.meta')
    if not meta_path.exists():
        raise BindError('%s is not an imported sprite in the project (no .png.meta with a sprite frame); '
                        'open the project in Cocos Creator once so it imports the picture' % rel)
    try:
        m = read_json(meta_path)
    except ValueError as e:
        raise BindError('%s.meta is not valid JSON (%s)' % (rel, e))
    if rel in by_png:
        u, sub = by_png[rel]
        typ = (m.get('userData') or {}).get('type') if meta_is_3x(m) else m.get('type')
        if typ in ('sprite-frame', 'sprite'):
            return u, sub, meta_is_3x(m), None
    png = pathlib.Path(project) / rel
    name = pathlib.Path(rel).stem
    data = json.loads(json.dumps(m))
    if meta_is_3x(m):
        ud = data.setdefault('userData', {})
        typ = ud.get('type')
        if typ not in TEXTURE_TYPES_3X + ('sprite-frame',):
            raise BindError('%s is imported as "%s" (3.x .meta userData.type); a bound picture must be "sprite-frame". '
                            'Set the type to sprite-frame in Creator, or use another picture for this node' % (rel, typ))
        subs = data.setdefault('subMetas', {})
        tex = subs.get(V3_TEX_ID)
        if not isinstance(tex, dict) or not tex.get('uuid'):
            raise BindError('%s.meta has no texture sub-asset "%s"; open the project in Cocos Creator once so it '
                            'imports the picture' % (rel, V3_TEX_ID))
        u = '%s@%s' % (data['uuid'], V3_FRAME_ID)
        fields = dict(_trim_fields(png), packable=True, pixelsToUnit=100, pivotX=0.5, pivotY=0.5, meshType=0,
                      isUuid=True, imageUuidOrDatabaseUri=tex['uuid'], atlasUuid='')
        subs[V3_FRAME_ID] = {'importer': 'sprite-frame', 'uuid': u, 'displayName': name, 'id': V3_FRAME_ID,
                             'name': 'spriteFrame', 'userData': fields, 'ver': '1.0.12', 'imported': False,
                             'files': ['.json'], 'subMetas': {}}
        ud['type'] = 'sprite-frame'
        ud.setdefault('redirect', tex['uuid'])
        return u, fields, True, {'meta': meta_path, 'data': data, 'from': typ}
    typ = data.get('type')
    if typ not in TEXTURE_TYPES_24 + ('sprite',):
        raise BindError('%s is imported as "%s" (2.4 .meta type); a bound picture must be "sprite". Set the type '
                        'to sprite in Creator, or use another picture for this node' % (rel, typ))
    if not data.get('uuid'):
        raise BindError('%s.meta has no uuid; open the project in Cocos Creator once so it imports the picture' % rel)
    # same uuid every run (dry run and real run agree; Creator keeps a sub-meta uuid it finds in the .meta)
    u = str(uuidlib.uuid5(uuidlib.NAMESPACE_URL, 'cocos-sprite-frame:' + data['uuid']))
    fields = dict(_trim_fields(png), ver='1.0.6', uuid=u, rawTextureUuid=data['uuid'], subMetas={})
    data['type'] = 'sprite'
    data['subMetas'] = {name: fields}
    return u, fields, False, {'meta': meta_path, 'data': data, 'from': typ}


def picture_geometry(png, sub):
    """Visible rect and whole size, measured on the PNG (the meta can be stale after a file swap)."""
    from PIL import Image
    with Image.open(png) as src:
        im = src.convert('RGBA')
    W, H = im.size
    kind = (sub or {}).get('trimType', 'auto')
    if kind == 'none':
        box = (0, 0, W, H)
    elif kind == 'custom':
        x, y = int(sub.get('trimX', 0)), int(sub.get('trimY', 0))
        box = (x, y, x + int(sub.get('width', W)), y + int(sub.get('height', H)))
    else:
        thr = int((sub or {}).get('trimThreshold', 1))
        box = im.getchannel('A').point(lambda v: 255 if v > thr else 0).getbbox() or (0, 0, 1, 1)
    rect = [box[2] - box[0], box[3] - box[1]]
    stale = bool(sub) and (int(sub.get('rawWidth', W)) != W or int(sub.get('rawHeight', H)) != H or
                           (kind == 'auto' and [int(sub.get('width', 0)), int(sub.get('height', 0))] != rect))
    return {'raw': [W, H], 'rect': rect, 'meta_stale': stale}


def flat_png(png):
    from PIL import Image
    with Image.open(png) as src:
        im = src.convert('RGBA')
    px = [p for p in im.resize((32, 32)).getdata() if p[3] > 128]
    if not px:
        return True
    return all(max(p[i] for p in px) - min(p[i] for p in px) <= 12 for i in range(3))


# ---------------------------------------------------------------- prefab / scene graph
OVERRIDE_TYPE = 'CCPropertyOverrideInfo'   # as Creator 3.x writes it (no "cc." prefix)


class Resolver:
    """3.x nested prefab instances: a scene/prefab keeps only the instance root node and a cc.PrefabInstance whose
    propertyOverrides (targetInfo.localID + propertyPath + value) change the nested prefab's nodes/components.
    The children live in the nested .prefab (found by PrefabInfo.asset uuid). A view is a fresh copy of that prefab
    with the overrides applied, so sizes and frames read from it are what the game shows."""

    def __init__(self, project):
        self.project = pathlib.Path(project).resolve() if project else None
        self._assets = None

    def asset_path(self, u):
        if self.project is None or not u:
            return None
        if self._assets is None:
            self._assets = {}
            for meta in (self.project / 'assets').rglob('*.prefab.meta'):
                try:
                    m = read_json(meta)
                except (ValueError, OSError):
                    continue
                if isinstance(m, dict) and m.get('uuid'):
                    self._assets[m['uuid']] = meta.with_suffix('')
        return self._assets.get(u)

    def view(self, doc, i, depth=0):
        inst, pi = doc.instance(i), doc.prefab_info(i)
        u = ((pi or {}).get('asset') or {}).get('__uuid__')
        p = self.asset_path(u)
        if inst is None or p is None or depth > 8:
            return None
        inner = Doc(p, self)
        own = [(lid, path, v) for lid, path, v, _ in doc.overrides(inst)]
        fid = inst.get('fileId')
        outer = [(lid[1:], path, v) for lid, path, v in doc.pending if len(lid) > 1 and lid[0] == fid]
        inner.apply_overrides(own + outer)   # outer levels win, as in the engine
        inner.depth = depth + 1
        return inner


class Doc:
    def __init__(self, path, resolver=None):
        self.path = pathlib.Path(path)
        self.data = read_json(path)
        if not isinstance(self.data, list):
            raise BindError('%s: not a Cocos prefab/scene (JSON array expected)' % path)
        self.nodes = [i for i, o in enumerate(self.data) if isinstance(o, dict) and o.get('__type__') == 'cc.Node']
        # 3.x: sizes live on cc.UITransform, nodes carry _lpos/_lscale; 2.4: _contentSize on the node
        self.v3 = any(isinstance(o, dict) and (o.get('__type__') == 'cc.UITransform' or '_lscale' in o)
                      for o in self.data)
        self.resolver = resolver
        self.pending = []      # overrides for deeper nested instances (localID longer than 1)
        self.touched = set()   # id() of objects changed by an override (nested views only)
        self.depth = 0
        self._names = {}

    # ---- 3.x nested prefab instances
    def prefab_info(self, i):
        o = self.obj(self.data[i].get('_prefab'))
        return o if isinstance(o, dict) else None

    def instance(self, i):
        pi = self.prefab_info(i)
        o = self.obj(pi.get('instance')) if pi else None
        return o if isinstance(o, dict) and o.get('__type__') == 'cc.PrefabInstance' else None

    def overrides(self, inst):
        out = []
        for ref in inst.get('propertyOverrides') or []:
            o = self.obj(ref)
            if not isinstance(o, dict):
                continue
            t = self.obj(o.get('targetInfo')) or {}
            out.append((list(t.get('localID') or []), list(o.get('propertyPath') or []), o.get('value'), o))
        return out

    def file_ids(self):
        """fileId -> object: nodes by PrefabInfo.fileId, components by CompPrefabInfo (__prefab) fileId."""
        out = {}
        for o in self.data:
            if not isinstance(o, dict):
                continue
            if o.get('__type__') == 'cc.Node':
                pi = self.obj(o.get('_prefab'))
                if isinstance(pi, dict) and pi.get('fileId'):
                    out.setdefault(pi['fileId'], o)
            elif isinstance(o.get('__prefab'), dict):
                cp = self.obj(o['__prefab'])
                if isinstance(cp, dict) and cp.get('fileId'):
                    out.setdefault(cp['fileId'], o)
        return out

    def apply_overrides(self, ovs):
        fids = self.file_ids()
        for lid, path, v in ovs:
            if not lid or not path:
                continue
            if len(lid) > 1:
                self.pending.append((lid, path, v))
                continue
            o = fids.get(lid[0])
            if o is None:
                continue
            for k in path[:-1]:
                o = o.setdefault(k, {})
            o[path[-1]] = json.loads(json.dumps(v))
            self.touched.add(id(fids[lid[0]]))

    def root(self):
        top = self.data[0] if self.data else {}
        r = self.obj(top.get('data')) if isinstance(top, dict) else None
        if isinstance(r, dict):
            return self.data.index(r)
        return next((i for i in self.nodes if self.parent(i) is None), self.nodes[0] if self.nodes else None)

    def node_name(self, i):
        if i in self._names:
            return self._names[i]
        n, name = self.data[i], self.data[i].get('_name', '')
        if self.instance(i) is not None and self.resolver is not None:
            v = self.resolver.view(self, i, self.depth)
            if v is not None and v.root() is not None:
                name = v.data[v.root()].get('_name', '') or name
        self._names[i] = name
        return name

    def comp_file_id(self, comp, what):
        cp = self.obj(comp.get('__prefab')) if isinstance(comp.get('__prefab'), dict) else None
        if not isinstance(cp, dict) or not cp.get('fileId'):
            raise BindError('%s: the %s in the nested prefab has no __prefab fileId, so no override can point at it; '
                            'bind the node in %s itself' % (self.path.name, what, self.path.name))
        return cp['fileId']

    def resolve(self, path, prefix=(), scale=(1.0, 1.0), outer=None):
        """-> (doc, node index, nest). nest is None for a node stored in this file, else
        {'doc': file being bound, 'instance': its cc.PrefabInstance, 'local_id': localID prefix, 'scale': ...}."""
        hits = [i for i in self.nodes if self.path_of(i) == path]
        if len(hits) > 1:
            raise BindError('%s: node "%s" is ambiguous (%d nodes); rename them first' % (self.path.name, path, len(hits)))
        if hits:
            nest = None if outer is None else dict(outer, local_id=list(prefix), scale=scale, asset=self.path)
            return self, hits[0], nest
        for r in self.nodes:
            inst = self.instance(r)
            if inst is None:
                continue
            rp = self.path_of(r)
            if not path.startswith(rp + '/'):
                continue
            view = self.resolver.view(self, r, self.depth) if self.resolver else None
            if view is None:
                raise BindError('%s: node "%s" is inside the nested prefab instance "%s" whose .prefab was not found '
                                'in the project' % (self.path.name, path, rp))
            par = self.parent(r)
            sx, sy = self.scale(par) if par is not None else (1.0, 1.0)
            pre = list(prefix) + ([inst.get('fileId')] if outer is not None else [])
            nxt = outer or {'doc': self, 'instance': inst}
            return view.resolve(view.path_of(view.root()) + path[len(rp):], pre, (scale[0] * sx, scale[1] * sy), nxt)
        hint = ''
        if self.v3 and any(isinstance(o, dict) and o.get('__type__') == 'cc.PrefabInstance' for o in self.data):
            hint = ('; this 3.x file has nested prefab instances whose children are not stored here: name the node '
                    'through the instance (e.g. "Root/<instance>/<child>") or bind it in that prefab\'s own .prefab')
        raise BindError('%s: node "%s" not found%s' % (self.path.name, path, hint))

    def transform(self, i):
        t = self.comps(i, 'cc.UITransform')
        return t[0] if t else None

    def obj(self, ref):
        return self.data[ref['__id__']] if isinstance(ref, dict) and '__id__' in ref else None

    def parent(self, i):
        p = self.data[i].get('_parent')
        return p['__id__'] if isinstance(p, dict) and '__id__' in p else None

    def path_of(self, i):
        names = []
        while i is not None and self.data[i].get('__type__') == 'cc.Node':
            names.append(self.node_name(i))
            i = self.parent(i)
        return '/'.join(reversed(names))

    def find(self, path):
        d, i, nest = self.resolve(path)
        if nest is not None:
            raise BindError('%s: node "%s" is inside a nested prefab instance' % (self.path.name, path))
        return i

    def comps(self, i, kind=None):
        out = []
        for ref in self.data[i].get('_components') or []:
            c = self.obj(ref)
            if c and (kind is None or c.get('__type__') == kind):
                out.append(c)
        return out

    def children(self, i):
        return [r['__id__'] for r in self.data[i].get('_children') or [] if isinstance(r, dict) and '__id__' in r]

    def descendants(self, i, depth=2):
        out, level = [], [i]
        for _ in range(depth):
            level = [c for n in level for c in self.children(n)]
            out += level
        return out

    def size_owner(self, i):
        """The object holding _contentSize: the node (2.4) or its cc.UITransform (3.x)."""
        if not self.v3:
            return self.data[i]
        t = self.transform(i)
        if t is None:
            raise BindError('%s: node "%s" has no cc.UITransform (Cocos 3.x keeps the size there)'
                            % (self.path.name, self.path_of(i)))
        return t

    def size(self, i):
        s = self.size_owner(i).get('_contentSize') or {}
        return [float(s.get('width', 0)), float(s.get('height', 0))]

    def set_size(self, i, w, h):
        o = self.size_owner(i)
        o.setdefault('_contentSize', {'__type__': 'cc.Size'})
        o['_contentSize']['width'] = w
        o['_contentSize']['height'] = h

    def scale(self, i):
        """Product of |scale| from the node up to the root (3.x _lscale, 2.4 _trs array or older _scale)."""
        sx = sy = 1.0
        while i is not None and self.data[i].get('__type__') == 'cc.Node':
            n = self.data[i]
            trs = n.get('_trs')
            if isinstance(n.get('_lscale'), dict):
                sx *= abs(n['_lscale'].get('x', 1)); sy *= abs(n['_lscale'].get('y', 1))
            elif isinstance(trs, dict) and isinstance(trs.get('array'), list) and len(trs['array']) >= 9:
                sx *= abs(trs['array'][7]); sy *= abs(trs['array'][8])
            elif isinstance(n.get('_scale'), dict):
                sx *= abs(n['_scale'].get('x', 1)); sy *= abs(n['_scale'].get('y', 1))
            else:
                sx *= abs(n.get('_scaleX', 1)); sy *= abs(n.get('_scaleY', 1))
            i = self.parent(i)
        return sx, sy


def frame_uuid(sprite):
    f = sprite.get('_spriteFrame')
    return f.get('__uuid__') if isinstance(f, dict) else None


def contain(ratio, box_w, box_h):
    if box_w <= 0 or box_h <= 0:
        raise BindError('node has no size to fit into (%sx%s)' % (box_w, box_h))
    if box_w / box_h > ratio:
        return round(box_h * ratio, 1), round(box_h, 1)
    return round(box_w, 1), round(box_w / ratio, 1)


def drawn_ratio(node_size, trim, geo):
    """Ratio at which Cocos 2.4 draws the visible part (simple.js): trim on stretches the rect over the node;
    trim off maps the whole PNG onto the node and the rect sits inside it."""
    nw, nh = node_size
    if nw <= 0 or nh <= 0:
        return None
    if trim:
        return nw / nh
    (rw, rh), (W, H) = geo['rect'], geo['raw']
    return (rw * nw / W) / (rh * nh / H)


def cover_old_text(doc, i, frames):
    blocks, labels = [], []
    for c in [i] + doc.descendants(i):
        if doc.comps(c, 'cc.Label') or doc.comps(c, 'cc.RichText'):
            if c != i:
                labels.append(doc.path_of(c))
        if c == i:
            continue
        if doc.comps(c, 'cc.Graphics'):
            blocks.append(doc.path_of(c))
            continue
        for s in doc.comps(c, 'cc.Sprite'):
            u = frame_uuid(s)
            if u in BUILTIN_FLAT or (u in frames and flat_png(frames[u]['png'])):
                blocks.append(doc.path_of(c))
    return blocks, labels


# ---------------------------------------------------------------- bind
SPRITE_OVERRIDE_KEYS = ('_spriteFrame', '_sizeMode', '_isTrimmedMode', '_atlas')


def set_override(doc, inst, lid, path, value):
    """Write one propertyOverride on a 3.x cc.PrefabInstance (replace the value when the same target/path exists)."""
    for _lid, _path, _v, o in doc.overrides(inst):
        if _lid == lid and _path == path:
            o['value'] = value
            return
    if not isinstance(inst.get('propertyOverrides'), list):
        inst['propertyOverrides'] = []
    oid = len(doc.data)
    doc.data.append({'__type__': OVERRIDE_TYPE, 'targetInfo': {'__id__': oid + 1}, 'propertyPath': list(path),
                     'value': value})
    doc.data.append({'__type__': 'cc.TargetInfo', 'localID': list(lid)})
    inst['propertyOverrides'].append({'__id__': oid})


def bind_one(doc, b, frames, by_png, project, meta_fixes=None):
    outer_doc = doc
    doc, i, nest = outer_doc.resolve(b['node'])
    if nest is not None:
        return bind_nested(outer_doc, doc, i, nest, b, frames, by_png, project, meta_fixes)
    return bind_local(doc, i, b, frames, by_png, project, meta_fixes)


def bind_nested(outer_doc, view, i, nest, b, frames, by_png, project, meta_fixes):
    """3.x node inside a nested prefab instance: bind on the effective copy of the nested prefab, then write what
    changed as propertyOverrides on the instance in the bound file (the nested .prefab is not touched)."""
    sprites = view.comps(i, 'cc.Sprite')
    tr = view.transform(i) if view.v3 else None
    before_sp = json.loads(json.dumps({k: sprites[0].get(k) for k in SPRITE_OVERRIDE_KEYS})) if sprites else {}
    before_sz = json.loads(json.dumps((tr or {}).get('_contentSize')))
    rec = bind_local(view, i, b, frames, by_png, project, meta_fixes, scale_mul=nest['scale'])
    sp = sprites[0]
    pre, inst = nest['local_id'], nest['instance']
    changes = []
    if tr is not None and tr.get('_contentSize') != before_sz:
        changes.append((pre + [view.comp_file_id(tr, 'cc.UITransform')], ['_contentSize'], tr['_contentSize']))
    sp_id = None
    for k in SPRITE_OVERRIDE_KEYS:
        if sp.get(k) != before_sp.get(k):
            sp_id = sp_id or view.comp_file_id(sp, 'cc.Sprite')
            changes.append((pre + [sp_id], [k], sp.get(k)))
    for lid, path, v in changes:
        set_override(outer_doc, inst, lid, path, json.loads(json.dumps(v)))
    rec['prefab'] = outer_doc.path.relative_to(project).as_posix()
    rec['nested'] = {'prefab': pathlib.Path(nest['asset']).resolve().relative_to(project).as_posix(),
                     'overrides': [{'localID': lid, 'propertyPath': path} for lid, path, _ in changes]}
    return rec


def bind_local(doc, i, b, frames, by_png, project, meta_fixes=None, scale_mul=(1.0, 1.0)):
    if doc.comps(i, 'cc.Label') or doc.comps(i, 'cc.RichText'):
        raise BindError('%s: node has a Label; Cocos 2.4/3.x draw one render component per node, put the picture on a '
                        'child Sprite node' % b['node'])
    sprites = doc.comps(i, 'cc.Sprite')
    if not sprites:
        raise BindError('%s: node has no cc.Sprite' % b['node'])
    sp = sprites[0]
    rel = b['image']
    try:
        uuid, sub, pic_v3, fix = sprite_frame_of(project, rel, by_png)
    except BindError as e:
        raise BindError('%s: %s' % (b['node'], e))
    if pic_v3 != doc.v3:
        raise BindError('%s: %s was imported by Cocos %s but %s is a Cocos %s file; bind pictures of the same project'
                        % (b['node'], rel, '3.x' if pic_v3 else '2.4', doc.path.name, '3.x' if doc.v3 else '2.4'))
    if fix is not None and meta_fixes is not None:
        meta_fixes[str(fix['meta'])] = fix
        by_png[rel] = (uuid, sub)
        frames[uuid] = {'png': pathlib.Path(project) / rel, 'rel': rel, 'meta': sub, 'v3': pic_v3}
    geo = picture_geometry(pathlib.Path(project) / rel, sub)
    blocks, labels = cover_old_text(doc, i, frames)
    if blocks and labels:
        raise BindError('%s: cover_old_text: colour block %s and label %s under the button: old words are patched '
                        'over and new words typed on top. Regenerate the whole picture with the new word (T02) and '
                        'delete the block and label' % (b['node'], ', '.join(blocks), ', '.join(labels)))
    old = doc.size(i)
    by = b.get('by', 'rect')
    if by not in ('rect', 'original'):
        raise BindError('%s: "by" must be rect or original' % b['node'])
    stype = sp.get('_type', SIMPLE)
    rec = {'prefab': doc.path.relative_to(project).as_posix(), 'node': b['node'], 'image': rel, 'frame_uuid': uuid,
           'old_size': old, 'picture_raw': geo['raw'], 'picture_rect': geo['rect'], 'by': by}
    if geo['meta_stale']:
        rec['meta_stale'] = 'the .meta does not match the PNG yet; Cocos updates it on the next import'
    if fix is not None:
        rec['meta_fixed'] = 'import type %s -> %s' % (fix['from'], 'sprite-frame' if pic_v3 else 'sprite')
    if doc.v3:
        rec['engine'] = '3.x'
    if stype != SIMPLE:
        new, trim = old, sp.get('_isTrimmedMode', True)
        rec['kept'] = 'sprite type %s keeps its size' % stype
    else:
        src = geo['rect'] if by == 'rect' else geo['raw']
        new = list(contain(src[0] / float(src[1]), old[0], old[1]))
        trim = by == 'rect'
    sx, sy = doc.scale(i)
    sx, sy = sx * scale_mul[0], sy * scale_mul[1]
    src = geo['rect'] if trim else geo['raw']
    up = max(new[0] * sx / src[0], new[1] * sy / src[1])
    rec.update({'new_size': new, 'trim': trim, 'size_mode': 'CUSTOM', 'upscale': round(up, 2)})
    if stype == SIMPLE and up > MAX_UPSCALE:
        raise BindError('%s: upscale: the node shows %s at %.1fx its pixels (> %.0fx); regenerate it at about %dx%d px'
                        % (b['node'], rel, up, MAX_UPSCALE, math.ceil(new[0] * sx * 2), math.ceil(new[1] * sy * 2)))
    doc.set_size(i, new[0], new[1])
    if doc.v3:
        sp['_spriteFrame'] = {'__uuid__': uuid, '__expectedType__': 'cc.SpriteFrame'}
        if sp.get('_atlas'):
            sp['_atlas'] = None  # the picture is a standalone sprite frame now, not a frame of the old atlas
    else:
        sp['_spriteFrame'] = {'__uuid__': uuid}
    sp['_sizeMode'] = CUSTOM
    sp['_isTrimmedMode'] = bool(trim)
    r = drawn_ratio(new, trim, geo)
    rec['ratio_diff'] = round(abs(r / (geo['rect'][0] / float(geo['rect'][1])) - 1), 4) if r else None
    return rec


def resolve_bindings(m, gen_log, project):
    out = []
    records = (read_json(gen_log).get('records') or {}) if gen_log else {}
    for b in m.get('bindings') or []:
        b = dict(b)
        if not b.get('image') and b.get('name'):
            post = (records.get(b['name']) or {}).get('post') or {}
            p = post.get('copied_to') or post.get('final')
            if not p:
                raise BindError('%s: no finished picture for "%s" in %s' % (b.get('node'), b['name'], gen_log))
            try:
                b['image'] = pathlib.Path(p).resolve().relative_to(pathlib.Path(project).resolve()).as_posix()
            except ValueError:
                raise BindError('%s: %s is outside the project; run postprocess.py with --project/--dest first'
                                % (b.get('node'), p))
        if not b.get('prefab') or not b.get('node') or not b.get('image'):
            raise BindError('binding needs prefab, node and image (or name with --gen-log): %s' % json.dumps(b))
        out.append(b)
    return out


def run_bind(project, map_path, gen_log, dry):
    project = pathlib.Path(project).resolve()
    frames, by_png = index_frames(project)
    bindings = resolve_bindings(read_json(map_path), gen_log, project)
    docs, records, meta_fixes = {}, [], {}
    resolver = Resolver(project)
    for b in bindings:
        p = (project / b['prefab']).resolve()
        if p not in docs:
            docs[p] = Doc(p, resolver)
        records.append(bind_one(docs[p], b, frames, by_png, project, meta_fixes))
    if not dry:
        for fix in meta_fixes.values():
            write_json(fix['meta'], fix['data'])
        for d in docs.values():
            write_json(d.path, d.data)
        log_path = project / 'docs' / 'art' / 'bind_log.json'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log = read_json(log_path) if log_path.exists() else {'tool': 'remake-art/scripts/bind_art.py', 'bindings': {}}
        for r in records:
            log['bindings']['%s#%s' % (r['prefab'], r['node'])] = r
        write_json(log_path, log)
    return records


# ---------------------------------------------------------------- check
def run_check(project, files):
    project = pathlib.Path(project).resolve()
    frames, _ = index_frames(project)
    if not files:
        files = [p for ext in ('*.prefab', '*.fire', '*.scene') for p in (project / 'assets').rglob(ext)]
    bad = []
    resolver = Resolver(project)

    def walk(doc, prefix=''):
        """the file's own nodes, then nested 3.x instances seen through their overrides (only what an override
        changed is checked there: the nested .prefab's own values are checked when that file is checked)."""
        yield doc, prefix
        for r in doc.nodes:
            if doc.instance(r) is None:
                continue
            v = resolver.view(doc, r, doc.depth)
            if v is not None:
                par = doc.parent(r)
                yield from walk(v, prefix + (doc.path_of(par) + '/' if par is not None and doc.path_of(par) else ''))

    for f in files:
        try:
            top = Doc(f, resolver)
        except (BindError, ValueError):
            continue
        for doc, prefix in walk(top):
            check_doc(doc, prefix, top, project, frames, bad)
    return bad


def check_doc(doc, prefix, top, project, frames, bad):
    nested = doc is not top
    for i in doc.nodes:
        for sp in doc.comps(i, 'cc.Sprite'):
            if nested and id(sp) not in doc.touched and id(doc.transform(i) or {}) not in doc.touched:
                continue
            u = frame_uuid(sp)
            if sp.get('_type', SIMPLE) != SIMPLE or u not in frames or u in BUILTIN_FLAT:
                continue
            if sp.get('_sizeMode', CUSTOM) != CUSTOM:
                continue  # TRIMMED / RAW: the engine sizes the node from the frame itself
            try:
                node_size = doc.size(i)
            except BindError:
                continue  # 3.x sprite node without cc.UITransform: nothing to measure
            geo = picture_geometry(frames[u]['png'], frames[u]['meta'])
            r = drawn_ratio(node_size, sp.get('_isTrimmedMode', True), geo)
            if r is None:
                continue
            want = geo['rect'][0] / float(geo['rect'][1])
            diff = abs(r / want - 1)
            if diff > RATIO_TOL:
                bad.append({'file': top.path.resolve().relative_to(project).as_posix(), 'node': prefix + doc.path_of(i),
                            'image': frames[u]['rel'], 'node_size': node_size, 'picture_rect': geo['rect'],
                            'ratio_diff': round(diff, 3)})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--project', required=True)
    ap.add_argument('--map')
    ap.add_argument('--gen-log', default='')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--check', nargs='*')
    a = ap.parse_args()
    try:
        if a.check is not None:
            bad = run_check(a.project, a.check)
            for b in bad:
                print('[FAIL] squashed: %s %s shows %s (%dx%d visible) in a %gx%g node, %.0f%% off; bind it with '
                      'bind_art.py' % (b['file'], b['node'], b['image'], b['picture_rect'][0], b['picture_rect'][1],
                                       b['node_size'][0], b['node_size'][1], b['ratio_diff'] * 100))
            print('%d squashed sprite(s)' % len(bad))
            return 1 if bad else 0
        if not a.map:
            ap.error('--map is required unless --check is given')
        for r in run_bind(a.project, a.map, a.gen_log, a.dry_run):
            print('[ok]   %s %s: %gx%g -> %gx%g (trim %s, upscale %.2fx)%s' % (
                r['prefab'], r['node'], r['old_size'][0], r['old_size'][1], r['new_size'][0], r['new_size'][1],
                'on' if r['trim'] else 'off', r['upscale'], ' [meta stale]' if r.get('meta_stale') else '')
                + (' [%s]' % r['meta_fixed'] if r.get('meta_fixed') else ''))
        if a.dry_run:
            print('dry run: nothing written')
        return 0
    except BindError as e:
        print('[FAIL] %s' % e)
        print('nothing written')
        return 1


if __name__ == '__main__':
    sys.exit(main())
