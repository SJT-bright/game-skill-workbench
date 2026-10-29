const {test}=require('node:test');const assert=require('node:assert/strict');const {EventEmitter}=require('node:events');const {PassThrough}=require('node:stream');const fs=require('node:fs/promises');const path=require('node:path');const os=require('node:os');
const {inferStage,isGameThread,queueMessage,STAGES}=require('../src/codex.cjs');const {dockBounds,EXPANDED,COLLAPSED}=require('../src/docking.cjs');const {collect}=require('../src/core.cjs');
const tid='11111111-1111-4111-8111-111111111111';
test('Stage evidence follows recent explicit statements, not generic completion or negated future phases',()=>{
 assert.equal(inferStage([{role:'user',text:'开始玩法制作。'}]).stage,'玩法制作');
 assert.equal(inferStage([{role:'assistant',text:'玩法已完成，美工制作未开始。'}]).stage,'玩法结束');
 assert.equal(inferStage([{role:'user',text:'进入美工制作。'}]).stage,'美工制作');
 assert.equal(inferStage([{role:'assistant',text:'美工已经完成。待试玩。'}]).stage,'待试玩');
 assert.equal(inferStage([{role:'user',text:'进入检查阶段。'}]).stage,'检查');
 assert.equal(inferStage([{role:'assistant',text:'本游戏已全部完成。'}]).stage,'已完成');
 assert.equal(inferStage([{role:'assistant',text:'本次修改完成，真机未通过。'}]).stage,null);
 assert.equal(inferStage([{role:'assistant',text:'玩法已完成。'},{role:'user',text:'开始美工制作，之后进入检查。'}]).stage,'美工制作');
 assert.equal(inferStage([{role:'assistant',text:'```\n项目已全部完成\n```\n尚未进入美工制作。'}]).stage,null);
});
test('Only scoped game conversations are discovered; shared workspaces do not merge thread identities',()=>{
 assert.ok(isGameThread({id:tid,name:'松果邮局',cwd:'/work/games/Pinecone'}));
 assert.equal(isGameThread({id:tid,name:'游戏工作台软件开发',cwd:'/work/games/Pinecone'}),false);
 assert.equal(isGameThread({id:tid,name:'审查启动包工坊流程',cwd:'/work/游戏出海项目制作'}),false);
 assert.equal(isGameThread({id:tid,name:'普通写作',cwd:'/work/notes'}),false);
 assert.ok(isGameThread({id:tid,name:'松果邮局',cwd:'/work/game-root'},['/work/game-root']));
 assert.equal(isGameThread({id:tid,name:'松果邮局',cwd:'/work/game-root-other'},['/work/game-root']),false);
});
test('Dock handle clamps to current display and opens against the same edge; wide-screen changes stay visible',()=>{
 const area={x:1920,y:20,width:1440,height:880};const input={x:3300,y:850,width:32,height:88};
 const tab=dockBounds(input,area,{collapsed:true});assert.equal(tab.edge,'right');assert.equal(tab.bounds.x,3328);assert.equal(tab.bounds.y,812);
 const open=dockBounds(tab.bounds,area,{edge:tab.edge,force:true});assert.equal(open.bounds.x,area.x+area.width-EXPANDED.width);assert.equal(open.bounds.height,EXPANDED.height);assert.equal(open.bounds.y,area.y+area.height-EXPANDED.height);
 const left=dockBounds({x:1924,y:30,width:420,height:650},area);assert.equal(left.edge,'left');assert.equal(left.bounds.x,1920);
 const noSnap=dockBounds({x:2200,y:60,width:420,height:650},area);assert.equal(noSnap.edge,null);assert.equal(noSnap.bounds.x,2200);
 const small=dockBounds({x:-400,y:-50,width:420,height:650},{x:0,y:0,width:360,height:580},{force:true,edge:'right'});assert.deepEqual(small.bounds,{x:0,y:0,width:360,height:580});
});
function fakeSpawn(capture,{stall=false,code=0}={}){return(binary,args)=>{capture.push({binary,args});const child=new EventEmitter();child.stdout=new PassThrough();child.stderr=new PassThrough();child.exitCode=null;child.kill=signal=>{queueMicrotask(()=>{child.exitCode=143;child.emit('exit',143);});return true;};if(!stall)queueMicrotask(()=>{child.stdout.write('Queued for exact thread');child.exitCode=code;child.emit('exit',code);});return child;};}
test('Skill push addresses the exact selected thread using argument arrays and reports only queue acknowledgement',async()=>{
 const captures=[];const message='Skill 路径：C:\\My Games\\Skills\\Art\n使用新版 Skill 继续后续制作。';const result=await queueMessage(tid,message,{binary:'test-codex',spawnFn:fakeSpawn(captures)});assert.equal(result.status,'queued');assert.deepEqual(captures,[{binary:'test-codex',args:['queue','--thread',tid,'--message',message]}]);
 await assert.rejects(queueMessage('../other',message,{binary:'test-codex',spawnFn:fakeSpawn(captures)}));assert.equal(captures.length,1);
});
test('Timed out send stays uncertain and is not silently retried',async()=>{const captures=[];const result=await queueMessage(tid,'Use newest Skill',{binary:'test-codex',timeout:10,spawnFn:fakeSpawn(captures,{stall:true})});assert.equal(result.status,'uncertain');assert.equal(captures.length,1);});
test('Local-only Skill can be used on this computer but remains blocked from publishing',async t=>{const root=await fs.mkdtemp(path.join(os.tmpdir(),'dock-local-skill-'));t.after(()=>fs.rm(root,{recursive:true,force:true}));const dir=path.join(root,'cocos-game-finished-product-check');await fs.mkdir(dir);await fs.writeFile(path.join(dir,'SKILL.md'),'# Local only');await assert.rejects(collect(dir),/本机专用/);assert.equal((await collect(dir,{localUse:true})).files.length,1);});
test('A missing executable is a known non-delivery and remains recoverable',async()=>{await assert.rejects(queueMessage(tid,'fixture',{binary:path.join(os.tmpdir(),'gamedesk-missing-cli-'+Date.now())}),e=>e.deliveryStarted===false&&e.code==='ENOENT');});
