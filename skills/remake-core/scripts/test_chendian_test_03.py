"""Preview input ownership and adapter-overwrite controls; no browser launch."""
import json, shutil, subprocess, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BRIDGE=ROOT/'assets/preview-touch-bridge.js'
HARNESS=r"""
const fs=require('node:fs'),vm=require('node:vm');
const mode=process.argv[1],source=fs.readFileSync(process.argv[2],'utf8');
class N {
 constructor(tag,parent){this.tagName=tag;this.parentNode=parent;this.l={};}
 addEventListener(t,f,o){(this.l[t]??=[]).push({f,c:o===true||!!o?.capture})}
 dispatchEvent(e){e.target=this;e.stop=false;e.stopImmediatePropagation=()=>e.stop=true;e.preventDefault=()=>e.defaultPrevented=true;const chain=[];for(let n=this;n;n=n.parentNode)chain.push(n);for(const n of [...chain].reverse()){for(const x of n.l[e.type]||[])if(x.c&&!e.stop)x.f(e)}for(const n of chain){for(const x of n.l[e.type]||[])if(!x.c&&!e.stop)x.f(e)}return !e.defaultPrevented}
}
class T{constructor(init){Object.assign(this,init)}}
class TE{constructor(type,init){this.type=type;Object.assign(this,init)}}
const w=new N('WINDOW'),d=new N('DOCUMENT',w),canvas=new N('CANVAS',d),other=new N('BUTTON',d);canvas.id='GameCanvas';
w.document=d;w.EventTarget=N;w.Touch=T;w.TouchEvent=TE;d.documentElement={};d.createEvent=()=>({initEvent(type,bubbles,cancelable){Object.assign(this,{type,bubbles,cancelable})}});
const got={touch:[],mouse:[],overlay:0,stub:0,host:[],touchCapable:false};
const send=(target,type,x=30,y=40)=>N.prototype.dispatchEvent.call(target,{type,bubbles:true,cancelable:true,button:0,clientX:x,clientY:y});
for(const type of ['touchstart','touchmove','touchend','touchcancel'])canvas.addEventListener(type,e=>got.touch.push({type,x:e.changedTouches[0].clientX,y:e.changedTouches[0].clientY,id:e.changedTouches[0].identifier,n:e.touches.length}));
other.addEventListener('mousedown',()=>got.overlay++);
vm.runInNewContext(source,{window:w});
if(mode.includes('host')){
 let down=false;w.__hostState=()=>({mouse:!mode.includes('disabled')});
 if(!mode.includes('disabled')){canvas.addEventListener('mousedown',()=>{down=true;got.host.push('start')});w.addEventListener('mousemove',()=>{if(down)got.host.push('move')});w.addEventListener('mouseup',()=>{if(down){down=false;got.host.push('end')}});w.addEventListener('blur',()=>{if(down){down=false;got.host.push('cancel')}})}
}
if(mode.includes('overwrite')){canvas.dispatchEvent=()=>got.stub++;w.TouchEvent=function(){};w.Touch=function(){};d.createEvent=()=>{throw Error('adapter replaced createEvent')}}
if(mode==='touch'){const p=new T({identifier:8,target:canvas,clientX:60,clientY:70});send(other,'mousedown');N.prototype.dispatchEvent.call(canvas,new TE('touchstart',{changedTouches:[p],touches:[p]}));N.prototype.dispatchEvent.call(canvas,new TE('touchend',{changedTouches:[p],touches:[]}));}
else{send(canvas,'mousedown');send(canvas,'mousemove',80,90);send(canvas,'mouseup',80,90);send(other,'mousedown');if(mode.includes('blur')){send(canvas,'mousedown',10,20);send(w,'blur',10,20)}}
got.touchCapable='ontouchstart'in d.documentElement;console.log(JSON.stringify(got));
"""
@unittest.skipUnless(shutil.which('node'),'node required')
class InputControls(unittest.TestCase):
 def run_mode(self,mode,path=BRIDGE):
  r=subprocess.run(['node','-e',HARNESS,mode,str(path)],text=True,capture_output=True,check=True);return json.loads(r.stdout)
 def test_plain_web_and_adapter_overwrite(self):
  for mode in ['web','overwrite','host-disabled-overwrite']:
   with self.subTest(mode=mode):
    d=self.run_mode(mode);self.assertEqual([r['type'] for r in d['touch']],['touchstart','touchmove','touchend']);self.assertEqual([(r['x'],r['y'])for r in d['touch']],[(30,40),(80,90),(80,90)]);self.assertEqual(len(set(r['id']for r in d['touch'])),1);self.assertEqual(d['touch'][-1]['n'],0);self.assertEqual(d['overlay'],1);self.assertEqual(d['stub'],0)
 def test_existing_host_owns_one_drag(self):
  d=self.run_mode('host-overwrite');self.assertEqual(d['host'],['start','move','end']);self.assertEqual(d['touch'],[]);self.assertEqual(d['stub'],0);self.assertEqual(d['overlay'],1)
 def test_real_touch_path_untouched(self):
  d=self.run_mode('touch');self.assertEqual([r['type']for r in d['touch']],['touchstart','touchend']);self.assertEqual(d['touch'][0]['id'],8);self.assertEqual(d['overlay'],1)
 def test_blur_cancels_without_stuck_press(self):
  for mode in ['blur-overwrite','host-blur-overwrite']:
   d=self.run_mode(mode);self.assertEqual(d['host'][-1] if d['host'] else d['touch'][-1]['type'],'cancel' if d['host'] else 'touchcancel')
 def test_controlled_legacy_route_is_detected(self):
  # Recreate the old decision and late API lookup while preserving the same event fixture.
  import tempfile
  source=BRIDGE.read_text().replace(' || hostOwnsMouse(e.target)','').replace('if (nativeDispatch) nativeDispatch.call(target, event);','if (false) nativeDispatch.call(target, event);')
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/'legacy.js';p.write_text(source);r=self.run_mode('host-overwrite',p)
  self.assertEqual(r['host'],[]);self.assertEqual(r['touch'],[]);self.assertGreater(r['stub'],0)
if __name__=='__main__':unittest.main()
