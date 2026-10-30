"""Native step: startup chain (design D77 1.3 row startup.py, 3.2, R3, R4).

Cocos 2.4, new policy: the build's main.js must be the kit main.js (startup part, or manifest files entry
    build-templates/bytedance/main.js). A remake build already has it from build-templates (only checked here);
    an editor main.js (English original) or an older kit main.js is replaced, the old one moved to
    .tiktok-kit-removed. R4: the kit main.js follows the 2.4.15 editor conventions, so an engine version not in the
    part's "engine_versions" (default ["2.4.15"]) keeps its editor main.js with a warning; touch and storage then get
    their own game.js lines. game.js must really require './main' (Nanas: template present, never loaded).
    Own startup files (root JS loaded by game.js before main, or named like the part's own_markers) are taken out
    when their load line is one whole statement; a wrapper that cannot be taken out (pkg81 native-preload wraps the
    engine in a callback) stays with a warning for the game's session.
Cocos 2.4, legacy policy: nothing changes; own startup files are warnings (K_W_own_startup).
Cocos 3.x: no device-proven startup part exists (R3, Q5): check only, own startup files are warnings.
"""
import re

from . import (KitError, MAIN_REQUIRE, Result, STOCK_ROOT_JS, is_engine_or_adapter, kit_main_current,
               kit_main_versions, live_matches, neutralize, require_rx, sha256, step_parts, text_of)

STEP = 'startup'
KIT_MAIN = 'build-templates/bytedance/main.js'
DEFAULT_ENGINE_VERSIONS = ('2.4.15',)


def _engine_version(files):
    try:
        from package_gates.adapter_fix import _engine_version as read
    except ImportError:
        return None
    return read(files)


def startup_part(manifest):
    parts = step_parts(manifest, STEP, 2)
    return parts[0] if parts else (None, {})


def kit_main_bytes(manifest):
    name, part = startup_part(manifest)
    if name:
        return manifest.kit_bytes(name)
    spec = manifest.files.get(KIT_MAIN)
    path = manifest.kit_dir / KIT_MAIN
    if not isinstance(spec, dict) or not path.is_file() or sha256(path.read_bytes()) != spec.get('sha256'):
        raise KitError('kit main.js missing or differs from KIT_MANIFEST')
    return path.read_bytes()


def part_dests(manifest):
    return {(p.get('file') or {}).get('dest') for p in manifest.parts.values()} - {None}


def own_startup(files, manifest, engine):
    """Root JavaScript that is an own startup layer: loaded by game.js before './main' (2.4) / before the engine
    (3.x), or named like the startup part's own_markers. Stock, engine, adapter, kit and kit-part files never count."""
    import re
    _, part = startup_part(manifest)
    pats = [re.compile(p) for p in part.get('own_files') or []]
    pats += [re.compile(r'(^|/)[\w-]*(load-guard|boot|preload|loader)[\w-]*\.js$')]
    game = text_of(files.get('game.js'))
    mains = live_matches(game, MAIN_REQUIRE)
    limit = mains[0].start() if mains else len(game)
    kit, dests = manifest.kit_hashes(), part_dests(manifest)
    out = []
    for rel, data in sorted(files.items()):
        if '/' in rel or not rel.endswith('.js') or rel in STOCK_ROOT_JS or rel in dests or is_engine_or_adapter(rel):
            continue
        if sha256(data) in kit:
            continue
        early = engine == 2 and any(m.start() < limit for m in live_matches(game, require_rx(rel)))
        if early or any(p.search(rel) for p in pats):
            out.append(rel)
    return out


def main_state(files, manifest):
    data = files.get('main.js')
    if data is None:
        return 'absent'
    digest = sha256(data)
    if digest == kit_main_current(manifest):
        return 'kit_current'
    return 'kit_old' if digest in kit_main_versions(manifest) else 'own'


def main_extras(manifest):
    """[(spec)] files the kit main.js itself requires (startup24.extra_files, kit 2.0 W-F1a): webp-decode-probe.js.
    main.js v1.3+ has require('./webp-decode-probe') inside `if (window.__TIKTOK_KIT_WEBP_PROBE__ === true)`; a static
    dependency check does not read the `if`, so the file always ships next to the kit main.js. Only the probe script:
    no probe image and no switch line (those come with --keep-webp-exception, part webp_probe24), so it never runs."""
    _, part = startup_part(manifest)
    return [x for x in part.get('extra_files') or [] if x.get('dest') and x.get('src')]


def extra_needed(files, spec):
    """True when the package main.js really loads this extra file (live require, comments ignored)."""
    return bool(live_matches(text_of(files.get('main.js')), require_rx(spec['dest'])))


def install_main_extras(ctx, r):
    files = ctx.files()
    for spec in main_extras(ctx.manifest):
        if not extra_needed(files, spec):
            continue
        path = ctx.manifest.kit_dir / spec['src']
        data = path.read_bytes() if path.is_file() else None
        if data is None or sha256(data) != spec.get('sha256'):
            r.block('K_kit_unusable', 'kit file %s missing or differs from KIT_MANIFEST' % spec['src'])
            continue
        old = files.get(spec['dest'])
        if old == data:
            continue
        if old is not None:
            if ctx.policy == 'legacy':
                r.warn('K_W_own_startup', 'legacy game keeps its own %s (not the kit file)' % spec['dest'],
                       {'file': spec['dest']})
                continue
            ctx.move_away(spec['dest'])
        ctx.write(spec['dest'], data)
        r.change(spec['dest'], old, data, 'kit %s next to the kit main.js (%s)' % (
            spec['dest'], spec.get('what') or 'required by main.js'))


def requirers(files, rel):
    """Other package JS files (not game.js, not the file itself, not the engine) that load `rel` on a live line."""
    import re
    engine = re.compile(r'(^|/)cocos2d-js(-min)?(\.[0-9a-f]{5,})?\.js$|(^|/)physics(-min)?\.js$')
    rx = require_rx(rel)
    out = []
    for name, data in sorted(files.items()):
        if name in (rel, 'game.js') or not name.endswith('.js') or engine.search(name):
            continue
        if live_matches(text_of(data), rx):
            out.append(name)
    return out


REMOVED_LINE = re.compile(r'^([ \t]*// tiktok-kit-removed:startup24: )(.*)$', re.M)


def defuse_removed(text, rel):
    """A commented-out load line keeps the old text for the reader, but `require(` becomes `require_removed(` so no
    scanner that ignores comments (audit_packed_assets entry requires: pkg81 \"missing entry require:
    ./native-load-guard\") still sees a load of the moved file."""
    rx = require_rx(rel)

    def fix(m):
        return m.group(1) + m.group(2).replace('require(', 'require_removed(') if rx.search(m.group(2)) else m.group(0)
    return REMOVED_LINE.sub(fix, text)


def compatible(files, manifest):
    _, part = startup_part(manifest)
    allowed = tuple(part.get('engine_versions') or (part.get('needs') or {}).get('engine_versions')
                    or DEFAULT_ENGINE_VERSIONS)
    version = _engine_version(files)
    return version in allowed, version, allowed


def install_webp_probe(ctx, r):
    """--keep-webp-exception (Q4): the kit WebP probe part (file, extra files, the switch line before
    require('./main')) is installed by finalize, never written by the model. Needs the kit main.js."""
    from . import install_part, self_check
    parts = step_parts(ctx.manifest, 'webp_probe', 2)
    if not parts:
        r.block('K1_kit_bytes', 'KIT_MANIFEST has no webp_probe24 part for the WebP exception')
        return
    if main_state(ctx.files(), ctx.manifest) != 'kit_current':
        r.block('K2_kit_wiring', 'the WebP exception needs the kit main.js (it reads __TIKTOK_KIT_WEBP_PROBE__)')
        return
    for name, part in parts:
        install_part(ctx, r, name, part, 'replace')
        for extra in part.get('extra_files') or []:
            path = ctx.manifest.kit_dir / extra['src']
            data = path.read_bytes() if path.is_file() else None
            if data is None or sha256(data) != extra.get('sha256'):
                r.block('K_kit_unusable', 'kit file %s missing or differs from KIT_MANIFEST' % extra['src'])
                continue
            old = ctx.read(extra['dest'])
            if old != data:
                ctx.write(extra['dest'], data)
                r.change(extra['dest'], old, data, 'kit WebP probe file (exception: %s)'
                         % ctx.options['keep_webp_exception'])
        self_check(ctx, r, [(name, part)], 'new')


def detect(ctx):
    if ctx.engine != 2:
        return 'n/a'
    files = ctx.files()
    state = main_state(files, ctx.manifest)
    return 'own' if state == 'kit_current' and own_startup(files, ctx.manifest, 2) else state


def apply(ctx):
    r = Result(STEP)
    files = ctx.files()
    if ctx.engine != 2:
        r.state = 'n/a'
        for rel in own_startup(files, ctx.manifest, ctx.engine) if ctx.engine == 3 else []:
            r.warn('K_W_own_startup', 'own startup file %s kept (v7.7 has no 3.x startup part, R3); hand it to this '
                   "game's session" % rel, {'file': rel})
        return r.as_dict()
    state = main_state(files, ctx.manifest)
    r.state = state
    own = own_startup(files, ctx.manifest, 2)
    if ctx.policy == 'legacy':
        for rel in own:
            r.warn('K_W_own_startup', 'legacy game keeps its own startup file %s; hand it to this game\'s session'
                   % rel, {'file': rel})
        if state not in ('kit_current', 'kit_old'):
            r.info.append('main.js is not the kit main.js (legacy game: left as is)')
        else:
            install_main_extras(ctx, r)
        return r.as_dict()
    try:
        kit = kit_main_bytes(ctx.manifest)
    except KitError as error:
        r.block('K_kit_unusable', str(error))
        return r.as_dict()
    ok, version, allowed = compatible(files, ctx.manifest)
    if state != 'kit_current':
        if state == 'own' and not ok:
            r.warn('K_W_startup_engine', 'engine %s is not in %s: the editor main.js stays (R4); touch and storage '
                   'get their own game.js lines' % (version, ', '.join(allowed)), {'engine_version': version})
        else:
            if files.get('main.js') is not None:
                ctx.move_away('main.js')
            ctx.write('main.js', kit)
            r.change('main.js', files.get('main.js'), kit, 'kit main.js %s' % (
                'installed' if state == 'absent' else 'replaces %s main.js' % ('older kit' if state == 'kit_old'
                                                                               else 'editor/own')))
    install_main_extras(ctx, r)
    game = text_of(files.get('game.js'))
    new_game = game
    for rel in own:
        users = requirers(files, rel)
        if users:
            # W-D1 request 2: moving it would break the files that still load it
            r.warn('K_W_own_startup_kept', 'own startup file %s stays: %s still require%s it; hand it to this '
                   "game's session" % (rel, ', '.join(users), 's' if len(users) == 1 else ''),
                   {'file': rel, 'required_by': users})
            continue
        trial, done, refused = neutralize(new_game, require_rx(rel), 'startup24')
        if refused:
            r.warn('K_W_own_startup_kept', 'own startup file %s stays: its load line cannot be taken out '
                   'automatically (%s); hand it to this game\'s session' % (rel, refused[0]), {'file': rel})
            continue
        if done:
            new_game = defuse_removed(trial, rel)
            moved = ctx.move_away(rel)
            r.change(rel, files[rel], None, 'own startup file moved to %s' % moved)
        else:
            r.warn('K_W_own_startup_kept', 'own startup-like file %s is not loaded by game.js; left in place' % rel,
                   {'file': rel})
    if new_game != game:
        ctx.write('game.js', new_game.encode('utf-8'))
        r.change('game.js', files.get('game.js'), new_game.encode('utf-8'), 'own startup load lines commented out')
    if ctx.options.get('keep_webp_exception'):
        install_webp_probe(ctx, r)
    for item in verify(ctx.files(), ctx.manifest, ctx.policy, 2):
        if item['level'] == 'block':
            r.blocks.append(dict(item, message='after install: ' + item['message']))
    return r.as_dict()


def verify(files, manifest, policy, engine=None):
    from .policy import engine_of_names
    engine = engine or engine_of_names(files)
    out = []
    root = {k: v for k, v in files.items() if '/' not in k}
    own = own_startup(root, manifest, engine) if engine in (2, 3) else []
    for rel in own:
        out.append({'id': 'K_W_own_startup', 'level': 'warn', 'message': 'own startup file %s in the package' % rel,
                    'evidence': {'file': rel}})
    if engine == 2:
        for spec in main_extras(manifest):
            if not extra_needed(root, spec):
                continue
            have = root.get(spec['dest'])
            if have is not None and sha256(have) == spec.get('sha256'):
                continue
            out.append({'id': 'K1_kit_bytes', 'level': 'block' if policy == 'new' else 'warn',
                        'message': 'startup24: main.js requires ./%s but it is %s (manifest sha %s)' % (
                            spec['dest'][:-3] if spec['dest'].endswith('.js') else spec['dest'],
                            'missing' if have is None else 'not the kit file', str(spec.get('sha256'))[:12]),
                        'evidence': {'part': 'startup24', 'file': spec['dest'],
                                     'state': 'absent' if have is None else 'own'}})
    if engine != 2 or policy != 'new':
        return out
    state = main_state(root, manifest)
    ok, version, _ = compatible(files, manifest)
    if state != 'kit_current' and not (state == 'own' and not ok):
        out.append({'id': 'K1_kit_bytes', 'level': 'block', 'message': 'startup24: main.js is %s, not the kit main.js'
                    % {'absent': 'missing', 'kit_old': 'an older kit version', 'own': 'an editor/own file'}[state],
                    'evidence': {'part': 'startup24', 'state': state}})
    loads = len(live_matches(text_of(files.get('game.js')), MAIN_REQUIRE))
    if loads != 1:
        out.append({'id': 'K2_kit_wiring', 'level': 'block', 'message': "game.js requires './main' %d times (need "
                    'exactly 1; 0 = the kit startup chain never runs, as in Nanas)' % loads,
                    'evidence': {'part': 'startup24', 'count': loads}})
    return out
