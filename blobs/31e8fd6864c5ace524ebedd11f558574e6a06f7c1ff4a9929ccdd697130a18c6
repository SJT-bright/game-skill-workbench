"""Optional production budgets in CSS pixels; never a screenshot approval.

The caller supplies the complete expected case list. Legacy producers without
a declaration return None and retain their existing behaviour. No game assets
are written; font preflight uses an isolated byte-identical fnt snapshot.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile


def number(value, label, minimum=0.0, strict=False):
    if type(value) not in (int, float):
        raise ValueError(label + ' must be a finite number')
    try:
        value = float(value)
    except OverflowError:
        raise ValueError(label + ' must be finite') from None
    if not math.isfinite(value) or value < minimum or (strict and value == minimum):
        raise ValueError(label + ' is out of range')
    return value


def pair(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(label + ' must contain two positive CSS dimensions')
    return [number(x, label, strict=True) for x in value]


def cases(data, expected_cases, fields, root_fields):
    if not isinstance(data, dict) or set(data) != set(root_fields):
        raise ValueError('budget has missing or unsupported fields')
    if data['unit'] != 'css_px':
        raise ValueError('budget unit must be css_px; design units and DPR are not CSS sizes')
    if not isinstance(expected_cases, (list, tuple)) or not expected_cases or any(
            not isinstance(x, str) or not x.strip() or x != x.strip() for x in expected_cases):
        raise ValueError('complete nonempty expected case ids are required')
    if len(set(expected_cases)) != len(expected_cases):
        raise ValueError('duplicate expected case ids')
    rows = data['cases']
    if not isinstance(rows, list) or not rows:
        raise ValueError('budget cases must be nonempty')
    ids = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(fields):
            raise ValueError('case has missing or unsupported fields')
        name = row['id']
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError('invalid case id')
        ids.append(name)
    if len(set(ids)) != len(ids) or set(ids) != set(expected_cases):
        raise ValueError('budget cases must cover every expected case exactly once')
    return rows


def validate_budget(data, expected_cases):
    """Return a canonical image declaration, or None for an undeclared legacy asset."""
    if data is None:
        return None
    rows = cases(data, expected_cases, ('id', 'css_size'), ('unit', 'density', 'cases'))
    density = number(data['density'], 'density', minimum=2.0)
    result = {'unit': 'css_px', 'density': density, 'cases': []}
    for row in rows:
        size = pair(row['css_size'], 'css_size')
        for dimension in size:
            number(dimension * density, 'required output dimension', strict=True)
        result['cases'].append({'id': row['id'], 'css_size': size})
    return result


def plan_output(data, expected_cases):
    """Compute the required source dimensions before requesting or cutting artwork."""
    budget = validate_budget(data, expected_cases)
    if budget is None:
        raise ValueError('planning needs a declared budget')
    required = [math.ceil(max(r['css_size'][i] for r in budget['cases']) * budget['density']) for i in (0, 1)]
    return {'scope': 'source_budget_only', 'runtime_verified': False,
            'minimum_output_size': required, 'cases': budget['cases']}


def validate_output(data, size):
    """Check final output pixels after all derivations, never before the last resize."""
    if data is None:
        return None
    ids = [r.get('id') for r in data.get('cases', []) if isinstance(r, dict)] if isinstance(data, dict) else []
    budget = validate_budget(data, ids)
    if not isinstance(size, (list, tuple)) or len(size) != 2 or any(type(x) is not int or x <= 0 for x in size):
        raise ValueError('output size must contain two positive integer pixel dimensions')
    required = plan_output(budget, ids)['minimum_output_size']
    if any(actual < needed for actual, needed in zip(size, required)):
        raise ValueError('final output %s is below the declared CSS budget %s' % (list(size), required))
    return {'scope': 'source_budget_only', 'runtime_verified': False, 'minimum_output_size': required,
            'output_size': list(size), 'cases': [dict(r, density=min(size[i] / r['css_size'][i] for i in (0, 1)))
                                                   for r in budget['cases']]}


def parse_font(raw):
    glyphs, kern, native, line_height = {}, {}, None, None
    for line in raw.decode('utf-8-sig').splitlines():
        tag = line.strip().partition(' ')[0]
        kv = {m[0]: m[1].strip('"') for m in re.findall(r'(\w+)=("[^"]*"|\S+)', line)}
        if tag not in ('info', 'common', 'char', 'kerning'):
            continue
        def field(key, default=None, nonnegative=False):
            try:
                value = float(kv[key] if key in kv else default)
            except (TypeError, ValueError, OverflowError):
                raise ValueError('invalid fnt ' + key) from None
            if not math.isfinite(value) or (nonnegative and value < 0):
                raise ValueError('invalid fnt ' + key)
            return value
        if tag == 'info':
            if native is not None:
                raise ValueError('duplicate fnt info record')
            native = field('size', nonnegative=True)
            if not native.is_integer():
                raise ValueError('fnt size must be integral')
        elif tag == 'common':
            if line_height is not None:
                raise ValueError('duplicate fnt common record')
            line_height = field('lineHeight', nonnegative=True)
            if not line_height.is_integer():
                raise ValueError('fnt lineHeight must be integral')
        elif tag == 'char':
            code = field('id', nonnegative=True)
            if not code.is_integer() or not 0 <= code <= 0x10ffff or int(code) in glyphs:
                raise ValueError('duplicate or invalid fnt character id')
            glyphs[int(code)] = {k: field(k, 0 if k in ('xoffset', 'yoffset') else None,
                                        nonnegative=k in ('width', 'height', 'xadvance'))
                                 for k in ('width', 'height', 'xoffset', 'yoffset', 'xadvance')}
            if any(not value.is_integer() for value in glyphs[int(code)].values()):
                raise ValueError('fnt glyph metrics must be integral')
        else:
            first, second = field('first', nonnegative=True), field('second', nonnegative=True)
            if not first.is_integer() or not second.is_integer() or not (0 <= first <= 0x10ffff and 0 <= second <= 0x10ffff) or (int(first), int(second)) in kern:
                raise ValueError('duplicate or invalid fnt kerning pair')
            kern[(int(first), int(second))] = field('amount')
            if not kern[(int(first), int(second))].is_integer():
                raise ValueError('fnt kerning must be integral')
    if not native or not line_height or not glyphs:
        raise ValueError('font needs positive size, lineHeight and real glyph metrics')
    return native, glyphs, kern


def validate_font_budget(project, font_file, data, expected_cases):
    """Plan one real BMFont at final CSS size; never infer SHRINK or claim runtime size.

    min_font_size_css and min_gap_css are explicit product constraints. This
    helper does not replace glyph-core quality or runtime binding inspection.
    """
    if data is None:
        return None
    rows = cases(data, expected_cases,
                 ('id', 'text', 'font_size_css', 'available_css', 'min_font_size_css', 'spacing_css', 'min_gap_css'),
                 ('unit', 'cases'))
    root = Path(project).resolve()
    candidate = root / font_file
    if any(p.is_symlink() for p in (candidate, *candidate.parents)):
        raise ValueError('symlink font source is not supported')
    source = candidate.resolve()
    if not source.is_relative_to(root / 'assets') or source.suffix.lower() != '.fnt' or not source.is_file():
        raise ValueError('font must be an existing .fnt under project/assets')
    raw = source.read_bytes()
    native, glyphs, kern = parse_font(raw)
    # Reuse the packaged rule on exactly these bytes, without scanning unrelated
    # legacy fonts or modifying the real project. It also keeps CLI use read-only.
    from audit_page_richness import font_advance_problems
    with tempfile.TemporaryDirectory(prefix='art-font-budget-') as temporary:
        isolated = Path(temporary)
        (isolated / 'assets').mkdir()
        (isolated / 'assets/font.fnt').write_bytes(raw)
        findings = font_advance_problems(isolated)
    if findings:
        raise ValueError('; '.join(findings).replace('assets/font.fnt', str(source.relative_to(root))))
    result = {'scope': 'source_budget_only', 'runtime_verified': False, 'font': str(source.relative_to(root)),
              'font_sha256': hashlib.sha256(raw).hexdigest(), 'cases': []}
    for row in rows:
        text = row['text']
        if not isinstance(text, str) or not text.strip() or any(c in text for c in '\n\r\t'):
            raise ValueError('font budget needs an explicit nonempty single-line longest string')
        size = number(row['font_size_css'], 'font_size_css', strict=True)
        minimum = number(row['min_font_size_css'], 'min_font_size_css', strict=True)
        if size < minimum:
            raise ValueError('font size is below min_font_size_css: ' + row['id'])
        available = pair(row['available_css'], 'available_css')
        spacing = number(row['spacing_css'], 'spacing_css')
        minimum_gap = number(row['min_gap_css'], 'min_gap_css', strict=True)
        scale, cursor, prev, previous_right = size / native, 0.0, None, None
        boxes, gaps = [], []
        for char in text:
            code = ord(char)
            if code not in glyphs:
                raise ValueError('missing actual glyph: ' + repr(char))
            glyph = glyphs[code]
            if prev is not None:
                cursor += kern.get((prev, code), 0) * scale + spacing
            if glyph['width'] > 0 and glyph['height'] > 0:
                left = cursor + glyph['xoffset'] * scale
                right = left + glyph['width'] * scale
                if previous_right is not None:
                    gaps.append(left - previous_right)
                boxes.append([left, glyph['yoffset'] * scale, right,
                              (glyph['yoffset'] + glyph['height']) * scale])
                previous_right = right
            elif not char.isspace():
                raise ValueError('longest string contains an empty visible glyph: ' + repr(char))
            cursor += glyph['xadvance'] * scale
            prev = code
        if not boxes:
            raise ValueError('no visible glyphs in longest string')
        bounds = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                  max(b[2] for b in boxes), max(b[3] for b in boxes)]
        # Reserve both engine cursor allocation and actual glyph extents. No
        # automatic shrinking, text shortening, or font mutation occurs here.
        required = [max(cursor, bounds[2]) - min(0, bounds[0]), bounds[3] - min(0, bounds[1])]
        for value in (*bounds, cursor, *required, *gaps):
            if not math.isfinite(value):
                raise ValueError('font computation is not finite')
        if any(needed > room + 1e-9 for needed, room in zip(required, available)):
            raise ValueError('longest string exceeds available_css: ' + row['id'])
        if gaps and min(gaps) + 1e-9 < minimum_gap:
            raise ValueError('actual glyph separation is below min_gap_css: ' + row['id'])
        result['cases'].append({'id': row['id'], 'text': text, 'font_size_css': size,
                                'ink_bounds_css': bounds, 'advance_width_css': cursor,
                                'required_css': required, 'available_css': available,
                                'minimum_actual_gap_css': min(gaps) if gaps else None})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--budget', required=True, type=Path)
    parser.add_argument('--expected-cases', nargs='+', required=True)
    parser.add_argument('--size', nargs=2, type=int)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--font')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.budget.read_text())
        if data is None:
            raise ValueError('explicit budget file cannot contain null')
        if args.font:
            if args.project is None or args.size is not None:
                raise ValueError('--font needs --project and does not accept --size')
            result = validate_font_budget(args.project, args.font, data, args.expected_cases)
        else:
            if args.project is not None:
                raise ValueError('image mode does not accept --project')
            result = (plan_output(data, args.expected_cases) if args.size is None else
                      validate_output(validate_budget(data, args.expected_cases), args.size))
        report = {'passed': True, 'declared': result is not None, 'measurements': result}
    except (OSError, ValueError) as error:
        report = {'passed': False, 'error': str(error)}
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
