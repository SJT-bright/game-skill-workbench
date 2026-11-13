"""Known ad capability mistakes share the existing file gate; no game/browser replay."""
import json
import subprocess
import unittest
from unittest.mock import patch
import upload_size_gate as gate

BAD = b'''var sdk=window.TTMinis.game;
function request(){if(typeof sdk.canIUse==='function'&&!sdk.canIUse('createRewardedVideoAd'))return {status:'unsupported'};
return sdk.createRewardedVideoAd({adUnitId:'example'});}'''
GOOD = BAD.replace(b"!sdk.canIUse('createRewardedVideoAd')", b"sdk.canIUse('createRewardedVideoAd')===false")

class AdSdkGateTests(unittest.TestCase):
    def test_known_fault_is_refused_at_the_existing_file_gate(self):
        with self.assertRaisesRegex(ValueError, 'ad SDK capability rejects callable API'):
            gate.enforce_tiktok_host({'assets/main/index.js': BAD})
    def test_explicit_false_and_unrelated_files_are_accepted(self):
        result = gate.enforce_tiktok_host({'assets/main/index.js': GOOD, 'ui.js': b'var width=200;'})
        self.assertEqual(result['ad_sdk_capabilities']['findings'], [])
    def test_capability_scan_cannot_be_omitted_from_gate_output(self):
        output = {'findings': [], 'platform_input_bindings': {
            'schema': 'platform_input_bindings.v1', 'findings': [], 'unresolved': []}}
        result = subprocess.CompletedProcess([], 0, json.dumps(output), '')
        with patch.object(gate.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'ad SDK capability check did not run'):
                gate.enforce_tiktok_host({'game.js': b'boot();'})
    def test_file_inspection_retains_a_separate_result_without_runtime_claim(self):
        result = gate.inspect_files({'game.js': b'boot();', 'game.json': b'{}',
                                     'project.config.json': b'{"appid":"test"}', 'ads.js': GOOD})
        self.assertGreater(result['total_bytes'], 0)
        self.assertEqual(result['ad_sdk_capabilities']['findings'], [])
        self.assertNotIn('runtime_passed', result)

if __name__ == '__main__':
    unittest.main()
