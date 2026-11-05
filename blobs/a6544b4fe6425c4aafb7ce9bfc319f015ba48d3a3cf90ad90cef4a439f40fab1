#!/usr/bin/env python3
"""Fit English into the label boxes while writing it (生成时预防 P06 1/5, Saul 2026-11-04: 「在设计的时候……就进行约束，
让他做的是对的」, not only found later by audit_text_fit.py / art_check.py).

Stage 2 of the English pack, right after the Chinese strings in prefabs / scenes became English. For every cc.Label in
the project's prefabs and scenes it reads the box width (node contentSize / UITransform), font size, line height,
overflow, wrap and how many lines the box holds, and measures the English -- and the longest value the label will ever
show -- with the label's own font:

  TTF / OTF   fontTools glyph advances (no fontTools: Pillow; neither: the fixed table below, x1.05)
  BMFont      the .fnt xadvance table
  system font fixed Arial-like width table (the phone draws Roboto / SF / PingFang, about as wide)

Longest value: numbers use max_value from docs/english/label-values.json (else the same digits with the widest digit,
and a `max_value_missing` note), percentages use 100%, countdowns use 00:00:00; a row in label-values.json (or in
docs/art/longest-text.json) may give the longest text itself.

  fits                         left alone
  one line, does not fit       overflow = SHRINK, wrap off, written into the prefab; the shrunk size must stay >= 70 %
                               of the font size (min_font_size in the record), else it goes on the to-fix list
  several lines, do not fit    to-fix list (widen the box, shorten the text, or give it another line); not written
  overflow NONE                the engine sizes the node to the text, so its saved box is no limit: listed under `grows`
                               with the width it needs; a `room` row in label-values.json makes it a fixed SHRINK box
  same-name siblings           reported; the 2nd, 3rd ... get _2, _3 unless a script names them (then reported only)

label-values.json: {"labels": [{"path": "*/coinLabel", "max_value": 999999}, {"path": "*/volume", "longest": "100%"},
                               {"path": "assets/ui/Home.prefab:Home/top/gold", "room": 160}]}

The prefab / scene is rewritten in place (a copy of the original goes to docs/english/fit-labels/backup/). The record
is docs/english/fit-labels.json. Exit codes: 0 nothing left to fix, 1 to-fix list not empty, 2 bad input.

  python fit_english_labels.py --project GAME [--dry-run] [--values JSON] [--files a.prefab ...]
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shutil
import sys
from pathlib import Path

SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles', '.tiktok-kit', 'settings'}
UI_EXT = {'.prefab', '.fire', '.scene'}
MIN_SHRINK = 0.70            # SHRINK may not go below 70 % of the font size (P06)
CJK = re.compile(r'[\u3400-\u9fff\uf900-\ufaff\u3040-\u30ff]')
LETTER_OR_DIGIT = re.compile(r'[A-Za-z0-9]')
PERCENT = re.compile(r'\d+(?:\.\d+)?(?=\s*%)')
COUNTDOWN = re.compile(r'\d{1,2}:\d{2}(?::\d{2})?')
NUMBER = re.compile(r'\d+')
OVERFLOW = {0: 'NONE', 1: 'CLAMP', 2: 'SHRINK', 3: 'RESIZE_HEIGHT'}

# Advance widths per 1000 units of Arial Regular (the same numbers every Arial / Liberation Sans ships with).
_W = {' ': 278, '!': 278, '"': 355, '#': 556, '$': 556, '%': 889, '&': 667, "'": 191, '(': 333, ')': 333, '*': 389,
      '+': 584, ',': 278, '-': 333, '.': 278, '/': 278, ':': 278, ';': 278, '<': 584, '=': 584, '>': 584, '?': 556,
      '@': 1015, '[': 278, '\\': 278, ']': 278, '^': 469, '_': 556, '`': 333, '{': 334, '|': 260, '}': 334, '~': 584,
      '×': 584, '•': 350, '…': 1000, '’': 222, '‘': 222, '“': 333, '”': 333, '–': 556, '—': 1000}
_W.update({d: 556 for d in '0123456789'})
_W.update(dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                   [667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611,
                    722, 667, 944, 667, 667, 611])))
_W.update(dict(zip('abcdefghijklmnopqrstuvwxyz',
                   [556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278,
                    556, 500, 722, 500, 500, 500])))
BOLD = 1.07                  # Arial Bold is about 7 % wider than Regular on English text
UNKNOWN_TTF = 1.05           # a TTF we could not open is measured with the table, 5 % wider to be safe


def table_width(text, size):
    return sum(_W.get(ch, 1000 if CJK.match(ch) else 600) for ch in text) * size / 1000.0


# ------------------------------------------------------------------------------------------------------------- fonts

class Fonts:
    """Font files of the project by uuid (from the .meta next to them) and their width functions."""

    def __init__(self, root):
        self.root = Path(root)
        self.by_uuid, self._cache, self.methods = {}, {}, set()
        assets = self.root / 'assets'
        for meta in assets.rglob('*.meta') if assets.is_dir() else []:
            asset = meta.with_suffix('')
            if asset.suffix.lower() not in ('.ttf', '.otf', '.fnt'):
                continue
            try:
                m = json.loads(meta.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            for u in [m.get('uuid')] + [s.get('uuid') for s in (m.get('subMetas') or {}).values() if isinstance(s, dict)]:
                if u:
                    self.by_uuid[u] = asset

    def width_fn(self, uuid):
        """(fn(text, size) -> width, method name)."""
        path = self.by_uuid.get(uuid) if uuid else None
        if path is None:
            return (lambda t, s: table_width(t, s)), 'system-table' if not uuid else 'font-not-found-table'
        if path in self._cache:
            return self._cache[path]
        if path.suffix.lower() == '.fnt':
            cfg = parse_fnt(path.read_text(encoding='utf-8', errors='replace'))
            res = ((lambda t, s, c=cfg: bm_width(c, t, s)), 'bmfont') if cfg else \
                ((lambda t, s: table_width(t, s) * UNKNOWN_TTF), 'bad-fnt-table')
        else:
            res = ttf_width(path)
        self._cache[path] = res
        return res


def ttf_width(path):
    try:
        from fontTools.ttLib import TTFont
        f = TTFont(str(path), lazy=True, fontNumber=0)
        cmap, hmtx, upem = f.getBestCmap() or {}, f['hmtx'].metrics, float(f['head'].unitsPerEm)
        missing = hmtx.get('.notdef', (upem * 0.6, 0))[0]

        def fn(text, size):
            return sum(hmtx.get(cmap.get(ord(ch)), (missing, 0))[0] for ch in text) * size / upem
        return fn, 'fonttools'
    except Exception:            # noqa: BLE001  no fontTools, or a font it cannot read
        pass
    try:
        from PIL import ImageFont
        cache = {}

        def fn(text, size):
            key = max(1, int(round(size)))
            if key not in cache:
                cache[key] = ImageFont.truetype(str(path), size=key)
            return cache[key].getlength(text) * size / key
        fn('A', 20)
        return fn, 'pillow'
    except Exception:            # noqa: BLE001
        return (lambda t, s: table_width(t, s) * UNKNOWN_TTF), 'ttf-unreadable-table'


def parse_fnt(text):
    size, adv = None, {}
    for line in text.splitlines():
        tag, _, rest = line.strip().partition(' ')
        kv = dict(m.groups() for m in re.finditer(r'(\w+)=("[^"]*"|\S+)', rest))
        try:
            if tag == 'info':
                size = abs(float(kv.get('size', '0'))) or None
            elif tag == 'common' and not size:
                size = float(kv.get('lineHeight', '0')) or None
            elif tag == 'char':
                adv[int(kv['id'])] = float(kv.get('xadvance', kv.get('width', '0')))
        except (KeyError, ValueError):
            continue
    return {'size': size or 1.0, 'adv': adv} if adv else None


def bm_width(cfg, text, size):
    scale = size / cfg['size']
    return sum(cfg['adv'].get(ord(ch), cfg['adv'].get(32, cfg['size'] * 0.5) if ch == ' ' else cfg['size'] * 0.6)
               for ch in text) * scale


# -------------------------------------------------------------------------------------------------- prefab structure

def ref(v):
    return v.get('__id__') if isinstance(v, dict) else None


class Doc:
    """One prefab / scene file: a JSON list of objects joined by {"__id__": n}."""

    def __init__(self, path):
        self.path = Path(path)
        self.raw = self.path.read_text(encoding='utf-8')
        self.objs = json.loads(self.raw)
        if not isinstance(self.objs, list):
            raise ValueError('not a Cocos prefab / scene list')

    def node_of(self, comp):
        i = ref(comp.get('node'))
        return self.objs[i] if isinstance(i, int) and 0 <= i < len(self.objs) else None

    def components(self, node):
        out = []
        for c in node.get('_components') or []:
            i = ref(c)
            if isinstance(i, int) and 0 <= i < len(self.objs):
                out.append(self.objs[i])
        return out

    def parent(self, node):
        i = ref(node.get('_parent'))
        return self.objs[i] if isinstance(i, int) and 0 <= i < len(self.objs) else None

    def path_of(self, node):
        names, seen = [], set()
        while node is not None and id(node) not in seen and node.get('__type__') in ('cc.Node', 'cc.Scene'):
            seen.add(id(node))
            if node.get('__type__') == 'cc.Node':
                names.append(str(node.get('_name') or ''))
            node = self.parent(node)
        return '/'.join(reversed(names))

    def size_of(self, node):
        """(width, height) of the node box: 2.4 _contentSize, 3.x the UITransform."""
        for c in self.components(node):
            if c.get('__type__') == 'cc.UITransform' and isinstance(c.get('_contentSize'), dict):
                s = c['_contentSize']
                return float(s.get('width') or 0), float(s.get('height') or 0)
        s = node.get('_contentSize')
        if isinstance(s, dict):
            return float(s.get('width') or 0), float(s.get('height') or 0)
        return 0.0, 0.0

    def set_width(self, node, width):
        for c in self.components(node):
            if c.get('__type__') == 'cc.UITransform' and isinstance(c.get('_contentSize'), dict):
                c['_contentSize']['width'] = width
                return
        if isinstance(node.get('_contentSize'), dict):
            node['_contentSize']['width'] = width

    def dump(self):
        return json.dumps(self.objs, ensure_ascii=False, indent=2)


def key(lab, *names):
    """The first key the label object really has (2.4 writes _N$overflow, 3.x _overflow)."""
    for n in names:
        if n in lab:
            return n
    return names[0]


def label_props(doc, lab):
    node = doc.node_of(lab)
    if node is None:
        return None
    k_str = key(lab, '_N$string', '_string')
    w, h = doc.size_of(node)
    size = float(lab.get('_fontSize') or 0) or 20.0
    line_h = float(lab.get('_lineHeight') or 0) or size * 1.2
    bold = bool(lab.get('_isBold')) or bool(int(lab.get('_styleFlags') or 0) & 1)
    outline = 0.0
    if lab.get('_enableOutline'):
        outline = float(lab.get('_outlineWidth') or 0)
    for c in doc.components(node):
        if c.get('__type__') == 'cc.LabelOutline' and c.get('_enabled', True):
            outline = max(outline, float(c.get('_width') or 0))
    font = None
    if not lab.get('_isSystemFontUsed', False):
        font = ref_uuid(lab.get('_N$file')) or ref_uuid(lab.get('_font'))
    return {'node': node, 'string': str(lab.get(k_str) or lab.get('_string') or ''), 'k_string': k_str,
            'k_overflow': key(lab, '_N$overflow', '_overflow'), 'overflow': int(lab.get(key(lab, '_N$overflow', '_overflow')) or 0),
            'wrap': bool(lab.get('_enableWrapText', True)), 'w': w, 'h': h, 'size': size, 'line_h': line_h,
            'bold': bold, 'outline': outline, 'font': font}


def ref_uuid(v):
    return v.get('__uuid__') if isinstance(v, dict) else None


# ------------------------------------------------------------------------------------------------------- the values

def load_values(root, path):
    rows = []
    for p in ([Path(path)] if path else []) + [Path(root) / 'docs/english/label-values.json',
                                                 Path(root) / 'docs/art/longest-text.json']:
        try:
            data = json.loads(p.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        for r in (data.get('labels') if isinstance(data, dict) else data) or []:
            if isinstance(r, dict) and r.get('path') and (r.get('text') or r.get('longest') or 'max_value' in r
                                                          or r.get('room')):
                rows.append(r)
    return rows


VALUE_PART = re.compile(r'(\d{1,2}:\d{2}(?::\d{2})?)|(\d+(?:\.\d+)?)(\s*%)|(\d+)')


def find_row(where, rows):
    """The values row for a label: path is a glob on 'file:node/path' or on the node path alone."""
    for r in rows:
        if fnmatch.fnmatch(where, r['path']) or fnmatch.fnmatch(where.split(':', 1)[-1], r['path']):
            return r
    return None


def longest_value(text, where, rows, widest_digit='8'):
    """(longest text the label will show, note or None). Countdown -> 00:00:00, percentage -> 100%, a plain number
    -> max_value from the values file, else the same number of digits all the widest digit (note max_value_missing)."""
    r = find_row(where, rows)
    if r and (r.get('longest') or r.get('text')):
        return str(r.get('longest') or r.get('text')), None
    if r and 'max_value' in r:
        mv = str(r['max_value'])
        return NUMBER.sub(lambda m: mv, text, count=1), None
    note = []

    def rep(m):
        if m.group(1):
            return '00:00:00'
        if m.group(2):
            return '100' + m.group(3)
        note.append(1)
        return widest_digit * len(m.group(4))
    return VALUE_PART.sub(rep, text), ('max_value_missing' if note else None)


def widest(fn, size):
    return max('0123456789', key=lambda d: fn(d, size))


# ---------------------------------------------------------------------------------------------------------- fitting

def wrap_lines(text, room, measure):
    lines = []
    for para in text.split('\n'):
        cur = ''
        for word in para.split(' '):
            trial = word if not cur else cur + ' ' + word
            if cur and measure(trial) > room:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        lines.append(cur)
    return lines


def fit_one(p, text, measure):
    """Decision for one label: ('ok' | 'shrink' | 'todo', details)."""
    w, h, size = p['w'], p['h'], p['size']
    room = (p.get('room') or w) - 2 * p['outline']    # the outline is drawn on both sides

    def width(t, s=size):
        return measure(t, s) * (BOLD if p['bold'] else 1.0)

    if p['overflow'] == 0 and not p.get('room'):
        # NONE: the engine sizes the node to the text, so the saved box is only the last text's size, not a limit.
        # Freezing it would shrink "0" -> "99999" to nothing. Reported with its width; a `room` row in
        # label-values.json turns it into a real box (then fitted like the rest); overlaps stay with audit_text_fit.
        return 'grows', {'need': round(width(text), 1), 'saved_box': round(w, 1)}
    if room <= 0:
        return 'todo', {'why': 'label box has no width (%.0f)' % w}
    capacity = max(1, int((h + 0.5) // p['line_h'])) if h > 0 else 1
    multi = '\n' in text or (p['wrap'] and p['overflow'] in (1, 2, 3) and capacity >= 2)
    if not multi:
        need = width(text)
        if need <= room:
            return 'ok', {'need': need, 'room': room}
        ratio = room / need
        min_size = round(size * ratio, 1)
        info = {'need': round(need, 1), 'room': round(room, 1), 'shrunk_width': round(width(text, size * ratio), 1),
                'min_font_size': min_size, 'ratio': round(ratio, 3)}
        if ratio < MIN_SHRINK:
            info['why'] = 'one line needs %.0f, the box gives %.0f: SHRINK would go to %.0f%% (< 70%%) -- widen the box ' \
                          'or shorten the text' % (need, room, 100 * ratio)
            return 'todo', info
        return 'shrink', info
    lines = wrap_lines(text, room, lambda t: width(t)) if p['wrap'] else text.split('\n')
    widest = max(width(ln) for ln in lines)
    info = {'lines': len(lines), 'capacity': capacity, 'widest_line': round(widest, 1), 'room': round(room, 1)}
    if p['overflow'] == 0:
        return 'ok', info                              # NONE: the node grows with the text (no box to fit)
    if len(lines) <= capacity and widest <= room:
        return 'ok', info
    if p['overflow'] == 2:
        # SHRINK already: smallest size that keeps the wrapped text in the box
        s = size
        while s > size * MIN_SHRINK:
            s -= 0.5
            ls = wrap_lines(text, room, lambda t: measure(t, s) * (BOLD if p['bold'] else 1.0)) if p['wrap'] else lines
            cap = max(1, int((h + 0.5) // (p['line_h'] * s / size)))
            if len(ls) <= cap and max(measure(x, s) * (BOLD if p['bold'] else 1.0) for x in ls) <= room:
                info.update({'min_font_size': round(s, 1), 'ratio': round(s / size, 3)})
                return 'ok', info
    info['why'] = '%d lines of English, the box holds %d (%.0f x %.0f, line height %.0f): widen or heighten the box, ' \
                  'or shorten the text' % (len(lines), capacity, w, h, p['line_h'])
    return 'todo', info


def script_names(root):
    """Every quoted string in the project's scripts: a node name a script looks up is never renamed."""
    names = set()
    assets = Path(root) / 'assets'
    for p in assets.rglob('*') if assets.is_dir() else []:
        if p.suffix.lower() in ('.js', '.ts') and p.is_file() and not (SKIP_DIRS & {x.lower() for x in p.parts}):
            try:
                src = p.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            for m in re.finditer(r'''(['"`])([^'"`\n]{1,80})\1''', src):
                names.update(x for x in re.split(r'[/]', m.group(2)) if x)
    return names


def same_name_siblings(doc, protected, rename):
    out, kids = [], {}
    for o in doc.objs:
        if isinstance(o, dict) and o.get('__type__') == 'cc.Node':
            par = ref(o.get('_parent'))
            if par is not None:
                kids.setdefault(par, []).append(o)
    for par, nodes in kids.items():
        by = {}
        for n in nodes:
            by.setdefault(str(n.get('_name') or ''), []).append(n)
        taken = {str(n.get('_name') or '') for n in nodes}
        for name, group in by.items():
            if len(group) < 2:
                continue
            rec = {'parent': doc.path_of(doc.objs[par]), 'name': name, 'count': len(group), 'renamed': []}
            if name in protected or not rename:
                rec['kept'] = 'a script names "%s"' % name if name in protected else 'dry run'
            else:
                k = 2
                for n in group[1:]:
                    while '%s_%d' % (name, k) in taken:
                        k += 1
                    n['_name'] = '%s_%d' % (name, k)
                    taken.add(n['_name'])
                    rec['renamed'].append(n['_name'])
                    k += 1
            out.append(rec)
    return out


def ui_files(root):
    assets = Path(root) / 'assets'
    for p in sorted(assets.rglob('*')) if assets.is_dir() else []:
        if p.suffix.lower() in UI_EXT and p.is_file() and not (SKIP_DIRS & {x.lower() for x in p.relative_to(root).parts[:-1]}):
            yield p


def run(root, files=None, values=None, dry_run=False):
    root = Path(root)
    fonts, rows = Fonts(root), load_values(root, values)
    protected = script_names(root)
    record = {'tool': 'fit_english_labels', 'schema': 1, 'project': root.name, 'dry_run': dry_run, 'min_shrink': MIN_SHRINK,
              'changed': [], 'todo': [], 'grows': [], 'fits': 0, 'skipped_chinese': [], 'same_name': [], 'notes': [],
              'measured_with': {}, 'files_written': []}
    for f in [Path(x) for x in files] if files else ui_files(root):
        try:
            doc = Doc(f)
        except (OSError, ValueError) as e:
            record['notes'].append({'file': str(f), 'error': str(e)})
            continue
        try:
            rel = f.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            rel = f.name
        dirty = False
        for lab in [o for o in doc.objs if isinstance(o, dict) and o.get('__type__') == 'cc.Label']:
            p = label_props(doc, lab)
            if not p or not p['string'].strip():
                continue
            where = '%s:%s' % (rel, doc.path_of(p['node']))
            if CJK.search(p['string']):
                record['skipped_chinese'].append(where)
                continue
            if not LETTER_OR_DIGIT.search(p['string']):
                continue
            fn, method = fonts.width_fn(p['font'])
            record['measured_with'][method] = record['measured_with'].get(method, 0) + 1
            text, note = longest_value(p['string'], where, rows, widest(fn, p['size']))
            row = find_row(where, rows)
            if row and row.get('room'):
                p['room'] = float(row['room'])
            verdict, info = fit_one(p, text, fn)
            base = {'where': where, 'text': p['string'], 'longest': text, 'font_size': p['size'], 'box': [p['w'], p['h']],
                    'overflow_before': OVERFLOW.get(p['overflow'], p['overflow']), 'measured_with': method}
            if note:
                base['note'] = note
            base.update(info)
            if verdict == 'ok':
                record['fits'] += 1
            elif verdict == 'grows':
                record['grows'].append(base)
            elif verdict == 'shrink':
                base['overflow_after'] = 'SHRINK'
                lab[p['k_overflow']] = 2
                lab['_enableWrapText'] = False    # one line: SHRINK must not wrap it into two tiny lines
                if p.get('room') and p['room'] != p['w']:
                    doc.set_width(p['node'], p['room'])   # NONE + a room row: the box becomes the room
                record['changed'].append(base)
                dirty = True
            else:
                record['todo'].append(base)
        sn = same_name_siblings(doc, protected, rename=not dry_run)
        for r in sn:
            r['file'] = rel
            dirty = dirty or bool(r['renamed'])
        record['same_name'] += sn
        if dirty and not dry_run:
            backup = root / 'docs/english/fit-labels/backup' / rel
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, backup)
            f.write_text(doc.dump() + ('\n' if doc.raw.endswith('\n') else ''), encoding='utf-8')
            record['files_written'].append(rel)
    record['passed'] = not record['todo']
    return record


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--files', nargs='+', help='only these prefab / scene files (default: all under assets/)')
    ap.add_argument('--values', type=Path, help='longest values (default docs/english/label-values.json)')
    ap.add_argument('--dry-run', action='store_true', help='measure and report, write nothing')
    ap.add_argument('--out', type=Path, help='record path (default <project>/docs/english/fit-labels.json)')
    a = ap.parse_args(argv)
    if not (a.project / 'assets').is_dir():
        print(json.dumps({'error': 'not a Cocos project (no assets/): %s' % a.project}, ensure_ascii=False))
        return 2
    rec = run(a.project, a.files, a.values, a.dry_run)
    # Fitting a TTF Score/Reward label does not satisfy the art requirement.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'remake-core/scripts'))
    import audit_value_presentation
    values = audit_value_presentation.audit(a.project)
    rec['value_presentation'] = values
    rec['passed'] = rec['passed'] and values['passed']
    out = a.out or a.project / 'docs/english/fit-labels.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'tool': 'fit_english_labels', 'passed': rec['passed'], 'fits': rec['fits'],
                      'set_to_shrink': len(rec['changed']), 'grows_with_text': len(rec['grows']), 'todo': [t['where'] + ' -- ' + t.get('why', '') for t in rec['todo']][:40],
                      'same_name': len(rec['same_name']), 'still_chinese': len(rec['skipped_chinese']),
                      'value_findings': values['findings'][:40], 'files_written': rec['files_written'], 'record': str(out)}, ensure_ascii=False, indent=2))
    return 0 if rec['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
