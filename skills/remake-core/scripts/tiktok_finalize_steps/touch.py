"""Native step: touch coordinates (design D77 1.3 row touch.py, 3.1).

Parts: manifest parts with step 'touch' (touch24 = touch-coordinates.js, touch3x = tiktok-touch-3x.js).
2.4 with the kit main.js: main.js already has the kit_line, so only the file is placed (and game.js must require
    './main'). Otherwise one marked line goes next to the manifest anchor in game.js (2.4: after
    __globalAdapter.adaptEngine(); 3.x: before require('./web-adapter')).
new policy:    own touch layers (own_markers, not a kit hash) at the package root are moved to .tiktok-kit-removed and
               their single-statement load line is commented out; an own layer that cannot be taken out blocks.
legacy policy: added only when the game has no touch layer at all; an own layer stays (warning).
"""
from . import part_step_detect, part_step_verify, run_part_step

STEP = 'touch'
DEFAULTS = {'new': 'replace', 'legacy': 'add_if_absent'}


def detect(ctx):
    return part_step_detect(ctx, STEP)


def apply(ctx):
    return run_part_step(ctx, STEP, DEFAULTS, 'touch coordinates')


def verify(files, manifest, policy, engine=None):
    return part_step_verify(files, manifest, policy, STEP, engine)
