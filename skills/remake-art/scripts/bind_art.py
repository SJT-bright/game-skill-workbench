#!/usr/bin/env python3
"""Bind new pictures to Cocos Creator 2.4 prefab/scene nodes so they keep their own ratio (P08).

Do not hand-edit node width/height after swapping a picture: this script does it.

  python3 bind_art.py --project <Cocos 2.4 project> --map bind.json [--gen-log <gen_log.json>] [--dry-run]
  python3 bind_art.py --project <Cocos 2.4 project> --check [<prefab or .fire> ...]     read-only, about 1 s

bind.json: {"bindings": [{"prefab": "assets/prefabs/Result.prefab", "node": "Result/panel/btn_claim",
                          "image": "assets/resources/ui/btn_claim.png"}, ...]}
  "node"   names from the prefab root (scene: from the first node under the scene), joined by "/".
  "image"  a PNG inside the project that Cocos has imported (it has a .meta). Instead of "image", "name"
           takes the picture from --gen-log (ad-boost postprocess.py: post.copied_to, else post.final).
  "by"     "rect" (default): the visible part fills the node; "original": the node stands for the whole PNG
           including its transparent border (glow/alignment kept on purpose).

What a binding does (Cocos 2.4 Sprite.trim, as in ad-boost AdBoostKit 1.2.0 trimFor):
  * node size = the picture's ratio contained in the node's old box (never stretched, never larger than the box);
  * by rect -> trim on; by original -> trim off; sizeMode CUSTOM; the sprite frame is set to the picture;
  * SLICED / TILED / FILLED sprites keep their size (stretching is their job), only the frame is set.
Errors (nothing is written for the whole run):
  * upscale: the node would show the picture more than 2x its pixels (with the node and parent scales)
    -> regenerate bigger (display size x 2, backgrounds x 1.5);
  * cover_old_text: under the bound node there is a flat colour block (built-in single-colour frame, a flat
    PNG or cc.Graphics) and a cc.Label -> old words covered by a patch and new words typed on top;
    regenerate the whole picture with the new word instead (rule T02);
  * no Sprite on the node, a Label on the same node (2.4 draws one render component per node), node not
    found / ambiguous, picture not imported.
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

MAX_UPSCALE = 2.0
RATIO_TOL = 0.10
# Cocos 2.4 built-in single-colour frames (default_sprite_splash, default_sprite)
BUILTIN_FLAT = {'a23235d1-15db-4b95-8439-a2e005bfff91', '8cdb44ac-a3f6-449f-b354-7cd48cf84061'}
SIMPLE, SLICED = 0, 1
CUSTOM = 0


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
        for sub in (m.get('subMetas') or {}).values():
            if isinstance(sub, dict) and sub.get('uuid'):
                rel = png.relative_to(project).as_posix()
                by_uuid[sub['uuid']] = {'png': png, 'rel': rel, 'meta': sub}
                by_png.setdefault(rel, (sub['uuid'], sub))
    return by_uuid, by_png


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
class Doc:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.data = read_json(path)
        if not isinstance(self.data, list):
            raise BindError('%s: not a Cocos 2.4 prefab/scene (JSON array expected)' % path)
        self.nodes = [i for i, o in enumerate(self.data) if isinstance(o, dict) and o.get('__type__') == 'cc.Node']

    def obj(self, ref):
        return self.data[ref['__id__']] if isinstance(ref, dict) and '__id__' in ref else None

    def parent(self, i):
        p = self.data[i].get('_parent')
        return p['__id__'] if isinstance(p, dict) and '__id__' in p else None

    def path_of(self, i):
        names = []
        while i is not None and self.data[i].get('__type__') == 'cc.Node':
            names.append(self.data[i].get('_name', ''))
            i = self.parent(i)
        return '/'.join(reversed(names))

    def find(self, path):
        hits = [i for i in self.nodes if self.path_of(i) == path]
        if not hits:
            raise BindError('%s: node "%s" not found' % (self.path.name, path))
        if len(hits) > 1:
            raise BindError('%s: node "%s" is ambiguous (%d nodes); rename them first' % (self.path.name, path, len(hits)))
        return hits[0]

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

    def size(self, i):
        s = self.data[i].get('_contentSize') or {}
        return [float(s.get('width', 0)), float(s.get('height', 0))]

    def set_size(self, i, w, h):
        self.data[i].setdefault('_contentSize', {'__type__': 'cc.Size'})
        self.data[i]['_contentSize']['width'] = w
        self.data[i]['_contentSize']['height'] = h

    def scale(self, i):
        """Product of |scale| from the node up to the root (2.4 _trs array or older _scale)."""
        sx = sy = 1.0
        while i is not None and self.data[i].get('__type__') == 'cc.Node':
            n = self.data[i]
            trs = n.get('_trs')
            if isinstance(trs, dict) and isinstance(trs.get('array'), list) and len(trs['array']) >= 9:
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
def bind_one(doc, b, frames, by_png, project):
    i = doc.find(b['node'])
    if doc.comps(i, 'cc.Label') or doc.comps(i, 'cc.RichText'):
        raise BindError('%s: node has a Label; Cocos 2.4 draws one render component per node, put the picture on a '
                        'child Sprite node' % b['node'])
    sprites = doc.comps(i, 'cc.Sprite')
    if not sprites:
        raise BindError('%s: node has no cc.Sprite' % b['node'])
    sp = sprites[0]
    rel = b['image']
    if rel not in by_png:
        raise BindError('%s: %s is not an imported sprite in the project (no .png.meta with a sprite frame); '
                        'open the project in Cocos Creator once so it imports the picture' % (b['node'], rel))
    uuid, sub = by_png[rel]
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
    if stype != SIMPLE:
        new, trim = old, sp.get('_isTrimmedMode', True)
        rec['kept'] = 'sprite type %s keeps its size' % stype
    else:
        src = geo['rect'] if by == 'rect' else geo['raw']
        new = list(contain(src[0] / float(src[1]), old[0], old[1]))
        trim = by == 'rect'
    sx, sy = doc.scale(i)
    src = geo['rect'] if trim else geo['raw']
    up = max(new[0] * sx / src[0], new[1] * sy / src[1])
    rec.update({'new_size': new, 'trim': trim, 'size_mode': 'CUSTOM', 'upscale': round(up, 2)})
    if stype == SIMPLE and up > MAX_UPSCALE:
        raise BindError('%s: upscale: the node shows %s at %.1fx its pixels (> %.0fx); regenerate it at about %dx%d px'
                        % (b['node'], rel, up, MAX_UPSCALE, math.ceil(new[0] * sx * 2), math.ceil(new[1] * sy * 2)))
    doc.set_size(i, new[0], new[1])
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
    docs, records = {}, []
    for b in bindings:
        p = (project / b['prefab']).resolve()
        if p not in docs:
            docs[p] = Doc(p)
        records.append(bind_one(docs[p], b, frames, by_png, project))
    if not dry:
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
        files = [p for ext in ('*.prefab', '*.fire') for p in (project / 'assets').rglob(ext)]
    bad = []
    for f in files:
        try:
            doc = Doc(f)
        except (BindError, ValueError):
            continue
        for i in doc.nodes:
            for sp in doc.comps(i, 'cc.Sprite'):
                u = frame_uuid(sp)
                if sp.get('_type', SIMPLE) != SIMPLE or u not in frames or u in BUILTIN_FLAT:
                    continue
                if sp.get('_sizeMode', CUSTOM) != CUSTOM:
                    continue  # TRIMMED / RAW: the engine sizes the node from the frame itself
                geo = picture_geometry(frames[u]['png'], frames[u]['meta'])
                r = drawn_ratio(doc.size(i), sp.get('_isTrimmedMode', True), geo)
                if r is None:
                    continue
                want = geo['rect'][0] / float(geo['rect'][1])
                diff = abs(r / want - 1)
                if diff > RATIO_TOL:
                    bad.append({'file': pathlib.Path(f).resolve().relative_to(project).as_posix(), 'node': doc.path_of(i),
                                'image': frames[u]['rel'], 'node_size': doc.size(i), 'picture_rect': geo['rect'],
                                'ratio_diff': round(diff, 3)})
    return bad


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
                'on' if r['trim'] else 'off', r['upscale'], ' [meta stale]' if r.get('meta_stale') else ''))
        if a.dry_run:
            print('dry run: nothing written')
        return 0
    except BindError as e:
        print('[FAIL] %s' % e)
        print('nothing written')
        return 1


if __name__ == '__main__':
    sys.exit(main())
