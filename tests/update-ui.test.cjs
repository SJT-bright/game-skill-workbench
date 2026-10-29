const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../ui/app.js'),'utf8');
function harness(patch={}){
 const app={innerHTML:'',addEventListener(){}},modal={addEventListener(){}},listeners={},calls=[];
 let onState;const initial={games:[],installed:{},index:{releases:[]},settings:{},sources:[],collapsed:true,updateNotices:[],...patch};
 const context=vm.createContext({SkillCategories:require('../ui/skill-categories.js'),ThreadSelection:require('../ui/thread-selection.js'),document:{querySelector:q=>q==='#app'?app:q==='#modal'?modal:null,querySelectorAll:()=>[],addEventListener:(event,fn)=>listeners[event]=fn,body:{classList:{toggle(){}},dataset:{}}},window:{dock:{call:async(method,value)=>{calls.push([method,value]);return initial;},onState:fn=>onState=fn}},setInterval(){},setTimeout(){},clearTimeout(){},console});
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
