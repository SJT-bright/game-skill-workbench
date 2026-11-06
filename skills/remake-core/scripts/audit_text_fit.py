#!/usr/bin/env python3
"""Text fit with real glyph widths (Saul 2026-11-04, 蛋壳特工队 six screenshots: 「这些我不知道是……更新前还是更新后的
skill做的，还是没有检查出来」, 「让以后skill能自行的识别出来」, 「从源头」).

Works out where every piece of text really ends on screen -- its width from the game's own font (the TTF / BMFont in
the project, or the width ui_dump.js measured in the page) and its alignment inside the label box -- and checks it
against what it sits on. No per-project declarations: the plate under a text is found in the dump itself (its button's
picture, else the topmost picture drawn before the text that holds its centre), the plate's visible body from the
alpha of its PNG, and what lies under a full-screen popup background is left to that page's own dump.

  text_outside_plate   text sticks out of the card / button / panel it sits on      (邮件 10000 out of the coin card,
                                                                                    Quick Patrol sentence out of the panel)
  text_on_icon         text runs into an icon / badge on the same plate             (Get Free under the video icon,
                                                                                    VIP Watch on the VIP badge)
  text_on_text         two texts drawn over each other
  text_off_screen      text partly running off the screen
  text_off_band        text wider than the bar painted inside a bigger picture       (LEGENDARY REWARDS poster: DRAWS TO
                                                                                    GUARANTEE past the gold bar)
  text_cut             a CLAMP label whose text is wider than its box: the end is cut off
  words_covered        a picture with words in it (chinese-audit OCR) partly covered by an opaque picture
                                                                                   (itembg1 = "WATCH AD TO CLAIM" used as the
                                                                                    card under the hero heads)
  text_over_words      a label drawn over a picture that already has words in it (two layers of text)
  longest_does_not_fit a value from docs/art/longest-text.json does not fit (「按最长合理值排版」)
  pixel_checks_unavailable  no Python with numpy on this computer: the picture checks above could not run (简化.11.10;
                       a Python without numpy re-runs the audit in /usr/bin/python3 or another one that has it)
Hints (listed, never fail): tight_for_longer_values (same number of digits with the widest digit does not fit),
text_on_edge (text crossing the edge of a big inner box).

  python audit_text_fit.py --project GAME --dumps DIR [--out result.json] [--plan plan.md] [--longest JSON]

--plan writes the layout budget: for every text on a plate, its width, the room the plate leaves (minus icons on the
same row and side padding) and how wide the plate must be. Run it as soon as the strings are English and before the
button / plate pictures are generated, so the pictures are made at the size the text needs.
Exit codes: 0 nothing blocking, 1 blocking findings, 2 bad input.
"""
from __future__ import annotations

import argparse
import collections
import fnmatch
import json
import re
from pathlib import Path

SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles', '.tiktok-kit', 'settings'}
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp'}
FONT_EXT = {'.ttf', '.otf', '.fnt'}
SYSTEM_FONTS = ['/System/Library/Fonts/Supplemental/Arial.ttf', '/Library/Fonts/Arial.ttf',
                '/System/Library/Fonts/Helvetica.ttc', 'C:/Windows/Fonts/arial.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
LETTERS = re.compile(r'[A-Za-z]')
RICH_TAG = re.compile(r'<[^>]*>')
NUMERIC = re.compile(r'^[\s0-9.,:/x×+%-]*[0-9][\s0-9.,:/x×+%-]*$')
EFFECT_NAME = re.compile(r'light|glow|shine|flash|effect|fx|halo|spark|particle|ray|beam|twinkle|blink', re.I)
FULL_SCREEN = 0.85          # pictures covering this much of the screen are backgrounds / dim layers, never a plate
PLATE_MIN = 1.2             # a plate must be at least this much bigger than the text it holds
ICON_MAX = 6.0              # a picture up to this many times the text's area counts as an icon on the plate
OPAQUE = 160                # alpha counted as solid paint


class Box:
    __slots__ = ('x0', 'y0', 'x1', 'y1')

    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = float(x0), float(y0), float(x1), float(y1)

    @property
    def w(self):
        return max(0.0, self.x1 - self.x0)

    @property
    def h(self):
        return max(0.0, self.y1 - self.y0)

    @property
    def area(self):
        return self.w * self.h

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2

    def contains(self, x, y):
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def overlap(self, o):
        return max(0.0, min(self.x1, o.x1) - max(self.x0, o.x0)), max(0.0, min(self.y1, o.y1) - max(self.y0, o.y0))

    def inter(self, o):
        return Box(max(self.x0, o.x0), max(self.y0, o.y0), min(self.x1, o.x1), min(self.y1, o.y1))

    def as_list(self):
        return [round(self.x0, 1), round(self.y0, 1), round(self.w, 1), round(self.h, 1)]


def norm_text(s):
    return re.sub(r'\s+', ' ', RICH_TAG.sub('', str(s or ''))).strip()


def unique_words(parts):
    """OCR reads a picture on two backgrounds: 'PLAY', 'PLAY' -> 'PLAY'."""
    seen, out = set(), []
    for p in parts:
        k = re.sub(r'[^A-Z0-9]', '', p.upper())
        if k and k not in seen:
            seen.add(k)
            out.append(p.strip())
    return ' / '.join(out)


# ---------------------------------------------------------------------------------------------------------- project

class Project:
    """Fonts, pictures and OCR words of one game, looked up by the names a dump uses."""

    def __init__(self, root):
        self.root = Path(root)
        self.fonts = collections.defaultdict(list)
        self.images = collections.defaultdict(list)
        assets = self.root / 'assets'
        if assets.is_dir():
            for p in assets.rglob('*'):
                if not p.is_file() or SKIP_DIRS & {x.lower() for x in p.relative_to(self.root).parts[:-1]}:
                    continue
                ext = p.suffix.lower()
                if ext in FONT_EXT:
                    self.fonts[p.stem.lower()].append(p)
                elif ext in IMAGE_EXT:
                    self.images[p.stem.lower()].append(p)
        self._fnt, self._ttf, self._img, self._alpha = {}, {}, {}, {}
        self.words = self._ocr_words()

    def _ocr_words(self):
        """Words the chinese-audit OCR read in each picture (英化 projects): {relative file: 'WATCH AD / TO CLAIM'}."""
        out = {}
        try:
            audit = json.loads((self.root / 'docs/english/chinese-audit/audit.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return out
        for it in audit.get('items') or []:
            if not isinstance(it, dict) or it.get('kind') != 'image' or not it.get('file'):
                continue
            words = unique_words([str(x) for x in it.get('ocr_text') or [] if isinstance(x, str)])
            if len(LETTERS.findall(words)) >= 3:
                out[str(it['file']).replace('\\', '/')] = words
        return out

    def bmfont(self, name):
        if name in self._fnt:
            return self._fnt[name]
        cfg = None
        for p in self.fonts.get(name.lower(), []):
            if p.suffix.lower() != '.fnt':
                continue
            try:
                cfg = parse_fnt(p.read_text(encoding='utf-8', errors='replace'))
            except (OSError, ValueError):
                cfg = None
            if cfg:
                break
        self._fnt[name] = cfg
        return cfg

    def ttf(self, name, size, system=False):
        """(font, exact) -- exact is False when a system font stands in for the game's own."""
        key = (name, system, round(size * 4) / 4)
        if key in self._ttf:
            return self._ttf[key]
        try:
            from PIL import ImageFont
        except ImportError:
            self._ttf[key] = (None, False)
            return self._ttf[key]
        own = [] if system else [p for p in self.fonts.get(name.lower(), []) if p.suffix.lower() in ('.ttf', '.otf')]
        result = (None, False)
        for p, exact in [(p, True) for p in own] + [(Path(p), system) for p in SYSTEM_FONTS]:
            if not Path(p).is_file():
                continue
            try:
                result = (ImageFont.truetype(str(p), size=max(1.0, key[2])), exact)
                break
            except (OSError, TypeError, ValueError):
                try:
                    result = (ImageFont.truetype(str(p), size=max(1, int(round(key[2])))), exact)
                    break
                except (OSError, ValueError):
                    continue
        self._ttf[key] = result
        return result

    def picture(self, frame, frame_size):
        """(path, rgba image, part) for a sprite frame, or None. part = the part of the PNG the node shows, as
        fractions (x0, y0, x1, y1): the whole PNG, or its transparent-trimmed part when the frame is trimmed."""
        key = (str(frame).lower(), tuple(frame_size or ()))
        if key in self._img:
            return self._img[key]
        try:
            from PIL import Image
        except ImportError:
            self._img[key] = None
            return None
        best = []
        for p in self.images.get(str(frame).lower(), []):
            try:
                im = Image.open(p).convert('RGBA')
            except (OSError, ValueError):
                continue
            W, H = im.size
            bb = im.getchannel('A').getbbox() or (0, 0, W, H)
            rank, part = 1, (0.0, 0.0, 1.0, 1.0)
            if frame_size and len(frame_size) == 2:
                fw, fh = frame_size
                if abs(fw - W) <= 2 and abs(fh - H) <= 2:
                    rank = 0
                elif abs(fw - (bb[2] - bb[0])) <= 2 and abs(fh - (bb[3] - bb[1])) <= 2:
                    rank, part = 0, (bb[0] / W, bb[1] / H, bb[2] / W, bb[3] / H)
            best.append((rank, p, im, part))
        best.sort(key=lambda t: t[0])
        found = best[0][1:] if best and (best[0][0] == 0 or len(best) == 1) else None
        self._img[key] = found
        return found

    def alpha(self, pic):
        key = str(pic[0])
        if key not in self._alpha:
            try:
                import numpy as np
                self._alpha[key] = np.asarray(pic[1].getchannel('A'))
            except ImportError:
                self._alpha[key] = None
        return self._alpha[key]

    def rel(self, p):
        try:
            return Path(p).resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return str(p)


def parse_fnt(text):
    """BMFont text format -> {'size', 'line_height', 'adv': {code: xadvance}, 'kern': {(a, b): amount}}."""
    size, line_h, adv, kern, glyphs = None, None, {}, {}, {}
    for line in text.splitlines():
        tag, _, rest = line.strip().partition(' ')
        kv = dict(m.groups() for m in re.finditer(r'(\w+)=("[^"]*"|\S+)', rest))
        try:
            if tag == 'info':
                size = abs(float(kv.get('size', '0')))
            elif tag == 'common':
                line_h = float(kv.get('lineHeight', '0'))
            elif tag == 'char':
                adv[int(kv['id'])] = float(kv.get('xadvance', kv.get('width', '0')))
                glyphs[int(kv['id'])] = {'width': float(kv.get('width', kv.get('xadvance', '0'))), 'xoffset': float(kv.get('xoffset', '0'))}
            elif tag == 'kerning':
                kern[(int(kv['first']), int(kv['second']))] = float(kv.get('amount', '0'))
        except (KeyError, ValueError):
            continue
    if not adv:
        return None
    return {'size': size or line_h or 1.0, 'line_height': line_h or size or 1.0, 'adv': adv, 'kern': kern, 'glyphs': glyphs}


def bm_width(cfg, line, size, spacing):
    scale = size / (cfg['size'] or 1.0)
    w, prev = 0.0, None
    for ch in line:
        code = ord(ch)
        a = cfg['adv'].get(code)
        if a is None:
            a = cfg['adv'].get(32, cfg['size'] * 0.5) if ch == ' ' else cfg['size'] * 0.6
        w += a * scale + (cfg['kern'].get((prev, code), 0.0) * scale if prev is not None else 0.0)
        prev = code
    return w + spacing * max(0, len(line) - 1)


def bm_ink_width(cfg, line, size, spacing):
    # xadvance places the following glyph; the final advance can include a
    # transparent inter-character gap. Measure the union of actual glyph rects.
    scale = size / (cfg['size'] or 1.0)
    cursor, left, right, prev = 0.0, None, None, None
    for index, ch in enumerate(line):
        code = ord(ch)
        advance = cfg['adv'].get(code)
        if advance is None:
            advance = cfg['adv'].get(32, cfg['size'] * 0.5) if ch == ' ' else cfg['size'] * 0.6
        if prev is not None:
            cursor += cfg['kern'].get((prev, code), 0.0) * scale
        glyph = cfg.get('glyphs', {}).get(code)
        width = glyph['width'] if glyph is not None else advance
        offset = glyph.get('xoffset', 0.0) if glyph is not None else 0.0
        if width > 0:
            start, end = cursor + offset * scale, cursor + (offset + width) * scale
            left = start if left is None else min(left, start)
            right = end if right is None else max(right, end)
        cursor += advance * scale + (spacing if index + 1 < len(line) else 0.0)
        prev = code
    return max(0.0, right - left) if left is not None else 0.0


def measure(project, lab, text, size):
    """(width of the longest line in design units, exact) -- (None, False) when no font can measure it."""
    lines = text.split('\n') or ['']
    kind = lab.get('font_kind') or ''
    spacing = float(lab.get('spacingX') or 0)
    name = str(lab.get('font') or '')
    if kind == 'bitmap':
        cfg = project.bmfont(name)
        if not cfg:
            return None, False
        return max(bm_ink_width(cfg, ln, size, spacing) for ln in lines), True
    system = kind == 'system' or lab.get('system_font') is True or not name
    font, exact = project.ttf(name, size, system=system)
    if font is None:
        return None, False
    w = max(font.getlength(ln) for ln in lines)
    if lab.get('bold'):
        w *= 1.04
    ol = lab.get('outline')
    outline = float(ol.get('width') or 0) if isinstance(ol, dict) else (2.0 if ol is True else 0.0)
    return w + 2 * outline, exact


# ------------------------------------------------------------------------------------------------------------- dumps

def load_dumps(paths):
    files = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files += sorted(p.rglob('*ui-dump*.json'))
        elif p.is_file():
            files.append(p)
    out = []
    for f in files:
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(d, dict) and d.get('tool') == 'ui_dump' and not d.get('error') and d.get('nodes'):
            d['_file'] = str(f)
            out.append(d)
    return out


def canvas_size(d):
    c = d.get('canvas_css') or [0, 0, 0, 0]
    vp = d.get('viewport') or {}
    w = c[2] if len(c) > 2 and c[2] else vp.get('width') or 1
    h = c[3] if len(c) > 3 and c[3] else vp.get('height') or 1
    return float(w), float(h)


def node_box(n, W, H):
    r = n.get('screen') or n.get('rect')
    if not r or len(r) < 4:
        return None
    return Box(r[0] * W, r[1] * H, (r[0] + r[2]) * W, (r[1] + r[3]) * H)


def clipped(n):
    """True when a Mask cut the node (scroll lists): its visible part is not where the text really ends."""
    for a, b in (('unclipped_screen', 'screen'), ('unclipped_rect', 'rect')):
        u, r = n.get(a), n.get(b)
        if u and r and any(abs(x - y) > 1e-4 for x, y in zip(u, r)):
            return True
    return False


def is_ancestor(a, b):
    return b.startswith(a + '/')


def last(path):
    return path.rsplit('/', 1)[-1]


class Item:
    __slots__ = ('node', 'path', 'order', 'box', 'body', 'kind', 'text', 'pic', 'words', 'font_px', 'measured',
                 'align_known', 'button', 'tw', 'sx', 'lab')

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


def visible_body(project, n, box):
    """Opaque part of a picture (alpha >= 64), from its PNG; the node box when the PNG cannot be matched."""
    spr = (n.get('comps') or {}).get('sprite') or {}
    if spr.get('sliced') or spr.get('tiled') or (n.get('angle') or 0) % 360:
        return box, None
    pic = project.picture(spr.get('frame') or '', spr.get('frame_size'))
    if not pic:
        return box, None
    a = project.alpha(pic)
    if a is None:
        return box, pic
    H, W = a.shape[0], a.shape[1]
    part = pic[2]
    px0, py0, px1, py1 = int(part[0] * W), int(part[1] * H), int(round(part[2] * W)), int(round(part[3] * H))
    sub = a[py0:py1, px0:px1] >= 64
    if not sub.any():
        return box, pic
    import numpy as np
    ys, xs = np.nonzero(sub)
    pw, ph = max(1, px1 - px0), max(1, py1 - py0)
    return Box(box.x0 + xs.min() / pw * box.w, box.y0 + ys.min() / ph * box.h,
               box.x0 + (xs.max() + 1) / pw * box.w, box.y0 + (ys.max() + 1) / ph * box.h), pic


def opaque_share(project, item, region):
    """Share of solid paint (alpha >= 160) of item's picture inside a screen region; 1.0 when the PNG is unknown."""
    if not item.pic or region.area <= 0:
        return 1.0
    a = project.alpha(item.pic)
    if a is None:
        return 1.0
    H, W = a.shape[0], a.shape[1]
    part, box = item.pic[2], item.box
    fx0, fy0 = part[0] * W, part[1] * H
    fw, fh = (part[2] - part[0]) * W, (part[3] - part[1]) * H
    x0 = int(fx0 + (region.x0 - box.x0) / box.w * fw)
    x1 = int(round(fx0 + (region.x1 - box.x0) / box.w * fw))
    y0 = int(fy0 + (region.y0 - box.y0) / box.h * fh)
    y1 = int(round(fy0 + (region.y1 - box.y0) / box.h * fh))
    sub = a[max(0, y0):max(y0 + 1, min(H, y1)), max(0, x0):max(x0 + 1, min(W, x1))]
    return float((sub >= OPAQUE).mean()) if sub.size else 1.0


class Shot:
    """The same-frame screenshot of a dump, to confirm a text is really drawn where the dump says (labels hidden
    behind panels, game-world numbers, a page caught mid-slide) and that letters really reach into an icon."""

    def __init__(self, d):
        self.a = None
        p = Path(str(d.get('screenshot') or ''))
        if p and not p.is_absolute():
            p = Path(d['_file']).parent / p
        try:
            import numpy as np
            from PIL import Image
            if p.is_file():
                im = Image.open(p).convert('RGB')
                self.a = np.asarray(im).astype(np.int16)
        except (ImportError, OSError, ValueError):
            self.a = None
        if self.a is not None:
            c = d.get('canvas_css') or [0, 0, 0, 0]
            page = d.get('page') or {}
            pw = float(page.get('width') or (c[2] if len(c) > 2 else 0) or self.a.shape[1])
            self.k = self.a.shape[1] / pw
            self.ox, self.oy = float(c[0] if c else 0), float(c[1] if len(c) > 1 else 0)

    def share(self, box, rgb, tol=70):
        """Share of pixels in box within tol of rgb; None without a screenshot."""
        if self.a is None or not rgb or box.area <= 0:
            return None
        import numpy as np
        x0, x1 = int((self.ox + box.x0) * self.k), int(round((self.ox + box.x1) * self.k))
        y0, y1 = int((self.oy + box.y0) * self.k), int(round((self.oy + box.y1) * self.k))
        h, w = self.a.shape[0], self.a.shape[1]
        sub = self.a[max(0, y0):max(0, min(h, y1)), max(0, x0):max(0, min(w, x1))]
        if not sub.size:
            return None
        return float((np.abs(sub - np.array(rgb[:3], dtype=np.int16)).max(axis=2) <= tol).mean())


    def _px(self, box):
        x0, x1 = int((self.ox + box.x0) * self.k), int(round((self.ox + box.x1) * self.k))
        y0, y1 = int((self.oy + box.y0) * self.k), int(round((self.oy + box.y1) * self.k))
        h, w = self.a.shape[0], self.a.shape[1]
        return self.a[max(0, y0):max(0, min(h, y1)), max(0, x0):max(0, min(w, x1))]

    def stands_out(self, inner, outer):
        """True when the picture in inner looks different from the plate around it (median colour of outer)."""
        import numpy as np
        a, b = self._px(inner), self._px(outer)
        if not a.size or not b.size:
            return True
        ref = np.median(b.reshape(-1, 3), axis=0)
        return float((np.abs(a.reshape(-1, 3) - ref).max(axis=1) > 40).mean()) >= 0.10


def glyph_rgb(t):
    """Fill colour to look for in the screenshot: TTF / system labels only (bitmap digits carry their own colours)."""
    lab = t.lab or {}
    if t.kind != 'label' or lab.get('font_kind') == 'bitmap' or not lab.get('color'):
        return None
    return lab['color']


def collect(project, d):
    """Text items (labels, pictures with words) and plain pictures of one dump, above the topmost full-screen
    background: what lies under a popup's dim layer belongs to the page below and its own dump."""
    W, H = canvas_size(d)
    texts, pics = [], []
    nodes = [n for n in d['nodes'] if (n.get('opacity', 1) or 0) >= 0.05]
    buttons = [n['path'] for n in nodes if 'button' in (n.get('comps') or {})]
    floors = []
    for n in nodes:
        c = n.get('comps') or {}
        box = node_box(n, W, H)
        if box is None or box.area <= 0:
            continue
        owner = next((b for b in sorted(buttons, key=len, reverse=True) if n['path'] == b or is_ancestor(b, n['path'])), None)
        lab = c.get('label') or c.get('richtext')
        if lab and norm_text(lab.get('string')) and (n.get('angle') or 0) % 360 == 0:
            t = text_item(project, n, lab, box)
            if t:
                t.button = owner
                texts.append(t)
            continue
        spr = c.get('sprite')
        if box.area >= FULL_SCREEN * W * H:
            gfx = c.get('graphics') or {}
            fill = gfx.get('fillColor') or []
            if c.get('block_input') or (spr and (n.get('opacity', 1) or 0) * (float(spr.get('alpha', 255)) / 255.0) >= 0.2) \
                    or (len(fill) == 4 and fill[3] >= 64):
                floors.append(n.get('order', 0))    # a page background, a popup's dim layer or its touch blocker
            continue
        if not spr or (n.get('opacity', 1) or 0) * (float(spr.get('alpha', 255)) / 255.0) < 0.2:
            continue
        body, pic = visible_body(project, n, box)
        words = project.words.get(project.rel(pic[0])) if pic else None
        img_text = c.get('image_text') or {}
        if img_text.get('string') or img_text.get('desired'):
            words = words or str(img_text.get('string') or img_text.get('desired'))
        it = Item(node=n, path=n['path'], order=n.get('order', 0), box=box, body=body, kind='picture', pic=pic,
                  words=words, button=owner)
        pics.append(it)
        if words and box.area < 0.5 * W * H:
            texts.append(Item(node=n, path=n['path'], order=n.get('order', 0), box=box, body=body, kind='picture_words',
                              text=words, pic=pic, words=words, font_px=body.h, measured=True, align_known=True,
                              button=owner))
    floor = -1
    for f in sorted(floors, reverse=True):
        if any(t.order > f for t in texts):
            floor = f
            break
    return [t for t in texts if t.order > floor], [p for p in pics if p.order > floor], (W, H)


def text_item(project, n, lab, box):
    text = RICH_TAG.sub('', str(lab.get('string'))).strip('\n')
    node_w, node_h = float(lab.get('width') or 0), float(lab.get('height') or 0)
    if node_w <= 0 or node_h <= 0:
        return None
    sx, sy = box.w / node_w, box.h / node_h
    size = float(lab.get('actualFontSize') or lab.get('fontSize') or 0) or node_h * 0.8
    ov = lab.get('overflow')
    measured = True
    if lab.get('text_w') is not None:                       # measured in the page by ui_dump.js
        tw = float(lab['text_w'])
    elif ov == 0:                                           # NONE: the engine sizes the node to the text
        tw = node_w
    else:
        tw, measured = measure(project, lab, text, size)
        if tw is None:
            tw, measured = node_w, False
        elif ov in (2, 3) or (ov == 1 and lab.get('wrap')):
            if tw > 1.02 * node_w and 'wrap' not in lab and ' ' in text.strip():
                measured = False                            # older dump: maybe wrapped into lines we cannot see
            tw = min(tw, node_w)                            # SHRINK / wrapping keeps the text inside the box
    align = lab.get('h_align')
    align_known = align is not None
    if align is None:
        align = 1
    tw_px = tw * sx
    if align == 0:
        x0 = box.x0
    elif align == 2:
        x0 = box.x1 - tw_px
    else:
        x0 = box.cx - tw_px / 2
    lines = max(1, text.count('\n') + 1, int(lab.get('lines') or 0))
    line_px = float(lab.get('line_height') or size * 1.2) * sy
    th = min(box.h, max(size * sy, lines * line_px * 0.9)) if lines > 1 else min(box.h, size * sy * 1.15)
    y0 = box.cy - th / 2
    if lines > 1 and lab.get('v_align') == 0:
        y0 = box.y0
    elif lines > 1 and lab.get('v_align') == 2:
        y0 = box.y1 - th
    return Item(node=n, path=n['path'], order=n.get('order', 0), box=box, body=Box(x0, y0, x0 + tw_px, y0 + th),
                kind='label', text=text, font_px=size * sy, measured=measured, align_known=align_known, tw=tw, sx=sx,
                lab=lab)


# ------------------------------------------------------------------------------------------------------------ checks

def plate_of(t, pics, screen_area):
    """The picture a text sits on: its button's own picture, else the topmost picture drawn before it that holds the
    text's centre and is bigger than the text."""
    if t.button:
        own = [p for p in pics if (p.path == t.button or is_ancestor(t.button, p.path)) and p.order <= t.order
               and p.path != t.path and not is_ancestor(t.path, p.path) and not EFFECT_NAME.search(last(p.path))
               and p.body.contains(t.body.cx, t.body.cy) and p.body.area >= PLATE_MIN * max(1.0, t.body.area)]
        if own:
            return max(own, key=lambda p: p.body.area)
    cands = [p for p in pics if p.order < t.order and p.path != t.path and p.body.contains(t.body.cx, t.body.cy)
             and p.box.area < FULL_SCREEN * screen_area and p.body.area >= PLATE_MIN * max(1.0, t.body.area)
             and not is_ancestor(t.path, p.path) and near(t.path, p.path)]
    return max(cands, key=lambda p: p.order) if cands else None


def near(text_path, pic_path):
    """The picture belongs to the text's own widget: an ancestor of it, or at most two levels below a common
    ancestor that is at most four levels above the text (a card and its count label, a poster and its caption).
    A monster on the map under a floating damage number is not the number's plate."""
    if is_ancestor(pic_path, text_path):
        return True
    a, b = text_path.split('/'), pic_path.split('/')
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    return len(a) - k <= 4 and len(b) - k <= 2


def margin(t):
    return max(2.0, 0.03 * t.body.w)



def available_row_budget(plate, text, icons, pad, alignment=1):
    """Clip icons to the padded plate, merge overlap, and use this label's gap.
    Existing actual overlap/off-plate checks retain their original tolerances.
    """
    start, end = plate.x0 + pad, plate.x1 - pad
    occupied = []
    for icon in icons:
        left, right = max(start, icon.body.x0), min(end, icon.body.x1)
        if right > left:
            occupied.append((left, right))
    merged = []
    for left, right in sorted(occupied):
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(right, merged[-1][1]))
        else:
            merged.append((left, right))
    free = []
    cursor = start
    for left, right in merged:
        if left > cursor:
            free.append((cursor, left))
        cursor = max(cursor, right)
    if cursor < end:
        free.append((cursor, end))
    component = next(((left, right) for left, right in free if left <= text.cx <= right), None)
    room = 0.0
    if component:
        if alignment == 0:
            room = max(0.0, component[1] - max(component[0], text.x0))
        elif alignment == 2:
            room = max(0.0, min(component[1], text.x1) - component[0])
        else:
            room = max(0.0, 2 * min(text.cx - component[0], component[1] - text.cx))
    return room, sum(right-left for left, right in merged), component, merged


def observed_longest_shrink(t, lab, longest_text):
    """An already rendered longest string is actual evidence, not a projection.
    Its ink still passes all ordinary on-screen/plate/icon/text assertions above.
    Only SHRINK with a reported real font size and measured exact string qualifies.
    """
    actual, declared = lab.get('actualFontSize'), lab.get('fontSize')
    return (lab.get('overflow') == 2 and t.measured
            and type(actual) in (int, float) and type(declared) in (int, float)
            and 0 < actual <= declared and str(longest_text) == t.text)

def band_of(plate, t):
    """The bar painted inside the plate's picture under the text, as a screen Box, or None when the text does not
    sit on a plain bar (open panel, busy art, the bar is most of the picture)."""
    if not plate.pic:
        return None
    try:
        import numpy as np
    except ImportError:
        return None
    _, im, part = plate.pic
    W, H = im.size
    crop = im.crop((int(part[0] * W), int(part[1] * H), int(round(part[2] * W)), int(round(part[3] * H))))
    scale = min(1.0, 420.0 / max(1, crop.size[0]))
    if scale < 1.0:
        crop = crop.resize((max(1, int(crop.size[0] * scale)), max(1, int(crop.size[1] * scale))))
    a = np.asarray(crop).astype(np.int16)
    ih, iw = a.shape[0], a.shape[1]
    box = plate.box

    def to_img(x, y):
        return int((x - box.x0) / box.w * iw), int((y - box.y0) / box.h * ih)

    tx0, ty0 = to_img(t.body.x0, t.body.y0)
    tx1, ty1 = to_img(t.body.x1, t.body.y1)
    th, tw = max(1, ty1 - ty0), max(1, tx1 - tx0)
    # Only the neighbourhood of the text matters: a bar reaching the window's left/right edge is wide enough,
    # one reaching its top/bottom is no bar. Keeps the flood fill small (FruitScrape: 54 s -> about 1 s).
    wx0, wx1 = max(0, tx0 - int(0.6 * tw) - 2), min(iw, tx1 + int(0.6 * tw) + 2)
    cy = (ty0 + ty1) // 2
    wy0, wy1 = max(0, cy - 2 * th - 2), min(ih, cy + 2 * th + 2)
    win = a[wy0:wy1, wx0:wx1]
    if win.size == 0:
        return None
    seeds = [to_img(t.body.x0 + f * t.body.w, t.body.cy) for f in (0.45, 0.5, 0.55)]
    seeds = [(x - wx0, y - wy0) for x, y in seeds if wx0 <= x < wx1 and wy0 <= y < wy1]
    if len(seeds) < 2:
        return None
    comps = []
    for sx, sy in seeds:
        seed = win[sy, sx]
        if seed[3] < 128:
            return None
        mask = (np.abs(win[:, :, :3] - seed[:3]).max(axis=2) <= 54) & (win[:, :, 3] >= 128)
        comps.append(component(mask, sx, sy))
    if any(c is None for c in comps):
        return None
    x0, y0, x1, y1, n, sel = comps[0]
    if any(abs(c[0] - x0) > 2 or abs(c[2] - x1) > 2 for c in comps[1:]):
        return None
    hh, ww = win.shape[0], win.shape[1]
    if x0 == 0 or x1 == ww - 1 or (y0 == 0 and wy0 > 0) or (y1 == hh - 1 and wy1 < ih):
        return None
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    if not (bw >= 1.5 * bh and bh >= 0.5 * th and bw >= 0.5 * tw and n >= 0.5 * bw * bh and bw * bh <= 0.5 * iw * ih):
        return None
    x0, x1, y0, y1 = x0 + wx0, x1 + wx0, y0 + wy0, y1 + wy0
    colours = win[:, :, :3][sel]
    if colours.size and float(colours.std(axis=0).max()) > 28:
        return None                                         # not a plain bar: patterned art
    return Box(box.x0 + x0 / iw * box.w, box.y0 + y0 / ih * box.h, box.x0 + (x1 + 1) / iw * box.w,
               box.y0 + (y1 + 1) / ih * box.h)


def component(mask, sx, sy):
    """Bounding box, size and member mask of the 4-connected region of mask holding (sx, sy)."""
    import numpy as np
    if not mask[sy, sx]:
        return None
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    stack = [(sx, sy)]
    seen[sy, sx] = True
    n = 0
    while stack:
        x, y = stack.pop()
        n += 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx] and mask[ny, nx]:
                seen[ny, nx] = True
                stack.append((nx, ny))
    ys, xs = np.nonzero(seen)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()), n, seen


def widest_variant(text, project, lab):
    if not NUMERIC.match(text) or lab is None:
        return None
    size = float(lab.get('actualFontSize') or lab.get('fontSize') or 0) or 10
    best, best_w = None, -1.0
    for dgt in '0123456789':
        w, _ = measure(project, lab, dgt, size)
        if w is not None and w > best_w:
            best, best_w = dgt, w
    if best is None:
        return None
    v = re.sub('[0-9]', best, text)
    return v if v != text else None


def load_longest(project, path):
    p = Path(path) if path else Path(project.root) / 'docs/art/longest-text.json'
    try:
        data = json.loads(p.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return []
    rows = data.get('labels') if isinstance(data, dict) else data
    return [r for r in rows or [] if isinstance(r, dict) and r.get('path') and r.get('text')]


def hidden(project, t, pics):
    """A text wholly under an opaque picture drawn after it is not on screen at all (a panel over a placeholder)."""
    for p in pics:
        if p.order <= t.order or is_ancestor(t.path, p.path):
            continue
        region = t.body.inter(p.body)
        if region.area >= 0.8 * max(1.0, t.body.area) and opaque_share(project, p, region) >= 0.6:
            return True
    return False


def is_icon(p, t, plate, project):
    if p is plate or p.path == t.path or p.body.area <= 0 or is_ancestor(p.path, t.path) or is_ancestor(t.path, p.path):
        return False
    if EFFECT_NAME.search(last(p.path)) or EFFECT_NAME.search(str(((p.node.get('comps') or {}).get('sprite') or {}).get('frame') or '')):
        return False
    if plate and p.order < plate.order:
        return False                                        # under the plate: hidden by it
    return True


def audit_dump(project, d, longest):
    texts, pics, (W, H) = collect(project, d)
    screen_area = W * H
    shot = Shot(d)
    seen = []
    for t in texts:                 # drop labels whose letters are not on the screenshot where the dump puts them
        s = shot.share(t.body, glyph_rgb(t)) if glyph_rgb(t) else None
        if s is not None and s < 0.03:
            continue
        seen.append(t)
    texts = seen
    page = d.get('screen') or Path(d['_file']).stem
    gameplay = d.get('kind') == 'gameplay'
    found, hints, budget = [], [], []
    vp = list(canvas_size(d))

    def add(kind, t, msg, **extra):
        rec = {'kind': kind, 'page': page, 'path': t.path, 'text': (t.text or '')[:60], 'message': msg,
               'viewport': vp, 'file': d['_file']}
        rec.update(extra)
        found.append(rec)

    def hint(kind, t, msg):
        hints.append({'kind': kind, 'page': page, 'path': t.path, 'text': (t.text or '')[:60], 'message': msg,
                      'viewport': vp})

    for t in texts:
        if clipped(t.node) or hidden(project, t, pics):
            continue
        m = margin(t)
        plate = plate_of(t, pics, screen_area)
        if plate and gameplay and not t.button:
            plate = None                    # in a level only HUD buttons are plates; the rest is the game world
        what = '"%s"' % (t.text or '').replace('\n', ' ')[:30]
        where = '按钮' if t.button else '底板'
        # 1. off the plate (labels: we know where their glyphs end; word pictures end where their paint ends)
        if plate and t.measured and t.kind == 'label':
            left, right = plate.body.x0 - t.body.x0, t.body.x1 - plate.body.x1
            own = is_ancestor(plate.path, t.path) or plate.path.rsplit('/', 1)[0] == t.path.rsplit('/', 1)[0] or \
                bool(t.button and (plate.path == t.button or is_ancestor(t.button, plate.path)))
            if max(left, right) > m and not own and plate.body.area <= ICON_MAX * t.body.area:
                # not the text's own card or button but a badge / icon next to it, and the text runs half over it
                add('text_on_icon', t, '%s 压在 %s 上，还伸出它 %.0fpx：字和图标各自留位，按「图标宽＋间距＋字宽＋两侧留白」排' % (
                    what, last(plate.path), max(left, right)), picture=plate.path, over_px=round(max(left, right), 1))
            elif max(left, right) > m:
                add('text_outside_plate', t, '%s 超出它所在的%s %s 的%s %.0fpx（字宽 %.0fpx，%s可见宽 %.0fpx）' % (
                    what, where, last(plate.path), '左边' if left >= right else '右边', max(left, right), t.body.w,
                    where, plate.body.w), plate=plate.path, over_px=round(max(left, right), 1),
                    align_guessed=not t.align_known)
            elif t.button:
                up, down = plate.body.y0 - t.body.y0, t.body.y1 - plate.body.y1
                if max(up, down) > 0.5 * t.body.h:
                    add('text_outside_plate', t, '%s 一半以上跑出按钮 %s 的%s' % (what, last(plate.path),
                                                                              '上边' if up > down else '下边'),
                        plate=plate.path, over_px=round(max(up, down), 1))
        # 2. into an icon on the same plate (word pictures: their paint is the whole button, the letters are only part
        #    of it -- icons over them are words_covered)
        if not gameplay and t.measured and t.kind == 'label':
            for p in pics:
                if not is_icon(p, t, plate, project):
                    continue
                ox, oy = t.body.overlap(p.body)
                if ox < max(4.0, 0.08 * t.body.w) or oy < 0.4 * t.body.h:
                    continue                                    # a thin bar under the digits is not an icon in them
                region = t.body.inter(p.body)
                if opaque_share(project, p, region) < 0.3:
                    continue                                    # glow / soft shadow, not a solid icon
                if plate and p.body.area >= plate.body.area:
                    continue
                if p.body.area >= PLATE_MIN * t.body.area and p.body.contains(t.body.x0 + 1, t.body.cy) and \
                        p.body.contains(t.body.x1 - 1, t.body.cy):
                    continue                                    # another plate the whole text sits on
                if p.body.area > ICON_MAX * t.body.area:
                    if not p.body.contains(t.body.cx, t.body.cy):
                        hint('text_on_edge', t, '%s 跨在 %s 的边上（重叠 %.0f×%.0fpx）' % (what, last(p.path), ox, oy))
                    continue
                if plate and shot.a is not None and not shot.stands_out(p.body, plate.body):
                    continue                                    # the picture does not show on its plate (white on white)
                letters = shot.share(region, glyph_rgb(t)) if glyph_rgb(t) else None
                msg = '%s 压到了 %s（重叠 %.0f×%.0fpx）：字和图标各自留位，按「图标宽＋间距＋字宽＋两侧留白」排' % (
                    what, last(p.path), ox, oy)
                if letters is not None and letters < 0.06:
                    continue                                    # the box overlaps, the letters do not
                if letters is None and shot.a is not None and glyph_rgb(t) is None:
                    hint('text_on_icon', t, msg + '（位图字，截图上没法按颜色确认，看图）')
                    continue
                add('text_on_icon', t, msg, picture=p.path, overlap_px=[round(ox, 1), round(oy, 1)])
                break
        # 3. partly off the screen (wholly outside = a scrolled-away page, not shown)
        inside = Box(0, 0, W, H)
        ox, oy = t.body.overlap(inside)
        ui_text = plate is not None or t.button is not None or len((t.text or '').split()) >= 2
        if t.kind == 'label' and ui_text and ox * oy > 0 and \
                (t.body.x0 < -2 or t.body.x1 > W + 2 or t.body.y0 < -2 or t.body.y1 > H + 2):
            add('text_off_screen', t, '%s 跑出屏幕 %.0fpx' % (what, max(-t.body.x0, t.body.x1 - W, -t.body.y0, t.body.y1 - H)))
        # 4. past the bar painted in the plate
        if plate and t.body.w >= 40 and plate.box.area >= 8 * t.body.area and not (t.kind == 'picture_words' and t.button):
            band = band_of(plate, t)
            if band:
                left, right = band.x0 - t.body.x0, t.body.x1 - band.x1
                if max(left, right) > max(4.0, 0.05 * t.body.w):
                    add('text_off_band', t, '%s 比 %s 图里画好的色条宽，%s超出 %.0fpx（色条宽 %.0fpx，字宽 %.0fpx）：放字前先量色条内宽' % (
                        what, last(plate.path), '左边' if left >= right else '右边', max(left, right), band.w, t.body.w),
                        plate=plate.path, band=band.as_list(), over_px=round(max(left, right), 1))
        # 5. CLAMP cuts the end off
        lab = t.lab
        if lab and lab.get('overflow') == 1 and lab.get('wrap') is False and lab.get('text_w') is None:
            tw, exact = measure(project, lab, t.text, float(lab.get('actualFontSize') or lab.get('fontSize') or 0))
            if tw is not None and exact and tw > 1.03 * float(lab.get('width') or 0) + 2:
                add('text_cut', t, '%s 比框宽 %.0f%%，CLAMP 把字尾裁掉了' % (what, 100 * (tw / float(lab['width']) - 1)))
        # layout budget, longest values
        if plate and t.kind == 'label' and plate.body.area > t.body.area:
            row = Box(plate.body.x0, t.body.y0, plate.body.x1, t.body.y1)
            row_icons = [p for p in pics if is_icon(p, t, plate, project) and p.body.area < plate.body.area
                         and p.body.overlap(row)[1] >= 0.35 * t.body.h and p.body.overlap(plate.body)[0] > 0
                         and p.body.area <= ICON_MAX * t.body.area]
            pad = max(4.0, 0.06 * plate.body.w)
            room, icons_w, available_interval, occupied_intervals = available_row_budget(plate.body, t.body, row_icons, pad, (lab or {}).get('h_align', 1))
            gaps = 0.0  # Actual component endpoints already preserve the observed icon separation.
            budget.append({'page': page, 'path': t.path, 'text': t.text[:40], 'font_px': round(t.font_px or 0, 1),
                           'text_px': round(t.body.w, 1), 'plate': plate.path, 'plate_px': round(plate.body.w, 1),
                           'icons_px': round(icons_w, 1), 'room_px': round(room, 1), 'spare_px': round(room - t.body.w, 1),
                           'need_plate_px': round(t.body.w + icons_w + 2 * pad + gaps, 1), 'available_interval': available_interval, 'occupied_intervals': occupied_intervals, 'viewport': vp})
            for rowl in longest:
                if fnmatch.fnmatch(t.path, rowl['path']) and lab:
                    if observed_longest_shrink(t, lab, rowl['text']):
                        budget[-1].setdefault('observed_longest', []).append({
                            'text': rowl['text'], 'actual_font_size': lab['actualFontSize'],
                            'ink_width_px': round(t.body.w, 3),
                            'validation': 'actual ink/plate/icon/screen assertions, not hypothetical declared-font projection'})
                        continue
                    tw, _ = measure(project, lab, str(rowl['text']), float(lab.get('fontSize') or 0))
                    if tw is not None:
                        need = tw * (t.sx or 1)
                        if need > room + m:
                            add('longest_does_not_fit', t, '最长值 "%s" 要 %.0fpx，%s 只留得出 %.0fpx（%s）' % (
                                rowl['text'], need, last(plate.path), room, rowl.get('why') or 'longest-text.json'),
                                plate=plate.path, need_px=round(need, 1), room_px=round(room, 1))
            v = widest_variant(t.text, project, lab)
            if v:
                tw, _ = measure(project, lab, v, float(lab.get('actualFontSize') or lab.get('fontSize') or 0))
                if tw is not None and tw * (t.sx or 1) > room + m >= t.body.w:
                    hint('tight_for_longer_values', t, '"%s" 放得下，同样位数的 "%s" 放不下（要 %.0fpx，留 %.0fpx）：数量槽按最长合理值留' % (
                        t.text, v, tw * (t.sx or 1), room))
    # 6. text over text
    if not gameplay:
        flat = [t for t in texts if not clipped(t.node) and t.measured
                and not (t.kind == 'picture_words' and EFFECT_NAME.search(last(t.path)))]
        pairs = []
        for i, a in enumerate(flat):
            for b in flat[i + 1:]:
                if a.path == b.path or is_ancestor(a.path, b.path) or is_ancestor(b.path, a.path):
                    continue
                if not (near(a.path, b.path) or near(b.path, a.path)):
                    continue                                    # one of them belongs to another widget / the world
                if 'picture_words' in (a.kind, b.kind) and 'label' in (a.kind, b.kind):
                    continue                                    # text_over_words below
                if a.kind == b.kind == 'picture_words' and (a.words == b.words or a.body.contains(b.body.cx, b.body.cy)
                                                             or b.body.contains(a.body.cx, a.body.cy)):
                    continue                                    # layers of one word picture (art + glow copy)
                ox, oy = a.body.overlap(b.body)
                if ox >= 3 and oy >= 0.35 * min(a.body.h, b.body.h):
                    region = a.body.inter(b.body)
                    seen_l = [s for s in (shot.share(region, glyph_rgb(x)) for x in (a, b) if glyph_rgb(x)) if s is not None]
                    if seen_l and max(seen_l) < 0.06:
                        continue                                # boxes touch, letters do not
                    pairs.append((a, b, ox, oy))
        # A dump taken before cc.Layout ran shows a row of sibling labels piled on each other while the screenshot
        # shows them side by side (VIP「Watch 1 times to reach VIP2」, 11-04). Old ui_dump.js had no settle step.
        rows = collections.Counter(a.path.rsplit('/', 1)[0] for a, b, _, _ in pairs
                                   if a.kind == b.kind == 'label' and a.path.rsplit('/', 1)[0] == b.path.rsplit('/', 1)[0])
        unsettled = {p for p, k in rows.items() if k >= 2} if not d.get('settle') else set()
        for parent in sorted(unsettled):
            first = next(a for a, b, _, _ in pairs if a.path.rsplit('/', 1)[0] == parent)
            add('unsettled_dump', first, '%s 下面一行字在 dump 里互相压着，截图上却排开了：这份 dump 是排版（Layout）还没跑完时采的，'
                '节点位置不可信。用新版 ui_dump.js（会先让 Layout、Label、Widget 排完再读）重新采这一页' % last(parent))
        for a, b, ox, oy in pairs:
            if a.path.rsplit('/', 1)[0] in unsettled and a.path.rsplit('/', 1)[0] == b.path.rsplit('/', 1)[0]:
                continue
            add('text_on_text', a, '"%s" 和 "%s" 叠在一起（重叠 %.0f×%.0fpx）' % (
                (a.text or '')[:20], (b.text or '')[:20], ox, oy), other=b.path)
    # 7. pictures with words, partly covered by opaque pictures; labels written over them
    for w in [t for t in texts if t.kind == 'picture_words' and not clipped(t.node) and not EFFECT_NAME.search(last(t.path))]:
        for p in pics:
            if p.path == w.path or p.order <= w.order or is_ancestor(w.path, p.path):
                continue
            if EFFECT_NAME.search(last(p.path)):
                continue
            region = w.body.inter(p.body)
            share = region.area / max(1.0, w.body.area)
            # the words sit in the middle of their picture: a cover over the centre, or over a third of it, hides
            # some of them; a panel edge over the bottom rim of a big word picture does not
            if (p.body.contains(w.body.cx, w.body.cy) or share >= 0.35) and 0.15 <= share < 0.95 and \
                    opaque_share(project, p, region) >= 0.5:
                add('words_covered', w, '图 %s 上画着 "%s"，被 %s 盖住 %.0f%%，没盖住的字露在外面：这里要用无字的底图' % (
                    last(w.path), (w.words or '')[:40], last(p.path), 100 * share), picture=p.path)
                break
        core = Box(w.body.x0 + 0.2 * w.body.w, w.body.y0 + 0.2 * w.body.h, w.body.x1 - 0.2 * w.body.w, w.body.y1 - 0.2 * w.body.h)
        for t in texts:
            if t.kind != 'label' or t.order <= w.order or clipped(t.node):
                continue
            ox, oy = t.body.overlap(core)          # a count on the rim of an item icon is not over its words
            if ox * oy >= 0.25 * max(1.0, t.body.area):
                add('text_over_words', t, '"%s" 写在已经画着字的图 %s（"%s"）上面：两层字叠在一起' % (
                    (t.text or '')[:24], last(w.path), (w.words or '')[:30]), picture=w.path)
    return found, hints, budget


_NUMPY_PYTHON = []


def numpy_python():
    """简化.11.10: the bar / alpha / screenshot checks need numpy + Pillow. Without numpy they returned nothing and the
    audit passed (Homebrew's python3 has no numpy: the gold-bar case of the six screenshots then went unreported).
    None when this Python has both; else a Python that has them (macOS /usr/bin/python3, as art_check.py does);
    '' when no Python here has them."""
    if _NUMPY_PYTHON:
        return _NUMPY_PYTHON[0]
    import importlib.util
    import os
    import shutil
    import subprocess
    import sys
    found = None
    if not (importlib.util.find_spec('numpy') and importlib.util.find_spec('PIL')):
        found = ''
        here = os.path.realpath(sys.executable)
        if not os.environ.get('AUDIT_TEXT_FIT_CHILD'):
            for cand in ('/usr/bin/python3', shutil.which('python3'), '/usr/local/bin/python3', '/opt/homebrew/bin/python3'):
                if not cand or not os.path.exists(cand) or os.path.realpath(cand) == here:
                    continue
                try:
                    ok = subprocess.run([cand, '-c', 'import numpy, PIL'], capture_output=True, timeout=60).returncode == 0
                except (OSError, subprocess.SubprocessError):
                    ok = False
                if ok:
                    found = cand
                    break
    _NUMPY_PYTHON.append(found)
    return found


def audit(project_root, dumps, longest_path=None):
    """Run the audit with numpy: in this Python when it has numpy, else in one that has it. With no such Python the
    result never passes (pixel_checks_unavailable) instead of passing on the checks that could run."""
    other = numpy_python()
    if other:
        import os
        import subprocess
        args = json.dumps([str(project_root), [str(d) for d in dumps], str(longest_path) if longest_path else None])
        r = subprocess.run([other, '-B', str(Path(__file__).resolve()), '--numpy-child'], input=args, text=True,
                           capture_output=True, timeout=3600, env=dict(os.environ, AUDIT_TEXT_FIT_CHILD='1'))
        if r.returncode != 0:
            raise RuntimeError('audit_text_fit under %s failed: %s' % (other, (r.stderr or '').strip()[-400:]))
        return json.loads(r.stdout)
    result = _audit(project_root, dumps, longest_path)
    if other == '':
        result['findings'].append({'kind': 'pixel_checks_unavailable', 'page': '-', 'path': '', 'text': '',
                                   'viewport': [0, 0], 'file': '',
                                   'message': '这台电脑没有带 numpy 的 Python：图里画好的色条、图片实际可见范围和截图核对都没量，'
                                              '不能算通过（macOS 用 /usr/bin/python3，或 pip install numpy）'})
        result['passed'] = False
    return result


def _audit(project_root, dumps, longest_path=None):
    project = Project(project_root)
    longest = load_longest(project, longest_path)
    found, hints, budget, pages = [], [], [], 0
    for d in load_dumps(dumps):
        pages += 1
        f, h, b = audit_dump(project, d, longest)
        found += f
        hints += h
        budget += b
    merged = collections.OrderedDict()        # the same mistake at two phone sizes is one fix
    for f in found:
        key = (f['kind'], re.sub(r'\[\d+\]', '', f['path']), f['text'])
        if key in merged:
            merged[key].setdefault('also', []).append('%s@%dx%d' % (f['page'], *f['viewport']))
        else:
            merged[key] = f
    return {'tool': 'audit_text_fit', 'schema': 1, 'pages': pages, 'passed': not merged,
            'findings': list(merged.values()), 'hints': hints, 'budget': budget,
            'fonts_found': sorted(project.fonts), 'ocr_pictures': len(project.words)}


def plan_markdown(result):
    rows = sorted(result['budget'], key=lambda r: r['spare_px'])
    out = ['# 排版预算（audit_text_fit --plan）', '',
           '每行是一段字：它在底板/按钮上占多宽；底板减去同一行的图标、间距和两边留白后还剩多宽。余量是负数的，生图前就把底板/按钮做到「底板至少要」那么宽，'
           '或者换行、缩短英文（字号不低于可读下限）。数字按 docs/art/longest-text.json 里的最长值排。', '',
           '| 页面 | 节点 | 字 | 字号px | 字宽px | 底板可见宽 | 图标 | 可用宽 | 余量 | 底板至少要 |', '|---|---|---|---|---|---|---|---|---|---|']
    for r in rows[:300]:
        out.append('| %s@%dx%d | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            r['page'], r['viewport'][0], r['viewport'][1], '/'.join(r['path'].split('/')[-2:]),
            r['text'].replace('|', '/').replace('\n', ' '), r['font_px'], r['text_px'], r['plate_px'], r['icons_px'],
            r['room_px'], r['spare_px'], r['need_plate_px']))
    return '\n'.join(out) + '\n'


def main(argv=None):
    import sys
    if (argv if argv is not None else sys.argv[1:]) == ['--numpy-child']:     # audit() running itself under numpy
        root, dumps, longest = json.loads(sys.stdin.read())
        print(json.dumps(_audit(root, dumps, longest), ensure_ascii=False))
        return 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--dumps', nargs='+', required=True)
    ap.add_argument('--longest', type=Path, help='longest values to lay out for (default <project>/docs/art/longest-text.json)')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--plan', type=Path, help='write the layout budget table (markdown)')
    a = ap.parse_args(argv)
    if not (a.project / 'assets').is_dir():
        print(json.dumps({'error': 'not a Cocos project: %s' % a.project}, ensure_ascii=False))
        return 2
    result = audit(a.project, a.dumps, a.longest)
    if not result['pages']:
        print(json.dumps({'error': 'no ui_dump files under %s' % ' '.join(a.dumps)}, ensure_ascii=False))
        return 2
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if a.plan:
        a.plan.parent.mkdir(parents=True, exist_ok=True)
        a.plan.write_text(plan_markdown(result), encoding='utf-8')
    print(json.dumps({'tool': 'audit_text_fit', 'pages': result['pages'], 'passed': result['passed'],
                      'found': [{'kind': f['kind'], 'text': f['text'], 'message': f['message'], 'page': f['page']}
                                for f in result['findings'][:40]], 'hints': len(result['hints'])},
                     ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
