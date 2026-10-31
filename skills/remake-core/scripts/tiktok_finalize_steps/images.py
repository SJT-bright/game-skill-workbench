"""tiktok_finalize step `images` (SOURCE phase, v7.7 design 1.3 row 1, 3.6).

Runs on the Cocos project before the Creator build, so the editor re-imports the changed art.
New-game policy:
  - every assets/**/*.webp becomes .png (has transparent pixels) or .jpg (opaque, quality 88);
    its .webp.meta is renamed with the uuid kept (3.x: the "files" extension list follows);
  - a texture-compression setting that makes the build emit WebP is turned off
    (2.4 .meta platformSettings formats "webp"; 3.x .meta userData.compressSettings with a preset whose
    miniGame options contain webp);
  - a texture larger than 2x its display size on BOTH axes is shrunk to exactly 2x (display size taken the
    way audit_image_clarity.py takes it), only when shrinking cannot change what is shown (see _resize_safety);
  - originals go to <project>/.tiktok-kit/originals/<relative path> (first copy kept, never overwritten).
Legacy policy: nothing is changed; WebP that stays must pass the standard probe gate (package_gates/webp.py G4).

The PNG written here is lossless. 256-colour quantisation (pngquant) happens once, on the build output, in
png.py, so an image listed in image-overrides.json as "quantize": false really stays unquantised (R7).

<project>/.tiktok-kit/image-overrides.json (optional, Q3: banded images handled one by one):
  {"images": {"assets/ui/bg.webp": {"format": "jpg", "jpg_quality": 95},
              "assets/ui/sky.png":  {"quantize": false},
              "assets/ui/hero.webp": {"resize": false}}}
  key = path relative to the project (the .webp path before conversion or the .png/.jpg after), or a glob
  with * / ? (used when no exact key matches); format png|jpg, jpg_quality 60-100, quantize true|false
  (read by png.py), resize true|false, max_side 64-8192 (explicit shrink of an image the automatic rule
  leaves alone, e.g. art loaded by code: Q4 "shrink first"; every frame's geometry is scaled with it).

Option keep_webp_exception=<reason> (Q4, only after shrinking still leaves the package over 30 MB): a new
game keeps its .webp files unconverted and gets a warning; the native phase must install the standard
probe (KIT_MANIFEST part webp_probe24), otherwise verify() blocks the package. Cocos 2.4 only: on a 3.x project the
option is refused (DECISIONS 13:25: no 3.x probe in v7.7; 3.x gets under 30 MB with PNG/JPG and max_side).

Hard-coded .webp in game data (W-D4 request 2, v7.7 wave 3): when a new game's conversion or compression switch-off
changes anything, every ".webp" / '.webp' string literal in assets/**/*.json|.ts|.js (not .meta) and every .json path
string ending in .webp blocks (IMG0_source_images, file and line, use ".png"/".jpg"), e.g. Marlows R6's art manifest
"imageExt": ".webp" (the build then had no .webp and 19 images failed to load). A format list that also names
".png"/".jpg" close by is not reported. With keep_webp_exception, and for legacy games, these are warnings. Game data is
never rewritten automatically.

Step interface (design 1.4): detect(ctx) -> state, apply(ctx) -> {changed, blocks, warnings}, verify(view).
ctx may be an object or a dict with: project, engine (2|3, else detected), policy ('new'|'legacy'),
board, options (dict, see DEFAULTS).
"""
import hashlib
import io
import json
import re
import shutil
import sys
from pathlib import Path

PART = 'images'
PHASE = 'source'
KIT_DIR = '.tiktok-kit'
OVERRIDES = 'image-overrides.json'
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles', KIT_DIR}

DEFAULTS = {
    'jpg_quality': 88,          # opaque WebP -> JPG quality (design 1.3)
    'resize': True,             # shrink above 2x display size
    'resize_factor': 2.0,
    'min_display': 24,          # same default as audit_image_clarity.py
    'quantize': True,           # Q3 switch, read by png.py (256 colours, banded images via overrides)
    'keep_webp_exception': '',  # Q4: non-empty reason = new game keeps its WebP (standard probe required)
}


def _get(ctx, key, default=None):
    if isinstance(ctx, dict):
        return ctx.get(key, default)
    return getattr(ctx, key, default)


def options(ctx):
    out = dict(DEFAULTS)
    out.update(_get(ctx, 'options') or {})
    return out


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _rel(project, path):
    return Path(path).relative_to(project).as_posix()


def _skipped(project, path):
    return bool(SKIP_DIRS & {x.lower() for x in Path(path).relative_to(project).parts})


def walk(project, suffixes):
    root = Path(project) / 'assets'
    if not root.is_dir():
        return
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.name.lower().endswith(suffixes) and not _skipped(project, p):
            yield p


def engine_of(project, ctx=None):
    given = _get(ctx, 'engine') if ctx is not None else None
    if given in (2, 3):
        return given
    project = Path(project)
    try:
        pkg = json.loads((project / 'package.json').read_text(encoding='utf-8'))
        ver = str((pkg.get('creator') or {}).get('version') or '')
        if ver.startswith('3'):
            return 3
    except (OSError, ValueError, AttributeError):
        pass
    if (project / 'settings' / 'v2').is_dir():
        return 3
    return 2


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def load_overrides(project):
    """-> (by_path {project-relative path: spec}, problems [str]). A broken file is a block, never ignored."""
    path = Path(project) / KIT_DIR / OVERRIDES
    if not path.exists():
        return {}, []
    data = read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get('images'), dict):
        return {}, [f'{KIT_DIR}/{OVERRIDES}: not JSON of the form {{"images": {{path: spec}}}}']
    out, problems = {}, []
    for key, spec in data['images'].items():
        if not isinstance(spec, dict):
            problems.append(f'{OVERRIDES}: {key}: spec must be an object')
            continue
        bad = set(spec) - {'format', 'jpg_quality', 'quantize', 'resize', 'max_side', 'note'}
        if bad:
            problems.append(f'{OVERRIDES}: {key}: unknown field(s) {sorted(bad)}')
        if spec.get('format') not in (None, 'png', 'jpg'):
            problems.append(f'{OVERRIDES}: {key}: format must be png or jpg')
        q = spec.get('jpg_quality')
        if q is not None and not (isinstance(q, int) and 60 <= q <= 100):
            problems.append(f'{OVERRIDES}: {key}: jpg_quality must be an integer 60-100')
        m = spec.get('max_side')
        if m is not None and not (isinstance(m, int) and not isinstance(m, bool) and 64 <= m <= 8192):
            problems.append(f'{OVERRIDES}: {key}: max_side must be an integer 64-8192')
        for flag in ('quantize', 'resize'):
            if flag in spec and not isinstance(spec[flag], bool):
                problems.append(f'{OVERRIDES}: {key}: {flag} must be true or false')
        out[key.replace('\\', '/').lstrip('./')] = spec
    return out, problems


def override_for(overrides, rel_path):
    """Spec for one image, matching the path before or after conversion; a key with * or ? is a glob
    (fnmatch, '*' also crosses '/'), used only when no exact key matches. Glob keys are tried in sorted order."""
    if rel_path in overrides:
        return overrides[rel_path]
    stem = rel_path.rsplit('.', 1)[0]
    for ext in ('webp', 'png', 'jpg', 'jpeg'):
        if f'{stem}.{ext}' in overrides:
            return overrides[f'{stem}.{ext}']
    import fnmatch
    for key in sorted(k for k in overrides if '*' in k or '?' in k):
        if fnmatch.fnmatchcase(rel_path, key) or any(fnmatch.fnmatchcase(f'{stem}.{e}', key)
                                                     for e in ('webp', 'png', 'jpg', 'jpeg')):
            return overrides[key]
    return {}


# ---------------------------------------------------------------- inventory

IMAGE_EXT = ('.webp', '.png', '.jpg', '.jpeg')


def _frames(meta, engine):
    """frame uuid -> the dict that holds its geometry (2.4: the subMeta itself, 3.x: subMeta.userData)."""
    out = {}
    for key, sub in (meta.get('subMetas') or {}).items():
        if not isinstance(sub, dict) or not sub.get('uuid'):
            continue
        if engine == 3:
            if sub.get('importer') == 'sprite-frame' and isinstance(sub.get('userData'), dict):
                out[sub['uuid']] = sub['userData']
        elif sub.get('importer', 'sprite-frame') == 'sprite-frame' and ('rawWidth' in sub or 'width' in sub):
            out[sub['uuid']] = sub
    return out


def _loadable(project, image, cache):
    """True when the image sits in resources/ or an asset bundle folder, i.e. code may load it by path."""
    assets = Path(project) / 'assets'
    for folder in Path(image).parents:
        if folder == assets or assets not in folder.parents:
            break
        if folder in cache:
            if cache[folder]:
                return True
            continue
        hit = folder.name == 'resources'
        m = read_json(folder.with_name(folder.name + '.meta')) or {}
        if m.get('isBundle') is True or (isinstance(m.get('userData'), dict) and m['userData'].get('isBundle') is True):
            hit = True
        cache[folder] = hit
        if hit:
            return True
    return False


def _presets(project):
    cfg = read_json(Path(project) / 'settings' / 'v2' / 'packages' / 'builder.json') or {}
    return ((cfg.get('textureCompressConfig') or {}).get('userPreset')) or {}


def compress_webp(meta, engine, presets):
    """'yes' when this image's own texture-compression setting makes the build emit WebP, 'unknown', or None."""
    if engine == 2:
        for plat in (meta.get('platformSettings') or {}).values():
            if isinstance(plat, dict) and any(isinstance(f, dict) and f.get('name') == 'webp'
                                              for f in plat.get('formats') or []):
                return 'yes'
        return None
    cs = (meta.get('userData') or {}).get('compressSettings') or {}
    if not cs.get('useCompressTexture'):
        return None
    preset = presets.get(cs.get('presetId'))
    if preset is None:
        return 'unknown'
    opts = preset.get('options') or {}
    return 'yes' if any(isinstance(v, dict) and 'webp' in v for v in opts.values()) else None


def textures(project, engine):
    """All image assets with a .meta under assets/."""
    project = Path(project)
    presets = _presets(project) if engine == 3 else {}
    cache, out = {}, []
    for image in walk(project, IMAGE_EXT):
        meta_path = image.with_name(image.name + '.meta')
        meta = read_json(meta_path)
        if not isinstance(meta, dict):
            continue
        out.append({'image': image, 'meta_path': meta_path, 'meta': meta, 'rel': _rel(project, image),
                    'uuid': meta.get('uuid'), 'frames': _frames(meta, engine),
                    'loadable': _loadable(project, image, cache),
                    'compress_webp': compress_webp(meta, engine, presets)})
    return out


# ---------------------------------------------------------------- display size (audit_image_clarity.py way)

def _clarity():
    here = Path(__file__).resolve().parent.parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    import audit_image_clarity
    return audit_image_clarity


SCENE_EXT = ('.fire', '.scene', '.prefab')
OTHER_EXT = ('.anim', '.json', '.mtl', '.pac', '.labelatlas', '.plist', '.effect', '.pmtl', '.physics-material')
UUID_RE = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:@[0-9a-f]+)?')


def _uuid_refs(value, path=()):
    if isinstance(value, dict):
        if isinstance(value.get('__uuid__'), str):
            yield path, value['__uuid__']
        for k, v in value.items():
            yield from _uuid_refs(v, path + (k,))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _uuid_refs(v, path + (i,))


def usages(project, texs):
    """texture uuid -> {'sprites': [...], 'other': [...]} for every scene/prefab/asset reference."""
    clar = _clarity()
    owner = {}                                     # any uuid (texture or frame) -> texture uuid
    for t in texs:
        if t['uuid']:
            owner[t['uuid']] = t['uuid']
            for sub in (t['meta'].get('subMetas') or {}).values():
                if isinstance(sub, dict) and sub.get('uuid'):
                    owner[sub['uuid']] = t['uuid']
    out = {u: {'sprites': [], 'other': []} for u in set(owner.values())}
    for f in walk(project, SCENE_EXT):
        objs = read_json(f)
        if not isinstance(objs, list):
            continue
        rel, cache = _rel(project, f), {}
        for idx, o in enumerate(objs):
            if not isinstance(o, dict):
                continue
            for path, ref in _uuid_refs(o):
                tex = owner.get(ref)
                if not tex:
                    continue
                node_ref = (o.get('node') or {}).get('__id__')
                if o.get('__type__') == 'cc.Sprite' and path == ('_spriteFrame',) and isinstance(node_ref, int):
                    w, h = clar.content_size(objs, node_ref)
                    sx, sy = clar.node_scale(objs, node_ref, cache)
                    out[tex]['sprites'].append({'file': rel, 'index': idx, 'display': (w * sx, h * sy),
                                                'type': o.get('_type', 0), 'size_mode': o.get('_sizeMode', 1)})
                else:
                    out[tex]['other'].append(f'{rel}#{idx}:{o.get("__type__", "?")}.{".".join(map(str, path))}')
    for f in walk(project, OTHER_EXT):
        try:
            text = f.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for ref in set(UUID_RE.findall(text)):
            tex = owner.get(ref)
            if tex:
                out[tex]['other'].append(_rel(project, f))
    return out


def _full_frame(geom, w, h):
    g = lambda k: geom.get(k) or 0
    return (g('trimX') == 0 and g('trimY') == 0 and g('offsetX') == 0 and g('offsetY') == 0
            and geom.get('width') == w and geom.get('height') == h
            and geom.get('rawWidth') == w and geom.get('rawHeight') == h)


def _ceil(x):
    return int(-(-x // 1))


def resize_plan(tex, use, size, opts, override):
    """-> ((new_w, new_h) or None, reason). Only shrinks when it cannot change what the player sees."""
    w, h = size
    if not opts.get('resize', True) or override.get('resize') is False:
        return None, 'resize switched off'
    if override.get('max_side'):
        # Explicit per-image decision (Q4: shrink before keeping WebP). The game session has checked how the
        # art is shown; geometry of every frame is scaled with the pixels, scene sprites become CUSTOM size.
        m = int(override['max_side'])
        if max(w, h) <= m:
            return None, f'within image-overrides max_side {m}'
        f = m / float(max(w, h))
        return (max(1, round(w * f)), max(1, round(h * f))), f'image-overrides max_side {m}: {w}x{h}'
    if len(tex['frames']) != 1:
        return None, f'{len(tex["frames"])} sprite frames (atlas or raw texture)'
    if not _full_frame(next(iter(tex['frames'].values())), w, h):
        return None, 'trimmed frame'
    if tex['loadable']:
        return None, 'in resources/ or a bundle: code may load it by path'
    if use['other']:
        return None, 'referenced outside a static cc.Sprite: ' + ', '.join(sorted(set(use['other']))[:3])
    sprites = use['sprites']
    if not sprites:
        return None, 'not used by any scene/prefab sprite (display size unknown)'
    if any(s['type'] not in (0, 3) for s in sprites):
        return None, 'used as sliced/tiled/mesh sprite'
    dw = max(s['display'][0] for s in sprites)
    dh = max(s['display'][1] for s in sprites)
    if dw <= 0 or dh <= 0 or max(dw, dh) < opts['min_display']:
        return None, 'display size unknown or tiny'
    k = float(opts['resize_factor'])
    f = max(k * dw / w, k * dh / h)                 # smallest scale that keeps BOTH axes >= 2x display
    if f >= 1:
        return None, 'within 2x display size'
    nw = min(w, max(_ceil(w * f), _ceil(k * dw)))
    nh = min(h, max(_ceil(h * f), _ceil(k * dh)))
    if nw >= w and nh >= h:
        return None, 'within 2x display size'
    return (nw, nh), f'display {round(dw)}x{round(dh)}: {w}x{h} -> {nw}x{nh}'


# ---------------------------------------------------------------- hard-coded .webp in game data (W-D4 request 2)

DATA_EXT = ('.json', '.ts', '.js')                  # .meta files end in .meta and are never read here
KIT_SOURCE_DIR = 'assets/tiktok-platform/'          # the kit's own modules / plugin scripts
WEBP_EXT_LITERAL = re.compile(r'''(["'`])\.webp\1''', re.I)
WEBP_PATH_LITERAL = re.compile(r'''(["'])([^"'\n]{1,200}?\.webp)\1''', re.I)
OTHER_EXT_LITERAL = re.compile(r'''["'`]\.(?:png|jpe?g)["'`]''', re.I)
REMOTE = ('http:', 'https:', '//', 'data:')
EXT_LIST_WINDOW = 120

WEBP_EXCEPTION_3X = ('--keep-webp-exception is not available for Cocos 3.x in v7.7: no 3.x WebP probe is a kit part '
                     'and none is device-proven. A 3.x game must get under 30 MB with PNG/JPG and image-overrides '
                     'max_side shrinking; a 3.x probe (webp_probe3x) comes in v7.8')


def webp_literals(project):
    """[(rel, line, literal)] for every ".webp" / '.webp' string literal in assets/**/*.json|.ts|.js (not .meta), plus,
    in .json data, path strings ending in .webp (e.g. "image": "art/bg.webp"). Not reported: an extension literal
    with ".png"/".jpg" literals close by (a list of supported formats, e.g. AssetLoadGuard's types=[...]), remote
    URLs, and the kit's own files. Read only: game data is never rewritten here."""
    project = Path(project)
    hits = []
    for f in walk(project, DATA_EXT):
        rel = _rel(project, f)
        if rel.startswith(KIT_SOURCE_DIR):
            continue
        try:
            text = f.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        if '.webp' not in text.lower():
            continue
        seen = set()
        for m in WEBP_EXT_LITERAL.finditer(text):
            window = text[max(0, m.start() - EXT_LIST_WINDOW):m.end() + EXT_LIST_WINDOW]
            if OTHER_EXT_LITERAL.search(window):
                continue
            seen.add(m.start())
            hits.append((rel, text.count('\n', 0, m.start()) + 1, m.group(0)))
        if rel.lower().endswith('.json'):
            for m in WEBP_PATH_LITERAL.finditer(text):
                value = m.group(2)
                if m.start() in seen or value.lower() == '.webp' or value.lower().startswith(REMOTE):
                    continue
                hits.append((rel, text.count('\n', 0, m.start()) + 1, m.group(0)))
    return hits


def webp_literal_messages(project, kept):
    """One message per file. kept=True: WebP stays (exception / legacy), so the literal may name a kept file."""
    by_file = {}
    for rel, line, lit in webp_literals(project):
        by_file.setdefault(rel, []).append((line, lit))
    out = []
    for rel, items in sorted(by_file.items()):
        where = ', '.join('line %d %s' % (line, lit[:60]) for line, lit in items[:5])
        more = ' (+%d more)' % (len(items) - 5) if len(items) > 5 else ''
        if kept:
            out.append(f'{rel}: hard-coded .webp ({where}{more}); WebP is kept, but if these images ever become '
                       'PNG/JPG this file must say ".png" or ".jpg"')
        else:
            out.append(f'{rel}: hard-coded .webp ({where}{more}); the images become PNG/JPG, so the game would '
                       'request .webp files the build no longer has (Marlows R6: 19 images failed to load). '
                       'Change it to ".png" or ".jpg" in the game; finalize does not rewrite game data')
    return out


# ---------------------------------------------------------------- plan (pure, no writes)

SCRIPT_EXT = ('.js', '.ts')


def has_alpha(img):
    if img.mode in ('RGBA', 'LA', 'PA') or (img.mode == 'P' and 'transparency' in img.info) or \
            (img.mode in ('RGB', 'L') and 'transparency' in img.info):
        return img.convert('RGBA').getchannel('A').getextrema()[0] < 255
    return False


def _open(path):
    from PIL import Image
    img = Image.open(path)
    img.load()
    return img


def plan(ctx):
    project = Path(_get(ctx, 'project'))
    engine = engine_of(project, ctx)
    policy = _get(ctx, 'policy') or 'new'
    opts = options(ctx)
    exception = str(opts.get('keep_webp_exception') or '').strip()
    overrides, blocks = load_overrides(project)
    warnings, actions, report = [], [], []
    if engine == 3 and exception:                   # DECISIONS 13:25: no 3.x WebP exception in v7.7
        blocks.append(WEBP_EXCEPTION_3X)
        return {'engine': engine, 'policy': policy, 'actions': [], 'blocks': blocks, 'warnings': warnings,
                'report': report, 'texs': []}
    texs = textures(project, engine)
    with_meta = {t['image'] for t in texs}
    for p in walk(project, ('.webp',)):
        if p not in with_meta:
            blocks.append(f'{_rel(project, p)}: .webp without a readable .meta (cannot keep its uuid)')
    webp = [t for t in texs if t['rel'].lower().endswith('.webp')]
    if policy != 'new':
        if webp or any(t['compress_webp'] for t in texs):
            warnings.append(f'legacy policy: {len(webp)} WebP image(s) and '
                            f'{sum(1 for t in texs if t["compress_webp"])} WebP compression setting(s) kept; '
                            'the package must pass the standard WebP probe gate (webp.py G4)')
            warnings += webp_literal_messages(project, kept=True)
        return {'engine': engine, 'policy': policy, 'actions': [], 'blocks': blocks, 'warnings': warnings,
                'report': report, 'texs': texs}
    scripts = {}
    for s in walk(project, SCRIPT_EXT):
        try:
            scripts[_rel(project, s)] = s.read_text(encoding='utf-8', errors='replace')
        except OSError:
            pass
    use = usages(project, texs)
    for t in texs:
        ov = override_for(overrides, t['rel'])
        act = {'rel': t['rel'], 'convert': None, 'resize': None, 'compress_off': False}
        try:
            img = _open(t['image'])
        except Exception as exc:                       # unreadable art is never silently skipped
            blocks.append(f'{t["rel"]}: cannot be read as an image ({exc})')
            continue
        alpha = has_alpha(img) if t['rel'].lower().endswith('.webp') else None
        if alpha is not None and exception:
            warnings.append(f'{t["rel"]}: WebP kept (--keep-webp-exception: {exception}); '
                            'the native phase must install the standard probe webp_probe24')
            alpha = None
        if alpha is not None:
            fmt = ov.get('format') or ('png' if alpha else 'jpg')
            if fmt == 'jpg' and alpha:
                blocks.append(f'{t["rel"]}: image-overrides asks for JPG but the image has transparent pixels')
                continue
            new_rel = t['rel'][:-5] + '.' + fmt
            if (project / new_rel).exists() or (project / (new_rel + '.meta')).exists():
                blocks.append(f'{t["rel"]}: cannot rename, {new_rel} already exists')
                continue
            name = t['image'].name
            users = [s for s, text in scripts.items() if name in text]
            if users:
                blocks.append(f'{t["rel"]}: scripts name the file with its .webp extension ({", ".join(users[:3])})')
                continue
            act.update(convert=fmt, new_rel=new_rel, alpha=alpha)
        if t['compress_webp'] == 'yes':
            act['compress_off'] = True
        elif t['compress_webp'] == 'unknown':
            warnings.append(f'{t["rel"]}: texture-compression preset not found in builder.json; '
                            'check the build output has no .webp')
        new_size, why = resize_plan(t, use.get(t['uuid'], {'sprites': [], 'other': []}), img.size, opts, ov)
        if new_size and exception and t['rel'].lower().endswith('.webp'):
            new_size, why = None, 'WebP kept by exception: not re-encoded'
        if new_size:
            act['resize'] = new_size
            act['flip'] = [(s['file'], s['index']) for s in use[t['uuid']]['sprites'] if s['size_mode'] != 0]
        report.append({'image': t['rel'], 'size': list(img.size), 'resize': list(new_size) if new_size else None,
                       'why': why, 'convert': act['convert'], 'compress_off': act['compress_off']})
        img.close()
        if act['convert'] or act['resize'] or act['compress_off']:
            act['tex'] = t
            act['jpg_quality'] = ov.get('jpg_quality') or opts['jpg_quality']
            actions.append(act)
    if any(a['convert'] or a['compress_off'] for a in actions):
        # W-D4 request 2: game data that builds ".webp" URLs breaks once the build has no .webp (same id IMG0)
        (warnings if exception else blocks).extend(webp_literal_messages(project, kept=bool(exception)))
    return {'engine': engine, 'policy': policy, 'actions': actions, 'blocks': blocks, 'warnings': warnings,
            'report': report, 'texs': texs}


def detect(ctx):
    if _get(ctx, 'phase', 'source') != 'source':
        return 'n/a'
    p = plan(ctx)
    return _state(p)


def _state(p):
    if p['blocks']:
        return 'conflict'
    if p['policy'] != 'new':
        return 'own' if p['warnings'] else 'kit_current'
    return 'absent' if p['actions'] else 'kit_current'


def _result(state, changed, blocks, warnings, report):
    """Result.as_dict() shape of tiktok_finalize_steps/__init__.py (W-B)."""
    f = lambda gid, level, msg: {'id': gid, 'level': level, 'message': msg}
    return {'step': PART, 'state': state, 'changed': changed,
            'blocks': [f('IMG0_source_images', 'block', m) for m in blocks],
            'warnings': [f('IMG0_source_images', 'warn', m) for m in warnings],
            'info': report}


# ---------------------------------------------------------------- apply

def _dump(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def _backup(project, path):
    src = Path(path)
    dest = Path(project) / KIT_DIR / 'originals' / _rel(project, src)
    if src.exists() and not dest.exists():                 # first original wins; never overwritten
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def _encode(img, fmt, quality):
    from PIL import Image
    buf = io.BytesIO()
    if fmt == 'jpg':
        if img.mode != 'RGB':
            rgba = img.convert('RGBA')
            flat = Image.new('RGB', rgba.size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.getchannel('A'))
            img = flat
        img.save(buf, 'JPEG', quality=int(quality), optimize=True)
    else:
        if img.mode not in ('RGBA', 'RGB', 'LA', 'L', 'P'):
            img = img.convert('RGBA')
        img.save(buf, 'PNG', compress_level=9)
    return buf.getvalue()


def _scale_geom(geom, sx, sy, engine):
    for k, s in (('width', sx), ('rawWidth', sx), ('height', sy), ('rawHeight', sy)):
        if isinstance(geom.get(k), (int, float)):
            geom[k] = geom[k] if geom[k] == 0 else max(1, round(geom[k] * s))
    for k, s in (('borderLeft', sx), ('borderRight', sx), ('borderTop', sy), ('borderBottom', sy),
                 ('trimX', sx), ('trimY', sy)):
        if isinstance(geom.get(k), (int, float)):
            geom[k] = round(geom[k] * s)
    for k, s in (('offsetX', sx), ('offsetY', sy)):
        if isinstance(geom.get(k), (int, float)) and geom[k]:
            geom[k] = round(geom[k] * s * 2) / 2            # Cocos keeps half-pixel offsets
    v = geom.get('vertices') if engine == 3 else None
    if isinstance(v, dict):
        for key, stride in (('rawPosition', 3), ('uv', 2)):     # pixel coordinates: x, y (, z kept)
            if isinstance(v.get(key), list):
                v[key] = [round(x * sx, 4) if i % stride == 0 else round(x * sy, 4) if i % stride == 1 else x
                          for i, x in enumerate(v[key])]
        for key in ('minPos', 'maxPos'):
            if isinstance(v.get(key), list) and len(v[key]) >= 2:
                v[key] = [round(v[key][0] * sx, 4), round(v[key][1] * sy, 4)] + v[key][2:]


def _strip_webp_compress(meta, engine):
    if engine == 2:
        plats = meta.get('platformSettings') or {}
        for name in list(plats):
            plat = plats[name]
            if isinstance(plat, dict) and isinstance(plat.get('formats'), list):
                plat['formats'] = [f for f in plat['formats'] if not (isinstance(f, dict) and f.get('name') == 'webp')]
                if not plat['formats']:
                    del plats[name]
    else:
        meta['userData']['compressSettings']['useCompressTexture'] = False


def _change(project, path, before, after, what):
    return {'file': _rel(project, path), 'before_sha256': sha256(before) if before is not None else None,
            'after_sha256': sha256(after) if after is not None else None, 'what': what}


def apply(ctx):
    p = plan(ctx)
    project = Path(_get(ctx, 'project'))
    engine = p['engine']
    if p['blocks']:                                     # refuse before touching anything
        return _result('conflict', [], p['blocks'], p['warnings'], p['report'])
    changed, flips = [], {}
    for act in p['actions']:
        t = act['tex']
        meta = json.loads(json.dumps(t['meta']))
        old_img, old_meta = t['image'].read_bytes(), t['meta_path'].read_bytes()
        _backup(project, t['image'])
        _backup(project, t['meta_path'])
        what = []
        img_bytes = old_img
        if act['convert'] or act['resize']:
            img = _open(t['image'])
            if act['resize']:
                from PIL import Image
                sx, sy = act['resize'][0] / img.size[0], act['resize'][1] / img.size[1]
                what.append(f'{img.size[0]}x{img.size[1]} -> {act["resize"][0]}x{act["resize"][1]}')
                img = img.convert('RGBA' if img.mode in ('P', 'LA', 'PA') else img.mode).resize(
                    act['resize'], Image.LANCZOS)
                if engine == 2:
                    meta['width'], meta['height'] = act['resize']
                for geom in _frames(meta, engine).values():
                    _scale_geom(geom, sx, sy, engine)
                for f, idx in act.get('flip', []):
                    flips.setdefault(f, set()).add(idx)
            fmt = act['convert'] or ('jpg' if t['rel'].lower().endswith(('.jpg', '.jpeg')) else 'png')
            img_bytes = _encode(img, fmt, act['jpg_quality'])
            img.close()
        new_img, new_meta = t['image'], t['meta_path']
        if act['convert']:
            new_img = project / act['new_rel']
            new_meta = new_img.with_name(new_img.name + '.meta')
            what.insert(0, f'{t["image"].name} -> {new_img.name} ({"alpha" if act["alpha"] else "opaque"})')
            if engine == 3:
                meta['files'] = ['.' + act['convert'] if x == '.webp' else x for x in meta.get('files') or []]
                if isinstance(meta.get('userData'), dict):
                    meta['userData']['hasAlpha'] = bool(act['alpha'])
        if act['compress_off']:
            _strip_webp_compress(meta, engine)
            what.append('WebP texture compression off')
        meta_bytes = _dump(meta) if meta != t['meta'] else old_meta
        new_img.write_bytes(img_bytes)
        new_meta.write_bytes(meta_bytes)
        if new_img != t['image']:
            t['image'].unlink()
            t['meta_path'].unlink()
            changed.append(_change(project, t['image'], old_img, None, 'removed (converted)'))
            changed.append(_change(project, t['meta_path'], old_meta, None, 'renamed, uuid kept'))
        changed.append(_change(project, new_img, None if new_img != t['image'] else old_img, img_bytes, '; '.join(what)))
        if meta_bytes != old_meta or new_meta != t['meta_path']:
            changed.append(_change(project, new_meta, None if new_meta != t['meta_path'] else old_meta, meta_bytes,
                                   'meta: uuid ' + str(meta.get('uuid')) + ' kept'))
    for rel, idxs in sorted(flips.items()):
        path = project / rel
        before = path.read_bytes()
        objs = json.loads(before.decode('utf-8'))
        for i in sorted(idxs):
            objs[i]['_sizeMode'] = 0                    # CUSTOM: keep the node size the scene already stores
        _backup(project, path)
        after = _dump(objs)
        path.write_bytes(after)
        changed.append(_change(project, path, before, after, f'{len(idxs)} shrunk sprite(s) set to sizeMode CUSTOM'))
    again = plan(ctx)                                    # re-read and self-check (design 1.4)
    blocks = list(again['blocks'])
    if again['actions']:
        blocks.append('images: rewrite did not verify, still to do: ' +
                      ', '.join(a['rel'] for a in again['actions'][:5]))
    left = [t['rel'] for t in again['texs'] if t['rel'].lower().endswith('.webp')]
    # legacy games keep their WebP (webp.py G4 decides); only a new game without the exception must have none left
    if left and p['policy'] == 'new' and not str(options(ctx).get('keep_webp_exception') or '').strip():
        blocks.append('images: .webp still in assets/: ' + ', '.join(left[:5]))
    return _result('conflict' if blocks else _state(p), changed, blocks, p['warnings'], p['report'])


# ---------------------------------------------------------------- verify (read-only, for the kit_parts gate)

def verify(view_or_files, manifest=None, policy=None):
    """Findings for the package bytes. New policy: any .webp art in the package is a block, unless the platform
    kit's standard WebP probe is in it (Q4 exception: G4 in webp.py then decides). The probe counts as standard
    only when its bytes equal a KIT_MANIFEST version of part webp_probe24 (or webp_probe3x)."""
    from . import finding
    files = getattr(view_or_files, 'files', view_or_files)
    policy = policy or getattr(view_or_files, 'policy', None) or 'new'
    webp = sorted(n for n in files if n.lower().endswith('.webp'))
    probe_images = {'loading/webp-probe.webp'}          # kit 2.0 webp_probe24 extra_files dest
    if manifest is not None and manifest.part('webp_probe24'):
        probe_images |= {x.get('dest') for x in manifest.part('webp_probe24').get('extra_files') or []} - {None}
    art = [n for n in webp if n not in probe_images]
    if not art:
        return []
    if policy == 'legacy':
        return [finding('IMG1_webp_kept', 'warn', f'{len(art)} WebP image(s) kept (legacy game); '
                        'standard probe gate G4 applies', art[:10])]
    kit = set()
    if manifest is not None:
        for part in ('webp_probe24', 'webp_probe3x'):
            if manifest.part(part):
                kit |= manifest.all_versions(part)
    probe_js = [n for n in files if '/' not in n and n.endswith('.js') and sha256(files[n]) in kit]
    if probe_js:
        return [finding('IMG1_webp_exception', 'warn', f'{len(art)} WebP image(s) kept with the standard probe '
                        f'{probe_js[0]} (--keep-webp-exception); G4 decides', art[:10])]
    return [finding('IMG1_webp_in_package', 'block', f'{len(art)} WebP image(s) in a new-game package '
                    '(no standard kit probe); run tiktok_finalize.py source and rebuild', art[:10])]
