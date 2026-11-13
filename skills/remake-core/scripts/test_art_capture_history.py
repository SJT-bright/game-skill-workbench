"""Entirely synthetic files/proofs. No browser, real game or production acceptance."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from uuid import uuid4
from PIL import Image
from art_case_dependencies import digest,file_sha,snapshot_views,affected_cases
import art_capture_history as H

HERE=Path(__file__).resolve().parent

class History(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.project=self.root/'project';self.build=self.root/'web';self.old=self.root/'old';self.new=self.root/'new'
        (self.project/'assets').mkdir(parents=True);(self.project/'docs/art').mkdir(parents=True);self.build.mkdir();self.old.mkdir();self.new.mkdir()
        (self.build/'index.html').write_text('<head></head>')
        self.text='cc.Class({home:function(){return 0;},popup:function(){return 1;},settings:function(){return 9;}});'
        self.write_source(self.text)
        self.cases=[dict(id=x,screen=x,kind='popup' if x!='home' else 'home',purpose=x,width=10,height=20,dpr=1,stable=False,anchor=x=='home',recipe='synthetic',environment='synthetic',witness=[{'path':'Canvas/X'}]) for x in ['home','popup','settings']]
        (self.project/'docs/art/capture-plan.json').write_text(json.dumps({'cases':self.cases}))
        methods=[dict(name=x,cases=[x],basis='explicit synthetic owner') for x in ['home','popup','settings']]
        self.contract={'schema':'art-case-dependencies.v1','cases':['home','popup','settings'],'files':[dict(unit='ui',domain=d,path=path,kind='methods',methods=methods) for d,path in [('source','assets/UI.js'),('export','UI.js')]]}
        self.contract['case_inputs']={c:{'mode':'origin_bound','basis':'synthetic constant-return UI; no time/random/network','external_inputs':[]} for c in self.contract['cases']}
        self.contract_path=self.root/'contract.json';self.contract_path.write_text(json.dumps(self.contract))
        self.start();self.baseline=self.root/'baseline.json';H.initialize(self.project,self.build,self.contract_path,self.baseline)
        for c in self.cases:self.capture(self.old,c)
    def write_source(self,text):
        (self.project/'assets/UI.js').write_text(text);(self.build/'UI.js').write_text(text)
    def start(self):
        p=subprocess.run(['node',str(HERE/'art_capture_round.mjs'),'start',str(self.project),str(self.build)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
    def capture(self,folder,case):
        active=H.read(H.store(self.project)/'current.json');uid=str(uuid4());png=folder/(case['id']+'.png');Image.new('RGB',(10,20),'white').save(png)
        d=dict(tool='ui_dump',schema=1,producer='ego_page.dump_ui',screen=case['screen'],kind=case['kind'],purpose=case['purpose'],viewport={'width':10,'height':20},screenshot=png.name,screenshot_sha256=file_sha(png),art_capture_id=uid,nodes=[{'path':'Canvas/X'}])
        file=folder/('capture-ui-dump-'+case['id']+'.json');file.write_text(json.dumps(d))
        proof=dict(id=uid,case=case['id'],caseHash=digest(case),version=active['version'],round=active['id'],session=str(uuid4()),timeOrigin=time.time()*1000+1000,env='e'*64,auxiliary=False,dump=file_sha(file),png=file_sha(png),reads=['index.html','UI.js'])
        (H.store(self.project)/'proofs').mkdir(exist_ok=True)
        (H.store(self.project)/'proofs'/(uid+'.json')).write_text(json.dumps(dict(proof,seal=digest(proof))))
    def transition(self):
        self.write_source(self.text.replace('return 1','return 2'));self.start()
        for c in self.cases[:2]:self.capture(self.new,c)
        manifest={'schema':H.SCHEMA,'project':str(self.project),'baseline':str(self.baseline),'baseline_sha256':file_sha(self.baseline),'base_dumps':str(self.old),'fresh_cases':['home','popup'],'quality_refs':[]}
        (self.new/H.MANIFEST).write_text(json.dumps(manifest));return manifest
    def test_same_version_old_round_needs_neither_art_pass_nor_second_png(self):
        self.start();r=H.verify(self.project,self.build,self.old)
        self.assertTrue(r['ready']);self.assertTrue(all(x['action']=='reuse' for x in r['cases']));self.assertFalse(r['quality_promoted'])
    def test_local_method_transition_preserves_originals_and_failure_quality(self):
        m=self.transition();q=self.root/'failed.json';q.write_text(json.dumps({'tool':'art_check','passed':False,'status':'fail','failed':1}))
        m['quality_refs']=[{'path':str(q),'sha256':file_sha(q)}];(self.new/H.MANIFEST).write_text(json.dumps(m))
        before={str(p):file_sha(p) for p in self.old.iterdir()};r=H.verify(self.project,self.build,self.new)
        self.assertTrue(r['ready']);self.assertEqual([x['action'] for x in r['cases']],['fresh','fresh','reuse'])
        self.assertEqual(Path(r['resolved_dumps'][2]).parent,self.old);self.assertFalse(r['quality_refs'][0]['original_passed'])
        self.assertEqual(before,{str(p):file_sha(p) for p in self.old.iterdir()})
        self.assertEqual(H.resolve_input_files(self.new),[Path(x) for x in r['resolved_dumps']])
        from art_round_check import run, artifact_hash
        self.assertEqual(run('verify',self.project,self.build,self.new)['resolved_dumps'],r['resolved_dumps'])
        self.assertEqual(len(artifact_hash(self.project,self.new)),64)
    def test_cannot_retrofit_contract_or_repair_tampered_png(self):
        self.transition();b=H.sealed(self.baseline);b['created_ms']=time.time()*1000+1e8
        self.baseline.write_text(json.dumps(dict(b,seal=digest(b))))
        m=H.read(self.new/H.MANIFEST);m['baseline_sha256']=file_sha(self.baseline);(self.new/H.MANIFEST).write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'not initialized before'):H.verify(self.project,self.build,self.new)
    def test_omitted_actual_affected_case_is_rejected(self):
        m=self.transition();m['fresh_cases']=['home'];(self.new/H.MANIFEST).write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'omits actual affected inputs'):H.verify(self.project,self.build,self.new)
    def test_changed_quality_and_png_rejected(self):
        self.transition();(self.old/'settings.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'dump/PNG changed'):H.verify(self.project,self.build,self.new)
    def test_shared_bytes_expand_once_instead_of_claiming_local(self):
        b=H.sealed(self.baseline);self.write_source('var shared=2;'+self.text)
        a=snapshot_views(self.contract,self.project,self.build)
        delta=affected_cases(self.contract,b['views'],a,{'source':['assets/UI.js'],'export':['UI.js']})
        self.assertEqual(set(delta['affected_cases']),set(self.contract['cases']));self.assertTrue(delta['shared_expansions'])
    def test_unknown_compiled_method_correspondence_rejected(self):
        b=H.sealed(self.baseline);(self.project/'assets/UI.js').write_text(self.text.replace('return 1','return 2'))
        a=snapshot_views(self.contract,self.project,self.build)
        d=affected_cases(self.contract,b['views'],a,{'source':['assets/UI.js'],'export':[]})
        self.assertTrue(d['unknown'])
    def test_unknown_dynamic_method_closure_rejected(self):
        b=H.sealed(self.baseline);self.write_source(self.text.replace('return 1','return this[name]'))
        a=snapshot_views(self.contract,self.project,self.build)
        d=affected_cases(self.contract,b['views'],a,{'source':['assets/UI.js'],'export':['UI.js']})
        self.assertTrue(d['unknown'])
    def test_declared_volatile_state_stays_fresh_even_if_its_code_is_unchanged(self):
        contract=copy.deepcopy(self.contract);contract['case_inputs']['settings']['mode']='fresh'
        views=snapshot_views(contract,self.project,self.build)
        self.assertEqual(affected_cases(contract,views,views,{'source':[],'export':[]})['affected_cases'],['settings'])
    def test_archived_bytes_cannot_be_replaced_by_a_claimed_projection(self):
        self.transition();b=H.sealed(self.baseline);b['owned_bytes']['source:assets/UI.js']='eA=='
        self.baseline.write_text(json.dumps(dict(b,seal=digest(b))))
        m=H.read(self.new/H.MANIFEST);m['baseline_sha256']=file_sha(self.baseline);(self.new/H.MANIFEST).write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'archived dependency bytes'):H.verify(self.project,self.build,self.new)
    def test_unrelated_bundle_classes_do_not_make_owner_container_ambiguous(self):
        self.write_source('cc.Class({start:function(){},update:function(){}});'+self.text+'cc.Class({start:function(){},update:function(){}});')
        views=snapshot_views(self.contract,self.project,self.build)
        self.assertFalse(views['source:assets/UI.js']['dynamic'])
    def test_tool_metadata_change_replays_archives_without_new_capture(self):
        self.transition();b=H.sealed(self.baseline);b['extractor_sha256']='0'*64
        self.baseline.write_text(json.dumps(dict(b,seal=digest(b))))
        m=H.read(self.new/H.MANIFEST);m['baseline_sha256']=file_sha(self.baseline);(self.new/H.MANIFEST).write_text(json.dumps(m))
        r=H.verify(self.project,self.build,self.new)
        self.assertTrue(r['ready']);self.assertTrue(r['dependency_verifier_chain']['archived_projections_replayed'])
        self.assertNotEqual(r['dependency_verifier_chain']['initialized'],r['dependency_verifier_chain']['current'])
        b['views']['source:assets/UI.js']['shared']='0'*64
        self.baseline.write_text(json.dumps(dict(b,seal=digest(b))));m['baseline_sha256']=file_sha(self.baseline);(self.new/H.MANIFEST).write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'historical dependency projection changed'):H.verify(self.project,self.build,self.new)
    def test_production_planner_reads_real_baseline_round_and_original_proofs(self):
        self.transition()
        args=['python3','-B',str(HERE/'art_change_plan.py'),'--project',str(self.project),'--build',str(self.build),
              '--baseline',str(self.baseline),'--base-dumps',str(self.old)]
        planned=subprocess.run(args,capture_output=True,text=True,check=True)
        p=json.loads(planned.stdout)
        self.assertFalse(p['build']['required']);self.assertTrue(p['capture']['required'])
        self.assertEqual(set(p['capture']['fresh_cases']),{'popup'})
        self.assertFalse(p['capture']['verified_current_ready'])
        checked=subprocess.run(args+['--dumps',str(self.new)],capture_output=True,text=True,check=True)
        p=json.loads(checked.stdout);self.assertFalse(p['capture']['required']);self.assertTrue(p['capture']['verified_current_ready'])
        self.assertEqual(Path(p['capture']['resolved_dumps'][2]).parent,self.old)
        (self.old/'settings.png').write_bytes(b'tampered')
        rejected=subprocess.run(args+['--dumps',str(self.new)],capture_output=True,text=True,check=True)
        p=json.loads(rejected.stdout);self.assertIsNone(p['capture']['required']);self.assertFalse(p['capture']['verified_current_ready'])
    def test_current_bound_analysis_does_not_repeat_for_retained_old_baseline(self):
        self.transition();history=H.verify(self.project,self.build,self.new)
        from art_check_record import TRIAL_GROUPS
        from art_change_plan import plan
        # Synthetic scheduling calibration only; no real art acceptance claimed.
        rows=[{'check':'fixture:'+group,'status':'通过','log':logs[0]} for group,logs in TRIAL_GROUPS.items() if group!='slots']
        rows.append({'check':'读到的页面','status':'通过'})
        report={'synthetic_fixture_only':True,'tool':'art_check','status':'pass','rows':rows,'checked':len(rows),'capture_round':history}
        _,_,_,_,_=H.current_context(self.project,self.build)
        state=json.loads(subprocess.run(['node',str(HERE/'art_capture_round.mjs'),'status',str(self.project),str(self.build)],capture_output=True,text=True,check=True).stdout)
        historical=H.transition_plan(self.project,self.build,self.baseline,self.old);rules={'checker.py':'f'*64}
        opts=dict(reports=[('synthetic-complete.json',report)],rule_hashes_before=rules,rule_hashes_after=rules,verified_history=history)
        self.assertFalse(plan(state,**opts)['analyze']['required'])
        self.assertFalse(plan(state,history_plan=historical,**opts)['analyze']['required'])
        report['capture_round']=dict(history,version='0'*64)
        self.assertTrue(plan(state,history_plan=historical,**opts)['analyze']['required'])
        report['capture_round']=history;rows[0]['status']='需处理'
        self.assertTrue(plan(state,history_plan=historical,**opts)['analyze']['required'])
    def test_second_local_repair_does_not_recapture_previous_fixed_page(self):
        self.transition();checkpoint=self.root/'checkpoint-B.json'
        H.initialize(self.project,self.build,self.contract_path,checkpoint,self.new)
        self.write_source(self.text.replace('return 1','return 2').replace('return 9','return 8'));self.start()
        newest=self.root/'third';newest.mkdir()
        for c in [self.cases[0],self.cases[2]]:self.capture(newest,c)
        m={'schema':H.SCHEMA,'project':str(self.project),'baseline':str(checkpoint),'baseline_sha256':file_sha(checkpoint),
           'base_dumps':str(self.new),'fresh_cases':['home','settings'],'quality_refs':[]}
        (newest/H.MANIFEST).write_text(json.dumps(m));r=H.verify(self.project,self.build,newest)
        self.assertTrue(r['ready']);self.assertEqual(Path(r['resolved_dumps'][1]).parent,self.new)
        self.assertEqual(r['cases'][1]['action'],'reuse')

    def test_local_method_change_requires_only_affected_case_without_unrelated_anchor(self):
        self.write_source(self.text.replace('return 1','return 2'));self.start()
        planned=H.transition_plan(self.project,self.build,self.baseline,self.old)
        self.assertEqual(planned['fresh_cases'],['popup']);self.assertEqual(planned['anchors'],[])
        self.capture(self.new,self.cases[1]);(self.new/H.MANIFEST).write_text(json.dumps(planned['manifest']))
        before={str(p):file_sha(p) for p in self.old.iterdir()}
        checked=H.verify(self.project,self.build,self.new)
        self.assertEqual([row['action'] for row in checked['cases']],['reuse','fresh','reuse'])
        self.assertEqual(before,{str(p):file_sha(p) for p in self.old.iterdir()})

    def test_no_change_transition_requires_no_capture_and_reuses_all_originals(self):
        self.start();planned=H.transition_plan(self.project,self.build,self.baseline,self.old)
        self.assertEqual(planned['fresh_cases'],[]);self.assertEqual(planned['anchors'],[])
        (self.new/H.MANIFEST).write_text(json.dumps(planned['manifest']))
        checked=H.verify(self.project,self.build,self.new)
        self.assertTrue(checked['ready']);self.assertTrue(all(row['action']=='reuse' for row in checked['cases']))

    def test_unmapped_file_is_scope_required_not_full_fresh_fallback(self):
        (self.project/'assets/New.js').write_text('var unmapped=1;');(self.build/'New.js').write_text('var unmapped=1;');self.start()
        planned=H.transition_plan(self.project,self.build,self.baseline,self.old)
        self.assertEqual(planned['status'],'scope_required');self.assertFalse(planned['ready'])
        self.assertFalse(planned['use_plain_current_capture']);self.assertEqual(planned['fresh_cases'],[])
        self.assertIsNone(planned['manifest']);self.assertTrue(planned['scope_gaps'])
        from art_change_plan import plan
        fake_status={'changes':{k:False for k in ('source','export','matrix','collector')},'current_round_version':'synthetic-current'}
        current=plan(fake_status,history_plan=planned)
        self.assertTrue(current['planning_blockers']);self.assertEqual(current['capture']['fresh_cases'],[])
        self.assertEqual(current['status'],'scope_required');self.assertIsNone(current['capture']['required'])
        self.assertIn('no capture authorized',current['capture']['scope'])
        self.assertFalse(current['capture']['verified_current_ready'])

    def test_explicit_changed_anchor_input_is_honored_without_global_anchor_quota(self):
        b=H.sealed(self.baseline);self.write_source(self.text.replace('return 1','return 2'))
        changed={'source':['assets/UI.js'],'export':['UI.js']}
        delta=H.dependency_impact(self.contract,b['views'],snapshot_views(self.contract,self.project,self.build),changed)
        contract=copy.deepcopy(self.contract)
        contract['case_inputs']['home']['anchor_dependencies']=[{'domain':'source','path':'assets/UI.js','basis':'synthetic viewport setup owner'}]
        old={c['id']:c for c in self.cases}
        required,anchors=H.required_cases(contract,old,self.cases,delta,changed)
        self.assertEqual(required,{'home','popup'});self.assertEqual(anchors,{'home'})
        required,anchors=H.required_cases(contract,old,self.cases,dict(delta,affected_cases=[]),{'source':[],'export':[]})
        self.assertEqual(required,set());self.assertEqual(anchors,set())

    def test_outside_owned_methods_needs_shared_scope_instead_of_all_cases(self):
        b=H.sealed(self.baseline);self.write_source('var uncertainShared=2;'+self.text);self.start()
        planned=H.transition_plan(self.project,self.build,self.baseline,self.old)
        self.assertEqual(planned['status'],'scope_required');self.assertEqual(planned['fresh_cases'],[])
        self.assertTrue(any('outside owned methods' in gap['reason'] for gap in planned['scope_gaps']))
        contract=copy.deepcopy(self.contract)
        for entry in contract['files']:
            entry['shared_cases']=['home'];entry['shared_basis']='synthetic known homepage-only module initializer'
        views=snapshot_views(contract,self.project,self.build)
        delta=H.dependency_impact(contract,b['views'],views,{'source':['assets/UI.js'],'export':['UI.js']})
        self.assertEqual(delta['unknown'],[]);self.assertEqual(delta['affected_cases'],['home'])

    def test_shared_owner_cannot_certify_source_only_stale_export(self):
        b=H.sealed(self.baseline);(self.project/'assets/UI.js').write_text('var shared=2;'+self.text)
        contract=copy.deepcopy(self.contract)
        for entry in contract['files']:
            entry['shared_cases']=['home'];entry['shared_basis']='synthetic homepage initializer'
        delta=H.dependency_impact(contract,b['views'],snapshot_views(contract,self.project,self.build),{'source':['assets/UI.js'],'export':[]})
        self.assertTrue(any('shared-byte changes do not correspond' in issue for issue in delta['unknown']))

if __name__=='__main__':unittest.main()
