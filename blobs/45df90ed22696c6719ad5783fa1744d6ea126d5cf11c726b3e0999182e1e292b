"""Read-only user-locked art maintenance evidence; never a full ART pass.

Unknown projects retain the ordinary receipt gate. This explicit, exact-byte contract
implements art-before-trial's existing-project/no-prior-report rule without inventing
an old pass or rerunning the original game's art direction.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

MANIFEST = Path('docs/art/locked-maintenance-scope.json')
SCHEMA = 'user_locked_art_maintenance.v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def checked(ref):
    if not isinstance(ref, dict) or not isinstance(ref.get('path'), str):
        raise ValueError('pinned evidence reference required')
    p = Path(ref['path']).resolve()
    if not p.is_file() or sha(p) != ref.get('sha256'):
        raise ValueError('locked-art evidence missing or changed: ' + str(p))
    return p


def assets(project):
    root = Path(project).resolve()
    out = {}
    for p in sorted((root/'assets').rglob('*')):
        if p.is_file():
            if not p.resolve().is_relative_to(root/'assets'):
                raise ValueError('asset symlink escapes project')
            out[p.relative_to(root).as_posix()] = sha(p)
    return out


def actual_diff(before, after):
    return {p: {'before':before.get(p), 'after':after.get(p)}
            for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)}


def approved_event(ref):
    approval = read(checked(ref))
    event = read(checked(approval['event_record']))
    payload = event.get('payload', {})
    quote = approval.get('quote', '').strip()
    text = '\n'.join(x.get('text', '') for x in payload.get('content', []) if isinstance(x, dict))
    if (approval.get('decided_by') != 'user' or len(quote) < 8 or
            event.get('type') != 'response_item' or payload.get('role') != 'user' or
            quote not in text or event.get('timestamp') != approval.get('timestamp')):
        raise ValueError('actual dated user approval event required')
    # A self-authored quote file cannot establish user authorship: the original
    # session must contain this exact message payload and timestamp.
    source = Path(approval['source_session']).resolve()
    session_root = (Path.home()/'.codex/sessions').resolve()
    if not source.is_relative_to(session_root) or not source.name.startswith('rollout-') or source.suffix != '.jsonl':
        raise ValueError('approval original session must be canonical Codex session evidence')
    matched = False
    with source.open(encoding='utf-8') as stream:
        for line in stream:
            raw = json.loads(line)
            if raw.get('timestamp') == event['timestamp'] and raw.get('type') == event['type'] and raw.get('payload') == payload:
                matched = True
                break
    if not matched:
        raise ValueError('approval event absent from original session')
    return approval


def source_comparison(project, ref):
    doc = read(checked(ref))
    zref = doc['baseline_zip']; path = checked(zref)
    prefix = zref.get('asset_prefix', '')
    parts = PurePosixPath(prefix).parts
    if not prefix.endswith('/assets/') or not parts or '..' in parts or prefix.startswith('/'):
        raise ValueError('explicit normalized approved source ZIP asset prefix required')
    before = {}
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise ValueError('approved baseline is not a valid ZIP') from exc
    with archive:
        names = [x.filename for x in archive.infolist() if not x.is_dir() and x.filename.startswith(prefix)]
        if not names or len(names) != len(set(names)):
            raise ValueError('baseline ZIP assets missing or duplicated')
        for name in names:
            rel = name[len(prefix):]
            if '..' in PurePosixPath(rel).parts or rel.startswith('/'):
                raise ValueError('unsafe baseline asset entry')
            before['assets/' + rel] = hashlib.sha256(archive.read(name)).hexdigest()
    after = assets(project)
    changed = actual_diff(before, after)
    if before != doc.get('baseline_assets') or after != doc.get('current_assets') or changed != doc.get('changed_assets'):
        raise ValueError('actual source ZIP/current byte comparison differs from pinned scope')
    return changed, before, after


def coverage(changed, declared, valid_proofs):
    if not isinstance(declared, dict) or set(declared) != set(changed):
        raise ValueError('every changed asset requires exact local evidence coverage')
    for name, row in declared.items():
        proofs = row.get('proof_ids')
        if not isinstance(proofs, list) or not proofs or not set(proofs) <= valid_proofs or len(row.get('reason', '').strip()) < 12:
            raise ValueError('changed asset evidence missing or unknown: ' + name)
        ext = Path(name).suffix.lower()
        kind = row.get('kind')
        if ext in {'.png','.jpg','.jpeg','.webp'}:
            if kind != 'generated_image' or 'values' not in proofs:
                raise ValueError('new image needs actual generated provenance and current value evidence')
        elif ext == '.meta':
            sibling = name[:-5]
            if kind != 'metadata' or sibling not in changed or not set(proofs) <= set(declared[sibling]['proof_ids']):
                raise ValueError('metadata must share evidence with its exact changed asset')
        elif ext in {'.ts','.js'}:
            if kind != 'code':
                raise ValueError('changed code requires code evidence declaration')
        elif PurePosixPath(name).name == '.DS_Store':
            if kind != 'nonrendering_metadata':
                raise ValueError('non-rendering Finder metadata must be explicit')
        else:
            # No generic waiver for fonts, prefabs, scenes, atlases, or new designs.
            raise ValueError('unsupported maintenance change needs normal affected-art acceptance: ' + name)


def generated_images(project, changed, ref):
    rows = read(checked(ref)).get('images', [])
    by_file = {}
    for row in rows:
        file = row.get('file')
        if file:
            p = Path(file); p = p if p.is_absolute() else project/p
            by_file[str(p.resolve())] = row
    for rel in changed:
        if Path(rel).suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:
            continue
        if changed[rel]['after'] is None:
            raise ValueError('deleting artwork is outside this maintenance compatibility path')
        row = by_file.get(str((project/rel).resolve()))
        if not row or row.get('tool') != 'image_gen' or row.get('sha256') != sha(project/rel) or not row.get('prompt'):
            raise ValueError('actual generated production image record missing: ' + rel)
        parent_sha = row.get('from_sha256')
        if parent_sha:
            raw = [r for r in rows if r.get('raw') is True and r.get('sha256') == parent_sha and r.get('tool') == 'image_gen']
            if len(raw) != 1:
                raise ValueError('unique original generation record required: ' + rel)
            checked({'path':raw[0]['file'], 'sha256':parent_sha})
        elif not row.get('raw'):
            raise ValueError('production image lacks original generation bytes: ' + rel)


def value_evidence(project, doc, V):
    folders = set(); sizes = set()
    refs = doc.get('fixtures', [])
    if len(refs) < 2:
        raise ValueError('two actual value fixtures required')
    for ref in refs:
        fixture = read(checked(ref))
        if fixture.get('scope') != 'actual_production_presentation_fixture_only_no_balance_or_save_mutation' or not isinstance(fixture.get('before'), dict) or not fixture.get('before') or fixture.get('before') != fixture.get('after') or not fixture.get('slots'):
            raise ValueError('value fixture modified stored state or lacks observation')
        cap = fixture['cap']; dump_path = checked({'path':cap['file'], 'sha256':cap['dump_sha256']})
        shot = checked({'path':cap['png'], 'sha256':cap['screenshot_sha256']})
        dump = read(dump_path)
        ds = Path(dump.get('screenshot', '')); ds = ds if ds.is_absolute() else dump_path.parent/ds
        if dump.get('tool') != 'ui_dump' or dump.get('errors') or dump.get('truncated') or ds.resolve() != shot:
            raise ValueError('value dump is not the actual paired screenshot')
        for slot in fixture['slots']:
            matches = [node for node in dump.get('nodes', []) if node.get('path', '').endswith('/'+slot['path'])]
            if len(matches) != 1 or matches[0].get('comps', {}).get('label', {}).get('string') != slot.get('fixture'):
                raise ValueError('actual captured value label differs from declared display fixture')
        vp = cap['page']
        if any(dump.get('page', {}).get(k) != vp.get(k) for k in ('width','height','dpr')):
            raise ValueError('value fixture page dimensions differ from actual dump')
        sizes.add((vp['width'], vp['height'])); folders.add(dump_path.parent)
    if len(sizes) < 2 or any(w <= 0 or h <= w for w,h in sizes):
        raise ValueError('two portrait value viewport sizes required')
    prior = read(checked(doc['report']))
    current = V.audit(project, sorted(folders))
    keys = ('tool','schema','revision','mode','passed','source_sha256','pages','findings')
    if any(prior.get(k) != current.get(k) for k in keys) or current.get('passed') is not True or current.get('mode') != 'runtime':
        raise ValueError('actual current value audit does not pass or no longer matches')
    return sorted(sizes), current['pages']


def validate(project, receipt=None, manifest=None):
    import art_receipt as A
    import art_production as P
    import audit_value_presentation as V
    import audit_ui_contract as U
    import package_issue_gate as I
    project = Path(project).resolve()
    location = Path(manifest).resolve() if manifest else project/MANIFEST
    doc = read(location)
    if doc.get('schema') != SCHEMA or doc.get('project') != str(project):
        raise ValueError('locked-art maintenance project/schema mismatch')
    approval = approved_event(doc['approval'])
    changed, before, after = source_comparison(project, doc['source_comparison'])
    if doc.get('historical_receipt'):
        old_path = checked(doc['historical_receipt'])
        if old_path != A.receipt_path(project).resolve() or (receipt is not None and read(old_path) != receipt):
            raise ValueError('historical art receipt was replaced or changed')
        old_status = read(old_path).get('status')
    else:
        if A.receipt_path(project).exists():
            raise ValueError('existing historical receipt must be preserved and pinned')
        old_status = 'not_established'
    for ref in doc.get('historical_reports', []):
        checked(ref)  # Preserve evidence, deliberately do not upgrade its verdict.
    binding = doc['binding']
    actual_binding = {'images':A.image_fingerprints(project), 'display':A.display_fingerprints(project),
                      'source_sha256':V.source_fingerprint(project), 'production':P.fingerprint(project)}
    if any(binding.get(k) != value for k,value in actual_binding.items()):
        raise ValueError('current images/display/source/production binding changed')
    native = Path(doc['native']).resolve()
    if not native.is_dir() or not native.is_relative_to(project) or U.tree_digest(native) != binding.get('native_tree_sha256'):
        raise ValueError('current Native tree changed or missing')
    issues = I.audit(project, native)
    ids = {row['id'] for row in issues['checked_issues']}
    if not ids or issues.get('pending_external_issues') or ids != set(doc.get('issue_ids', [])):
        raise ValueError('known issues are missing, deferred, open, or differ from locked scope')
    case_ids = {}; ui_sizes = set()
    for row in issues['checked_issues']:
        proof = read(checked(row['proof']))
        case_ids[row['id']] = sorted(proof['cases'])
        for case in proof['cases'].values():
            # The official ledger already verifies current/negative/normal hashes,
            # runner/checker identity, dependencies, observations and bad controls.
            raw = read(checked(case['current']))
            for result in raw.get('results', []):
                vp = result.get('checker', {}).get('viewport', {})
                if vp.get('width') and vp.get('height'):
                    ui_sizes.add((vp['width'],vp['height']))
    if case_ids != doc.get('issue_cases') or len(ui_sizes) < 2:
        raise ValueError('all registered case identities and two actual UI sizes required')
    sizes, value_pages = value_evidence(project, doc['values'], V)
    generated_images(project, changed, doc['generated'])
    startup = read(checked(doc['startup']))
    if startup.get('passed') is not True or startup.get('failed') != 0 or startup.get('native') != str(native) or startup.get('binding', {}).get('native_tree_sha256') != binding['native_tree_sha256']:
        raise ValueError('actual current Native startup proof required')
    coverage(changed, doc['coverage'], {'values','startup'} | {'issue:'+x for x in ids})
    return {'state':'user_locked_art_maintenance', 'manifest':str(location), 'manifest_sha256':sha(location),
            'historical_art_status':old_status, 'full_art_verdict':'not_established_by_this_scope',
            'approval_timestamp':approval['timestamp'], 'native_tree_sha256':binding['native_tree_sha256'],
            'changed_assets':sorted(changed), 'unchanged_assets':len(set(before)&set(after))-sum(1 for x in changed if x in before and x in after),
            'issue_ids':sorted(ids), 'registered_cases':sum(map(len,case_ids.values())),
            'ui_viewports':sorted(ui_sizes), 'value_viewports':sizes, 'value_pages':value_pages,
            'boundary':'User-approved original art preserved; exact later changes, current values, startup and all registered defects verified. Historical fail/missing full-art result remains unchanged. This is not full ART-06, physical-device or platform acceptance.'}
