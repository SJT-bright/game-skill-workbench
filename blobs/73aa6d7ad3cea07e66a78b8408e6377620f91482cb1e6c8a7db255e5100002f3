#!/usr/bin/env python3
"""Actual source mutations + Node loader + Native byte calibration, no games/browser/ZIP."""
import concurrent.futures
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import resource_package_prepare as R
from test_first_screen_budget import Fixture


class ResourcePreparation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)/'project';self.fx=Fixture(self.p)
    def base(self,version='2.4.15',resources=10000,code=None):
        self.fx.bundle('resources',sub=False)
        self.fx.image('resources/ui/icon.png',resources)
        script=self.fx.script('scripts/Home.js',code or 'cc.Class({extends:cc.Component,play:function(){return 7;}});')
        u=self.fx.serialized('scenes/Home.fire','scene',scripts=[script]);self.fx.save_builder(u)
        (self.p/'project.json').write_text(json.dumps({'version':version}))
        return self.p
    def group_plan(self):
        return {'schema':R.PLAN_SCHEMA,'bundles':[],'deferred_groups':[{'source':'assets/resources/levels','destination':'assets/levels','name':'levels'}]}
    def group(self,code=None):
        self.base(code=code or "cc.Class({extends:cc.Component,play:function(){cc.resources.load('levels/card',cc.SpriteFrame,function(e,x){console.log(x);});return 7;}});")
        self.fx.image('resources/levels/card.png',5_000_000)
        self.fx.meta('resources/levels',{'uuid':'folder-stays-exact','ver':'1.1.2','custom':3,'compressionType':{'wechatgame':'merge_all_json'},'subMetas':{}})
    def assert_prepared(self,r):self.assertTrue(r['passed'],r);self.assertEqual(r['status'],'prepared');self.assertEqual(r['blocks'],[])
    def native(self,size=1000,extra=None):
        n=Path(self.tmp.name)/'native';n.mkdir(exist_ok=True)
        files={'game.js':b"require('./main');",'game.json':json.dumps({'subpackages':[{'name':'resources','root':'subpackages/resources/'}]}).encode(),
               'project.config.json':b'{"appid":"ttfixture"}','main.js':(self.p/'build-templates/bytedance/main.js').read_bytes() if (self.p/'build-templates/bytedance/main.js').exists() else b"tt.loadSubpackage({name:'resources',success:function(){cc.assetManager.loadBundle('resources',function(){});}});",
               'cocos2d-js-min.js':b'engine2','subpackages/resources/game.js':b'void 0;', 'subpackages/resources/data.bin':b'x'*size}
        if extra:files.update(extra)
        for rel,data in files.items():q=n/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
        return n
    def test_old_unbundled_resources_applied_uuid_and_other_platform_unchanged(self):
        self.base(resources=3_000_000);m=self.p/'assets/resources.meta';before=json.loads(m.read_text());before['compressionType']['wechatgame']='merge_all_json';m.write_text(json.dumps(before))
        asset=(self.p/'assets/resources/ui/icon.png.meta').read_bytes();r=R.prepare(self.p);self.assert_prepared(r)
        after=json.loads(m.read_text());self.assertEqual(after['uuid'],before['uuid']);self.assertEqual(after['compressionType']['wechatgame'],'merge_all_json');self.assertEqual(after['compressionType']['bytedance'],'subpackage')
        self.assertEqual((self.p/'assets/resources/ui/icon.png.meta').read_bytes(),asset)
        self.assertLess(r['budget']['main']['bytes'],4_000_000);self.assertGreater(r['budget']['first_download']['bytes'],3_000_000)
        self.assertTrue((self.p/'build-templates/bytedance/storage-guard.js').is_file())
    def test_same_input_and_concurrent_calls_do_not_repeat_analysis(self):
        self.base();original=R.first_screen.analyze
        with patch.object(R.first_screen,'analyze',wraps=original) as count:
            with concurrent.futures.ThreadPoolExecutor(2) as ex:r=list(ex.map(lambda _:R.prepare(self.p),range(2)))
            self.assertEqual(count.call_count,2) # before and after exactly one preparation
        self.assertEqual(sorted(x['reused'] for x in r),[False,True]);self.assertTrue(all(x['passed'] for x in r))
    def test_existing_legal_bundle_config_bytes_not_rewritten(self):
        self.base();m=self.p/'assets/resources.meta';d=json.loads(m.read_text());d['compressionType']['bytedance']='subpackage';m.write_text(json.dumps(d,indent=4));before=m.read_bytes()
        self.assert_prepared(R.prepare(self.p));self.assertEqual(m.read_bytes(),before)
    def test_whole_deferred_group_move_preserves_assets_and_real_loader_callback(self):
        self.group();before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.p/'assets/resources/levels').iterdir()}
        r=R.prepare(self.p,self.group_plan());self.assert_prepared(r)
        for name,digest in before.items():self.assertEqual(hashlib.sha256((self.p/'assets/levels'/name).read_bytes()).hexdigest(),digest)
        self.assertEqual(json.loads((self.p/'assets/levels.meta').read_text())['uuid'],'folder-stays-exact')
        self.assertIn('return 7;', (self.p/'assets/scripts/Home.js').read_text())
        runner="""let loads=0,paths=[];global.cc={resources:{load(){throw Error('wrong main route')}},assetManager:{getBundle(){return null},loadBundle(n,cb){loads++;if(n!=='levels')throw Error(n);cb(null,{load(p,t,cb){paths.push(p);cb(null,{value:7});}})}}};const a=require(process.argv[1]);let done=0;for(let i=0;i<2;i++)a.load('levels/card',function SpriteFrame(){},(e,x)=>{if(e||x.value!==7)throw e||Error('bad');if(++done===2){if(loads!==1||paths.join(',')!=='card,card')throw Error(JSON.stringify({loads,paths}));console.log('route-and-shared-loader-pass');}});"""
        proc=subprocess.run(['node','-e',runner,str(self.p/R.ADAPTER)],text=True,capture_output=True,timeout=5);self.assertEqual(proc.returncode,0,proc.stderr);self.assertIn('route-and-shared-loader-pass',proc.stdout)
        self.assertTrue(R.prepare(self.p,self.group_plan())['reused'])
    def test_new_resource_follows_existing_group_ownership(self):
        self.group();self.assert_prepared(R.prepare(self.p,self.group_plan()));self.fx.image('resources/levels/new.png',20000)
        before=(self.p/'assets/resources/levels/new.png.meta').read_bytes();r=R.prepare(self.p);self.assert_prepared(r)
        self.assertEqual((self.p/'assets/levels/new.png.meta').read_bytes(),before);self.assertFalse((self.p/'assets/resources/levels/new.png').exists())
    def test_dynamic_domain_returns_exact_mapping_without_mutation(self):
        self.group("cc.Class({extends:cc.Component,play:function(){cc.resources.load(window.name,cc.SpriteFrame,function(){});}});")
        before=R.inputs(self.p);r=R.prepare(self.p,self.group_plan());self.assertFalse(r['passed']);self.assertEqual(before,R.inputs(self.p));self.assertTrue(any(x['task']=='dynamic_resource_domain' and x['source']=='assets/scripts/Home.js' for x in r['tasks']));self.assertIn('current_agent',r['next_action'])
    def test_group_requested_before_home_cannot_be_marked_deferred(self):
        self.group("cc.Class({extends:cc.Component,onLoad:function(){cc.resources.loadDir('levels',cc.SpriteFrame,function(){});}});")
        before=R.inputs(self.p);r=R.prepare(self.p,self.group_plan());self.assertFalse(r['passed']);self.assertEqual(before,R.inputs(self.p));self.assertTrue(any(x['task']=='group_requested_before_home' for x in r['tasks']))
    def test_first_download_and_main_are_separate_budgets(self):
        self.base(resources=9*1024*1024);r=R.prepare(self.p);self.assertFalse(r['passed']);self.assertTrue(r['budget']['main']['passed']);self.assertFalse(r['budget']['first_download']['passed']);self.assertGreater(R.startup_budget.load(self.p)['summary']['first_download_bytes'],R.FIRST_LIMIT)
    def test_custom_boot_is_not_overwritten_and_is_mapping_task(self):
        self.base();p=self.p/'build-templates/bytedance/main.js';p.parent.mkdir(parents=True);p.write_text('custom gameplay bootstrap');before=R.inputs(self.p);r=R.prepare(self.p);self.assertFalse(r['passed']);self.assertEqual(R.inputs(self.p),before);self.assertTrue(any(x['task']=='boot_integration' for x in r['tasks']))
    def test_independent_is_not_invented_from_ordinary_bundle(self):
        self.base();r=R.prepare(self.p,{'schema':R.PLAN_SCHEMA,'deferred_groups':[],'bundles':[{'directory':'assets/resources','name':'resources','load':'startup','independent':True}]});self.assertFalse(r['passed']);self.assertTrue(any(x['task']=='independent_entry' for x in r['tasks']))
    def test_first_native_allows_normal_subpackage_over_four_megabytes_and_reuses(self):
        self.base();self.assert_prepared(R.prepare(self.p));n=self.native(5_000_000);r=R.calibrate(self.p,n);self.assertTrue(r['passed'],r);self.assertGreater(next(iter(r['actual']['normal_subpackages'].values())),4_000_000);self.assertTrue(R.calibrate(self.p,n)['reused'])
    def test_actual_native_first_download_failure_is_not_estimate_pass(self):
        self.base();self.assert_prepared(R.prepare(self.p));r=R.calibrate(self.p,self.native(10*1024*1024));self.assertFalse(r['passed']);self.assertIn('actual first download',str(r['blocks']))
    def test_independent_native_limit_and_wrong_key_are_rejected(self):
        self.base();self.assert_prepared(R.prepare(self.p));n=self.native();g=n/'game.json';game=json.loads(g.read_text());game['subpackages'].append({'name':'ind','root':'subpackages/ind','independent':True});g.write_text(json.dumps(game));p=n/'subpackages/ind';p.mkdir();(p/'game.js').write_text('void 0;');(p/'data').write_bytes(b'X'*4_000_001)
        r=R.calibrate(self.p,n);self.assertFalse(r['passed']);self.assertIn('Independent subpackage',str(r['blocks']))
        game.pop('subpackages');game['subPackages']=[];g.write_text(json.dumps(game));self.assertIn('requires game.json subpackages',str(R.calibrate(self.p,n)['blocks']))
    def test_245_keeps_editor_boot_until_actual_chain_and_no_cross_engine_template(self):
        self.base(version='2.4.5');r=R.prepare(self.p);self.assert_prepared(r);self.assertFalse((self.p/'build-templates/bytedance/main.js').exists());n=self.native();self.assertTrue(R.calibrate(self.p,n)['passed'])
        (n/'main.js').write_text('nothing loads resources');self.assertFalse(R.calibrate(self.p,n)['passed'])
    def test_source_change_invalidates_only_static_resource_preparation(self):
        self.base();self.assert_prepared(R.prepare(self.p));self.fx.image('resources/ui/new.png',10000);r=R.consume_current(self.p);self.assertFalse(r['passed']);self.assertIn('assets/resources/ui/new.png',r['files']);self.assert_prepared(R.prepare(self.p))
    def test_union_of_resources_and_other_early_bundle_counts_both(self):
        self.base(resources=2_000_000,code="cc.Class({extends:cc.Component,onLoad:function(){cc.assetManager.loadBundle('early',function(){});}});")
        self.fx.bundle('early');self.fx.image('early/back.png',7_300_000)
        r=R.prepare(self.p);self.assertFalse(r['passed']);self.assertGreater(r['budget']['first_download']['bytes'],R.FIRST_LIMIT)
    def test_unknown_startup_bundle_has_exact_mapping_task(self):
        self.base(code="cc.Class({extends:cc.Component,onLoad:function(){cc.assetManager.loadBundle(window.bundleName,function(){});}});")
        before=R.inputs(self.p);r=R.prepare(self.p);self.assertFalse(r['passed']);self.assertEqual(before,R.inputs(self.p));self.assertTrue(any(x['task']=='dynamic_startup_bundle' for x in r['tasks']))
    def test_dead_text_does_not_prove_245_bootstrap(self):
        self.base(version='2.4.5');self.assert_prepared(R.prepare(self.p));n=self.native();(n/'main.js').write_text("// tt.loadSubpackage({name:'resources',success:function(){cc.assetManager.loadBundle('resources',next)}});\nvoid 0;")
        self.assertFalse(R.calibrate(self.p,n)['passed'])
    def test_move_failure_rolls_back_original_folder_uuid(self):
        self.group();before=R.inputs(self.p);original=R.first_screen.analyze;count=0
        def fail_after(*a,**k):
            nonlocal count
            count+=1
            if count==2:raise ValueError('deliberate post-apply analysis failure')
            return original(*a,**k)
        with patch.object(R.first_screen,'analyze',side_effect=fail_after):r=R.prepare(self.p,self.group_plan())
        self.assertFalse(r['passed']);self.assertEqual(before,R.inputs(self.p));self.assertEqual(json.loads((self.p/'assets/resources/levels.meta').read_text())['uuid'],'folder-stays-exact')

class Resource3AndRefresh(unittest.TestCase):
    setUp=ResourcePreparation.setUp
    base=ResourcePreparation.base
    assert_prepared=ResourcePreparation.assert_prepared
    def project3(self,compression='subpackage',size=10000,dynamic=False):
        self.base(version='3.8.6',resources=size,code=("cc.Class({extends:cc.Component,onLoad:function(){cc.assetManager.loadBundle(window.bundleName,function(){});}});" if dynamic else None))
        m=self.p/'assets/resources.meta';d=json.loads(m.read_text());m.write_text(json.dumps({'uuid':d['uuid'],'importer':'directory','userData':{'isBundle':True,'bundleName':'resources','compressionType':{'bytedance-mini-game':compression},'other':17}}))
        return self.p
    def native3(self,complex_boot=False):
        n=Path(self.tmp.name)/'native3';n.mkdir(exist_ok=True)
        files={'game.js':b"require('./cocos-js/cc');var app=require('./application');app.start();",
               'application.js':b"cc.settings.init('src/settings.json');module.exports.start=function(){};",
               'cocos-js/cc.js':b'engine3','web-adapter.js':b'adapter3',
               'src/settings.json':json.dumps({'subpackages':['resources'],'bundleVers':{},'assets':{'preloadBundles':[{'bundle':'resources'}]}}).encode(),
               'game.json':json.dumps({'subpackages':[{'name':'resources','root':'subpackages/resources/'}]}).encode(),
               'project.config.json':b'{"appid":"ttfixture"}',
               'subpackages/resources/game.js':b'void 0;', 'subpackages/resources/config.json':b'{"name":"resources"}', 'subpackages/resources/payload':b'x'*10000}
        if complex_boot:files['application.js']=b"cc.settings.init({settingsPath:'src/settings.json'});module.exports.start=function(){};"
        for rel,data in files.items():p=n/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        return n
    def provider(self,fake=False):
        import project_qa
        qa=self.p/'qa';qa.mkdir(exist_ok=True)
        code=("def resource_package_adapter(**k): return {'passed':True}\n" if fake else '''import hashlib,json
from pathlib import Path

def digest(data):return hashlib.sha256((json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\\n').encode()).hexdigest()
def resource_package_adapter(project,phase,source_inventory,plan,native_inventory,native_files):
    home='assets/scripts/Home.js'
    r={'schema':'resource_package_adapter.v1','basis':'Reviewed finite resource domain from current Home load site; Native custom settings-object init is preserved and checked on exact current bytes.','unknown':[], 'source_inventory_sha256':digest(source_inventory),
       'startup_bundles':['resources'],'resolved_sites':[{'source':home,'line':1,'source_sha256':source_inventory[home],'bundles':['resources']}]}
    if phase=='native':
        assert b"settingsPath:'src/settings.json'" in native_files['application.js']
        assert b"app.start()" in native_files['game.js']
        r.update(native_inventory_sha256=digest(native_inventory),bootstrap_inputs={k:native_inventory[k] for k in ['game.js','application.js','src/settings.json','cocos-js/cc.js']})
    return r
''')
        (qa/'adapter.py').write_text(code)
        m=qa/'project-qa.json';m.write_text(json.dumps({'schema':'cocos_project_qa.v1','validators':{'resource_package_adapter.v1':{'path':'qa/adapter.py','dependencies':[]}}}))
        project_qa.register(self.p,m,reviewed=True)
    def test_3x_actual_legal_configuration_and_native_calibration_complete(self):
        self.project3();before=R.inputs(self.p);r=R.prepare(self.p);self.assert_prepared(r);self.assertFalse(r['mutated']);self.assertEqual(before,R.inputs(self.p));self.assertFalse((self.p/'build-templates/bytedance/main.js').exists())
        n=self.native3();out=R.calibrate(self.p,n);self.assertTrue(out['passed'],out);self.assertEqual(out['status'],'calibrated')
    def test_3x_fixed_actual_config_can_complete_after_main_overrun(self):
        self.project3('merge_all_json',2_000_000);r=R.prepare(self.p);self.assertFalse(r['passed']);self.assertTrue(any(x['task']=='engine3_main_budget' for x in r['tasks']))
        m=self.p/'assets/resources.meta';d=json.loads(m.read_text());d['userData']['compressionType']['bytedance-mini-game']='subpackage';m.write_text(json.dumps(d));self.assert_prepared(R.prepare(self.p))
    def test_3x_unknown_dynamic_can_finish_with_registered_actual_adapter(self):
        self.project3(dynamic=True)
        with patch.dict(os.environ,{'COCOS_QA_TRUST_FILE':str(Path(self.tmp.name)/'trust.json')}):
            self.assertFalse(R.prepare(self.p)['passed']);self.provider();r=R.prepare(self.p);self.assert_prepared(r);self.assertTrue(r['adapter_identity']);self.assertTrue(R.prepare(self.p)['reused'])
    def test_3x_true_only_adapter_is_rejected(self):
        self.project3(dynamic=True)
        with patch.dict(os.environ,{'COCOS_QA_TRUST_FILE':str(Path(self.tmp.name)/'trust.json')}):
            self.provider(fake=True);r=R.prepare(self.p);self.assertFalse(r['passed']);self.assertIn('true is not evidence',str(r['blocks']))
    def test_3x_native_config_mismatch_and_real_fix(self):
        self.project3();self.assert_prepared(R.prepare(self.p));n=self.native3();path=n/'subpackages/resources/config.json';path.write_text('{"name":"wrong"}');self.assertFalse(R.calibrate(self.p,n)['passed']);path.write_text('{"name":"resources"}');self.assertTrue(R.calibrate(self.p,n)['passed'])
    def test_3x_unknown_native_chain_can_complete_reviewed_bound_adapter(self):
        self.project3()
        with patch.dict(os.environ,{'COCOS_QA_TRUST_FILE':str(Path(self.tmp.name)/'trust.json')}):
            self.assert_prepared(R.prepare(self.p));n=self.native3(True);self.assertFalse(R.calibrate(self.p,n)['passed']);self.provider();self.assert_prepared(R.prepare(self.p));r=R.calibrate(self.p,n);self.assertTrue(r['passed'],r)
    def test_3x_reviewed_adapter_change_invalidates_identity(self):
        self.project3(dynamic=True)
        with patch.dict(os.environ,{'COCOS_QA_TRUST_FILE':str(Path(self.tmp.name)/'trust.json')}):
            self.provider();self.assert_prepared(R.prepare(self.p));p=self.p/'qa/adapter.py';p.write_text(p.read_text()+'\n# modified after review\n');self.assertFalse(R.consume_current(self.p)['passed'])
    def test_readonly_refresh_2x_updates_proof_after_real_file_change(self):
        self.base();self.assert_prepared(R.prepare(self.p));self.fx.image('resources/ui/new.png',10000);before=R.inputs(self.p);r=R.refresh_current(self.p);self.assert_prepared(r);self.assertFalse(r['mutated']);self.assertEqual(before,R.inputs(self.p));self.assertTrue(R.consume_current(self.p)['passed'])
    def test_readonly_refresh_2x_returns_needs_prepare_instead_of_mutating(self):
        self.base();self.assert_prepared(R.prepare(self.p));m=self.p/'assets/resources.meta';d=json.loads(m.read_text());d['compressionType']['bytedance']='merge_all_json';m.write_text(json.dumps(d));before=R.inputs(self.p);r=R.refresh_current(self.p);self.assertEqual(r['status'],'needs_prepare');self.assertFalse(r['passed']);self.assertEqual(before,R.inputs(self.p));self.assertEqual(json.loads(m.read_text())['compressionType']['bytedance'],'merge_all_json')
    def test_3x_reviewed_builder_pointers_read_actual_config_and_refuse_drift(self):
        self.project3();self.fx.image('levels/extra.png',2_000_000);self.fx.meta('levels',{'uuid':'keep-levels-meta','importer':'directory','userData':{}})
        cfg=self.p/'settings/v2/packages/custom-builder.json';cfg.parent.mkdir(parents=True,exist_ok=True);cfg.write_text(json.dumps({'group':{'enabled':True,'name':'levels','compression':'subpackage'}}))
        with patch.dict(os.environ,{'COCOS_QA_TRUST_FILE':str(Path(self.tmp.name)/'trust.json')}):
            self.provider();helper=self.p/'qa/adapter.py';helper.write_text(helper.read_text()+'''
_original=resource_package_adapter
def resource_package_adapter(**kwargs):
    r=_original(**kwargs)
    r['bundles']=[{'directory':'assets/levels','name':'levels','config':{'file':'settings/v2/packages/custom-builder.json','name_pointer':['group','name'],'mode_pointer':['group','compression'],'enabled_pointer':['group','enabled']}}]
    return r
''')
            import project_qa
            project_qa.register(self.p,self.p/'qa/project-qa.json',reviewed=True)
            r=R.prepare(self.p);self.assert_prepared(r);self.assertTrue(any(x['name']=='levels' for x in r['plan']['bundles']))
            d=json.loads(cfg.read_text());d['group']['compression']='merge_all_json';cfg.write_text(json.dumps(d));self.assertFalse(R.prepare(self.p)['passed'])
    def test_3x_hashed_actual_settings_can_complete_without_template(self):
        self.project3();self.assert_prepared(R.prepare(self.p));n=self.native3();(n/'src/settings.json').rename(n/'src/settings.ab12.json');path=n/'application.js';path.write_text(path.read_text().replace('src/settings.json','src/settings.ab12.json'));r=R.calibrate(self.p,n);self.assertTrue(r['passed'],r)
    def test_readonly_refresh_preserves_existing_startup_documents(self):
        self.base();self.assert_prepared(R.prepare(self.p));docs={p:p.read_bytes() for p in (self.p/'docs/startup').rglob('*') if p.is_file()};self.fx.image('resources/ui/new.png',10000);self.assert_prepared(R.refresh_current(self.p));self.assertEqual(docs,{p:p.read_bytes() for p in (self.p/'docs/startup').rglob('*') if p.is_file()})
    def test_readonly_refresh_3x_after_source_finalization(self):
        self.project3();self.assert_prepared(R.prepare(self.p));self.fx.image('resources/ui/new.png',10000);before=R.inputs(self.p);r=R.refresh_current(self.p);self.assert_prepared(r);self.assertEqual(before,R.inputs(self.p));self.assertFalse(r['mutated']);self.assertTrue(R.consume_current(self.p)['passed'])

if __name__=='__main__':unittest.main()
