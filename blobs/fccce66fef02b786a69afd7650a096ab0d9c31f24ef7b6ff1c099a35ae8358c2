#!/usr/bin/env python3
"""Build docs/ui-layout.json from UI dumps of the running game (user rule 2026-10-21: no hand-typed layout).

Positions and sizes come only from chrome_touch.py {"type":"dump_ui"} dumps (scripts/ui_dump.js reading the
live Cocos scene). audit_ui_coverage.py re-runs this extraction and rejects a layout that was edited by hand.

  python extract_ui_layout.py DUMP_FILES_OR_FOLDERS... --out docs/ui-layout.json [--overrides docs/ui-layout-overrides.json]

Dump one screen per state and phone ratio: kind "home" (main menu), "gameplay", "popup" (one per popup),
"result" (win/lose screen, summarized with popup geometry) or "page".

What is picked automatically (each pick is listed under "auto_notes" so GPT can compare it with the screenshots):
  gameplay  HUD elements = buttons, texts, progress bars and HUD-named sprites outside the game world
            (world roots such as Board/Grid/Map/Background are skipped); children of a picked node are
            part of it; a text or icon overlapping a sibling under the same parent is merged with it
            (designed groups like coin icon + number), two overlapping buttons are kept apart and reported
  home      every outermost button; primary = PLAY/START/NEXT/CONTINUE-like names or the one clearly
            biggest button; label from the button's own text (none / small word / text)
  popup     the topmost blocking or popup-named node is the popup; its largest rendered surface is the panel
            (a Sprite or named Graphics PanelSurface/PanelArt); the inner box comes from 9-slice borders
            (otherwise an estimated 6% inset, marked);
            ornaments = ornament-named sprites or text-free sprites crossing the panel edge; contents = the rest

The overrides file may only correct those choices, never positions:
  {"exclude": ["Canvas/Game"], "include": ["Canvas/ComboBadge"],
   "popup_root": {"pause_9x19": "Canvas/PausePopup"},
   "tags": {"Canvas/Home/BtnPlay": {"primary": true, "label": "text"},
            "Canvas/Pause/Ribbon": {"role": "decoration"}, "Canvas/HUD/Tip": {"temporary": true},
            "Canvas/Pause/Bg": {"role": "panel"}, "Canvas/HUD/Fx": {"role": "ignore"}}}
An exact noninteractive card surface may declare role "container" and a
"contains" list of sibling content paths under the same card root. Its measured
border remains checked, and its content is checked inside that border; this is
not an exclusion or an override of any rectangle.
An independently extracted noninteractive Sprite may declare intentional_contact_with
(an exact other noninteractive Sprite path) plus why. This preserves both rectangles
and all other collisions; the auditor only permits <= 3 CSS px and <= 10% edge contact.
Optional home_entry_pages is a list of exact dumped screen IDs, explicitly annotated as
reachable from HOME after checking actual navigation. Entry names still come from runtime
buttons; the annotation itself does not prove navigation. Match CSS width/height and DPR,
not just framebuffer size. home_entry_sources records each borrowed dump/hash for review.
Exit codes: 0 written, 2 bad input (missing/failed dump, duplicate screen, position in overrides).
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

WORLD = re.compile(r'^(bg|background|board|grid|map|world|tiles?|pieces?|blocks?|terrain|road|track|'
                   r'_?uiboard|board[-_]?transfer[-_]?root|board[-_]?background|tile[-_]?origin[-_]?root|'
                   r'game_?(layer|root|node|world|area)|play_?(area|field|layer)|level_?(root|layer|node)|stage_?(root|layer))\d*$', re.I)
HUD = re.compile(r'hud|top|bottom|bar|btn|button|icon|coin|gem|diamond|star|heart|life|lives|energy|score|timer|clock|'
                 r'level|lvl|badge|avatar|pause|setting|menu|counter|progress|combo|booster|item|prop|tool|gold|cash', re.I)
TEMP = re.compile(r'tip|toast|hint|guide|bubble|tutorial|how_?to_?play|finger|hand|float', re.I)
DECOR = re.compile(r'corner|deco|ribbon|tassel|orn|flower|bow|leaf|sparkle|shine|glow|light|rivet|nail|vine', re.I)
PRIMARY = re.compile(r'play|start|next|continue|begin|retry|again|^go$|claim', re.I)
POPUP = re.compile(r'popup|^pop|dialog|dlg|window|modal|alert|result|settle|pause|fail|victory|defeat|win$|lose', re.I)
INNER = re.compile(r'inner|content|body', re.I)
FORBIDDEN_TAG_KEYS = {'rect', 'frame', 'safe', 'panel_rect', 'x', 'y', 'w', 'h', 'width', 'height', 'size'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_dumps(inputs):
    files = []
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            from art_capture_history import resolve_input_files
            files += resolve_input_files(p)
        elif p.is_file():
            files.append(p)
        else:
            raise ValueError('not a dump file or folder: %s' % p)
    dumps = []
    for f in files:
        d = json.loads(f.read_text(encoding='utf-8'))
        if not isinstance(d, dict) or d.get('tool') != 'ui_dump':
            continue
        if d.get('error'):
            raise ValueError('%s: the dump failed (%s); fix the run, do not type the layout by hand' % (f, d['error']))
        if d.get('kind') not in {'home', 'page', 'gameplay', 'popup', 'result'} or not d.get('screen'):
            raise ValueError('%s: dump has no screen/kind (made outside chrome_touch dump_ui?)' % f)
        dumps.append((f.resolve(), d))
    if not dumps:
        raise ValueError('no ui_dump files found (run chrome_touch.py with {"type":"dump_ui"} actions first)')
    names = {}
    for f, d in dumps:
        page = d.get('page') or {}
        try:
            viewport = (int(page['width']), int(page['height']))
        except (KeyError, TypeError, ValueError):
            raise ValueError('%s: dump needs a valid CSS viewport width/height' % f)
        # One page at one size may be captured more than once on purpose: audit_value_presentation asks for a second
        # capture showing the longest value from docs/art/longest-text.json (合成进化恐龙 2026-11-05: battle "current" and
        # "longest" made this whole layout row unreadable). Such variants carry different capture_name values.
        capture = (f.stem[len('capture-ui-dump-'):] if d.get('art_capture_id') and f.name.startswith('capture-ui-dump-') else d.get('capture_name'))
        capture = capture.strip() if isinstance(capture, str) and capture.strip() else None
        key = (str(d['screen']), viewport, capture)
        if key in names:
            raise ValueError('screen %s at %sx%s dumped twice (%s, %s): an old capture left in the folder? remove it. Two '
                             'states of one page (e.g. current and longest value) need a different "capture_name" in '
                             'each dump' % (d['screen'], viewport[0], viewport[1], names[key], f))
        names[key] = f
        d['_viewport'], d['_capture'] = viewport, capture
    counts, per_size = {}, {}
    for _, d in dumps:
        counts[d['screen']] = counts.get(d['screen'], 0) + 1
        k = (str(d['screen']), d['_viewport'])
        per_size[k] = per_size.get(k, 0) + 1
    for f, d in dumps:
        if per_size[(str(d['screen']), d['_viewport'])] > 1 and d['_capture'] is None:
            raise ValueError('screen %s at %sx%s has several captures; give each one its own "capture_name" (%s)'
                             % (d['screen'], d['_viewport'][0], d['_viewport'][1], f))
    for _, d in dumps:
        if per_size[(str(d['screen']), d['_viewport'])] > 1:
            page = d['page']
            d['_layout_name'] = '%s_%sx%s__%s' % (d['screen'], int(page['width']), int(page['height']), d['_capture'])
        elif counts[d['screen']] > 1:
            page = d['page']
            d['_layout_name'] = '%s_%sx%s' % (d['screen'], int(page['width']), int(page['height']))
        else:
            d['_layout_name'] = str(d['screen'])
    return dumps


def load_overrides(path):
    if not path:
        return {}
    o = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(o, dict):
        raise ValueError('overrides must be an object')
    for p, tag in (o.get('tags') or {}).items():
        if not isinstance(tag, dict) or FORBIDDEN_TAG_KEYS & set(tag):
            raise ValueError('overrides tag for %s may not contain positions or sizes' % p)
        if tag.get('label', 'none') not in {'none', 'small', 'text'} or tag.get('role', 'content') not in {
                'content', 'decoration', 'panel', 'ignore', 'container'}:
            raise ValueError('overrides tag for %s: label none/small/text, role content/decoration/panel/ignore' % p)
        if 'intentional_contact_with' in tag:
            target=tag['intentional_contact_with']
            if (not isinstance(target,str) or not target.strip() or target!=target.strip() or target==p
                    or any(c in target+p for c in '*?[]{}') or not isinstance(tag.get('why'),str) or not tag['why'].strip()):
                raise ValueError('intentional contact requires an exact other path and nonempty why: '+p)
        if tag.get('role')=='container':
            children=tag.get('contains');parent=p.rsplit('/',1)[0]
            if (not isinstance(children,list) or not children or len(set(children))!=len(children)
                    or any(not isinstance(x,str) or not x.startswith(parent+'/') or x==p or under(p,x) for x in children)):
                raise ValueError('container %s requires exact sibling content paths under its own card root' % p)
    linked=o.get('home_entry_pages',[])
    if not isinstance(linked,list) or not all(isinstance(x,str) and x.strip() for x in linked):
        raise ValueError('home_entry_pages must be a list of nonempty exact screen IDs')
    if len(linked)!=len(set(linked)):
        raise ValueError('home_entry_pages must not contain duplicate screen IDs')
    return o


def under(path, prefix):
    return path == prefix or path.startswith(prefix + '/')


def to_px(d, r):
    cx, cy, cw, ch = d['canvas_css']
    dpr = d['page'].get('dpr') or 1
    return [round((cx + r[0] * cw) * dpr, 1), round((cy + r[1] * ch) * dpr, 1), round(r[2] * cw * dpr, 1), round(r[3] * ch * dpr, 1)]


def area(r):
    return max(0.0, r[2]) * max(0.0, r[3])


def overlaps(a, b, tol=2):
    return min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]) > tol and min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]) > tol


def union(a, b):
    x0, y0 = min(a[0], b[0]), min(a[1], b[1])
    x1, y1 = max(a[0] + a[2], b[0] + b[2]), max(a[1] + a[3], b[1] + b[3])
    return [round(x0, 1), round(y0, 1), round(x1 - x0, 1), round(y1 - y0, 1)]


def inside(a, b, tol=1):
    return a[0] >= b[0] - tol and a[1] >= b[1] - tol and a[0] + a[2] <= b[0] + b[2] + tol and a[1] + a[3] <= b[1] + b[3] + tol


def text_of(n):
    c = n['comps']
    t = ((c.get('label') or {}).get('string') or (c.get('richtext') or {}).get('string') or '').strip()
    frame = str((c.get('sprite') or {}).get('frame', ''))
    if not t and frame.lower().startswith('txt_'):      # picture text generated with the art (user 2026-10-22)
        t = frame[4:].replace('_', ' ').strip()
    return t


class Screen:
    def __init__(self, path, d, o, source_indexes=None):
        self.d, self.o, self.notes = d, o, []
        project = next((p for p in Path(path).resolve().parents if (p / 'assets').is_dir()), None)
        if source_indexes is None:
            source_indexes = {}
        if project not in source_indexes:
            index = {}
            if project:
                for source in (project / 'assets').rglob('*.png'):
                    index.setdefault(source.stem, []).append(source)
            source_indexes[project] = index
        self.source_index = source_indexes[project]
        self.size = [round(d['page']['width'] * (d['page'].get('dpr') or 1)), round(d['page']['height'] * (d['page'].get('dpr') or 1))]
        self.screen_area = self.size[0] * self.size[1]
        tags = o.get('tags') or {}
        excl = list(o.get('exclude') or []) + list(((o.get('screens') or {}).get(d['screen']) or {}).get('exclude') or [])
        self.include = list(o.get('include') or [])
        self.nodes = []
        for n in d['nodes']:
            r = n.get('screen') or n.get('rect')
            if not (isinstance(r, list) and len(r) == 4) or r[2] <= 0 or r[3] <= 0 or n.get('opacity', 1) < 0.05:
                continue
            if r[0] >= 1 or r[1] >= 1 or r[0] + r[2] <= 0 or r[1] + r[3] <= 0:
                continue
            tag = tags.get(n['path'], {})
            if tag.get('role') == 'ignore' or any(under(n['path'], e) for e in excl):
                continue
            n = dict(n, px=to_px(d, r), tag=tag)
            if 'inner' in (n['comps'].get('sprite') or {}):
                inner = n['comps']['sprite']['inner']
                raw = n.get('rect')
                if n.get('screen') and raw and raw[2] and raw[3]:
                    inner = [r[0]+(inner[0]-raw[0])*r[2]/raw[2], r[1]+(inner[1]-raw[1])*r[3]/raw[3],
                             inner[2]*r[2]/raw[2], inner[3]*r[3]/raw[3]]
                # SpriteFrame capInsets delimit the stretchable centre, not a
                # semantic content margin. Retain the measured metadata for
                # review, but never treat 9-slice caps as the panel's text box.
                n['slice_center_px'] = to_px(d, inner)
            self.nodes.append(n)
        self.by_path = {n['path']: n for n in self.nodes}

    def visible_rect(self,n):
        s=n.get('comps',{}).get('sprite',{})
        sources=self.source_index.get(s.get('frame'),[])
        if not sources or s.get('sliced') or s.get('tiled') or abs(n.get('angle',0))>.01:return list(n['px'])
        try:
            from PIL import Image
            boxes=[]
            for source in sources:
                with Image.open(source) as im:
                    a=im.convert('RGBA').getchannel('A');box=a.getbbox()
                    if box is None:return list(n['px'])
                    x,y,w,h=n['px'];boxes.append([x+box[0]/im.width*w,y+box[1]/im.height*h,(box[2]-box[0])/im.width*w,(box[3]-box[1])/im.height*h])
            result=boxes[0]
            for b in boxes[1:]:result=union(result,b)
            return [round(v,1) for v in result]
        except (OSError,ImportError):return list(n['px'])

    def share(self, r):
        return area(r) / self.screen_area

    def in_world(self, n):
        parts = n['path'].split('/')
        return any(WORLD.match(p) for p in parts) and not any(under(n['path'], i) for i in self.include)

    def candidate(self, n, hud_names=True):
        c = n['comps']
        if n['path'] in self.include:
            return True
        if self.share(n['px']) > 0.5:
            return False
        if 'button' in c or c.get('progress') or text_of(n):
            return True
        return bool(hud_names and 'sprite' in c and HUD.search(n['name']))

    def outermost(self, picked):
        paths = [n['path'] for n in picked]
        return [n for n in picked if not any(p != n['path'] and under(n['path'], p) for p in paths)]

    def merge_groups(self, picked):
        """Merge a text/icon with an overlapping sibling under the same parent (designed group)."""
        items = [dict(name=n['path'], rect=list(n['px']), button='button' in n['comps'], parent=n['path'].rsplit('/', 1)[0],
                      temporary=bool(n['tag'].get('temporary', TEMP.search(n['path']) is not None)))
                 for n in picked]
        changed = True
        while changed:
            changed = False
            for i, a in enumerate(items):
                for b in items[i + 1:]:
                    if a['parent'] == b['parent'] and not (a['button'] and b['button']) and overlaps(a['rect'], b['rect']):
                        a['rect'] = union(a['rect'], b['rect'])
                        a['name'] = a['parent'] + '/{' + a['name'].rsplit('/', 1)[-1] + '+' + b['name'].rsplit('/', 1)[-1] + '}'
                        a['button'] = a['button'] or b['button']
                        a['temporary'] = a['temporary'] and b['temporary']
                        items.remove(b)
                        self.notes.append('merged designed group ' + a['name'])
                        changed = True
                        break
                if changed:
                    break
        return items

    def gameplay(self):
        picked = self.outermost([n for n in self.nodes if not self.in_world(n) and self.candidate(n)])
        skipped = sorted({n['path'].split('/')[0] + '/…/' + n['name'] for n in self.nodes if self.in_world(n)})[:8]
        if skipped:
            self.notes.append('game world skipped (not HUD): ' + ', '.join(skipped))
        elements = []
        for it in self.merge_groups(picked):
            e = {'name': it['name'], 'rect': it['rect']}
            if it['temporary']:
                e['temporary'] = True
            elements.append(e)
        if not elements:
            self.notes.append('no HUD element found: check the dump was taken during play, or tag nodes with "include"')
        boards=[n for n in self.nodes if re.fullmatch(r'_?UIBoard|Board|Grid',n['name'],re.I) and self.share(n['px'])>.1]
        return {'kind': 'gameplay', 'elements': elements,'playfields':[n['px'] for n in boards]}

    def home(self):
        buttons = self.outermost([n for n in self.nodes if 'button' in n['comps'] and not self.in_world(n)])
        out = []
        areas = sorted(area(b['px']) for b in buttons)
        median = areas[len(areas) // 2] if areas else 0
        for b in buttons:
            tag = b['tag']
            texts = [text_of(n) for n in self.nodes if under(n['path'], b['path']) and text_of(n)]
            words = ' '.join(texts).split()
            w, h = b['px'][2], b['px'][3]
            if 'label' in tag:
                label = tag['label']
            elif not words:
                label = 'text' if (w / max(h, 1) >= 2.2 and self.share(b['px']) >= 0.015) else 'none'
                if label == 'text':
                    self.notes.append('%s has no text node but is a wide tile; treated as a baked-text button' % b['path'])
            elif len(words) == 1 and len(words[0]) <= 8:
                label = 'small'
            else:
                label = 'text'
            if 'primary' in tag:
                primary = bool(tag['primary'])
            else:
                primary = bool(PRIMARY.search(b['name']) or (area(b['px']) == areas[-1] and len(areas) > 1
                                                             and area(b['px']) >= 2.5 * median and self.share(b['px']) >= 0.015))
            item = {'name': b['path'], 'rect': list(b['px']), 'label': label}
            baked = [str(n['comps']['sprite'].get('frame', ''))[4:].replace('_', ' ') for n in self.nodes if under(n['path'], b['path'])
                     and str((n['comps'].get('sprite') or {}).get('frame', '')).lower().startswith('btn_')]
            if words or baked:                          # btn_<words>: the word is baked into the one-piece button picture
                item['text'] = ' '.join(words + baked)[:80]     # lets audit_ui_coverage spot SHARE / INVITE buttons by their words
            if primary:
                item['primary'] = True
            out.append(item)
        if not out:
            self.notes.append('no button found on the home screen dump')
        return {'kind': 'page', 'role': 'home', 'buttons': out}

    def popup(self):
        roots = self.o.get('popup_root') or {}
        root = roots.get(self.d['screen']) or roots.get('*')
        if root and root not in self.by_path:
            raise ValueError('%s: popup_root %s is not an active node in the dump' % (self.d['screen'], root))
        if not root:
            cands = [n for n in self.nodes if (n['comps'].get('block_input') or POPUP.search(n['name'])) and self.share(n['px']) >= 0.3]
            if not cands:
                raise ValueError('%s: no popup found (no blocking or popup-named node); dump while the popup is open or set popup_root'
                                 % self.d['screen'])
            top = max(cands, key=lambda n: n['order'])
            has_kids = any(under(n['path'], top['path']) and n['path'] != top['path'] for n in self.nodes)
            root = top['path'] if has_kids else top['path'].rsplit('/', 1)[0]
            self.notes.append('popup root picked: ' + root)
        sub = [n for n in self.nodes if under(n['path'], root)]
        tags = [n for n in sub if n['tag'].get('role') == 'panel']
        if tags:
            panel = tags[0]
        else:
            surfaces = [n for n in sub if not self.in_world(n) and 0.04 <= self.share(n['px']) <= 0.9 and 'button' not in n['comps'] and
                        ((('sprite' in n['comps']) and not DECOR.search(n['name'])) or
                         (n['name'] in ('PanelSurface', 'PanelArt') and 'graphics' in n['comps']))]
            if not surfaces:
                raise ValueError('%s: no rendered panel surface under %s' % (self.d['screen'], root))
            framed=[n for n in surfaces if n['comps'].get('sprite',{}).get('sliced') or re.search(r'panel|boxbg|box[-_]?background',n['name'],re.I)]
            if not framed:
                # An unframed end-of-run overlay may deliberately retain its
                # board. Do not pick a board shadow as an enclosing dialog.
                actions=self.outermost([n for n in sub if 'button' in n['comps'] and not self.in_world(n)])
                self.notes.append('unframed overlay: no semantic panel surface; retained game board is not a dialog frame')
                return {'kind':'page','buttons':[{'name':n['path'],'rect':list(n['px']),'label':'none',
                    **({'primary':True} if len(actions)<=2 or PRIMARY.search(n['name']) else {})} for n in actions], 'role':'overlay'}
            panel = max(framed, key=lambda n: area(n['px']))
        self.notes.append('panel picked: ' + panel['path'])
        pr = panel['px']
        safe, estimated = None, False
        if not safe:
            inner = [n for n in sub if 'sprite' in n['comps'] and INNER.search(n['name']) and n is not panel and inside(n['px'], pr)
                     and self.share(n['px']) >= 0.02]
            if inner:
                safe = max(inner, key=lambda n: area(n['px']))['px']
            else:
                pad = 0
                safe, estimated = [pr[0] + pad, pr[1] + pad, pr[2] - 2 * pad, pr[3] - 2 * pad], True
                self.notes.append('inner box estimated (panel has no 9-slice borders): GPT checks the frame on the screenshot')

        def has_text(n):
            return any(under(m['path'], n['path']) and text_of(m) for m in sub)

        decorations, picked = [], []
        for n in sub:
            if n is panel or n['path'] == root or self.share(n['px']) > 0.9 or n['comps'].get('block_input'):
                continue
            if under(panel['path'], n['path']):
                continue          # an ancestor of the panel (container), not content
            role = n['tag'].get('role')
            crossing = overlaps(n['px'], pr, 0) and not inside(n['px'], pr)
            is_decor = role == 'decoration' or (role != 'content' and 'sprite' in n['comps'] and 'button' not in n['comps']
                                                 and not has_text(n) and (DECOR.search(n['name']) or crossing))
            if is_decor:
                decorations.append({'name': n['path'], 'rect': list(n['px'])})
            elif role == 'content' or self.candidate(n, hud_names=False) or ('sprite' in n['comps'] and self.share(n['px']) < 0.9 * self.share(pr)):
                picked.append(n)
        decor_paths = [x['name'] for x in decorations]
        picked = [n for n in picked if not any(under(n['path'], p) for p in decor_paths)]
        measured=[dict(n,px=self.visible_rect(n)) for n in self.outermost(picked)]
        contents = [{'name': it['name'], 'rect': it['rect'],
                     **({'chrome':True} if re.search(r'/(?:Close|BtnClose|CloseButton)(?:/|$)',it['name'],re.I) else {}),
                     **({'outside_panel':True} if not overlaps(it['rect'],pr,0) or not (pr[0]<=it['rect'][0]+it['rect'][2]/2<=pr[0]+pr[2] and pr[1]<=it['rect'][1]+it['rect'][3]/2<=pr[1]+pr[3]) else {})}
                    for it in self.merge_groups(measured)]
        for item in contents:
            n=next((n for n in measured if n['path']==item['name']),None)
            members=[n] if n else [m for m in measured if '/{' in item['name'] and m['path'].rsplit('/',1)[0]==item['name'].split('/{',1)[0]]
            sources=[]
            for m in members:
                sprite=m.get('comps',{}).get('sprite',{})
                paths=self.source_index.get(sprite.get('frame'),[])
                if not paths or sprite.get('sliced') or sprite.get('tiled'):sources=[];break
                sources.extend({'path':str(p),'sha256':sha(p),'rect':list(m['px'])} for p in paths)
            if sources:
                item['alpha_sources']=sources
                try:
                    from PIL import Image
                    item['surface_backing']=all(Image.open(source['path']).convert('RGB').getextrema()==tuple((v,v) for v in Image.open(source['path']).convert('RGB').getpixel((0,0))) for source in sources)
                except (OSError,ImportError):pass
            item['text_content']=any(bool(text_of(m)) or str(m.get('comps',{}).get('sprite',{}).get('frame','')).startswith(('digit_','symbol_')) for m in members)
        # A declared contact never removes a node or changes its measured rectangle.
        # Both endpoints must remain independently extracted, text-free Sprites.
        for source in measured:
            target=source['tag'].get('intentional_contact_with')
            if target is None:continue
            matches=[n for n in self.nodes if n['path']==target]
            if len(matches)!=1 or sum(n['path']==source['path'] for n in self.nodes)!=1:
                raise ValueError('intentional contact requires two unique visible Sprite paths: '+source['path'])
            endpoints=[source,matches[0]];items=[]
            for n in endpoints:
                family=[m for m in self.d['nodes'] if under(m['path'],n['path']) or under(n['path'],m['path'])]
                descendants=[m for m in family if under(m['path'],n['path'])]
                if ('sprite' not in n['comps'] or n['comps']['sprite'].get('sliced') or n['comps']['sprite'].get('tiled')
                        or any(set(m['comps']) & {'button','toggle','slider','editbox','touch','block_input'} for m in family)
                        or any(text_of(m) or str(m['comps'].get('sprite',{}).get('frame','')).startswith(('txt_','digit_','symbol_','btn_')) for m in descendants)):
                    raise ValueError('intentional contact may not hide text or interactive controls: '+n['path'])
                item=next((item for item in contents if item['name']==n['path']),None)
                if item is None:raise ValueError('intentional contact Sprite must remain independently extracted: '+n['path'])
                items.append(item)
            if not isinstance(source['tag'].get('why'),str) or not source['tag']['why'].strip():
                raise ValueError('intentional contact requires why: '+source['path'])
            for item in items:
                item['contact_eligible_sprite']=True
                item['contact_dpr']=self.d['page'].get('dpr') or 1
            items[0]['intentional_contact_with']=target
            items[0]['contact_why']=source['tag']['why']
            self.notes.append('declared exact Sprite contact '+source['path']+' -> '+target+': '+source['tag']['why'])
        # Explicit per-card semantic nesting. Do not remove the surface or its
        # content from geometry, and never infer this relationship from overlap.
        for surface in measured:
            if surface['tag'].get('role')!='container':continue
            if 'button' in surface['comps'] or 'sprite' not in surface['comps']:
                raise ValueError('declared card container must be a noninteractive measured Sprite: '+surface['path'])
            prefixes=surface['tag']['contains']
            if any(not any(under(n['path'],prefix) for n in sub) for prefix in prefixes):
                raise ValueError('declared card content is absent: '+surface['path'])
            owner=next((item for item in contents if item['name']==surface['path']),None)
            if owner is None:raise ValueError('declared container surface was not independently extracted: '+surface['path'])
            owner['container_for']=prefixes
            for item in contents:
                if any(under(item['name'],prefix) for prefix in prefixes):
                    if item.get('container_owner'):raise ValueError('ambiguous card container owner: '+item['name'])
                    item['container_owner']=surface['path']
        res = {'kind': 'popup', 'panel': list(pr), 'safe': [round(v, 1) for v in safe], 'decorations': decorations, 'contents': contents}
        res['screen_size']=self.size
        if estimated:
            res['safe_estimated'] = True
        return res

    def page(self):
        return {'kind': 'page', 'entry_names': [n['path'] for n in self.nodes if 'button' in n['comps']]}

    def build(self):
        kind = self.d['kind']
        body = {'home': self.home, 'gameplay': self.gameplay, 'popup': self.popup,
                'result': self.popup, 'page': self.page}[kind]()
        return dict({'name': self.d.get('_layout_name', self.d['screen']), 'size': self.size}, **body, auto_notes=self.notes)


def build(dump_inputs, overrides_path=None):
    dumps = load_dumps(dump_inputs)
    o = load_overrides(overrides_path)
    ordered = sorted(dumps, key=lambda x: (x[1].get('_layout_name', x[1]['screen']), str(x[0])))
    screens = []
    # Screens from the same project share its file index during this extraction.
    source_indexes = {}
    for f, d in ordered:
        # One page that cannot be read (no popup found, no panel) used to stop the layout for every page, so the
        # whole row only said "读不出布局" (合成进化恐龙 2026-11-05: 1 of 66 pages). Now that page carries the error
        # and audit_ui_coverage fails it alone; the other pages are still checked (美工skill 2026-11-06).
        try:
            screens.append(Screen(f, d, o, source_indexes).build())
        except ValueError as exc:
            screens.append({'name': d.get('_layout_name', d['screen']), 'kind': 'page' if d['kind'] == 'home' else
                            ('popup' if d['kind'] == 'result' else d['kind']), 'error': str(exc), 'auto_notes': []})
    for (f, d), s in zip(ordered, screens):
        s['source_dump'] = {'path': str(f), 'sha256': sha(f)}
    # Explicit route annotations are reviewed by the caller; geometry is never invented.
    linked = set(o.get('home_entry_pages') or [])
    unknown=linked-{d['screen'] for _,d in ordered}
    if unknown:
        raise ValueError('home_entry_pages has no runtime dump: '+', '.join(sorted(unknown)))
    def viewport(d):
        page=d['page']
        return (page['width'],page['height'],page.get('dpr') or 1)
    for (f, d), s in zip(ordered, screens):
        if s.get('role') != 'home':
            continue
        entries = list(s.get('entry_names',[]))
        sources=[]
        for (other_f, other_d), other_s in zip(ordered, screens):
            if other_d['screen'] in linked and viewport(other_d)==viewport(d):
                observed=other_s.get('entry_names', [])
                if observed:
                    entries += observed
                    sources.append({'screen':other_d['screen'],'source_dump':other_s['source_dump'],'entry_names':observed})
        if sources:
            s['entry_names'] = sorted(set(entries))
            s['home_entry_sources'] = sources
            s['auto_notes'].append('Linked HOME entries use explicit route annotations; verify actual navigation, not just this layout.')
    return {'provenance': 'runtime_dump',
            'generator': {'tool': 'extract_ui_layout', 'sha256': sha(__file__)},
            'dumps': sorted(({'path': str(f), 'sha256': sha(f)} for f, _ in dumps), key=lambda x: x['path']),
            'overrides': {'path': str(Path(overrides_path).resolve()), 'sha256': sha(overrides_path)} if overrides_path else None,
            'screens': screens}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('dumps', nargs='+')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--overrides', type=Path)
    a = ap.parse_args()
    try:
        layout = build(a.dumps, a.overrides)
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False))
        return 2
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(layout, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'written', 'out': str(a.out), 'screens': [(s['name'], s['kind']) for s in layout['screens']],
                      'notes': sum(len(s['auto_notes']) for s in layout['screens'])}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
