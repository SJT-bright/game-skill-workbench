"""Native step: rewarded-ad guard rewarded-guard.js (生成时预防 R4F1, plan P01 point 2; R4A left it unwired).

Part: rewarded24 (KIT_MANIFEST, STEP_ALIASES 'rewarded'). The kit main.js v1.7 already requires it (kit_line) and
startup24.extra_files ships the file next to it, so for a kit-main package this step only confirms it and writes
nothing: no second load line. A 2.4 package that keeps its own main.js (an engine version outside
startup24.needs.engine_versions) gets the file plus one marked line in game.js right after
__globalAdapter.adaptEngine(), before main.js and every game script (same anchor as storage24).
new policy:    installed (new games and English packages that are not on the legacy list).
legacy policy: not installed; a line finalize itself inserted earlier is still checked.
Cocos 3.x: no part yet (a rewarded3x part is R4G2's), so the step is n/a there and never blocks a 3.x build.
"""
from . import Result, part_step_detect, part_step_verify, run_part_step, step_parts

STEP = 'rewarded'
DEFAULTS = {'new': 'replace', 'legacy': 'skip'}


def detect(ctx):
    return part_step_detect(ctx, STEP)


def apply(ctx):
    if ctx.engine in (2, 3) and not step_parts(ctx.manifest, STEP, ctx.engine):
        r = Result(STEP)
        r.state = 'n/a'
        r.info.append('no rewarded-guard part for Cocos %s in KIT_MANIFEST' % ('2.4' if ctx.engine == 2 else '3.x'))
        return r.as_dict()
    return run_part_step(ctx, STEP, DEFAULTS, 'rewarded-ad guard')


def verify(files, manifest, policy, engine=None):
    return part_step_verify(files, manifest, policy, STEP, engine)
