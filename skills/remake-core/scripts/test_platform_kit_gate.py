#!/usr/bin/env python3
"""Remake (user 2026-10-27): the unchanged TikTok Platform Kit covers the per-game Retry fault matrix, but HOME/real-input
startup evidence stays mandatory. Also runs the kit's own Node tests and its project checker."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
KIT = HERE.parent / 'assets' / 'platform-kit'
NODE = shutil.which('node')

import audit_final_package_startup as gate  # noqa: E402


def make_project(root):
    proj = root / 'game'
    (proj / 'assets').mkdir(parents=True)
    (proj / 'project.json').write_text(json.dumps({'engine': 'cocos-creator-js', 'version': '2.4.15'}))
    shutil.copytree(KIT / 'assets' / 'tiktok-platform', proj / 'assets' / 'tiktok-platform')
    cfg = proj / 'assets' / 'tiktok-platform' / 'PlatformConfig.js'
    cfg.write_text(cfg.read_text().replace("gameId: 'change-me'", "gameId: 'kitgate'")
                   .replace('normalLevelCoins: 0,', 'normalLevelCoins: 12,'))       # kit 2.0: B must be set
    (proj / 'assets' / 'resources').mkdir()
    (proj / 'assets' / 'resources.meta').write_text(json.dumps({'isBundle': True, 'compressionType': {'bytedance': 'subpackage'}}))
    shutil.copytree(KIT / 'build-templates', proj / 'build-templates')
    # kit 2.0 (W-A1): the storage layer is a kit part the install step copies into build-templates/bytedance/
    shutil.copy(KIT / 'parts' / 'storage-guard.js', proj / 'build-templates' / 'bytedance' / 'storage-guard.js')
    (proj / 'settings').mkdir()
    # v7.5 (D7 item 6): the install step copies the kit's settings/bytedance.json (numeric App ID, no start-scene bundle).
    shutil.copy(KIT / 'settings' / 'bytedance.json', proj / 'settings' / 'bytedance.json')
    native = root / 'native'
    native.mkdir()
    for name in ('main.js', 'touch-coordinates.js'):
        shutil.copy(KIT / 'build-templates' / 'bytedance' / name, native / name)
    return proj, native


class PlatformKitGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='kit-gate-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project, self.native = make_project(self.tmp)

    def test_unchanged_kit_covers_retry(self):
        ok, why = gate.platform_kit_covers_retry(self.native, self.project)
        self.assertTrue(ok, why)

    def test_changed_native_boot_is_not_covered(self):
        main = self.native / 'main.js'
        main.write_text(main.read_text().replace('10000', '20000'))
        ok, why = gate.platform_kit_covers_retry(self.native, self.project)
        self.assertFalse(ok)
        self.assertIn('main.js', why)

    def test_changed_kit_file_in_project_is_not_covered(self):
        f = self.project / 'assets' / 'tiktok-platform' / 'SaveStore.js'
        f.write_text(f.read_text() + '\n// edited\n')
        self.assertFalse(gate.platform_kit_covers_retry(self.native, self.project)[0])

    def test_startup_contract_still_required(self):
        with self.assertRaises(ValueError) as ctx:
            gate.audit_final_startup(self.native, self.project, None, None)
        self.assertIn('--startup-contract', str(ctx.exception))

    def test_without_kit_retry_evidence_is_required(self):
        (self.native / 'main.js').write_text('// project boot')
        contract = self.tmp / 'contract.json'
        contract.write_text('{}')
        with self.assertRaises(ValueError) as ctx:
            gate.audit_final_startup(self.native, self.project, contract, None)
        self.assertIn('--loading-recovery-runtime required', str(ctx.exception))

    @unittest.skipUnless(NODE, 'node not installed')
    def test_kit_node_suites_pass(self):
        for name in ('kit.test.js', 'kit-negative-controls.js', 'boot.test.js', 'boot-negative-controls.js'):
            r = subprocess.run([NODE, str(KIT / 'tests' / name)], capture_output=True, text=True, timeout=180)
            self.assertEqual(r.returncode, 0, name + ': ' + (r.stdout + r.stderr)[-600:])


if __name__ == '__main__':
    unittest.main(verbosity=2)
