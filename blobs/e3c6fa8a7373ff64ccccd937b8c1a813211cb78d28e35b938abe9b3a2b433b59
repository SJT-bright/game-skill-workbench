"""Consume independently bound review observations; never run a game or browser.

The catalogue names obligations, not executions. A successful existing review
can seed separate metadata checkpoints. Changed inputs require real dependency
ownership in the existing check ledger, not a whole-review replay or a new hash
on an old observation. Unmapped catalogue coverage is never reported as pass.
"""
from collections import Counter
from contextvars import ContextVar
from pathlib import Path
from types import SimpleNamespace
import json
import time

import check_ledger as cl

_context = ContextVar('known_issue_checkpoint_context', default=None)
PREFIX = 'known.'


def reused(node):
    value = _context.get()
    return bool(value and node in value['reused'])


def node_binding(node, fallback):
    value = _context.get()
    row = value['reused'].get(node) if value else None
    return (row['record']['result']['original_binding'] if row else
            value.get('artifact_bindings', {}).get(node, fallback) if value else fallback)


def accepts_prior_binding(binding):
    value = _context.get()
    return bool(value and (any(row['record']['result'].get('original_binding') == binding
                              for row in value['reused'].values()) or
                           binding in value.get('artifact_bindings', {}).values()))


def stored_observation(node, fallback):
    value = _context.get()
    row = value['reused'].get(node) if value else None
    return row['record']['result']['observation']['observation'] if row else fallback


def reference_path(node, reference, base):
    path = (Path(base) / reference.get('path', '')).resolve()
    if path.is_file():
        return path
    value = _context.get()
    row = value['reused'].get(node) if value else None
    if row:
        for ref in row['record'].get('files', []):
            frozen = Path(ref['path'])
            if ref.get('sha256') == reference.get('sha256') and frozen.is_file():
                if cl.sha(frozen.read_bytes()) == reference.get('sha256'):
                    return frozen
    return path


def artifact_bindings(args, review):
    """Identify only independently approved scoped rows; never approve a table.

    The old wrapper may keep its exact observation binding, while every other
    row still validates against its own dependency proof/current input.
    """
    import check_known_issues as gate
    current = None
    result = {}
    for cid in ('LOAD-01', 'STORAGE-01'):
        refs = review.get('checks', {}).get(cid, {}).get('auto_reports', [])
        for ref in refs if isinstance(refs, list) else []:
            try:
                path = Path(ref['path'])
                if not path.is_absolute():
                    path = args.review.parent / path
                if cl.sha(path.read_bytes()) != ref.get('sha256'):
                    continue
                report = gate.load(path)
                origin = report.get('binding')
                if current is None:
                    current = gate.binding(args)
                if not isinstance(origin, dict) or origin == current:
                    continue
                if cid == 'LOAD-01' and report.get('tool') == 'audit_startup_contract':
                    from startup_scoped_evidence import consume
                    witness = consume(args.project, args.native, path, current_binding=current)
                    valid = witness is not None and witness.get('original_binding') == origin
                elif cid == 'STORAGE-01' and report.get('tool') == 'audit_native_storage_contract':
                    from storage_scoped_reuse import validate_report
                    valid = not validate_report(report, args.native, current, project=args.project)
                else:
                    valid = False
                if valid:
                    result[PREFIX + cid] = origin
                    break
            except (ValueError, OSError, KeyError, TypeError):
                continue
    return result


def source_roots(args):
    return {'source': cl.manifest(args.project, project=True),
            'package': cl.manifest(args.native), 'web': cl.manifest(args.web)}


def node_definitions(gate, args, review, catalog):
    board = review.get('board', gate.DEFAULT_BOARD)
    art_style = review.get('art_style', 'original')
    rows = review.get('checks', {})
    entries = review.get('reward_entries', [])
    if not isinstance(rows, dict) or not isinstance(entries, list):
        raise ValueError('Review checks/entry inventory malformed')
    metadata = [{k: v for k, v in entry.items() if k != 'states'}
                for entry in entries if isinstance(entry, dict)]
    records = gate.project_records(args.project)
    common = {'stage': args.stage, 'board': board, 'art_style': art_style,
              'production_records': records, 'entry_metadata': metadata}
    nodes = {}
    for item in catalog['items']:
        if not gate.applies(item, board, art_style) or not gate.final_gate(item):
            continue
        if args.stage == 'pre_scan' and item['phase'] in ('device', 'post_package'):
            continue
        if args.stage == 'post_package' and item['phase'] == 'device':
            continue
        nodes[PREFIX + item['id']] = dict(common, definition=item, observation=rows.get(item['id'], {}))
    nodes[PREFIX + 'inventory'] = dict(common, observation={
        k: review.get(k) for k in ('inventory_complete', 'inventory_evidence', 'inventory_snapshot')})
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Reward entry must be an object')
        eid = str(entry.get('id', ''))
        states = entry.get('states', {})
        if not eid or not isinstance(states, dict):
            raise ValueError('Reward entry identity/states missing')
        for state in catalog['reward_states']:
            nodes[PREFIX + 'reward.' + eid + '.' + state] = dict(
                common, state=state, state_catalog=catalog['reward_states'],
                entry={k: v for k, v in entry.items() if k != 'states'},
                observation=states.get(state, {}))
    pairs = review.get('independent_reward_checks', {})
    if not isinstance(pairs, dict):
        raise ValueError('Independent reward checks must be an object')
    for name, definition in gate.independent_pairs(metadata).items():
        nodes[PREFIX + 'pair.' + name] = dict(common, definition=definition, observation=pairs.get(name, {}))
    return nodes


def referenced_files(value, base):
    """Freeze the actual evidence closure, including relative JSON sidecars.

    Existing original files are checked against explicit reference hashes. A
    missing original can be recovered from the ledger's frozen evidence; a
    changed original is not quietly treated as the same report.
    """
    found, seen = set(), set()
    path_fields = {'path', 'trace', 'runtime_file', 'report_file', 'proof_file',
                   'plan_file', 'raw_report', 'raw_file', 'raw_files', 'run_file',
                   'frames_file', 'screenshot', 'evidence'}
    pending = [(value, Path(base).resolve(), '')]
    while pending:
        obj, parent, field = pending.pop()
        if isinstance(obj, dict):
            ref = obj.get('path')
            if isinstance(ref, str) and isinstance(obj.get('sha256'), str):
                p = (parent / ref).resolve()
                if p.is_file() and cl.sha(p.read_bytes()) != obj['sha256']:
                    raise ValueError('Referenced evidence bytes changed: ' + str(p))
            pending.extend((child, parent, key) for key, child in obj.items())
        elif isinstance(obj, list):
            pending.extend((child, parent, field) for child in obj)
        elif field in path_fields and isinstance(obj, str) and 0 < len(obj) < 4096 and '\n' not in obj:
            try:
                p = (parent / obj).resolve()
                if not p.is_file() or p in seen:
                    continue
                seen.add(p); found.add(str(p))
                if p.suffix.lower() == '.json':
                    try:
                        data = json.loads(p.read_bytes())
                    except (ValueError, UnicodeError):
                        continue
                    pending.append((data, p.parent, ''))
            except OSError:
                continue
    return sorted(found)


def validated_nodes(result, allowed_nodes):
    """Accept only explicit, complete ownership of every validation error.

    Global/cross-node failures or an unknown result shape prevent all new
    commits. Error text is diagnostic, never an authority for ownership.
    """
    if (result.get('per_node_validation_schema') != 'known-node-validation.v1'
            or result.get('status') not in ('passed', 'blocked')):
        return {}
    nodes = result.get('per_node_validation')
    global_errors = result.get('global_validation_errors')
    errors = result.get('errors')
    if not isinstance(nodes, dict) or not isinstance(global_errors, list) or not isinstance(errors, list):
        return {}
    if global_errors or not all(isinstance(error, str) for error in errors):
        return {}
    attributed = []
    for node, row in nodes.items():
        if (not isinstance(node, str) or node not in allowed_nodes or not isinstance(row, dict)
                or row.get('status') not in ('passed', 'failed')
                or not isinstance(row.get('errors'), list)
                or not all(isinstance(error, str) for error in row['errors'])
                or bool(row['errors']) != (row['status'] == 'failed')):
            return {}
        attributed.extend(row['errors'])
    if Counter(errors) != Counter(attributed) or bool(errors) != (result['status'] == 'blocked'):
        return {}
    return nodes


def audit_once(args, validate):
    import check_known_issues as gate
    review = gate.load(args.review)
    review_sha256 = cl.sha(args.review.read_bytes())
    # Existing separately reviewed project schemas retain their real validator;
    # never manufacture a generic migration for a private legacy adapter.
    if (not isinstance(review, dict) or review.get('schema') != 3
            or getattr(args, 'executor_exit', False)):
        return validate(args)
    import project_qa
    if project_qa.review_policy(args, review):
        return validate(args)
    catalog = gate.load(gate.CATALOG)
    nodes = node_definitions(gate, args, review, catalog)
    roots = source_roots(args)
    # Raw consumer bytes intentionally participate, independently of any exact
    # compatibility identities used by legacy gameplay observers.
    tools = cl.tool_fingerprint([__file__, gate.__file__])
    conditions_rule = cl.sha(Path(gate.__file__).read_bytes())
    store = cl.Ledger(args.project)
    created = []
    approved_artifacts = artifact_bindings(args, review)
    try:
        plans, files = {}, {}
        for cid, conditions in nodes.items():
            conditions = dict(conditions, consumer_rule_sha256=conditions_rule)
            try:
                files[cid] = referenced_files(conditions, args.review.parent)
            except ValueError as error:
                raise ValueError(cid + ': ' + str(error)) from error
            # This is a new metadata contract over an independently validated
            # scoped artifact, never a rewrite of the old whole-tree record.
            record_id, record_roots = cid, roots
            if cid in approved_artifacts:
                conditions['approved_artifact_origin'] = approved_artifacts[cid]
                record_id, record_roots = PREFIX + 'scope.' + cid[len(PREFIX):], {}
            plans[cid] = store.prepare(record_id, record_roots, conditions, tools,
                                       label='已有证据核对 · ' + cid, domain='package')
        reusable = {cid: row for cid, row in plans.items() if row['action'] == 'reuse'}
        unavailable = [row for row in plans.values()
                       if row['action'] not in ('run', 'reuse')]
        if unavailable:
            for row in unavailable:
                store.event(row['check_id'], row['action'], reason=row['why'],
                            domain='package', label='已有证据核对 · ' + row['check_id'])
            return {'status': 'blocked', 'stage': args.stage, 'binding': gate.binding(args),
                    'errors': [row['check_id'] + ': ' + row['why'] for row in unavailable],
                    'repair_scope': [row['check_id'] for row in unavailable],
                    'replay_authorized': False, 'checks': checkpoint_rows(plans)}
        token = _context.set({'reused': reusable, 'artifact_bindings': approved_artifacts})
        try:
            result = validate(args)
        finally:
            _context.reset(token)
        verified = validated_nodes(result, plans)
        if verified:
            before = roots
            if source_roots(args) != before:
                raise ValueError('Review input changed during verification')
            if cl.sha(args.review.read_bytes()) != review_sha256:
                raise ValueError('Review changed during verification')
            original_binding = gate.binding(args)
            for cid, plan in plans.items():
                if plan['action'] == 'reuse':
                    store.execute(plan, lambda: None, lambda _: False)
                    continue
                row = verified.get(cid)
                if not row:
                    continue  # An unvalidated node cannot inherit another row's pass.
                if row['status'] == 'failed':
                    value = {'validation_only': True, 'original_binding': original_binding,
                             'status': 'failed', 'errors': row['errors'],
                             'review': str(args.review.resolve()), 'review_sha256': review_sha256}
                    store.execute(plan, lambda v=value: v, lambda _: False)
                    plan['validation_failed'] = True
                    continue
                value = {'validation_only': True, 'original_binding': approved_artifacts.get(cid, original_binding),
                         'observation': nodes[cid], 'status': 'pass',
                         'observation_at': nodes[cid].get('observation', {}).get('observed_at'),
                         'review': str(args.review.resolve()),
                         'review_sha256': review_sha256}
                stored, detail = store.execute(plan, lambda v=value: v, lambda v: v.get('status') == 'pass',
                                                capture=lambda cid=cid: files[cid])
                if not detail['reused']:
                    created.append(plan['key'])
                    # Check the frozen copies, not merely the live path read
                    # before copy. A moving evidence file cannot certify itself.
                    referenced_files(stored, args.review.parent)
                    if cl.sha(Path(stored['review']).read_bytes()) != stored['review_sha256']:
                        raise ValueError('Review changed while preserving checkpoint evidence')
                plan['validation_passed'] = True
            if source_roots(args) != before or cl.tool_fingerprint([__file__, gate.__file__]) != tools:
                raise ValueError('Review inputs/rules changed while committing checkpoints')
        result['checks'] = checkpoint_rows(plans)
        result['checkpoint_schema'] = 'known-issue-checkpoints.v1'
        result['execution_boundary'] = 'Existing-evidence validation only; no new game or browser observation'
        return result
    except BaseException as error:
        # Each row has a separate identity, while the source snapshot is read
        # only once per batch boundary. Invalidate only our newly written rows
        # if that final boundary moves; valid historical rows remain untouched.
        with store.db:
            for key in created:
                row = store.db.execute('SELECT data FROM records WHERE key=?', (key,)).fetchone()
                if row:
                    value = json.loads(row[0]); value['passed'] = False
                    value['error'] = 'checkpoint commit refused: ' + str(error)
                    store.db.execute('UPDATE records SET data=? WHERE key=?', (cl.canonical(value), key))
        raise
    finally:
        store.close()


def checkpoint_rows(plans):
    return [{'id': cid, 'action': 'failed' if row.get('validation_failed') else
             'reused' if row['action'] == 'reuse' else
             'validated' if row.get('validation_passed') else
             'not_committed' if row['action'] == 'run' else row['action'],
             'original_at': (row.get('record') or {}).get('result', {}).get('observation_at'),
             'recorded_at': (row.get('record') or {}).get('executed_at'),
             'validation_only': True,
             'original_key': cl.sha(row['record']['binding']) if row.get('record') else None,
             'reason': row['why']} for cid, row in plans.items()]


def consume_for_writer(project, native, web, build_tag=None, review=None, board=None):
    """Read a supplied/current review, or report absent coverage without a pass.

    The canonical writer independently enforces actual technical obligations.
    Missing old catalogue metadata must not force untouched old-game testing.
    Full production coverage remains owned by the producing stages.
    """
    import check_known_issues as gate
    path = Path(review) if review else Path(project) / 'docs/test/known-issue-review.json'
    if not path.is_file():
        if review:
            raise ValueError('known.review: explicitly supplied review is missing: ' + str(path))
        return {'status': 'not_recorded', 'passed': False,
                'boundary': 'No complete catalogue approval claimed; use original production records and the scoped task boundary',
                'replayed': False}
    doc = gate.load(path)
    if not web:
        raise ValueError('known.review: actual current Web directory required to consume an existing review')
    tag = build_tag or doc.get('binding', {}).get('build_tag')
    args = SimpleNamespace(project=Path(project).resolve(), native=Path(native).resolve(),
                           web=Path(web).resolve(), build_tag=tag, review=path.resolve(),
                           board=board, stage='pre_scan', executor_exit=False)
    import project_qa
    profile = project_qa.review_policy(args, doc)
    if doc.get('schema') != 3 and not profile:
        raise ValueError('known.review: unsupported review schema has no registered producer')
    if profile:
        # A registered project hook can contain executable work. Its owning
        # producer proof is separately bound by the canonical writer; this
        # consumer must never invoke an arbitrary legacy hook on readback.
        return {'status': 'project_supplement', 'passed': False,
                'review': str(path.resolve()), 'sha256': cl.sha(path.read_bytes()),
                'boundary': 'Requires the separately verified project-supplement producer proof; no generic catalogue approval claimed',
                'replayed': False}
    result = gate.audit(args)
    if result.get('status') != 'passed':
        raise ValueError('known.review: ' + '; '.join(result.get('errors', ['not verified'])))
    return result
