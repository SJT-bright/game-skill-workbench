'use strict';
// Validate a project's WebP decode probe module in isolation (the actual file, executed).
// This tests the probe contract, not the final engine/SDK or phone rendering.
//   Cocos 2.4: module.exports = function(root, ready)          -> sets root.cc.sys.capabilities.webp
//   Cocos 3.x: exports.check(cc, sdk, timeout, done) + exports.apply(cc, ok) -> cc.sys.hasFeature(WEBP)
// v7.5 (Mabel's Meadow problem 3, LunasJade problem 2): the probe must decode a real .webp file shipped in the
// package (relative path). A data: URI is refused, also as a fallback: a mini-game image loader is not required
// to accept one. With --package <dir> the probed file must exist in the main package (not in a subpackage).
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const argv=process.argv.slice(2),filename=argv.find(a=>!a.startsWith('--')&&argv[argv.indexOf(a)-1]!=='--package');
const pkgAt=argv.indexOf('--package'),pkg=pkgAt>=0?argv[pkgAt+1]:null;
if(!filename)throw Error('Usage: node test_webp_decode_probe.cjs /absolute/project/probe.js [--package /unpacked/package]');
const code=fs.readFileSync(filename,'utf8'),results=[],sources=new Set();
const CASES=['supported','error','timeout','legacy','already','zero-size','throws'];
function checkSrc(src,kind){
  assert.equal(typeof src,'string',kind+': probe never set img.src');
  assert.doesNotMatch(src,/^data:/i,kind+': probe src is a data: URI ('+src.slice(0,30)+'...); decode a real .webp file in the main package');
  assert.match(src,/^(?:\.\/)?[\w-][\w./-]*\.webp$/,kind+': probe src must be a relative .webp file in the package, got '+src);
  assert.doesNotMatch(src,/(^|\/)\.\.(\/|$)/,kind+': probe src leaves the package');
  sources.add(src.replace(/^\.\//,''));
}
function webpKind(buf){
  if(buf.length<16||buf.toString('latin1',0,4)!=='RIFF'||buf.toString('latin1',8,12)!=='WEBP')return null;
  for(let p=12;p+8<=buf.length;){const tag=buf.toString('latin1',p,p+4),size=buf.readUInt32LE(p+4);if(tag==='VP8L')return'lossless';if(tag==='VP8 ')return'lossy';p+=8+size+(size&1);}
  return null;
}

function run24(){
  for(const kind of CASES){
    let timer,done=0,img,events={},created=0;const caps={webp:kind==='already'},module={exports:{}};
    vm.runInNewContext(code,{module,exports:module.exports,setTimeout:f=>(timer=f,1),clearTimeout(){}});
    const root={cc:{sys:{capabilities:caps}},TTMinis:{game:{createImage(){created++;if(kind==='throws')throw Error('SDK image unavailable');img={width:kind==='zero-size'?0:2,height:2};if(kind!=='legacy'){img.addEventListener=(k,f)=>events[k]=f;img.removeEventListener=()=>{}}return img;}}}};
    module.exports(root,()=>done++);
    if(kind!=='already'&&kind!=='throws')checkSrc(img&&img.src,kind);
    if(kind==='supported'||kind==='zero-size'){events.load();events.error&&events.error();timer();}
    if(kind==='legacy'){img.onload();img.onerror&&img.onerror();}
    if(kind==='error')events.error();if(kind==='timeout')timer();
    if(kind==='already')assert.equal(created,0);
    assert.equal(done,1,kind+' settles exactly once');assert.equal(caps.webp,['supported','legacy','already'].includes(kind),kind+' capability result');
    results.push({case:kind,passed:true});
  }
}

// Cocos 3.x interface: the seven cases of LunasJade v0.10.1 tests/test_webp_probe.cjs, without its
// "file fails, data URI decodes" case (a data: fallback is refused here).
function run3x(){
  function makeCC(engineSays){const Feature={WEBP:'WEBP',IMAGE_BITMAP:'IMAGE_BITMAP'},map={WEBP:engineSays,IMAGE_BITMAP:false};return{sys:{Feature,hasFeature:f=>map[f],capabilities:{webp:engineSays}}};}
  function load(){const mod={exports:{}},timers=[];vm.runInNewContext(code,{module:mod,exports:mod.exports,setTimeout:f=>(timers.push(f),timers.length),clearTimeout(id){timers[id-1]=null;}});return{P:mod.exports,timers};}
  const MODE={supported:'load',error:'error',timeout:'timeout',legacy:'legacy-load',already:null,'zero-size':'zero',throws:'throw'};
  for(const kind of CASES){
    const{P,timers}=load(),cc=makeCC(kind==='already'),imgs=[],mode=MODE[kind];let calls=0,result=null;
    const sdk={createImage(){if(mode==='throw'){imgs.push(null);throw Error('SDK image unavailable');}
      const img={width:mode==='zero'?0:2,height:mode==='zero'?0:2,ev:{}};
      if(mode!=='legacy-load'){img.addEventListener=(k,f)=>{img.ev[k]=f;};img.removeEventListener=()=>{};}
      imgs.push(img);return img;}};
    const drive=()=>{for(const img of imgs){if(!img||img.driven||!img.src)continue;img.driven=true;checkSrc(img.src,kind);
      if(mode==='load'||mode==='zero'){img.ev.load();img.ev.error&&img.ev.error();img.onload&&img.onload();}
      if(mode==='legacy-load'){img.onload();img.onerror&&img.onerror();}
      if(mode==='error'){img.ev.error();img.ev.load&&img.ev.load();}
      if(mode==='timeout'){const t=timers[timers.length-1];t&&t();img.ev.load&&img.ev.load();}
      drive();return;}};
    P.check(cc,sdk,2500,(ok,reason)=>{calls++;result={ok,reason};});
    drive();
    timers.forEach(t=>t&&t()); // late timers must not fire a second result
    imgs.forEach(img=>img&&img.src&&checkSrc(img.src,kind));
    assert.equal(calls,1,kind+' settles exactly once');
    if(kind==='already')assert.equal(imgs.length,0,'no probe when the engine already decodes WebP');
    const expectOk=['supported','legacy','already'].includes(kind);
    assert.equal(result.ok,expectOk,kind+' result ('+result.reason+')');
    assert.equal(P.apply(cc,result.ok),expectOk,kind+' applied value');
    assert.equal(cc.sys.hasFeature('WEBP'),expectOk,kind+' Texture2D will see this');
    assert.equal(cc.sys.capabilities.webp,expectOk,kind+' capabilities.webp');
    assert.equal(cc.sys.hasFeature('IMAGE_BITMAP'),false,kind+' other features untouched');
    results.push({case:kind,result:result.ok,reason:result.reason,images:imgs.length,passed:true});
  }
  const{P}=load(),cc=makeCC(true); // engine true is never turned false
  assert.equal(P.apply(cc,false),true);P.apply(cc,true);P.apply(cc,false);assert.equal(cc.sys.hasFeature('WEBP'),true);
  results.push({case:'engine-true-kept',passed:true});
}

let iface,error=null;
try{
  const probe={exports:{}};vm.runInNewContext(code,{module:probe,exports:probe.exports,setTimeout(){},clearTimeout(){}});
  iface=typeof probe.exports==='function'?'cocos2.4':(probe.exports&&typeof probe.exports.check==='function'&&typeof probe.exports.apply==='function'?'cocos3.x':null);
  if(!iface)throw Error('unknown probe interface: expected module.exports=function(root,ready) or exports.check/exports.apply');
  if(iface==='cocos2.4')run24();else run3x();
  if(pkg){
    for(const src of sources){
      assert.ok(!/^subpackages\//.test(src),'probed '+src+' is in a subpackage (not downloaded when the probe runs)');
      const file=path.join(pkg,src);assert.ok(fs.existsSync(file),'probed '+src+' is not in the package');
      const k=webpKind(fs.readFileSync(file));assert.ok(k,'probed '+src+' is not a WebP file');
      results.push({case:'package-file',file:src,format:k,passed:true});
    }
  }
}catch(e){error=e.message;}
const report={tool:'test_webp_decode_probe',interface:iface||null,module_sha256:crypto.createHash('sha256').update(code).digest('hex'),
  passed:!error,error,probed_files:[...sources],results,boundary:'isolated actual probe module; final Native engine/SDK/UI negative and positive controls still required'};
console.log(JSON.stringify(report,null,2));
if(error)process.exitCode=1;
