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

    # ---- 2026-11-12: the default hand-over of a finished game (deliver) ----
    def project(self, secret=False):
        project = self.root/'工程 Game'; (project/'assets/Script').mkdir(parents=True)
        (project/'assets/Script/Main.js').write_text('cc.log("main");')
        (project/'assets/Script/Main.js.meta').write_text('{"uuid":"a"}')
        (project/'settings').mkdir(); (project/'settings/project.json').write_text('{"appSecret": "%s"}' % ('abcdef123' if secret else ''))
        (project/'library').mkdir(); (project/'library/cache.json').write_text('{}')
        (project/'.git').mkdir(); (project/'.git/config').write_text('[core]')
        return project
    def ready(self, **extra):
        self.delivery.write_text(json.dumps({'delivery_ready':True,'sha256':self.digest,'archive':str(self.game),
                                             'preview':{'url':'http://127.0.0.1:8123/'},**extra}))

    def test_deliver_makes_the_source_zip_and_the_evidence_zip_next_to_the_test_zip(self):
        project=self.project(); self.ready(); before=self.game.read_bytes()
        r=H.deliver(self.delivery,project)
        self.assertEqual(r['status'],'team_handoff_ready'); self.assertEqual(r['made'],{'source_zip':True,'evidence_zip':True})
        source=Path(r['source_zip']); evidence=Path(r['evidence_zip'])
        self.assertEqual((source.parent,source.name),(self.root.resolve(),'test_源码.zip')); self.assertEqual(evidence.name,'test_交接证据.zip')
        self.assertEqual(self.game.read_bytes(),before,'the upload ZIP is never touched')
        with zipfile.ZipFile(source) as z: names=z.namelist()
        self.assertIn('工程 Game/assets/Script/Main.js',names)
        self.assertFalse([n for n in names if '.git' in n or n.startswith('工程 Game/library/')],'no VCS folder, no cache')
        got=H.receive(self.game,source,evidence)
        self.assertTrue(got['intake_passed'],got['problems']); self.assertTrue(got['source_identity']['paired_to_test_zip'])
        self.assertEqual(r['reply_lines'][:3],['测试包：'+str(self.game.resolve()),'源码包：'+str(source),'交接证据包：'+str(evidence)])
        self.assertIn('没有逐项检查账本',r['reply_lines'][3])

    def test_deliver_twice_returns_the_same_files(self):
        project=self.project(); self.ready()
        first=H.deliver(self.delivery,project); second=H.deliver(self.delivery,project)
        self.assertEqual(second['made'],{'source_zip':False,'evidence_zip':False})
        self.assertEqual((second['source_zip'],second['evidence_zip'],second['sha256']),(first['source_zip'],first['evidence_zip'],first['sha256']))
        self.assertEqual(sorted(p.name for p in self.root.glob('test_*.zip')),['test_交接证据.zip','test_源码.zip'])

    def test_deliver_after_the_project_changed_writes_a_new_source_zip_and_keeps_the_old_one(self):
        project=self.project(); self.ready()
        first=H.deliver(self.delivery,project); old=Path(first['source_zip']).read_bytes()
        (project/'assets/Script/Main.js').write_text('cc.log("changed");')
        second=H.deliver(self.delivery,project)
        self.assertEqual(Path(second['source_zip']).name,'test_源码 (2).zip'); self.assertEqual(Path(second['evidence_zip']).name,'test_交接证据 (2).zip')
        self.assertEqual(Path(first['source_zip']).read_bytes(),old,'nothing existing is overwritten')

    def test_deliver_refuses_without_a_successful_delivery_record_or_with_another_zip(self):
        project=self.project()
        self.delivery.write_text(json.dumps({'delivery_ready':False,'sha256':self.digest,'archive':str(self.game)}))
        with self.assertRaisesRegex(ValueError,'delivery_ready'):H.deliver(self.delivery,project)
        self.ready()
        with zipfile.ZipFile(self.game,'a') as z:z.writestr('extra.js','// changed after the record')
        with self.assertRaisesRegex(ValueError,'不是同一份文件'):H.deliver(self.delivery,project)
        self.assertEqual(list(self.root.glob('test_*.zip')),[])

    def test_deliver_refuses_a_project_with_a_credential_and_writes_nothing(self):
        project=self.project(secret=True); self.ready()
        with self.assertRaisesRegex(ValueError,'账号、密码或密钥'):H.deliver(self.delivery,project)
        self.assertEqual(list(self.root.glob('test_*.zip')),[])

    def test_deliver_refuses_a_given_source_zip_of_another_source(self):
        project=self.project(); self.ready()
        with self.assertRaisesRegex(ValueError,'不是同一份源码'):H.deliver(self.delivery,project,self.source)
        self.assertEqual(list(self.root.glob('test_*.zip')),[])

    def test_deliver_refuses_when_the_project_changed_after_the_delivery_check(self):
        project=self.project(); self.ready(logic_source_binding={'current_source_sha256':'0'*64})
        with self.assertRaisesRegex(ValueError,'交付复核之后工程又改过'):H.deliver(self.delivery,project)
        self.ready(logic_source_binding={'current_source_sha256':H.source_identity(project)})
        self.assertEqual(H.deliver(self.delivery,project)['status'],'team_handoff_ready')

    def test_deliver_uses_the_source_zip_the_delivery_record_already_checked(self):
        project=self.project(); from make_source_zip import build
        mine=self.root/'Given_Source.zip'; self.assertTrue(build(project,mine)['written'])
        self.ready(source_hygiene={'source':str(mine),'passed':True})
        r=H.deliver(self.delivery,project)
        self.assertEqual(r['source_zip'],str(mine.resolve())); self.assertEqual(r['made'],{'source_zip':False,'evidence_zip':True})

    def test_deliver_with_the_test_zip_inside_the_project_puts_both_zips_next_to_the_project(self):
        project=self.project(); inside=project/'delivery'; inside.mkdir()
        game=inside/'Final.zip'; shutil.copyfile(self.game,game); shutil.copyfile(self.receipt,str(game)+'.receipt.json')
        self.delivery.write_text(json.dumps({'delivery_ready':True,'sha256':self.digest,'archive':str(game)}))
        r=H.deliver(self.delivery,project)
        self.assertEqual(Path(r['source_zip']).parent,project.parent.resolve()); self.assertEqual(Path(r['evidence_zip']).parent,project.parent.resolve())
        self.assertTrue(H.receive(game,r['source_zip'],r['evidence_zip'])['intake_passed'])
        with self.assertRaisesRegex(ValueError,'工程外'):H.deliver(self.delivery,project,out_dir=inside)

    def test_source_identity_is_the_same_for_a_project_and_its_source_zip_wherever_the_project_is(self):
        from make_source_zip import build
        from logic_regressions import source_digest
        project=self.project(); out=self.root/'s.zip'; build(project,out)
        self.assertEqual(H.source_identity(project),H.source_identity(out)); self.assertEqual(H.source_identity(project),source_digest(project))
        moved=self.root/'build'/'Game'; moved.parent.mkdir(); shutil.copytree(project,moved)
        self.assertEqual(H.source_identity(moved),H.source_identity(out),'a parent folder named build does not empty the identity')

    def test_existing_output_is_never_overwritten(self):
        self.bundle.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'new evidence ZIP'):self.export()
        self.assertEqual(self.bundle.read_bytes(),b'keep')

    def test_missing_source_is_disclosed_and_invalid_source_rejected(self):
        self.assertTrue(H.receive(self.game)['evidence_gaps'])
        self.source.write_bytes(b'not a source zip')
        self.assertFalse(H.receive(self.game,self.source)['intake_passed'])


if __name__ == '__main__': unittest.main()
