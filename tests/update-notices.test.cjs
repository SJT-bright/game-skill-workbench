const test=require('node:test'),assert=require('node:assert/strict');
const {mergeNotices,notificationBody,SKILL_POLL_MS,APPLICATION_POLL_MS}=require('../src/update-notices.cjs');
const release={id:'r2',skillId:'s',name:'Game Skill',version:'v2',summary:'文件更新'};
test('downloaded notices remain unread across repeated sync and replacement uses latest version only',()=>{
 const first=mergeNotices([], [release],{installed:{s:{id:'r2'}},now:'2026-10-27T01:00:00Z'});assert.equal(first[0].status,'updated');assert.deepEqual(mergeNotices(first,[]),first);
 const next=mergeNotices(JSON.parse(JSON.stringify(first)),[{...release,id:'r3',version:'v3'}],{installed:{s:{id:'r3'}},now:'2026-10-27T02:00:00Z'});assert.equal(next.length,1);assert.equal(next[0].version,'v3');assert.match(notificationBody(next),/已更新/);
});
test('history pins and disabled auto-download must not be described as installed',()=>{
 const pinned=mergeNotices([],[release],{installed:{s:{id:'r1'}},pins:{s:true}});assert.equal(pinned[0].status,'pinned');assert.match(notificationBody(pinned),/保留历史版本/);assert.doesNotMatch(notificationBody(pinned),/已更新/);
 assert.equal(mergeNotices([],[release],{installed:{s:{id:'r1'}}})[0].status,'available');
});
test('software and Skill checks are automatic and bounded',()=>{assert.equal(SKILL_POLL_MS,60000);assert.equal(APPLICATION_POLL_MS,300000);});
