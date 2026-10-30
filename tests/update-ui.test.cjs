const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../ui/app.js'),'utf8');
function harness(patch={},preferences={}){
 const app={innerHTML:'',addEventListener(){}},modal={addEventListener(){}},listeners={},calls=[];
 let onState;const initial={games:[],installed:{},index:{releases:[]},settings:{},sources:[],collapsed:true,updateNotices:[],...patch};
 const context=vm.createContext({localStorage:{getItem:()=>JSON.stringify(preferences),setItem:(_,v)=>Object.assign(preferences,JSON.parse(v))},SkillCategories:require('../ui/skill-categories.js'),ThreadSelection:require('../ui/thread-selection.js'),document:{querySelector:q=>q==='#app'?app:q==='#modal'?modal:null,querySelectorAll:()=>[],addEventListener:(event,fn)=>listeners[event]=fn,body:{classList:{toggle(){}},dataset:{}}},window:{dock:{call:async(method,value)=>{calls.push([method,value]);return initial;},onState:fn=>onState=fn}},setInterval(){},setTimeout(){},clearTimeout(){},console});
 vm.runInContext(source,context);vm.runInContext('state='+JSON.stringify(initial),context);
 return {app,calls,run:code=>vm.runInContext(code,context),emit:s=>onState(s),click:async dataset=>listeners.click({target:{closest:selector=>selector==='button,[data-game]'?{dataset,hasAttribute:()=>false}:null}}),initial};
}
test('Only English and remake bundles appear even with many private and supporting Skills installed',()=>{
 const entries=['cocos-game-to-english','cocos-game-from-starter','game-audio-library','cocos-game-finished-product-check'].map(name=>({skillId:name,name,local:true}));
 const ui=harness({installed:Object.fromEntries(entries.map(x=>[x.skillId,x]))});
 assert.equal(ui.run('usableSkills().length'),2);
 assert.equal(ui.run('latest().map(x=>x.skillId).join(",")'),'bundle-english,bundle-remake');
 assert.equal(ui.run('usableSkills().some(x=>x.name.includes("finished"))'),false);
});
test('Installed updates remain unread and pinned notices do not claim installation',async()=>{
 const ui=harness({updateNotices:[{id:'v2',kind:'skill',status:'updated'},{id:'v3',kind:'skill',status:'pinned'}]});
 assert.match(ui.run('nav()'),/update-count">2</);
 assert.match(ui.run('updateInbox()'),/已更新 1 · 保留版本 1/);
 ui.run('tab="skills";render()');
 assert.equal(ui.calls.some(([method])=>method==='ackUpdates'),false);
 await ui.click({action:'ackUpdates'});
 assert.equal(ui.calls.filter(([method])=>method==='ackUpdates').length,1);
});
test('Collapsed update dot reacts to notice and application changes without game count changes',()=>{
 const ui=harness();ui.run('render()');assert.doesNotMatch(ui.app.innerHTML,/edge-update-dot/);
 ui.emit({...ui.initial,updateNotices:[{id:'v2',kind:'skill',status:'updated'}]});assert.match(ui.app.innerHTML,/edge-update-dot/);
 ui.emit({...ui.initial});assert.doesNotMatch(ui.app.innerHTML,/edge-update-dot/);
 ui.emit({...ui.initial,appUpdate:{available:true,manifest:{version:'0.2.4'}}});assert.match(ui.app.innerHTML,/edge-update-dot/);
});
test('Settings show real versions, checked times, and escaped sync errors',()=>{
 const ui=harness({version:'0.2.3',lastCheck:'2026-10-27T02:00:00Z',lastError:'<sync failed>',appUpdate:{available:true,manifest:{version:'0.2.4'},checkedAt:'2026-10-27T03:00:00Z'}});
 const html=ui.run('settings()');assert.match(html,/0\.2\.3/);assert.match(html,/0\.2\.4/);assert.match(html,/最近同步/);assert.match(html,/&lt;sync failed&gt;/);assert.match(html,/检查/);
});
test('Two-package view preserves opt-in component version history and restore actions',()=>{
 const ui=harness({installed:{english:{skillId:'english',name:'cocos-game-to-english',id:'v2',local:false}},index:{releases:[{skillId:'english',name:'cocos-game-to-english',id:'v2',version:'v2',summary:'latest'},{skillId:'english',name:'cocos-game-to-english',id:'v1',version:'v1',summary:'older'}]}});
 ui.run('histories.add("bundle-english")');const html=ui.run('skills()');assert.match(html,/data-history="bundle-english"/);assert.match(html,/data-restore="v1"/);assert.match(html,/当前使用/);assert.match(html,/cocos-game-to-english · v1/);
});

test('Selection and category survive restart and background refresh without changing the chosen target',()=>{const preferences={selectedGame:'b',skillCategory:'重塑',filter:'测试阶段',activityFilter:'ongoing'},ui=harness({games:[{id:'a'},{id:'b'}]},preferences);ui.run('render()');assert.equal(ui.run('selectedGame'),'b');assert.equal(ui.run('skillCategory'),'重塑');ui.emit({...ui.initial,games:[{id:'a',name:'changed'},{id:'b'}]});assert.equal(ui.run('selectedGame'),'b');assert.equal(preferences.selectedGame,'b');ui.run('filter="全部";render()');assert.equal(preferences.selectedGame,'b');});
test('each game restores its workflow and filtered-out targets cannot be pushed from the footer',()=>{const games=[{id:'a',threadId:'ta',name:'One',path:'/games/One',workflow:'英化'},{id:'b',threadId:'tb',name:'Two',path:'/games/Two',workflow:'重塑'}],installed=Object.fromEntries(['cocos-game-to-english','cocos-game-from-starter'].map(name=>[name,{name,skillId:name,local:true}]));const ui=harness({games,installed,collapsed:false});ui.run('selectGame("a")');assert.equal(ui.run('skillCategory'),'英化');ui.run('selectGame("b")');assert.equal(ui.run('skillCategory'),'重塑');ui.run('query="does-not-match"');assert.equal(ui.run('targetVisible()'),false);assert.match(ui.run('launch()'),/目标被筛选隐藏/);assert.match(ui.run('launch()'),/data-action="push" disabled/);});
test('multi-chat groups collapse without losing the selected conversation',()=>{const games=[{id:'a',threadId:'ta',path:'/games/One',name:'Older'},{id:'b',threadId:'tb',path:'/games/One',name:'Newer'}],ui=harness({games,collapsed:false});ui.run('selectedGame="b"');assert.equal(ui.run('visibleThreads(threadBoard().groups[0])[0].id'),'b');assert.equal(ui.run('visibleThreads(threadBoard().groups[0]).length'),1);ui.run('expandedGroups.add(threadBoard().groups[0].key)');assert.equal(ui.run('visibleThreads(threadBoard().groups[0]).length'),2);});
test('browsing the other Skill package does not silently change the game workflow',async()=>{const ui=harness({games:[{id:'a',name:'One',path:'/games/One',workflow:'英化'}],collapsed:false,installed:Object.fromEntries(['cocos-game-to-english','cocos-game-from-starter'].map(name=>[name,{name,skillId:name,local:true}]))});ui.run('selectedGame="a";tab="skills"');await ui.click({skillCategory:'重塑'});assert.equal(ui.run('skillCategory'),'重塑');assert.equal(ui.calls.some(([method])=>method==='setGamePreferences'),false);ui.run('tab="games";render()');assert.equal(ui.run('skillCategory'),'英化');});
