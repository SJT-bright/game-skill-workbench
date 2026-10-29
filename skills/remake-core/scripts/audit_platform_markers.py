#!/usr/bin/env python3
"""Read-only IAA/revisit marker presence audit, never SDK behavior acceptance.

No sharing (user 2026-10-23, above all for 英化): sharing cannot be used, so the game's own source must not call any
share API (shareAppMessage, onShareAppMessage, showShareMenu, updateShareMenu, onShareTimeline, shareMessageToFriend,
navigator.share ...). An original game's share button, popup, reward and call are removed. hideShareMenu (turning
the platform menu's share off) is allowed. Share calls found in the game's source fail this audit (exit 2); hits in
the Native ZIP (engine adapters) are listed for review only.

The same goes for the other "do more, break more" features the user removed on 2026-10-23 (both boards): more games /
cross-promotion (navigateToMiniProgram, showMoreGamesModal, createMoreGamesButton ...) and ranking / leaderboards
(setUserCloudStorage, getFriendCloudStorage, setImRankData ...). They are listed with the share calls.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import zipfile

from verify_native_zip import verify
from feature_policy import enabled


GROUPS = {
    'iaa': ('TTMinis', 'createRewardedVideoAd', 'onClose', 'isEnded'),
    'growth': ('TTMinis', 'canIUse', 'addShortcut', 'getShortcutMissionReward',
               'startEntranceMission', 'getEntranceMissionReward', 'canReceiveReward'),
}
SHARE_CALLS = ('shareAppMessage', 'onShareAppMessage', 'offShareAppMessage', 'showShareMenu', 'updateShareMenu',
               'onShareTimeline', 'shareMessageToFriend', 'shareToFriend', 'navigator.share', 'shareVideo',
               'showShareImageMenu', 'authPrivateMessage')
EXCLUDED = {'library', 'temp', 'build', 'dist', 'profiles', 'node_modules',
            '.git', '__pycache__'}
SUFFIXES = {'.ts', '.js', '.mjs', '.cjs'}


def scan(entries, markers):
    hits = {marker: [] for marker in markers}
    patterns = {marker: re.compile(r'(?<![\w$])' + re.escape(marker) + r'(?![\w$])')
                for marker in markers}
    count = 0
    for name, data in entries:
        count += 1
        content = data.decode('utf-8-sig')
        for marker, pattern in patterns.items():
            if pattern.search(content):
                hits[marker].append(name)
    return {'scanned_files': count, 'hits': hits,
            'missing': [marker for marker, paths in hits.items() if not paths]}


def source_entries(project):
    if not project.is_dir():
        raise ValueError('Source project is not a directory')
    for path in sorted(project.rglob('*')):
        relative = path.relative_to(project)
        if any(part in EXCLUDED for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError('Source symlink requires separate review: ' + str(relative))
        if path.is_file() and path.suffix in SUFFIXES and not path.name.endswith('.d.ts'):
            yield relative.as_posix(), path.read_bytes()


CROSS_CALLS = ('navigateToMiniProgram', 'navigateToMiniGame', 'showMoreGamesModal', 'createMoreGamesButton', 'createGameClubButton')
RANK_CALLS = ('setUserCloudStorage', 'getFriendCloudStorage', 'getGroupCloudStorage', 'setImRankData', 'getImRankList', 'openDataContext')


def share_hits(entries, extra=()):
    pattern = re.compile(r'(?<![\w$])(' + '|'.join(re.escape(c) for c in SHARE_CALLS + tuple(extra)) + r')(?![\w$])')
    hits = {}
    for name, data in entries:
        for m in pattern.finditer(data.decode('utf-8-sig', errors='replace')):
            hits.setdefault(m.group(1), [])
            if name not in hits[m.group(1)]:
                hits[m.group(1)].append(name)
    return hits


def audit(project, native_zip=None, features=('iaa', 'growth')):
    markers = list(dict.fromkeys(marker for feature in features for marker in GROUPS[feature]))
    result = {'source_project': str(project.resolve()), 'features': list(features),
              'source': scan(source_entries(project), markers), 'native_zip': None,
              'share_calls_in_source': share_hits(source_entries(project), CROSS_CALLS + (() if enabled(project)['league'] else RANK_CALLS)),
              'method': 'text_markers_including_strings_comments_and_unused_code',
              'not_verified': ['reachable SDK calls or TTMinis.game context',
                               'compatibility, strict result or lifecycle behavior',
                               'inventory persistence and actual reward consumption',
                               'configuration ownership, real phone/IAA or upload/release']}
    if native_zip is not None:
        structure = verify(native_zip)
        with zipfile.ZipFile(native_zip) as archive:
            entries = ((name, archive.read(name)) for name in sorted(archive.namelist())
                       if Path(name).suffix in {'.js', '.mjs', '.cjs'})
            result['native_zip'] = {
                'archive': str(native_zip.resolve()), 'sha256': structure['sha256'],
                **scan(entries, markers),
            }
            result['native_zip']['share_calls_for_review'] = share_hits(
                (name, archive.read(name)) for name in sorted(archive.namelist()) if Path(name).suffix in {'.js', '.mjs', '.cjs'})
    missing = bool(result['source']['missing']) or bool(
        result['native_zip'] and result['native_zip']['missing'])
    from audit_no_social_features import audit as audit_no_social
    result['no_social_features'] = audit_no_social(project)
    result['status'] = ('share_feature_present_remove_it' if result['share_calls_in_source'] or not result['no_social_features']['passed']
                        else 'required_markers_missing_requires_review' if missing
                        else 'markers_present_requires_behavior_review')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--native-zip', type=Path)
    parser.add_argument('--features', nargs='+', choices=tuple(GROUPS),
                        default=['iaa', 'growth'])
    parser.add_argument('--report', type=Path, help='New report; existing files are preserved')
    args = parser.parse_args()
    try:
        if args.report and args.report.exists():
            raise ValueError('Report already exists; choose a new path')
        result = audit(args.project, args.native_zip, tuple(dict.fromkeys(args.features)))
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                                   encoding='utf-8')
        print(json.dumps({
            'status': result['status'], 'features': result['features'],
            'source_files': result['source']['scanned_files'],
            'source_missing': result['source']['missing'],
            'native_files': result['native_zip']['scanned_files'] if result['native_zip'] else None,
            'native_missing': result['native_zip']['missing'] if result['native_zip'] else None,
            'share_calls_in_source': result['share_calls_in_source'],
            'not_verified': result['not_verified'],
        }, ensure_ascii=False, indent=2))
        return 2 if result['status'].startswith(('required_markers_missing', 'share_feature')) else 0
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError) as error:
        print('Platform marker audit failed: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
