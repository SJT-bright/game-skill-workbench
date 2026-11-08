"""Official capture/verify entry tests with a CDP protocol fixture, never a real browser."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import audit_page_richness as richness
import art_round_check

HERE = Path(__file__).resolve().parent
MODULE = HERE / 'art_capture_round.mjs'
COMPAT = json.loads((HERE / 'art-capture-producer-compat.json').read_text())


def previous_collector():
    """Reconstruct only the exact reviewed metadata-only parent, for executable proof."""
    text = MODULE.read_text()
    start = text.index('// Exact compatibility for the reviewed producer-metadata-only release.')
    end = text.index('const write =', start)
    text = text[:start] + text[end:]
    text = text.replace('policy:digest(policy), collector:collectorFingerprint()};',
        "policy:digest(policy), collector:sha(Buffer.concat([fs.readFileSync(fileURLToPath(import.meta.url)),\n      fs.readFileSync(new URL('./ui_dump.js',import.meta.url))]))};")
    text = text.replace("{...dump,producer:'ego_page.dump_ui',screen:", '{...dump,screen:')
    encoded = text.encode()
    if hashlib.sha256(encoded).hexdigest() != COMPAT['before_script_sha256']:
        raise AssertionError('unexpected collector semantic change; exact metadata compatibility proof no longer holds')
    return encoded


class CaptureProducer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project, self.build, self.out = self.root/'project', self.root/'web', self.root/'captures'
        for p in (self.project/'assets', self.project/'docs/art', self.build):p.mkdir(parents=True)
        (self.project/'assets/layout.json').write_text('{"slot":40}')
        (self.build/'index.html').write_text('<html><head></head><body>protocol fixture</body></html>')
        self.policy={'cases':[{'id':'one','screen':'home','kind':'home','stable':False,
          'recipe':'open fixture','environment':'controlled CDP fixture','width':1,'height':1,'dpr':1,
          'witness':[{'path':'Canvas/Target','frame':'icon'}]}]}
        self.plan=self.project/'docs/art/capture-plan.json';self.plan.write_text(json.dumps(self.policy))

    def cli(self, module, command):
        return subprocess.run(['node',str(module),command,str(self.project),str(self.build),str(self.out)],capture_output=True,text=True)

    def old_module(self):
        folder=self.root/'old-scripts';folder.mkdir()
        module=folder/'art_capture_round.mjs';module.write_bytes(previous_collector())
        shutil.copyfile(HERE/'ui_dump.js',folder/'ui_dump.js');return module

    def capture(self, module):
        started=self.cli(module,'start');self.assertEqual(started.returncode,0,started.stderr)
        script=r'''
        import fs from 'node:fs';import {openCapture} from MODULE;
        const session=await openCapture({project:PROJECT,build:BUILD,out:OUT});let live;
        const page={async goto(url){const html=await(await fetch(url)).text();
          live={origin:new URL(url).origin,token:html.match(/art-capture-session" content="([^"]+)/)[1],
                t:1,w:1,h:1,dpr:1,sw:false,ua:'controlled-protocol-fixture',lang:'en',tz:'UTC'};},
          async cdp(method,args){
            if(method.startsWith('Network.'))return {};
            if(method==='Page.captureScreenshot')return {data:'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jvXkAAAAASUVORK5CYII='};
            if(method==='Runtime.evaluate'){
              let value;if(args.expression.includes('art-capture-session'))value=live;
              else if(args.expression.includes('indexedDB.databases'))value={local:[],session:[],cookie:'',supported:true};
              else value={tool:'ui_dump',schema:1,nodes:[{id:'a',path:'Canvas/Target',active:true,opacity:1,
                screen:[0,0,1,1],comps:{sprite:{frame:'icon',frame_size:[1,1]}}}]};
              return {result:{value}};
            }throw Error(method);
          }};
        try{await session.navigate(page);console.log(await session.capture(page,'one'));}
        finally{await session.close();}
        '''
        for key,value in {'MODULE':module.as_uri(),'PROJECT':str(self.project),'BUILD':str(self.build),'OUT':str(self.out)}.items():script=script.replace(key,json.dumps(value))
        result=subprocess.run(['node','--input-type=module','-e',script],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        return self.out/'capture-ui-dump-one.json'

    def hashes(self):
        return {str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}

    def test_new_official_capture_is_loaded_by_real_page_reader(self):
        file=self.capture(MODULE);data=json.loads(file.read_text())
        self.assertEqual(data['producer'],'ego_page.dump_ui')
        self.assertEqual(len(richness.load([self.out])),1)
        result=art_round_check.run('verify',self.project,self.build,self.out)
        self.assertTrue(result['ready']);self.assertNotIn('error',result)

    def test_exact_default_source_delta_and_identity_pair(self):
        old=previous_collector();ui=(HERE/'ui_dump.js').read_bytes()
        self.assertEqual(hashlib.sha256(MODULE.read_bytes()).hexdigest(),COMPAT['after_script_sha256'])
        self.assertEqual(hashlib.sha256(ui).hexdigest(),COMPAT['ui_dump_sha256'])
        self.assertEqual(hashlib.sha256(old+ui).hexdigest(),COMPAT['before_collector_sha256'])

    def test_complete_old_round_is_verified_in_memory_without_rewriting(self):
        file=self.capture(self.old_module());self.assertNotIn('producer',json.loads(file.read_text()))
        before=self.hashes()
        self.assertEqual(richness.load([self.out]),[])
        loaded=richness.load([self.out],project=self.project)
        self.assertEqual(len(loaded),1);self.assertEqual(loaded[0]['producer'],'ego_page.dump_ui')
        self.assertEqual(self.hashes(),before)
        self.assertNotIn('producer',json.loads(file.read_text()))

    def test_old_png_export_source_and_matrix_changes_are_refused(self):
        file=self.capture(self.old_module())
        paths=[self.out/'one.png', self.build/'index.html', self.project/'assets/layout.json', self.plan]
        originals={p:p.read_bytes() for p in paths}
        for changed in paths:
            with self.subTest(changed=changed.name):
                for p,raw in originals.items():p.write_bytes(raw)
                if changed==self.plan:
                    policy=json.loads(originals[changed]);policy['cases'][0]['recipe']='different arrival';changed.write_text(json.dumps(policy))
                else:changed.write_bytes(originals[changed]+b' ')
                self.assertEqual(richness.load([self.out],project=self.project),[])
        for p,raw in originals.items():p.write_bytes(raw)
        altered=json.loads(file.read_text());altered['nodes'][0]['path']='Canvas/Forged';file.write_text(json.dumps(altered))
        self.assertEqual(richness.load([self.out],project=self.project),[])

    def test_incomplete_round_never_promoted_by_missing_metadata_repair(self):
        self.policy['cases'].append(dict(self.policy['cases'][0],id='missing',screen='settings'))
        self.plan.write_text(json.dumps(self.policy));self.capture(self.old_module())
        self.assertEqual(richness.load([self.out],project=self.project),[])

    def test_unknown_collector_or_dumper_edit_requires_new_round(self):
        self.capture(self.old_module())
        folder=self.root/'current-scripts';folder.mkdir()
        module=folder/'art_capture_round.mjs';shutil.copyfile(MODULE,module)
        shutil.copyfile(HERE/'ui_dump.js',folder/'ui_dump.js')
        shutil.copyfile(HERE/'art-capture-producer-compat.json',folder/'art-capture-producer-compat.json')
        before=module.read_bytes();ui=(folder/'ui_dump.js').read_bytes()
        for changed in (module,folder/'ui_dump.js'):
            module.write_bytes(before);(folder/'ui_dump.js').write_bytes(ui)
            changed.write_bytes(changed.read_bytes()+b'\n')
            result=self.cli(module,'verify')
            self.assertEqual(result.returncode,2);self.assertIn('collector changed',result.stderr)

if __name__=='__main__':unittest.main()
