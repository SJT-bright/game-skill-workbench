#!/usr/bin/env python3
"""Size limits for images made during English localisation (v7.5, MusicSlice item 6). Read-only.

MusicSlice v29b replaced its result/settings art with English images of 1.5-2.2 MB each (result-btn-retry.png 1983x793,
shown about 390 wide: 5x), so about 25 MB had to download before the home page. Only NEW images are judged: an image
whose SHA-256 is in the pre-English list (the Chinese original's images) is the game's own art and is never refused, so
completed games are not affected.

  new image > 800,000 bytes                            -> refused
  new image wider or taller than 2.5x its display size -> refused (display size from the prefab/scene, when known)
Export new English images at 2x display size, then compress (the 2x rule of audit_image_clarity.py).

API:  check(images, pre_english, display=None) -> {"passed": bool, "problems": [...], "new_images": [...]}
  images: {name: bytes} or iterable of (name, bytes); pre_english: iterable of SHA-256 strings, or a JSON file
  {"images": {sha: name}} / [sha, ...], or (v7.8) the original recorded by `art_records.py base`
  (docs/art/base-assets.json); display: optional {name or sha: (width, height)}.
CLI:  python3 audit_new_english_images.py --zip <upload.zip> --pre-english <list.json> [--out report.json]
      python3 audit_new_english_images.py --make-list <Chinese original project dir> --out <list.json> [--ocr auto|none]
      P16 (2026-11-04): --make-list also cuts every atlas slice / animation frame, reads each with the local OCR and
      writes art-replace-round1.json next to --out: "replace" = pictures/slices with Chinese (first art round), "manual_review"
      = unreadable or no recognizer (no recognizer: everything is listed, nothing is called clean).
      R4C (2026-11-05): the same file gets "regenerate" = panel/background pictures (both sides >= 96 px) that are one
      plain colour block inside (no pattern/texture/shading); round 1 redraws them in the game's style. Patterned ones
      are not listed.
Exit 0 pass, 1 refused, 2 bad input.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile
import zipfile

IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp')
MAX_BYTES = 800_000
MAX_RATIO = 2.5


def pixels(data):
    if data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) >= 24:
        return struct.unpack('>II', data[16:24])
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        if data[12:16] == b'VP8X':
            return 1 + int.from_bytes(data[24:27], 'little'), 1 + int.from_bytes(data[27:30], 'little')
        if data[12:16] == b'VP8L':
            b = data[21:25]
            return 1 + (((b[1] & 0x3F) << 8) | b[0]), 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
        if data[12:16] == b'VP8 ':
            return struct.unpack('<H', data[26:28])[0] & 0x3FFF, struct.unpack('<H', data[28:30])[0] & 0x3FFF
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


def load_pre(pre_english):
    if isinstance(pre_english, (str, Path)):
        doc = json.loads(Path(pre_english).read_text(encoding='utf-8-sig'))
        if isinstance(doc, dict) and doc.get('kind') == 'base-assets':
            # v7.8: the original recorded by art_records.py base (docs/art/base-assets.json, {path: sha})
            return {str(s).lower() for key in ('images', 'embedded') for s in (doc.get(key) or {}).values()}
        pre_english = doc.get('images', doc) if isinstance(doc, dict) else doc
    return {str(s).lower() for s in pre_english}


def check(images, pre_english, display=None):
    pre = load_pre(pre_english)
    display = display or {}
    items = images.items() if isinstance(images, dict) else images
    seen, new, problems = set(), [], []
    for name, data in items:
        if not str(name).lower().endswith(IMAGE_SUFFIXES):
            continue
        digest = hashlib.sha256(data).hexdigest()
        if digest in pre or digest in seen:
            continue
        seen.add(digest)
        dims = pixels(data)
        row = {'image': name, 'sha256': digest, 'bytes': len(data), 'pixels': list(dims) if dims else None}
        shown = display.get(name) or display.get(digest)
        if len(data) > MAX_BYTES:
            problems.append('%s: new English image is %d bytes (> %d): export at 2x display size and compress' % (name, len(data), MAX_BYTES))
        if dims and shown and shown[0] and shown[1]:
            ratio = max(dims[0] / shown[0], dims[1] / shown[1])
            row.update(display=list(shown), ratio=round(ratio, 2))
            if ratio > MAX_RATIO:
                problems.append('%s: %dx%d is %.1fx its display size %dx%d (> %.1fx): export at 2x display size'
                                % (name, dims[0], dims[1], ratio, shown[0], shown[1], MAX_RATIO))
        new.append(row)
    return {'tool': 'audit_new_english_images', 'schema': 1, 'pre_english_images': len(pre), 'new_images': new,
            'problems': problems, 'passed': not problems}


def _chinese_audit():
    """cocos-game-to-english/scripts/chinese_audit.py (English pack). None when this remake-core has no English skill next to it."""
    d = Path(__file__).resolve().parent.parent.parent / 'cocos-game-to-english' / 'scripts'
    if not (d / 'chinese_audit.py').is_file():
        return None
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    import chinese_audit
    return chinese_audit


def _row(item, ocr_text=None, reasons=None):
    r = {k: item.get(k) for k in ('kind', 'file', 'slice', 'atlas_file', 'atlas_format', 'pixels_sha256', 'file_sha256', 'size')
         if item.get(k) is not None}
    if ocr_text is not None:
        r['ocr_text'] = ocr_text[:20]
    if reasons:
        r['reasons'] = reasons
    return r


def scan_chinese(project, ocr='auto', spine_pages=None):
    """P16 (生成时预防, 2026-11-04): at the START of English work, cut every atlas slice and animation frame (Cocos .plist,
    Spine/libGDX .atlas, DragonBones *_tex.json, BMFont pages, via chinese_audit.current_state) and read each whole
    picture and slice with the local recognizer (Vision on macOS, Windows.Media.Ocr via ocr_windows.ps1, tesseract).
    Pictures/slices with Chinese go straight onto the first-round art replacement list; ones the recognizer could not
    settle go to manual_review. No recognizer (or no Pillow, or no English skill next to remake-core): nothing is
    called clean, every picture and slice goes to manual_review, and the reason is written down."""
    C = _chinese_audit()
    base = {'schema': 'art_replace_round1.v1', 'tool': 'audit_new_english_images --make-list', 'replace': [],
            'manual_review': [], 'clean': 0, 'pictures': 0, 'slices': 0}
    if C is None:
        return dict(base, status='unavailable', recognizer=None,
                    note='chinese_audit.py not found next to remake-core: open every picture and atlas slice yourself')
    try:
        rec, notes = C.pick_recognizer(ocr)
        use = not isinstance(rec, C.NoRecognizer)
        tasks, tmp = {}, tempfile.mkdtemp(prefix='english-make-list-')

        def on_pixels(item, img):
            if not use:
                return
            both = item.get('rotate', 0) in (90, 270)
            key = C.receipt_key(item['pixels_sha256'], both, rec.name, rec.version)
            item['ocr_key'] = key
            if key in tasks:
                return
            prep, info = C.prepare_ocr_input(img, both)
            p = Path(tmp) / (key + '.png')
            prep.save(str(p), format='PNG')
            tasks[key] = {'key': key, 'path': str(p), 'pixels_sha256': item['pixels_sha256'], 'size': list(img.size),
                          'both': both, 'prepared': info}
        try:
            state = C.current_state(project, None, None, on_pixels, spine_pages=spine_pages)
            results = rec.run(list(tasks.values())) if tasks else {}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    except Exception as exc:  # no Pillow, unreadable project ...: fall back to "look at everything"
        return dict(base, status='unavailable', recognizer=None, note='scan could not run (%s): open every picture and '
                    'atlas slice yourself' % exc)
    out = dict(base, status='ok' if use else 'no_recognizer',
               recognizer={'name': rec.name, 'version': rec.version, 'note': rec.note, 'notes': notes})
    if not use:
        out['note'] = rec.note or 'no recognizer that reads Chinese: every picture and slice is listed for manual review'
    out['spine_binding_problems'] = [_row(item, reasons=[item['error']]) for item in state['items']
                                     if item.get('binding_error')]
    out['items'] = []   # (item, verdict 'chinese' | 'clean' | 'manual', ocr text, reasons); dropped before writing
    for item in state['items']:
        k = item['kind']
        if k not in ('image', 'slice', 'atlas_error'):
            continue
        if k == 'atlas_error' or item.get('error'):
            out['items'].append((item, 'manual', None, [item.get('error') or 'unreadable']))
            continue
        out['pictures' if k == 'image' else 'slices'] += 1
        if not use:
            out['items'].append((item, 'manual', None, ['not read by a recognizer']))
            continue
        r = results.get(item.get('ocr_key')) or {'ok': False, 'error': 'recognizer returned nothing', 'items': []}
        receipt = {'status': 'ok' if r.get('ok') else 'failed', 'error': r.get('error'), 'results': r.get('items') or []}
        st, reasons, hits = C.classify(receipt)
        text = [x.get('text') for x in receipt['results']]
        out['items'].append((item, 'chinese' if hits else 'manual' if st == 'needs_review' else 'clean', text, reasons))
    for item, verdict, text, reasons in out['items']:
        if verdict == 'chinese':
            out['replace'].append(_row(item, text, reasons))
        elif verdict == 'manual':
            out['manual_review'].append(_row(item, text, reasons))
        else:
            out['clean'] += 1
    return out


FLAT_MIN_SIDE = 96      # panels / backgrounds; icons and small buttons are not judged here
FLAT_COVER = 0.60       # visible pixels inside the visible box (a filled block, rounded corners allowed)
FLAT_SHARE = 0.90       # share of the inner area within FLAT_TOL of its median colour
FLAT_TOL = 16
FLAT_DARK = 60          # mean luma below this: also "too dark"


def flat_panel_reason(img):
    """R4C (census too_dark 11/12, plain_background 9/11): a panel/background picture that is one plain colour block.
    The outer 10 % ring of the visible box (outline, rounded corners) is ignored; inside, >= 90 % of the pixels within
    16 of the median colour = no pattern, no texture, no shading. Pictures with a pattern, gradient or scenery are not
    listed. Returns the reason text or None."""
    im = img.convert('RGBA')
    w, h = im.size
    if min(w, h) < FLAT_MIN_SIDE:
        return None
    box = im.getchannel('A').point(lambda v: 255 if v > 128 else 0).getbbox()
    if not box or min(box[2] - box[0], box[3] - box[1]) < FLAT_MIN_SIDE:
        return None
    im = im.crop(box).resize((64, 64))
    px = list(im.getdata())
    if sum(1 for p in px if p[3] > 128) < FLAT_COVER * len(px):
        return None
    inner = [p[:3] for i, p in enumerate(px) if 6 <= i % 64 < 58 and 6 <= i // 64 < 58 and p[3] > 128]
    if not inner:
        return None
    med = [sorted(c[k] for c in inner)[len(inner) // 2] for k in range(3)]
    share = sum(1 for c in inner if max(abs(c[k] - med[k]) for k in range(3)) <= FLAT_TOL) / float(len(inner))
    if share < FLAT_SHARE:
        return None
    luma = 0.299 * med[0] + 0.587 * med[1] + 0.114 * med[2]
    why = 'flat_panel: one plain colour #%02x%02x%02x covers %d%% of the inside' % (med[0], med[1], med[2], share * 100)
    if luma < FLAT_DARK:
        why += ' and it is dark (luma %d)' % luma
    return why + ('; regenerate it in round 1 in the game\'s art style with shading, a border and a pattern/texture '
                  '(not a single colour, not darker than the home page)')


def flat_panels(project):
    """Whole pictures of the Chinese original that are plain colour panels -> first-round regenerate list."""
    try:
        from PIL import Image
    except ImportError:
        return None
    rows = []
    for p in sorted(Path(project).rglob('*')):
        if not (p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES) or {'library', 'temp', 'build'} & set(p.parts):
            continue
        try:
            with Image.open(p) as im:
                why = flat_panel_reason(im)
                size = list(im.size)
        except (OSError, ValueError):
            continue
        if why:
            rows.append({'kind': 'image', 'file': p.relative_to(project).as_posix(), 'size': size, 'reasons': [why]})
    return rows


TITLE_FILE = re.compile(r'(?i)(title|logo|banner|wordmark|biaoti|game[_\- ]?name|标题|游戏名|名字|名称|横幅)')
HOME_SCENE = re.compile(r'(?i)(home|main|start|menu|lobby|hall|index|loading|launch|splash|boot|load|首页|主页|大厅|加载|启动)')
# page titles and buttons stay word pictures (LEVEL FAILED, SHOP, PLAY): calibrated on 7 local English games 2026-11-05
NOT_TITLE = re.compile(r'(?i)(win|lose|fail|result|level|shop|store|setting|pause|sign|rank|skin|task|reward|gift|tip|'
                       r'over|victory|defeat|complete|popup|dialog|btn|button|eff|fx|anim|frame|\d{3,})')
TITLE_MIN_W = 300
TITLE_PROMPT = ('the hero / characters / props / a pattern or the scene of this game in its own art style; no game name, '
                'no words, no letters (Saul 2026-11-05: 游戏里不出现游戏名)')


def _uuids(img):
    """The image's own uuid and its sprite-frame sub-uuids from <img>.meta (2.x subMetas, 3.x '<uuid>@xxxx')."""
    meta = _read_meta(Path(str(img) + '.meta'))
    out = {meta.get('uuid')} if meta.get('uuid') else set()
    for sub in (meta.get('subMetas') or {}).values():
        if isinstance(sub, dict) and sub.get('uuid'):
            out.add(sub['uuid'])
    return {u for u in out if isinstance(u, str) and len(u) >= 8}


def _read_meta(p):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def title_logos(project, scan):
    """R4Q2 (补查3 第 2 组; Saul 2026-11-05: no game name in the game): the big worded picture at the top of the home /
    loading page (the original title logo) goes onto "regenerate" with a hero / pattern / scene prompt, not onto a
    translate-the-words list. Picked from the pictures the scan found words in (replace + manual_review): its file name
    says title / logo / banner, or it is the widest worded picture (>= 300 px wide, wider than tall) that a home /
    loading scene or prefab uses. Its replace row is marked regenerate_instead so nobody draws an English logo."""
    project = Path(project)
    rows = [r for key in ('replace', 'manual_review') for r in scan.get(key) or []
            if r.get('kind') == 'image' and r.get('file')]
    scenes = [p for p in project.rglob('*') if p.suffix.lower() in ('.fire', '.scene', '.prefab') and p.is_file()
              and HOME_SCENE.search(p.stem) and not {'library', 'temp', 'build', 'docs', 'qa'} & set(p.parts)]
    texts = []
    for p in scenes:
        try:
            texts.append((p, p.read_text(encoding='utf-8', errors='replace')))
        except OSError:
            pass
    picked, widest = {}, {}
    for r in rows:
        img = project / r['file']
        if not img.is_file():
            continue
        try:
            dims = pixels(img.read_bytes()[:65536]) or (0, 0)
        except OSError:
            continue
        if NOT_TITLE.search(img.stem):
            continue
        if TITLE_FILE.search(img.name):
            picked[r['file']] = 'file name %s says title/logo' % img.name
            continue
        if dims[0] < TITLE_MIN_W or dims[0] <= dims[1]:
            continue
        ids = _uuids(img)
        for sp, text in texts:
            if any(u in text for u in ids):
                key = sp.relative_to(project).as_posix()
                if dims[0] > widest.get(key, (0, ''))[0]:
                    widest[key] = (dims[0], r['file'])
    for key, (w, f) in widest.items():
        picked.setdefault(f, 'widest worded picture (%d px) on %s' % (w, key))
    out = []
    for r in rows:
        if r['file'] in picked:
            r['regenerate_instead'] = 'title_logo'
            if r['file'] not in {o['file'] for o in out}:
                out.append({'kind': 'image', 'file': r['file'], 'size': r.get('size'), 'prompt': TITLE_PROMPT,
                            'reasons': ['title_logo: %s; redraw it as the hero / a pattern / the scene with no game '
                                        'name and no words, do not translate it' % picked[r['file']]]})
    return out


# R4R2 (补查3 第 1 组补充, 弹球传奇 11-05: 48 of 54 runtime words missing): whole-word pictures fetched by code at run
# time (ball names, EQUIP / EQUIPPED) are in no prefab or scene, so the list above never showed them.
WORD_CALL = re.compile(r'''\b(?:caption|wordImage|word_image|loadWord|loadCaption|EnglishArt\.(?:frame|word|caption))\s*\(\s*'''
                       r'''(['"])([^'"\n]{1,40})\1''')
WORD_PATH = re.compile(r'''(['"])(?:[\w\-/]*/)?(txt_[a-z0-9_]+)\1''')
WORD_LABEL_CALL = re.compile(r'''\b(?:caption|EnglishArt\.(?:caption|label))\s*\(\s*(?:this\.)?([A-Za-z_$][\w$]*)\s*[,)]''')
NAME_KEYS = ('name', 'title', 'displayName', 'display_name', 'label', 'nameEn', 'name_en')
CJK_RE = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]')


def _word_slug(text):
    return re.sub(r'^_|_$', '', re.sub(r'[^a-z0-9]+', '_', str(text).lower()))


def runtime_word_images(project):
    """Whole-word pictures that scripts ask for at run time, checked against the pictures in the project:
      caption('equipped') / EnglishArt.frame('txt_shop')   -> txt_equipped / txt_shop (a literal key or word)
      'EnglishUI/txt_classic'                               -> txt_classic
      caption(this.stateLabel) + this.stateLabel.string = "EQUIPPED"   -> txt_equipped
      caption(this.ballName) + ballName.string = list['name']           -> every short `name` of the JSON config tables
    Missing ones are the "unwired" rows: draw txt_<slug>.png before the first round. A Chinese config name has no key
    yet: translate it, then draw txt_<slug of the English>."""
    root = Path(project)
    have = {p.stem.lower() for p in root.rglob('*') if p.suffix.lower() in IMAGE_SUFFIXES
            and not {'library', 'temp', 'build'} & set(p.parts)}
    want, config_members = {}, False
    scripts = [p for p in sorted((root / 'assets').rglob('*')) if p.suffix in ('.js', '.ts') and p.is_file()
               and not p.name.endswith('.d.ts') and not {'library', 'temp', 'build', 'node_modules'} & set(p.parts)]
    for p in scripts:
        try:
            src = p.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        rel = p.relative_to(root).as_posix()
        for m in WORD_CALL.finditer(src):
            arg = m.group(2)
            # EnglishArt.frame('btn_close') names the picture itself; caption('equipped') names a word -> txt_<slug>
            key = arg.rsplit('/', 1)[-1] if 'frame' in m.group(0).split('(')[0] or arg.startswith('txt_') else 'txt_' + _word_slug(arg)
            want.setdefault(key, {'from': rel, 'how': m.group(0)})
        for m in WORD_PATH.finditer(src):
            want.setdefault(m.group(2), {'from': rel, 'how': m.group(0)})
        for m in WORD_LABEL_CALL.finditer(src):
            member = re.escape(m.group(1))
            for s in re.finditer(r'''\b%s\.string\s*=\s*(['"])([^'"\n]{1,40})\1''' % member, src):
                if not CJK_RE.search(s.group(2)) and _word_slug(s.group(2)):
                    want.setdefault('txt_' + _word_slug(s.group(2)), {'from': rel, 'how': '%s.string = %r' % (m.group(1), s.group(2))})
            if re.search(r'''\b%s\.string\s*=\s*[\w$.]+(?:\[\s*['"](?:%s)['"]\s*\]|\.(?:%s)\b)''' % (member, '|'.join(NAME_KEYS), '|'.join(NAME_KEYS)), src):
                config_members = True
    untranslated = []
    if config_members:
        for p in sorted((root / 'assets').rglob('*.json')):
            if {'library', 'temp', 'build'} & set(p.parts):
                continue
            try:
                data = json.loads(p.read_text(encoding='utf-8-sig'))
            except (OSError, ValueError):
                continue
            if isinstance(data, list) and data and isinstance(data[0], dict) and '__type__' in data[0]:
                continue                                   # a serialized Cocos asset, not a config table
            stack = [data]
            while stack:
                v = stack.pop()
                if isinstance(v, list):
                    stack += v
                elif isinstance(v, dict):
                    for k, x in v.items():
                        if k in NAME_KEYS and isinstance(x, str) and 0 < len(x) <= 24:
                            if CJK_RE.search(x):
                                untranslated.append({'from': p.relative_to(root).as_posix(), 'text': x})
                            elif _word_slug(x):
                                want.setdefault('txt_' + _word_slug(x), {'from': p.relative_to(root).as_posix(), 'how': '%s: %r' % (k, x)})
                        elif isinstance(x, (dict, list)):
                            stack.append(x)
    missing = [dict(key=k, file=k + '.png', **v) for k, v in sorted(want.items()) if k.lower() not in have]
    return {'wanted': len(want), 'wired': len(want) - len(missing), 'missing': missing,
            'untranslated_names': untranslated[:200],
            'note': 'whole-word pictures the code fetches at run time; draw every missing txt_<slug>.png in the round-1 '
                    'art batch (same style as the other word pictures), translate untranslated_names first'}


def make_list(project, ocr='auto', scan=True, flat_mode='list'):
    out = {}
    for p in sorted(Path(project).rglob('*')):
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and not {'library', 'temp', 'build'} & set(p.parts):
            out[hashlib.sha256(p.read_bytes()).hexdigest()] = p.relative_to(project).as_posix()
    doc = {'source': str(Path(project).resolve()), 'images': out}
    if scan:
        scan = scan_chinese(project, ocr)
        scan.pop('items', None)
        flats = flat_panels(project)
        # R4Q3 (补查3 第 3 组, Saul chose 「保留原画风」 for 火箭三消 and 弹球传奇): an English game's first round keeps the
        # original art, so plain one-colour panels / backgrounds of the original are LISTED for Saul to pick
        # ("style_choices"), not put on "regenerate" (R4C did). flat_mode='regenerate' (--flat-panels regenerate) only
        # when Saul named the art skill for them.
        if flat_mode == 'regenerate':
            scan['regenerate'] = flats or []
        else:
            scan['regenerate'] = []
            scan['style_choices'] = flats or []
            scan['style_choices_note'] = ('plain-colour panels/backgrounds of the original: kept as they are (英化第一轮照原画风); '
                                          'redraw only the ones Saul picks, then rerun with --flat-panels regenerate')
        if flats is None:
            scan['regenerate_note'] = 'Pillow missing: plain-colour panels were not measured, look at every panel yourself'
        doc['chinese_scan'] = scan
        scan['regenerate'] += title_logos(project, scan)  # R4Q2: the original title logo is redrawn without a name
        scan['runtime_words'] = runtime_word_images(project)  # R4R2: words code fetches at run time, missing = unwired
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--zip', type=Path)
    ap.add_argument('--pre-english', type=Path)
    ap.add_argument('--make-list', type=Path, help='Chinese original project: write its image SHA list to --out')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--ocr', default='auto', choices=['auto', 'vision', 'tesseract', 'windows', 'none', 'fake'],
                    help='--make-list: recognizer for the Chinese scan of every picture and atlas slice (default auto)')
    ap.add_argument('--flat-panels', choices=('list', 'regenerate'), default='list', help='--make-list (R4Q3): plain-colour '
                    'panels of the original: list them for Saul to pick (default) or put them on regenerate')
    ap.add_argument('--replace-out', type=Path, help='--make-list: first-round art replacement list '
                    '(default: art-replace-round1.json next to --out)')
    a = ap.parse_args(argv)
    try:
        if a.make_list:
            if not a.out:
                ap.error('--make-list needs --out')
            doc = make_list(a.make_list, a.ocr, flat_mode=a.flat_panels)
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            scan = doc['chinese_scan']
            rp = a.replace_out or a.out.parent / 'art-replace-round1.json'
            rp.write_text(json.dumps(scan, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            unresolved = scan.get('spine_binding_problems') or []
            print(json.dumps({'images': len(doc['images']), 'scan': scan['status'], 'replace': len(scan['replace']),
                              'spine_binding_problems': unresolved[:10],
                              'manual_review': len(scan['manual_review']), 'regenerate': len(scan.get('regenerate') or []), 'style_choices': len(scan.get('style_choices') or []),
                              'replace_list': str(rp)}, ensure_ascii=False))
            return int(bool(unresolved))
        if not (a.zip and a.pre_english):
            ap.error('--zip and --pre-english are required')
        with zipfile.ZipFile(a.zip) as zf:
            r = check(((n, zf.read(n)) for n in zf.namelist() if n.lower().endswith(IMAGE_SUFFIXES)), a.pre_english)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({'passed': False, 'error': str(exc)})); return 2
    if a.out:
        a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': r['passed'], 'new_images': len(r['new_images']), 'problems': r['problems'][:10]}, ensure_ascii=False))
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
