"""tiktok_finalize step `png` (NATIVE phase, v7.7 design 1.3 row `png.py`, 3.6, Q3).

Runs on the Creator build output, before any gate. Both policies (new and legacy):
  every *.png in the build is compressed ONCE with
      pngquant --quality=0-85 --skip-if-larger --strip
  (256 colours; a file pngquant cannot make smaller is left as it is).

This is the only place art is quantised: images.py writes lossless PNG in the project, so an image listed in
<project>/.tiktok-kit/image-overrides.json with "quantize": false really stays unquantised (R7). Such an image is
found in the build by its uuid (the build names native files <uuid>[.<md5>].png) or, failing that, by identical
bytes. An override that matches no build file (for example art packed into an auto atlas) is a warning.

Same result on every run (design 1.4): <project>/.tiktok-kit/png-cache.json maps input sha256 -> output sha256.
A PNG whose bytes already equal a recorded output is skipped, so a second finalize changes no byte. The cache
records the pngquant version and arguments; a different version or argument list throws the cache away.
pngquant missing, or pngquant failing on a file, is a block: the step never skips silently.
"""
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from . import Result, sha256

PART = 'png'
PHASE = 'native'
KIT_DIR = '.tiktok-kit'
CACHE = 'png-cache.json'
OVERRIDES = 'image-overrides.json'
ARGS = ['--quality=0-85', '--skip-if-larger', '--strip']
SKIPPED_CODES = (98, 99)          # 98: result would be larger, 99: quality below minimum -> keep the input
GATE = 'PNG0_compress'
SHA256 = re.compile(r'[0-9a-f]{64}')
UUID_IN_NAME = re.compile(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})')


def _get(ctx, key, default=None):
    if isinstance(ctx, dict):
        return ctx.get(key, default)
    return getattr(ctx, key, default)


def pngquant_path(ctx=None):
    opts = _get(ctx, 'options') or {} if ctx is not None else {}
    given = opts.get('pngquant') if isinstance(opts, dict) else None
    return given if given is not None else shutil.which('pngquant')


def pngquant_version(exe):
    out = subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise OSError('pngquant --version failed: ' + (out.stderr or out.stdout).strip())
    return out.stdout.strip().split()[0]


def run_pngquant(exe, data):
    """-> output bytes (the input itself when pngquant keeps it). Raises OSError on any other failure."""
    out = subprocess.run([exe] + ARGS + ['-'], input=data, capture_output=True, timeout=300)
    if out.returncode == 0 and out.stdout:
        return out.stdout
    if out.returncode in SKIPPED_CODES:
        return data
    raise OSError('pngquant exit %d: %s' % (out.returncode, out.stderr.decode('utf-8', 'replace').strip()[:200]))


# ---------------------------------------------------------------- cache and overrides

def _cache_path(ctx):
    """<project>/.tiktok-kit/png-cache.json; without a project (check-only runs, W-B pkg85 case) a sibling of the
    build folder, <native>/../.tiktok-kit-png-cache/<native name>.json, never inside the ZIP."""
    project = _get(ctx, 'project')
    if project:
        return Path(project) / KIT_DIR / CACHE
    root = _get(ctx, 'root')
    return Path(root).resolve().parent / '.tiktok-kit-png-cache' / (Path(root).resolve().name + '.json') if root else None


def load_cache(ctx, version):
    """Read existing results. With a converter version, reject cache entries made by a different version."""
    path = _cache_path(ctx)
    if path is None or not path.is_file():
        return {}, None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}, f'{KIT_DIR}/{CACHE} unreadable, rebuilt'
    cache_version = data.get('pngquant') if isinstance(data, dict) else None
    if (not isinstance(cache_version, str) or not cache_version or data.get('args') != ARGS
            or (version is not None and cache_version != version)):
        return {}, f'{KIT_DIR}/{CACHE} made by pngquant {data.get("pngquant") if isinstance(data, dict) else "?"} ' \
                   f'{data.get("args") if isinstance(data, dict) else ""}; cache discarded'
    entries = data.get('entries')
    if not isinstance(entries, dict) or any(
        not SHA256.fullmatch(key) or not isinstance(value, str) or not SHA256.fullmatch(value)
        for key, value in entries.items()
    ):
        return {}, f'{KIT_DIR}/{CACHE} contains invalid PNG hashes; cache discarded'
    return dict(entries), None


def save_cache(ctx, version, entries):
    path = _cache_path(ctx)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {'pngquant': version, 'args': ARGS, 'entries': dict(sorted(entries.items()))}
    path.write_text(json.dumps(body, indent=1, sort_keys=True) + '\n', encoding='utf-8')


def _project_image(project, key):
    """Project file an override key names, before or after the WebP conversion of images.py."""
    stem = key.rsplit('.', 1)[0] if '.' in key.rsplit('/', 1)[-1] else key
    for cand in [key] + [f'{stem}.{e}' for e in ('png', 'jpg', 'jpeg', 'webp')]:
        p = Path(project) / cand
        if p.is_file():
            return p
    return None


def no_quantize(ctx):
    """-> (uuids, shas, keys_by_uuid_or_sha, problems) for images whose override says "quantize": false."""
    project = _get(ctx, 'project')
    uuids, shas, names, problems = set(), set(), {}, []
    if not project:
        return uuids, shas, names, problems
    path = Path(project) / KIT_DIR / OVERRIDES
    if not path.is_file():
        return uuids, shas, names, problems
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        images = data['images']
        assert isinstance(images, dict)
    except (OSError, ValueError, KeyError, TypeError, AssertionError):
        problems.append(f'{KIT_DIR}/{OVERRIDES}: not JSON of the form {{"images": {{path: spec}}}}')
        return uuids, shas, names, problems
    for key, spec in sorted(images.items()):
        if not isinstance(spec, dict) or 'quantize' not in spec:
            continue
        if not isinstance(spec['quantize'], bool):
            problems.append(f'{OVERRIDES}: {key}: quantize must be true or false')
            continue
        if spec['quantize']:
            continue
        img = _project_image(project, key.replace('\\', '/').lstrip('./'))
        if img is None:
            problems.append(f'{OVERRIDES}: {key}: no such image in the project')
            continue
        try:
            uuid = json.loads(img.with_name(img.name + '.meta').read_text(encoding='utf-8')).get('uuid')
        except (OSError, ValueError, AttributeError):
            uuid = None
        if uuid:
            uuids.add(uuid)
            names[uuid] = key
        digest = sha256(img.read_bytes())
        shas.add(digest)
        names[digest] = key
    return uuids, shas, names, problems


# ---------------------------------------------------------------- plan

def pngs(root):
    root = Path(root)
    return sorted(p for p in root.rglob('*') if p.is_file() and not p.is_symlink() and p.suffix.lower() == '.png')


def plan(ctx, cache=None, *, prepared_only=False):
    """Read-only. -> dict: exe, version, cache, todo [(path, data)], kept [(rel, why)], blocks, warnings.
    cache: entries already in memory (apply's self-check passes the cache it just wrote)."""
    root = Path(_get(ctx, 'root'))
    opts = _get(ctx, 'options') or {}
    out = {'exe': None, 'version': None, 'cache': {}, 'todo': [], 'done': [], 'kept': [], 'blocks': [],
           'warnings': [], 'bytes_before': 0}
    if not prepared_only:
        exe = pngquant_path(ctx)
        if not exe or not os.access(exe, os.X_OK):
            out['blocks'].append('pngquant not found (brew install pngquant); PNG compression cannot be skipped')
            return out
        try:
            out['version'] = pngquant_version(exe)
        except (OSError, subprocess.SubprocessError) as error:
            out['blocks'].append(f'pngquant unusable: {error}')
            return out
        out['exe'] = exe
    if cache is None:
        cache, note = load_cache(ctx, out['version'])
        if note:
            out['warnings'].append(note)
    out['cache'] = cache
    if not _get(ctx, 'project'):
        out['warnings'].append(f'no --project: PNG cache kept beside the build ({_cache_path(ctx)})')
    uuids, shas, names, problems = no_quantize(ctx)
    out['blocks'] += problems
    hit = set()
    outputs = set(cache.values())
    quantize_all = opts.get('quantize', True) is not False
    if not quantize_all:
        out['warnings'].append('PNG quantisation switched off for the whole package (options quantize=false)')
    for p in pngs(root):
        rel = p.relative_to(root).as_posix()
        data = p.read_bytes()
        out['bytes_before'] += len(data)
        digest = sha256(data)
        m = UUID_IN_NAME.search(p.name)
        key = (m.group(1) if m and m.group(1) in uuids else None) or (digest if digest in shas else None)
        if key:
            hit.add(names[key])
            out['kept'].append((rel, 'image-overrides quantize=false (' + names[key] + ')'))
            continue
        if not quantize_all:
            out['kept'].append((rel, 'quantize switched off'))
            continue
        if digest in outputs:
            out['done'].append(rel)
            continue
        out['todo'].append((p, data))
    for key in sorted(set(names.values()) - hit):
        out['warnings'].append(f'{OVERRIDES}: {key} quantize=false matched no PNG in the build '
                               '(packed into an auto atlas, or not a PNG after conversion)')
    return out


def detect(ctx):
    if _get(ctx, 'phase', 'native') != 'native':
        return 'n/a'
    p = plan(ctx)
    if p['blocks']:
        return 'conflict'
    return 'absent' if p['todo'] else 'kit_current'


# ---------------------------------------------------------------- prepared input and apply

def check_prepared(ctx):
    """Compare actual PNG bytes with the existing quantization results, without changing files."""
    res = Result(PART)
    p = plan(ctx, prepared_only=True)
    for message in p['warnings']:
        res.warn(GATE, message)
    for message in p['blocks']:
        res.block(GATE, message)
    if p['todo']:
        root = Path(_get(ctx, 'root'))
        names = ', '.join(path.relative_to(root).as_posix() for path, _ in p['todo'][:5])
        res.block(GATE, 'Native PNG 尚未完成试玩前处理（%d 张）：%s。先回试玩前阶段执行 tiktok_finalize.py native，再核对图片记录。'
                  % (len(p['todo']), names))
    res.state = 'conflict' if res.blocks else 'kit_current'
    res.info.append({'already_final': len(p['done']),
                     'kept_unquantised': [rel for rel, _ in p['kept']][:50]})
    return res.as_dict()

def apply(ctx):
    if (_get(ctx, 'options') or {}).get('prepared_png_only'):
        return check_prepared(ctx)
    res = Result(PART)
    p = plan(ctx)
    res.warnings += [{'id': GATE, 'level': 'warn', 'message': w} for w in p['warnings']]
    if p['blocks']:
        for b in p['blocks']:
            res.block(GATE, b)
        res.state = 'conflict'
        return res.as_dict()
    root = Path(_get(ctx, 'root'))
    cache = dict(p['cache'])
    jobs = int((_get(ctx, 'options') or {}).get('png_jobs') or min(8, os.cpu_count() or 2))
    todo = p['todo']
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = {pool.submit(run_pngquant, p['exe'], data): (path, data) for path, data in todo}
        for fut in concurrent.futures.as_completed(futures):
            path, data = futures[fut]
            try:
                results[path] = fut.result()
            except (OSError, subprocess.SubprocessError) as error:
                res.block(GATE, f'{path.relative_to(root).as_posix()}: {error}')
    if res.blocks:                                   # nothing written when any file failed
        res.state = 'conflict'
        return res.as_dict()
    saved, changed_n = 0, 0
    for path, data in todo:
        new = results[path]
        before = sha256(data)
        if before in cache and cache[before] != sha256(new):
            res.warn(GATE, f'{path.relative_to(root).as_posix()}: pngquant output differs from the cached one '
                     '(same version); new output used')
        cache[before] = sha256(new)
        if new != data:
            path.write_bytes(new)
            saved += len(data) - len(new)
            changed_n += 1
            res.change(path.relative_to(root).as_posix(), data, new, 'pngquant 256 colours')
        cache[sha256(new)] = sha256(new)            # an output fed back in is already final
    cache_read_only = (_get(ctx, 'options') or {}).get('png_cache_read_only', False)
    if not cache_read_only:
        save_cache(ctx, p['version'], cache)
    # The copy is checked again using the output hashes from this run.
    again = plan(ctx, cache=cache, prepared_only=cache_read_only)
    if again['blocks'] or again['todo']:
        res.block(GATE, 'png: rewrite did not verify, still to compress: ' +
                  ', '.join(x[0].relative_to(root).as_posix() for x in again['todo'][:5]))
    res.info.append({'pngquant': p['version'], 'args': ARGS, 'pngs': len(todo) + len(p['done']) + len(p['kept']),
                     'compressed': changed_n, 'already_final': len(p['done']),
                     'kept_unquantised': [r for r, _ in p['kept']][:50],
                     'bytes_before': p['bytes_before'], 'bytes_saved': saved})
    res.state = 'conflict' if res.blocks else ('absent' if todo else 'kit_current')
    return res.as_dict()


# ---------------------------------------------------------------- verify

def verify(view_or_files, manifest=None, policy=None):
    """Read only. Package bytes alone cannot show whether a PNG went through pngquant (a palette PNG may be the
    artist's own, a truecolour PNG may be one pngquant could not shrink), so this step has no byte gate: the
    kit_parts gate K4 compares the `changed` records of apply() with the package instead."""
    return []
