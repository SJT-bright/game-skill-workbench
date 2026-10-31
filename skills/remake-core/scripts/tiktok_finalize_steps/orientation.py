"""Source step: the game is designed portrait (v7.8, 总表 B31; 切水果 v1 went out landscape). Read only.

Blocks in both policies (new and legacy games alike), before the Cocos build:
    K_portrait_design  a cc.Canvas in any scene (.fire/.scene) or prefab under assets/ has _designResolution wider
                       than high, or the Cocos 3.x project setting settings/v2/packages/project.json
                       general.designResolution is wider than high.
Warnings (the step cannot confirm portrait, it does not guess):
    K_W_portrait_unreadable  a scene/prefab under assets/ is not readable JSON.
    K_W_portrait_unknown     no design resolution found at all (no cc.Canvas with _designResolution, no 3.x setting).
The block lands in the source record, so both package writers refuse the build (K5_source_finalized). The package
half (game.json deviceOrientation) is package_gates/portrait.py.
"""
import json

from . import Result, finding

STEP = 'orientation'
SCENE_SUFFIXES = ('.fire', '.scene', '.prefab')
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', '.tiktok-kit', '__MACOSX'}
SETTINGS_3X = 'settings/v2/packages/project.json'


def _size(node):
    if isinstance(node, dict):
        w, h = node.get('width'), node.get('height')
        if isinstance(w, (int, float)) and isinstance(h, (int, float)) and not isinstance(w, bool) \
                and not isinstance(h, bool):
            return w, h
    return None


def _canvas_sizes(data):
    """[(width, height)] of every cc.Canvas with a _designResolution in one serialized scene/prefab."""
    items = data if isinstance(data, list) else [data]
    out = []
    for obj in items:
        if isinstance(obj, dict) and obj.get('__type__') == 'cc.Canvas':
            size = _size(obj.get('_designResolution'))
            if size:
                out.append(size)
    return out


def scan(files):
    """files {posix relpath (project relative): bytes}. -> {'checked': [...], 'landscape': [...], 'unreadable': [...]}"""
    checked, landscape, unreadable = [], [], []
    for rel in sorted(files):
        parts = rel.split('/')
        if rel.endswith(SCENE_SUFFIXES) and parts[0] == 'assets' and not SKIP_DIRS & set(parts):
            try:
                data = json.loads(files[rel].decode('utf-8-sig'))
            except (ValueError, UnicodeDecodeError):
                unreadable.append(rel)
                continue
            for w, h in _canvas_sizes(data):
                item = {'file': rel, 'width': w, 'height': h}
                checked.append(item)
                if w > h:
                    landscape.append(item)
        elif rel == SETTINGS_3X:
            try:
                general = json.loads(files[rel].decode('utf-8-sig')).get('general') or {}
                size = _size(general.get('designResolution'))
            except (ValueError, UnicodeDecodeError, AttributeError):
                unreadable.append(rel)
                continue
            if size:
                item = {'file': rel, 'width': size[0], 'height': size[1]}
                checked.append(item)
                if size[0] > size[1]:
                    landscape.append(item)
    return {'checked': checked, 'landscape': landscape, 'unreadable': unreadable}


def _project_files(ctx):
    out = {}
    for top in ('assets', 'settings'):
        base = ctx.root / top
        if not base.is_dir():
            continue
        for p in sorted(base.rglob('*')):
            rel = p.relative_to(ctx.root).as_posix()
            if p.is_file() and not p.is_symlink() and not SKIP_DIRS & set(rel.split('/')) and (
                    rel.endswith(SCENE_SUFFIXES) or rel == SETTINGS_3X):
                out[rel] = p.read_bytes()
    return out


def verify(files, manifest=None, policy=None):
    """Read-only findings on {relpath: bytes} of a project (both policies)."""
    return _findings(scan(files))


def _findings(found):
    out = []
    if found['landscape']:
        shown = ', '.join('%s %sx%s' % (i['file'], i['width'], i['height']) for i in found['landscape'][:5])
        out.append(finding('K_portrait_design', 'block', '%d design resolution(s) wider than high (%s): every TikTok '
                           'mini-game must be portrait. Set each cc.Canvas design resolution (3.x: Project Settings '
                           'designResolution) taller than wide, re-lay the scenes and run the source phase again'
                           % (len(found['landscape']), shown), found['landscape'][:20]))
    if found['unreadable']:
        out.append(finding('K_W_portrait_unreadable', 'warn', '%d scene/prefab/setting file(s) not readable as JSON, '
                           'design resolution not checked: %s' % (len(found['unreadable']),
                                                                  ', '.join(found['unreadable'][:5])),
                           found['unreadable'][:20]))
    if not found['checked']:
        out.append(finding('K_W_portrait_unknown', 'warn', 'no cc.Canvas design resolution and no 3.x '
                           'designResolution setting found under assets/ and settings/; portrait not confirmed at the '
                           'source (the package gate still checks game.json deviceOrientation)'))
    return out


def _state(found):
    if found['landscape']:
        return 'conflict'
    return 'kit_current' if found['checked'] else 'n/a'


def detect(ctx):
    return _state(scan(_project_files(ctx)))


def apply(ctx):
    r = Result(STEP)
    found = scan(_project_files(ctx))
    for item in _findings(found):
        (r.blocks if item['level'] == 'block' else r.warnings).append(item)
    r.state = _state(found)
    r.info.append('design resolutions checked: %d' % len(found['checked']))
    return r.as_dict()
