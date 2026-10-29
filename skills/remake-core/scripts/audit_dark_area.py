#!/usr/bin/env python3
"""Measure page screenshots for the negative art rules only (user 2026-10-28: no style, no brightness floor).

Read-only helper. For each screenshot it measures:
  dark_ratio      share of pixels with CIE L* < 30 (large dark areas)
  avg_lstar       average lightness (0 = black, 100 = white); reported for information only, never a
                  pass/fail rule (user 2026-10-27/28: no minimum brightness, no required bright style)
  flat_ratio      share of the single most common colour on the whole screen
  edge_flat_ratio share of the single most common colour in the outer border ring;
                  near 1.0 means the panel sits on a plain black/solid backdrop
                  (e.g. a win popup with no generated background behind it)
  white_gray_ratio   share of colourless white/light-grey pixels (white sheets cut up by cards)
  white_block_ratio  largest connected plain white/near-white block (big white sheets/panels)
  plain_block_ratio  largest connected block of any one plain colour (big solid buttons/panels)

Usage:
  python audit_dark_area.py SCREENSHOT [...] [--max-dark 0.15]
      [--max-flat 0.40] [--max-edge-flat 0.60] [--max-white-block 0.25]
      [--max-plain-block 0.35] [--binding review.json] [--out result.json]

--binding copies the "binding" object of the known-issue review JSON into the report,
so check_known_issues.py can accept the report as current evidence for ART-02/ART-03.
Every limit is a "must not appear" rule: large dark areas, plain black/solid backdrops, big white sheets,
big single-colour blocks. The art style itself comes from the starter pack ART_DIRECTION.
Exit codes: 0 all within limits, 1 at least one over a limit,
2 bad input or output exists, 3 Pillow is not installed (pip install pillow).
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

DARK_LSTAR = 30.0
EDGE = 0.10  # border ring width as a share of width/height


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lstar(r, g, b):
    y = 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)
    return 116.0 * (y ** (1.0 / 3.0)) - 16.0 if y > 0.008856 else 903.3 * y


def _top_share(pixels):
    if not pixels:
        return 0.0
    bins = Counter((r >> 3, g >> 3, b >> 3) for r, g, b in pixels)
    return bins.most_common(1)[0][1] / len(pixels)


CELL = 8  # px on the 360-px thumbnail


def _blocks(pixels, w, h):
    """Largest connected plain block: (any single colour share, near-white share).
    A cell is plain when all its pixels fall in one colour bin; blocks are 4-connected plain cells
    of the same bin. Catches big white sheets and big solid buttons/panels/backdrops."""
    cw, ch = w // CELL, h // CELL
    if not cw or not ch:
        return 0.0, 0.0
    cells = {}
    for cy in range(ch):
        for cx in range(cw):
            bins = set()
            for y in range(cy * CELL, cy * CELL + CELL, 2):
                for x in range(cx * CELL, cx * CELL + CELL, 2):
                    r, g, b = pixels[y * w + x]
                    bins.add((r >> 4, g >> 4, b >> 4))
                    if len(bins) > 1:
                        break
                if len(bins) > 1:
                    break
            if len(bins) == 1:
                cells[(cx, cy)] = bins.pop()
    seen, best_any, best_white = set(), 0, 0
    for start, colour in cells.items():
        if start in seen:
            continue
        stack, size = [start], 0
        seen.add(start)
        while stack:
            x, y = stack.pop(); size += 1
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n not in seen and cells.get(n) == colour:
                    seen.add(n); stack.append(n)
        best_any = max(best_any, size)
        r, g, b = (c * 16 + 8 for c in colour)
        if _lstar(r, g, b) >= 88 and max(r, g, b) - min(r, g, b) <= 40:
            best_white = max(best_white, size)
    total = cw * ch
    return round(best_any / total, 4), round(best_white / total, 4)


def measure(path, image_module):
    with image_module.open(path) as im:
        im = im.convert('RGB')
        im.thumbnail((360, 360))
        w, h = im.size
        pixels = list(im.get_flattened_data()) if hasattr(im, 'get_flattened_data') else list(im.getdata())
    values = [_lstar(*p) for p in pixels]
    ex, ey = max(1, int(w * EDGE)), max(1, int(h * EDGE))
    edge = [pixels[y * w + x] for y in range(h) for x in range(w)
            if x < ex or x >= w - ex or y < ey or y >= h - ey]
    return {'dark_ratio': round(sum(1 for v in values if v < DARK_LSTAR) / len(values), 4),
            'avg_lstar': round(sum(values) / len(values), 1),
            'flat_ratio': round(_top_share(pixels), 4),
            'edge_flat_ratio': round(_top_share(edge), 4),
            'white_gray_ratio': round(sum(1 for p, v in zip(pixels, values)
                                          if v >= 85 and max(p) - min(p) <= 18) / len(values), 4),
            **dict(zip(('plain_block_ratio', 'white_block_ratio'), _blocks(pixels, w, h)))}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('images', nargs='+', type=Path)
    parser.add_argument('--max-dark', type=float, default=0.15, help='max share of pixels with L* < 30 (default 0.15)')
    parser.add_argument('--max-flat', type=float, default=0.40, help='max share of one colour on the whole screen (default 0.40)')
    parser.add_argument('--max-edge-flat', type=float, default=0.60, help='max share of one colour in the border ring (default 0.60)')
    parser.add_argument('--max-white-gray', type=float, default=0.35, help='max share of plain white/light-grey pixels (default 0.35)')
    parser.add_argument('--max-white-block', type=float, default=0.25, help='max connected plain white/near-white block (default 0.25)')
    parser.add_argument('--max-plain-block', type=float, default=0.35, help='max connected block of one plain colour (default 0.35)')
    parser.add_argument('--project', type=Path, help='project for verified official loading presentation only')
    parser.add_argument('--dumps', type=Path, action='append', help='paired runtime dump folders; requires --project')
    parser.add_argument('--binding', type=Path, help='known-issue review JSON whose "binding" is copied into the report')
    parser.add_argument('--out', type=Path, help='write full JSON here (must not exist yet)')
    args = parser.parse_args()
    try:
        from PIL import Image
    except ImportError:
        print(json.dumps({'status': 'error', 'error': 'Pillow not installed: pip install pillow'}), file=sys.stderr)
        return 3
    binding = None
    if args.binding:
        try:
            binding = json.loads(args.binding.read_text(encoding='utf-8')).get('binding')
        except (OSError, ValueError, AttributeError):
            binding = None
        if not isinstance(binding, dict):
            print(json.dumps({'status': 'error', 'error': f'no binding object in {args.binding}'}), file=sys.stderr)
            return 2
    if args.out and args.out.exists():
        print(json.dumps({'status': 'error', 'error': f'output exists: {args.out}'}), file=sys.stderr)
        return 2
    presentations = {}
    if args.project or args.dumps:
        if not args.project or not args.dumps:
            parser.error('--project and --dumps are required together')
        from official_loading import dumps_in, screenshot, audit as audit_official_loading
        try:
            observed = {}
            for dump in dumps_in(args.dumps):
                shot = screenshot(dump).resolve()
                observed[shot] = observed.get(shot, 0) + 1
                result = audit_official_loading(dump, args.project, Image, binding)
                if result is not None:
                    # A second dump must not attach an exception to an ordinary image.
                    if shot in presentations:
                        raise ValueError('ambiguous loading screenshot: ' + str(shot))
                    presentations[shot] = result
            if any(observed[p] != 1 for p in presentations):
                raise ValueError('loading exception shares a screenshot with another capture')
        except (OSError, ValueError, TypeError, KeyError) as exc:
            print(json.dumps({'status': 'error', 'error': str(exc)}), file=sys.stderr)
            return 2
    results, over = [], 0
    for path in args.images:
        if not path.is_file():
            print(json.dumps({'status': 'error', 'error': f'not a file: {path}'}), file=sys.stderr)
            return 2
        m = measure(path, Image)
        m['path'] = str(path)
        problems = []
        presentation = presentations.get(path.resolve())
        if presentation is not None:
            problems, stats = presentation
            m['official_loading'] = stats
            m['problems'] = problems
            m['passed'] = not problems
            over += int(bool(problems))
            results.append(m)
            continue
        if m['dark_ratio'] > args.max_dark:
            problems.append('large dark area')
        if m['flat_ratio'] > args.max_flat:
            problems.append('large single-colour area')
        if m['edge_flat_ratio'] > args.max_edge_flat:
            problems.append('plain black/solid backdrop around panel')
        if m['white_block_ratio'] > args.max_white_block or m['white_gray_ratio'] > args.max_white_gray:
            problems.append('large plain white panel/sheet')
        elif m['plain_block_ratio'] > args.max_plain_block:
            problems.append('large plain single-colour block')
        m['problems'] = problems
        m['passed'] = not problems
        over += 0 if m['passed'] else 1
        results.append(m)
    report = {'tool': 'audit_dark_area', 'max_dark': args.max_dark,
              'max_flat': args.max_flat, 'max_edge_flat': args.max_edge_flat, 'dark_lstar_below': DARK_LSTAR,
              'max_white_block': args.max_white_block, 'max_white_gray': args.max_white_gray, 'max_plain_block': args.max_plain_block,
              'checked': len(results), 'failed': over, 'passed': over == 0,
              'checks': [{'path': r['path'], 'passed': r['passed']} for r in results], 'results': results,
              'note': 'Measurement only, negative rules only (no brightness floor; avg_lstar is informational). '
                      'Screenshots must cover every page and popup of the current build.'}
    if binding is not None:
        report['binding'] = binding
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = {'checked': len(results), 'failed': over,
               'over': [{'path': r['path'], 'problems': r['problems'], 'dark_ratio': r['dark_ratio'],
                         'avg_lstar': r['avg_lstar'], 'edge_flat_ratio': r['edge_flat_ratio'],
                         'white_block_ratio': r['white_block_ratio'], 'white_gray_ratio': r['white_gray_ratio'], 'plain_block_ratio': r['plain_block_ratio']}
                        for r in results if not r['passed']][:10]}
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if over else 0


if __name__ == '__main__':
    raise SystemExit(main())
