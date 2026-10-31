"""New game or legacy game (design D77 section 2).

Identity = the Cocos scene uuids: assets/**/*.fire.meta / *.scene.meta in a project; in a build, the `scenes`
section of every bundle config (2.4: compressed 22-char uuids or indexes into `uuids`; 3.x: indexes) plus the launch
scene. Copying a project into a new version folder keeps the uuids, so a new version of a listed game stays legacy.

decide():
    marker <project>/.tiktok-kit/policy.json says new          -> new   (a marker can only make things stricter)
    scene uuids overlap an entry of the frozen LEGACY_GAMES.json -> legacy
    the project folder is exactly an entry's recorded last source -> legacy (v7.7.5, 总表 B27)
    v7.8 (总表 B27, second half): the sub-asset uuids of the project's .meta files (subMetas: sprite frames, ...) are
      read too, because the list was built from packages, whose config.json holds them. They only count when the two
      rules above found nothing, and never for a game started from a workshop starter pack (many packs carry the
      original source of a listed English game, so the same uuids are in them):
        the project sits in / next to a starter pack (starter_trace)   -> new
        the caller says --board remake                                 -> new (a remake is never legacy by
                                                                          sub-asset uuids alone; v7.7.5 said new too)
        otherwise (board localize or not given)                        -> legacy (剪刀达人 v30 moved out of its folder)
      tiktok_finalize `source` writes the new-game marker in the first two cases (`auto_new`), so every later
      caller without a board (writers, art_receipt, logic_check) agrees without the session having run init.
    anything else (not listed, no uuid readable)                -> new (Saul Q1, 2026-10-29: every game not on the
                                                                   frozen list is new, including games in progress)
"""
import json
import re
import time
import zipfile
from pathlib import Path, PurePosixPath

from . import KIT_DIR

LEGACY = KIT_DIR / 'LEGACY_GAMES.json'
MARKER = Path('.tiktok-kit') / 'policy.json'
B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
SKIP = {'library', 'temp', 'build', 'local', 'node_modules', '.git', '__MACOSX', 'profiles', '.tiktok-kit'}
CONFIG = re.compile(r'(^|/)config(\.[0-9a-f]{5,})?\.json$')


def decode_uuid(value):
    """Cocos compressed uuid (22 chars: 2 hex + 20 base64) -> dashed lowercase uuid; dashed input passes through."""
    if not isinstance(value, str):
        return None
    value = value.split('@', 1)[0]
    if UUID.match(value.lower()):
        return value.lower()
    if len(value) == 32 and re.fullmatch(r'[0-9a-fA-F]{32}', value):
        h = value.lower()
    elif len(value) == 22 and all(c in B64 for c in value[2:]) and re.fullmatch(r'[0-9a-fA-F]{2}', value[:2]):
        h = value[:2].lower()
        for i in range(2, 22, 2):
            lhs, rhs = B64.index(value[i]), B64.index(value[i + 1])
            h += '%x%x%x' % (lhs >> 2, ((lhs & 3) << 2) | (rhs >> 4), rhs & 0xF)
    else:
        return None
    return '%s-%s-%s-%s-%s' % (h[:8], h[8:12], h[12:16], h[16:20], h[20:])


def _scenes_from_config(data):
    try:
        cfg = json.loads(data.decode('utf-8-sig'))
    except (ValueError, UnicodeDecodeError):
        return set()
    if not isinstance(cfg, dict) or not isinstance(cfg.get('scenes'), dict):
        return set()
    uuids = cfg.get('uuids') if isinstance(cfg.get('uuids'), list) else []
    out = set()
    for value in cfg['scenes'].values():
        if isinstance(value, int) and 0 <= value < len(uuids):
            value = uuids[value]
        u = decode_uuid(value)
        if u:
            out.add(u)
    return out


def scene_uuids_from_files(files):
    """Build (Native) files {relpath: bytes} -> set of dashed scene uuids."""
    out = set()
    for name, data in files.items():
        if CONFIG.search(name) and '__MACOSX' not in name:
            out |= _scenes_from_config(data)
    return out


def _meta_uuid(data):
    try:
        meta = json.loads(data.decode('utf-8-sig'))
    except (ValueError, UnicodeDecodeError):
        return None
    if isinstance(meta, dict) and meta.get('importer') in ('scene', None):
        return decode_uuid(meta.get('uuid'))
    return None


def scene_uuids_from_project(project):
    project = Path(project)
    out = set()
    assets = project / 'assets'
    if not assets.is_dir():
        return out
    for p in assets.rglob('*'):
        if not (p.name.endswith('.fire.meta') or p.name.endswith('.scene.meta')):
            continue
        if SKIP & set(p.relative_to(project).parts) or not p.is_file():
            continue
        u = _meta_uuid(p.read_bytes())
        if u:
            out.add(u)
    return out


def project_base(names):
    """Folder inside a source ZIP that holds assets/ (the shallowest), or None."""
    bases = set()
    for n in names:
        parts = PurePosixPath(n).parts
        if 'assets' in parts[:-1]:
            i = parts.index('assets')
            if not SKIP & set(parts[:i]):
                bases.add('/'.join(parts[:i]))
    if not bases:
        return None
    return sorted(bases, key=lambda b: (b.count('/') if b else -1, b))[0]


def native_prefix(names):
    """Prefix inside a ZIP where game.js + game.json + project.config.json sit together, or None."""
    heads = {}
    for n in names:
        p = PurePosixPath(n)
        if p.name in ('game.js', 'game.json', 'project.config.json'):
            heads.setdefault(str(p.parent) if str(p.parent) != '.' else '', set()).add(p.name)
    full = sorted([k for k, v in heads.items() if len(v) == 3 and '__MACOSX' not in k], key=lambda k: (k.count('/'), k))
    return None if not full else (full[0] + '/' if full[0] else '')


def _assets_from_config(data):
    try:
        cfg = json.loads(data.decode('utf-8-sig'))
    except (ValueError, UnicodeDecodeError):
        return set()
    uuids = cfg.get('uuids') if isinstance(cfg, dict) and isinstance(cfg.get('uuids'), list) else []
    return {u for u in (decode_uuid(v) for v in uuids) if u}


def asset_uuids_from_files(files):
    out = set()
    for name, data in files.items():
        if CONFIG.search(name) and '__MACOSX' not in name:
            out |= _assets_from_config(data)
    return out


def _any_meta_uuid(data):
    try:
        meta = json.loads(data.decode('utf-8-sig'))
    except (ValueError, UnicodeDecodeError):
        return None
    return decode_uuid(meta.get('uuid')) if isinstance(meta, dict) else None


def asset_uuids_from_project(project):
    project = Path(project)
    out = set()
    for p in (project / 'assets').rglob('*.meta') if (project / 'assets').is_dir() else []:
        if p.is_file() and not SKIP & set(p.relative_to(project).parts):
            u = _any_meta_uuid(p.read_bytes())
            if u:
                out.add(u)
    return out


def _sub_meta_uuids(data):
    """Every subMetas uuid of one .meta (2.4 sprite frames / textures, nested ones too; 3.x 'uuid@sub' decodes to
    the parent, which is already a top-level uuid)."""
    try:
        meta = json.loads(data.decode('utf-8-sig'))
    except (ValueError, UnicodeDecodeError):
        return set()
    out = set()
    stack = [meta.get('subMetas')] if isinstance(meta, dict) else []
    while stack:
        subs = stack.pop()
        if not isinstance(subs, dict):
            continue
        for value in subs.values():
            if isinstance(value, dict):
                u = decode_uuid(value.get('uuid'))
                if u:
                    out.add(u)
                stack.append(value.get('subMetas'))
    return out


def sub_asset_uuids_from_project(project):
    """v7.8 (B27): sub-asset uuids of every .meta under assets/ (what a package's config.json `uuids` also lists)."""
    project = Path(project)
    out = set()
    for p in (project / 'assets').rglob('*.meta') if (project / 'assets').is_dir() else []:
        if p.is_file() and not SKIP & set(p.relative_to(project).parts):
            out |= _sub_meta_uuids(p.read_bytes())
    return out


STARTER_FILES = ('workshop.json', 'starter.json')


def _is_starter_pack(d):
    """A workshop / design starter pack folder: workshop.json or starter.json, or START_HERE.md with GAME_DESIGN.md
    or ECONOMY.json next to it (starter-pack-spec.md)."""
    try:
        if any((d / n).is_file() for n in STARTER_FILES):
            return True
        return (d / 'START_HERE.md').is_file() and ((d / 'GAME_DESIGN.md').is_file() or (d / 'ECONOMY.json').is_file())
    except OSError:
        return False


def starter_trace(project, max_packs=2):
    """v7.8 (B27): the project was opened from a starter pack -> short text, else None. Read only.
    - inside a pack: the project folder or one of its 3 parents is a starter pack (pack/source, pack/source/x, ...);
    - next to a pack: one of the 3 parents holds a starter-pack child (a folder that is one, or *_StarterPack /
      *_StarterPack.zip). A folder with more than `max_packs` such children is a collection (下载/！自制游戏 itself
      holds dozens) and does not count."""
    try:
        here = Path(project).resolve()
    except (OSError, TypeError):
        return None
    if not here.is_dir():
        return None
    chain = [here] + list(here.parents)[:3]
    for d in chain:
        if _is_starter_pack(d):
            return 'inside starter pack %s' % d
    for d in chain[1:4]:
        try:
            kids = [c for c in d.iterdir() if c != here and not c.name.startswith('.')]
        except OSError:
            continue
        packs = {re.sub(r'(?i)\.zip$', '', c.name) for c in kids
                 if re.search(r'(?i)_StarterPack(\.zip)?$', c.name) or (c.is_dir() and _is_starter_pack(c))}
        if 0 < len(packs) <= max_packs:
            return 'next to starter pack %s' % (d / sorted(packs)[0])
    return None


def engine_of_names(names, texts=None):
    names = list(names)
    if any(re.search(r'(^|/)cocos2d-js(-min)?(\.[0-9a-f]+)?\.js$', n) for n in names):
        return 2
    if any(n.startswith('cocos-js/') or re.search(r'(^|/)web-adapter\.js$', n) for n in names):
        return 3
    return None


def engine_of_project_texts(project_json=None, package_json=None):
    for raw, key in ((package_json, 'creator'), (project_json, None)):
        if not raw:
            continue
        try:
            data = json.loads(raw.decode('utf-8-sig') if isinstance(raw, bytes) else raw)
        except (ValueError, UnicodeDecodeError):
            continue
        version = (data.get('creator') or {}).get('version') if key else data.get('version')
        if isinstance(version, str) and version[:1] in '23':
            return int(version[0])
    return None


def engine_of_project(project):
    project = Path(project)
    read = lambda n: (project / n).read_bytes() if (project / n).is_file() else None
    return engine_of_project_texts(read('project.json'), read('package.json'))


def identity_from_project(project):
    return {'kind': 'source', 'scenes': scene_uuids_from_project(project),
            'assets': asset_uuids_from_project(project), 'engine': engine_of_project(project)}


def identity_from_files(files):
    return {'kind': 'native', 'scenes': scene_uuids_from_files(files), 'assets': asset_uuids_from_files(files),
            'engine': engine_of_names(files)}


def _identity_from_zipfile(z, max_bytes):
    infos = [i for i in z.infolist() if not i.is_dir() and '__MACOSX' not in i.filename]
    names = [i.filename for i in infos]
    source = None
    base = project_base(names)
    if base is not None:
        prefix = base + '/' if base else ''
        scenes, assets, subs = set(), set(), set()
        for i in infos:
            n = i.filename
            if not n.startswith(prefix + 'assets/') or not n.endswith('.meta') or i.file_size > max_bytes \
                    or SKIP & set(PurePosixPath(n[len(prefix):]).parts):
                continue
            data = z.read(i)
            u = _any_meta_uuid(data)
            if u:
                assets.add(u)
                if n.endswith('.fire.meta') or n.endswith('.scene.meta'):
                    scenes.add(u)
            subs |= _sub_meta_uuids(data)
        get = lambda n: z.read(prefix + n) if (prefix + n) in names else None
        source = {'kind': 'source', 'scenes': scenes, 'assets': assets, 'base': base, 'sub_assets': subs - assets,
                  'engine': engine_of_project_texts(get('project.json'), get('package.json'))}
        if scenes:
            return source
    prefix = native_prefix(names)
    if prefix is not None:
        files = {}
        for i in infos:
            if i.filename.startswith(prefix) and CONFIG.search(i.filename) and i.file_size <= max_bytes:
                files[i.filename[len(prefix):]] = z.read(i)
        out = identity_from_files(files)
        out['engine'] = engine_of_names(n[len(prefix):] for n in names if n.startswith(prefix))
        if out['scenes'] or out['assets'] or source is None:
            return dict(out, base=prefix)
    return source or {'kind': None, 'scenes': set(), 'assets': set(), 'engine': None, 'base': None}


def identity_from_zip(path, max_bytes=5_000_000, nested_max=300_000_000):
    """-> {'kind': 'native'|'source'|None, 'scenes', 'assets', 'engine', 'base'}. Reads only configs / metas.
    A ZIP holding only other ZIPs (starter-pack bundles) is read one level deep."""
    import io
    with zipfile.ZipFile(path) as z:
        out = _identity_from_zipfile(z, max_bytes)
        if out['kind'] is not None and (out['scenes'] or out['assets']):
            return out
        for info in z.infolist():
            if info.filename.lower().endswith('.zip') and '__MACOSX' not in info.filename \
                    and info.file_size <= nested_max:
                try:
                    with zipfile.ZipFile(io.BytesIO(z.read(info))) as inner:
                        sub = _identity_from_zipfile(inner, max_bytes)
                except zipfile.BadZipFile:
                    continue
                if sub['scenes'] or sub['assets']:
                    return dict(sub, base=info.filename + '!/' + (sub.get('base') or ''))
        return out


def scene_uuids_from_zip(path):
    out = identity_from_zip(path)
    return dict(out, uuids=out['scenes'])


def scene_uuids_from_dir(native):
    native = Path(native)
    files = {}
    for p in native.rglob('config*.json'):
        if p.is_file() and CONFIG.search(p.name):
            files[p.relative_to(native).as_posix()] = p.read_bytes()
    return scene_uuids_from_files(files)


def load_legacy(path=None):
    path = Path(path) if path else LEGACY
    if not path.is_file():
        return {'games': [], 'unlisted_policy': 'new', 'missing': True, 'path': str(path)}
    data = json.loads(path.read_text(encoding='utf-8'))
    data.setdefault('games', [])
    data.setdefault('unlisted_policy', 'new')
    data['path'] = str(path)
    return data


def read_marker(project):
    if not project:
        return None
    p = Path(project) / MARKER
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_marker(project, board, kit_version, reason='init'):
    """Write the new-game marker. There is deliberately no way to write a legacy marker."""
    p = Path(project) / MARKER
    p.parent.mkdir(parents=True, exist_ok=True)
    old = read_marker(project)
    data = {'policy': 'new', 'kit_version': kit_version, 'board': board,
            'created': (old or {}).get('created') or time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'by': reason}
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return data


ASSET_MIN = 5          # unique asset uuids that must match when no unique scene uuid does
ASSET_SHARE = 0.2      # ... and at least this share of the entry's stored unique asset uuids


def match_legacy(scenes, legacy, assets=()):
    """Entries whose UNIQUE uuids (make_legacy_list drops uuids shared with starter packs or other games) match."""
    hits = []
    scenes, assets = set(scenes), set(assets)
    for game in legacy.get('games') or []:
        common_s = scenes & set(game.get('scene_uuids') or [])
        stored = set(game.get('asset_uuids') or [])
        common_a = assets & stored
        by_assets = stored and len(common_a) >= ASSET_MIN and len(common_a) >= ASSET_SHARE * len(stored)
        if common_s or by_assets:
            hits.append({'name': game.get('name'), 'folder': game.get('folder'), 'scenes': sorted(common_s),
                         'assets_matched': len(common_a), 'assets_stored': len(stored)})
    return hits


def match_legacy_path(project, legacy):
    """v7.7.5 (总表 B27): the project folder IS the one the list recorded as an entry's last source package. Only the
    exact folder counts, never a parent or a child, so a new game started inside an old game's folder stays new.
    The list was read from packages (their config.json also lists sub-assets), a project only shows top-level .meta
    uuids: 剪刀达人's recorded project shows 63 of the 400 stored ones (80 needed), 欢乐刮水果's recorded Chinese
    original none (its stored uuids came from the English package). Both were judged new and could not ship."""
    try:
        here = Path(project).resolve()
    except (OSError, TypeError):
        return []
    if not here.is_dir():
        return []
    hits = []
    for game in legacy.get('games') or []:
        last = game.get('last_package')
        path = last.get('path') if isinstance(last, dict) else None
        if not path or last.get('kind') != 'source':
            continue
        try:
            same = Path(path).resolve() == here
        except OSError:
            same = False
        if same:
            hits.append({'name': game.get('name'), 'folder': game.get('folder'), 'scenes': [], 'assets_matched': 0,
                         'assets_stored': len(game.get('asset_uuids') or []), 'by': 'last_package path'})
    return hits


def identity(project=None, files=None, native=None):
    scenes, assets = set(), set()
    if project and Path(project, 'assets').is_dir():
        ident = identity_from_project(project)
        scenes |= ident['scenes']
        assets |= ident['assets']
    if files is not None:
        scenes |= scene_uuids_from_files(files)
        assets |= asset_uuids_from_files(files)
    if native:
        files = {p.relative_to(native).as_posix(): p.read_bytes()
                 for p in Path(native).rglob('config*.json') if p.is_file() and CONFIG.search(p.name)}
        scenes |= scene_uuids_from_files(files)
        assets |= asset_uuids_from_files(files)
    return scenes, assets


def decide(project=None, files=None, native=None, legacy=None, uuids=None, assets=None, board=None, sub_assets=None):
    """-> {'policy': 'new'|'legacy', 'reason': str, 'scene_uuids': [...], 'legacy_match': [...]}
    board: the caller's --board when it has one (only the v7.8 sub-asset rule reads it). sub_assets: sub-asset uuids
    already read (source ZIP); with a project they are read from its .meta files. A new decision the sub-asset rule
    turned around carries 'auto_new' (why) and 'sub_asset_match' (what would have matched)."""
    legacy = legacy if legacy is not None else load_legacy()
    mark = read_marker(project)
    if uuids is None:
        uuids, found_assets = identity(project, files, native)
        assets = found_assets if assets is None else assets
    assets = set(assets or ())
    uuids = sorted(uuids)
    out = {'scene_uuids': uuids, 'asset_uuids_read': len(assets), 'legacy_match': [],
           'legacy_list': legacy.get('path'), 'legacy_frozen': bool(legacy.get('frozen')),
           'unlisted_policy': legacy.get('unlisted_policy', 'new')}
    if mark and mark.get('policy') == 'new':
        return dict(out, policy='new', reason='project marker .tiktok-kit/policy.json says new (%s)' % mark.get('by'))
    hits = match_legacy(uuids, legacy, assets)
    by_path = False
    if not hits and project is not None:
        hits = match_legacy_path(project, legacy)
        by_path = bool(hits)
    by_sub = False
    if not hits:
        subs = set(sub_assets or ())
        if project is not None and sub_assets is None and Path(project, 'assets').is_dir():
            subs = sub_asset_uuids_from_project(project)
        subs -= assets
        out['sub_asset_uuids_read'] = len(subs)
        sub_hits = match_legacy(uuids, legacy, assets | subs) if subs else []
        if sub_hits:
            names = ', '.join(str(h['folder']) for h in sub_hits)
            trace = starter_trace(project) if project is not None else None
            if trace or board == 'remake':
                why = trace or '--board remake'
                return dict(out, policy='new', auto_new=why, sub_asset_match=sub_hits,
                            reason='only sub-asset uuids match %s, but %s -> new game (v7.8 B27)' % (names, why))
            hits, by_sub = [dict(h, by='sub-asset uuids') for h in sub_hits], True
    if hits:
        how = ' (same folder as its recorded last package)' if by_path else \
            ' (by sub-asset uuids; a game opened from a starter pack is new: run init)' if by_sub else ''
        return dict(out, policy='legacy', legacy_match=hits,
                    reason='on the legacy list: %s%s' % (', '.join(str(h['folder']) for h in hits), how))
    why = 'no scene uuid readable' if not uuids else 'not on the legacy list'
    if legacy.get('missing'):
        why += ' (LEGACY_GAMES.json missing)'
    return dict(out, policy='new', reason=why + ' -> new game (default)')
