"""Gate counterexamples only: these fixtures are not game or device evidence."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import audit_ad_storage_contract as gate


class StorageEvidenceGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.native = self.project/'native'; self.native.mkdir()
        (self.native/'game.js').write_text('createRewardedVideoAd')
        self.files = {'game.js': b'createRewardedVideoAd'}
        (self.project/'qa').mkdir()
        (self.project/'qa/runner.py').write_text('# isolated fixture identity')
        (self.project/'qa/host.js').write_text('// isolated fixture dependency')
        runner = self.ref('qa/runner.py'); deps = [self.ref('qa/host.js')]
        self.data = {'schema': 'native_ad_storage_contract.v2',
                     'native_tree_sha256': gate.tree_sha(self.native),
                     'evidence_layer': 'native_adapter_simulation',
                     'shapes': sorted(gate.REQUIRED_SHAPES), 'runner': runner,
                     'harness_dependencies': deps, 'cases': {}, 'evidence_refs': {}}
        for shape in gate.REQUIRED_SHAPES:
            self.data['cases'][shape] = [{'path': ['balance_delta'], 'op': 'eq', 'value': 0}]
            raw = {'schema': 'native_storage_shape_case.v2', 'shape': shape,
                   'native_tree_sha256': self.data['native_tree_sha256'],
                   'runner': runner, 'harness_dependencies': deps,
                   'injection': {'api': 'tt.getStorageSync', 'shape': shape, 'read_count': 1},
                   'errors': [], 'observed': {'balance_delta': 0}}
            self.write_case(shape, raw)
        # Synthetic player-chain material exercises the validator only.
        raw.update(shape='false', observed={'balance_delta':0}, input_transport='playwright_cdp_touch')
        raw['observed']['trusted_touch_count']=2
        (self.project/'qa/chain.json').write_text(json.dumps(raw))
        self.negative=self.project/'negative';self.negative.mkdir();(self.negative/'game.js').write_text('known bad fixture')
        negative=copy.deepcopy(raw);negative['native_tree_sha256']=gate.tree_sha(self.negative);negative['observed']['balance_delta']=1
        (self.project/'qa/negative.json').write_text(json.dumps(negative))
        import audit_ad_local_retest
        self.chain={'schema':'native_ad_local_retest.v1','native_tree_sha256':self.data['native_tree_sha256'],
          'cases':{name:{'raw':self.ref('qa/chain.json'),'assertions':[{'path':['observed','balance_delta'],'op':'eq','value':0}]} for name in audit_ad_local_retest.REQUIRED_CASES},
          'controls':[{'case':'completed','native_root':str(self.negative),'raw':self.ref('qa/negative.json')}]}
        self.save_chain()
        self.save()

    def save_chain(self):
        (self.project/'qa/player-chain.json').write_text(json.dumps(self.chain))
        self.data['local_player_retest']=self.ref('qa/player-chain.json')

    def ref(self, rel):
        return {'path': rel, 'sha256': hashlib.sha256((self.project/rel).read_bytes()).hexdigest()}

    def write_case(self, shape, raw):
        rel = 'qa/'+shape+'.json'
        (self.project/rel).write_text(json.dumps(raw))
        self.data['evidence_refs'][shape] = self.ref(rel)

    def mutate_case(self, change):
        shape = 'false'
        raw = json.loads((self.project/self.data['evidence_refs'][shape]['path']).read_text())
        change(raw); self.write_case(shape, raw); self.save()

    def save(self):
        (self.project/'qa/storage-boolean-contract.json').write_text(json.dumps(self.data))

    def verify(self):
        return gate.verify(self.files, self.native, self.project)

    def test_complete_material_is_limited_to_adapter_storage(self):
        result = self.verify()
        self.assertTrue(result['passed'])
        self.assertEqual(result['coverage'], 'adapter_storage_and_local_player_chain')

    def test_old_v1_declarations_refused(self):
        self.data['schema'] = 'native_ad_storage_contract.v1'; self.save()
        with self.assertRaisesRegex(ValueError, 'v2 required'): self.verify()

    def test_unexecuted_shape_refused(self):
        del self.data['evidence_refs']['invalid_string']; self.save()
        with self.assertRaisesRegex(ValueError, 'every storage shape'): self.verify()

    def test_pass_flag_cannot_override_wrong_business_value(self):
        self.mutate_case(lambda raw: raw.update(passed=True, observed={'balance_delta': 1}))
        with self.assertRaisesRegex(ValueError, 'postconditions'): self.verify()

    def test_missing_observation_is_not_a_pass(self):
        self.mutate_case(lambda raw: raw.update(observed={}))
        with self.assertRaisesRegex(ValueError, 'postconditions'): self.verify()

    def test_boolean_not_equal_to_number(self):
        self.mutate_case(lambda raw: raw.update(observed={'balance_delta': False}))
        with self.assertRaisesRegex(ValueError, 'postconditions'): self.verify()

    def test_empty_assertions_refused(self):
        self.data['cases']['false'] = []; self.save()
        with self.assertRaisesRegex(ValueError, 'business assertions'): self.verify()

    def test_unsupported_assertion_refused(self):
        self.data['cases']['false'][0]['op'] = 'always'; self.save()
        with self.assertRaisesRegex(ValueError, 'invalid storage business'): self.verify()

    def test_wrong_injection_api_refused(self):
        self.mutate_case(lambda raw: raw['injection'].update(api='Storage.prototype.getItem'))
        with self.assertRaisesRegex(ValueError, 'adapter injection'): self.verify()

    def test_unexercised_injection_refused(self):
        self.mutate_case(lambda raw: raw['injection'].update(read_count=0))
        with self.assertRaisesRegex(ValueError, 'adapter injection'): self.verify()

    def test_wrong_shape_cannot_reuse_other_case(self):
        self.mutate_case(lambda raw: raw.update(shape='true'))
        with self.assertRaisesRegex(ValueError, 'identity mismatch'): self.verify()

    def test_old_raw_cannot_be_rebound_by_editing_only_contract(self):
        (self.native/'game.js').write_text('createRewardedVideoAd; changed()')
        self.data['native_tree_sha256'] = gate.tree_sha(self.native); self.save()
        with self.assertRaisesRegex(ValueError, 'identity mismatch'): self.verify()

    def test_changed_runner_refused(self):
        (self.project/'qa/runner.py').write_text('# changed')
        with self.assertRaisesRegex(ValueError, 'missing or changed'): self.verify()

    def test_changed_host_refused(self):
        (self.project/'qa/host.js').write_text('// changed')
        with self.assertRaisesRegex(ValueError, 'missing or changed'): self.verify()

    def test_harness_errors_refused(self):
        self.mutate_case(lambda raw: raw.update(errors=['TypeError']))
        with self.assertRaisesRegex(ValueError, 'harness errors'): self.verify()

    def test_appended_success_cannot_hide_previous_output(self):
        rel = self.data['evidence_refs']['false']['path']
        p = self.project/rel; p.write_text(p.read_text()+'\n{"passed":true}')
        self.data['evidence_refs']['false'] = self.ref(rel); self.save()
        with self.assertRaisesRegex(ValueError, 'invalid storage JSON'): self.verify()

    def test_registered_contract_checked_after_sdk_rename(self):
        self.files = {'game.js': b'platform.requestVideo()'}
        self.data['cases']['false'] = []; self.save()
        with self.assertRaisesRegex(ValueError, 'business assertions'): self.verify()

    def test_device_claim_refused(self):
        self.data['evidence_layer'] = 'real_tiktok_iaa'; self.save()
        with self.assertRaisesRegex(ValueError, 'adapter simulation'): self.verify()

    def test_missing_player_chain_blocks(self):
        del self.data['local_player_retest'];self.save()
        with self.assertRaisesRegex(ValueError,'invalid storage evidence reference'):self.verify()

    def test_missing_consumer_blocks(self):
        del self.chain['cases']['consumer'];self.save_chain();self.save()
        with self.assertRaisesRegex(ValueError,'required player-chain'):self.verify()

    def test_wrong_player_result_blocks_even_with_refreshed_hash(self):
        p=self.project/'qa/chain.json';raw=json.loads(p.read_text());raw['observed']['balance_delta']=7;p.write_text(json.dumps(raw))
        for case in self.chain['cases'].values():case['raw']=self.ref('qa/chain.json')
        self.save_chain();self.save()
        with self.assertRaisesRegex(ValueError,'local ad postconditions'):self.verify()

    def test_nonreproducing_player_negative_blocks(self):
        p=self.project/'qa/negative.json';raw=json.loads(p.read_text());raw['observed']['balance_delta']=0;p.write_text(json.dumps(raw))
        self.chain['controls'][0]['raw']=self.ref('qa/negative.json');self.save_chain();self.save()
        with self.assertRaisesRegex(ValueError,'did not reproduce'):self.verify()

    def test_mouse_player_material_blocks(self):
        p=self.project/'qa/chain.json';raw=json.loads(p.read_text());raw['input_transport']='mouse';p.write_text(json.dumps(raw))
        for case in self.chain['cases'].values():case['raw']=self.ref('qa/chain.json')
        self.save_chain();self.save()
        with self.assertRaisesRegex(ValueError,'Native/input'):self.verify()

    def test_existing_narrow_source_bypass_guard_preserved(self):
        path = self.project/'EnglishProject/assets/script/RewardFlow.ts'
        path.parent.mkdir(parents=True); path.write_text('cc.sys.localStorage.getItem("wallet")')
        with self.assertRaisesRegex(ValueError, 'bypasses shared storage reader'): self.verify()

    def test_shared_writer_obligations_reaches_storage_gate(self):
        import package_obligations as obligations
        manifest = self.project/'resources.json'; manifest.write_text('{}')
        self.data['cases']['false'] = []; self.save()
        with patch.object(obligations.issues, 'audit', return_value={}), patch.object(obligations.resources, 'audit', return_value={}):
            with self.assertRaisesRegex(ValueError, 'business assertions'):
                obligations.verify(self.files, self.native, self.project, manifest)


if __name__ == '__main__':
    unittest.main()
