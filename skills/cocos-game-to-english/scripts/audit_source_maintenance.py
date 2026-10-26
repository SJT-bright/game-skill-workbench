"""Acceptance for explicitly scoped maintenance of a previously delivered source game.

This profile preserves approved assets and runs existing-game regressions. It is
not new-game/remake acceptance. Loading, storage, raw evidence and writer checks
remain compulsory. Unsupported/missing execution evidence fails closed.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    return json.loads(Path(p).read_text())

def audit(args):
    from audit_mobile_input import snapshot
    from check_known_issues import tree_sha, auto_reports
    from audit_page_readiness import validate as validate_pages, scan
    from audit_runtime_coverage import verify as validate_coverage
    r = read(args.review)
    root, native, web = args.project.resolve(), args.native.resolve(), args.web.resolve()
    base, errors = args.review.parent, []
    criteria_scope_report = None
    def need(ok, message):
        if not ok:
            errors.append(message)
    def ref(record):
        p = Path(record['path'])
        if not p.is_absolute():
            p = base / p
        need(p.is_file() and sha(p) == record.get('sha256'), 'Missing/changed maintenance evidence: '+str(p))
        return p
    need(r.get('schema') == 'source_maintenance_review.v1', 'Maintenance schema')
    need(r.get('authorization') == 'explicit_existing_game_scope', 'Explicit existing-game maintenance authorization required')
    auth = ref(r.get('authorization_evidence', {}))
    need(len(auth.read_text()) > 80, 'Actual authorization and scope record required')
    expected = dict(source_sha256=snapshot(root)[2], native_tree_sha256=tree_sha(native), web_tree_sha256=tree_sha(web), build_tag=args.build_tag)
    def verdict():
        return dict(tool='audit_source_maintenance', status='blocked' if errors else 'passed', passed=not errors, binding=expected, errors=errors, criteria_scope=criteria_scope_report, scope='Explicit existing-game source maintenance; preserved assets and level rules, actual source/Native business, storage, runtime loading/pages/audio/visual checks; not full remake or physical TikTok acceptance')
    need(r.get('binding') == expected, 'Source/Web/Native/build binding changed')
    try:
        from maintenance_criteria_scope import evaluate as evaluate_criteria_scope
        criteria_scope_report = evaluate_criteria_scope(r.get('criteria_scope'), root, expected, base)
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        need(False, 'criteria-level scope invalid: ' + str(exc))
    previous = Path(r['baseline_project']).resolve()
    need(previous != root and (previous/'project.json').is_file(), 'Previously delivered editable baseline required')
    baseline_zip = ref(r['baseline_zip'])
    need(baseline_zip.suffix.lower() == '.zip', 'Historical delivered package required')
    baseline_native = Path(r['baseline_native']).resolve()
    baseline_binding = read(ref(r['baseline_binding']))
    need(baseline_binding.get('source_sha256') == snapshot(previous)[2] and baseline_binding.get('native_tree_sha256') == tree_sha(baseline_native), 'Historical source/Native binding changed')
    import verify_native_zip
    original_zip = verify_native_zip.verify(baseline_zip, r['app_id'])
    original_tree = {str(p.relative_to(baseline_native)):sha(p) for p in baseline_native.rglob('*') if p.is_file() and p.name != '.DS_Store'}
    need(original_zip['file_sha256'] == original_tree, 'Historical package does not match preserved Native baseline')
    now_tree = {str(p.relative_to(native)):sha(p) for p in native.rglob('*') if p.is_file() and p.name != '.DS_Store'}
    native_changes = sorted(k for k in set(original_tree)|set(now_tree) if original_tree.get(k) != now_tree.get(k))
    need(native_changes == sorted(r.get('reviewed_native_changes', [])), 'Unreviewed Native delta')
    need(set(native_changes) <= {'assets/main/index.js','game.js','cocos/cocos2d-js-min.js'}, 'Unsupported Native delta: preserve loader/resources or calibrate a new production profile')
    if 'game.js' in native_changes:
        need((baseline_native/'game.js').read_text().rstrip() == (native/'game.js').read_text().rstrip(), 'Unexpected Native bootstrap behavior change')
    if 'cocos/cocos2d-js-min.js' in native_changes:
        engine = r['native_engine_execution']
        engine_runner = ref(engine['runner'])
        engine_report = ref(engine['raw'])
        prior = read(engine_report)
        command = engine['command']
        need(str(engine_runner) in command, 'Native engine review runner missing')
        run = subprocess.run(command,capture_output=True,text=True,timeout=60)
        need(run.returncode == 0 and prior == read(engine_report) and prior.get('passed') is True and prior.get('current_sha256') == sha(native/'cocos/cocos2d-js-min.js') and prior.get('baseline_sha256') == sha(baseline_native/'cocos/cocos2d-js-min.js'), 'Native engine delta not independently verified')
    def sources(p):
        return {str(f.relative_to(p)):sha(f) for folder in ['assets','build-templates','settings'] for f in sorted((p/folder).rglob('*')) if f.is_file() and f.name != '.DS_Store'}
    old, current = sources(previous), sources(root)
    need(bool(old) and bool(current), 'Source baseline empty')
    changed = sorted(k for k in set(old)|set(current) if old.get(k) != current.get(k))
    need(changed == sorted(r.get('reviewed_source_changes', [])) and bool(changed), 'Unreviewed source/asset changes')
    need(set(changed) <= {'assets/scripts/Progression.js','assets/scripts/SockDrawerApp.js','build-templates/web-mobile/index.html'}, 'Unsupported source changes for this calibrated loading/storage protocol')
    need(not any(k.startswith('assets/resources/') for k in changed), 'This preservation profile cannot authorize art/audio/level replacement')
    for item in r.get('checks', {}).values():
        need(item.get('status') == 'pass' and len(item.get('observed', '')) > 30, 'Maintenance observation missing or failed')
    required = {'LOAD-01','LOAD-03','STORAGE-01','BUSINESS','PAGES','NORMAL','AUDIO','VISUAL','COVERAGE','SCOPE','ENGLISH'}
    need(set(r.get('checks', {})) == required, 'Missing maintenance check domains')
    english = r.get('checks', {}).get('ENGLISH', {})
    need(isinstance(english.get('evidence'), list) and bool(english.get('evidence')), 'Current English coverage and rendered-text evidence required')
    for entry in english.get('evidence', []):
        try:
            evidence = read(ref(entry))
            if isinstance(evidence, dict) and evidence.get('binding') is not None:
                need(evidence.get('binding') == expected, 'English evidence belongs to another build')
        except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
            need(False, 'invalid English evidence: ' + str(exc))
    if errors:
        return verdict()
    # auto_tools is catalog-driven; use the real catalog entry, including its
    # current policy and replay checks, rather than a parallel relaxed validator.
    catalog = read(HERE.parent/'assets/known-issues.json')
    for ident in ['LOAD-03','STORAGE-01']:
        item = next(x for x in catalog['items'] if x['id'] == ident)
        auto_reports(item,r['checks'].get(ident,{}),base,errors,expected)
    if errors:
        return verdict()
    # Startup freezes need rendered frames, not a stamped loading verdict.
    startup_plan_file = ref(r['startup_plan'])
    startup_reports = [ref(x) for x in r['startup_runs']]
    need(bool(startup_reports), 'Startup timing raw reports missing')
    for raw_path in startup_reports:
        raw = read(raw_path)
        need(raw.get('binding') == expected, 'Startup run belongs to another candidate')
        frame_root = Path(raw.get('recording',{}).get('dir','')).resolve()
        need(frame_root.is_dir() and frame_root.is_relative_to(raw_path.parent.resolve()), 'Startup frames must stay with their actual run')
    startup_verdicts = [read(ref(x)) for x in r['checks']['LOAD-03']['auto_reports']]
    startup_verdict = next((x for x in startup_verdicts if x.get('tool') == 'audit_startup_loading'), {})
    # The shared auto_reports validator above already reopens all pixels and
    # enforces the current startup policy. Match this review to that exact set.
    need(startup_verdict.get('plan_file') == str(startup_plan_file.resolve()), 'Review references another startup plan')
    need(set(startup_verdict.get('raw_reports',{})) == {str(p.resolve()) for p in startup_reports}, 'Review startup matrix differs from validated manifest')
    if errors:
        return verdict()
    page_plan = read(ref(r['page_plan']))
    page_file = ref(r['page_runtime'])
    page = read(page_file)
    page_errors, count, _ = validate_pages(page_plan,page,expected,page_file.parent)
    errors += ['LOAD-01: '+e for e in page_errors]
    need(not scan(root)[0], 'Unresolved page-readiness source risks')
    need(page_plan.get('scope') == 'full_existing_game' and count >= 210, 'Full existing-game route inventory and two-viewport matrix required for this calibrated profile')
    normal = read(ref(r['normal_runtime']))
    need(normal.get('binding') == expected and normal.get('passed') is True, 'Current normal-control runtime missing/failed')
    need(len(normal.get('episodes', [])) >= 2 and normal.get('saveBefore') and normal.get('saveAfter'), 'Cold start, earned save and reload evidence required')
    coverage_file = ref(r['runtime_coverage'])
    errors += validate_coverage(read(coverage_file),{'source':root/'assets','native':native,'web':web},coverage_file.parent)
    # Execute the same actual source/compiled Native business harness. The
    # signed case inventory cannot be reduced or relabelled after execution.
    business = r['business_execution']
    runner = ref(business['runner'])
    raw = ref(business['raw'])
    command = business['command']
    need(str(runner) in command and any(str(native) in p for p in command), 'Actual final Native business command required')
    before = read(raw)
    proc = subprocess.run(command,capture_output=True,text=True,timeout=120)
    need(proc.returncode == 0, 'Actual business regression failed')
    after = read(raw)
    need(before == after, 'Business execution differs from signed raw report')
    rows = after.get('cases', [])
    need(after.get('schema') == 'sock_reward_audit.v1' and len(rows) >= 126 and after.get('failed') == 0 and bool(rows) and all(c.get('passed') is True for c in rows), 'Business cases failed/missing')
    need({c.get('mode') for c in rows} == {'source','native'}, 'Business suite must execute source and compiled Native')
    actual_ids = sorted(str(c.get('mode'))+':'+str(c.get('id')) for c in rows)
    need(actual_ids == sorted(business.get('required_cases', [])) and len(actual_ids) >= 2, 'Business case inventory changed')
    need(after.get('input',{}).get('native',{}).get('sha256') == sha(native/'assets/main/index.js'), 'Business suite targeted another Native bundle')
    need(after.get('input',{}).get('test_tool_sha256') == sha(runner), 'Business runner identity changed')
    source_targets = after.get('input',{}).get('source',{})
    need(bool(source_targets), 'Actual production source targets missing')
    for name, digest in source_targets.items():
        need(sha(root/'assets/scripts'/(name+'.js')) == digest, 'Business source target changed: '+name)
    supplements = r.get('business_supplements', [])
    minimum = {'sock_mechanism_supplement.v1':196, 'sock_native_bridge_boundary.v1':6, 'sock_delivery_boundary_supplement.v1':6}
    seen = set()
    for entry in supplements:
        extra_runner, extra_raw = ref(entry['runner']), ref(entry['raw'])
        before = read(extra_raw)
        schema = before.get('schema')
        need(schema in minimum and schema not in seen, 'Unsupported/duplicate supplemental business protocol')
        seen.add(schema)
        command = entry['command']
        need(str(extra_runner) in command and str(native/'assets/main/index.js') in command, 'Supplement must execute actual final compiled Native')
        execution = subprocess.run(command,capture_output=True,text=True,timeout=120)
        after = read(extra_raw)
        need(execution.returncode == 0 and before == after, 'Supplemental execution failed or differs from signed result')
        cases = after.get('cases', [])
        need(after.get('failed') == 0 and len(cases) >= minimum.get(schema, 10**9) and all(c.get('passed') is True for c in cases), 'Supplemental cases missing/failed')
        target = after.get('input',{}).get('native',after.get('input',{}).get('native_bundle',{}))
        need(target.get('sha256') == sha(native/'assets/main/index.js'), 'Supplement targeted another Native bundle')
    need(seen == set(minimum), 'Full existing-game mechanisms/bridge/persistence supplements required')
    audio = read(ref(r['audio_runtime']))
    need(audio.get('binding') == expected and audio.get('passed') is True and audio.get('decodedClips',0) > 0 and audio.get('musicPlaying') is True, 'Actual current audio decode/play evidence required')
    audio_raw = read(ref(audio['raw_runtime']))
    episode = audio_raw.get('episode',{})
    need(audio_raw.get('binding') == expected and audio_raw.get('passed') is True and episode.get('final',{}).get('placements',0) > 0 and episode.get('audio',{}).get('decodedClips') == audio.get('decodedClips') and episode.get('audio',{}).get('musicPlaying') is True and bool(episode.get('actions')), 'Audio raw interaction/decode trace missing or stale')
    visual = read(ref(r['visual_review']))
    need(visual.get('binding') == expected and visual.get('reviewer') == 'codex' and visual.get('passed') is True and len(visual.get('observed','')) > 50, 'Current Codex visual review required')
    for evidence in visual.get('evidence', []):
        ref(evidence)
    need(bool(visual.get('evidence')), 'Visual frames missing')
    if args.stage == 'post_package':
        import verify_native_zip
        refusal = read(ref(r['writer_refusal']))
        need(refusal.get('binding') == expected and refusal.get('passed') is True and refusal.get('review_restored') is True, 'Actual current writer refusal proof required')
        need({'missing_review','failed_check','stale_binding','missing_storage','normal'} <= {c.get('id') for c in refusal.get('checks',[]) if c.get('passed') is True}, 'Writer rejection matrix incomplete')
        for entry in refusal.get('writer_files',[]):
            ref(entry)
        package = ref(r['package'])
        checked = verify_native_zip.verify(package,r['app_id'])
        actual = {str(p.relative_to(native)):sha(p) for p in native.rglob('*') if p.is_file() and p.name != '.DS_Store'}
        need(checked['file_sha256'] == actual, 'Delivered ZIP differs from final Native tree')
    if args.stage == 'device':
        errors.append('Maintenance profile does not attest physical TikTok acceptance')
    return verdict()
