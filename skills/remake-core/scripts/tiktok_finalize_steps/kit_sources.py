"""Source step: the platform-kit modules in the project are byte-identical to KIT_MANIFEST (design D77 1.3).

2.4: every non-reference manifest `files` entry under assets/tiktok-platform/ is copied to the same path in the
     project. PlatformConfig.js (editable) is only added when missing, never overwritten.
3.x: every manifest part with engine 3 and phase 'source' (W-A2 plugin scripts) is copied to file.dest; when the
     part says "plugin": true its .meta gets the import-as-plugin flags (native + mini-game), uuid kept.
new policy: missing -> added; changed -> kit file restored, the old one moved to .tiktok-kit/removed/.
legacy policy: report differences only (nothing written).
Same module name (v7.7 W-F1a, W-D3 request 5): Cocos 2.4 module names are global, so a game script anywhere under
assets/ named like a kit module (MabelsMeadow r8: assets/scripts/platform/TikTokMissionService.js, an old
MissionFlow.js) stops the Creator build with "Filename conflict". new policy: that script and its .meta move to
.tiktok-kit/removed/<relative path> with a warning (the game's require() of the name then loads the kit module);
legacy policy: warning only.
"""
import json
import uuid as uuidlib

from . import KitError, Result, sha256

KIT_PREFIX = 'assets/tiktok-platform/'
PLUGIN_FLAGS = {'isPlugin': True, 'loadPluginInWeb': True, 'loadPluginInNative': True,
                'loadPluginInMiniGame': True, 'loadPluginInEditor': False}


def kit_file_bytes(manifest, key):
    spec = manifest.files[key]
    path = manifest.kit_dir / key
    if not path.is_file():
        raise KitError('kit file missing: %s' % key)
    data = path.read_bytes()
    if sha256(data) != spec.get('sha256'):
        raise KitError('kit file %s differs from KIT_MANIFEST' % key)
    return data


def wanted(ctx):
    """[(dest relpath, kit bytes, editable, part name or None, plugin)] for this engine."""
    out = []
    if ctx.engine == 3:
        for name, part in ctx.manifest.parts_for(3, 'source'):
            spec = part.get('file') or {}
            if spec.get('dest'):
                out.append((spec['dest'], ctx.manifest.kit_bytes(name), bool(part.get('editable')), name,
                            bool(part.get('plugin'))))
        return out
    for key, spec in sorted(ctx.manifest.files.items()):
        if key.startswith(KIT_PREFIX) and isinstance(spec, dict) and not spec.get('reference'):
            out.append((key, kit_file_bytes(ctx.manifest, key), bool(spec.get('editable')), None, False))
    return out


def _state(have, kit, editable):
    if have is None:
        return 'absent'
    if have == kit:
        return 'kit_current'
    return 'own' if not editable else 'kit_current'      # an edited PlatformConfig.js is expected


def detect(ctx):
    states = {dest: _state(ctx.read(dest), kit, editable) for dest, kit, editable, _, _ in wanted(ctx)}
    if not states:
        return 'n/a'
    if all(s == 'kit_current' for s in states.values()):
        return 'kit_current'
    return 'own' if any(s == 'own' for s in states.values()) else 'absent'


def plugin_meta(existing, dest):
    try:
        meta = json.loads(existing.decode('utf-8')) if existing else {}
    except (ValueError, UnicodeDecodeError):
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    meta.setdefault('ver', '4.0.24')
    meta.setdefault('importer', 'javascript')
    meta.setdefault('imported', True)
    meta.setdefault('uuid', str(uuidlib.uuid5(uuidlib.NAMESPACE_URL, 'tiktok-kit:' + dest)))
    meta.setdefault('files', ['.js'])
    meta.setdefault('subMetas', {})
    user = meta.get('userData') if isinstance(meta.get('userData'), dict) else {}
    user.update(PLUGIN_FLAGS)
    meta['userData'] = user
    return (json.dumps(meta, indent=2) + '\n').encode('utf-8')


def same_name_modules(ctx, items):
    """[(kit dest, game file)] for Cocos 2.4: a project script outside assets/tiktok-platform/ whose module name equals
    a kit module (2.4 module names are global: MabelsMeadow r8 ships assets/scripts/platform/TikTokMissionService.js
    and an old MissionFlow.js, and Creator stops with \"Filename conflict\", W-D3 request 5)."""
    if ctx.engine != 2:
        return []
    names = {}
    for dest, _, _, _, _ in items:
        if dest.startswith(KIT_PREFIX) and dest.endswith('.js'):
            names[dest.rsplit('/', 1)[-1][:-3]] = dest
    if not names:
        return []
    assets = ctx.root / 'assets'
    out = []
    if not assets.is_dir():
        return out
    for path in sorted(assets.rglob('*')):
        if path.suffix not in ('.js', '.ts') or not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(ctx.root).as_posix()
        if rel.startswith(KIT_PREFIX) or path.name.endswith('.d.ts'):
            continue
        stem = path.name[:-len(path.suffix)]
        if stem in names:
            out.append((names[stem], rel))
    return out


def take_out_same_name(ctx, r, items):
    kit_bytes = {dest: kit for dest, kit, _, _, _ in items}
    for dest, rel in same_name_modules(ctx, items):
        data = ctx.read(rel)
        same = data is not None and data == kit_bytes.get(dest)
        if ctx.policy == 'legacy':
            r.warn('K_W_kit_module_duplicate', 'game script %s has the same module name as kit file %s (Cocos 2.4 '
                   'module names are global; a build with both stops with \"Filename conflict\"); legacy game: '
                   'reported only' % (rel, dest), {'file': rel, 'kit_file': dest})
            continue
        moved = ctx.move_away(rel)
        r.change(rel, data, None, 'game script with the kit module name moved to %s' % moved)
        meta = rel + '.meta'
        if ctx.read(meta) is not None:
            ctx.move_away(meta)
            r.info.append('moved %s with it' % meta)
        r.warn('K_W_kit_module_duplicate', 'game script %s (%s) had the same module name as kit file %s and was '
               'moved to %s; the game\'s require() of that name now loads the kit module' % (
                   rel, 'same bytes as the kit file' if same else 'not the kit file, sha %s' % sha256(data)[:12],
                   dest, moved), {'file': rel, 'kit_file': dest, 'same_bytes': same})


def apply(ctx):
    r = Result('kit_sources')
    try:
        items = wanted(ctx)
    except KitError as error:
        r.block('K_kit_unusable', str(error))
        return r.as_dict()
    take_out_same_name(ctx, r, items)
    if not items:
        r.state = 'n/a'
        r.info.append('no kit source files for engine %s in this manifest' % ctx.engine)
        if ctx.engine == 3 and ctx.policy == 'new':
            r.block('K1_kit_bytes', 'KIT_MANIFEST has no 3.x source parts (plugins-3x); cannot install the platform '
                                    'kit into a 3.x project')
        return r.as_dict()
    states = []
    for dest, kit, editable, part, plugin in items:
        have = ctx.read(dest)
        state = _state(have, kit, editable)
        states.append(state)
        if state == 'own' and ctx.policy == 'legacy':
            r.warn('K_W_kit_source_changed', '%s differs from the platform kit (legacy game: left as is)' % dest,
                   {'file': dest, 'sha256': sha256(have)})
        elif state == 'absent' and ctx.policy == 'legacy':
            r.warn('K_W_kit_source_missing', '%s not in the project (legacy game: not added)' % dest, {'file': dest})
        elif state in ('own', 'absent'):
            if state == 'own':
                moved = ctx.move_away(dest)
                r.info.append('moved own %s to %s' % (dest, moved))
            ctx.write(dest, kit)
            r.change(dest, have, kit, 'kit file restored' if state == 'own' else 'kit file added')
        if plugin and ctx.policy == 'new':
            meta_rel = dest + '.meta'
            old = ctx.read(meta_rel)
            new = plugin_meta(old, dest)
            if new != old:
                ctx.write(meta_rel, new)
                r.change(meta_rel, old, new, 'import as plugin (native + mini-game)')
    r.state = 'kit_current' if all(s == 'kit_current' for s in states) else \
        ('own' if 'own' in states else 'absent')
    if ctx.policy == 'new':
        for dest, kit, editable, _, _ in items:
            have = ctx.read(dest)
            if have is None or (not editable and have != kit):
                r.block('K1_kit_bytes', 'kit file did not verify after install: %s' % dest)
    return r.as_dict()


def verify(ctx):
    """Findings for a project (source records): kit files present and byte-identical."""
    out = []
    items = wanted(ctx)
    for dest, rel in same_name_modules(ctx, items):
        out.append({'id': 'K_kit_module_duplicate', 'level': 'block' if ctx.policy == 'new' else 'warn',
                    'message': '%s has the same Cocos 2.4 module name as kit file %s' % (rel, dest)})
    for dest, kit, editable, _, _ in items:
        have = ctx.read(dest)
        if have is None or (not editable and have != kit):
            out.append({'id': 'K1_kit_bytes', 'level': 'block' if ctx.policy == 'new' else 'warn',
                        'message': '%s %s' % (dest, 'missing' if have is None else 'differs from the kit')})
    return out
