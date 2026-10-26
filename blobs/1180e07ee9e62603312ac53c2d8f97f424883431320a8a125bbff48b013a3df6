'use strict';
// Validate a project's CommonJS probe(root, ready) implementation in isolation.
// This tests the probe contract, not the final engine/SDK or phone rendering.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto');
const filename=process.argv[2];if(!filename)throw Error('Usage: node test_webp_decode_probe.cjs /absolute/project/probe.js');
const code=fs.readFileSync(filename,'utf8'),results=[];
for(const kind of ['supported','error','timeout','legacy','already','zero-size','throws']){
 let timer,done=0,img,events={},created=0;const caps={webp:kind==='already'},module={exports:{}};
 vm.runInNewContext(code,{module,setTimeout:f=>(timer=f,1),clearTimeout(){}});
 const root={cc:{sys:{capabilities:caps}},TTMinis:{game:{createImage(){created++;if(kind==='throws')throw Error('SDK image unavailable');img={width:kind==='zero-size'?0:2,height:2};if(kind!=='legacy'){img.addEventListener=(k,f)=>events[k]=f;img.removeEventListener=()=>{}}return img;}}}};
 module.exports(root,()=>done++);
 if(kind==='supported'||kind==='zero-size'){assert.match(img.src,/^data:image\/webp;base64,/);events.load();events.error();timer();}
 if(kind==='legacy'){img.onload();img.onerror();}
 if(kind==='error')events.error();if(kind==='timeout')timer();
 if(kind==='already')assert.equal(created,0);
 assert.equal(done,1,kind+' settles exactly once');assert.equal(caps.webp,['supported','legacy','already'].includes(kind),kind+' capability result');
 results.push({case:kind,passed:true});
}
console.log(JSON.stringify({tool:'test_webp_decode_probe',module_sha256:crypto.createHash('sha256').update(code).digest('hex'),passed:true,results,boundary:'isolated actual probe module; final Native engine/SDK/UI negative and positive controls still required'},null,2));
