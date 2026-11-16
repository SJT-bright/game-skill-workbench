#!/usr/bin/env python3
"""Startup contract check (LOAD-01): the game must always be able to get in (Rainy Duck 2026-10-21).

Two parts, both cheap:
1. Native build sizes: the main package plus the subpackages the game needs before HOME must stay
   under --max-startup-mb (default 10 MiB); audio may not sit in that startup set.
2. Source review list: code patterns that caused "endless loading" before. Each hit must be fixed or
   explained once in docs/startup-contract-review.json ({"<file>:<line>": "why this is fine"}).
     - startup gated on optional SDK feedback (showModal/showLoading/showToast/canIUse)
     - fixed total deadlines for loading (setTimeout >= 10 s near load code)
     - director.loadScene used directly (no "load asset, check generation, then run" step)
     - cc.game.run / game.run called more than once
     - loadRemote/load retried with the same request (no new request on Retry)

  python audit_startup_contract.py --project <Cocos project> [--native <Native build dir>]
         [--startup-subpackages a,b] [--max-startup-mb 10] [--binding review.json] [--out report.json]
Exit codes: 0 pass, 1 problems, 2 bad input.
"""
import argparse
import json
import re
import sys
from pathlib import Path

AUDIO = {'.mp3', '.ogg', '.wav', '.m4a', '.aac'}
SKIP = {'node_modules', 'library', 'temp', 'local', 'build', 'profiles', '.git', 'settings', 'packages', 'extensions'}
RULES = [
    ('optional_api_gate', re.compile(r'(!\s*\w+(\.\w+)*\.(showModal|showLoading|showToast|hideLoading)\b'
                                     r'|canIUse\(\s*["\'](showModal|showLoading|showToast|hideLoading)'
                                     r'|typeof\s+\w+(\.\w+)*\.(showModal|showLoading|showToast)\s*[!=]==?\s*["\']undefined)'),
     'startup must not depend on optional feedback APIs; missing/failed showModal etc. only falls back'),
    ('fixed_deadline', re.compile(r'setTimeout\s*\([^;]*?,\s*([1-9]\d{4,})\s*\)'),
     'fixed total deadline: time out on "no progress for N s in foreground", reset on real progress, pause in background'),
    ('direct_load_scene', re.compile(r'director\.loadScene\s*\('),
     'load the scene asset first (bundle.loadScene / preloadScene), check it still belongs to the current attempt, then run it'),
    ('same_request_retry', re.compile(r'retry[^\n]{0,80}(loadRemote|loadRes|\.load)\(|(loadRemote|loadRes)\([^\n]{0,80}retry', re.I),
     'Retry must issue a new request (new Image/request, old result detached), not re-call the same pending load'),
]
LOAD_WORDS = re.compile(r'load|preload|bundle|subpackage|scene|resource|asset', re.I)


def walk_sources(project):
    root = project / 'assets' if (project / 'assets').is_dir() else project
    for f in root.rglob('*'):
        if f.is_file() and f.suffix in {'.ts', '.js'} and not (set(f.relative_to(project).parts) & SKIP):
            yield f


def scan_source(project):
    hits, game_runs = [], []
    for f in walk_sources(project):
        rel = f.relative_to(project).as_posix()
        try:
            lines = f.read_text(encoding='utf-8', errors='replace').splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            code = line.split('//')[0]
            for rid, pat, why in RULES:
                if pat.search(code):
                    if rid == 'fixed_deadline':
                        window = ' '.join(lines[max(0, i - 6):i + 3])
                        if not LOAD_WORDS.search(window):
                            continue
                    hits.append({'id': '%s:%d' % (rel, i), 'rule': rid, 'line': code.strip()[:160], 'why': why})
            if re.search(r'\b(cc\.)?game\.run\s*\(', code):
                game_runs.append('%s:%d' % (rel, i))
    if len(game_runs) > 1:
        for g in game_runs:
            hits.append({'id': g, 'rule': 'game_run_twice', 'line': 'game.run(...)',
                         'why': 'engine init must run once; a Retry while init is in flight must not call game.run again'})
    return hits


def native_sizes(native, startup_subs):
    gj = native / 'game.json'
    subs = []
    if gj.is_file():
        try:
            data = json.loads(gj.read_text(encoding='utf-8'))
            for s in data.get('subpackages', data.get('subPackages', [])) or []:
                root = s.get('root') or s.get('name')
                if root:
                    subs.append((s.get('name') or root, root.strip('/')))
        except ValueError:
            pass
    sizes = {name: 0 for name, _ in subs}
    audio_in = {name: 0 for name, _ in subs}
    main, main_audio = 0, 0
    for f in native.rglob('*'):
        if not f.is_file():
            continue
        rel = f.relative_to(native).as_posix()
        owner = next((name for name, root in subs if rel == root or rel.startswith(root + '/')), None)
        n = f.stat().st_size
        if owner is None:
            main += n
            main_audio += n if f.suffix.lower() in AUDIO else 0
        else:
            sizes[owner] += n
            audio_in[owner] += n if f.suffix.lower() in AUDIO else 0
    startup = main + sum(sizes.get(s, 0) for s in startup_subs)
    startup_audio = main_audio + sum(audio_in.get(s, 0) for s in startup_subs)
    return {'main_bytes': main, 'subpackages': sizes, 'startup_subpackages': startup_subs,
            'startup_bytes': startup, 'startup_audio_bytes': startup_audio,
            'unknown_startup_subpackages': [s for s in startup_subs if s not in sizes]}



def validate_runtime_report(report, binding):
    """Final LOAD gate rejects source-only/legacy attestations and replays the real chain."""
    import audit_native_startup_renderer as renderer
    try:
        if report.get('policy_version') != 2 or report.get('runtime_required') is not True:
            return ['Final startup report requires real Native renderer policy v2']
        ref = report['startup_renderer_report']; path = Path(ref['path'])
        if not path.is_file() or renderer.sha(path) != ref['sha256']:
            return ['Real Native startup report missing or changed']
        proof = json.loads(path.read_text()); native = Path(report['native']); project = Path(report['project'])
        return renderer.validate(proof,native,binding,project) + renderer.execute_registered(proof,native,binding,project)
    except (KeyError,ValueError,TypeError,OSError) as e:
        return ['Real Native startup report invalid: '+str(e)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--native', type=Path)
    ap.add_argument('--startup-subpackages', default='', help='comma list of subpackages loaded before HOME')
    ap.add_argument('--max-startup-mb', type=float, default=10.0)
    ap.add_argument('--source-only', action='store_true', help='preflight use: skip the build size part')
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--renderer-report', type=Path, help='actual real-Native renderer report, required for final Native startup checks')
    ap.add_argument('--runtime-only', action='store_true', help='finished-product startup maintenance: require and replay actual Native runtime; upload writer separately enforces file/size rules')
    a = ap.parse_args()
    if a.runtime_only:
        try:
            if not (a.native and a.binding and a.renderer_report):
                raise ValueError('runtime-only requires final Native, binding and renderer report')
            import audit_native_startup_renderer as renderer
            binding = json.loads(a.binding.read_text(encoding='utf-8'))['binding']
            report = {'tool':'audit_startup_contract','policy_version':2,'runtime_required':True,
                      'scope':'finished-product Native startup runtime; file/size checks remain in the upload writer',
                      'project':str(a.project.resolve()),'native':str(a.native.resolve()),'binding':binding,
                      'startup_renderer_report':{'path':str(a.renderer_report.resolve()),'sha256':renderer.sha(a.renderer_report)}}
            errors = validate_runtime_report(report,binding)
            report.update(checked=1,failed=len(errors),passed=not errors,errors=errors)
            if a.out:
                a.out.parent.mkdir(parents=True,exist_ok=True)
                with a.out.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
            print(json.dumps({'passed':not errors,'errors':errors},ensure_ascii=False))
            return int(bool(errors))
        except (KeyError,TypeError,ValueError,OSError) as error:
            print(json.dumps({'status':'refuse','error':str(error)},ensure_ascii=False));return 1
    try:
        if not a.project.is_dir():
            raise ValueError('project not found: ' + str(a.project))
        hits = scan_source(a.project)
        review_file = a.project / 'docs' / 'startup-contract-review.json'
        reviewed = json.loads(review_file.read_text(encoding='utf-8')) if review_file.is_file() else {}
        if not isinstance(reviewed, dict):
            raise ValueError('docs/startup-contract-review.json must map "file:line" to a reason')
        sizes = None
        if a.native:
            if not a.native.is_dir():
                raise ValueError('native build not found: ' + str(a.native))
            sizes = native_sizes(a.native, [s for s in a.startup_subpackages.split(',') if s])
        binding = None
        if a.binding:
            binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
            if not isinstance(binding, dict):
                raise ValueError('no binding object in ' + str(a.binding))
        if a.out and a.out.exists():
            raise ValueError('output exists: ' + str(a.out))
    except (OSError, ValueError) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2
    problems = []
    open_hits = [h for h in hits if not str(reviewed.get(h['id'], '')).strip()]
    for h in open_hits:
        problems.append('%s [%s] %s' % (h['id'], h['rule'], h['why']))
    if sizes:
        limit = int(a.max_startup_mb * 1024 * 1024)
        if sizes['unknown_startup_subpackages']:
            problems.append('startup subpackages not found in game.json: ' + ', '.join(sizes['unknown_startup_subpackages']))
        if sizes['startup_bytes'] > limit:
            problems.append('startup download %.1f MB > %.1f MB: move later art (other maps, skins, shop, sound panel) and audio to bundles loaded after HOME'
                            % (sizes['startup_bytes'] / 1048576, a.max_startup_mb))
        if sizes['startup_audio_bytes'] > 0:
            problems.append('audio (%.1f MB) is in the startup download; put sound in its own bundle so a sound failure never blocks HOME/PLAY'
                            % (sizes['startup_audio_bytes'] / 1048576))
    elif a.native is None and not a.source_only:
        problems.append('no --native build given: startup size not measured')
    runtime_ref=a.renderer_report or a.project/'docs/native-startup-renderer.json'
    runtime_required=bool(a.native) and not a.source_only
    if runtime_required:
        if runtime_ref.is_file():
            import audit_native_startup_renderer as renderer
            runtime_errors=validate_runtime_report({'policy_version':2,'runtime_required':True,'startup_renderer_report':{'path':str(runtime_ref.resolve()),'sha256':renderer.sha(runtime_ref)},'native':str(a.native.resolve()),'project':str(a.project.resolve())},binding)
            problems.extend(runtime_errors)
        else:problems.append('Final Native startup check requires --renderer-report with executable real entry/adapter/renderer/scene proof')
    report = {'tool': 'audit_startup_contract', 'checked': 1 + (1 if sizes else 0), 'failed': len(problems),
              'passed': not problems, 'source_hits': hits, 'open_hits': len(open_hits), 'sizes': sizes,
              'checks': [{'name': 'source patterns reviewed', 'passed': not open_hits},
                         {'name': 'startup size and audio', 'passed': bool(sizes) and not [p for p in problems if 'startup' in p or 'audio' in p]}],
              'note': 'Static check only. The browser fault runs of audit_startup_loading.py prove the game really gets in.'}
    report.update(policy_version=2,runtime_required=runtime_required,project=str(a.project.resolve()),native=str(a.native.resolve()) if a.native else None)
    if runtime_ref.is_file():
        import audit_native_startup_renderer as renderer
        report['startup_renderer_report']={'path':str(runtime_ref.resolve()),'sha256':renderer.sha(runtime_ref)}
    if binding is not None:
        report['binding'] = binding
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'failed': len(problems), 'problems': problems[:10],
                      'startup_mb': round(sizes['startup_bytes'] / 1048576, 2) if sizes else None}, ensure_ascii=False))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
