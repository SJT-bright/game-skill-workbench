"""First complete source prepares sync-owned kit parts before its real checks/receipt."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import tiktok_finalize as F
import tiktok_finalize_steps as T
from test_tiktok_finalize import project24,APP


class SourceSyncConvergence(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.p=project24(Path(self.temp.name)/'project')
    def mark(self,board='localize'):
        F.P.write_marker(self.p,board,T.load_manifest().version,reason='first-production-fixture')
    def test_first_complete_source_then_sync_preserves_real_source_receipt(self):
        self.mark();source=F.finalize_source(self.p,'localize');self.assertEqual(source['blocks'],[],source['blocks'])
        self.assertEqual([x['step'] for x in source['steps'][:2]],['ui_kit','run_parts'])
        ui=self.p/'assets/tiktok-platform/GameUIKit.js';self.assertTrue(ui.is_file())
        self.assertIn('preparation',source['steps'][0]);self.assertIn('preparation_binding',source)
        receipt=(self.p/F.SOURCE_RECORD).read_bytes();identity=F.source_sha256(self.p)
        sync=F.finalize_sync(self.p,'localize');self.assertEqual(sync['blocks'],[],sync['blocks']);self.assertEqual(sync['changed'],[])
        self.assertEqual(F.source_sha256(self.p),identity);self.assertEqual((self.p/F.SOURCE_RECORD).read_bytes(),receipt)
        self.assertEqual(F.check_source_record(self.p),[])
    def test_changed_uikit_rule_refuses_original_binding_without_rewriting_receipt(self):
        self.mark();source=F.finalize_source(self.p,'localize');self.assertEqual(source['blocks'],[])
        receipt=(self.p/F.SOURCE_RECORD).read_bytes();current=T.load_manifest();data=copy.deepcopy(current.data)
        data['files']['parts/GameUIKit.js']['project_path']='assets/tiktok-platform/GameUIKit-reviewed-new-path.js'
        changed=T.Manifest(data,current.kit_dir)
        problems=F.check_source_record(self.p,manifest=changed)
        self.assertTrue(problems);self.assertTrue(any('ui_kit' in str(x) for x in problems),problems)
        self.assertEqual((self.p/F.SOURCE_RECORD).read_bytes(),receipt)
        self.assertFalse((self.p/'assets/tiktok-platform/GameUIKit-reviewed-new-path.js').exists())
    def test_legacy_complete_source_does_not_install_new_kit_parts(self):
        legacy={'games':[{'name':'old-game','folder':'old-game','scene_uuids':['1b2c3d4e-0000-4000-8000-00000000abcd']}]}
        source=F.finalize_source(self.p,'localize',legacy=legacy)
        self.assertEqual(source['policy'],'legacy',source['decision'])
        self.assertFalse((self.p/'assets/tiktok-platform/GameUIKit.js').exists())
        self.assertFalse(any(x['step'] in ('ui_kit','run_parts') for x in source['steps']))
    def test_explicit_scoped_source_stays_scoped(self):
        self.mark();source=F.finalize_source(self.p,'localize',steps=('frame_scan',))
        self.assertEqual(source['blocks'],[]);self.assertEqual([x['step'] for x in source['steps']],['frame_scan'])
        self.assertFalse((self.p/'assets/tiktok-platform/GameUIKit.js').exists())
    def test_remake_run_parts_installed_during_first_complete_source(self):
        self.mark('remake');source=F.finalize_source(self.p,'remake');self.assertEqual(source['blocks'],[],source['blocks'])
        for key,spec in T.load_manifest().files.items():
            if isinstance(spec,dict) and isinstance(spec.get('sync_install'),dict):
                path=self.p/spec['project_path'];self.assertTrue(path.is_file(),key)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),spec['sha256'])
        before=F.source_sha256(self.p);sync=F.finalize_sync(self.p,'remake');self.assertEqual(sync['changed'],[]);self.assertEqual(F.source_sha256(self.p),before);self.assertEqual(F.check_source_record(self.p),[])

if __name__=='__main__':unittest.main()
