const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path');
const {run}=require('../scripts/publish-background.cjs'),{ALLOWED}=require('../scripts/sync-skills.cjs');
test('headless publisher skips unchanged sources, retries failure and never includes local-only Skill',async t=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'dock-publisher-'));t.after(()=>fs.rm(root,{recursive:true,force:true}));let fail=true,calls=[];
 const options={dataRoot:root,sourceRoot:'/fixture/skills',collectFn:async source=>({treeHash:path.basename(source)+'-hash'}),publishFn:async ({source})=>{const name=path.basename(source);calls.push(name);if(fail&&name===ALLOWED[0])throw Error('fixture network');return {changed:true,commit:'fixture'};}};
 let report=await run(options);assert.equal(report.status,'partial');assert.equal(calls.length,ALLOWED.length);assert.ok(!calls.includes('cocos-game-finished-product-check'));
 fail=false;calls=[];report=await run(options);assert.equal(report.status,'complete');assert.deepEqual(calls,[ALLOWED[0]]);
 calls=[];await run(options);assert.deepEqual(calls,[]);
 await fs.writeFile(path.join(root,'running.json'),JSON.stringify({pid:process.pid}));assert.equal((await run(options)).status,'busy');assert.deepEqual(calls,[]);
});
