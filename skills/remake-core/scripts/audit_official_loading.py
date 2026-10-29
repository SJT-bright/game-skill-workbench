"""Affected loading presentation only; not ART-06 or functional acceptance.

Runs the real page-content and screenshot consumers, retaining exact capture
coverage. Functional loading/timing/Retry evidence still uses its original gates.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from official_loading import MANIFEST, dumps_in, screenshot, audit, inside


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--dumps', type=Path, required=True)
    parser.add_argument('--binding', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('output already exists; use a fresh report')
    project = args.project.resolve()
    problems, pages = [], []
    try:
        from PIL import Image
        import art_check
        import audit_page_richness
        manifest = json.loads((project / MANIFEST).read_text())
        screens = json.loads((project / 'docs/art/screens.json').read_text())
        if screens.get('runtime_verified') is not True:
            raise ValueError('screen inventory must be runtime-verified')
        binding = json.loads(args.binding.read_text())['binding'] if args.binding else None
        claimed = {inside(project, r['dump']) for r in manifest['frames']}
        found = set()
        observed = set()
        identities = set()
        phases = set()
        identity_phases = {}
        shots = set()
        for d in dumps_in([args.dumps]):
            if Path(d['_file']) not in claimed:
                continue
            found.add(Path(d['_file']))
            errors, stats = audit_page_richness.check(d, Image, project, binding)
            if 'official_loading' not in stats:
                raise ValueError('claimed loading frame lost its evidence mapping')
            pages.append({'file': d['_file'], 'screen': d.get('screen'), 'problems': errors, 'stats': stats})
            problems += [d.get('screen', '?') + ': ' + e for e in errors]
            vp = d.get('viewport', {})
            observed.add((d.get('screen'), vp.get('width'), vp.get('height')))
            identities.add(d.get('screen'))
            phases.add(stats.get('phase'))
            identity_phases.setdefault(d.get('screen'), set()).add(stats.get('phase'))
            shots.add(screenshot(d).resolve())
        if found != claimed or not found:
            problems.append('all claimed normal/retry dumps must be present')
        required_viewports = screens.get('required_viewports', [])
        sizes = {(v.get('width'), v.get('height')) for v in required_viewports}
        if len(sizes) < 2 or any(type(n) is not int or n <= 0 for pair in sizes for n in pair):
            problems.append('retain the original two valid phone viewports')
        if 'retry' not in phases or not (phases - {'retry', None}):
            problems.append('actual normal loading and failure-Retry frames required')
        identities |= {r['id'] for r in screens.get('screens', []) if r.get('purpose') in {'loading','loading_retry'} or r.get('presentation') == 'official_loading'}
        if any(len(values) != 1 for values in identity_phases.values()):
            problems.append('one exact screen identity cannot stand for different loading phases')
        gaps = art_check.screen_viewport_gaps([{'id': i} for i in identities], required_viewports, observed)
        problems += ['missing exact loading screen/viewport: %s@%sx%s' % v for v in gaps]
        if shots:
            dark_out = args.out.with_name(args.out.stem + '-dark.json')
            cmd = [sys.executable, '-B', str(Path(__file__).with_name('audit_dark_area.py')),
                   *map(str, sorted(shots)), '--project', str(project), '--dumps', str(args.dumps), '--out', str(dark_out)]
            if args.binding:
                cmd += ['--binding', str(args.binding)]
            run = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if run.returncode:
                problems.append('actual screenshot consumer refused: ' + (run.stdout + run.stderr)[-1200:])
    except (OSError, ValueError, TypeError, KeyError, ImportError, subprocess.TimeoutExpired) as exc:
        problems.append(str(exc))
    report = {'tool': 'audit_official_loading', 'stage': 'presentation', 'passed': not problems,
              'checked': len(pages), 'pages': pages, 'errors': problems,
              'boundary': 'Affected official loading presentation only; not complete art, timing, recovery or input acceptance.'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
    return int(bool(problems))


if __name__ == '__main__':
    raise SystemExit(main())
