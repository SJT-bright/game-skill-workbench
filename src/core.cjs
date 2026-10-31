const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const http = require('node:http');
const os = require('node:os');
const HASH = /^[a-f0-9]{64}$/;
const ID = /^[a-zA-Z0-9_-]{1,100}$/;
const MAX_BYTES = 64 * 1024 * 1024;
const MAX_FILES = 4000;
const digest = data => crypto.createHash('sha256').update(data).digest('hex');
const exists = async p => fs.access(p).then(() => true, () => false);
async function readJSON(p, fallback) { try { return JSON.parse((await fs.readFile(p, 'utf8')).replace(/^\uFEFF/,'')); } catch (e) { if(e.code === 'ENOENT') return fallback; throw e; } }
async function atomicJSON(p, data) {
  await fs.mkdir(path.dirname(p), {recursive:true});
  const tmp = p + '.' + crypto.randomUUID() + '.tmp';
  try { await fs.writeFile(tmp, JSON.stringify(data, null, 2), {mode:0o600}); await fs.rename(tmp, p); }
  finally { await fs.rm(tmp, {force:true}); }
}
function safePath(p) {
  if (typeof p !== 'string' || !p || p.length > 500 || /[\\\x00-\x1f<>:"|?*]/.test(p) || path.posix.isAbsolute(p)) throw Error('文件路径不安全');
  if (p.split('/').some(s => !s || s === '.' || s === '..' || /[. ]$/.test(s) || /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)/i.test(s))) throw Error('文件名不兼容 Mac / Windows');
  if (p.split('/').includes('cocos-game-finished-product-check')) throw Error('检测成品 Skill 为本机专用，不能共享');
  return p;
}
async function collect(root,{localUse=false}={}) {
  root = await fs.realpath(root);
  if (!localUse && path.basename(root) === 'cocos-game-finished-product-check') throw Error('检测成品 Skill 为本机专用，不能共享');
  const files = [], blobs = new Map(), names = new Set(); let bytes = 0;
  async function walk(dir, prefix='') {
    for (const entry of (await fs.readdir(dir, {withFileTypes:true})).sort((a,b)=>a.name<b.name?-1:a.name>b.name?1:0)) {
      if (entry.name.startsWith('.') || ['node_modules','__pycache__'].includes(entry.name)) continue;
      const rel = safePath(prefix + entry.name), absolute = path.join(dir, entry.name);
      if (entry.isSymbolicLink()) throw Error('共享目录包含符号链接：' + rel);
      if (entry.isDirectory()) { await walk(absolute, rel + '/'); continue; }
      if (!entry.isFile()) throw Error('不支持的文件：' + rel);
      const stat = await fs.stat(absolute); bytes += stat.size;
      if (bytes > MAX_BYTES || files.length >= MAX_FILES) throw Error('Skill 超过 64 MB / 4000 文件上限');
      const key = rel.normalize('NFC').toLowerCase(); if (names.has(key)) throw Error('存在跨平台同名冲突：' + rel); names.add(key);
      const data = await fs.readFile(absolute), hash = digest(data);
      files.push({path:rel, hash, size:data.length, executable: !!(stat.mode & 0o111)}); blobs.set(hash, data);
    }
  }
  await walk(root);
  if (!files.some(f=>f.path === 'SKILL.md' || f.path.endsWith('/SKILL.md'))) throw Error('请选择包含 SKILL.md 的 Skill 文件夹');
  const treeHash = digest(JSON.stringify(files));
  return {files, blobs, bytes, treeHash};
}
function validateRelease(r) {
  if (!r || !ID.test(r.id) || !ID.test(r.skillId) || typeof r.name !== 'string' || r.name.length > 160 || typeof r.summary !== 'string' || r.summary.length > 10000 || !HASH.test(r.treeHash) || !Array.isArray(r.files) || !r.files.length || r.files.length > MAX_FILES) throw Error('版本清单格式无效');
  if(r.directory){safePath(r.directory);if(r.directory.includes('/'))throw Error('Skill 目录无效');}
  let total=0; const names=new Set();
  for (const f of r.files) {
    safePath(f.path); const key=f.path.normalize('NFC').toLowerCase();
    if(names.has(key) || !HASH.test(f.hash) || !Number.isSafeInteger(f.size) || f.size < 0) throw Error('版本文件清单无效');
    names.add(key); total += f.size;
  }
  if (total > MAX_BYTES || digest(JSON.stringify(r.files)) !== r.treeHash) throw Error('版本清单校验失败');
  return r;
}
function light(r) { const {files, ...meta} = r; return meta; }
class HubStore {
  constructor(root) { this.root=root; }
  async index() { return readJSON(path.join(this.root, 'index.json'), {schema:1, releases:[]}); }
  async release(id) { if(!ID.test(id)) throw Error('版本编号无效'); return readJSON(path.join(this.root,'releases',id+'.json'),null); }
  async publish(source, name, note='') {
    if (typeof name !== 'string' || !name.trim() || name.length>160 || note.length>8000) throw Error('请输入有效的 Skill 名称与更新说明');
    const snapshot = await collect(source), idx = await this.index();
    const skillId = 's-' + digest(name.trim()).slice(0,20);
    const prev = idx.releases.find(r=>r.skillId===skillId);
    if (prev?.treeHash === snapshot.treeHash) return {changed:false, release:prev};
    const old = prev ? await this.release(prev.id) : null;
    const oldFiles = new Map((old?.files||[]).map(f=>[f.path,f.hash]));
    const added=snapshot.files.filter(f=>!oldFiles.has(f.path)).length;
    const modified=snapshot.files.filter(f=>oldFiles.has(f.path)&&oldFiles.get(f.path)!==f.hash).length;
    const deleted=(old?.files||[]).filter(f=>!snapshot.files.some(n=>n.path===f.path)).length;
    const count=idx.releases.filter(r=>r.skillId===skillId).length+1;
    const fileNote = await fs.readFile(path.join(source,'UPDATE.md'),'utf8').catch(e=>{if(e.code==='ENOENT')return '';throw e;});
    note = note.trim() || fileNote.trim().slice(0,8000);
    const directory=/^(cocos-|game-|ego-|grok-|desktop-|mobile-|chrome-)[a-z0-9-]+$/.test(path.basename(source))?path.basename(source):undefined;
    const release={id:crypto.randomUUID(), skillId, ...(directory?{directory}:{}), name:name.trim(), version:'v'+count, createdAt:new Date().toISOString(), summary:note.trim() || `文件变更：新增 ${added}，修改 ${modified}，移除 ${deleted}。`, changes:{added,modified,deleted}, treeHash:snapshot.treeHash, bytes:snapshot.bytes, fileCount:snapshot.files.length, files:snapshot.files};
    await fs.mkdir(path.join(this.root,'blobs'),{recursive:true});
    for(const [hash,data] of snapshot.blobs) { const dest=path.join(this.root,'blobs',hash); if(!await exists(dest)) await fs.writeFile(dest,data,{flag:'wx'}).catch(e=>{if(e.code!=='EEXIST')throw e;}); }
    await atomicJSON(path.join(this.root,'releases',release.id+'.json'), release);
    idx.releases.unshift(light(release)); await atomicJSON(path.join(this.root,'index.json'),idx);
    return {changed:true, release:light(release)};
  }
}
async function startHub(store, {host='127.0.0.1',port=0,token=crypto.randomBytes(24).toString('hex')}={}) {
  const peers=new Set();
  const server=http.createServer(async(req,res)=>{
    try {
      if(req.headers.origin) { res.writeHead(403); return res.end('Desktop clients only'); }
      const auth=Buffer.from(req.headers.authorization||''), wanted=Buffer.from('Bearer '+token);
      if(auth.length!==wanted.length||!crypto.timingSafeEqual(auth,wanted)){res.writeHead(401);return res.end('Unauthorized');}
      if(req.method!=='GET'){res.writeHead(405);return res.end();}
      const url=new URL(req.url,'http://localhost');
      res.setHeader('Cache-Control','no-store'); res.setHeader('X-Content-Type-Options','nosniff');
      if(url.pathname==='/events') {
        res.writeHead(200,{'Content-Type':'text/event-stream','Connection':'keep-alive'}); res.write(': connected\n\n'); peers.add(res);
        req.on('close',()=>peers.delete(res)); return;
      }
      if(url.pathname==='/index.json'){res.setHeader('Content-Type','application/json');return res.end(JSON.stringify(await store.index()));}
      const rel=url.pathname.match(/^\/releases\/([a-zA-Z0-9_-]+)$/);
      if(rel){const r=await store.release(rel[1]);if(!r){res.writeHead(404);return res.end();}res.setHeader('Content-Type','application/json');return res.end(JSON.stringify(r));}
      const blob=url.pathname.match(/^\/blobs\/([a-f0-9]{64})$/);
      if(blob){const data=await fs.readFile(path.join(store.root,'blobs',blob[1]));res.setHeader('Content-Type','application/octet-stream');return res.end(data);}
      res.writeHead(404);res.end();
    }catch(e){res.writeHead(e.code==='ENOENT'?404:500);res.end('Request failed');}
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,host,resolve);});
  const heartbeat=setInterval(()=>{for(const p of peers)p.write(': keepalive\n\n');},20000);heartbeat.unref();
  return {port:server.address().port,token, notify:()=>{for(const p of peers)p.write('data: changed\n\n');}, close:async()=>{clearInterval(heartbeat);for(const p of peers)p.end();await new Promise(resolve=>{server.close(resolve);server.closeAllConnections();});}};
}
function connection(c) {
  if(c.feedMode==='github')return {feedMode:'github',repository:require('./github.cjs').repository(c.repository)};
  const u=new URL(c.url);
  if(u.username||u.password||u.search||u.hash||u.pathname!=='/' || !['http:','https:'].includes(u.protocol)) throw Error('请输入同步服务根地址');
  const local=u.hostname==='localhost'||u.hostname==='127.0.0.1'||u.hostname==='[::1]'||/^10\./.test(u.hostname)||/^192\.168\./.test(u.hostname)||/^172\.(1[6-9]|2\d|3[01])\./.test(u.hostname);
  if(u.protocol==='http:'&&!local) throw Error('公网同步地址请使用 HTTPS');
  if(typeof c.token!=='string'||c.token.length<24||c.token.length>200)throw Error('订阅密钥无效');
  return {url:u.origin, token:c.token};
}
async function request(c, route, binary=false) {
  c=connection(c);if(c.feedMode==='github'){const data=await require('./github.cjs').readFeed(c.repository,route);if(data.length>MAX_BYTES)throw Error('响应体过大');return binary?data:JSON.parse(data.toString('utf8'));} const res=await fetch(c.url+route,{headers:{Authorization:'Bearer '+c.token},signal:AbortSignal.timeout(20000),redirect:'error'});
  if(!res.ok)throw Error(res.status===401?'订阅密钥不正确':`同步请求失败 (${res.status})`);
  const length=Number(res.headers.get('content-length'));if(length>MAX_BYTES)throw Error('响应体过大');
  let total=0; const chunks=[];
  for await(const chunk of res.body){total+=chunk.length;if(total>MAX_BYTES)throw Error('响应体过大');chunks.push(chunk);}
  const data=Buffer.concat(chunks);return binary?data:JSON.parse(data.toString('utf8'));
}
// Stage with hard links: unchanged files retain inode, timestamps and contents.
// Detach changed files before writing, so failures cannot mutate the live tree.
async function linkTree(source,target){
 const stat=await fs.lstat(source);if(stat.isSymbolicLink())throw Error('本机 Skill 包含符号链接');
 if(!stat.isDirectory())throw Error('Skill 目录无效');
 for(const entry of await fs.readdir(source,{withFileTypes:true})){
  const from=path.join(source,entry.name),to=path.join(target,entry.name);
  if(entry.isSymbolicLink())throw Error('本机 Skill 包含符号链接：'+entry.name);
  if(entry.isDirectory()){await fs.mkdir(to,{recursive:true});await linkTree(from,to);}
  else if(entry.isFile()){if(await exists(to))continue;try{await fs.link(from,to);}catch(e){if(!['ENOTSUP','EPERM','EXDEV'].includes(e.code))throw e;await fs.copyFile(from,to);const st=await fs.stat(from);await fs.utimes(to,st.atime,st.mtime);}}
  else throw Error('Skill 含不支持的本机文件');
 }
}
class ClientStore {
  constructor(root){this.root=root;}
  async recover(){
    const journal=await readJSON(path.join(this.root,'transaction.json'),null);
    if(!journal)return;
    if(!ID.test(journal.skillId)||!ID.test(journal.releaseId)||!ID.test(journal.stageId))throw Error('本地恢复记录无效');
    if(journal.directory){safePath(journal.directory);if(journal.directory.includes('/'))throw Error('恢复目录无效');}
    const dest=path.join(this.root,'skills',journal.directory||journal.skillId),backup=dest+'.previous',stage=dest+'.stage-'+journal.stageId;
    const state=await this.state();
    if(state[journal.skillId]?.id!==journal.releaseId){
      if(await exists(backup)){await fs.rm(dest,{recursive:true,force:true});await fs.rename(backup,dest);}
      else if(!journal.had)await fs.rm(dest,{recursive:true,force:true});
    }
    await fs.rm(backup,{recursive:true,force:true});await fs.rm(stage,{recursive:true,force:true});await fs.rm(path.join(this.root,'transaction.json'),{force:true});
  }
  async state(){return readJSON(path.join(this.root,'installed.json'),{});}
  async sync(c) {
    const index=await request(c,'/index.json');
    if(index.schema!==1||!Array.isArray(index.releases)||index.releases.length>100000)throw Error('订阅索引无效');
    // Index contains metadata only. Historical file lists and blobs are fetched on demand.
    for(const r of index.releases)if(!ID.test(r.id)||!ID.test(r.skillId)||typeof r.name!=='string'||typeof r.version!=='string'||typeof r.summary!=='string'||!HASH.test(r.treeHash))throw Error('订阅索引条目无效');
    await atomicJSON(path.join(this.root,'index.json'),index); return index;
  }
  async install(c,id,options={}) {
    const operation=(this.installQueue||Promise.resolve()).catch(()=>{}).then(()=>this.installOne(c,id,options));
    this.installQueue=operation;return operation;
  }
  async installOne(c,id,{replace=false}={}) {
    const release=validateRelease(await request(c,'/releases/'+id));
    await this.recover();
    let directory=release.directory||release.skillId;const existing=await this.state();
    const normalize=value=>String(value||'').normalize('NFC').toLowerCase();
    const samePath=(a,b)=>process.platform==='win32'?normalize(path.resolve(a))===normalize(path.resolve(b)):path.resolve(a)===path.resolve(b);
    // Directory identity is stronger than a display title. Only a canonical
    // component may adopt legacy records with the same canonical name.
    const canonical=release.directory&&(release.skillId==='s-'+digest(release.directory).slice(0,20)||normalize(release.name)===normalize(release.directory));
    const aliases=Object.entries(existing).filter(([key,s])=>key!==release.skillId&&canonical&&normalize(s.name)===normalize(release.directory)&&normalize(path.basename(s.path))===normalize(release.directory));
    const aliasIds=new Set(aliases.map(([key])=>key));
    const claimed=folder=>Object.entries(existing).some(([key,s])=>key!==release.skillId&&!aliasIds.has(key)&&samePath(s.path,path.join(this.root,'skills',folder)));
    // A different Skill can legitimately use the same preferred folder name.
    // Give it a stable private directory instead of mixing files or blocking all updates.
    if(claimed(directory))directory+='--'+digest(release.skillId).slice(0,20);
    if(claimed(directory))throw Error('Skill 安装记录异常：'+release.name+'，目标目录被其他组件占用');
    const stageId=crypto.randomUUID(),dest=path.join(this.root,'skills',directory), stage=dest+'.stage-'+stageId, backup=dest+'.previous';
    await fs.mkdir(stage,{recursive:true});
    try {
      const current=existing[release.skillId]||aliases[0]?.[1]||this.seeds?.[release.skillId];
      if(!replace){
        if(await exists(dest))await linkTree(dest,stage);
        // ZIP imports live outside skills/. Preserve their local additions too.
        for(const item of [current,...aliases.map(([,s])=>s)])if(item?.path&&!samePath(item.path,dest)&&await exists(item.path))await linkTree(item.path,stage);
      }
      const stats={unchanged:0,added:0,updated:0};
      for(const f of release.files){
        const p=path.join(stage,...f.path.split('/'));let data,match=false;
        if(current?.path){try{const candidate=await fs.readFile(path.join(current.path,...f.path.split('/')));if(candidate.length===f.size&&digest(candidate)===f.hash){data=candidate;match=true;}}catch{}}
        if(match&&await exists(p)){const st=await fs.stat(p),staged=await fs.readFile(p);if(staged.length===f.size&&digest(staged)===f.hash&&(!!(st.mode&0o111)===!!f.executable||process.platform==='win32')){stats.unchanged++;continue;}}
        if(!data)data=await request(c,'/blobs/'+f.hash,true);
        if(data.length!==f.size||digest(data)!==f.hash)throw Error('文件哈希校验失败：'+f.path);
        const present=await exists(p);if(present){const st=await fs.lstat(p);if(!st.isFile())throw Error('Skill 文件与本机目录冲突：'+f.path);await fs.unlink(p);}
        await fs.mkdir(path.dirname(p),{recursive:true});await fs.writeFile(p,data,{mode:f.executable?0o755:0o644});stats[present?'updated':'added']++;
      }
      await collect(stage,{localUse:true});
      const installation={...light(release),files:release.files,path:dest,installMode:replace?'replace':'merge',installStats:stats};
      // Crash recovery: retain the previous tree until both replacement and ledger commit succeed.
      if(await exists(backup)&&!await exists(dest))await fs.rename(backup,dest);
      await fs.rm(backup,{recursive:true,force:true});
      const had=await exists(dest);
      await atomicJSON(path.join(this.root,'transaction.json'),{skillId:release.skillId,releaseId:release.id,stageId,had,directory});
      if(had)await fs.rename(dest,backup);
      try {await fs.rename(stage,dest);const state=await this.state();for(const key of aliasIds)delete state[key];state[release.skillId]=installation;await atomicJSON(path.join(this.root,'installed.json'),state);}
      catch(e){await fs.rm(dest,{recursive:true,force:true});if(had)await fs.rename(backup,dest);await fs.rm(path.join(this.root,'transaction.json'),{force:true});throw e;}
      await fs.rm(backup,{recursive:true,force:true});
      await fs.rm(path.join(this.root,'transaction.json'),{force:true});
      return installation;
    } finally {await fs.rm(stage,{recursive:true,force:true});}
  }
}
function makePrompt(game, installed, action='update') {
  if(!game?.name||!game?.path||!installed?.path)throw Error('请先选择游戏并获取 Skill 文件');
  const tasks={update:'根据这次 Skill 更新，检查当前游戏受影响的部分，按新版规则定点处理并验证。',check:'按此 Skill 检查当前游戏，先读取现有进度与证据，执行本阶段必要检查。',start:'按此 Skill 启动当前游戏的制作，先读取项目规则、已有文件与进度，再继续当前阶段。'};
  return `当前游戏：${game.name}\n项目目录：${game.path}\n\n请重新读取本机 Skill 文件，不沿用对话里的旧版摘要：\nSkill：${installed.name} ${installed.version}\nSkill 目录：${installed.path}\n文件树 SHA-256：${installed.treeHash}\n先读取该目录的 SKILL.md，再按需读取其 references、scripts 等配套文件。\n\n本次更新说明：\n${installed.summary}\n\n${tasks[action]||tasks.update}\n保留原始素材、存档与已确认的玩法。说明本次实际读取的 Skill 版本、处理内容、验证结果及未完成项。此次不自动上传或发布游戏。\n`;
}
const addresses=()=>Object.values(os.networkInterfaces()).flat().filter(a=>a.family==='IPv4'&&!a.internal).map(a=>a.address);
module.exports={HubStore,ClientStore,startHub,collect,validateRelease,makePrompt,atomicJSON,readJSON,connection,request,digest,addresses};
