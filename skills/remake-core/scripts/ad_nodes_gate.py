"""Read-only six-standard-family gate shared by formal trials and package writers.

The caller decides whether this production policy applies. There is no bypass
flag here. A formal trial needs current wiring and scoped UI evidence; a writer
also needs current runtime observations bound to the exact Native being packed.
The gate reads the existing lightweight art record and affected-case checker;
it does not replay a full art audit or revive aggregate image receipts.
"""
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[1]
STANDARD = ('end', 'home', 'skin', 'energy', 'in_run_item', 'trial')
MODEL = 'strict_six_standard_families'
ROLE_ALIASES = {'result_double': 'double', 'wheel': 'spin', 'skin_unlock': 'skin',
                'energy_refill': 'energy', 'item_refill': 'booster_refill'}
ART_INSTRUCTIONS = ('SKILL.md', 'references/saul-art-rules.md', 'references/style-limits.md',
                    'references/artwork-and-feedback.md', 'references/new-feature-ui.md',
                    'references/production-prevention.md', 'references/ui-style-and-samples.md')


def _module(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError('required same-bundle tool missing: ' + str(path))
    name = '_ad_fusion_' + hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    previous = list(sys.path)
    try:
        sys.path.insert(0, str(path.parent))
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = previous
    return module


def _json(path):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate JSON key: ' + key)
            out[key] = value
        return out
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs)


def _local(project, name, *, directory=False):
    if not isinstance(name, str) or not name or Path(name).is_absolute() or '\\' in name:
        raise ValueError('expected project-relative POSIX path: ' + str(name))
    path = (project / name).resolve()
    if not path.is_relative_to(project) or path == project:
        raise ValueError('path escapes project or names project root: ' + name)
    if directory and not path.is_dir():
        raise ValueError('directory missing: ' + name)
    if not directory and not path.is_file():
        raise ValueError('file missing: ' + name)
    return path


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ids(value, label):
    if (not isinstance(value, list) or not value or
            any(not isinstance(x, str) or not x.strip() for x in value) or len(set(value)) != len(value)):
        raise ValueError(label + ' must be a nonempty list of distinct IDs')
    return value


def _game_js(member):
    parts = PurePosixPath(member).parts
    lower = {x.lower() for x in parts}
    if not member.lower().endswith('.js') or lower.intersection({'qa', 'docs', 'test', 'tests', 'node_modules', 'cocos-js'}):
        return False
    return not re.search(r'(^|/)(?:cocos2d-js(?:-min)?|physics(?:-min)?|adapter(?:-min)?|web-adapter|engine-adapter|'
                         r'system\.bundle|polyfills(?:\.bundle)?|.*adapter)\.js$', member, re.I)


def _native_binding(project, runtime, native, files):
    base = _local(project, runtime.get('build_directory'), directory=True)
    if native is None and files is None:
        raise ValueError('writer requires the actual Native directory or exact package files')
    if native is not None and Path(native).resolve() != base:
        raise ValueError('runtime build_directory is not the Native selected by this writer')
    if files is not None and not isinstance(files, dict):
        raise ValueError('package files must map Native-relative paths to bytes')
    artifacts = runtime.get('build_artifacts')
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError('runtime build_artifacts is empty')
    members = []
    for ref in artifacts:
        if not isinstance(ref, dict):
            raise ValueError('invalid runtime build artifact')
        path = _local(project, ref.get('path'))
        if not path.is_relative_to(base):
            raise ValueError('runtime artifact is outside declared Native: ' + ref['path'])
        member = path.relative_to(base).as_posix()
        expected = ref.get('sha256')
        if not isinstance(expected, str) or _sha(path) != expected:
            raise ValueError('runtime Native artifact hash changed: ' + member)
        if files is not None:
            actual = files.get(member)
            if not isinstance(actual, bytes) or hashlib.sha256(actual).hexdigest() != expected:
                raise ValueError('runtime artifact differs from exact package member: ' + member)
        members.append(member)
    if not any(_game_js(member) for member in members):
        raise ValueError('runtime needs at least one actual game build JS, not QA/docs/engine/adapter')
    return {'passed': True, 'build_directory': base.relative_to(project).as_posix(),
            'matched_members': members, 'boundary': 'Only runtime-declared Native members are compared; no full image fingerprint replay.'}


def _prepare_context(project, ref):
    if ref is None:
        raise ValueError('UI production_context from the owning art Skill is required before production')
    if not isinstance(ref, dict):
        raise ValueError('ui.production_context must be a file reference')
    path = _local(project, ref.get('path'))
    if _sha(path) != ref.get('sha256'):
        raise ValueError('UI preparation context file changed')
    data = _json(path)
    if (not isinstance(data, dict) or data.get('schema') != 'adboost_art_context.v1'
            or data.get('context_ready') is not True or data.get('problems')):
        raise ValueError('UI preparation context is not ready')
    if Path(data.get('project', '')).resolve() != project:
        raise ValueError('UI preparation context belongs to another project')
    if data.get('board') not in ('localize', 'remake'):
        raise ValueError('UI preparation context has no resolved production board')
    owning = SKILLS / 'remake-art'
    recorded_root = Path((data.get('remake_art') or {}).get('root', ''))
    docs = data.get('documents')
    if not isinstance(docs, list) or not docs:
        raise ValueError('UI preparation context has no owning art instructions')
    seen = set()
    for doc in docs:
        if not isinstance(doc, dict) or not isinstance(doc.get('path'), str):
            raise ValueError('invalid prepared art instruction reference')
        original = Path(doc['path'])
        if not original.is_relative_to(recorded_root):
            raise ValueError('prepared art instruction is outside its owning Skill')
        current = owning / original.relative_to(recorded_root)
        if not current.is_file() or _sha(current) != doc.get('sha256'):
            raise ValueError('owning art instructions changed: ' + str(current))
        seen.add(original.relative_to(recorded_root).as_posix())
    missing = set(ART_INSTRUCTIONS) - seen
    if missing:
        raise ValueError('UI preparation omitted owning art instructions: ' + ', '.join(sorted(missing)))
    styles = data.get('style_sources')
    if not isinstance(styles, list) or not styles:
        raise ValueError('UI preparation context has no real game style reference')
    for style in styles:
        if not isinstance(style, dict) or style.get('kind') not in ('art_direction', 'original_reference', 'game_reference'):
            raise ValueError('UI preparation has no supported real game style source')
        path = Path(style.get('path', ''))
        if not path.is_file() or _sha(path) != style.get('sha256'):
            raise ValueError('game style source changed since preparation: ' + str(path))
        if style['kind'] == 'art_direction':
            if (data['board'] != 'remake' or path.name != 'ART_DIRECTION.md'
                    or not path.resolve().is_relative_to(project)
                    or not path.read_text(encoding='utf-8').strip()):
                raise ValueError('ART_DIRECTION must be a nonempty remake style source')
        else:
            from PIL import Image
            with Image.open(path) as image:
                image.load()
                if list(image.size) != style.get('pixels'):
                    raise ValueError('prepared style reference pixel dimensions changed')
    if data['board'] == 'localize' and not any(x['kind'] == 'original_reference' for x in styles):
        raise ValueError('English UI preparation must include an actual original-game image reference')
    return {'context_ready': True, 'path': ref['path'], 'boundary': 'Preparation is not visual approval.'}


def _ui_mapping(project, manifest):
    config = manifest.get('ui')
    if not isinstance(config, dict):
        raise ValueError('ad-node manifest needs ui with existing export, dumps and first-piece references')
    paths = {key: str(_local(project, config.get(key), directory=key != 'first_piece_report'))
             for key in ('web_export', 'dumps', 'first_piece_report')}
    pages_path = _local(project, 'docs/logic/pages.json')
    pages = _json(pages_path)
    screens = _json(_local(project, 'docs/art/screens.json'))
    visual = _json(_local(project, 'docs/art/visual-slots.json'))
    capture = _json(_local(project, 'docs/art/capture-plan.json'))
    if not isinstance(pages, dict) or pages.get('schema') != 'pages.v1':
        raise ValueError('UI pages must use the existing pages.v1 registry')
    if not isinstance(screens, dict) or screens.get('pages_sha256') != _sha(pages_path):
        raise ValueError('art screens are not derived from the current page registry')
    page_map = {x['id']: x for x in pages.get('pages', []) if isinstance(x, dict) and isinstance(x.get('id'), str)}
    screen_ids = {x.get('id') for x in screens.get('screens', []) if isinstance(x, dict)}
    slots = {x['id']: x for x in visual.get('cases', []) if isinstance(x, dict) and isinstance(x.get('id'), str)}
    captures = [x for x in capture.get('cases', []) if isinstance(x, dict)]
    asset_map = {x['id']: x for x in visual.get('production_assets', []) if isinstance(x, dict) and isinstance(x.get('id'), str)}
    required_pages, required_cases, used_assets, links = set(), set(), set(), {}
    for node in manifest.get('nodes', []):
        if node.get('kind') not in STANDARD:
            continue
        own = node.get('ui') or {}
        pids = _ids(own.get('page_ids', config.get('page_ids')), node['kind'] + '.ui.page_ids')
        vids = _ids(own.get('visual_case_ids', config.get('visual_case_ids')), node['kind'] + '.ui.visual_case_ids')
        if any(page not in page_map or page not in screen_ids for page in pids):
            raise ValueError(node['kind'] + ': required page is missing from pages/screens')
        entries = [e for pid in pids for e in page_map[pid].get('ad_entries', []) if isinstance(e, dict)]
        for entry in node.get('entries', []):
            role = ROLE_ALIASES.get(entry['role'], entry['role'])
            if not any(e.get('button') == entry['button'] and ROLE_ALIASES.get(e.get('role'), e.get('role')) == role for e in entries):
                raise ValueError('required advertisement button/role is not registered on its UI pages: ' + entry['id'])
        for vid in vids:
            slot = slots.get(vid)
            if slot is None or slot.get('screen') not in pids:
                raise ValueError('visual case is missing or outside its declared advertisement page: ' + vid)
            candidates = [x for x in captures if x.get('screen') == slot.get('screen') and x.get('width') == slot.get('viewport_width')
                          and ('viewport_height' not in slot or x.get('height') == slot['viewport_height'])
                          and ('capture_case' not in slot or x.get('id') == slot['capture_case'])]
            if len(candidates) != 1 or not isinstance(candidates[0].get('id'), str):
                raise ValueError('visual case has no exact unambiguous capture mapping: ' + vid)
            links[vid] = candidates[0]['id']
        for aid in own.get('production_asset_ids', config.get('production_asset_ids', [])):
            asset = asset_map.get(aid)
            if not asset or not set(asset.get('expected_cases') or []).intersection(vids):
                raise ValueError('advertisement production asset has no required visual consumer: ' + str(aid))
            used_assets.add(aid)
        required_pages.update(pids)
        required_cases.update(vids)
    return dict(paths, required_page_ids=sorted(required_pages), required_visual_case_ids=sorted(required_cases),
                required_capture_case_ids=sorted(set(links.values())), visual_to_capture=links,
                production_asset_ids=sorted(used_assets),
                production_context=_prepare_context(project, config.get('production_context')))


def _earlier_formal_trial(project):
    # Read the owning formal-trial log, not a user switch or a generic passed
    # scalar. These are historical identities: do not demand that old snapshots
    # or old Native folders still exist after supported preview cleanup.
    owner = SKILLS / 'cocos-game-to-english/scripts/chinese_audit.py'
    if not owner.is_file():
        return False
    try:
        out = _module(owner).resolve_out(project, None)
        rows = _json(Path(out) / 'trial-links.json')
        def complete(row):
            if not isinstance(row, dict) or row.get('passed') is not True or row.get('draft') is not False:
                return False
            if not isinstance(row.get('snapshot'), str) or not row['snapshot'].strip():
                return False
            if not isinstance(row.get('native_tree_sha256'), str) or not re.fullmatch(r'[0-9a-fA-F]{64}', row['native_tree_sha256']):
                return False
            if 'open_problems' in row and (type(row['open_problems']) is not int or row['open_problems'] != 0):
                return False
            snapshot_sha = row.get('snapshot_manifest_sha256')
            export_sha = row.get('export_manifest_sha256')
            if snapshot_sha is not None and (not isinstance(snapshot_sha, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', snapshot_sha)):
                return False
            if export_sha is not None and (not isinstance(export_sha, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', export_sha)):
                return False
            if snapshot_sha is not None and export_sha is not None and snapshot_sha != export_sha:
                return False
            return True
        return isinstance(rows, list) and any(complete(row) for row in rows)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def check_project(project, native=None, files=None, stage='writer', art_stage_check=None):
    """Return a fail-closed report; never runs browser, generation or a full art audit.

    art_stage_check(project, manifest=..., stage=..., ui=...) is the owning scoped
    checker. Default: exact sibling ad_ui_stage_check.py::check_project.
    """
    result = {'schema': 'ad_nodes_gate.v1', 'stage': stage, 'passed': False, 'problems': [],
              'ad_nodes': None, 'art': None, 'ui': None, 'native_binding': None}
    try:
        if stage not in ('writer', 'trial'):
            raise ValueError('stage must be writer or trial')
        project = Path(project).resolve(strict=True)
        if not project.is_dir():
            raise ValueError('project must be a directory')
        module = _module(SKILLS / 'ad-boost/scripts/ad_nodes.py')
        manifest = _json(_local(project, module.MANIFEST_PATH))
        kwargs = dict(level='runtime' if stage == 'writer' else 'wired', include_candidates=False)
        if stage == 'trial':
            kwargs['load_runtime'] = False
        report = module.audit_project(project, manifest=manifest, **kwargs)
        result['ad_nodes'] = report
        if (report.get('counting_model') != MODEL or report.get('required_standard_kinds') != list(STANDARD)
                or report.get('standard_count') != 6 or report.get('count') != 6
                or report.get('missing_mandatory') or report.get('passed') is not True):
            raise ValueError('strict standard six advertisement nodes incomplete: ' + ', '.join(report.get('missing_mandatory', [])))
        if stage == 'writer':
            runtime = _json(_local(project, module.RUNTIME_PATH))
            result['native_binding'] = _native_binding(project, runtime, native, files)
        art = _module(HERE / 'art_check_record.py').check(project, earlier_trial=_earlier_formal_trial(project))
        result['art'] = art
        if not isinstance(art, dict) or art.get('level') not in ('ok', 'warn'):
            raise ValueError('existing lightweight art check blocks: ' + str(art.get('message') if isinstance(art, dict) else art))
        ui = _ui_mapping(project, manifest)
        result['ui'] = ui
        checker = art_stage_check or _module(HERE / 'ad_ui_stage_check.py').check_project
        checked = checker(project, manifest=manifest, stage=stage, ui=ui)
        result['ui']['check'] = checked
        if (not isinstance(checked, dict) or checked.get('passed') is not True or checked.get('problems')
                or not set(ui['required_visual_case_ids']).issubset(checked.get('checked_visual_case_ids', []))):
            raise ValueError('affected advertisement UI has not passed its current scoped art/capture checks')
        result['passed'] = True
    except Exception as error:  # A broken/missing gate never silently approves production.
        result['problems'].append(str(error))
    return result
