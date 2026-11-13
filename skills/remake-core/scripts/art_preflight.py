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


def current_clarity_policy(project, supplied=None):
    from clarity_policy import resolve_policy, validate
    if supplied is None:
        return resolve_policy(project)
    validate({key: supplied[key] for key in ('schema', 'preset', 'min_ratio',
              'background_min_ratio', 'severity')}, 'first-piece clarity policy')
    sources = supplied.get('sources') or {}
    path = supplied.get('policy_path')
    default_path = (Path(project)/'docs/art/clarity-policy.json').resolve()
    kwargs = dict(policy_path=path if path and Path(path).resolve() != default_path else None)
    if any(str(value).startswith('CLI') for value in sources.values()):
        if (any(value == 'CLI preset' for value in sources.values())
                or all(sources.get(key) == 'CLI field' for key in ('min_ratio', 'background_min_ratio', 'severity'))):
            kwargs['cli_preset'] = supplied['preset']
        for key in ('min_ratio', 'background_min_ratio', 'severity'):
            if sources.get(key) == 'CLI field':
                kwargs['cli_'+key] = supplied[key]
    return resolve_policy(project, **kwargs)


def _first_piece_binding(project, dump_files, case_ids, board=None, binding=None, clarity_policy=None):
    """Use existing read-only cache dependency rules; never create capture/ART evidence."""
    import art_analysis_cache
    import audit_art_slots
    import audit_page_richness
    files = [Path(value).resolve() for value in dump_files]
    documents = audit_page_richness.selected_dump_files(
        audit_page_richness.load(sorted({value.parent for value in files})), files)
    documents, selected, remaining = audit_art_slots.first_piece_documents(
        Path(project)/'docs/art/visual-slots.json', documents, case_ids)
    options = dict(scope='first-piece-only', selected_cases=selected, board=board,
                   clarity_policy=current_clarity_policy(project, clarity_policy),
                   binding=(dict(path=str(Path(binding).resolve()), sha256=art_analysis_cache.file_hash(binding))
                            if binding else None))
    cache = art_analysis_cache.PageCache(project, options=options)
    result = dict(schema='art_first_piece_input_binding.v1', scope=options,
                  available=cache.base is not None, source_and_rules_sha256=cache.base,
                  documents=[], checker_sha256={}, receipt_written=False,
                  note='Dependency freshness only; not capture provenance, an ART receipt or visual approval.')
    for doc in documents:
        shot = audit_page_richness.screenshot_of(doc).resolve()
        key = cache.key(doc, shot)
        result['documents'].append(dict(file=str(Path(doc['_file']).resolve()),
            dump_sha256=art_analysis_cache.file_hash(doc['_file']), screenshot=str(shot),
            screenshot_sha256=art_analysis_cache.file_hash(shot), dependency_key=key))
        result['available'] = result['available'] and key is not None
    for name in ('art_preflight.py', 'audit_art_slots.py', 'audit_page_richness.py',
                 'art_analysis_cache.py', 'art_production.py', 'art_check.py', 'clarity_policy.py'):
        result['checker_sha256'][name] = art_analysis_cache.file_hash(HERE/name)
    if not result['available']:
        result['error'] = cache.reason or 'selected evidence has unclosed dependencies or needs a specialized checker'
    return result, cache


def first_piece_input_binding(project, dump_files, case_ids, board=None, binding=None, clarity_policy=None):
    """Public read-only helper for recomputing exactly the first-piece report binding."""
    try:
        result, cache = _first_piece_binding(project, dump_files, case_ids, board, binding, clarity_policy)
        cache.finish()  # No get/put: verifies stability without writing a cache.
        return result
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        return dict(schema='art_first_piece_input_binding.v1', available=False,
                    error=str(exc), receipt_written=False)


def _result_cache_key(report_path, binding):
    import art_analysis_cache as cache
    return cache.sha(cache.encoded(dict(kind='first-piece-result.v1',
        report_sha256=cache.file_hash(report_path), input_binding=binding)))


def sealed_first_piece(project, report_path, dump_files, case_ids, board=None, binding=None, clarity_policy=None):
    """Verify exact current inputs and the tool-owned seal, including failed results."""
    actual, cache = _first_piece_binding(project, dump_files, case_ids, board, binding, clarity_policy)
    cached = cache.get(_result_cache_key(report_path, actual)) if actual.get('available') else None
    cache.finish()
    checked = cached[1].get('report') if cached else None
    if (not isinstance(checked, dict) or checked.get('tool') != 'art_production_preflight'
            or checked.get('input_binding') != actual or checked.get('selected_cases') != list(case_ids)
            or type(checked.get('passed')) is not bool or checked.get('full_art_passed') is not None
            or checked.get('receipt_written') is not False):
        checked = None
    return actual, checked, cache


def seal_first_piece(cache, report_path, checked):
    """Use the existing private analysis cache; this is not an aggregate ART receipt."""
    declared = checked.get('input_binding') or {}
    if declared.get('available') and type(checked.get('passed')) is bool:
        cache.put(_result_cache_key(report_path, declared), [[], dict(report=checked)])
        cache.finish()


def run(project, dumps, out, board=None, binding=None, case_ids=None, *, dump_files=None, clarity_policy=None):
    import art_production
    project, out = Path(project).resolve(), Path(out).resolve()
    clarity_policy = current_clarity_policy(project, clarity_policy)
    if dump_files is not None and case_ids is None:
        raise ValueError('explicit original dump files require first-piece case IDs')
    if case_ids is not None and dumps is None and dump_files is None:
        raise ValueError('first-piece selection requires actual dumps')
    if out.is_relative_to(project) or out.exists() and any(out.iterdir()):
        raise ValueError('use a fresh output directory outside project')
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    has_dumps = dumps is not None or dump_files is not None
    production = art_production.audit(project, require_cases=has_dumps)
    result = dict(tool='art_production_preflight', scope='assets-and-first-integration-only',
                  production=production, runtime_verified=False, receipt_written=False,
                  clarity_policy=clarity_policy)
    if case_ids is not None:
        result.update(selected_cases=[], remaining_cases=[], full_art_passed=None)
    passed = production['passed']
    binding_guard = None
    if not has_dumps and (not production['declared'] or not production['assets']):
        result.update(error='no registered production assets; nothing was checked', status='not_run')
        passed = False
    if has_dumps:
        import audit_page_richness
        folders = sorted({Path(f).resolve().parent for f in dump_files}) if dump_files is not None else [Path(dumps)]
        documents = audit_page_richness.selected_dump_files(audit_page_richness.load(folders), dump_files)
        config = project / 'docs/art/visual-slots.json'
        binding_guard = None
        if case_ids is not None:
            import audit_art_slots
            try:
                documents, selected, remaining = audit_art_slots.first_piece_documents(config, documents, case_ids)
                result.update(selected_cases=selected, remaining_cases=remaining)
                result['input_binding'], binding_guard = _first_piece_binding(
                    project, [d['_file'] for d in documents], case_ids, board, binding, clarity_policy)
                if not result['input_binding']['available']:
                    raise ValueError('first-piece input binding unavailable: ' + result['input_binding']['error'])
            except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
                result.update(error=str(exc), passed=False, elapsed_seconds=time.monotonic()-started)
                _write_json(out/'production-preflight.json', result)
                print(json.dumps(result, ensure_ascii=False))
                return 1
        if not documents:
            result['error'] = 'no captured pages'
            passed = False
        else:
            dump_files = [Path(d['_file']) for d in documents]
            result['text'] = _text_preflight(project, dump_files, out)
            result['layout'] = _layout_preflight(project, documents, out, board, binding)
            passed = passed and result['text']['passed'] and result['layout']['passed'] is not False
        if config.exists():
            import audit_art_slots
            try:
                result['slots'] = audit_art_slots.run(config,
                    [Path(d['_file']) for d in documents],
                    [audit_page_richness.screenshot_of(d) for d in documents], case_ids=case_ids)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                result['slots'] = dict(passed=False, error=str(exc))
            passed = passed and result['slots']['passed']
        report = out/'pages.json'
        cmd = [sys.executable, '-B', str(HERE/'audit_page_richness.py'), '--project', str(project),
               '--dumps', *[str(f) for f in folders], '--out', str(report)]
        if case_ids is not None:
            for doc in documents:
                cmd += ['--dump-file', str(Path(doc['_file']).resolve())]
        if board: cmd += ['--board', board]
        if binding: cmd += ['--binding', str(binding)]
        from clarity_policy import cli_args
        cmd += cli_args(clarity_policy)
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
            result['pages']['visual_reviews'] = audit_page_richness.assembly_visual_reviews(pages)
            result['visual_review_required'] = bool(result['pages']['visual_reviews'])
            passed = passed and bool(pages['pages']) and not pages['setup'] and not result['pages']['findings']
        if binding_guard is not None:
            try:
                binding_guard.finish()
            except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
                result['input_binding'].update(available=False, error=str(exc))
                result['error'] = 'first-piece inputs changed during analysis'
                passed = False
    result.update(passed=bool(passed), elapsed_seconds=time.monotonic()-started)
    report_path = out/'production-preflight.json'
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    if binding_guard is not None:
        try:
            seal_first_piece(binding_guard, report_path, result)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            result['input_binding'].update(available=False, error=str(exc))
            result.update(passed=False, error='first-piece inputs changed before result registration')
            passed = False
            _write_json(report_path, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if passed else 1
