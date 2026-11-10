"""Source step: a NEW Cocos 2.4 game that uses physics gets the platform-kit physics clock (v7.8, 总表 P16 第 1 步).

Why: without enabledAccumulator the 2.4 PhysicsManager steps 1/60 s on every frame, so on a 120 Hz screen the physics
world runs twice as fast (全民飞车漂移 v3.1: RunUI.ts:145 only `enabled = true`; Pizza Drift on the same base fell off at
the first corner). The kit part parts/PhysicsClock.js sets cc.director.getPhysicsManager().enabledAccumulator = true at
load and before every scene launch, and gives Clock.scale(dt) / Clock.force(v, dt) for the game's pushes.

    new game, 2.4, a script switches physics on (logic_check PHYS_ON / alias), no enabledAccumulator = true in the game:
        assets/tiktok-platform/PhysicsClock.js added (or restored to the kit bytes; an own copy moves to
        .tiktok-kit/removed/); info: the pushes are still the game's code (logic_check L-FPS-DT lists them, the runtime
        suite frame_rate decides).
    legacy game: nothing is written (its feel was tuned and tested the old way); warning K_W_physics_clock_legacy when
        the same condition holds.
    game sets enabledAccumulator itself, no physics, or Cocos 3.x (fixed-step physics): n/a, nothing written.
    a game script of its own named PhysicsClock (2.4 module names are global): not installed, warning
        K_W_physics_clock_name (the frame_rate suite still judges the game).
Never blocks: the runtime suite frame_rate is the final judge (new game blocks there).
"""
from . import KitError, Result, sha256

STEP = 'physics_clock'
KIT_KEY = 'parts/PhysicsClock.js'
DEST = 'assets/tiktok-platform/PhysicsClock.js'


def _rules():
    import logic_check            # one definition of "physics switched on" (L-FPS-ACCUM, W86)
    return logic_check


def scan(ctx):
    """-> {'physics': [files], 'accumulator': [files], 'own_name': [files]} over the game's scripts (kit folder left out)."""
    lc = _rules()
    files = [(rel, code) for rel, code in lc.scripts(ctx.root) if not rel.startswith('assets/tiktok-platform/')]
    aliases = {m.group(1) for _, c in files for m in lc.PHYS_ALIAS.finditer(c)}
    alias_on = None
    if aliases:
        import re
        alias_on = re.compile(r'(?<![\w.$])(?:%s)\s*\.enabled\s*=\s*(?:true|!0)\b' % '|'.join(map(re.escape, sorted(aliases))))
    physics = [rel for rel, code in files if lc.PHYS_ON.search(code) or (alias_on and alias_on.search(code))]
    accumulator = [rel for rel, code in files if lc.PHYS_ACCUM.search(code)]
    own_name = [rel for rel, _ in files if rel.rsplit('/', 1)[-1] in ('PhysicsClock.js', 'PhysicsClock.ts')]
    return {'physics': physics, 'accumulator': accumulator, 'own_name': own_name}


def kit_bytes(manifest):
    spec = (manifest.files or {}).get(KIT_KEY)
    if not isinstance(spec, dict) or not spec.get('sha256'):
        raise KitError('KIT_MANIFEST has no %s' % KIT_KEY)
    path = manifest.kit_dir / KIT_KEY
    if not path.is_file():
        raise KitError('kit file missing: %s' % KIT_KEY)
    data = path.read_bytes()
    if sha256(data) != spec['sha256']:
        raise KitError('kit file %s differs from KIT_MANIFEST' % KIT_KEY)
    return data


def _needed(found):
    return bool(found['physics']) and not found['accumulator']


def detect(ctx):
    if ctx.engine != 2:
        return 'n/a'
    found = scan(ctx)
    if not _needed(found):
        return 'n/a'
    have = ctx.read(DEST)
    if have is None:
        return 'absent'
    return 'kit_current' if have == kit_bytes(ctx.manifest) else 'own'


def apply(ctx):
    r = Result(STEP)
    if ctx.engine != 2:
        r.state = 'n/a'
        r.info.append('Cocos %s: physics steps on a fixed clock already' % ctx.engine)
        return r.as_dict()
    found = scan(ctx)
    if not found['physics']:
        r.state = 'n/a'
        r.info.append('no script switches 2.4 physics on')
        return r.as_dict()
    if found['accumulator']:
        r.state = 'n/a'
        r.info.append('the game sets enabledAccumulator itself (%s)' % ', '.join(found['accumulator'][:3]))
        return r.as_dict()
    where = ', '.join(found['physics'][:3])
    if ctx.policy == 'legacy':
        r.state = 'n/a'
        r.warn('K_W_physics_clock_legacy', '2.4 physics on (%s) without enabledAccumulator: physics runs faster on a '
               '120 Hz screen. Legacy game: left as is (its feel was tested this way); the runtime suite frame_rate '
               'warns' % where, {'files': found['physics'][:10]})
        return r.as_dict()
    if found['own_name']:
        r.state = 'conflict'
        r.warn('K_W_physics_clock_name', 'game script %s is named PhysicsClock (Cocos 2.4 module names are global): the '
               'kit physics clock was not added. Set cc.director.getPhysicsManager().enabledAccumulator = true yourself '
               'and scale the pushes by dt; the runtime suite frame_rate decides' % ', '.join(found['own_name']))
        return r.as_dict()
    try:
        kit = kit_bytes(ctx.manifest)
    except KitError as error:
        r.block('K_kit_unusable', str(error))
        return r.as_dict()
    have = ctx.read(DEST)
    if have == kit:
        r.state = 'kit_current'
    else:
        if have is not None:
            moved = ctx.move_away(DEST)
            r.info.append('moved own %s to %s' % (DEST, moved))
        ctx.write(DEST, kit)
        r.change(DEST, have, kit, 'physics clock (enabledAccumulator on) %s' % ('restored' if have is not None else 'added'))
        r.state = 'own' if have is not None else 'absent'
        if ctx.read(DEST) != kit:
            r.block('K1_kit_bytes', 'kit file did not verify after install: %s' % DEST)
    r.info.append('2.4 physics on in %s: enabledAccumulator now comes from %s. The pushes are still the game\'s code: '
                  'scale each per-call push by dt (Clock.force(v, dt), Clock.scale(dt)); logic_check L-FPS-DT lists them, '
                  'the runtime suite frame_rate (60 Hz vs 120 Hz, 5 %%) decides' % (where, DEST))
    return r.as_dict()


def verify(ctx):
    """Read-only findings for a project: a new 2.4 physics game without the accumulator and without the kit file."""
    if ctx.engine != 2 or ctx.policy != 'new':
        return []
    found = scan(ctx)
    if not _needed(found) or found['own_name']:
        return []
    have = ctx.read(DEST)
    if have is not None and have == kit_bytes(ctx.manifest):
        return []
    return [{'id': 'K_physics_clock', 'level': 'warn', 'message': '2.4 physics on (%s) without enabledAccumulator and '
             'without %s: run tiktok_finalize.py source' % (', '.join(found['physics'][:3]), DEST)}]
