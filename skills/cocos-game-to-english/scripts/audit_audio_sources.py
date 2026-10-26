#!/usr/bin/env python3
"""Check that every audio file in the game has a recorded, commercially usable source.

Read-only. Scans PROJECT/assets for audio files. Each file must be covered by:
  1. docs/audio/credits.csv written by the game-audio-library pipeline (column "outputs"
     lists the game files made from each source; "license" must be allowed), or
  2. a line in docs/audio/sources.md naming the file, for audio kept from the original
     game or supplied by the starter pack: write "原游戏自带" / "启动包提供" (plus the licence
     when known). Synthesized/AI-made, NC/ND/personal-use, CC-BY-SA and "待下载" are rejected.
The licence rules mirror game-audio-library/scripts/common.py classify_license.

Usage:
  python audit_audio_sources.py --project GAME_PROJECT [--binding review.json] [--out result.json]

Exit codes: 0 all recorded and allowed, 1 problems found, 2 bad input or output exists.
It does not listen to audio. Attribution-required files are counted so the credits page can be checked.
"""
import argparse
import csv
import json
import re
from pathlib import Path

AUDIO = {'.mp3', '.ogg', '.wav', '.m4a', '.aac', '.flac'}
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'audio-inbox', 'audio_work'}
DENY = [r'\bnc\b', r'non[- ]?commercial', r'personal use', r'editorial', r'\bnd\b', r'no[- ]?deriv',
        r'sampling\+', r'\bsa\b', r'share[- ]?alike']
FREE = [r'\bcc0\b', r'public ?domain', r'\bpdm\b', r'pixabay', r'mixkit', r'kenney', r'sonniss',
        r'99sounds', r'bigsoundbank', r'royalty[- ]?free']
ATTR = [r'\bcc[- ]?by\b', r'oga[- ]?by', r'attribution', r'zapsplat', r'incompetech', r'soundimage', r'noiseforfun']
KEPT = re.compile(r'原游戏自带|启动包提供|original game|starter pack', re.I)
NOT_REAL = re.compile(r'synth|generated|numpy|scipy|\bai[- ]?(made|generated|music|audio)\b|合成|生成|待下载', re.I)


def licence(text):
    """(allowed, attribution_required, reason)"""
    t = (text or '').lower().replace('_', ' ')
    if not t.strip():
        return False, False, 'empty licence'
    for p in DENY:
        if re.search(p, t):
            return False, False, 'not allowed: ' + p
    if NOT_REAL.search(t):
        return False, False, 'synthesized/AI-made or pending download'
    if any(re.search(p, t) for p in FREE):
        return True, False, ''
    if any(re.search(p, t) for p in ATTR):
        return True, True, ''
    return False, False, 'unknown licence: ' + text


def scan(project):
    root = project / 'assets'
    if not root.is_dir():
        raise ValueError(f'no assets folder in {project}')
    return [p for p in sorted(root.rglob('*'))
            if p.suffix.lower() in AUDIO and p.is_file()
            and not SKIP_DIRS & {x.lower() for x in p.relative_to(project).parts}]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--binding', type=Path, help='known-issue review JSON whose "binding" is copied into the report')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        if a.out and a.out.exists():
            raise ValueError(f'output exists: {a.out}')
        binding = None
        if a.binding:
            binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
            if not isinstance(binding, dict):
                raise ValueError(f'no binding object in {a.binding}')
        files = scan(a.project)
        credits_csv = a.project / 'docs/audio/credits.csv'
        rows = []
        if credits_csv.is_file():
            with credits_csv.open(newline='', encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
        sources_md = a.project / 'docs/audio/sources.md'
        lines = sources_md.read_text(encoding='utf-8-sig').splitlines() if sources_md.is_file() else []
    except (OSError, ValueError) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False))
        return 2

    by_output = {}
    for r in rows:
        for out in (r.get('outputs') or '').split(';'):
            if out.strip():
                by_output.setdefault(out.strip().replace('\\', '/'), []).append(r)
    checks, attribution = [], 0
    for f in files:
        rel = f.relative_to(a.project).as_posix()
        problem, attr = '', False
        recs = by_output.get(rel)
        if recs:
            results = [licence(r.get('license', '')) for r in recs]
            bad = [why for ok, _, why in results if not ok]
            problem = ('credits.csv: ' + bad[0]) if bad else ''
            attr = any(x[1] for x in results)
        else:
            hits = [x for x in lines if f.name in x]
            if not hits:
                problem = 'no record in docs/audio/credits.csv or docs/audio/sources.md'
            elif any(NOT_REAL.search(x) or any(re.search(p, x.lower()) for p in DENY) for x in hits):
                problem = 'sources.md marks it synthesized/pending or NC/ND/SA/personal-use'
            elif any(KEPT.search(x) for x in hits):
                problem = ''
            else:
                results = [licence(x) for x in hits]
                problem = '' if any(ok for ok, _, _ in results) else 'sources.md: no allowed licence on its line'
                attr = any(ok and need for ok, need, _ in results)
        attribution += 1 if attr and not problem else 0
        checks.append({'path': rel, 'passed': not problem, 'problem': problem, 'attribution_required': attr})
    failed = sum(1 for c in checks if not c['passed'])
    report = {'tool': 'audit_audio_sources', 'checked': len(checks), 'failed': failed, 'passed': failed == 0,
              'attribution_required': attribution, 'checks': checks,
              'note': 'Checks source records only. If attribution_required > 0, docs/audio/CREDITS.txt must appear on an in-game credits page.'}
    if binding is not None:
        report['binding'] = binding
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'checked': len(checks), 'failed': failed, 'attribution_required': attribution,
                      'problems': [c for c in checks if not c['passed']][:15]}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
