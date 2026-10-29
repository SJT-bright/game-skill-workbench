#!/usr/bin/env python3
"""Mobile-input delivery gate. Static checks never certify real device behavior.

Default complete mode fails closed on missing, stale or failed evidence.
Code mode is only an intermediate audit and always reports mobile acceptance pending.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

from verify_native_zip import verify

SOURCE_ROOTS = {'assets', 'settings', '.creator', 'platform', 'build-templates',
                'packages', 'extensions', 'plugins', 'src', 'scripts', 'LICENSES'}
IGNORED = {'library', 'temp', 'build', 'dist', 'profiles', 'node_modules', '.git',
           '__pycache__', '.DS_Store'}
JS = {'.ts', '.js', '.mjs', '.cjs'}
VIEWS = [(375, 812), (390, 844), (393, 852), (412, 915)]
DPRS = [1, 2, 3]
GATES = ['source_geometry', 'native_geometry', 'raw_platform_input',
         'fullscreen_web', 'phone_ios', 'phone_android']
NEGATIVE = ['drag_out', 'cancel', 'second_finger']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def clean_js(source):
    # Preserve offsets and skip regex literals too. A regex containing quotes
    # or // otherwise makes a naive comment regex erase a minified engine.
    out, i, expression = list(source), 0, True
    token = re.compile(r'[A-Za-z_$][\w$]*|\d+(?:\.\d+)?')
    def mask(start, end):
        for j in range(start, end):
            if out[j] != '\n': out[j] = ' '
    while i < len(source):
        char = source[i]
        if char.isspace():
            i += 1; continue
        start = i
        if source.startswith('//', i):
            i = source.find('\n', i)
            if i < 0: i = len(source)
            mask(start, i); continue
        if source.startswith('/*', i):
            end = source.find('*/', i + 2)
            i = len(source) if end < 0 else end + 2
            mask(start, i); continue
        if char in '\"\'`':
            quote = char; i += 1
            while i < len(source):
                if source[i] == '\\': i += 2; continue
                if source[i] == quote:
                    i += 1; break
                i += 1
            mask(start, min(i, len(source))); expression = False; continue
        if char == '/' and expression:
            i += 1; in_class = False
            while i < len(source):
                if source[i] == '\\': i += 2; continue
                if source[i] == '[': in_class = True
                elif source[i] == ']': in_class = False
                elif source[i] == '/' and not in_class:
                    i += 1
                    while i < len(source) and source[i].isalpha(): i += 1
                    break
                elif source[i] == '\n': break
                i += 1
            mask(start, min(i, len(source))); expression = False; continue
        word = token.match(source, i)
        if word:
            value = word.group(); i += len(value)
            expression = value in {'return', 'throw', 'case', 'delete', 'void', 'typeof', 'new', 'yield', 'await', 'instanceof', 'in'}
            continue
        expression = char in '([{:;,=!?&|+*%~^-<>/'
        i += 1
    return ''.join(out)


def blocks(code):
    stack, result = [], []
    for i, char in enumerate(code):
        if char == '{':
            stack.append(i)
        elif char == '}' and stack:
            result.append((stack.pop(), i + 1))
    return sorted(result, key=lambda p: p[1] - p[0])


def risks(name, data, native=False):
    source = data.decode('utf-8-sig')
    code, issues = clean_js(source), []
    regions = blocks(code)
    for token in re.finditer(r'\bgetUILocation\s*\(', code):
        enclosing = [(a, b) for a, b in regions if a <= token.start() < b]
        if not enclosing:
            continue
        # The closest function/block detects the exact former Canvas-offset
        # formula without treating an unrelated input debounce as a hit test.
        a, b = enclosing[0]; fragment = code[a:b]
        if all(term in fragment for term in ('getVisibleSize', 'convertToNodeSpaceAR', 'worldPosition')):
            issues.append({'file': name, 'line': source.count('\n', 0, token.start()) + 1,
                           'rule': 'guessed_ui_canvas_offset_ignores_camera'})
    if native:
        # Restrict this rule to the actual minigame PAL converter, not browser
        # DOM input (where clientX/clientY are correct).
        pattern = re.compile(r'_getLocation\s*=\s*function\s*\([^)]*\)\s*\{')
        for match in pattern.finditer(code):
            a = code.find('{', match.start())
            region = next(((x, y) for x, y in regions if x == a), None)
            if region:
                fragment = code[region[0]:region[1]]
                if '.clientX' in fragment and '.clientY' in fragment and '.height' in fragment and '.screenX' not in fragment:
                    issues.append({'file': name, 'line': source.count('\n', 0, match.start()) + 1,
                                   'rule': 'minigame_pal_client_only_rejects_documented_screen_fields'})
    return issues


def camera_risks(project):
    """Cocos 3.x Canvas hitTest requires a compatible UI projection.

    Only inspect the camera explicitly bound to a Canvas, not unrelated 3D cameras.
    Perspective UI requires separate reviewed ray/plane picking, so stop the default gate.
    """
    issues = []
    for path in (project / 'assets').rglob('*'):
        if path.suffix not in ('.scene', '.prefab'):
            continue
        try:
            objects = json.loads(path.read_text())
        except (ValueError, UnicodeError):
            continue
        if not isinstance(objects, list):
            continue
        for obj in objects:
            if not isinstance(obj, dict) or obj.get('__type__') != 'cc.Canvas':
                continue
            ref = obj.get('_cameraComponent') or {}
            index = ref.get('__id__') if isinstance(ref, dict) else None
            if not isinstance(index, int) or not 0 <= index < len(objects):
                continue
            camera = objects[index]
            if camera.get('__type__') == 'cc.Camera' and camera.get('_projection') == 1:
                issues.append({'file': path.relative_to(project).as_posix(),
                    'rule': 'canvas_perspective_camera_requires_actual_ui_hit_review',
                    'camera_index': index, 'near': camera.get('_near'),
                    'projection': 'Cocos 3.x PERSPECTIVE=1; ORTHO=0'})
    return issues


def snapshot(project):
    if not (project / 'assets').is_dir():
        raise ValueError('Expected a clean Cocos source project with assets/')
    files, code = {}, {}
    for path in sorted(project.rglob('*')):
        rel = path.relative_to(project)
        if any(part in IGNORED for part in rel.parts):
            continue
        if len(rel.parts) > 1 and rel.parts[0] not in SOURCE_ROOTS:
            continue
        if path.is_symlink():
            raise ValueError('Source symlink requires explicit review: ' + str(rel))
        if path.is_file():
            data = path.read_bytes(); files[rel.as_posix()] = digest(data)
            if path.suffix in JS and not path.name.endswith('.d.ts'):
                code[rel.as_posix()] = data
    canonical = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
    return files, code, digest(canonical)


def finite_point(value):
    return isinstance(value, list) and len(value) == 2 and all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in value)


def read_artifact(ref, base, json_data=True):
    if not isinstance(ref, dict) or not isinstance(ref.get('path'), str):
        raise ValueError('Evidence requires path and SHA256, not just a passed flag')
    rel = PurePosixPath(ref['path'])
    if rel.is_absolute() or any(p in ('..', '.') for p in rel.parts) or '\\' in ref['path']:
        raise ValueError('Evidence paths must stay below the review directory')
    path = base / rel
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(base.resolve()):
        raise ValueError('Evidence file missing or outside review directory: ' + ref['path'])
    if file_sha(path) != ref.get('sha256'):
        raise ValueError('Evidence SHA256 mismatch: ' + ref['path'])
    if not path.stat().st_size:
        raise ValueError('Empty evidence file: ' + ref['path'])
    if json_data:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError('Evidence JSON must be an object')
        return value
    return path


def check_geometry(report, controls, binding, gate):
    if report.get('binding') != binding or report.get('gate') != gate:
        raise ValueError('Geometry evidence belongs to another build or gate')
    if report.get('provenance') != 'actual_engine_methods' or report.get('oracle') != 'render_camera_world_to_screen':
        raise ValueError('Use actual engine methods and an independent render projection oracle')
    if report.get('handler_origin') != ('extracted_native_zip' if gate == 'native_geometry' else 'source'):
        raise ValueError('Geometry must execute the correct source/final extracted Native handler')
    coverage = set()
    for c in report.get('cases', []):
        if not isinstance(c, dict):
            raise ValueError('Geometry case must be an object')
        key = (c.get('control'), tuple(c.get('viewport', [])), c.get('dpr'))
        if key in coverage:
            raise ValueError('Duplicate geometry case')
        if c.get('layout') != 'fullscreen' or c.get('inside_hit') is not True or c.get('outside_hit') is not False:
            raise ValueError('Full-screen button hit/outside rejection failed')
        if not finite_point(c.get('screen_point')) or not finite_point(c.get('projected_center')):
            raise ValueError('Geometry contains invalid coordinates')
        if any(abs(a - b) > 1e-5 for a, b in zip(c['screen_point'], c['projected_center'])):
            raise ValueError('Tap point is not the independently projected visible button centre')
        coverage.add(key)
    required = {(c['key'], v, d) for c in controls for v in VIEWS for d in DPRS}
    if not required <= coverage:
        raise ValueError('Missing full-screen viewport/DPR/control geometry cases')
    if report.get('offset_scale_rotation_checked') is not True:
        raise ValueError('Camera viewport and transformed-node boundary case missing')


def check_raw(report, binding):
    if report.get('binding') != binding or report.get('gate') != 'raw_platform_input':
        raise ValueError('Raw-input evidence is stale or mislabelled')
    if report.get('handler_origin') != 'extracted_native_zip':
        raise ValueError('Raw platform events must run through the final Native input adapter and handler')
    required = {'documented_screen_fields', 'client_only_legacy', 'zero_coordinates',
                'touch_end_empty_current', 'multi_touch', 'cancel'}
    seen = set()
    for c in report.get('cases', []):
        if not isinstance(c, dict):
            raise ValueError('Raw input case must be an object')
        name = c.get('case'); seen.add(name)
        if c.get('passed') is not True or not isinstance(c.get('raw_event'), dict):
            raise ValueError('Raw input case failed or original event not retained')
        if name in {'documented_screen_fields', 'client_only_legacy', 'zero_coordinates'}:
            if not finite_point(c.get('mapped_point')) or not finite_point(c.get('expected_point')):
                raise ValueError('Raw touch produced invalid/missing coordinates')
            if any(abs(a-b) > 1e-5 for a,b in zip(c['mapped_point'], c['expected_point'])):
                raise ValueError('Raw input coordinate mapping failed')
            if c.get('pressed_feedback') is not True or type(c.get('callback_count')) is not int or c['callback_count'] != 1:
                raise ValueError('Raw input must reach pressed feedback and one actual callback')
    if not required <= seen:
        raise ValueError('Missing platform field, zero, changedTouches/end, multifinger or cancel cases')


def check_ui(report, controls, binding, gate, base):
    if report.get('binding') != binding or report.get('gate') != gate:
        raise ValueError('UI evidence belongs to another build/gate')
    phone = gate.startswith('phone_')
    expected = 'actual_tiktok_device' if phone else 'actual_cocos_web_input'
    if report.get('provenance') != expected:
        raise ValueError('Synthetic/Mock/internal function calls cannot certify this UI gate')
    if not report.get('reviewer') or report.get('reviewed_recording') is not True:
        raise ValueError('Actual recording/log evidence requires a named reviewer')
    read_artifact(report.get('recording'), base, False)
    env = report.get('environment', {})
    if env.get('layout') != 'fullscreen' or not finite_point(env.get('viewport')) or not finite_point(env.get('canvas_css_size')):
        raise ValueError('Fixed-ratio iframe or missing actual Canvas size is not phone/full-screen evidence')
    if any(abs(a-b) > 2 for a,b in zip(env['viewport'], env['canvas_css_size'])):
        raise ValueError('Canvas must fill the tested viewport; use a separate full-screen test')
    if env['viewport'][1] / env['viewport'][0] < 2 or env.get('dpr') not in DPRS:
        raise ValueError('A tall full-screen viewport and recorded DPR are required')
    if phone and (env.get('physical_device') is not True or env.get('platform') != gate[6:] or not env.get('tiktok_version')):
        raise ValueError('Actual TikTok device, OS scope and client version required')
    if phone and (env.get('runtime_build_tag') != binding['build_tag'] or not env.get('platform_code_version')):
        raise ValueError('Confirm the device loaded this upload version, not only a local filename')
    applicable = [c for c in controls if ('tiktok' if phone else 'web') in c['runtimes']]
    cases = {}
    for c in report.get('cases', []):
        if not isinstance(c, dict):
            raise ValueError('UI case must be an object')
        key = (c.get('control'), c.get('scenario'))
        if key in cases:
            raise ValueError('Duplicate UI case')
        cases[key] = c
    for control in applicable:
        for scenario in ['tap', 'duplicate_end', *NEGATIVE]:
            c = cases.get((control['key'], scenario), {})
            if type(c.get('gameplay_callback_count')) is not int or c['gameplay_callback_count'] != 0:
                raise ValueError('Button/panel gesture reached gameplay or was not measured')
            expected_count = 1 if scenario in ('tap', 'duplicate_end') else 0
            if type(c.get('callback_count')) is not int or c['callback_count'] != expected_count:
                raise ValueError('Missing/duplicated callback or drag/cancel/multifinger activation')
            if scenario == 'tap':
                if c.get('pressed_feedback') is not True or c.get('down_hit') is not True:
                    raise ValueError('No pressed feedback / down hit: ' + control['key'])
                before, after = c.get('before'), c.get('after')
                if not isinstance(before, dict) or not isinstance(after, dict) or before == after:
                    raise ValueError('Tap requires actual before/after state readback')
                if not all(k in after and type(after[k]) is type(v) and after[k] == v for k,v in control['expected_after'].items()):
                    raise ValueError('Tap did not reach the intended state: ' + control['key'])
        if control.get('modal'):
            for scenario in ['backdrop', 'close_reopen', 'late_callback']:
                c = cases.get((control['key'], scenario), {})
                if c.get('passed') is not True or c.get('gameplay_callback_count') != 0 or c.get('unexpected_reward_delta') != 0:
                    raise ValueError('Missing panel isolation/late callback/reward check')


def audit(project, native=None, review=None, stage='complete', build_tag=''):
    files, code, source_sha = snapshot(project)
    errors, native_files, native_sha = [], {}, None
    found = camera_risks(project) + [i for name,data in code.items() for i in risks(name, data)]
    if native:
        structure = verify(native); native_files = structure['file_sha256']; native_sha = structure['sha256']
        with zipfile.ZipFile(native) as z:
            found.extend(i for name in native_files if Path(name).suffix in JS
                         for i in risks(name, z.read(name), True))
    binding = {'source_sha256': source_sha, 'native_zip_sha256': native_sha, 'build_tag': build_tag}
    pending = GATES.copy()
    if found:
        errors.append('Known unsafe hit-test/raw-input pattern present')
    if review:
        data = json.loads(review.read_text()); base = review.parent
        binding['build_tag'] = data.get('binding', {}).get('build_tag', '')
        if data.get('schema') != 1 or data.get('binding') != binding or not binding['build_tag']:
            errors.append('Review binding is missing or stale (source/Native/build tag)')
        else:
            controls = data.get('controls', [])
            try:
                if data.get('inventory_complete') is not True or not controls:
                    raise ValueError('List all actual conditional/permanent controls and review the inventory')
                read_artifact(data.get('inventory_evidence'), base, False)
                keys = set()
                for c in controls:
                    if not isinstance(c, dict) or not c.get('key') or c['key'] in keys:
                        raise ValueError('Control inventory has empty/duplicate keys')
                    keys.add(c['key'])
                    if c.get('source_file') not in files or c.get('native_file') not in native_files:
                        raise ValueError('Control handler source/final Native path missing')
                    if not isinstance(c.get('expected_after'), dict) or not c['expected_after'] or not isinstance(c.get('runtimes'), list) or not c['runtimes'] or not set(c['runtimes']) <= {'web', 'tiktok'}:
                        raise ValueError('Define intended state change and applicable runtime per control')
                if not any('tiktok' in c['runtimes'] for c in controls):
                    raise ValueError('TikTok control inventory cannot be empty')
                for gate in GATES:
                    try:
                        report = read_artifact(data.get('gates', {}).get(gate), base)
                        if gate.endswith('geometry'):
                            check_geometry(report, controls, binding, gate)
                        elif gate == 'raw_platform_input':
                            check_raw(report, binding)
                        else:
                            check_ui(report, controls, binding, gate, base)
                        pending.remove(gate)
                    except (ValueError, OSError, TypeError, KeyError, ZeroDivisionError) as error:
                        errors.append(gate + ': ' + str(error))
            except (ValueError, OSError, TypeError, KeyError) as error:
                errors.append('inventory: ' + str(error))
    if stage == 'complete' and (pending or not native):
        errors.append('Mobile acceptance incomplete: ' + ', '.join(pending))
    blocked = bool(found) or (stage == 'complete' and bool(errors)) or bool(review and errors)
    return {'schema': 1, 'binding': binding, 'stage': stage,
            'status': 'blocked' if blocked else ('static_checks_clear_mobile_pending' if stage == 'code' else 'mobile_review_evidence_complete'),
            'source_files': len(files), 'native_files': len(native_files), 'known_risks': found,
            'pending_gates': pending, 'errors': errors,
            'limits': 'Text rules cannot detect every alias/dynamic transform. Evidence authenticity and inventory completeness require an actual reviewer; this does not certify IAA, upload/review/release or zero future bugs.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('project', type=Path)
    p.add_argument('--native-zip', type=Path)
    p.add_argument('--review', type=Path)
    p.add_argument('--stage', choices=['code', 'complete'], default='complete')
    p.add_argument('--build-tag', default='')
    p.add_argument('--init-review', type=Path)
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    try:
        for path in [a.report, a.init_review]:
            if path and path.exists():
                raise ValueError('Existing evidence is preserved: ' + str(path))
        if a.init_review and (a.review or not a.build_tag):
            raise ValueError('--init-review needs --build-tag and cannot be combined with --review')
        result = audit(a.project, a.native_zip, a.review, a.stage, a.build_tag)
        if a.init_review:
            template = {'schema': 1, 'binding': result['binding'], 'inventory_complete': False,
                        'inventory_evidence': None, 'controls': [], 'gates': {g: None for g in GATES},
                        'required_geometry_viewports': VIEWS, 'required_dprs': DPRS}
            a.init_review.parent.mkdir(parents=True, exist_ok=True)
            a.init_review.write_text(json.dumps(template, ensure_ascii=False, indent=2) + '\n')
        if a.report:
            a.report.parent.mkdir(parents=True, exist_ok=True)
            a.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result['status'] == 'blocked' else 0
    except (ValueError, OSError, TypeError, KeyError, zipfile.BadZipFile) as error:
        print('Mobile input audit failed: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
