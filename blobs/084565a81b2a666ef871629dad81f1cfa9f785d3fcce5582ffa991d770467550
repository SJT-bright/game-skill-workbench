const fs=require('fs'),path=require('path'),vm=require('vm'),crypto=require('crypto');const payload=process.argv[2]==='--stdin'?JSON.parse(fs.readFileSync(0,'utf8')):null,root=payload?'packaged-bytes':path.resolve(process.argv[2]),out=payload?null:process.argv[3],rows=[];const read=rel=>payload?payload.files[rel]:fs.readFileSync(path.join(root,rel),'utf8');
for(const mode of ['diagnostic_missing','diagnostic_parse_error','normal']){
 const logs=[],prompts=[],api={showModal(o){prompts.push(o)},createCanvas(){return{}},getSystemInfoSync(){return{SDKVersion:'0.35.0'}}},host={tt:api},c=vm.createContext({GameGlobal:host,tt:api,WebAssembly,console:{log(...a){logs.push(a)},error(...a){logs.push(a)}},setTimeout(){},clearTimeout(){}}),cache={};let calls=0,thrown=null,ackBeforeDependency=false,entryBeforeDependency=null,injectedError=null,injectedException=null,escapedOriginal=false;
 const req=name=>{
  if(name==='./native-diagnostics.js'){const trace=c.__bambooBootstrap;ackBeforeDependency=trace?.entry_executed===true;entryBeforeDependency={entry_executed:trace?.entry_executed,build_tag:trace?.build_tag,phase:trace?.phase}}
  if(name==='./native-diagnostics.js'&&mode!=='normal'){const error=mode==='diagnostic_missing'?Object.assign(new Error('Cannot find module native-diagnostics.js'),{code:'MODULE_NOT_FOUND'}):new SyntaxError('Unexpected token in diagnostic dependency');injectedError={name:error.name,message:error.message,stack:error.stack};injectedException=error;throw error}
  if(name==='./cocos-entry.js'){calls++;return{}}
  if(name==='./native-media-map.js')return{url(){},ext(){},ensure(){},ensurePackage(){}};
  const rel=name.replace(/^\.\//,'');if(cache[rel])return cache[rel].exports;const module={exports:{}};cache[rel]=module;
  vm.runInContext('(function(require,module,exports){'+read(rel)+'\n})',c,{filename:rel})(req,module,module.exports);return module.exports;
 };c.require=req;
 try{vm.runInContext(read('game.js'),c,{filename:'game.js'})}catch(e){escapedOriginal=e===injectedException;thrown={name:e.name,message:e.message,stack:e.stack}}
 const trace=c.__bambooBootstrap,expected=mode==='normal'?null:injectedError;
 const observed={entryAck:trace?.entry_executed===true,ackBeforeDependency,entryBeforeDependency,injectedError,firstError:trace?.first_exception||null,originalError:thrown,dispatch:calls,promptCount:prompts.length,logCount:logs.length};
 const nonempty=value=>typeof value==='string'&&value.length>0;
 const sameError=record=>!!record&&!!expected&&record.name===expected.name&&record.message===expected.message&&record.stack===expected.stack;
 const passed=mode==='normal'?calls===1&&!thrown:observed.entryAck&&ackBeforeDependency&&entryBeforeDependency?.entry_executed===true&&nonempty(entryBeforeDependency.build_tag)&&nonempty(entryBeforeDependency.phase)&&trace.build_tag===entryBeforeDependency.build_tag&&sameError(trace.first_exception)&&escapedOriginal&&thrown.name===expected.name&&thrown.message===expected.message&&String(thrown.stack).endsWith(expected.stack)&&trace.first_exception.phase===entryBeforeDependency.phase&&calls===0;
 rows.push({mode,passed,observed});
}
const report={native:root,entry_sha256:crypto.createHash('sha256').update(read('game.js')).digest('hex'),scope:'Actual game.js and production imports; SDK/module-boundary fault injection, not renderer/device acceptance',passed:rows.every(x=>x.passed),rows};if(out)fs.writeFileSync(out,JSON.stringify(report,null,2));console.log(JSON.stringify(report));process.exitCode=report.passed?0:1;
