"""Synthetic original observations with real validators, SQLite and scope providers.

No actual browser/game runs. Only the registered execution transport is replaced
by a synthetic observation producer; every shared evidence validator runs.
"""
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import audit_native_startup_renderer as renderer
import audit_final_package_startup as final
import audit_startup_contract as contract_tool
from audit_mobile_input import snapshot
import check_ledger as cl
import native_startup_ledger as startup
import project_qa
import regression_scope_gate as regression
import startup_scoped_evidence as scoped


class ScopedStartup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='startup scoped controls ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root / 'project'; self.project.mkdir()
        self.native = self.project / 'build/native'; self.native.mkdir(parents=True)
        self.web = self.project / 'build/web'; self.web.mkdir()
        (self.project / 'assets').mkdir()
        (self.project / 'assets/home.js').write_text('exports.home=1;')
        (self.project / 'assets/shop.png').write_bytes(b'unrelated source shop asset')
        (self.web / 'home.js').write_text('exports.home=1;')
        (self.web / 'shop.png').write_bytes(b'unrelated web shop asset')
        payload = {'game.js': b'require("./main.js");', 'main.js': b'exports.boot=1;',
            'adapter-min.js': b'exports.adapter=1;', 'cocos/cocos2d-js.js': b'exports.engine=1;',
            'assets/main/config.json': b'{"scenes":["Home"]}', 'game.json': b'{}',
            'art/home.png': b'actual synthetic home image', 'art/shop.png': b'not read until shop'}
        for name, data in payload.items():
            path = self.native / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        self.qa = self.project / 'qa'; self.qa.mkdir()
        self.runner = self.qa / 'runner.py'; self.runner.write_text('# synthetic transport identity; never executed\n')
        self.extension = self.qa / 'extension.py'
        self.extension.write_text('def validate(*args):\n    return None\n')
        self.provider = self.qa / 'scope.py'
        self.provider.write_text('''from pathlib import Path
import json
import check_ledger as cl
def derive_startup_scope(*,native,source,web,proof,raw,binding,project):
    trace=raw['startup_dependency_trace']
    data=json.loads((project/trace['path']).read_text())
    if data['native_reads']!=['game.js','main.js','adapter-min.js','cocos/cocos2d-js.js','assets/main/config.json','game.json','art/home.png']:
        raise ValueError('synthetic finite request domain changed')
    return {'schema':'startup-read-scope.v1','coverage':data['coverage'],
        'registered_runner':proof['execution']['registered_runner'],'control_profile':proof['control_profile'],
        'trace':trace,'inputs':{'native':list(data['native_reads']),
            'source':[n for n in cl.manifest(source,project=True) if n!='assets/shop.png'],
            'web':[n for n in cl.manifest(web) if n!='shop.png']}}
''')
        manifest = self.qa / 'manifest.json'
        manifest.write_text(json.dumps({'schema': 'cocos_project_qa.v1',
            'runners': {'fixture': {'path':'qa/runner.py', 'dependencies':[], 'timeout_seconds':10,
                'control_profile':'fixture_startup_scope'}},
            'validators': {'fixture_startup_scope': {'path':'qa/extension.py','dependencies':[]},
                scoped.PROVIDER:{'path':'qa/scope.py','dependencies':[]}}}))
        self.env = patch.dict(os.environ, {'COCOS_QA_TRUST_FILE': str(self.root / 'trust.json')})
        self.env.start(); self.addCleanup(self.env.stop)
        project_qa.register(self.project, manifest, reviewed=True)
        self.binding = {'source_sha256':snapshot(self.project)[2],
            'native_tree_sha256':renderer.digest(renderer.tree(self.native)),
            'web_tree_sha256':renderer.digest(renderer.tree(self.web)), 'build_tag':'original-v1'}
        coverage = sorted(scoped.COVERAGE)
        trace = {'binding':self.binding, 'native_tree_sha256':self.binding['native_tree_sha256'],
            'runner_sha256':renderer.sha(self.runner), 'coverage':coverage,
            'native_reads':['game.js','main.js','adapter-min.js','cocos/cocos2d-js.js','assets/main/config.json','game.json','art/home.png']}
        self.trace = self.qa / 'requests.json'; self.save(self.trace, trace)
        data = {'binding':self.binding,'native_tree_sha256':self.binding['native_tree_sha256'],
            'browser_canvas':{'native_api':True,'two_d_blocks_webgl':True,'fresh_webgl':True},
            'viewport':[390,844],'touch':1,'user_agent':'Synthetic Mobile',
            'engine_identity':{'game_run_original':True,'renderer_original':True,'canvas_get_context_original':True},
            'phase_order':['entry','adapter','renderer','scene'],'renderer':{'webgl_context':True},
            'scene':{'active':True,'name':'Home'},'passed':True,'errors':[],
            'business':{'home':{'visible':True,'required_assets_ready':True,'loading_overlay_gone':True,
                'play_interactable':True,'node_path':'Home','lifecycle_complete':True,'after_draw_observed':True,'at_ms':1},
                'play':{'touch':{'transport':'ego_page_cdp','at_ms':2},'level_ready':True,
                    'level_identity':'Level1','before':{'moving':False},'after':{'moving':True},'effect_at_ms':3}},
            'startup_dependency_trace':self.ref(self.trace)}
        self.raw = self.qa / 'raw.json'; self.save(self.raw, data)
        picture = self.qa / 'screen.png'; picture.write_bytes(b'\x89PNG\r\n\x1a\n' + b'x'*6000)
        self.proof = {'schema':'native_startup_renderer.v1','producer':'real_browser_native_entry',
            'binding':self.binding,'native_tree_sha256':self.binding['native_tree_sha256'],
            'inputs':[{'relative_path':n,'sha256':renderer.sha(self.native/n)} for n in payload if n!='art/shop.png'],
            'runner':{'path':str(self.runner),'sha256':renderer.sha(self.runner)},
            'raw':self.ref(self.raw),'screenshot':self.ref(picture),
            'control_profile':'fixture_startup_scope','execution':{'registered_runner':'fixture'}}
        self.proof_path = self.qa / 'proof.json'; self.save(self.proof_path, self.proof)
        self.contract = self.qa / 'startup.json'
        self.save(self.contract, {'tool':'audit_startup_contract','policy_version':2,'runtime_required':True,
            'passed':True,'failed':0,'binding':self.binding,'native':str(self.native),'project':str(self.project),
            'startup_renderer_report':{'path':str(self.proof_path),'sha256':renderer.sha(self.proof_path)}})
        self.assertEqual(renderer.validate(self.proof,self.native,self.binding,self.project), [])
        def observed(proof,native,binding,project,*,capture):
            self.assertEqual(renderer.validate(proof,native,binding,project), [])
            capture(self.proof_path,proof); return []
        with patch.object(renderer,'execute_registered',side_effect=observed) as transport:
            self.original = startup.replay(self.proof,self.native,self.binding,self.project)
        self.assertEqual(transport.call_count,1)

    def save(self,path,data): path.write_text(json.dumps(data,sort_keys=True))
    def ref(self,path): return {'path':path.relative_to(self.project).as_posix(),'sha256':renderer.sha(path)}
    def approve(self): return scoped.approve(self.project,self.native,self.contract,self.web)
    def formal28_record(self, *, invalid_actual=False):
        fixture=scoped.load(Path(__file__).parent/'test-fixtures/startup-formal28-tools.json')
        store=cl.Ledger(self.project)
        try:
            row=store.previous(startup.CHECK_ID)[0]
            original_key=cl.sha(row['binding'])
            row['binding']['tool_sha256']=fixture['tool_sha256']
            old_key=cl.sha(row['binding'])
            if invalid_actual:
                actual_path=Path(row['result']['raw_evidence'][0])
                invalid=scoped.load(actual_path);invalid['producer']='unknown_old_unvalidated_observer'
                self.save(actual_path,invalid)
                for ref in row['files']:
                    if Path(ref['path'])==actual_path:ref['sha256']=renderer.sha(actual_path)
            with store.db:
                store.db.execute('DELETE FROM records WHERE key=?',(original_key,))
                store.db.execute('INSERT INTO records VALUES(?,?,?)',(old_key,startup.CHECK_ID,cl.canonical(row)))
            return old_key,copy.deepcopy(row)
        finally:store.close()
    def current(self):
        return {'source_sha256':snapshot(self.project)[2], 'native_tree_sha256':renderer.digest(renderer.tree(self.native)),
            'web_tree_sha256':renderer.digest(renderer.tree(self.web)),'build_tag':'changed-v2'}

    def test_old_pass_approve_changed_unrelated_images_and_final_consumer_no_execution(self):
        before = self.contract.read_bytes(); approved = self.approve()
        self.assertFalse(approved['executed_renderer'])
        for path in (self.native/'art/shop.png',self.web/'shop.png',self.project/'assets/shop.png'):
            path.write_bytes(b'changed unrelated exact owned deferred asset')
        with patch.object(renderer,'execute_registered',side_effect=AssertionError('renderer replayed')), \
             patch.object(project_qa,'invoke',side_effect=AssertionError('scope helper invoked by consumer')):
            current = scoped.consume(self.project,self.native,self.contract,current_binding=self.current())
            self.assertEqual(current['observed_at'],self.original['observed_at'])
            self.assertEqual(current['original_binding'],self.binding)
            self.assertNotEqual(current['current_binding']['native_tree_sha256'],self.binding['native_tree_sha256'])
            # Exercise the actual official final consumer; Retry validator is an
            # independent existing contract, not the startup ownership exercise.
            retry = self.qa/'retry.json'; self.save(retry,{'synthetic_retry':True})
            with patch.object(final,'validate_recovery',return_value=[]):
                result=final.audit_final_startup(self.native,self.project,self.contract,retry,reuse_only=True)
            self.assertTrue(result['passed']); self.assertFalse(result['registered_renderer_replayed'])
            self.assertEqual(result['current_binding']['web_tree_sha256'],self.current()['web_tree_sha256'])
            replay=regression.startup_replay(self.proof,self.native,self.current(),self.project,reuse_only=True,plan_project=self.project)
            self.assertEqual(replay['action'],'reused')
        self.assertEqual(self.contract.read_bytes(),before)

    def test_preserved_exact_old_artifacts_can_register_after_current_art_change(self):
        old_native=self.root/'preserved native';shutil.copytree(self.native,old_native)
        old_source=self.root/'preserved source';(old_source/'assets').mkdir(parents=True)
        shutil.copytree(self.project/'assets',old_source/'assets',dirs_exist_ok=True)
        old_web=self.root/'preserved web';shutil.copytree(self.web,old_web)
        (self.native/'art/shop.png').write_bytes(b'new deferred art')
        (self.project/'assets/shop.png').write_bytes(b'new source art')
        (self.web/'shop.png').write_bytes(b'new web art')
        with patch.object(renderer,'execute_registered',side_effect=AssertionError('old import reran renderer')):
            result=scoped.approve(self.project,old_native,self.contract,old_web,source=old_source,
                                 target_native=self.native,target_web=self.web)
        self.assertEqual(result['status'],'startup_scope_registered')
        # Current Web must be the actual original logical Web location; import
        # source path is a preserved artifact, not the served candidate path.
        result=scoped.consume(self.project,self.native,self.contract)
        self.assertEqual(result['current_binding']['native_tree_sha256'],self.current()['native_tree_sha256'])
        self.assertEqual(result['current_binding']['web_tree_sha256'],self.current()['web_tree_sha256'])

    def test_actual_formal28_tool_identity_imports_original_observation_without_replay(self):
        old_key,before=self.formal28_record()
        # Exact reviewed scheduler compatibility may preserve this old identity;
        # either way the genuine formal tool row and original observation stay.
        fixture=scoped.load(Path(__file__).parent/'test-fixtures/startup-formal28-tools.json')
        self.assertEqual(before['binding']['tool_sha256'],fixture['tool_sha256'])
        with patch.object(renderer,'execute_registered',side_effect=AssertionError('old tool import replayed renderer')):
            self.approve()
        (self.native/'art/shop.png').write_bytes(b'changed deferred item')
        self.assertEqual(scoped.consume(self.project,self.native,self.contract)['action'],'reused')
        store=cl.Ledger(self.project)
        try:after=json.loads(store.db.execute('SELECT data FROM records WHERE key=?',(old_key,)).fetchone()[0])
        finally:store.close()
        self.assertEqual(before,after)

    def test_old_pass_with_unknown_actual_observer_cannot_bypass_current_semantics(self):
        self.formal28_record(invalid_actual=True)
        with self.assertRaisesRegex(ValueError,'current renderer semantics'):
            self.approve()

    def test_a_new_failure_for_current_native_outranks_old_scope_pass(self):
        self.approve();(self.native/'art/shop.png').write_bytes(b'new candidate art')
        conditions,tools=startup.identity(self.proof,self.native,self.project)
        conditions['native_tree_sha256']=self.current()['native_tree_sha256']
        store=cl.Ledger(self.project)
        try:
            plan=store.prepare(startup.CHECK_ID,{},conditions,tools,domain='startup')
            store.execute(plan,lambda:{'passed':False},lambda row:False)
        finally:store.close()
        with self.assertRaisesRegex(ValueError,'recorded failure'):
            scoped.consume(self.project,self.native,self.contract)

    def test_observed_home_resource_change_refuses_without_renderer(self):
        self.approve();(self.native/'art/home.png').write_bytes(b'changed actual startup asset')
        with self.assertRaisesRegex(ValueError,'affected dependencies: art/home.png'):
            scoped.consume(self.project,self.native,self.contract)

    def test_same_input_and_concurrent_approval_call_scope_provider_only_once(self):
        invoke=project_qa.invoke;calls=[]
        def observed(*args,**kwargs):
            if args[1]=='derive_startup_scope':calls.append(1)
            return invoke(*args,**kwargs)
        with patch.object(project_qa,'invoke',side_effect=observed):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(self.approve) for _ in range(2)]
                results=[future.result() for future in futures]
            again=self.approve()
        self.assertEqual(len(calls),1)
        self.assertEqual(sum(bool(item['reused']) for item in results),1)
        self.assertTrue(again['reused'])

    def test_original_producer_automatically_freezes_scope_without_second_renderer(self):
        output=self.qa/'new-producer-contract.json'
        argv=['audit_startup_contract.py','--runtime-only','--project',str(self.project),
            '--native',str(self.native),'--binding',str(self.contract),
            '--renderer-report',str(self.proof_path),'--scope-web',str(self.web),'--out',str(output)]
        with patch('sys.argv',argv),patch.object(renderer,'execute_registered',side_effect=AssertionError('producer replayed existing observation')),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(contract_tool.main(),0)
        self.assertTrue((self.project/scoped.HOME/(renderer.sha(output)+'.json')).is_file())
        self.assertEqual(scoped.consume(self.project,self.native,output)['action'],'reused')

    def test_registration_does_not_create_a_missing_original_execution(self):
        store=cl.Ledger(self.project)
        with store.db:store.db.execute('DELETE FROM records WHERE check_id=?',(startup.CHECK_ID,))
        store.close()
        with patch.object(renderer,'execute_registered',side_effect=AssertionError('import executed renderer')),self.assertRaisesRegex(ValueError,'original passing registered execution'):
            self.approve()

    def test_current_binding_cannot_relabel_different_web_or_source(self):
        self.approve()
        binding=self.current();binding['web_tree_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'actual Source/Native/Web'):
            scoped.consume(self.project,self.native,self.contract,current_binding=binding)
        (self.project/'assets/home.js').write_bytes(b'changed source startup consumer')
        with self.assertRaisesRegex(ValueError,'startup.source: affected dependencies'):
            scoped.consume(self.project,self.native,self.contract)

    def test_code_settings_and_new_names_do_not_inherit_old_scope(self):
        self.approve()
        for name in ('game.js','game.json','cocos/cocos2d-js.js'):
            path=self.native/name;before=path.read_bytes();path.write_bytes(before+b' ')
            with self.assertRaisesRegex(ValueError,'affected dependencies'):
                scoped.consume(self.project,self.native,self.contract)
            path.write_bytes(before)
        (self.native/'art/unknown.png').write_bytes(b'new unknown file')
        with self.assertRaisesRegex(ValueError,'names changed'):
            scoped.consume(self.project,self.native,self.contract)

    def test_environment_and_provider_changes_refuse_only_scope(self):
        self.approve()
        with patch.object(startup,'environment',return_value='changed actual environment'):
            with self.assertRaisesRegex(ValueError,'environment/consumer rules changed'):
                scoped.consume(self.project,self.native,self.contract)
        self.provider.write_text(self.provider.read_text()+'\n# changed reviewed ownership\n')
        with self.assertRaisesRegex(ValueError,'registered project QA file changed'):
            scoped.consume(self.project,self.native,self.contract)

    def test_changed_raw_evidence_and_failed_original_are_not_relabelled(self):
        self.approve()
        link=scoped.load(Path(self.project/scoped.HOME)/(renderer.sha(self.contract)+'.json'))
        store=cl.Ledger(self.project)
        row=json.loads(store.db.execute('SELECT data FROM records WHERE key=?',(link['record_key'],)).fetchone()[0]);store.close()
        Path(row['files'][0]['path']).write_bytes(b'corrupted frozen evidence')
        with self.assertRaisesRegex(ValueError,'original evidence missing or failed'):
            scoped.consume(self.project,self.native,self.contract)

    def test_complete_flag_without_original_trace_is_rejected(self):
        raw=scoped.load(self.raw);del raw['startup_dependency_trace'];self.save(self.raw,raw)
        proof=copy.deepcopy(self.proof);proof['raw']=self.ref(self.raw);self.save(self.proof_path,proof)
        contract=scoped.load(self.contract);contract['startup_renderer_report']['sha256']=renderer.sha(self.proof_path);self.save(self.contract,contract)
        with self.assertRaises((ValueError,KeyError)):
            self.approve()

    def test_scope_provider_cannot_omit_observed_or_executable_inputs(self):
        provider=project_qa.lookup(self.project,'validators',scoped.PROVIDER)
        roots={'native':self.native,'source':self.project,'web':self.web}
        actual={k:scoped.files(v,source=k=='source') for k,v in roots.items()}
        scope,_=scoped.derive_scope(provider,roots,self.proof,scoped.load(self.raw),self.binding,self.project,actual)
        scope['inputs']['native'].remove('art/home.png')
        with patch.object(project_qa,'invoke',return_value=scope), self.assertRaisesRegex(ValueError,'omits actual'):
            scoped.derive_scope(provider,roots,self.proof,scoped.load(self.raw),self.binding,self.project,actual)

    def test_input_moves_during_scope_registration_cannot_create_pass(self):
        invoke=project_qa.invoke
        def moving(*args,**kwargs):
            value=invoke(*args,**kwargs)
            if args[1]=='derive_startup_scope':
                (self.native/'art/shop.png').write_bytes(b'changed during registration')
            return value
        with patch.object(project_qa,'invoke',side_effect=moving),self.assertRaisesRegex(ValueError,'changed during approval'):
            self.approve()
        with self.assertRaisesRegex(ValueError,'original evidence missing or failed'):
            # The index must not have been published.
            if scoped.consume(self.project,self.native,self.contract) is None:
                raise ValueError('original evidence missing or failed')


if __name__=='__main__':unittest.main()
