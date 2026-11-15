"""Source step: build settings carry the App ID (design D77 1.3 row settings.py).

Cocos 2.4: settings/bytedance.json. new policy: appid, startSceneAssetBundle false, REMOTE_SERVER_ROOT "".
    legacy policy: appid only. The file is created when missing; other keys keep their values and order.
Cocos 3.x: Creator 3.x keeps the ByteDance build options in profiles/v2/packages/bytedance-mini-game.json, which
    source ZIPs do not carry (Marlows R6 source: only settings/v2/packages/{builder,engine,...}.json). When that file
    exists its "appid" values are set; otherwise nothing is written here and the native step appid.py writes
    project.config.json after the build.
App ID source order: see appid.expected().
"""
import json

from . import Result
from .appid import expected

STEP = 'settings'
BYTEDANCE_24 = 'settings/bytedance.json'
BYTEDANCE_3X = 'profiles/v2/packages/bytedance-mini-game.json'


def wanted(ctx, app_id):
    if ctx.policy == 'new':
        return {'appid': app_id, 'startSceneAssetBundle': False, 'REMOTE_SERVER_ROOT': ''}
    return {'appid': app_id}


def _set_appid(node, app_id, depth=0):
    count = 0
    if isinstance(node, dict) and depth < 6:
        for key, value in node.items():
            if key == 'appid' and isinstance(value, str):
                if value != app_id:
                    node[key] = app_id
                count += 1
            else:
                count += _set_appid(value, app_id, depth + 1)
    return count


def detect(ctx):
    rel = BYTEDANCE_24 if ctx.engine == 2 else BYTEDANCE_3X
    raw = ctx.read(rel)
    if raw is None:
        return 'absent'
    value, _, _ = expected(ctx)
    try:
        data = json.loads(raw.decode('utf-8-sig'))
    except (ValueError, UnicodeDecodeError):
        return 'conflict'
    if ctx.engine == 2:
        return 'kit_current' if all(data.get(k) == v for k, v in wanted(ctx, value).items()) else 'own'
    return 'kit_current' if value and _set_appid(json.loads(raw.decode('utf-8-sig')), value) else 'own'


def apply(ctx):
    r = Result(STEP)
    value, source, problems = expected(ctx)
    r.blocks += [p for p in problems if p['level'] == 'block']
    if not value or r.blocks:
        r.state = 'conflict'
        return r.as_dict()
    rel = BYTEDANCE_24 if ctx.engine == 2 else BYTEDANCE_3X if ctx.engine == 3 else None
    if rel is None:
        r.block('K_engine_unknown', 'Cocos version of the project not readable (project.json / package.json)')
        return r.as_dict()
    raw = ctx.read(rel)
    if raw is None and ctx.engine == 3:
        r.state = 'n/a'
        r.info.append('%s not in the project (normal for 3.x sources); appid.py writes project.config.json' % rel)
        return r.as_dict()
    try:
        data = json.loads(raw.decode('utf-8-sig')) if raw is not None else {}
    except (ValueError, UnicodeDecodeError) as error:
        r.block('K_settings_unreadable', '%s unreadable: %s' % (rel, error))
        return r.as_dict()
    before = json.dumps(data, sort_keys=True)
    if ctx.engine == 2:
        data.update(wanted(ctx, value))
    elif not _set_appid(data, value):
        r.warn('K_W_settings_no_appid', '%s has no appid field; appid.py writes project.config.json' % rel)
    if raw is None or json.dumps(data, sort_keys=True) != before:
        new = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        ctx.write(rel, new)
        r.change(rel, raw, new, 'appid %s (from %s)%s' % (value, source, ', startSceneAssetBundle false, '
                                                          'REMOTE_SERVER_ROOT ""' if ctx.engine == 2 and
                                                          ctx.policy == 'new' else ''))
    r.state = 'kit_current' if not r.changed else ('absent' if raw is None else 'own')
    return r.as_dict()
