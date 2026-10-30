#!/usr/bin/env python3
"""Generate the frozen legacy-game list (v7.7, design D77 section 2, W-L list v2). READ ONLY on every game folder.

    python3 make_legacy_list.py \
        --delivered <J> --finished <F> --games-root <下载/！自制游戏> --project-root <游戏出海项目制作> \
        --index <！游戏学习库/索引.json> --templates <启动包工坊> \
        --out-json <KIT/LEGACY_GAMES.json> --out-review <legacy_list_review.md> [--cache <scratch/nodes.json>]

Every root option is repeatable. What counts as a place a delivered game lives:
  --delivered     (J) every sub-folder is one game.
  --finished      (F) every top-level ZIP or sub-folder is one game.
  --games-root    (D) every game folder directly under it that holds a built TikTok package (a ZIP with game.json at
                  its root or in its first-level folder). Skipped: *_StarterPack, 启动包工坊, !玩法来源, _*, ！*/!* folders.
  --project-root  (P) every child of the delivery / work sub-folders (PROJECT_DIRS) is read package by package; a
                  child is not assumed to be one game (交付/源码, 交付/发给李总 hold many games).
  --index         (I) the en_source.path of every entry of the learning-library index: read even when it lies outside
                  the roots, and used as a completeness check (each entry ends on the list or in the unmatched section).

Identity is what is UNIQUE to a game:
  1. uuids found in two or more starter packs / templates (--templates) are removed (Cocos built-ins, shared templates).
  2. Packages are clustered into games. A J / F / D folder is one game (all its packages); a '待-X' folder is the same
     game as 'X'. Two packages are the same game when they share at least LINK_MIN uuids and those are at least
     LINK_SHARE of the smaller package (a source against a build counts only uuids some source holds: the editor
     generates new uuids for packed atlases). Two games built from one starter pack share only starter uuids, which
     step 1 removed. Project-root version folders that uuids cannot join are joined by game name; fragments
     (< FRAGMENT uuids) join their version folder's game, small old backups (< SMALL) the game they half belong to.
  3. A uuid found in two or more game clusters is removed; what is left is the game's identity. How many unique
     asset uuids are stored (<= ASSET_CAP) is chosen so the most packages of the game still match.
  A self-check matches every package read against the written list (RESULT: recognised / not recognised).
Matching rule: policy.match_legacy(). The output is a DRAFT ("frozen": false) until Saul has reviewed the table.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tiktok_finalize_steps import policy as P  # noqa: E402

ASSET_CAP = 400
LINK_MIN = 10          # uuids two packages must share to be one game ...
LINK_SHARE = 0.9       # ... and this share of the smaller package (W-L evidence: 0.7-0.95 give the same list)
FRAGMENT = 10          # a project-root cluster with fewer uuids is a fragment of the version folder it sits in
SMALL = 30             # a project-root cluster with fewer uuids, half of them in one other game, is that game
SKIP_DIRS = P.SKIP | {'node_modules', '.git', 'library', 'temp', 'local', 'wx-open', 'openDataContext'}
ANALYSIS = ('完结游戏共性分析',)
PROJECT_DIRS = ('交付', '交付包', 'delivery', 'deliveries', 'deliverables', 'exports', '工作工程', 'work', 'games',
                '本地预览', 'local-previews', 'BattleCars_TikTok_Test_20261022')
PROJECT_SKIP = re.compile(r'(?i:^(\.?candidates|docs|tooling|tools|wiki|audits|reviews)$|^skill)|Skill')
EMPTY_NAMES = {'untitled folder'}
WAIT = '待-'


def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def walk(root, max_depth):
    """Yield (dirpath, dirnames, filenames) below root, pruning tool/cache folders and depth."""
    base = str(root).count(os.sep)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith('._'))
        if dirpath.count(os.sep) - base >= max_depth:
            dirnames[:] = []
        yield dirpath, dirnames, sorted(filenames)


def native_dir_files(path):
    files = {}
    for p in Path(path).rglob('config*.json'):
        if p.is_file() and P.CONFIG.search(p.name) and not SKIP_DIRS & set(p.relative_to(path).parts):
            files[p.relative_to(path).as_posix()] = p.read_bytes()
    names = [p.relative_to(path).as_posix() for p in Path(path).glob('*')] + \
            [p.relative_to(path).as_posix() for p in Path(path).glob('cocos*/*')]
    return files, names


def candidates(folder, max_depth=4):
    """Every readable package of one game: [(path, kind_hint)] (zip, native dir, web build dir, project dir)."""
    out = []
    folder = Path(folder)
    if folder.is_file():
        return [(folder, 'zip')] if folder.suffix.lower() == '.zip' else []
    for dirpath, dirnames, filenames in walk(folder, max_depth):
        names = set(filenames)
        d = Path(dirpath)
        if {'game.js', 'game.json', 'project.config.json'} <= names:
            out.append((d, 'native_dir'))
            dirnames[:] = []
            continue
        if 'assets' in dirnames and ({'project.json', 'package.json'} & names):
            out.append((d, 'project_dir'))
            dirnames[:] = []
            continue
        if 'index.html' in names and 'assets' in dirnames and (d / 'assets' / 'main').is_dir():
            out.append((d, 'native_dir'))          # web-mobile / preview build: same bundle configs
            dirnames[:] = []
            continue
        for f in filenames:
            if f.lower().endswith('.zip') and not f.startswith('._'):
                out.append((d / f, 'zip'))
    return out


def identity(path, hint):
    if hint == 'zip':
        return P.identity_from_zip(path)
    if hint == 'native_dir':
        files, names = native_dir_files(path)
        out = P.identity_from_files(files)
        out['engine'] = P.engine_of_names(names)
        return out
    return P.identity_from_project(path)


def tiktok_zip(path):
    """A built TikTok package: game.json at the ZIP root or in its first-level folder."""
    try:
        with zipfile.ZipFile(path) as z:
            return any(n.split('/')[-1] == 'game.json' and n.count('/') <= 1 and '__MACOSX' not in n
                       for n in z.namelist())
    except (zipfile.BadZipFile, OSError, ValueError):
        return False


def has_tiktok_package(folder, max_depth=8):
    for dirpath, _dirs, filenames in walk(folder, max_depth):
        for f in filenames:
            if f.lower().endswith('.zip') and not f.startswith('._') and tiktok_zip(Path(dirpath) / f):
                return True
    return False


def skip_game_root_child(d):
    n = d.name
    return (not d.is_dir() or n.startswith(('.', '_', '！', '!')) or n.endswith('_StarterPack')
            or n == '启动包工坊' or n in EMPTY_NAMES)


def tag(kind, i):
    return kind if i == 0 else '%s%d' % (kind, i + 1)


def enumerate_units(delivered=(), finished=(), games_roots=(), project_roots=(), project_dirs=PROJECT_DIRS, log=print):
    """-> (units, roots). unit = {'label', 'path', 'where', 'forced': one folder is one game, 'depth'}."""
    units, roots = [], {}
    waiting = []      # game folders under a games root without a TikTok package (in progress, never delivered)
    for i, root in enumerate(delivered or ()):
        k = tag('J', i)
        roots[k] = str(root)
        for d in sorted(Path(root).iterdir()):
            if d.is_dir() and not d.name.startswith('.'):
                units.append({'label': '%s/%s' % (k, d.name), 'path': d, 'where': k, 'forced': True, 'depth': 4})
    for i, root in enumerate(finished or ()):
        k = tag('F', i)
        roots[k] = str(root)
        for d in sorted(Path(root).iterdir()):
            if d.name.startswith('.') or any(d.name.startswith(a) for a in ANALYSIS):
                continue
            if d.is_dir() or d.suffix.lower() == '.zip':
                units.append({'label': '%s/%s' % (k, d.name), 'path': d, 'where': k, 'forced': True, 'depth': 4})
    for i, root in enumerate(games_roots or ()):
        k = tag('D', i)
        roots[k] = str(root)
        kept = 0
        for d in sorted(Path(root).iterdir()):
            if skip_game_root_child(d):
                continue
            if not has_tiktok_package(d):
                waiting.append(d)
                continue
            kept += 1
            units.append({'label': '%s/%s' % (k, d.name), 'path': d, 'where': k, 'forced': True, 'depth': 6})
        log('games root %s: %d game folders with a TikTok package' % (root, kept))
    for i, root in enumerate(project_roots or ()):
        k = tag('P', i)
        roots[k] = str(root)
        for sub in project_dirs:
            base = Path(root) / sub
            if not base.exists():
                log('project root: %s missing' % base)
                continue
            children = [base] if base.is_dir() and not any(c.is_dir() for c in base.iterdir()) else \
                sorted(base.iterdir())
            for d in children:
                if d.name.startswith('.') or PROJECT_SKIP.search(d.name) or d.name in EMPTY_NAMES:
                    continue
                if d.is_dir() or d.suffix.lower() == '.zip':
                    label = '%s/%s' % (k, sub) if d == base else '%s/%s/%s' % (k, sub, d.name)
                    units.append({'label': label, 'path': d, 'where': k, 'forced': False, 'depth': 6})
    enumerate_units.waiting = waiting
    return units, roots


def read_index(paths):
    """Learning-library entries -> [{'no', 'name', 'name_en', 'path' (None when the index has none)}]."""
    out = []
    for path in paths or ():
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        for g in data if isinstance(data, list) else data.get('games', []):
            src = (g.get('en_source') or {}).get('path')
            out.append({'no': g.get('no'), 'name': g.get('name_cn') or g.get('title'), 'name_en': g.get('name_en'),
                        'self_made': g.get('self_made'), 'path': os.path.expanduser(src) if src else None,
                        'index': str(path)})
    return out


def _stamp(path):
    st = Path(path).stat()
    return [st.st_size if Path(path).is_file() else None, round(st.st_mtime, 3)]


def read_package(path, hint, cache=None):
    """One package -> node fields (uuid sets as sets). The optional cache is keyed by path + size + mtime."""
    stamp = _stamp(path)
    key = '%s|%s' % (hint, path)
    hit = (cache or {}).get(key)
    if hit and hit.get('stamp') == stamp:
        row = dict(hit)
    else:
        try:
            ident = identity(path, hint)
        except (zipfile.BadZipFile, OSError, ValueError, KeyError, RuntimeError, EOFError) as error:
            row = {'error': repr(error)[:200]}
        else:
            row = {'kind': ident.get('kind'), 'engine': ident.get('engine'),
                   'scenes': sorted(ident['scenes']), 'assets': sorted(ident['assets'])}
        row['stamp'] = stamp
        if cache is not None:
            cache[key] = dict(row)
    row.update(path=str(path), hint=hint, mtime=stamp[1], size=stamp[0])
    row['scenes'] = set(row.get('scenes') or ())
    row['assets'] = set(row.get('assets') or ())
    return row


def read_nodes(units, index=(), cache=None, log=print):
    """-> (nodes, index_rows). A node is one package; node['unit'] is its unit label, node['forced'] its game folder.
    Index sources outside every unit become their own node (where 'I'); inside a unit they are read with it."""
    nodes, seen = [], {}
    t0 = time.time()
    for n, u in enumerate(units, 1):
        found = candidates(u['path'], u['depth'])
        for path, hint in found:
            row = read_package(path, hint, cache)
            row.update(unit=u['label'], where=u['where'], forced=u['label'] if u['forced'] else None)
            seen[str(path)] = len(nodes)
            nodes.append(row)
        u['packages'] = len(found)
        if n % 25 == 0:
            log('  %d/%d units, %d packages, %.0fs' % (n, len(units), len(nodes), time.time() - t0))
    rows = []
    for e in index or ():
        r = dict(e, nodes=[])
        p = e['path']
        if not p:
            r['status'] = 'no_path'
        elif not Path(p).exists():
            r['status'] = 'missing'
        else:
            inside = [i for s, i in seen.items() if s == p or s.startswith(p.rstrip('/') + '/')]
            owner = next((u for u in units if p == str(u['path']) or p.startswith(str(u['path']) + '/')), None)
            if not inside:
                for path, hint in (candidates(p, 5) if Path(p).is_dir() else [(Path(p), 'zip')]):
                    row = read_package(path, hint, cache)
                    label = owner['label'] if owner else 'I/%s-%s' % (e['no'], e['name'])
                    row.update(unit=label, where=owner['where'] if owner else 'I',
                               forced=(owner['label'] if owner and owner['forced'] else label if not owner else None))
                    seen[str(path)] = len(nodes)
                    inside.append(len(nodes))
                    nodes.append(row)
            r['nodes'] = inside
            r['status'] = 'read'
        rows.append(r)
    log('read %d packages from %d units in %.0fs' % (len(nodes), len(units), time.time() - t0))
    return nodes, rows


def load_cache(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8')) if path else None
    except (OSError, ValueError):
        return {}


def save_cache(cache, path):
    if path and cache is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')


def template_uuids(templates, log=print, cache=None):
    """uuid -> set of starter packs / templates holding it (scene and asset metas, unpacked folders and pack ZIPs)."""
    found = defaultdict(set)
    for root in templates or ():
        root = Path(root)
        for top in ('已完成', '原创', 'projects', 'library', 'kit', 'sources', 'originals', 'production_inputs'):
            base = root / top
            if not base.is_dir():
                continue
            for pack in sorted(base.iterdir()):
                if not pack.is_dir():
                    continue
                had_dir = False
                for cand, hint in candidates(pack, max_depth=5):
                    if hint == 'zip' and had_dir:
                        continue
                    row = read_package(cand, hint, cache)
                    if 'error' in row:
                        continue
                    had_dir = had_dir or hint != 'zip'
                    for u in row['scenes'] | row['assets']:
                        found[u].add(top + '/' + pack.name)
        log('templates: %d uuids from %s' % (len(found), root))
    return found


# ---------------------------------------------------------------- clustering


class Groups:
    def __init__(self, n):
        self.up = list(range(n))

    def find(self, i):
        while self.up[i] != i:
            self.up[i] = self.up[self.up[i]]
            i = self.up[i]
        return i

    def join(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.up[max(a, b)] = min(a, b)
        return a != b


def folder_key(label):
    """'J/待-1乐观小明-Tansys（自制）' and 'J/1乐观小明-Tansys（自制）' are one game (parent decision 2026-10-29)."""
    head, _, name = label.partition('/')
    return head + '/' + (name[len(WAIT):] if name.startswith(WAIT) else name)


def own_uuids(nodes, multi_pack):
    return [set() if 'error' in n else (n['scenes'] | n['assets']) - multi_pack for n in nodes]


def shared_counts(own, max_owners=2000):
    inv = defaultdict(list)
    for i, s in enumerate(own):
        for u in s:
            inv[u].append(i)
    pairs = Counter()
    for ids in inv.values():
        if len(ids) > max_owners:
            continue
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                pairs[(ids[a], ids[b])] += 1
    return pairs


def cluster(nodes, multi_pack, link_min=LINK_MIN, link_share=LINK_SHARE):
    """Packages -> games. A J/F/D folder (and its 待- twin) is one game; two packages anywhere are one game when they
    share >= link_min uuids and those are >= link_share of the smaller package's uuids (starter uuids already removed).
    -> (groups: [[node index]], own, links: [(a, b, shared, share)])"""
    own = own_uuids(nodes, multi_pack)
    g = Groups(len(nodes))
    first = {}
    for i, n in enumerate(nodes):
        if n.get('forced'):
            k = folder_key(n['forced'])
            g.join(first.setdefault(k, i), i)
    links = []
    in_source = set().union(*[own[i] for i, n in enumerate(nodes) if n.get('kind') == 'source']) if nodes else set()
    for (a, b), c in shared_counts(own).items():
        ka, kb = nodes[a].get('kind'), nodes[b].get('kind')
        if ka != kb and 'source' in (ka, kb):
            # a build carries uuids the editor generates per build (packed atlases); they are in no source, so a
            # source and a build of the same game are compared on the uuids some source holds
            small = min(len(own[a] & in_source), len(own[b] & in_source)) or 1
        else:
            small = min(len(own[a]), len(own[b]))
        share = c / small
        if c >= link_min and share >= link_share:
            if g.join(a, b):
                links.append((a, b, c, round(share, 3)))
    out = defaultdict(list)
    for i in range(len(nodes)):
        out[g.find(i)].append(i)
    tidy(nodes, own, g, out)
    out = defaultdict(list)
    for i in range(len(nodes)):
        out[g.find(i)].append(i)
    return sorted(out.values(), key=lambda ids: min(ids)), own, links


GENERIC = {'deliverables', '历史备份', '核验', 'delivery', 'deliveries', 'exports', 'work', 'games', 'package', 'source'}


def name_key(label):
    k = re.sub(r'[^0-9a-z\u4e00-\u9fff]', '', unit_name(label).lower())
    return None if len(k) < 5 or k in GENERIC or unit_name(label) in GENERIC else k


def tidy(nodes, own, g, groups):
    """Version folders under a project root (P) that uuids could not join: a build whose uuids are all generated by
    the editor shares nothing with its source. (1) P-only clusters with the same game name are one game.
    (2) A P-only fragment with fewer than FRAGMENT uuids (an open-data sub-project, an empty baseline) joins the
    largest cluster that reads the same version folder."""
    info = []
    for root, ids in groups.items():
        forced = any(nodes[i].get('forced') and nodes[i]['where'][:1] != 'I' for i in ids)
        units = {nodes[i]['unit'] for i in ids}
        size = len(set().union(*[own[i] for i in ids]))
        info.append((root, forced, units, size))
    by_name = {}
    for root, forced, units, size in info:
        if forced:
            continue
        for u in units:
            k = name_key(u) if u[:1] == 'P' else None
            if k:
                if k in by_name:
                    g.join(by_name[k], root)
                else:
                    by_name[k] = root
    by_unit = defaultdict(list)
    for root, forced, units, size in info:
        for u in units:
            by_unit[u].append((size, root))
    sets = {root: set().union(*[own[i] for i in ids]) for root, ids in groups.items()}
    owner = defaultdict(set)
    for root, s in sets.items():
        for u in s:
            owner[u].add(root)
    for root, forced, units, size in info:
        if forced or size >= SMALL:
            continue
        near = Counter(r for u in sets[root] for r in owner[u] if g.find(r) != g.find(root))
        if near:
            r, c = near.most_common(1)[0]
            if c >= 0.5 * size:            # an old backup of another game (P/工作工程/历史备份)
                g.join(r, root)
                continue
        if size >= FRAGMENT:
            continue
        near = sorted((s, r) for u in units for s, r in by_unit[u] if g.find(r) != g.find(root))
        if near:
            g.join(near[-1][1], root)


# ---------------------------------------------------------------- entries

ORDER = {'J': 0, 'D': 1, 'F': 2, 'P': 3, 'I': 4}
VERSION_TAIL = re.compile(r'[-_ ](?:v\d|V\d|r\d|R\d|t\d|20\d{6}|Native|TikTok|Source|English|Cocos|Original|Baseline|'
                          r'Maintenance|Imported|Import|art|audio|gameplay|home|experience|source|finished|fixed|sound|'
                          r'loading|flow|motion|input|result|mobile|editable|StartupFix|ArtRedo|UI|HomeSkill|'
                          r'PreviewReview|BaselineImport|UploadReady|AndroidReview|OriginalBaseline|GardenUI|'
                          r'ModelPolish|ArtR\d|StartShield|LogicFix|repair|ReviveAd|TestAds|Growth|Independent|'
                          r'English-Source|WeChat|Wechat|最终版|完整|源码|测试|维护)')


def game_name(path):
    """'1段家祐-Nanas（自制）' -> 'Nanas'; '恢复线场_Cocos源码_.zip' -> '恢复线场'."""
    name = path.stem if path.is_file() else path.name
    name = re.sub(r'（自制）|\(自制\)|（自制）', '', name).strip()
    if path.is_file():
        return re.split(r'[_-](?:Cocos|CocosCreator|Source|源码)', name, maxsplit=1)[0].strip(' _-') or name
    if '-' in name:
        return name.rsplit('-', 1)[1].strip()
    return re.sub(r'^(新\d+_|\d(?=\D))', '', name) or name


def package_name(row):
    """Game name from a package file name (for entries whose folder name says nothing, e.g. P/deliverables)."""
    if not row:
        return '?'
    stem = re.sub(r'\.zip$', '', Path(row['path']).name, flags=re.I)
    return VERSION_TAIL.split(stem, maxsplit=1)[0].strip(' -_') or stem


def unit_name(label):
    """Readable game name of a unit label: J/D folders as game_name(); P children without their version tail."""
    where, _, rest = label.partition('/')
    last = rest.rsplit('/', 1)[-1]
    if where[:1] == 'P':
        base = re.sub(r'\.zip$', '', last, flags=re.I)
        base = re.sub(r'^\d+-', '', base)
        return VERSION_TAIL.split(base, maxsplit=1)[0].strip(' -_') or base
    if where[:1] == 'I':
        return rest.split('-', 1)[-1]
    return game_name(Path(last))


def primary(rows):
    ok = [r for r in rows if 'error' not in r]
    for kind in ('source', 'native'):
        pick = sorted((r for r in ok if r.get('kind') == kind and r['scenes']), key=lambda r: r['mtime'])
        if pick:
            return pick[-1]
    return sorted(ok, key=lambda r: r['mtime'])[-1] if ok else None


def board_guess(labels, index_rows):
    made = [r.get('self_made') for r in index_rows if r.get('self_made') is not None]
    if any('自制' in l for l in labels):
        return 'remake', False
    if made:
        return ('remake' if made[0] else 'localize'), False
    if any(l.split('/', 1)[0][:1] in 'JD' for l in labels):
        return 'localize', False
    name = unit_name(labels[0])
    return ('remake' if name[:1].isascii() and name[:1].isalpha() else 'localize'), True


def stored_size(ids, nodes, uniq_s, uniq_a, asset_cap=ASSET_CAP):
    """How many of the ranked unique asset uuids to store. policy.match_legacy needs >= ASSET_MIN hits and
    >= ASSET_SHARE of what is stored, so storing 400 makes a small old package of the same game unrecognisable.
    Pick the size that lets the most packages of this game match (ties: the larger size)."""
    sizes = sorted({k for k in (asset_cap, 300, 200, 150, 100, 60, 30, 15) if k < len(uniq_a)} | {min(asset_cap, len(uniq_a))},
                   reverse=True)
    scenes = set(uniq_s)
    best = (-1, 0)
    for k in sizes:
        top = set(uniq_a[:k])
        need = max(P.ASSET_MIN, P.ASSET_SHARE * k)
        hit = sum(1 for i in ids if (nodes[i]['scenes'] & scenes) or len(nodes[i]['assets'] & top) >= need)
        if hit > best[0]:
            best = (hit, k)
    return best[1]


def build_entries(nodes, groups, own, tmpl, index_rows, units, asset_cap=ASSET_CAP):
    """One entry per game cluster (clusters with no readable uuid and no J/F/D folder are not games)."""
    multi_pack = {u for u, p in tmpl.items() if len(p) > 1}
    node_index = defaultdict(list)
    for r in index_rows:
        for i in r['nodes']:
            node_index[i].append(r)
    clusters = []
    for ids in groups:
        labels = sorted({nodes[i]['unit'] for i in ids}, key=lambda l: (ORDER.get(l[:1], 9), l))
        uu = set().union(*[own[i] for i in ids])
        if not uu and not any(nodes[i].get('forced') for i in ids):
            continue
        idx = {r['no']: r for i in ids for r in node_index[i]}
        clusters.append({'ids': ids, 'labels': labels, 'own': uu, 'index': [idx[k] for k in sorted(idx, key=str)]})
    owners = Counter(u for c in clusters for u in c['own'])
    by_games = {u for u, k in owners.items() if k > 1}
    entries = []
    for c in clusters:
        rows = [nodes[i] for i in c['ids']]
        ok = [r for r in rows if 'error' not in r]
        scenes = set().union(*[r['scenes'] for r in ok]) if ok else set()
        assets = set().union(*[r['assets'] for r in ok]) if ok else set()
        read = scenes | assets
        uniq_s = sorted(scenes - multi_pack - by_games)
        freq = Counter(u for i in c['ids'] for u in own[i])
        uniq_a = sorted(assets - multi_pack - by_games - scenes, key=lambda u: (-freq[u], u))
        keep = stored_size(c['ids'], nodes, uniq_s, uniq_a, asset_cap)
        main = primary(rows)
        board, guessed = board_guess(c['labels'], c['index'])
        names = [r['name'] for r in c['index'] if r.get('name')]
        folder_names = []
        for l in c['labels']:
            n = unit_name(l)
            if n not in folder_names:
                folder_names.append(n)
        c['entry'] = {
            'name': folder_names[0] if c['labels'][0][:1] in 'JDF' else names[0] if names else
            package_name(main) if folder_names[0] in GENERIC else folder_names[0],
            'names': folder_names[:12], 'index_games': ['%s %s' % (r['no'], r['name']) for r in c['index']],
            'folder': c['labels'][0], 'folders': c['labels'],
            'uuids_read': len(read), 'uuids_in_starter_packs': len(read & multi_pack),
            'uuids_shared_with_games': len(read & by_games - multi_pack),
            'scene_uuids_read': len(scenes), 'packages_without_cocos_data': sum(1 for r in ok if not r.get('kind')),
            'board': board, 'board_guessed': guessed,
            'engine': (main or {}).get('engine') or next((r['engine'] for r in ok if r.get('engine')), None),
            'scene_uuids': uniq_s,
            'asset_uuids': sorted(uniq_a[:keep]),
            'asset_uuids_total': len(uniq_a),
            'scene_uuids_shared': sorted(scenes & (multi_pack | by_games)),
            'packages_read': len(ok),
            'packages_unreadable': [r['path'] for r in rows if 'error' in r],
            'last_package': None if not main else {
                'path': main['path'], 'kind': main.get('kind'),
                'sha256': file_sha(main['path']) if Path(main['path']).is_file() else None,
                'date': time.strftime('%Y-%m-%d', time.localtime(main['mtime']))},
        }
        entries.append(c['entry'])
    empty = [u['label'] for u in units if u['forced'] and not u.get('packages')]
    entries = [e for e in entries if e['packages_read'] or not set(e['folders']) <= set(empty)]
    return entries, clusters, by_games


def identifiable(entry):
    return bool(entry['scene_uuids']) or len(entry['asset_uuids']) >= P.ASSET_MIN


def self_check(nodes, clusters, own, entries):
    """Every package with readable uuids, matched against the generated list: does it hit its own game's entry?"""
    legacy = {'games': entries}
    listed = {id(e) for e in entries}
    miss, total, wrong, blind = [], 0, [], []
    for c in clusters:
        e = c.get('entry')
        if e is None or id(e) not in listed:
            continue
        for i in c['ids']:
            n = nodes[i]
            if not own[i]:
                if n.get('kind'):
                    blind.append({'path': n['path'], 'entry': e['folder'], 'kind': n['kind']})
                continue
            total += 1
            hits = [h['folder'] for h in P.match_legacy(n['scenes'], legacy, n['assets'])]
            if e['folder'] not in hits:
                miss.append({'path': n['path'], 'entry': e['folder'], 'hits': hits})
            elif len(hits) > 1:
                wrong.append({'path': n['path'], 'entry': e['folder'], 'hits': hits})
    return {'packages': total, 'not_recognised': miss, 'also_matches_other_games': wrong,
            'no_game_uuid': blind}


# ---------------------------------------------------------------- whole run


def name_hint(row, entries):
    """An index entry without en_source.path: name the list entries whose folders carry its Chinese or English name."""
    keys = [k for k in (row.get('name'), row.get('name_en')) if k]
    keys = [re.sub(r'[^0-9a-z\u4e00-\u9fff]', '', re.split(r'[（(]', k)[0].lower()) for k in keys]
    keys = [k for k in keys if len(k) >= 3]
    hits = []
    for e in entries:
        texts = e['folders'] + e['names'] + [(e['last_package'] or {}).get('path') or '']
        flat = ' '.join(re.sub(r'[^0-9a-z\u4e00-\u9fff/]', '', f.lower()) for f in texts)
        if any(k in flat for k in keys):
            hits.append('`%s`%s' % (e['folder'], '' if identifiable(e) else '（认不出）'))
    return '、'.join(hits)


def build(delivered=(), finished=(), games_roots=(), project_roots=(), index=(), templates=(), previous=None,
          cache=None, log=print, link_min=LINK_MIN, link_share=LINK_SHARE, project_dirs=PROJECT_DIRS):
    units, roots = enumerate_units(delivered, finished, games_roots, project_roots, project_dirs, log)
    index_rows = read_index(index)
    for p in index or ():
        roots['I' if len(index) == 1 else 'I%d' % (list(index).index(p) + 1)] = str(p)
    nodes, index_rows = read_nodes(units, index_rows, cache, log)
    tmpl = template_uuids(templates, log, cache)
    multi_pack = {u for u, p in tmpl.items() if len(p) > 1}
    groups, own, links = cluster(nodes, multi_pack, link_min, link_share)
    entries, clusters, by_games = build_entries(nodes, groups, own, tmpl, index_rows, units)
    check = self_check(nodes, clusters, own, entries)
    of_node = {}
    for c in clusters:
        for i in c['ids']:
            of_node[i] = c.get('entry')
    listed = {id(e) for e in entries}
    for r in index_rows:
        hits = sorted({of_node[i]['folder'] for i in r['nodes'] if of_node.get(i) and id(of_node[i]) in listed})
        r['entry'] = hits[0] if hits else None
        r['entry_identifiable'] = bool(hits) and identifiable(next(e for e in entries if e['folder'] == hits[0]))
        if r['status'] == 'no_path':
            r['hint'] = name_hint(r, entries)
    old = set()
    if previous and Path(previous).is_file():
        for g in json.loads(Path(previous).read_text(encoding='utf-8')).get('games', []):
            old.add(g.get('folder'))
    for e in entries:
        e['in_draft72'] = bool(old & set(e['folders']))
    packs = defaultdict(set)
    for u, owners in tmpl.items():
        for o in owners:
            packs[o].add(u)
    view = {'games': entries}
    same_origin = sorted((p, [h['folder'] for h in P.match_legacy(us, view, us)]) for p, us in packs.items())
    same_origin = [[p, f] for p, f in same_origin if f]
    in_progress = []
    for d in getattr(enumerate_units, 'waiting', []):
        s, a = set(), set()
        for path, hint in candidates(d, 4):
            row = read_package(path, hint, cache)
            s |= row['scenes']
            a |= row['assets']
        hits = [h['folder'] for h in P.match_legacy(s, view, a)]
        in_progress.append({'folder': str(d), 'name': d.name, 'legacy_match': hits})
    scenes = set().union(*(n['scenes'] for n in nodes)) if nodes else set()
    empty = [u['label'] for u in units if not u.get('packages')]
    stats = {
        'roots': roots, 'project_dirs': list(project_dirs),
        'units': dict(Counter(u['where'] for u in units)), 'units_without_packages': empty,
        'packages': len(nodes), 'packages_by_kind': {str(k): v for k, v in Counter(n.get('kind') for n in nodes).items()},
        'link_min': link_min, 'link_share': link_share, 'fragment': FRAGMENT, 'small': SMALL, 'links': len(links),
        'template_uuids': len(tmpl), 'template_uuids_multi_pack': len(multi_pack),
        'shared_uuids': len(multi_pack | by_games), 'uuids_in_two_or_more_games': len(by_games),
        'template_packs': len(packs), 'template_packs_matching_legacy': same_origin,
        'game_scene_uuids': len(scenes), 'game_scene_uuids_in_starter_packs': len(scenes & set(tmpl)),
        'game_scene_uuids_multi_pack': len(scenes & multi_pack), 'game_scene_uuids_shared_games': len(scenes & by_games),
        'self_check': {'packages': check['packages'], 'not_recognised': len(check['not_recognised']),
                       'also_matches_other_games': len(check['also_matches_other_games']),
                       'packages_without_game_uuid': len(check['no_game_uuid'])},
        'index': [{k: r.get(k) for k in ('no', 'name', 'name_en', 'path', 'status', 'entry', 'entry_identifiable', 'hint')}
                  for r in index_rows],
        'in_progress_folders': len(in_progress),
        'in_progress_matching_legacy': [x for x in in_progress if x['legacy_match']],
        'draft': str(previous) if previous else None, 'in_draft72': sum(1 for e in entries if e['in_draft72']),
    }
    return entries, stats, {'check': check, 'links': links, 'nodes': nodes, 'clusters': clusters}


# ---------------------------------------------------------------- output


def write_json(entries, stats, path):
    data = {
        'name': 'TikTokPlatformKit legacy games', 'frozen': False, 'version': 2,
        'generated': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'generator': 'make_legacy_list.py',
        'unlisted_policy': 'new',
        'match_rule': 'legacy when a unique scene uuid matches, or at least %d unique asset uuids (and %d%% of the '
                      'stored ones) match; uuids found in two or more starter packs or in two or more listed games '
                      'never count. Packages of one game in several folders are one entry (folders).'
                      % (P.ASSET_MIN, int(P.ASSET_SHARE * 100)),
        'stats': stats, 'games': []}
    head = json.dumps(data, ensure_ascii=False, indent=1)
    assert head.endswith('"games": []\n}')
    body = ',\n'.join('  ' + json.dumps(e, ensure_ascii=False, sort_keys=True) for e in entries)
    text = head[:-len('[]\n}')] + '[\n' + body + '\n ]\n}\n'
    assert json.loads(text)['games'] == json.loads(json.dumps(entries, ensure_ascii=False))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding='utf-8')
    return data


def unlisted_reason(e):
    """Why an entry cannot identify its game (Chinese, for Saul)."""
    if not e['packages_read']:
        why = '源码和包都缺：文件夹里没有游戏包'
    elif e['packages_read'] == e['packages_without_cocos_data']:
        why = '只有启动包或非 Cocos 的 ZIP，读不出场景和资源'
    elif not e['scene_uuids_read'] and e['uuids_read'] == e['uuids_in_starter_packs']:
        why = '包里没有 Cocos 场景，读到的 %d 个 uuid 全是启动包里也有的（Cocos 内置资源）' % e['uuids_read']
    elif e['uuids_read'] == e['uuids_in_starter_packs']:
        why = '读到的 %d 个 uuid 全在两个以上启动包里（用启动包或别的游戏做的底子，自己没加新资源）' % e['uuids_read']
    else:
        why = '没有独有 uuid：%d 个里 %d 个在两个以上启动包里、%d 个和别的名单游戏共用' % (
            e['uuids_read'], e['uuids_in_starter_packs'], e['uuids_shared_with_games'])
    if e['packages_unreadable']:
        why += '；另有 %d 个包打不开' % len(e['packages_unreadable'])
    return why


def folder_cell(e, limit=3):
    f = ['`%s`' % x for x in e['folders'][:limit]]
    more = len(e['folders']) - limit
    return '、'.join(f) + ('等 %d 个文件夹' % len(e['folders']) if more > 0 else '')


def games_in(e):
    """Different games merged into one entry: the J/F/D folders (one folder = one game) of the entry."""
    seen = []
    for l in e['folders']:
        if l[:1] in 'JDF' and folder_key(l) not in [folder_key(s) for s in seen]:
            seen.append(l)
    return seen


def write_review(entries, stats, path, json_path, check=None):
    eng = {2: '2.4', 3: '3.x', None: '?'}
    ok = [e for e in entries if identifiable(e)]
    bad = [e for e in entries if not identifiable(e)]
    weak = [e for e in ok if not e['scene_uuids']]
    new = [e for e in entries if not e['in_draft72']]
    merged = [e for e in entries if len(games_in(e)) > 1 and not all(folder_key(l) == folder_key(games_in(e)[0])
                                                                       for l in games_in(e))]
    idx = stats.get('index') or []
    idx_on = [r for r in idx if r.get('entry') and r.get('entry_identifiable')]
    idx_off = [r for r in idx if r not in idx_on]
    roots = stats['roots']
    names = {'J': '已交付游戏，每个子文件夹算一款', 'F': '成功完结游戏，每个 ZIP 或子文件夹算一款',
             'D': '下载里的游戏文件夹，只算里面有 TikTok 包（ZIP 根目录或第一层有 game.json）的文件夹；'
                  '跳过 *_StarterPack、启动包工坊、!玩法来源、_ 开头和 ！ 开头的文件夹',
             'P': '另一个项目根目录，读 %s 下面的每个子文件夹和 ZIP（版本文件夹按 uuid 归到游戏，不按文件夹算）'
                  % '、'.join(stats.get('project_dirs') or ()),
             'I': '游戏学习库索引，每条的 en_source.path 都读，并逐条对照'}
    sc = stats.get('self_check') or {}
    lines = [
        '# v7.7 遗留游戏名单（第二版草稿，等 Saul 过目，还没冻结）', '',
        '**摘要**：名单上 %d 款游戏，其中 %d 款能认出、%d 款认不出（认不出的出包时按新游戏处理）。比 72 款的第一版草稿'
        '新增 %d 款。学习库索引 %d 款：%d 款在名单上能认出，%d 款认不出或索引没写源码路径（见\"学习库对照\"）。'
        '另有 %d 条是几款不同的游戏共用同一套 uuid，只能合成一条（见\"几款游戏共用一套 uuid\"）；'
        '%d 个正在做的游戏文件夹会被认成旧游戏，要先写新游戏标记（见\"正在做、还没交付的游戏\"）。'
        % (len(entries), len(ok), len(bad), len(new), len(idx), len(idx_on), len(idx_off), len(merged),
           len(stats.get('in_progress_matching_legacy') or [])), '',
        '生成：`make_legacy_list.py`（只读扫描），%s。草稿 JSON：`%s`（`\"frozen\": false`）。'
        '共读了 %d 个包（源码 ZIP、上传包 ZIP、解开的工程、构建产物和网页预览，只读 bundle config 和 .meta）。'
        % (time.strftime('%Y-%m-%d %H:%M'), json_path, stats['packages']), '',
        '扫描范围（文件夹一栏的前缀就是下面的字母）：', '']
    for k, v in roots.items():
        lines.append('- `%s` = `%s`：%s' % (k, v, names.get(k[:1], '')))
    lines += ['',
              '名单上的游戏按旧游戏出包：只补\"缺了一定坏、补上不冲突\"的件，自写的启动、广告、存档代码只警告。'
              '**名单外的游戏一律按新游戏处理**（Q1 已定，包括正在做、还没交付的游戏）。空文件夹和 `untitled folder` '
              '不算游戏，`待-` 文件夹和去掉 `待-` 的同名文件夹算同一款（parent 已定）。', '',
              '## 为什么只看场景 uuid 不够', '',
              '启动包之间大量共用场景 uuid：这次读到的游戏场景 uuid 共 %d 个，其中 %d 个在启动包里也有、%d 个在两个以上'
              '启动包里（例如 duo-jump 模板的场景 `a7aba472` 出现在 11 个启动包里，Nanas、SimonsScrew 都是从它做的）。'
              '如果只按场景 uuid 认身份，用同一个启动包新做的游戏会被认成旧游戏，躲开新游戏的拦截。'
              '所以名单只存本游戏独有的场景 uuid 和资源 uuid（去掉在两个以上启动包里、或在两款以上名单游戏里出现的），'
              '出包时看独有 uuid 是否重合：独有场景 uuid 重合 1 个，或独有资源 uuid 重合至少 %d 个且占名单所存的 %d%% 以上，'
              '才算旧游戏。本次读到启动包/模板 uuid %d 个（其中 %d 个在两个以上启动包里），排除的共用 uuid 共 %d 个。'
              % (stats.get('game_scene_uuids', 0), stats.get('game_scene_uuids_in_starter_packs', 0),
                 stats.get('game_scene_uuids_multi_pack', 0), P.ASSET_MIN, int(P.ASSET_SHARE * 100),
                 stats['template_uuids'], stats['template_uuids_multi_pack'], stats['shared_uuids']), '',
              '## 同一款游戏在几个文件夹里怎么合并', '',
              '第一版只扫了 J 和 F，又把\"在两款以上游戏里出现的 uuid\"全部去掉，所以一款游戏的版本放在两个文件夹里，'
              '两边共有的 uuid 都被去掉，游戏就认不出了。这一版先把包归成游戏，再去共用 uuid：', '',
              '1. J、F、D 的一个文件夹算一款游戏（文件夹里所有的包都归它）；`待-X` 和 `X` 算同一款。',
              '2. 任意两个包共有至少 %d 个 uuid，并且占较小那个包的 %d%% 以上，就算同一款游戏。源码和构建产物相比时，'
              '只比\"在某个源码里出现过的 uuid\"，因为构建时编辑器会给合图生成新的 uuid，源码里没有。'
              '在两个以上启动包里的 uuid 先去掉，所以两款用同一个启动包做的游戏不会因为启动包的 uuid 合到一起。'
              % (stats['link_min'], int(stats['link_share'] * 100)),
              '3. P 下面没法用 uuid 归到一起的版本文件夹，游戏名相同的算一款（例如 `Double-Jump-Duo-v19-Cocos-Source` '
              '和 `Double-Jump-Duo-v13-Native-Test`：构建产物的 uuid 全是编辑器生成的，和源码对不上）；'
              '只有不到 %d 个 uuid 的零碎包（排行榜子工程、空的基线工程）归到同一个版本文件夹里最大的那款游戏；'
              '不到 %d 个 uuid、一半以上和另一款游戏共有的旧备份（`P/工作工程/历史备份`）归到那款游戏。'
              % (stats.get('fragment', FRAGMENT), stats.get('small', SMALL)),
              '4. 最后再按\"在两款以上游戏里出现的 uuid 不算\"去掉共用的，剩下的就是这款游戏的身份。', '',
              '阈值的依据（`briefs/out/W-L/evidence/threshold.md` 有完整数字）：不同游戏的包之间共有比例最高只有 20%%'
              '（MabelsBus 和 Nanas、剪刀达人 和 气球快跑），同一款游戏的包绝大多数在 90%% 以上。取 50%% 会把 MabelsBus、'
              'Nanas、BusQueue 三款合成一条；取 70%%、80%% 会把 StarConnect 并进 地铁换乘 那一条；90%% 和 95%% 结果相同。'
              '共有个数下限取 5、10、20 结果相同，用 %d 是为了不让只共有几个 uuid 的偶然重合连起来。这次用 %d%%。'
              % (stats['link_min'], int(stats['link_share'] * 100)), '',
              '自检：名单生成后，把读到的每个有独有 uuid 的包拿来按出包时的规则匹配，%d 个包里 %d 个认成了自己那款游戏，'
              '%d 个认不出（都是旧候选版、原版中文源码或零碎子工程，见文末），%d 个同时认成别的游戏。另有 %d 个包里'
              '一个独有 uuid 都没有（全是启动包或底子的 uuid），这些包要靠同一款游戏的工程才能认出。'
              % (sc.get('packages', 0), sc.get('packages', 0) - sc.get('not_recognised', 0), sc.get('not_recognised', 0),
                 sc.get('also_matches_other_games', 0), sc.get('packages_without_game_uuid', 0)), '']
    lines += ['## 新增的游戏（%d 款，第一版草稿里没有）' % len(new), '',
              '| # | 游戏 | 学习库 | 引擎 | 能否认出 | 独有 uuid（场景 + 资源） | 文件夹 |', '|---|---|---|---|---|---|---|']
    for i, e in enumerate(new, 1):
        lines.append('| %d | %s | %s | %s | %s | %d + %d | %s |' % (
            i, e['name'], '、'.join(e['index_games']) or '—', eng.get(e['engine'], '?'),
            '能' if identifiable(e) else '**认不出**', len(e['scene_uuids']), e['asset_uuids_total'],
            '、'.join('`%s`' % f for f in e['folders'])))
    lines.append('')
    if merged:
        lines += ['## 几款游戏共用一套 uuid（合成一条，%d 条）' % len(merged), '',
                  '这些是不同的游戏，但一款是拿另一款做底子做的，或者文件夹里放着底子的副本（`_底子`、`_base`、'
                  '`底子_*`、`原版源码_*`），uuid 几乎完全一样。分成两条的话，共用的 uuid 两边都会被去掉，两款都认不出；'
                  '合成一条，两款都按旧游戏处理。拿其中任何一款当底子做新游戏，起项目都必须跑 `tiktok_finalize.py init`。', '']
        for e in merged:
            lines.append('- %s：%s' % (' + '.join('`%s`' % l for l in games_in(e)), '、'.join(e['index_games']) or '学习库里没有'))
        lines.append('')
    lines += ['## 认不出或对不上的游戏（%d 款，出包时会按新游戏处理）' % len(bad), '']
    if bad:
        lines += ['| 游戏 | 文件夹 | 读到的包 | 原因 |', '|---|---|---|---|']
        for e in bad:
            why = unlisted_reason(e)
            if 'Hoots' in e['folder']:
                why += '。找过：这个文件夹里只有两个 v17 ZIP（上传包和\"源代码与资源\"），源码 ZIP 里是 native/ 和 web/ 两份' \
                       '构建产物加 docs/，没有 .fire / .scene；两个下载根目录和项目根目录里也没有别的 Hoots 工程'
            lines.append('| %s | %s | %d | %s |' % (e['name'], folder_cell(e, 6), e['packages_read'], why))
    else:
        lines.append('没有。')
    lines.append('')
    lines += ['## 学习库对照（索引 %d 款）' % len(idx), '',
              '索引里每一款的 en_source.path 都读过。%d 款在名单上能认出；下面是其余的：' % len(idx_on), '']
    if idx_off:
        lines += ['| # | 游戏 | en_source.path | 结果 |', '|---|---|---|---|']
        for r in idx_off:
            if r['status'] == 'no_path':
                res = '索引里没写源码路径，按游戏名在名单里找：%s' % (r.get('hint') or '没找到')
            elif r['status'] == 'missing':
                res = '路径不存在'
            elif r.get('entry'):
                res = '归到 `%s`，但这一条认不出' % r['entry']
            else:
                res = '读到的包里没有游戏 uuid'
            lines.append('| %s | %s | %s | %s |' % (r['no'], r['name'], '`%s`' % r['path'] if r['path'] else '—', res))
    else:
        lines.append('没有。')
    lines.append('')
    if weak:
        lines += ['## 只能靠资源 uuid 认的游戏（%d 款，场景 uuid 和启动包或别的游戏共用）' % len(weak), '',
                  '这些游戏的新版本照样能认出来（资源 uuid 跟着工程复制走）。拿它们当底子做新游戏时，起项目必须跑 '
                  '`tiktok_finalize.py init` 写新游戏标记，否则会被认成旧游戏。', '']
        lines += ['- %s（`%s`，独有资源 uuid %d 个，名单存了 %d 个）' % (e['name'], e['folder'], e['asset_uuids_total'],
                                                            len(e['asset_uuids'])) for e in weak]
        lines.append('')
    same = stats.get('template_packs_matching_legacy') or []
    if same:
        lines += ['## 和名单游戏同源的启动包（%d 个，共查了 %d 个启动包）' % (len(same), stats.get('template_packs', 0)), '',
                  '这些启动包本身就是名单上某款游戏的原版源码或底子，按上面的规则会被认成那款旧游戏。用它们新做游戏时，'
                  '起项目必须跑 `tiktok_finalize.py init` 写新游戏标记（标记只能往严里改，写了就按新游戏），'
                  '这一步由 W-D 接进起项目检查。其余启动包都认不成旧游戏。', '']
        lines += ['- `%s` → %s' % (p, '、'.join('`%s`' % f for f in folders)) for p, folders in same]
        lines.append('')
    wip = stats.get('in_progress_matching_legacy') or []
    if wip:
        lines += ['## 正在做、还没交付的游戏里会被认成旧游戏的（%d 个，共查了 %d 个没有 TikTok 包的游戏文件夹）'
                  % (len(wip), stats.get('in_progress_folders', 0)), '',
                  '这些文件夹用名单上的游戏做了底子（或者就是名单上那款游戏的工作副本）。Q1 定了正在做的游戏算新游戏，'
                  '但这些工程里还没有新游戏标记，出包时会按名单认成旧游戏。要按新游戏做的，先在工程里跑一次 '
                  '`python3 remake-core/scripts/tiktok_finalize.py init --project <工程> --board remake`。', '']
        lines += ['- `%s` → 认成 %s' % (x['name'], '、'.join('`%s`' % f for f in x['legacy_match'])) for x in wip]
        lines.append('')
    lines += ['## 全部游戏（%d 款）' % len(entries), '',
              '| # | 游戏 | 文件夹 | 板块 | 引擎 | 名单取自哪个包（最新的一个） | 独有 uuid（场景 + 资源） | 读了几个包 |',
              '|---|---|---|---|---|---|---|---|']
    for i, e in enumerate(entries, 1):
        lp = e['last_package'] or {}
        pkg = '—' if not lp.get('path') else '`%s`（%s，%s）' % (
            Path(lp['path']).name, {'source': '源码', 'native': '上传包/产物'}.get(lp.get('kind'), '非 Cocos 包'),
            lp.get('date', '?'))
        lines.append('| %d | %s%s | %s | %s%s | %s | %s | %d（%d + %d） | %d |' % (
            i, e['name'], '' if e['in_draft72'] else '（新增）', folder_cell(e), e['board'],
            '（猜）' if e['board_guessed'] else '', eng.get(e['engine'], '?'), pkg,
            len(e['scene_uuids']) + e['asset_uuids_total'], len(e['scene_uuids']), e['asset_uuids_total'],
            e['packages_read']))
    lines += ['', '\"板块\"一栏：文件夹名带（自制）的算重塑；学习库写了是否自制的按学习库；J、D 里其余的算英化；'
                  '其他按名字猜（标了\"猜\"）。板块只写进记录，不影响新旧判定。', '']
    if check and check['not_recognised']:
        lines += ['## 自检认不出的包（%d 个）' % len(check['not_recognised']), '',
                  '这些包属于名单上的游戏，但它自己的独有 uuid 不够（旧候选版、原版中文源码、零碎子工程）。'
                  '同一款游戏最新的工程和上传包都能认出。', '']
        lines += ['- `%s` → 属于 `%s`' % (m['path'], m['entry']) for m in check['not_recognised']]
        lines.append('')
    lines += ['## 要 Saul 确认', '',
              '1. 上面\"全部游戏\"表就是要冻结的名单吗？表里认不出的、表外的游戏以后都按新游戏处理'
              '（漏掉的旧游戏只能等下一次 Skill 发版补，会话自己不能加）。',
              '2. \"认不出或对不上\"的游戏：补一个能读的源码包再生成，还是就按新游戏处理。',
              '3. \"几款游戏共用一套 uuid\"合成一条可以吗？（分开的话这几款都会认不出。）', '']
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text('\n'.join(lines), encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--delivered', action='append', default=[], help='J: 已交付游戏文件夹（可重复）')
    ap.add_argument('--finished', action='append', default=[], help='F: 成功完结游戏文件夹（可重复）')
    ap.add_argument('--games-root', action='append', default=[], help='D: 游戏文件夹所在的下载根目录（可重复）')
    ap.add_argument('--project-root', action='append', default=[], help='P: 项目根目录（可重复）')
    ap.add_argument('--project-dirs', help='P 下面要读的子文件夹，逗号分隔（默认 %s）' % ','.join(PROJECT_DIRS))
    ap.add_argument('--index', action='append', default=[], help='I: 学习库 索引.json（可重复）')
    ap.add_argument('--templates', action='append', default=[], help='启动包工坊（启动包/模板，用来排除共用 uuid）')
    ap.add_argument('--previous', help='上一版名单 JSON（标出新增的游戏）')
    ap.add_argument('--cache', help='包读取缓存（只放 scratch；按路径 + 大小 + 修改时间）')
    ap.add_argument('--link-min', type=int, default=LINK_MIN)
    ap.add_argument('--link-share', type=float, default=LINK_SHARE)
    ap.add_argument('--out-json', required=True)
    ap.add_argument('--out-review', required=True)
    ap.add_argument('--out-check', help='自检明细 JSON（可选）')
    args = ap.parse_args(argv)
    log = lambda m: print(time.strftime('%H:%M:%S'), m, file=sys.stderr, flush=True)
    cache = load_cache(args.cache)
    dirs = tuple(x for x in args.project_dirs.split(',') if x) if args.project_dirs else PROJECT_DIRS
    entries, stats, extra = build(args.delivered, args.finished, args.games_root, args.project_root, args.index,
                                  args.templates, args.previous, cache, log, args.link_min, args.link_share, dirs)
    save_cache(cache, args.cache)
    write_json(entries, stats, args.out_json)
    write_review(entries, stats, args.out_review, args.out_json, extra['check'])
    if args.out_check:
        Path(args.out_check).write_text(json.dumps(extra['check'], ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'games': len(entries), 'unidentifiable': sum(1 for e in entries if not identifiable(e)),
                      'new_since_draft': sum(1 for e in entries if not e['in_draft72']),
                      'self_check': stats['self_check'], 'packages': stats['packages']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
