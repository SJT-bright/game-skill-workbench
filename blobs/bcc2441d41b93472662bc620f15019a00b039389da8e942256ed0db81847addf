"""AST and raw-proof negative controls; fixtures are contract units, not phone acceptance."""
import copy,json,subprocess,tempfile,unittest
from pathlib import Path
from startup_storage_consumers import inventory,coverage_errors
from test_native_storage_upgrade_contract import business

class Consumers(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.js=self.root/'game.js';self.js.write_text("window.__require({A:[function(require,module,exports){var raw=cc.sys.localStorage;raw.getItem('flag');raw.getItem('best');},{}]});")
        sites=inventory(self.root);bykey={r['key']:r['site_id'] for r in sites}
        self.specs=[{'key':k,'type':t,'critical':False,'sites':[bykey[k]],'valid_fixtures':v} for k,t,v in [('flag','boolean',[True,False]),('best','integer',[45,0])]]
        self.trace={'legacy_consumers':{'fields':self.specs}};self.raw={'legacy_consumer_observations':[],'recovery_failure_observations':[]}
        for spec in self.specs:
            for v in spec['valid_fixtures']:
                r=business();r.pop('fixture_case');r.update(key=spec['key'],case='typed_upgrade',fixture=v,fixture_installed_before_entry=True,read_sites=spec['sites'],errors=[],value_preserved=True,cold_reopen_preserved=True,storage_before={spec['key']:v,'other':'keep'},storage_after={spec['key']:json.dumps(v),'other':'keep'},cold_storage_after={spec['key']:json.dumps(v),'other':'keep'},async_read={'value':v},sync_read={'type':'boolean','value':bool(v)},removed_keys=[])
                self.raw['legacy_consumer_observations'].append(r)
            metadata=copy.deepcopy(next(r for r in self.raw['legacy_consumer_observations'] if r['key']==spec['key'] and r['case']=='typed_upgrade'));metadata.update(case='metadata_unavailable',metadata_status='unavailable');self.raw['legacy_consumer_observations'].append(metadata)
            r=business();r.pop('fixture_case');r.update(key=spec['key'],case='unrecoverable',fixture_installed_before_entry=True,storage_before={spec['key']:spec['valid_fixtures'][0]},storage_after={spec['key']:spec['valid_fixtures'][0]},writes=[],removed_keys=[],loading_overlay_visible=False,recovery_feedback_visible=True,async_read={'status':'error'},isolated_consumer_writes=[])
            self.raw['legacy_consumer_observations'].append(r)
        for name in ['modal_fail','modal_reject','modal_no_callback']:
            self.raw['recovery_failure_observations'].append({'case':name,'injection_hit':True,'recovery_visible':True,'loading_overlay_visible':False,'errors':[],'action':{'trusted_input':True,'attempt_before':1,'attempt_after':2}})
    def check(self):return coverage_errors(self.trace,self.raw,self.root)
    def test_valid_and_each_key_required(self):
        self.assertEqual(self.check(),[])
        self.raw['legacy_consumer_observations']=[r for r in self.raw['legacy_consumer_observations'] if r['key']!='flag']
        self.assertTrue(any('flag' in e for e in self.check()))
    def test_actual_inventory_cannot_be_shrunk_by_declaration(self):
        self.specs.pop();self.assertTrue(any('uncovered' in e for e in self.check()))
    def test_boolean_false_not_string_or_number_and_raw_after_matters(self):
        r=self.raw['legacy_consumer_observations'][1];self.assertIs(r['fixture'],False)
        r['storage_after']['flag']='true';self.assertTrue(any('raw storage' in e for e in self.check()))
        r['storage_after']['flag']='false';r['async_read']['value']=0
        self.assertTrue(any('typed async' in e for e in self.check()))
    def test_new_player_or_after_entry_fixture_cannot_certify_upgrade(self):
        r=self.raw['legacy_consumer_observations'][0];r['fixture_installed_before_entry']=False
        self.assertTrue(self.check());r['fixture_installed_before_entry']=True;r['storage_before']={}
        self.assertTrue(self.check())
    def test_preservation_cold_restart_and_unrelated_value_required(self):
        r=self.raw['legacy_consumer_observations'][0];r['cold_storage_after']['other']='reset'
        self.assertTrue(any('raw storage' in e for e in self.check()))
    def test_unrecoverable_no_clear_no_permanent_loading(self):
        r=next(r for r in self.raw['legacy_consumer_observations'] if r['case']=='unrecoverable');r['storage_after']={}
        self.assertTrue(self.check());r['storage_after']=copy.deepcopy(r['storage_before']);r['loading_overlay_visible']=True
        self.assertTrue(self.check())
    def test_critical_no_unsafe_spend_and_tapped_retry(self):
        spec=self.specs[1];spec['critical']=True
        r=next(r for r in self.raw['legacy_consumer_observations'] if r['case']=='unrecoverable' and r['key']=='best')
        self.assertTrue(self.check());r.update(unsafe_grant_or_spend=False,recovery_action={'trusted_input':True,'new_attempt_observed':True})
        self.assertEqual(self.check(),[])
    def test_modal_failure_silent_and_no_callback_need_real_recovery(self):
        for name in ['modal_fail','modal_reject','modal_no_callback']:
            r=next(r for r in self.raw['recovery_failure_observations'] if r['case']==name);r['action']['attempt_after']=1
            self.assertTrue(any(name in e for e in self.check()));r['action']['attempt_after']=2
    def test_auto_filled_sdk_metadata_cannot_claim_missing_api_coverage(self):
        row=next(r for r in self.raw['legacy_consumer_observations'] if r['case']=='metadata_unavailable')
        row['metadata_status']='present'
        self.assertTrue(any('metadata unavailability' in e for e in self.check()))

    def test_home_only_is_not_play(self):
        self.raw['legacy_consumer_observations'][0]['business'].pop('play')
        self.assertTrue(self.check())
    def test_ast_alias_bracket_constants_comments_shadowing(self):
        self.js.write_text("const x=cc.sys['localStorage'];x['getItem']('en'+'abled'); /*cc.sys.localStorage.getItem('fake')*/ const text=\"cc.sys.localStorage.getItem('fake2')\";function unrelated(cc){cc.sys.localStorage.getItem('shadowed')}cache.getItem('asset');")
        self.assertEqual([r['key'] for r in inventory(self.root)],['enabled'])
    def test_split_computed_method_cannot_bypass_file_selection(self):
        self.js.write_text("cc.sys['local'+'Storage']['get'+'Item']('flag');window.tt['get'+'StorageSync']('best');")
        self.assertEqual([r['key'] for r in inventory(self.root)],['flag','best'])

    def test_function_alias_bind_call_apply_are_actual_consumers(self):
        self.js.write_text("const s=cc.sys.localStorage;const read=s.getItem.bind(s);read('a');s.getItem.call(s,'b');s.getItem.apply(s,['c']);")
        self.assertEqual([r['key'] for r in inventory(self.root)],['a','b','c'])

    def test_var_alias_and_cocos3_imports(self):
        self.js.write_text("if(true){var raw=cc.sys.localStorage;}raw.getItem('flag');")
        self.assertEqual([r['key'] for r in inventory(self.root)],['flag'])
        self.js.write_text("import {sys as engineSys} from 'cc';engineSys.localStorage.getItem('flag');")
        self.assertEqual([r['key'] for r in inventory(self.root)],['flag'])
        self.js.write_text("const engine=require('cc');engine.sys.localStorage.getItem('flag');")
        self.assertEqual([r['key'] for r in inventory(self.root)],['flag'])

    def test_adapter_name_does_not_exempt_real_business_read(self):
        (self.root/'adapter-min.js').write_text("const bridge={getItem:function(k){return tt.getStorageSync(k)}};tt.getStorageSync('another_key');")
        self.assertEqual(sorted(r['key'] for r in inventory(self.root)),['another_key','best','flag'])

    def test_dynamic_and_bad_javascript_are_not_green(self):
        self.js.write_text('cc.sys.localStorage.getItem(variableKey);')
        self.assertTrue(any('dynamic' in e for e in self.check()))
        self.js.write_text('cc.sys.localStorage.getItem(')
        with self.assertRaisesRegex(ValueError,'AST inventory failed'):inventory(self.root)
    def test_full_existing_v3_proof_for_other_key_does_not_hide_new_consumer(self):
        from test_native_storage_upgrade_contract import UpgradeTests
        f=UpgradeTests('test_valid_v3_and_actual_consumer');f.setUp();self.addCleanup(f.doCleanups)
        (f.native/'legacy.js').write_text("cc.sys.localStorage.getItem('another_key');")
        from check_known_issues import tree_sha
        f.binding['native_tree_sha256']=tree_sha(f.native)
        self.assertTrue(any('another_key' in e for e in f.validate()))

    def test_known_unaffected_receipt_reuses_original_execution_only_without_consumers(self):
        from test_native_storage_upgrade_contract import UpgradeTests
        import audit_native_storage_contract as contract
        from check_known_issues import tree_sha
        f=UpgradeTests('test_valid_v3_and_actual_consumer');f.setUp();self.addCleanup(f.doCleanups)
        expected=contract.receipt_identity(f.trace);old=copy.deepcopy(expected)
        old['contract_files']={k:v for k,v in old['contract_files'].items() if k in ('maintenance_scope.py','startup_business_contract.py')}
        old['contract_files']['audit_native_storage_contract.py']='499c175aff78232fc57e5b8a7a6a78dd245bf090ed295f3b87491752b23d42ae'
        report={'native':str(f.native),'execution_receipt':{'identity':old}}
        self.assertTrue(contract.unchanged_nonconsumer_receipt(report,f.trace,expected))
        old['trace_sha256']='forged';self.assertFalse(contract.unchanged_nonconsumer_receipt(report,f.trace,expected))
        old['trace_sha256']=expected['trace_sha256']
        (f.native/'raw.js').write_text("cc.sys.localStorage.getItem('settings_flag');")
        f.binding['native_tree_sha256']=tree_sha(f.native);expected=contract.receipt_identity(f.trace);old['trace_sha256']=expected['trace_sha256']
        self.assertFalse(contract.unchanged_nonconsumer_receipt(report,f.trace,expected))

    def test_no_direct_storage_consumers_do_not_invalidate_other_games(self):
        self.js.write_text("useAlreadySchemaBackedService();")
        self.assertEqual(coverage_errors({}, {}, self.root),[])
if __name__=='__main__':unittest.main()
