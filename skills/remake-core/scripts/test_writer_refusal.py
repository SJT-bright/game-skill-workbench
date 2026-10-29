#!/usr/bin/env python3
"""Prove that the game's real packaging script (the "writer") refuses to make a ZIP without a passing gate.

Monkey Dash 2026-10-21: the shared gate rejects bad reviews in its own tests, but nobody had checked that
the project's packaging script actually calls it. This runs the real writer through refusal and normal paths:

  missing_review   the known-issue review file is moved away          -> writer must exit non-zero, no new ZIP
  failed_check     one check row in the review is set to "fail"        -> writer must exit non-zero, no new ZIP
  stale_binding    the review's source fingerprint is replaced         -> writer must exit non-zero, no new ZIP
  missing_storage  STORAGE-01 Native report removed                    -> writer must exit non-zero, no new ZIP
  normal           the original review is restored                     -> writer must exit 0 and make a new ZIP

The original review is always restored byte-for-byte (checked by SHA-256). A ZIP that a refusal case
still produced is moved to <zip-dir>/_refusal_test_leaks/ so it can never be delivered.

The writer must run `check_known_issues.py check --stage pre_scan` (or an equivalent call) on the review
before it builds the ZIP and stop on a non-zero result; that is what this test proves.

Usage:
  python test_writer_refusal.py --review docs/test/known-issue-review.json --zip-dir build/zips \
      --out evidence/writer-refusal.json -- python3 tools/make_upload_zip.py --tag v9
  (everything after -- is the writer command, run from the current folder)
Exit codes: 0 all four cases behaved, 1 the writer let a bad case through or broke the normal path, 2 bad input.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def zips(folder):
    folder = Path(folder)
    if not folder.exists():
        return {}
    return {p: p.stat().st_mtime_ns for p in folder.rglob('*.zip') if '_refusal_test_leaks' not in p.parts}


def run_case(name, writer, zip_dir, timeout, expect_ok):
    before = zips(zip_dir)
    started = time.time()
    try:
        proc = subprocess.run(writer, capture_output=True, text=True, timeout=timeout)
        code, tail = proc.returncode, (proc.stdout + proc.stderr)[-1500:]
    except subprocess.TimeoutExpired:
        code, tail = None, 'writer timed out'
    after = zips(zip_dir)
    new = sorted(str(p) for p, m in after.items() if p not in before or before[p] != m)
    leaks = []
    if not expect_ok and new:
        leak_dir = Path(zip_dir) / '_refusal_test_leaks' / name
        leak_dir.mkdir(parents=True, exist_ok=True)
        for p in new:
            target = leak_dir / Path(p).name
            shutil.move(p, target)
            leaks.append(str(target))
    passed = (code == 0 and bool(new)) if expect_ok else (code not in (0, None) and not new)
    return {'id': name, 'passed': passed, 'expected': 'exit 0 and a new ZIP' if expect_ok else 'non-zero exit and no new ZIP',
            'exit_code': code, 'new_zips': new if expect_ok else [], 'leaked_zips_quarantined': leaks,
            'seconds': round(time.time() - started, 2), 'output_tail': tail}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--review', type=Path, required=True, help='the known-issue review JSON the writer checks')
    ap.add_argument('--zip-dir', type=Path, required=True, help='folder where the writer puts ZIPs')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--timeout', type=int, default=1800)
    ap.add_argument('writer', nargs=argparse.REMAINDER, help='-- followed by the writer command')
    a = ap.parse_args()
    writer = a.writer[1:] if a.writer[:1] == ['--'] else a.writer
    if not writer:
        ap.error('give the writer command after --')
    if not a.review.is_file():
        ap.error(f'review not found: {a.review}')
    if a.out.exists():
        ap.error(f'output exists: {a.out}')
    original = a.review.read_bytes()
    original_sha = sha(a.review)
    review = json.loads(original.decode('utf-8'))
    binding = review.get('binding')
    if not isinstance(binding, dict) or not isinstance(review.get('checks'), dict) or not review['checks']:
        ap.error('review has no binding or checks; make it with check_known_issues.py init first')
    aside = a.review.with_name(a.review.name + '.refusal-test-aside')
    checks = []
    try:
        a.review.rename(aside)
        checks.append(run_case('missing_review', writer, a.zip_dir, a.timeout, False))
        aside.rename(a.review)

        broken = json.loads(original.decode('utf-8'))
        first = sorted(broken['checks'])[0]
        broken['checks'][first] = {**broken['checks'][first], 'status': 'fail'}
        a.review.write_text(json.dumps(broken, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        checks.append(run_case('failed_check', writer, a.zip_dir, a.timeout, False))

        stale = json.loads(original.decode('utf-8'))
        stale['binding'] = {**stale['binding'], 'source_sha256': '0' * 64}
        a.review.write_text(json.dumps(stale, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        checks.append(run_case('stale_binding', writer, a.zip_dir, a.timeout, False))

        if 'STORAGE-01' in review['checks']:
            no_storage = json.loads(original.decode('utf-8'))
            no_storage['checks']['STORAGE-01']['auto_reports'] = []
            a.review.write_text(json.dumps(no_storage, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            checks.append(run_case('missing_storage', writer, a.zip_dir, a.timeout, False))

        a.review.write_bytes(original)
        checks.append(run_case('normal', writer, a.zip_dir, a.timeout, True))
    finally:
        if aside.exists() and not a.review.exists():
            aside.rename(a.review)
        if not a.review.exists() or sha(a.review) != original_sha:
            a.review.write_bytes(original)
        if aside.exists():
            aside.unlink()
    restored = sha(a.review) == original_sha
    # Pin executable scripts, not review/input/output data arguments. The
    # normal-case calibration ZIP is explicitly temporary and removed later.
    writer_files = [w for i,w in enumerate(writer) if Path(w).is_file() and
                    (i == 0 or Path(w).suffix.lower() in {'.py','.js','.cjs','.mjs','.sh'})]
    report = {'tool': 'test_writer_refusal', 'binding': binding, 'checked': len(checks),
              'failed': sum(not c['passed'] for c in checks) + (0 if restored else 1),
              'passed': all(c['passed'] for c in checks) and restored and len(checks) == (5 if 'STORAGE-01' in review['checks'] else 4),
              'review_restored': restored, 'writer_command': writer,
              'writer_files': [{'path': str(Path(w).resolve()), 'sha256': sha(w)} for w in writer_files],
              'checks': checks,
              'note': 'Proves the real writer calls the gate. A ZIP made in the normal case still needs post_package checks before delivery.'}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'cases': {c['id']: c['passed'] for c in checks},
                      'review_restored': restored, 'report': str(a.out)}, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
