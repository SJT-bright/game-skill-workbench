#!/usr/bin/env python3
"""Shared proof gate and actual writer/delivery refusal; isolated synthetic artifacts only.
Other size/renderer gates are stubbed in entry tests; STORAGE-01 is not stubbed.
"""
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
HERE = Path(__file__).resolve().parent
DEPS = Path(os.environ.get('SKILL_TEST_DEPS', str(HERE)))
sys.path.extend([str(DEPS), str(DEPS.parents[1]/'cocos-game-check/package-check/scripts')])
import audit_native_storage_contract as contract
from audit_final_storage import audit_final_storage
import test_native_storage_upgrade_contract as upgrade_fixture
import check_known_issues as consumer


class FinalStorageTests(unittest.TestCase):
    def setUp(self):
        f = self.f = upgrade_fixture.UpgradeTests('test_valid_v3_and_actual_consumer'); f.setUp(); self.addCleanup(f.doCleanups)
        self.project=f.root/'Source';(self.project/'assets').mkdir(parents=True)
        (self.project/'assets/store.js').write_text('// source fixture')
        f.trace['project']=str(self.project)
        f.binding['source_sha256'] = consumer.snapshot(self.project)[2]
        f.trace['execution']['dependencies'] = []
        self.report = f.root/'approved.json'; self.startup=f.root/'startup.json'
        self.approve()

    def approve(self):
        f=self.f;trace_path=f.root/'trace.json';trace_path.write_text(json.dumps(f.trace))
        r=contract.approve_runtime(f.trace,f.native,f.binding)
        self.assertTrue(r['passed'],r.get('errors'))
        r.update(native=str(f.native),trace=str(trace_path),trace_sha256=contract.digest(trace_path))
        self.report.write_text(json.dumps(r))
        self.startup.write_text(json.dumps({'binding':f.binding,'native_storage_report':{
            'path':str(self.report),'sha256':contract.digest(self.report)}}))

    def test_current_contract_and_review_both_accepted_without_replay(self):
        f=self.f
        with patch.object(contract,'replay',side_effect=AssertionError('consumer must not run matrix')):
            self.assertEqual(audit_final_storage(f.native,self.project,self.startup)['action'],'rejudged')
            review=f.root/'review.json';review.write_text(json.dumps({'binding':f.binding,'checks':{'STORAGE-01':{
                'auto_reports':[{'path':str(self.report),'sha256':contract.digest(self.report)}]}}}))
            self.assertEqual(audit_final_storage(f.native,self.project,review=review)['id'],'storage.native.contract')

    def test_missing_changed_and_stale_proof_refused(self):
        f=self.f
        self.startup.write_text(json.dumps({'binding':f.binding}))
        with self.assertRaisesRegex(ValueError,'native_storage_report'):audit_final_storage(f.native,self.project,self.startup)
        self.approve();self.report.write_text('{}')
        with self.assertRaisesRegex(ValueError,'storage.native.contract'):audit_final_storage(f.native,self.project,self.startup)
        self.approve();(self.project/'assets/store.js').write_text('// changed dependency/source')
        with self.assertRaisesRegex(ValueError,'scope_required|affected dependencies|binding stale'):audit_final_storage(f.native,self.project,self.startup)

    def test_light_writer_really_refuses_before_runtime_and_zip(self):
        import build_checked_zip as alias
        import make_tiktok_zip as writer
        import test_single_writer
        import audit_final_storage as shared_storage
        fixture = test_single_writer.SingleWriter('test_legacy_build_routes_all_parameters_once')
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        fixture.mock_engine()
        f = self.f
        # The alias forwards to the canonical backend. Other gates belong to
        # their own controls; this case keeps the actual storage gate active.
        self.startup.write_text(json.dumps({'binding':f.binding}))
        with patch.object(shared_storage, 'audit_final_storage', side_effect=audit_final_storage), \
                patch.object(writer, 'writer_regressions', side_effect=AssertionError('must refuse before runtime')), \
                patch.object(writer, 'write_zip', side_effect=AssertionError('must not write')):
            with self.assertRaisesRegex(ValueError,'storage.native.contract'):
                alias.build(**dict(fixture.kw, startup_contract=self.startup))
        self.assertFalse(fixture.out.exists())

    def test_main_writer_really_refuses_no_zip(self):
        import make_tiktok_zip as writer
        import test_single_writer
        import audit_final_storage as shared_storage
        fixture = test_single_writer.SingleWriter('test_legacy_build_routes_all_parameters_once')
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        fixture.mock_engine()
        self.startup.write_text(json.dumps({'binding':self.f.binding}))
        with patch.object(shared_storage, 'audit_final_storage', side_effect=audit_final_storage), \
                patch.object(writer, 'write_zip', side_effect=AssertionError('must not write')):
            with self.assertRaisesRegex(ValueError,'storage.native.contract'):
                writer.write_package(**dict(fixture.kw, startup_contract=self.startup))
        self.assertFalse(fixture.out.exists())

    def test_delivery_really_refuses_before_success_record(self):
        spec=importlib.util.spec_from_file_location('delivery',HERE.parents[1]/'cocos-game-check/package-check/scripts/prepare_delivery.py')
        if not Path(spec.origin).is_file():
            spec=importlib.util.spec_from_file_location('delivery',DEPS.parents[1]/'cocos-game-check/package-check/scripts/prepare_delivery.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        import upload_size_gate,package_obligations
        stable=Path(os.environ.get('SKILL_TEST_STABLE_ROOT',str(Path.cwd())))
        work=Path(tempfile.mkdtemp(prefix='storage-delivery-fixture-',dir=stable));self.addCleanup(shutil.rmtree,work,True)
        archive=work/'game.zip';archive.write_bytes(b'explicit synthetic boundary');record=work/'delivery.json'
        size={'passed':True,'size_passed':True,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'run_id':'synthetic','errors':[]}
        f=self.f;self.startup.write_text(json.dumps({'binding':f.binding}))
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(upload_size_gate,'inspect_final_zip',return_value=size))
            stack.enter_context(patch.object(m,'writer_board',return_value='localize'))
            stack.enter_context(patch.object(package_obligations,'verify',return_value={}))
            stack.enter_context(patch.object(m,'check',return_value={}))
            stack.enter_context(patch.object(m,'regression_checks',return_value=[]))
            runtime=stack.enter_context(patch.object(m,'audit_final_startup',side_effect=AssertionError('must refuse first')))
            with self.assertRaisesRegex(ValueError,'storage.native.contract'):
                m._prepare(archive,f.native,'ttfixture',record,self.project,self.startup,None,None,None,None,None,None,None,[],{})
            runtime.assert_not_called();self.assertFalse(record.exists())

if __name__=='__main__':unittest.main(verbosity=2)
