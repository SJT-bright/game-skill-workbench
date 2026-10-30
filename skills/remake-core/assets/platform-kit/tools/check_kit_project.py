#!/usr/bin/env python3
"""TikTok Platform Kit 2.0 - project check (read only).

Usage:  python3 check_kit_project.py --project /path/to/CocosProject [--out report.json]

Checks a Cocos Creator 2.4.15 project made from the kit:
  1. engine is 2.4.15
  2. kit files are present ONCE and byte-identical to KIT_MANIFEST.json (PlatformConfig.js is the
     only editable file; its gameId must be changed; kit 2.0: it keeps growthReward() = 5B and
     normalLevelCoins is set). A file equal to an older kit version is named as such.
  3. build-templates/bytedance has the kit main.js + touch-coordinates.js + storage-guard.js (kit 2.0,
     manifest project_path), and no game.js/game.json override (the editor's own game.js keeps the
     right engine file names); any other file there is a warning (tiktok_finalize moves it away)
  4. assets/resources is a ByteDance subpackage (keeps the main package small)
  5. no .webp images (WebP decode was misdetected on phones once)
  6. settings/bytedance.json exists (copy the kit template): numeric appid (not empty/testappId) equal to
     PlatformConfig.js appId, startSceneAssetBundle false, REMOTE_SERVER_ROOT empty
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
APPID = re.compile(r'[1-9][0-9]{9,24}')
DIRECT_SDK = re.compile(r'createRewardedVideoAd|addShortcut|checkShortcut|startEntranceMission|getShortcutMissionReward|'
                        r'getEntranceMissionReward')
GROWTH_FIXED = 'config.GROWTH_REWARD_B = 5;'
GROWTH_FN = 'config.growthReward = function'
LEVEL_COINS = re.compile(r'normalLevelCoins\s*:\s*([0-9]+)\s*[,}\n]')


def project_path(name, info):
    """Where a manifest file sits in a game project (kit 2.0: parts/storage-guard.js -> build-templates/bytedance/)."""
    return info.get('project_path') or name


def older(info, digest):
    return digest in set(info.get('previous_sha256') or [])


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
        if not project_path(name, info).startswith('assets/') or info.get('reference'):
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
            if GROWTH_FN not in text or GROWTH_FIXED not in text:
                errors.append('PlatformConfig.js: growthReward() / GROWTH_REWARD_B = 5 missing or changed (kit 2.0: '
                              'add-to-home and revisit pay 5B each, no per-game amount); copy the kit 2.0 file and '
                              're-enter gameId / placementMap / normalLevelCoins')
            m = LEVEL_COINS.search(text)
            if not m or int(m.group(1)) <= 0:
                errors.append('PlatformConfig.js: set normalLevelCoins to B (unlock_table.json normal_level_coins); '
                              'until then growthReward() throws and the two home entries pay nothing')
        else:
            digest = sha(found[0])
            if digest == info['sha256']:
                continue
            if older(info, digest):
                errors.append('%s is an older kit version (%s): copy the kit %s file unchanged'
                              % (base, digest[:8], manifest['version']))
            else:
                errors.append('%s was changed: kit files must be copied unchanged (fix the kit, not the game)' % base)

    bt = proj / 'build-templates' / 'bytedance'
    wanted = set()
    for name, info in manifest['files'].items():
        rel = project_path(name, info)
        if not rel.startswith('build-templates/') or info.get('reference'):
            continue
        wanted.add(rel)
        target = proj / rel
        if not target.is_file():
            errors.append('missing %s (copy it from platform-kit/%s)' % (rel, name))
        elif sha(target) != info['sha256']:
            if older(info, sha(target)):
                errors.append('%s is an older kit version (%s): copy the kit %s file unchanged'
                              % (rel, sha(target)[:8], manifest['version']))
            else:
                errors.append('%s was changed: copy the kit version unchanged' % rel)
    for extra in ('game.js', 'game.json'):
        if (bt / extra).is_file():
            errors.append('build-templates/bytedance/%s overrides the editor template: delete it' % extra)
    if bt.is_dir():
        others = sorted(p.relative_to(proj).as_posix() for p in bt.rglob('*')
                        if p.is_file() and not p.name.startswith('.') and not p.name.endswith('.meta')
                        and p.relative_to(proj).as_posix() not in wanted and p.name not in ('game.js', 'game.json'))
        if others:
            warnings.append('build-templates/bytedance has non-kit files (tiktok_finalize source moves them to '
                            '.tiktok-kit/removed/): %s' % ', '.join(others[:8]))

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
        try:
            s = json.loads(bd.read_text(encoding='utf-8-sig'))
        except ValueError:
            s = None
        if not isinstance(s, dict):
            errors.append('settings/bytedance.json is not a JSON object: copy platform-kit/settings/bytedance.json')
            s = {}
        appid = str(s.get('appid') if s.get('appid') is not None else '').strip()
        if not APPID.fullmatch(appid):
            errors.append('settings/bytedance.json: appid %r is not a numeric App ID (empty/testappId/text '
                          'builds a testappId package); copy platform-kit/settings/bytedance.json' % appid)
        else:
            cfg = [f for f in files if f.name == 'PlatformConfig.js']
            m = re.search(r"appId\s*:\s*['\"]([^'\"]*)['\"]", cfg[0].read_text(encoding='utf-8')) if cfg else None
            if m and m.group(1).strip() != appid:
                errors.append('settings/bytedance.json: appid %s differs from PlatformConfig.js appId %s: '
                              'use one App ID' % (appid, m.group(1).strip()))
        if s.get('startSceneAssetBundle'):
            errors.append('settings/bytedance.json: turn off "Start Scene Asset Bundle"')
        if (s.get('REMOTE_SERVER_ROOT') or '').strip():
            errors.append('settings/bytedance.json: REMOTE_SERVER_ROOT must be empty (no remote downloads)')
    else:
        errors.append('settings/bytedance.json missing: copy platform-kit/settings/bytedance.json (numeric appid); '
                      'without it the command-line build ships testappId')

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
