#!/usr/bin/env python3
"""Dark button bodies and item icons on their own plate (Saul 2026-10-31, 香肠太难了 Redesign v2: "不要这种深色背景，的按钮，
也不要图案后面还跟着这个背景，比如金币的图案增加了一个背景，不要这样，要禁止"; every icon button and the three direction keys sat
on one tomato-red tile, measured RGB 192,79,57 = L* 48, the free-coins entry was two coins and a video icon on that tile).

Cost: no capture of its own. audit_page_richness.check() hands over the screenshot it has already opened, every button
and item icon is measured on a strided crop of that one array (about 1 ms a page), and the button states nobody
screenshots (pressed / hover / disabled sprites, COLOR transitions) are read once per project from the scenes and
prefabs that contain a cc.Button, decoding only the few textures those buttons name. What is covered:

  dark_button        every visible button on every dumped page and popup, both phone sizes, interactable or not, game
                     controls included: its rendered body (the biggest picture under the button, the same plate
                     flat_button measures) has a dark main colour. Dark = L* < 40, or L* < 52 with HSV value < 0.85
                     (dull: tomato/brick/sauce red, dark brown, navy, dark green, dark grey, black). Saturated light
                     colours (bright red 229,57,53 = L* 52 V 0.90, bright blue, orange, mint) pass. Measured
                     on the screenshot, so node tint, opacity and overlays count as the player sees them.
  icon_plate         a coin / gem / heart / energy item icon that has its own plate: a square or rounded-square tile
                     painted into the icon picture (corners and all four sides one colour that is not the scene behind,
                     the item different in the middle), or a separate picture/graphics node right behind the icon that
                     holds no text (a price button or a resource capsule with its number is not a plate).
  dark_button_state  (project setup) a cc.Button whose pressed / hover / disabled sprite, or COLOR transition tint over
                     its normal sprite, comes out dark. Disabled tint only counts for a button saved as not
                     interactable (one the player will see disabled).

Original art: an English game (docs/board.txt localize, or docs/art-style.txt original) keeps the original game's
buttons on purpose; a frame whose every source file is byte-identical to an image of the original (the English flow's
docs/english/pre-english-images.json from step 1, or docs/art/base-assets.json), or that matches
docs/art/clarity-exempt.json, is not reported. With neither record an English game cannot tell its new buttons from
the original ones, and every finding says how to record the original.
"""
import colorsys
import fnmatch
import json
from pathlib import Path
import re

DARK_L = 40.0            # always dark below this L*
DULL_L = 50.0            # dark below this L* when the colour is also dull (Saul's tomato tile: L* 48, V 0.75)
DULL_V = 0.85            # HSV value (max channel) below this = dull
MUDDY_L, MUDDY_V = 55.0, 0.55   # no channel above 140 and not light: dark teal / olive / grey (Meteor "FREE" 72,133,118)
HINT_L, HINT_V = 55.0, 0.80     # just above the line: listed for the eye (visual_verdict 6), never a failure
MIN_OPACITY = 0.6        # a half-transparent button is a deliberate state; the scene shows through it
MIN_PX = 12              # smaller crops are not measured
MIN_BODY_SHARE = 0.25    # the main colour must cover at least a quarter of the plate
MIN_BUTTON_PIXELS = 0.20 # less than this differs from the scene behind: a hit area or a bare icon, no body
BG_DISTANCE = 28         # RGB distance from the scene behind that counts as "button pixel"
MAX_BUTTON = 0.40        # full-screen tap catchers are not buttons with a body
SAMPLE = 48              # crops are strided down to about 48 x 48 samples
PIECE_REPEAT = 3         # a button path drawn 3+ times on a gameplay page is a play piece (tile, card), not a control
ITEM_TOKENS = {'coin', 'coins', 'gold', 'golds', 'jinbi', 'jb', 'money', 'cash', 'gem', 'gems', 'diamond', 'diamonds',
               'zuanshi', 'zuan', 'crystal', 'crystals', 'heart', 'hearts', 'life', 'lives', 'energy', 'stamina', 'tili',
               'lightning', 'bolt'}
HOLDER_TOKENS = {'bar', 'meter', 'bg', 'back', 'panel', 'frame', 'slot', 'card', 'board', 'progress', 'fill', 'strip',
                 'capsule', 'pill', 'banner', 'ribbon', 'shadow', 'glow', 'light', 'shine', 'fx', 'particle',
                 'txt', 'text', 'word', 'words', 'label', 'title', 'caption', 'hud'}   # picture text "COINS" is not an icon
TOKENS = re.compile(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+')
DARK_LIST = '深红、砖红、酱红、深棕、藏青、深蓝、深绿、深灰、黑'
SAUL = 'Saul 2026-10-31 香肠太难了: "不要这种深色背景，的按钮"'
SAUL_PLATE = 'Saul 2026-10-31 香肠太难了: "金币的图案增加了一个背景，不要这样，要禁止"'


def _np():
    try:
        import numpy
        return numpy
    except ImportError:          # art_check.py reruns itself with a numpy python; a bare call says so
        return None


def area(r):
    return max(0.0, r[2]) * max(0.0, r[3])


def _rect(n):
    return n.get('screen') or n['rect']


def geometry(d):
    """(x, y, w, h) of the game canvas inside the screenshot, as fractions: dump rects are relative to the canvas
    (canvas_css inside the page), the screenshot is the page (any device pixel ratio)."""
    cc, pg = d.get('canvas_css') or [], d.get('page') or {}
    pw, ph = float(pg.get('width') or 0), float(pg.get('height') or 0)
    if len(cc) == 4 and pw > 0 and ph > 0 and cc[2] and cc[3]:
        return (cc[0] / pw, cc[1] / ph, cc[2] / pw, cc[3] / ph)
    return (0.0, 0.0, 1.0, 1.0)


def _shot(r, geom):
    gx, gy, gw, gh = geom
    return [gx + r[0] * gw, gy + r[1] * gh, r[2] * gw, r[3] * gh]


def _under(a, b):
    """Same rule as audit_page_richness.node_under: ancestor ids when the dump has them, else the path."""
    if '_audit_ancestors' in a and b.get('id'):
        return a is b or b['id'] in a['_audit_ancestors']
    pa, pb = a.get('path', ''), b.get('path', '')
    return pa == pb or pa.startswith(pb + '/')


def _frame(n):
    return str(((n.get('comps') or {}).get('sprite') or {}).get('frame', '') or '')


def _text(n):
    c = n.get('comps') or {}
    lab = c.get('label') or c.get('richtext') or {}
    return str(lab.get('string') or lab.get('text') or n.get('text') or '').strip() if isinstance(lab, dict) else ''


def tokens(*values):
    return {t.lower() for v in values for t in TOKENS.findall(str(v))}


def lstar(rgb):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    y = 0.2126 * lin(float(rgb[0])) + 0.7152 * lin(float(rgb[1])) + 0.0722 * lin(float(rgb[2]))
    return 116 * y ** (1 / 3) - 16 if y > 216 / 24389 else 24389 / 27 * y


def is_dark(rgb):
    lum, v = lstar(rgb), max(rgb) / 255.0
    return lum < DARK_L or (lum < DULL_L and v < DULL_V) or (lum < MUDDY_L and v < MUDDY_V)


def near_dark(rgb):
    """Not dark, but close enough that a person should look (reported as a hint, not a failure)."""
    return not is_dark(rgb) and lstar(rgb) < HINT_L and max(rgb) / 255.0 < HINT_V


def family(rgb):
    """The word Saul would use for a dark colour (for the message only)."""
    h, s, v = colorsys.rgb_to_hsv(*(c / 255.0 for c in rgb))
    lum, hue = lstar(rgb), h * 360
    if lum < 18:
        return '黑'
    if s < 0.18:
        return '深灰'
    if hue < 15 or hue >= 340:
        return '深红' if lum < 40 else '砖红/番茄红'
    if hue < 45:
        return '深棕' if s < 0.75 or lum < 40 else '酱红/深橙'
    if hue < 70:
        return '深棕/橄榄'
    if hue < 170:
        return '深绿'
    if hue < 255:
        return '藏青/深蓝'
    return '深紫'


def box_of(r, W, H):
    x0, y0 = int(max(0.0, r[0]) * W), int(max(0.0, r[1]) * H)
    x1, y1 = int(min(1.0, r[0] + r[2]) * W), int(min(1.0, r[1] + r[3]) * H)
    if x1 - x0 < MIN_PX or y1 - y0 < MIN_PX:
        return None
    return x0, y0, x1, y1


def _crop(arr, box, np):
    x0, y0, x1, y1 = box
    step = max(1, max(x1 - x0, y1 - y0) // SAMPLE)
    return arr[y0:y1:step, x0:x1:step].astype(np.int16), step


def _behind(arr, box, np):
    """Median colour of a thin ring just outside the box: the scene the button sits on."""
    H, W = arr.shape[:2]
    x0, y0, x1, y1 = box
    pad = max(2, int(0.06 * max(x1 - x0, y1 - y0)))
    step = max(1, max(x1 - x0, y1 - y0) // SAMPLE)
    parts = []
    if y0 - pad >= 0:
        parts.append(arr[y0 - pad:y0:step, x0:x1:step].reshape(-1, 3))
    if y1 + pad <= H:
        parts.append(arr[y1:y1 + pad:step, x0:x1:step].reshape(-1, 3))
    if x0 - pad >= 0:
        parts.append(arr[y0:y1:step, x0 - pad:x0:step].reshape(-1, 3))
    if x1 + pad <= W:
        parts.append(arr[y0:y1:step, x1:x1 + pad:step].reshape(-1, 3))
    parts = [p for p in parts if len(p)]
    if not parts:
        return None
    return np.median(np.concatenate(parts).astype(np.int16), axis=0)


def _main_colour(px, np):
    """(mean colour, mask) of the most common 16-level colour bin and its neighbours."""
    q = px >> 4
    key = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    vals, counts = np.unique(key, return_counts=True)
    m = int(vals[counts.argmax()])
    mq = np.array([m // 256, (m // 16) % 16, m % 16], dtype=np.int16)
    near = np.abs(q - mq).max(axis=1) <= 1
    return px[near].mean(axis=0), near


def body(arr, r, np):
    """Main colour of the button body inside normalised rect r of the RGB array: {'rgb', 'share', 'button'} or None."""
    H, W = arr.shape[:2]
    box = box_of(r, W, H)
    if box is None:
        return None
    bg = _behind(arr, box, np)
    crop, _ = _crop(arr, box, np)
    px = crop.reshape(-1, 3)
    if bg is None or not len(px):
        return None
    far = np.sqrt(((px - bg) ** 2).sum(axis=1)) > BG_DISTANCE
    own = px[far]
    if len(own) < MIN_BUTTON_PIXELS * len(px):
        return {'rgb': None, 'share': 0.0, 'button': len(own) / float(len(px))}
    col, near = _main_colour(own, np)
    return {'rgb': tuple(int(round(c)) for c in col), 'share': float(near.sum()) / len(px),
            'button': len(own) / float(len(px)), 'behind': float(np.sqrt(((col - bg) ** 2).sum()))}


def rendered_plate(b, nodes):
    """The biggest picture or graphics under the button (what flat_button measures), else the button itself."""
    br = _rect(b)
    plates = [n for n in nodes if _under(n, b) and
              ('graphics' in n['comps'] or ('sprite' in n['comps'] and not _frame(n).lower().startswith('txt_'))) and
              area(_rect(n)) >= 0.3 * area(br)]
    return max(plates, key=lambda n: area(_rect(n))) if plates else b


def _repeated(nodes):
    counts = {}
    for n in nodes:
        counts[n['path']] = counts.get(n['path'], 0) + 1
    return {p for p, c in counts.items() if c >= PIECE_REPEAT}


DIM_NAME = re.compile(r'dim|shade|shadow|mask|overlay|modal|blackbg|black_bg|zhezhao|遮罩', re.I)


def dimmed(b, nodes, by_id):
    """A full-screen shade drawn after the button (a popup's dim, block_input or not): the button is the dimmed
    scene behind a popup, not a dark button (珊瑚守卫 result page: sprShopShadow, a 2x2 black sprite at 63%)."""
    for n in nodes:
        if n.get('order', 0) <= b.get('order', 0) or area(n['rect']) < 0.85 or _under(b, n):
            continue
        comps = n.get('comps') or {}
        s = comps.get('sprite') or {}
        size = s.get('frame_size') or [99, 99]
        flat = 'graphics' in comps or (isinstance(size, list) and len(size) == 2 and max(size) <= 4)
        if (flat or DIM_NAME.search(n.get('name', '') + ' ' + str(s.get('frame', '')))) and _opacity(n, by_id) >= 0.1:
            return True
    return False


def _opacity(n, by_id):
    """Opacity the player sees: the node's own times every ancestor's (dump opacity is per node)."""
    o = float(n.get('opacity', 1) or 0)
    for a in n.get('_audit_ancestors') or ():
        o *= float((by_id.get(a) or {}).get('opacity', 1) or 0)
    return o


def measure_buttons(nodes, buttons, arr, kind=None, original=(), geom=(0.0, 0.0, 1.0, 1.0)):
    """One measurement per visible button with a body: dicts with button, plate, frame, rgb, share, dark, hint."""
    np = _np()
    if np is None or arr is None:
        return
    by_id = {n['id']: n for n in nodes if n.get('id')}
    pieces = _repeated(buttons) if kind == 'gameplay' else set()
    seen = set()
    for b in buttons:
        if b['path'] in pieces or area(_rect(b)) >= MAX_BUTTON:
            continue
        plate = rendered_plate(b, nodes)
        comps = plate.get('comps') or {}
        if 'sprite' not in comps and 'graphics' not in comps:
            continue                                  # text-only button: bare_button reports it, it has no body
        frame = _frame(plate)
        if _opacity(plate, by_id) < MIN_OPACITY:
            continue                                  # half-transparent on purpose (cooldown, locked look)
        key = (b['path'], frame)
        if key in seen or dimmed(b, nodes, by_id):
            continue
        seen.add(key)
        m = body(arr, _shot(_rect(plate), geom), np)
        if not m or not m['rgb'] or m['share'] < MIN_BODY_SHARE:
            continue
        dark, hint = is_dark(m['rgb']), near_dark(m['rgb'])
        if (dark or hint) and frame and frame in original:
            continue                                  # English game: the original game's own button picture
        yield {'button': b, 'plate': plate, 'frame': frame, 'rgb': m['rgb'], 'share': m['share'],
               'dark': dark, 'hint': hint}


def dark_button_problems(nodes, buttons, arr, kind=None, original=(), geom=(0.0, 0.0, 1.0, 1.0)):
    """(dark_button findings, near-dark hints) for one page. arr: RGB numpy array of the page screenshot."""
    out, hints = [], []
    for m in measure_buttons(nodes, buttons, arr, kind, original, geom):
        rgb, b, frame = m['rgb'], m['button'], m['frame']
        what = '%s%s' % (b['path'], ' "%s"' % frame if frame else '')
        if m['dark']:
            out.append('dark_button: %s has a dark body on the screenshot (%s, RGB %d,%d,%d, L* %.0f, %.0f%% of the '
                       'button): no button body in %s, pressed/disabled/claimed states included (%s); English games '
                       'use the original game\'s button picture, remakes regenerate a lighter body in the starter-pack '
                       'style' % (what, family(rgb), rgb[0], rgb[1], rgb[2], lstar(rgb), m['share'] * 100, DARK_LIST, SAUL))
        elif m['hint']:
            hints.append('%s 底色偏深（RGB %d,%d,%d，L* %.0f）' % (what, rgb[0], rgb[1], rgb[2], lstar(rgb)))
    return out, hints


KINDS = ('dark_button', 'icon_plate', 'dark_button_state', 'button_colour_unavailable')
NO_RECORD = (' [English game without docs/english/pre-english-images.json or docs/art/base-assets.json: its original '
             'buttons cannot be told from new ones; record the original first: audit_new_english_images.py --make-list '
             '<中文原工程> --out docs/english/pre-english-images.json, or art_records.py base --project <工程> --from <原版>]')


def page_problems(d, nodes, img, original=()):
    """(findings, near-dark hints) for one dumped page, measured on the screenshot the caller already opened
    (a PIL image; None = no screenshot, nothing measured). nodes: the page's visible, un-occluded nodes."""
    if img is None:
        return [], []
    np = _np()
    if np is None:
        return ['button_colour_unavailable: measuring button colours needs numpy (art_check.py reruns itself with a '
                'python that has it); this page has not passed the dark-button / icon-plate check'], []
    arr = np.asarray(img if img.mode == 'RGB' else img.convert('RGB'))
    geom, kind = geometry(d), d.get('kind')
    cc = d.get('canvas_css') or [0, 0, 1, 1]
    buttons = [n for n in nodes if 'button' in (n.get('comps') or {})]
    dark, hints = dark_button_problems(nodes, buttons, arr, kind, original, geom)
    plates = icon_plate_problems(nodes, arr, kind, (float(cc[2] or 1), float(cc[3] or 1)), original, geom)
    found = dark + plates
    if found and getattr(original, 'missing', False):
        found = [x + NO_RECORD for x in found]
    return found, hints


# ------------------------------------------------------------------ item icons on their own plate

PATCH = 0.12             # corner / side patches: 12% of the box, starting 5% in from the edge
SAME = 35                # patches this close to each other are one plate colour
PLATE_VS_BEHIND = 40     # the plate differs this much from the scene around it
ITEM_VS_PLATE = 50       # the middle (the item) differs this much from the plate
HUE_APART = 25           # degrees: plate and item are different objects (香肠 v2: tile hue 9, coins hue 44)
HOLDER_MIN, HOLDER_MAX = 1.25, 6.0   # a separate plate is 1.25x-6x the icon's area
HOLDER_ASPECT = 1.6      # and squarish (tile, disc, badge); wider ones are resource capsules / bars
DECOR_TOKENS = {'glow', 'light', 'shine', 'ray', 'rays', 'burst', 'sunburst', 'halo', 'shadow', 'fx', 'particle', 'star',
                'stars', 'sparkle', 'sparkles', 'flash', 'effect', 'spin', 'wheel'}
HUD_BAND = (0.18, 0.90)  # gameplay pages: only the HUD (top 18% / bottom 10%, or under a hud/top-bar node) is UI
HUD_NAME = re.compile(r'hud|topbar|top_bar|top-bar|resource|wallet|scorebar', re.I)


def item_icon(n):
    t = tokens(n.get('name', ''), _frame(n))
    return 'sprite' in (n.get('comps') or {}) and bool(t & ITEM_TOKENS) and not (t & HOLDER_TOKENS)


def _patch(arr, box, fx, fy, fw, fh, np):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    a0, b0 = x0 + int(fx * w), y0 + int(fy * h)
    a1, b1 = max(a0 + 1, x0 + int((fx + fw) * w)), max(b0 + 1, y0 + int((fy + fh) * h))
    step = max(1, max(a1 - a0, b1 - b0) // 12)
    return np.median(arr[b0:b1:step, a0:a1:step].reshape(-1, 3).astype(np.int16), axis=0)


def _dist(a, b, np):
    return float(np.sqrt(((np.asarray(a, dtype=np.float32) - np.asarray(b, dtype=np.float32)) ** 2).sum()))


def other_object(a, b):
    """True when colours a and b belong to different objects (a red tile vs gold coins), not to one object's rim and
    face (a coin's orange rim vs its yellow face: same hue, different lightness)."""
    ha, sa, _ = colorsys.rgb_to_hsv(*(c / 255.0 for c in a))
    hb, sb, _ = colorsys.rgb_to_hsv(*(c / 255.0 for c in b))
    dl = abs(lstar(a) - lstar(b))
    if sa >= 0.25 and sb >= 0.25:
        dh = abs(ha - hb) * 360
        return min(dh, 360 - dh) >= HUE_APART
    if (sa < 0.15) != (sb < 0.15):
        return dl >= 15 or max(sa, sb) >= 0.4      # a grey/white plate under a coloured item, or the reverse
    return dl >= 40


def plate_shape(arr, r, np):
    """Plate colour when the box shows one colour on all four sides (5-17% in from each edge) that is not the scene
    behind it, with a different object in the middle; else None. Square, rounded and round plates alike."""
    H, W = arr.shape[:2]
    box = box_of(r, W, H)
    if box is None:
        return None
    bg = _behind(arr, box, np)
    if bg is None:
        return None
    e, p, m = 0.05, PATCH, 0.5 - PATCH / 2
    top, bottom, left, right = [_patch(arr, box, x, y, p, p, np) for x, y in
                                ((m, e), (m, 1 - e - p), (e, m), (1 - e - p, m))]
    frame = [top, left, right]                    # the bottom may carry a caption baked into the tile ("COINS")
    plate = np.median(np.stack(frame), axis=0)
    if any(_dist(f, plate, np) > SAME for f in frame) or _dist(plate, bg, np) < PLATE_VS_BEHIND:
        return None
    if _dist(bottom, plate, np) > SAME:            # then the tile must reach the bottom corners' height on both sides
        low = [_patch(arr, box, x, 0.70, p, p, np) for x in (e, 1 - e - p)]
        if any(_dist(f, plate, np) > SAME for f in low):
            return None
    middle = _patch(arr, box, 0.35, 0.35, 0.3, 0.3, np)
    plate_rgb = tuple(int(round(c)) for c in plate)
    if _dist(middle, plate, np) < ITEM_VS_PLATE or not other_object(plate_rgb, tuple(int(c) for c in middle)):
        return None
    return plate_rgb


def _holds_text(p, nodes):
    pr = _rect(p)
    for n in nodes:
        if not _text(n):
            continue
        r = _rect(n)
        cx, cy = r[0] + r[2] / 2, r[1] + r[3] / 2
        if pr[0] <= cx <= pr[0] + pr[2] and pr[1] <= cy <= pr[1] + pr[3]:
            return True
    return False


def _inter(a, b):
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def _in_hud(n, by_id):
    r = _rect(n)
    cy = r[1] + r[3] / 2
    if cy <= HUD_BAND[0] or cy >= HUD_BAND[1] or HUD_NAME.search(n.get('path', '')):
        return True
    return any(HUD_NAME.search((by_id.get(a) or {}).get('name', '')) for a in n.get('_audit_ancestors') or ())


def icon_plate_problems(nodes, arr, kind=None, canvas=(1.0, 1.0), original=(), geom=(0.0, 0.0, 1.0, 1.0)):
    """icon_plate findings for one page: coin / gem / heart / energy icons with a plate of their own."""
    out = []
    for icon, plate, colour in find_icon_plates(nodes, arr, kind, canvas, original, geom):
        frame = _frame(icon)
        if plate is None:
            out.append('icon_plate: %s "%s" is drawn on a plate inside its own picture (RGB %d,%d,%d all round the '
                       'item): coin, gem, heart and energy icons are one standalone picture with a transparent '
                       'background, never on a square/round tile or capsule (%s); English games use the original '
                       'game\'s item picture' % (icon['path'], frame, colour[0], colour[1], colour[2], SAUL_PLATE))
        else:
            pframe = _frame(plate)
            out.append('icon_plate: %s "%s" sits on its own plate %s%s (RGB %d,%d,%d around it): coin, gem, heart and '
                       'energy icons stand alone with no tile, disc or capsule behind them; a plate is only for a button '
                       'or a capsule that also holds its text or number (%s)'
                       % (icon['path'], frame, plate['path'], ' "%s"' % pframe if pframe else '', colour[0], colour[1],
                          colour[2], SAUL_PLATE))
    return out


def find_icon_plates(nodes, arr, kind=None, canvas=(1.0, 1.0), original=(), geom=(0.0, 0.0, 1.0, 1.0)):
    """Yield (icon node, plate node or None for a plate painted into the icon picture, plate colour)."""
    np = _np()
    if np is None or arr is None:
        return
    by_id = {n['id']: n for n in nodes if n.get('id')}
    cw, ch = canvas
    pieces = _repeated(nodes) if kind == 'gameplay' else set()
    seen = set()
    for icon in nodes:
        if not item_icon(icon) or _opacity(icon, by_id) < MIN_OPACITY or dimmed(icon, nodes, by_id):
            continue
        if kind == 'gameplay' and (icon['path'] in pieces or not _in_hud(icon, by_id)):
            continue                                  # coins and hearts lying in the play field are game pieces
        ir, frame = _rect(icon), _frame(icon)
        if area(ir) <= 0 or area(ir) > 0.06:
            continue
        key = (icon['path'], frame)
        if key in seen:
            continue
        # 1) the plate painted into the icon picture itself (香肠 v2 icon_coins: two coins and a video icon on a tile)
        if not _holds_text(icon, [n for n in nodes if n is not icon and not _under(n, icon)]):
            tile = plate_shape(arr, _shot(ir, geom), np)
            if tile:
                seen.add(key)
                if frame not in original:             # English game: the original's own item picture stays
                    yield icon, None, tile
                continue
        # 2) a separate picture right behind the icon that holds no text (a price button or a capsule with its number
        #    is not a plate)
        for p in nodes:
            comps = p.get('comps') or {}
            if p is icon or _under(p, icon) or p.get('order', 0) >= icon.get('order', 0):
                continue
            if 'sprite' not in comps and 'graphics' not in comps:
                continue
            pr = _rect(p)
            ratio = area(pr) / area(ir)
            if not (HOLDER_MIN <= ratio <= HOLDER_MAX) or _inter(ir, pr) < 0.9 * area(ir) or area(pr) > 0.06:
                continue
            pw, ph = pr[2] * cw, pr[3] * ch
            if max(pw, ph) > HOLDER_ASPECT * max(1e-6, min(pw, ph)) or item_icon(p) or p['path'] in pieces:
                continue
            if tokens(p.get('name', ''), _frame(p)) & DECOR_TOKENS:
                continue                              # a glow / burst behind a reward is decoration, not a plate
            if _opacity(p, by_id) < MIN_OPACITY or _holds_text(p, nodes):
                continue
            colour = plate_shape(arr, _shot(pr, geom), np)
            if not colour:
                continue
            seen.add(key)
            pframe = _frame(p)
            if not (pframe and pframe in original and frame in original):   # the original's own icon-on-plate stays
                yield icon, p, colour
            break


# ------------------------------------------------------------------ project side: frame index, original art, states

IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.webp')
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles', '.tiktok-kit'}
PRESS_TINT_L = 70.0      # a COLOR transition press tint darker than this (default 211,211,211 = L* 85) is checked


def _metas(proj):
    root = Path(proj) / 'assets'
    if not root.is_dir():
        return
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for p in entries:
            if p.is_dir():
                if p.name.lower() not in SKIP_DIRS:
                    stack.append(p)
            elif p.name.endswith('.meta'):
                yield p


def frame_index(proj):
    """{'uuid': {uuid: (texture, (x, y, w, h) or None, rotated)}, 'name': {frame name: [texture, ...]}} for Cocos 2.4
    (subMetas keyed by frame name, TexturePacker .plist frames) and 3.x (sprite-frame sub-assets, uuid@f9941)."""
    by_uuid, by_name = {}, {}
    for meta in _metas(proj):
        src = Path(str(meta)[:-5])
        low = src.name.lower()
        if not (low.endswith(IMAGE_EXT) or low.endswith('.plist')):
            continue
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        tex = src if low.endswith(IMAGE_EXT) else src.with_suffix('.png')
        for key, sub in (data.get('subMetas') or {}).items():
            if not isinstance(sub, dict):
                continue
            ud = sub.get('userData') if isinstance(sub.get('userData'), dict) else sub
            name = key if not sub.get('importer') else (src.stem if sub.get('name') in (None, 'spriteFrame') else sub['name'])
            if sub.get('importer') not in (None, 'sprite-frame'):
                continue
            try:
                rect = (int(ud.get('trimX', 0)), int(ud.get('trimY', 0)), int(ud['width']), int(ud['height']))
            except (KeyError, TypeError, ValueError):
                rect = None
            row = (tex, rect, bool(ud.get('rotated')), name)
            if sub.get('uuid'):
                by_uuid[str(sub['uuid'])] = row
            by_name.setdefault(name, []).append(tex)
    return {'uuid': by_uuid, 'name': by_name}


class OriginalArt:
    """Frames an English game keeps from the original (docs/board.txt localize or docs/art-style.txt original):
    every source file of the frame is byte-identical to an image in docs/english/pre-english-images.json or
    docs/art/base-assets.json, or the frame matches docs/art/clarity-exempt.json. Hashing starts only when a finding
    asks (most pages never need it)."""

    def __init__(self, proj):
        self.proj = Path(proj) if proj else None
        self.english = False
        self.record = None
        self.globs = []
        self._index = None
        self._sha = {}
        if self.proj is None:
            return
        board = self._read('docs/board.txt').strip().lower()
        style = self._read('docs/art-style.txt').strip().lower()
        self.english = board == 'localize' or style == 'original'
        if not self.english:
            return
        try:
            base = json.loads(self._read('docs/art/base-assets.json') or 'null')
        except ValueError:
            base = None
        if isinstance(base, dict) and isinstance(base.get('images'), dict):
            self.record = {str(h).lower() for h in base['images'].values()}
            self.record |= {str(h).lower() for h in (base.get('derived') or {})}
        try:                         # the English flow's own list (step 1, audit_new_english_images.py --make-list)
            pre = json.loads(self._read('docs/english/pre-english-images.json') or 'null')
        except ValueError:
            pre = None
        if isinstance(pre, dict) and isinstance(pre.get('images'), dict):
            self.record = (self.record or set()) | {str(h).lower() for h in pre['images']}
        try:                         # same file and rule as audit_page_richness CLARITY_EXEMPT: frame + why
            ce = json.loads(self._read('docs/art/clarity-exempt.json') or 'null')
            rows = ce.get('frames', []) if isinstance(ce, dict) else []
            self.globs = [str(r['frame']) for r in rows
                          if isinstance(r, dict) and r.get('frame') and str(r.get('why', '')).strip()]
        except (ValueError, AttributeError, TypeError):
            self.globs = []

    def _read(self, rel):
        try:
            return (self.proj / rel).read_text(encoding='utf-8-sig')
        except OSError:
            return ''

    @property
    def missing(self):
        """An English game that has not recorded its original: findings say how to record it."""
        return self.english and self.record is None

    def __contains__(self, frame):
        if not self.english or not frame:
            return False
        if any(fnmatch.fnmatch(frame, g) for g in self.globs):
            return True
        if not self.record:
            return False
        if self._index is None:
            self._index = frame_index(self.proj)
        files = self._index['name'].get(frame) or []
        return bool(files) and all(self._digest(f) in self.record for f in files)

    def _digest(self, f):
        if f not in self._sha:
            import hashlib
            try:
                self._sha[f] = hashlib.sha256(Path(f).read_bytes()).hexdigest()
            except OSError:
                self._sha[f] = ''
        return self._sha[f]


def _colour(obj):
    if isinstance(obj, dict) and all(k in obj for k in ('r', 'g', 'b')):
        return (int(obj['r']), int(obj['g']), int(obj['b']))
    return None


def _field(obj, name):
    for k in ('_N$' + name, name, '_' + name):
        if k in obj:
            return obj[k]
    return None


def _uuid(ref):
    return str(ref['__uuid__']) if isinstance(ref, dict) and ref.get('__uuid__') else None


def _texture_body(tex, rect, rotated, np):
    """Main opaque colour of a sprite frame inside its texture (alpha >= 200), or None."""
    from PIL import Image
    try:
        im = Image.open(tex).convert('RGBA')
    except (OSError, ValueError):
        return None
    if rect:
        x, y, w, h = rect
        if rotated:
            w, h = h, w
        if w > 0 and h > 0:
            im = im.crop((x, y, x + w, y + h))
    a = np.asarray(im)
    step = max(1, max(a.shape[:2]) // SAMPLE)
    a = a[::step, ::step].reshape(-1, 4)
    own = a[a[:, 3] >= 200][:, :3].astype(np.int16)
    if len(own) < 0.2 * len(a) or not len(own):
        return None
    col, near = _main_colour(own, np)
    if near.sum() < MIN_BODY_SHARE * len(own):
        return None
    return tuple(int(round(c)) for c in col)


def _tint(rgb, colour):
    return tuple(int(round(c * t / 255.0)) for c, t in zip(rgb, colour or (255, 255, 255)))


def state_problems(proj, original=None):
    """dark_button_state findings: button states nobody screenshots (pressed / disabled sprites, COLOR tints).
    Reads only the scenes and prefabs that contain a cc.Button and decodes only the textures those buttons name."""
    np = _np()
    root = Path(proj) / 'assets' if proj else None
    if np is None or root is None or not root.is_dir():
        return []
    original = original if original is not None else OriginalArt(proj)
    files = []
    for ext in ('*.prefab', '*.fire', '*.scene'):
        files += [f for f in root.rglob(ext) if not (set(p.lower() for p in f.relative_to(root).parts) & SKIP_DIRS)]
    wanted, buttons = set(), []
    for f in files:
        try:
            raw = f.read_bytes()
        except OSError:
            continue
        if b'cc.Button' not in raw:
            continue
        try:
            objs = json.loads(raw.decode('utf-8'))
        except ValueError:
            continue
        if not isinstance(objs, list):
            continue
        def ref(r):
            i = r.get('__id__') if isinstance(r, dict) else None
            return i if isinstance(i, int) and 0 <= i < len(objs) else None
        sprite_of = {}               # node index -> its own Sprite frame (the normal look)
        for c in objs:
            if isinstance(c, dict) and c.get('__type__') in ('cc.Sprite', 'cc.SpriteComponent') and ref(c.get('node')) is not None:
                sprite_of.setdefault(ref(c.get('node')), _uuid(c.get('_spriteFrame')))
        for o in objs:
            if not isinstance(o, dict) or o.get('__type__') != 'cc.Button':
                continue
            ni = ref(o.get('node'))
            ti = ref(_field(o, 'target'))
            ti = ni if ti is None else ti
            node = objs[ni] if ni is not None and isinstance(objs[ni], dict) else {}
            tnode = objs[ti] if ti is not None and isinstance(objs[ti], dict) else node
            normal = sprite_of.get(ti)
            row = {'file': f, 'name': str(node.get('_name') or tnode.get('_name') or '?'),
                   'transition': _field(o, 'transition'), 'interactable': _field(o, 'interactable') is not False,
                   'node_colour': _colour(tnode.get('_color')) or (255, 255, 255), 'normal': normal,
                   'pressed': _uuid(_field(o, 'pressedSprite')), 'disabled': _uuid(_field(o, 'disabledSprite')),
                   'pressed_colour': _colour(_field(o, 'pressedColor')),
                   'disabled_colour': _colour(_field(o, 'disabledColor'))}
            buttons.append(row)
            wanted |= {u for u in (row['normal'], row['pressed'], row['disabled']) if u}
    if not buttons or not wanted:
        return []
    index = frame_index(proj)['uuid']
    cache, out = {}, []

    def look(u):
        if u not in cache:
            hit = index.get(u)
            cache[u] = (_texture_body(hit[0], hit[1], hit[2], np), hit[0], hit[3]) if hit else (None, None, '')
        return cache[u]

    for b in buttons:
        rel = b['file'].relative_to(Path(proj)).as_posix()
        checks = []
        if b['transition'] == 2:                       # SPRITE: separate state pictures
            for state, u in (('pressed', b['pressed']), ('disabled', b['disabled'])):
                if u:
                    rgb, tex, name = look(u)
                    if rgb:
                        checks.append((state, _tint(rgb, b['node_colour']), tex, name))
        elif b['transition'] == 1 and b['normal']:     # COLOR: the state colour replaces the node colour
            rgb, tex, name = look(b['normal'])
            if rgb:
                pc, dc = b['pressed_colour'], b['disabled_colour']
                if pc and lstar(pc) < PRESS_TINT_L:
                    checks.append(('pressed', _tint(rgb, pc), tex, name))
                if dc and not b['interactable']:
                    checks.append(('disabled', _tint(rgb, dc), tex, name))
        for state, rgb, tex, name in checks:
            if not is_dark(rgb) or name in original:
                continue
            out.append('dark_button_state: %s button "%s" turns dark when %s (%s, RGB %d,%d,%d, L* %.0f, picture %s): '
                       'pressed and disabled states follow the same rule as the button itself (no %s; %s)'
                       % (rel, b['name'], state, family(rgb), rgb[0], rgb[1], rgb[2], lstar(rgb),
                          Path(str(tex)).name if tex else '?', DARK_LIST, SAUL))
    return out
