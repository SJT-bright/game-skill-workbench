#!/usr/bin/env python3
"""Find developer/test wording that players would see (user rule 2026-10-21).

Seen in playable builds: "PLAYABLE PROTOTYPE / PLACEHOLDER ART", "PLAYTEST LAB - NO STAGE REWARDS", "LOCAL PREVIEW",
"All 72 layouts are reachable here", "TRY THE MECHANICS"; 2026-10-23: status readouts "HOME SCREEN OPEN ·
PROFILE RETURN OPEN", "MISSIONS 2/3 RESOLVED" (state words of the code shown as text). Even a playtest build shown to the user
must look like the real game; test-only entries are reached by the test tools, not by player buttons.

Scans string literals in scripts and Label/RichText strings in scenes/prefabs/JSON under assets/.
With --final it also fails on referenced placeholder art (file names containing "placeholder").

  python audit_dev_text.py --project <Cocos project> [--final] [--binding review.json] [--out report.json]
Exit codes: 0 clean, 1 found, 2 bad input.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PHRASES = [r'prototype', r'placeholder', r'play\s*test', r'test\s*(lab|mode|build|only|entry)', r'debug', r'\bqa\b',
           r'dev\s*(mode|build|menu)', r'layouts? (are|is) reachable', r'try the mechanics', r'cheat', r'skip to level',
           r'unlock all', r'no stage rewards', r'normal save is separate', r'sandbox', r'\bwip\b', r'todo',
           r'local\s*preview', r'mock\s*(sdk|mode|ad)', r'test\s*ad\b', r'fake\s*(ad|sdk|reward)']   # 2026-10-21: "LOCAL PREVIEW" popup
# user 2026-10-23: status / debug readouts shown to the player ("HOME SCREEN OPEN · PROFILE RETURN OPEN", "MISSIONS 2/3 RESOLVED")
PHRASES += [r'\b(home|profile|shop|store|map|settings|league|skins?|level|result|pause|main|title)\s+(screen|page|panel|popup|scene)\s+'
            r'(open|opened|closed|shown|hidden|active|ready|loaded|visible)\b',
            r'\b(screen|page|panel|popup|scene)\s+(open|opened|closed|shown|hidden|loaded)\b',
            r'\b(return|back)\s+(open|opened|closed|ready|active)\b', r'\b\d+\s*/\s*\d+\s+resolved\b']
PAT = re.compile('|'.join(PHRASES), re.I)
STR = re.compile(r'''(["'`])((?:\\.|(?!\1).){2,200})\1''')
LABEL_KEYS = ('_string', '_N$string', 'string', 'text', '_text')
SKIP_DIRS = {'node_modules', 'library', 'temp', 'local', 'build', 'profiles', '.git', 'settings'}


def strip_comments(code):
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.S)
    return re.sub(r'(^|[^:])//.*', r'\1', code)


def scan(project, final):
    hits, placeholders = [], []
    root = project / 'assets' if (project / 'assets').is_dir() else project
    for f in root.rglob('*'):
        if not f.is_file() or set(f.relative_to(project).parts) & SKIP_DIRS:
            continue
        rel = f.relative_to(project).as_posix()
        if 'placeholder' in f.name.lower() and f.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}:
            placeholders.append(rel)
        suf = f.suffix.lower()
        try:
            text = f.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        if suf in {'.ts', '.js'}:
            for line_no, line in enumerate(strip_comments(text).splitlines(), 1):
                if 'console.' in line or 'cc.log' in line or 'throw ' in line:
                    continue                       # logs/errors are not on screen
                for m in STR.finditer(line):
                    s = m.group(2)
                    if ' ' in s or s.isupper():    # looks like display text, not an identifier/key
                        if PAT.search(s):
                            hits.append({'file': rel, 'line': line_no, 'text': s[:120]})
        elif suf in {'.fire', '.scene', '.prefab', '.json'}:
            try:
                data = json.loads(text)
            except ValueError:
                continue
            stack = [data]
            while stack:
                x = stack.pop()
                if isinstance(x, dict):
                    for k, v in x.items():
                        if k in LABEL_KEYS and isinstance(v, str) and PAT.search(v):
                            hits.append({'file': rel, 'line': 0, 'text': v[:120]})
                        elif isinstance(v, (dict, list)):
                            stack.append(v)
                elif isinstance(x, list):
                    stack.extend(x)
    return hits, placeholders


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--final', action='store_true', help='after the art stage: placeholder art must be gone')
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        if not a.project.is_dir():
            raise ValueError('project folder not found: ' + str(a.project))
        hits, placeholders = scan(a.project, a.final)
        binding = None
        if a.binding:
            binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
            if not isinstance(binding, dict):
                raise ValueError('no binding object in ' + str(a.binding))
        if a.out and a.out.exists():
            raise ValueError('output exists: ' + str(a.out))
    except (OSError, ValueError) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2
    failed = len(hits) + (len(placeholders) if a.final else 0)
    report = {'tool': 'audit_dev_text', 'checked': 1, 'failed': failed, 'passed': failed == 0, 'final': a.final,
              'dev_text': hits[:200], 'placeholder_art': placeholders[:200],
              'checks': [{'name': 'player-visible developer text', 'passed': not hits},
                         {'name': 'placeholder art (final only)', 'passed': not (a.final and placeholders)}],
              'note': 'Comments and console logs are ignored. Review each hit: if the text is never shown to players, rename it.'}
    if binding is not None:
        report['binding'] = binding
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'failed': failed, 'dev_text': hits[:8], 'placeholder_art': placeholders[:5] if a.final else len(placeholders)},
                     ensure_ascii=False))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
