#!/usr/bin/env python3
"""Source-stage TikTok App ID check (v7.5, Germ2048 item 6). Read-only.

Cocos Creator 2.4.15 command-line builds take the ByteDance App ID from settings/bytedance.json ("appid"); the value in
settings/builder.json is ignored by the command line, and a missing file builds with "testappId". So at the source stage:
  - settings/bytedance.json must exist and its appid must be a numeric App ID (digits only), not empty, not testappId;
  - 7683427172773644296 is the shared test-group App ID used by many games: it is accepted and never flagged.
Cocos 3.x keeps the App ID in the build task, not in settings/: reported "not_applicable" (the native ZIP check covers it).
Exit 0 pass / not applicable, 1 needs fix, 2 bad input.

  python3 audit_source_appid.py --project <cocos project> [--out report.json]
"""
import argparse
import json
from pathlib import Path
import re
import sys

SHARED_TEST_GROUP = '7683427172773644296'
PLACEHOLDERS = {'', 'testappid', 'touristappid', 'your_appid', 'appid', 'change-me', 'tt0000000000000000'}


def audit(project):
    project = Path(project).resolve()
    if not (project / 'assets').is_dir():
        raise ValueError('not a Cocos project (no assets folder): %s' % project)
    version = ''
    try:
        version = str(json.loads((project / 'project.json').read_text(encoding='utf-8-sig')).get('version') or '')
    except (OSError, ValueError):
        pass
    if not version and (project / 'package.json').is_file():
        try:
            version = str((json.loads((project / 'package.json').read_text(encoding='utf-8-sig')).get('creator') or {}).get('version') or '')
        except (OSError, ValueError):
            pass
    report = {'tool': 'audit_source_appid', 'schema': 1, 'project': str(project), 'engine': version,
              'settings_file': 'settings/bytedance.json', 'appid': None, 'problems': [], 'notes': []}
    if version.startswith('3'):
        report.update(status='not_applicable', passed=True)
        report['notes'].append('Cocos 3.x: the App ID is set in the build task; verify_native_zip.py checks project.config.json')
        return report
    path = project / 'settings' / 'bytedance.json'
    builder = project / 'settings' / 'builder.json'
    if builder.is_file():
        try:
            b = json.loads(builder.read_text(encoding='utf-8-sig'))
            bid = ((b.get('bytedance') or {}) if isinstance(b, dict) else {}).get('appid')
            if bid:
                report['notes'].append('settings/builder.json has a bytedance appid (%s); the command-line build ignores it' % bid)
        except (OSError, ValueError, AttributeError):
            pass
    if not path.is_file():
        report['problems'].append('settings/bytedance.json is missing: the command-line build will write "testappId" into '
                                  'project.config.json. Copy the platform kit template and set "appid"')
    else:
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as exc:
            data = None
            report['problems'].append('settings/bytedance.json unreadable: %s' % exc)
        if isinstance(data, dict):
            appid = str(data.get('appid') if data.get('appid') is not None else '').strip()
            report['appid'] = appid
            if appid.lower() in PLACEHOLDERS:
                report['problems'].append('settings/bytedance.json appid is %r: set the real numeric App ID' % (appid or 'empty'))
            elif not re.fullmatch(r'\d{10,24}', appid):
                report['problems'].append('settings/bytedance.json appid %r is not a numeric TikTok App ID' % appid)
            elif appid == SHARED_TEST_GROUP:
                report['notes'].append('shared test-group App ID (used by many games; expected, not a risk)')
        elif data is not None:
            report['problems'].append('settings/bytedance.json is not a JSON object')
    report['passed'] = not report['problems']
    report['status'] = 'pass' if report['passed'] else 'needs_fix'
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        r = audit(a.project)
    except ValueError as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False)); return 2
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(r, ensure_ascii=False))
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
