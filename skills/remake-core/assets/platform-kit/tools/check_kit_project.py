#!/usr/bin/env python3
"""TikTok Platform Kit v1 - project check (read only).

Usage:  python3 check_kit_project.py --project /path/to/CocosProject [--out report.json]

Checks a Cocos Creator 2.4.15 project made from the kit:
  1. engine is 2.4.15
  2. kit files are present ONCE and byte-identical to KIT_MANIFEST.json (PlatformConfig.js is the
     only editable file; its gameId must be changed)
  3. build-templates/bytedance has the kit main.js + touch-coordinates.js, and no game.js/game.json
     override (the editor's own game.js keeps the right engine file names)
  4. assets/resources is a ByteDance subpackage (keeps the main package small)
  5. no .webp images (WebP decode was misdetected on phones once)
  6. settings/bytedance.json: startSceneAssetBundle false, REMOTE_SERVER_ROOT empty
  7. warning when game code calls the ad / mission SDK directly instead of the kit services
Exit code 0 = pass, 1 = fail, 2 = bad input. Passing does NOT prove a phone scan; see README.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
SKIP = {'library', 'temp', 'build', 'local', 'node_modules', '.git', 'packages', 'profiles'}
DIRECT_SDK = re.compile(r'createRewardedVideoAd|addShortcut|startEntranceMission|getShortcutMissionReward|getEntranceMissionReward')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def walk(root):
    for p in root.rglob('*'):
        if any(part in SKIP for part in p.relative_to(root).parts):
            continue
        if p.is_file():
            yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', required=True, type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    proj = a.project.resolve()
    manifest = json.loads((KIT / 'KIT_MANIFEST.json').read_text(encoding='utf-8'))
    if not (proj / 'project.json').is_file() or not (proj / 'assets').is_dir():
        print('not a Cocos Creator 2.x project: project.json + assets/ expected'); return 2
    errors, warnings = [], []

    version = json.loads((proj / 'project.json').read_text(encoding='utf-8-sig')).get('version')
    if version != manifest['engine']:
        errors.append('engine %s, kit needs Cocos Creator %s' % (version, manifest['engine']))

    files = list(walk(proj / 'assets'))
    for name, info in manifest['files'].items():
        if not name.startswith('assets/'):
            continue
        base = Path(name).name
        found = [f for f in files if f.name == base]
        if not found:
            errors.append('missing kit file %s (copy assets/tiktok-platform/ into assets/)' % base)
            continue
        if len(found) > 1:
            errors.append('%s exists %d times: keep one copy' % (base, len(found)))
        if info.get('editable'):
            text = found[0].read_text(encoding='utf-8')
            if "gameId: 'change-me'" in text:
                errors.append('PlatformConfig.js: set gameId for this game')
        elif sha(found[0]) != info['sha256']:
            errors.append('%s was changed: kit files must be copied unchanged (fix the kit, not the game)' % base)

    bt = proj / 'build-templates' / 'bytedance'
    for name, info in manifest['files'].items():
        if not name.startswith('build-templates/'):
            continue
        target = proj / name
        if not target.is_file():
            errors.append('missing %s' % name)
        elif sha(target) != info['sha256']:
            errors.append('%s was changed: copy the kit version unchanged' % name)
    for extra in ('game.js', 'game.json'):
        if (bt / extra).is_file():
            errors.append('build-templates/bytedance/%s overrides the editor template: delete it' % extra)

    meta = proj / 'assets' / 'resources.meta'
    if not meta.is_file():
        errors.append('assets/resources folder (Asset Bundle) missing')
    else:
        m = json.loads(meta.read_text(encoding='utf-8-sig'))
        if not m.get('isBundle') or (m.get('compressionType') or {}).get('bytedance') != 'subpackage':
            errors.append('assets/resources: Asset Bundle with ByteDance compression type "Mini Game Subpackage" required')

    webp = [str(f.relative_to(proj)) for f in files if f.suffix.lower() == '.webp']
    if webp:
        errors.append('.webp images found (%d), use PNG/JPG: %s' % (len(webp), ', '.join(webp[:5])))

    bd = proj / 'settings' / 'bytedance.json'
    if bd.is_file():
        s = json.loads(bd.read_text(encoding='utf-8-sig'))
        if s.get('startSceneAssetBundle'):
            errors.append('settings/bytedance.json: turn off "Start Scene Asset Bundle"')
        if (s.get('REMOTE_SERVER_ROOT') or '').strip():
            errors.append('settings/bytedance.json: REMOTE_SERVER_ROOT must be empty (no remote downloads)')
    else:
        warnings.append('settings/bytedance.json not found yet: build once for ByteDance, then re-run')

    kit_names = {Path(n).name for n in manifest['files']}
    for f in files:
        if f.suffix in ('.js', '.ts') and f.name not in kit_names and not f.name.endswith('.d.ts'):
            try:
                if DIRECT_SDK.search(f.read_text(encoding='utf-8', errors='ignore')):
                    warnings.append('%s calls the TikTok ad/mission SDK directly: use RewardedService / MissionFlow' % f.relative_to(proj))
            except OSError:
                pass

    report = {'kit': manifest['name'], 'kit_version': manifest['version'], 'project': str(proj),
              'passed': not errors, 'errors': errors, 'warnings': warnings,
              'scope': 'static project check only; not a Native build, device scan, real ad or upload result'}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if a.out:
        a.out.write_text(text, encoding='utf-8')
    print(text)
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
