#!/usr/bin/env python3
"""Base-game assets and generated-art records (v7.8, 总表 H8 and H10). Stdlib only; works on Python 3.9.

H8 (Saul: 「底子原版的图一张都不能留」; 企鹅雪道美术 v2 had 35 of 56 images and all 4 sounds byte-identical to 懒猫跑酷,
v4/v5/美术 v6 still shipped the 懒猫 texture embedded in Fishbone.fbx, 丛林荡藤 v6 33 images of its 蜘蛛人 base):
  docs/art/base-assets.json   written once at project start (`tiktok_finalize.py init --base ...` or the `base` command
                              below; a game already started records it later with the same command). Holds where the base
                              was and the sha256 of every image, sound and model-embedded texture under its assets/.
                              A game made from scratch writes {"base": "none", "why": "..."}.
  docs/art/base-keep.json     {"keep": [{"file": "<project path or glob>", "why": "..."}]}: a base file that really stays
                              (every entry needs a why; it is listed in the art check).
  check: every image (.png .jpg .jpeg .webp .bmp .tga .psd .tif .tiff), every texture embedded in a model
  (.fbx binary/ASCII, .glb, .gltf data URIs) and every sound (.mp3 .ogg .oga .wav .m4a .aac .flac) under <project>/assets/
  that is byte-identical to the base and not in base-keep.json is a finding. Images of 4x4 pixels or less (w*h <= 16, fill
  pixels), the platform kit's own files and the official Cocos loading images are not counted. A remake without
  base-assets.json fails too (the message names the command that records it). English games (board localize, or
  docs/art-style.txt "original") are not checked: they keep the original's art on purpose.

H10 (Saul 10-30: buttons and digits drawn by code are not picture text; 企鹅雪道美术 v3 drew them with PIL + Fredoka):
  docs/art/generated.json     one entry per generated picture: sha256, file, prompt, tool, date. Record the FINAL file
                              (after cropping / compressing), with --raw <the generator's own output> when there is one.
                              Later edits of a recorded picture are recorded with `derive` (new sha, from_sha256 of the
                              recorded one); `tiktok_finalize.py source` records its own WebP conversion and shrinking
                              automatically (carry()), so the normal flow never needs a manual re-record.
                              CC0 / free-library art: --source <url> --license <CC0...> instead of --prompt.
  docs/art/script-drawn-allow.json  {"allow": [{"file": "<path or glob>", "why": "..."}]}: pictures that are drawn by code
                              on purpose (a plain nine-slice plate, a gradient), each with a why.
  check: every image under assets/ that is not base-identical (H8 handles those), not kit / official loading / tiny and not
  allowed must be in generated.json (directly or through a derive chain back to an entry with a prompt or source+license);
  otherwise 「不是生成的图」. English games: warning only, and only when the base (the original) was recorded, because
  without it the new pictures cannot be told from the original's.
  「v7.8 前已有」 (Saul 10-30): a game marked new on or before the v7.8 release day (.tiktok-kit/policy.json created <=
  PRE_V78_CUTOFF) may once run `pre-v78`: every picture then under assets/ without a record (not base-identical, kit,
  official loading, tiny or allowed) is written to generated.json as {"pre_v78": true, "why": ...}. It counts as recorded
  but every check lists it as 「v7.8 前已有 N 张（不是生成记录）」; an edited one needs `derive` like any other; pictures
  added later need a real generated record. Code-drawn buttons and digits Saul already rejected (企鹅雪道美术 v3) must be
  regenerated, not registered: the check cannot tell who drew the pixels, so this rule is the guard.

Only what goes into the package counts (W90b; 总表 H8 says 「运行时可见的图和声音」): shipped() decides it for Cocos 2.4
and 3.x alike -- in a resources folder or an asset bundle, referenced by uuid (its own or a subMetas uuid) from a scene,
from anything in resources / a bundle or from a script, directly or through prefabs, animations, atlases, materials and
fonts, named by path in a script, without a readable .meta (cannot be told), or found in the build given with --build.
H8 and H10 findings are shipped files only; base-identical or unrecorded files the project never uses are listed as
「工程里没用到，建议删掉」 (a hint, never a block). 热气球 BreezyBalloon: its 102 base files all ship (resources and the
legacy / later bundles; all 102 are in the v2.2 package by uuid); only 5 are byte-identical there because the build
re-encoded the other 97 (1 losslessly, 96 lossy with mean pixel difference <= 6) -- a byte compare against the package
misses them.

Severity: art_check.py turns these into two rows; a finding makes the art check (and so the art receipt) fail. The package
writers refuse a failed receipt for NEW remake games and only warn for legacy / English games (W83). At the writers
art_receipt.check() also re-compares the SOUNDS with the base (sounds are not in the image receipt).

CLI
  art_records.py base --project P --from <base project folder or source ZIP>
  art_records.py base --project P --none --why "made from scratch, no base"
  art_records.py generated --project P --prompt "..." --tool "codex image_gen" [--date YYYY-MM-DD] [--raw RAW] FILE...
  art_records.py generated --project P --source URL --license CC0 --tool kenney FILE...
  art_records.py derive --project P [--from OLD_FILE_OR_SHA] [--how "cropped"] FILE...
  art_records.py keep --project P --why "..." FILE_OR_GLOB...
  art_records.py allow --project P --why "..." FILE_OR_GLOB...
  art_records.py pre-v78 --project P --why "装 v7.8 时工程里已有的图"   (once; only games marked new by PRE_V78_CUTOFF)
  art_records.py check --project P [--board remake|localize] [--build <构建文件夹或包 ZIP>] [--json]
Exit codes: 0 ok, 1 findings (check) / refused (record), 2 bad input.
"""
import argparse
import base64
import datetime as dt
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
SCHEMA = 1
BASE_FILE = Path('docs') / 'art' / 'base-assets.json'
KEEP_FILE = Path('docs') / 'art' / 'base-keep.json'
GENERATED_FILE = Path('docs') / 'art' / 'generated.json'
ALLOW_FILE = Path('docs') / 'art' / 'script-drawn-allow.json'
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tga', '.psd', '.tif', '.tiff')
MODEL_EXT = ('.fbx', '.glb', '.gltf')
AUDIO_EXT = ('.mp3', '.ogg', '.oga', '.wav', '.m4a', '.aac', '.flac')
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles', '.tiktok-kit', '__macosx',
             'tiktok-platform'}
KIT_DIR = HERE.parent / 'assets' / 'platform-kit'
OFFICIAL_LOADING = HERE / 'official_loading_assets.json'
BASE_CMD = 'python3 %s base --project "%%s" --from "<底子工程文件夹或源码 ZIP>"' % (HERE / 'art_records.py')
NONE_CMD = 'python3 %s base --project "%%s" --none --why "<为什么没有底子>"' % (HERE / 'art_records.py')
GEN_CMD = 'python3 %s generated --project "%%s" --prompt "<提示词>" --tool "<生图工具>" <图>' % (HERE / 'art_records.py')
LOCALIZE_STYLES = ('original',)
PRE_V78_CUTOFF = '2026-10-31'      # v7.8 release day: games marked new on or before it may register 「v7.8 前已有」 once
MARKER_FILE = Path('.tiktok-kit') / 'policy.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


# ------------------------------------------------------------------ reading images, sounds and model textures

def pixels(data):
    """(w, h) of a PNG / JPEG / WebP / BMP / GIF header, else None."""
    if data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) >= 24:
        return struct.unpack('>II', data[16:24])
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP' and len(data) >= 30:
        if data[12:16] == b'VP8X':
            return 1 + int.from_bytes(data[24:27], 'little'), 1 + int.from_bytes(data[27:30], 'little')
        if data[12:16] == b'VP8L':
            b = data[21:25]
            return 1 + (((b[1] & 0x3F) << 8) | b[0]), 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
        if data[12:16] == b'VP8 ':
            return struct.unpack('<H', data[26:28])[0] & 0x3FFF, struct.unpack('<H', data[28:30])[0] & 0x3FFF
    if data[:2] == b'BM' and len(data) >= 26:
        w, h = struct.unpack('<ii', data[18:26])
        return abs(w), abs(h)
    if data[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker, length = data[i + 1], struct.unpack('>H', data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack('>HH', data[i + 5:i + 9])
                return w, h
            i += 2 + length
    return None


def tiny_image(data):
    """4x4 or smaller (w*h <= 16, the reference check_rules.py rule): fill pixels, not art. Unreadable and under 200
    bytes counts as tiny too (as in the reference)."""
    dims = pixels(data)
    if dims:
        return dims[0] * dims[1] <= 16
    return len(data) < 200


def _png_end(data, start):
    """End offset of the PNG starting at `start` (walks the chunks to IEND), or None."""
    i = start + 8
    while i + 12 <= len(data):
        n = struct.unpack('>I', data[i:i + 4])[0]
        kind = data[i + 4:i + 8]
        i += 12 + n
        if kind == b'IEND':
            return i if i <= len(data) else None
    return None


def embedded_images(data, suffix):
    """[(name, bytes)] of the textures embedded in a model file.
    FBX binary: Video/Content is a raw property 'R' <uint32 length> <bytes>; FBX ASCII: Content: , "<base64>";
    GLB: images[].bufferView in the JSON chunk; glTF: data: URIs."""
    suffix = suffix.lower()
    out = []
    if suffix == '.fbx':
        if data[:18] == b'Kaydara FBX Binary':
            for sig in (b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff', b'RIFF'):
                i = 0
                while True:
                    j = data.find(sig, i)
                    if j < 0:
                        break
                    i = j + 1
                    if j >= 5 and data[j - 5:j - 4] == b'R':
                        n = struct.unpack('<I', data[j - 4:j])[0]
                        if 0 < n and j + n <= len(data):
                            out.append(('embedded-%d' % len(out), data[j:j + n]))
        else:
            for m in re.finditer(rb'Content:\s*,?\s*"([A-Za-z0-9+/=\s]{40,})"', data):
                try:
                    blob = base64.b64decode(re.sub(rb'\s', b'', m.group(1)))
                except ValueError:
                    continue
                if pixels(blob):
                    out.append(('embedded-%d' % len(out), blob))
    elif suffix == '.glb' and data[:4] == b'glTF' and len(data) >= 20:
        try:
            jlen = struct.unpack('<I', data[12:16])[0]
            doc = json.loads(data[20:20 + jlen].decode('utf-8'))
            bin_start = 20 + jlen + 8
            for k, image in enumerate(doc.get('images') or []):
                view = (doc.get('bufferViews') or [])[image['bufferView']] if 'bufferView' in image else None
                if view is not None:
                    a = bin_start + int(view.get('byteOffset', 0))
                    out.append((image.get('name') or 'image-%d' % k, data[a:a + int(view['byteLength'])]))
        except (ValueError, KeyError, IndexError, TypeError, struct.error):
            pass
    if suffix in ('.gltf', '.glb'):
        for m in re.finditer(rb'data:image/[a-z]+;base64,([A-Za-z0-9+/=]+)', data):
            try:
                out.append(('uri-%d' % len(out), base64.b64decode(m.group(1))))
            except ValueError:
                pass
    return out


def _parts(rel):
    return [x.lower() for x in PurePosixPath(rel).parts]


def _wanted(rel):
    parts = _parts(rel)
    name = parts[-1] if parts else ''
    return not (SKIP_DIRS & set(parts[:-1])) and not name.startswith('._') and name.endswith(IMAGE_EXT + MODEL_EXT + AUDIO_EXT)


def _source_files(src):
    """[(posix relative path, reader)] of every image / model / sound in a folder or ZIP. Only files below a folder named
    assets/ when there are any (a Cocos project, a source ZIP, a build); otherwise everything."""
    src = Path(src)
    rows = []
    if src.is_dir():
        root = src / 'assets' if (src / 'assets').is_dir() else src
        for p in sorted(root.rglob('*')):
            if p.is_file() and not p.is_symlink():
                rel = p.relative_to(src).as_posix()
                if _wanted(rel):
                    rows.append((rel, (lambda p=p: p.read_bytes())))
    elif src.is_file() and zipfile.is_zipfile(src):
        z = zipfile.ZipFile(src)
        names = [n for n in z.namelist() if not n.endswith('/') and _wanted(n)]
        under = [n for n in names if 'assets' in _parts(n)[:-1]]
        for n in sorted(under or names):
            rows.append((n, (lambda n=n: z.read(n))))
    else:
        raise ValueError('底子不是文件夹也不是 ZIP：%s' % src)
    return rows


def fingerprint(src):
    """{'images': {rel: sha}, 'audio': {rel: sha}, 'embedded': {'rel#name': sha}, 'tiny': n}."""
    out = {'images': {}, 'audio': {}, 'embedded': {}, 'tiny': 0}
    for rel, read in _source_files(src):
        low = rel.lower()
        data = read()
        if low.endswith(IMAGE_EXT):
            if tiny_image(data):
                out['tiny'] += 1
            else:
                out['images'][rel] = sha(data)
        elif low.endswith(AUDIO_EXT):
            out['audio'][rel] = sha(data)
        else:
            for name, blob in embedded_images(data, PurePosixPath(low).suffix):
                if not tiny_image(blob):
                    out['embedded']['%s#%s' % (rel, name)] = sha(blob)
    return out


def project_assets(project):
    """Fingerprint of <project>/assets/ with paths relative to the project (assets/...)."""
    project = Path(project)
    out = {'images': {}, 'audio': {}, 'embedded': {}, 'tiny': 0}
    root = project / 'assets'
    if not root.is_dir():
        return out
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(project).as_posix()
        if not _wanted(rel):
            continue
        data = p.read_bytes()
        low = rel.lower()
        if low.endswith(IMAGE_EXT):
            if tiny_image(data):
                out['tiny'] += 1
            else:
                out['images'][rel] = sha(data)
        elif low.endswith(AUDIO_EXT):
            out['audio'][rel] = sha(data)
        else:
            for name, blob in embedded_images(data, p.suffix):
                if not tiny_image(blob):
                    out['embedded']['%s#%s' % (rel, name)] = sha(blob)
    return out


_EXCLUDED = None


def excluded_hashes():
    """Platform-kit files and the official Cocos loading images: shipped by the Skill, never base art and never art
    the game has to generate."""
    global _EXCLUDED
    if _EXCLUDED is None:
        hs = set()
        if KIT_DIR.is_dir():
            for p in KIT_DIR.rglob('*'):
                if p.is_file() and p.name.lower().endswith(IMAGE_EXT + AUDIO_EXT):
                    hs.add(sha(p.read_bytes()))
        try:
            for row in json.loads(OFFICIAL_LOADING.read_text(encoding='utf-8')).get('assets', []):
                if row.get('sha256'):
                    hs.add(str(row['sha256']).lower())
        except (OSError, ValueError, AttributeError):
            pass
        _EXCLUDED = hs
    return _EXCLUDED


# ------------------------------------------------------------------ what goes into the package (W90b, H8 补)

UUID_RE = re.compile(rb'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
SCENE_EXT = ('.fire', '.scene')
SCRIPT_EXT = ('.ts', '.js')
STRING_RE = re.compile(r'''["'`]([^"'`\r\n]{3,200})["'`]''')
SHIP_WORDS = {'referenced': '被场景、预制体、动画、图集、材质或字体引用', 'resources': '在 resources 文件夹里',
              'bundle': '在资源包（bundle）文件夹里', 'no_meta': '没有可读的 .meta，认不出，按会进包算',
              'script': '代码里写了它的 uuid 或路径', 'build': '出现在给的构建里'}
FOLDER_ONLY = {'resources', 'bundle'}


def _meta_uuids(meta):
    """Every uuid a .meta gives its asset: the main one and all subMetas (2.4 sprite frames, 3.x textures, model
    sub-assets), recursively."""
    out = []
    if isinstance(meta, dict):
        if isinstance(meta.get('uuid'), str):
            out.append(meta['uuid'].split('@', 1)[0].lower())
        for sub in (meta.get('subMetas') or {}).values() if isinstance(meta.get('subMetas'), dict) else ():
            out += _meta_uuids(sub)
    return out


def _excluded_scenes(project):
    """2.4: settings/builder.json excludeScenes (scenes left out of the build). 3.x keeps every scene (over-report)."""
    try:
        data = json.loads((Path(project) / 'settings' / 'builder.json').read_text(encoding='utf-8-sig'))
        return {str(u).lower() for u in data.get('excludeScenes') or []}
    except (OSError, ValueError, AttributeError):
        return set()


def _build_index(build):
    """({uuid in a build file name}, {sha256 of every image / sound in it}) of a build folder or package ZIP."""
    uuids, hashes = set(), set()
    if not build:
        return uuids, hashes
    build = Path(build)
    if build.is_dir():
        items = [(p.relative_to(build).as_posix(), p.read_bytes) for p in build.rglob('*') if p.is_file()]
    elif build.is_file() and zipfile.is_zipfile(build):
        z = zipfile.ZipFile(build)
        items = [(n, (lambda n=n: z.read(n))) for n in z.namelist() if not n.endswith('/')]
    else:
        raise ValueError('构建不是文件夹也不是 ZIP：%s' % build)
    for name, read in items:
        for m in UUID_RE.findall(name.encode('utf-8')):
            uuids.add(m.decode().lower())
        if name.lower().endswith(IMAGE_EXT + AUDIO_EXT + MODEL_EXT):
            hashes.add(sha(read()))
    return uuids, hashes


def _norm_path(text):
    text = text.strip().replace('\\', '/')
    for prefix in ('db://assets/', 'assets/', './', '/'):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
    low = text.lower()
    for tail in ('/spriteframe', '/texture'):
        if low.endswith(tail):
            text = text[:-len(tail)]
    stem = PurePosixPath(text)
    return str(stem.with_suffix('')).lower() if stem.suffix.lower() in IMAGE_EXT + AUDIO_EXT + MODEL_EXT else text.lower()


def shipped(project, build=None):
    """Which images, sounds and models under <project>/assets/ go into the package (Cocos 2.4 and 3.x alike).
    A file goes in when it is
      - in any folder named resources, or in an asset-bundle folder (.meta isBundle / userData.isBundle): the whole
        folder is built;
      - referenced by uuid -- its own or a subMetas uuid (sprite frame, texture, model sub-asset) -- from a scene (2.4
        excludeScenes left out), from anything inside resources / a bundle, or from a script, directly or through other
        assets (prefab, animation, atlas, material, font: their content and their .meta are both read);
      - named in a script (uuid, or a path such as 'ui/btn_play' / 'btn_play.png': a load by path);
      - without a readable .meta (cannot be told: counted as shipped);
      - (with `build`) found in the build folder / ZIP by uuid in a file name or by bytes.
    -> {'files': {rel: [reasons]} for every shipped image / sound / model, 'unused': [rel], 'reasons_text': SHIP_WORDS,
        'scenes': n, 'build': str or None}."""
    project = Path(project).resolve()
    root = project / 'assets'
    files, metas, folder_bundle = [], {}, set()
    uuid_to = {}
    if root.is_dir():
        for p in sorted(root.rglob('*')):
            rel = p.relative_to(project).as_posix()
            parts = _parts(rel)
            if SKIP_DIRS & set(parts[:-1]) or parts[-1].startswith('._') or p.is_symlink():
                continue
            if p.is_file() and p.name.endswith('.meta'):
                target = rel[:-5]
                try:
                    meta = json.loads(p.read_text(encoding='utf-8-sig'))
                except (OSError, ValueError, UnicodeDecodeError):
                    continue
                if not isinstance(meta, dict):
                    continue
                metas[target] = meta
                for u in _meta_uuids(meta):
                    uuid_to.setdefault(u, target)
                user = meta.get('userData') if isinstance(meta.get('userData'), dict) else {}
                if meta.get('isBundle') is True or user.get('isBundle') is True:
                    folder_bundle.add(target)
            elif p.is_file():
                files.append(rel)
    reasons = {}

    def add(rel, why):
        reasons.setdefault(rel, [])
        if why not in reasons[rel]:
            reasons[rel].append(why)

    media = [r for r in files if r.lower().endswith(IMAGE_EXT + AUDIO_EXT + MODEL_EXT)]
    excluded = _excluded_scenes(project)
    roots, scenes = [], 0
    for rel in files:
        low = rel.lower()
        parts = _parts(rel)
        ancestors = ['/'.join(rel.split('/')[:i]) for i in range(2, len(parts))]
        if 'resources' in parts[1:-1]:
            add(rel, 'resources')
            roots.append(rel)
        elif any(a in folder_bundle for a in ancestors):
            add(rel, 'bundle')
            roots.append(rel)
        if low.endswith(SCENE_EXT):
            own = _meta_uuids(metas.get(rel) or {})
            if not (own and own[0] in excluded):
                roots.append(rel)
                scenes += 1
        elif low.endswith(SCRIPT_EXT):
            roots.append(rel)
        if rel in media and not _meta_uuids(metas.get(rel) or {}):
            add(rel, 'no_meta')
    # references: walk from the roots through every asset's content (non-media files) and its .meta
    seen, queue = set(), list(dict.fromkeys(roots))
    literals = set()
    while queue:
        rel = queue.pop()
        if rel in seen:
            continue
        seen.add(rel)
        low = rel.lower()
        blobs = []
        if not low.endswith(IMAGE_EXT + AUDIO_EXT + MODEL_EXT):
            try:
                path = project / rel
                if path.stat().st_size <= 64 * 1024 * 1024:
                    blobs.append(path.read_bytes())
            except OSError:
                pass
        meta = metas.get(rel)
        if meta is not None:
            blobs.append(json.dumps(meta).encode('utf-8'))
        own = set(_meta_uuids(meta or {}))
        script = low.endswith(SCRIPT_EXT)
        for blob in blobs:
            for m in UUID_RE.findall(blob):
                u = m.decode().lower()
                target = uuid_to.get(u)
                if not target or u in own and target == rel:
                    continue
                if target in media:
                    add(target, 'script' if script else 'referenced')
                if target not in seen:
                    queue.append(target)
        if script and blobs:
            for m in STRING_RE.finditer(blobs[0].decode('utf-8', 'replace')):
                literals.add(m.group(1))
    # a load by path in code: a literal naming the file (two or more path parts, or the file name with its extension)
    tails, names = set(), set()
    for lit in literals:
        bits = [b for b in _norm_path(lit).split('/') if b]
        for i in range(len(bits) - 1):
            tails.add('/'.join(bits[i:]))
        last = lit.strip().replace('\\', '/').split('/')[-1].lower()
        if last.endswith(IMAGE_EXT + AUDIO_EXT + MODEL_EXT):
            names.add(last)
    for rel in media:
        if rel in reasons and 'referenced' in reasons[rel]:
            continue
        bits = str(PurePosixPath(rel[len('assets/'):]).with_suffix('')).lower().split('/')
        keys = {'/'.join(bits[i:]) for i in range(len(bits) - 1)}
        if keys & tails or PurePosixPath(rel).name.lower() in names:
            add(rel, 'script')
    if build:
        b_uuids, b_hashes = _build_index(build)
        for rel in media:
            own = set(_meta_uuids(metas.get(rel) or {}))
            try:
                digest = sha((project / rel).read_bytes())
            except OSError:
                digest = None
            if own & b_uuids or digest in b_hashes:
                add(rel, 'build')
    return {'files': {r: reasons[r] for r in media if r in reasons}, 'unused': [r for r in media if r not in reasons],
            'scenes': scenes, 'build': str(build) if build else None}


def ship_reason(ship, rel):
    """[reasons] for an images / sounds / embedded-texture row (rel may be 'model.fbx#embedded-0'); [] = not shipped.
    ship None = not known: everything counts as shipped."""
    if ship is None:
        return ['no_meta']
    return ship['files'].get(rel.split('#', 1)[0], [])


# ------------------------------------------------------------------ JSON files under docs/art

def _read(project, rel):
    path = Path(project) / rel
    if not path.is_file():
        return None, None
    try:
        return json.loads(path.read_text(encoding='utf-8-sig')), None
    except (OSError, ValueError) as error:
        return None, '%s 读不了：%s' % (rel.as_posix(), error)


def _write(project, rel, data):
    path = Path(project) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    os.close(fd)
    try:
        Path(tmp).write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def read_base(project):
    """-> (record or None, error or None). record['base'] == 'none' for a game without a base."""
    data, error = _read(project, BASE_FILE)
    if data is None:
        return None, error
    if not isinstance(data, dict) or not data.get('base'):
        return None, '%s 不是底子记录（缺 base）' % BASE_FILE.as_posix()
    if data.get('base') == 'none':
        if not str(data.get('why') or '').strip():
            return None, '%s 写了 base none 但没写 why' % BASE_FILE.as_posix()
        return data, None
    if not all(isinstance(data.get(k), dict) for k in ('images', 'audio')):
        return None, '%s 缺 images / audio' % BASE_FILE.as_posix()
    return data, None


def _rows(data, key):
    if isinstance(data, dict):
        data = data.get(key)
    return [x for x in data if isinstance(x, dict)] if isinstance(data, list) else []


def _match(entry, rel, digest, also=()):
    if entry.get('sha256') and str(entry['sha256']).lower() == digest:
        return True
    glob = str(entry.get('file') or '').strip()
    if not glob:
        return False
    for path in (rel,) + tuple(also):
        file_part = path.split('#', 1)[0]
        for cand in (path, file_part):
            if cand == glob or fnmatch.fnmatch(cand, glob) or fnmatch.fnmatch(cand, 'assets/' + glob.lstrip('/')):
                return True
    return False


def _justified(project, rel_file, key):
    """(entries with a why, entries without one) of base-keep.json / script-drawn-allow.json."""
    data, error = _read(project, rel_file)
    rows = _rows(data, key)
    good = [x for x in rows if str(x.get('why') or '').strip()]
    bad = [x for x in rows if not str(x.get('why') or '').strip()]
    return good, bad, error


def record_base(project, base):
    project, base = Path(project).resolve(), Path(base).resolve()
    if not base.exists():
        raise ValueError('底子不存在：%s' % base)
    if base == project:
        raise ValueError('底子就是这个工程本身：要给开工前的原版（工程文件夹或源码 ZIP）')
    fp = fingerprint(base)
    if not (fp['images'] or fp['audio'] or fp['embedded']):
        raise ValueError('底子里没有找到任何图片、声音或模型贴图：%s' % base)
    data = {'kind': 'base-assets', 'schema': SCHEMA, 'base': str(base), 'base_type': 'zip' if base.is_file() else 'dir',
            'base_sha256': sha(base.read_bytes()) if base.is_file() else None, 'recorded': now(),
            'counts': {k: len(fp[k]) for k in ('images', 'audio', 'embedded')}, 'tiny_skipped': fp['tiny'],
            'images': fp['images'], 'audio': fp['audio'], 'embedded': fp['embedded'], 'derived': {}}
    _write(project, BASE_FILE, data)
    return data


def record_none(project, why):
    if not str(why or '').strip():
        raise ValueError('没有底子也要写 why')
    data = {'kind': 'base-assets', 'schema': SCHEMA, 'base': 'none', 'why': str(why).strip(), 'recorded': now()}
    _write(Path(project), BASE_FILE, data)
    return data


def base_hashes(record):
    """({image sha: base file}, {audio sha: base file}) incl. embedded textures and tiktok_finalize-derived bytes."""
    images, audio = {}, {}
    if not record or record.get('base') == 'none':
        return images, audio
    for rel, h in sorted((record.get('images') or {}).items()):
        images.setdefault(str(h).lower(), rel)
    for rel, h in sorted((record.get('embedded') or {}).items()):
        h = str(h).lower()
        # a model texture that is also a loose file in the base: name both (企鹅雪道: Fishbone.fbx = FishboneAlbedo.jpg)
        images[h] = '%s = %s' % (images[h], rel) if h in images and '#' not in images[h] else images.get(h, rel)
    for rel, h in sorted((record.get('audio') or {}).items()):
        audio.setdefault(str(h).lower(), rel)
    for h, row in sorted((record.get('derived') or {}).items()):
        target = audio if str(row.get('kind')) == 'audio' else images
        target.setdefault(str(h).lower(), '%s（%s 转换后）' % (row.get('base_file') or row.get('from_file'), row.get('by')))
    return images, audio


# ------------------------------------------------------------------ generated-art records

def _rel(project, path):
    p = Path(path).resolve()
    try:
        return p.relative_to(Path(project).resolve()).as_posix()
    except ValueError:
        return str(p)


def _generated(project):
    data, error = _read(project, GENERATED_FILE)
    if error:
        raise ValueError(error)
    if not isinstance(data, dict):
        data = {'kind': 'generated-art', 'schema': SCHEMA, 'images': []}
    data.setdefault('images', [])
    return data


def valid_generated(project):
    """{sha: entry} of every recorded picture that traces back to a generated (prompt + tool) or library (source +
    license) entry, plus (problems: entries that do not)."""
    data, error = _read(project, GENERATED_FILE)
    rows = _rows(data, 'images')
    ok = {}
    for x in rows:
        h = str(x.get('sha256') or '').lower()
        if not h or x.get('from_sha256'):
            continue
        if (str(x.get('prompt') or '').strip() and str(x.get('tool') or '').strip()) or \
                (str(x.get('source') or '').strip() and str(x.get('license') or '').strip()) or \
                (x.get('pre_v78') is True and str(x.get('why') or '').strip()):
            ok[h] = x
    changed = True
    while changed:
        changed = False
        for x in rows:
            h, src = str(x.get('sha256') or '').lower(), str(x.get('from_sha256') or '').lower()
            if h and src and src in ok and h not in ok:
                ok[h] = x
                changed = True
    bad = [x for x in rows if str(x.get('sha256') or '').lower() not in ok]
    return ok, bad, error, rows


def record_generated(project, files, tool, prompt=None, date=None, raw=None, source=None, license_=None):
    project = Path(project).resolve()
    if not str(tool or '').strip():
        raise ValueError('要写 --tool（用的生图工具，例如 codex image_gen）')
    if not (str(prompt or '').strip() or (str(source or '').strip() and str(license_ or '').strip())):
        raise ValueError('要写 --prompt（提示词）；素材库下载的图写 --source 和 --license')
    data = _generated(project)
    date = date or dt.date.today().isoformat()
    known = set(valid_generated(project)[0])      # an earlier entry without prompt/source does not count
    added = []
    base = {'tool': str(tool).strip(), 'date': date, 'recorded': now()}
    if prompt:
        base['prompt'] = str(prompt).strip()
    if source:
        base.update(source=str(source).strip(), license=str(license_ or '').strip())
    root_sha = None
    if raw:
        raw_data = Path(raw).read_bytes()
        root_sha = sha(raw_data)
        if root_sha not in known:
            data['images'].append(dict(base, sha256=root_sha, file=_rel(project, raw), raw=True))
            known.add(root_sha)
            added.append(data['images'][-1])
    for f in files:
        p = Path(f)
        if not p.is_file():
            raise ValueError('图不存在：%s' % f)
        h = sha(p.read_bytes())
        if h in known:
            continue
        if root_sha and h != root_sha:
            entry = dict(base, sha256=h, file=_rel(project, p), from_sha256=root_sha,
                         how='processed from the generator output (crop / resize / compress)')
        else:
            entry = dict(base, sha256=h, file=_rel(project, p))
        data['images'].append(entry)
        known.add(h)
        added.append(entry)
    _write(project, GENERATED_FILE, data)
    return added


def _marker_created(project):
    """Day the new-game marker was written (YYYY-MM-DD), or None."""
    try:
        data = json.loads((Path(project) / MARKER_FILE).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    created = str(data.get('created') or '')[:10] if isinstance(data, dict) and data.get('policy') == 'new' else ''
    return created or None


def record_pre_v78(project, why):
    """Saul 10-30: once per game marked new on or before the v7.8 release day, record every picture already under
    assets/ that has no generated record as 「v7.8 前已有」. -> the entries added."""
    project = Path(project).resolve()
    if not str(why or '').strip():
        raise ValueError('要写 --why（例如：装 v7.8 时工程里已有的图）')
    created = _marker_created(project)
    if not created:
        raise ValueError('找不到新游戏标记 %s：「v7.8 前已有」只给装 v7.8 前已开工的新游戏用' % MARKER_FILE.as_posix())
    if created > PRE_V78_CUTOFF:
        raise ValueError('这款游戏 %s 才标成新游戏，晚于 v7.8（%s）：新做的图要用 generated 记录，不能登记「v7.8 前已有」'
                         % (created, PRE_V78_CUTOFF))
    data = _generated(project)
    if any(x.get('pre_v78') for x in data['images']):
        raise ValueError('%s 里已经登记过一次「v7.8 前已有」，只能登记一次；之后新做的图用 generated 记录'
                         % GENERATED_FILE.as_posix())
    assets = project_assets(project)
    record, _ = read_base(project)
    images, _ = base_hashes(record)
    skip = excluded_hashes()
    ok, _, _, _ = valid_generated(project)
    allow, _, _ = _justified(project, ALLOW_FILE, 'allow')
    today = dt.date.today().isoformat()
    added, seen = [], set()
    for rel, h in sorted(assets['images'].items()):
        if h in skip or h in images or h in ok or h in seen or any(_match(x, rel, h) for x in allow):
            continue                       # base-identical stays H8; kit / official / recorded / allowed need nothing
        seen.add(h)
        added.append({'sha256': h, 'file': rel, 'pre_v78': True, 'why': str(why).strip(), 'by': 'art_records pre-v78',
                      'marker_created': created, 'date': today, 'recorded': now()})
    data['images'].extend(added)
    _write(project, GENERATED_FILE, data)
    return added


def _pre_v78_root(ok, h):
    """True when the recorded picture h traces back (through derive) to a 「v7.8 前已有」 entry."""
    x, hops = ok.get(h), 0
    while x is not None and hops < 64:
        if x.get('pre_v78') is True:
            return True
        src = str(x.get('from_sha256') or '').lower()
        x, hops = (ok.get(src) if src else None), hops + 1
    return False


def record_derived(project, files, origin=None, how=None, by='art_records derive'):
    """A recorded picture that was edited (cropped, resized, recoloured, compressed): new sha, from_sha256 = the recorded
    one (the entry for the same file, or `origin` = a file or a sha)."""
    project = Path(project).resolve()
    data = _generated(project)
    ok, _, _, rows = valid_generated(project)
    added = []
    for f in files:
        p = Path(f)
        if not p.is_file():
            raise ValueError('图不存在：%s' % f)
        h = sha(p.read_bytes())
        if h in ok:
            continue
        rel = _rel(project, p)
        if origin:
            o = Path(origin)
            src = sha(o.read_bytes()) if o.is_file() else str(origin).lower()
        else:
            same = [x for x in rows if x.get('file') == rel and str(x.get('sha256')).lower() in ok]
            src = str(same[-1]['sha256']).lower() if same else None
        if not src or src not in ok:
            raise ValueError('%s：找不到它来自哪张有记录的生成图；先用 generated 记原图，或用 --from 指明' % rel)
        entry = {'sha256': h, 'file': rel, 'from_sha256': src, 'how': how or 'edited after generation', 'by': by,
                 'date': dt.date.today().isoformat(), 'recorded': now()}
        data['images'].append(entry)
        ok[h] = entry
        added.append(entry)
    _write(project, GENERATED_FILE, data)
    return added


def record_reason(project, which, files, why):
    if not str(why or '').strip():
        raise ValueError('要写 --why')
    rel_file, key = (KEEP_FILE, 'keep') if which == 'keep' else (ALLOW_FILE, 'allow')
    data, error = _read(project, rel_file)
    if error:
        raise ValueError(error)
    if isinstance(data, list):
        data = {key: data}
    if not isinstance(data, dict):
        data = {key: []}
    data.setdefault(key, [])
    for f in files:
        p = Path(f)
        name = _rel(project, p) if p.exists() else str(f)
        data[key].append({'file': name, 'why': str(why).strip(), 'date': dt.date.today().isoformat()})
    _write(Path(project), rel_file, data)
    return data[key][-len(files):] if files else []


# ------------------------------------------------------------------ checks

def applies(project, board=None, art_style=None):
    """(checked, board, style): H8 is checked for board remake unless docs/art-style.txt says original."""
    project = Path(project)
    if not board:
        f = project / 'docs' / 'board.txt'
        text = f.read_text(encoding='utf-8').strip().lower() if f.is_file() else ''
        board = text if text in ('remake', 'localize') else 'remake'
    if art_style is None:
        f = project / 'docs' / 'art-style.txt'
        art_style = f.read_text(encoding='utf-8').strip().lower() if f.is_file() else ''
    return board == 'remake' and art_style not in LOCALIZE_STYLES, board, art_style


def _short(items, n=8):
    return '、'.join(items[:n]) + ('……共 %d 个' % len(items) if len(items) > n else '')


def _unused_hint(rows, what):
    """'工程里没用到' line: not a finding, never blocks (W90b)."""
    if not rows:
        return ''
    return '；另有 %d 个%s工程里没用到、不会进包（不拦，建议删掉）：%s' % (len(rows), what, _short(rows, 5))


def _ship(project, ship, build):
    if ship is not None:
        return ship
    try:
        return shipped(project, build)
    except Exception as error:  # noqa: BLE001 - cannot tell what ships: everything counts (over-report)
        return {'files': {}, 'unused': [], 'error': repr(error), 'all': True}


def _reason(ship, rel):
    return ['no_meta'] if ship.get('all') else ship_reason(ship, rel)


def check_base(project, board=None, art_style=None, assets=None, ship=None, build=None):
    """H8. -> {'state', 'ok' True|False|None, 'same', 'kept', 'unlisted', 'unused', 'invalid_keep', 'message', 'counts'}.
    state: not_applicable | nothing | no_record | unreadable | none | checked.
    W90b: only files that go into the package (shipped()) are findings; base-identical files the project never uses are
    listed in 'unused' (a hint to delete them, never a block)."""
    project = Path(project).resolve()
    checked, board, style = applies(project, board, art_style)
    out = {'state': None, 'ok': None, 'same': [], 'kept': [], 'unlisted': [], 'unused': [], 'invalid_keep': [],
           'board': board, 'art_style': style or None, 'record': BASE_FILE.as_posix()}
    if not checked:
        out.update(state='not_applicable', message='英化（board localize / art-style original）保留原图原声，不查')
        return out
    assets = assets or project_assets(project)
    out['counts'] = {k: len(assets[k]) for k in ('images', 'audio', 'embedded')}
    if not (assets['images'] or assets['audio'] or assets['embedded']):
        out.update(state='nothing', ok=True, message='assets/ 下没有图片、声音或模型贴图，没有要核对的')
        return out
    record, error = read_base(project)
    if record is None:
        out.update(state='unreadable' if error else 'no_record', ok=False,
                   message='%s；重塑开工时要记下底子：%s（从零做的写：%s）' % (
                       error or '没有底子记录 %s' % BASE_FILE.as_posix(), BASE_CMD % project, NONE_CMD % project))
        return out
    if record.get('base') == 'none':
        out.update(state='none', ok=True, message='没有底子（%s）' % record.get('why'))
        return out
    images, audio = base_hashes(record)
    skip = excluded_hashes()
    ship = _ship(project, ship, build)
    keep, invalid, keep_error = _justified(project, KEEP_FILE, 'keep')
    out['invalid_keep'] = [x.get('file') or x.get('sha256') for x in invalid]
    for kind, table, base in (('image', assets['images'], images), ('embedded', assets['embedded'], images),
                              ('audio', assets['audio'], audio)):
        for rel, h in sorted(table.items()):
            if h in skip or h not in base:
                continue
            row = {'file': rel, 'kind': kind, 'sha256': h, 'base_file': base[h]}
            why = _reason(ship, rel)
            if not why:
                out['unused'].append(row)
                continue
            row['shipped'] = why
            hit = next((x for x in keep if _match(x, rel, h)), None)
            if hit:
                row['why'] = hit['why']
                out['kept'].append(row)
            else:
                out['unlisted'].append(row)
            out['same'].append(row)
    out['state'] = 'checked'
    out['ok'] = not out['unlisted'] and not keep_error
    words = {'image': '图', 'embedded': '模型内嵌贴图', 'audio': '声音'}
    if out['unlisted']:
        parts = []
        for kind in ('image', 'embedded', 'audio'):
            rows = [r['file'] for r in out['unlisted'] if r['kind'] == kind]
            if rows:
                parts.append('%s %d 个：%s' % (words[kind], len(rows), _short(rows)))
        folder_only = [r['file'] for r in out['unlisted'] if set(r['shipped']) <= FOLDER_ONLY]
        out['message'] = ('会进包、和底子逐字节相同、没登记的 %d 个（%s）：换掉；确实要留的写进 %s 并写 why（%s）'
                          % (len(out['unlisted']), '；'.join(parts), KEEP_FILE.as_posix(),
                             'python3 %s keep --project "%s" --why "<原因>" <文件>' % (HERE / 'art_records.py', project)))
        if folder_only:
            out['message'] += ('；其中 %d 个只是因为放在 resources 或资源包文件夹里才进包，没有场景、预制体引用，'
                               '代码也没写它的路径：多半用不到，删掉即可（%s）' % (len(folder_only), _short(folder_only, 5)))
    else:
        out['message'] = '工程 %d 张图、%d 个模型内嵌贴图、%d 个声音，会进包的里和底子相同的 %d 个都已登记' % (
            out['counts']['images'], out['counts']['embedded'], out['counts']['audio'], len(out['kept'])) \
            if out['kept'] else '工程 %d 张图、%d 个模型内嵌贴图、%d 个声音，会进包的里 0 个和底子相同' % (
            out['counts']['images'], out['counts']['embedded'], out['counts']['audio'])
    out['message'] += _unused_hint([r['file'] for r in out['unused']], '和底子相同的文件')
    if ship.get('error'):
        out['message'] += '；认不出哪些会进包（%s），全部按会进包算' % ship['error']
    if keep_error:
        out['message'] += '；' + keep_error
    if out['kept']:
        out['message'] += '；留着的：' + _short(['%s（%s）' % (r['file'], r['why'][:30]) for r in out['kept']], 5)
    if out['invalid_keep']:
        out['message'] += '；%s 里 %d 条没写 why，不算' % (KEEP_FILE.as_posix(), len(out['invalid_keep']))
    return out


def check_generated(project, board=None, art_style=None, assets=None, ship=None, build=None):
    """H10. -> {'state', 'ok', 'strict', 'unrecorded', 'edited', 'allowed', 'recorded', 'unused', 'message'}.
    strict False (English game): findings are a warning (ok None). W90b: only pictures that go into the package count;
    unrecorded pictures the project never uses are listed in 'unused' (hint only)."""
    project = Path(project).resolve()
    strict, board, style = applies(project, board, art_style)
    out = {'state': None, 'ok': None, 'strict': strict, 'unrecorded': [], 'edited': [], 'allowed': [], 'recorded': 0,
           'pre_v78': 0, 'unused': [], 'board': board, 'record': GENERATED_FILE.as_posix()}
    assets = assets or project_assets(project)
    record, error = read_base(project)
    if not strict and (record is None or record.get('base') == 'none'):
        out.update(state='not_applicable',
                   message='英化游戏：没有记下原版（%s），分不出哪些是新做的图，只提示' % BASE_FILE.as_posix())
        return out
    if not assets['images']:
        out.update(state='nothing', ok=True, message='assets/ 下没有图片')
        return out
    images, _ = base_hashes(record)
    skip = excluded_hashes()
    ok, bad, gen_error, rows = valid_generated(project)
    allow, invalid, allow_error = _justified(project, ALLOW_FILE, 'allow')
    by_file = {}
    for x in rows:
        if x.get('file') and str(x.get('sha256')).lower() in ok:
            by_file[x['file']] = x
    ship = _ship(project, ship, build)
    for rel, h in sorted(assets['images'].items()):
        if h in skip or h in images:
            continue                       # H8 (base) or kit / official loading
        if h in ok:
            out['recorded'] += 1
            if _pre_v78_root(ok, h) and _reason(ship, rel):
                out['pre_v78'] += 1        # listed in every report (Saul 10-30): registered, not generated
            continue
        if not _reason(ship, rel):
            out['unused'].append(rel)      # never shipped: not counted (W90b)
            continue
        hit = next((x for x in allow if _match(x, rel, h)), None)
        if hit:
            out['allowed'].append({'file': rel, 'why': hit['why']})
        elif rel in by_file:
            out['edited'].append({'file': rel, 'sha256': h, 'recorded_sha256': by_file[rel].get('sha256')})
        else:
            out['unrecorded'].append({'file': rel, 'sha256': h})
    out['state'] = 'checked'
    problems = out['unrecorded'] + out['edited']
    errors = [e for e in (gen_error, allow_error) if e]
    out['ok'] = (not problems and not errors) if strict else (True if not problems and not errors else None)
    tail = []
    if out['unrecorded']:
        tail.append('不是生成的图（没有生成记录）%d 张：%s' % (len(out['unrecorded']), _short([r['file'] for r in out['unrecorded']])))
    if out['edited']:
        tail.append('生成后又改过、没补记 %d 张：%s（是同一张图裁切/压缩就跑 `python3 %s derive --project "%s" <图>`）'
                    % (len(out['edited']), _short([r['file'] for r in out['edited']]), HERE / 'art_records.py', project))
    if problems:
        out['message'] = '；'.join(tail) + '。按钮和数字要用生图工具出图，每出一张跑 %s；确实要代码画的（纯色九宫格底板）写进 %s 并写 why' % (
            GEN_CMD % project, ALLOW_FILE.as_posix())
        if not strict:
            out['message'] = '英化游戏只提示：' + out['message']
    elif not out['recorded'] and not out['allowed']:
        out['message'] = '没有新做的图（其余都是底子原图、平台包或 4x4 以内的填充图）'
    else:
        out['message'] = '新做的图 %d 张都有生成记录%s' % (out['recorded'], '，代码画的 %d 张已登记' % len(out['allowed'])
                                                     if out['allowed'] else '')
    if out['pre_v78']:
        out['message'] += '；其中 %d 张是「v7.8 前已有」（装 v7.8 时一次性登记，不是生成记录）' % out['pre_v78']
    out['message'] += _unused_hint(out['unused'], '没有生成记录的图')
    if errors:
        out['message'] += '；' + '；'.join(errors)
    if bad:
        out['message'] += '；%s 里 %d 条找不到提示词或来源，不算' % (GENERATED_FILE.as_posix(), len(bad))
    if invalid:
        out['message'] += '；%s 里 %d 条没写 why，不算' % (ALLOW_FILE.as_posix(), len(invalid))
    return out


def check(project, board=None, art_style=None, build=None):
    """build: optional build folder or package ZIP; a file found in it counts as shipped as well."""
    assets = project_assets(project)
    ship = _ship(Path(project).resolve(), None, build)
    return {'base': check_base(project, board, art_style, assets, ship),
            'generated': check_generated(project, board, art_style, assets, ship)}


def summary(result):
    b, g = result['base'], result['generated']
    return {'base_state': b['state'], 'base_ok': b['ok'], 'base_unlisted': len(b['unlisted']), 'base_kept': len(b['kept']),
            'base_unused': len(b.get('unused') or []), 'generated_state': g['state'], 'generated_ok': g['ok'],
            'not_generated': len(g['unrecorded']) + len(g['edited']), 'allowed': len(g['allowed']),
            'pre_v78': g.get('pre_v78') or 0, 'generated_unused': len(g.get('unused') or [])}


def base_audio_now(project, board=None):
    """For the package writers (art_receipt.check): sounds byte-identical to the recorded base and not kept.
    [] when not applicable or nothing recorded (art_check already failed a missing record)."""
    checked, _, _ = applies(project, board)
    record, _ = read_base(project)
    if not checked or not record or record.get('base') == 'none':
        return []
    assets = {'images': {}, 'embedded': {}, 'audio': {}}
    root = Path(project) / 'assets'
    for p in sorted(root.rglob('*')) if root.is_dir() else []:
        rel = p.relative_to(project).as_posix()
        if p.is_file() and rel.lower().endswith(AUDIO_EXT) and _wanted(rel):
            assets['audio'][rel] = sha(p.read_bytes())
    _, audio = base_hashes(record)
    keep, _, _ = _justified(project, KEEP_FILE, 'keep')
    skip = excluded_hashes()
    same = [rel for rel, h in sorted(assets['audio'].items())
            if h in audio and h not in skip and not any(_match(x, rel, h) for x in keep)]
    if not same:
        return []
    ship = _ship(Path(project).resolve(), None, None)      # W90b: only sounds that go into the package
    return [rel for rel in same if _reason(ship, rel)]


# ------------------------------------------------------------------ tiktok_finalize source: follow its own conversions

def snapshot(project):
    """{rel: sha} of the standalone images and sounds under assets/ (before tiktok_finalize's steps)."""
    a = project_assets(project)
    out = dict(a['images'])
    out.update(a['audio'])
    return out


def _pairs(before, after):
    """[(old rel, old sha, new rel, new sha)]: same path with new bytes, or x.webp -> x.png / x.jpg."""
    out = []
    gone = {k: v for k, v in before.items() if k not in after}
    stems = {}
    for k, v in gone.items():
        stems.setdefault(str(PurePosixPath(k).with_suffix('')), (k, v))
    for rel, h in sorted(after.items()):
        if rel in before:
            if before[rel] != h:
                out.append((rel, before[rel], rel, h))
        else:
            old = stems.get(str(PurePosixPath(rel).with_suffix('')))
            if old:
                out.append((old[0], old[1], rel, h))
    return out


def carry(project, before, by='tiktok_finalize source'):
    """Record the bytes `by` itself wrote: a generated picture it converted or shrank gets a derived entry, a base file
    it converted stays recognisable as base (base-assets.json 'derived'), keep / allow entries follow a renamed file.
    -> {'generated': n, 'base': n, 'keep': n, 'allow': n}. Never raises."""
    project = Path(project)
    counts = {'generated': 0, 'base': 0, 'keep': 0, 'allow': 0}
    try:
        pairs = _pairs(before or {}, snapshot(project))
        if not pairs:
            return counts
        ok, _, _, _ = valid_generated(project)
        if ok:
            data = _generated(project)
            for old_rel, old_h, rel, h in pairs:
                if old_h in ok and h not in ok:
                    data['images'].append({'sha256': h, 'file': rel, 'from_sha256': old_h, 'by': by,
                                           'how': 'converted / shrunk by %s' % by, 'date': dt.date.today().isoformat(),
                                           'recorded': now()})
                    ok[h] = data['images'][-1]
                    counts['generated'] += 1
            if counts['generated']:
                _write(project, GENERATED_FILE, data)
        record, _ = read_base(project)
        if record and record.get('base') != 'none':
            images, audio = base_hashes(record)
            for old_rel, old_h, rel, h in pairs:
                if (old_h in images or old_h in audio) and h not in images and h not in audio:
                    record.setdefault('derived', {})[h] = {
                        'from_sha256': old_h, 'from_file': old_rel, 'file': rel, 'by': by,
                        'base_file': images.get(old_h) or audio.get(old_h),
                        'kind': 'audio' if old_h in audio else 'image'}
                    counts['base'] += 1
            if counts['base']:
                _write(project, BASE_FILE, record)
        for which, rel_file, key in (('keep', KEEP_FILE, 'keep'), ('allow', ALLOW_FILE, 'allow')):
            data, error = _read(project, rel_file)
            rows = _rows(data, key)
            if error or not rows:
                continue
            extra = []
            for old_rel, old_h, rel, h in pairs:
                if old_rel == rel:
                    continue
                for x in rows:
                    if str(x.get('why') or '').strip() and _match(x, old_rel, old_h) and not _match(x, rel, h):
                        extra.append({'file': rel, 'why': x['why'], 'from_file': old_rel, 'by': by})
                        break
            if extra:
                if isinstance(data, list):
                    data = {key: data}
                data[key] = list(data.get(key) or []) + extra
                _write(project, rel_file, data)
                counts[which] = len(extra)
    except Exception as error:  # noqa: BLE001 - recording follows the source phase, it never stops it
        counts['error'] = repr(error)
    return counts


# ------------------------------------------------------------------ CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0],
                                 epilog=__doc__.split('CLI\n', 1)[-1], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('base', help='记下底子（开工时；已开工的游戏补记）')
    p.add_argument('--project', required=True, type=Path)
    p.add_argument('--from', dest='base', type=Path, help='底子工程文件夹或源码 ZIP')
    p.add_argument('--none', action='store_true', help='从零做，没有底子')
    p.add_argument('--why')
    p = sub.add_parser('generated', help='记下生成的图（处理成最终文件后，每张跑一次）')
    p.add_argument('--project', required=True, type=Path)
    p.add_argument('--prompt')
    p.add_argument('--tool', required=True)
    p.add_argument('--date')
    p.add_argument('--raw', type=Path, help='生图工具直接给的原图（最终文件是裁切/压缩后的）')
    p.add_argument('--source', help='素材库下载的图：来源网址')
    p.add_argument('--license', help='素材库下载的图：授权（CC0 等）')
    p.add_argument('files', nargs='+', type=Path)
    p = sub.add_parser('derive', help='有记录的生成图又裁切/压缩/调色后，记下新文件')
    p.add_argument('--project', required=True, type=Path)
    p.add_argument('--from', dest='origin', help='来自哪张有记录的图（文件或 sha256；不写就找同一路径的记录）')
    p.add_argument('--how')
    p.add_argument('files', nargs='+', type=Path)
    for name, text in (('keep', '登记确实要留的底子文件'), ('allow', '登记确实要代码画的图')):
        p = sub.add_parser(name, help=text)
        p.add_argument('--project', required=True, type=Path)
        p.add_argument('--why', required=True)
        p.add_argument('files', nargs='+')
    p = sub.add_parser('pre-v78', help='装 v7.8 时一次性登记工程里已有、没有生成记录的图（只给 v7.8 前已开工的新游戏）')
    p.add_argument('--project', required=True, type=Path)
    p.add_argument('--why', required=True)
    p = sub.add_parser('check', help='只读：查 H8 / H10')
    p.add_argument('--project', required=True, type=Path)
    p.add_argument('--board', choices=('remake', 'localize'))
    p.add_argument('--build', type=Path, help='构建文件夹或 TikTok 包 ZIP：出现在里面的也算会进包')
    p.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'base':
            if a.none == bool(a.base):
                ap.error('给 --from <底子> 或 --none --why "..." 其中一个')
            data = record_none(a.project, a.why) if a.none else record_base(a.project, a.base)
            print(json.dumps({k: data.get(k) for k in ('base', 'why', 'counts', 'tiny_skipped', 'recorded')},
                             ensure_ascii=False))
            print('已写 %s' % (a.project / BASE_FILE))
            return 0
        if a.cmd == 'generated':
            rows = record_generated(a.project, a.files, a.tool, a.prompt, a.date, a.raw, a.source, a.license)
        elif a.cmd == 'derive':
            rows = record_derived(a.project, a.files, a.origin, a.how)
        elif a.cmd in ('keep', 'allow'):
            rows = record_reason(a.project, a.cmd, a.files, a.why)
        elif a.cmd == 'pre-v78':
            rows = record_pre_v78(a.project, a.why)
            print('登记了 %d 张「v7.8 前已有」的图（只能登记这一次；之后新做的图每张跑 generated）' % len(rows), file=sys.stderr)
        else:
            result = check(a.project, a.board, build=a.build)
            if a.json:
                print(json.dumps(result, ensure_ascii=False, indent=1))
            else:
                print('H8 底子原图原声：%s' % result['base']['message'])
                print('H10 生图记录：%s' % result['generated']['message'])
            return 0 if result['base']['ok'] is not False and result['generated']['ok'] is not False else 1
    except ValueError as error:
        print('拒绝：%s' % error, file=sys.stderr)
        return 1
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
