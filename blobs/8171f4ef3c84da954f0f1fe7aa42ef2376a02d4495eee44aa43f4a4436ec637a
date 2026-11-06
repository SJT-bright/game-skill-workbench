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
生成时预防 R4B (问题普查 startup_stuck 34 款, startup_retry_broken 27, host_api_mismatch 12): this step also installs
    the first lines of game.js, so no game hand-writes them (install_early):
    hostshim24 / hostshim3x  parts/host-shim.js, line BEFORE the adapter (2.4 adapter-min.js, 3.x web-adapter.js)
    boot3x                   parts-3x/boot-guard-3x.js, line BEFORE System.warmup( (3.x only)
    New games: installed (native phase and `sync --native` on the build game.js; source phase on a 3.x
    build-templates/bytedance-mini-game/game.js when the project has one, so every build already has the lines).
    Legacy games: report only. A 3.x game with its own start page (game.js loads ./boot-loading, or a root
    boot-loading.js / native-recovery.js, LunasJade): boot3x reported, never stacked. A game.js without the anchor
    (not a stock Cocos mini-game game.js) is reported and left alone; an anchor found 2+ times refuses (K2).
    rewardguard3x            parts/rewarded-guard.js, line AFTER web-adapter.js (3.x only, 生成时预防 R4G2; 2.4 gets
                             it from the kit main.js v1.7)
    2.4 source phase: the editor writes game.js at build time, so only host-shim.js reaches build-templates/bytedance
    (build_templates step, part template); the game.js line is written by native / sync --native.
"""
import re

from . import (KitError, MAIN_REQUIRE, Result, STOCK_ROOT_JS, anchors, install_part, is_engine_or_adapter,
               kit_main_current, kit_main_versions, kit_lines, live_matches, neutralize, part_action, part_facts,
               part_findings, require_rx, self_check, sha256, step_parts, text_of, wire_line, wirings)

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


# ---------------------------------------------------------------- 生成时预防 R4B: host shim + 3.x startup guard
EARLY_STEPS = ('hostshim', 'boot',
               'rewardguard')   # 生成时预防 R4G2: 3.x rewarded-ad guard (part rewardguard3x, after web-adapter)
TEMPLATE_DIR3 = 'build-templates/bytedance-mini-game/'
TEMPLATE_GAMES3 = ('game.js', 'game.ejs')
OWN_BOOT_FILES = re.compile(r'^(?:boot-loading|native-recovery)\.js$')


def early_parts(manifest, engine):
    out = []
    for step in EARLY_STEPS:
        out += step_parts(manifest, step, engine)
    return out


def is_boot(name, part):
    return part.get('step') == 'boot' or name == 'boot3x'


def own_boot_page(files, manifest, part):
    """-> [why] when a 3.x game has its own start page (LunasJade boot-loading.js / native-recovery.js): game.js
    loads it on a live line, a root file has its name, or a root file carries the part's own_markers. The kit guard
    itself and other kit part files never count; a copy of the kit's reference boot-loading.js does (it IS a page)."""
    pats = [re.compile(p) for p in part.get('own_markers') or []]
    dests = {(p.get('file') or {}).get('dest') for p in manifest.parts.values()}
    out = []
    game = text_of(files.get('game.js'))
    for p in pats:
        if live_matches(game, p):
            out.append('game.js /%s/' % p.pattern)
    for rel, data in sorted(files.items()):
        if '/' in rel or not rel.endswith('.js') or rel == 'game.js' or rel in dests or is_engine_or_adapter(rel):
            continue
        if OWN_BOOT_FILES.search(rel):
            out.append(rel)
        elif any(p.search(text_of(data)) for p in pats):
            out.append(rel)
    return out


def _anchor_of(wiring):
    return wiring.get('insert_before') or wiring.get('insert_after')


def install_early(ctx, r):
    """Native phase: install host-shim (+ boot3x on 3.x) in the build folder. Writes into r (r.state untouched)."""
    for name, part in early_parts(ctx.manifest, ctx.engine):
        files = ctx.files()
        f = part_facts(files, ctx.manifest, name, part, ctx.engine)
        if is_boot(name, part):
            own = own_boot_page(files, ctx.manifest, part)
            if own:
                r.warn('K_W_own_startup', '%s not installed: the game has its own start page (%s); the kit startup '
                       'guard is never stacked on it' % (name, ', '.join(own)), {'part': name, 'own': own})
                continue
        action = part_action(part, ctx.policy, 'replace' if ctx.policy == 'new' else 'skip')
        if action == 'skip':
            r.info.append('%s not installed (%s game: report only; %s)' % (
                name, ctx.policy, 'game.js already loads it' if f['marked'] or f['plain'] else 'state ' + f['state']))
            continue
        game_w = wirings(part, ctx.engine, 'game.js')
        if not f['marked'] and not f['plain'] and game_w and not anchors(f['game'], _anchor_of(game_w[0]))[0]:
            r.warn('K_W_startup_anchor', '%s not installed: game.js has no /%s/ (not a stock Cocos mini-game '
                   "game.js); hand it to this game's session" % (name, _anchor_of(game_w[0])), {'part': name})
            continue
        sub = Result(STEP)
        install_part(ctx, sub, name, part, action)
        r.changed += sub.changed
        r.blocks += sub.blocks
        r.warnings += sub.warnings
        r.info += sub.info
        if not sub.blocks:
            self_check(ctx, r, [(name, part)], 'new')


def _template_files3(ctx):
    base = ctx.path(TEMPLATE_DIR3)
    if not base.is_dir():
        return {}
    return {p.name: p.read_bytes() for p in sorted(base.iterdir()) if p.is_file() and not p.name.startswith('.')}


def apply_source(ctx):
    """Source phase (and sync): wire the 3.x build-template game.js / game.ejs when the project has one."""
    from .build_templates import applies
    r = Result(STEP)
    r.state = 'n/a'
    parts = early_parts(ctx.manifest, ctx.engine) if ctx.engine in (2, 3) else []
    if not parts:
        return r.as_dict()
    if ctx.engine == 2:
        r.info.append('2.4: host-shim.js comes with build-templates/bytedance; its game.js line is written by '
                      '`native` / `sync --native` (the editor writes game.js)')
        return r.as_dict()
    tmpl = _template_files3(ctx)
    games = [g for g in TEMPLATE_GAMES3 if g in tmpl]
    if not games:
        r.info.append('no %sgame.js: the load lines are written by `native` / `sync --native`' % TEMPLATE_DIR3)
        return r.as_dict()
    states = []
    for g in games:
        rel = TEMPLATE_DIR3 + g
        text = text_of(tmpl[g])
        new = text
        for name, part in parts:
            if is_boot(name, part):
                own = own_boot_page(dict(tmpl, **{'game.js': new.encode('utf-8')}), ctx.manifest, part)
                if own:
                    r.warn('K_W_own_startup', '%s not wired in %s: the game has its own start page (%s)'
                           % (name, rel, ', '.join(own)), {'part': name, 'own': own})
                    continue
            if ctx.policy != 'new' or not applies(ctx) or \
                    part_action(part, ctx.policy, 'replace') == 'skip':
                r.info.append('%s: %s not wired (%s; report only)' % (rel, name, 'legacy game' if ctx.policy != 'new'
                                                                   else 'localize board: original templates kept'))
                states.append('kit_current' if kit_lines(new, name) else 'absent')
                continue
            game_w = wirings(part, 3, 'game.js')
            if not game_w:
                continue
            trial, state, detail = wire_line(new, name, ctx.manifest.version, game_w[0])
            if state == 'conflict':
                if not anchors(new, _anchor_of(game_w[0]))[0]:
                    r.info.append('%s: %s not wired (%s); `native` writes it in the build game.js' % (rel, name, detail))
                else:
                    r.block('K2_kit_wiring', '%s: %s' % (rel, detail), {'part': name, 'file': rel})
                continue
            states.append(state)
            new = trial
        if new != text and not r.blocks:
            ctx.write(rel, new.encode('utf-8'))
            r.change(rel, tmpl[g], new.encode('utf-8'), 'host-shim / boot-guard load line in the build template')
    r.state = 'absent' if r.changed else ('kit_current' if states and all(s == 'kit_current' for s in states)
                                          else r.state)
    return r.as_dict()


def detect(ctx):
    if ctx.phase == 'source':
        return 'n/a' if ctx.engine != 3 or not _template_files3(ctx) else 'report'
    if ctx.engine != 2:
        return 'n/a'
    files = ctx.files()
    state = main_state(files, ctx.manifest)
    return 'own' if state == 'kit_current' and own_startup(files, ctx.manifest, 2) else state


def apply(ctx):
    if ctx.phase == 'source':
        return apply_source(ctx)
    r = Result(STEP)
    files = ctx.files()
    if ctx.engine != 2:
        r.state = 'n/a'
        for rel in own_startup(files, ctx.manifest, ctx.engine) if ctx.engine == 3 else []:
            r.warn('K_W_own_startup', 'own startup file %s kept (the kit 3.x startup guard is boot3x); hand it to '
                   "this game's session" % rel, {'file': rel})
        if ctx.engine == 3:
            install_early(ctx, r)
            if r.changed:
                r.state = 'absent'
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
        install_early(ctx, r)      # report only (policy legacy = report)
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
    install_early(ctx, r)
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
    if policy == 'new' and engine in (2, 3):
        # R4B: a host-shim / boot3x that is present must be the kit file, loaded once, before its anchor. Not required
        # (a package built before R4B has none); finalize's own self-check requires it for the games it installs.
        for name, part in early_parts(manifest, engine):
            if is_boot(name, part) and own_boot_page(root, manifest, part):
                continue
            out += part_findings(files, manifest, name, part, engine, policy, required=False)
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
