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


def coin_reward_rule(proj):
    """R4N1 (补查2 第 5 组, SLS07): feature_policy.applies('writer_coin_reward', board, project). English game without a
    coin wallet and without remake-board records -> 'not_applicable'; everything else (and a kit used outside the
    Skill, where feature_policy is not found) -> 'block' as before."""
    scripts = KIT.parent.parent / 'scripts'
    if not (scripts / 'feature_policy.py').is_file():
        return 'block', 'feature_policy.py not found next to the kit'
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import feature_policy
        board = feature_policy.board_of(proj)[0]
        return feature_policy.rule_verdict('writer_coin_reward', board, proj)
    except Exception as exc:  # noqa: BLE001 - a policy error must not soften the gate
        return 'block', 'feature_policy error: %s' % exc


# R4O3 (补查2 第 5 组, SLS07; Saul 2026-11-04 ECON-SHORTCUT / ECON-REVISIT): game code that uses the kit's
# HomeGrowthEntries in a game without coins must pass init(store, {reward, rewardText}) (the no-coin replacement);
# without it the two home entries pay nothing. Only read when normalLevelCoins 0 was allowed above.
ENTRIES_USE = re.compile(r'''getComponent\(\s*['"]?HomeGrowthEntries['"]?\s*\)|addComponent\(\s*['"]?HomeGrowthEntries'''
                         r'''['"]?\s*\)|require\(\s*['"][^'"]*HomeGrowthEntries['"]\s*\)|\bHomeGrowthEntries\.Controller\b''')
REWARD_OPTION = re.compile(r'\breward\s*:')


def no_coin_entry_findings(proj, files, kit_names):
    """[(level, message)]: K_home_entries_no_reward. Block when the project recorded that it has no coins
    (docs/economy/economy_capabilities.json wallet false: a game made with the 11-04 no-coin rules); warn otherwise
    (English games already in progress before R4O3)."""
    users, wired = [], []
    for f in files:
        if f.suffix not in ('.js', '.ts') or f.name in kit_names or f.name.endswith('.d.ts'):
            continue
        try:
            text = f.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        if ENTRIES_USE.search(text):
            (wired if REWARD_OPTION.search(text) else users).append(f.relative_to(proj).as_posix())
    if not users or wired:
        return []
    recorded = False
    cap = proj / 'docs' / 'economy' / 'economy_capabilities.json'
    try:
        recorded = json.loads(cap.read_text(encoding='utf-8-sig')).get('wallet') is False
    except (OSError, ValueError, AttributeError):
        recorded = False
    level = 'block' if recorded else 'warn'
    return [(level, 'K_home_entries_no_reward%s: %s use HomeGrowthEntries in a game without coins but pass no reward '
                    'option, so add-to-home / revisit pay nothing. Call init(store, {reward: function (kind, draft) '
                    '{...}, rewardText: ...}) with the replacement of economy_capabilities no_wallet_substitutes '
                    '(energy +3 each; no energy: add a coin and skins first, then 5B)%s'
             % ('' if level == 'block' else ' (warning)', ', '.join(users[:5]),
                '' if recorded else '; warning only: the project has no economy_capabilities.json wallet false record'))]


# R4Q5 (补查3 第 5 组, 奔跑吧巨人): PlatformConfig ids must be this game's own. Allowed: the shared TikTok test app
# in the kit template (Saul 2026-10-29: games keep sharing App ID 7683427172773644296 and its three ad units) and the
# ids written in the project's own record docs/platform/platform_ids.json ({"appId", "clientKey", "adUnitIds",
# "source"}). A gameId, or an appId / clientKey / ad unit that is neither, and that another game on this machine
# (--peers) also carries, was copied from that game: error (a shared gameId only warns: copies of the same game
# share it). Not shared, not recorded, not seen elsewhere: warning.
ID_FIELDS = {'gameId': re.compile(r"gameId\s*:\s*'([^']*)'"), 'appId': re.compile(r"appId\s*:\s*'([^']*)'"),
             'clientKey': re.compile(r"clientKey\s*:\s*'([^']*)'")}
AD_UNIT = re.compile(r"\bad[0-9]{12,24}\b")
ID_RECORD = Path('docs') / 'platform' / 'platform_ids.json'


def config_ids(text):
    out = {k: (rx.search(text).group(1).strip() if rx.search(text) else '') for k, rx in ID_FIELDS.items()}
    out['adUnitIds'] = sorted(set(AD_UNIT.findall(text)))
    return out


def peer_configs(peers, proj):
    """-> [(project dir, ids)] for every PlatformConfig*.js under the --peers folders (3 levels deep), not proj."""
    out = []
    for base in peers or []:
        base = Path(base)
        for p in list(base.glob('assets/tiktok-platform/PlatformConfig*.js')) + \
                list(base.glob('*/assets/tiktok-platform/PlatformConfig*.js')) + \
                list(base.glob('*/*/assets/tiktok-platform/PlatformConfig*.js')) + \
                list(base.glob('*/*/*/assets/tiktok-platform/PlatformConfig*.js')):
            game = p.parents[2]
            # R4R4: a build output (build/web-mobile/src, library, temp) is this game's own copy, not another game
            if {'build', 'library', 'temp', 'node_modules'} & set(p.relative_to(base).parts[:-3]):
                continue
            try:
                if game.resolve() == proj.resolve():
                    continue
                out.append((game, config_ids(p.read_text(encoding='utf-8', errors='replace'))))
            except OSError:
                continue
    return out


def foreign_config_findings(proj, text, peers=None):
    errors, warnings = [], []
    ids = config_ids(text)
    try:
        tmpl = config_ids((KIT / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').read_text(encoding='utf-8'))
    except OSError:
        tmpl = {'appId': '', 'clientKey': '', 'adUnitIds': []}
    shared = {tmpl['appId'], tmpl['clientKey']} | set(tmpl['adUnitIds'])
    record = {}
    if (proj / ID_RECORD).is_file():
        try:
            record = json.loads((proj / ID_RECORD).read_text(encoding='utf-8-sig'))
        except ValueError:
            errors.append('%s is not valid JSON' % ID_RECORD.as_posix())
    own = {str(record.get('appId') or ''), str(record.get('clientKey') or '')} | \
        {str(x) for x in (record.get('adUnitIds') or []) if isinstance(x, str)}
    own.discard('')
    others = peer_configs(peers, proj)
    if ids['gameId'] and ids['gameId'] != 'change-me':
        same = [str(g) for g, o in others if o['gameId'] == ids['gameId']]
        if same:
            warnings.append('PlatformConfig.js gameId %r is also the gameId of %s: unless that is a copy of this same '
                            'game, the save key is shared; give this game its own gameId' % (ids['gameId'], ', '.join(same[:3])))
    values = [('appId', ids['appId']), ('clientKey', ids['clientKey'])] + [('ad unit', a) for a in ids['adUnitIds']]
    for what, v in values:
        if not v or v in shared or v in own:
            continue
        same = [str(g) for g, o in others if v in ({o['appId'], o['clientKey']} | set(o['adUnitIds']))]
        if same:
            errors.append('PlatformConfig.js %s %s comes from another game (%s), not from this project: use the '
                          'shared test app of the kit template, or write this game\'s own ids in %s'
                          % (what, v, ', '.join(same[:3]), ID_RECORD.as_posix()))
        else:
            warnings.append('PlatformConfig.js %s %s is neither the shared test app nor in %s: write where it comes '
                            'from (source) in that record' % (what, v, ID_RECORD.as_posix()))
    return errors, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', required=True, type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--peers', type=Path, action='append', default=[],
                    help='R4Q5: folder of other game projects; a gameId / app id / ad unit shared with one is an error')
    a = ap.parse_args()
    proj = a.project.resolve()
    manifest = json.loads((KIT / 'KIT_MANIFEST.json').read_text(encoding='utf-8'))
    if not (proj / 'project.json').is_file() or not (proj / 'assets').is_dir():
        print('not a Cocos Creator 2.x project: project.json + assets/ expected'); return 2
    errors, warnings = [], []
    no_coin_entries = False   # R4O3: set when normalLevelCoins 0 is allowed (English game without coins)

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
            fe, fw = foreign_config_findings(proj, text, a.peers)   # R4Q5
            errors += fe
            warnings += fw
            if GROWTH_FN not in text or GROWTH_FIXED not in text:
                errors.append('PlatformConfig.js: growthReward() / GROWTH_REWARD_B = 5 missing or changed (kit 2.0: '
                              'add-to-home and revisit pay 5B each, no per-game amount); copy the kit 2.0 file and '
                              're-enter gameId / placementMap / normalLevelCoins')
            m = LEVEL_COINS.search(text)
            if not m or int(m.group(1)) <= 0:
                rule, why = coin_reward_rule(proj)
                msg = ('PlatformConfig.js: set normalLevelCoins to B (unlock_table.json normal_level_coins); '
                       'until then growthReward() throws and the two home entries pay nothing')
                if rule == 'not_applicable':   # R4N1 (SLS07): an English game with no coins keeps normalLevelCoins 0
                    warnings.append('PlatformConfig.js normalLevelCoins 0 allowed: %s. Add-to-home / revisit must pay '
                                    'the no-coin replacement (MissionFlow reward option; economy_capabilities '
                                    'no_wallet_substitutes), never growthReward()' % why)
                    no_coin_entries = True
                else:
                    errors.append(msg)
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
    if no_coin_entries:
        for level, msg in no_coin_entry_findings(proj, files, kit_names):
            (errors if level == 'block' else warnings).append(msg)

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
