"""Early art-only verification using the same production, text, layout and pixel checkers.
Never writes an ART receipt or changes game files. Full art_check still checks
capture provenance, all required pages and all other checks before a trial.
"""
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def _text_preflight(project, dump_files, out):
    """Use the full gate's text measurements, on this first piece only."""
    import audit_text_fit
    started = time.monotonic()
    try:
        fit = audit_text_fit.audit(project, dump_files)
        _write_json(out/'text-fit.json', fit)
        (out/'text-plan.md').write_text(audit_text_fit.plan_markdown(fit), encoding='utf-8')
        return dict(status='completed', passed=bool(fit['passed']) and fit['pages'] > 0,
                    checked=fit['pages'], findings=fit['findings'],
                    report=str(out/'text-fit.json'), plan=str(out/'text-plan.md'),
                    elapsed_seconds=time.monotonic()-started)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        return dict(status='error', passed=False, error=str(exc),
                    elapsed_seconds=time.monotonic()-started)


def _layout_preflight(project, documents, out, board=None, binding=None):
    """Check the real adapter now; never pretend a partial set is full layout coverage."""
    import extract_ui_layout
    import audit_ui_coverage
    started = time.monotonic()
    result = dict(status='not_run', passed=None, geometry_checked=False,
                  remaining=['full-game layout coverage and visual comparison'])
    files = [Path(d['_file']) for d in documents]
    overrides = project/'docs/ui-layout-overrides.json'
    try:
        layout = extract_ui_layout.build(files, overrides if overrides.is_file() else None)
        _write_json(out/'ui-layout.json', layout)
        audit_ui_coverage.verify_provenance(layout)
        by_file = {str(Path(d['_file']).resolve()): d for d in documents}
        errors = []
        for screen in layout['screens']:
            source = by_file[screen['source_dump']['path']]
            if screen.get('error'):
                errors.append(dict(screen=screen['name'], error=screen['error']))
            # purpose is an explicit capture declaration, not a guessed node/page name.
            # A home captured as kind=page otherwise silently loses home geometry.
            for role in ('home', 'gameplay'):
                if source.get('kind') != role and source.get('purpose') != role:
                    continue
                extracted = (screen.get('role') == 'home' and bool(screen.get('buttons'))
                             if role == 'home' else screen.get('kind') == 'gameplay')
                if not extracted:
                    errors.append(dict(screen=screen['name'], error='declared %s was not extracted as %s; '
                                       'fix the capture kind/adapter before collecting the other pages' % (role, role)))
        result['extraction'] = dict(passed=not errors, checked=len(layout['screens']),
                                    errors=errors, report=str(out/'ui-layout.json'))
        if errors:
            result.update(status='failed', passed=False)
            return result
        missing = []
        if not any(s.get('role') == 'home' and s.get('buttons') for s in layout['screens']):
            missing.append('home with runtime buttons')
        if not any(s.get('kind') == 'gameplay' for s in layout['screens']):
            missing.append('gameplay')
        if missing:
            result['remaining'] = missing + result['remaining']
            return result
        report = out/'ui_coverage.json'
        cmd = [sys.executable, '-B', str(HERE/'audit_ui_coverage.py'), str(out/'ui-layout.json'),
               '--project', str(project), '--out', str(report)]
        if board: cmd += ['--board', board]
        if binding: cmd += ['--binding', str(binding)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        (out/'ui_coverage.log').write_text(proc.stdout + proc.stderr, encoding='utf-8')
        if proc.returncode not in (0, 1) or not report.is_file():
            raise RuntimeError('layout checker did not complete; see ui_coverage.log')
        coverage = json.loads(report.read_text(encoding='utf-8'))
        result.update(status='completed', passed=bool(coverage['passed']) and proc.returncode == 0,
                      geometry_checked=True, coverage=coverage)
        return result
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        # Explicit HOME navigation dependencies may be outside this first piece.
        # No geometry verdict is emitted until those real captures are supplied.
        if isinstance(exc, ValueError) and str(exc).startswith('home_entry_pages has no runtime dump: '):
            result['remaining'].insert(0, str(exc))
            return result
        result.update(status='error', passed=False, error=str(exc))
        return result
    finally:
        result['elapsed_seconds'] = time.monotonic()-started


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
        else:
            dump_files = [Path(d['_file']) for d in documents]
            result['text'] = _text_preflight(project, dump_files, out)
            result['layout'] = _layout_preflight(project, documents, out, board, binding)
            passed = passed and result['text']['passed'] and result['layout']['passed'] is not False
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
