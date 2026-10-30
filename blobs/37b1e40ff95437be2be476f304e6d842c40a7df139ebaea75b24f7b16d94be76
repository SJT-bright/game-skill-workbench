"""Native step: project.config.json carries this game's App ID (design D77 1.3 row appid.py, 3.8). Both policies.

Expected App ID, in this order: the writer's --app-id (ctx.app_id), else PlatformConfig.js `appId` in the
project (assets/tiktok-platform/PlatformConfig.js, or PlatformConfig.plugin.js for 3.x), else ~/.game-skill/
ad-config.json `appId` (ctx.options['ad_config'] overrides the path). --app-id that differs from PlatformConfig.js
blocks; no usable App ID blocks; a test / tourist / empty appid is never accepted. Only the value is rewritten, the
rest of the file keeps its bytes, so a second run changes nothing.
"""
import json
import re
from pathlib import Path

from . import Result, text_of

STEP = 'appid'
PLATFORM_CONFIG = ('assets/tiktok-platform/PlatformConfig.js', 'assets/tiktok-platform/PlatformConfig.plugin.js')
APPID_JS = re.compile(r'\bappId\s*:\s*[\'"]([^\'"]*)[\'"]')
APPID_JSON = re.compile(r'("appid"\s*:\s*)"([^"]*)"')
VALID = re.compile(r'^\d{10,25}$')


def platform_config_app_id(project):
    if not project:
        return None
    for rel in PLATFORM_CONFIG:
        p = Path(project) / rel
        if p.is_file():
            m = APPID_JS.search(p.read_text(encoding='utf-8', errors='replace'))
            if m:
                return m.group(1)
    return None


def ad_config_app_id(options):
    path = Path(options.get('ad_config') or Path.home() / '.game-skill' / 'ad-config.json')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    value = data.get('appId') if isinstance(data, dict) else None
    return str(value) if value else None


def expected(ctx):
    """-> (app_id or None, source, findings)"""
    pc = platform_config_app_id(ctx.project)
    out = []
    if ctx.app_id and pc and str(ctx.app_id) != pc:
        out.append({'id': 'K_appid_mismatch', 'level': 'block', 'message': '--app-id %s differs from PlatformConfig.js '
                    'appId %s' % (ctx.app_id, pc), 'evidence': {'app_id': ctx.app_id, 'platform_config': pc}})
    for value, source in ((ctx.app_id, '--app-id'), (pc, 'PlatformConfig.js'),
                          (ad_config_app_id(ctx.options), '~/.game-skill/ad-config.json')):
        if value:
            value = str(value)
            if not VALID.match(value):
                out.append({'id': 'K_appid_invalid', 'level': 'block', 'message': 'App ID from %s is not a TikTok App '
                            'ID: %r' % (source, value)})
                return None, source, out
            return value, source, out
    out.append({'id': 'K_appid_missing', 'level': 'block', 'message': 'no App ID: pass --app-id, or set appId in '
                'PlatformConfig.js / ~/.game-skill/ad-config.json'})
    return None, None, out


def verify(files, manifest=None, policy=None, app_id=None):
    raw = files.get('project.config.json')
    if raw is None:
        return [{'id': 'K_appid_missing', 'level': 'block', 'message': 'project.config.json missing'}]
    m = APPID_JSON.search(text_of(raw))
    value = m.group(2) if m else None
    if not value or not VALID.match(value):
        return [{'id': 'K_appid_invalid', 'level': 'block', 'message': 'project.config.json appid is %r' % (value,)}]
    if app_id and value != str(app_id):
        return [{'id': 'K_appid_mismatch', 'level': 'block', 'message': 'project.config.json appid %s, expected %s'
                 % (value, app_id)}]
    return []


def detect(ctx):
    value, _, _ = expected(ctx)
    return 'kit_current' if value and not verify(ctx.files(root_only=True), app_id=value) else 'absent'


def apply(ctx):
    r = Result(STEP)
    value, source, problems = expected(ctx)
    for item in problems:
        r.blocks.append(item)
    if not value or r.blocks:
        r.state = 'conflict'
        return r.as_dict()
    raw = ctx.read('project.config.json')
    if raw is None:
        r.block('K_appid_missing', 'project.config.json missing in the build')
        return r.as_dict()
    text = text_of(raw)
    found = list(APPID_JSON.finditer(text))
    if len(found) > 1:
        r.block('K_appid_invalid', 'project.config.json has %d "appid" keys' % len(found))
        return r.as_dict()
    if found and found[0].group(2) == value:
        r.state = 'kit_current'
    else:
        if found:
            new = text[:found[0].start()] + found[0].group(1) + '"%s"' % value + text[found[0].end():]
        else:
            data = json.loads(text)
            data['appid'] = value
            new = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
        ctx.write('project.config.json', new.encode('utf-8'))
        r.change('project.config.json', raw, new.encode('utf-8'), 'appid %s -> %s (from %s)'
                 % (found[0].group(2) if found else None, value, source))
        r.state = 'absent' if not found else 'own'
    for item in verify(ctx.files(root_only=True), app_id=value):
        r.blocks.append(dict(item, message='after write: ' + item['message']))
    r.info.append('appid %s from %s' % (value, source))
    return r.as_dict()
