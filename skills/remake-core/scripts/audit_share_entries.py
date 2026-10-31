#!/usr/bin/env python3
"""Share-for-reward sites and "unavailable" dead buttons (v7.5, Germ2048 item 7). Read-only, static.

English rule (cocos-game-to-english/references/fixed-entries.md, v7.5 default from Saul's Germ2048 choice): share rewards
that are part of the core loop (revive, gift, double) become rewarded video; every other share entry is deleted together
with what triggers it (gift orb, popup). Germ2048's original did half of it: the share wrapper returned a fixed
"Sharing rewards are unavailable on this platform." and every entry stayed, so Claim / Revive / x2 never paid out.

Checks:
  1. player-visible text (string literals with a space in .ts/.js, Label strings in .prefab/.fire) saying a feature
     is "unavailable / not available on this platform", or "Sharing / Leaderboard unavailable" -> needs_fix; "coming soon" -> review;
  2. every call of a share wrapper (X.Share(...), shareAppMessage(...), shareToStory(...), ...) is listed; each game call
     site (not the platform layer: platform/api/sdk/wx/tt/qq folders or a file defining the wrapper) must
     be recorded in docs/ as deleted or converted to rewarded video -> otherwise needs_fix. A record is either
     docs/share-entries.json {"entries": [{"file": "assets/.../ReviveUISc.ts", "decision": "rewarded_video"|"deleted"}]}
     or a line in a docs/**/*.md that names the script (file stem) and says deleted/removed/rewarded/video/广告/删.
Exit 0 pass, 1 needs fix, 2 bad input.

  python3 audit_share_entries.py --project <cocos project> [--docs <docs folder>] [--out report.json]
"""
import argparse
import json
from pathlib import Path
import re
import sys

SKIP = {'library', 'temp', 'build', 'local', 'node_modules', '.git', 'packages', 'profiles', 'tiktok-platform'}
# Calibration 2026-10-29 (20 completed games): every one shows "... unavailable. Please retry." for a failed ad/save, so a
# bare "unavailable" is a normal error message. Refused: a FEATURE said to be missing on this platform (Germ2048:
# "Sharing rewards are unavailable on this platform.", "Leaderboard unavailable."). "Coming soon" is listed for review.
DEAD_TEXT = re.compile(r'(?:unavailable|not available|not supported) (?:on|in) (?:(?:this|the) platform|tiktok)\b|'
                       r'\b(?:shar\w*|leaderboards?|rank\w*|invit\w*|friends?)\b[^.\n]{0,30}\b(?:unavailable|not available)|'
                       r'暂未开放|暂不支持|本平台(?:暂)?不支持', re.I)
SOFT_TEXT = re.compile(r'\bcoming soon\b|敬请期待', re.I)
DEV_ONLY = re.compile(r'test build|browser|local preview|\bpreview\b|editor', re.I)   # local-test fallbacks, not shipped to players
# Platform layers (one wrapper per platform, e.g. 我出枪贼快 framework/platform/api/qqApi.ts) are where the share API lives;
# the game's call sites of the wrapper are what must be recorded. A file that defines a Share wrapper counts as a layer too.
LAYER_DIRS = {'platform', 'platforms', 'api', 'sdk', 'ald', 'wx', 'tt', 'qq', 'adapter', 'adapters'}
WRAPPER_DEF = re.compile(r'(?:static\s+(?:async\s+)?|function\s+|^\s*(?:async\s+)?)[Ss]hare\s*\([^)]*\)\s*(?::\s*[\w<>\[\]]+\s*)?\{|'
                         r'\b[Ss]hare\s*:\s*function\b', re.M)
LITERAL = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`((?:[^`\\]|\\.)*)`')
LABEL = re.compile(r'"_(?:N\$)?string"\s*:\s*"((?:[^"\\]|\\.)*)"')
SHARE_CALL = re.compile(r'(?<![\w$])(?:[A-Za-z_$][\w$]*\s*\.\s*)?(Share|share|shareAppMessage|shareToStory|shareMessageToFriend|'
                        r'shareVideoMessage|shareToFriend|showShareMenu)\s*\(')
DEFINITION = re.compile(r'(?:function\s+|static\s+(?:async\s+)?|async\s+|private\s+|public\s+|protected\s+|^\s*)$')
DECISION = re.compile(r'删|去掉|移除|广告|激励|deleted|removed|remove|rewarded|video|ad\b', re.I)
COMMENT = re.compile(r'/\*.*?\*/|(^|[^:\'"\\])//[^\n]*', re.S)


def strip(code):
    return COMMENT.sub(lambda m: (m.group(1) or '') + '\n' * m.group(0).count('\n'), code)


def line(text, pos):
    return text.count('\n', 0, pos) + 1


def files(project, suffixes):
    for p in sorted((project / 'assets').rglob('*')):
        if p.is_file() and p.suffix in suffixes and not p.name.endswith('.d.ts') and not SKIP & set(p.relative_to(project).parts):
            yield p


def records(docs):
    rec = []
    if not docs or not docs.is_dir():
        return rec, None
    js = docs / 'share-entries.json'
    if js.is_file():
        try:
            for e in json.loads(js.read_text(encoding='utf-8-sig')).get('entries', []):
                if isinstance(e, dict) and e.get('decision') in ('rewarded_video', 'deleted') and e.get('file'):
                    rec.append(('json', Path(str(e['file'])).stem, e['decision']))
        except (OSError, ValueError, AttributeError):
            pass
    for md in sorted(docs.rglob('*.md')):
        try:
            for ln in md.read_text(encoding='utf-8', errors='ignore').splitlines():
                if DECISION.search(ln):
                    rec.append(('md:' + md.name, ln, None))
        except OSError:
            continue
    return rec, str(docs)


def recorded(stem, rec):
    for kind, value, _ in rec:
        if kind == 'json' and value == stem:
            return kind
        if kind.startswith('md:') and re.search(r'(?<![\w])%s(?![\w])' % re.escape(stem), value):
            return kind
    return None


def audit(project, docs=None):
    project = Path(project).resolve()
    if not (project / 'assets').is_dir():
        raise ValueError('not a Cocos project (no assets folder): %s' % project)
    docs = Path(docs).resolve() if docs else project / 'docs'
    dead, soft, sites = [], [], []
    for p in files(project, ('.ts', '.js')):
        code = strip(p.read_text(encoding='utf-8', errors='ignore'))
        rel = p.relative_to(project).as_posix()
        for m in LITERAL.finditer(code):
            s = next(g for g in m.groups() if g is not None)
            if ' ' in s.strip() and DEAD_TEXT.search(s) and not DEV_ONLY.search(s):
                dead.append({'where': '%s:%d' % (rel, line(code, m.start())), 'text': s[:120]})
            elif SOFT_TEXT.search(s):
                soft.append({'where': '%s:%d' % (rel, line(code, m.start())), 'text': s[:120]})
        layer = bool(LAYER_DIRS & {x.lower() for x in p.relative_to(project).parts[:-1]}) or bool(WRAPPER_DEF.search(code))
        for m in SHARE_CALL.finditer(code):
            head = code[max(0, m.start() - 40):m.start()]
            if DEFINITION.search(head.split('\n')[-1]) and re.match(r'[^)]*\)\s*(?::\s*[\w<>\[\]]+\s*)?\{', code[m.end():m.end() + 200]):
                continue   # the wrapper's own definition, not a call site
            if re.search(r'(?:on|wx\.on)ShareAppMessage', code[m.start():m.end()]):
                continue
            sites.append({'where': '%s:%d' % (rel, line(code, m.start())), 'call': re.sub(r'\s*\($', '()', m.group(0).strip())[:60], 'script': p.stem, 'platform_layer': layer})
    for p in files(project, ('.prefab', '.fire', '.scene')):
        text = p.read_text(encoding='utf-8', errors='ignore')
        for m in LABEL.finditer(text):
            if SOFT_TEXT.search(m.group(1)) and not DEAD_TEXT.search(m.group(1)):
                soft.append({'where': '%s:%d' % (p.relative_to(project).as_posix(), line(text, m.start())), 'text': m.group(1)[:120]})
            elif DEAD_TEXT.search(m.group(1)):
                dead.append({'where': '%s:%d' % (p.relative_to(project).as_posix(), line(text, m.start())), 'text': m.group(1)[:120]})
    rec, docs_used = records(docs)
    for s in sites:
        s['record'] = recorded(s['script'], rec)
    unrecorded = [s for s in sites if not s['record'] and not s['platform_layer']]
    problems = ['player-visible "not available" text (dead button: delete the entry or make it work): %s "%s"' % (d['where'], d['text'])
                for d in dead]
    problems += ['share call %s (%s) has no docs/ record saying deleted or converted to rewarded video' % (s['where'], s['call'])
                 for s in unrecorded]
    return {'tool': 'audit_share_entries', 'schema': 1, 'project': str(project), 'docs': docs_used, 'dead_text': dead, 'review_text': soft,
            'share_sites': sites, 'unrecorded_sites': len(unrecorded), 'problems': problems, 'passed': not problems,
            'status': 'pass' if not problems else 'needs_fix',
            'boundary': 'static text and call sites; whether a converted entry really pays out is the ad regression / runtime check'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--docs', type=Path, help='docs folder holding the record (default <project>/docs)')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        r = audit(a.project, a.docs)
    except ValueError as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False)); return 2
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: r[k] for k in ('status', 'problems', 'unrecorded_sites')}, ensure_ascii=False))
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
