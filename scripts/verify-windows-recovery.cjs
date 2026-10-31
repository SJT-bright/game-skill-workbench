// Windows release gate: published legacy -> repair -> current real updater -> future QA version.
const fs=require('node:fs/promises'),path=require('node:path'),{execFileSync}=require('node:child_process');
(async()=>{
 if(process.platform!=='win32')throw Error('Actual Windows runner required');
 const current=require('../package.json').version,parts=current.split('.').map(Number),next=[parts[0],parts[1],parts[2]+1].join('.');
 const source=path.resolve(`dist/${current}/GameDesk-Skill-${current}-win-x64`),base=path.resolve('.qa/future-version'),target=path.join(base,'application'),archive=path.resolve(`release/GameDesk-${next}-windows-x64.zip`);
 await fs.mkdir(base,{recursive:true});await fs.rm(target,{recursive:true,force:true});await fs.cp(source,target,{recursive:true});
 const file=path.join(target,'resources/app/package.json'),metadata=JSON.parse(await fs.readFile(file,'utf8'));if(metadata.version!==current)throw Error('Built baseline version mismatch');metadata.version=next;await fs.writeFile(file,JSON.stringify(metadata));
 // Assert every production main/updater byte is identical to the release candidate.
 for(const name of ['main.cjs','updater.cjs','windows-installer.cjs'])if(!(await fs.readFile(path.join(source,'resources/app/src',name))).equals(await fs.readFile(path.join(target,'resources/app/src',name))))throw Error('QA copy changed production '+name);
 const quote=v=>"'"+v.replaceAll("'","''")+"'";
 try{
  execFileSync('powershell.exe',['-NoProfile','-Command',`Compress-Archive -Path ${quote(path.join(target,'*'))} -DestinationPath ${quote(archive)} -Force`],{stdio:'inherit'});
  execFileSync(process.execPath,['scripts/verify-windows-upgrade.cjs','--recovered'],{stdio:'inherit',env:{...process.env,WINDOWS_UPGRADE_BASELINE:'0.2.14',WINDOWS_UPGRADE_CANDIDATE:next}});
 }finally{
  // Never allow the synthetic future version into release/*.zip publication.
  await fs.rm(archive,{force:true});await fs.rm(target,{recursive:true,force:true});
 }
})().catch(e=>{console.error(e.message);process.exitCode=1;});
