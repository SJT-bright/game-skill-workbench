"""Explicit maintenance candidate governance; never runs a game or installs Skills."""
import copy
import hashlib
import json
from pathlib import Path
import shutil

import production_learning as L

PLAN_SCHEMA = 'production_learning_plan.v1'


def issue(code, **details):
    return dict(code=code, **details)


def tree_files(root):
    root = Path(root).resolve()
    if not root.is_dir(): raise ValueError('base tree missing')
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink(): raise ValueError('symlink in maintenance source tree')
        rel = path.relative_to(root).as_posix()
        if '__pycache__' in path.parts or path.name in ('.DS_Store', '.production-learning-application.json') or path.suffix == '.pyc': continue
        if path.is_file(): files[rel] = L.sha(path)
    return files


def identity(files):
    return L.digest(L.encoded(files))


def all_bundles(workspace):
    with L.database(workspace) as db:
        rows = [json.loads(x[0]) for x in db.execute('SELECT payload FROM bundles ORDER BY id')]
    return [L.validate_bundle(row) for row in rows]


def condition_key(rule):
    return L.digest(L.encoded(dict(scope=rule.get('scope'), conditions=rule.get('conditions', {}))))


def cause_scope(rule):
    return str(rule.get('cause_key')) + ':' + condition_key(rule)


def action_key(action):
    # Consumer evidence reads are not producer execution. Keep roles explicit.
    return tuple(action.get(k) for k in ('role', 'node', 'operation', 'target', 'check_id'))


def protected(action, catalog):
    return [row['id'] for row in catalog['protected_behaviors']
            if (action.get('target') in row['targets'] and action.get('decision') not in ('forbid', 'observe'))
            or action.get('operation') in row['forbidden_operations']]


def load_active(base,catalog):
    path=Path(base)/catalog['active_registry']
    if not path.exists():
        if (Path(base)/'remake-core/scripts/production_learning.py').is_file() or (Path(base)/'.production-learning-application.json').is_file():
            raise ValueError('active registry missing from a learning-aware base; restore it before maintenance')
        # First migration from a formal base before this mechanism existed.
        return dict(schema='production_learning_active.v1',registry_version=1,
            catalog_version=catalog['catalog_version'],catalog_sha256=L.sha(L.POLICY),formal_base_archive_sha256=catalog['formal_base_archive_sha256'],
            structural_principles=catalog['structural_principles'],rules=[],evidence_index={},reviews=[])
    doc=json.loads(path.read_text())
    if (doc.get('schema')!='production_learning_active.v1' or doc.get('registry_version')!=1 or
            doc.get('catalog_version')!=catalog['catalog_version'] or doc.get('catalog_sha256')!=L.sha(L.POLICY) or
            doc.get('formal_base_archive_sha256')!=catalog['formal_base_archive_sha256'] or
            doc.get('structural_principles')!=catalog['structural_principles'] or
            not isinstance(doc.get('rules'),list) or not isinstance(doc.get('evidence_index'),dict) or not isinstance(doc.get('reviews'),list)):
        raise ValueError('active registry schema/catalog/base mismatch; explicit maintenance migration required')
    reviewed_ids=set()
    review_pairs=set()
    for review in doc['reviews']:
        if not isinstance(review,dict) or not isinstance(review.get('registry_rule_ids'),list):raise ValueError('active registry review inventory missing')
        reviewed_ids.update(review['registry_rule_ids'])
        review_pairs.add((review.get('plan_sha256'),review.get('review_sha256')))
    if any(not isinstance(rule,dict) or rule.get('status') not in ('active','revoked','superseded') or
            rule.get('id') not in reviewed_ids or rule.get('changes') for rule in doc['rules']):
        raise ValueError('active registry contains unreviewed or pending rule semantics')
    for rid,item in doc['evidence_index'].items():
        if (not isinstance(item,dict) or item.get('payload_sha256')!=rid or len(rid)!=64 or
                any(c not in '0123456789abcdef' for c in rid) or
                not isinstance(item.get('raw_sha256s'),list) or not item['raw_sha256s'] or
                any(not isinstance(x,str) or len(x)!=64 or any(c not in '0123456789abcdef' for c in x) for x in item['raw_sha256s']) or
                not isinstance(item.get('approved_outcomes'),list) or not set(item['approved_outcomes'])<={'failure','fixed','normal'} or
                type(item.get('observed_success')) is not bool or not isinstance(item.get('observed_costs'),list) or
                any(type(x) not in (int,float) or not 0<=x<86400 for x in item['observed_costs']) or
                not isinstance(item.get('review_sources'),list) or not item['review_sources']):
            raise ValueError('active registry evidence index is malformed')
        for source in item['review_sources']:
            if (not isinstance(source,dict) or not all(isinstance(source.get(k),str) and len(source[k])==64 and
                    all(c in '0123456789abcdef' for c in source[k]) for k in ('plan_sha256','review_sha256'))):
                raise ValueError('active evidence has no pinned original review source')
            if (source['plan_sha256'],source['review_sha256']) not in review_pairs:raise ValueError('active evidence review source not in registry review inventory')
    return doc


def registry_evidence(active):
    # Only this BASE reader creates the private carried-index marker. Imported
    # bundle records are rebuilt from their validated public fields below.
    return {rid:dict(_reviewed_registry_index=item,id=rid) for rid,item in active['evidence_index'].items()}


def make_active(proposed,review,plan_sha,review_sha):
    previous=proposed['active_registry']
    evidence_index={}
    for rid,record in proposed['registry_evidence'].items():
        old=previous.get('evidence_index',{}).get(rid)
        item=dict(payload_sha256=rid,raw_sha256s=sorted(set(record['raw_sha256s'])),
                  approved_outcomes=sorted(set(record['approved_outcomes'])),observed_success=record['observed_success'],observed_costs=sorted(set(record['observed_costs'])),
                  review_sources=list(old.get('review_sources',[])) if old else [])
        source=dict(plan_sha256=plan_sha,review_sha256=review_sha)
        if source not in item['review_sources']:item['review_sources'].append(source)
        evidence_index[rid]=item
    rules=[]
    for original in proposed['registry_rules']:
        rule=copy.deepcopy(original)
        rule['status']='active' if rule['status']=='candidate' else rule['status']
        # Applied edits are historical metadata, never replayable pending changes.
        pending=rule.pop('changes',[])
        if pending:rule['applied_change_hashes']=[{k:x[k] for k in ('path','before_sha256','after_sha256')} for x in pending]
        rules.append(rule)
    source=dict(plan_sha256=plan_sha,review_sha256=review_sha,base_identity=proposed['base_identity'],reviewer=review['reviewer'],rule_ids=proposed['rule_ids'],registry_rule_ids=sorted(x['id'] for x in rules))
    reviews=list(previous.get('reviews',[]))
    if source not in reviews:reviews.append(source)
    return dict(schema='production_learning_active.v1',registry_version=1,catalog_version=proposed['catalog_version'],catalog_sha256=proposed['catalog_sha256'],
        formal_base_archive_sha256=proposed['formal_base_archive_sha256'],structural_principles=previous['structural_principles'],
        rules=rules,evidence_index=evidence_index,reviews=reviews,
        boundary='Reviewed shared semantics and original evidence hash facts; no logs copied and no new observations produced.')


def observed_outcomes(record):
    if '_reviewed_registry_index' in record:return set(record['_reviewed_registry_index']['approved_outcomes'])
    data=record['payload']
    if not isinstance(data,dict):return set()
    if data.get('passed') is False or data.get('status') in ('fail','failed','refuse','blocked') or type(data.get('exit')) is int and data['exit']!=0:return {'failure'}
    if data.get('passed') is True or data.get('status') in ('pass','passed') or type(data.get('exit')) is int and data['exit']==0:return {'fixed','normal'}
    return set()


def observed_positive(record):
    if '_reviewed_registry_index' in record:return record['_reviewed_registry_index']['observed_success'] is True
    return bool(observed_outcomes(record) & {'fixed','normal'})


def observed_costs(record):
    if '_reviewed_registry_index' in record:return set(record['_reviewed_registry_index']['observed_costs'])
    data=record['payload']
    if not isinstance(data,dict):return set()
    return {data[key] for key in ('elapsed_seconds','seconds','total_elapsed_seconds','duration_seconds')
            if type(data.get(key)) in (int,float) and 0<=data[key]<86400}


def rule_errors(rule, evidence, catalog):
    errors = []
    if not isinstance(rule, dict): return [issue('rule_not_object')]
    rid = rule.get('id')
    if not isinstance(rid, str) or not L.IDENTIFIER.fullmatch(rid): errors.append(issue('rule_id_required'))
    if not isinstance(rule.get('cause_key'), str) or not L.IDENTIFIER.fullmatch(rule['cause_key']): errors.append(issue('root_cause_unknown', rule_id=rid))
    if type(rule.get('revision')) is not int or rule['revision'] < 1: errors.append(issue('invalid_revision', rule_id=rid))
    status = rule.get('status')
    if status not in ('candidate', 'active', 'revoked', 'superseded'): errors.append(issue('unknown_status', rule_id=rid))
    authority = rule.get('authority')
    if (not isinstance(authority, list) or not authority or any(not isinstance(x, dict) or x.get('kind') not in ('user', 'official', 'reviewed_source')
            or not isinstance(x.get('ref'), str) or not x['ref'].strip() or x['ref'].startswith(('/', '~')) for x in authority)):
        errors.append(issue('authority_source_required', rule_id=rid))
    scope, conditions = rule.get('scope'), rule.get('conditions')
    if (not isinstance(scope, dict) or scope.get('level') != 'shared' or not isinstance(scope.get('applies'), dict)
            or not scope['applies'] or set(scope['applies']) - set(catalog['scope_axes'])
            or any(not isinstance(v, list) or not v or len(set(map(str,v))) != len(v) or
                   any(not isinstance(x,str) or not x.strip() or x in ('*','unknown') for x in v) for v in scope['applies'].values())):
        errors.append(issue('unknown_or_project_specific_scope', rule_id=rid))
    if isinstance(scope,dict) and isinstance(scope.get('applies'),dict):
        for axis,values in scope['applies'].items():
            if isinstance(values,list) and any(value not in catalog.get('scope_values',{}).get(axis,[]) for value in values): errors.append(issue('unknown_scope_value',rule_id=rid,axis=axis))
    if not isinstance(conditions, dict) or set(conditions) - set(catalog['condition_facts']) or any(type(v) is not bool for v in conditions.values()):
        errors.append(issue('conditions_require_known_boolean_facts', rule_id=rid))
    general = rule.get('generalization', {})
    if general != dict(private_fields_removed=True, reviewed=True): errors.append(issue('private_facts_not_reviewed_for_generalization', rule_id=rid))
    supersedes = rule.get('supersedes')
    if not isinstance(supersedes, list) or any(not isinstance(x,str) or not L.IDENTIFIER.fullmatch(x) for x in supersedes) or len(set(supersedes)) != len(supersedes):
        errors.append(issue('invalid_supersedes', rule_id=rid))
    actions = rule.get('prevention_actions')
    if not isinstance(actions, list) or not actions: errors.append(issue('prevention_actions_required', rule_id=rid)); actions=[]
    for action in actions:
        if not isinstance(action, dict): errors.append(issue('action_not_object', rule_id=rid)); continue
        required = ('id', 'node', 'producer', 'target', 'check_id')
        if any(not isinstance(action.get(k), str) or not L.IDENTIFIER.fullmatch(action[k]) for k in required): errors.append(issue('explicit_action_and_node_ids_required', rule_id=rid))
        consumers = action.get('consumers')
        if not isinstance(consumers, list) or not consumers or any(not isinstance(x,str) or not L.IDENTIFIER.fullmatch(x) for x in consumers): errors.append(issue('consumer_nodes_required', rule_id=rid))
        if action.get('role') not in ('producer','consumer','prevention') or action.get('operation') not in catalog['operations'] or action.get('decision') not in ('require','forbid','reuse','observe'):
            errors.append(issue('unknown_action', rule_id=rid))
        if action.get('role') == 'producer' and action.get('node') != action.get('producer'): errors.append(issue('producer_node_mismatch', rule_id=rid))
        if action.get('role') == 'consumer' and (action.get('node') not in (consumers or []) or action.get('operation') != 'consume_evidence'):
            errors.append(issue('consumer_must_consume_not_reexecute', rule_id=rid))
        if action.get('operation') == 'run_check' and action.get('role') != 'producer': errors.append(issue('only_producer_executes_check', rule_id=rid))
        for name in protected(action, catalog): errors.append(issue('revoked_behavior_cannot_return', rule_id=rid, protected_id=name))
    if rid in {row['id'] for row in catalog['protected_behaviors']} and status != 'revoked': errors.append(issue('protected_id_cannot_reactivate', rule_id=rid))
    if status not in ('revoked','superseded'):
        early=any(isinstance(a,dict) and a.get('role')=='prevention' and a.get('operation') in ('prepare','prevent') and
            (str(a.get('node','')).startswith(('intake.','source.','integration.')) or a.get('prevention_stage') in ('intake','source','integration')) for a in actions)
        limit=rule.get('prevention_limit')
        external=(isinstance(limit,dict) and all(isinstance(limit.get(k),str) and limit[k].strip() for k in
            ('external_condition','why_not_preventable','earliest_recovery_node','recovery_action')) and
            isinstance(limit.get('earliest_recovery_node'),str) and L.IDENTIFIER.fullmatch(limit['earliest_recovery_node']) and
            limit.get('strategy') in ('restore','degrade','bounded_retry'))
        if not early and not external:errors.append(issue('production_prevention_or_explicit_external_limit_required',rule_id=rid))
    refs = rule.get('evidence')
    if not isinstance(refs, list) or any(not isinstance(x,dict) or x.get('record_id') not in evidence or x.get('outcome') not in ('failure','fixed','normal') for x in refs):
        errors.append(issue('bound_evidence_required', rule_id=rid)); refs=[]
    for ref in refs:
        if ref['record_id'] in evidence and ref['outcome'] not in observed_outcomes(evidence[ref['record_id']]):
            errors.append(issue('evidence_outcome_does_not_match_original_record',rule_id=rid,record_id=ref['record_id']))
    tests = rule.get('tests')
    if not isinstance(tests,list):errors.append(issue('tests_inventory_required',rule_id=rid));tests=[]
    if status not in ('revoked','superseded'):
        outcomes = {x.get('outcome') for x in refs}
        if not {'failure','fixed','normal'} <= outcomes: errors.append(issue('failure_fixed_and_normal_counterexamples_required', rule_id=rid))
        if not isinstance(tests,list) or not tests or any(not isinstance(x,dict) or x.get('passed') is not True or x.get('record_id') not in evidence or
                not isinstance(x.get('id'),str) or type(x.get('cost_seconds')) not in (int,float) or not 0 <= x['cost_seconds'] < 86400 for x in tests):
            errors.append(issue('validation_and_actual_test_cost_required', rule_id=rid))
        else:
            for test in tests:
                record=evidence[test['record_id']]
                if not observed_positive(record) or test['cost_seconds'] not in observed_costs(record):
                    errors.append(issue('test_result_or_cost_not_bound_to_original_record',rule_id=rid,test_id=test['id']))
    return errors


def overlaps(a, b):
    for axis in set(a.get('scope',{}).get('applies',{})) & set(b.get('scope',{}).get('applies',{})):
        if not set(a['scope']['applies'][axis]) & set(b['scope']['applies'][axis]): return False
    ca, cb = a.get('conditions',{}), b.get('conditions',{})
    return not any(ca[key] != cb[key] for key in set(ca) & set(cb))


def plan(workspace, base, *, _bundles=None):
    catalog = L.policy(); before = tree_files(base); bundles = all_bundles(workspace) if _bundles is None else _bundles
    active_registry=load_active(base,catalog)
    problems, rules, evidence = [], [], registry_evidence(active_registry)
    for bundle in bundles:
        evidence.update({x['id']:{k:x[k] for k in ('id','source','raw_sha256','payload')} for x in bundle['records']})
    for prior in active_registry['rules']:
        errors=rule_errors(prior,evidence,catalog);problems.extend(errors)
        if not errors:rules.append(copy.deepcopy(prior))
    for bundle in bundles:
        if (bundle.get('catalog_sha256') != L.sha(L.POLICY) or bundle.get('catalog_version') != catalog['catalog_version'] or bundle.get('formal_base_archive_sha256') != catalog['formal_base_archive_sha256']):
            problems.append(issue('stale_bundle_catalog_or_formal_base', bundle_id=bundle['id']))
        for rule in bundle['proposals']:
            errors = rule_errors(rule, evidence, catalog); problems.extend(errors)
            if not errors: rules.append(copy.deepcopy(rule))
    by_id = {}
    for rule in rules: by_id.setdefault(rule['id'], []).append(rule)
    selected = []
    for rid, candidates in sorted(by_id.items()):
        revoked = [x for x in candidates if x['status']=='revoked' and any(a['kind']=='user' for a in x['authority'])]
        if revoked and any(x['status'] not in ('revoked','superseded') and x['revision']>=min(r['revision'] for r in revoked) for x in candidates): problems.append(issue('user_revoked_id_cannot_return', rule_id=rid))
        latest = max(x['revision'] for x in candidates)
        revisions = [x for x in candidates if x['revision']==latest]
        def semantic(x):
            result={k:x[k] for k in ('id','revision','cause_key','scope','conditions','prevention_actions','supersedes','status')}
            if result['status'] in ('active','candidate'):result['status']='effective'
            return result
        if len({L.digest(L.encoded(semantic(x))) for x in revisions}) != 1:
            problems.append(issue('same_revision_conflict', rule_id=rid)); continue
        chosen = copy.deepcopy(revisions[0])
        if any(x['status']=='active' for x in revisions) and any(x['status']=='candidate' and x.get('changes') for x in revisions):
            problems.append(issue('active_revision_requires_new_revision_for_patch',rule_id=rid))
        if len({x['revision'] for x in candidates}) > 1 and rid not in chosen['supersedes']:
            problems.append(issue('revision_requires_explicit_supersedes', rule_id=rid))
        selected.append(chosen)
    index = {x['id']:x for x in selected}; hidden=set()
    for rule in selected:
        for old in rule['supersedes']:
            if old==rule['id']: continue
            if old not in index: problems.append(issue('unknown_superseded_rule', rule_id=rule['id'], supersedes=old))
            elif cause_scope(rule)!=cause_scope(index[old]): problems.append(issue('supersedes_scope_mismatch', rule_id=rule['id'], supersedes=old))
            else: hidden.add(old)
    # Detect supersedes cycles, even if they would otherwise hide all rules.
    def cycle(rid, chain):
        if rid in chain:return True
        return any(old!=rid and old in index and cycle(old,chain|{rid}) for old in index[rid]['supersedes'])
    if any(cycle(rid,set()) for rid in index): problems.append(issue('supersedes_cycle'))
    active=[x for x in selected if x['id'] not in hidden and x['status'] not in ('revoked','superseded')]
    revoked=[x for x in selected if x['status']=='revoked' and any(a['kind']=='user' for a in x['authority'])]
    for rule in active:
        for prior in revoked:
            if overlaps(rule,prior) and any(tuple(a.get(k) for k in ('role','operation','target','check_id','decision'))==tuple(b.get(k) for k in ('role','operation','target','check_id','decision')) for a in rule['prevention_actions'] for b in prior['prevention_actions']):
                problems.append(issue('user_revoked_behavior_cannot_return_under_new_id',rule_id=rule['id'],revoked_id=prior['id']))
    for pos, rule in enumerate(active):
        for other in active[pos+1:]:
            if not overlaps(rule,other):continue
            for a in rule['prevention_actions']:
                for b in other['prevention_actions']:
                    same_subject=(a['role'],a['node'],a['target'],a['check_id'])==(b['role'],b['node'],b['target'],b['check_id'])
                    if same_subject and {a['decision'],b['decision']} & {'forbid'} and a['decision']!=b['decision']:
                        problems.append(issue('opposite_actions_under_same_conditions',rules=[rule['id'],other['id']],node=a['node']))
                    if (cause_scope(rule)!=cause_scope(other) and a['role']==b['role']=='producer' and a['operation']==b['operation']=='run_check' and a['decision']==b['decision']=='require' and (a['producer'],a['check_id'])==(b['producer'],b['check_id'])):
                        problems.append(issue('duplicate_execution_node',rules=[rule['id'],other['id']],check_id=a['check_id']))
    groups={}
    for rule in active:groups.setdefault(cause_scope(rule),[]).append(rule)
    merged=[]; execution={}; changes={}
    for key, members in sorted(groups.items()):
        actions={}
        for rule in members:
            for action in rule['prevention_actions']:
                semantic={k:v for k,v in action.items() if k!='id'}
                actions[L.digest(L.encoded(semantic))]=action
            for change in rule.get('changes',[]):
                try:
                    path=L.relative(change['path'])
                    if path.split('/')[0] not in catalog['allowed_skills'] or path.casefold() in {x.casefold() for x in catalog['protected_paths']}:raise ValueError('protected or unknown Skill path')
                    if before.get(path)!=change.get('before_sha256'):raise ValueError('stale patch baseline')
                    if change.get('after_sha256')!=L.digest(change['content'].encode('utf-8')):raise ValueError('patch content digest differs')
                    if path in changes and changes[path]!=change:raise ValueError('conflicting concurrent patches for one path')
                    changes[path]=change
                except (KeyError,TypeError,ValueError,AttributeError) as error:problems.append(issue('patch_candidate_refused',rule_id=rule['id'],error=str(error)))
        for action in actions.values():
            if action['role']=='producer' and action['operation']=='run_check' and action['decision']=='require':
                ek=(key,action['producer'],action['check_id'])
                if ek in execution:problems.append(issue('duplicate_execution_node',groups=[execution[ek],key],check_id=action['check_id']))
                execution[ek]=key
        merged.append(dict(cause_scope_key=key,member_ids=sorted(x['id'] for x in members),scope=members[0]['scope'],conditions=members[0]['conditions'],prevention_actions=list(actions.values()),rules=[{k:x[k] for k in ('id','revision','status','authority','supersedes','evidence','tests')} for x in members]))
    carried_rules=[]
    for item in selected:
        carried=copy.deepcopy(item)
        if carried['id'] in hidden and carried['status']!='revoked':carried['status']='superseded'
        carried_rules.append(carried)
    carried_evidence={}
    def retain_record(rid):
        record=evidence[rid];old=active_registry['evidence_index'].get(rid,{})
        hashes=set(old.get('raw_sha256s',[]))
        if 'raw_sha256' in record:hashes.add(record['raw_sha256'])
        return carried_evidence.setdefault(rid,dict(raw_sha256s=sorted(hashes),approved_outcomes=[],
            observed_success=observed_positive(record),observed_costs=sorted(observed_costs(record))))
    for rule in carried_rules:
        for ref in rule['evidence']:
            item=retain_record(ref['record_id'])
            if ref['outcome'] not in item['approved_outcomes']:item['approved_outcomes'].append(ref['outcome'])
        for test in rule['tests']:retain_record(test['record_id'])
    if tree_files(base)!=before:problems.append(issue('base_changed_during_planning'))
    return dict(schema=PLAN_SCHEMA,delivery_blocking=False,status='blocked_candidate' if problems else 'ready_for_review',blocked=bool(problems),
        catalog_version=catalog['catalog_version'],catalog_sha256=L.sha(L.POLICY),formal_base_archive_sha256=catalog['formal_base_archive_sha256'],
        active_registry=active_registry,registry_rules=carried_rules,registry_evidence=carried_evidence,
        base_identity=identity(before),base_files=before,bundle_ids=sorted(x['id'] for x in bundles),
        groups=merged,rule_ids=sorted(x['id'] for x in active),changes=[changes[p] for p in sorted(changes)],findings=problems,
        observations_retained=sum(len(x['observations']) for x in bundles),
        boundary='Maintenance candidates only. No game is blocked, no Skill CI/game test runs, and no rule is installed or uploaded.')


def audit(workspace, base, plan_path):
    proposed=json.loads(Path(plan_path).read_text());current=plan(workspace,base)
    findings=[]
    if proposed.get('schema')!=PLAN_SCHEMA or proposed!=current:findings.append(issue('stale_plan_or_concurrent_queue_change'))
    findings.extend(current['findings'])
    return dict(status='blocked_candidate' if findings else 'reviewable_candidate',blocked=bool(findings),delivery_blocking=False,
                findings=findings,plan_sha256=L.sha(plan_path),base_identity=current['base_identity'])


def apply(workspace, base, plan_path, review_path, candidate):
    workspace=L.safe_workspace(workspace);base=Path(base).resolve();candidate=Path(candidate)
    if any(x.is_symlink() for x in (candidate,*candidate.parents)):raise ValueError('candidate symlink refused')
    candidate=candidate.resolve();staging=workspace/'candidates'
    if not candidate.is_relative_to(staging) or candidate==staging or candidate.is_relative_to(base) or base.is_relative_to(candidate):
        raise ValueError('patches may only target a distinct workspace/candidates/<name>')
    plan_raw=Path(plan_path).read_bytes();review_raw=Path(review_path).read_bytes()
    proposed=json.loads(plan_raw);review=json.loads(review_raw);plan_sha=L.digest(plan_raw);review_sha=L.digest(review_raw)
    if (review.get('schema')!='production_learning_review.v1' or review.get('approved') is not True or review.get('scope')!='isolated_candidate_only'
            or review.get('plan_sha256')!=plan_sha or review.get('base_identity')!=proposed.get('base_identity')
            or set(review.get('approved_rule_ids',[]))!=set(proposed.get('rule_ids',[])) or not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip()):
        raise ValueError('exact reviewed plan, base and approved rule IDs are required')
    with L.database(workspace) as db:
        if L.sha(plan_path)!=plan_sha or L.sha(review_path)!=review_sha:raise ValueError('review inputs changed during approval consumption')
        # The queue cannot change while checking the plan and applying its files.
        rows=[L.validate_bundle(json.loads(x[0])) for x in db.execute('SELECT payload FROM bundles ORDER BY id')]
        if sorted(x['id'] for x in rows)!=proposed.get('bundle_ids'):raise ValueError('concurrent queue change; rebuild maintenance plan')
        if proposed.get('blocked') or L.sha(L.POLICY)!=proposed.get('catalog_sha256') or identity(tree_files(base))!=proposed.get('base_identity'):
            raise ValueError('blocked or stale reviewed candidate')
        # Recompute outside the SQLite transaction would race; validate the full
        # plan through a memory-only bundle provider under this same lock.
        if plan(workspace,base,_bundles=rows)!=proposed:raise ValueError('reviewed plan differs from current governance')
        new_registry=make_active(proposed,review,plan_sha,review_sha)
        registry_path=L.policy()['active_registry']
        expected=dict(proposed['base_files'])
        expected[registry_path]=L.digest(L.encoded(new_registry)+b'\n')
        expected.update({x['path']:x['after_sha256'] for x in proposed['changes']})
        existing=db.execute('SELECT candidate,identity FROM applied WHERE plan_sha=?',(plan_sha,)).fetchone()
        if existing:
            if existing[0]!=candidate.relative_to(workspace).as_posix() or tree_files(candidate)!=expected:raise ValueError('applied candidate changed; do not overwrite it')
            return dict(status='unchanged',blocked=False,delivery_blocking=False,plan_sha256=plan_sha,candidate=candidate.relative_to(workspace).as_posix())
        if candidate.exists():raise ValueError('isolated candidate already exists without this application receipt')
        temporary=staging/('.preparing-'+plan_sha[:24]);staging.mkdir(parents=True,exist_ok=True)
        if temporary.exists():raise ValueError('unfinished candidate requires inspection; no overwrite')
        try:
            shutil.copytree(base,temporary,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
            for change in proposed['changes']:
                target=L.local(temporary,change['path'],exists=False)
                if (L.sha(target) if target.is_file() else None)!=change['before_sha256']:raise ValueError('candidate input changed during patching')
                target.parent.mkdir(parents=True,exist_ok=True);target.write_text(change['content'],encoding='utf-8')
            L.atomic_json(temporary/registry_path,new_registry)
            if (tree_files(temporary)!=expected or tree_files(base)!=proposed['base_files'] or L.sha(plan_path)!=plan_sha or L.sha(review_path)!=review_sha):raise ValueError('source changed during candidate application')
            L.atomic_json(temporary/'.production-learning-application.json',dict(plan_sha256=plan_sha,review_sha256=review_sha,base_identity=proposed['base_identity'],rule_ids=proposed['rule_ids']))
            temporary.rename(candidate)
            db.execute('INSERT INTO applied VALUES (?,?,?)',(plan_sha,candidate.relative_to(workspace).as_posix(),identity(expected)))
        except Exception:
            if temporary.exists():shutil.rmtree(temporary)
            raise
    return dict(status='applied_to_isolated_candidate',blocked=False,delivery_blocking=False,plan_sha256=plan_sha,candidate=candidate.relative_to(workspace).as_posix(),checks_executed=0)
