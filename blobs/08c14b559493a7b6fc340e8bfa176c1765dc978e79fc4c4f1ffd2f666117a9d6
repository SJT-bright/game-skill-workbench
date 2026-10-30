#!/usr/bin/env python3
"""Rewarded-ad entries must be reachable, static part (v7.5, Germ2048 item 8.1). Read-only.

Germ2048's original passed "ad markers present" because createRewardedVideoAd was in the code, but the only script that
used it sat on btn_video in "ui Start.prefab", a node saved inactive: a component on an inactive node never runs, so
its own "this.node.active = true" never ran and the player never saw a video button.

  1. ad functions: createRewardedVideoAd, RewardedService .request(), and every function whose body calls one (wrappers,
     followed to a fixpoint; generic names like show/play/request are not propagated);
  2. ad scripts: game components (not the platform layer) that call an ad function;
  3. entries: prefab/scene nodes carrying an ad script, or a cc.Button whose click event targets one;
  4. an entry is reachable when it and its ancestors are saved active, or another script turns the node on by name
     (e.g. "btn_video.active = true" outside the node's own components).
Verdict: ad entries exist in prefabs/scenes and none is reachable -> needs_fix (exit 1). Each unreachable entry, and ad
code with no prefab/scene entry (buttons built in code), is listed for review.
The final-stage proof is runtime: dump_ui on home / result / revive must show at least one rewarded-video button.

  python3 audit_ad_entry_reachability.py --project <cocos project> [--out report.json]
"""
import argparse
import json
from pathlib import Path
import re
import sys

SKIP = {'library', 'temp', 'build', 'local', 'node_modules', '.git', 'packages', 'profiles'}
LAYER_DIRS = {'tiktok-platform', 'platform', 'platforms', 'sdk', 'adapter', 'adapters', 'wx', 'tt', 'qq'}
BASE = re.compile(r'\bcreateRewardedVideoAd\s*\(')
DEF = re.compile(r'^[ \t]*(?:(?:public|private|protected|static|async|export|function)\s+)*([A-Za-z_$][\w$]*)\s*'
                 r'(?:=\s*(?:async\s*)?function\s*\(|:\s*(?:async\s*)?function\s*\(|\([^()\n]*\)\s*(?::\s*[^{\n]+)?\{)', re.M)
GENERIC = {'show', 'play', 'request', 'start', 'open', 'init', 'then', 'update', 'onLoad', 'onEnable', 'call', 'apply', 'run',
           'load', 'create', 'get', 'set', 'tick', 'exit', 'close', 'constructor', 'if', 'for', 'while', 'switch', 'catch', 'function'}
B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
COMMENT = re.compile(r'/\*.*?\*/|(^|[^:\'"\\])//[^\n]*', re.S)


def compress(uuid):
    """Cocos Creator 2.x 23-character compressed uuid used as __type__ for script components."""
    h = uuid.replace('-', '')
    out = h[:5]
    for i in range(5, 32, 3):
        v = int(h[i:i + 3], 16)
        out += B64[v >> 6] + B64[v & 63]
    return out


def scripts(project):
    out = {}
    for p in sorted((project / 'assets').rglob('*')):
        if p.is_file() and p.suffix in ('.ts', '.js') and not p.name.endswith('.d.ts') and not SKIP & set(p.relative_to(project).parts):
            text = COMMENT.sub(lambda m: (m.group(1) or '') + '\n' * m.group(0).count('\n'), p.read_text(encoding='utf-8', errors='ignore'))
            out[p] = text
    return out


def match_brace(text, start):
    depth, i, n, quote = 0, start, len(text), None
    while i < n:
        ch = text[i]
        if quote:
            if ch == '\\':
                i += 1
            elif ch == quote:
                quote = None
        elif ch in '"\'`':
            quote = ch
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return n - 1


def bodies(text, wrappers_only=False):
    """(name, body) per function/method definition; the body is brace-matched, so nested callbacks stay inside it.
    wrappers_only: static methods, top-level functions and "name: function" only (instance handlers such as onclick_self
    are entries, not wrappers)."""
    out = []
    for m in DEF.finditer(text):
        head = m.group(0)
        if wrappers_only and not (re.search(r'\b(?:static|function|export)\b', head) or re.search(r'[:=]\s*(?:async\s*)?function', head)
                                  or not head[:1].isspace()):
            continue
        start = text.find('{', m.end() - 1)
        if start < 0:
            continue
        end = match_brace(text, start)
        nxt = re.match(r'\s*\{', text[end + 1:])
        if nxt and ';' not in text[start:end]:   # "(): { a: T } {": the first braces were a return type
            start = end + 1 + nxt.end() - 1
            end = match_brace(text, start)
        out.append((m.group(1), text[start:end + 1]))
    return out


def ad_functions(code):
    """name -> files defining it, for createRewardedVideoAd wrappers followed to a fixpoint."""
    names = {}
    while True:
        call = re.compile(r'\b(?:%s)\s*\(' % '|'.join(map(re.escape, sorted(names)))) if names else None
        added = False
        for p, text in code.items():
            kit = 'RewardedService' in text
            for name, body in bodies(text, wrappers_only=True):
                if name in GENERIC or len(name) < 5 or p in names.get(name, ()):
                    continue
                inner = body[1:]
                if BASE.search(inner) or (kit and re.search(r'\.request\s*\(', inner)) or \
                        (call and any(m.group(0).split('(')[0].strip() != name for m in call.finditer(inner))):
                    names.setdefault(name, set()).add(p)
                    added = True
        if not added:
            return names


def calls_ad(path, text, names):
    """True when the file calls an ad function it does not define itself (or uses the kit / the raw API outside a wrapper)."""
    if 'RewardedService' in text and re.search(r'\.request\s*\(', text) and path.name != 'RewardedService.js':
        return True
    own = {n for n, files in names.items() if path in files}
    if BASE.search(text) and not own:
        return True
    other = [n for n in names if n not in own]
    return bool(other) and bool(re.search(r'\b(?:%s)\s*\(' % '|'.join(map(re.escape, sorted(other))), text))


def audit(project):
    project = Path(project).resolve()
    if not (project / 'assets').is_dir():
        raise ValueError('not a Cocos project (no assets folder): %s' % project)
    code = scripts(project)
    names = ad_functions(code)
    ad_scripts = {}
    for p, text in code.items():
        if LAYER_DIRS & {x.lower() for x in p.relative_to(project).parts[:-1]}:
            continue
        if calls_ad(p, text, names):
            meta = p.with_name(p.name + '.meta')
            try:
                uuid = json.loads(meta.read_text(encoding='utf-8-sig'))['uuid']
            except (OSError, ValueError, KeyError):
                uuid = None
            ad_scripts[p.stem] = {'file': p.relative_to(project).as_posix(), 'uuid': uuid, 'type': compress(uuid) if uuid else None}
    by_type = {v['type']: k for k, v in ad_scripts.items() if v['type']}
    entries = []
    for f in sorted((project / 'assets').rglob('*')):
        if f.suffix not in ('.prefab', '.fire', '.scene') or SKIP & set(f.relative_to(project).parts):
            continue
        try:
            data = json.loads(f.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        if not isinstance(data, list):
            continue
        parent = {}
        for i, o in enumerate(data):
            if isinstance(o, dict) and o.get('__type__') in ('cc.Node', 'cc.Scene'):
                for c in o.get('_children') or []:
                    if isinstance(c, dict) and '__id__' in c:
                        parent[c['__id__']] = i
        for i, o in enumerate(data):
            if not (isinstance(o, dict) and o.get('__type__') == 'cc.Node'):
                continue
            hit = None
            for c in o.get('_components') or []:
                comp = data[c['__id__']] if isinstance(c, dict) and isinstance(c.get('__id__'), int) and c['__id__'] < len(data) else {}
                if comp.get('__type__') in by_type:
                    hit = by_type[comp['__type__']]
                if comp.get('__type__') == 'cc.Button':
                    for e in comp.get('clickEvents') or []:
                        ev = data[e['__id__']] if isinstance(e, dict) and isinstance(e.get('__id__'), int) else {}
                        if ev.get('component') in ad_scripts:
                            hit = ev['component']
            if not hit:
                continue
            chain, j = [], i
            while j is not None:
                chain.append(data[j])
                j = parent.get(j)
            inactive = [n.get('_name') for n in chain if n.get('__type__') == 'cc.Node' and n.get('_active') is False]
            name = o.get('_name') or ''
            outside = [p.relative_to(project).as_posix() for p, text in code.items() if p.stem != hit and name and
                       re.search(r'\b%s\b[^\n;]{0,80}\.active\s*=\s*(?!false\b)' % re.escape(name), text)]
            entries.append({'where': '%s#%s' % (f.relative_to(project).as_posix(), name), 'script': hit, 'saved_inactive': inactive,
                            'turned_on_by': outside, 'reachable': not inactive or bool(outside)})
    reachable = [e for e in entries if e['reachable']]
    problems, review = [], []
    if ad_scripts and entries and not reachable:
        problems.append('no rewarded-ad entry can be reached: %s' % '; '.join(
            '%s is saved inactive (%s) and nothing else turns it on (a component on an inactive node never runs)'
            % (e['where'], ', '.join(e['saved_inactive'])) for e in entries))
    if ad_scripts and not entries:
        # Calibration 2026-10-29: 9 of 20 completed games build their buttons in code; no prefab entry is not a refusal.
        review.append('ad code in %s but no prefab/scene button carries it (buttons built in code?): prove one entry with dump_ui'
                      % ', '.join(sorted(ad_scripts)))
    review += ['%s is saved inactive (%s) and nothing else turns it on' % (e['where'], ', '.join(e['saved_inactive']))
               for e in entries if not e['reachable'] and reachable]
    return {'tool': 'audit_ad_entry_reachability', 'schema': 1, 'project': str(project), 'ad_functions': sorted(names),
            'ad_scripts': ad_scripts, 'entries': entries, 'reachable_entries': len(reachable), 'problems': problems,
            'review': review, 'passed': not problems, 'status': 'needs_fix' if problems else ('review' if review else 'pass'),
            'boundary': 'static prefab/scene and code; popups opened by code are counted when their prefab root is active. '
                        'Final proof: dump_ui reads a rewarded-video button on home/result/revive'}


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
    print(json.dumps({k: r[k] for k in ('status', 'reachable_entries', 'problems', 'review')}, ensure_ascii=False))
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
