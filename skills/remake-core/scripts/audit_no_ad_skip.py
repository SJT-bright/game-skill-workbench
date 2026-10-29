#!/usr/bin/env python3
"""Find "skip level" features (user rule: no game ever offers watching an ad to skip a level).

Read-only. Scans PROJECT/assets scripts (comments removed), scenes and prefabs, and optionally
the Native upload ZIP, for level/stage-skip identifiers and texts:
  blocking  skipLevel / skip_stage / levelSkip / adSkipLevel ..., "Skip Level", "Skip this level",
            跳关 / 跳过本关 / 跳过关卡 / 跳过此关
  review    bare "skip" buttons inside result/fail/level prefabs or scenes (often a skip-level button;
            tutorial skip is fine) - listed for a look, they do not fail the check
Lines containing the test-only marker __QA_LEVEL_JUMP__ are ignored here (verify_native_zip.py
makes sure that marker never reaches the upload package).

Usage:
  python audit_no_ad_skip.py --project GAME_PROJECT [--native-zip upload.zip] [--binding review.json] [--out result.json]
Exit codes: 0 nothing blocking, 1 skip-level code or text found, 2 bad input.
"""
import argparse
import json
import re
import zipfile
from pathlib import Path

SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles'}
CODE = {'.ts', '.js'}
SERIAL = {'.prefab', '.fire', '.scene'}
BLOCK = re.compile(r'(skip[_\-\s]?(this[_\-\s]?)?(level|stage|lvl))|((level|stage|lvl)[_\-\s]?skip)|'
                   r'(ad[_\-]?skip[_\-]?(level|stage))|跳关|跳过本关|跳过关卡|跳过此关|跳过这一关', re.I)
REVIEW_NAME = re.compile(r'"_name"\s*:\s*"([^"]*skip[^"]*)"', re.I)
REVIEW_FILE = re.compile(r'fail|lose|result|win|level|stage|settle|over', re.I)
QA = '__QA_LEVEL_JUMP__'


def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), text, flags=re.S)
    return re.sub(r'(^|[^:"\'\\])//.*', r'\1', text)


def scan_text(label, text, is_code, blocking, review, is_serial=False):
    body = strip_comments(text) if is_code else text
    for no, line in enumerate(body.splitlines(), 1):
        if QA in line:
            continue
        m = BLOCK.search(line)
        if m:
            blocking.append({'where': f'{label}:{no}', 'match': m.group(0), 'line': line.strip()[:160]})
    if is_serial and REVIEW_FILE.search(label):
        for m in REVIEW_NAME.finditer(text):
            if not BLOCK.search(m.group(1)) and 'tutorial' not in m.group(1).lower() and 'guide' not in m.group(1).lower():
                review.append({'where': label, 'node': m.group(1)})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--native-zip', type=Path)
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        if not (a.project / 'assets').is_dir():
            raise ValueError(f'no assets folder in {a.project}')
        if a.out and a.out.exists():
            raise ValueError(f'output exists: {a.out}')
        binding = None
        if a.binding:
            binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
            if not isinstance(binding, dict):
                raise ValueError(f'no binding object in {a.binding}')
        blocking, review, files = [], [], 0
        for p in sorted((a.project / 'assets').rglob('*')):
            if not p.is_file() or p.suffix not in CODE | SERIAL or SKIP_DIRS & {x.lower() for x in p.relative_to(a.project).parts}:
                continue
            files += 1
            scan_text(p.relative_to(a.project).as_posix(), p.read_text(encoding='utf-8', errors='replace'),
                      p.suffix in CODE, blocking, review, p.suffix in SERIAL)
        if a.native_zip:
            with zipfile.ZipFile(a.native_zip) as z:
                for name in z.namelist():
                    if Path(name).suffix in {'.js', '.json'} and 'adapter' not in name and 'cocos2d' not in name:
                        files += 1
                        scan_text('zip:' + name, z.read(name).decode('utf-8', errors='replace'), name.endswith('.js'),
                                  blocking, review)
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False))
        return 2
    report = {'tool': 'audit_no_ad_skip', 'checked': files, 'failed': len(blocking), 'passed': not blocking,
              'checks': [{'passed': False, **b} for b in blocking], 'review': review,
              'note': 'Remove every skip-level entry, handler, ad request and consumer; rename unrelated code that only looks similar.'}
    if binding is not None:
        report['binding'] = binding
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'checked': files, 'blocking': len(blocking), 'review': len(review),
                      'found': blocking[:8], 'look_at': review[:5]}, ensure_ascii=False))
    return 1 if blocking else 0


if __name__ == '__main__':
    raise SystemExit(main())
