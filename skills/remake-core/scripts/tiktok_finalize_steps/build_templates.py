"""Source step: build-templates hold only the kit's files (design D77 1.3, new remake games only).

2.4 (build-templates/bytedance/): keep exactly the kit files (manifest `files` under build-templates/bytedance/ plus
     any part whose file.template points there, e.g. storage-guard.js); every other file there (own boot/touch file,
     game.js, project.config.json override) moves to .tiktok-kit/removed/.
3.x (build-templates/bytedance-mini-game/): add the engine-3 parts whose file.template points there
     (tiktok-touch-3x.js, storage-guard.js); move away only files that match a part's own_markers (an own touch
     layer); game.js and other template files stay (the load lines are wired in the native step).
localize board and legacy games: nothing (an original project's own templates are too risky to replace).
"""
import re

from . import KitError, Result, sha256

DIR = {2: 'build-templates/bytedance/', 3: 'build-templates/bytedance-mini-game/'}


def wanted(ctx):
    """{template relpath: kit bytes}"""
    base = DIR.get(ctx.engine)
    out = {}
    if not base:
        return out
    if ctx.engine == 2:
        for key, spec in ctx.manifest.files.items():
            if key.startswith(base) and isinstance(spec, dict) and not spec.get('reference'):
                path = ctx.manifest.kit_dir / key
                data = path.read_bytes() if path.is_file() else None
                if data is None or sha256(data) != spec.get('sha256'):
                    raise KitError('kit template %s missing or differs from KIT_MANIFEST' % key)
                out[key] = data
    for name, part in ctx.manifest.parts_for(ctx.engine):
        tmpl = (part.get('file') or {}).get('template')
        if tmpl and tmpl.startswith(base):
            out[tmpl] = ctx.manifest.kit_bytes(name)
    return out


def own_patterns(ctx):
    """own_markers / own_files of the native layer parts only (touch, storage): a template file is moved away only
    when it is an own touch or storage layer. Plugin and ad parts carry no markers for this (W-A2 request 3)."""
    from . import step_parts
    pats = []
    for step in ('touch', 'storage'):
        for _, part in step_parts(ctx.manifest, step, ctx.engine):
            pats += [re.compile(p) for p in part.get('own_markers') or []]
    return pats


def applies(ctx):
    return ctx.policy == 'new' and ctx.board != 'localize' and ctx.engine in DIR


def present(ctx):
    base = ctx.path(DIR[ctx.engine])
    if not base.is_dir():
        return []
    return sorted(p.relative_to(ctx.root).as_posix() for p in base.rglob('*')
                  if p.is_file() and not p.name.startswith('.') and not p.name.endswith('.meta'))


def detect(ctx):
    if ctx.engine not in DIR:
        return 'n/a'
    want = wanted(ctx)
    have = present(ctx)
    if any(ctx.read(rel) != data for rel, data in want.items()):
        return 'absent' if all(ctx.read(rel) is None for rel in want) else 'own'
    extra = [rel for rel in have if rel not in want]
    return 'kit_current' if not extra else 'own'


def apply(ctx):
    r = Result('build_templates')
    if ctx.engine not in DIR:
        r.state = 'n/a'
        return r.as_dict()
    if not applies(ctx):
        r.state = 'skipped'
        r.info.append('build-templates left as is (%s)' % ('localize board' if ctx.board == 'localize'
                                                          else 'legacy game'))
        return r.as_dict()
    try:
        want = wanted(ctx)
        r.state = detect(ctx)
    except KitError as error:
        r.block('K_kit_unusable', str(error))
        return r.as_dict()
    if not want:
        r.block('K1_kit_bytes', 'KIT_MANIFEST names no build-template files for engine %s' % ctx.engine)
        return r.as_dict()
    pats = own_patterns(ctx)
    kit_hashes = ctx.manifest.kit_hashes()
    for rel in present(ctx):
        if rel in want:
            continue
        data = ctx.read(rel)
        if ctx.engine == 2 or (sha256(data) not in kit_hashes and
                               any(p.search(data.decode('utf-8', 'replace')) for p in pats)):
            moved = ctx.move_away(rel)
            meta = rel + '.meta'
            if ctx.read(meta) is not None:
                ctx.move_away(meta)
            r.change(rel, data, None, 'moved to %s' % moved)
    for rel, data in sorted(want.items()):
        old = ctx.read(rel)
        if old != data:
            if old is not None:
                ctx.move_away(rel)
            ctx.write(rel, data)
            r.change(rel, old, data, 'kit template %s' % ('restored' if old is not None else 'added'))
    for rel, data in want.items():
        if ctx.read(rel) != data:
            r.block('K1_kit_bytes', 'build template did not verify: %s' % rel)
    if ctx.engine == 2:
        extra = [rel for rel in present(ctx) if rel not in want]
        if extra:
            r.block('K3_single_layer', 'build-templates/bytedance still has non-kit files: %s' % ', '.join(extra))
    return r.as_dict()
