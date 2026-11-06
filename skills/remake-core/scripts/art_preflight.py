"""Early art-only verification using the same production, slot and pixel checkers.
Never writes an ART receipt or changes game files. Full art_check still checks
capture provenance, all required pages and all other checks before a trial.
"""
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def run(project, dumps, out, board=None, binding=None):
    import art_production
    project, out = Path(project).resolve(), Path(out).resolve()
    if out.is_relative_to(project) or out.exists() and any(out.iterdir()):
        raise ValueError('use a fresh output directory outside project')
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    production = art_production.audit(project, require_cases=dumps is not None)
    result = dict(tool='art_production_preflight', scope='assets-and-first-integration-only',
                  production=production, runtime_verified=False, receipt_written=False)
    passed = production['passed']
    if dumps is None and (not production['declared'] or not production['assets']):
        result.update(error='no registered production assets; nothing was checked', status='not_run')
        passed = False
    if dumps is not None:
        import audit_page_richness
        documents = audit_page_richness.load([Path(dumps)])
        if not documents:
            result['error'] = 'no captured pages'
            passed = False
        config = project / 'docs/art/visual-slots.json'
        if config.exists():
            import audit_art_slots
            try:
                result['slots'] = audit_art_slots.run(config,
                    [Path(d['_file']) for d in documents],
                    [audit_page_richness.screenshot_of(d) for d in documents])
            except (ValueError, OSError, KeyError, TypeError) as exc:
                result['slots'] = dict(passed=False, error=str(exc))
            passed = passed and result['slots']['passed']
        report = out/'pages.json'
        cmd = [sys.executable, '-B', str(HERE/'audit_page_richness.py'), '--project', str(project),
               '--dumps', str(dumps), '--out', str(report)]
        if board: cmd += ['--board', board]
        if binding: cmd += ['--binding', str(binding)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        (out/'pages.log').write_text(proc.stdout + proc.stderr)
        if proc.returncode not in (0, 1) or not report.exists():
            result['error'] = 'pixel checker did not complete'
            passed = False
        else:
            pages = json.loads(report.read_text())
            # Keep the complete underlying report. A first piece need not supply every
            # project page yet, but its actual problems and setup errors still fail.
            result['pages'] = dict(checked=pages['checked'], setup=pages['setup'],
                findings=[p for p in pages['pages'] if p['problems']],
                remaining_project_purposes=pages['missing'])
            passed = passed and bool(pages['pages']) and not pages['setup'] and not result['pages']['findings']
    result.update(passed=bool(passed), elapsed_seconds=time.monotonic()-started)
    (out/'production-preflight.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))
    return 0 if passed else 1
