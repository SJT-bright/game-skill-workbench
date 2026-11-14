"""Same-delivery archive reuse controls; no game, browser or external CLI.

Actual ZIP CRC/configuration/membership and original-receipt rules execute.
Unrelated host/VM/functional/preview owners are explicit test fixtures only.
"""
from contextlib import ExitStack, nullcontext
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[1] / 'cocos-game-check/package-check/scripts'
sys.path.insert(0, str(PACKAGE))
import verify_native_zip as V
import upload_size_gate as U
import delivery_archive_context as C
import check_package as P
import prepare_delivery as D

REAL_REUSABLE = P.reusable_regressions
APP = 'synthetic-delivery-archive'
sha = lambda data: hashlib.sha256(data).hexdigest()


class DeliveryArchiveContext(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='delivery-archive-controls-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = self.root/'native'; self.native.mkdir()
        self.project = self.root/'project'; (self.project/'assets').mkdir(parents=True)
        (self.project/'docs').mkdir(); (self.project/'docs/board.txt').write_text('localize')
        self.archive = self.root/'candidate.zip'
        self.files = {'game.js':b'// inert archive fixture; never run\n', 'game.json':b'{}',
                      'project.config.json':json.dumps({'appid':APP}).encode()}
        for name, data in self.files.items(): (self.native/name).write_bytes(data)
        self.write_archive(self.files)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.cli = self.stack.enter_context(patch('tiktok_cli_gate.verify', return_value={'passed':True,'errors':[], 'version':'fixture-no-cli'}))
        self.stack.enter_context(patch.object(U, 'enforce_tiktok_host', return_value=None))
        self.stack.enter_context(patch('audit_upload_startup.audit_files', return_value={'passed':True,'errors':[], 'fixture_no_VM':True}))
        self.stack.enter_context(patch('package_gates.run', return_value={'blocks':[], 'warnings':[], 'gates':[], 'missing':[], 'policy':'new', 'policy_reason':'fixture'}))
        self.stack.enter_context(patch.object(P,'regression_context',side_effect=lambda files,folder,adapter,board,policy,project:(project,adapter,board or 'localize','new')))
        self.stack.enter_context(patch.object(P,'reusable_regressions',return_value={'reused':True,'rewarded_ad_regression':{'status':'not_applicable'},'runtime_regression':{'status':'passed','passed':True,'suites':[]}}))
        self.stack.enter_context(patch.object(P,'packed_assets',return_value={'passed':True,'errors':[]}))
        self.stack.enter_context(patch.object(P,'tools_in_use',return_value={'status':'fixture','summary':[]}))
        self.stack.enter_context(patch('make_tiktok_zip.pre_home',return_value={}))
        self.contract = self.root/'startup.json'; self.contract.write_text('{"binding":{"web_tree_sha256":"synthetic-web"}}')
        startup = {'passed':True,'checks':[], 'startup_contract_sha256':sha(self.contract.read_bytes()), 'current_binding':{'web_tree_sha256':'synthetic-web'}}
        (self.root/'other-temp').mkdir()
        self.stack.enter_context(patch.object(D.tempfile,'gettempdir',return_value=str(self.root/'other-temp')))
        self.stack.enter_context(patch.object(D,'audit_final_startup',return_value=startup))
        self.stack.enter_context(patch('audit_final_storage.audit_final_storage',return_value={'id':'storage.native.contract','game_executed':False}))
        self.stack.enter_context(patch.object(D.package_obligations,'verify',return_value={'fixture':True}))
        self.stack.enter_context(patch.object(D.package_obligations,'publication_guard',side_effect=lambda *a,**k:nullcontext()))
        self.stack.enter_context(patch.object(D,'verify_preview',return_value={'web_tree_sha256':'synthetic-web'}))
        self.stack.enter_context(patch('production_hooks.collect_after_delivery',return_value={'fixture':True}))

    def write_archive(self, files, *, receipt=True, directory=None):
        with zipfile.ZipFile(self.archive,'w',compression=zipfile.ZIP_STORED) as archive:
            if directory is not None: archive.writestr(directory,b'')
            for name,data in files.items(): archive.writestr(name,data)
        if receipt:
            hashes = {name:sha(data) for name,data in files.items()}
            fin = {'kind':'finalize-native','policy':'new','board':'localize','blocks':[], 'policy_override':False,'files_after':hashes,'steps':[],'table':[]}
            self.receipt = V.receipt_path(self.archive)
            self.receipt.write_text(json.dumps(V.make_receipt('make_tiktok_zip',self.archive,sha(self.archive.read_bytes()),hashes,
                {'blocks':[],'warnings':[],'gates':[]},'localize',finalize=fin)))

    def fresh(self):
        result, context = C.inspect_delivery_archive(self.archive)
        self.assertTrue(result['passed'],result)
        self.addCleanup(context.close)
        return result,context

    def test_fresh_payload_once_and_canonical_verifier_once_for_board_and_check(self):
        original=zipfile.ZipFile.read; reads=[]
        def count(archive,name,*a,**k):
            reads.append(name.filename if isinstance(name,zipfile.ZipInfo) else name)
            return original(archive,name,*a,**k)
        with patch.object(zipfile.ZipFile,'read',new=count),patch.object(V,'verify',wraps=V.verify) as canonical:
            fresh,ctx=self.fresh()
            self.assertEqual(D.writer_board(self.archive,APP,self.project,files=self.files,_archive_context=ctx),'localize')
            result=P.check(self.archive,APP,self.native,board='localize',reuse_writer_regressions=True,project=self.project,_archive_context=ctx)
            self.assertEqual(result['sha256'],fresh['sha256'])
            self.assertEqual(canonical.call_count,1)
        self.assertEqual(sorted(reads),sorted(self.files))
        self.assertEqual(self.cli.call_count,1)
        print('DELIVERY_ARCHIVE_COUNTS '+json.dumps({'fresh_member_reads':len(reads),'members':len(self.files),'canonical_verifier_calls':canonical.call_count,'fresh_CLI_fixture_calls':self.cli.call_count}))

    def test_full_prepare_records_fresh_and_consumer_timings_and_closes_context(self):
        record=self.root/'delivery.json'; original=zipfile.ZipFile.read; reads=[];contexts=[]
        def count(archive,name,*a,**k):reads.append(name);return original(archive,name,*a,**k)
        real=C.inspect_delivery_archive
        def factory(*a,**k):
            result,ctx=real(*a,**k);contexts.append(ctx);return result,ctx
        with patch.object(zipfile.ZipFile,'read',new=count),patch.object(C,'inspect_delivery_archive',side_effect=factory):
            result=D.prepare(self.archive,self.native,APP,record,project=self.project,startup_contract=self.contract,resource_manifest=self.root/'resources.json',preview_url='http://fixture.invalid/')
        self.assertTrue(result['delivery_ready']);self.assertEqual(len(reads),len(self.files))
        persisted=json.loads(record.read_text());self.assertEqual(persisted['check_timings'],result['check_timings'])
        self.assertEqual(persisted['check_timings']['status'],'verification_snapshot_before_publication')
        timing=json.loads(Path(str(record)+'.timing.json').read_text())
        self.assertEqual(timing['status'],'completed');self.assertGreater(timing['total_seconds'],0)
        self.assertEqual(timing['archive_sha256'],sha(self.archive.read_bytes()))
        self.assertEqual(timing['record_sha256'],sha(record.read_bytes()))
        self.assertEqual(timing['record_kind'],'delivery')
        self.assertEqual(timing['fresh_run_id'],json.loads(Path(str(record)+'.size.json').read_text())['run_id'])
        print('DELIVERY_TIMING_CONTROL '+json.dumps(timing,sort_keys=True))
        for name in ['package.fresh_size_crc_cli','package.writer_board','package.check','storage.native.contract','startup.native.current_evidence','preview.same_build']:
            rows=[r for r in timing['nodes'] if r['id']==name];self.assertEqual(len(rows),1);self.assertGreaterEqual(rows[0]['seconds'],0)
        with self.assertRaisesRegex(ValueError,'not active'):C.consume_delivery_archive(contexts[0],self.archive,APP)

    def test_new_delivery_always_gets_another_fresh_payload_and_cli(self):
        result,a=self.fresh();C.consume_delivery_archive(a,self.archive,APP);a.close()
        result,b=self.fresh();C.consume_delivery_archive(b,self.archive,APP)
        self.assertIsNot(a,b);self.assertEqual(self.cli.call_count,2)
        with self.assertRaisesRegex(ValueError,'not active'):C.consume_delivery_archive(a,self.archive,APP)

    def test_wrong_app_id_rejected_on_first_and_reused_consumer(self):
        _,ctx=self.fresh()
        with self.assertRaisesRegex(ValueError,'App ID'):C.consume_delivery_archive(ctx,self.archive,'wrong')
        C.consume_delivery_archive(ctx,self.archive,APP)
        with self.assertRaisesRegex(ValueError,'App ID'):C.consume_delivery_archive(ctx,self.archive,'wrong')

    def test_native_membership_and_bytes_must_match(self):
        _,ctx=self.fresh()
        for changed in [dict(self.files,extra=b'new'),dict(self.files,**{'game.js':b'changed'})]:
            with self.subTest(changed=sorted(changed)),self.assertRaisesRegex(ValueError,'Native input'):
                D.writer_board(self.archive,APP,self.project,files=changed,_archive_context=ctx)

    def test_writer_board_and_project_board_disagreement_refused(self):
        _,ctx=self.fresh();(self.project/'docs/board.txt').write_text('remake')
        with self.assertRaisesRegex(ValueError,'project board'):D.writer_board(self.archive,APP,self.project,_archive_context=ctx)

    def test_receipt_board_and_finalize_disagreement_refused(self):
        data=json.loads(self.receipt.read_text());data['finalize']['board']='remake';self.receipt.write_text(json.dumps(data))
        _,ctx=self.fresh()
        with self.assertRaisesRegex(ValueError,'finalize record'):D.writer_board(self.archive,APP,self.project,_archive_context=ctx)

    def test_receipt_changed_even_to_another_valid_document_refused(self):
        _,ctx=self.fresh();C.consume_delivery_archive(ctx,self.archive,APP)
        data=json.loads(self.receipt.read_text());data['new_metadata']='still structurally official';self.receipt.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'receipt changed'):C.consume_delivery_archive(ctx,self.archive,APP)

    def test_same_byte_receipt_symlink_replacement_is_refused(self):
        _,ctx=self.fresh();C.consume_delivery_archive(ctx,self.archive,APP)
        target=self.receipt.with_name('same-bytes-original.json');self.receipt.rename(target);self.receipt.symlink_to(target)
        self.assertNotEqual(V.receipt_status(self.archive,sha(self.archive.read_bytes()),{n:sha(b) for n,b in self.files.items()})['entry'],'official')
        with self.assertRaisesRegex(ValueError,'linked'):C.consume_delivery_archive(ctx,self.archive,APP)

    def test_zip_replaced_after_fresh_inspection_refused(self):
        _,ctx=self.fresh();self.write_archive(dict(self.files,extra=b'new member'),receipt=False)
        with self.assertRaisesRegex(ValueError,'ZIP changed'):C.consume_delivery_archive(ctx,self.archive,APP)

    def test_closed_or_forged_context_never_falls_back_to_fresh_verification(self):
        _,ctx=self.fresh();ctx.close()
        for fake in [ctx,{'passed':True,'file_sha256':{}},object()]:
            with self.subTest(fake=type(fake).__name__),patch.object(V,'verify',side_effect=AssertionError('no fallback')):
                with self.assertRaises(ValueError):P.check(self.archive,APP,self.native,reuse_writer_regressions=True,_archive_context=fake)

    def test_preserved_directory_metadata_keeps_forbidden_directory_rule(self):
        self.write_archive(self.files,directory='.git/')
        _,ctx=self.fresh()
        with self.assertRaisesRegex(ValueError,'Not allowed'):C.consume_delivery_archive(ctx,self.archive,APP)

    def test_independent_check_keeps_full_payload_read(self):
        original=zipfile.ZipFile.read;reads=[]
        def count(archive,name,*a,**k):reads.append(name);return original(archive,name,*a,**k)
        with patch.object(zipfile.ZipFile,'read',new=count),patch.object(V,'verify',wraps=V.verify) as canonical:
            result=P.check(self.archive,APP,self.native,board='localize',reuse_writer_regressions=True,project=self.project)
        self.assertEqual(canonical.call_count,1);self.assertEqual(len(reads),len(self.files));self.assertEqual(result['entry'],'official')

    def formal34_fixture(self):
        data=json.loads((HERE/'test-fixtures/delivery-formal34.json').read_text())
        archive=self.root/data['zip_name'];archive.write_bytes(base64.b64decode(data['zip_base64']))
        receipt=V.receipt_path(archive);receipt.write_text(json.dumps(data['receipt']))
        adapter=self.root/'formal34-adapter.json';adapter.write_text(data['adapter_text'])
        self.assertEqual(sha(archive.read_bytes()),data['zip_sha256'])
        self.assertEqual(sha(json.dumps(data['receipt'],sort_keys=True,separators=(',',':')).encode()),data['receipt_document_sha256'])
        return data,archive,receipt,adapter

    def test_original_formal34_receipt_and_regression_tools_remain_reusable(self):
        data,archive,receipt,adapter=self.formal34_fixture();before=receipt.read_bytes()
        report,ctx=C.inspect_delivery_archive(archive);self.assertTrue(report['passed'],report);self.addCleanup(ctx.close)
        current=C.consume_delivery_archive(ctx,archive,'formal34-context-fixture')
        self.assertEqual(current['entry'],'official')
        payload=C.delivery_payload(ctx,archive)
        # Real existing consumer and real current tool digests, not a compatibility waiver.
        reused=REAL_REUSABLE(receipt,payload,adapter,'new');self.assertTrue(reused['reused'],reused)
        self.assertEqual(reused['runtime_regression']['tool_sha256'],data['original_tool_sha256']['runtime'])
        self.assertEqual(receipt.read_bytes(),before)
        self.assertEqual(P.runtime_regression_gate.tool_digest(P.runtime_regression_gate.load_suites()),data['original_tool_sha256']['runtime'])
        self.assertEqual(P.ad_regression_gate.tool_digest(),data['original_tool_sha256']['ad'])

    def test_unknown_old_runtime_tool_or_failed_summary_is_not_accepted(self):
        data,archive,receipt,adapter=self.formal34_fixture()
        report,ctx=C.inspect_delivery_archive(archive);self.assertTrue(report['passed']);self.addCleanup(ctx.close)
        C.consume_delivery_archive(ctx,archive,'formal34-context-fixture')
        payload=C.delivery_payload(ctx,archive)
        for update in [{'tool_sha256':'0'*64},{'status':'failed','passed':False}]:
            changed=copy.deepcopy(data['receipt']);changed['regressions']['runtime_regression'].update(update);receipt.write_text(json.dumps(changed))
            result=REAL_REUSABLE(receipt,payload,adapter,'new');self.assertFalse(result['reused'],result)
        receipt.write_text(json.dumps(data['receipt']));adapter.write_text(data['adapter_text']+' ')
        self.assertFalse(REAL_REUSABLE(receipt,payload,adapter,'new')['reused'])

    def test_formal34_same_bytes_renamed_archive_still_uses_original_receipt(self):
        data,archive,receipt,adapter=self.formal34_fixture();renamed=archive.with_name('renamed-formal34.zip');archive.rename(renamed)
        report,ctx=C.inspect_delivery_archive(renamed);self.assertTrue(report['passed'],report);self.addCleanup(ctx.close)
        result=C.consume_delivery_archive(ctx,renamed,'formal34-context-fixture')
        self.assertEqual(Path(result['receipt']),receipt)
        self.assertEqual(result['sha256'],data['zip_sha256'])

    def test_fresh_crc_corruption_is_not_exported_as_a_context(self):
        blob=bytearray(self.archive.read_bytes());at=blob.index(self.files['game.js']);blob[at]^=1;self.archive.write_bytes(blob)
        report,ctx=C.inspect_delivery_archive(self.archive)
        self.assertFalse(report['passed']);self.assertIsNone(ctx);self.cli.assert_not_called()

    def test_duplicate_and_symlink_members_are_rejected_before_context(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(self.archive,'a') as archive:archive.writestr('game.js',b'duplicate')
        report,ctx=C.inspect_delivery_archive(self.archive);self.assertFalse(report['passed']);self.assertIsNone(ctx)
        self.write_archive(self.files)
        with zipfile.ZipFile(self.archive,'a') as archive:
            item=zipfile.ZipInfo('linked');item.create_system=3;item.external_attr=0o120777<<16;archive.writestr(item,b'game.js')
        report,ctx=C.inspect_delivery_archive(self.archive);self.assertFalse(report['passed']);self.assertIsNone(ctx)

    def test_receipt_swapped_after_fresh_gate_before_context_capture_refused(self):
        original=U.inspect_final_zip
        def replace(*args,**kwargs):
            result=original(*args,**kwargs)
            data=json.loads(self.receipt.read_text());data['metadata']='replaced at gate boundary';self.receipt.write_text(json.dumps(data))
            return result
        with patch.object(U,'inspect_final_zip',side_effect=replace):
            with self.assertRaisesRegex(ValueError,'receipt changed'):C.inspect_delivery_archive(self.archive)

    def test_record_collision_timing_binds_only_our_blocked_record(self):
        record=self.root/'competing.json';other=b'{"owned_by":"another invocation"}\n'
        def compete(*unused,**kwargs):
            record.write_bytes(other);return {'web_tree_sha256':'synthetic-web'}
        with patch.object(D,'verify_preview',side_effect=compete):
            with self.assertRaises(FileExistsError):
                D.prepare(self.archive,self.native,APP,record,project=self.project,startup_contract=self.contract,
                          resource_manifest=self.root/'resources.json',preview_url='http://fixture.invalid/')
        self.assertEqual(record.read_bytes(),other)
        blocked=Path(str(record)+'.blocked.json');self.assertTrue(blocked.is_file())
        timing=json.loads(Path(str(record)+'.timing.json').read_text())
        self.assertEqual(timing['record_kind'],'blocked');self.assertEqual(timing['record'],str(blocked.resolve()))
        self.assertEqual(timing['record_sha256'],sha(blocked.read_bytes()))
        self.assertTrue(timing['record_unchanged']);self.assertNotEqual(timing['record_sha256'],sha(other))

    def test_late_preview_receipt_mutation_blocks_success_record(self):
        record=self.root/'late.json'
        def mutate(*unused,**kwargs):
            data=json.loads(self.receipt.read_text());data['late']='replacement';self.receipt.write_text(json.dumps(data));return {'web_tree_sha256':'synthetic-web'}
        created=[];factory=C.inspect_delivery_archive
        def capture(*a,**k):
            report,ctx=factory(*a,**k);created.append(ctx);return report,ctx
        with patch.object(D,'verify_preview',side_effect=mutate),patch.object(C,'inspect_delivery_archive',side_effect=capture):
            with self.assertRaisesRegex(ValueError,'receipt changed'):
                D.prepare(self.archive,self.native,APP,record,project=self.project,startup_contract=self.contract,resource_manifest=self.root/'resources.json',preview_url='http://fixture.invalid/')
        with self.assertRaisesRegex(ValueError,'not active'):C.consume_delivery_archive(created[0],self.archive,APP)
        self.assertFalse(record.exists());self.assertFalse(json.loads(Path(str(record)+'.blocked.json').read_text())['delivery_ready'])
        timing=json.loads(Path(str(record)+'.timing.json').read_text())
        self.assertEqual(timing['status'],'failed');self.assertEqual(timing['record_kind'],'blocked')
        self.assertEqual(timing['record_sha256'],sha(Path(str(record)+'.blocked.json').read_bytes()))
        self.assertEqual(timing['archive_sha256'],sha(self.archive.read_bytes()))


if __name__=='__main__':unittest.main()
