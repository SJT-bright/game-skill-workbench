"""Native step: one silent login at startup (design D77 1.3 row login.py, 3.8). Check only, never writes.

Cocos 2.4: the kit main.js v1.3 sends it (startup24 `checks` entry id 'login': its kit_line must be in main.js).
    new policy: kit main.js with that line = proven. An editor main.js kept for R4 is fine when the game JS calls
    login itself; no login anywhere blocks (K2_login).
Cocos 3.x: v7.7 has no 3.x login part unless the manifest names one (step 'login', engine 3); without it a missing
    login is a warning (the kit cannot supply it yet).
legacy policy: a missing login is a warning (W2_login stays a warning, as in v7.5).
"""
import re

from . import Result, is_engine_or_adapter, kit_main_current, sha256, step_parts, text_of

STEP = 'login'
LOGIN = re.compile(r'\.login\s*\(|\[\s*["\']login["\']\s*\]')


def kit_login_line(manifest):
    for _, part in step_parts(manifest, 'startup', 2):
        for check in part.get('checks') or []:
            if check.get('id') == 'login' and check.get('kit_line'):
                return check['kit_line']
    return None


def facts(files, manifest, engine):
    main = files.get('main.js')
    line = kit_login_line(manifest) if engine == 2 else None
    kit_main = main is not None and sha256(main) == kit_main_current(manifest)
    by_kit = bool(kit_main and line and line in text_of(main))
    by_part = bool(step_parts(manifest, STEP, engine))
    own = sorted(rel for rel, data in files.items() if rel.endswith('.js') and not is_engine_or_adapter(rel)
                 and LOGIN.search(text_of(data)))
    return {'by_kit': by_kit, 'kit_has_part': by_part or bool(line), 'calls': own}


def verify(files, manifest, policy, engine=None):
    from .policy import engine_of_names
    engine = engine or engine_of_names(files)
    if engine not in (2, 3):
        return []
    f = facts(files, manifest, engine)
    if f['by_kit'] or f['calls']:
        return []
    if policy == 'new' and f['kit_has_part']:
        return [{'id': 'K2_login', 'level': 'block', 'message': 'no silent login at startup: main.js is not the kit '
                 'main.js with its login line and no game JS calls login', 'evidence': {'engine': engine}}]
    return [{'id': 'K_W_login', 'level': 'warn', 'message': 'no TikTok login call in the package (%s)' % (
        'legacy game' if policy == 'legacy' else 'the kit has no Cocos 3.x login part yet'),
        'evidence': {'engine': engine}}]


def detect(ctx):
    if ctx.engine not in (2, 3):
        return 'n/a'
    f = facts(ctx.files(), ctx.manifest, ctx.engine)
    return 'kit_current' if f['by_kit'] else ('own' if f['calls'] else 'absent')


def apply(ctx):
    r = Result(STEP)
    files = ctx.files()
    r.state = detect(ctx)
    for item in verify(files, ctx.manifest, ctx.policy, ctx.engine):
        (r.blocks if item['level'] == 'block' else r.warnings).append(item)
    return r.as_dict()
