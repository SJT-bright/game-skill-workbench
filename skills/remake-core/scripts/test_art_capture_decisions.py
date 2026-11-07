"""Read-only round decisions and explicit live-witness readiness, without a browser."""
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


class CaptureDecisionTests(unittest.TestCase):
    def fixture(self, root):
        project, build, scripts = root/'project', root/'web', root/'scripts'
        for folder in (project/'assets', project/'docs/art', build, scripts):
            folder.mkdir(parents=True)
        module = scripts/'art_capture_round.mjs'
        shutil.copyfile(HERE/'art_capture_round.mjs', module)
        (scripts/'ui_dump.js').write_text('() => ({nodes:[]})')
        (project/'assets/layout.json').write_text('{"slot":40}')
        (build/'index.html').write_text('<html><head></head><body>fixture</body></html>')
        policy = {'cases': [{'id':'one', 'screen':'home', 'kind':'home', 'stable':False,
                  'recipe':'open fixture', 'environment':'test', 'width':1, 'height':1,
                  'dpr':1, 'witness':[{'path':'Canvas/Target', 'frame':'icon'}]}]}
        (project/'docs/art/capture-plan.json').write_text(json.dumps(policy))
        return project, build, module, policy

    def cli(self, module, command, project, build):
        proc = subprocess.run(['node', str(module), command, str(project), str(build)],
                              capture_output=True, text=True)
        return proc, json.loads(proc.stdout)

    def tree(self, root):
        return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob('*') if p.is_file()}

    def test_status_all_change_combinations_are_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, build, module, policy = self.fixture(root)
            proc, started = self.cli(module, 'start', project, build)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            originals = {p:p.read_bytes() for p in (project/'assets/layout.json', build/'index.html',
                         project/'docs/art/capture-plan.json', module.with_name('ui_dump.js'))}
            _, baseline = self.cli(module, 'status', project, build)
            for source, exported, matrix, collector in itertools.product((False, True), repeat=4):
                with self.subTest(source=source, exported=exported, matrix=matrix, collector=collector):
                    for file, raw in originals.items():
                        file.write_bytes(raw)
                    for changed, file in zip((source, exported, matrix, collector), originals):
                        if changed:
                            if file.name == 'capture-plan.json':
                                altered = json.loads(originals[file]); altered['cases'][0]['recipe'] += '; next'
                                file.write_text(json.dumps(altered))
                            else:
                                file.write_bytes(originals[file]+b'\n ')
                    before = self.tree(root)
                    proc, value = self.cli(module, 'status', project, build)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertEqual(self.tree(root), before)
                    self.assertEqual(value['changes'], {'source':source,'export':exported,
                                                       'matrix':matrix,'collector':collector})
                    expected = ('rebuild_web' if source and not exported else
                                'verify_export_then_new_round' if exported else
                                'new_round' if matrix or collector else 'keep_round')
                    self.assertEqual(value['suggested_action'], expected)
                    self.assertEqual(value['current_round'], started['id'])
                    self.assertEqual(value['current_round_version'], started['version'])
                    for key, changed in [('source_hash',source),('export_hash',exported),
                                         ('matrix_hash',matrix),('collector_hash',collector)]:
                        self.assertEqual(value[key] != baseline[key], changed)
                    self.assertTrue(value['read_only'])
                    self.assertFalse({'passed','ready','reuse_allowed'} & value.keys())

    def test_status_unknown_does_not_create_round_or_trust_missing_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, build, module, _ = self.fixture(root)
            before = self.tree(root)
            proc, value = self.cli(module, 'status', project, build)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(value['suggested_action'], 'unknown')
            self.assertEqual(value['reason_code'], 'no_previous_round')
            self.assertIsNone(value['current_round'])
            self.assertTrue(all(v is None for v in value['changes'].values()))
            self.assertEqual(self.tree(root), before)
            self.assertFalse((project/'.tiktok-kit').exists())
            _, started = self.cli(module, 'start', project, build)
            (project/'.tiktok-kit/art-rounds/snapshots'/f"{started['version']}.json").unlink()
            before = self.tree(root)
            proc, value = self.cli(module, 'status', project, build)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(value['suggested_action'], 'unknown')
            self.assertEqual(value['reason_code'], 'previous_snapshot_missing')
            self.assertEqual(value['current_round'], started['id'])
            self.assertEqual(self.tree(root), before)

    def test_cli_preserves_error_exit_and_adds_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, build, module, policy = self.fixture(root)
            _, started = self.cli(module, 'start', project, build)
            snapshot = project/'.tiktok-kit/art-rounds/snapshots'/f"{started['version']}.json"
            snapshot.write_text('{}')
            proc, value = self.cli(module, 'status', project, build)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(value['error'], 'snapshot does not match')
            self.assertEqual(proc.stderr.strip(), value['error'])
            self.assertEqual(value['reason_code'], 'capture_command_failed')
            policy['cases'][0]['witness'][0]['count'] = 0
            (project/'docs/art/capture-plan.json').write_text(json.dumps(policy))
            proc, value = self.cli(module, 'status', project, build)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(value['reason_code'], 'capture_not_ready')
            self.assertEqual(value['detail_code'], 'invalid_witness')
            self.assertEqual(value['next_action'], 'recapture_current_case')
            self.assertEqual(proc.stderr.strip(), value['error'])

    def test_explicit_witness_negative_and_normal_pairs(self):
        script = r'''
        import assert from 'node:assert/strict';
        import {validateWitnesses} from MODULE;
        const copy=x=>structuredClone(x), node={id:'a',path:'Canvas/Target',active:true,opacity:1,
          screen:[0,0,0.1,0.1],comps:{sprite:{frame:'icon',frame_size:[470,468]},
          label:{string:'400',font:'Digits',font_kind:'bitmap',text_metric:'fnt',text_w:31.5}}};
        const witness={path:node.path,text:'400',frame:'icon',font:'Digits',font_kind:'bitmap',require_font_metrics:true};
        let rejected=0;
        function check(nodes=[node],w=witness){return validateWitnesses(nodes,{id:'price',witness:[w]});}
        function reject(nodes,w=witness,detail){
          assert.throws(()=>check(nodes,w),e=>e.code==='capture_not_ready'&&
            e.reason_code==='capture_not_ready'&&e.next_action==='recapture_current_case'&&
            (!detail||e.detail_code===detail));rejected++;
        }
        assert.equal(check().length,1);
        reject([]);reject([{...node,active:false}]);reject([{...node,opacity:0}]);
        reject([{...node,opacity:-1}]);
        const second={...copy(node),id:'b'};
        reject([node,second],witness,'ambiguous_witness');
        assert.equal(check([node,second],{...witness,count:2})[0].length,2);
        reject([node],{...witness,count:2});
        for(const count of [0,-1,1.5,'2',null])reject([node],{...witness,count},'invalid_witness');
        for(const frame_size of [undefined,null,[],[470],[0,468],[470,0],[-1,468],[Infinity,468],['470',468]]){
          const bad=copy(node);bad.comps.sprite.frame_size=frame_size;reject([bad],witness,'frame_not_loaded');
        }
        for(const field of ['frame','font','font_kind']){
          const bad=copy(node);(field==='frame'?bad.comps.sprite:bad.comps.label)[field]='wrong';reject([bad]);
        }
        for(const fieldValue of [{font:null},{font:''},{text_metric:'canvas'},{text_w:0},{text_w:NaN},{text_w:Infinity},{text_w:'31.5'}]){
          const bad=copy(node);Object.assign(bad.comps.label,fieldValue);reject([bad]);
        }
        const noFont=copy(node);noFont.comps.label.font=null;
        reject([noFont],{path:node.path,font_kind:'bitmap',require_font_metrics:true},'font_metrics_not_ready');
        const ad=copy(node);ad.comps.label.string='WATCH AD';reject([ad]);
        assert.equal(check([ad],{path:node.path})[0].length,1); // No invented business text from a path.
        const bare=copy(node);delete bare.comps.sprite.frame_size;
        assert.equal(check([bare],{path:node.path,text:'400'})[0].length,1);
        const ttf=copy(node);ttf.comps.label={string:'400',font:'UI',font_kind:'ttf'};
        assert.equal(check([ttf],{path:node.path,font:'UI',font_kind:'ttf'})[0].length,1);
        reject([ttf],{path:node.path,font_kind:'ttf',require_font_metrics:true},'invalid_witness');
        reject([node],{path:node.path,require_font_metrics:true},'invalid_witness');
        const alternate=copy(second);alternate.comps.sprite.frame='other';
        reject([node,alternate],{path:node.path,frame:'icon'},'ambiguous_witness');
        assert.equal(check([node,alternate],{path:node.path,frame:'icon',count:1})[0].length,1);
        const changed=copy(node);changed.comps.label.text_w=32;
        assert.notDeepEqual(check(),check([changed]));
        console.log(JSON.stringify({rejected}));
        '''.replace('MODULE', json.dumps((HERE/'art_capture_round.mjs').as_uri()))
        proc = subprocess.run(['node','--input-type=module','-e',script], capture_output=True,text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertGreaterEqual(json.loads(proc.stdout)['rejected'], 30)

    def test_capture_checks_before_png_and_again_before_writing(self):
        # A protocol stand-in, not real Cocos/visual acceptance. The real browser is never opened.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, build, module, policy = self.fixture(root)
            policy['cases'][0]['witness'] = [{'path':'Canvas/Target','font_kind':'bitmap','require_font_metrics':True}]
            (project/'docs/art/capture-plan.json').write_text(json.dumps(policy))
            proc, _ = self.cli(module,'start',project,build)
            self.assertEqual(proc.returncode,0,proc.stderr)
            script = r'''
            import assert from 'node:assert/strict';
            import fs from 'node:fs';
            import {openCapture} from MODULE;
            const session=await openCapture({project:PROJECT,build:BUILD,out:OUT});
            let live,mode='missing',reads=0,shots=0;
            const page={async goto(url){const html=await (await fetch(url)).text();
              live={origin:new URL(url).origin,token:html.match(/art-capture-session" content="([^"]+)/)[1],
                t:1,w:1,h:1,dpr:1,sw:false,ua:'protocol-fixture',lang:'en',tz:'UTC'};},
              async cdp(method,args){
                if(method.startsWith('Network.'))return {};
                if(method==='Page.captureScreenshot'){shots++;return {data:'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jvXkAAAAASUVORK5CYII='};}
                if(method==='Runtime.evaluate'){
                  let value;
                  if(args.expression.includes('art-capture-session'))value=live;
                  else if(args.expression.includes('indexedDB.databases'))value={local:[],session:[],cookie:'',supported:true};
                  else{reads++;value={nodes:[{id:'a',path:'Canvas/Target',active:true,opacity:1,screen:[0,0,1,1],
                    comps:{label:{string:'400',font:mode==='missing'?null:'Digits',font_kind:'bitmap',text_metric:'fnt',
                    text_w:mode==='changed'&&reads%2===0?20:10}}}]};}
                  return {result:{value}};
                }throw Error(method);
              }};
            try{
              await session.navigate(page);
              await assert.rejects(session.capture(page,'one'),e=>e.reason_code==='capture_not_ready'&&e.detail_code==='font_metrics_not_ready');
              assert.equal(shots,0);assert.equal(fs.existsSync(OUT),false);
              mode='changed';reads=0;
              await assert.rejects(session.capture(page,'one'),e=>e.reason_code==='capture_not_ready'&&e.detail_code==='witness_changed');
              assert.equal(shots,1);assert.equal(fs.existsSync(OUT),false);
              mode='normal';reads=0;
              const saved=await session.capture(page,'one');assert.equal(fs.existsSync(saved),true);
              assert.equal(shots,2);console.log(JSON.stringify({rejected:2,saved:1}));
            }finally{await session.close();}
            '''
            for key,value in {'MODULE':module.as_uri(),'PROJECT':str(project),'BUILD':str(build),'OUT':str(root/'captures')}.items():
                script=script.replace(key,json.dumps(value))
            proc=subprocess.run(['node','--input-type=module','-e',script],capture_output=True,text=True,timeout=20)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(json.loads(proc.stdout),{'rejected':2,'saved':1})


if __name__ == '__main__':
    unittest.main()
