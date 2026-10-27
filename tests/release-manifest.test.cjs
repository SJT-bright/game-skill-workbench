const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs/promises');const os=require('node:os');const path=require('node:path');const {execFileSync}=require('node:child_process');const {version}=require('../package.json');
test('Release manifest survives draft publication by using version tag URLs rather than temporary asset URLs',async()=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'dock-manifest-'));try{
  await fs.mkdir(path.join(root,'release'));const names=[`GameDesk-${version}-mac-arm64.zip`,`GameDesk-${version}-windows-x64.zip`];
  for(const name of names)await fs.writeFile(path.join(root,'release',name),'test verified package bytes');
  await fs.writeFile(path.join(root,'assets.json'),JSON.stringify({assets:names.map((name,i)=>({name,id:i+1,browser_download_url:`https://github.com/owner/repo/releases/download/untagged-temporary/${name}`}))}));
  execFileSync(process.execPath,[path.resolve(__dirname,'../scripts/release-manifest.cjs'),'assets.json'],{cwd:root,env:{...process.env,GITHUB_REPOSITORY:'owner/repo',GITHUB_SHA:'revision'}});
  const m=JSON.parse(await fs.readFile(path.join(root,'release/gamedesk-update.json'),'utf8'));for(const p of Object.values(m.packages)){assert.ok(p.url.includes(`/releases/download/v${version}/`));assert.ok(!p.url.includes('untagged-'));assert.equal(p.bytes,27);}
 }finally{await fs.rm(root,{recursive:true,force:true});}
});
