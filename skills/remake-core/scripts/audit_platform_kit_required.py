#!/usr/bin/env python3
"""Platform kit required whenever the game is built with the local Cocos Creator 2.4.15 (v7.5, Germ2048 item 4). Read-only.

The old rule "platform kit only when the original project is 2.4.15" let Germ2048 (project.json 2.4.0, built with the
only local Creator, 2.4.15) ship without build-templates/bytedance, without the touch fix and with its own ad wrapper.
The decision now follows the Creator version that actually builds the game:
  --creator-version, else $COCOS_CREATOR / the Creator installs under /Applications/Cocos/Creator/, else 2.4.15.
When a 2.x project is built with 2.4.15:
  1. build-templates/bytedance/ holds the kit main.js and touch-coordinates.js, byte-identical to KIT_MANIFEST.json;
  2. remake-core/assets/platform-kit/tools/check_kit_project.py passes. Its "engine 2.4.x" line is not an error when
     the build uses 2.4.15 (the editor upgrades project.json on the first 2.4.15 build); everything else is;
  3. a game-owned TikTok ad wrapper (createRewardedVideoAd outside the kit RewardedService.js) is a WARNING in v7.5
     (parent decision A1): the hard gate on ad behaviour is the mandatory 10-case package-check ad_regression.py, which
     needs qa/ad-regression.json. The kit check's "missing RewardedService.js" / "RewardedService.js was changed" lines
     are reported as warnings for the same reason; every other kit line stays a refusal.
v7.7 (parent decision 2026-10-29, option (a) of W-D2 REQUESTS item 1): an ENGLISH project - .tiktok-kit/policy.json
with board localize, or a docs/english/ folder - keeps its own build-templates (design D77 section 4 item 3: touch,
storage layer and startup part are installed at the native stage and proven by kit_parts K1-K4). For it rule 1 is
replaced by a fresh source-stage record: tiktok_finalize.check_source_record (the writers' K5) must be empty, and the
kit check's build-templates lines are not problems. Remake projects keep rule 1 unchanged.
Exit 0 pass / not applicable, 1 needs fix, 2 bad input.

  python3 audit_platform_kit_required.py --project <cocos project> [--creator-version 2.4.15] [--out report.json]
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
KIT = HERE.parent / 'assets' / 'platform-kit'
CHECK = KIT / 'tools' / 'check_kit_project.py'
SKIP = {'library', 'temp', 'build', 'local', 'node_modules', '.git', 'packages', 'profiles'}
AD_CALL = re.compile(r'createRewardedVideoAd')
INSTALL_ROOT = Path('/Applications/Cocos/Creator')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def creator_version(explicit=None):
    if explicit:
        return explicit, 'argument'
    env = os.environ.get('COCOS_CREATOR', '')
    m = re.search(r'(\d+\.\d+\.\d+)', env)
    if m:
        return m.group(1), '$COCOS_CREATOR'
    try:
        found = sorted(p.name for p in INSTALL_ROOT.iterdir() if re.fullmatch(r'2\.\d+\.\d+', p.name))
    except OSError:
        found = []
    if '2.4.15' in found:
        return '2.4.15', str(INSTALL_ROOT)   # the TikTok build Creator; other 2.x installs are not used for bytedance builds
    if found:
        return max(found, key=lambda v: tuple(int(x) for x in v.split('.'))), str(INSTALL_ROOT)
    return '2.4.15', 'default (the only 2.x Creator used for TikTok builds)'


def project_version(project):
    try:
        return str(json.loads((project / 'project.json').read_text(encoding='utf-8-sig')).get('version') or '')
    except (OSError, ValueError):
        return ''


def english_project(project):
    """-> reason string when this is an English (localize) project, else None."""
    marker = project / '.tiktok-kit' / 'policy.json'
    try:
        data = json.loads(marker.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        data = None
    if isinstance(data, dict) and data.get('board') == 'localize':
        return '.tiktok-kit/policy.json board localize'
    if (project / 'docs' / 'english').is_dir():
        return 'docs/english/ present'
    return None


def source_record_problems(project):
    """The writers' K5 check (tiktok_finalize.check_source_record) as problem strings."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import tiktok_finalize as F
    return ['%s: %s' % (f['id'], f['message']) for f in F.check_source_record(project)]


def own_ad_wrappers(project, kit_names):
    out = []
    for p in sorted((project / 'assets').rglob('*')):
        if not p.is_file() or p.suffix not in ('.js', '.ts') or p.name.endswith('.d.ts') or p.name in kit_names:
            continue
        if SKIP & set(p.relative_to(project).parts):
            continue
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        if AD_CALL.search(text):
            out.append(p.relative_to(project).as_posix())
    return out


def audit(project, explicit_version=None, kit=None):
    kit = Path(kit).resolve() if kit else KIT
    project = Path(project).resolve()
    if not (project / 'assets').is_dir():
        raise ValueError('not a Cocos project (no assets folder): %s' % project)
    pv = project_version(project)
    bv, source = creator_version(explicit_version)
    report = {'tool': 'audit_platform_kit_required', 'schema': 1, 'project': str(project), 'project_version': pv,
              'build_creator_version': bv, 'build_version_source': source, 'problems': [], 'warnings': [], 'notes': [],
              'check_kit_project': None}
    if not pv.startswith('2.') or bv != '2.4.15':
        report.update(status='not_applicable', passed=True)
        report['notes'].append('kit applies to 2.x projects built with Creator 2.4.15 (project %s, build %s)' % (pv or '?', bv))
        return report
    manifest = json.loads((kit / 'KIT_MANIFEST.json').read_text(encoding='utf-8'))
    english = english_project(project)
    report['english_project'] = english
    if english:
        problems = source_record_problems(project)
        report['source_record'] = 'fresh' if not problems else 'missing or stale'
        report['problems'].extend(problems)
        report['notes'].append('English project (%s): build-templates/bytedance is not required; touch, storage and '
                               'startup are installed at the native stage (kit_parts K1-K4), so a fresh '
                               'tiktok_finalize source record is required instead' % english)
    for name, info in manifest['files'].items():
        if english:
            break
        if name.startswith('build-templates/'):
            target = project / name
            if not target.is_file():
                report['problems'].append('missing %s (copy the platform kit file unchanged)' % name)
            elif sha(target) != info['sha256']:
                report['problems'].append('%s differs from KIT_MANIFEST.json (copy the kit version unchanged)' % name)
    kit_names = {Path(n).name for n in manifest['files']}
    wrappers = own_ad_wrappers(project, kit_names)
    adapter = project / 'qa' / 'ad-regression.json'
    report['own_ad_wrappers'] = wrappers
    report['ad_regression_adapter'] = adapter.relative_to(project).as_posix() if adapter.is_file() else None
    r = subprocess.run([sys.executable, '-B', str(kit / 'tools' / 'check_kit_project.py'), '--project', str(project)], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=120)
    try:
        kit = json.loads(r.stdout[r.stdout.find('{'):])
    except ValueError:
        kit = {'passed': False, 'errors': ['check_kit_project.py output unreadable: ' + (r.stdout + r.stderr)[-300:]], 'warnings': []}
    report['check_kit_project'] = {'exit': r.returncode, 'passed': kit.get('passed'), 'errors': kit.get('errors', []),
                                   'warnings': kit.get('warnings', [])}
    for e in kit.get('errors', []):
        if re.match(r'engine 2\.\d+\.\d+, kit needs Cocos Creator 2\.4\.15', e):
            report['notes'].append(e + ' -> accepted: the build uses Creator 2.4.15, which upgrades project.json')
            continue
        if e.startswith(('missing kit file RewardedService.js', 'RewardedService.js was changed')):
            # v7.5 A1: rewarded-ad code that is not the kit's is a warning; ad_regression.py is the hard gate.
            report['warnings'].append('check_kit_project: ' + e + ' (warning in v7.5: the 10-case ad regression decides)')
            continue
        if e.startswith('missing build-templates/') or 'build-templates/bytedance/main.js was changed' in e or \
                'build-templates/bytedance/touch-coordinates.js was changed' in e:
            continue   # already reported above with the kit wording
        if english and 'build-templates/' in e:
            report['notes'].append('check_kit_project: ' + e + ' -> not required for an English project')
            continue
        report['problems'].append('check_kit_project: ' + e)
    if wrappers:
        report['warnings'].append('game-owned TikTok ad wrapper (%s): replace it with the kit RewardedService.js, or keep it and pass '
                                  'the mandatory 10-case ad regression (package-check ad_regression.py)%s' %
                                  (', '.join(wrappers), '' if adapter.is_file() else '; qa/ad-regression.json is still missing'))
    report['passed'] = not report['problems']
    report['status'] = 'pass' if report['passed'] else 'needs_fix'
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--creator-version', help='Creator version that will build the game (default: detected, else 2.4.15)')
    ap.add_argument('--kit-dir', type=Path, help='platform-kit folder (default: the one in this Skill); tests only')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        r = audit(a.project, a.creator_version, a.kit_dir)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False)); return 2
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: r.get(k) for k in ('status', 'project_version', 'build_creator_version', 'problems', 'warnings', 'notes',
                                            'own_ad_wrappers')}, ensure_ascii=False))
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
