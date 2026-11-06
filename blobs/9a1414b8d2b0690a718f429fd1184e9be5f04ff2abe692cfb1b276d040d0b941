"""Source step (read only, well under 1 s): old and new art both live on one button slot (生成时预防 Round 4 R4Q1).

补查3 group 1 (5 games, 11-05: 合成进化恐龙, 奔跑吧巨人, 火箭三消, 方块收割者, 弹球传奇): after a whole new button
picture was bound, the old Label still drew its words over it ("X2" twice, old NO THANKS showing), and the button's
Widget and its parent's Layout both moved it (touch areas overlapping). remake-art/scripts/bind_art.py now binds a
button slot in one go (labels off, one layout owner, CUSTOM size, grey state on the new picture); this step reports
what was bound the old way, in every .prefab / .fire / .scene under assets/:
  text_over_picture  a button slot (cc.Button on the node, or on its parent targeting it) whose Sprite is drawn and
                     under which an enabled Label / RichText still has text, when either the slot was bound by
                     bind_art.py (docs/art/bind_log.json) or the text has CJK characters (an English game)
  two_layout_owners  an enabled cc.Widget on a node whose parent has an enabled cc.Layout that lays out children
Levels: legacy -> not checked; English (board localize) and new games -> warning (K_W_slot_overlap). Calibrated
read only on the local projects (see the R4Q1 patch 说明.md): in-progress games hit, so nothing blocks yet.
Called by tiktok_finalize `source` (SOURCE_STEPS) and `sync` (SYNC_SOURCE_STEPS). CLI: python3 -m
tiktok_finalize_steps.slot_overlap_scan <project> (prints the hits as JSON).
"""
import json
import re
import sys
import time
from pathlib import Path

from . import Result

STEP = 'slot_overlap_scan'
GATE = 'K_W_slot_overlap'
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', '.tiktok-kit', '__macosx', 'profiles'}
MAX_BYTES = 8 * 1024 * 1024
CJK = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]')


def _on(c):
    return isinstance(c, dict) and c.get('_enabled', True) is not False


def _text(c):
    for k in ('_string', '_N$string', 'string'):
        if isinstance(c.get(k), str):
            return c[k]
    return ''


def _get(c, name):
    for k in ('_N$' + name, '_' + name, name):
        if k in c:
            return c[k]
    return None


class _Doc:
    def __init__(self, data):
        self.d = data

    def obj(self, ref):
        if isinstance(ref, dict) and isinstance(ref.get('__id__'), int) and 0 <= ref['__id__'] < len(self.d):
            o = self.d[ref['__id__']]
            return o if isinstance(o, dict) else None
        return None

    def is_node(self, i):
        return isinstance(i, int) and 0 <= i < len(self.d) and isinstance(self.d[i], dict) and \
            self.d[i].get('__type__') == 'cc.Node'

    def comps(self, i, kind):
        out = []
        for ref in self.d[i].get('_components') or []:
            c = self.obj(ref)
            if c and c.get('__type__') == kind:
                out.append(c)
        return out

    def parent(self, i):
        p = self.d[i].get('_parent')
        return p['__id__'] if isinstance(p, dict) and self.is_node(p.get('__id__')) else None

    def children(self, i):
        return [r['__id__'] for r in self.d[i].get('_children') or [] if isinstance(r, dict) and
                self.is_node(r.get('__id__'))]

    def path(self, i):
        names, seen = [], set()
        while i is not None and i not in seen:
            seen.add(i)
            names.append(str(self.d[i].get('_name', '')))
            i = self.parent(i)
        return '/'.join(reversed(names))

    def active(self, i):
        return self.d[i].get('_active', True) is not False


def _texts(doc, top, depth=4):
    """Enabled text components drawn under `top` on active nodes (a Label under a RichText is the RichText's)."""
    out, level = [], [(top, False)]
    for _ in range(depth):
        nxt = []
        for n, in_rich in level:
            for c in doc.children(n):
                if not doc.active(c):
                    continue
                rich = bool(doc.comps(c, 'cc.RichText'))
                for comp in doc.comps(c, 'cc.RichText') + ([] if in_rich else doc.comps(c, 'cc.Label')):
                    if _on(comp) and _text(comp).strip():
                        out.append((c, _text(comp)))
                nxt.append((c, in_rich or rich))
        level = nxt
    return out


def _button_of(doc, i):
    for b in doc.comps(i, 'cc.Button'):
        return b
    par = doc.parent(i)
    if par is not None:
        for b in doc.comps(par, 'cc.Button'):
            t = _get(b, 'target')
            if not isinstance(t, dict) or t.get('__id__') in (None, i):
                return b
    return None


def scan_doc(data, rel, bound=()):
    doc, hits = _Doc(data), []
    for i, o in enumerate(data):
        if not isinstance(o, dict) or o.get('__type__') != 'cc.Node' or not doc.active(i):
            continue
        path = doc.path(i)
        sprites = [s for s in doc.comps(i, 'cc.Sprite') if _on(s) and isinstance(s.get('_spriteFrame'), dict)]
        if sprites and _button_of(doc, i) is not None:
            was_bound = path in bound
            words = [(c, t) for c, t in _texts(doc, i) if was_bound or CJK.search(t)]
            if words:
                hits.append({'file': rel, 'node': path, 'kind': 'text_over_picture', 'bound_by_bind_art': was_bound,
                             'labels': ['%s %s' % (doc.path(c), json.dumps(t[:30], ensure_ascii=False))
                                        for c, t in words[:4]]})
        par = doc.parent(i)
        if par is not None and any(_on(w) for w in doc.comps(i, 'cc.Widget')):
            lay = [l for l in doc.comps(par, 'cc.Layout') if _on(l) and (_get(l, 'layoutType') or 0) != 0]
            if lay:
                hits.append({'file': rel, 'node': path, 'kind': 'two_layout_owners',
                             'owners': ['cc.Widget', 'parent cc.Layout (%s)' % doc.path(par)]})
    return hits


def _files(root):
    assets = Path(root) / 'assets'
    if not assets.is_dir():
        return
    for p in sorted(assets.rglob('*')):
        if p.suffix not in ('.prefab', '.fire', '.scene') or not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part.lower() in SKIP_DIRS for part in rel.parts[:-1]) or p.stat().st_size > MAX_BYTES:
            continue
        yield p, rel.as_posix()


def _bound(root):
    """file -> {node path} bound by bind_art.py (docs/art/bind_log.json)."""
    out = {}
    try:
        log = json.loads((Path(root) / 'docs' / 'art' / 'bind_log.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return out
    for key in (log.get('bindings') or {}) if isinstance(log, dict) else {}:
        if '#' in key:
            f, n = key.split('#', 1)
            out.setdefault(f, set()).add(n)
    return out


def scan(root):
    t0 = time.time()
    bound, hits, n = _bound(root), [], 0
    for p, rel in _files(root):
        try:
            data = json.loads(p.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        if isinstance(data, list):
            n += 1
            hits += scan_doc(data, rel, bound.get(rel, ()))
    return {'files': n, 'hits': hits, 'seconds': round(time.time() - t0, 3)}


def level_of(policy='new', board=None):
    return 'skip' if policy == 'legacy' else 'warn'


def message(hits):
    shown = '; '.join('%s %s %s' % (h['file'], h['node'], h['kind']) for h in hits[:6])
    return ('%d button slot(s) with old and new art both active: %s. Bind whole pictures with remake-art/scripts/'
            'bind_art.py (button slot: old labels off, one layout owner, CUSTOM size, grey state on the new picture); '
            'list the slots left with `bind_art.py --slots` (R4Q1)' % (len(hits), shown))


def detect(ctx):
    if ctx.policy == 'legacy':
        return 'kit_current'
    return 'conflict' if scan(ctx.root)['hits'] else 'kit_current'


def apply(ctx):
    r = Result(STEP)
    level = level_of(ctx.policy, getattr(ctx, 'board', None))
    if level == 'skip':
        r.state = 'kit_current'
        r.info.append('legacy game: button slots not checked')
        return r.as_dict()
    found = scan(ctx.root)
    if found['hits']:
        r.warn(GATE, message(found['hits']), found['hits'][:30])
    r.state = 'kit_current'
    r.info.append('%d scene / prefab file(s), %d hit(s) in %.2f s; level %s' % (
        found['files'], len(found['hits']), found['seconds'], level))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    return []


if __name__ == '__main__':
    print(json.dumps(scan(sys.argv[1] if len(sys.argv) > 1 else '.'), ensure_ascii=False, indent=1))
