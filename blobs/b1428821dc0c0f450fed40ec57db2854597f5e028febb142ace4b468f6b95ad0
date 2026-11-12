"""Cross-computer receipt/ledger transport units, not actual game or phone acceptance."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

import game_handoff as H
from verify_native_zip import make_receipt
from test_upload_size_gate import payload


class Handoff(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.game = self.root/'test.zip'; self.source = self.root/'source.zip'
        self.files = payload()
        with zipfile.ZipFile(self.game,'w') as z:
            for n,b in self.files.items(): z.writestr(n,b)
        with zipfile.ZipFile(self.source,'w') as z: z.writestr('Source/assets/store.js','// source fixture')
        self.digest = H.sha(self.game.read_bytes())
        receipt = make_receipt('build_checked_zip',self.game,self.digest,
            {n:H.sha(b) for n,b in self.files.items()},{'blocks':[]},'localize',
            finalize={'kind':'finalize-native','policy':'new','files_after':{},'blocks':[]})
        self.receipt = self.root/'test.zip.receipt.json'; self.receipt.write_text(json.dumps(receipt))
        self.delivery = self.root/'delivery.json'; self.delivery.write_text(json.dumps({
            'delivery_ready':True,'sha256':self.digest,'preview':{'url':'http://127.0.0.1:8123/'}}))
        self.bundle = self.root/'handoff.zip'

    def export(self,project=None): return H.export(self.game,self.source,self.delivery,self.bundle,project)
    def rewrite(self,fn):
        with zipfile.ZipFile(self.bundle) as z: data={n:z.read(n) for n in z.namelist()}
        fn(data)
        with zipfile.ZipFile(self.bundle,'w') as z:
            for n,b in data.items(): z.writestr(n,b)

    def test_missing_receipt_can_receive_but_cannot_get_current_approval(self):
        self.receipt.unlink(); before=self.game.read_bytes()
        r=H.receive(self.game,self.source)
        self.assertTrue(r['intake_passed']); self.assertFalse(r['delivery_ready'])
        self.assertFalse(r['current_runtime_approval']); self.assertEqual(r['writer_evidence']['state'],'unavailable')
        self.assertEqual(self.game.read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'same-byte writer'): self.export()

    def test_official_receipt_relocates_and_renamed_zip_does_not_need_author_paths(self):
        self.export(); incoming=self.root/'other-computer'; incoming.mkdir()
        game=incoming/'renamed.zip'; source=incoming/'source-renamed.zip'; evidence=incoming/'proof.zip'
        for a,b in [(self.game,game),(self.source,source),(self.bundle,evidence)]: shutil.copyfile(a,b)
        self.receipt.unlink();self.delivery.unlink();self.game.unlink();self.source.unlink();self.bundle.unlink()
        r=H.receive(game,source,evidence)
        self.assertTrue(r['intake_passed'],r['problems']); self.assertEqual(r['writer_evidence']['state'],'verified')
        self.assertFalse(r['delivery_ready']);self.assertFalse(r['current_runtime_approval'])
        self.assertTrue(r['source_identity']['paired_to_test_zip'])

    def test_other_source_zip_is_not_the_paired_source(self):
        self.export()
        with zipfile.ZipFile(self.source,'w') as z:z.writestr('assets/other.js','// changed')
        r=H.receive(self.game,self.source,self.bundle)
        self.assertFalse(r['intake_passed']);self.assertIn('source ZIP does not match',' '.join(r['problems']))

    def test_other_test_bytes_cannot_reuse_portable_receipt(self):
        self.export()
        with zipfile.ZipFile(self.game,'a') as z:z.writestr('extra.js','// changed')
        r=H.receive(self.game,self.source,self.bundle)
        self.assertFalse(r['intake_passed']);self.assertIn('test ZIP bytes',' '.join(r['problems']))

    def test_changed_evidence_is_rejected_without_import(self):
        self.export();self.rewrite(lambda d:d.update({'delivery.json':b'{}'}))
        r=H.receive(self.game,self.source,self.bundle)
        self.assertFalse(r['intake_passed']);self.assertIn('hash mismatch',' '.join(r['problems']))

    def test_handoff_path_traversal_is_not_extracted(self):
        self.export();self.rewrite(lambda d:d.update({'../outside.txt':b'bad'}))
        r=H.receive(self.game,self.source,self.bundle)
        self.assertFalse(r['intake_passed']);self.assertFalse((self.root.parent/'outside.txt').exists())

    def test_missing_author_records_are_a_gap_not_a_fabricated_pass(self):
        r=self.export(); self.assertEqual(r['ledger']['state'],'missing')
        r=H.receive(self.game,self.source,self.bundle)
        self.assertTrue(r['intake_passed']); self.assertTrue(any('per-check' in e for e in r['evidence_gaps']))

    def test_no_current_delivery_record_cannot_export_as_complete_author_handoff(self):
        self.delivery.write_text(json.dumps({'sha256':self.digest,'delivery_ready':False}))
        with self.assertRaisesRegex(ValueError,'successful delivery record'):self.export()
        self.assertFalse(self.bundle.exists())

    def test_original_ledger_exports_imports_and_preserves_time_without_running(self):
        from check_ledger import Ledger
        author=self.root/'author'; receiver=self.root/'receiver'
        raw=self.root/'unit-evidence.json';raw.write_text('{"unit":true}')
        roots={'package':{'game.js':H.sha(self.files['game.js'])}}
        l=Ledger(author)
        try:
            plan=l.prepare('startup.fixture',roots,{}, {'unit':'tool-hash'},domain='startup')
            l.execute(plan,lambda:{'passed':True,'raw':str(raw)},lambda r:r['passed'])
            original=l.previous('startup.fixture')[0]['executed_at']
        finally:l.close()
        self.export(author)
        r=H.receive(self.game,self.source,self.bundle)
        self.assertTrue(r['intake_passed']);self.assertFalse((receiver/'docs').exists())
        self.assertFalse(r['portable_evidence']['current_approval'])
        # Explicitly exercise the existing trusted ledger importer on this unit bundle.
        unpack=self.root/'unpack'
        with zipfile.ZipFile(self.bundle) as z:z.extractall(unpack)
        l=Ledger(receiver)
        try:
            r=l.import_bundle(unpack/'checks');self.assertEqual(r['imported'],1)
            self.assertFalse(r['current_approval']);self.assertEqual(l.previous('startup.fixture')[0]['executed_at'],original)
            self.assertEqual(l.prepare('startup.fixture',roots,{}, {'unit':'tool-hash'},domain='startup')['action'],'reuse')
            changed={'package':{'game.js':'changed'}}
            self.assertNotEqual(l.prepare('startup.fixture',changed,{}, {'unit':'tool-hash'},domain='startup')['action'],'reuse')
        finally:l.close()

    def test_existing_output_is_never_overwritten(self):
        self.bundle.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'new evidence ZIP'):self.export()
        self.assertEqual(self.bundle.read_bytes(),b'keep')

    def test_missing_source_is_disclosed_and_invalid_source_rejected(self):
        self.assertTrue(H.receive(self.game)['evidence_gaps'])
        self.source.write_bytes(b'not a source zip')
        self.assertFalse(H.receive(self.game,self.source)['intake_passed'])


if __name__ == '__main__': unittest.main()
