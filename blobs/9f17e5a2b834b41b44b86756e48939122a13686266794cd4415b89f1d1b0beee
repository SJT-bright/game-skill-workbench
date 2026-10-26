'use strict';
// Installed before adaptEngine captures fsUtils.loadSubpackage.
module.exports=function install(root){
 var fs=root.fsUtils;if(!fs||!fs.loadSubpackage)throw Error('Native filesystem adapter missing');
 var raw=fs.loadSubpackage,jobs={},progress={},hidden=false,last=Date.now(),serial=0;
 function sdk(){var candidates=[root.TTMinis&&root.TTMinis.game,typeof TTMinis!=='undefined'&&TTMinis.game,root.tt,typeof tt!=='undefined'&&tt,root.wx];for(var i=0;i<candidates.length;i++)if(candidates[i]&&typeof candidates[i].loadSubpackage==='function')return candidates[i];return null;}
 function end(r,error){if(jobs[r.name]!==r)return;delete jobs[r.name];r.done(error||null);}
 var api={progress:progress,setBackground:function(v){hidden=!!v;last=Date.now();Object.keys(jobs).forEach(function(n){jobs[n].last=last;});},cancel:function(names){names.forEach(function(n){var r=jobs[n];if(r)end(r,new Error('Subpackage attempt replaced'));});},update:function(){var now=Date.now(),dt=Math.max(0,now-last);last=now;if(hidden){Object.keys(jobs).forEach(function(n){jobs[n].last=now;});return;}Object.keys(jobs).forEach(function(n){var r=jobs[n];r.idle+=Math.max(0,now-r.last);r.last=now;if(r.idle>=10000)end(r,new Error('Subpackage made no progress: '+n));});}};
 fs.loadSubpackage=function(name,onProgress,done){if(jobs[name])end(jobs[name],new Error('Subpackage attempt replaced'));var r={name:name,id:++serial,done:done||function(){},idle:0,last:Date.now(),bytes:-1};jobs[name]=r;function moved(value){if(jobs[name]!==r)return;var mark=value&&(typeof value.totalBytesWritten==='number'?value.totalBytesWritten:value.progress);if(typeof mark==='number'&&mark>r.bytes){r.bytes=mark;r.idle=0;r.last=Date.now();progress[name]=(progress[name]||0)+1;}if(onProgress)try{onProgress(value);}catch(ignore){}}
  try{var platform=sdk();if(!platform){return raw(name,moved,function(e){end(r,e);});}var result=platform.loadSubpackage({name:name,success:function(){end(r);},fail:function(){end(r,new Error('Could not load subpackage '+name));}});if(result&&typeof result.onProgressUpdate==='function')result.onProgressUpdate(moved);if(result&&typeof result.then==='function')result.then(function(){end(r);},function(){end(r,new Error('Could not load subpackage '+name));});return result;}catch(e){end(r,e);}
 };
 root.__mosslightLoadGuard=api;return api;
};
