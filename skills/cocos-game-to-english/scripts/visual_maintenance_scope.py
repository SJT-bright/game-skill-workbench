"""Evidence-bound page-template mappings for preserving an existing game's UI.

Only named page-template demands can be mapped. Every mapped page must be an
unchanged ui_dump observation with a same-capture screenshot in both portrait
ratios. The visual defects detected by audit_page_richness remain active.
"""
import hashlib
from pathlib import Path

from maintenance_scope import checked_ref, load_scope, read

# These identifiers map only to the template checks named below. They are not
# prefixes, filters, or page-level exemptions.
RULES = {
    'settings_original_switches': {
        'purposes': {'settings_sound'},
        'skips': {'settings_general', 'settings_sound', 'required:settings'},
    },
    'home_original_composition': {
        'purposes': {'home'},
        'skips': {'home_composition', 'home_gift'},
    },
    'result_original_multiplier': {
        'purposes': {'result_win'},
        'skips': {'result_double_x2'},
    },
    'checkin_original_card_sizes': {
        'purposes': {'checkin'},
        'skips': {'checkin_day7_size'},
    },
}


def validate_derived(d):
    """Verify that an envelope preserves a raw official dump and paired pixels."""
    prov = d.get('derived_provenance')
    if not isinstance(prov, dict):
        raise ValueError('maintenance visual mapping requires raw-derived provenance')
    if d.get('tool') != 'ui_dump' or d.get('schema') != 1 or d.get('producer') != 'ego_page.dump_ui':
        raise ValueError('derived dump must identify official ui_dump schema 1 and ego_page.dump_ui producer')
    source = checked_ref({'path': prov.get('source_dump'), 'sha256': prov.get('source_sha256')}, Path(d['_file']).parent)
    raw = read(source)
    if raw.get('tool') != 'ui_dump' or raw.get('schema') != 1 or raw.get('truncated') is True or raw.get('errors'):
        raise ValueError('raw source must be a complete successful official ui_dump')
    for k, value in raw.items():
        if k not in {'tool', 'schema', 'producer', 'screen', 'purpose', 'screenshot'} and d.get(k) != value:
            raise ValueError('derived dump changed original field ' + k)
    if d.get('nodes') != raw.get('nodes'):
        raise ValueError('derived dump changed nodes')
    page = raw.get('page')
    if not isinstance(page, dict) or type(page.get('width')) not in (int, float) or type(page.get('height')) not in (int, float):
        raise ValueError('raw ui_dump viewport missing')
    shot = Path(d.get('screenshot', ''))
    shot = shot if shot.is_absolute() else Path(d['_file']).parent / shot
    checked_ref({'path': str(shot), 'sha256': prov.get('source_screenshot_sha256')}, source.parent)
    return True


def _current_dumps(mapping, rule, dumps, base):
    refs = mapping.get('current_dumps')
    if not isinstance(refs, list) or len(refs) < 2:
        raise ValueError(rule + ': current_dumps must cite both real mobile ratios')
    by_path = {Path(d['_file']).resolve(): d for d in dumps if d.get('_file')}
    selected, seen = [], set()
    for ref in refs:
        p = checked_ref(ref, base)
        d = by_path.get(p)
        if d is None:
            raise ValueError(rule + ': cited current dump is not in this audit input: ' + str(p))
        validate_derived(d)
        purpose = d.get('purpose', 'other')
        if purpose not in RULES[rule]['purposes']:
            raise ValueError(rule + ': expected purpose ' + ', '.join(sorted(RULES[rule]['purposes'])))
        page = d.get('page') or {}
        size = (page.get('width'), page.get('height'))
        if not all(type(x) in (int, float) and x > 0 for x in size) or size[1] <= size[0]:
            raise ValueError(rule + ': current portrait mobile viewport required')
        if size in seen:
            raise ValueError(rule + ': duplicate viewport; two distinct portrait ratios required')
        seen.add(size)
        selected.append((p, d))
    if len(seen) < 2:
        raise ValueError(rule + ': two distinct portrait ratios required')
    return selected


def _assert_rule_specific(rule, selected, originals, scope):
    if rule == 'settings_original_switches':
        # The retained page must still expose the two original functioning
        # controls. Mapping the new Sound-tab template never hides their loss.
        source_text = '\n'.join(p.read_text(encoding='utf-8-sig') for p in originals)
        for _, d in selected:
            found = set()
            for n in d.get('nodes', []):
                if n.get('name') not in {'btn-sound', 'btn-shake'}:
                    continue
                if 'button' not in n.get('comps', {}) or n['comps']['button'].get('interactable', True) is not True:
                    continue
                if '/panel-setting/' in n.get('path', ''):
                    found.add(n['name'])
            if found != {'btn-sound', 'btn-shake'}:
                raise ValueError('settings_original_switches: each current settings page must retain active btn-sound and btn-shake')
            if any(('"' + name + '"') not in source_text for name in found):
                raise ValueError('settings_original_switches: control identity not found in original serialized scene')
    elif rule == 'result_original_multiplier':
        if not scope.get('economy_catalog'):
            raise ValueError('result_original_multiplier: original reward economy proof required')
        if 'hero_trial' not in scope.get('existing_features', []) and not scope.get('runtime_trace'):
            raise ValueError('result_original_multiplier: current reward runtime proof required')
    elif rule == 'checkin_original_card_sizes':
        if 'daily_checkin' not in scope.get('existing_features', []):
            raise ValueError('checkin_original_card_sizes: existing daily check-in required')


def _scene_node_names(paths):
    names = set()
    for path in paths:
        try:
            import json
            value = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as exc:
            raise ValueError('original serialized scene is unreadable: ' + str(path)) from exc
        def walk(node):
            if isinstance(node, dict):
                if node.get('__type__') == 'cc.Node' and isinstance(node.get('_name'), str):
                    names.add(node['_name'])
                for child in node.values():
                    walk(child)
            elif isinstance(node, list):
                for child in node:
                    walk(child)
        walk(value)
    return names


def validate_policy(path, scope_path, project, binding, dumps):
    """Validate a small, explicit mapping list and return auditable detail."""
    scope = load_scope(scope_path, project, binding)
    p = Path(path).resolve()
    v = read(p)
    if v.get('schema') != 'maintenance_visual_policy.v2' or v.get('binding') != binding:
        raise ValueError('visual policy v2 with current binding required')
    if v.get('scope') is None or checked_ref(v['scope'], p.parent) != Path(scope_path).resolve():
        raise ValueError('visual policy must bind validated maintenance scope')

    original_refs = v.get('original_scene_refs')
    if not isinstance(original_refs, list) or not original_refs:
        raise ValueError('original serialized layout refs required')
    originals = [checked_ref(x, p.parent) for x in original_refs]
    scope_sources = {checked_ref(x, Path(scope_path).resolve().parent) for x in scope.get('original_sources', [])}
    if any(x not in scope_sources or x.suffix.lower() not in {'.fire', '.scene'} for x in originals):
        raise ValueError('original layout refs must be serialized scenes in the validated source provenance')

    mappings = v.get('mappings')
    if not isinstance(mappings, list) or not mappings:
        raise ValueError('explicit per-rule visual mappings required')
    ids = [x.get('rule') for x in mappings if isinstance(x, dict)]
    if len(ids) != len(mappings) or len(ids) != len(set(ids)) or not set(ids) <= set(RULES):
        raise ValueError('unknown, duplicate, or malformed visual rule mapping')
    if set(ids) != set(v.get('rules', [])):
        raise ValueError('rules must exactly match the per-rule mapping records')

    result = []
    for mapping in mappings:
        rule = mapping['rule']
        reason = mapping.get('reason')
        if not isinstance(reason, str) or len(reason.strip()) < 20:
            raise ValueError(rule + ': a specific preservation rationale is required')
        selected = _current_dumps(mapping, rule, dumps, p.parent)
        anchors = mapping.get('anchors')
        if not isinstance(anchors, list) or len(anchors) != len(set(anchors)) or not anchors or \
                not all(isinstance(x, str) and x.strip() for x in anchors):
            raise ValueError(rule + ': explicit original/current page anchor node names required')
        original_names = _scene_node_names(originals)
        if not set(anchors) <= original_names:
            raise ValueError(rule + ': mapping anchors must exist in the cited original serialized scene')
        for _, d in selected:
            current_names = {n.get('name') for n in d.get('nodes', [])}
            if not set(anchors) <= current_names:
                raise ValueError(rule + ': current page does not retain every original anchor node')
        _assert_rule_specific(rule, selected, originals, scope)
        result.append({
            'rule': rule,
            'skipped_template_checks': sorted(RULES[rule]['skips']),
            'preserved_anchor_nodes': anchors,
            'current_pages': [
                {'path': str(file), 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                 'purpose': d.get('purpose', 'other'), 'viewport': [d['page']['width'], d['page']['height']]}
                for file, d in selected
            ],
            'original_scenes': [{'path': str(x), 'sha256': hashlib.sha256(x.read_bytes()).hexdigest()} for x in originals],
            'reason': reason.strip(),
        })
    return {
        'rules': ids,
        'policy': str(p),
        'mappings': result,
        'boundary': 'Only the listed page-template checks are mapped. Actual text, English copy, contrast, size, resolution, clipping, overlap, stretch, visibility, button and touch defects remain active.',
    }
