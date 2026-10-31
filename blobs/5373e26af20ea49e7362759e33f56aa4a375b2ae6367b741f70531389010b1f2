"""K6_kit_module_old (v7.8, 总表 B30 C): an old platform-kit SOURCE module inside a Cocos 2.4 package's script bundle.

What was not checked before: K1/K2 prove the NATIVE parts byte by byte (main.js, touch-coordinates.js, storage-guard.js)
and K5 proves the project's source copies (writers only). Nothing looked at what the BUILD actually contains: Cocos 2.4
merges every assets/ script into assets/main/index.js / subpackages/*/game.js, minified, so a stale build (made before
the kit sources were restored) or a hand-copied old module ships an old RewardedService / SaveStore / MissionFlow while
the project looks current (全民飞车漂移 v2: RewardedService v1.1 in the bundle, 4 of 4 old marks, 0 of 16 current).
From the 全民飞车门禁 prototype kit_version_gate.py: minification keeps property names and strings and every module
starts with cc._RF.push(module, "<uuid>", "<Name>"); the bundle is cut into modules there and each kit module is
recognised by the names / strings only the current text or only one previous text has (platform-kit
KIT_FINGERPRINTS.json, built by platform-kit/tools/build_kit_fingerprints.py from the manifest and the old texts in
platform-kit/tools/kit_versions/).
    K6_kit_module_old      block for a new game, warning for a legacy game: a kit module recognised as a previous
                           version. Only display strings differ (MissionFlow's preview hint): warning on every game.
    K6_kit_module_unknown  warning: a kit-named module that matches neither the current nor a known previous text
    K6_fingerprints_stale  warning: KIT_FINGERPRINTS.json was built for other kit hashes (rebuild it; the release
                           self-test test_kit_module_versions.py fails then)
Cocos 3.x kit plugins are separate files and keep their marker lines (K1_plugin3x), so only 2.4 bundles are read here.
"""
import hashlib
import json
import re
from pathlib import Path

from . import finding

KIT = Path(__file__).resolve().parents[2] / 'assets' / 'platform-kit'
FINGERPRINTS = KIT / 'KIT_FINGERPRINTS.json'
VERSIONS = KIT / 'tools' / 'kit_versions'
SCRIPT_MODULES = ('RewardedService', 'SaveStore', 'MissionFlow', 'TikTokMissionService', 'PlatformConfig', 'HomeGrowthEntries')
NOISE = set('''prototype length call apply push pop exports module require function return this var let const
then catch resolve reject undefined null true false constructor toString default use strict Math floor min max now
Date setTimeout clearTimeout options console log warn error string number object game tt wx cc _RF'''.split())
STR_RE = re.compile(r'"((?:[^"\\\n]|\\.){3,200})"|\'((?:[^\'\\\n]|\\.){3,200})\'')
PROP_RE = re.compile(r'\.([A-Za-z_$][\w$]{3,})\b')
KEY_RE = re.compile(r'[{,]\s*([A-Za-z_$][\w$]{3,})\s*:')
RF_RE = re.compile(r'cc\._RF\.push\(\s*[\w$]+\s*,\s*"[0-9a-zA-Z+/=_-]*"\s*,\s*"([\w$-]+)"\s*\)')


def strip_comments(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in '"\'`':
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == '\\' else 1
            out.append(src[i:j + 1])
            i = j + 1
        elif src.startswith('//', i):
            j = src.find('\n', i)
            i = n if j < 0 else j
        elif src.startswith('/*', i):
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def tokens(src, strings=True):
    s = strip_comments(src)
    t = {'p:' + m for m in PROP_RE.findall(s)} | {'p:' + m for m in KEY_RE.findall(s)}
    if strings:
        for a, b in STR_RE.findall(s):
            v = (a or b).strip()
            if v and not v.isdigit():
                t.add('s:' + v)
    return {x for x in t if x[2:] not in NOISE}


def build(manifest, kit_dir=KIT, versions=VERSIONS):
    """Fingerprints from the manifest's current files and the previous texts in tools/kit_versions/<Module>/<sha>.txt."""
    fps = {'schema': 'tiktok-kit.fingerprints.v1', 'manifest_version': manifest.get('version'), 'modules': {}}
    for mod in SCRIPT_MODULES:
        rel = 'assets/tiktok-platform/%s.js' % mod
        meta = (manifest.get('files') or {}).get(rel)
        if not meta:
            continue
        editable = bool(meta.get('editable'))
        data = (Path(kit_dir) / rel).read_bytes()
        if hashlib.sha256(data).hexdigest() != meta['sha256']:
            raise ValueError('kit file %s does not match its manifest hash' % rel)
        cur = tokens(data.decode('utf-8'), strings=not editable)
        entry = {'current_sha256': meta['sha256'], 'editable': editable, 'previous': {}, 'previous_without_text': []}
        prev = {}
        for h in meta.get('previous_sha256') or []:
            f = Path(versions) / mod / (h + '.txt')
            if f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest() == h:
                prev[h] = tokens(f.read_text(encoding='utf-8'), strings=not editable)
            else:
                entry['previous_without_text'].append(h)
        allprev = set().union(*prev.values()) if prev else set()
        entry['current_only'] = sorted(cur - allprev)
        entry['common'] = sorted(cur & allprev)[:60]
        for h, ps in prev.items():
            entry['previous'][h] = sorted(ps - cur)
        fps['modules'][mod] = entry
    return fps


def load(path=FINGERPRINTS):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def stale_modules(fps, manifest):
    return sorted(m for m, e in (fps.get('modules') or {}).items()
                  if ((manifest.get('files') or {}).get('assets/tiktok-platform/%s.js' % m) or {}).get('sha256') != e.get('current_sha256'))


def segments(files):
    """{module name: [(file, code)]} for every cc._RF.push module in the package's script bundles."""
    seg = {}
    for name, data in files.items():
        if not name.endswith('.js') or name.startswith(('cocos/', 'adapter')):
            continue
        if not (name.endswith(('index.js', 'project.js', 'game.js')) or '/' not in name):
            continue
        s = data.decode('utf-8', 'replace') if isinstance(data, bytes) else data
        if 'cc._RF.push' not in s:
            continue
        hits = list(RF_RE.finditer(s))
        for i, m in enumerate(hits):
            end = s.find('cc._RF.pop()', m.end())
            nxt = hits[i + 1].start() if i + 1 < len(hits) else len(s)
            end = nxt if end < 0 or end > nxt else end
            seg.setdefault(m.group(1), []).append((name, s[m.end():end]))
    return seg


def classify(entry, code):
    t = tokens(code, strings=not entry['editable'])
    cur = set(entry['current_only'])
    cur_hit = cur & t
    res = {'current_hits': '%d/%d' % (len(cur_hit), len(cur)), 'previous_hits': {}}
    best_prev, best_ratio = None, 0.0
    for h, lst in entry['previous'].items():
        ph = sorted(set(lst) & t)
        r = len(ph) / max(1, len(lst))
        res['previous_hits'][h[:12]] = '%d/%d' % (len(ph), len(lst))
        if r > best_ratio:
            best_prev, best_ratio, res['previous_examples'] = h, r, ph[:6]
    cur_ratio = len(cur_hit) / max(1, len(cur))
    common = set(entry.get('common') or [])
    subset_prev = [h for h, lst in entry['previous'].items() if not lst]
    if not cur:
        res['version'] = 'unversioned'          # editable PlatformConfig: no stable version marks
    elif cur_ratio >= 0.7 and best_ratio <= 0.2:
        res['version'] = 'current'
    elif best_ratio >= 0.6 and cur_ratio <= 0.3:
        res['version'] = 'previous'
        res['previous_sha256'] = best_prev
        # calibration (9 games, 2026-10-30): MissionFlow's previous versions differ only in a player-visible string
        res['text_only'] = all(x.startswith('s:') for x in cur) and all(x.startswith('s:') for x in entry['previous'][best_prev])
    elif subset_prev and cur_ratio <= 0.3 and common and len(common & t) / len(common) >= 0.6:
        res['version'] = 'previous'
        res['previous_sha256'] = subset_prev[-1]
        res['previous_examples'] = ['p:(missing) ' + x[2:] for x in sorted(cur - t)[:6]]
        res['text_only'] = False
    else:
        res['version'] = 'unknown'
    res['missing_current_examples'] = sorted(cur - t)[:6]
    return res


def verify(files, manifest, policy, engine, fingerprints=None):
    """Findings for a 2.4 package (files: {name: bytes}); manifest: the KIT_MANIFEST dict."""
    if engine != 2:
        return []
    try:
        fps = fingerprints if fingerprints is not None else load()
    except (OSError, ValueError) as error:
        return [finding('K6_fingerprints_stale', 'warn', 'KIT_FINGERPRINTS.json unreadable (%s): old kit modules in the '
                        'script bundle were not checked' % error)]
    out = []
    stale = stale_modules(fps, manifest)
    if stale:
        out.append(finding('K6_fingerprints_stale', 'warn', 'KIT_FINGERPRINTS.json was built for other kit hashes of %s: '
                           'run platform-kit/tools/build_kit_fingerprints.py; those modules were not checked' % ', '.join(stale)))
    seg = segments(files)
    level = 'block' if policy == 'new' else 'warn'
    for mod, entry in sorted((fps.get('modules') or {}).items()):
        if mod in stale:
            continue
        for name, code in seg.get(mod, []):
            r = classify(entry, code)
            ev = {'module': mod, 'file': name, 'version': r['version'], 'current_hits': r['current_hits'],
                  'previous_hits': r['previous_hits']}
            if r['version'] == 'previous':
                ev['previous_sha256'] = r['previous_sha256']
                marks = ', '.join(x[2:] for x in r.get('previous_examples') or [])
                if r.get('text_only'):
                    out.append(finding('K6_kit_module_old', 'warn', '%s in %s is the previous kit text %s; only display '
                                       'strings differ (%s): rebuild after tiktok_finalize.py source' % (
                                           mod, name, r['previous_sha256'][:12], marks), ev))
                else:
                    out.append(finding('K6_kit_module_old', level, '%s in %s is an OLD platform-kit version (previous sha %s, '
                                       'evidence %s; current marks %s): the build was made before the kit sources were '
                                       'restored, or an old copy sits in the project. Run tiktok_finalize.py source, '
                                       'rebuild in Creator, write the package again' % (
                                           mod, name, r['previous_sha256'][:12], marks, r['current_hits']), ev))
            elif r['version'] == 'unknown' and not entry.get('editable'):
                out.append(finding('K6_kit_module_unknown', 'warn', '%s in %s matches neither the current kit text nor a '
                                   'known previous one (current %s, previous %s): an edited copy?' % (
                                       mod, name, r['current_hits'], r['previous_hits']), ev))
    return out
