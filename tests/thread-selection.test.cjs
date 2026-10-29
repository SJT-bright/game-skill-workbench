const {test}=require('node:test');const assert=require('node:assert/strict');
const {activity,identity,select}=require('../ui/thread-selection.js');
const make=(id,rest={})=>({id,threadId:id,name:'松果邮局',path:'/games/Pinecone',source:'codex',...rest});
test('Public current state wins; waiting is ongoing and ended turn never means game completed',()=>{
 assert.equal(activity(make('1',{metadataStatus:{type:'active',activeFlags:['waitingOnUserInput']},telemetry:{active:false,status:'idle'}})),'ongoing');
 assert.equal(activity(make('1',{metadataStatus:'idle',stage:'玩法制作',telemetry:{active:true}})),'ended');
 assert.equal(activity(make('1',{metadataStatus:'notLoaded',telemetry:{status:'unknown'}})),'unknown');
 assert.equal(activity(make('1',{metadataStatus:'systemError',telemetry:{active:true}})),'unknown');
 assert.equal(activity(make('1',{metadataStatus:'active'}),{stale:true}),'unknown');
});
test('A dedicated game groups conversations; shared cwd or identical titles never merge unrelated identities',()=>{
 const rows=[make('a'),make('b',{name:'松果邮局检查'}),make('c',{path:'/games/Other'}),make('d',{path:'/shared'}),make('e',{path:'/shared'})];
 const result=select(rows,{roots:['/shared']});assert.equal(result.groups.length,4);assert.deepEqual(result.groups[0].threads.map(t=>t.id),['a','b']);assert.equal(result.threadCount,5);
 assert.notEqual(identity(rows[3],['/shared']).key,identity(rows[4],['/shared']).key);
});
test('Windows paths group independent of drive/path case and remain separate across game folders',()=>{
 assert.equal(identity(make('a',{path:'C:\\Games\\Pinecone'})).key,identity(make('b',{path:'c:/games/pinecone/'})).key);
 assert.notEqual(identity(make('a',{path:'C:\\Games\\One'})).key,identity(make('b',{path:'C:\\Games\\Two'})).key);
});
test('Activity filters intersect stage and search; counts are scoped before activity selection and exact targets survive',()=>{
 const rows=[make('a',{stage:'玩法制作',metadataStatus:'active'}),make('b',{stage:'玩法制作',metadataStatus:'idle'}),make('c',{stage:'已完成',metadataStatus:'idle'})];
 const result=select(rows,{stage:'玩法制作',activityFilter:'ongoing',query:'pinecone'});
 assert.deepEqual(result.counts,{all:2,ongoing:1,ended:1,unknown:0});assert.equal(result.threadCount,1);assert.equal(result.groups[0].threads[0].threadId,'a');assert.equal(rows[1].stage,'玩法制作');
 const stale=select(rows,{stale:true});assert.equal(stale.counts.ongoing,0);assert.equal(stale.counts.unknown,3);assert.equal(stale.threadCount,3);
});
test('Three production phases map explicit substages without confusing completed or unknown games',()=>{
 const {phase,PHASES}=require('../ui/thread-selection.js');
 for(const [label,stages]of Object.entries(PHASES))for(const stage of stages){assert.equal(phase(stage),label);assert.equal(select([make(stage,{stage})],{stage:label}).threadCount,1);}
 assert.equal(phase('已完成'),'已完成');assert.equal(phase(null),'待识别');
 assert.equal(select([make('done',{stage:'已完成'}),make('unknown',{stage:null})],{stage:'测试阶段'}).threadCount,0);
 const rows=[make('a',{stage:'待试玩',metadataStatus:'active'}),make('b',{stage:'检查',metadataStatus:'idle'}),make('c',{stage:'玩法制作',metadataStatus:'active'})];
 assert.deepEqual(select(rows,{stage:'测试阶段',activityFilter:'ongoing'}).groups[0].threads.map(t=>t.id),['a']);
});
