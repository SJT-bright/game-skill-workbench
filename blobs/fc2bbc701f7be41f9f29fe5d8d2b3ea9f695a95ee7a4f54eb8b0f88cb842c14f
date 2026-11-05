#!/usr/bin/env python3
"""Digit glyph-core size audit (S2, v7.8 H11 follow-up).

The v7.8 hud_digit_small rule measures the FONT SIZE on screen. A generated digit picture can carry wide transparent
margins (Milo's Bubble Cove 10-24: 64x96 atlas cells whose digits are only ~50 px high, drawn at size 12 -> a ~7 CSS px
"2/5"), so the font size looks fine while the visible digit is tiny. This module measures the visible INK.

Static   digit_glyph_padding  - per bitmap font (.fnt + page PNG, .labelatlas, digit_0..9 pictures, digits strip):
                                ink height of the digits / em (BMFont info size, LabelAtlas fontSize, picture height).
Runtime  small_glyph_core     - on-screen ink height of every core value = screen font size x the font's ink ratio;
                                without a known font it is measured on the screenshot (|dL*| >= 15 vs the ring outside).
         small_value_font     - core value outside the v7.8 gameplay-HUD scope whose font size / picture box is small.
                                Remake games only (Saul 2026-10-31 "small_value_font 先只拦重塑"): in an English game
                                (english_game) the same finding is small_value_font_hint, advisory, never a failure.
         glyph_core_review    - advisory: only the screenshot could be measured (no font metrics).
Overflow past the value plate is NOT checked (REPORT.md, open questions).

Interface: font_ink_ratios(project) -> {font_stem_lower: info}, glyph_core_problems(d, nodes, ratios, image_module)
-> ['code: text', ...] in the audit_page_richness format.
"""
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_page_richness as apr        # noqa: E402  (shared helpers: text, area, inter, NUMERIC, HUD rules)

INK_ALPHA = 48               # alpha > 48/255 is ink (anti-aliased fringe below it is not seen at phone size)
MIN_INK_RATIO = 0.65         # .fnt / .labelatlas digit ink / em below this = wide margins (429-font calibration, REPORT.md)
SYSTEM_INK_RATIO = 0.72      # digit height of system / TTF fonts (Arial, Helvetica, PingFang digits ~0.70-0.73 em)
MIN_CORE_CSS = 18.0          # core value ink >= 18 CSS px = v7.8 3% font size x SYSTEM_INK_RATIO on an 844 screen
MIN_CORE_SHARE = 0.0216      # same rule without canvas_css: 3% x 0.72 of the screen height
MIN_MINOR_CSS = 12.0         # secondary values (card level, price, count badge): ink >= 12 CSS px (TankAce 10-26)
MIN_MINOR_SHARE = 0.014
MIN_SHOT_FILL = 0.35         # screenshot ink under 35% of the box = value covered / not drawn: not judged
SHOT_DL = 15.0               # screenshot fallback: ink pixel = |L* - ring L*| >= 15
FLAG_SMALL_FONT = True       # small_value_font: core values whose FONT SIZE / picture box is small, outside the v7.8
                             # gameplay-HUD scope (hud_digit_small covers that); measured from metrics, never screenshots;
                             # blocks remake games only, English games get small_value_font_hint (Saul 2026-10-31)
# Matched on words of the node path (camelCase split, lower case): 'ScrollView' is not 'lv', 'coinNumber' is 'coin'.
CORE_NAME = re.compile(r'(?<![a-z])(?:hud|topbar|top_bar|resource|wallet|coin|gold|gem|diamond|money|cash|pearl|heart|'
                       r'energy|stamina|power|life|lives|score|level|lv|stage|star|reward|prize|amount|best|combo)s?(?![a-z])')
MINOR_NAME = re.compile(r'(?<![a-z])(?:price|cost|count|num|badge|card|skin|item|unlock|lock)s?(?![a-z])')
DIGIT_FRAME = re.compile(r'^(?:.*?[_\-])?(?:digit|digits|num|number|shuzi)[_\-]?(\d|slash|plus|x|/|\+)$', re.I)
DIGIT_SHEET = re.compile(r'(?:^|[_\-])(?:digit|digits|num|nums|number|numbers|shuzi)s?$', re.I)
END_PURPOSES = {'result', 'result_win', 'result_fail', 'revive', 'win', 'lose', 'gameover', 'game_over'}
SKIP_DIRS = {'node_modules', 'library', 'temp', 'build', 'local', 'profiles', '.git'}


# ---------------------------------------------------------------- static: font ink ratios

def _alpha(image_module, path):
    im = image_module.open(path)
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
        return im.convert('RGBA').split()[-1]
    return None                                # no alpha channel: ink cannot be told from the glyph cell


def ink_rows(alpha, box):
    """(top, bottom) ink rows of alpha inside box (x, y, w, h), or None when the box holds no ink."""
    x, y, w, h = box
    if w <= 0 or h <= 0:
        return None
    crop = alpha.crop((x, y, x + w, y + h))
    bb = crop.point(lambda v: 255 if v > INK_ALPHA else 0).getbbox()
    return (bb[1], bb[3]) if bb else None


def parse_fnt(path):
    """Text BMFont: {'size', 'line_height', 'base', 'pages': {id: file}, 'chars': {id: dict}}; None when not text."""
    try:
        lines = Path(path).read_text(encoding='utf-8', errors='ignore').splitlines()
    except OSError:
        return None
    out = {'size': 0, 'line_height': 0, 'base': 0, 'pages': {}, 'chars': {}}
    for line in lines:
        tag = line.split(' ', 1)[0]
        kv = dict(re.findall(r'(\w+)=("[^"]*"|-?\d+)', line))
        num = lambda k, default=0: int(kv[k]) if k in kv and kv[k].lstrip('-').isdigit() else default
        if tag == 'info':
            out['size'] = abs(num('size'))
        elif tag == 'common':
            out['line_height'], out['base'] = num('lineHeight'), num('base')
        elif tag == 'page':
            out['pages'][num('id')] = kv.get('file', '').strip('"')
        elif tag == 'char':
            out['chars'][num('id', -1)] = {k: num(k) for k in ('x', 'y', 'width', 'height', 'yoffset', 'page')}
    return out if out['chars'] else None


def fnt_ink(path, image_module):
    """Ink of the digits 0-9 of one .fnt: ratio = median digit ink height / em (info size, else lineHeight)."""
    f = parse_fnt(path)
    if not f:
        return None
    em = f['size'] or f['line_height']
    alphas, inks, cells = {}, [], []
    for cid in range(48, 58):
        c = f['chars'].get(cid)
        if not c or c['width'] <= 0 or c['height'] <= 0:
            continue
        page = f['pages'].get(c['page'])
        if page is None:
            continue
        if page not in alphas:
            p = Path(path).parent / page
            try:
                alphas[page] = _alpha(image_module, p) if p.is_file() else None
            except Exception:
                alphas[page] = None
        a = alphas[page]
        if a is None:
            continue
        rows = ink_rows(a, (c['x'], c['y'], c['width'], c['height']))
        if rows:
            inks.append(rows[1] - rows[0])
            cells.append(c['height'])
    if len(inks) < 3 or not em:
        return None
    ink = statistics.median(inks)
    return {'kind': 'fnt', 'file': str(path), 'em': em, 'line_height': f['line_height'], 'digits': len(inks),
            'ink': ink, 'ratio': round(ink / em, 3), 'trim': round(ink / statistics.median(cells), 3)}


def labelatlas_ink(path, image_module, uuid_png):
    """Cocos 2.4 .labelatlas: meta itemWidth/itemHeight/startChar/fontSize + rawTextureUuid."""
    try:
        meta = json.loads(Path(str(path) + '.meta').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    png = uuid_png.get(meta.get('rawTextureUuid'))
    iw, ih, em = int(meta.get('itemWidth') or 0), int(meta.get('itemHeight') or 0), float(meta.get('fontSize') or 0)
    start = str(meta.get('startChar') or '0')[:1]
    if not png or iw <= 0 or ih <= 0:
        return None
    try:
        a = _alpha(image_module, png)
    except Exception:
        return None
    if a is None:
        return None
    per_row = max(1, a.size[0] // iw)
    inks = []
    for d in range(10):
        i = ord(str(d)) - ord(start)
        if i < 0:
            continue
        rows = ink_rows(a, (i % per_row * iw, i // per_row * ih, iw, ih))
        if rows:
            inks.append(rows[1] - rows[0])
    if len(inks) < 3:
        return None
    em = em or ih * 0.88
    ink = statistics.median(inks)
    return {'kind': 'labelatlas', 'file': str(path), 'em': em, 'line_height': ih, 'digits': len(inks), 'ink': ink,
            'ratio': round(ink / em, 3), 'trim': round(ink / ih, 3)}


def picture_ink(paths, image_module, kind):
    """digit_0..9 single pictures (kind 'digit_png') or one 10-cell strip (kind 'digit_strip'): ink / picture height."""
    inks, h = [], 0
    for p in paths:
        try:
            a = _alpha(image_module, p)
        except Exception:
            continue
        if a is None:
            continue
        if kind == 'digit_strip':
            cw = a.size[0] / 10.0
            for i in range(10):
                rows = ink_rows(a, (int(i * cw), 0, int(cw), a.size[1]))
                if rows:
                    inks.append(rows[1] - rows[0])
        else:
            rows = ink_rows(a, (0, 0) + a.size)
            if rows:
                inks.append(rows[1] - rows[0])
        h = a.size[1]
    if len(inks) < 3 or not h:
        return None
    ink = statistics.median(inks)
    return {'kind': kind, 'file': str(paths[0]), 'em': h, 'line_height': h, 'cell_h': h, 'digits': len(inks), 'ink': ink,
            'ratio': round(ink / h, 3), 'trim': round(ink / h, 3)}


def _files(project, suffix):
    base = Path(project) / 'assets'
    if not base.is_dir():
        return []
    return [f for f in base.rglob('*' + suffix) if f.is_file() and not (SKIP_DIRS & set(f.relative_to(base).parts))]


def font_ink_ratios(project, image_module=None):
    """{font name (stem, lower case): info} for every digit font of the project; info['ratio'] = digit ink / em."""
    if image_module is None:
        from PIL import Image as image_module
    out = {}
    for f in _files(project, '.fnt'):
        info = fnt_ink(f, image_module)
        if info:
            out.setdefault(f.stem.lower(), info)
    atlases = _files(project, '.labelatlas')
    if atlases:
        uuid_png = {}
        for m in _files(project, '.png.meta'):
            try:
                uuid_png[json.loads(m.read_text(encoding='utf-8')).get('uuid')] = m.with_suffix('')
            except (OSError, ValueError):
                pass
        for f in atlases:
            info = labelatlas_ink(f, image_module, uuid_png)
            if info:
                out.setdefault(f.stem.lower(), info)
    groups = {}
    for f in _files(project, '.png'):
        m = DIGIT_FRAME.match(f.stem)
        if m and m.group(1).isdigit():
            groups.setdefault((f.parent, f.stem[:m.start(1)].lower()), []).append(f)
        elif DIGIT_SHEET.search(f.stem):
            try:
                with image_module.open(f) as im:
                    w, h = im.size
            except Exception:
                continue
            if 4.0 <= w / float(h or 1) <= 13.0:          # 10 digit cells side by side (cell w:h 0.4-1.3)
                info = picture_ink([f], image_module, 'digit_strip')
                if info:
                    info['cell_h'] = h
                    out.setdefault(f.stem.lower(), info)
                    for i in range(10):                    # frames cut from the strip: digit3 / digit_3
                        for key in ('digit%d' % i, 'digit_%d' % i):
                            out.setdefault(key, info)
    for (_, prefix), files in groups.items():
        info = picture_ink(sorted(files), image_module, 'digit_png')
        if info:
            for f in files:                               # a sprite frame is looked up by its own name
                out.setdefault(f.stem.lower(), info)
            out.setdefault(prefix.rstrip('_-') or 'digit', info)
    return out


def digit_glyph_padding_problems(ratios, project=None):
    """Static rule: one problem per font file whose digit ink is under MIN_INK_RATIO of its em."""
    seen, out = set(), []
    for name, info in sorted(ratios.items()):
        if info['file'] in seen or info['kind'] not in ('fnt', 'labelatlas'):
            continue                 # picture digits may be trimmed by the engine or by code: judged at runtime only
        seen.add(info['file'])
        if info['ratio'] < MIN_INK_RATIO:
            rel = info['file']
            if project:
                try:
                    rel = Path(info['file']).relative_to(project).as_posix()
                except ValueError:
                    pass
            out.append('digit_glyph_padding: %s (%s) - the digits fill only %.0f%% of the font size (ink %.0f of %.0f px, '
                       'min %.0f%%): the generated digit pictures carry wide transparent margins, so a big font size still '
                       'shows small digits; crop each digit tight to its ink and rebuild the font so the digit height is about '
                       'the font size (Milo\'s Bubble Cove 10-24 "2比5文字怎么这么小")'
                       % (rel, info['kind'], 100 * info['ratio'], info['ink'], info['em'], 100 * MIN_INK_RATIO))
    return out


# ---------------------------------------------------------------- runtime: ink on screen

def lstar(rgb):
    return apr.lstar(rgb)


def shot_ink(img, r):
    """Ink height (screen share) of the text inside screen rect r measured on the screenshot, or None.
    Ink = pixels whose L* differs from the median L* of a ring just outside the box by SHOT_DL or more."""
    W, H = img.size
    x0, y0, x1, y1 = int(r[0] * W), int(r[1] * H), int((r[0] + r[2]) * W + 0.999), int((r[1] + r[3]) * H + 0.999)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    box = img.crop((x0, y0, x1, y1))
    w, h = x1 - x0, y1 - y0
    ls = [lstar(p) for p in box.getdata()]
    # Background = the most common L* inside the box: digit strokes cover a minority of their own box, while the
    # ring outside a loose box may land on a plate border of another colour.
    hist = {}
    for v in ls:
        hist[int(v // 4)] = hist.get(int(v // 4), 0) + 1
    peak = max(hist, key=hist.get)
    bg = statistics.median([v for v in ls if int(v // 4) == peak])
    px = [abs(v - bg) >= SHOT_DL for v in ls]
    comps = _components(px, w, h)
    # Drop plate rims / icon edges caught by a loose box: parts touching the box edge that run along most of it.
    def rim(c):
        cw, chh = c[2] - c[0] + 1, c[3] - c[1] + 1
        vertical = (c[0] == 0 or c[2] == w - 1) and chh >= 0.9 * h and cw <= max(2, 0.15 * w)
        horizontal = (c[1] == 0 or c[3] == h - 1) and cw >= 0.9 * w and chh <= max(2, 0.2 * h)
        return vertical or horizontal
    glyphs = [c for c in comps if not rim(c)]
    if not glyphs:
        return None
    big = max(c[4] for c in glyphs)
    glyphs = [c for c in glyphs if c[4] >= max(3, 0.15 * big)]          # specks and anti-aliasing dust
    if not glyphs:
        return None
    top, bottom = min(c[1] for c in glyphs), max(c[3] for c in glyphs)
    return (bottom - top + 1) / float(H)


def _components(mask, w, h):
    """8-connected parts of a flat bool mask: [(x0, y0, x1, y1, pixel count), ...]."""
    seen = bytearray(w * h)
    out = []
    for i in range(w * h):
        if not mask[i] or seen[i]:
            continue
        seen[i] = 1
        stack, x0, y0, x1, y1, n = [i], w, h, -1, -1, 0
        while stack:
            j = stack.pop()
            x, y = j % w, j // w
            n += 1
            x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < w and 0 <= yy < h:
                        k = yy * w + xx
                        if mask[k] and not seen[k]:
                            seen[k] = 1
                            stack.append(k)
        out.append((x0, y0, x1, y1, n))
    return out


def _font_info(lab, ratios):
    name = str(lab.get('font') or '').lower()
    for key in (name, Path(name).stem, name.rsplit('/', 1)[-1]):
        if key and key in ratios:
            return ratios[key]
    return None


def _value_text(s):
    s = re.sub(r'<[^>]*>', ' ', s or '').strip()
    return bool(s) and (bool(apr.NUMERIC.match(s)) or apr.value_label(s))


def path_words(path):
    return re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', path).lower()


def _hud(t, path_counts):
    r = t.get('screen') or t['rect']
    cy = r[1] + r[3] / 2
    if apr.HUD_NAME.search(t['path']):
        return True
    return not (apr.HUD_BAND[0] <= cy <= apr.HUD_BAND[1]) and not apr.on_repeated_piece(t, path_counts)


def digit_groups(nodes):
    """Picture digits drawn one sprite per digit (frame digit_5 / num_3 / art_digit_0): one pseudo node per parent."""
    groups = {}
    for n in nodes:
        sp = n.get('comps', {}).get('sprite')
        if not sp:
            continue
        m = DIGIT_FRAME.match(str(sp.get('frame', '')))
        if m:
            groups.setdefault(n['path'].rsplit('/', 1)[0], []).append((n, m.group(1)))
    out = []
    for parent, members in groups.items():
        rs = [(n.get('screen') or n['rect']) for n, _ in members]
        x0, y0 = min(r[0] for r in rs), min(r[1] for r in rs)
        x1, y1 = max(r[0] + r[2] for r in rs), max(r[1] + r[3] for r in rs)
        first = min((n for n, _ in members), key=lambda n: n.get('order', 0))
        s = ''.join(ch if ch.isdigit() else '/' if ch in ('slash', '/') else '+' if ch in ('plus', '+') else 'x'
                    for _, ch in sorted(members, key=lambda m: (m[0].get('screen') or m[0]['rect'])[0]))
        out.append({'path': parent, 'name': parent.rsplit('/', 1)[-1], 'order': first.get('order', 0),
                    'depth': first.get('depth', 0), 'id': None, '_frames': [str(n['comps']['sprite']['frame']) for n, _ in members],
                    'rect': [x0, y0, x1 - x0, y1 - y0], 'screen': [x0, y0, x1 - x0, y1 - y0],
                    'comps': {'image_text': {'string': s}}, '_members': [n for n, _ in members]})
    return out


def ink_share(t, ratios, img):
    """(on-screen ink height as a screen share, how) of a value node, or (None, why)."""
    r = t.get('screen') or t['rect']
    lab = t['comps'].get('label') or t['comps'].get('richtext')
    if lab and lab.get('height'):
        size = _font_size(lab)
        screen_font = min(size * r[3] / float(lab['height']), r[3]) if size else 0
        kind = lab.get('font_kind') or ('bitmap' if apr.bitmap_font(lab) else 'system')
        info = _font_info(lab, ratios) if kind == 'bitmap' else None
        if screen_font and info:
            return screen_font * info['ratio'], 'font %s ink %.0f%%' % (lab.get('font'), 100 * info['ratio'])
        if screen_font and kind in ('system', 'ttf'):
            return screen_font * SYSTEM_INK_RATIO, '%s font' % kind
    if '_frames' in t:
        infos = []
        for n in t['_members']:
            info = ratios.get(str(n['comps']['sprite'].get('frame', '')).lower())
            if not info:
                continue
            fs = n['comps']['sprite'].get('frame_size')
            if fs and info.get('cell_h') and abs(fs[1] - info['cell_h']) > 1:
                info = dict(info, ratio=1.0)             # the engine trimmed the frame: the box is the ink
            infos.append(info['ratio'])
        if infos:
            return r[3] * statistics.median(infos), 'digit pictures ink %.0f%%' % (100 * statistics.median(infos))
    if img is not None:
        h = shot_ink(img, r)
        if h and h >= MIN_SHOT_FILL * r[3]:
            return min(h, r[3]), 'screenshot'
        if h:
            return None, 'screenshot ink only %.0f%% of the box: value hidden or not drawn, not judged' % (100 * h / r[3])
    return None, 'font unknown and no screenshot'


def _font_css(t, ch):
    lab = t['comps'].get('label') or t['comps'].get('richtext')
    r = t.get('screen') or t['rect']
    if not lab or not lab.get('height') or not ch:
        return None
    return min(_font_size(lab) * r[3] / float(lab['height']), r[3]) * ch


def _font_size(lab):
    """Drawn font size: the smaller of fontSize / actualFontSize (some dumps report actualFontSize above a SHRINK
    label's own fontSize, BlackHoleCity ResourceBar 12 vs 40)."""
    sizes = [v for v in (lab.get('fontSize'), lab.get('actualFontSize')) if v]
    return min(sizes) if sizes else 0


def glyph_core_problems(d, nodes, ratios, image_module, records=None, img=None, english=False):
    """small_glyph_core / small_value_font / glyph_core_review for the values Saul reads first: HUD numbers (v7.8 hud_digit_problems scope,
    all page kinds), named core values (coins, hearts, score, level, reward, stars ...) and font_value_label lines
    ("LEVEL 1"); secondary named values (price, card level, count badge) use the lower MIN_MINOR limit.
    img: the page screenshot audit_page_richness.check() already decoded (RGB); opened here only when not given.
    english: an English game (english_game): small_value_font is reported as the advisory small_value_font_hint."""
    if img is None and image_module is not None and d.get('_file') and apr.screenshot_of(d).is_file():
        img = image_module.open(apr.screenshot_of(d)).convert('RGB')
    ch = (d.get('canvas_css') or [0, 0, 0, 0])[3]
    path_counts = {}
    for n in nodes:
        path_counts[n['path']] = path_counts.get(n['path'], 0) + (1 if 'sprite' in n['comps'] else 0)
    buttons = [n for n in nodes if 'button' in n['comps']]
    grouped = digit_groups(nodes)
    members = {id(m) for g in grouped for m in g['_members']}
    out = []
    for t in [n for n in nodes if id(n) not in members] + grouped:
        s = apr.text(t)
        if not _value_text(s):
            continue
        r = t.get('screen') or t['rect']
        if apr.area(r) <= 0 or apr.inter(r, [0, 0, 1, 1]) < 0.5 * apr.area(r):
            continue
        words = path_words(t['path'])
        in_button = 'button' in t['comps'] or any(apr.node_under(t, b) for b in buttons)
        named = bool(CORE_NAME.search(words))
        top_bar = r[1] + r[3] / 2 < apr.HUD_BAND[0] and named                 # resource bar on any page
        hud = d.get('kind') == 'gameplay' and _hud(t, path_counts)            # v7.8 hud_digit_problems scope
        end_value = d.get('purpose') in END_PURPOSES and named                # result / revive reward, score
        core = not in_button and (hud or top_bar or end_value or apr.HUD_NAME.search(t['path']) is not None)
        minor = not core and (named or bool(MINOR_NAME.search(words)) or apr.value_label(s))
        if not (core or minor) or (not core and not hud and apr.on_repeated_piece(t, path_counts)
                                   and not MINOR_NAME.search(words)):
            continue
        h, how = ink_share(t, ratios, img)
        if records is not None:
            records.append({'path': t['path'], 'text': s[:16], 'core': core, 'hud': hud, 'in_button': in_button,
                            'share': h, 'css': h * ch if (h and ch) else None, 'how': how, 'rect': r,
                            'box_css': r[3] * ch if ch else None, 'font_css': _font_css(t, ch)})
        if h is None:
            continue
        css = h * ch if ch else None
        lim_css, lim_share = (MIN_CORE_CSS, MIN_CORE_SHARE) if core else (MIN_MINOR_CSS, MIN_MINOR_SHARE)
        small = css < lim_css if css is not None else h < lim_share
        if small:
            # Nominal size = what the font size / node box promises (v7.8 hud_digit_small measures this one).
            nominal = (_font_css(t, ch) / ch * SYSTEM_INK_RATIO) if (ch and _font_css(t, ch)) else r[3]   # picture: box = digit
            padded = (nominal * ch >= lim_css - 1e-6) if ch else (nominal >= lim_share - 1e-9)   # size looks big enough
            seen = '%.1f CSS px' % css if css is not None else '%.1f%% of the screen' % (100 * h)
            need = '%.0f CSS px' % lim_css if css is not None else '%.1f%%' % (100 * lim_share)
            if padded and how == 'screenshot':
                out.append('glyph_core_review: the %s value "%s" (%s) measures only %s of visible digits on the '
                           'screenshot (min %s) although its font size / box is big enough; no font metrics were found, so '
                           'look at the screenshot: tight-crop the digits if they really are this small (advisory)'
                           % ('core' if core else 'secondary', s[:16], t['path'], seen, need))
            elif padded:
                out.append('small_glyph_core: the %s value "%s" (%s) has a big enough font size / box but its visible '
                           'digits are only %s high (%s; min %s): the digit pictures carry wide transparent margins - crop '
                           'them tight and rebuild the font, or enlarge the value (Milo 10-24 "2比5文字怎么这么小", TankAce '
                           '10-26 "根本看不清", 企鹅雪道 10-30 分数体力货币关卡数要明显)'
                           % ('core' if core else 'secondary', s[:16], t['path'], seen, how, need))
            elif core and not hud and how != 'screenshot' and FLAG_SMALL_FONT:
                what = ('the %s value "%s" (%s) is drawn %s high (%s; min %s)'
                        % ('core' if core else 'secondary', s[:16], t['path'], seen, how, need))
                if english:
                    out.append('small_value_font_hint: %s - English game: listed for a look only, not a failure (Saul '
                               '2026-10-31 "small_value_font 先只拦重塑"); enlarge it if it really reads small' % what)
                else:
                    out.append('small_value_font: %s: enlarge the value (企鹅雪道 10-30 分数体力货币关卡数要明显)' % what)
            continue
    return out


def english_game(project, board=None):
    """True for an English (localize) game, where small_value_font is only the advisory small_value_font_hint (Saul
    2026-10-31 "small_value_font 先只拦重塑"). The board is the one given (art_check.py --board), else the one the
    package writers use (art_receipt.strictness order: .tiktok-kit/finalize-source.json, then .tiktok-kit/policy.json,
    which `tiktok_finalize.py init --board` writes at kickoff, then docs/board.txt), else remake. docs/art-style.txt
    "original" also counts as English (art_records.applies)."""
    root = Path(project) if project is not None else None
    if not board and root is not None:
        import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import feature_policy  # P20: the one board reader (same order as before: finalize-source, policy, board.txt)
        board = feature_policy.board_of(root)[0]
    if board == 'localize':
        return True
    if root is None:
        return False
    try:
        return (root / 'docs' / 'art-style.txt').read_text(encoding='utf-8-sig').strip().lower() == 'original'
    except OSError:
        return False


def project_of(dump_file):
    """Nearest folder above a dump that holds a Cocos assets/ folder (the dump's own project), or None."""
    for p in Path(dump_file).resolve().parents:
        if (p / 'assets').is_dir() and ((p / 'project.json').is_file() or (p / 'package.json').is_file()
                                        or (p / 'settings').is_dir()):
            return p
    return None


def main(argv=None):
    import argparse
    try:  # P20: a missing Pillow is a not_run line (exit 2), --help still prints help
        from PIL import Image
    except ImportError:
        import importlib.util as _ilu
        _cg = Path(__file__).resolve().parents[2] / 'cocos-game-check' / 'package-check' / 'scripts' / 'check_guard.py'
        if not _cg.is_file():
            raise
        _spec = _ilu.spec_from_file_location('check_guard', _cg)
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _mod.need_modules('PIL', doc=__doc__)
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--project', help='Cocos project root (static digit_glyph_padding)')
    ap.add_argument('dumps', nargs='*', help='folders holding *ui-dump-*.json (runtime small_glyph_core)')
    a = ap.parse_args(argv)
    ratios = font_ink_ratios(a.project, Image) if a.project else {}
    problems = digit_glyph_padding_problems(ratios, a.project) if a.project else []
    english = english_game(a.project) if a.project else False
    for d in apr.load(a.dumps):
        nodes = [n for n in d.get('nodes', []) if n.get('opacity', 1) > 0.05]
        for p in glyph_core_problems(d, nodes, ratios, Image, english=english):
            problems.append('%s: %s' % (Path(d['_file']).name, p))
    print(json.dumps({'ok': not problems, 'problems': problems,
                      'fonts': {k: {x: v[x] for x in ('kind', 'ratio', 'ink', 'em')} for k, v in ratios.items()}},
                     ensure_ascii=False, indent=1))
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
