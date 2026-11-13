"""Link deterministic art production to the existing visual-slots declaration.

Records bind inputs, output, exact production rules and intended runtime cases.
They are not visual approvals. Audit replays the original producer and compares
all RGBA pixels; the normal slot checker still verifies real page instances.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[1]
ART = SKILLS / 'remake-art' / 'scripts'
MANIFEST = Path('docs/art/visual-slots.json')
KINDS = {
    'fixed_button': ['compose_fixed_button.py', 'trim_visible.py'],
    'sheet_frame': ['cut_sheet_frame.py'],
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local(project, value, existing=True):
    project = Path(project).resolve()
    value = Path(value)
    candidate = value if value.is_absolute() else project / value
    # Refuse symlink input/output aliases, including intermediate directories.
    if any(p.is_symlink() for p in (candidate, *candidate.parents)):
        raise ValueError('symlink production path is not supported: ' + str(value))
    path = candidate.resolve()
    if not path.is_relative_to(project) or path == project:
        raise ValueError('production path must stay inside project: ' + str(value))
    if existing and not path.is_file():
        raise ValueError('production file missing: ' + str(value))
    return path


def file_record(project, path):
    path = local(project, path)
    return {'file': path.relative_to(Path(project).resolve()).as_posix(), 'sha256': sha(path)}


def declaration_bytes(project):
    """Discover opt-in before applying production-only path restrictions.

    Legacy visual-slots may live behind a directory symlink. Reading a valid
    document with no production_assets must not change those projects' gates.
    An existing but unreadable/malformed document remains an error, not absence.
    """
    path = Path(project).resolve() / MANIFEST
    if not path.exists():
        return None
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('visual-slots must be an object')
    return raw if 'production_assets' in value else None


def read_manifest(project):
    path = local(project, MANIFEST, existing=False)
    if not path.exists():
        return {'cases': []}
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or not isinstance(value.get('cases'), list):
        raise ValueError('visual-slots must contain a cases array')
    if 'production_assets' in value and (not isinstance(value['production_assets'], list) or not value['production_assets']):
        raise ValueError('declared production_assets must be a nonempty array')
    return value


def rule_hashes(kind, parameters=None):
    if kind == 'sheet_frame' and isinstance(parameters, dict) and 'rows_from_bands' in parameters:
        if type(parameters['rows_from_bands']) is not bool:
            raise ValueError('rows_from_bands must be a boolean')
    if kind not in KINDS:
        raise ValueError('unsupported production kind: ' + str(kind))
    paths = [HERE / 'art_production.py', HERE / 'art_usage_budget.py', HERE / 'tiktok_finalize_steps/images.py',
             *(ART / name for name in KINDS[kind])]
    actual = {p.relative_to(SKILLS).as_posix(): sha(p) for p in paths}
    # Only this reviewed release pair may preserve the old default-path binding.
    # The opt-in band extractor and every unknown future edit use actual bytes.
    if kind == 'sheet_frame' and (not isinstance(parameters, (dict, type(None)))
            or (parameters or {}).get('rows_from_bands', False) is not False):
        return actual
    try:
        compat = json.loads((HERE / 'art-default-rules-compat.json').read_text(encoding='utf-8'))
        expected_paths = {'remake-core/scripts/art_production.py',
                          'remake-art/scripts/cut_sheet_frame.py'}
        if (compat.get('schema') != 'art_default_rules_compat.v1'
                or compat.get('scope') != '11.17.11-default-path-only'
                or set(compat.get('files', {})) != expected_paths):
            return actual
        mappings = compat['files']
        for relative in expected_paths:
            pair = mappings[relative]
            if (set(pair) != {'before_sha256', 'after_sha256'}
                    or any(not isinstance(pair[k], str) or len(pair[k]) != 64
                           or any(c not in '0123456789abcdef' for c in pair[k]) for k in pair)
                    or sha(SKILLS / relative) != pair['after_sha256']):
                return actual
        return {key: mappings[key]['before_sha256'] if key in mappings else value
                for key, value in actual.items()}
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return actual


def load_producer(name):
    # Resolve only packaged, fixed names; never import a command from the record.
    path = ART / name
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(ART))
        spec = importlib.util.spec_from_file_location('_art_link_' + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = old_path


def valid_id(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def prepare(project, asset_id, cases, kind, output, spec=None, sheet=None, parameters=None, final_size=None, usage_budget=None):
    project = Path(project).resolve()
    if not valid_id(asset_id) or not isinstance(cases, list) or not cases or not all(valid_id(x) for x in cases) or len(set(cases)) != len(cases):
        raise ValueError('asset id and distinct nonempty expected case ids are required')
    target = local(project, output, existing=False)
    if not target.is_relative_to(project / 'assets'):
        raise ValueError('registered output must be under project/assets')
    record = {'id': asset_id, 'kind': kind, 'expected_cases': cases[:],
              'output': {'file': target.relative_to(project).as_posix()}, 'rules': rule_hashes(kind, parameters)}
    if kind == 'fixed_button':
        recipe = local(project, spec)
        data = json.loads(recipe.read_text(encoding='utf-8'))
        record['recipe'] = file_record(project, recipe)
        record['inputs'] = [file_record(project, recipe.parent / data[k]['file'])
                            for k in ('base', 'word', 'icon') if k in data]
    else:
        record['inputs'] = [file_record(project, sheet)]
        record['parameters'] = dict(parameters or {})
    if record['output']['file'] in [x['file'] for x in record['inputs']] + ([record['recipe']['file']] if 'recipe' in record else []):
        raise ValueError('output must not overwrite a production input')
    document = read_manifest(project)
    check_conflicts(document, record)
    for previous in document.get('production_assets', []):
        if previous['id'] == asset_id:
            record['expected_cases'] = list(dict.fromkeys(previous['expected_cases'] + record['expected_cases']))
            if 'derivations' in previous:
                record['derivations'] = copy.deepcopy(previous['derivations'])
            if usage_budget is None and 'usage_budget' in previous:
                usage_budget = verify_file(project, previous['usage_budget'])
    if usage_budget is not None:
        from art_usage_budget import validate_budget
        budget_path = local(project, usage_budget)
        data = json.loads(budget_path.read_text(encoding='utf-8'))
        if data is None:
            raise ValueError('explicit usage budget cannot be null')
        record['usage'] = validate_budget(data, record['expected_cases'])
        record['usage_budget'] = file_record(project, budget_path)
    if final_size is not None:
        record['derivations'] = [{'op': 'lanczos_downscale', 'size': list(final_size)}]
    return record


def check_conflicts(document, record):
    ids = set()
    for old in document.get('production_assets', []):
        if not isinstance(old, dict) or not valid_id(old.get('id')) or old['id'] in ids:
            raise ValueError('duplicate or malformed production asset id')
        ids.add(old['id'])
        if old['id'] == record['id']:
            if old.get('kind') != record['kind'] or old.get('output', {}).get('file') != record['output']['file']:
                raise ValueError('asset id already belongs to a different output or producer')
        elif old.get('output', {}).get('file') == record['output']['file']:
            raise ValueError('output already belongs to a different asset id')


def verify_file(project, entry):
    if not isinstance(entry, dict) or not isinstance(entry.get('file'), str) or Path(entry['file']).is_absolute():
        raise ValueError('expected a project-relative file record')
    path = local(project, entry['file'])
    if sha(path) != entry.get('sha256'):
        raise ValueError('production bytes changed: ' + entry['file'])
    return path


def replay(project, record):
    from PIL import Image
    kind = record['kind']
    current_rules = rule_hashes(kind, record.get('parameters'))
    original_rules = record.get('rules')
    if (not isinstance(original_rules, dict) or set(original_rules) != set(current_rules)
            or any(not isinstance(value, str) or len(value) != 64
                   or any(char not in '0123456789abcdef' for char in value)
                   for value in original_rules.values())):
        raise ValueError('production rule provenance is missing or malformed')
    # A tool edit invalidates the analysis, not the original artwork. Replay the
    # bound inputs under current rules and compare every output pixel in inspect.
    # Never rewrite the historical rule hashes or ask for regeneration solely
    # because the checker itself changed.
    rule_review = {'original': dict(original_rules), 'current': current_rules,
                   'changed': original_rules != current_rules,
                   'verification': 'current-rule-replay-and-exact-output-comparison'}
    if 'usage_budget' in record:
        from art_usage_budget import validate_budget
        data = json.loads(verify_file(project, record['usage_budget']).read_text(encoding='utf-8'))
        if data is None or validate_budget(data, record['expected_cases']) != record.get('usage'):
            raise ValueError('registered usage budget changed or is incomplete')
    elif 'usage' in record:
        raise ValueError('usage requires its original budget file')
    source_paths = [verify_file(project, x) for x in record['inputs']]
    if kind == 'fixed_button':
        recipe = verify_file(project, record['recipe'])
        data = json.loads(recipe.read_text(encoding='utf-8'))
        expected_paths = [local(project, recipe.parent / data[k]['file']) for k in ('base', 'word', 'icon') if k in data]
        if expected_paths != source_paths:
            raise ValueError('recipe inputs differ from registered inputs')
        expected, boxes = load_producer('compose_fixed_button.py').compose(data, recipe.parent)
        measurements = {'boxes': boxes, 'caption': data['caption']}
    else:
        if len(source_paths) != 1:
            raise ValueError('sheet frame requires one source sheet')
        params = record['parameters']
        for key in ('grid', 'cell'):
            if not isinstance(params.get(key), list) or len(params[key]) != 2 or any(type(x) is not int or x <= 0 for x in params[key]):
                raise ValueError('invalid sheet ' + key)
        producer = load_producer('cut_sheet_frame.py')
        with Image.open(source_paths[0]) as source:
            rgba = source.convert('RGBA')
            expected, cell, bounds = producer.extract(rgba, *params['grid'], *params['cell'], rows_from_bands=params.get('rows_from_bands', False))
            if params.get('fixed_rect') is not None:
                fixed = params['fixed_rect']
                if not isinstance(fixed, list) or len(fixed) != 4 or any(type(x) is not int for x in fixed):
                    raise ValueError('invalid fixed source rectangle')
                expected.close()
                expected = producer.fixed_frame(rgba, cell, fixed)
                bounds = fixed
            rgba.close()
        measurements = {'cell_rect': cell, 'crop_rect': bounds}
    native_size = expected.size
    from clarity_policy import resolve_policy
    expected = apply_derivations(expected, record, clarity_policy=resolve_policy(project), measurements=measurements)
    if 'boxes' in measurements:
        sx, sy = expected.width / native_size[0], expected.height / native_size[1]
        measurements['boxes'] = {name: [b[0]*sx, b[1]*sy, b[2]*sx, b[3]*sy]
                                for name, b in measurements['boxes'].items()}
    measurements['output_size'] = list(expected.size)
    measurements['production_rules'] = rule_review
    return expected, measurements


def inspect(project, record):
    from PIL import Image
    output = verify_file(project, record['output'])
    if not output.is_relative_to(Path(project).resolve() / 'assets'):
        raise ValueError('registered output must be under project/assets')
    expected, measurements = replay(project, record)
    try:
        with Image.open(output) as actual:
            actual_rgba = actual.convert('RGBA')
            try:
                if actual_rgba.size != expected.size or actual_rgba.tobytes() != expected.convert('RGBA').tobytes():
                    raise ValueError('produced output differs from replayed pixels: ' + record['output']['file'])
            finally:
                actual_rgba.close()
        return measurements
    finally:
        expected.close()



def apply_derivations(image, record, clarity_policy=None, measurements=None):
    """Only proportional LANCZOS reductions; never a crop, upsample or lossy encoder."""
    from PIL import Image
    steps = record.get('derivations', [])
    if not isinstance(steps, list) or len(steps) > 16:
        raise ValueError('invalid source image derivations')
    for step in steps:
        if not isinstance(step, dict) or set(step) != {'op', 'size'} or step['op'] != 'lanczos_downscale':
            raise ValueError('unsupported image derivation')
        size = step['size']
        if not isinstance(size, list) or len(size) != 2 or any(type(x) is not int or x <= 0 for x in size):
            raise ValueError('invalid derived size')
        w, h = image.size
        nw, nh = size
        if nw > w or nh > h:
            raise ValueError('source derivation must shrink, never enlarge')
        if (nw, nh) == (w, h):
            continue
        # images.resize_plan uses round/ceil: allow at most one pixel rounding on either axis.
        if abs(nw / w - nh / h) > max(1 / w, 1 / h):
            raise ValueError('source derivation distorts aspect ratio')
        resized = image.resize(tuple(size), Image.Resampling.LANCZOS)
        image.close()
        image = resized
    if 'usage' in record:
        from art_usage_budget import validate_budget, validate_output
        if record['usage'] is None:
            raise ValueError('declared usage cannot be null')
        budget_result = validate_output(validate_budget(record['usage'], record['expected_cases']), image.size,
                                        policy=clarity_policy, background=record.get('background', False))
        if measurements is not None:
            measurements['usage_budget'] = budget_result
    return image


def pending_source_resizes(project, records):
    """Read existing images policy, metadata and static usages; never apply source steps."""
    from PIL import Image
    from tiktok_finalize_steps import images
    project = Path(project).resolve()
    # Function-only import: strictness reads policy, never invokes production audit.
    from art_receipt import strictness
    _, _, policy = strictness(project)
    wanted = {record['output']['file'] for record in records}
    if policy != 'new':
        return {name: {'state': 'legacy_no_source_resize'} for name in wanted}
    overrides, problems = images.load_overrides(project)
    if problems:
        raise ValueError('source image plan invalid: ' + '; '.join(problems))
    wanted = {record['output']['file'] for record in records}
    engine = images.engine_of(project)
    textures = [x for x in images.textures(project, engine) if x['rel'] in wanted]
    usages = images.usages(project, textures)
    options = images.options({'project': project})
    pending = {name: {'state': 'unresolved', 'reason': 'no imported texture metadata; recheck after first page integration'} for name in wanted}
    for texture in textures:
        with Image.open(texture['image']) as actual:
            size, why = images.resize_plan(texture, usages.get(texture['uuid'], {'sprites': [], 'other': []}),
                                            actual.size, options, images.override_for(overrides, texture['rel']))
        pending[texture['rel']] = {'state': 'planned' if size else 'not_planned', 'reason': why}
        if size:
            pending[texture['rel']]['size'] = list(size)
        elif 'unknown' in why or 'not used' in why:
            pending[texture['rel']]['state'] = 'unresolved'
    return pending


def adopt_source_resize(project, asset_id):
    """Accept only an exact replay followed by proportional LANCZOS downscaling.

    This does not write or carry the ART receipt. Affected pages must be recaptured.
    Complete RGBA equivalence also permits lossless byte-only reencoding.
    """
    from PIL import Image
    project = Path(project).resolve()
    document = read_manifest(project)
    matches = [x for x in document.get('production_assets', []) if isinstance(x, dict) and x.get('id') == asset_id]
    if len(matches) != 1:
        raise ValueError('expected one registered production asset: ' + str(asset_id))
    record = copy.deepcopy(matches[0])
    check_conflicts(document, record)
    output = local(project, record['output']['file'])
    expected, _ = replay(project, record)
    try:
        with Image.open(output) as source:
            actual = source.convert('RGBA')
        try:
            if actual.size != expected.size:
                step = {'op': 'lanczos_downscale', 'size': list(actual.size)}
                expected = apply_derivations(expected, {'derivations': [step]})
                record.setdefault('derivations', []).append(step)
            if actual.size != expected.size or actual.tobytes() != expected.convert('RGBA').tobytes():
                raise ValueError('source output is not exact LANCZOS replay or lossless reencoding')
        finally:
            actual.close()
    finally:
        expected.close()
    result = commit(project, record)
    result.update(recapture_required=True, receipt_refreshed=False)
    return result


def commit(project, record):
    """Called only by a successful producer. No passed flag is ever consumed."""
    project = Path(project).resolve()
    record = dict(record, output=file_record(project, record['output']['file']))
    inspect(project, record)
    path = local(project, MANIFEST, existing=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.production.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('another producer is updating visual-slots; retry this command')
    temp = None
    try:
        os.close(fd)
        document = read_manifest(project)
        check_conflicts(document, record)
        records = document.setdefault('production_assets', [])
        for index, previous in enumerate(records):
            if previous['id'] == record['id']:
                # Keep previously declared uses when refreshing the same output.
                record['expected_cases'] = list(dict.fromkeys(previous['expected_cases'] + record['expected_cases']))
                records[index] = record
                break
        else:
            records.append(record)
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
            temp = Path(f.name)
            json.dump(document, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)
    return {'asset_id': record['id'], 'asset_verified': True, 'runtime_verified': False,
            'expected_cases': record['expected_cases'], 'manifest': MANIFEST.as_posix()}


def has_visual_rule(case):
    if not isinstance(case,dict):return False
    if 'display_budget' in case:
        # Reuse the runtime schema: malformed size declarations cannot become a
        # valid production binding merely because an older containment rule exists.
        from audit_art_slots import validate_display_budget
        validate_display_budget(case)
        return True
    return bool((case.get('inside') and case.get('children')) or case.get('horizontal_gap') or case.get('pixel_regions'))


def audit(project, require_cases=True):
    project = Path(project).resolve()
    result = {'schema': 'art_production.v1', 'declared': False, 'passed': True, 'assets': [], 'runtime_verified': False}
    try:
        if declaration_bytes(project) is None:
            return result
        result['declared'] = True
        document = read_manifest(project)
        cases = document['cases']
        case_map = {}
        for case in cases:
            if not isinstance(case, dict) or not valid_id(case.get('id')) or case['id'] in case_map:
                raise ValueError('duplicate or malformed visual case id')
            case_map[case['id']] = case
        for record in document['production_assets']:
            row = {'id': record.get('id') if isinstance(record, dict) else None, 'passed': False}
            try:
                check_conflicts(document, record)
                expected = record['expected_cases']
                if not isinstance(expected, list) or not expected or not all(valid_id(x) for x in expected) or len(set(expected)) != len(expected):
                    raise ValueError('missing or duplicate expected runtime cases')
                row['measurements'] = inspect(project, record)
                if require_cases:
                    for name in expected:
                        case = case_map.get(name)
                        if not has_visual_rule(case):
                            raise ValueError('runtime case missing or has no visual rule: ' + name)
                row['passed'] = True
            except (OSError, ValueError, KeyError, TypeError, IndexError, ImportError) as exc:
                row['error'] = str(exc)
            result['assets'].append(row)
        pending = pending_source_resizes(project, document['production_assets'])
        for row, record in zip(result['assets'], document['production_assets']):
            future = pending.get(record['output']['file'])
            row['source_resize_plan'] = future
            if future and future.get('size'):
                row.update(passed=False, pending_source_resize=future, error=(
                    'source image plan will resize this asset to %s; rerun the same producer with --final-size %s %s '
                    'before the first full art check, keeping final frame geometry correct; '
                    'if images already resized it, use --adopt-source-resize %s; recapture affected pages'
                    % (future['size'], *future['size'], record['id'])))
        result['passed'] = all(x['passed'] for x in result['assets'])
    except (OSError, ValueError, KeyError, TypeError, IndexError, ImportError) as exc:
        result.update(passed=False, error=str(exc))
    return result


def fingerprint(project):
    """Read-only receipt dependency binding; never a substitute for audit().

    No production declaration returns None, retaining legacy receipt behavior.
    Existing declarations bind the raw manifest and actual input/output/rule bytes.
    Missing or malformed dependencies cannot be refreshed into a valid receipt.
    """
    project = Path(project).resolve()
    try:
        raw = declaration_bytes(project)
        if raw is None:
            return None
        path = local(project, MANIFEST)
        # Reuse format validation but do not rerun image generation or pixel analysis.
        document = read_manifest(project)
        cases = {}
        for case in document['cases']:
            if not isinstance(case, dict) or not valid_id(case.get('id')) or case['id'] in cases:
                raise ValueError('duplicate or malformed visual case id')
            cases[case['id']] = case
        records = []
        for record in document['production_assets']:
            check_conflicts(document, record)
            expected = record['expected_cases']
            if not isinstance(expected, list) or not expected or not all(valid_id(x) for x in expected) or len(set(expected)) != len(expected):
                raise ValueError('missing or duplicate expected runtime cases')
            for name in expected:
                case = cases.get(name)
                if not has_visual_rule(case):
                    raise ValueError('runtime case missing or has no visual rule: ' + name)
            inputs = record['inputs']
            if not isinstance(inputs, list) or not inputs:
                raise ValueError('production input records missing')
            bound = {'id': record['id'], 'kind': record['kind'],
                     'rules': rule_hashes(record['kind'], record.get('parameters')),
                     'inputs': [file_record(project, verify_file(project, entry)) for entry in inputs],
                     'output': file_record(project, verify_file(project, record['output']))}
            if 'usage_budget' in record:
                bound['usage_budget'] = file_record(project, verify_file(project, record['usage_budget']))
            if record['kind'] == 'fixed_button':
                bound['recipe'] = file_record(project, verify_file(project, record['recipe']))
            if not local(project, bound['output']['file']).is_relative_to(project / 'assets'):
                raise ValueError('registered output must be under project/assets')
            records.append(bound)
        # A concurrent editor must not bind parsed new declarations with old raw bytes.
        if path.read_bytes() != raw:
            raise ValueError('production declaration changed while fingerprinting')
        payload = {'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'assets': records}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                           ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        return {'schema': 'art_production_binding.v1', 'sha256': digest, 'assets': len(records)}
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        raise ValueError('production binding invalid: ' + str(exc)) from exc


def add_arguments(parser):
    parser.add_argument('--project', type=Path, help='register production inputs and required page cases in this project')
    parser.add_argument('--asset-id', help='stable production asset id; requires --project and --cases')
    parser.add_argument('--cases', nargs='+', help='required visual-slots case ids for every affected state/viewport')
    parser.add_argument('--usage-budget', type=Path, help='complete per-case CSS usage budget JSON inside project; bound to production')
    parser.add_argument('--final-size', type=int, nargs=2, metavar=('W', 'H'),
                        help='registered final proportional LANCZOS size; needs --project/--asset-id/--cases')


def requested(args, parser):
    values = (args.project, args.asset_id, args.cases)
    if (args.final_size or args.usage_budget) and not all(values):
        parser.error('--final-size/--usage-budget require registered production arguments')
    if any(values) and not all(values):
        parser.error('--project, --asset-id and --cases must be supplied together')
    return all(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--assets-only', action='store_true', help='check producer output only; does not approve runtime display')
    parser.add_argument('--adopt-source-resize', metavar='ASSET_ID', help='bind only exact lossless/LANCZOS derivation; does not refresh ART receipt')
    args = parser.parse_args()
    if args.adopt_source_resize:
        try:
            result = adopt_source_resize(args.project, args.adopt_source_resize)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except (OSError, ValueError, KeyError, TypeError) as exc:
            parser.exit(1, 'source derivation refused: ' + str(exc) + '\n')
    result = audit(args.project, require_cases=not args.assets_only)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
