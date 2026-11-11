#!/usr/bin/env python3
"""Regression checks for the shared optional-ad/free-claim static gate. No browser."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import package_gates

SOURCE = '''
function RewardPanel() {}
RewardPanel.prototype.start = function () {
    UI.setButtonClickEvents(this, this.claim, "collect", 1);
    UI.setButtonClickEvents(this, this.watch, "collect", 0);
};
RewardPanel.prototype.collect = function (event, mode) {
    if (this.processing) return;
    if (mode === 0) {
        this.processing = true;
        var self = this;
        sdk.showVideoAd("bonus", function () {
            self.processing = false;
            self.collect(event, 2);
        });
        return;
    }
    this.save(mode === 1 ? this.base : this.base.concat(this.bonus));
};
'''


@unittest.skipUnless(shutil.which('node'), 'Node.js is required for the AST scanner')
class FreeClaimAdLock(unittest.TestCase):
    def test_structural_controls(self):
        result = subprocess.run(['node', str(HERE / 'test_free_claim_ad_lock.cjs')],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'passed': True, 'cases': 11})

    def test_shared_gate_blocks_the_bad_structure_on_both_boards(self):
        for board in ('localize', 'remake'):
            report = package_gates.run({'assets/main/index.js': SOURCE.encode()},
                                       board=board, policy='legacy', modules=('ads_static',))
            self.assertEqual([row['id'] for row in report['blocks']], ['A4_free_claim_ad_lock'])
            self.assertEqual(report['blocks'][0]['evidence']['hits'][0]['handler'], 'collect')

    def test_fixed_structure_is_accepted(self):
        fixed = SOURCE.replace('if (this.processing) return;',
                               'if (this.processing) { if (mode !== 1) return; this.cancelBonus(); }')
        report = package_gates.run({'assets/main/index.js': fixed.encode()},
                                   board='localize', modules=('ads_static',))
        self.assertEqual(report['blocks'], [])

    def test_missing_node_reports_a_check_error(self):
        with mock.patch('package_gates.ads_static.shutil.which', return_value=None):
            report = package_gates.run({'assets/main/index.js': SOURCE.encode()}, modules=('ads_static',))
        self.assertEqual([row['id'] for row in report['blocks']], ['GATE_ERROR_ads_static'])

    def test_candidate_parse_failure_is_not_zero_findings(self):
        report = package_gates.run({'assets/main/index.js': (SOURCE + '\nfunction (').encode()},
                                   modules=('ads_static',))
        self.assertEqual([row['id'] for row in report['blocks']], ['GATE_ERROR_ads_static'])

    def test_cli_failure_and_missing_input(self):
        scanner = str(HERE / 'scan_free_claim_ad_lock.cjs')
        bad = subprocess.run(['node', scanner], input=json.dumps({'files': [{'file': 'entry.js', 'code': SOURCE}]}),
                             capture_output=True, text=True, timeout=20)
        self.assertEqual(bad.returncode, 1)
        self.assertEqual(json.loads(bad.stdout)['status'], 'failed')
        empty = subprocess.run(['node', scanner], input='', capture_output=True, text=True, timeout=20)
        self.assertEqual(empty.returncode, 2)
        self.assertEqual(json.loads(empty.stdout)['status'], 'not_run')
        missing = subprocess.run(['node', scanner], input=json.dumps({'files': [{'file': 'entry.js'}]}),
                                 capture_output=True, text=True, timeout=20)
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(json.loads(missing.stdout)['status'], 'not_run')


if __name__ == '__main__':
    unittest.main()
