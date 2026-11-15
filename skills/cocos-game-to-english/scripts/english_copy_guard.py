#!/usr/bin/env python3
"""English copy guard, run right after the English text is written (生成时预防 R4N5, 问题普查 09 补查2 第 2、8 组).

Two jobs, both static, seconds, no build, no browser:

1. Glyph set for the generated bitmap fonts, worked out BEFORE the art step (第 2 组, 弹球传奇 11-05: digits.fnt had
   only 0-9 while the first round shows `x50`; 48 of 54 runtime words were made later, one by one). The set is the
   union of every character a value can show next to its digits:
     - format strings in the copy table, Labels and language JSON: `x{n}` `+{0}` `{a}/{b}` `%d%` `Lv.{n}`
     - format strings built in scripts: `'x' + n`, `n + '%'`, `` `+${n}` ``, `a + '/' + b`, `mm + ':' + ss`, on the
       label line itself or (R4P4) on a line up to 40 lines above that builds the simple variable the label shows
       (`const t = 'x' + n;` ... `label.string = t;`, followed through up to 3 assignments)
     - (R4R2) a number formatter's unit table `['K','M','B','T','Q']` and the short literals glued on near it
       (`+ 'E' +`, toFixed's '.'), wherever the formatter lives (方块收割者 11-05: K/M/B/T/Q/E in a 0-9 font)
     - digits 0-9 always
   and the whole-word pictures come from ONE list (short fixed words: copy-table rows marked image, the word_image rows
   of docs/english/fit-labels.json, short button/title words). Both go to docs/english/charset.json. Each project .fnt
   is compared with the set; `missing` names what a font still lacks. Generate the digit font from `value_charset` and
   every word in `word_images` before the first piece, not while building.

2. Copy checks on what was just written (第 8 组):
     literal_newline   a Label / RichText whose text has a literal backslash-n (合成进化恐龙 health tip): rewritten to a
                       real line break in the prefab / scene (backup in docs/english/copy-guard/backup/); in scripts and
                       JSON it is only listed
     richtext_tags     RichText tags that do not pair (火箭三消 `<color=#fff>..</c>`) or are not Cocos tags
     ad_button_text    a rewarded-ad button whose words do not say "watch an ad" (奔跑吧巨人 win page `CLAIM x2`):
                       buttons from docs/game_capabilities.json ad_entries block; buttons only named like an ad button
                       (btnAd, videoBtn, watchAd, double...) are review rows. Use the kit's watch-ad button picture.

  python english_copy_guard.py --project GAME [--dry-run] [--out JSON]
Exit codes: 0 nothing blocking, 1 blocking rows (missing glyphs, unpaired tags, ad text, literal newline left), 2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from pathlib import Path

SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles', '.tiktok-kit', 'settings'}
UI_EXT = {'.prefab', '.fire', '.scene'}
CJK = re.compile(r'[\u3400-\u9fff\uf900-\ufaff\u3040-\u30ff]')
DIGITS = '0123456789'
# a placeholder a number goes into: {n} {0} {a} ${x} %d %s %1$s
PLACEHOLDER = re.compile(r'\$\{[^}]*\}|\{[A-Za-z0-9_]*\}|%(?:\d+\$)?[ds]')
TOKEN = re.compile(r'\S+')
# script concatenation:  'x' + n   n + '%'   a + '/' + b   (a short literal on either side of a + with a name / number)
LIT = r'''(['"])([^'"\\\n]{1,4})\1'''
CONCAT_AFTER = re.compile(LIT + r'''\s*\+\s*[A-Za-z_$(0-9]''')
CONCAT_BEFORE = re.compile(r'''[A-Za-z0-9_$)\]]\s*\+\s*''' + LIT)
TEMPLATE = re.compile(r'`([^`\\]{0,80})`')
DISPLAY = re.compile(r'\.(?:string|text)\s*\+?=|setString\s*\(')
SHOWN = re.compile(r'[\x21-\x7e×]')
# R4P4: a format string built on one line and put on the label on a later one (const t = 'x' + n; label.string = t;)
SIMPLE_NAME = re.compile(r'(?<![\w$.\'"`])([A-Za-z_$][\w$]*)\b(?!\s*[(.\'"`:])')
ASSIGN = re.compile(r'^\s*(?:(?:const|let|var)\s+)?([A-Za-z_$][\w$]*)\s*(?::\s*[\w.<>\[\]| ]+?)?\s*\+?=(?!=)\s*(.+)$')
JS_WORDS = {'this', 'new', 'true', 'false', 'null', 'undefined', 'return', 'typeof', 'void', 'await', 'String',
            'Number', 'Math', 'const', 'let', 'var', 'cc', 'if', 'else'}
TRACK_BACK = 40               # lines looked back from the label line (about one function)
TRACK_DEPTH = 3               # t = s + '!'; s = 'x' + n: assignments followed
RICH_TAG = re.compile(r'<\s*(/?)\s*([A-Za-z]+)\b[^>]*?(/?)\s*>')
COCOS_RICH = {'color', 'size', 'b', 'i', 'u', 'outline', 'img', 'on', 'br', 'param'}
SELF_CLOSING = {'img', 'br'}
AD_WORDS = re.compile(r'\b(watch|ad|ads|video)\b', re.I)
AD_NAME = re.compile(r'(?:^|[_\-\s])(?:ad|ads|video|watch)(?:[_\-\s]|$)|(?:btn|button)_?(?:ad|video)|'
                     r'(?:ad|video|watch)_?(?:btn|button)|watchad|double', re.I)
WORD_IMAGE_MAX = 16          # characters in a fixed word picture (CLAIM, NO THANKS, LEVEL, BEST, TRY AGAIN ...)


def ref(v):
    return v.get('__id__') if isinstance(v, dict) else None


def ui_files(root):
    assets = Path(root) / 'assets'
    for p in sorted(assets.rglob('*')) if assets.is_dir() else []:
        if p.suffix.lower() in UI_EXT and p.is_file() and not (SKIP_DIRS & {x.lower() for x in p.relative_to(root).parts[:-1]}):
            yield p


def script_files(root):
    assets = Path(root) / 'assets'
    for p in sorted(assets.rglob('*')) if assets.is_dir() else []:
        if p.suffix.lower() in ('.js', '.ts') and p.is_file() and not p.name.endswith('.d.ts') \
                and not (SKIP_DIRS & {x.lower() for x in p.relative_to(root).parts[:-1]}):
            yield p


def json_files(root):
    assets = Path(root) / 'assets'
    for p in sorted(assets.rglob('*.json')) if assets.is_dir() else []:
        if p.is_file() and not (SKIP_DIRS & {x.lower() for x in p.relative_to(root).parts[:-1]}):
            yield p


class Doc:
    def __init__(self, path):
        self.path = Path(path)
        self.raw = self.path.read_text(encoding='utf-8')
        self.objs = json.loads(self.raw)
        if not isinstance(self.objs, list):
            raise ValueError('not a Cocos prefab / scene list')

    def get(self, i):
        return self.objs[i] if isinstance(i, int) and 0 <= i < len(self.objs) else None

    def path_of(self, node):
        names, seen = [], set()
        while isinstance(node, dict) and id(node) not in seen and node.get('__type__') in ('cc.Node', 'cc.Scene'):
            seen.add(id(node))
            if node.get('__type__') == 'cc.Node':
                names.append(str(node.get('_name') or ''))
            node = self.get(ref(node.get('_parent')))
        return '/'.join(reversed(names))

    def comps(self, node):
        return [c for c in (self.get(ref(x)) for x in node.get('_components') or []) if isinstance(c, dict)]

    def children(self, node):
        return [c for c in (self.get(ref(x)) for x in node.get('_children') or []) if isinstance(c, dict)]


def text_keys(comp):
    return [k for k in ('_N$string', '_string') if isinstance(comp.get(k), str)]


# ------------------------------------------------------------------------------------------------ 1. glyph set
def value_chars(text):
    """Characters glued to a number or a placeholder in one English text: 'x{n}' -> {'x'}, '{a}/{b}' -> {'/'},
    'Lv.{n}' -> {'L','v','.'}, '05:30' -> {':'}, 'Score 120' -> {} (the word stands apart)."""
    out = set()
    for tok in TOKEN.findall(text):
        marked = PLACEHOLDER.sub('\0', tok)
        if ('\0' not in marked and not re.search(r'\d', marked)) or re.search(r'[A-Za-z]{2,}', marked):
            continue
        out.update(ch for ch in marked if ch != '\0' and not ch.isdigit() and SHOWN.fullmatch(ch))
    return out


def _names(expr):
    expr = re.sub(r'''(['"])(?:(?!\1)[^\\\n]|\\.)*\1''', ' ', expr.split('//', 1)[0])   # drop string literals, comment
    return set(SIMPLE_NAME.findall(expr)) - JS_WORDS


def display_lines(src):
    """Lines that put text on a label, plus (R4P4) the lines that build a simple variable shown a few lines later:
    `const t = 'x' + n;` then `label.string = t;`. A variable is followed back up to TRACK_BACK lines (about one
    function) and through up to TRACK_DEPTH assignments (`s = 'x' + n; t = s + '!'; label.string = t`); `this.x`
    members and function parameters are not followed."""
    lines = src.splitlines()
    keep = set()
    for i, ln in enumerate(lines):
        m = DISPLAY.search(ln)
        if not m:
            continue
        keep.add(i)
        names = _names(ln[m.end():])
        seen, start = set(names), max(0, i - TRACK_BACK)
        for _ in range(TRACK_DEPTH):
            found = set()
            for j in range(start, i):
                a = ASSIGN.match(lines[j])
                if a and a.group(1) in names and j not in keep:
                    keep.add(j)
                    found |= _names(a.group(2))
            names = found - seen
            seen |= names
            if not names:
                break
    return [lines[i] for i in sorted(keep)]


def script_value_chars(src):
    """Short literals concatenated with a value in code ('x' + n, n + '%', `+${n}`)."""
    out, fmts = set(), []
    # only lines that put text on a label (calibrated on 4 games: without this, URL / path / log building added
    # ( ) = > { } $ _ and letters to the set); R4P4: and the lines building a variable that a label line shows
    src = '\n'.join(display_lines(src))
    for m in list(CONCAT_AFTER.finditer(src)) + list(CONCAT_BEFORE.finditer(src)):
        lit = m.group(2)
        if CJK.search(lit) or not lit.strip() or len(lit.strip()) > 3:
            continue
        if re.fullmatch(r'[A-Za-z]{2,}', lit.strip()):
            continue                                   # 'px', 'ms', 'id': a word, not a value glyph
        out.update(ch for ch in lit if not ch.isspace() and SHOWN.fullmatch(ch))
        fmts.append(lit)
    for m in TEMPLATE.finditer(src):
        body = m.group(1)
        if '${' in body and not CJK.search(body):
            chars = value_chars(body)
            out |= chars
            if chars:
                fmts.append(body)
    return out, fmts


# R4R2 (补查3 第 10 组, 方块收割者 / 弹球传奇 11-05): a number formatter's unit table (`var UNITS = ['K','M','B','T','Q']`)
# and the symbols it glues on (`... + 'E' + exp`, toFixed's '.') reach a bitmap Label without passing a label line, so the
# label-line scan above never saw them and the digit font was drawn with 0-9 only.
UNIT_TABLE = re.compile(r'''\[\s*((?:(['"])[A-Za-z]{0,2}\2\s*,\s*)+(['"])[A-Za-z]{0,2}\3)\s*,?\s*\]''')
UNIT_LIT = re.compile(r'''(['"])([A-Za-z]{0,2})\1''')
FORMAT_HINT = re.compile(r'toExponential|toFixed|toPrecision|Math\.pow\(\s*1000|1e3\b|/\s*1000\b|Math\.log10|LN10')
FORMAT_NEAR = 25              # formatter calls (toFixed, toExponential, /1000 ...) this far below a unit table count
FORMAT_TAIL = 15              # lines below a table / formatter call whose short concatenations are value glyphs


def number_format_chars(src):
    """Unit letters of number-formatter tables and the short literals glued on near them:
    ['K','M','B','T','Q'] + `'E' +` + toFixed -> 'BEKMQT.'; arrays without a K and an M ('Off','Low') are not units."""
    lines = src.splitlines()
    out, fmts, anchors = set(), [], set()
    for m in UNIT_TABLE.finditer(src):
        units = [u for _, u in UNIT_LIT.findall(m.group(1)) if u]
        if len(units) < 2 or not ({'k', 'm'} <= {u.lower() for u in units}):
            continue
        out.update(ch for u in units for ch in u)
        fmts.append('[%s]' % ','.join(units))
        anchors.add(src.count('\n', 0, m.start()))
    if not anchors:
        return out, fmts
    # the formatter follows its table: formatter calls up to FORMAT_NEAR lines below a table, then FORMAT_TAIL lines
    # below each (calibrated on GiantRush util.ts: a UUID builder 100 lines away added '-' with a wider window)
    anchors |= {i for i, ln in enumerate(lines) if FORMAT_HINT.search(ln) and any(0 <= i - t <= FORMAT_NEAR for t in anchors)}
    near = sorted({j for a in anchors for j in range(max(0, a - 3), min(len(lines), a + FORMAT_TAIL + 1))})
    body = '\n'.join(lines[j] for j in near)
    for m in list(CONCAT_AFTER.finditer(body)) + list(CONCAT_BEFORE.finditer(body)):
        lit = m.group(2).strip()
        if lit and len(lit) <= 3 and not CJK.search(lit) and not re.fullmatch(r'[A-Za-z]{2,}', lit):
            out.update(ch for ch in lit if SHOWN.fullmatch(ch))
            fmts.append(lit)
    if re.search(r'toFixed\(\s*(?!0\s*\))', body):
        out.add('.')                                   # 1.2K: a scaled value keeps its decimal point
    return out, fmts


def copy_table_rows(root):
    p = Path(root) / 'docs/copy/copy-table.csv'
    if not p.is_file():
        return []
    try:
        rows = list(csv.reader(p.read_text(encoding='utf-8-sig').splitlines()))
    except (OSError, csv.Error):
        return []
    head = [x.strip().lower() for x in rows[0]] if rows else []
    if head and set(head[:2]) & {'zh', 'en', 'cn', 'english', 'chinese'}:
        rows = rows[1:]
    else:
        head = []
    out = []
    for r in rows:
        if len(r) < 2:
            continue
        row = {'en': r[1]}
        if head:
            row.update({h: (r[i] if i < len(r) else '') for i, h in enumerate(head)})
            row['en'] = r[1]
        out.append(row)
    return out


def is_word_image(text):
    t = text.strip()
    return bool(t) and len(t) <= WORD_IMAGE_MAX and not PLACEHOLDER.search(t) and not re.search(r'\d', t) \
        and re.fullmatch(r"[A-Za-z][A-Za-z !?'&-]*", t) is not None and len(t.split()) <= 3 and t.upper() == t


def parse_fnt_ids(text):
    return {int(m.group(1)) for m in re.finditer(r'^\s*char\s+id=(\d+)', text, re.M)}


def charset(root):
    root = Path(root)
    value, words, sources = set(DIGITS), {}, []
    for row in copy_table_rows(root):
        en = row.get('en') or ''
        if CJK.search(en):
            continue
        v = value_chars(en)
        if v:
            value |= v
            sources.append({'from': 'docs/copy/copy-table.csv', 'text': en, 'chars': ''.join(sorted(v))})
        kind = (row.get('kind') or row.get('as') or '').strip().lower()
        if kind in ('image', 'word_image', 'picture') or is_word_image(en):
            words.setdefault(en.strip(), 'docs/copy/copy-table.csv')
    for f in ui_files(root):
        try:
            doc = Doc(f)
        except (OSError, ValueError):
            continue
        rel = f.relative_to(root).as_posix()
        for o in doc.objs:
            if isinstance(o, dict) and o.get('__type__') in ('cc.Label', 'cc.RichText'):
                for k in text_keys(o)[:1]:
                    s = RICH_TAG.sub('', o[k])
                    if CJK.search(s):
                        continue
                    v = value_chars(s)
                    if v:
                        value |= v
                        sources.append({'from': rel, 'text': s, 'chars': ''.join(sorted(v))})
    for f in script_files(root):
        try:
            src = f.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        v, fmts = script_value_chars(src)
        if v:
            value |= v
            sources.append({'from': f.relative_to(root).as_posix(), 'formats': sorted(set(fmts))[:20],
                            'chars': ''.join(sorted(v))})
        v, fmts = number_format_chars(src)            # R4R2: unit tables of number formatters
        if v:
            value |= v
            sources.append({'from': f.relative_to(root).as_posix(), 'number_format': sorted(set(fmts))[:20],
                            'chars': ''.join(sorted(v))})
    fit = root / 'docs/english/fit-labels.json'
    try:
        for r in json.loads(fit.read_text(encoding='utf-8')).get('bitmap_needed') or []:
            if r.get('kind') == 'word_image' and r.get('text'):
                words.setdefault(str(r['text']).strip(), 'docs/english/fit-labels.json')
    except (OSError, ValueError, AttributeError):
        pass
    fonts = []
    assets = root / 'assets'
    for p in sorted(assets.rglob('*.fnt')) if assets.is_dir() else []:
        try:
            ids = parse_fnt_ids(p.read_text(encoding='utf-8', errors='replace'))
        except OSError:
            continue
        has = {chr(i) for i in ids if 0 <= i < 0x110000}
        if not has & set(DIGITS):
            continue                                   # a letter-only font: not a value font
        fonts.append({'font': p.relative_to(root).as_posix(), 'has': ''.join(sorted(has)),
                      'missing': ''.join(sorted(value - has))})
    return {'value_charset': ''.join(sorted(value)), 'word_images': sorted(words), 'word_sources': words,
            'value_sources': sources[:200], 'fonts': fonts}


# --------------------------------------------------------------------------------------------- 2. copy checks
def tag_problems(text):
    """[] when every RichText tag pairs: '<color=#f00>3</c>' -> ['</c> closes <color>']."""
    stack, out = [], []
    for m in RICH_TAG.finditer(text):
        closing, name, selfc = m.group(1), m.group(2).lower(), m.group(3)
        if name not in COCOS_RICH:
            out.append('<%s%s> is not a Cocos RichText tag' % (closing, name))
            continue
        if selfc or name in SELF_CLOSING:
            continue
        if not closing:
            stack.append(name)
        elif not stack:
            out.append('</%s> closes nothing' % name)
        elif stack[-1] != name:
            out.append('</%s> closes <%s>' % (name, stack[-1]))
            stack.pop()
        else:
            stack.pop()
    out += ['<%s> is never closed' % n for n in stack]
    return out


def ad_paths(root):
    try:
        d = json.loads((Path(root) / 'docs/game_capabilities.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    out = []
    for r in d.get('ad_entries') or [] if isinstance(d, dict) else []:
        if isinstance(r, dict) and r.get('button'):
            out.append(str(r['button']).strip('/'))
    return out


def subtree_texts(doc, node, depth=0):
    out = []
    for c in doc.comps(node):
        if c.get('__type__') in ('cc.Label', 'cc.RichText'):
            for k in text_keys(c)[:1]:
                if c[k].strip():
                    out.append(RICH_TAG.sub('', c[k]))
    if depth < 4:
        for ch in doc.children(node):
            out += subtree_texts(doc, ch, depth + 1)
    return out


def check(root, dry_run=False):
    root = Path(root)
    rec = {'literal_newline': [], 'richtext_tags': [], 'ad_button_text': [], 'ad_button_review': [], 'files_written': []}
    ads = ad_paths(root)
    for f in ui_files(root):
        try:
            doc = Doc(f)
        except (OSError, ValueError):
            continue
        rel = f.relative_to(root).as_posix()
        dirty = False
        for o in doc.objs:
            if not isinstance(o, dict) or o.get('__type__') not in ('cc.Label', 'cc.RichText'):
                continue
            node = doc.get(ref(o.get('node')))
            where = '%s:%s' % (rel, doc.path_of(node) if node else '?')
            for k in text_keys(o):
                s = o[k]
                if '\\n' in s and not CJK.search(s):
                    if not dry_run:
                        o[k] = s.replace('\\r\\n', '\n').replace('\\n', '\n')
                        dirty = True
                    if k == text_keys(o)[0]:
                        rec['literal_newline'].append({'where': where, 'text': s, 'fixed': not dry_run})
            if o.get('__type__') == 'cc.RichText' or RICH_TAG.search(o.get(text_keys(o)[0], '') if text_keys(o) else ''):
                for k in text_keys(o)[:1]:
                    probs = tag_problems(o[k]) if o.get('__type__') == 'cc.RichText' or '</' in o[k] else []
                    if probs:
                        rec['richtext_tags'].append({'where': where, 'text': o[k], 'problems': probs})
        for node in [o for o in doc.objs if isinstance(o, dict) and o.get('__type__') == 'cc.Node']:
            if not any(c.get('__type__') == 'cc.Button' for c in doc.comps(node)):
                continue
            path = doc.path_of(node)
            listed = any(path == a or path.endswith('/' + a) or a.endswith('/' + path) for a in ads)
            named = bool(AD_NAME.search(str(node.get('_name') or '')))
            if not (listed or named):
                continue
            texts = [t for t in subtree_texts(doc, node) if re.search(r'[A-Za-z]{2}', t) and not CJK.search(t)]
            if not texts or any(AD_WORDS.search(t) for t in texts):
                continue                               # picture only (the kit's watch-ad button) or says WATCH AD
            row = {'where': '%s:%s' % (rel, path), 'text': ' | '.join(texts),
                   'fix': 'an ad button says it plays an ad: WATCH AD x2 / FREE (AD) ...; use the kit watch-ad button picture'}
            rec['ad_button_text' if listed else 'ad_button_review'].append(row)
        if dirty and not dry_run:
            backup = root / 'docs/english/copy-guard/backup' / rel
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, backup)
            f.write_text(json.dumps(doc.objs, ensure_ascii=False, indent=2) + ('\n' if doc.raw.endswith('\n') else ''),
                         encoding='utf-8')
            rec['files_written'].append(rel)
    # copy table and language JSON: listed, not rewritten (a script may split on the two characters on purpose)
    for row in copy_table_rows(root):
        en = row.get('en') or ''
        if '\\n' in en:
            rec['literal_newline'].append({'where': 'docs/copy/copy-table.csv', 'text': en, 'fixed': False})
        probs = tag_problems(en) if '</' in en else []
        if probs:
            rec['richtext_tags'].append({'where': 'docs/copy/copy-table.csv', 'text': en, 'problems': probs})
    for f in json_files(root):
        try:
            data = json.loads(f.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        stack = [data]
        while stack:
            v = stack.pop()
            if isinstance(v, dict):
                stack += list(v.values())
            elif isinstance(v, list):
                stack += v
            elif isinstance(v, str) and not CJK.search(v):
                if '\\n' in v and re.search(r'[A-Za-z]{3}', v):
                    rec['literal_newline'].append({'where': f.relative_to(root).as_posix(), 'text': v, 'fixed': False})
                if '</' in v:
                    probs = tag_problems(v)
                    if probs:
                        rec['richtext_tags'].append({'where': f.relative_to(root).as_posix(), 'text': v, 'problems': probs})
    return rec


def run(root, dry_run=False):
    root = Path(root)
    cs = charset(root)
    ck = check(root, dry_run)
    missing = [f for f in cs['fonts'] if f['missing']]
    covered = [f for f in cs['fonts'] if not f['missing']]
    # Calibrated read-only on 4 English games in progress (11-05): a missing glyph and a literal \n in the copy table /
    # JSON are warnings (DinoMerge's '$' is built by a helper that may never reach a bitmap Label); unpaired RichText
    # tags in a prefab / scene and a recorded ad button without ad words exit 1.
    warnings = []
    if cs['fonts'] and not covered:
        warnings.append('no project .fnt has every value glyph: %s' % '; '.join('%s lacks %s' % (f['font'], f['missing'])
                                                                              for f in missing))
    warnings += ['literal \\n (not rewritten): %s' % r['where'] for r in ck['literal_newline'] if not r['fixed']]
    warnings += ['ad button text (named like an ad button): %s says "%s"' % (r['where'], r['text'])
                 for r in ck['ad_button_review']]
    blocking = ['RichText tags: %s -- %s' % (r['where'], '; '.join(r['problems'])) for r in ck['richtext_tags']
                if not r['where'].startswith('docs/')]
    warnings += ['RichText tags: %s -- %s' % (r['where'], '; '.join(r['problems'])) for r in ck['richtext_tags']
                 if r['where'].startswith('docs/')]
    blocking += ['ad button text: %s says "%s"' % (r['where'], r['text']) for r in ck['ad_button_text']]
    return {'tool': 'english_copy_guard', 'schema': 1, 'project': root.name, 'dry_run': dry_run, 'charset': cs,
            'checks': ck, 'blocking': blocking, 'warnings': warnings, 'passed': not blocking}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--dry-run', action='store_true', help='report only; do not turn literal \\n into line breaks')
    ap.add_argument('--out', type=Path, help='record (default <project>/docs/english/charset.json; with --dry-run and no --out nothing is written)')
    a = ap.parse_args(argv)
    if not (a.project / 'assets').is_dir():
        print(json.dumps({'error': 'not a Cocos project (no assets/): %s' % a.project}, ensure_ascii=False))
        return 2
    rec = run(a.project, a.dry_run)
    # --dry-run is read-only for the project: without --out the record is not written anywhere (preflight passes --out)
    out = a.out or (None if a.dry_run else a.project / 'docs/english/charset.json')
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'tool': 'english_copy_guard', 'passed': rec['passed'], 'value_charset': rec['charset']['value_charset'],
                      'word_images': len(rec['charset']['word_images']), 'fonts': rec['charset']['fonts'],
                      'blocking': rec['blocking'][:40], 'warnings': rec['warnings'][:40], 'review': [r['where'] for r in rec['checks']['ad_button_review']][:20],
                      'record': str(out) if out is not None else '(dry run: not written; pass --out FILE to keep it)'}, ensure_ascii=False, indent=2))
    return 0 if rec['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
