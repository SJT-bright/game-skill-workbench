"""Scoped Cocos 2.4 SDK-field/visible-Retry controls.

This supplements the common actual Native/HOME/touch contract. It does not grant
physical-device acceptance or replace the default loading regression matrix.
"""
import hashlib
import json
import math
from pathlib import Path
import zipfile

PROFILE = 'duo_sdk_ui_retry_v1'
FIXED_SDK_TEST = '("string"==typeof u.SDKVersion&&Number.parseInt(u.SDKVersion.split(".")[0],10)<2)'
BROKEN_SDK_TEST = 'Number.parseInt(u.SDKVersion[0])<2'


def image_recovery_errors(raw, binding, runner_sha=None):
    from startup_business_contract import validate_business
    if not isinstance(raw, dict) or not isinstance(binding, dict):
        return ['image recovery raw/binding must be objects']
    errors = []
    def need(ok, message):
        if not ok:
            errors.append(message)
    need(raw.get('binding') == binding and raw.get('native_tree_sha256') == binding.get('native_tree_sha256'), 'image recovery final Native binding mismatch')
    if runner_sha is not None:
        need(raw.get('runner_sha256') == runner_sha, 'image recovery runner differs')
    need(raw.get('passed') is True and raw.get('home_ready') is True, 'image failure must actually recover HOME')
    need(raw.get('failure_kind') == 'image_decode_error', 'actual image failure boundary required')
    before_errors = raw.get('errors_before')
    need(isinstance(before_errors, list) and bool(before_errors) and any(token in json.dumps(before_errors).lower() for token in ('4930', 'image', 'texture')), 'image failure must contain actual decode/transport error')
    need(raw.get('errors_after') == [] and not raw.get('first_exception'), 'fresh retry still has startup errors')
    need(raw.get('retry_visible') is True and raw.get('retry_group') == 'ui', 'Retry must be visible in the UI camera group')
    need(type(raw.get('attempt_before')) is int and raw['attempt_before'] == 1 and type(raw.get('attempt_after')) is int and raw['attempt_after'] == 2, 'one Retry must create exactly the second attempt')
    before, after = raw.get('request_count_before'), raw.get('request_count_after')
    need(type(before) is int and before >= 1 and type(after) is int and after > before, 'Retry must issue fresh underlying image requests')
    touch = raw.get('retry_touch', {})
    need(isinstance(touch, dict) and touch.get('transport') == 'ego_page_cdp' and touch.get('trusted_touch') is True and type(touch.get('at_ms')) in (int, float) and math.isfinite(touch['at_ms']) and touch['at_ms'] >= 0, 'actual Retry touch required')
    if isinstance(touch, dict) and type(touch.get('at_ms')) in (int, float):
        home_time = raw.get('business', {}).get('home', {}).get('at_ms')
        need(type(home_time) in (int, float) and touch['at_ms'] <= home_time, 'Retry must precede the recovered HOME')
    errors.extend(validate_business(raw))
    return errors


def validate(report, native, binding, project, data, need, ref):
    from audit_native_startup_renderer import tree, digest, sha
    base = tree(native)
    runner_sha = report.get('runner', {}).get('sha256')
    need(report.get('control_profile') == PROFILE, 'Duo scope mismatch')
    need(data.get('home_ready') is True, 'normal HOME observation missing')
    system_info = data.get('observed_system_info')
    need(isinstance(system_info, dict) and 'SDKVersion' not in system_info, 'normal control must actually omit optional SDKVersion')
    for name in ('known_bad', 'reintroduced_defect'):
        path = ref(report.get('controls', {}).get(name, {}), name + ' SDK-field execution')
        if not path:
            continue
        try:
            raw = json.loads(path.read_text())
            root = Path(raw['input_native_root']).resolve()
            need(root.is_relative_to(project.resolve()), name + ' control outside registered project')
            manifest = tree(root)
            need(raw.get('binding') == binding and raw.get('runner_sha256') == runner_sha, name + ' execution binding mismatch')
            need(raw.get('native_tree_sha256') == digest(manifest) and digest(manifest) != digest(base), name + ' Native identity mismatch')
            need(raw.get('passed') is False and raw.get('home_ready') is False and bool(raw.get('errors')), name + ' must actually fail before HOME')
            need(raw.get('failure_kind') == 'missing_sdk_version', name + ' wrong failure kind')
            info = raw.get('observed_system_info')
            need(isinstance(info, dict) and 'SDKVersion' not in info, name + ' SDKVersion was supplied by the host')
            error_text = json.dumps(raw.get('errors', [])).lower()
            need('sdkversion' in error_text or ('reading' in error_text and ('undefined' in error_text or 'null' in error_text)), name + ' actual missing-field exception absent')
            need(raw.get('browser_canvas') == data.get('browser_canvas'), name + ' Canvas calibration differs')
            if name == 'known_bad':
                source = ref(raw.get('source_zip', {}), 'preserved v16 Native ZIP')
                if source:
                    with zipfile.ZipFile(source) as archive:
                        original = {n: hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist() if not n.endswith('/')}
                    need(manifest == original, 'known-bad Native is not the exact preserved ZIP')
            else:
                mutation = raw.get('mutation', {})
                rel = 'adapter-min.js'
                source = (native / rel).read_text()
                need(source.count(FIXED_SDK_TEST) == 1, 'fixed SDK guard boundary changed')
                expected = dict(base)
                expected[rel] = hashlib.sha256(source.replace(FIXED_SDK_TEST, BROKEN_SDK_TEST, 1).encode()).hexdigest()
                need(raw.get('base_native_tree_sha256') == digest(base), 'reintroduced SDK defect has stale final base')
                need(mutation == {'file': rel, 'base_sha256': base[rel], 'mutated_sha256': expected[rel], 'before': FIXED_SDK_TEST, 'after': BROKEN_SDK_TEST}, 'SDK defect mutation is not the exact one-file reintroduction')
                need(manifest == expected, 'SDK defect control changed unrelated files')
        except (KeyError, TypeError, ValueError, OSError, zipfile.BadZipFile) as error:
            need(False, name + ' invalid SDK-field control: ' + str(error))
    image_path = ref(report.get('controls', {}).get('image_recovery', {}), 'actual visible-Retry image recovery')
    if image_path:
        try:
            image = json.loads(image_path.read_text())
            for error in image_recovery_errors(image, binding, runner_sha):
                need(False, error)
            need(image.get('browser_canvas') == data.get('browser_canvas') and image.get('engine_identity') == data.get('engine_identity'), 'image recovery uses a different Canvas/engine')
            need(image.get('phase_order') == ['entry', 'adapter', 'renderer', 'scene'] and image.get('renderer', {}).get('webgl_context') is True, 'image recovery must use actual Native renderer')
        except (TypeError, ValueError, OSError) as error:
            need(False, 'invalid image recovery raw: ' + str(error))


def validate_loading(data, binding, base):
    """Two scoped runs: normal at two phone ratios, actual image failure/Retry.

    Calibration still requires an actual failing SDK-field old/control tree and
    an actual final HOME/play observation. No booleans alone can satisfy it.
    """
    from startup_business_contract import validate_business
    from audit_native_startup_renderer import tree, digest
    errors = []
    def need(ok, message):
        if not ok:
            errors.append('DUO-LOADING: ' + message)
    need(data.get('profile') == PROFILE and data.get('producer') == 'real_browser_touch_trace', 'scoped real-browser producer required')
    need(isinstance(binding, dict) and all(binding.get(k) for k in ('source_sha256', 'native_tree_sha256', 'web_tree_sha256', 'build_tag')), 'complete final binding required')
    need(data.get('binding') == binding and data.get('execution_binding', binding) == binding, 'stale/missing execution binding')
    runner_sha = data.get('runner_sha256')
    need(isinstance(runner_sha, str) and len(runner_sha) == 64, 'actual runner hash required')
    refs = data.get('raw_evidence', [])
    raws = []
    need(isinstance(refs, list) and bool(refs), 'raw evidence missing')
    for ref in refs:
        try:
            path = (base / ref['path']).resolve()
            path.relative_to(base.resolve())
            raw_bytes = path.read_bytes()
            need(bool(raw_bytes) and hashlib.sha256(raw_bytes).hexdigest() == ref.get('sha256'), 'raw evidence changed: ' + str(path))
            raws.append(json.loads(raw_bytes))
        except (KeyError, TypeError, ValueError, OSError) as error:
            need(False, 'invalid raw evidence: ' + str(error))
            raws.append({})
    viewports = data.get('viewports', [])
    need(isinstance(viewports, list) and len(viewports) >= 2 and len({round(v[0]/v[1], 3) for v in viewports if isinstance(v, list) and len(v) == 2 and all(type(n) is int and n > 0 for n in v)}) >= 2, 'two actual phone ratios required for normal control')
    cases = data.get('cases', [])
    def observations(row):
        indexes = row.get('evidence_refs', [])
        valid = isinstance(indexes, list) and bool(indexes) and all(type(i) is int and 0 <= i < len(raws) for i in indexes)
        need(valid, row.get('scenario', '?') + ' invalid evidence indexes')
        return [raws[i] for i in indexes] if valid else []
    normal_rows = [r for r in cases if r.get('scenario') == 'normal_control']
    retry_rows = [r for r in cases if r.get('scenario') == 'explicit_failure']
    need(len(normal_rows) == 1 and len(retry_rows) == 1 and len(cases) == 2, 'exact normal_control and explicit_failure scope required')
    if normal_rows:
        row = normal_rows[0]
        positives = observations(row)
        observed = [raw.get('viewport') for raw in positives]
        need(all(v in observed for v in viewports) and row.get('observed_viewports') == viewports, 'normal phone ratios lack actual observations')
        for raw in positives:
            need(raw.get('binding') == binding and raw.get('native_tree_sha256') == binding.get('native_tree_sha256') and raw.get('runner_sha256') == runner_sha, 'normal final Native/executor mismatch')
            need(raw.get('passed') is True and raw.get('home_ready') is True and raw.get('errors') == [] and not raw.get('first_exception'), 'normal startup failed')
            for error in validate_business(raw):
                need(False, error)
    if retry_rows:
        for raw in observations(retry_rows[0]):
            for error in image_recovery_errors(raw, binding, runner_sha):
                need(False, error)
    calibration = data.get('calibration', {})
    indexes = calibration.get('evidence_refs', [])
    valid = isinstance(indexes, list) and bool(indexes) and all(type(i) is int and 0 <= i < len(raws) for i in indexes)
    need(valid, 'calibration evidence indexes invalid')
    if valid:
        selected = [raws[i] for i in indexes]
        negatives = [r for r in selected if r.get('failure_kind') == 'missing_sdk_version' and r.get('passed') is False and r.get('home_ready') is False and r.get('errors') and r.get('native_tree_sha256') != binding.get('native_tree_sha256')]
        need(bool(negatives), 'actual old SDK-field failure missing')
        for raw in negatives:
            need(raw.get('runner_sha256') == runner_sha, 'calibration executor differs')
            try:
                need(digest(tree(Path(raw['input_native_root']))) == raw.get('native_tree_sha256'), 'calibration negative Native changed')
            except (KeyError, TypeError, ValueError, OSError):
                need(False, 'calibration negative Native identity invalid')
        need(any(r.get('passed') is True and r.get('home_ready') is True and r.get('native_tree_sha256') == binding.get('native_tree_sha256') for r in selected), 'actual fixed HOME calibration missing')
    return errors
