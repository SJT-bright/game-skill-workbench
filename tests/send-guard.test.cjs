const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/main.cjs'),'utf8');
const implementation=source.slice(source.indexOf('async function sendGame('),source.indexOf('\nconst handlers='));
test('same-thread concurrent sends are rejected before asynchronous preparation and release the lock on failure',async()=>{
 let finish,calls=0,fail=false;
 const sending=new Set(),game={id:'g',threadId:'11111111-1111-4111-8111-111111111111',name:'fixture',path:'/fixture'};
 const send=vm.runInNewContext(implementation+';sendGame',{config:{games:[game]},UUID:/^[a-f0-9-]{36}$/,busy:false,sending,sendWithReceipt:async({send})=>send(),installed:{s:{local:true}},getTask:async()=>{await new Promise(r=>finish=r);if(fail)throw Error('fixture failure');return {skill:{path:'/skill',name:'Skill',version:'v1',treeHash:'hash'}};},path,root:'/fixture',readJSON:async()=>({}),queueMessage:async()=>{calls++;return {status:'queued'}},atomicJSON:async()=>{},emit:async()=>{}});
 const first=send({gameId:'g',skillId:'s'});await assert.rejects(send({gameId:'g',skillId:'s'}),/正在发送/);finish();await first;assert.equal(calls,1);assert.equal(sending.size,0);
 fail=true;const second=send({gameId:'g',skillId:'s'});finish();await assert.rejects(second,/fixture failure/);assert.equal(sending.size,0);
});
