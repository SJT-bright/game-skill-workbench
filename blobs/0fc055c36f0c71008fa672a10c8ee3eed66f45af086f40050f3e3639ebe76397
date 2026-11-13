"""Optional production budgets in CSS pixels; never a screenshot approval.

Historical image density is a first-generation reserve recommendation, advisory
by default. Only an explicit blocking clarity policy gates source/render ratios.
Font geometry, case coverage, units and source integrity remain separate checks.

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
from clarity_policy import resolve_policy, measure, validate as validate_clarity, add_arguments as add_clarity_arguments, from_args as clarity_from_args


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
    density = number(data['density'], 'density', strict=True)
    result = {'unit': 'css_px', 'density': density, 'cases': []}
    for row in rows:
        size = pair(row['css_size'], 'css_size')
        for dimension in size:
            number(dimension * density, 'required output dimension', strict=True)
        result['cases'].append({'id': row['id'], 'css_size': size})
    return result


def plan_output(data, expected_cases):
    """Recommend source dimensions before the first request; legacy density is a reserve, not a default gate."""
    budget = validate_budget(data, expected_cases)
    if budget is None:
        raise ValueError('planning needs a declared budget')
    required = [math.ceil(max(r['css_size'][i] for r in budget['cases']) * budget['density']) for i in (0, 1)]
    return {'scope': 'source_budget_only', 'runtime_verified': False,
            'minimum_output_size': required, 'recommended_output_size': required,
            'minimum_output_size_semantics': 'legacy key: generation reserve recommendation, not default acceptance gate',
            'blocking': False, 'cases': budget['cases']}


def validate_output(data, size, policy=None, background=False, project=None):
    """Measure final source pixels. Old density is reserve advice; only explicit strict policy blocks.

    Pass the project-resolved policy from a producer, or project=... for direct
    use. This never changes declared budget bytes or canonical legacy usage.
    Dimensions, case coverage and units remain strict input integrity checks.
    """
    if data is None:
        return None
    ids = [r.get('id') for r in data.get('cases', []) if isinstance(r, dict)] if isinstance(data, dict) else []
    budget = validate_budget(data, ids)
    if not isinstance(size, (list, tuple)) or len(size) != 2 or any(type(x) is not int or x <= 0 for x in size):
        raise ValueError('output size must contain two positive integer pixel dimensions')
    effective = policy if policy is not None else resolve_policy(project)
    keys = ('min_ratio', 'background_min_ratio', 'severity')
    if not isinstance(effective, dict) or any(key not in effective for key in keys):
        raise ValueError('output policy must be a fully resolved clarity policy')
    validate_clarity({key: effective[key] for key in keys}, 'output policy')
    required = plan_output(budget, ids)['minimum_output_size']
    rows, notices = [], []
    for row in budget['cases']:
        metric = measure(size, row['css_size'], effective, background=background)
        below_reserve = metric['source_render_ratio'] + 1e-9 < budget['density']
        measured = dict(row, density=metric['source_render_ratio'], **metric,
                        below_generation_reserve=below_reserve,
                        generation_reserve_ratio=budget['density'])
        rows.append(measured)
        if metric['blocking']:
            raise ValueError('explicit strict clarity policy: final output %s for %s is %.6gx source/render, below configured %.6gx; original density %.6gx is generation reserve only' %
                             (list(size), row['id'], metric['source_render_ratio'], metric['threshold'], budget['density']))
        if below_reserve or metric['below_threshold']:
            notices.append({'case': row['id'], 'source_render_ratio': metric['source_render_ratio'],
                            'generation_reserve_ratio': budget['density'], 'reference_ratio': metric['threshold'],
                            'severity': 'advisory', 'blocking': False,
                            'message': 'Recorded size reference only: actual visible clarity is the standard; no regeneration or producer replay is scheduled by this ratio.'})
    return {'scope': 'source_budget_only', 'runtime_verified': False, 'visual_passed': None,
            'minimum_output_size': required, 'recommended_output_size': required,
            'minimum_output_size_semantics': 'legacy key: generation reserve recommendation, not default acceptance gate',
            'output_size': list(size), 'cases': rows, 'clarity_policy': effective,
            'advisories': notices, 'blocking': False, 'auto_regenerate': False}


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


def plan_individual(asset_id, purpose, max_css, *, background=False, reserve_ratio=None,
                    safe_edge_px=8, generator_sizes=None, source_image=None, render_css=None):
    """First-request source-size advice; no production declaration or quality gate.

    max_css is the largest intended content size across all target views, never
    design units or DPR. Safety space is transparent margin for isolated UI and
    painted bleed for a background. Existing opt-in production budgets stay separate.
    """
    if not isinstance(asset_id, str) or not asset_id.strip() or not isinstance(purpose, str) or not purpose.strip():
        raise ValueError('individual planning needs asset-id and a concrete purpose')
    css = pair(max_css, 'max_css')
    density = number(reserve_ratio if reserve_ratio is not None else (1.5 if background else 2.0), 'reserve_ratio', strict=True)
    edge = number(safe_edge_px, 'safe_edge_px')
    content = [math.ceil(number(x * density, 'content source dimension', strict=True)) for x in css]
    requested = [math.ceil(number(x + 2 * edge, 'canvas source dimension', strict=True)) for x in content]
    tiers = []
    for size in generator_sizes or []:
        if len(size) != 2 or any(type(x) is not int or x <= 0 for x in size):
            raise ValueError('generator sizes must be positive integer W H pairs')
        tiers.append(list(size))
    fits = [size for size in tiers if all(size[i] >= requested[i] for i in (0, 1))]
    fits.sort(key=lambda size: size[0] * size[1])
    selected = fits[0] if fits else None
    options = []
    if tiers and not selected:
        options.append({'choice': 'larger_generator_tier', 'at_least_source_px': requested,
                        'message': 'Choose a larger available output tier before the first generation request.'})
        alternatives = []
        for size in tiers:
            factor = min(max(0, size[i] - 2 * edge) / (css[i] * density) for i in (0, 1))
            if factor > 0:
                alternatives.append({'generator_size': size, 'uniform_display_scale': min(1, factor),
                                     'max_css_size': [round(x * min(1, factor), 3) for x in css]})
        alternatives.sort(key=lambda row: -row['uniform_display_scale'])
        if alternatives:
            options.append({'choice': 'smaller_display', **alternatives[0],
                            'message': 'Keep content aspect ratio and reduce the planned display, if acceptable to the product.'})
    canvas = selected or requested
    result = {'scope': 'first_generation_advice_only', 'generation_mode': 'individual',
              'asset_id': asset_id.strip(), 'purpose': purpose.strip(), 'background': bool(background),
              'max_css_size': css, 'content_aspect_ratio': css[0] / css[1],
              'reserve_ratio': density, 'reserve_is_acceptance_threshold': False,
              'safe_edge_px': edge, 'safe_edge_role': 'painted bleed outside final crop' if background else 'transparent margin outside artwork',
              'recommended_content_source_px': content, 'recommended_source_px': requested,
              'recommended_canvas_aspect_ratio': requested[0] / requested[1],
              'generator_sizes': tiers, 'selected_generator_size': selected,
              'composition_content_rect_px': [(canvas[i] - content[i]) / 2 for i in (0, 1)] + content,
              'optional_safe_margin_crop_rect_px': [(canvas[i] - requested[i]) / 2 for i in (0, 1)] + requested,
              'postprocess_note': 'If the selected output tier is larger, an optional lossless crop keeps the declared safety margin; no regeneration/retry is scheduled.',
              'generator_limit_advisories': options, 'needs_size_decision_before_request': bool(tiers and not selected),
              'auto_generate': False, 'auto_retry': False, 'blocking': False,
              'runtime_verified': False, 'visual_passed': None,
              'acceptance': 'Actual visible clarity is the standard. Generation reserves are planning advice, not a resolution acceptance gate; missing glyphs, cropping, distortion, contrast and text height remain independent.'}
    if render_css is not None and source_image is None:
        raise ValueError('render-css measurement needs an actual source-image')
    if source_image is not None:
        from PIL import Image
        image = Path(source_image).resolve()
        with Image.open(image) as im:
            actual = list(im.size)
        display = pair(render_css, 'render_css') if render_css is not None else css
        usable = [max(0, x - 2 * edge) for x in actual]
        result['source_render_measurement'] = {
            'source_image': str(image), 'sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
            'source_px': actual, 'render_css': display,
            'source_render_ratio': min(actual[i] / display[i] for i in (0, 1)),
            'usable_content_ratio_assuming_declared_edges': min(usable[i] / display[i] for i in (0, 1)),
            'render_origin': 'caller-supplied observed CSS; no browser proof' if render_css is not None else 'planned maximum CSS, not an observed runtime size',
            'severity': 'advisory', 'blocking': False, 'visual_passed': None}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--budget', type=Path)
    parser.add_argument('--expected-cases', nargs='+')
    parser.add_argument('--size', nargs=2, type=int)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--font')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--plan-individual', action='store_true', help='before generation: advise one complete standalone asset; never a quality gate')
    parser.add_argument('--asset-id')
    parser.add_argument('--purpose')
    parser.add_argument('--max-css', nargs=2, type=float, metavar=('W', 'H'), help='largest intended visible CSS size across target views')
    parser.add_argument('--background', action='store_true')
    parser.add_argument('--reserve-ratio', type=float, help='first-generation reserve only; default ordinary 2/background 1.5, adjustable')
    parser.add_argument('--safe-edge-px', type=float, help='source pixels per edge (default 8): transparent UI margin or painted background bleed')
    parser.add_argument('--generator-size', nargs=2, type=int, action='append', metavar=('W', 'H'), help='available external output tier; repeat; no generation is executed')
    parser.add_argument('--source-image', type=Path, help='optional actual image to read dimensions/SHA for comparison')
    parser.add_argument('--render-css', nargs=2, type=float, metavar=('W', 'H'), help='optional observed CSS for source/render record; requires source-image')
    add_clarity_arguments(parser)
    args = parser.parse_args(argv)
    try:
        effective_policy = clarity_from_args(args, args.project)
    except ValueError as error:
        parser.error(str(error))
    try:
        if args.plan_individual:
            if args.budget or args.expected_cases or args.font or args.project or args.size:
                raise ValueError('--plan-individual is separate from legacy budget/font validation')
            result = plan_individual(args.asset_id, args.purpose, args.max_css, background=args.background,
                                     reserve_ratio=args.reserve_ratio, safe_edge_px=args.safe_edge_px if args.safe_edge_px is not None else 8,
                                     generator_sizes=args.generator_size, source_image=args.source_image, render_css=args.render_css)
            report = {'passed': True, 'scope': 'planning_input_valid_only', 'visual_passed': None, 'advisory': True, 'measurements': result}
            if args.out:
                args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps(report, ensure_ascii=False))
            return 0
        if not args.budget or not args.expected_cases:
            raise ValueError('legacy mode requires --budget and --expected-cases; use --plan-individual for first-request advice')
        if args.asset_id or args.purpose or args.max_css or args.background or args.reserve_ratio is not None or args.safe_edge_px is not None or args.generator_size or args.source_image or args.render_css:
            raise ValueError('individual planning options require --plan-individual')
        data = json.loads(args.budget.read_text())
        if data is None:
            raise ValueError('explicit budget file cannot contain null')
        if args.font:
            if args.project is None or args.size is not None:
                raise ValueError('--font needs --project and does not accept --size')
            result = validate_font_budget(args.project, args.font, data, args.expected_cases)
        else:
            result = (plan_output(data, args.expected_cases) if args.size is None else
                      validate_output(validate_budget(data, args.expected_cases), args.size, policy=effective_policy))
        report = {'passed': True, 'declared': result is not None, 'measurements': result}
    except (OSError, ValueError) as error:
        report = {'passed': False, 'error': str(error)}
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
