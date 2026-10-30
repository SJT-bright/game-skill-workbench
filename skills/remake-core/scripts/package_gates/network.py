"""Network / bundle-name / cross-promotion gates (v7.5, W1a).

H12_bundle_name     (block) game JS loads a bundle/subpackage by name that the package does not have
                    (MusicSlice v29b loadSubpackage('general'), GooglyEyeRecall). Ported from the completed-game
                    gate tiktok_upload_gate.py (known_bundles / missing_bundle_refs), calibrated 0 false blocks.
H13_analytics_domain (block) game JS carries a Chinese analytics SDK report host (Tencent MTA pas.qq.com /
                    mta.qq.com, Umeng, CNZZ, Baidu Tongji, TalkingData, Aldwx, GrowingIO, Zhuge): TikTok only
                    reaches domains registered in the developer console, so these never work there.
H14_cross_promo     (block) game JS calls navigateToMiniProgram / showMoreGamesModal or carries another mini
                    game's App ID (tt/wx + 16 hex). An emptied component that keeps only its field names has
                    none of these strings and passes (MergeShot2048 v83/v84).
Engine and platform-adapter files are never scanned (see package_gates.PackageView.game_js).
"""
import json
import posixpath
import re

from . import finding

LOAD_NAME = re.compile(r'''\b(?:loadBundle|loadSubpackage|loadSubPackage|preDownloadSubpackage)\s*\(\s*'''
                       r'''(?:\{\s*name\s*:\s*)?(['"])([A-Za-z0-9_\-]{1,64})\1''')
BUILTIN_BUNDLES = {'internal', 'main', 'resources', 'start-scene'}
SETTINGS = re.compile(r'(^|/)src/settings[^/]*\.(js|json)$')

ANALYTICS = re.compile(
    r'(?<![A-Za-z0-9.\-])((?:[A-Za-z0-9\-]+\.)*(?:pas\.qq\.com|mta\.qq\.com|pingma\.qq\.com|umeng\.com|umengcloud\.com|'
    r'cnzz\.com|hm\.baidu\.com|talkingdata\.com|talkingdata\.net|tenddata\.com|aldwx\.com|growingio\.com|'
    r'zhugeio\.com))(?![A-Za-z0-9\-])', re.I)
CROSS_PROMO = re.compile(r'\b(navigateToMiniProgram|showMoreGamesModal)\b')
FOREIGN_APP_ID = re.compile(r'''(['"])((?:tt|wx)[0-9a-f]{16})\1''')


def known_bundles(view):
    names = set(BUILTIN_BUNDLES)
    for sub in view.game_json.get('subpackages') or view.game_json.get('subPackages') or []:
        if not isinstance(sub, dict):
            continue
        for key in ('name', 'root'):
            value = str(sub.get(key) or '').strip().strip('/')
            if value:
                names.add(value)
                names.add(value.split('/')[-1])
    for name in view.files:
        parts = name.split('/')
        if len(parts) > 2 and parts[0] in ('assets', 'subpackages', 'remote'):
            names.add(parts[1])
        if len(parts) > 3 and parts[0] == 'subpackages' and parts[2] == 'assets':
            names.add(parts[3])
    for name in view.files:
        if not SETTINGS.search(name):
            continue
        text = view.text(name)
        names.update(re.findall(r'["\']?([A-Za-z0-9_\-]{1,64})["\']?\s*:\s*["\'][0-9a-f]{5}["\']', text))
        for block in re.findall(r'(?:subpackages|remoteBundles|projectBundles|preloadBundles)["\']?\s*:\s*\[([^\]]*)\]', text):
            names.update(re.findall(r'["\']([^"\']{1,64})["\']', block))
    return names


def _scanned(view):
    """Game JavaScript only; 'adapter' in the file name is also skipped (same rule as the calibrated gate)."""
    return [n for n in view.game_js() if 'adapter' not in posixpath.basename(n).lower()]


def missing_bundle_refs(view):
    known = known_bundles(view)
    found = {}
    for name in _scanned(view):
        for match in LOAD_NAME.finditer(view.text(name)):
            bundle = match.group(2)
            if bundle not in known:
                found.setdefault(bundle, name)
    return found


def _context(text, match, width=60):
    start, end = max(0, match.start() - width), min(len(text), match.end() + width)
    return text[start:end].replace('\n', ' ')


def analytics_hits(view):
    hits = []
    for name in _scanned(view):
        text = view.text(name)
        for match in ANALYTICS.finditer(text):
            if match.group(1).lower().startswith(('doc.', 'docs.', 'developer.')):
                continue          # documentation links (e.g. doc.aldwx.com in a .d.ts), not a report host
            hits.append({'file': name, 'host': match.group(1).lower(), 'context': _context(text, match)})
    return hits


def cross_promo_hits(view):
    try:
        own = str(json_appid(view) or '')
    except (ValueError, UnicodeDecodeError):
        own = ''
    hits = []
    for name in _scanned(view):
        text = view.text(name)
        for match in CROSS_PROMO.finditer(text):
            hits.append({'file': name, 'match': match.group(1), 'context': _context(text, match)})
        for match in FOREIGN_APP_ID.finditer(text):
            if match.group(2) != own:
                hits.append({'file': name, 'match': match.group(2), 'context': _context(text, match)})
    return hits


def json_appid(view):
    raw = view.files.get('project.config.json')
    if not raw:
        return None
    data = json.loads(raw.decode('utf-8-sig'))
    return data.get('appid') if isinstance(data, dict) else None


def check(view):
    out = []
    absent = missing_bundle_refs(view)
    if absent:
        out.append(finding('H12_bundle_name', 'block',
                           'code loads a bundle/subpackage the package does not have: ' +
                           '; '.join('%s (%s)' % kv for kv in list(absent.items())[:6]) +
                           ' - remove the call (other-channel code) or ship that bundle as a declared subpackage',
                           [{'bundle': b, 'file': f} for b, f in absent.items()]))
    hits = analytics_hits(view)
    if hits:
        hosts = sorted({h['host'] for h in hits})
        out.append(finding('H13_analytics_domain', 'block',
                           'Chinese analytics SDK report host in game JS: %s (%s) - TikTok only reaches registered '
                           'domains; remove the analytics module' % (', '.join(hosts), hits[0]['file']), hits[:10]))
    promo = cross_promo_hits(view)
    if promo:
        kinds = sorted({h['match'] for h in promo})
        out.append(finding('H14_cross_promo', 'block',
                           'cross-promotion / jump to other mini games in game JS: %s (%s) - empty the behaviour '
                           '(keep same-name fields if a prefab lists the component) so no call or foreign App ID '
                           'remains' % (', '.join(kinds[:6]), promo[0]['file']), promo[:10]))
    return out
