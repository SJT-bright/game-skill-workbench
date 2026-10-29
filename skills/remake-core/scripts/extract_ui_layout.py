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
                   r'game_?(layer|root|node|world|area)|play_?(area|field|layer)|level_?(root|layer|node)|stage_?(root|layer))\d*$', re.I)
HUD = re.compile(r'hud|top|bottom|bar|btn|button|icon|coin|gem|diamond|star|heart|life|lives|energy|score|timer|clock|'
                 r'level|lvl|badge|avatar|pause|setting|menu|counter|progress|combo|booster|item|prop|tool|gold|cash', re.I)
TEMP = re.compile(r'tip|toast|hint|guide|bubble|tutorial|finger|hand|float', re.I)
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
            files += sorted(x for x in p.rglob('*ui-dump*.json') if x.is_file())
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
        key = (str(d['screen']), viewport)
        if key in names:
            raise ValueError('screen %s at %sx%s dumped twice (%s, %s)' % (d['screen'], viewport[0], viewport[1], names[key], f))
        names[key] = f
    counts = {}
    for _, d in dumps:
        counts[d['screen']] = counts.get(d['screen'], 0) + 1
    for _, d in dumps:
        if counts[d['screen']] > 1:
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
                'content', 'decoration', 'panel', 'ignore'}:
            raise ValueError('overrides tag for %s: label none/small/text, role content/decoration/panel/ignore' % p)
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
    def __init__(self, path, d, o):
        self.d, self.o, self.notes = d, o, []
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
                n['inner_px'] = to_px(d, inner)
            self.nodes.append(n)
        self.by_path = {n['path']: n for n in self.nodes}

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
        return {'kind': 'gameplay', 'elements': elements}

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
            surfaces = [n for n in sub if 0.04 <= self.share(n['px']) <= 0.9 and 'button' not in n['comps'] and
                        ((('sprite' in n['comps']) and not DECOR.search(n['name'])) or
                         (n['name'] in ('PanelSurface', 'PanelArt') and 'graphics' in n['comps']))]
            if not surfaces:
                raise ValueError('%s: no rendered panel surface under %s' % (self.d['screen'], root))
            panel = max(surfaces, key=lambda n: area(n['px']))
        self.notes.append('panel picked: ' + panel['path'])
        pr = panel['px']
        safe, estimated = panel.get('inner_px'), False
        if not safe:
            inner = [n for n in sub if 'sprite' in n['comps'] and INNER.search(n['name']) and n is not panel and inside(n['px'], pr)
                     and self.share(n['px']) >= 0.02]
            if inner:
                safe = max(inner, key=lambda n: area(n['px']))['px']
            else:
                pad = round(0.06 * min(pr[2], pr[3]), 1)
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
        contents = [{'name': it['name'], 'rect': it['rect']} for it in self.merge_groups(self.outermost(picked))]
        res = {'kind': 'popup', 'panel': list(pr), 'safe': [round(v, 1) for v in safe], 'decorations': decorations, 'contents': contents}
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
    screens = [Screen(f, d, o).build() for f, d in ordered]
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
