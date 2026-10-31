"""Native step: storage layer storage-guard.js (design D77 1.3 row storage.py, 3.4, Q6).

Parts: manifest parts with step 'storage'. 2.4 with the kit main.js v1.3: main.js loads it (kit_line), only the
file is placed. Otherwise one marked line in game.js at the manifest anchor (2.4: after adaptEngine, cc exists;
3.x: per manifest wiring).
new policy:    installed; an own storage layer at the package root (e.g. an older storage-guard.js that is no kit
               version) is replaced, a second layer elsewhere blocks (K3).
legacy policy: not installed (Q6: old games get it only after `tiktok_finalize.py adopt`); a line finalize itself
               inserted earlier is still checked.
"""
from . import part_step_detect, part_step_verify, run_part_step

STEP = 'storage'
DEFAULTS = {'new': 'replace', 'legacy': 'skip'}


def detect(ctx):
    return part_step_detect(ctx, STEP)


def apply(ctx):
    return run_part_step(ctx, STEP, DEFAULTS, 'storage layer')


def verify(files, manifest, policy, engine=None):
    return part_step_verify(files, manifest, policy, STEP, engine)
