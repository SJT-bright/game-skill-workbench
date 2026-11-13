"""Scope admission and delivery-outbox failure boundaries, no game execution."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import production_hooks as H
import resource_package_prepare as R
import production_learning as L


class ProductionHooks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='production-hooks-')
        self.addCleanup(self.tmp.cleanup)
        self.project=Path(self.tmp.name)/'工程 with spaces';(self.project/'assets').mkdir(parents=True)

    def test_existing_unadmitted_maintenance_does_not_start_preparation(self):
        with patch.object(R,'prepare',side_effect=AssertionError('unrelated resource changes forbidden')) as p:
            self.assertIsNone(H.resource_step(self.project,'localize'))
            p.assert_not_called()
        self.assertEqual(list((self.project/'assets').iterdir()),[])

    def test_explicit_intake_admission_is_idempotent_and_routes_same_scope(self):
        p=H.admit_resources(self.project);before=p.read_bytes();self.assertEqual(H.admit_resources(self.project),p)
        self.assertEqual(p.read_bytes(),before)
        result={'passed':True,'status':'prepared'}
        with patch.object(R,'prepare',return_value=result) as prepare:
            self.assertIs(H.resource_step(self.project,'localize'),result)
            prepare.assert_called_once_with(self.project,board='localize')
        with patch.object(R,'calibrate',return_value=result) as calibrate:
            self.assertIs(H.resource_step(self.project,'localize',native='Native'),result)
            calibrate.assert_called_once_with(self.project,'Native')

    def test_other_board_and_calibration_override_do_not_expand_scope(self):
        H.admit_resources(self.project)
        with patch.object(R,'prepare',side_effect=AssertionError('scope expansion')) as prepare:
            self.assertIsNone(H.resource_step(self.project,'remake'))
            self.assertIsNone(H.resource_step(self.project,'localize',policy_override='new'))
            prepare.assert_not_called()

    def test_collector_error_and_missing_project_never_gate_delivery(self):
        with patch.object(L,'collect_nonblocking',side_effect=OSError('outbox unavailable')):
            result=H.collect_after_delivery(self.project)
        self.assertFalse(result['delivery_blocking']);self.assertEqual(result['status'],'deferred')
        self.assertFalse(H.collect_after_delivery(None)['delivery_blocking'])

    def test_existing_defaults_and_explicit_record_union_preserve_original_bytes(self):
        paths=['docs/timing/stage-timing.jsonl','docs/test/package-issues.jsonl','docs/checks/current.json']
        before={}
        for name in paths:
            p=self.project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'status':'fixed','cause_key':'resource.ownership','prevention_stage':'source'})+'\n');before[name]=p.read_bytes()
        outside=self.project.parent/'outside.json';outside.write_text('{}')
        observed={}
        def collect(project,**kw):observed.update(kw);return {'delivery_blocking':False,'status':'collected'}
        with patch.object(L,'collect_nonblocking',side_effect=collect):
            result=H.collect_after_delivery(self.project,record_paths=[self.project/paths[0],self.project/paths[2],outside],final_zip_sha256='a'*64)
        self.assertFalse(result['delivery_blocking'])
        self.assertEqual(set(observed['record_paths']),set(paths));self.assertEqual(len(observed['record_paths']),3)
        self.assertEqual(observed['context'],{'delivery_ready':True,'final_zip_sha256':'a'*64})
        for name,data in before.items():self.assertEqual((self.project/name).read_bytes(),data)

if __name__=='__main__':unittest.main(verbosity=2)
