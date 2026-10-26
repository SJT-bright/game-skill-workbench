'use strict';
// Settle the real Cocos downloader/parser callback, so its in-flight cache is released.
module.exports=function install(root,engine,nativeBeforeAdapter){
 if(root.__mosslightImageGuard)return root.__mosslightImageGuard;
 var am=engine&&engine.assetManager;if(!am||!am.downloader)return null;
 var jobs=[],hidden=false,last=Date.now(),serial=0,mark=0,types=['.png','.jpg','.jpeg','.bmp','.gif','.ico','.tiff','.image','.webp'];
 var api={progress:function(){return mark;},setBackground:function(v){hidden=!!v;last=Date.now();jobs.forEach(function(r){r.last=last;});},update:function(){var now=Date.now(),dt=Math.max(0,now-last);last=now;if(hidden){jobs.forEach(function(r){r.last=now;});return;}jobs.slice().forEach(function(r){r.idle+=Math.max(0,now-r.last);r.last=now;if(r.idle>=10000)r.finish(new Error('Image made no progress'));});}};
 function wrap(raw){return function(url,options,done){if(typeof options==='function'){done=options;options={};}options=options||{};var r={id:++serial,idle:0,last:Date.now(),bytes:-1,settled:false,handle:null};jobs.push(r);mark++;r.finish=function(err,value){if(r.settled)return;r.settled=true;var i=jobs.indexOf(r);if(i>=0)jobs.splice(i,1);if(err&&r.handle)try{if(typeof r.handle.abort==='function')r.handle.abort();else if('src'in r.handle)r.handle.src='';}catch(ignore){}done(err||null,value);};var opts={};Object.keys(options).forEach(function(k){opts[k]=options[k];});var progress=opts.onFileProgress;opts.onFileProgress=function(a,b){var n=typeof a==='number'?a:a&&a.totalBytesWritten;if(typeof n==='number'&&isFinite(n)&&n>r.bytes){r.bytes=n;r.idle=0;r.last=Date.now();mark++;}if(progress)progress.apply(this,arguments);};try{r.handle=raw.call(this,url,opts,r.finish);}catch(e){r.finish(e);}return r.handle;};}
 function hook(registry){if(!registry||!registry.register)return;var register=registry.register;registry.register=function(type,handler){if(typeof type==='string')return register.call(this,type,types.indexOf(type)>=0?wrap(handler):handler);var map={};Object.keys(type).forEach(function(k){map[k]=types.indexOf(k)>=0?wrap(type[k]):type[k];});return register.call(this,map);};}
 // Do not change Native filesystem/cache handling: wrap the handlers adaptEngine actually registers.
 if(nativeBeforeAdapter){hook(am.downloader);hook(am.parser);}
 else{
  // Web: an abortable XHR supplies real byte progress; decode with a fresh Image each attempt.
  var raw=am.downloader.downloadFile;
  function webImage(url,opts,done){var image=null,objectURL=null,xhr=null,aborted=false;function clearURL(){if(objectURL){URL.revokeObjectURL(objectURL);objectURL=null;}}var handle={abort:function(){aborted=true;if(xhr)xhr.abort();if(image){image.onload=image.onerror=null;image.src='';}clearURL();}};var options={};Object.keys(opts).forEach(function(k){options[k]=opts[k];});options.responseType='blob';xhr=raw(url,options,opts.onFileProgress,function(err,blob){if(aborted)return;if(err)return done(err);try{objectURL=URL.createObjectURL(blob);image=new Image();image.onload=function(){image.onload=image.onerror=null;clearURL();done(null,image);};image.onerror=function(){image.onload=image.onerror=null;clearURL();done(new Error('Image decode failed'));};image.src=objectURL;}catch(e){clearURL();done(e);}});return handle;}
  var map={};types.forEach(function(t){map[t]=wrap(webImage);});am.downloader.register(map);
 }
 // Cocos' own automatic retries must not retain the abandoned attempt behind the visible Retry.
 var download=am.downloader.download;am.downloader.download=function(id,url,type,options,done){if(types.indexOf(type)>=0){var opts={};Object.keys(options||{}).forEach(function(k){opts[k]=options[k];});opts.maxRetryCount=0;options=opts;}return download.call(this,id,url,type,options,done);};
 root.__mosslightImageGuard=api;return api;
};
