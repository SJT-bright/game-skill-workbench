// Isolated native smoke only: exercise production IPC, ledger migration and sync.
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const {HubStore,startHub,digest}=require('./core.cjs');
module.exports=async({win,handlers,root})=>{
 const source=path.join(root,'sync-fixture','cocos-game-to-english');await fs.mkdir(source,{recursive:true});await fs.writeFile(path.join(source,'SKILL.md'),'# Native updated English rules');
 const hub=new HubStore(path.join(root,'sync-fixture','hub')),published=await hub.publish(source,'cocos-game-to-english');const server=await startHub(hub);
 const call=(name,value)=>win.webContents.executeJavaScript(`window.dock.call(${JSON.stringify(name)},${JSON.stringify(value)})`);
 try{
  const id='s-'+digest('cocos-game-to-english').slice(0,20),ledgerPath=path.join(root,'subscriber','installed.json'),ledger=JSON.parse(await fs.readFile(ledgerPath,'utf8')),prior=ledger[id];assert.ok(prior);
  // Simulate the duplicate ID left by a historical installation without deleting originals.
  ledger['legacy-english']={...prior,skillId:'legacy-english'};delete ledger[id];await fs.writeFile(ledgerPath,JSON.stringify(ledger));
  const live=(await handlers.state()).installed;delete live[id];live['legacy-english']=ledger['legacy-english'];
  await fs.writeFile(path.join(prior.path,'personal-native.md'),'preserve imported note');
  // Changing subscription sources intentionally clears that source's old pins.
  // Establish this fixture source first, then lock its legacy component.
  await call('settings',{url:`http://127.0.0.1:${server.port}`,token:server.token,autoDownload:false});
  await fs.writeFile(path.join(root,'pins.json'),JSON.stringify({'legacy-english':true}));
  await call('settings',{url:`http://127.0.0.1:${server.port}`,token:server.token,autoDownload:true});
  assert.ok((await handlers.state()).installed['legacy-english'],'automatic sync must respect legacy history pin');
  const release=await hub.release(published.release.id),file=release.files.find(f=>f.path==='SKILL.md'),blob=path.join(hub.root,'blobs',file.hash),good=await fs.readFile(blob);await fs.writeFile(blob,'corrupted transfer');
  await assert.rejects(call('install',{id:release.id}),/哈希/);assert.deepEqual(JSON.parse(await fs.readFile(ledgerPath,'utf8')),ledger);
  await fs.writeFile(blob,good);await call('install',{id:release.id});let state=await handlers.state();assert.ok(state.installed[id]);assert.equal(state.installed['legacy-english'],undefined);const installed=state.installed[id];
  assert.equal(await fs.readFile(path.join(installed.path,'personal-native.md'),'utf8'),'preserve imported note');assert.equal(await fs.readFile(path.join(installed.path,'SKILL.md'),'utf8'),'# Native updated English rules');
  await fs.writeFile(path.join(source,'SKILL.md'),'# Native automatic follow-up');const next=await hub.publish(source,'cocos-game-to-english');await call('settings',{url:`http://127.0.0.1:${server.port}`,token:server.token,autoDownload:true});state=await handlers.state();assert.equal(state.installed[id].id,next.release.id);assert.equal(await fs.readFile(path.join(state.installed[id].path,'SKILL.md'),'utf8'),'# Native automatic follow-up');
  return {nativeSkillConflictRecovery:true,nativeSkillLegacyHistoryPinPreserved:true,nativeSkillFailedTransferPreserved:true,nativeSkillAutomaticFollowUp:true,nativeSkillLocalFilesPreserved:true};
 }finally{await call('disconnect');await server.close();}
};
