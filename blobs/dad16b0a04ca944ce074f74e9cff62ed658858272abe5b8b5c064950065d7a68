#!/usr/bin/env python3
"""Bitmap fonts only for digits and symbols; sentences use a real font (user 2026-10-28).

Image-generated letter atlases often draw lowercase letters as capitals or omit them, so text like
"Help ... Tap ... pond" renders as "HelP ... TaP ... Pond". This audit reads the project's .fnt files,
their .meta uuids and the Labels in scenes/prefabs, and fails on:
  letter_case_alias   a lowercase glyph uses the same atlas rectangle as its capital
  missing_glyph       a Label string uses a character its bitmap font does not have
  sentence_in_bitmap  a multi-word Label string is bound to a bitmap font (use a TTF font)
  partial_letter_case a mixed-case bitmap font lacks the other case of some letter (a likely substitution)
Runtime strings set from code are not visible here; the art stage still reviews screenshots.
"""
import argparse
import json
import re
from pathlib import Path

CHAR = re.compile(r'\bid=["\']?(\d+)')
FIELD = re.compile(r'\b(x|y|width|height|page)=["\']?(-?\d+)')


def glyphs(path):
    """{char: (page, x, y, w, h)} from a text or XML BMFont file."""
    out = {}
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if not (line.startswith('char ') or line.startswith('<char ')):
            continue
        m = CHAR.search(line)
        if not m:
            continue
        f = dict(FIELD.findall(line))
        out[chr(int(m.group(1)))] = tuple(int(f.get(k, 0)) for k in ('page', 'x', 'y', 'width', 'height'))
    return out


def uuid_of(path):
    meta = path.with_name(path.name + '.meta')
    try:
        return json.loads(meta.read_text(encoding='utf-8')).get('uuid')
    except (OSError, ValueError):
        return None


def labels(project):
    """(file, font uuid, string) for every cc.Label in scenes and prefabs."""
    rows = []
    for p in sorted(project.rglob('*')):
        if p.suffix not in ('.fire', '.prefab', '.scene') or 'node_modules' in p.parts or 'library' in p.parts:
            continue
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        for obj in data if isinstance(data, list) else []:
            if not isinstance(obj, dict) or obj.get('__type__') != 'cc.Label':
                continue
            font = obj.get('_N$file') or obj.get('_font') or {}
            text = obj.get('_N$string', obj.get('_string', ''))
            if isinstance(font, dict) and font.get('__uuid__') and isinstance(text, str):
                rows.append((p, font['__uuid__'], text))
    return rows


def numeric_units(project, path, glyph, usages):
    """A numeric font may contain measured formatter units, not an alphabet.

    Re-read the real glyph set and usage strings. The existing charset producer
    supplies dynamic formatter requirements; a declaration alone never exempts
    alphabet glyphs or bitmap sentences.
    """
    letters = {c for c in glyph if c.isascii() and c.isalpha()}
    if not set('0123456789') <= set(glyph) or not letters <= set('BKMxX'):
        return set()
    if any(re.search(r'[A-WYZa-wyz]{2,}|[A-Za-z]\s+[A-Za-z]', value) for value in usages):
        return set()
    observed = {c for value in usages if re.fullmatch(r'[\d\s.,+−\-/%:×xXBKM]*', value) for c in value}
    try:
        doc = json.loads((project/'docs/english/charset.json').read_text(encoding='utf-8-sig'))
        rel = path.relative_to(project).as_posix()
        font = next((f for f in doc.get('fonts', []) if isinstance(f, dict) and f.get('font') == rel
                     and set(f.get('has', '')) == set(glyph)), None)
        if font:
            observed.update(str(doc.get('value_charset', '')))
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    units = set('BKM') & observed
    # x/X are symbols only when the actual atlas proves the same × glyph.
    if '×' in glyph and glyph['×'][3] > 0:
        units.update(c for c in 'xX' if c in glyph and glyph[c] == glyph['×'])
    return units


def audit(project):
    project = Path(project).resolve()
    fonts = {}
    for p in sorted((project / 'assets').rglob('*.fnt')) if (project / 'assets').is_dir() else []:
        fonts[uuid_of(p) or str(p)] = (p, glyphs(p))
    findings = []

    def add(kind, path, detail):
        findings.append({'kind': kind, 'file': str(Path(path).relative_to(project)), 'detail': detail})
    label_rows = labels(project)
    for uuid, (path, g) in fonts.items():
        units = numeric_units(project,path,g,[text for _,font,text in label_rows if font == uuid])
        for low in 'abcdefghijklmnopqrstuvwxyz':
            up = low.upper()
            if low in g and up in g and g[low] == g[up] and g[low][3] > 0 and not {low,up} <= units:
                add('letter_case_alias', path, '%r uses the same atlas image as %r' % (low, up))
        letters = {c for c in g if c.isascii() and c.isalpha()}
        if any(c.islower() for c in letters) and any(c.isupper() for c in letters):
            single = sorted(c for c in letters if c.swapcase() not in letters and c not in units)
            if single:
                add('partial_letter_case', path, 'letters with one case only: ' + ''.join(single))
    for path, uuid, text in label_rows:
        if uuid not in fonts:
            continue
        fpath, g = fonts[uuid]
        missing = sorted({c for c in text if not c.isspace() and c not in g})
        if missing:
            add('missing_glyph', path, '%r in %s lacks %s' % (text[:40], fpath.name, ''.join(missing)))
        if len(re.findall(r'[A-Za-z]{2,}', text)) >= 2:
            add('sentence_in_bitmap', path, '%r uses bitmap font %s; sentences need a real (TTF) font' % (text[:40], fpath.name))
    return {'tool': 'audit_bitmap_letter_fonts', 'passed': not findings, 'fonts': len(fonts), 'findings': findings,
            'boundary': 'scene/prefab Labels and .fnt files only; strings set from code need the screenshot review'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    report = audit(a.project)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('tool', 'passed', 'fonts')} | {'findings': report['findings'][:20]}, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
