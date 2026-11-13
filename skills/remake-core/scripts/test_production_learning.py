"""Portable collection/maintenance controls; synthetic projects only, no game or browser."""
import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parent))
import production_learning as L
import production_rule_governance as G


class Learning(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.project=self.root/'game';(self.project/'assets').mkdir(parents=True)
        self.workspace=self.root/'maintenance';self.base=self.root/'base';(self.base/'remake-core/scripts').mkdir(parents=True)
        (self.base/'remake-core/scripts/example.py').write_text('value = 1\n')
        self.samples=[dict(case='old',passed=False,elapsed_seconds=.2),dict(case='fixed',passed=True,elapsed_seconds=.3),dict(case='normal',passed=True,elapsed_seconds=.1)]
        self.ids=[L.digest(L.encoded(x)) for x in self.samples]

    def write(self,name,value):
        p=self.project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value));return p

    def rule(self,rid='RULE.STARTUP',cause='startup.exact-binding',role='producer'):
        node='startup.produce' if role=='producer' else 'writer.consume'
        return dict(id=rid,revision=1,status='candidate',title='title never determines identity',cause_key=cause,
            scope=dict(level='shared',applies=dict(engine=['2.x'],platform=['tiktok'],stage=['native'])),conditions=dict(inputs_changed=True),
            authority=[dict(kind='user',ref='user:current-task')],supersedes=[],generalization=dict(private_fields_removed=True,reviewed=True),
            prevention_actions=[dict(id='ACTION.CHECK',role=role,node=node,producer='startup.produce',consumers=['writer.consume'],
                operation='run_check' if role=='producer' else 'consume_evidence',target='startup.named-proof',check_id='STARTUP_01',decision='require'),
                dict(id='ACTION.PREVENT',role='prevention',node='source.prepare-proof',producer='source.prepare-proof',consumers=['startup.produce','writer.consume'],operation='prevent',target='startup.named-proof',check_id='STARTUP_01',decision='require')],
            evidence=[dict(record_id=rid,outcome=outcome) for rid,outcome in zip(self.ids,['failure','fixed','normal'])],
            tests=[dict(id='targeted-control',passed=True,cost_seconds=.3,record_id=self.ids[1])],changes=[])

    def bundle(self,rules=()):
        cat=L.policy();records=[dict(id=rid,source=f'docs/test-{i}.json',raw_sha256=L.digest(L.encoded(payload)),payload=payload) for i,(rid,payload) in enumerate(zip(self.ids,self.samples))]
        body=dict(schema=L.BUNDLE_SCHEMA,catalog_sha256=L.sha(L.POLICY),catalog_version=cat['catalog_version'],formal_base_archive_sha256=cat['formal_base_archive_sha256'],records=records,proposals=list(rules),observations=[])
        return dict(body,id=L.digest(L.encoded(body)),created_at=L.now())

    def imp(self,*rules):return L.import_bundle(self.workspace,self.bundle(rules))

    def codes(self,report):return {x['code'] for x in report['findings']}

    def plan_file(self):
        plan=G.plan(self.workspace,self.base);path=self.workspace/'plan.json';L.atomic_json(path,plan);return plan,path

    def review(self,plan,path):
        review=self.workspace/'review.json';L.atomic_json(review,dict(schema='production_learning_review.v1',approved=True,scope='isolated_candidate_only',plan_sha256=L.sha(path),base_identity=plan['base_identity'],approved_rule_ids=plan['rule_ids'],reviewer='local-maintainer'));return review

    def test_collector_idempotent_original_records_unchanged(self):
        p=self.write('docs/existing.json',dict(passed=True,path=str(self.project/'assets/a.png')));before=p.read_bytes()
        one=L.collect_nonblocking(self.project,[p],context=dict(delivery_ready=True,final_zip_sha256='a'*64));two=L.collect_nonblocking(self.project,[p],context=dict(delivery_ready=True,final_zip_sha256='a'*64))
        self.assertEqual(one['bundle_id'],two['bundle_id']);self.assertEqual(two['status'],'unchanged');self.assertFalse(two['delivery_blocking']);self.assertEqual(p.read_bytes(),before)
        data=json.loads((self.project/one['bundle']).read_text());self.assertNotIn(str(self.project),json.dumps(data));self.assertEqual(data['records'][0]['payload']['path'],'<project>/assets/a.png')

    def test_default_existing_stage_timer_and_package_issue_records_are_collected(self):
        paths=['docs/timing/stage-timing.jsonl','docs/timing/timing-summary.json','docs/test/package-issues.jsonl']
        payloads=[dict(event='stage_end',stage='art',elapsed_seconds=4.5),
                  dict(stages=[dict(stage='art',seconds=4.5)]),
                  dict(id='local.issue.1',status='open',message='recorded symptom only')]
        originals={}
        for name,payload in zip(paths,payloads):
            path=self.write(name,payload);originals[name]=path.read_bytes()
        result=L.collect_nonblocking(self.project)
        self.assertEqual(result['records'],3);self.assertFalse(result['delivery_blocking'])
        bundle=json.loads((self.project/result['bundle']).read_text())
        self.assertEqual({row['source'] for row in bundle['records']},set(paths))
        self.assertEqual(bundle['proposals'],[]);self.assertEqual(bundle['observations'],[])
        self.assertTrue(all((self.project/name).read_bytes()==raw for name,raw in originals.items()))

    def test_portable_bundle_import_needs_no_original_computer(self):
        p=self.write('docs/existing.json',dict(passed=True,seconds=.1));r=L.collect_nonblocking(self.project,[p]);packet=json.loads((self.project/r['bundle']).read_text())
        relocated=self.root/'new-machine/packet.json';relocated.parent.mkdir();L.atomic_json(relocated,packet)
        self.assertEqual(L.import_bundle(self.workspace,relocated)['status'],'imported');self.assertEqual(L.import_bundle(self.workspace,relocated)['status'],'unchanged')

    def test_confirmed_fix_requires_cause_delta_and_old_failure(self):
        good=dict(status='resumed',cause_key='storage.startup',fix='use one restored state',changes=[dict(before_sha256='a'*64,after_sha256='b'*64)],outcomes=['failure','fixed','normal'],prevention_stage='source')
        unknown=dict(good);unknown.pop('cause_key');self.write('docs/repair.json',[good,unknown]);result=L.collect_nonblocking(self.project,['docs/repair.json']);bundle=json.loads((self.project/result['bundle']).read_text())
        self.assertEqual([x['classification'] for x in bundle['observations']],['recorded_confirmed_fix','candidate_needs_cause_or_validation']);self.assertTrue(all(x['generalized'] is False for x in bundle['observations']));self.assertEqual(bundle['proposals'],[])

    def test_collector_failure_and_external_path_never_block_delivery(self):
        p=self.write('docs/good.json',dict(passed=True));outside=self.root/'outside.json';outside.write_text('{}')
        rejected=L.collect_nonblocking(self.project,[outside]);self.assertFalse(rejected['delivery_blocking']);self.assertEqual(rejected['records'],0)
        with mock.patch.object(L,'atomic_json',side_effect=PermissionError('read-only outbox')):
            failed=L.collect_nonblocking(self.project,[p])
        self.assertEqual(failed['status'],'error');self.assertFalse(failed['delivery_blocking']);self.assertTrue(p.is_file())

    def test_collector_busy_queue_keeps_portable_outbox(self):
        p=self.write('docs/good.json',dict(passed=True));self.workspace.mkdir();db=sqlite3.connect(self.workspace/'learning.sqlite3',isolation_level=None);db.execute('BEGIN IMMEDIATE')
        try:result=L.collect_nonblocking(self.project,[p],queue_dir=self.workspace)
        finally:db.rollback();db.close()
        self.assertEqual(result['status'],'deferred');self.assertFalse(result['delivery_blocking']);self.assertTrue((self.project/result['bundle']).is_file())

    def test_large_file_and_total_budget_defer_without_unbounded_read(self):
        large=self.project/'docs/large.json';large.parent.mkdir();large.open('wb').close()
        with large.open('r+b') as stream:stream.truncate(L.MAX_BYTES+1)
        result=L.collect_nonblocking(self.project,[large])
        self.assertEqual(result['status'],'deferred');self.assertEqual(result['read_bytes'],0);self.assertFalse(result['delivery_blocking'])
        a=self.write('docs/a.json',dict(value='a'*60));b=self.write('docs/b.json',dict(value='b'*60))
        with mock.patch.object(L,'MAX_BYTES',100),mock.patch.object(L,'MAX_TOTAL_BYTES',100):
            result=L.collect_nonblocking(self.project,[a,b])
        self.assertEqual(result['records'],1);self.assertEqual(result['status'],'deferred');self.assertLessEqual(result['read_bytes'],100)
        with mock.patch.object(L,'MAX_RECORDS',1):result=L.collect_nonblocking(self.project,[a,b])
        self.assertEqual(result['records'],1);self.assertEqual(result['deferred_records'],1)

    def test_concurrent_queue_deduplicates_exact_bundle(self):
        packet=self.bundle([self.rule()])
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:L.import_bundle(self.workspace,packet),range(8)))
        self.assertEqual(sum(x['status']=='imported' for x in results),1)
        with L.database(self.workspace) as db:self.assertEqual(db.execute('SELECT count(*) FROM bundles').fetchone()[0],1)

    def test_same_cause_scope_merges_without_title_similarity(self):
        first=self.rule('RULE.A');other=self.rule('RULE.B');other['title']='completely unrelated title';other['prevention_actions'][0]['id']='OTHER.ACTION';self.imp(first,other)
        result=G.plan(self.workspace,self.base);self.assertFalse(result['blocked'],result);self.assertEqual(len(result['groups']),1);self.assertEqual(len(result['groups'][0]['prevention_actions']),2);self.assertEqual(result['groups'][0]['member_ids'],['RULE.A','RULE.B'])

    def test_opposite_actions_and_duplicate_execution_block_candidate_only(self):
        first=self.rule('RULE.A');opposite=self.rule('RULE.B',cause='other.cause');opposite['prevention_actions'][0]['decision']='forbid';self.imp(first,opposite);p=G.plan(self.workspace,self.base)
        self.assertIn('opposite_actions_under_same_conditions',self.codes(p));self.assertFalse(p['delivery_blocking'])
        separate=self.root/'separate';L.import_bundle(separate,self.bundle([first,self.rule('RULE.C',cause='different.cause')]))
        self.assertIn('duplicate_execution_node',self.codes(G.plan(separate,self.base)))

    def test_producer_and_writer_consumer_are_legitimate_different_roles(self):
        self.imp(self.rule('RULE.PRODUCER'),self.rule('RULE.CONSUMER',role='consumer'));p=G.plan(self.workspace,self.base);self.assertFalse(p['blocked'],p);self.assertEqual(len(p['groups'][0]['prevention_actions']),3)

    def test_overlapping_scope_duplicate_producer_is_not_hidden_by_scope_spelling(self):
        broad=self.rule('RULE.BROAD',cause='broad.cause');narrow=self.rule('RULE.NARROW',cause='narrow.cause')
        broad['scope']['applies'].pop('engine');self.imp(broad,narrow)
        self.assertIn('duplicate_execution_node',self.codes(G.plan(self.workspace,self.base)))

    def test_valid_rule_stale_patch_base_is_a_maintenance_block(self):
        r=self.rule();r['changes']=[dict(path='remake-core/scripts/example.py',before_sha256='0'*64,after_sha256=L.digest(b'x'),content='x')]
        self.imp(r);p=G.plan(self.workspace,self.base)
        self.assertIn('patch_candidate_refused',self.codes(p));self.assertFalse(p['delivery_blocking'])

    def test_four_protected_behaviors_cannot_return(self):
        rules=[]
        for index,row in enumerate(L.policy()['protected_behaviors']):
            r=self.rule('RULE.RESTORE'+str(index),cause='restore.'+str(index));r['prevention_actions'][0]['target']=row['targets'][0];rules.append(r)
        self.imp(*rules);p=G.plan(self.workspace,self.base);self.assertEqual(len([x for x in p['findings'] if x['code']=='revoked_behavior_cannot_return']),4)

    def test_user_revoked_id_and_behavior_do_not_reactivate(self):
        old=self.rule('RULE.OLD');old['status']='revoked';again=copy.deepcopy(old);again.update(status='candidate',revision=2,supersedes=['RULE.OLD']);self.imp(old,again)
        self.assertIn('user_revoked_id_cannot_return',self.codes(G.plan(self.workspace,self.base)))
        other=self.root/'revoked-other';new=self.rule('RULE.NEW',cause='renamed.cause');L.import_bundle(other,self.bundle([old,new]))
        self.assertIn('user_revoked_behavior_cannot_return_under_new_id',self.codes(G.plan(other,self.base)))

    def test_unknown_scope_private_facts_and_unbound_cost_stay_candidate(self):
        r=self.rule();r['scope']=dict(level='project',applies=dict(engine=['this-game']));r['generalization']=dict(private_fields_removed=False,reviewed=False);r['tests'][0]['cost_seconds']=999
        self.imp(r);p=G.plan(self.workspace,self.base);codes=self.codes(p);self.assertIn('unknown_or_project_specific_scope',codes);self.assertIn('private_facts_not_reviewed_for_generalization',codes);self.assertIn('test_result_or_cost_not_bound_to_original_record',codes)

    def test_old_catalog_wrong_evidence_and_stale_baseline_refuse(self):
        r=self.rule();r['evidence'][0]['outcome']='normal';r['changes']=[dict(path='remake-core/scripts/example.py',before_sha256='0'*64,after_sha256=L.digest(b'x'),content='x')]
        packet=self.bundle([r]);packet['catalog_version']='old';packet['id']=L.digest(L.encoded(L.bundle_body(packet)));L.import_bundle(self.workspace,packet)
        codes=self.codes(G.plan(self.workspace,self.base));self.assertIn('stale_bundle_catalog_or_formal_base',codes);self.assertIn('evidence_outcome_does_not_match_original_record',codes)

    def test_reviewed_patch_applies_only_isolated_and_is_idempotent(self):
        r=self.rule();content='value = 2\n';r['changes']=[dict(path='remake-core/scripts/example.py',before_sha256=L.sha(self.base/'remake-core/scripts/example.py'),after_sha256=L.digest(content.encode()),content=content)];self.imp(r)
        plan,path=self.plan_file();self.assertFalse(plan['blocked'],plan);review=self.review(plan,path);target=self.workspace/'candidates/reviewed'
        first=G.apply(self.workspace,self.base,path,review,target);second=G.apply(self.workspace,self.base,path,review,target)
        self.assertEqual(first['status'],'applied_to_isolated_candidate');self.assertEqual(second['status'],'unchanged');self.assertEqual((target/'remake-core/scripts/example.py').read_text(),content);self.assertEqual((self.base/'remake-core/scripts/example.py').read_text(),'value = 1\n')
        with self.assertRaises(ValueError):G.apply(self.workspace,self.base,path,review,self.root/'live')

    def test_concurrent_queue_or_source_change_invalidates_plan(self):
        self.imp(self.rule());plan,path=self.plan_file();review=self.review(plan,path);self.imp(self.rule('RULE.OTHER',cause='other.cause',role='consumer'))
        self.assertTrue(G.audit(self.workspace,self.base,path)['blocked'])
        with self.assertRaises(ValueError):G.apply(self.workspace,self.base,path,review,self.workspace/'candidates/nope')
        (self.base/'remake-core/scripts/example.py').write_text('external change')
        self.assertTrue(G.audit(self.workspace,self.base,path)['blocked'])

    def test_patch_traversal_symlink_and_protected_catalog_refused(self):
        for index,path in enumerate(['../escape.py','remake-core/assets/production-learning-policy.json']):
            r=self.rule('RULE.BAD'+str(index));r['changes']=[dict(path=path,before_sha256=None,after_sha256=L.digest(b'x'),content='x')];work=self.root/('bad'+str(index));L.import_bundle(work,self.bundle([r]));self.assertIn('patch_candidate_refused',self.codes(G.plan(work,self.base)))
        (self.base/'link').symlink_to(self.root)
        with self.assertRaises(ValueError):G.plan(self.workspace,self.base)

    def test_supersedes_is_explicit_and_same_revision_conflict_is_not_last_writer_wins(self):
        r=self.rule();other=copy.deepcopy(r);other['prevention_actions'][0]['target']='different-target';self.imp(r,other)
        self.assertIn('same_revision_conflict',self.codes(G.plan(self.workspace,self.base)))
        work=self.root/'revision';new=self.rule();new['revision']=2;L.import_bundle(work,self.bundle([r,new]));self.assertIn('revision_requires_explicit_supersedes',self.codes(G.plan(work,self.base)))

    def test_cli_collect_failure_is_zero_and_maintenance_protocol_is_real(self):
        tool=Path(L.__file__)
        failed=subprocess.run([sys.executable,'-B',str(tool),'collect','--project',str(self.root/'missing')],capture_output=True,text=True,check=True)
        self.assertFalse(json.loads(failed.stdout)['delivery_blocking'])
        bundle=self.root/'bundle.json';L.atomic_json(bundle,self.bundle([self.rule()]))
        imported=subprocess.run([sys.executable,'-B',str(tool),'import','--workspace',str(self.workspace),'--bundle',str(bundle)],capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(imported.stdout)['status'],'imported')
        plan=self.workspace/'plan.json'
        subprocess.run([sys.executable,'-B',str(tool),'plan','--workspace',str(self.workspace),'--base',str(self.base),'--out',str(plan)],capture_output=True,text=True,check=True)
        checked=subprocess.run([sys.executable,'-B',str(tool),'audit','--workspace',str(self.workspace),'--base',str(self.base),'--plan',str(plan)],capture_output=True,text=True,check=True)
        self.assertFalse(json.loads(checked.stdout)['blocked'])

    def test_checks_without_production_prevention_remain_candidate(self):
        good=self.rule('RULE.GOOD');check_only=self.rule('RULE.CHECKONLY',cause='other.check-only')
        check_only['prevention_actions']=check_only['prevention_actions'][:1]
        self.imp(good,check_only);result=G.plan(self.workspace,self.base)
        self.assertIn('production_prevention_or_explicit_external_limit_required',self.codes(result))
        self.assertFalse(result['delivery_blocking'])
        work=self.root/'good';L.import_bundle(work,self.bundle([good]));self.assertFalse(G.plan(work,self.base)['blocked'])
        limited=copy.deepcopy(check_only);limited['prevention_limit']=dict(external_condition='host storage unavailable',why_not_preventable='Host availability is outside source generation',earliest_recovery_node='startup.restore',recovery_action='Restore readable state in memory and defer optional writes',strategy='degrade')
        other=self.root/'external';L.import_bundle(other,self.bundle([limited]));self.assertFalse(G.plan(other,self.base)['blocked'])

    def test_active_registry_survives_fresh_workspace_conflict_synonym_and_revocation(self):
        original=self.rule('RULE.ACTIVE');self.imp(original);first,path=self.plan_file();review=self.review(first,path)
        base2=self.workspace/'candidates/version1';G.apply(self.workspace,self.base,path,review,base2)
        registry_path=base2/L.policy()['active_registry'];active=json.loads(registry_path.read_text())
        self.assertEqual(active['rules'][0]['status'],'active');self.assertEqual(active['evidence_index'][self.ids[2]]['approved_outcomes'],['normal'])
        self.assertNotIn('payload',active['evidence_index'][self.ids[2]])
        self.assertNotIn('observations',active);self.assertEqual(active['structural_principles'],L.policy()['structural_principles'])
        opposite=self.rule('RULE.OPPOSITE',cause='new.cause');opposite['prevention_actions'][0]['decision']='forbid'
        fresh=self.root/'new-computer-conflict';L.import_bundle(fresh,self.bundle([opposite]))
        self.assertIn('opposite_actions_under_same_conditions',self.codes(G.plan(fresh,base2)))
        synonym=self.rule('RULE.SYNONYM');synonym['prevention_actions'][0]['id']='ANOTHER.ACTION'
        fresh=self.root/'new-computer-synonym';L.import_bundle(fresh,self.bundle([synonym]));merged=G.plan(fresh,base2)
        self.assertFalse(merged['blocked'],merged);self.assertEqual(len(merged['groups']),1);self.assertEqual(len(merged['groups'][0]['prevention_actions']),2)
        # Revoke in a new maintenance workspace; the next computer must retain it.
        revoked=copy.deepcopy(original);revoked.update(status='revoked',revision=2,supersedes=['RULE.ACTIVE'])
        work=self.root/'revocation';L.import_bundle(work,self.bundle([revoked]));p=G.plan(work,base2);self.assertFalse(p['blocked'],p)
        pf=work/'plan.json';L.atomic_json(pf,p);rf=work/'review.json';L.atomic_json(rf,dict(schema='production_learning_review.v1',approved=True,scope='isolated_candidate_only',plan_sha256=L.sha(pf),base_identity=p['base_identity'],approved_rule_ids=p['rule_ids'],reviewer='local-reviewer'))
        base3=work/'candidates/version2';G.apply(work,base2,pf,rf,base3)
        next_work=self.root/'next-machine';new=self.rule('RULE.RENAMED',cause='new.name');L.import_bundle(next_work,self.bundle([new]))
        self.assertIn('user_revoked_behavior_cannot_return_under_new_id',self.codes(G.plan(next_work,base3)))
        # Payloads cannot overwrite the generated registry or fabricate a pass index.
        evil=self.rule('RULE.OVERRIDE');evil['changes']=[dict(path=L.policy()['active_registry'],before_sha256=L.sha(registry_path),after_sha256=L.digest(b'{}'),content='{}')]
        other=self.root/'override';L.import_bundle(other,self.bundle([evil]));self.assertIn('patch_candidate_refused',self.codes(G.plan(other,base2)))
        registry_path.unlink()
        with self.assertRaisesRegex(ValueError,'active registry missing'):G.plan(fresh,base2)

    def test_live_install_location_and_delivery_context_path_are_refused(self):
        with mock.patch.object(L.Path,'home',return_value=self.root):
            with self.assertRaises(ValueError):L.import_bundle(self.root/'.codex/skills',self.bundle())
        result=L.collect_nonblocking(self.project,[],context=dict(delivery_ready=True,external_path='/another/computer'))
        self.assertEqual(result['status'],'error');self.assertFalse(result['delivery_blocking'])


if __name__=='__main__':unittest.main()
