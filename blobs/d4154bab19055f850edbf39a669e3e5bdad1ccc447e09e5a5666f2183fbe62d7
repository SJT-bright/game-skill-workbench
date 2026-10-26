#!/usr/bin/env python3
"""Monotonous-page and flat-background check (PAGE-01, both boards; user 2026-10-21 negative examples: a flat blue
result page with only "NEXT LEVEL", a light-blue result page and a light-blue gameplay sky with nothing on them, a
home page whose PLAY is bare text and whose icon labels use the system font, a "Weekly Rankings" popup that is one
big blank panel). Reads chrome_touch dump_ui dumps of the running game and the screenshot taken with each dump;
nothing typed by hand.

Every dump, gameplay included (from its screenshot, same measure as audit_dark_area.py):
  flat_background one plain colour covers more than 40% of the screen, or one connected plain block more than 35%
                  (the background must be a picture: gradient + clouds/pattern/scenery at least, even if simple)
  no_screenshot   the screenshot next to the dump is missing
  busy_background PERMANENT BAN (user 2026-10-23, both boards, the Metro Switch home): a background with too much detail
                  (a painted city / plaza full of small things) that swallows the title and the buttons. Measured on the
                  screenshot outside every UI node (188 px wide, luminance steps > 20): more than 30% of the background
                  pixels are edges. Backgrounds are calm - big soft shapes, gradients, a few clouds or blurred scenery -
                  so the title logo and the buttons stand out (masked popups are skipped)
Every non-gameplay dump:
  monotonous      fewer than 5 visible things, or they cover less than 25% of the screen
  plain_backdrop  no full-screen picture and no game scene behind (a flat colour / tinted default sprite)
  bare_button     a button with text but no plate picture
  system_font     any visible text drawn in the system default font (use the game font)
  empty_panel     a popup/page panel whose inside is less than 30% filled
  dev_text        developer wording on screen ("LOCAL PREVIEW", "PROTOTYPE", "TEST AD" ...)
Text on every dump, gameplay HUD included (user 2026-10-22: thin system-font words dropped on generated art, white
RETRY on cream, navy PLAY on a navy button, "Coins 0 Springs 1" on a busy picture):
  low_contrast    text colour vs what is behind it in the screenshot (WCAG ratio): >= 4.5 below 24 px on the phone,
                  >= 3 from 24 px; an outline (>= 2 px) that stands out from the background (>= 3) also counts
  small_text      text smaller than 11 px on the simulated phone
  plain_text      any text without outline, shadow or bold (thin font text): design it. Exception (user 2026-10-23): dense
                  text over 40 characters (announcements, notices, gameplay rules / how to play) may be a thinner font
  font_text       fixed words drawn with a font (titles, buttons, labels, item and mission names, "COINS 47",
                  "Price · 250 coins"): picture text generated with GPT in the game style, frame txt_<words>; text that
                  really changes at run time is listed in docs/text/runtime-text.json          (user 2026-10-22)
  dark_green_text dark green / teal / slate text of any size                                     (user 2026-10-22)
ALL TEXT IS GENERATED PICTURE TEXT, IN ONE PIECE WITH THE ART (user 2026-10-23, both boards, strongly emphasised; good
example: "THE COLLECTION" page - every word, the COMMON/RARE/EPIC/SECRET tabs, "VIDEO +50", "USE CLASSIC KIT" baked into
the pictures; bad example: the "Scissors Master" home - typed dark title and subtitle, flat PLAY with typed text, flat
LEVELS/SKINS/Add to Home/Revisit tiles, typed numbers 0/9 and 0):
  spliced_button  a word (font label or txt_ picture text) laid over a button plate: the whole button is ONE generated
                  picture with its stylized word (frame btn_<words>, e.g. btn_play, btn_video_plus_50; icon captions baked
                  into the icon picture); finite states get their own whole pictures (btn_claim / btn_claimed)
  font_number     a number (coins, energy, level, score, price, timer, percent: "0", "0/9", "+50", "70%") drawn with a TTF or
                  system font: generate the digit pictures in the game style and use them as a BitmapFont (.fnt) / LabelAtlas
                  (dump_ui records label font_kind: bitmap / ttf / system); colours of bitmap digits are measured on pixels
  typed_title     on home, the game title or subtitle typed with a font (a label in the top part >= 40% wide or >= 36 px), or
                  picture text laid over the title plate: the title is ONE stylized logo picture generated in the game style
  dark_bold_text  PERMANENT BAN (user 2026-10-23, both boards, every page, gameplay HUD included): dark bold / heavy text
                  of ANY hue (teal, slate, navy, brown, grey, black, dark red ...): a label whose colour is darker than L* 50
                  and is bold, outlined, shadowed or >= 16 px on the phone (examples: dark-teal "COINS 785 / LEVEL 1" over
                  the sky, dark-teal "HOME SCREEN OPEN / MISSIONS 2/3 RESOLVED" on a cream panel). Text fill is white,
                  cream, light yellow or a light saturated theme colour, with a darker outline/shadow
  dark_picture_text the same ban measured on the screenshot pixels (picture text txt_*, numbers, labels): inside the text
                  box, the glyph pixels (different from what is behind) are mostly dark (L* < 45) and almost none light
  squashed_text   a word picture (txt_/btn_/logo/title/words ...) drawn with a changed aspect ratio (> 10%; dump_ui records
                  frame_size and display_size; user 2026-10-23: DETAILS 570x345 forced into 234x49 = 2.89x): crop each word
                  to its own SpriteFrame and scale it uniformly; squashed_picture: the same for other pictures (bars,
                  glows, backgrounds may stretch)
  low_res         ART-04 at run time (user 2026-10-23: the final review found 22 frames below 2x their node size after the user
                  had approved the art): a simple sprite whose picture (frame_size) is smaller than 2x the size it is drawn at
                  (display_size; backgrounds and full-screen pictures 1.5x), so it looks soft on phone screens. Same check in
                  every art round as in the final review; regenerate / re-crop at >= 2x. Original untouched frames of a
                  localized game may be listed in docs/art/clarity-exempt.json {"frames": [{"frame": "<glob>", "why": "..."}]}
  canvas_text     a sprite drawn at run time on a Canvas (fillText); setup canvas_font_code: fillText/strokeText in the
                  project scripts (allowed only for files in runtime-text.json "canvas_text_files" with a why)
  uniform_text_colour >= 3 text items on a page (same node name = one item) all in one colour family (label colour, or
                  the light glyph pixels on the screenshot): titles, buttons, numbers and labels differ in colour
                  (user 2026-10-23: the all-teal Hazel's Shelf Scramble home, the all-orange "Your Progress" popup)
  overlap (穿模, user 2026-10-23: energy "20" on the lightning icon, coin pile hanging off WATCH AD, "WATCH AD · DOUBLE
  COINS" as a caption): overlap_text_picture (text over an icon/picture, >= 15% of the text box), overlap_text,
  overlap_buttons (>= 10%), clip_out (a picture sticking out of its button/capsule by > 35% of its size), text_outside
  for capsules, action_caption (the main action words as a small caption under a button instead of on the button);
  cards count as holders too (a day-7 car sticking out of its card, user 2026-10-23)
  glyph_overlap / double_number / negative_spacing / font_advance (user 2026-10-23 Daily Rewards: "100" printed as "10"
                  over "100"): digit pictures covering each other, a number printed twice, spacingX < 0, a .fnt glyph wider
                  than its xadvance. Fixed numbers are generated with their plate/icon as one picture; changing numbers
                  use one bitmap-font Label
  checker_fill    the fake-transparency checkerboard of an image generator baked into the art (screenshot pixels)
  mixed_caption_style  a group of feature/icon buttons (similar size, next to each other) whose captions are made in
                  different ways: baked into the icon picture / separate picture text / font label / a caption plate
                  (+ font or picture text), different caption plates, or picture captions in different colours. One
                  group = one caption style (user 2026-10-23: LEVELS on a white ribbon, SOUVENIRS on a teal ribbon,
                  SETTINGS typed with no plate, HOME SCREEN +2 / PROFILE REVISIT +2 typed on cloud plates)
  text_arrow      a typed arrow ("<", ">") inside a button instead of a drawn arrow icon
  flat_button     a button that is one flat colour in the screenshot (a plain rounded box)
  off_style_button a button plate whose frame is not in docs/art/button-set.json (one button set per game)
  solid_block     a flat single-colour rectangle >= 2% of the screen besides the background (placeholder squares,
                  grey lock blocks, blank card insides; from the screenshot)            (user 2026-10-21 round 2)
  placeholder     a sprite whose frame is a default/blank/placeholder frame (>= 0.5% of the screen)
  blank_card      a card/frame/slot picture (1.5-12% of the screen) with nothing inside it
  dark_text       text darker than L* 35 at font size >= 28 or bold (near-black / navy / dark-grey thick text)
  text_outside    a button's text sticking out of its plate
  empty_area      on a full page, a band >= 18% of the screen height with nothing in it
By purpose (dump_ui "purpose"):
  result_win / result_fail  >= 2 buttons, a number (reward/score/level), >= 3 pictures besides buttons and the
                            background (stars, coin, ribbon, mascot), >= 25% of the screen used
  home / result              at most 2 buttons with text on the plate (others are icons)
  map (level select)        >= 6 level buttons on one screen, each with its number
  checkin (7-day reward)    7 day cards with day numbers, the day-7 card >= 2x the size of the others, a Claim button
  home                      a BIG title picture in the top half (>= 55% of the screen width), cover art (characters/
                            scenery pictures that are not buttons, >= 15% of the screen), a PLAY button with a plate,
                            >= 2 icon buttons
  function pages            home, result, pause, settings, revive, trial: all buttons together <= 40% of the screen
                            (titles, logo, cover art and panels are not buttons; user 2026-10-21, 30% -> 40% on 2026-10-23)
  popups (reward, add-to-home, revisit, pause, revive, trial, offer ... everything but settings/league/checkin/shop/
  skins/map, which have their own content rules)
    plain_popup             the panel holds only text and buttons: it needs a generated illustration (gift/chest,
                            mascot, phone with the game icon, reward items with the currency icon ...) covering
                            >= 10% of the panel (user 2026-10-23 negative example: a flat pale "Home screen reward" panel
                            with font text and three flat buttons ADD NOW / CHECK REWARD / CLOSE)
  league                    >= 10 numbers (ranks and points), >= 35% of the screen used
  settings (General tab)    >= 3 rows/buttons, "How to Play", with no Credits/About entry (references/common-game-components.md)
  settings_sound (Sound tab) "Music" and "Sound"/"SFX" sections, >= 6 buttons (two switches, minus/plus), percentages
Required pages: home, result_win, result_fail, settings, settings_sound; league as well when
docs/league/decision.json says "add"; checkin when docs/features.json has the 7-day check-in; map when the level plan
(level_plan.json, audit_level_plan.py) says mode "levels" (user 2026-10-22: every level game has a map).

Usage:
  python audit_page_richness.py --project <game> [--dumps <folder> ...] [--binding review.json] --out report.json
Exit codes: 0 pass, 1 fail, 2 bad input. Structure from the scene tree only; Codex still judges the look.
"""
from feature_policy import removed as removed_feature
import argparse
import colorsys
from collections import Counter
import fnmatch
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_dark_area  # noqa: E402  same pixel measure as the screenshot audit
from audit_dev_text import PAT as DEV_TEXT  # noqa: E402  "LOCAL PREVIEW", "PROTOTYPE" ... seen by the player

PLAIN_FRAMES = re.compile(r'^(default_sprite_splash|default_sprite|default_panel|default_btn_\w+|singlecolor|single_color|'
                          r'white|blank|pure|solid|rect|square|color|colour|1x1|px)(\b|_|$)', re.I)
DIGIT = re.compile(r'\d')
GRID_W, GRID_H = 30, 60
MAINTENANCE_RULES = set()

REQUIRED = ('home', 'result_win', 'result_fail', 'settings', 'settings_sound')
FUNCTION_PAGES = {'home', 'result_win', 'result_fail', 'pause', 'settings', 'settings_sound', 'revive', 'trial'}
MAX_BUTTON_SHARE, MIN_TITLE_WIDTH, MIN_COVER_ART = 0.40, 0.55, 0.15   # buttons <= 40% (user 2026-10-23)
MIN_POPUP_ART = 0.10        # popup illustration share of the panel (user 2026-10-23)
TITLE_DECOR = re.compile(r'ribbon|banner|title|header|corner|border|frame|divider|line', re.I)   # not an illustration
OWN_POPUP_RULES = {'settings', 'settings_sound', 'league', 'checkin', 'shop', 'skins', 'map'}
MAX_FLAT, MAX_PLAIN_BLOCK = 0.40, 0.35
MIN_SOLID_BLOCK, MAX_EMPTY_BAND, DARK_LSTAR = 0.02, 0.18, 35.0
DARK_BOLD_LSTAR = 50.0      # user 2026-10-23: no dark bold text of any hue (label colour)
INK_DARK, INK_LIGHT = 45.0, 58.0   # screenshot: glyph pixels darker than INK_DARK with (almost) none lighter than INK_LIGHT
CARD_NAMES = re.compile(r'card|frame|slot|cell|box|plate|item_bg|level_bg|tile_bg', re.I)
ARROWS = re.compile(r'^\s*[<>‹›«»←→◀▶◁▷^vV＜＞]+\s*$')
WORDS = re.compile(r'[A-Za-z]{2,}')
NUMERIC = re.compile(r'^[\s\d+\-xX×/:.,%$#·]*\d[\s\d+\-xX×/:.,%$#·]*$')   # "0", "0/9", "+50", "1,250", "70%", "x2", "02:30"
DENSE_TEXT = 40       # user 2026-10-23: announcements / how-to-play paragraphs (> 40 characters) may be a thinner font
BITMAP_FONT_NAME = re.compile(r'fnt|bitmap|bmfont|atlas|digit|num', re.I)
MIN_BAKED_TEXT_BUTTON = 0.012   # a btn_<words> picture this big counts as a text button (icons are smaller)
GENERATED_TEXT_SOURCES = {}
RUNTIME_TEXT = []     # docs/text/runtime-text.json: labels that really change at run time (rival names ...), path globs
CAPTION_FRAMES = []    # Explicit whole-button word artworks; style membership alone does not imply a caption.
BUTTON_SET = None     # docs/art/button-set.json: frame-name globs of the one button set drawn for this game
PLACEHOLDER_FRAMES = re.compile(r'placeholder|default_sprite|singlecolor|single_color|blank|^white$|^1x1', re.I)
WORDLIKE = {'txt', 'text', 'texts', 'word', 'words', 'label', 'labels', 'caption', 'title', 'font', 'letter', 'letters', 'logo'}
NAME_TOKENS = re.compile(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])')   # BtnWord -> Btn, Word; txt_play -> txt, play (sword, texture: no)
MAX_STRETCH, MIN_STRETCH_AREA, MAX_STRETCH_AREA = 1.10, 0.002, 0.6   # user 2026-10-23: words 570x345 forced into 234x49
STRETCH_OK = re.compile(r'bar|fill|progress|line|divider|strip|stripe|glow|shadow|mask|ray|light|particle|bg|backdrop|'
                        r'background|sky|ground|floor|water|wave|gradient|vignette|overlay|dim', re.I)   # stretchable pictures
MIN_SHARP, MIN_SHARP_BG, MIN_SHARP_AREA = 1.99, 1.495, 0.003   # ART-04: picture >= 2x its node size, backgrounds 1.5x
BACKGROUND_NAME = re.compile(r'bg|backdrop|background|sky|scene|wallpaper', re.I)
CLARITY_EXEMPT = []   # docs/art/clarity-exempt.json: frame globs (with a why) kept from the original game (localize)
CANVAS_TEXT_FILES = []   # docs/text/runtime-text.json "canvas_text_files": scripts allowed to draw text with Canvas fonts
CANVAS_TEXT_CODE = re.compile(r'\.(fillText|strokeText)\s*\(')
MAX_BUSY, BUSY_WIDTH, BUSY_STEP = 0.30, 188, 20   # user 2026-10-23: calm backgrounds (edge pixels of the background)
DOUBLE_BUTTON = re.compile(r'double|(?<![a-z])x_?2(?!\d)|(?<!\d)2_?x(?![a-z])|×\s*2|翻倍|multiply', re.I)
GIFT_NAME = re.compile(r'gift|present|giftbox|礼盒|礼物', re.I)
REMOVED_NAME = re.compile(r'leader|ranking|league|checkin|check_in|daily_?reward|signin|sign_in|more_?games|moregame|cross_?promo', re.I)
OPTIONAL = {}
MODE = None           # level_plan.json mode (levels / endless): endless result_fail pages need the x2 button too


def solid_blocks(path, image_module):
    """Connected flat single-colour blocks in the screenshot (thumbnail, 8 px cells), largest first: (share, fill, bbox)."""
    with image_module.open(path) as im:
        im = im.convert('RGB')
        im.thumbnail((360, 360))
        w, h = im.size
        px = im.load()
    cell = 8
    cw, ch = w // cell, h // cell
    cells = {}
    for cy in range(ch):
        for cx in range(cw):
            bins = {tuple(c >> 4 for c in px[x, y]) for y in range(cy * cell, cy * cell + cell, 2)
                    for x in range(cx * cell, cx * cell + cell, 2)}
            if len(bins) == 1:
                cells[(cx, cy)] = bins.pop()
    seen, blocks = set(), []
    for start, colour in cells.items():
        if start in seen:
            continue
        stack, members = [start], []
        seen.add(start)
        while stack:
            x, y = stack.pop(); members.append((x, y))
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n not in seen and cells.get(n) == colour:
                    seen.add(n); stack.append(n)
        xs, ys = [m[0] for m in members], [m[1] for m in members]
        box = (min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
        blocks.append((len(members) / (cw * ch), len(members) / (box[2] * box[3]),
                       (box[0] / cw, box[1] / ch, box[2] / cw, box[3] / ch)))
    return sorted(blocks, reverse=True)


def lstar(rgb):
    return audit_dark_area._lstar(*rgb)


def rel_lum(rgb):
    def ch(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = rel_lum(a), rel_lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def generated_text_contrast(img, group, nodes, need, image_module):
    """Use the actual source alpha/fill masks, so the blue gaps between glyphs are not classified as text ink."""
    if group.get('comps',{}).get('image_text',{}).get('complete'):
        pieces=[n for n in nodes if node_under(n,group) and n is not group and 'sprite' in n['comps']]
    elif group.get('comps',{}).get('sprite',{}).get('frame') in GENERATED_TEXT_SOURCES:pieces=[group]
    else:return None
    if not pieces:return None
    ratios=[]
    for n in pieces:
        source=GENERATED_TEXT_SOURCES.get(n['comps']['sprite'].get('frame'))
        if not source or abs(n.get('angle',0))>1:return None
        r=n.get('unclipped_screen') or n.get('screen') or n['rect'];W,H=img.size
        box=(round(r[0]*W),round(r[1]*H),round((r[0]+r[2])*W),round((r[1]+r[3])*H))
        width,height=box[2]-box[0],box[3]-box[1]
        if width<2 or height<2:return None
        raw=image_module.open(source['path'] if isinstance(source,dict) else source).convert('RGBA')
        if isinstance(source,dict) and source.get('rect'):
            sx,sy,sw,sh=source['rect'];raw=raw.crop((sx,sy,sx+sw,sy+sh))
        raw=raw.resize((width,height))
        shown=img.crop(box).convert('RGB')
        if n.get('unclipped_screen') and n.get('screen'):
            clip=n['screen'];cb=(max(0,round(clip[0]*W)-box[0]),max(0,round(clip[1]*H)-box[1]),min(width,round((clip[0]+clip[2])*W)-box[0]),min(height,round((clip[1]+clip[3])*H)-box[1]));raw=raw.crop(cb);shown=shown.crop(cb)
        light=[];dark=[]
        for rgba,rgb in zip(raw.getdata(),shown.getdata()):
            if rgba[3]<200:continue
            ink=lstar(rgba[:3])
            if ink>=70:light.append(rgb)
            elif ink<=40:dark.append(rgb)
        if len(light)<8:return None
        median=lambda pixels:tuple(sorted(v[k] for v in pixels)[len(pixels)//2] for k in range(3))
        fill=median(light);outline=median(dark) if len(dark)>=8 else None
        surface=text_surface(n,nodes);bg=surface_background(img,surface)
        pair=contrast(fill,outline) if outline else 0
        against=contrast(fill,bg) if bg else 0
        # Same contrast thresholds as ordinary picture text, measured on actual rendered glyph pixels.
        if pair>=need and ((bg is not None and contrast(outline,bg)>=3) or against>=need):ratios.append(need)
        elif against>=need:ratios.append(against)
        else:ratios.append(max(pair if bg is None else 0,against))
    return min(ratios)


def text_problems(d, nodes, buttons, image_module):
    """Contrast, size and styling of every visible label, measured on the screenshot of this dump."""
    out = []
    shot = screenshot_of(d)
    img = None
    if image_module is not None and shot.is_file():
        img = image_module.open(shot).convert('RGB')
    cx, cy, cw, ch = d.get('canvas_css') or [0, 0, 1, 1]
    for n in nodes:
        if transient_banner_offscreen(n):
            # MainLayer.level_up is deliberately parked outside the viewport between its
            # entrance/exit tween. Its centered tween frame is captured and checked separately.
            continue
        lab = n['comps'].get('label')
        if not lab and text(n) and img is not None:            # picture text (frame txt_*): measured on the pixels
            surface = text_surface(n, nodes)
            dark_ink = picture_text_dark(img, n.get('screen') or n['rect'], surface)
            if dark_ink:
                out.append('dark_picture_text: "%s" (%s) is dark heavy picture text (%s): permanently banned (user 2026-10-23); '
                           'redraw it with a light fill (white/cream/light yellow/light theme colour) and a darker outline'
                           % (text(n)[:30], n['path'], dark_ink))
            size_css = (n.get('screen') or n['rect'])[3] * ch if ch else 0
            need = 4.5 if size_css < 24 else 3.0
            measured=generated_text_contrast(img,n,nodes,need,image_module)
            ratio = (None if measured>=need else measured) if measured is not None else picture_text_contrast(img, n.get('screen') or n['rect'], need, surface)
            if ratio is not None:
                out.append('low_contrast: picture text "%s" contrast %.1f:1 against its background (needs %.1f): give the text a clearly separated fill/outline or an integrated contrast plate'
                           % (text(n)[:30], ratio, need))
            continue
        if not lab or not text(n):
            continue
        r = n.get('screen') or n['rect']
        h_design = lab.get('height') or 0
        size = (lab.get('actualFontSize') or lab.get('fontSize') or 0)
        css = size * (r[3] * ch / h_design) if h_design else None          # font size in CSS px on the simulated phone
        word = text(n)[:30]
        if css is not None and round(css, 1) < 11:
            out.append('small_text: "%s" is %.0f px on the phone (needs >= 11 px)' % (word, css))
        bitmap = bitmap_font(lab)
        if NUMERIC.match(text(n)) and not bitmap:
            out.append('font_number: "%s" (%s) is a number drawn with a font (%s): coins, energy, level, score, price, timer and '
                       'percent digits are generated digit pictures in the game style (0-9 and + - / : %% x drawn with the art), '
                       'used as a BitmapFont (.fnt) / LabelAtlas so the value still changes at run time (user 2026-10-23)'
                       % (word, n['path'], lab.get('font_kind') or lab.get('font') or ('system font' if lab.get('system_font') else 'font')))
        if bitmap:              # the glyphs are pictures: fill, outline and colours are in the images, measured on the pixels
            if img is not None:
                surface = text_surface(n, nodes)
                dark_ink = picture_text_dark(img, r, surface)
                if dark_ink:
                    out.append('dark_picture_text: "%s" (%s) is dark heavy picture digits (%s): permanently banned (user 2026-10-23); '
                               'redraw the digit pictures with a light fill and a darker outline' % (word, n['path'], dark_ink))
                need = 4.5 if (css or 0) < 24 else 3.0
                ratio = picture_text_contrast(img, r, need, surface)
                if ratio is not None:
                    out.append('low_contrast: bitmap text "%s" contrast %.1f:1 against its background (needs %.1f): use an integrated contrasting well or regenerate the glyph fill/outline'
                               % (word, ratio, need))
            if WORDS.search(text(n)) and len(text(n)) <= DENSE_TEXT and not runtime_text(n['path']):
                out.append('font_text: "%s" (%s) is fixed words typed with a bitmap font: fixed words are one generated picture '
                           '(frame txt_<words>, buttons btn_<words>)' % (word, n['path']))
            continue
        outline = lab.get('outline') if isinstance(lab.get('outline'), dict) else ({} if lab.get('outline') else None)
        styled = bool(outline) or lab.get('shadow') or lab.get('bold')
        in_button = any(node_under(n, b) for b in buttons)
        if not styled and len(text(n)) <= DENSE_TEXT:          # long paragraphs (rules, notices) may be a thinner font
            out.append('plain_text: "%s" is thin font text (no outline, shadow or bold): make it picture text with the art, or the '
                       'game display font with an outline/shadow in the theme colours' % word)
        if WORDS.search(text(n)) and len(text(n)) <= 40 and not runtime_text(n['path']):
            out.append('font_text: "%s" (%s) is drawn with a font; fixed words (titles, buttons, labels, item and mission names, '
                       'COINS/Price ...) are picture text generated with GPT in the game\'s style, frame txt_<words> '
                       '(only text that really changes at run time goes in docs/text/runtime-text.json)' % (word, n['path']))
        if in_button and ARROWS.match(text(n)):
            out.append('text_arrow: "%s" in %s is a typed arrow: draw the arrow buttons as part of the game\'s button set'
                       % (word, n['path']))
        col = lab.get('color')
        if isinstance(col, list) and len(col) == 3 and dark_green(col):
            out.append('dark_green_text: "%s" is dark green/teal %s: banned (user 2026-10-22); picture text, or a bright display '
                       'font with an outline' % (word, tuple(col)))
        heavy = lab.get('bold') or outline is not None or lab.get('shadow') or (css or 0) >= 16 or size >= 24
        if isinstance(col, list) and len(col) == 3 and lstar(col) < DARK_BOLD_LSTAR and heavy and not dark_green(col):
            out.append('dark_bold_text: "%s" is dark bold text %s (L* %.0f): permanently banned (user 2026-10-23, any hue, HUD '
                       'too); fill it white/cream/light yellow or a light theme colour with a darker outline, or picture text '
                       'drawn that way' % (word, tuple(col), lstar(col)))
        elif img is not None:
            dark_ink = picture_text_dark(img, r)
            if dark_ink:
                out.append('dark_picture_text: "%s" looks dark and heavy on the screenshot (%s): permanently banned (user '
                           '2026-10-23); redraw it with a light fill and a darker outline' % (word, dark_ink))
        if img is None or not (isinstance(col, list) and len(col) == 3):
            continue
        W, H = img.size
        x0, y0 = int(max(0, r[0]) * W), int(max(0, r[1]) * H)
        x1, y1 = int(min(1, r[0] + r[2]) * W), int(min(1, r[1] + r[3]) * H)
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        # what is behind the text: a ring just outside the text box (the box itself is mostly glyphs)
        m = max(3, (y1 - y0) // 3)
        ring = []
        for (a0, b0, a1, b1) in ((x0 - m, y0 - m, x1 + m, y0), (x0 - m, y1, x1 + m, y1 + m), (x0 - m, y0, x0, y1), (x1, y0, x1 + m, y1)):
            a0, b0, a1, b1 = max(0, a0), max(0, b0), min(W, a1), min(H, b1)
            if a1 - a0 > 0 and b1 - b0 > 0:
                ring += list(img.crop((a0, b0, a1, b1)).getdata())
        oc = outline.get('color') if outline else None
        bg = ring[::max(1, len(ring) // 3000)]
        if len(bg) < 8:
            continue
        bg_l = sorted(rel_lum(p) for p in bg)[len(bg) // 2]
        bg_c = min(bg, key=lambda p: abs(rel_lum(p) - bg_l))
        need = 4.5 if (css or 0) < 24 else 3.0
        ratio = contrast(col, bg_c)
        if ratio >= need:
            continue
        if oc and (outline.get('width') or 0) >= 2 and contrast(oc, bg_c) >= 3 and contrast(col, oc) >= 3:
            continue
        out.append('low_contrast: "%s" contrast %.1f:1 against what is behind it (needs %.1f): change the text colour, add an outline '
                   'or a plate behind it' % (word, ratio, need))
    return out


def surface_background(img, surface_rect):
    """Return a reliable dominant RGB fill from the smallest containing rendered surface."""
    if not surface_rect:
        return None
    W, H = img.size
    x0 = int(max(0, surface_rect[0]) * W)
    y0 = int(max(0, surface_rect[1]) * H)
    x1 = int(min(1, surface_rect[0] + surface_rect[2]) * W)
    y1 = int(min(1, surface_rect[1] + surface_rect[3]) * H)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    pixels = list(img.crop((x0, y0, x1, y1)).getdata())
    bins = Counter(tuple((v // 8) * 8 + 4 for v in p) for p in pixels)
    bg, count = max(bins.items(), key=lambda item: item[1])
    return bg if count >= max(8, 0.08 * len(pixels)) else None


def picture_text_dark(img, r, surface_rect=None):
    """Pixels of a text box on the screenshot: glyph pixels (L* differs >= 15 from what is just outside the box) that are
    mostly dark with (almost) no light fill = dark heavy text. Returns a short reason or ''."""
    W, H = img.size
    x0, y0 = int(max(0, r[0]) * W), int(max(0, r[1]) * H)
    x1, y1 = int(min(1, r[0] + r[2]) * W), int(min(1, r[1] + r[3]) * H)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return ''
    m = max(3, (y1 - y0) // 3)
    ring = []
    for (a0, b0, a1, b1) in ((x0 - m, y0 - m, x1 + m, y0), (x0 - m, y1, x1 + m, y1 + m), (x0 - m, y0, x0, y1), (x1, y0, x1 + m, y1)):
        a0, b0, a1, b1 = max(0, a0), max(0, b0), min(W, a1), min(H, b1)
        if a1 - a0 > 0 and b1 - b0 > 0:
            ring += list(img.crop((a0, b0, a1, b1)).getdata())
    surface = surface_background(img, surface_rect)
    if surface is not None:
        bg = lstar(surface)
    else:
        if len(ring) < 8:
            return ''
        ring = ring[::max(1, len(ring) // 2000)]
        bg = sorted(lstar(p) for p in ring)[len(ring) // 2]
    box = list(img.crop((x0, y0, x1, y1)).getdata())
    box = box[::max(1, len(box) // 4000)]
    # Include pale fills that sit close to a light panel. A 15 L* cutoff sees only
    # their dark outline and can incorrectly classify an outlined light glyph as
    # dark-heavy text; the contrast check separately decides whether that fill is
    # readable against its local background.
    ink = [v for v in (lstar(p) for p in box) if abs(v - bg) >= 2]
    if len(ink) < 0.08 * len(box) or len(ink) < 20:
        return ''
    dark = sum(1 for v in ink if v < INK_DARK) / len(ink)
    light = sum(1 for v in ink if v >= INK_LIGHT) / len(ink)
    if dark >= 0.6 and light < 0.1:
        return '%.0f%% of the glyph pixels are dark (L* < %d), %.0f%% light, background L* %.0f' % (dark * 100, INK_DARK, light * 100, bg)
    return ''


def picture_text_contrast(img, r, need, surface_rect=None):
    """Check generated/bitmap glyph pixels against the local rendered background, including an actual outline when present."""
    W, H = img.size
    x0, y0 = int(max(0, r[0]) * W), int(max(0, r[1]) * H)
    x1, y1 = int(min(1, r[0] + r[2]) * W), int(min(1, r[1] + r[3]) * H)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    m = max(3, (y1 - y0) // 3)
    ring_sides = []
    for (a0, b0, a1, b1) in ((x0 - m, y0 - m, x1 + m, y0), (x0 - m, y1, x1 + m, y1 + m),
                             (x0 - m, y0, x0, y1), (x1, y0, x1 + m, y1)):
        a0, b0, a1, b1 = max(0, a0), max(0, b0), min(W, a1), min(H, b1)
        if a1 > a0 and b1 > b0:
            pixels = list(img.crop((a0, b0, a1, b1)).getdata())
            ring_sides.append(pixels[::max(1, len(pixels) // 1200)])
    if sum(map(len, ring_sides)) < 8:
        return None
    box = list(img.crop((x0, y0, x1, y1)).getdata())
    box = box[::max(1, len(box) // 5000)]
    # A text box may nearly fill its own colored well, leaving the outside ring on a
    # different surface. When the scene dump identifies the closest rendered surface,
    # sample its dominant interior color; otherwise use the neighboring pixels.
    def median_rgb(pixels):
        return tuple(sorted(p[i] for p in pixels)[len(pixels) // 2] for i in range(3))
    surface = surface_background(img, surface_rect)
    if surface is None:
        candidates = [median_rgb(side) for side in ring_sides if side]
        if not candidates:
            return None
        best = max(candidates, key=lambda c: sum(1 for p in box if max(abs(p[i] - c[i]) for i in range(3)) <= 20))
        matches = sum(1 for p in box if max(abs(p[i] - best[i]) for i in range(3)) <= 20)
        if matches < max(8, 0.05 * len(box)):
            ring = [p for side in ring_sides for p in side]
            bg = median_rgb(ring)
        else:
            bg = best
    else:
        bg = surface
    bg_l, bg_star = rel_lum(bg), lstar(bg)
    # Low-contrast glyph fills can differ from a cream panel by only a few L* steps;
    # filtering at 8 here silently discarded the exact case this check must catch.
    # Keep small differences, then use the dominant pixel colour and outline pair
    # below to distinguish text from antialiasing and texture noise.
    ink = [p for p in box if abs(lstar(p) - bg_star) >= 2]
    if len(ink) < max(20, 0.05 * len(box)):
        return None
    # A bitmap fill is often textured/antialiased; 0.05 luminance buckets keep its
    # actual foreground together instead of leaving only the darker outline as a mode.
    bins = Counter(int(round(rel_lum(p) * 20)) for p in ink)
    modes = [(count, bucket / 20.0) for bucket, count in bins.items() if count >= max(3, 0.05 * len(ink))]
    if not modes:
        return None
    count, main_l = max(modes)
    ratio = (max(main_l, bg_l) + 0.05) / (min(main_l, bg_l) + 0.05)
    if ratio >= need:
        return None
    # A legible two-tone glyph may use a light fill and a dark outline. The darker
    # outline must separate from the surface and the fill must separate from it.
    for other_count, other_l in modes:
        if other_count / len(ink) < 0.05:
            continue
        pair = (max(main_l, other_l) + 0.05) / (min(main_l, other_l) + 0.05)
        for outline_l in (main_l, other_l):
            outline_bg = (max(outline_l, bg_l) + 0.05) / (min(outline_l, bg_l) + 0.05)
            if outline_bg >= 3.0 and pair >= 3.0:
                return None
    return ratio


BASE_PANEL = re.compile(r'panel[_ -]?(?:surface|art)|background|backdrop|backplate', re.I)
VALUE_SURFACE = re.compile(r'well|value|countdown|counter', re.I)


def node_parent(n):
    return str(n.get('path', '')).rsplit('/', 1)[0]


def base_panel_layer(n):
    return bool(BASE_PANEL.search(str(n.get('name', '')) + ' ' + str(n.get('path', '').rsplit('/', 1)[-1])))


def base_layer_occludes(surface, glyph, nodes):
    """Return a later full panel layer that covers a value surface before its text is drawn."""
    surface_rect = surface.get('screen') or surface['rect']
    surface_area = area(surface_rect)
    if surface_area <= 0:
        return None
    for layer in nodes:
        if layer is surface or not ({'graphics', 'sprite'} & set(layer.get('comps', {}))):
            continue
        if node_parent(layer) != node_parent(surface) or layer.get('depth') != surface.get('depth'):
            continue
        if not (surface.get('order', 0) < layer.get('order', 0) < glyph.get('order', 0)) or not base_panel_layer(layer):
            continue
        layer_rect = layer.get('screen') or layer['rect']
        if inter(surface_rect, layer_rect) >= 0.98 * surface_area:
            return layer
    return None


def hidden_value_surface_problems(nodes):
    """Flag a named numeric well whose panel background is drawn on top of it."""
    out = []
    for surface in nodes:
        if 'graphics' not in surface.get('comps', {}):
            continue
        if not VALUE_SURFACE.search(str(surface.get('name', '')) + ' ' + str(surface.get('path', ''))):
            continue
        rect = surface.get('screen') or surface['rect']
        for glyph in nodes:
            if node_parent(glyph) != node_parent(surface) or glyph.get('order', 0) <= surface.get('order', 0) or not text(glyph):
                continue
            glyph_rect = glyph.get('screen') or glyph['rect']
            if area(glyph_rect) <= 0 or inter(glyph_rect, rect) < 0.98 * area(glyph_rect):
                continue
            layer = base_layer_occludes(surface, glyph, nodes)
            if layer:
                out.append('hidden_surface: %s is covered by later panel layer %s before "%s" is drawn; keep the value well '
                           'above the panel background and below its text' % (surface['path'], layer['path'], text(glyph)[:28]))
                break
    return out


def text_surface(n, nodes):
    """Smallest earlier visible Graphics/Sprite surface that fully contains this text box."""
    rect = n.get('screen') or n['rect']
    size = area(rect)
    if size <= 0:
        return None
    candidates = []
    for m in nodes:
        if m is n or m.get('order', 0) > n.get('order', 0):
            continue
        if not ({'graphics', 'sprite'} & set(m.get('comps', {}))):
            continue
        surface = m.get('screen') or m['rect']
        if area(surface) <= size:
            continue
        if inter(rect, surface) >= 0.98 * size:
            if base_layer_occludes(m, n, nodes):
                continue
            candidates.append((area(surface), surface))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def area(r):
    return max(0.0, r[2]) * max(0.0, r[3])


def transient_banner_offscreen(node):
    """Skip contrast sampling only for the known offscreen tween pose, never its visible pose."""
    if node.get('path') != 'Canvas/UI/MainLayer/level_up/label/__art_image':
        return False
    rect = node.get('screen') or node.get('rect')
    size = area(rect) if rect else 0
    visible = inter(rect, (0.0, 0.0, 1.0, 1.0)) / size if size else 0
    return visible < 0.25


def coverage(rects, frame=(0.0, 0.0, 1.0, 1.0)):
    fx, fy, fw, fh = frame
    if fw <= 0 or fh <= 0:
        return 0.0
    hit = 0
    for gy in range(GRID_H):
        for gx in range(GRID_W):
            x, y = fx + (gx + 0.5) * fw / GRID_W, fy + (gy + 0.5) * fh / GRID_H
            if any(r[0] <= x <= r[0] + r[2] and r[1] <= y <= r[1] + r[3] for r in rects):
                hit += 1
    return hit / (GRID_W * GRID_H)


def visual_coverage_nodes(content, nodes):
    """Rectangles that visibly render UI area; do not count an oversized button hit target as its artwork."""
    out = [n for n in content if 'sprite' in n['comps'] or text(n)]
    names = {'PanelSurface', 'CardSurface'}
    out += [n for n in nodes if n['name'] in names and 'graphics' in n['comps'] and area(n['rect']) < 0.85]
    out += [n for n in content if 'button' in n['comps'] and 'graphics' in n['comps']]
    return out


def center_in(r, box):
    cx, cy = r[0] + r[2] / 2, r[1] + r[3] / 2
    return box[0] <= cx <= box[0] + box[2] and box[1] <= cy <= box[1] + box[3]


def text(n):
    if n.get('comps',{}).get('sprite',{}).get('whole_text_part') is True:return ''
    for k in ('label', 'richtext', 'image_text'):
        if k in n['comps'] and str(n['comps'][k].get('string', '')).strip():
            return str(n['comps'][k]['string']).strip()
    frame = str(n['comps'].get('sprite', {}).get('frame', '')) if 'sprite' in n['comps'] else ''
    if frame.lower().startswith('txt_'):            # picture text generated with the art: frame txt_how_to_play
        return frame[4:].replace('_', ' ').strip()
    return ''


def baked(n):
    """Words baked into a one-piece button picture (frame btn_<words>, user 2026-10-23): btn_play -> "play"."""
    frame = str(n['comps'].get('sprite', {}).get('frame', '')) if 'sprite' in n['comps'] else ''
    if frame.lower().startswith('btn_'):return frame[4:].replace('_', ' ').strip()
    if CAPTION_FRAMES and any(fnmatch.fnmatch(frame.lower(),pattern.lower()) for pattern in CAPTION_FRAMES):return frame.replace('_',' ').strip()
    return ''


def words(n):
    return text(n) or baked(n)


def countdown_hint(n, nodes):
    """A short timer label next to a clock is information, not a button caption."""
    if not re.match(r'^(?:next reward|next claim|time left|available in|next in)\b', text(n), re.I):
        return False
    r = n.get('screen') or n['rect']
    cy = r[1] + r[3] / 2
    for peer in nodes:
        value = text(peer)
        if peer is n or not NUMERIC.match(value) or ':' not in value:
            continue
        q = peer.get('screen') or peer['rect']
        py = q[1] + q[3] / 2
        gap = max(0.0, q[0] - (r[0] + r[2]), r[0] - (q[0] + q[2]))
        if abs(cy - py) <= max(r[3], q[3]) * 0.75 and gap <= 0.18:
            return True
    return False


def bitmap_font(lab):
    kind = lab.get('font_kind')
    if kind is not None:
        return kind == 'bitmap'
    return bool(BITMAP_FONT_NAME.search(str(lab.get('font') or '')))    # dumps from before font_kind: judge by the font name


def one_piece_problems(nodes, buttons):
    """User 2026-10-23 (both boards): a button is ONE generated picture with its stylized word in it. A word (font label or
    txt_ picture text) laid over a button plate is a spliced button. Digits on a plate (level numbers, prices) may stay
    bitmap-font labels; text listed in docs/text/runtime-text.json is exempt."""
    out = []
    for b in buttons:
        sub = [n for n in nodes if node_under(n, b)]
        said = [n for n in sub if (WORDS.search(text(n)) and not runtime_text(n['path']) and
                ('label' in n['comps'] or 'richtext' in n['comps'] or str(n['comps'].get('sprite', {}).get('frame', '')).lower().startswith('txt_')))
                or (n is not b and wordlike(n) and not text(n) and not baked(n))]          # words.png / BtnWord cut from a word sheet
        plate = any('sprite' in n['comps'] and not text(n) and n not in said and area(n['rect']) >= 0.3 * area(b['rect']) for n in sub)
        if said and plate:
            out.append('spliced_button: %s lays the word "%s" (%s) over a button plate: generate the whole button with its '
                       'stylized word in one picture (frame btn_<words>, e.g. btn_play; icon captions baked into the icon '
                       'picture), no label or txt_ word on top of a plate (user 2026-10-23)'
                       % (b['path'], ' / '.join((text(n) or n['comps']['sprite'].get('frame') or n['name'])[:20] for n in said[:3]),
                          'font' if any('label' in n['comps'] for n in said) else 'separate picture text'))
    return out


def wordlike(n):
    """A sprite whose node or frame name says it is a word picture (words.png, txt_details, BtnLabel, title_logo), not a plate."""
    s = n['comps'].get('sprite')
    if not s:
        return False
    frame = str(s.get('frame', ''))
    return not frame.lower().startswith('btn_') and any(t.lower() in WORDLIKE for t in NAME_TOKENS.findall(frame + ' ' + n['name']))


def squash_problems(nodes, full):
    """User 2026-10-23 (DETAILS case): a 1140x1380 word sheet cut into 570x345 cells was forced into 234x49 buttons with
    SizeMode.CUSTOM - the words were squashed 2.89x (SKINS / DAILY 1.80x, MAP 1.19x). dump_ui records each sprite's own
    picture size (frame_size) and the size it is drawn at (display_size); a simple (not 9-sliced) picture whose aspect
    ratio is changed by more than 10% is stretched. Word pictures (txt_/btn_/logo/title/words ...) never; other pictures
    only when they are not stretchable by nature (bars, fills, glows, backgrounds). Canvas-drawn sprites (text drawn at
    run time with Canvas fonts, e.g. a RasterText.ts) are not generated picture text."""
    out = []
    for n in nodes:
        s = n['comps'].get('sprite')
        if not s:
            continue
        frame = str(s.get('frame', ''))
        wordy = bool(text(n) or baked(n) or wordlike(n))
        if s.get('canvas_drawn') and not runtime_text(n['path']):
            out.append('canvas_text: %s (frame "%s") is drawn at run time on a Canvas (fillText with a browser font): text is '
                       'generated picture text made with the art - only real run-time text listed in docs/text/runtime-text.json '
                       'may be drawn, and then with a generated bitmap font (user 2026-10-23)' % (n['path'], frame))
        fs, ds = s.get('frame_size'), s.get('display_size')
        # TILED sprites repeat the source frame across the node. Comparing the entire node to one
        # tile reports intentional repetition as stretch; their source-resolution handling is below.
        if s.get('sliced') or s.get('tiled') or n in full or not (isinstance(fs, list) and isinstance(ds, list) and len(fs) == 2 and len(ds) == 2):
            continue
        if min(fs) <= 0 or min(ds) <= 0 or not (MIN_STRETCH_AREA <= area(n['rect']) < MAX_STRETCH_AREA):
            continue
        k = (ds[0] / ds[1]) / (fs[0] / fs[1])
        stretch = max(k, 1 / k)
        if stretch <= MAX_STRETCH or (not wordy and STRETCH_OK.search(n['name'] + ' ' + frame)):
            continue
        how = 'squashed flat' if k > 1 else 'squeezed narrow'
        if wordy:
            out.append('squashed_text: %s (frame "%s") is a word picture %dx%d drawn at %gx%g - %s %.2fx (non-uniform scale): '
                       'crop each word to its visible pixels as its own SpriteFrame and scale it uniformly (min(w/W, h/H), '
                       'SizeMode TRIMMED/RAW, never CUSTOM to the button size); if it does not fit, change the button or '
                       'regenerate the word - never stretch letters (user 2026-10-23)'
                       % (n['path'], frame, fs[0], fs[1], ds[0], ds[1], how, stretch))
        else:
            out.append('squashed_picture: %s (frame "%s") %dx%d is drawn at %gx%g - %s %.2fx: keep the picture\'s own aspect '
                       'ratio (uniform scale) or 9-slice it' % (n['path'], frame, fs[0], fs[1], ds[0], ds[1], how, stretch))
    return out


def low_res_problems(nodes, full):
    """ART-04 at run time. Compare source pixels to the sprite's actual CSS-pixel size on the phone, not Cocos design
    units. Frames set from code are not in scene files, so the static audit_image_clarity.py misses them - the dump measures
    the live view."""
    out = []
    for n in nodes:
        s = n['comps'].get('sprite')
        if not s or s.get('sliced') or s.get('tiled') or s.get('canvas_drawn'):
            continue
        fs = s.get('frame_size')
        ds = s.get('css_display_size') or s.get('display_size')
        if not (isinstance(fs, list) and isinstance(ds, list) and len(fs) == 2 and len(ds) == 2) or min(fs) <= 0 or min(ds) <= 0:
            continue
        a = area(n['rect'])
        if a < MIN_SHARP_AREA:
            continue
        frame = str(s.get('frame', ''))
        # Cocos' default 2x2 frame is used here only as a dim touch-blocking shade.
        # It is not visible artwork or a background texture, so do not apply ART-04 to it.
        # Keep the exception narrow: the known MenuLayer path, fallback frame, and dim opacity must all match.
        if (n.get('name') == 'bgshade' and (n.get('path', '').endswith('/MenuLayer/bgshade') or n.get('path', '').endswith('/SettingLayer/bgshade')) and
                frame.lower() == 'default_sprite_splash' and float(n.get('opacity', 1) or 0) <= 0.30):
            continue
        if any(fnmatch.fnmatch(frame.lower(), g.lower()) for g in CLARITY_EXEMPT):
            continue
        bg = n in full or a >= MAX_STRETCH_AREA or bool(BACKGROUND_NAME.search(n['name'] + ' ' + frame))
        if not bg and STRETCH_OK.search(n['name'] + ' ' + frame):
            continue
        need = MIN_SHARP_BG if bg else MIN_SHARP
        r = min(fs[0] / ds[0], fs[1] / ds[1])
        if r >= need:
            continue
        want = 1.5 if bg else 2
        out.append('low_res: %s (frame "%s") picture %dx%d is drawn at %gx%g = %.2fx - needs >= %gx (%dx%d px) or it looks soft on '
                   'the phone: regenerate or re-crop it at >= %gx (ART-04, same check every art round as in the final review, '
                   'user 2026-10-23)' % (n['path'], frame, fs[0], fs[1], ds[0], ds[1], r, want, round(ds[0] * want), round(ds[1] * want), want))
    return out


BITMAP_DIGIT_FRAME = re.compile(r'(?:^|[_-])(?:digit|digits|num|nums|number|numbers|glyph|glyphs)[_-]?\d+(?:$|[_-])', re.I)
LEAGUE_VALUE_CONTEXT = re.compile(r'\b(?:rank|score|points?|position|place)\b', re.I)


def league_number_count(nodes):
    """Count rank/score values, including generated bitmap-digit groups, without counting digits in rival nicknames."""
    text_values, bitmap_groups = 0, set()
    for n in nodes:
        path = str(n.get('path', '') or '')
        name = str(n.get('name', '') or '')
        comps = n.get('comps', {})
        label = comps.get('label') or comps.get('richtext')
        value = str(label.get('string', '') if isinstance(label, dict) else '')
        if value and LEAGUE_VALUE_CONTEXT.search(path + ' ' + name + ' ' + value):
            text_values += len(re.findall(r'(?<![A-Za-z])\d+(?:,\d{3})*(?:\.\d+)?', value))
        sprite = comps.get('sprite')
        frame = str(sprite.get('frame', '') if isinstance(sprite, dict) else '')
        if frame and BITMAP_DIGIT_FRAME.search(frame):
            parent = path.rsplit('/', 1)[0] if '/' in path else path
            if LEAGUE_VALUE_CONTEXT.search(parent + ' ' + name):
                bitmap_groups.add(parent)
    return text_values + len(bitmap_groups)


def visible_level_button_count(nodes):
    """Count every visible level card, including locked/non-interactable cards.

    Layout coverage is about what players can see. A locked card still occupies a
    map slot and must be reviewed even though it correctly rejects input.
    """
    buttons = [n for n in nodes if 'button' in n.get('comps', {})]
    named = {n.get('path') for n in buttons if re.fullmatch(r'level_\d+', n.get('name', ''))}
    if named:
        return len(named)
    # Compatibility for maps whose cards do not use the level_<number> naming rule.
    return len({n.get('path') for n in buttons if any(
        re.fullmatch(r'\s*\d+(\s*-\s*\d+)?\s*', text(child)) or
        re.search(r'level|lv|stage', n.get('name', ''), re.I)
        for child in nodes if under(child.get('path', ''), n.get('path', ''))
    )})


DECOR = {'spark', 'sparks', 'sparkle', 'sparkles', 'star', 'stars', 'glow', 'shine', 'light', 'lights', 'shadow', 'halo', 'particle',
         'particles', 'deco', 'decor', 'decoration', 'bubble', 'bubbles', 'badge', 'dot', 'reddot', 'new', 'tag', 'corner', 'ribbon',
         'flare', 'twinkle', 'fx', 'mark', 'marker', 'lock', 'check', 'tick'}   # name tokens of small marks that may overlap on purpose
ACTION_WORDS = re.compile(r'^\W*(watch(\s*an?)?\s*ad|watch|play|claim|collect|get|buy|unlock|revive|retry|next(?=\W*(?:level|page|round|stage)\b|\W*$)|continue|start|spin|'
                          r'open|upgrade|equip|use)\b', re.I)
MAX_STICK_OUT = 0.35     # a picture may peek over its button/capsule edge by up to 35% of its own size
MAX_HOLDER = 0.15        # buttons, capsules and cards (the big day-7 card is ~10% of the screen; user 2026-10-23)
GLYPH = re.compile(r'^(?:(?:num|nums|number|numbers|digit|digits|glyph|char|font|n|d)[_\-]?)?[0-9]$|'
                   r'(?:^|[_\-])(?:num|nums|number|digit|digits|glyph)s?[_\-]?[0-9]?$', re.I)   # num_0, digit7, 5, glyph_3
MAX_GLYPH_OVERLAP = 0.12     # two digit/letter pictures may touch, not cover each other (user 2026-10-23: "100" printed as "10" over "100")
CHECKER_OK = re.compile(r'checker|chess|flag|board|tile|grid|plaid|tartan', re.I)   # real checker patterns in the art


def card_like(n):
    s = n['comps'].get('sprite') or {}
    return bool(s.get('sliced') or CARD_NAMES.search(n['name'] + ' ' + str(s.get('frame', ''))) or re.match(r'(?i)day\s*\d', n['name']))


def parent_of(n):
    return n['path'].rsplit('/', 1)[0]


def glyph(n):
    s = n['comps'].get('sprite')
    if s and re.match(r'^(?:rail|line)[_-]',str(s.get('frame','')),re.I):return False
    if not s or text(n) or baked(n) or decor(n) or area(n['rect']) >= 0.02:
        return False
    return bool(BITMAP_DIGIT_FRAME.search(str(s.get('frame',''))) or GLYPH.search(str(s.get('frame', ''))) or GLYPH.search(n['name']))


def glyph_problems(nodes):
    """User 2026-10-23 (Daily Rewards popup): the 3-digit rewards 100/150/200/300 were printed with the digits on top of
    each other ("10" over "100") while 25/50 looked fine. Numbers are never hand-placed digit pictures or a second label
    on top of the first:
      glyph_overlap    digit/letter pictures (num_0, digit7 ...) under one parent covering each other (>= 12% of the smaller)
      double_number    a number drawn twice over itself: a label with a child/parent label of a different string, or a
                       number label laid on digit pictures
      negative_spacing a label with spacingX < 0 pushing its letters/digits into each other
    Fixed numbers (check-in rewards, prices, level rewards) are generated as one picture with their icon/plate; numbers that
    change use one bitmap font (.fnt advances from the real glyph widths, see font_advance) on one Label."""
    out = []
    groups = {}
    for n in nodes:
        if glyph(n):
            groups.setdefault(parent_of(n), []).append(n)
    for parent, gl in groups.items():
        hit = None
        for i_, a in enumerate(gl):
            for b in gl[i_ + 1:]:
                small = min(area(a['rect']), area(b['rect']))
                if small > 0 and inter(a['rect'], b['rect']) >= MAX_GLYPH_OVERLAP * small:
                    hit = (a, b, inter(a['rect'], b['rect']) / small)
                    break
            if hit:
                break
        if hit:
            out.append('glyph_overlap: the digit pictures under %s are drawn over each other (%s and %s cover %.0f%% of the smaller '
                       'one): do not place digit pictures by hand - generate fixed numbers (check-in rewards, prices) together with '
                       'their coin/plate as ONE picture, and show changing numbers with one bitmap-font Label whose .fnt advances '
                       'come from the real glyph widths (user 2026-10-23: "100" printed as "10" over "100")'
                       % (parent, hit[0]['name'], hit[1]['name'], 100 * hit[2]))
    texts = [n for n in nodes if text(n)]
    for i_, a in enumerate(texts):
        for b in texts[i_ + 1:]:
            ta, tb = text(a), text(b)
            if not related(a, b) or ta == tb or not (DIGIT.search(ta) or DIGIT.search(tb)):
                continue
            small = min(area(a['rect']), area(b['rect']))
            if small > 0 and inter(a['rect'], b['rect']) >= 0.2 * small:
                out.append('double_number: "%s" (%s) and "%s" (%s) are printed over each other: one number is one Label (or one '
                           'generated picture with its plate), never a second label/copy on top (user 2026-10-23: "10" over "100")'
                           % (ta[:12], a['path'], tb[:12], b['path']))
    for t in texts:
        if not DIGIT.search(text(t)):
            continue
        for g in (n for gl in groups.values() for n in gl):
            small = min(area(t['rect']), area(g['rect']))
            if (g is not t and not (t['comps'].get('image_text',{}).get('complete') is True and g['path'].startswith(t['path']+'/')) and small > 0 and inter(t['rect'], g['rect']) >= 0.2 * small):
                out.append('double_number: the number "%s" (%s) is laid over the digit picture %s: the digits are drawn twice - '
                           'keep one of them (user 2026-10-23)' % (text(t)[:12], t['path'], g['path']))
                break
    for t in nodes:
        lab = t['comps'].get('label')
        if not lab:
            continue
        sx = lab.get('spacingX')
        if isinstance(sx, (int, float)) and sx < 0 and len(re.sub(r'\s', '', text(t))) >= 2:
            out.append('negative_spacing: "%s" (%s) has spacingX %g: the letters/digits are pushed into each other - spacing >= 0; '
                       'if it does not fit, make the plate wider or the font smaller (user 2026-10-23)' % (text(t)[:16], t['path'], sx))
    return out


def checker_problems(d, nodes):
    """User 2026-10-23 (Daily Rewards cards): the generated card art had the grey/white (here green) checkerboard an image
    generator paints when asked for "transparent" baked into the pixels. Measured on the screenshot: windows where the
    picture repeats every 2 cells across and down but changes every cell (and diagonally repeats). Needs numpy; skipped
    without it."""
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return ['checker_unavailable: checkerboard inspection needs numpy and Pillow; run this check with an environment containing both; this page has not passed fake-transparency inspection']
    shot = screenshot_of(d)
    if not shot.is_file():
        return []
    im = Image.open(shot).convert('L')
    W0, H0 = im.size
    f = max(1, round(W0 / 400.0))
    if f > 1:
        im = im.resize((W0 // f, H0 // f), Image.BILINEAR)
    g = np.asarray(im, dtype=np.float32)
    H, W = g.shape
    win = 24
    hb, wb = H // win, W // win
    if hb < 1 or wb < 1:
        return []

    def vario(dx, dy):
        a = g[:H - dy, :W - dx]
        b = g[dy:, dx:]
        v = np.zeros((H, W), np.float32)
        v[:H - dy, :W - dx] = (a - b) ** 2
        return v[:hb * win, :wb * win].reshape(hb, win, wb, win).mean(axis=(1, 3))

    cache = {}

    def v(dx, dy):
        if (dx, dy) not in cache:
            cache[(dx, dy)] = vario(dx, dy)
        return cache[(dx, dy)]

    flagged = np.zeros((hb, wb), bool)
    for s_ in range(2, 13):
        vx, vy, vd = v(s_, 0), v(0, s_), v(s_, s_)
        vx2 = np.minimum.reduce([v(k, 0) for k in (2 * s_ - 1, 2 * s_, 2 * s_ + 1)])
        vy2 = np.minimum.reduce([v(0, k) for k in (2 * s_ - 1, 2 * s_, 2 * s_ + 1)])
        flagged |= (vx > 60) & (vy > 60) & (vx2 < 0.25 * vx) & (vy2 < 0.25 * vy) & (vd < 0.35 * vx)
    ys, xs = np.nonzero(flagged)
    keep = []
    for y, x in zip(ys.tolist(), xs.tolist()):
        cx, cy = (x + 0.5) * win / W, (y + 0.5) * win / H
        if any(CHECKER_OK.search(n['name'] + ' ' + str(n['comps'].get('sprite', {}).get('frame', ''))) and
               n['rect'][0] <= cx <= n['rect'][0] + n['rect'][2] and n['rect'][1] <= cy <= n['rect'][1] + n['rect'][3] for n in nodes):
            continue
        keep.append((cx, cy))
    share = len(keep) * win * win / float(W * H)
    if len(keep) < 3 or share < 0.004:
        return []
    mx, my = sum(p[0] for p in keep) / len(keep), sum(p[1] for p in keep) / len(keep)
    holder = sorted((n for n in nodes if 'sprite' in n['comps'] and n['rect'][0] <= mx <= n['rect'][0] + n['rect'][2] and
                     n['rect'][1] <= my <= n['rect'][1] + n['rect'][3]), key=lambda n: area(n['rect']))
    return ['checker_fill: a checkerboard pattern (the fake "transparent" squares an image generator paints) covers %.1f%% of the '
            'screen around %s: regenerate the picture with a real transparent background (alpha) or cut the background out, '
            'and check the PNG is alpha 0 there - card insides are painted art, never a checkerboard (user 2026-10-23)'
            % (100 * share, holder[0]['path'] if holder else 'x=%.2f y=%.2f' % (mx, my))]


def font_advance_problems(proj):
    """Require visible separation between adjacent BMFont glyphs after outlines and shadows are rasterized.

    User 2026-10-24: a timer's glyph boxes did not geometrically overlap, but the rendered strokes crowded together.
    xadvance must leave max(2px, 10% of lineHeight) after the visible glyph box, not merely equal its width.
    """
    out = []
    base = proj / 'assets'
    if not base.is_dir():
        return out
    for f in sorted(base.rglob('*.fnt')):
        rel = f.relative_to(proj).as_posix()
        if any(p in rel.split('/') for p in ('node_modules', 'library', 'temp', 'build')) or f.stat().st_size > 2_000_000:
            continue
        bad = []
        try:
            lines = f.read_text(encoding='utf-8', errors='ignore').splitlines()
        except OSError:
            continue
        line_height = 0
        for line in lines:
            if line.startswith('common '):
                kv = dict(re.findall(r'(\w+)=(-?\d+)', line))
                try:
                    line_height = int(kv.get('lineHeight', 0))
                except ValueError:
                    line_height = 0
                break
        min_gap = max(2, int(line_height * 0.1 + 0.999)) if line_height > 0 else 2
        for line in lines:
            if not line.startswith('char '):
                continue
            kv = dict(re.findall(r'(\w+)=(-?\d+)', line))
            try:
                cid, w, xo, adv = int(kv['id']), int(kv['width']), int(kv.get('xoffset', 0)), int(kv['xadvance'])
            except (KeyError, ValueError):
                continue
            gap = adv - (xo + w)
            if w > 0 and gap < min_gap:
                bad.append('%s (width %d, xadvance %d, gap %d; need >= %d)' %
                           (chr(cid) if 32 < cid < 127 else cid, w, adv, gap, min_gap))
        if bad:
            out.append('font_advance: %s - glyph %s leave too little visible space, so outlines/shadows crowd adjacent letters or digits: '
                       'set xadvance >= xoffset + width + max(2, 0.1 * lineHeight) using trimmed glyph bounds (user 2026-10-24)'
                       % (rel, ', '.join(bad[:6])))
    return out


CLOCK_TEXT = re.compile(r'^\s*\d{1,2}(?::\d{2}){1,2}\s*$')
MIN_CLOCK_GAP_CSS = 2.5


def clock_glyph_clearance_problems(d, project):
    """Check changing clock labels at their actual phone scale, not only in .fnt source pixels.

    The v18 asset-only xadvance rule can pass a font whose gap becomes too small after BMFont, node,
    Canvas and viewport scaling. A clock such as 04:06 can then look like 4:6 even though node boxes
    do not overlap. Use the paired runtime dump's transformed box and CSS viewport dimensions.
    """
    out = []
    clock_nodes = []
    for n in d.get('nodes', []):
        label = n.get('comps', {}).get('label') or {}
        value = str(label.get('string', ''))
        if CLOCK_TEXT.fullmatch(value) and label.get('font_kind') == 'bitmap':
            clock_nodes.append((n, label, value))
    if not clock_nodes:
        return out

    shot = screenshot_of(d)
    css = d.get('canvas_css')
    if not shot.is_file() or not isinstance(css, list) or len(css) < 4 or not isinstance(css[2], (int, float)) or css[2] <= 0:
        return ['checker_unavailable: timer glyph spacing needs its paired screenshot and canvas_css viewport dimensions']

    font_files = []
    asset_root = Path(project) / 'assets'
    for f in asset_root.rglob('*.fnt') if asset_root.is_dir() else []:
        if any(p in f.parts for p in ('node_modules', 'library', 'temp', 'build')) or f.stat().st_size > 2_000_000:
            continue
        try:
            lines = f.read_text(encoding='utf-8', errors='ignore').splitlines()
        except OSError:
            continue
        info = next((line for line in lines if line.startswith('info ')), '')
        face_match = re.search(r'\bface="([^"]+)"', info)
        size_match = re.search(r'\bsize=(-?\d+)', info)
        if not face_match or not size_match or int(size_match.group(1)) == 0:
            continue
        metrics, kernings = {}, {}
        for line in lines:
            if line.startswith('char '):
                kv = dict(re.findall(r'(\w+)=(-?\d+)', line))
                try:
                    metrics[int(kv['id'])] = (int(kv.get('width', 0)), int(kv.get('xoffset', 0)), int(kv['xadvance']))
                except (KeyError, ValueError):
                    pass
            elif line.startswith('kerning '):
                kv = dict(re.findall(r'(\w+)=(-?\d+)', line))
                try:
                    kernings[(int(kv['first']), int(kv['second']))] = int(kv['amount'])
                except (KeyError, ValueError):
                    pass
        font_files.append((f.stem, face_match.group(1), abs(int(size_match.group(1))), metrics, kernings))

    norm = lambda value: re.sub(r'[^a-z0-9]', '', str(value).lower())
    for n, label, value in clock_nodes:
        font_name = norm(label.get('font', ''))
        matches = [font for font in font_files if font_name and font_name in (norm(font[0]), norm(font[1]))]
        if len(matches) != 1:
            out.append('checker_unavailable: %s clock font "%s" has no unique matching .fnt metrics'
                       % (n.get('path', n.get('name', 'timer')), label.get('font', '')))
            continue
        _, _, face_size, metrics, kernings = matches[0]
        rect = n.get('screen') or n.get('rect')
        try:
            label_width = float(label.get('width', 0))
            transformed_width = float(rect[2]) * float(css[2])
            actual_font_size = float(label.get('actualFontSize') or label.get('fontSize'))
            spacing = float(label.get('spacingX') or 0)
            if not rect or label_width <= 0 or transformed_width <= 0 or actual_font_size <= 0:
                raise ValueError
        except (TypeError, ValueError, IndexError):
            out.append('checker_unavailable: %s clock label has no usable runtime size/transform data'
                       % n.get('path', n.get('name', 'timer')))
            continue
        transform = transformed_width / label_width
        gaps = []
        missing = []
        for left, right in zip(value.strip(), value.strip()[1:]):
            if ord(left) not in metrics or ord(right) not in metrics:
                missing.extend(ch for ch in (left, right) if ord(ch) not in metrics)
                continue
            width, offset, advance = metrics[ord(left)]
            _, next_offset, _ = metrics[ord(right)]
            gap_units = advance + kernings.get((ord(left), ord(right)), 0) + next_offset - (offset + width)
            # Cocos 2.4 applies Label.spacingX after scaling the BMFont xAdvance, in node-local units.
            # Keep those units separate before converting both parts through the runtime transform.
            gaps.append((gap_units * actual_font_size / face_size + spacing) * transform)
        path = n.get('path', n.get('name', 'timer'))
        if missing or not gaps:
            out.append('checker_unavailable: %s clock .fnt does not contain every displayed glyph'
                       % path)
            continue
        smallest = min(gaps)
        if smallest < MIN_CLOCK_GAP_CSS:
            out.append('font_advance_rendered: "%s" (%s) has only %.2f CSS px between adjacent bitmap glyphs after phone scaling '
                       '(needs >= %.1f px): increase the timer Label spacing/font fit, then recheck the same live state at both '
                       'phone widths; source .fnt xadvance alone can pass while digits visually crowd together'
                       % (value.strip(), path, smallest, MIN_CLOCK_GAP_CSS))
    return out


def decor(n):
    """Small marks that may overlap on purpose (sparkles, badges, red dots, lock/gift marks); "lightning" is not "light"."""
    return any(t.lower() in DECOR for t in NAME_TOKENS.findall(n['name'] + ' ' + str(n['comps'].get('sprite', {}).get('frame', ''))))


def inter(a, b):
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def panel_fill_block(box, nodes):
    """A flat connected patch inside a named main panel is panel whitespace unless it matches its own visible surface."""
    contains = lambda outer, inner: (inner[0] >= outer[0] - 0.01 and inner[1] >= outer[1] - 0.01 and
                                     inner[0] + inner[2] <= outer[0] + outer[2] + 0.01 and
                                     inner[1] + inner[3] <= outer[1] + outer[3] + 0.01)
    panels = [n for n in nodes if str(n['name']).lower() in ('panelsurface', 'panelart', 'panel', 'resultpanel') and
              ('graphics' in n['comps'] or 'sprite' in n['comps']) and area(n['rect']) >= 0.12]
    if not any(contains(n.get('screen') or n['rect'], box) for n in panels):
        return False
    block_area = area(box)
    if block_area <= 0:
        return False
    # Preserve the placeholder warning when a separate Sprite/Graphics shape occupies this patch;
    # ignore only true full-screen backdrops, which geometrically cover every point in the panel.
    def matching_surface(n):
        r = n.get('screen') or n['rect']
        full_screen = r[0] <= 0.05 and r[1] <= 0.05 and r[0] + r[2] >= 0.95 and r[1] + r[3] >= 0.95
        return (str(n['name']).lower() not in ('panelsurface', 'panelart', 'panel', 'resultpanel') and not full_screen and
                ('graphics' in n['comps'] or 'sprite' in n['comps']) and
                inter(box, r) / block_area >= 0.65)
    return not any(matching_surface(n) for n in nodes)


def background_only_block(box, nodes):
    """Do not call a flat sky/wallpaper patch a UI placeholder when it has no surface over it."""
    block_area = area(box)
    if block_area <= 0:
        return False
    backdrops = []
    for n in nodes:
        name = str(n.get('name', '')).lower()
        frame = str(n.get('comps', {}).get('sprite', {}).get('frame', '')).lower()
        identity = name + ' ' + frame
        if re.search(r'bgshade|overlay|dim|shade', identity):
            continue
        if not BACKGROUND_NAME.search(identity):
            continue
        rect = n.get('screen') or n.get('rect')
        if rect and inter(box, rect) / block_area >= 0.98 and area(rect) >= 0.85:
            backdrops.append(n)
    if not backdrops:
        return False
    # A real flat placeholder remains reportable: its own Sprite/Graphics node covers the
    # sampled patch. Ignore only the unadorned pixels from the full-screen backdrop itself.
    for n in nodes:
        identity = str(n.get('name', '')).lower() + ' ' + str(n.get('comps', {}).get('sprite', {}).get('frame', '')).lower()
        if (n in backdrops or re.search(r'bgshade|overlay|dim|shade', identity) or
                not ({'graphics', 'sprite'} & set(n.get('comps', {})))):
            continue
        if n.get('opacity', 1) <= 0.05:
            continue
        rect = n.get('screen') or n.get('rect')
        if rect and inter(box, rect) / block_area >= 0.65:
            return False
    return True


def texted_action_button(button, nodes):
    """Count action labels and baked btn_* art, while allowing the icon_* caption set."""
    descendants = [n for n in nodes if node_under(n, button)]
    for n in descendants:
        if WORDS.search(text(n)) and center_in(n.get('screen') or n['rect'], button.get('screen') or button['rect']):
            return True
        word = baked(n)
        if not word:
            continue
        frame = str(n.get('comps', {}).get('sprite', {}).get('frame', '')).lower()
        if frame.startswith(('icon_', 'ctrl_')):
            continue
        if area(button.get('screen') or button['rect']) >= MIN_BAKED_TEXT_BUTTON:
            return True
    return False


def flat_button_problems(buttons, nodes, img):
    """Measure the rendered button plate, not a wider transparent Button hit box."""
    out = []
    for b in buttons:
        br = b.get('screen') or b['rect']
        plates = [n for n in nodes if node_under(n, b) and
                  ('graphics' in n['comps'] or ('sprite' in n['comps'] and
                   not str(n['comps']['sprite'].get('frame', '')).lower().startswith('txt_'))) and
                  area(n.get('screen') or n['rect']) >= 0.3 * area(br)]
        rendered = max(plates, key=lambda n: area(n.get('screen') or n['rect'])) if plates else b
        r = rendered.get('screen') or rendered['rect']
        if area(r) < 0.004:
            continue
        W, H = img.size
        box = (int(max(0, r[0]) * W), int(max(0, r[1]) * H), int(min(1, r[0] + r[2]) * W), int(min(1, r[1] + r[3]) * H))
        if box[2] - box[0] < 6 or box[3] - box[1] < 6:
            continue
        px = list(img.crop(box).getdata())
        bins = {}
        for p_ in px:
            k = (p_[0] >> 3, p_[1] >> 3, p_[2] >> 3)
            bins[k] = bins.get(k, 0) + 1
        if bins and max(bins.values()) / len(px) >= 0.6:
            frame = str((rendered['comps'].get('sprite') or {}).get('frame', ''))
            out.append('flat_button: %s is one flat colour (%.0f%% of its rendered plate%s): draw it like the rest of the button set '
                       '(rim, gloss, shading, an icon), not a plain rounded box'
                       % (b['path'], 100 * max(bins.values()) / len(px), ' "%s"' % frame if frame else ''))
    return out


def node_under(a, b):
    if '_audit_ancestors' in a and b.get('id'):
        return a is b or b['id'] in a['_audit_ancestors']
    return under(a['path'], b['path'])

def related(a, b):
    return node_under(a, b) or node_under(b, a)


def fully_occluded(node, masks):
    """A higher, full-screen input-blocking modal makes its lower scene inactive for visual audits."""
    r=node['rect'];x=max(0,r[0]);y=max(0,r[1]);visible=[x,y,max(0,min(1,r[0]+r[2])-x),max(0,min(1,r[1]+r[3])-y)]
    size = area(visible)
    if size <= 0:
        return False
    return any(mask.get('order', 0) > node.get('order', 0) and inter(visible, mask['rect']) >= 0.98 * size
               for mask in masks)


def modal_masks(nodes):
    """Full-screen input blockers are the only nodes that can hide a lower screen from visual audits."""
    return [n for n in nodes if area(n['rect']) >= 0.85 and n.get('comps', {}).get('block_input')]


def claim_button(button, nodes):
    """Recognize an actionable Claim plate even when its word is baked into a sprite."""
    names = [button.get('name', ''), button.get('path', '')]
    for n in nodes:
        if node_under(n, button):
            names.append(str((n.get('comps', {}).get('sprite') or {}).get('frame', '')))
    words_ = {word.lower() for value in names for word in re.split(r'[^a-z0-9]+', value) if word}
    return bool(words_ & {'claim', 'claimed'})


MAX_ICON_BUTTON = 0.045     # feature/icon buttons (bigger ones are main buttons)


def caption_style_problems(d, nodes, buttons, image_module):
    """User 2026-10-23 (both boards): five home feature buttons made four different ways - LEVELS picture text on a white
    ribbon, SOUVENIRS picture text on a teal ornate ribbon, SETTINGS typed with a font and no plate, HOME SCREEN +2 and
    PROFILE REVISIT +2 typed on cloud plates. Buttons of one group (similar size, next to each other) share ONE caption
    style: the same way of making it (baked into the icon picture, or the same generated caption plate + picture text),
    the same plate, the same colours."""
    # The shared caption-style rule is for feature entrances. Utility and primary action controls
    # (for example Close next to Claim) have different roles and are not one caption group.
    utility = re.compile(r'(?:^|/)(?:btn_)?(?:close|back|pause|plus|minus|claim|claimed|retry|continue|confirm|cancel|submit|start|play|plate|pack|sell)$', re.I)
    icons = [b for b in buttons if area(b['rect']) <= MAX_ICON_BUTTON and b['rect'][2] > 0 and
             not utility.search(b.get('path', b.get('name', '')))]
    # Numeric resource capsules and numbered map nodes are values, not feature captions.
    icons = [b for b in icons if not (
        any(text(n) for n in nodes if n is not b and node_under(n, b)) and
        not any(WORDS.search(text(n)) or baked(n) for n in nodes if n is not b and node_under(n, b)))]
    if len(icons) < 2:
        return []
    shot = screenshot_of(d) if d.get('_file') else None
    img = image_module.open(shot).convert('RGB') if image_module is not None and shot is not None and shot.is_file() else None
    in_other = lambda n, b: any(under(n['path'], o['path']) for o in buttons if o is not b)

    texts = [m for m in nodes if text(m)]

    def holds_text(n):       # a caption plate ("caption_cloud") holds a word; it is not a word itself
        r = n.get('screen') or n['rect']
        return any(m is not n and center_in(m.get('screen') or m['rect'], r) for m in texts)

    def is_word(n):          # a caption has words; numbers next to a button are values, not captions
        return bool(WORDS.search(text(n)) or baked(n)) or (wordlike(n) and not text(n) and not holds_text(n))

    def caption(b):
        r = b.get('screen') or b['rect']
        found = []
        owns_caption = any(n is not b and node_under(n, b) and is_word(n) and not in_other(n, b) for n in nodes)
        for n in nodes:
            if n is b or not is_word(n) or countdown_hint(n, nodes) or in_other(n, b):
                continue
            q = n.get('screen') or n['rect']
            cx, cy = q[0] + q[2] / 2, q[1] + q[3] / 2
            inside = node_under(n, b)
            below = r[0] - 0.3 * r[2] <= cx <= r[0] + 1.3 * r[2] and r[1] + 0.75 * r[3] <= cy <= r[1] + 1.9 * r[3]
            if inside or (below and not owns_caption):
                found.append(n)
        sig, plate_family = set(), None
        for n in found:
            lab = n['comps'].get('label') or n['comps'].get('richtext')
            sig.add('font label' if lab and not bitmap_font(n['comps'].get('label') or {}) else 'bitmap label' if lab else 'picture text')
            q = n.get('screen') or n['rect']
            cx, cy = q[0] + q[2] / 2, q[1] + q[3] / 2
            plates = [m for m in nodes if 'sprite' in m['comps'] and not is_word(m) and m is not b and not under(b['path'], m['path'])
                      and 'button' not in m['comps'] and not in_other(m, b) and area(m['rect']) < 0.05
                      and area(m['rect']) >= 0.8 * area(q) and center_in(q, m.get('screen') or m['rect'])]
            if plates:
                plate = min(plates, key=lambda m: area(m['rect']))
                fam = str(plate['comps']['sprite'].get('frame', '')).lower()
                for w in re.findall(r'[a-z]+', text(n).lower()):
                    fam = fam.replace(w, '')
                plate_family = re.sub(r'[\d_\-\s]+', '_', fam).strip('_') or 'plate'
        if not found:
            kind = 'baked into the icon picture'
        else:
            kind = ' + '.join(sorted(sig)) + (' on plate "%s"' % plate_family if plate_family else '')
        ink = None
        if img is not None:
            inks = {caption_ink_class(img, n.get('screen') or n['rect']) if baked(n) else ink_class(img, n.get('screen') or n['rect']) for n in found if 'label' not in n['comps']}
            inks.discard(None)
            ink = ','.join(sorted(inks)) or None
        return kind, ink, found

    # group: similar size and close to each other (same row, column or within 2.5 button widths), linked transitively
    info = {b['path']: caption(b) for b in icons}
    groups, seen = [], set()
    for b in icons:
        if b['path'] in seen:
            continue
        group, stack = [], [b]
        seen.add(b['path'])
        while stack:
            x = stack.pop(); group.append(x)
            rx = x.get('screen') or x['rect']
            for y in icons:
                if y['path'] in seen:
                    continue
                ry = y.get('screen') or y['rect']
                if not 0.6 <= ry[2] / max(rx[2], 1e-6) <= 1.67:
                    continue
                dx = abs((rx[0] + rx[2] / 2) - (ry[0] + ry[2] / 2))
                dy = abs((rx[1] + rx[3] / 2) - (ry[1] + ry[3] / 2))
                if dy <= 0.6 * rx[3] or dx <= 0.6 * rx[2] or (dx * dx + dy * dy) ** 0.5 <= 2.5 * max(rx[2], rx[3]):
                    seen.add(y['path']); stack.append(y)
        if len(group) >= 2:
            groups.append(group)
    out = []
    for g in groups:
        # A generated button image is the complete caption. Dynamic Cocos labels may
        # remain as inactive descendants in dump metadata, so classify this exact
        # button family by its visible __art_image frame before comparing captions.
        art_button_group = True
        for b in g:
            frame = ''
            for n in nodes:
                if n.get('path') == b.get('path') + '/__art_image':
                    frame = str((n.get('comps', {}).get('sprite') or {}).get('frame', ''))
                    break
            if not frame.startswith('btn_'):
                art_button_group = False
                break
        if art_button_group and len(g) >= 2:
            continue
        captioned = [b for b in g if info[b['path']][2]]
        if len(captioned) < 2:
            continue
        kinds = {}
        for b in captioned:
            kinds.setdefault(info[b['path']][0], []).append(b['name'])
        inks = {info[b['path']][1] for b in captioned if info[b['path']][1]}
        if len(kinds) > 1:
            out.append('mixed_caption_style: the buttons %s are one group but their captions are made %d different ways (%s): '
                       'make every caption the same way - baked into each icon picture in one style, or the same generated '
                       'caption plate with picture text for all (user 2026-10-23)'
                       % (', '.join(b['name'] for b in g), len(kinds),
                          '; '.join('%s: %s' % (k, '/'.join(v[:3])) for k, v in kinds.items())))
        elif len(inks) > 1:
            out.append('mixed_caption_style: the captions of %s are different colours (%s): one group, one caption style and colour'
                       % (', '.join(b['name'] for b in captioned), ' vs '.join(sorted(inks))))
    return out


def overlap_problems(nodes, buttons, full):
    """User 2026-10-23 (energy capsule "20" drawn over the lightning icon in a thin font, a coin pile hanging off the left
    end of the WATCH AD button, "WATCH AD · DOUBLE COINS" typed as a small caption under it): every time pictures and
    words are put together, check that nothing clips into anything else (穿模).
      overlap_text_picture  text over a picture that is not its background (>= 15% of the text box on an icon/picture)
      overlap_text          two texts over each other (>= 20% of the smaller one)
      overlap_buttons       two buttons over each other (>= 10% of the smaller one)
      clip_out              a picture inside a button or capsule sticking out of it by more than 35% of its own size
      text_outside          a number/text inside a capsule sticking out of it (buttons: checked in check() as before)
      action_caption        the main action ("WATCH AD", "PLAY", "CLAIM" ...) written as a small caption under a button:
                            the action word is on the generated button picture; captions only explain (e.g. "x2 coins")"""
    out = []
    pics = [n for n in nodes if 'sprite' in n['comps'] and not text(n) and not baked(n) and n not in full and area(n['rect']) < 0.3
            and not decor(n)]
    texts = [n for n in nodes if text(n)]
    for t in texts:
        at = area(t['rect'])
        if at <= 0:
            continue
        for p in pics:
            if related(t, p) or 'button' in p['comps']:
                continue
            # Dynamic values centered in an art-backed resource/timer well, and image-text
            # rendered on an explicit contrast plate, are meant to overlap those backing
            # surfaces. Keep checking sibling icons and stickers; only exempt the exact
            # same-parent, named plate relationship.
            holder = parent_of(t).rsplit('/', 1)[-1]
            same_parent = parent_of(t) == parent_of(p)
            intentional_text_plate = same_parent and (
                (p['name'] == '__art_image' and
                 holder in {'bar_seconds', 'level_badge', 'map_level', 'map_power', 'map_key', 'power', 'key'} or holder.startswith('day_') or holder.startswith('reward_capsule_')) or
                (p['name'] == '__art_value_plate' and
                 holder in {'bar_crash', 'bar_seconds', 'level_badge', 'map_level', 'map_power', 'map_key', 'power', 'key'} or holder.startswith('day_') or holder.startswith('reward_capsule_')) or
                p['name'] == '__art_contrast_plate'
            )
            if intentional_text_plate:
                continue
            i = inter(t['rect'], p['rect'])
            if not i or (area(p['rect']) >= 2.5 * at and i >= 0.8 * at):   # the plate/panel the text sits on
                continue
            if i >= 0.15 * at:
                out.append('overlap_text_picture: "%s" (%s) is drawn over the picture %s (%.0f%% of the text box): move the text into '
                           'the free part of its capsule/plate or make the plate bigger - text and pictures must not clip into each '
                           'other (user 2026-10-23: the energy "20" on the lightning icon)' % (text(t)[:20], t['path'], p['path'], 100 * i / at))
                break
    for i_, a in enumerate(texts):
        for b in texts[i_ + 1:]:
            small = min(area(a['rect']), area(b['rect']))
            if not related(a, b) and small > 0 and inter(a['rect'], b['rect']) >= 0.2 * small:
                out.append('overlap_text: "%s" and "%s" are drawn over each other (%s, %s)' % (text(a)[:16], text(b)[:16], a['path'], b['path']))
    real = [b for b in buttons if area(b['rect']) < 0.5]
    for i_, a in enumerate(real):
        for b in real[i_ + 1:]:
            small = min(area(a['rect']), area(b['rect']))
            if not related(a, b) and small > 0 and inter(a['rect'], b['rect']) >= 0.1 * small:
                out.append('overlap_buttons: %s and %s overlap (%.0f%% of the smaller one): give every button its own space'
                           % (a['path'], b['path'], 100 * inter(a['rect'], b['rect']) / small))
    holders = [n for n in nodes if 'sprite' in n['comps'] and n not in full and 0 < area(n['rect']) < MAX_HOLDER and
               ('button' in n['comps'] or any(m is not n and node_under(m, n) for m in nodes) or card_like(n))]
    for c in holders:
        cr = c['rect']
        for d_ in nodes:
            if d_ is c or area(d_['rect']) < 0.0015 or decor(d_):
                continue
            if not node_under(d_, c):     # a reward picture laid on a card as its sibling (user 2026-10-23: day-7 car)
                if not (card_like(c) and parent_of(d_) == parent_of(c) and d_.get('order', 0) > c.get('order', 0) and
                        'sprite' in d_['comps'] and not text(d_) and center_in(d_['rect'], cr) and area(d_['rect']) < area(cr)):
                    continue
            r = d_['rect']
            ox = (max(0.0, cr[0] - r[0]) + max(0.0, r[0] + r[2] - cr[0] - cr[2])) / r[2] if r[2] else 0
            oy = (max(0.0, cr[1] - r[1]) + max(0.0, r[1] + r[3] - cr[1] - cr[3])) / r[3] if r[3] else 0
            if text(d_):
                below = r[1] >= cr[1] + cr[3] * 0.9               # a caption under an icon (checked by action_caption)
                if 'button' not in c['comps'] and not below and max(ox, oy) > 0.10:
                    out.append('text_outside: "%s" sticks out of its capsule %s: keep numbers inside the free part of the capsule'
                               % (text(d_)[:20], c['path']))
                continue
            if 'sprite' in d_['comps'] and max(ox, oy) > MAX_STICK_OUT:
                # Tutorial hand cursors intentionally overlap the vehicle they ask the player
                # to drag. They are not decorative art escaping a button or capsule.
                frame = str(d_['comps']['sprite'].get('frame', '')).lower()
                if (frame == 'item_hand' and d_['name'] == 'tip' and
                        '/board/Car0/tip' in d_['path']):
                    continue
                out.append('clip_out: %s sticks out of %s by %.0f%% of its size (max 35%%): pictures stay on their button/capsule - '
                           'regenerate the button as one picture with everything inside, or move/shrink it (user 2026-10-23: the coin '
                           'pile hanging off WATCH AD)' % (d_['path'], c['path'], 100 * max(ox, oy)))
    for b in real:
        if area(b['rect']) < MIN_BAKED_TEXT_BUTTON:
            continue
        br = b['rect']
        for t in texts:
            if countdown_hint(t, nodes):
                continue
            r = t['rect']
            if node_under(t, b) and r[1] < br[1] + br[3] * 0.9:
                continue
            if not (br[1] + br[3] * 0.9 <= r[1] <= br[1] + br[3] + 2.5 * r[3] + 0.01 and inter([r[0], br[1], r[2], br[3]], br) > 0):
                continue
            own = ' '.join(words(n) for n in nodes if node_under(n, b) and n is not t).lower()
            first = re.split(r'[·•|,:\-]', text(t))[0].strip().lower()
            if ACTION_WORDS.match(text(t)) or (len(first) >= 3 and first in own):
                out.append('action_caption: "%s" (%s) is the main action written as a small caption under %s: the action words are '
                           'on the generated button picture itself; a caption under a button only explains (e.g. "x2 coins") and is '
                           'generated picture text too (user 2026-10-23: "WATCH AD · DOUBLE COINS")' % (text(t)[:30], t['path'], b['path']))
    return out


def hue_class(rgb):
    """Colour family of a text fill: 'neutral' (white/cream/grey/black, low chroma) or one of 12 hue bins of 30 degrees."""
    if max(rgb) - min(rgb) < 40:
        return 'neutral'
    h, _l, _s = colorsys.rgb_to_hls(*(c / 255.0 for c in rgb))
    return 'hue%d' % (int(h * 360 + 15) % 360 // 30 * 30)


def caption_ink_class(img, r):
    """Whole baked captions include a coloured plate. Compare their bright letter faces,
    not the dominant plate hue. Cream/white faces share one neutral colour family."""
    W,H=img.size
    box=img.crop((int(max(0,r[0])*W),int(max(0,r[1])*H),int(min(1,r[0]+r[2])*W),int(min(1,r[1]+r[3])*H)))
    px=[p for p in box.getdata() if lstar(p)>=88]
    if len(px)<12:
        return ink_class(img,r)
    count={}
    for p in px:
        key='neutral' if min(p)>=175 else hue_class(p)
        count[key]=count.get(key,0)+1
    return max(count,key=count.get)


def ink_class(img, r):
    """Fill colour family of text measured on the screenshot: the glyph pixels (L* differs >= 15 from just outside the
    box) that are light (L* >= 50; the fill, not the outline) - the most common colour family among them."""
    W, H = img.size
    x0, y0 = int(max(0, r[0]) * W), int(max(0, r[1]) * H)
    x1, y1 = int(min(1, r[0] + r[2]) * W), int(min(1, r[1] + r[3]) * H)
    if x1 - x0 < 6 or y1 - y0 < 6:
        return None
    m = max(3, (y1 - y0) // 3)
    ring = []
    for (a0, b0, a1, b1) in ((x0 - m, y0 - m, x1 + m, y0), (x0 - m, y1, x1 + m, y1 + m), (x0 - m, y0, x0, y1), (x1, y0, x1 + m, y1)):
        a0, b0, a1, b1 = max(0, a0), max(0, b0), min(W, a1), min(H, b1)
        if a1 - a0 > 0 and b1 - b0 > 0:
            ring += list(img.crop((a0, b0, a1, b1)).getdata())
    if len(ring) < 8:
        return None
    ring = ring[::max(1, len(ring) // 2000)]
    bg = sorted(lstar(p) for p in ring)[len(ring) // 2]
    box = list(img.crop((x0, y0, x1, y1)).getdata())
    box = box[::max(1, len(box) // 4000)]
    ink = [p for p in box if abs(lstar(p) - bg) >= 15]
    fill = [p for p in ink if lstar(p) >= 50] or ink
    if len(fill) < 12:
        return None
    count = {}
    for p in fill:
        c = hue_class(p)
        count[c] = count.get(c, 0) + 1
    return max(count, key=count.get)


def colour_problems(d, nodes, image_module):
    """User 2026-10-23 bad examples: the "Hazel's Shelf Scramble" home where the title, PLAY and the numbers 100 / 3 are all
    the same teal, and the "Your Progress" popup where every word is the same orange-yellow with a brown outline. Titles,
    buttons, numbers and labels share one style family but differ in colour (and size/shape). Text items are grouped by
    their node name (a list of rank rows is one item); with >= 3 items all in one colour family the page fails."""
    shot = screenshot_of(d) if d.get('_file') else None
    img = image_module.open(shot).convert('RGB') if image_module is not None and shot is not None and shot.is_file() else None
    groups = {}
    for n in nodes:
        lab = n['comps'].get('label') or n['comps'].get('richtext')
        if not text(n) or (lab and len(text(n)) > DENSE_TEXT):
            continue
        cls = None
        col = (n['comps'].get('label') or {}).get('color')
        if n['comps'].get('label') and not bitmap_font(n['comps']['label']) and isinstance(col, list) and len(col) == 3:
            cls = hue_class(col)
        elif img is not None:
            cls = ink_class(img, n.get('screen') or n['rect'])
        if cls is not None:
            groups.setdefault(n['name'], (cls, text(n)[:16]))
    classes = {c for c, _ in groups.values()}
    if len(groups) >= 3 and len(classes) == 1:
        c = classes.pop()
        return ['uniform_text_colour: all %d text items are the same colour (%s: %s): give the title, buttons, numbers and labels '
                'different fill colours (one style family, varied colours, sizes and letter shapes; user 2026-10-23: the all-teal '
                '"Hazel\'s Shelf Scramble" home, the all-orange "Your Progress" popup)'
                % (len(groups), 'white/neutral' if c == 'neutral' else 'hue ~%s deg' % c[3:], ', '.join(t for _, t in list(groups.values())[:4]))]
    return []


def dark_green(rgb):
    """User 2026-10-22: dark green / teal / slate text drawn with a font ("COINS 47", "Price · 250 coins", "BRILLIANT!")."""
    h, l, sat = colorsys.rgb_to_hls(*(c / 255.0 for c in rgb))
    return 80 <= h * 360 <= 210 and lstar(rgb) < 55 and sat >= 0.12


def runtime_text(path):
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path, '*/' + g) for g in RUNTIME_TEXT)


def under(path, prefix):
    return path == prefix or path.startswith(prefix + '/')


def load(folders):
    dumps = []
    for folder in folders:
        for f in sorted(Path(folder).rglob('*ui-dump-*.json')):
            try:
                d = json.loads(f.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            if isinstance(d, dict) and d.get('tool') == 'ui_dump' and d.get('producer') in {'chrome_touch.dump_ui', 'ego_page.dump_ui'} and d.get('schema') == 1 and isinstance(d.get('nodes'), list) and not d.get('error'):
                d['_file'] = str(f)
                dumps.append(d)
    return dumps


def screenshot_of(d):
    f = Path(d['_file'])
    name = d.get('screenshot') or f.name.replace('-ui-dump-', '-ui-').rsplit('.', 1)[0] + '.png'
    return f.parent / name


def flat_background(d, image_module):
    shot = screenshot_of(d)
    if not shot.is_file():
        return ['no_screenshot: %s is missing (chrome_touch saves it with every dump_ui)' % shot.name], None
    m = audit_dark_area.measure(shot, image_module)
    if m['flat_ratio'] > MAX_FLAT or m['plain_block_ratio'] > MAX_PLAIN_BLOCK:
        return ['flat_background: one plain colour covers %.0f%% of the screen (largest plain block %.0f%%; limits 40%%/35%%): '
                'make a background picture, a simple gradient with clouds/pattern/scenery in the game style is enough'
                % (m['flat_ratio'] * 100, m['plain_block_ratio'] * 100)], m
    return [], m


def busy_background(d, content):
    """Measure background edge density without an optional NumPy dependency."""
    try:
        from PIL import Image
    except ImportError:
        return ['checker_unavailable: busy_background requires Pillow'], None
    shot = screenshot_of(d)
    if not shot.is_file():
        return ['checker_unavailable: busy_background screenshot is missing'], None
    im = Image.open(shot).convert('L')
    w, h = im.size
    H = max(2, round(BUSY_WIDTH * h / float(w)))
    im = im.resize((BUSY_WIDTH, H), Image.BOX)
    pixels = list(im.getdata())
    ew, eh = BUSY_WIDTH - 1, H - 1
    keep = bytearray([1]) * (ew * eh)
    for n in content:
        r = n.get('screen') or n['rect']
        x0, y0 = max(0, int(r[0] * BUSY_WIDTH) - 1), max(0, int(r[1] * H) - 1)
        x1, y1 = min(ew, int((r[0] + r[2]) * BUSY_WIDTH) + 2), min(eh, int((r[1] + r[3]) * H) + 2)
        if x1 > x0 and y1 > y0:
            for y in range(y0, y1):
                keep[y * ew + x0:y * ew + x1] = bytes(x1 - x0)
    eligible = sum(keep)
    if eligible < 0.25 * len(keep):
        return [], None
    edges = 0
    for y in range(eh):
        for x in range(ew):
            if keep[y * ew + x]:
                i = y * BUSY_WIDTH + x
                edges += max(abs(pixels[i + 1] - pixels[i]), abs(pixels[i + BUSY_WIDTH] - pixels[i])) > BUSY_STEP
    share = edges / eligible
    if share > MAX_BUSY:
        return ['busy_background: the background is too detailed (%.0f%% of it is edges, max %.0f%%; user 2026-10-23, the Metro '
                'Switch home: a painted plaza full of small things, the dark title and plain buttons disappear in it): draw a calm '
                'background - big soft shapes, gradients, a few clouds or blurred scenery - so the title logo and the buttons '
                'stand out' % (share * 100, MAX_BUSY * 100)], round(share, 3)
    return [], round(share, 3)


def canvas_text_code(proj):
    """User 2026-10-23: a RasterText.ts drew the dynamic words with Canvas fonts (ctx.fillText) - that is typed text, not
    generated picture text. Game scripts under assets/ must not draw text on a Canvas; a script that really has to (run-time
    text only, with a reason) is listed in docs/text/runtime-text.json "canvas_text_files": [{"file": ..., "why": ...}]."""
    out = []
    base = proj / 'assets'
    if not base.is_dir():
        return out
    for f in sorted(base.rglob('*')):
        if f.suffix not in ('.ts', '.js') or not f.is_file() or f.stat().st_size > 2_000_000:
            continue
        rel = f.relative_to(proj).as_posix()
        if any(p in rel.split('/') for p in ('node_modules', 'library', 'temp', 'build')) or \
                any(fnmatch.fnmatch(rel, g) or rel.endswith('/' + g.lstrip('./')) or rel == g.lstrip('./') for g in CANVAS_TEXT_FILES):
            continue
        try:
            code = f.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        hits = [i + 1 for i, line in enumerate(code.splitlines()) if CANVAS_TEXT_CODE.search(line)]
        if hits:
            out.append('canvas_font_code: %s draws text on a Canvas with a font (fillText/strokeText, line %s): all words are '
                       'generated picture text and numbers a generated bitmap font; remove it (only real run-time text may stay, '
                       'listed with a reason in docs/text/runtime-text.json "canvas_text_files"; user 2026-10-23)'
                       % (rel, ', '.join(map(str, hits[:5]))))
    return out


def check(d, image_module=None, project=None, binding=None):
    from official_loading import audit as audit_official_loading
    official = audit_official_loading(d, project, image_module, binding)
    if official is not None:
        problems, stats = official
        if problems:
            return problems, stats
        # Presentation exception only: clarity, geometry, readable text and overlap
        # retain the same assertions as ordinary pages. No game-quality pass is cached.
        nodes = [n for n in d.get('nodes', []) if n.get('opacity', 1) > 0.05]
        full = [n for n in nodes if area(n['rect']) >= 0.85]
        buttons = [n for n in nodes if 'button' in n.get('comps', {})]
        # An authenticated official brand image is not generated game picture text.
        readable = [n for n in nodes if not ('sprite' in n.get('comps', {}) and not text(n))]
        problems += [v for v in text_problems(d, readable, buttons, image_module)
                     if v.split(':', 1)[0] not in {'plain_text', 'font_text', 'font_number', 'text_arrow'}]
        problems += squash_problems(nodes, full) + low_res_problems(nodes, full)
        problems += overlap_problems(nodes, buttons, full) + glyph_problems(nodes)
        if project is not None:
            problems += clock_glyph_clearance_problems(d, project)
        if image_module is not None:
            problems += checker_problems(d, nodes)
        return problems, stats
    # Duplicate sibling names are legal Cocos nodes. A textual path is not a unique ancestor ID.
    stack, records = [], []
    for original in d.get('nodes', []):
        n = dict(original)
        while stack and stack[-1].get('depth', 0) >= n.get('depth', 0):
            stack.pop()
        if n.get('id') and 'depth' in n:
            n['_audit_ancestors'] = n.get('ancestor_ids', [a['id'] for a in stack if a.get('id')])
        records.append(n)
        stack.append(n)
    def visible_in_camera(n):
        r = n.get('screen') or n['rect']
        return area(r) > 0 and r[0] < 1 and r[1] < 1 and r[0] + r[2] > 0 and r[1] + r[3] > 0
    nodes = [n for n in records if n.get('opacity', 1) > 0.05 and visible_in_camera(n)]
    all_visual = [n for n in nodes if text(n) or 'sprite' in n['comps'] or 'button' in n['comps']]
    all_pictures = [n for n in all_visual if 'sprite' in n['comps']]
    all_full = [n for n in nodes if area(n['rect']) >= 0.85]
    masks = modal_masks(all_full)
    # Do not audit gameplay/home nodes hidden by an active modal shade; their muted pixels and
    # rectangles otherwise create false low-contrast and overlap defects on the popup above them.
    nodes = [n for n in nodes if not fully_occluded(n, masks)]
    visible = [n for n in nodes if text(n) or 'sprite' in n['comps'] or 'button' in n['comps']]
    full = [n for n in visible if area(n['rect']) >= 0.85]
    # A transparent modal shade leaves the source scene visible in the screenshot,
    # even though its input blocker excludes muted underlay text from overlap checks.
    backdrops = [n for n in all_full if 'sprite' in n['comps'] and n not in masks and
                 not PLAIN_FRAMES.match(str(n['comps']['sprite'].get('frame', '')).lower())]
    content = [n for n in visible if area(n['rect']) < 0.85]
    buttons = [n for n in content if 'button' in n['comps'] and n['comps']['button'].get('interactable', True)]
    pictures = [n for n in content if 'sprite' in n['comps']]
    numbers = [n for n in content if DIGIT.search(text(n))]
    cov = coverage([n.get('screen') or n['rect'] for n in visual_coverage_nodes(content, nodes)])
    problems, pixels = hidden_value_surface_problems(nodes), None
    if image_module is not None:
        flat, pixels = flat_background(d, image_module)
        problems += flat
    # Local text backing audit must run before the gameplay early return.
    if image_module is not None and screenshot_of(d).is_file():
        from check_text_backplates import ui_dump_problems
        problems += ui_dump_problems(d, image_module.open(screenshot_of(d)).convert('RGB'), nodes, words)
    kind, purpose = d.get('kind'), d.get('purpose', 'other')
    reported_numbers = league_number_count(content) if purpose == 'league' else len(numbers)
    pix = {'flat_ratio': pixels['flat_ratio'], 'plain_block_ratio': pixels['plain_block_ratio']} if pixels else {}
    problems += text_problems(d, nodes, [n for n in nodes if 'button' in n['comps']], image_module)
    problems += one_piece_problems(nodes, [n for n in nodes if 'button' in n['comps'] and n['comps']['button'].get('interactable', True)])
    problems += squash_problems(nodes, full) + colour_problems(d, nodes, image_module) + low_res_problems(nodes, full)
    problems += overlap_problems(nodes, [n for n in nodes if 'button' in n['comps'] and n['comps']['button'].get('interactable', True)], full)
    problems += caption_style_problems(d, nodes, [n for n in nodes if 'button' in n['comps'] and n['comps']['button'].get('interactable', True)],
                                       image_module)
    problems += glyph_problems(nodes)
    if project is not None:
        problems += clock_glyph_clearance_problems(d, project)
    if image_module is not None:
        problems += checker_problems(d, nodes)
    content0 = [n for n in visible if area(n['rect']) < 0.85]
    if image_module is not None and not masks and kind != 'popup':
        busy, busy_share = busy_background(d, content0)
        problems += busy
        if busy_share is not None:
            pix['busy_share'] = busy_share
    removed = sorted({n['name'] for n in content0 if removed_feature(n['name'] + ' ' + str((n['comps'].get('sprite') or {}).get('frame', '')), OPTIONAL)})
    if (purpose in ('league', 'checkin') and not OPTIONAL.get(purpose)) or removed:
        problems.append('removed_feature: %s - no ranking/leaderboard, no 7-day check-in, no more-games / cross-promotion '
                        '(user 2026-10-23, both boards): delete the page, its buttons and its code'
                        % ('a %s page' % purpose if purpose in ('league', 'checkin') else ', '.join(removed[:4])))
    if kind == 'gameplay':
        return problems, dict(pix, gameplay=True)
    # Check-in pages have a dedicated seven-card, day-7 and Claim structure check below;
    # their modal panel/background footprint must not be mistaken for an empty full page.
    if len(content) < 5 or (cov < 0.25 and purpose != 'checkin'):
        problems.append('monotonous: only %d visible things covering %.0f%% of the screen (needs >= 5 and >= 25%%): '
                        'add title, reward, stars, mascot or decoration' % (len(content), cov * 100))
    behind = [n for n in all_pictures if not any(under(n['path'], m['path']) for m in masks)]
    composite_bg=[n for n in all_pictures if BACKGROUND_NAME.search(n['name']+' '+str(n['comps']['sprite'].get('frame','')))]
    if not backdrops and coverage([n.get('screen')or n['rect']for n in composite_bg])<.85 and not (masks and len(behind) >= 8):
        problems.append('plain_backdrop: no background picture and no game scene behind (flat colour)')
    for b in buttons:
        sub = [n for n in nodes if node_under(n, b)]
        has_plate = any('sprite' in n['comps'] and area(n['rect']) >= 0.3 * area(b['rect']) for n in sub)
        if not has_plate and any(text(n) for n in sub):
            problems.append('bare_button: %s is only text ("%s"); give it a plate picture' % (b['path'], next(text(n) for n in sub if text(n))[:30]))
    shot_img = None
    if image_module is not None and screenshot_of(d).is_file():
        shot_img = image_module.open(screenshot_of(d)).convert('RGB')
    for b in buttons:
        sub = [n for n in nodes if node_under(n, b)]
        plates = [n for n in sub if 'sprite' in n['comps'] and not text(n)]
        plate = max(plates, key=lambda n: area(n['rect'])) if plates else None
        frame = str(plate['comps']['sprite'].get('frame', '')) if plate else ''
        if BUTTON_SET is not None and plate and not any(fnmatch.fnmatch(frame.lower(), g.lower()) for g in BUTTON_SET):
            problems.append('off_style_button: %s uses "%s", which is not in the game\'s button set (docs/art/button-set.json): '
                            'every button comes from the one set drawn in the game style' % (b['path'], frame))
    if shot_img is not None:
        problems += flat_button_problems(buttons, nodes, shot_img)
    for n in content:
        lab = n['comps'].get('label')
        if not lab or not text(n) or lab.get('system_font') is not True or lab.get('font'):
            continue
        problems.append('system_font: "%s" (%s) uses the system default font; use the game font' % (text(n)[:30], n['path']))
    panels = [n for n in nodes if n not in masks and area(n['rect']) < 0.85 and
              'button' not in n['comps'] and area(n['rect']) >= 0.12 and
              (('sprite' in n['comps'] and (n['comps']['sprite'].get('sliced') or kind == 'popup')) or
               (n['name'] == 'PanelSurface' and 'graphics' in n['comps']))]
    if panels and kind in ('popup', 'page', 'home'):
        p = max(panels, key=lambda n: area(n['rect']))
        inner = [n['rect'] for n in content if n is not p and center_in(n['rect'], p['rect']) and area(n['rect']) < 0.9 * area(p['rect'])]
        filled = coverage(inner, p['rect'])
        # A check-in page has its own seven-card/day-7 layout checks; generic
        # panel fill counts the card grid incorrectly. Keep the generic guard
        # active for other pages, including league/rankings panels.
        if filled < 0.30 and purpose != 'checkin':
            problems.append('empty_panel: %s is only %.0f%% filled (needs >= 30%%): the screenshot "Weekly Rankings" mistake'
                            % (p['path'], filled * 100))
        if (kind == 'popup' or masks) and purpose not in OWN_POPUP_RULES:
            art = [n['rect'] for n in pictures if n is not p and n not in panels and not text(n) and center_in(n['rect'], p['rect'])
                   and not TITLE_DECOR.search(n['name'] + ' ' + str(n['comps']['sprite'].get('frame', '')))
                   and area(n['rect']) >= 0.005 and not any(node_under(n, b) for b in buttons)]
            art_share = coverage(art, p['rect'])
            if art_share < MIN_POPUP_ART:
                problems.append('plain_popup: %s holds only text and buttons (pictures %.0f%% of the panel, needs >= 10%%): add a '
                                'generated illustration - gift/chest, mascot, phone with the game icon, the reward items with the '
                                'currency icon - plus a picture-text title on a ribbon (user 2026-10-23: the flat "Home screen '
                                'reward" popup)' % (p['path'], art_share * 100))
    if purpose in ('result_win', 'result_fail'):
        decor = [n for n in pictures if not any(node_under(n, b) for b in buttons) and n not in panels]
        need = []
        result_controls=[n for n in content if 'button' in n['comps']]
        if len(result_controls)<2 or not buttons:need.append('>= 2 visible result controls and an enabled exit, found %d visible / %d enabled'%(len(result_controls),len(buttons)))
        if not numbers: need.append('a number (reward coins, score or level)')
        if len(decor) < 3: need.append('>= 3 pictures besides buttons (stars, coin, ribbon, mascot), found %d' % len(decor))
        if cov < 0.25: need.append('>= 25%% of the screen used, found %.0f%%' % (cov * 100))
        if need:
            problems.append('result_page: ' + '; '.join(need))
        if (purpose == 'result_win' or MODE == 'endless') and 'result_original_multiplier' not in MAINTENANCE_RULES:
            sub_names = lambda b: ' '.join([b['name'], str((b['comps'].get('sprite') or {}).get('frame', ''))] +
                                           [n['name'] + ' ' + str((n['comps'].get('sprite') or {}).get('frame', '')) + ' ' + text(n)
                                            for n in nodes if node_under(n, b)])
            if not any(DOUBLE_BUTTON.search(sub_names(b)) for b in buttons):
                problems.append('result_double: no "watch an ad, x2 reward" button: every level end (endless: every run end) offers '
                                'it (user 2026-10-23, both boards; AdRewards.resultReward(...).doubled), name it BtnDouble / btn_x2_*')
    button_share = coverage([b['rect'] for b in buttons])
    if purpose in FUNCTION_PAGES and button_share > MAX_BUTTON_SHARE:
        problems.append('buttons_too_big: function buttons cover %.0f%% of the screen (max 40%%; the title and cover art do not '
                        'count): make the buttons smaller and give the space to the title and cover art' % (button_share * 100))
    if purpose == 'home' and 'home_original_composition' not in MAINTENANCE_RULES:
        in_button = lambda n: any(node_under(n, b) for b in buttons)
        logo = [n for n in pictures if not in_button(n) and n['rect'][1] + n['rect'][3] / 2 < 0.5 and n['rect'][2] >= MIN_TITLE_WIDTH
                and area(n['rect']) >= 0.04 and n not in panels]
        logo = sorted(logo, key=lambda n: n['rect'][1])[:1]          # the highest one is the title; the rest is cover art
        cover = [n['rect'] for n in pictures if not in_button(n) and n not in logo and n not in panels and area(n['rect']) >= 0.01]
        cover_share = coverage(cover)
        plated = [b for b in buttons if any('sprite' in n['comps'] and area(n['rect']) >= 0.3 * area(b['rect'])
                                            for n in nodes if node_under(n, b))]
        icons = [b for b in plated if area(b['rect']) <= 0.03]
        cx_, cy_, cw_, ch_ = d.get('canvas_css') or [0, 0, 1, 1]
        for n in content:
            lab = n['comps'].get('label') or n['comps'].get('richtext')
            r = n['rect']
            if in_button(n) or not WORDS.search(text(n)) or r[1] + r[3] / 2 >= 0.45:
                continue
            h_design = (lab or {}).get('height') or 0
            css = ((lab or {}).get('fontSize') or 0) * (r[3] * ch_ / h_design) if h_design else 0
            if lab and (r[2] >= 0.4 or css >= 36):
                problems.append('typed_title: "%s" (%s) is a title/subtitle typed with a font: the game title is ONE stylized logo '
                                'picture generated in the game style (a subtitle is part of that picture), never typed (user 2026-10-23)'
                                % (text(n)[:30], n['path']))
            elif not lab and logo and center_in(r, logo[0]['rect']) and n is not logo[0]:
                problems.append('typed_title: "%s" (%s) is picture text laid over the title plate %s: generate the title as one '
                                'logo picture with its words, not a plate plus letters (user 2026-10-23)'
                                % (text(n)[:30], n['path'], logo[0]['path']))
        need = []
        if not logo: need.append('a big title picture in the top half (>= 55% of the screen width)')
        if cover_share < MIN_COVER_ART: need.append('cover art: characters/scenery pictures (not buttons) >= 15%% of the screen, found %.0f%%'
                                                    % (cover_share * 100))
        if not any(area(b['rect']) > 0.03 for b in plated): need.append('a big PLAY button with a plate')
        if len(icons) < 2: need.append('>= 2 icon buttons, found %d' % len(icons))
        if 'home_original_composition' not in MAINTENANCE_RULES and not any(
                GIFT_NAME.search(n['name'] + ' ' + str((n['comps'].get('sprite') or {}).get('frame', ''))) for n in content):
            need.append('the gift box (a 10-frame animated gift in the game style, tap -> ad -> coins; user 2026-10-23), '
                        'node/frame named gift')
        if need:
            problems.append('home_page: ' + '; '.join(need))
    texts = ' '.join(words(n) for n in content)
    dev = sorted({text(n)[:40] for n in content if DEV_TEXT.search(text(n))})
    if dev:
        problems.append('dev_text: the player sees developer wording: ' + ', '.join(dev[:4]))
    # --- user 2026-10-21 round 2 (level select with blank cards and a blue placeholder square, home with dark thick
    #     PLAY text, text sticking out of plates and a big empty middle)
    if image_module is not None and pixels is not None:
        for share, fill, box in solid_blocks(screenshot_of(d), image_module):   # the background is full width: skipped below
            # A dim full-screen input shade masks the underlay from interaction checks,
            # but the background pixels remain visible behind it in this screenshot.
            if background_only_block(box, all_visual):
                continue
            if panel_fill_block(box, nodes):
                continue
            if share >= MIN_SOLID_BLOCK and fill >= 0.8 and box[2] < 0.9:        # full-width bands are gradient background
                problems.append('solid_block: a flat single-colour rectangle covers %.0f%% of the screen at x %.0f%%, y %.0f%% '
                                '(placeholder square, grey lock block or an empty card): draw real content there'
                                % (share * 100, box[0] * 100, box[1] * 100))
    for n in pictures:
        frame = str(n['comps']['sprite'].get('frame', ''))
        if area(n['rect']) >= 0.005 and (PLACEHOLDER_FRAMES.search(frame) or PLAIN_FRAMES.match(frame.lower())):
            problems.append('placeholder: %s shows the frame "%s" (placeholder/default picture)' % (n['path'], frame))
    for n in pictures:
        frame = str(n['comps']['sprite'].get('frame', ''))
        if not (0.015 <= area(n['rect']) <= 0.12) or n in panels or 'button' in n['comps'] and text(n):
            continue
        if not (CARD_NAMES.search(frame) or CARD_NAMES.search(n['name'])):
            continue
        if frame.lower().startswith('btn_') and baked(n):
            continue  # A generated whole-word action button is not an empty collection card.
        inside = [m['rect'] for m in content if m is not n and center_in(m['rect'], n['rect']) and area(m['rect']) < 0.9 * area(n['rect'])]
        if coverage(inside, n['rect']) < 0.15:
            problems.append('blank_card: %s is an empty card/frame (put the level preview, item picture, number or icon in it)' % n['path'])
    for n in content:
        lab = n['comps'].get('label') or {}
        col = lab.get('color')
        if text(n) and isinstance(col, list) and len(col) == 3 and lstar(col) < DARK_LSTAR and ((lab.get('fontSize') or 0) >= 28 or lab.get('bold')):
            problems.append('dark_text: "%s" is dark thick text (L* %.0f); use white/light or a saturated theme colour, medium weight'
                            % (text(n)[:30], lstar(col)))
    for b in buttons:
        for n in nodes:
            if n is b or not node_under(n, b) or not text(n) or (n['comps'].get('label') or {}).get('overflow') not in (0, None):
                continue
            r, br = n['rect'], b['rect']
            if r[0] < br[0] - 0.04 * br[2] or r[0] + r[2] > br[0] + br[2] * 1.04:
                below = r[1] >= br[1] + br[3] * 0.9            # a caption under an icon is fine
                if not below:
                    problems.append('text_outside: "%s" sticks out of its button %s' % (text(n)[:30], b['path']))
    if kind in ('page', 'home') and not masks:
        spans = sorted((n['rect'][1], n['rect'][1] + n['rect'][3]) for n in content)
        gap, edge = 0.0, 0.05
        for top, bottom in spans:
            if top > edge:
                gap = max(gap, min(top, 0.95) - edge)
            edge = max(edge, bottom)
        gap = max(gap, 0.95 - edge)
        if gap >= MAX_EMPTY_BAND:
            problems.append('empty_area: a band of %.0f%% of the screen height has nothing in it (needs < 18%%): fill it with cover art, '
                            'more level nodes or move things closer' % (gap * 100))
    if purpose in ('home', 'result_win', 'result_fail'):
        texted = [b for b in buttons if texted_action_button(b, nodes)]
        if len(texted) > 2:
            problems.append('text_buttons: %d buttons have text on the plate (max 2, e.g. PLAY/NEXT; the rest are icons with a small '
                            'caption below): %s' % (len(texted), ', '.join(text(next(n for n in nodes if node_under(n, b) and text(n)))[:16]
                                                                      if any(text(n) for n in nodes if node_under(n, b)) else
                                                                      next(baked(n) for n in nodes if node_under(n, b) and baked(n))[:16]
                                                                      for b in texted)))
    if purpose == 'map':
        level_count = visible_level_button_count(nodes)
        if level_count < 6:
            problems.append('map_page: only %d level buttons on screen (show >= 6, e.g. a 3x4 grid or a path map, each with its number, '
                            'stars and locked/current/cleared state)' % level_count)
    if purpose == 'checkin':
        day_labels = [n for n in content if re.fullmatch(r'(day\s*)?[1-7]', text(n), re.I)]
        cards = []
        need = []
        for lab in day_labels:
            day_match = re.search(r'/Day([1-7])/', lab['path'])
            day_root = lab['path'][:day_match.start()] + '/Day' + day_match.group(1) if day_match else ''
            holders = [m for m in nodes if day_root and under(m['path'], day_root) and m['path'].endswith('/CardSurface') and
                       ('graphics' in m['comps'] or 'sprite' in m['comps']) and area(m['rect']) < 0.5]
            if not holders:
                holders = [m for m in pictures if m is not lab and center_in(lab['rect'], m['rect']) and 0.01 <= area(m['rect']) < 0.5]
            if holders:
                card = max(holders, key=lambda m: area(m['rect']))
                day = int(re.sub(r'\D', '', text(lab)))
                cards.append((day, card))
                card_root = card['path'].rsplit('/CardSurface', 1)[0]
                inside = [m for m in content if m['path'].startswith(card_root + '/') and
                          center_in(m.get('screen') or m['rect'], card.get('screen') or card['rect']) and
                          area(m['rect']) < 0.9 * area(card['rect'])]
                if coverage([m.get('screen') or m['rect'] for m in inside], card.get('screen') or card['rect']) < 0.10:
                    need.append('day %d card has no visible reward content (CardSurface inner coverage < 10%%)' % day)
        days = {d for d, _ in cards}
        if days != set(range(1, 8)): need.append('7 day cards with their numbers 1-7 (found %s)' % sorted(days))
        if 7 in days and len(cards) >= 2:
            big = max(area(c['rect']) for d, c in cards if d == 7)
            others = sorted(area(c['rect']) for d, c in cards if d != 7)
            if big < 2 * others[len(others) // 2] and 'checkin_original_card_sizes' not in MAINTENANCE_RULES:
                need.append('the day-7 card must be the big one (>= 2x the other cards, full width, big chest/gift picture)')
        if not any(claim_button(b, nodes) or any(words(n) for n in nodes if node_under(n, b)) for b in buttons):
            need.append('a Claim button')
        if need:
            problems.append('checkin_page: ' + '; '.join(need))
    if purpose == 'settings' and 'settings_original_switches' not in MAINTENANCE_RULES:
        need = []
        if len(buttons) < 3: need.append('>= 3 rows/buttons, found %d' % len(buttons))
        if not re.search(r'how\s*to\s*play|tutorial', texts, re.I): need.append('a "How to Play" row')
        if re.search(r'credits|about',texts,re.I):need.append('remove player-facing Credits/About entry per 2026-10-26 package policy')
        if need:
            problems.append('settings_general: ' + '; '.join(need))
    if purpose == 'settings_sound' and 'settings_original_switches' not in MAINTENANCE_RULES:
        need = []
        if not re.search(r'music', texts, re.I): need.append('a "Music" section')
        if not re.search(r'sound|sfx|effects', texts, re.I): need.append('a "Sound Effects" section')
        if len(buttons) < 6: need.append('>= 6 buttons (two switches, minus/plus for each), found %d' % len(buttons))
        if len(re.findall(r'\d+\s*%', texts)) < 2: need.append('two percentages (e.g. 70%)')
        if need:
            problems.append('settings_sound: ' + '; '.join(need))
    if purpose == 'league':
        if reported_numbers < 10 or cov < 0.35:
            problems.append('league_page: %d rank/score values and %.0f%% of the screen used (needs >= 10 visible ranks/points and >= 35%%)'
                            % (reported_numbers, cov * 100))
    return problems, dict(pix, visible=len(content), coverage=round(cov, 3), buttons=len(buttons), button_share=round(button_share, 3),
                          pictures=len(pictures),
                          numbers=reported_numbers, backdrop=bool(backdrops))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--dumps', type=Path, nargs='*', help='folders with chrome_touch dump_ui files (default <project>/docs/test)')
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--maintenance-scope', type=Path)
    ap.add_argument('--maintenance-visual-policy', type=Path)
    a = ap.parse_args()
    proj = a.project.resolve()
    folders = a.dumps or [proj / 'docs/test']
    dumps = load([f for f in folders if Path(f).is_dir()])
    global CAPTION_FRAMES, RUNTIME_TEXT, BUTTON_SET, CANVAS_TEXT_FILES, CLARITY_EXEMPT, MODE, OPTIONAL, GENERATED_TEXT_SOURCES
    GENERATED_TEXT_SOURCES={}
    for source in (proj/'assets').rglob('*.png'):
        if (Path(str(source)+'.meta')).is_file():
            try:
                meta=json.loads(Path(str(source)+'.meta').read_text())
                for name,sub in meta.get('subMetas',{}).items():
                    if name.startswith(('phrase_','digit_','symbol_','txt_')) or source.parent.name=='type20261024':
                        rect=[sub.get('trimX',0),sub.get('trimY',0),sub.get('width',0),sub.get('height',0)]
                        GENERATED_TEXT_SOURCES[name]={'path':source,'rect':rect if min(rect[2:])>0 else None}
            except (OSError,ValueError):pass
    from feature_policy import enabled
    OPTIONAL = enabled(proj)
    setup = []
    global MAINTENANCE_RULES
    MAINTENANCE_RULES = set()
    maintenance_mapping = None
    if a.maintenance_scope or a.maintenance_visual_policy:
        try:
            if not a.maintenance_scope or not a.maintenance_visual_policy or not a.binding:
                raise ValueError('scope, visual policy and current binding all required')
            from visual_maintenance_scope import validate_policy
            binding = json.loads(a.binding.read_text(encoding='utf-8'))['binding']
            maintenance_mapping = validate_policy(a.maintenance_visual_policy, a.maintenance_scope, proj, binding, dumps)
            MAINTENANCE_RULES = set(maintenance_mapping['rules'])
        except (ValueError, OSError, KeyError, TypeError) as exc:
            setup.append('maintenance_visual_scope: ' + str(exc))
    try:
        from audit_level_plan import plan_mode     # imported here: audit_level_plan imports this module
        MODE = plan_mode(proj)
    except ImportError:
        MODE = None
    try:
        ce = json.loads((proj / 'docs/art/clarity-exempt.json').read_text(encoding='utf-8-sig'))
        CLARITY_EXEMPT = [str(x['frame']) for x in ce.get('frames', []) if isinstance(x, dict) and x.get('frame') and str(x.get('why', '')).strip()]
    except (OSError, ValueError, AttributeError):
        CLARITY_EXEMPT = []
    try:
        rt = json.loads((proj / 'docs/text/runtime-text.json').read_text(encoding='utf-8-sig'))
        RUNTIME_TEXT = [str(x['path']) for x in rt.get('labels', []) if isinstance(x, dict) and x.get('path') and str(x.get('why', '')).strip()]
        CANVAS_TEXT_FILES = [str(x['file']).replace('\\', '/') for x in rt.get('canvas_text_files', [])
                             if isinstance(x, dict) and x.get('file') and str(x.get('why', '')).strip()]
    except (OSError, ValueError, AttributeError):
        RUNTIME_TEXT, CANVAS_TEXT_FILES = [], []
    try:
        bs = json.loads((proj / 'docs/art/button-set.json').read_text(encoding='utf-8-sig'))
        BUTTON_SET = [str(g) for g in bs.get('frames', []) if str(g).strip()]
        CAPTION_FRAMES = [str(g) for g in bs.get('caption_frames', []) if str(g).strip()]
        if not BUTTON_SET or not str(bs.get('style', '')).strip():
            raise ValueError
    except (OSError, ValueError, AttributeError):
        BUTTON_SET = None;CAPTION_FRAMES=[]
        setup.append('button_set: docs/art/button-set.json missing: generate every button (main, small, icon, arrows, close, back, '
                     'tabs) as one set in the game style and list their frame names ({"style": "...", "frames": ["btn_*", ...]})')
    setup += canvas_text_code(proj) + font_advance_problems(proj)
    try:
        from PIL import Image
    except ImportError:
        ap.error('Pillow is needed to measure the screenshots: pip install pillow')
    presentation_binding = None
    if a.binding:
        presentation_binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
        if not isinstance(presentation_binding, dict):
            ap.error('binding object required')
    pages, failed = [], []
    for d in dumps:
        problems, stats = check(d, Image, proj, presentation_binding)
        row = {'screen': d.get('screen'), 'kind': d.get('kind'), 'purpose': d.get('purpose', 'other'), 'file': d['_file'],
               'problems': problems, 'stats': stats}
        pages.append(row)
        if problems:
            failed.append(row)
    need = list(REQUIRED)
    if 'settings_original_switches' in MAINTENANCE_RULES:
        for mapped in ('settings', 'settings_sound'):
            if mapped in need:
                need.remove(mapped)
    try:
        if json.loads((proj / 'docs/league/decision.json').read_text(encoding='utf-8-sig')).get('decision') in ('add', 'keep_original'):
            need.append('league')
    except (OSError, ValueError, AttributeError):
        pass
    try:
        if json.loads((proj / 'docs/features.json').read_text(encoding='utf-8-sig')).get('daily_checkin') is True:
            need.append('checkin')
    except (OSError, ValueError, AttributeError):
        pass
    try:
        from audit_level_plan import plan_mode     # imported here: audit_level_plan imports this module
        if plan_mode(proj) == 'levels' and __import__('maintenance_scope').required_map(proj):
            need.append('map')
    except ImportError:
        pass
    if setup:
        failed.append({'screen': None, 'purpose': 'setup', 'problems': setup})
    have = {p['purpose'] for p in pages}
    missing = [x for x in need if x not in have]
    if missing:
        failed.append({'screen': None, 'purpose': ','.join(missing), 'problems': [
            'missing dumps: read these pages in the browser with chrome_touch dump_ui and "purpose": ' + ', '.join(missing)]})
    report = {'tool': 'audit_page_richness', 'schema': 2, 'checked': len(pages),
              'failed': len(failed), 'passed': not failed and bool(pages), 'status': 'pass' if not failed and pages else 'fail',
              'pages': pages, 'missing': missing, 'setup': setup,
              'boundary': 'Scene-tree structure from dump_ui; the final look is still judged by Codex on the contact sheets.'}
    if maintenance_mapping is not None:
        report['maintenance_mapping'] = maintenance_mapping
    if a.binding:
        try:
            b = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
        except (OSError, ValueError) as exc:
            ap.error('binding: %s' % exc)
        if not isinstance(b, dict):
            ap.error('no binding object in %s' % a.binding)
        report['binding'] = b
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'checked': report['checked'], 'failed': len(failed),
                      'found': [{'screen': f['screen'], 'problems': f['problems'][:3]} for f in failed][:8], 'report': str(a.out)},
                     ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
