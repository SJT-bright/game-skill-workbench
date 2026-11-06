"""Source step (read only, well under 1 s): skin previews use each skin's own picture (生成时预防 Round 4 R4P4, R4O2 leftover).

R4O2 wrote check_skin_preview.py (SLS35 2026-11-05: the store preview bound to the slot frame TileIn.png, skins "made"
by tinting the whole preview node). It only ran by hand; this step runs the same two checks at `source` and `sync`.
Runs only when the project has a skin table: unlock_table.json or skins.json (outside library / temp / build /
node_modules / .tiktok-kit / tiktok-platform) with skin or background rows in "items". No table -> nothing checked.
  table   every skin / background row has its own previewFrame (missing, TODO, shared, slot / frame picture reported)
  source  .ts / .js under assets/: a preview / skin node coloured anything but white (tint_as_skin)

Levels: legacy -> not checked. English (board localize) -> warning (K_W_skin_preview). New remake game -> block
(K_skin_preview) when the table was written by the R4O2 make_skin_table.py (any row carries "previewFrame"; then every
row must name a real picture before packaging) ; a new remake game whose table has no previewFrame at all (written by
an older generator or by hand, the frozen normal-10-50.v1 table) -> warning, so games in progress are not stopped.
Called by tiktok_finalize `source` (SOURCE_STEPS) and `sync` (SYNC_SOURCE_STEPS). CLI: scripts/check_skin_preview.py.
"""
import json
import sys
import time
from pathlib import Path

from . import Result

STEP = 'skin_preview_scan'
GATE = 'K_skin_preview'
TABLE_NAMES = ('unlock_table.json', 'skins.json')
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', '.tiktok-kit', '__macosx', 'profiles',
             'tiktok-platform', 'platform-kit'}
MAX_BYTES = 4 * 1024 * 1024


def _checker():
    here = str(Path(__file__).resolve().parent.parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    import check_skin_preview
    return check_skin_preview


def _walk(root, want):
    for p in sorted(Path(root).rglob('*')):
        rel = p.relative_to(root)
        if any(part.lower() in SKIP_DIRS for part in rel.parts[:-1]) or not want(p) or not p.is_file():
            continue
        if p.stat().st_size <= MAX_BYTES:
            yield p, rel.as_posix()


def tables_of(root):
    """-> [(rel, table)] skin tables with at least one skin / background row."""
    C = _checker()
    out = []
    for p, rel in _walk(root, lambda p: p.name in TABLE_NAMES):
        try:
            t = json.loads(p.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        items = t.get('items') if isinstance(t, dict) else None
        if isinstance(items, list) and any(isinstance(r, dict) and r.get('group') in C.GROUPS for r in items):
            out.append((rel, t))
    return out


def scan(root):
    t0 = time.time()
    C = _checker()
    root = Path(root)
    tables = tables_of(root)
    hits, generated = [], False
    for rel, t in tables:
        rows = [r for r in t['items'] if isinstance(r, dict) and r.get('group') in C.GROUPS]
        generated = generated or any('previewFrame' in r for r in rows)
        hits += [dict(h, file=rel) for h in C.check_table(t)]
    if tables and (root / 'assets').is_dir():
        for p, rel in _walk(root / 'assets', lambda p: p.suffix in ('.ts', '.js')):
            try:
                hits += C.check_source(p.read_text(encoding='utf-8', errors='replace'), 'assets/' + rel)
            except OSError:
                continue
    return {'tables': [rel for rel, _ in tables], 'generated': generated, 'hits': hits,
            'seconds': round(time.time() - t0, 3)}


def level_of(policy='new', board=None, generated=False):
    if policy == 'legacy':
        return 'skip'
    if board == 'localize' or not generated:
        return 'warn'
    return 'block'


def message(hits):
    shown = '; '.join('%s %s %s' % (h.get('file') or h.get('where'), h['kind'], h.get('id') or h.get('line', ''))
                      for h in hits[:8])
    return ('%d skin preview problem(s): %s. Every skin / background row names its own previewFrame picture and the '
            'store / trial template binds only that; never a slot / frame picture, never Sprite.color on the preview '
            'node (R4O2, SLS35). Check: remake-core/scripts/check_skin_preview.py' % (len(hits), shown))


def detect(ctx):
    if ctx.policy == 'legacy':
        return 'kit_current'
    found = scan(ctx.root)
    if not found['tables']:
        return 'n/a'
    return 'conflict' if found['hits'] else 'kit_current'


def apply(ctx):
    r = Result(STEP)
    if ctx.policy == 'legacy':
        r.state = 'kit_current'
        r.info.append('legacy game: skin previews not checked')
        return r.as_dict()
    found = scan(ctx.root)
    if not found['tables']:
        r.state = 'n/a'
        r.info.append('no skin table (unlock_table.json / skins.json with skin rows): not checked')
        return r.as_dict()
    level = level_of(ctx.policy, getattr(ctx, 'board', None), found['generated'])
    if found['hits']:
        if level == 'block':
            r.block(GATE, message(found['hits']), found['hits'][:30])
        else:
            r.warn(GATE.replace('K_', 'K_W_', 1), message(found['hits']), found['hits'][:30])
    r.state = 'conflict' if r.blocks else 'kit_current'
    r.info.append('%d table(s) %s; previewFrame written by generator: %s; %d hit(s) in %.2f s; level %s' % (
        len(found['tables']), ', '.join(found['tables'][:4]), found['generated'], len(found['hits']),
        found['seconds'], level))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    return []
