"""Actual ZIP + loopback preview readback for scoped immutable old contracts.

Unrelated game acceptance/CLI is isolated by the existing writer fixture. This
proves the delivery consumer chooses current Web identity, never a device pass.
"""
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

import test_gate_order_and_identity as W
import test_package_checks as P
import prepare_delivery as delivery
import verify_delivery_preview as preview
import browser_slots
from check_known_issues import tree_sha


class ScopedPreviewDelivery(unittest.TestCase):
    def setUp(self):
        self.static = P.runtime_patch().start()
        self.addCleanup(self.static.stop)
        ad_policy=patch('ad_standard_scope.requirement',return_value={'required':False,'reason':'synthetic delivery binding fixture only; no ad acceptance'})
        ad_policy.start();self.addCleanup(ad_policy.stop)
        W.WriterOrder.setUp(self)
        self.addCleanup(self.temp.cleanup)

    def test_current_snapshot_passes_and_old_snapshot_refuses_without_changing_original_contract(self):
        with patch('audit_final_package_startup.audit_final_startup', return_value={'passed': True}):
            result = W.build(self.native, P.APP, self.out, resource_manifest=self.manifest,
                             project=self.project, web=self.native)
        web = self.root / 'current-web'; web.mkdir()
        body = b'<html><script src="main.js"></script><p>synthetic fixed-phone payload</p></html>'
        (web/'index.html').write_bytes(body); (web/'main.js').write_bytes(b'window.syntheticCurrent=1;')
        (web/'later.png').write_bytes(b'new deferred asset')
        current = tree_sha(web); original = '0'*64
        contract = self.root/'old-contract.json'
        contract.write_text(json.dumps({'binding':{'web_tree_sha256':original},'synthetic':True}))
        before = contract.read_bytes()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                rel = self.path.split('?',1)[0]
                if rel=='/': data=b'<meta content="fixed-phone-v1"><meta name="game-preview-mode"><script>new URL(\'/game/index.html\')</script>'
                elif rel=='/game/index.html': data=body
                elif rel=='/game/main.js': data=(web/'main.js').read_bytes()
                else:
                    self.send_response(404); self.end_headers(); return
                self.send_response(200); self.end_headers(); self.wfile.write(data)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url='http://127.0.0.1:%s/'%server.server_port
            identity='synthetic-current-http-owner'
            slot={'kind':'preview','id':'synthetic-scoped-delivery','url':url,'keep':True,
                  'dir':str(web),'pid':os.getpid(),'process_identity':identity}
            checked=dict(result,runtime_execution='existing_evidence_only',file_sha256=result['file_sha256'])
            startup={'passed':True,'startup_contract_sha256':hashlib.sha256(before).hexdigest(),
                     'current_binding':{'web_tree_sha256':current},'checks':[]}
            with patch('prepare_delivery.tempfile.gettempdir',return_value=str(self.root/'other-temp')), \
                 patch('tiktok_cli_gate.verify',return_value={'passed':True,'errors':[],'version':'synthetic-cli-boundary'}), \
                 patch.object(delivery,'check',return_value=checked), \
                 patch.object(delivery,'audit_final_startup',return_value=startup) as startup_gate, \
                 patch.object(preview,'slots',return_value=[slot]), \
                 patch.object(preview,'process_identity',return_value=identity), \
                 patch('audit_native_startup_renderer.execute_registered',side_effect=AssertionError('browser replay forbidden')) as renderer:
                # A real retained snapshot and real HTTP entry/script readback.
                receipt=delivery.prepare(self.out,self.native,P.APP,self.root/'delivery-current.json',
                    project=self.project,startup_contract=contract,resource_manifest=self.manifest,preview_url=url)
                self.assertTrue(receipt['delivery_ready'])
                self.assertEqual(receipt['preview']['web_tree_sha256'],current)
                self.assertEqual(receipt['checks'][-1]['web_tree_sha256'],current)
                self.assertTrue(all(row['same'] for row in receipt['preview']['entry_files']))
                renderer.assert_not_called()
                # Simulate serving the old retained snapshot while current proof
                # still names the new Web. Its actual tree must fail immediately.
                old=self.root/'old-web';old.mkdir()
                for path in web.iterdir(): (old/path.name).write_bytes(path.read_bytes())
                (old/'later.png').write_bytes(b'old deferred asset')
                slot['dir']=str(old)
                with self.assertRaisesRegex(ValueError,'Web 构建不同'):
                    delivery.prepare(self.out,self.native,P.APP,self.root/'delivery-old.json',
                        project=self.project,startup_contract=contract,resource_manifest=self.manifest,preview_url=url)
                self.assertFalse((self.root/'delivery-old.json').exists())
                self.assertEqual(contract.read_bytes(),before)
                self.assertTrue(all(call.kwargs['reuse_only'] for call in startup_gate.call_args_list))
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
            self.assertFalse(thread.is_alive())


if __name__=='__main__': unittest.main()
