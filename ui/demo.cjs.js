// Browser-only interaction preview. The packaged desktop app uses its isolated preload API.
if(!window.dock){
  window.isDemo=true;document.body.classList.add('preview');
  const s1={id:'release-3',skillId:'demo-art',name:'游戏重塑',version:'v3',createdAt:'2026-10-26T01:20:00Z',summary:'调整手机首页按钮尺寸与布局。\n补充重开、异步恢复和存档检查，制作前先确认当前输入。',bytes:284900,fileCount:24,treeHash:'a'.repeat(64)},s2={...s1,id:'release-2',version:'v2',createdAt:'2026-10-25T01:20:00Z',summary:'补充首关交互与手机适配检查。'},s3={...s1,id:'release-1',version:'v1',createdAt:'2026-10-24T01:20:00Z',summary:'建立制作流程与原创美术检查规范。'};
  let demo={games:[{id:'g1',name:'松果邮局',path:'/示例项目/PineconePost',stage:'玩法制作',note:'首页已完成，接下来检查手机按钮和重开流程。',updatedAt:'2026-10-26T02:00:00Z'},{id:'g2',name:'月亮面包房',path:'/示例项目/MoonBakery',stage:'检查',note:'新版本已整理，等待按新版 Skill 检查。',updatedAt:'2026-10-25T02:00:00Z'},{id:'g3',name:'小岛收纳日记',path:'/示例项目/IslandTidy',stage:'待试玩',note:'本地预览已准备，继续核对本轮反馈。',updatedAt:'2026-10-25T02:00:00Z'}],repository:'SJT-bright/game-skill-workbench',appUpdate:{available:false,busy:false,error:''},sources:[],settings:{url:'https://skills.example.com',autoDownload:true,connected:true,port:47831},index:{releases:[s1,s2,s3]},installed:{'demo-art':{...s1,path:'/示例 Skill/游戏重塑'}},lastCheck:new Date().toISOString(),status:'演示：Skill 已同步',lastError:'',busy:false,hosting:false,hostUrls:[],codex:{busy:false,error:'',incomplete:false},dockEdge:'right',platform:'darwin',version:'0.2.0',collapsed:false};
  for(const g of demo.games){g.threadId='11111111-1111-4111-8111-111111111111';g.stageMode='auto';}
  let listeners=[];const emit=()=>listeners.forEach(fn=>fn(structuredClone(demo)));
  function prompt(v){const game=demo.games.find(g=>g.id===v.gameId),skill=demo.installed[v.skillId];if(!game||!skill)throw Error('请选择游戏和 Skill');return `当前游戏：${game.name}\n项目目录：${game.path}\n\n请重新读取本机 Skill：${skill.name} ${skill.version}\nSkill 目录：${skill.path}\n\n本次更新说明：\n${skill.summary}\n\n根据新版 Skill 检查当前游戏受影响的部分，定点处理并验证。保留原件、存档与已确认玩法。\n\n此处为交互演示，正式客户端会附上真实本机文件路径和 SHA-256。`;}
  window.dock={onState:fn=>{listeners.push(fn);return()=>listeners=listeners.filter(f=>f!==fn);},drag:()=>{},call:async(method,v)=>{
    if(method==='sendGame')return {status:'demo',detail:'演示未实际发送'};
    if(['syncCodex','refreshSkills'].includes(method)){emit();return structuredClone(demo);}
    if(method==='openChat')throw Error('演示不打开真实对话');
    if(method==='state')return structuredClone(demo);
    if(method==='chooseFolder')return demo.platform==='win32'?'C:\\Games\\MyGame':'/示例项目/MyGame';
    if(method==='taskText')return prompt(v);
    if(method==='copyTask'){await navigator.clipboard.writeText(prompt(v));return prompt(v);}
    if(method==='exportTask')return '/交互演示/Skill交接.zip';
    if(['reveal','exportConnection'].includes(method))throw Error('这是交互演示；真实文件操作请使用桌面客户端');
    if(method==='importConnection'){demo.settings.connected=true;demo.status='演示：连接已导入';}
    if(method==='settings'){demo.settings={...demo.settings,...v,connected:true};}
    if(method==='disconnect'){demo.settings.connected=false;demo.index.releases=[];demo.status='未连接同步源';}
    if(method==='sync'){demo.lastCheck=new Date().toISOString();}
    if(method==='install'){const r=demo.index.releases.find(r=>r.id===v.id);demo.installed[r.skillId]={...r,path:'/示例 Skill/'+r.name};}
    if(method==='saveGame'){if(!v.path)throw Error('请选择项目文件夹');const g={...v,id:v.id||crypto.randomUUID(),updatedAt:new Date().toISOString()};demo.games=demo.games.filter(x=>x.id!==g.id);demo.games.unshift(g);emit();return g;}
    if(method==='removeGame')demo.games=demo.games.filter(x=>x.id!==v);
    if(method==='collapse')demo.collapsed=!demo.collapsed;
    if(method==='addSource'){demo.sources.push({...v,id:crypto.randomUUID(),auto:false});}
    if(method==='removeSource')demo.sources=demo.sources.filter(x=>x.id!==v);
    if(method==='sourceAuto')demo.sources.find(x=>x.id===v.id).auto=v.auto;
    if(method==='startSharing'){demo.hosting=true;demo.localUrl='http://127.0.0.1:47831';}
    if(method==='stopSharing')demo.hosting=false;
    if(method==='subscribeSelf'){demo.settings.connected=true;demo.status='演示：已订阅本机发布端';}
    if(method==='publish'){const src=demo.sources.find(x=>x.id===v.id);src.lastVersion='v1';emit();return {changed:true};}
    if(method==='quit')throw Error('交互演示可以保留；正式客户端可从这里退出');
    emit();return structuredClone(demo);
  }};
  const switcher=document.createElement('div');switcher.className='preview-switch';switcher.innerHTML='<button class="active" data-platform="darwin">macOS</button><button data-platform="win32">Windows</button>';document.body.append(switcher);
  switcher.addEventListener('click',e=>{if(!e.target.dataset.platform)return;demo.platform=e.target.dataset.platform;switcher.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b===e.target));emit();});
}
