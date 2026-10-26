#!/usr/bin/env python3
"""Opt-in affected-state UI probe. Execute a reviewed runner; never trust report.command/pass."""
from pathlib import Path
import argparse, hashlib, itertools, json, math, subprocess, sys

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / 'ui_contract_trusted_runners.json'
IDENTITY = ('game_run_original', 'renderer_original', 'canvas_get_context_original', 'webgl_context', 'scene_active')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def tree_digest(root):
    rows = {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def rect(value):
    if not isinstance(value, dict):
        raise ValueError('world_rect missing')
    vals = [value.get(k) for k in ('x', 'y', 'width', 'height')]
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in vals) or vals[2] <= 0 or vals[3] <= 0:
        raise ValueError('world_rect must contain finite x/y and positive width/height')
    return vals

def outside(child, parent, tolerance):
    x, y, w, h = child; a, b, c, d = parent
    return x < a-tolerance or y < b-tolerance or x+w > a+c+tolerance or y+h > b+d+tolerance

def intersects(a, b, tolerance):
    return min(a[0]+a[2], b[0]+b[2])-max(a[0], b[0]) > tolerance and min(a[1]+a[3], b[1]+b[3])-max(a[1], b[1]) > tolerance

def slot_rect(spec, viewport):
    x, y, w, h = rect(spec); vx, vy, vw, vh = viewport
    if spec.get('anchor_x') == 'center': x += vx+vw/2
    elif spec.get('anchor_x', 'left') == 'left': x += vx
    else: raise ValueError('unknown anchor_x')
    if spec.get('anchor_y') == 'bottom': y = vy+vh-y-h
    elif spec.get('anchor_y', 'top') == 'top': y += vy
    else: raise ValueError('unknown anchor_y')
    return [x, y, w, h]

def validate(raw, contract, expected_hash, variant, project):
    """Pure evaluator also used by refusal self-tests. Public CLI always runs the pinned collector."""
    errors = []
    def fail(code, detail, state=None, slot=None):
        errors.append(dict(code=code, detail=detail, state=state, slot=slot))
    def visible(obj):
        return isinstance(obj, dict) and obj.get('visible') is True and type(obj.get('effective_opacity')) in (int, float) and math.isfinite(obj['effective_opacity']) and 1 <= obj['effective_opacity'] <= 255
    def evidence(ref, state):
        try:
            p = Path(ref['path']).resolve()
            if not p.is_relative_to(project) or not p.is_file() or sha(p) != ref['sha256']:
                raise ValueError('screenshot missing, outside project or changed')
            if p.stat().st_size < 5000 or not p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('nonempty same-run PNG screenshot required')
        except (KeyError, TypeError, ValueError, OSError) as exc: fail('evidence', str(exc), state)
    if not isinstance(raw, dict): return [dict(code='schema', detail='object report required')]
    if raw.get('schema') != 'ui_contract_runtime.v1' or raw.get('producer') != 'real_browser_ui_contract':
        fail('schema', 'real_browser_ui_contract ui_contract_runtime.v1 required')
    run = raw.get('execution', {})
    if not isinstance(run, dict): return errors+[dict(code='schema', detail='execution object required')]
    if run.get('variant') != variant: fail('binding', 'variant mismatch')
    actual_hash = run.get('native_tree_sha256')
    if run.get('base_native_tree_sha256') != expected_hash: fail('binding', 'base final Native tree mismatch')
    if not isinstance(actual_hash, str) or len(actual_hash) != 64: fail('binding', 'actual Native identity absent')
    elif (variant == 'final') != (actual_hash == expected_hash): fail('binding', 'variant must bind actual final or distinct mutated tree')
    identity = run.get('renderer_identity', {})
    if not isinstance(identity, dict) or not all(identity.get(k) is True for k in IDENTITY):
        fail('renderer', 'original real engine/renderer/Canvas/scene identities required')
    if run.get('errors') != []: fail('runtime', 'runtime errors must be explicit empty array')
    events = run.get('events')
    if not isinstance(events, list) or not events: fail('events', 'actual interaction events required'); events = []
    event_ids = {e.get('id') for e in events if isinstance(e, dict)}
    for name in contract.get('required_events', []):
        if name not in event_ids: fail('events', 'missing required event '+name)
    try: viewport = rect(run.get('viewport'))
    except ValueError as exc: return errors+[dict(code='viewport', detail=str(exc))]
    states = run.get('states')
    if not isinstance(states, list) or not states: return errors+[dict(code='missing_state', detail='states empty or absent')]
    state_ids = [s.get('id') for s in states if isinstance(s, dict)]
    if len(state_ids) != len(set(state_ids)): fail('duplicate_state', 'duplicate state ids')
    tolerance = contract.get('tolerance_px', 1)
    if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or not 0 <= tolerance <= 2:
        return errors+[dict(code='contract', detail='tolerance must be explicit 0..2 CSS px')]
    for state_id, rules in contract['states'].items():
        matching = [s for s in states if isinstance(s, dict) and s.get('id') == state_id]
        if len(matching) != 1: fail('missing_state', 'exactly one affected state required', state_id); continue
        state = matching[0]
        if state.get('modal') != rules['modal']: fail('state', 'actual modal mismatch', state_id)
        evidence(state.get('screenshot', {}), state_id)
        buttons = state.get('buttons')
        if not isinstance(buttons, list) or not buttons: fail('empty_capture', 'target buttons/statuses absent', state_id); continue
        all_content = []
        if not isinstance(rules.get('slots'), dict) or not rules['slots']:
            fail('contract', 'nonempty semantic slots required', state_id); continue
        if any(not isinstance(b, dict) or b.get('slot') not in rules['slots'] for b in buttons):
            fail('undeclared_slot', 'collector entity has no declared affected semantic slot', state_id)
        for slot, policy in rules['slots'].items():
            found = [b for b in buttons if isinstance(b, dict) and b.get('slot') == slot]
            if len(found) != 1: fail('missing_slot', 'exactly one semantic slot required', state_id, slot); continue
            entity = found[0]
            if entity.get('kind') != policy['kind']: fail('kind', 'wrong button/status kind', state_id, slot)
            if not entity.get('id') or not visible(entity): fail('hidden', 'slot empty/hidden or opacity absent', state_id, slot)
            try:
                parent = rect(entity.get('parent', {}).get('world_rect'))
                target = slot_rect(policy['rect'], viewport)
            except ValueError as exc: fail('rect', str(exc), state_id, slot); continue
            sprites, captions = entity.get('sprites'), entity.get('captions')
            if not isinstance(sprites, list) or not isinstance(captions, list):
                fail('empty_capture', 'actual sprite and caption arrays both required', state_id, slot); continue
            if policy.get('require_sprite', policy['kind'] == 'button') and not sprites:
                fail('missing_sprite', 'button has no actual sprite', state_id, slot)
            if policy.get('require_caption', True) and not captions: fail('missing_caption', 'actual caption absent', state_id, slot)
            if not sprites and not captions: fail('empty_capture', 'all content absent', state_id, slot)
            for kind, nodes in [('sprite', sprites), ('caption', captions)]:
                for node in nodes:
                    try: bounds = rect(node.get('world_rect'))
                    except (AttributeError, ValueError) as exc: fail('rect', str(exc), state_id, slot); continue
                    if not visible(node): fail('hidden', kind+' hidden/opacity absent', state_id, slot)
                    if kind == 'sprite':
                        if not node.get('frame') or node.get('loaded') is not True or node.get('texture_loaded') is not True:
                            fail('missing_sprite', 'empty or unloaded actual SpriteFrame/texture', state_id, slot)
                        if policy.get('frames') and node.get('frame') not in policy['frames']:
                            fail('sprite_frame', 'unexpected actual SpriteFrame', state_id, slot)
                    else:
                        if not isinstance(node.get('text'), str) or not node['text'].strip(): fail('missing_caption', 'caption text empty', state_id, slot)
                        fs = node.get('font_size')
                        if type(fs) not in (int, float) or not math.isfinite(fs) or fs < policy.get('min_font_px', 0): fail('font_size', 'actual caption font size absent/too small', state_id, slot)
                    if outside(bounds, viewport, tolerance): fail('viewport_overflow', kind+' outside actual viewport', state_id, slot)
                    if outside(bounds, parent, tolerance): fail('parent_overflow', kind+' outside parent world bounds', state_id, slot)
                    if outside(bounds, target, tolerance): fail('slot_overflow', kind+' outside declared semantic slot', state_id, slot)
                    all_content.append((slot, kind, bounds))
        for first, second in itertools.combinations(all_content, 2):
            if first[0] != second[0] and intersects(first[2], second[2], tolerance):
                fail('cross_slot_overlap', first[0]+'/'+first[1]+' overlaps '+second[0]+'/'+second[1], state_id)
        for tool_id, policy in rules.get('tools', {}).items():
            tools = state.get('tools', {})
            tool = tools.get(tool_id, {}) if isinstance(tools, dict) else {}
            if not isinstance(tool, dict): tool = {}
            if not visible(tool) or tool.get('loaded') is not True or tool.get('texture_loaded') is not True or tool.get('frame') not in policy['frames']:
                fail('missing_tool_sprite', 'semantic tool must display required loaded SpriteFrame/texture; box/Label is insufficient', state_id, tool_id)
            try:
                bounds = rect(tool.get('world_rect'))
                if outside(bounds, viewport, tolerance): fail('viewport_overflow', 'tool outside viewport', state_id, tool_id)
            except ValueError as exc: fail('rect', str(exc), state_id, tool_id)
            if policy.get('click_return_page') and tool.get('click_return_page') != policy['click_return_page']:
                fail('tool_route', 'real tool click/return not observed', state_id, tool_id)
    return errors

def detected_expected(errors, required):
    observed = {e['code'] for e in errors}
    invalid = {'binding', 'renderer', 'schema', 'runner', 'runtime', 'evidence', 'missing_state', 'empty_capture', 'hidden', 'rect', 'missing_slot', 'missing_sprite', 'missing_caption', 'duplicate_state', 'undeclared_slot', 'events', 'contract', 'kind', 'font_size'}
    return bool(required) and set(required) <= observed and not observed.intersection(invalid)

def execute(project, native, contract_path, runner_key, out, variants, calibrate=False):
    project, native, contract_path, out = map(lambda p: Path(p).resolve(), (project, native, contract_path, out))
    registry = json.loads(REGISTRY.read_text()); policy = registry[runner_key]
    if policy['project'] != str(project): raise ValueError('registered project mismatch')
    runner = Path(policy['path']).resolve()
    if not runner.is_file(): raise ValueError('registered runner file missing')
    if not isinstance(policy.get('dependencies'), dict) or not policy['dependencies']: raise ValueError('nonempty reviewed runner dependencies required')
    for path, expected in {str(runner): policy['sha256'], **policy.get('dependencies', {})}.items():
        p = Path(path).resolve()
        if not p.is_relative_to(project) or not p.is_file() or sha(p) != expected: raise ValueError('trusted runner/dependency changed: '+str(p))
    if policy['contract'] != str(contract_path) or sha(contract_path) != policy['contract_sha256']: raise ValueError('reviewed contract missing or changed')
    if not native.is_relative_to(project) or not native.is_dir(): raise ValueError('Native outside registered project')
    contract = json.loads(contract_path.read_text())
    if contract.get('schema') != 'ui_contract.v1' or not isinstance(contract.get('states'), dict) or not contract['states']: raise ValueError('nonempty affected-state contract required')
    timeout = policy['timeout_seconds']
    if type(timeout) is not int or not 1 <= timeout <= 600: raise ValueError('trusted timeout must be 1..600s')
    if any(v not in policy['variants'] for v in variants): raise ValueError('variant not reviewed')
    expected = tree_digest(native); out.mkdir(parents=True, exist_ok=True); results = []
    for variant in variants:
        report_path = out/(variant+'-runtime.json')
        if report_path.exists(): raise ValueError('fresh output required; report already exists')
        argv = [sys.executable, str(runner), '--native', str(native), '--expected-native-hash', expected, '--report', str(report_path), '--contract', str(contract_path), '--variant', variant]
        proc = subprocess.run(argv, cwd=project, shell=False, capture_output=True, text=True, timeout=timeout)
        (out/(variant+'-runner.log')).write_text(proc.stdout+'\n'+proc.stderr)
        raw = json.loads(report_path.read_text()) if report_path.is_file() else {}
        errors = validate(raw, contract, expected, variant, project)
        for source, pinned in {str(runner): policy['sha256'], **policy['dependencies']}.items():
            path = Path(source)
            if not path.is_file() or sha(path) != pinned:
                errors.append(dict(code='binding', detail='trusted source changed during execution: '+str(path)))
        if raw.get('execution', {}).get('runner') != {'path':str(runner), 'sha256':policy['sha256']}:
            errors.append(dict(code='binding', detail='actual collector runner identity differs from reviewed pin'))
        if proc.returncode: errors.append(dict(code='runner', detail='collector process returned '+str(proc.returncode)))
        if tree_digest(native) != expected: errors.append(dict(code='binding', detail='Native changed during execution'))
        result = dict(variant=variant, passed=not errors, errors=errors, runtime_path=str(report_path), runtime_sha256=sha(report_path) if report_path.exists() else None)
        if variant != 'final':
            required = contract.get('calibration', {}).get(variant, [])
            result['detected_expected_defect'] = detected_expected(errors, required)
        results.append(result)
    calibration_ok = calibrate and 'final' in variants and len(variants)>1 and all(r['passed'] if r['variant']=='final' else r.get('detected_expected_defect') for r in results)
    return dict(schema='ui_contract_check.v1', tool='audit_ui_contract', mode='calibration' if calibrate else 'check', native_tree_sha256=expected, contract_sha256=sha(contract_path), registered_runner=runner_key, runner_sha256=policy['sha256'], scope='declared affected states only', executions=results, passed=all(r['passed'] for r in results), calibration_passed=bool(calibration_ok) if calibrate else None)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'native', 'contract', 'out'): ap.add_argument('--'+name, required=True, type=Path)
    ap.add_argument('--runner', required=True)
    ap.add_argument('--variant', default='final')
    ap.add_argument('--calibrate', action='store_true', help='execute final plus registered single-defect controls')
    args = ap.parse_args()
    try:
        variants = ['final']+list(json.loads(args.contract.read_text()).get('calibration', {})) if args.calibrate else [args.variant]
        report = execute(args.project, args.native, args.contract, args.runner, args.out, variants, calibrate=args.calibrate)
    except (ValueError, KeyError, TypeError, AttributeError, OSError, subprocess.TimeoutExpired) as exc:
        report = dict(tool='audit_ui_contract', passed=False, errors=[dict(code='refused', detail=str(exc))])
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'ui-contract-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False)); return 0 if (report.get('calibration_passed') if args.calibrate else report['passed']) else 1

if __name__ == '__main__': sys.exit(main())
